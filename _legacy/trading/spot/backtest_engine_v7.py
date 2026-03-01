"""Spot DCA Backtest Engine V7 — Conviction Gate Fixes + Trend Direction Penalty.

Extends V6 with three targeted fixes, all with tunable parameters for sweeps:
  Fix 1: Invert conviction gate — tunable floor for dwell compression
  Fix 2: Spring entries optionally bypass conviction gate in Phase 3
  Fix 3: Trend direction penalty on deal opening (tunable ADX + conviction thresholds)

Tunable parameters (constructor kwargs):
  dwell_conviction_floor (30)  — min conviction for full dwell compression
  spring_score_threshold (60)  — min spring score to trigger Phase 3 entry
  spring_bypass_conviction (True) — whether spring skips conviction gate
  trend_gate_adx (25)          — ADX threshold for bearish trend detection
  trend_gate_conviction (50)   — min conviction to open deal in bearish trend

See: projects/ait-product/dwell-time-compression-spec.md
"""
import logging
from typing import Optional

import numpy as np
import pandas as pd

from .backtest_engine_v6 import (
    SpotBacktestEngineV6,
    COIN_LIQUIDITY,
    LIQUIDITY_FLOOR_BOOST,
    DONCHIAN_LOOKBACK,
    DONCHIAN_RANGE_MAX_PCT,
)
from .backtest_engine_v5 import (
    PHASE1_DD_MAX,
    PHASE2_DD_MAX,
    SPRING_THRESHOLD,
    SPRING_MAX_ENTRIES,
    SPRING_MIN_CONVICTION,
)
from .backtest_engine_v4 import (
    HARD_SNAPBACK_REGIMES,
    SOFT_SNAPBACK_REGIMES,
)
from .backtest_engine_v3 import (
    BacktestResult,
    BLOCKED_REGIMES,
)
from ..regime_detector import classify_regime_v2
from ..indicators import (
    atr as compute_atr,
    atr_pct as compute_atr_pct,
    compute_all as compute_all_indicators,
    bollinger_band_width,
    volume_sma,
)

logger = logging.getLogger(__name__)


