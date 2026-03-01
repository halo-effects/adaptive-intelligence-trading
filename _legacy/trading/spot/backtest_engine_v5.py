"""Spot DCA Backtest Engine V5 — Dwell Compression + Spring Accumulation.

Extends V4 with three-phase drawdown response replacing the hard DD halt:
  Phase 1 (DD < 15%): Normal grid, dwell compression active
  Phase 2 (DD 15-30%): Defensive grid — wider spacing, reduced sizing, no dwell
  Phase 3 (DD > 30%): Spring accumulation — targeted bottom entries on signal convergence

See: projects/ait-product/spring-accumulation-spec.md
     projects/ait-product/dwell-time-compression-spec.md
"""
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

from .backtest_engine_v4 import (
    SpotBacktestEngineV4,
    DwellProfile,
    DWELL_PROFILES,
    HARD_SNAPBACK_REGIMES,
    SOFT_SNAPBACK_REGIMES,
)
from .backtest_engine_v3 import (
    BacktestResult,
    ExitModeParams,
    BLOCKED_REGIMES,
    Lot,
)
from ..regime_detector import classify_regime_v2
from ..indicators import (
    atr as compute_atr,
    atr_pct as compute_atr_pct,
    compute_all as compute_all_indicators,
    bollinger_band_width,
    volume_sma,
)

# Patch (same as V4)
import trading.indicators as _ind
if not hasattr(_ind, 'regime_transition_signals'):
    def _regime_transition_signals_stub(df, regimes):
        return pd.DataFrame({
            "regime_stability": pd.Series(0.5, index=df.index),
            "regime_transition_pressure": pd.Series(0.0, index=df.index),
        })
    _ind.regime_transition_signals = _regime_transition_signals_stub

_original_compute_all = _ind.compute_all
def _patched_compute_all(df, include_leading=False):
    return _original_compute_all(df)
if not getattr(_ind.compute_all, '_v5_patched', False):
    _ind.compute_all = _patched_compute_all
    _ind.compute_all._v5_patched = True

logger = logging.getLogger(__name__)

# ── Phase thresholds ──────────────────────────────────────────────────────

PHASE1_DD_MAX = 15.0   # Normal grid
PHASE2_DD_MAX = 30.0   # Defensive grid
# Phase 3: DD > 30%

SPRING_THRESHOLD = 60   # Minimum spring score to trigger entry
SPRING_MAX_ENTRIES = 2  # Max spring SOs per deal
SPRING_CAPITAL_RESERVE = 0.15  # 15% of capital reserved for springs
SPRING_MIN_CONVICTION = 50.0   # Conviction gate


def _stochastic(df: pd.DataFrame, k_period: int = 14, d_period: int = 3,
                smooth_k: int = 3) -> pd.DataFrame:
    """Compute stochastic oscillator %K and %D (14,3,3)."""
    low_min = df["low"].rolling(k_period).min()
    high_max = df["high"].rolling(k_period).max()
    raw_k = 100 * (df["close"] - low_min) / (high_max - low_min).replace(0, np.nan)
    k = raw_k.rolling(smooth_k).mean()  # smoothed %K
    d = k.rolling(d_period).mean()       # %D
    return pd.DataFrame({"stoch_k": k, "stoch_d": d}, index=df.index)


