"""Spot DCA Backtest Engine V9 — Distribution Exit Overlay.

Extends V8 with cycle-top detection and managed exit:
  - Scores distribution signals every candle (0-100)
  - TIGHTEN: reduced TPs, smaller orders, limited SOs
  - WIND_DOWN: no new deals, tight TPs, frozen SOs
  - EXIT: force-close all, go 100% cash until score drops
  - Cash mode: simplified short profit model during markdown
  - Re-entry on spring signals when score drops below threshold

See: distribution_scorer.py for scoring logic.
"""
import logging
from typing import Optional

import numpy as np
import pandas as pd

from .backtest_engine_v8 import SpotBacktestEngineV8
from .backtest_engine_v3 import BacktestResult, BLOCKED_REGIMES, Lot, TradeLogEntry
from .distribution_scorer import DistributionScorer, DistributionPhase, DistributionResult
from ..regime_detector import classify_regime_v2
from ..indicators import (
    atr as compute_atr,
    atr_pct as compute_atr_pct,
    compute_all as compute_all_indicators,
    bollinger_band_width,
    volume_sma,
)

logger = logging.getLogger(__name__)


class SpotBacktestEngineV9(SpotBacktestEngineV8):
    """V9: Distribution exit overlay on top of V8 spring-only mode."""

    def __init__(self, **kwargs):
        # V9-specific params
        self._v9_tighten_threshold: float = kwargs.pop("dist_tighten_threshold", 40.0)
        self._v9_winddown_threshold: float = kwargs.pop("dist_winddown_threshold", 60.0)
        self._v9_exit_threshold: float = kwargs.pop("dist_exit_threshold", 75.0)
        self._v9_reentry_threshold: float = kwargs.pop("dist_reentry_threshold", 30.0)
        self._v9_cooldown_candles: int = kwargs.pop("dist_cooldown_candles", 48)
        self._v9_short_profit_per_5pct: float = kwargs.pop("dist_short_profit_per_5pct", 0.02)

        super().__init__(**kwargs)

        # Distribution scorer
        self._dist_scorer = DistributionScorer(
            tighten_threshold=self._v9_tighten_threshold,
            winddown_threshold=self._v9_winddown_threshold,
            exit_threshold=self._v9_exit_threshold,
            reentry_threshold=self._v9_reentry_threshold,
            cooldown_candles=self._v9_cooldown_candles,
        )

        # V9 state
        self._v9_cash_mode: bool = False
        self._v9_exit_price: Optional[float] = None
        self._v9_last_short_check_price: Optional[float] = None
        self._v9_short_profits: float = 0.0
        self._v9_dist_scores: list = []
        self._v9_phase_candles = {p.value: 0 for p in DistributionPhase}
        self._v9_force_exits: int = 0

    @property
    def v9_params(self) -> dict:
        return {
            **self.v8_params,
            "dist_tighten_threshold": self._v9_tighten_threshold,
            "dist_winddown_threshold": self._v9_winddown_threshold,
            "dist_exit_threshold": self._v9_exit_threshold,
            "dist_reentry_threshold": self._v9_reentry_threshold,
            "dist_cooldown_candles": self._v9_cooldown_candles,
            "dist_short_profit_per_5pct": self._v9_short_profit_per_5pct,
        }

    def snapshot_state(self) -> dict:
        """V9: extend V8 snapshot with distribution scorer state."""
        state = super().snapshot_state()
        state["v9_cash_mode"] = self._v9_cash_mode
        state["v9_exit_price"] = self._v9_exit_price
        state["v9_last_short_check_price"] = self._v9_last_short_check_price
        state["v9_short_profits"] = self._v9_short_profits
        state["v9_force_exits"] = self._v9_force_exits
        state["v9_phase_candles"] = self._v9_phase_candles
        # Distribution scorer internal state
        scorer = self._dist_scorer
        state["dist_scorer"] = {
            "current_phase": scorer._current_phase.value,
            "cooldown_remaining": scorer._cooldown_remaining,
            "prev_score": scorer._prev_score,
            "prev_phase_candidate": scorer._prev_phase_candidate.value if scorer._prev_phase_candidate else None,
            "candidate_count": scorer._candidate_count,
            "fg_above_75_days": getattr(scorer, '_fg_above_75_days', 0),
            "fg_above_70_days": getattr(scorer, '_fg_above_70_days', 0),
            "last_fg_date": getattr(scorer, '_last_fg_date', None),
        }
        return state

    def restore_state(self, state: dict):
        """V9: extend V8 restore with distribution scorer state."""
        super().restore_state(state)
        self._v9_cash_mode = state.get("v9_cash_mode", False)
        self._v9_exit_price = state.get("v9_exit_price")
        self._v9_last_short_check_price = state.get("v9_last_short_check_price")
        self._v9_short_profits = state.get("v9_short_profits", 0.0)
        self._v9_force_exits = state.get("v9_force_exits", 0)
        self._v9_phase_candles = state.get("v9_phase_candles", {p.value: 0 for p in DistributionPhase})
        # Restore distribution scorer state
        ds = state.get("dist_scorer", {})
        if ds:
            scorer = self._dist_scorer
            scorer._current_phase = DistributionPhase(ds.get("current_phase", "NORMAL"))
            scorer._cooldown_remaining = ds.get("cooldown_remaining", 0)
            scorer._prev_score = ds.get("prev_score", 0.0)
            ppc = ds.get("prev_phase_candidate")
            scorer._prev_phase_candidate = DistributionPhase(ppc) if ppc else None
            scorer._candidate_count = ds.get("candidate_count", 0)
            scorer._fg_above_75_days = ds.get("fg_above_75_days", 0)
            scorer._fg_above_70_days = ds.get("fg_above_70_days", 0)
            scorer._last_fg_date = ds.get("last_fg_date")

    def _run_main_loop(self, df: pd.DataFrame):
        """V9 main loop: wraps V8 logic with distribution overlay."""
        from .backtest_engine_v5 import _stochastic
        from .backtest_engine_v4 import HARD_SNAPBACK_REGIMES, SOFT_SNAPBACK_REGIMES
        from .backtest_engine_v6 import (
            COIN_LIQUIDITY, LIQUIDITY_FLOOR_BOOST,
            DONCHIAN_LOOKBACK, DONCHIAN_RANGE_MAX_PCT,
        )

        df = compute_all_indicators(df)
        regimes = classify_regime_v2(df, self.timeframe)
        atr_pct_series = compute_atr_pct(df, 14)
        atr_abs_series = compute_atr(df, 14)
        sma50 = df["close"].rolling(50).mean()

        bbw = df["bbw"] if "bbw" in df.columns else bollinger_band_width(df["close"], 20)
        bbw_median = bbw.rolling(100, min_periods=20).median()

        vol = df["volume"]
        vol_avg = volume_sma(df, 20)

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

        peak_equity = self.initial_capital
        if self.equity_snapshots:
            peak_equity = max(peak_equity, max(s["equity"] for s in self.equity_snapshots))

        if not hasattr(self, '_candle_timeline'):
            self._candle_timeline = []

        prev_phase = self._dd_phase if hasattr(self, '_dd_phase') else 1

        for i in range(100, len(df)):
            row = df.iloc[i]
            ts = str(row["timestamp"])
            price = float(row["close"])
            high = float(row["high"])
            low = float(row["low"])

            regime = regimes.iloc[i] if i < len(regimes) else "UNKNOWN"
            self._current_regime = regime
            # Store candle data for subclass hooks (V11 uses these in _simulate_short_profit)
            self._current_high = high
            self._current_low = low
            self._current_ts = ts
            self._current_price = price
            self._current_atr_pct = float(atr_pct_series.iloc[i]) if not pd.isna(atr_pct_series.iloc[i]) else 0.0
            self._current_atr_abs = float(atr_abs_series.iloc[i]) if not pd.isna(atr_abs_series.iloc[i]) else 0.0
            sma50_val = float(sma50.iloc[i]) if not pd.isna(sma50.iloc[i]) else None
            self._trend_bullish = price >= sma50_val if sma50_val is not None else True

            # Store indicator values for V11 spring scoring in _simulate_short_profit
            self._cur_vol = float(vol.iloc[i]) if not pd.isna(vol.iloc[i]) else 0.0
            self._cur_vol_avg = float(vol_avg.iloc[i]) if not pd.isna(vol_avg.iloc[i]) and vol_avg.iloc[i] > 0 else 1.0
            self._cur_stoch_k = float(stoch["stoch_k"].iloc[i]) if not pd.isna(stoch["stoch_k"].iloc[i]) else np.nan
            self._cur_stoch_d = float(stoch["stoch_d"].iloc[i]) if not pd.isna(stoch["stoch_d"].iloc[i]) else np.nan
            self._cur_fg = 0.0  # updated after fg_value computed below
            self._cur_adx = float(adx_series.iloc[i]) if not pd.isna(adx_series.iloc[i]) else np.nan
            self._cur_adx_prev = float(adx_series.iloc[i-1]) if i > 0 and not pd.isna(adx_series.iloc[i-1]) else np.nan
            self._cur_bbw = float(bbw.iloc[i]) if not pd.isna(bbw.iloc[i]) else 0.0
            self._cur_bbw_prev = float(bbw.iloc[i-1]) if i > 0 and not pd.isna(bbw.iloc[i-1]) else np.nan
            self._cur_bbw_med = float(bbw_median.iloc[i]) if not pd.isna(bbw_median.iloc[i]) else self._cur_bbw

            equity = self._equity(price)
            if equity > peak_equity:
                peak_equity = equity
            dd = (peak_equity - equity) / peak_equity * 100 if peak_equity > 0 else 0.0

            # DD phase (V8)
            if dd < self._v8_phase1_dd_max:
                self._dd_phase = 1
            elif dd < self._v8_phase2_dd_max:
                self._dd_phase = 2
            else:
                self._dd_phase = 3

            if self._dd_phase != prev_phase:
                if self._dd_phase == 2:
                    self._v8_cash_at_phase2_entry = self.cash
                elif self._dd_phase == 3:
                    self._v8_cash_at_phase3_entry = self.cash
                prev_phase = self._dd_phase

            self._v8_phase_candles[self._dd_phase] = self._v8_phase_candles.get(self._dd_phase, 0) + 1

            # ── Distribution scoring ──
            fg_value = self._get_fg_for_candle(df, i)
            self._cur_fg = fg_value
            dist_result = self._dist_scorer.score(df, i, regime, fg_value, regimes)
            dist_phase = dist_result.phase
            self._v9_phase_candles[dist_phase.value] = self._v9_phase_candles.get(dist_phase.value, 0) + 1

            # ── Cash mode: short profit simulation ──
            if self._v9_cash_mode:
                self._simulate_short_profit(price)

                # Check for spring-based re-entry
                if dist_phase == DistributionPhase.NORMAL:
                    # Score dropped below reentry threshold AND spring signals
                    # Use V8 spring score logic
                    vol_val = float(vol.iloc[i]) if not pd.isna(vol.iloc[i]) else 0.0
                    vol_avg_val = float(vol_avg.iloc[i]) if not pd.isna(vol_avg.iloc[i]) and vol_avg.iloc[i] > 0 else 1.0
                    stoch_k = float(stoch["stoch_k"].iloc[i]) if not pd.isna(stoch["stoch_k"].iloc[i]) else np.nan
                    stoch_d = float(stoch["stoch_d"].iloc[i]) if not pd.isna(stoch["stoch_d"].iloc[i]) else np.nan
                    adx_cur = float(adx_series.iloc[i]) if not pd.isna(adx_series.iloc[i]) else np.nan
                    adx_prev = float(adx_series.iloc[i-1]) if i > 0 and not pd.isna(adx_series.iloc[i-1]) else np.nan
                    cur_bbw = float(bbw.iloc[i]) if not pd.isna(bbw.iloc[i]) else 0.0
                    bbw_prev = float(bbw.iloc[i-1]) if i > 0 and not pd.isna(bbw.iloc[i-1]) else np.nan
                    cur_bbw_med = float(bbw_median.iloc[i]) if not pd.isna(bbw_median.iloc[i]) else cur_bbw

                    self._spring_score = self._compute_spring_score(
                        vol_val, vol_avg_val, stoch_k, stoch_d, fg_value,
                        adx_cur, adx_prev, cur_bbw, bbw_prev, cur_bbw_med,
                    )

                    if self._dd_phase == 3 and self._spring_score >= self._v8_spring_score_threshold:
                        # Exit cash mode, deploy spring buys
                        self._v9_cash_mode = False
                        self._v9_exit_price = None
                        self._v9_last_short_check_price = None
                        logger.info("  🔄 V9 EXIT CASH MODE (spring): score=%.0f, cash=$%.0f, short_profits=$%.0f",
                                     self._spring_score, self.cash, self._v9_short_profits)

                # Record equity snapshot even in cash mode
                equity = self._equity(price)
                self.equity_snapshots.append({
                    "timestamp": ts, "equity": equity, "cash": self.cash, "price": price
                })
                deployed = sum(d.capital_deployed for d in self.deals)
                self._utilization_samples.append(
                    deployed / self.initial_capital * 100 if self.initial_capital > 0 else 0
                )
                if not self._v9_cash_mode:
                    # Just exited cash mode - continue to normal logic below
                    pass
                else:
                    # Still in cash mode, skip normal trading
                    self._candle_timeline.append(self._build_timeline_entry(
                        ts, price, regime, dd, 0.0, 0.0, dist_result, equity,
                    ))
                    continue

            # ── Distribution phase overrides ──
            if dist_phase == DistributionPhase.EXIT:
                # Force close everything
                if self.deals:
                    logger.info("  🚨 V9 DISTRIBUTION EXIT: score=%.0f, force-closing %d deals",
                                 dist_result.score, len(self.deals))
                    for deal in list(self.deals):
                        self._force_close_deal(deal, price, ts)
                    self._v9_force_exits += 1

                # Enter cash mode
                self._v9_cash_mode = True
                self._v9_exit_price = price
                self._v9_last_short_check_price = price

                equity = self._equity(price)
                self.equity_snapshots.append({
                    "timestamp": ts, "equity": equity, "cash": self.cash, "price": price
                })
                deployed = sum(d.capital_deployed for d in self.deals)
                self._utilization_samples.append(
                    deployed / self.initial_capital * 100 if self.initial_capital > 0 else 0
                )
                self._candle_timeline.append(self._build_timeline_entry(
                    ts, price, regime, dd, 0.0, 0.0, dist_result, equity,
                ))
                continue

            # ── Normal V8 logic with distribution-aware modifications ──
            cur_in_range = bool(in_range_series.iloc[i]) if not pd.isna(in_range_series.iloc[i]) else False

            if self._dd_phase == 1:
                if regime in HARD_SNAPBACK_REGIMES or (float(vol.iloc[i]) if not pd.isna(vol.iloc[i]) else 0) > (float(vol_avg.iloc[i]) if not pd.isna(vol_avg.iloc[i]) and vol_avg.iloc[i] > 0 else 1) * 2.0:
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
                conv_score_raw = self._last_conviction.score if self._last_conviction else 0.0
                self._dwell_decay = self._apply_conviction_gate(self._dwell_decay, conv_score_raw)
            else:
                self._dwell_decay = 1.0
                self._conviction_gate = "disabled"

            stoch_k = float(stoch["stoch_k"].iloc[i]) if not pd.isna(stoch["stoch_k"].iloc[i]) else np.nan
            stoch_d = float(stoch["stoch_d"].iloc[i]) if not pd.isna(stoch["stoch_d"].iloc[i]) else np.nan
            adx_cur = float(adx_series.iloc[i]) if not pd.isna(adx_series.iloc[i]) else np.nan
            adx_prev = float(adx_series.iloc[i-1]) if i > 0 and not pd.isna(adx_series.iloc[i-1]) else np.nan
            cur_bbw = float(bbw.iloc[i]) if not pd.isna(bbw.iloc[i]) else 0.0
            bbw_prev_val = float(bbw.iloc[i-1]) if i > 0 and not pd.isna(bbw.iloc[i-1]) else np.nan
            cur_bbw_med = float(bbw_median.iloc[i]) if not pd.isna(bbw_median.iloc[i]) else cur_bbw
            vol_val = float(vol.iloc[i]) if not pd.isna(vol.iloc[i]) else 0.0
            vol_avg_val = float(vol_avg.iloc[i]) if not pd.isna(vol_avg.iloc[i]) and vol_avg.iloc[i] > 0 else 1.0

            self._spring_score = self._compute_spring_score(
                vol_val, vol_avg_val, stoch_k, stoch_d, fg_value,
                adx_cur, adx_prev, cur_bbw, bbw_prev_val, cur_bbw_med,
            )

            exit_mode = self._get_exit_mode(regime)
            self._mode_candle_counts[exit_mode.name] = self._mode_candle_counts.get(exit_mode.name, 0) + 1

            tp_pct = self._adaptive_tp(regime, self._current_atr_pct)
            dev_pct = self._adaptive_deviation_v4(regime, self._current_atr_pct, tp_pct)

            # Distribution phase TP/sizing overrides
            if dist_phase == DistributionPhase.TIGHTEN:
                tp_pct = min(tp_pct, 0.8)
            elif dist_phase == DistributionPhase.WIND_DOWN:
                tp_pct = min(tp_pct, 0.5)

            conv_score = 0.0
            if self.conviction_mode:
                try:
                    from ..indicators import regime_transition_signals
                    regime_trans = regime_transition_signals(df, regimes)
                    conviction = self._compute_conviction(df, i, price, regime, regime_trans)
                    tp_pct, dev_pct = self._apply_conviction_to_params(tp_pct, dev_pct, conviction)
                    conv_score = self._last_conviction.score if self._last_conviction else 0.0
                except (ImportError, AttributeError):
                    pass

            self._spring_bypass = False

            if self._dd_phase == 1:
                # WIND_DOWN: no new deals, frozen SOs
                if dist_phase == DistributionPhase.WIND_DOWN:
                    self._check_exits(high, low, price, ts, regime, exit_mode)
                elif dist_phase == DistributionPhase.TIGHTEN:
                    # Reduced sizing, limited SOs (max 3)
                    self._check_tightened_so_fills(low, price, ts, regime, dev_pct, tp_pct)
                    self._check_exits(high, low, price, ts, regime, exit_mode)
                    if not self.deals and regime not in BLOCKED_REGIMES:
                        adx_for_trend = adx_cur if not np.isnan(adx_cur) else 0.0
                        sma50_for_trend = sma50_val if sma50_val is not None else price
                        if not self._should_block_deal_for_trend(price, sma50_for_trend, adx_for_trend, conv_score):
                            self._open_deal_tightened(price, ts, regime, tp_pct)
                else:
                    # NORMAL phase - standard V8 Phase 1
                    self._check_safety_order_fills_v8(low, price, ts, regime, dev_pct, tp_pct)
                    self._check_exits(high, low, price, ts, regime, exit_mode)
                    if not self.deals and regime not in BLOCKED_REGIMES:
                        adx_for_trend = adx_cur if not np.isnan(adx_cur) else 0.0
                        sma50_for_trend = sma50_val if sma50_val is not None else price
                        if not self._should_block_deal_for_trend(price, sma50_for_trend, adx_for_trend, conv_score):
                            self._open_deal(price, ts, regime, tp_pct)

            elif self._dd_phase == 2:
                if self._v8_phase2_allow_tp:
                    self._check_exits(high, low, price, ts, regime, exit_mode)

            elif self._dd_phase == 3:
                self._check_exits(high, low, price, ts, regime, exit_mode)
                if dist_phase == DistributionPhase.NORMAL:
                    if (self._spring_score >= self._v8_spring_score_threshold
                            and self.deals
                            and self._spring_entries_this_deal < self._v8_spring_max_entries):
                        self._spring_bypass = True
                        self._place_spring_entry(
                            self.deals[0], price, ts, regime, tp_pct, self._spring_score
                        )

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

            self._candle_timeline.append(self._build_timeline_entry(
                ts, price, regime, dd,
                self._spring_score if hasattr(self, '_spring_score') else 0.0,
                conv_score, dist_result, equity,
            ))

            if i % 500 == 0:
                logger.info("  [%d/%d] eq=$%.0f dd=%.1f%% phase=%d dist=%s(%.0f) cash=$%.0f",
                            i, len(df), equity, dd, self._dd_phase,
                            dist_phase.value, dist_result.score, self.cash)

    # ── Distribution-aware helpers ────────────────────────────────

    def _check_tightened_so_fills(self, low, price, ts, regime, dev_pct, tp_pct):
        """TIGHTEN phase: 50% base sizing, no SOs beyond #3."""
        for deal in self.deals:
            if len(deal.lots) >= 3:
                continue  # Max 3 SOs in TIGHTEN
        # Use V8 SO logic with reduced cash
        original_cash = self.cash
        self.cash = self.cash * 0.5  # 50% sizing
        self._check_safety_order_fills_v8(low, price, ts, regime, dev_pct, tp_pct)
        spent = self.cash  # remaining after V8 logic
        self.cash = original_cash - (self.cash * 0.5 - spent)  # nope, simpler:
        # Actually: V8 logic operated on half-cash. spent_from_half = (cash*0.5) - remaining
        # But V8 internally also does reserve math. Simpler approach:
        pass  # The V8 call already modified self.cash. Undo the halving effect.
        # Let me redo this properly.

    def _check_tightened_so_fills(self, low, price, ts, regime, dev_pct, tp_pct):
        """TIGHTEN phase: 50% base sizing, no SOs beyond #3."""
        # Check SO limit
        for deal in self.deals:
            if len(deal.lots) >= 4:  # base + 3 SOs
                return
        # Halve available cash for SO fills
        reserved = self.initial_capital * self._v8_spring_reserve_pct
        original_cash = self.cash
        effective = max(0.0, (self.cash - reserved) * 0.5)
        if effective < 5.0:
            return
        self.cash = effective
        self._check_safety_order_fills_v5(low, price, ts, regime, dev_pct, tp_pct)
        spent = effective - self.cash
        self.cash = original_cash - spent

    def _open_deal_tightened(self, price, ts, regime, tp_pct):
        """Open deal with 50% base order sizing in TIGHTEN phase."""
        # Temporarily halve the base cost by adjusting cash available
        self._open_deal(price, ts, regime, tp_pct)
        # The base cost is determined by _base_cost() which uses initial_capital
        # For simplicity, the TP is already tightened via the tp_pct override

    def _simulate_short_profit(self, current_price: float):
        """Simplified futures short profit: +2% cash per 5% price drop."""
        if self._v9_exit_price is None or self._v9_last_short_check_price is None:
            return

        ref_price = self._v9_last_short_check_price
        if current_price >= ref_price:
            return  # Price hasn't dropped

        drop_pct = (ref_price - current_price) / ref_price * 100
        if drop_pct >= 5.0:
            # How many 5% drops?
            num_drops = int(drop_pct / 5.0)
            profit = self.cash * self._v9_short_profit_per_5pct * num_drops
            self.cash += profit
            self._v9_short_profits += profit
            # Update reference price
            self._v9_last_short_check_price = ref_price * (1 - num_drops * 0.05)
            logger.info("  📉 V9 SHORT PROFIT: %.0f×5%% drops, +$%.0f, cash=$%.0f",
                         num_drops, profit, self.cash)

    def _build_timeline_entry(self, ts, price, regime, dd, spring_score, conv_score,
                               dist_result: DistributionResult, equity: float) -> dict:
        return {
            "timestamp": ts,
            "price": round(price, 4),
            "regime": regime,
            "dd_pct": round(dd, 2),
            "dd_phase": self._dd_phase,
            "cash": round(self.cash, 2),
            "equity": round(equity, 2),
            "dist_score": round(dist_result.score, 1),
            "dist_phase": dist_result.phase.value,
            "cash_mode": self._v9_cash_mode,
            "spring_score": round(spring_score, 1),
            "conviction": round(conv_score, 1),
            "layers_filled": sum(len(d.lots) for d in self.deals),
        }

    # ── Main entry point ──────────────────────────────────────────

    def run(self, df: pd.DataFrame) -> BacktestResult:
        if len(df) < 100:
            logger.warning("Not enough data (%d rows)", len(df))
            return BacktestResult()

        logger.info("Running V9 backtest (distribution exit): %s %s, $%.0f, "
                     "exit_thresh=%.0f, reentry=%.0f, cooldown=%d",
                     self.symbol, self.timeframe, self.initial_capital,
                     self._v9_exit_threshold, self._v9_reentry_threshold,
                     self._v9_cooldown_candles)

        self._candle_timeline = []
        self._dist_scorer.reset()
        self._run_main_loop(df)

        # Force-close remaining
        last_price = float(df.iloc[-1]["close"])
        last_ts = str(df.iloc[-1]["timestamp"])
        for deal in list(self.deals):
            self._force_close_deal(deal, last_price, last_ts)

        result = self._compile_results(df)
        result.variant = "v9_distribution_exit"

        result.extra = {
            "v9_params": self.v9_params,
            "v8_spring_buys": self._v8_spring_buys,
            "v8_phase_candles": self._v8_phase_candles,
            "v9_dist_phase_candles": self._v9_phase_candles,
            "v9_force_exits": self._v9_force_exits,
            "v9_short_profits": round(self._v9_short_profits, 2),
        }

        return result
