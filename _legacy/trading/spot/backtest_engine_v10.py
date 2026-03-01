"""Spot DCA Backtest Engine V10 — Conviction-Weighted Wyckoff Engine.

Extends V8 with:
  - Wyckoff Phase Engine (ACCUMULATION/MARKUP/DISTRIBUTION/MARKDOWN)
  - Conviction-weighted position sizing
  - Short DCA engine (virtual positions during MARKDOWN)
  - Capital rotation (SPOT → CASH → SHORT → SPRING → SPOT)
  - Compounding (realized PnL increases effective capital)
  - Interim swing detection within MARKUP

See: projects/ait-product/v10-conviction-weighted-wyckoff-spec.md
"""
import logging
from dataclasses import dataclass, field
from typing import Optional, List

import numpy as np
import pandas as pd

from .backtest_engine_v8 import SpotBacktestEngineV8
from .backtest_engine_v3 import BacktestResult, BLOCKED_REGIMES, Lot, TradeLogEntry
from .distribution_scorer import DistributionScorer, DistributionPhase
from .wyckoff_phase_engine import WyckoffPhaseEngine, WyckoffPhase, CapitalMode
from ..regime_detector import classify_regime_v2
from ..indicators import (
    atr as compute_atr,
    atr_pct as compute_atr_pct,
    compute_all as compute_all_indicators,
    bollinger_band_width,
    volume_sma,
)

logger = logging.getLogger(__name__)


# ── Short position tracking ──────────────────────────────────────────

@dataclass
class ShortLot:
    lot_id: int
    entry_price: float
    qty: float  # in base currency units (e.g. ETH)
    cost_usd: float  # margin allocated
    entry_time: str
    tp_target: float = 0.0  # price below which we TP
    sl_target: float = 0.0  # stop-loss price above entry
    sell_price: Optional[float] = None
    sell_time: Optional[str] = None
    pnl: float = 0.0
    sell_reason: str = ""

    @property
    def is_closed(self) -> bool:
        return self.sell_price is not None

    def to_dict(self) -> dict:
        return {
            "lot_id": self.lot_id, "entry_price": self.entry_price,
            "qty": self.qty, "cost_usd": self.cost_usd,
            "entry_time": self.entry_time, "tp_target": self.tp_target,
            "sl_target": self.sl_target, "sell_price": self.sell_price,
            "sell_time": self.sell_time, "pnl": self.pnl,
            "sell_reason": self.sell_reason,
        }


@dataclass
class ShortDeal:
    deal_id: int
    symbol: str
    lots: List[ShortLot] = field(default_factory=list)
    open_time: str = ""
    close_time: Optional[str] = None
    funding_cost: float = 0.0

    @property
    def is_complete(self) -> bool:
        return len(self.lots) > 0 and all(l.is_closed for l in self.lots)

    @property
    def open_lots(self) -> List[ShortLot]:
        return [l for l in self.lots if not l.is_closed]

    @property
    def total_margin(self) -> float:
        return sum(l.cost_usd for l in self.lots if not l.is_closed)

    @property
    def avg_entry(self) -> float:
        open_l = self.open_lots
        if not open_l:
            return 0.0
        total_qty = sum(l.qty for l in open_l)
        if total_qty == 0:
            return 0.0
        return sum(l.entry_price * l.qty for l in open_l) / total_qty

    @property
    def total_qty(self) -> float:
        return sum(l.qty for l in self.open_lots)

    @property
    def total_pnl(self) -> float:
        return sum(l.pnl for l in self.lots if l.is_closed) - self.funding_cost

    def to_dict(self) -> dict:
        return {
            "deal_id": self.deal_id, "symbol": self.symbol,
            "lots": [l.to_dict() for l in self.lots],
            "open_time": self.open_time, "close_time": self.close_time,
            "funding_cost": self.funding_cost,
            "total_pnl": self.total_pnl,
        }


