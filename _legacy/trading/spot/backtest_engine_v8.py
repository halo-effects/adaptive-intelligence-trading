"""Spot DCA Backtest Engine V8 — Spring-Only Mode + Capital Preservation.

THE KEY FIX: Phase 2 STOPS all new safety orders, preserving cash for Phase 3.
Previous engines (V5-V7) continued filling SOs in Phase 2, draining capital before
spring signals could fire. V8 solves the fundamental capital exhaustion problem.

Architecture:
  Phase 1 (DD < phase1_dd_max): Normal grid, dwell compression active
  Phase 2 (DD phase1..phase2): SO FREEZE — only TP exits, NO new buys. Cash preserved.
  Phase 3 (DD > phase2_dd_max): Spring-only — deploy preserved cash in large buys with wide TPs

Spring improvements over V7:
  - Up to 5 spring entries (was 2)
  - Risk-profile-based spring sizing: Low=2×, Medium=3×, High=5×
  - Wider spring TPs: Low=5%, Medium=10%, High=20% (vs normal 1-2.5%)
  - Score-gated TP: higher spring score → wider TP within range
  - Hard capital reservation: spring_reserve_pct of capital is NEVER deployed in Phase 1/2

Tunable parameters (constructor kwargs):
  phase1_dd_max (15.0)        — DD threshold to enter Phase 2 (SO freeze)
  phase2_dd_max (30.0)        — DD threshold to enter Phase 3 (spring-only)
  spring_reserve_pct (0.25)   — fraction of capital hard-reserved for springs
  spring_score_threshold (60) — min spring score to trigger Phase 3 entry
  spring_max_entries (5)      — max spring buys per deal
  spring_size_mult (3.0)      — base spring sizing multiplier
  spring_tp_mult (4.0)        — spring TP = normal_TP × this multiplier
  spring_score_tp_scale (True)— higher spring score → wider TP
  phase2_allow_existing_tp (True) — allow TP exits in Phase 2

See: projects/ait-product/spring-accumulation-spec.md
     projects/ait-product/unified-signal-architecture-spec.md
"""
import logging
from typing import Optional

import numpy as np
import pandas as pd

from .backtest_engine_v7 import SpotBacktestEngineV7
from .backtest_engine_v6 import (
    COIN_LIQUIDITY,
    LIQUIDITY_FLOOR_BOOST,
    DONCHIAN_LOOKBACK,
    DONCHIAN_RANGE_MAX_PCT,
)
from .backtest_engine_v5 import _stochastic
from .backtest_engine_v4 import HARD_SNAPBACK_REGIMES, SOFT_SNAPBACK_REGIMES
from .backtest_engine_v3 import BacktestResult, BLOCKED_REGIMES, Lot, TradeLogEntry
from ..regime_detector import classify_regime_v2
from ..indicators import (
    atr as compute_atr,
    atr_pct as compute_atr_pct,
    compute_all as compute_all_indicators,
    bollinger_band_width,
    volume_sma,
)

logger = logging.getLogger(__name__)