class SpotBacktestEngineV5(SpotBacktestEngineV4):
    """V4 engine + three-phase drawdown response with spring accumulation."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._spring_entries_this_deal: int = 0
        self._dd_phase: int = 1
        self._spring_score: float = 0.0
        self._layer_sizing_mult: float = 1.0

    # ── Spring signal scoring ─────────────────────────────────────────

    def _compute_spring_score(
        self, volume: float, vol_avg: float,
        stoch_k: float, stoch_d: float,
        fg_value: Optional[int],
        adx_cur: float, adx_prev: float,
        bbw_cur: float, bbw_prev: float, bbw_median: float,
    ) -> float:
        score = 0.0

        # Volume climax (30 pts)
        if vol_avg > 0:
            if volume > 3 * vol_avg:
                score += 30
            elif volume > 2 * vol_avg:
                score += 20

        # Stochastic oversold (20 pts)
        if not (np.isnan(stoch_k) or np.isnan(stoch_d)):
            if stoch_k < 10 and stoch_d < 15:
                score += 20
            elif stoch_k < 20 and stoch_d < 25:
                score += 12

        # Fear & Greed (25 pts)
        if fg_value is not None:
            if fg_value <= 10:
                score += 25
            elif fg_value <= 20:
                score += 15
            elif fg_value < 30:
                score += 8

        # ADX declining from spike (15 pts)
        if not (np.isnan(adx_cur) or np.isnan(adx_prev)):
            if adx_cur < adx_prev and adx_prev > 40:
                score += 15

        # BBW contracting after expansion (15 pts)
        if not (np.isnan(bbw_cur) or np.isnan(bbw_prev) or np.isnan(bbw_median)):
            if bbw_cur < bbw_prev and bbw_prev > bbw_median * 1.5:
                score += 15

        return score

    def _spring_so_size_mult(self, score: float) -> float:
        if score >= 80:
            return 3.0
        elif score >= 70:
            return 2.5
        elif score >= 60:
            return 2.0
        return 1.0

    def _get_fg_for_candle(self, df: pd.DataFrame, i: int) -> Optional[int]:
        """Look up fear & greed value for candle's date."""
        if not self._fear_greed_history:
            return None
        candle_ts = df.iloc[i]["timestamp"]
        if isinstance(candle_ts, (int, float)):
            from datetime import datetime, timezone
            date_str = datetime.fromtimestamp(candle_ts / 1000, tz=timezone.utc).strftime("%Y-%m-%d")
        else:
            date_str = pd.to_datetime(candle_ts).strftime("%Y-%m-%d")
        return self._fear_greed_history.get(date_str)

    def _place_spring_so(self, deal, price: float, ts: str, regime: str,
                         tp_pct: float, size_mult: float):
        """Place a spring safety order with increased sizing."""
        base_cost = self._base_cost()
        so_cost = base_cost * size_mult

        # Capital reserve check: only use spring reserve
        spring_reserve = self.initial_capital * SPRING_CAPITAL_RESERVE
        available = min(so_cost, self.cash, spring_reserve)
        if available < 5.0:
            return

        fee = available * self.taker_fee
        qty = (available - fee) / price
        next_so = len(deal.lots)

        from .backtest_engine_v3 import TradeLogEntry
        lot = Lot(
            lot_id=next_so, buy_price=price, qty=qty,
            cost_usd=available, buy_fee=fee, buy_time=ts,
            tp_target=price * (1 + tp_pct / 100),
        )
        deal.lots.append(lot)
        self.cash -= available
        self._spring_entries_this_deal += 1

        self.trade_log.append(TradeLogEntry(
            timestamp=ts, action="BUY_SPRING", deal_id=deal.deal_id, lot_id=next_so,
            price=price, qty=qty, cost_usd=available, fee=fee, regime=regime,
        ))
        logger.info("  SPRING SO #%d: score=%.0f, size_mult=%.1f, cost=$%.0f @ $%.2f",
                     self._spring_entries_this_deal, self._spring_score, size_mult, available, price)

    # ── Main loop override ────────────────────────────────────────────

    def run(self, df: pd.DataFrame) -> BacktestResult:
        if len(df) < 100:
            logger.warning("Not enough data (%d rows)", len(df))
            return BacktestResult()

        # Compute indicators
        df = compute_all_indicators(df)
        regimes = classify_regime_v2(df, self.timeframe)
        atr_pct_series = compute_atr_pct(df, 14)
        atr_abs_series = compute_atr(df, 14)
        sma50 = df["close"].rolling(50).mean()

        # BBW
        bbw = df["bbw"] if "bbw" in df.columns else bollinger_band_width(df["close"], 20)
        bbw_median = bbw.rolling(100, min_periods=20).median()

        # Volume
        vol = df["volume"]
        vol_avg = volume_sma(df, 20)

        # Stochastic (14,3,3)
        stoch = _stochastic(df, 14, 3, 3)

        # ADX (already in df from compute_all)
        adx_series = df["adx_14"] if "adx_14" in df.columns else pd.Series(np.nan, index=df.index)

        logger.info("Running V5 backtest (dwell=%s): %s %s, $%.0f, profile=%s",
                     self.dwell.name, self.symbol, self.timeframe,
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
            self._trend_bullish = price >= float(sma50.iloc[i]) if not pd.isna(sma50.iloc[i]) else True

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
                self._layer_sizing_mult = 1.0  # spring entries use their own mult

            # ── Dwell-time logic (disabled in phase 2+) ───────────────
            cur_bbw = float(bbw.iloc[i]) if not pd.isna(bbw.iloc[i]) else 0.0
            cur_bbw_med = float(bbw_median.iloc[i]) if not pd.isna(bbw_median.iloc[i]) else cur_bbw

            vol_val = float(vol.iloc[i]) if not pd.isna(vol.iloc[i]) else 0.0
            vol_avg_val = float(vol_avg.iloc[i]) if not pd.isna(vol_avg.iloc[i]) and vol_avg.iloc[i] > 0 else 1.0
            vol_spike = vol_val > vol_avg_val * 2.0

            if self._dd_phase == 1:
                # Normal dwell logic from V4
                if regime in HARD_SNAPBACK_REGIMES or vol_spike:
                    self._snap_back(hard=True)
                elif regime in SOFT_SNAPBACK_REGIMES:
                    self._snap_back(hard=False)
                else:
                    if self._dwell_cooldown_remaining > 0:
                        self._dwell_cooldown_remaining -= 1
                    if self._dwell_cooldown_remaining <= 0:
                        if cur_bbw < cur_bbw_med:
                            self._dwell_candle_count += 1
                        else:
                            self._dwell_candle_count = max(0, self._dwell_candle_count - 1)
                self._dwell_decay = self._calculate_dwell_decay()
            else:
                # Phase 2/3: disable dwell compression
                self._dwell_decay = 1.0

            # ── Spring score (always compute for timeline) ────────────
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

            # Phase 2: widen spacing 2x
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

            # ── Phase-aware trading logic ─────────────────────────────
            if self._dd_phase == 1:
                # Normal: standard V3 logic (no halt override)
                self._check_safety_order_fills_v5(low, price, ts, regime, dev_pct, tp_pct)
                self._check_exits(high, low, price, ts, regime, exit_mode)
                if not self.deals and regime not in BLOCKED_REGIMES:
                    self._open_deal(price, ts, regime, tp_pct)

            elif self._dd_phase == 2:
                # Defensive: reduced sizing SOs, wider spacing (already applied above)
                self._check_safety_order_fills_v5(low, price, ts, regime, dev_pct, tp_pct)
                self._check_exits(high, low, price, ts, regime, exit_mode)
                # Don't open new deals in phase 2

            elif self._dd_phase == 3:
                # Spring accumulation: check for spring entry opportunities
                self._check_exits(high, low, price, ts, regime, exit_mode)

                # Spring entry logic
                if (self._spring_score >= SPRING_THRESHOLD
                        and self.deals
                        and self._spring_entries_this_deal < SPRING_MAX_ENTRIES
                        and conv_score >= SPRING_MIN_CONVICTION):
                    size_mult = self._spring_so_size_mult(self._spring_score)
                    self._layer_sizing_mult = size_mult
                    deal = self.deals[0]
                    self._place_spring_so(deal, price, ts, regime, tp_pct, size_mult)

            # ── Equity / DD tracking (NO hard halt) ───────────────────
            equity = self._equity(price)
            self.equity_snapshots.append({
                "timestamp": ts, "equity": equity, "cash": self.cash, "price": price
            })

            deployed = sum(d.capital_deployed for d in self.deals)
            self._utilization_samples.append(
                deployed / self.initial_capital * 100 if self.initial_capital > 0 else 0
            )

            # Update peak (may have changed after trades)
            if equity > peak_equity:
                peak_equity = equity

            # Track spring entries per deal reset
            if not self.deals:
                self._spring_entries_this_deal = 0

            # Layers filled
            layers_filled = sum(len(d.lots) for d in self.deals)

            # Per-candle timeline
            self._candle_timeline.append({
                "timestamp": ts,
                "price": round(price, 4),
                "regime": regime,
                "bbw": round(cur_bbw, 4),
                "bbw_median": round(cur_bbw_med, 4),
                "dwell_count": self._dwell_candle_count,
                "dwell_decay": round(self._dwell_decay, 4),
                "effective_dev": round(dev_pct, 4),
                "conviction": round(conv_score, 1),
                "layers_filled": layers_filled,
                "dd_phase": self._dd_phase,
                "spring_score": round(self._spring_score, 1),
                "spring_entries": self._spring_entries_this_deal,
                "layer_sizing_mult": round(self._layer_sizing_mult, 2),
            })

            if i % 500 == 0:
                logger.info("  [%d/%d] eq=$%.0f dd=%.1f%% phase=%d dwell=%d spring=%.0f deals=%d",
                            i, len(df), equity, dd, self._dd_phase,
                            self._dwell_candle_count, self._spring_score, len(self.deals))

        # Force-close remaining
        last_price = float(df.iloc[-1]["close"])
        last_ts = str(df.iloc[-1]["timestamp"])
        for deal in list(self.deals):
            self._force_close_deal(deal, last_price, last_ts)

        result = self._compile_results(df)
        result.variant = f"v5_dwell_{self.dwell.name}"
        return result

    def _check_safety_order_fills_v5(self, low: float, close: float, ts: str,
                                      regime: str, dev_pct: float, tp_pct: float):
        """Override SO fills with phase-aware sizing."""
        for deal in self.deals:
            filled_sos = len(deal.lots) - 1
            max_sos = self.profile.max_safety_orders
            if self.conviction_mode and self._last_conviction:
                max_sos = max(1, max_sos + self._last_conviction.max_so_adjustment)
            if filled_sos >= max_sos:
                continue
            if regime in BLOCKED_REGIMES:
                continue

            next_so = filled_sos + 1
            base_price = deal.lots[0].buy_price
            from .backtest_engine_v3 import BEARISH_SPACING_MULT
            spacing_mult = BEARISH_SPACING_MULT if not self._trend_bullish else 1.0
            trigger = self._so_trigger_price(base_price, next_so, dev_pct * spacing_mult)

            if low <= trigger:
                fill_price = trigger
                base_cost = self._base_cost()
                so_cost = self._so_cost(base_cost, next_so)

                # Phase 2: reduce sizing to 50%
                if self._dd_phase == 2:
                    so_cost *= 0.5

                so_cost = min(so_cost, self.cash)
                if so_cost < 5.0:
                    continue
                fee = so_cost * self.taker_fee
                qty = (so_cost - fee) / fill_price

                from .backtest_engine_v3 import TradeLogEntry
                lot = Lot(
                    lot_id=next_so, buy_price=fill_price, qty=qty,
                    cost_usd=so_cost, buy_fee=fee, buy_time=ts,
                    tp_target=fill_price * (1 + tp_pct / 100),
                )
                deal.lots.append(lot)
                self.cash -= so_cost

                self.trade_log.append(TradeLogEntry(
                    timestamp=ts, action="BUY", deal_id=deal.deal_id, lot_id=next_so,
                    price=fill_price, qty=qty, cost_usd=so_cost, fee=fee, regime=regime,
                ))