class SpotBacktestEngineV7(SpotBacktestEngineV6):
    """V6 engine + conviction gate fixes, spring bypass, trend direction penalty.

    All fix thresholds are tunable via constructor kwargs for parameter sweeps.
    """

    def __init__(self, **kwargs):
        # Extract V7-specific params before passing to parent
        self._dwell_conviction_floor: float = kwargs.pop("dwell_conviction_floor", 30.0)
        self._spring_score_threshold: float = kwargs.pop("spring_score_threshold", 60.0)
        self._spring_bypass_conviction: bool = kwargs.pop("spring_bypass_conviction", True)
        self._trend_gate_adx: float = kwargs.pop("trend_gate_adx", 25.0)
        self._trend_gate_conviction: float = kwargs.pop("trend_gate_conviction", 50.0)

        super().__init__(**kwargs)
        self._spring_bypass = False  # Track per-candle

    @property
    def v7_params(self) -> dict:
        """Return current V7 tunable parameter values."""
        return {
            "dwell_conviction_floor": self._dwell_conviction_floor,
            "spring_score_threshold": self._spring_score_threshold,
            "spring_bypass_conviction": self._spring_bypass_conviction,
            "trend_gate_adx": self._trend_gate_adx,
            "trend_gate_conviction": self._trend_gate_conviction,
        }

    # ── Fix 1: Inverted conviction gate thresholds (tunable) ──────────

    def _apply_conviction_gate(self, dwell_decay: float, conviction: float) -> float:
        """Fix 1: conviction >= dwell_conviction_floor = full compression.

        Old (V6): >60 full, 40-60 half, <40 disabled
        New (V7): >=floor full, <floor disabled (floor default=30)
        """
        if conviction >= self._dwell_conviction_floor:
            self._conviction_gate = "full"
            return dwell_decay
        else:
            self._conviction_gate = "disabled"
            return 1.0

    # ── Fix 3: Trend direction penalty (tunable) ─────────────────────

    def _should_block_deal_for_trend(self, price: float, sma50_val: float,
                                      adx_val: float, conviction: float) -> bool:
        """Return True if deal should be blocked due to bearish trend."""
        if pd.isna(adx_val) or pd.isna(sma50_val):
            return False
        if adx_val > self._trend_gate_adx and price < sma50_val:
            return conviction < self._trend_gate_conviction
        return False

    # ── Main loop override ────────────────────────────────────────────

    def run(self, df: pd.DataFrame) -> BacktestResult:
        if len(df) < 100:
            logger.warning("Not enough data (%d rows)", len(df))
            return BacktestResult()

        df = compute_all_indicators(df)
        regimes = classify_regime_v2(df, self.timeframe)
        atr_pct_series = compute_atr_pct(df, 14)
        atr_abs_series = compute_atr(df, 14)
        sma50 = df["close"].rolling(50).mean()

        bbw = df["bbw"] if "bbw" in df.columns else bollinger_band_width(df["close"], 20)
        bbw_median = bbw.rolling(100, min_periods=20).median()

        vol = df["volume"]
        vol_avg = volume_sma(df, 20)

        from .backtest_engine_v5 import _stochastic
        stoch = _stochastic(df, 14, 3, 3)

        adx_series = df["adx_14"] if "adx_14" in df.columns else pd.Series(np.nan, index=df.index)

        donchian_high = df["high"].rolling(DONCHIAN_LOOKBACK).max()
        donchian_low = df["low"].rolling(DONCHIAN_LOOKBACK).min()
        donchian_range_pct = (donchian_high - donchian_low) / donchian_low.replace(0, np.nan) * 100
        price_series = df["close"]
        in_range_series = (
            (price_series >= donchian_low)
            & (price_series <= donchian_high)
            & (donchian_range_pct < DONCHIAN_RANGE_MAX_PCT)
        )

        logger.info("Running V7 backtest (dwell=%s, liq=%s, conv_floor=%.0f, spring_thresh=%.0f, "
                     "spring_bypass=%s, trend_adx=%.0f, trend_conv=%.0f): %s %s, $%.0f, profile=%s",
                     self.dwell.name, self._liquidity_class,
                     self._dwell_conviction_floor, self._spring_score_threshold,
                     self._spring_bypass_conviction, self._trend_gate_adx,
                     self._trend_gate_conviction,
                     self.symbol, self.timeframe,
                     self.initial_capital, self.profile.name)

        peak_equity = self.initial_capital
        self._candle_timeline = []

        for i in range(100, len(df)):
            row = df.iloc[i]
            ts = str(row["timestamp"])
            price = float(row["close"])
            high = float(row["high"])
            low = float(row["low"])

            regime = regimes.iloc[i] if i < len(regimes) else "UNKNOWN"
            self._current_regime = regime
            self._current_atr_pct = float(atr_pct_series.iloc[i]) if not pd.isna(atr_pct_series.iloc[i]) else 0.0
            self._current_atr_abs = float(atr_abs_series.iloc[i]) if not pd.isna(atr_abs_series.iloc[i]) else 0.0
            sma50_val = float(sma50.iloc[i]) if not pd.isna(sma50.iloc[i]) else None
            self._trend_bullish = price >= sma50_val if sma50_val is not None else True

            # ── Compute drawdown phase ────────────────────────────────
            equity = self._equity(price)
            if equity > peak_equity:
                peak_equity = equity
            dd = (peak_equity - equity) / peak_equity * 100 if peak_equity > 0 else 0.0

            if dd < PHASE1_DD_MAX:
                self._dd_phase = 1
                self._layer_sizing_mult = 1.0
            elif dd < PHASE2_DD_MAX:
                self._dd_phase = 2
                self._layer_sizing_mult = 0.5
            else:
                self._dd_phase = 3
                self._layer_sizing_mult = 1.0

            # ── Donchian-based dwell detection ────────────────────────
            cur_in_range = bool(in_range_series.iloc[i]) if not pd.isna(in_range_series.iloc[i]) else False
            cur_donchian_high = float(donchian_high.iloc[i]) if not pd.isna(donchian_high.iloc[i]) else 0.0
            cur_donchian_low = float(donchian_low.iloc[i]) if not pd.isna(donchian_low.iloc[i]) else 0.0
            cur_donchian_range_pct = float(donchian_range_pct.iloc[i]) if not pd.isna(donchian_range_pct.iloc[i]) else 0.0

            vol_val = float(vol.iloc[i]) if not pd.isna(vol.iloc[i]) else 0.0
            vol_avg_val = float(vol_avg.iloc[i]) if not pd.isna(vol_avg.iloc[i]) and vol_avg.iloc[i] > 0 else 1.0
            vol_spike = vol_val > vol_avg_val * 2.0

            cur_bbw = float(bbw.iloc[i]) if not pd.isna(bbw.iloc[i]) else 0.0
            cur_bbw_med = float(bbw_median.iloc[i]) if not pd.isna(bbw_median.iloc[i]) else cur_bbw

            if self._dd_phase == 1:
                if regime in HARD_SNAPBACK_REGIMES or vol_spike:
                    self._snap_back(hard=True)
                elif regime in SOFT_SNAPBACK_REGIMES:
                    self._snap_back(hard=False)
                else:
                    if self._dwell_cooldown_remaining > 0:
                        self._dwell_cooldown_remaining -= 1
                    if self._dwell_cooldown_remaining <= 0:
                        if cur_in_range:
                            self._dwell_candle_count += 1
                        else:
                            self._dwell_candle_count = 0

                self._dwell_decay = self._calculate_dwell_decay()

                # Fix 1: Updated conviction gating (tunable threshold)
                conv_score_raw = self._last_conviction.score if self._last_conviction else 0.0
                self._dwell_decay = self._apply_conviction_gate(self._dwell_decay, conv_score_raw)
            else:
                self._dwell_decay = 1.0
                self._conviction_gate = "disabled"

            # ── Spring score ──────────────────────────────────────────
            stoch_k = float(stoch["stoch_k"].iloc[i]) if not pd.isna(stoch["stoch_k"].iloc[i]) else np.nan
            stoch_d = float(stoch["stoch_d"].iloc[i]) if not pd.isna(stoch["stoch_d"].iloc[i]) else np.nan
            adx_cur = float(adx_series.iloc[i]) if not pd.isna(adx_series.iloc[i]) else np.nan
            adx_prev = float(adx_series.iloc[i-1]) if i > 0 and not pd.isna(adx_series.iloc[i-1]) else np.nan
            bbw_prev = float(bbw.iloc[i-1]) if i > 0 and not pd.isna(bbw.iloc[i-1]) else np.nan
            fg_value = self._get_fg_for_candle(df, i)

            self._spring_score = self._compute_spring_score(
                vol_val, vol_avg_val, stoch_k, stoch_d, fg_value,
                adx_cur, adx_prev, cur_bbw, bbw_prev, cur_bbw_med,
            )

            # ── Adaptive params with phase adjustments ────────────────
            exit_mode = self._get_exit_mode(regime)
            self._mode_candle_counts[exit_mode.name] = self._mode_candle_counts.get(exit_mode.name, 0) + 1

            tp_pct = self._adaptive_tp(regime, self._current_atr_pct)
            dev_pct = self._adaptive_deviation_v4(regime, self._current_atr_pct, tp_pct)

            if self._dd_phase == 2:
                dev_pct = min(dev_pct * 2.0, self.profile.deviation_max * 2.0)

            # Conviction
            if self.conviction_mode:
                try:
                    from ..indicators import regime_transition_signals
                    regime_trans = regime_transition_signals(df, regimes)
                    conviction = self._compute_conviction(df, i, price, regime, regime_trans)
                    tp_pct, dev_pct = self._apply_conviction_to_params(tp_pct, dev_pct, conviction)
                except (ImportError, AttributeError):
                    pass

            conv_score = self._last_conviction.score if self._last_conviction else 0.0

            # Reset spring_bypass tracking for this candle
            self._spring_bypass = False

            # ── Phase-aware trading logic ─────────────────────────────
            if self._dd_phase == 1:
                self._check_safety_order_fills_v5(low, price, ts, regime, dev_pct, tp_pct)
                self._check_exits(high, low, price, ts, regime, exit_mode)
                if not self.deals and regime not in BLOCKED_REGIMES:
                    # Fix 3: Trend direction penalty (tunable thresholds)
                    adx_for_trend = adx_cur if not np.isnan(adx_cur) else 0.0
                    sma50_for_trend = sma50_val if sma50_val is not None else price
                    if not self._should_block_deal_for_trend(price, sma50_for_trend, adx_for_trend, conv_score):
                        self._open_deal(price, ts, regime, tp_pct)
            elif self._dd_phase == 2:
                self._check_safety_order_fills_v5(low, price, ts, regime, dev_pct, tp_pct)
                self._check_exits(high, low, price, ts, regime, exit_mode)
            elif self._dd_phase == 3:
                self._check_exits(high, low, price, ts, regime, exit_mode)
                # Fix 2: Spring entries — tunable threshold + optional conviction bypass
                if (self._spring_score >= self._spring_score_threshold
                        and self.deals
                        and self._spring_entries_this_deal < SPRING_MAX_ENTRIES):
                    # If bypass enabled, skip conviction check entirely
                    # If bypass disabled, require conviction >= SPRING_MIN_CONVICTION (V6 behavior)
                    if self._spring_bypass_conviction or conv_score >= SPRING_MIN_CONVICTION:
                        self._spring_bypass = self._spring_bypass_conviction
                        size_mult = self._spring_so_size_mult(self._spring_score)
                        self._layer_sizing_mult = size_mult
                        deal = self.deals[0]
                        self._place_spring_so(deal, price, ts, regime, tp_pct, size_mult)

            # ── Equity / DD tracking ──────────────────────────────────
            equity = self._equity(price)
            self.equity_snapshots.append({
                "timestamp": ts, "equity": equity, "cash": self.cash, "price": price
            })

            deployed = sum(d.capital_deployed for d in self.deals)
            self._utilization_samples.append(
                deployed / self.initial_capital * 100 if self.initial_capital > 0 else 0
            )

            if equity > peak_equity:
                peak_equity = equity

            if not self.deals:
                self._spring_entries_this_deal = 0

            layers_filled = sum(len(d.lots) for d in self.deals)

            # Per-candle timeline (extended with spring_bypass)
            self._candle_timeline.append({
                "timestamp": ts,
                "price": round(price, 4),
                "regime": regime,
                "bbw": round(cur_bbw, 4),
                "bbw_median": round(cur_bbw_med, 4),
                "donchian_high": round(cur_donchian_high, 4),
                "donchian_low": round(cur_donchian_low, 4),
                "donchian_range_pct": round(cur_donchian_range_pct, 4),
                "in_range": cur_in_range,
                "liquidity_class": self._liquidity_class,
                "conviction_gate": self._conviction_gate,
                "dwell_count": self._dwell_candle_count,
                "dwell_decay": round(self._dwell_decay, 4),
                "effective_dev": round(dev_pct, 4),
                "conviction": round(conv_score, 1),
                "layers_filled": layers_filled,
                "dd_phase": self._dd_phase,
                "spring_score": round(self._spring_score, 1),
                "spring_entries": self._spring_entries_this_deal,
                "spring_bypass": self._spring_bypass,
                "layer_sizing_mult": round(self._layer_sizing_mult, 2),
            })

            if i % 500 == 0:
                logger.info("  [%d/%d] eq=$%.0f dd=%.1f%% phase=%d dwell=%d range=%s spring=%.0f deals=%d",
                            i, len(df), equity, dd, self._dd_phase,
                            self._dwell_candle_count, cur_in_range, self._spring_score, len(self.deals))

        # Force-close remaining
        last_price = float(df.iloc[-1]["close"])
        last_ts = str(df.iloc[-1]["timestamp"])
        for deal in list(self.deals):
            self._force_close_deal(deal, last_price, last_ts)

        result = self._compile_results(df)
        result.variant = f"v7_dwell_{self.dwell.name}"
        return result