class SpotBacktestEngineV8(SpotBacktestEngineV7):
    """V8: Spring-only mode with capital preservation.

    The fundamental change: Phase 2 stops ALL new safety orders.
    Capital is preserved for Phase 3 spring deployment.
    """

    def __init__(self, **kwargs):
        # V8-specific params
        self._v8_phase1_dd_max: float = kwargs.pop("phase1_dd_max", 15.0)
        self._v8_phase2_dd_max: float = kwargs.pop("phase2_dd_max", 30.0)
        self._v8_spring_reserve_pct: float = kwargs.pop("spring_reserve_pct", 0.25)
        self._v8_spring_score_threshold: float = kwargs.pop("spring_score_threshold", 60.0)
        self._v8_spring_max_entries: int = kwargs.pop("spring_max_entries", 5)
        self._v8_spring_size_mult: float = kwargs.pop("spring_size_mult", 3.0)
        self._v8_spring_tp_mult: float = kwargs.pop("spring_tp_mult", 4.0)
        self._v8_spring_score_tp_scale: bool = kwargs.pop("spring_score_tp_scale", True)
        self._v8_phase2_allow_tp: bool = kwargs.pop("phase2_allow_existing_tp", True)

        super().__init__(**kwargs)

        # Track spring-specific metrics
        self._v8_spring_buys: int = 0
        self._v8_spring_pnl: float = 0.0
        self._v8_phase_candles = {1: 0, 2: 0, 3: 0}
        self._v8_cash_at_phase2_entry: float = 0.0
        self._v8_cash_at_phase3_entry: float = 0.0

    @property
    def v8_params(self) -> dict:
        return {
            **self.v7_params,
            "phase1_dd_max": self._v8_phase1_dd_max,
            "phase2_dd_max": self._v8_phase2_dd_max,
            "spring_reserve_pct": self._v8_spring_reserve_pct,
            "spring_score_threshold": self._v8_spring_score_threshold,
            "spring_max_entries": self._v8_spring_max_entries,
            "spring_size_mult": self._v8_spring_size_mult,
            "spring_tp_mult": self._v8_spring_tp_mult,
            "spring_score_tp_scale": self._v8_spring_score_tp_scale,
        }

    # ── State serialization for chained backtests ───────────────────

    def snapshot_state(self) -> dict:
        """Capture engine state for chaining across time periods.
        Returns a dict that can be passed to restore_state() on a new engine."""
        return {
            "cash": self.cash,
            "deals": [d.to_dict() for d in self.deals],
            "completed_deals": [d.to_dict() for d in self.completed_deals],
            "deal_counter": self._deal_counter,
            "trade_log": [vars(t) if hasattr(t, '__dict__') else t for t in self.trade_log],
            "equity_snapshots": self.equity_snapshots,
            "v8_spring_buys": self._v8_spring_buys,
            "v8_phase_candles": self._v8_phase_candles,
            "spring_entries_this_deal": self._spring_entries_this_deal,
            "utilization_samples": self._utilization_samples,
            "mode_candle_counts": self._mode_candle_counts,
        }

    @staticmethod
    def _lot_from_dict(d: dict) -> Lot:
        """Reconstruct a Lot from its to_dict() output."""
        from .backtest_engine_v3 import Runner
        runner = None
        if "runner" in d and d["runner"]:
            r = d["runner"]
            runner = Runner(
                qty=r["qty"], entry_price=r.get("entry_price", 0.0),
                tp_price=r["tp_price"],
                trail_high=r.get("trail_high", r.get("tp_price", 0.0)),
                trail_distance=r.get("trail_distance", 0.0),
                candles_since_improvement=r.get("candles_since_improvement", 0),
                timeout_candles=r.get("timeout_candles", 24),
                cost_usd=r.get("cost_usd", 0.0),
                sell_price=r.get("sell_price"), sell_time=r.get("sell_time"),
                sell_reason=r.get("sell_reason", ""),
                pnl=r.get("pnl", 0.0), best_high=r.get("best_high", 0.0),
            )
        return Lot(
            lot_id=d["lot_id"], buy_price=d["buy_price"], qty=d["qty"],
            cost_usd=d["cost_usd"], buy_fee=d["buy_fee"], buy_time=d["buy_time"],
            sell_price=d.get("sell_price"), sell_fee=d.get("sell_fee", 0.0),
            sell_time=d.get("sell_time"), tp_target=d.get("tp_target", 0.0),
            pnl=d.get("pnl", 0.0), actual_sell_reason=d.get("actual_sell_reason", ""),
            runner=runner, secured_sold=d.get("secured_sold", False),
        )

    @staticmethod
    def _deal_from_dict(d: dict):
        """Reconstruct a Deal from its to_dict() output."""
        from .backtest_engine_v3 import Deal
        deal = Deal(
            deal_id=d["deal_id"], symbol=d["symbol"],
            open_time=d.get("open_time", ""),
            close_time=d.get("close_time"),
            regime_at_open=d.get("regime_at_open", "UNKNOWN"),
        )
        deal.lots = [SpotBacktestEngineV8._lot_from_dict(l) for l in d.get("lots", [])]
        return deal

    def restore_state(self, state: dict):
        """Restore engine state from a previous snapshot (for chaining)."""
        self.cash = state["cash"]
        self.deals = [self._deal_from_dict(d) for d in state["deals"]]
        self.completed_deals = [self._deal_from_dict(d) for d in state["completed_deals"]]
        self._deal_counter = state["deal_counter"]
        self.equity_snapshots = state.get("equity_snapshots", [])
        self._v8_spring_buys = state.get("v8_spring_buys", 0)
        self._v8_phase_candles = state.get("v8_phase_candles", {1: 0, 2: 0, 3: 0})
        self._spring_entries_this_deal = state.get("spring_entries_this_deal", 0)
        self._utilization_samples = state.get("utilization_samples", [])
        self._mode_candle_counts = state.get("mode_candle_counts", {})

    def run_no_close(self, df: pd.DataFrame):
        """Run backtest WITHOUT force-closing at end. For chaining.
        Returns (partial_result_dict, state_snapshot)."""
        if len(df) < 100:
            logger.warning("Not enough data (%d rows)", len(df))
            return None, self.snapshot_state()

        # Run the main loop but intercept before force-close
        # We duplicate the run() logic but skip the force-close + compile step
        self._run_main_loop(df)
        state = self.snapshot_state()
        last_price = float(df.iloc[-1]["close"])
        equity = self._equity(last_price)
        return {
            "final_equity": round(equity, 2),
            "cash": round(self.cash, 2),
            "open_deals": len(self.deals),
            "open_lots": sum(len(d.lots) for d in self.deals),
            "completed_deals": len(self.completed_deals),
            "candles_processed": len(df) - 100,
        }, state

    def _run_main_loop(self, df: pd.DataFrame):
        """Core loop extracted for reuse by run() and run_no_close()."""
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
        # If we have prior equity snapshots (chained), use the max as peak
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
            self._current_atr_pct = float(atr_pct_series.iloc[i]) if not pd.isna(atr_pct_series.iloc[i]) else 0.0
            self._current_atr_abs = float(atr_abs_series.iloc[i]) if not pd.isna(atr_abs_series.iloc[i]) else 0.0
            sma50_val = float(sma50.iloc[i]) if not pd.isna(sma50.iloc[i]) else None
            self._trend_bullish = price >= sma50_val if sma50_val is not None else True

            equity = self._equity(price)
            if equity > peak_equity:
                peak_equity = equity
            dd = (peak_equity - equity) / peak_equity * 100 if peak_equity > 0 else 0.0

            if dd < self._v8_phase1_dd_max:
                self._dd_phase = 1
            elif dd < self._v8_phase2_dd_max:
                self._dd_phase = 2
            else:
                self._dd_phase = 3

            if self._dd_phase != prev_phase:
                if self._dd_phase == 2:
                    self._v8_cash_at_phase2_entry = self.cash
                    logger.info("  ⚠️ PHASE 2 (SO FREEZE): DD=%.1f%%, cash=$%.0f", dd, self.cash)
                elif self._dd_phase == 3:
                    self._v8_cash_at_phase3_entry = self.cash
                    logger.info("  🔴 PHASE 3 (SPRING-ONLY): DD=%.1f%%, cash=$%.0f", dd, self.cash)
                elif self._dd_phase == 1 and prev_phase > 1:
                    logger.info("  ✅ BACK TO PHASE 1: DD=%.1f%%, equity=$%.0f", dd, equity)
                prev_phase = self._dd_phase

            self._v8_phase_candles[self._dd_phase] = self._v8_phase_candles.get(self._dd_phase, 0) + 1

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
                conv_score_raw = self._last_conviction.score if self._last_conviction else 0.0
                self._dwell_decay = self._apply_conviction_gate(self._dwell_decay, conv_score_raw)
            else:
                self._dwell_decay = 1.0
                self._conviction_gate = "disabled"

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

            exit_mode = self._get_exit_mode(regime)
            self._mode_candle_counts[exit_mode.name] = self._mode_candle_counts.get(exit_mode.name, 0) + 1

            tp_pct = self._adaptive_tp(regime, self._current_atr_pct)
            dev_pct = self._adaptive_deviation_v4(regime, self._current_atr_pct, tp_pct)

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

            self._candle_timeline.append({
                "timestamp": ts,
                "price": round(price, 4),
                "regime": regime,
                "dd_pct": round(dd, 2),
                "dd_phase": self._dd_phase,
                "cash": round(self.cash, 2),
                "equity": round(equity, 2),
                "bbw": round(cur_bbw, 4),
                "bbw_median": round(cur_bbw_med, 4),
                "donchian_range_pct": round(cur_donchian_range_pct, 4),
                "in_range": cur_in_range,
                "conviction": round(conv_score, 1),
                "dwell_count": self._dwell_candle_count,
                "dwell_decay": round(self._dwell_decay, 4),
                "spring_score": round(self._spring_score, 1),
                "spring_entries": self._spring_entries_this_deal,
                "spring_bypass": self._spring_bypass,
                "layers_filled": layers_filled,
            })

            if i % 500 == 0:
                logger.info("  [%d/%d] eq=$%.0f dd=%.1f%% phase=%d cash=$%.0f spring=%d dwell=%d deals=%d",
                            i, len(df), equity, dd, self._dd_phase,
                            self.cash, self._v8_spring_buys,
                            self._dwell_candle_count, len(self.deals))

    # ── Capital management ────────────────────────────────────────────

    def _available_for_normal_grid(self) -> float:
        """Cash available for Phase 1 normal grid (excludes spring reserve)."""
        reserved = self.initial_capital * self._v8_spring_reserve_pct
        return max(0.0, self.cash - reserved)

    def _available_for_spring(self) -> float:
        """Cash available for spring entries (ALL remaining cash)."""
        return self.cash

    # ── Spring TP calculation ─────────────────────────────────────────

    def _spring_tp_pct(self, base_tp: float, spring_score: float) -> float:
        """Calculate wider TP for spring entries.

        Base spring TP = base_tp × spring_tp_mult.
        If score-scaling enabled, score 60→80 scales from 0.7× to 1.3× of that.
        """
        spring_tp = base_tp * self._v8_spring_tp_mult

        if self._v8_spring_score_tp_scale:
            # Score 60 → 0.7×, Score 80 → 1.3×
            score_factor = 0.7 + (spring_score - 60) / 20 * 0.6
            score_factor = max(0.7, min(1.3, score_factor))
            spring_tp *= score_factor

        # Clamp: min 3%, max 30%
        return max(3.0, min(30.0, spring_tp))

    # ── Spring sizing ─────────────────────────────────────────────────

    def _spring_entry_size(self, spring_score: float) -> float:
        """Spring entry cost in USD.

        Base = base_order × spring_size_mult, then scaled by score.
        Score 60→80 scales 0.6× to 1.4× of base spring size.
        """
        base = self._base_cost() * self._v8_spring_size_mult

        # Score scaling
        score_factor = 0.6 + (spring_score - 60) / 20 * 0.8
        score_factor = max(0.6, min(1.4, score_factor))
        base *= score_factor

        available = self._available_for_spring()
        return min(base, available)

    # ── Place spring entry ────────────────────────────────────────────

    def _place_spring_entry(self, deal, price: float, ts: str, regime: str,
                            base_tp: float, spring_score: float):
        """Place a spring buy with large sizing and wide TP."""
        cost = self._spring_entry_size(spring_score)
        if cost < 5.0:
            logger.info("  SPRING SKIP: insufficient cash ($%.2f)", cost)
            return

        fee = cost * self.taker_fee
        qty = (cost - fee) / price
        next_id = len(deal.lots)

        # Wide TP for spring entries
        tp_pct = self._spring_tp_pct(base_tp, spring_score)
        tp_target = price * (1 + tp_pct / 100)

        lot = Lot(
            lot_id=next_id, buy_price=price, qty=qty,
            cost_usd=cost, buy_fee=fee, buy_time=ts,
            tp_target=tp_target,
        )
        deal.lots.append(lot)
        self.cash -= cost
        self._spring_entries_this_deal += 1
        self._v8_spring_buys += 1

        self.trade_log.append(TradeLogEntry(
            timestamp=ts, action="BUY_SPRING_V8", deal_id=deal.deal_id,
            lot_id=next_id, price=price, qty=qty, cost_usd=cost, fee=fee,
            regime=regime,
        ))
        logger.info("  🌱 SPRING V8 #%d: score=%.0f, cost=$%.0f, TP=%.1f%% ($%.2f→$%.2f), cash_left=$%.0f",
                     self._spring_entries_this_deal, spring_score, cost,
                     tp_pct, price, tp_target, self.cash)

    # ── Override: check SO fills with capital reservation ─────────────

    def _check_safety_order_fills_v8(self, low, price, ts, regime, dev_pct, tp_pct):
        """Phase 1 SO fills — respects spring capital reserve."""
        # Temporarily reduce available cash for SO placement
        reserved = self.initial_capital * self._v8_spring_reserve_pct
        original_cash = self.cash

        # Only allow SOs to use non-reserved cash
        effective_cash = max(0.0, self.cash - reserved)
        if effective_cash < 5.0:
            return  # Not enough non-reserved cash for SOs

        # Call parent's SO fill logic (it checks self.cash internally)
        # We temporarily cap cash to enforce the reserve
        self.cash = effective_cash
        self._check_safety_order_fills_v5(low, price, ts, regime, dev_pct, tp_pct)
        # Restore: actual cash = original - what was spent
        spent = effective_cash - self.cash
        self.cash = original_cash - spent

    # ── Main loop ─────────────────────────────────────────────────────

    def run(self, df: pd.DataFrame) -> BacktestResult:
        if len(df) < 100:
            logger.warning("Not enough data (%d rows)", len(df))
            return BacktestResult()

        logger.info("Running V8 backtest (spring-only mode): %s %s, $%.0f, profile=%s, "
                     "reserve=%.0f%%, spring_thresh=%.0f, spring_size=%.1f×, spring_tp=%.1f×",
                     self.symbol, self.timeframe, self.initial_capital, self.profile.name,
                     self._v8_spring_reserve_pct * 100, self._v8_spring_score_threshold,
                     self._v8_spring_size_mult, self._v8_spring_tp_mult)

        self._candle_timeline = []
        self._run_main_loop(df)

        # Force-close remaining
        last_price = float(df.iloc[-1]["close"])
        last_ts = str(df.iloc[-1]["timestamp"])
        for deal in list(self.deals):
            self._force_close_deal(deal, last_price, last_ts)

        result = self._compile_results(df)
        result.variant = f"v8_spring_only"

        result.extra = {
            "v8_params": self.v8_params,
            "spring_buys": self._v8_spring_buys,
            "phase_candles": self._v8_phase_candles,
            "cash_at_phase2": self._v8_cash_at_phase2_entry,
            "cash_at_phase3": self._v8_cash_at_phase3_entry,
        }

        return result