class SpotBacktestEngineV10(SpotBacktestEngineV8):
    """V10: Conviction-Weighted Wyckoff Engine with short DCA and capital rotation."""

    def __init__(self, **kwargs):
        # V10-specific params
        self._v10_dist_threshold: float = kwargs.pop("v10_dist_threshold", 40.0)
        self._v10_markdown_dist_threshold: float = kwargs.pop("v10_markdown_dist_threshold", 60.0)
        self._v10_accum_spring_threshold: float = kwargs.pop("v10_accum_spring_threshold", 50.0)
        self._v10_short_tp_pct: float = kwargs.pop("v10_short_tp_pct", 2.5)
        self._v10_short_sl_pct: float = kwargs.pop("v10_short_sl_pct", 15.0)
        self._v10_short_max_entries: int = kwargs.pop("v10_short_max_entries", 8)
        self._v10_short_deviation_pct: float = kwargs.pop("v10_short_deviation_pct", 2.5)
        self._v10_funding_rate_daily: float = kwargs.pop("v10_funding_rate_daily", 0.0003)
        self._v10_cash_timeout_candles: int = kwargs.pop("v10_cash_timeout_candles", 48)
        self._v10_interim_pause_candles: int = kwargs.pop("v10_interim_pause_candles", 48)
        self._v10_compounding: bool = kwargs.pop("v10_compounding", True)
        self._v10_wyckoff_confirmation: int = kwargs.pop("v10_wyckoff_confirmation", 24)

        super().__init__(**kwargs)

        # Wyckoff Phase Engine
        self._wyckoff = WyckoffPhaseEngine(
            confirmation_candles=self._v10_wyckoff_confirmation,
            dist_threshold=self._v10_dist_threshold,
            markdown_dist_threshold=self._v10_markdown_dist_threshold,
            accumulation_spring_threshold=self._v10_accum_spring_threshold,
        )

        # Distribution scorer (reused from V9)
        self._dist_scorer = DistributionScorer(
            tighten_threshold=self._v10_dist_threshold,
            winddown_threshold=self._v10_markdown_dist_threshold,
            exit_threshold=75.0,
            reentry_threshold=30.0,
        )

        # Capital rotation state
        self._capital_mode = CapitalMode.SPOT
        self._cash_mode_candles: int = 0
        self._interim_pause_remaining: int = 0

        # Short engine state
        self._short_deals: List[ShortDeal] = []
        self._completed_short_deals: List[ShortDeal] = []
        self._short_deal_counter: int = 0
        self._short_allocated: float = 0.0

        # Compounding
        self._realized_pnl: float = 0.0
        self._effective_capital: float = self.initial_capital

        # V10 metrics
        self._v10_phase_transitions: list = []
        self._v10_short_pnl: float = 0.0
        self._v10_short_funding: float = 0.0
        self._v10_interim_sells: int = 0
        self._v10_interim_buys: int = 0
        self._total_candles_processed: int = 0

    @property
    def v10_params(self) -> dict:
        return {
            **self.v8_params,
            "v10_dist_threshold": self._v10_dist_threshold,
            "v10_markdown_dist_threshold": self._v10_markdown_dist_threshold,
            "v10_short_tp_pct": self._v10_short_tp_pct,
            "v10_short_sl_pct": self._v10_short_sl_pct,
            "v10_short_max_entries": self._v10_short_max_entries,
            "v10_funding_rate_daily": self._v10_funding_rate_daily,
            "v10_compounding": self._v10_compounding,
        }

    # ── Effective capital (compounding) ────────────────────────────

    def _effective_cap(self) -> float:
        if self._v10_compounding:
            return self.initial_capital + self._realized_pnl
        return self.initial_capital

    def _base_cost(self) -> float:
        """Override: use effective capital for compounding."""
        base_pct = self.profile.base_order_pct
        if self.conviction_mode and self._last_conviction:
            base_pct = base_pct * self._last_conviction.base_order_multiplier
        if self._v10_compounding or self.compounding:
            return self._sizing_equity() * base_pct
        return self._effective_cap() * base_pct

    # ── Conviction-weighted sizing ─────────────────────────────────

    def _wyckoff_size_mult(self, phase: WyckoffPhase, conviction: float) -> float:
        """Returns base order multiplier based on Wyckoff phase + conviction."""
        if phase == WyckoffPhase.ACCUMULATION:
            return 1.0 + (conviction / 100.0) * 2.0  # 1× to 3×
        elif phase == WyckoffPhase.MARKUP:
            return 0.5 + (conviction / 100.0) * 0.75  # 0.5× to 1.25×
        elif phase == WyckoffPhase.DISTRIBUTION:
            return 0.0  # no new buys
        elif phase == WyckoffPhase.MARKDOWN:
            return 0.0  # no new longs
        return 1.0

    # ── Short engine ───────────────────────────────────────────────

    def _open_short(self, price: float, ts: str, conviction: float):
        """Open a new short deal."""
        # Allocate conviction * 70% of available cash
        alloc = self.cash * (conviction / 100.0) * 0.70
        alloc = min(alloc, self.cash * 0.8)  # never more than 80%
        if alloc < 10.0:
            return

        self._short_deal_counter += 1
        base_cost = min(alloc * 0.3, self.cash)  # First entry = 30% of allocation
        if base_cost < 5.0:
            return

        qty = base_cost / price
        tp_target = price * (1 - self._v10_short_tp_pct / 100)
        sl_target = price * (1 + self._v10_short_sl_pct / 100)

        lot = ShortLot(
            lot_id=0, entry_price=price, qty=qty, cost_usd=base_cost,
            entry_time=ts, tp_target=tp_target, sl_target=sl_target,
        )
        deal = ShortDeal(
            deal_id=self._short_deal_counter, symbol=self.symbol,
            lots=[lot], open_time=ts,
        )
        self._short_deals.append(deal)
        self.cash -= base_cost
        self._short_allocated += base_cost

        self.trade_log.append(TradeLogEntry(
            timestamp=ts, action="SHORT_OPEN", deal_id=deal.deal_id,
            lot_id=0, price=price, qty=qty, cost_usd=base_cost,
            fee=0.0, regime=self._current_regime,
        ))
        logger.info("  📉 SHORT OPEN: $%.0f at $%.2f, TP=$%.2f, SL=$%.2f",
                     base_cost, price, tp_target, sl_target)

    def _check_short_safety_orders(self, high: float, price: float, ts: str):
        """Add to short position on bounces UP (inverted SO logic)."""
        for deal in self._short_deals:
            if deal.is_complete:
                continue
            open_lots = deal.open_lots
            if len(deal.lots) >= self._v10_short_max_entries:
                continue

            avg = deal.avg_entry
            if avg <= 0:
                continue

            next_so = len(deal.lots)
            # Trigger on bounce UP above avg entry + deviation
            trigger = avg * (1 + self._v10_short_deviation_pct * next_so / 100)

            if high >= trigger:
                so_cost = min(self.cash * 0.2, self.cash)
                if so_cost < 5.0:
                    continue

                qty = so_cost / trigger
                tp_target = trigger * (1 - self._v10_short_tp_pct / 100)
                sl_target = trigger * (1 + self._v10_short_sl_pct / 100)

                lot = ShortLot(
                    lot_id=next_so, entry_price=trigger, qty=qty, cost_usd=so_cost,
                    entry_time=ts, tp_target=tp_target, sl_target=sl_target,
                )
                deal.lots.append(lot)
                self.cash -= so_cost
                self._short_allocated += so_cost

                self.trade_log.append(TradeLogEntry(
                    timestamp=ts, action="SHORT_SO", deal_id=deal.deal_id,
                    lot_id=next_so, price=trigger, qty=qty, cost_usd=so_cost,
                    fee=0.0, regime=self._current_regime,
                ))

    def _check_short_exits(self, low: float, high: float, price: float, ts: str):
        """Check short TP (price drops) and SL (price rises)."""
        for deal in list(self._short_deals):
            if deal.is_complete:
                continue

            avg = deal.avg_entry
            total_qty = deal.total_qty

            # Take profit: price dropped below avg - TP%
            tp_price = avg * (1 - self._v10_short_tp_pct / 100)
            if low <= tp_price and total_qty > 0:
                self._close_short_deal(deal, tp_price, ts, "short_tp")
                continue

            # Stop loss: price above avg + SL%
            sl_price = avg * (1 + self._v10_short_sl_pct / 100)
            if high >= sl_price and total_qty > 0:
                self._close_short_deal(deal, sl_price, ts, "short_sl")
                continue

    def _close_short_deal(self, deal: ShortDeal, close_price: float, ts: str, reason: str):
        """Close all lots in a short deal."""
        for lot in deal.open_lots:
            # Short PnL: (entry - close) * qty
            pnl = (lot.entry_price - close_price) * lot.qty
            lot.sell_price = close_price
            lot.sell_time = ts
            lot.pnl = pnl
            lot.sell_reason = reason
            # Return margin + pnl
            self.cash += lot.cost_usd + pnl
            self._short_allocated -= lot.cost_usd
            self._v10_short_pnl += pnl
            self._realized_pnl += pnl

            self.trade_log.append(TradeLogEntry(
                timestamp=ts, action="SHORT_CLOSE", deal_id=deal.deal_id,
                lot_id=lot.lot_id, price=close_price, qty=lot.qty,
                cost_usd=lot.cost_usd, fee=0.0, pnl=pnl,
                regime=self._current_regime, sell_reason=reason,
            ))

        deal.close_time = ts
        self._completed_short_deals.append(deal)
        self._short_deals.remove(deal)
        logger.info("  📈 SHORT CLOSE (%s): pnl=$%.2f", reason, deal.total_pnl)

    def _close_all_shorts(self, price: float, ts: str, reason: str = "phase_transition"):
        """Close all short deals."""
        for deal in list(self._short_deals):
            self._close_short_deal(deal, price, ts, reason)

    def _apply_funding_costs(self):
        """Apply estimated funding costs to open short positions."""
        # 0.03% per day for 15m candles = 0.03/96 per candle
        rate_per_candle = self._v10_funding_rate_daily / 96.0
        for deal in self._short_deals:
            margin = deal.total_margin
            cost = margin * rate_per_candle
            if cost > self.cash:
                cost = max(0, self.cash * 0.01)  # cap at 1% of remaining cash
            deal.funding_cost += cost
            self._v10_short_funding += cost
            self.cash -= cost

    # ── Interim swing handling ─────────────────────────────────────

    def _handle_interim_distribution(self, price: float, ts: str, signal_strength: float):
        """Partial sell on interim distribution signal during MARKUP."""
        if signal_strength < 0.6 or not self.deals:
            return

        # Close 30-50% of positions (largest lots first)
        close_pct = 0.3 + (signal_strength - 0.6) * 0.5  # 0.6→30%, 1.0→50%
        for deal in self.deals:
            unsold = [l for l in deal.lots if not l.is_sold]
            unsold.sort(key=lambda l: l.cost_usd, reverse=True)  # largest first
            n_to_close = max(1, int(len(unsold) * close_pct))
            for lot in unsold[:n_to_close]:
                revenue = lot.qty * price
                fee = revenue * self.maker_fee
                net = revenue - fee
                pnl = net - lot.cost_usd
                lot.sell_price = price
                lot.sell_fee = fee
                lot.sell_time = ts
                lot.pnl = pnl
                lot.actual_sell_reason = "interim_dist"
                lot.secured_sold = True
                self.cash += net
                # Don't add to _realized_pnl here — counted when deal completes via d.total_pnl
                self._v10_interim_sells += 1

                self.trade_log.append(TradeLogEntry(
                    timestamp=ts, action="SELL_INTERIM", deal_id=deal.deal_id,
                    lot_id=lot.lot_id, price=price, qty=lot.qty,
                    cost_usd=revenue, fee=fee, pnl=pnl,
                    regime=self._current_regime, sell_reason="interim_dist",
                ))

            # Check if deal complete
            if deal.is_complete:
                deal.close_time = ts
                self.completed_deals.append(deal)
                self.deals.remove(deal)

        self._interim_pause_remaining = self._v10_interim_pause_candles
        logger.info("  ⚠️ INTERIM DIST: closed %.0f%% positions, pause %d candles",
                     close_pct * 100, self._interim_pause_remaining)

    def _handle_interim_spring(self, price: float, ts: str, signal_strength: float,
                                tp_pct: float):
        """Deploy freed cash on interim spring signal during MARKUP."""
        if signal_strength < 0.6:
            return

        cost = self._base_cost() * 1.5  # 1.5× sizing
        cost = min(cost, self.cash * 0.5)
        if cost < 5.0:
            return

        fee = cost * self.taker_fee
        qty = (cost - fee) / price

        if self.deals:
            deal = self.deals[0]
        else:
            self._deal_counter += 1
            deal = type(self.deals[0] if self.deals else None) if self.deals else None
            # Open a new deal
            from .backtest_engine_v3 import Deal
            deal = Deal(
                deal_id=self._deal_counter, symbol=self.symbol,
                open_time=ts, regime_at_open=self._current_regime,
            )
            self.deals.append(deal)

        next_id = len(deal.lots)
        lot = Lot(
            lot_id=next_id, buy_price=price, qty=qty,
            cost_usd=cost, buy_fee=fee, buy_time=ts,
            tp_target=price * (1 + tp_pct / 100),
        )
        deal.lots.append(lot)
        self.cash -= cost
        self._v10_interim_buys += 1
        self._interim_pause_remaining = 0  # resume entries

        self.trade_log.append(TradeLogEntry(
            timestamp=ts, action="BUY_INTERIM_SPRING", deal_id=deal.deal_id,
            lot_id=next_id, price=price, qty=qty, cost_usd=cost, fee=fee,
            regime=self._current_regime,
        ))
        logger.info("  🌿 INTERIM SPRING: $%.0f at $%.2f (1.5× sizing)", cost, price)

    # ── Capital rotation transitions ───────────────────────────────

    def _transition_to_cash(self, price: float, ts: str):
        """SPOT → CASH: tighten TPs, stop new deals, prepare to divest."""
        if self._capital_mode == CapitalMode.CASH:
            return
        old_mode = self._capital_mode
        self._capital_mode = CapitalMode.CASH
        self._cash_mode_candles = 0
        logger.info("  💰 CAPITAL ROTATION: %s → CASH at $%.2f", old_mode.value, price)
        self._v10_phase_transitions.append({
            "ts": ts, "from": old_mode.value, "to": "CASH", "price": price,
        })

    def _transition_to_short(self, price: float, ts: str, conviction: float):
        """CASH → SHORT: allocate capital to short engine."""
        if self._capital_mode == CapitalMode.SHORT:
            return
        old_mode = self._capital_mode
        self._capital_mode = CapitalMode.SHORT
        self._short_entry_price = price  # Track for stop-loss
        # Force close any remaining longs
        for deal in list(self.deals):
            self._force_close_deal(deal, price, ts)
        # Open initial short
        self._open_short(price, ts, conviction)
        logger.info("  📉 CAPITAL ROTATION: %s → SHORT at $%.2f (conviction=%.0f)",
                     old_mode.value, price, conviction)
        self._v10_phase_transitions.append({
            "ts": ts, "from": old_mode.value, "to": "SHORT", "price": price,
        })

    def _transition_to_spring(self, price: float, ts: str):
        """SHORT → SPRING: close shorts, deploy aggressively."""
        if self._capital_mode == CapitalMode.SPRING:
            return
        old_mode = self._capital_mode
        self._close_all_shorts(price, ts, "transition_spring")
        self._capital_mode = CapitalMode.SPRING
        logger.info("  🌱 CAPITAL ROTATION: %s → SPRING at $%.2f, cash=$%.0f",
                     old_mode.value, price, self.cash)
        self._v10_phase_transitions.append({
            "ts": ts, "from": old_mode.value, "to": "SPRING", "price": price,
        })

    def _transition_to_spot(self, price: float, ts: str):
        """SPRING → SPOT: resume normal grid."""
        if self._capital_mode == CapitalMode.SPOT:
            return
        old_mode = self._capital_mode
        self._capital_mode = CapitalMode.SPOT
        logger.info("  ✅ CAPITAL ROTATION: %s → SPOT at $%.2f", old_mode.value, price)
        self._v10_phase_transitions.append({
            "ts": ts, "from": old_mode.value, "to": "SPOT", "price": price,
        })

    # ── Main loop override ─────────────────────────────────────────

    def _run_main_loop(self, df: pd.DataFrame):
        """V10 main loop with Wyckoff phases and capital rotation."""
        from .backtest_engine_v5 import _stochastic
        from .backtest_engine_v4 import HARD_SNAPBACK_REGIMES, SOFT_SNAPBACK_REGIMES
        from .backtest_engine_v6 import (
            DONCHIAN_LOOKBACK, DONCHIAN_RANGE_MAX_PCT,
        )

        df = compute_all_indicators(df)
        regimes = classify_regime_v2(df, self.timeframe)
        atr_pct_series = compute_atr_pct(df, 14)
        atr_abs_series = compute_atr(df, 14)
        sma50 = df["close"].rolling(50).mean()
        sma200 = df["close"].rolling(200).mean() if len(df) >= 200 else pd.Series(np.nan, index=df.index)

        # Wyckoff phase engine uses the same SMA50/SMA200 as the grid
        # On 1h candles: SMA50 = 50 hours (~2 days), SMA200 = 200 hours (~8 days)

        bbw = df["bbw"] if "bbw" in df.columns else bollinger_band_width(df["close"], 20)
        bbw_median = bbw.rolling(100, min_periods=20).median()

        # Bollinger bands for interim detection
        bb_mid = df["close"].rolling(20).mean()
        bb_std = df["close"].rolling(20).std()
        bb_upper = bb_mid + 2 * bb_std
        bb_lower = bb_mid - 2 * bb_std

        vol = df["volume"]
        vol_avg = volume_sma(df, 20)

        stoch = _stochastic(df, 14, 3, 3)
        adx_series = df["adx_14"] if "adx_14" in df.columns else pd.Series(np.nan, index=df.index)
        rsi_series = df["rsi_14"] if "rsi_14" in df.columns else pd.Series(np.nan, index=df.index)

        donchian_high = df["high"].rolling(DONCHIAN_LOOKBACK).max()
        donchian_low = df["low"].rolling(DONCHIAN_LOOKBACK).min()
        donchian_range_pct = (donchian_high - donchian_low) / donchian_low.replace(0, np.nan) * 100
        price_series = df["close"]
        in_range_series = (
            (price_series >= donchian_low)
            & (price_series <= donchian_high)
            & (donchian_range_pct < DONCHIAN_RANGE_MAX_PCT)
        )

        # Pre-compute regime transition signals (expensive, do once)
        _regime_trans = None
        if self.conviction_mode:
            try:
                from ..indicators import regime_transition_signals
                _regime_trans = regime_transition_signals(df, regimes)
            except (ImportError, AttributeError):
                pass

        peak_equity = self._effective_cap()
        if self.equity_snapshots:
            peak_equity = max(peak_equity, max(s["equity"] for s in self.equity_snapshots))

        if not hasattr(self, '_candle_timeline'):
            self._candle_timeline = []

        prev_dd_phase = self._dd_phase if hasattr(self, '_dd_phase') else 1
        prev_wyckoff_phase = self._wyckoff.phase
        prev_rsi = np.nan
        prev_price = 0.0
        recent_vol_ratios: list = []

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
            sma200_val = float(sma200.iloc[i]) if not pd.isna(sma200.iloc[i]) else None
            self._trend_bullish = price >= sma50_val if sma50_val is not None else True

            rsi_val = float(rsi_series.iloc[i]) if not pd.isna(rsi_series.iloc[i]) else None
            adx_val = float(adx_series.iloc[i]) if not pd.isna(adx_series.iloc[i]) else None

            # (Wyckoff uses native SMA50/SMA200 from the data timeframe)
            bb_upper_val = float(bb_upper.iloc[i]) if not pd.isna(bb_upper.iloc[i]) else None
            bb_lower_val = float(bb_lower.iloc[i]) if not pd.isna(bb_lower.iloc[i]) else None

            vol_val = float(vol.iloc[i]) if not pd.isna(vol.iloc[i]) else 0.0
            vol_avg_val = float(vol_avg.iloc[i]) if not pd.isna(vol_avg.iloc[i]) and vol_avg.iloc[i] > 0 else 1.0
            vol_ratio = vol_val / vol_avg_val
            vol_spike = vol_ratio > 2.0
            recent_vol_ratios.append(vol_ratio)
            if len(recent_vol_ratios) > 10:
                recent_vol_ratios.pop(0)

            # ── Equity and drawdown ──
            equity = self._equity(price)
            # Include short position value in equity
            for sd in self._short_deals:
                for sl in sd.open_lots:
                    # Unrealized short PnL
                    equity += (sl.entry_price - price) * sl.qty

            if equity > peak_equity:
                peak_equity = equity
            dd = (peak_equity - equity) / peak_equity * 100 if peak_equity > 0 else 0.0

            # DD phase (V8 style)
            if dd < self._v8_phase1_dd_max:
                self._dd_phase = 1
            elif dd < self._v8_phase2_dd_max:
                self._dd_phase = 2
            else:
                self._dd_phase = 3

            if self._dd_phase != prev_dd_phase:
                if self._dd_phase == 2:
                    self._v8_cash_at_phase2_entry = self.cash
                elif self._dd_phase == 3:
                    self._v8_cash_at_phase3_entry = self.cash
                prev_dd_phase = self._dd_phase

            self._v8_phase_candles[self._dd_phase] = self._v8_phase_candles.get(self._dd_phase, 0) + 1
            self._total_candles_processed += 1

            # ── Distribution scoring ──
            fg_value = self._get_fg_for_candle(df, i)
            dist_result = self._dist_scorer.score(df, i, regime, fg_value, regimes)
            dist_score = dist_result.score

            # ── Spring score ──
            stoch_k = float(stoch["stoch_k"].iloc[i]) if not pd.isna(stoch["stoch_k"].iloc[i]) else np.nan
            stoch_d = float(stoch["stoch_d"].iloc[i]) if not pd.isna(stoch["stoch_d"].iloc[i]) else np.nan
            adx_cur = float(adx_series.iloc[i]) if not pd.isna(adx_series.iloc[i]) else np.nan
            adx_prev = float(adx_series.iloc[i-1]) if i > 0 and not pd.isna(adx_series.iloc[i-1]) else np.nan
            cur_bbw = float(bbw.iloc[i]) if not pd.isna(bbw.iloc[i]) else 0.0
            bbw_prev_val = float(bbw.iloc[i-1]) if i > 0 and not pd.isna(bbw.iloc[i-1]) else np.nan
            cur_bbw_med = float(bbw_median.iloc[i]) if not pd.isna(bbw_median.iloc[i]) else cur_bbw

            self._spring_score = self._compute_spring_score(
                vol_val, vol_avg_val, stoch_k, stoch_d, fg_value,
                adx_cur, adx_prev, cur_bbw, bbw_prev_val, cur_bbw_med,
            )

            # ── Wyckoff Phase Engine ──
            # Wyckoff engine uses native timeframe SMAs
            wyckoff_phase, wyckoff_conviction = self._wyckoff.update(
                price=price, sma50=sma50_val, sma200=sma200_val,
                regime=regime, spring_score=self._spring_score,
                dist_score=dist_score, dd_from_peak_pct=dd,
                rsi=rsi_val, adx=adx_val, volume_ratio=vol_ratio,
                bb_upper=bb_upper_val, bb_lower=bb_lower_val,
                fg_value=fg_value,
            )

            # Log phase transitions
            if wyckoff_phase != prev_wyckoff_phase:
                logger.info("  🔄 WYCKOFF: %s → %s (conviction=%.0f) at $%.2f",
                             prev_wyckoff_phase.value, wyckoff_phase.value,
                             wyckoff_conviction, price)
                self._v10_phase_transitions.append({
                    "ts": ts, "phase": wyckoff_phase.value,
                    "conviction": wyckoff_conviction, "price": price,
                })
                prev_wyckoff_phase = wyckoff_phase

            # ── Capital rotation state machine ──
            self._manage_capital_rotation(
                wyckoff_phase, wyckoff_conviction, price, ts,
            )

            # ── Apply funding costs to shorts ──
            if self._short_deals:
                self._apply_funding_costs()

            # ── Sizing multiplier from Wyckoff phase ──
            size_mult = self._wyckoff_size_mult(wyckoff_phase, wyckoff_conviction)

            # ── Exit mode and adaptive params ──
            exit_mode = self._get_exit_mode(regime)
            self._mode_candle_counts[exit_mode.name] = self._mode_candle_counts.get(exit_mode.name, 0) + 1

            tp_pct = self._adaptive_tp(regime, self._current_atr_pct)
            dev_pct = self._adaptive_deviation_v4(regime, self._current_atr_pct, tp_pct)

            conv_score = 0.0
            if self.conviction_mode and _regime_trans is not None:
                try:
                    conviction = self._compute_conviction(df, i, price, regime, _regime_trans)
                    tp_pct, dev_pct = self._apply_conviction_to_params(tp_pct, dev_pct, conviction)
                    conv_score = self._last_conviction.score if self._last_conviction else 0.0
                except (ImportError, AttributeError):
                    pass

            self._spring_bypass = False

            # ── Interim pause countdown ──
            if self._interim_pause_remaining > 0:
                self._interim_pause_remaining -= 1

            # ── Interim swing detection (during MARKUP) ──
            if wyckoff_phase == WyckoffPhase.MARKUP and self._interim_pause_remaining <= 0:
                sma50_rising = (sma50_val is not None and i > 1
                                and not pd.isna(sma50.iloc[i-1])
                                and sma50_val > float(sma50.iloc[i-1]))

                interim_dist = self._wyckoff.detect_interim_distribution(
                    rsi=rsi_val, prev_rsi=prev_rsi if not np.isnan(prev_rsi) else None,
                    price=price, prev_price=prev_price,
                    volume_ratio=vol_ratio, prev_volume_ratios=recent_vol_ratios,
                    bb_upper=bb_upper_val,
                )
                if interim_dist >= 0.6:
                    self._handle_interim_distribution(price, ts, interim_dist)

                interim_spring = self._wyckoff.detect_interim_spring(
                    price=price, sma50=sma50_val, sma50_rising=sma50_rising,
                    rsi=rsi_val, volume_ratio=vol_ratio, bb_lower=bb_lower_val,
                )
                if interim_spring >= 0.8 and self._interim_pause_remaining <= 0:
                    self._handle_interim_spring(price, ts, interim_spring, tp_pct)
                    self._interim_pause_remaining = 96  # pause 24hrs after interim buy too

            # ── Main trading logic by capital mode ──
            if self._capital_mode == CapitalMode.SPOT:
                self._run_spot_mode(
                    i, df, price, high, low, ts, regime, exit_mode,
                    dev_pct, tp_pct, conv_score, size_mult,
                    adx_cur, sma50_val, vol_spike, in_range_series,
                )
            elif self._capital_mode == CapitalMode.CASH:
                # Only allow exits, no new buys
                self._check_exits(high, low, price, ts, regime, exit_mode)
                self._cash_mode_candles += 1
                # Force close after timeout
                if self._cash_mode_candles >= self._v10_cash_timeout_candles:
                    for deal in list(self.deals):
                        self._force_close_deal(deal, price, ts)

            elif self._capital_mode == CapitalMode.SHORT:
                # Allow long exits, manage shorts
                self._check_exits(high, low, price, ts, regime, exit_mode)
                self._check_short_safety_orders(high, price, ts)
                self._check_short_exits(low, high, price, ts)

            elif self._capital_mode == CapitalMode.SPRING:
                # Aggressive spring buys + normal exits
                self._run_spring_mode(
                    i, df, price, high, low, ts, regime, exit_mode,
                    dev_pct, tp_pct, conv_score, wyckoff_conviction,
                    adx_cur, sma50_val, in_range_series,
                )

            # ── Track completed deals for compounding ──
            newly_completed = [d for d in self.completed_deals
                              if hasattr(d, '_v10_counted') is False or not d._v10_counted]
            for d in self.completed_deals:
                if not getattr(d, '_v10_counted', False):
                    self._realized_pnl += d.total_pnl
                    d._v10_counted = True

            # ── Equity snapshot ──
            equity = self._equity(price)
            # Add unrealized short PnL
            for sd in self._short_deals:
                for sl in sd.open_lots:
                    equity += (sl.entry_price - price) * sl.qty

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
                "wyckoff_phase": wyckoff_phase.value,
                "wyckoff_conviction": round(wyckoff_conviction, 1),
                "capital_mode": self._capital_mode.value,
                "cash": round(self.cash, 2),
                "equity": round(equity, 2),
                "dist_score": round(dist_score, 1),
                "spring_score": round(self._spring_score, 1),
                "conviction": round(conv_score, 1),
                "size_mult": round(size_mult, 2),
                "layers_filled": layers_filled,
                "short_deals": len(self._short_deals),
            })

            prev_rsi = rsi_val if rsi_val is not None else np.nan
            prev_price = price

            if i % 500 == 0:
                logger.info("  [%d/%d] eq=$%.0f dd=%.1f%% wyckoff=%s(%.0f) mode=%s cash=$%.0f shorts=%d",
                            i, len(df), equity, dd, wyckoff_phase.value,
                            wyckoff_conviction, self._capital_mode.value,
                            self.cash, len(self._short_deals))

    def _manage_capital_rotation(self, phase: WyckoffPhase, conviction: float,
                                  price: float, ts: str):
        """Simplified two-state capital rotation.
        
        Key insight: Don't use Wyckoff phases directly. Instead:
        - Track whether we've been in MARKUP (golden cross seen, prices rising)
        - Only allow SHORT entry after MARKUP has been established
        - Use distribution score + structural breakdown for SPOT→SHORT
        - Use spring score + accumulation signals for SHORT→SPOT
        """
        mode = self._capital_mode

        # Track if we've seen a REAL markup — prevents false shorts at data start
        # Require MARKUP phase AND significant candle count (not just first few candles)
        if not hasattr(self, '_has_seen_markup'):
            self._has_seen_markup = False
        if not hasattr(self, '_markup_candle_count'):
            self._markup_candle_count = 0
        if phase == WyckoffPhase.MARKUP:
            self._markup_candle_count += 1
            # Need to have been in markup for a while (500+ candles on 1h ≈ 3 weeks)
            # AND have processed enough total candles for reliable detection
            if self._markup_candle_count >= 500 and self._total_candles_processed >= 2000:
                self._has_seen_markup = True

        # ── SPOT→SHORT: Only after seeing markup, on distribution/markdown ──
        if mode == CapitalMode.SPOT and self._has_seen_markup:
            if phase == WyckoffPhase.DISTRIBUTION:
                self._transition_to_cash(price, ts)
            elif phase == WyckoffPhase.MARKDOWN:
                self._transition_to_short(price, ts, conviction)

        # ── CASH→SHORT: If markdown confirmed while in cash ──
        elif mode == CapitalMode.CASH:
            if phase == WyckoffPhase.MARKDOWN:
                self._transition_to_short(price, ts, conviction)
            elif phase in (WyckoffPhase.MARKUP, WyckoffPhase.ACCUMULATION):
                self._transition_to_spot(price, ts)

        # ── SHORT→SPOT: On accumulation, markup, OR simple bullish structure ──
        elif mode == CapitalMode.SHORT:
            if phase == WyckoffPhase.ACCUMULATION:
                self._transition_to_spring(price, ts)
            elif phase == WyckoffPhase.MARKUP:
                self._close_all_shorts(price, ts, "markup_transition")
                self._transition_to_spot(price, ts)
            # Failsafe: if Wyckoff hasn't transitioned but structure is clearly bullish,
            # exit SHORT early to avoid missing a rally
            elif (not hasattr(self, '_short_entry_price') or
                  price > getattr(self, '_short_entry_price', price) * 1.10):
                # Price 10% above short entry = we're wrong, bail out
                self._close_all_shorts(price, ts, "stop_loss_structure")
                self._transition_to_spot(price, ts)

        # ── SPRING→SPOT: On markup or accumulation ──
        elif mode == CapitalMode.SPRING:
            if phase in (WyckoffPhase.MARKUP, WyckoffPhase.ACCUMULATION):
                self._transition_to_spot(price, ts)

    def _run_spot_mode(self, i, df, price, high, low, ts, regime, exit_mode,
                        dev_pct, tp_pct, conv_score, size_mult,
                        adx_cur, sma50_val, vol_spike, in_range_series):
        """Standard spot DCA mode with conviction-weighted sizing."""
        from .backtest_engine_v4 import HARD_SNAPBACK_REGIMES, SOFT_SNAPBACK_REGIMES

        cur_in_range = bool(in_range_series.iloc[i]) if not pd.isna(in_range_series.iloc[i]) else False

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

            # Apply sizing multiplier — no buys if mult is 0
            if size_mult > 0:
                self._check_safety_order_fills_v8(low, price, ts, regime, dev_pct, tp_pct)
                self._check_exits(high, low, price, ts, regime, exit_mode)
                if not self.deals and regime not in BLOCKED_REGIMES and self._interim_pause_remaining <= 0:
                    adx_for_trend = adx_cur if not np.isnan(adx_cur) else 0.0
                    sma50_for_trend = sma50_val if sma50_val is not None else price
                    if not self._should_block_deal_for_trend(price, sma50_for_trend, adx_for_trend, conv_score):
                        self._open_deal_v10(price, ts, regime, tp_pct, size_mult)
            else:
                # No new buys but still exit
                self._check_exits(high, low, price, ts, regime, exit_mode)

        elif self._dd_phase == 2:
            self._dwell_decay = 1.0
            self._conviction_gate = "disabled"
            if self._v8_phase2_allow_tp:
                self._check_exits(high, low, price, ts, regime, exit_mode)

        elif self._dd_phase == 3:
            self._dwell_decay = 1.0
            self._conviction_gate = "disabled"
            self._check_exits(high, low, price, ts, regime, exit_mode)
            if (self._spring_score >= self._v8_spring_score_threshold
                    and self.deals
                    and self._spring_entries_this_deal < self._v8_spring_max_entries):
                self._spring_bypass = True
                self._place_spring_entry(
                    self.deals[0], price, ts, regime, tp_pct, self._spring_score
                )

    def _run_spring_mode(self, i, df, price, high, low, ts, regime, exit_mode,
                          dev_pct, tp_pct, conv_score, conviction,
                          adx_cur, sma50_val, in_range_series):
        """SPRING mode: aggressive buys with 2-3× sizing."""
        self._check_exits(high, low, price, ts, regime, exit_mode)

        # Spring mode buys with 2-3× sizing
        spring_mult = 2.0 + (conviction / 100.0)  # 2× to 3×
        if not self.deals and regime not in BLOCKED_REGIMES:
            self._open_deal_v10(price, ts, regime, tp_pct, spring_mult)
        elif self.deals:
            # Also allow spring safety orders
            self._check_safety_order_fills_v8(low, price, ts, regime, dev_pct, tp_pct)

    def _open_deal_v10(self, price: float, ts: str, regime: str,
                        tp_pct: float, size_mult: float):
        """Open deal with conviction-weighted sizing."""
        base_cost = self._base_cost() * size_mult
        base_cost = min(base_cost, self.cash * 0.5)  # Never use more than 50% for base
        if base_cost > self.cash or base_cost < 5.0:
            return

        fee = base_cost * self.taker_fee
        qty = (base_cost - fee) / price

        self._deal_counter += 1
        lot = Lot(
            lot_id=0, buy_price=price, qty=qty,
            cost_usd=base_cost, buy_fee=fee, buy_time=ts,
            tp_target=price * (1 + tp_pct / 100),
        )
        from .backtest_engine_v3 import Deal
        deal = Deal(
            deal_id=self._deal_counter, symbol=self.symbol,
            lots=[lot], open_time=ts, regime_at_open=regime,
        )
        self.deals.append(deal)
        self.cash -= base_cost

        self.trade_log.append(TradeLogEntry(
            timestamp=ts, action="BUY_V10", deal_id=deal.deal_id, lot_id=0,
            price=price, qty=qty, cost_usd=base_cost, fee=fee, regime=regime,
        ))

    # ── State serialization ────────────────────────────────────────

    def snapshot_state(self) -> dict:
        state = super().snapshot_state()
        state["v10_wyckoff"] = self._wyckoff.snapshot_state()
        state["v10_capital_mode"] = self._capital_mode.value
        state["v10_cash_mode_candles"] = self._cash_mode_candles
        state["v10_interim_pause_remaining"] = self._interim_pause_remaining
        state["v10_short_deals"] = [d.to_dict() for d in self._short_deals]
        state["v10_completed_short_deals"] = [d.to_dict() for d in self._completed_short_deals]
        state["v10_short_deal_counter"] = self._short_deal_counter
        state["v10_short_allocated"] = self._short_allocated
        state["v10_realized_pnl"] = self._realized_pnl
        state["v10_short_pnl"] = self._v10_short_pnl
        state["v10_short_funding"] = self._v10_short_funding
        state["v10_phase_transitions"] = self._v10_phase_transitions
        state["v10_interim_sells"] = self._v10_interim_sells
        state["v10_interim_buys"] = self._v10_interim_buys
        state["v10_total_candles"] = self._total_candles_processed
        state["v10_has_seen_markup"] = getattr(self, '_has_seen_markup', False)
        state["v10_markup_candle_count"] = getattr(self, '_markup_candle_count', 0)
        state["v10_short_entry_price"] = getattr(self, '_short_entry_price', 0)
        # Distribution scorer state
        scorer = self._dist_scorer
        state["v10_dist_scorer"] = {
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
        super().restore_state(state)
        # Wyckoff engine
        if "v10_wyckoff" in state:
            self._wyckoff.restore_state(state["v10_wyckoff"])
        # Capital mode
        self._capital_mode = CapitalMode(state.get("v10_capital_mode", "SPOT"))
        self._cash_mode_candles = state.get("v10_cash_mode_candles", 0)
        self._interim_pause_remaining = state.get("v10_interim_pause_remaining", 0)
        # Short deals
        self._short_deals = []
        for sd in state.get("v10_short_deals", []):
            deal = ShortDeal(
                deal_id=sd["deal_id"], symbol=sd["symbol"],
                open_time=sd.get("open_time", ""),
                close_time=sd.get("close_time"),
                funding_cost=sd.get("funding_cost", 0.0),
            )
            for ld in sd.get("lots", []):
                lot = ShortLot(
                    lot_id=ld["lot_id"], entry_price=ld["entry_price"],
                    qty=ld["qty"], cost_usd=ld["cost_usd"],
                    entry_time=ld["entry_time"],
                    tp_target=ld.get("tp_target", 0.0),
                    sl_target=ld.get("sl_target", 0.0),
                    sell_price=ld.get("sell_price"),
                    sell_time=ld.get("sell_time"),
                    pnl=ld.get("pnl", 0.0),
                    sell_reason=ld.get("sell_reason", ""),
                )
                deal.lots.append(lot)
            self._short_deals.append(deal)
        self._completed_short_deals = []
        for sd in state.get("v10_completed_short_deals", []):
            deal = ShortDeal(
                deal_id=sd["deal_id"], symbol=sd["symbol"],
                open_time=sd.get("open_time", ""),
                close_time=sd.get("close_time"),
                funding_cost=sd.get("funding_cost", 0.0),
            )
            for ld in sd.get("lots", []):
                lot = ShortLot(
                    lot_id=ld["lot_id"], entry_price=ld["entry_price"],
                    qty=ld["qty"], cost_usd=ld["cost_usd"],
                    entry_time=ld["entry_time"],
                    tp_target=ld.get("tp_target", 0.0),
                    sl_target=ld.get("sl_target", 0.0),
                    sell_price=ld.get("sell_price"),
                    sell_time=ld.get("sell_time"),
                    pnl=ld.get("pnl", 0.0),
                    sell_reason=ld.get("sell_reason", ""),
                )
                deal.lots.append(lot)
            self._completed_short_deals.append(deal)
        self._short_deal_counter = state.get("v10_short_deal_counter", 0)
        self._short_allocated = state.get("v10_short_allocated", 0.0)
        self._realized_pnl = state.get("v10_realized_pnl", 0.0)
        self._v10_short_pnl = state.get("v10_short_pnl", 0.0)
        self._v10_short_funding = state.get("v10_short_funding", 0.0)
        self._v10_phase_transitions = state.get("v10_phase_transitions", [])
        self._v10_interim_sells = state.get("v10_interim_sells", 0)
        self._v10_interim_buys = state.get("v10_interim_buys", 0)
        self._total_candles_processed = state.get("v10_total_candles", 0)
        self._has_seen_markup = state.get("v10_has_seen_markup", False)
        self._markup_candle_count = state.get("v10_markup_candle_count", 0)
        self._short_entry_price = state.get("v10_short_entry_price", 0)
        # Distribution scorer
        ds = state.get("v10_dist_scorer", {})
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

    # ── Main entry point ──────────────────────────────────────────

    def run(self, df: pd.DataFrame) -> BacktestResult:
        if len(df) < 100:
            logger.warning("Not enough data (%d rows)", len(df))
            return BacktestResult()

        logger.info("Running V10 backtest (Wyckoff conviction-weighted): %s %s, $%.0f, "
                     "dist_thresh=%.0f, compounding=%s",
                     self.symbol, self.timeframe, self.initial_capital,
                     self._v10_dist_threshold, self._v10_compounding)

        self._candle_timeline = []
        self._dist_scorer.reset()
        self._wyckoff.reset()
        self._run_main_loop(df)

        # Force-close remaining longs
        last_price = float(df.iloc[-1]["close"])
        last_ts = str(df.iloc[-1]["timestamp"])
        for deal in list(self.deals):
            self._force_close_deal(deal, last_price, last_ts)

        # Force-close remaining shorts
        self._close_all_shorts(last_price, last_ts, "backtest_end")

        result = self._compile_results(df)
        result.variant = "v10_wyckoff_conviction"

        result.extra = {
            "v10_params": self.v10_params,
            "v8_spring_buys": self._v8_spring_buys,
            "v8_phase_candles": self._v8_phase_candles,
            "v10_phase_transitions": self._v10_phase_transitions,
            "v10_short_pnl": round(self._v10_short_pnl, 2),
            "v10_short_funding": round(self._v10_short_funding, 2),
            "v10_realized_pnl": round(self._realized_pnl, 2),
            "v10_interim_sells": self._v10_interim_sells,
            "v10_interim_buys": self._v10_interim_buys,
            "v10_short_deals_completed": len(self._completed_short_deals),
        }

        return result
