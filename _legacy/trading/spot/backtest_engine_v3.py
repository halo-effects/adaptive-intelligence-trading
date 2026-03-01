"""Spot DCA Backtest Engine V3 — Hybrid Exits + Regime-Aware Mode Switching.

Phase 1.5: Partial exit (secured portion at TP) + runner (trailing remainder)
Phase 2: Regime-aware exit mode switching (Quick Cycle / Trend Ride / Defensive)

Key invariant: Runners can NEVER perform worse than fixed TP.
  - min_sell_price for runner = original TP price
  - Worst case for any lot = identical to fixed TP
"""
import logging
import json
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from ..regime_detector import classify_regime_v2
from ..indicators import (atr as compute_atr, atr_pct as compute_atr_pct,
                           compute_all as compute_all_indicators,
                           regime_transition_signals)
from .backtest_exit_scorer import BacktestExitScorer
from .conviction_scorer import compute_conviction_from_df

logger = logging.getLogger(__name__)

# ── Fee schedules ──────────────────────────────────────────────────────────

EXCHANGE_FEES: Dict[str, Dict[str, float]] = {
    "aster":       {"maker": 0.0001, "taker": 0.00035},
    "hyperliquid": {"maker": 0.0004, "taker": 0.0007},
    "binance":     {"maker": 0.001,  "taker": 0.001},
}

# ── Regime multipliers (same as v2 for entry/SO logic) ─────────────────────

REGIME_TP_MULT = {
    "ACCUMULATION": 0.85, "CHOPPY": 0.90, "RANGING": 0.85,
    "DISTRIBUTION": 0.90, "MILD_TREND": 1.05, "TRENDING": 1.20,
    "EXTREME": 0.70, "BREAKOUT_WARNING": 0.80, "UNKNOWN": 1.0,
}

REGIME_DEV_MULT = {
    "ACCUMULATION": 0.85, "CHOPPY": 0.90, "RANGING": 0.80,
    "DISTRIBUTION": 0.90, "MILD_TREND": 1.10, "TRENDING": 1.30,
    "EXTREME": 1.50, "BREAKOUT_WARNING": 1.20, "UNKNOWN": 1.0,
}

BLOCKED_REGIMES = {"EXTREME"}
BEARISH_SPACING_MULT = 1.4

# ── Exit mode configurations ──────────────────────────────────────────────

@dataclass
class ExitModeParams:
    name: str
    secured_pct: float      # fraction to sell at TP
    runner_pct: float        # fraction to keep as runner
    trail_distance_atr: float  # ATR multiplier for trail
    runner_timeout: int      # candles before timeout

# Fixed hybrid params (Phase 1.5 without regime switching)
HYBRID_FIXED = ExitModeParams("hybrid_70_30", 0.70, 0.30, 0.5, 24)

# ── Profile-aware exit mode parameters ────────────────────────────────────

PROFILE_EXIT_MODES: Dict[str, Dict[str, ExitModeParams]] = {
    "low": {
        "quick_cycle": ExitModeParams("quick_cycle", 0.90, 0.10, 0.2, 8),
        "trend_ride":  ExitModeParams("trend_ride",  0.80, 0.20, 0.5, 24),
        "defensive":   ExitModeParams("defensive",   1.00, 0.00, 0.0, 0),
    },
    "medium": {
        "quick_cycle": ExitModeParams("quick_cycle", 0.85, 0.15, 0.3, 12),
        "trend_ride":  ExitModeParams("trend_ride",  0.50, 0.50, 1.0, 48),
        "defensive":   ExitModeParams("defensive",   1.00, 0.00, 0.0, 0),
    },
    "high": {
        "quick_cycle": ExitModeParams("quick_cycle", 0.60, 0.40, 0.8, 36),
        "trend_ride":  ExitModeParams("trend_ride",  0.40, 0.60, 1.5, 72),
        "defensive":   ExitModeParams("defensive",   1.00, 0.00, 0.0, 0),
    },
}

def get_regime_exit_mode(regime: str, trend_bullish: bool, profile: str = "medium") -> ExitModeParams:
    """Phase 2: Select exit mode based on regime + risk profile."""
    modes = PROFILE_EXIT_MODES[profile]

    if profile == "low":
        # Conservative: default Quick Cycle, Trend Ride only in TRENDING
        # Defensive triggers earlier (MILD_TREND bearish, DISTRIBUTION)
        if regime in ("EXTREME", "DISTRIBUTION"):
            return modes["defensive"]
        if regime == "MILD_TREND" and not trend_bullish:
            return modes["defensive"]
        if regime == "TRENDING":
            return modes["trend_ride"]
        # Everything else: Quick Cycle (RANGING, ACCUMULATION, CHOPPY,
        # MILD_TREND bullish, BREAKOUT_WARNING, UNKNOWN)
        return modes["quick_cycle"]

    elif profile == "high":
        # Aggressive: default Trend Ride, Defensive only in EXTREME
        if regime == "EXTREME":
            return modes["defensive"]
        # Post-EXTREME cooldown uses Quick Cycle (handled by caller if needed,
        # but BREAKOUT_WARNING is a reasonable proxy)
        if regime == "BREAKOUT_WARNING":
            return modes["quick_cycle"]
        # Everything else: Trend Ride (RANGING, ACCUMULATION, CHOPPY,
        # MILD_TREND, TRENDING, DISTRIBUTION, UNKNOWN)
        return modes["trend_ride"]

    else:  # medium — original balanced logic
        if regime in ("RANGING", "ACCUMULATION", "CHOPPY"):
            return modes["quick_cycle"]
        elif regime == "TRENDING":
            return modes["trend_ride"]
        elif regime == "MILD_TREND":
            return modes["trend_ride"] if trend_bullish else modes["defensive"]
        elif regime in ("EXTREME", "DISTRIBUTION"):
            return modes["defensive"]
        elif regime == "BREAKOUT_WARNING":
            return modes["quick_cycle"]
        else:
            return modes["quick_cycle"]  # UNKNOWN fallback


# ── Risk profiles ──────────────────────────────────────────────────────────

@dataclass
class RiskProfile:
    name: str
    max_safety_orders: int
    base_order_pct: float
    tp_min: float
    tp_max: float
    tp_baseline: float
    deviation_min: float
    deviation_max: float
    deviation_baseline: float
    max_drawdown_pct: float
    so_size_multiplier: float = 2.0
    atr_baseline_pct: float = 0.8

PROFILES: Dict[str, RiskProfile] = {
    "low": RiskProfile(
        name="low", max_safety_orders=5, base_order_pct=0.03,
        tp_min=1.5, tp_max=2.5, tp_baseline=2.0,
        deviation_min=3.0, deviation_max=4.0, deviation_baseline=3.5,
        max_drawdown_pct=15.0,
    ),
    "medium": RiskProfile(
        name="medium", max_safety_orders=8, base_order_pct=0.04,
        tp_min=1.0, tp_max=2.0, tp_baseline=1.5,
        deviation_min=2.0, deviation_max=3.0, deviation_baseline=2.5,
        max_drawdown_pct=25.0,
    ),
    "high": RiskProfile(
        name="high", max_safety_orders=12, base_order_pct=0.05,
        tp_min=0.8, tp_max=1.5, tp_baseline=1.0,
        deviation_min=1.5, deviation_max=2.5, deviation_baseline=2.0,
        max_drawdown_pct=35.0,
    ),
}


# ── Data structures ────────────────────────────────────────────────────────

@dataclass
class Runner:
    """Tracks a runner sub-lot after partial exit."""
    qty: float
    entry_price: float          # original lot buy price
    tp_price: float             # original TP target = min sell price
    trail_high: float
    trail_distance: float
    candles_since_improvement: int = 0
    timeout_candles: int = 24
    cost_usd: float = 0.0      # proportional cost
    sell_price: Optional[float] = None
    sell_time: Optional[str] = None
    sell_reason: str = ""
    pnl: float = 0.0
    best_high: float = 0.0     # highest trail_high seen

    @property
    def is_sold(self) -> bool:
        return self.sell_price is not None


@dataclass
class Lot:
    lot_id: int
    buy_price: float
    qty: float
    cost_usd: float
    buy_fee: float
    buy_time: str
    sell_price: Optional[float] = None
    sell_fee: float = 0.0
    sell_time: Optional[str] = None
    tp_target: float = 0.0
    pnl: float = 0.0
    actual_sell_reason: str = ""
    # Runner tracking
    runner: Optional[Runner] = None
    secured_sold: bool = False  # True once secured portion sold

    @property
    def is_sold(self) -> bool:
        if self.runner is not None:
            return self.secured_sold and self.runner.is_sold
        return self.sell_price is not None

    def to_dict(self) -> dict:
        d = {
            "lot_id": self.lot_id, "buy_price": self.buy_price,
            "qty": self.qty, "cost_usd": self.cost_usd,
            "buy_fee": self.buy_fee, "buy_time": self.buy_time,
            "sell_price": self.sell_price, "sell_fee": self.sell_fee,
            "sell_time": self.sell_time, "tp_target": self.tp_target,
            "pnl": self.pnl, "actual_sell_reason": self.actual_sell_reason,
            "secured_sold": self.secured_sold,
        }
        if self.runner:
            d["runner"] = {
                "qty": self.runner.qty, "tp_price": self.runner.tp_price,
                "sell_price": self.runner.sell_price, "sell_reason": self.runner.sell_reason,
                "pnl": self.runner.pnl, "best_high": self.runner.best_high,
            }
        return d


@dataclass
class Deal:
    deal_id: int
    symbol: str
    lots: List[Lot] = field(default_factory=list)
    open_time: str = ""
    close_time: Optional[str] = None
    regime_at_open: str = "UNKNOWN"

    @property
    def is_complete(self) -> bool:
        return len(self.lots) > 0 and all(lot.is_sold for lot in self.lots)

    @property
    def unsold_lots(self) -> List[Lot]:
        return [l for l in self.lots if not l.is_sold]

    @property
    def total_invested(self) -> float:
        return sum(l.cost_usd for l in self.lots)

    @property
    def total_pnl(self) -> float:
        total = 0.0
        for l in self.lots:
            if l.sell_price is not None:
                total += l.pnl
            if l.runner and l.runner.is_sold:
                total += l.runner.pnl
        return total

    @property
    def total_fees(self) -> float:
        total = sum(l.buy_fee + l.sell_fee for l in self.lots)
        return total

    @property
    def capital_deployed(self) -> float:
        deployed = 0.0
        for l in self.lots:
            if not l.is_sold:
                if l.secured_sold and l.runner and not l.runner.is_sold:
                    deployed += l.runner.cost_usd
                elif l.sell_price is None:
                    deployed += l.cost_usd
        return deployed

    def to_dict(self) -> dict:
        return {
            "deal_id": self.deal_id, "symbol": self.symbol,
            "lots": [l.to_dict() for l in self.lots],
            "open_time": self.open_time, "close_time": self.close_time,
            "regime_at_open": self.regime_at_open,
            "total_invested": self.total_invested,
            "total_pnl": self.total_pnl, "total_fees": self.total_fees,
            "is_complete": self.is_complete,
        }


@dataclass
class TradeLogEntry:
    timestamp: str
    action: str
    deal_id: int
    lot_id: int
    price: float
    qty: float
    cost_usd: float
    fee: float
    pnl: float = 0.0
    regime: str = ""
    sell_reason: str = ""
    exit_mode: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class BacktestResult:
    total_return_pct: float = 0.0
    max_drawdown_pct: float = 0.0
    sharpe_ratio: float = 0.0
    deals_per_day: float = 0.0
    avg_profit_per_deal_usd: float = 0.0
    avg_profit_per_deal_pct: float = 0.0
    avg_hold_time_hours: float = 0.0
    capital_utilization_pct: float = 0.0
    win_rate: float = 0.0
    largest_single_loss: float = 0.0
    total_fees_paid: float = 0.0
    total_deals_completed: int = 0
    total_deals_open: int = 0
    initial_capital: float = 0.0
    final_equity: float = 0.0
    per_lot_stats: Dict[int, Dict[str, float]] = field(default_factory=dict)
    trade_log: List[dict] = field(default_factory=list)
    deals: List[dict] = field(default_factory=list)
    equity_curve: List[dict] = field(default_factory=list)
    profile: str = ""
    symbol: str = ""
    timeframe: str = ""
    exchange: str = ""
    variant: str = ""
    compounding: bool = False
    # Runner/hybrid stats
    runner_stats: Dict[str, Any] = field(default_factory=dict)
    regime_mode_stats: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2, default=str)


# ── Engine ─────────────────────────────────────────────────────────────────

class SpotBacktestEngineV3:
    """Spot DCA backtest with hybrid exits and regime-aware mode switching."""

    def __init__(
        self,
        profile: str = "medium",
        capital: float = 10000.0,
        exchange: str = "binance",
        symbol: str = "BTC/USDT",
        timeframe: str = "4h",
        variant: str = "fixed_tp",  # "fixed_tp", "hybrid_70_30", "regime_adaptive", "hybrid_custom"
        custom_exit_params: Optional[ExitModeParams] = None,
        compounding: bool = False,
        conviction_mode: bool = False,  # Enable conviction-driven parameter adjustment
        smart_entry_score: float = 60.0,  # Assumed entry score for backtest
        fear_greed_history: dict = None,  # Historical F&G: {date_str: int_value}
    ):
        self.profile = PROFILES[profile.lower()]
        self.initial_capital = capital
        self.cash = capital
        self.exchange = exchange.lower()
        self.symbol = symbol
        self.timeframe = timeframe
        self.variant = variant
        self._custom_exit_params = custom_exit_params
        self.compounding = compounding
        self.conviction_mode = conviction_mode
        self._smart_entry_score = smart_entry_score
        self._last_conviction = None  # Track for logging
        self._fear_greed_history = fear_greed_history or {}

        fees = EXCHANGE_FEES.get(self.exchange, EXCHANGE_FEES["binance"])
        self.taker_fee = fees["taker"]
        self.maker_fee = fees["maker"]

        self.deals: List[Deal] = []
        self.completed_deals: List[Deal] = []
        self.trade_log: List[TradeLogEntry] = []
        self.equity_snapshots: List[dict] = []

        self._deal_counter = 0
        self._halted = False
        self._current_regime = "UNKNOWN"
        self._current_atr_pct = 0.0
        self._current_atr_abs = 0.0
        self._trend_bullish = True
        self._utilization_samples: List[float] = []

        # Runner tracking
        self._runners_created = 0
        self._runners_improved = 0  # sold above TP price
        self._runners_at_floor = 0  # sold at exactly TP price
        self._runners_timed_out = 0
        self._runners_trail_stopped = 0
        self._runner_extra_profits: List[float] = []
        self._runner_best_ride_pct = 0.0

        # Regime mode tracking
        self._mode_candle_counts: Dict[str, int] = {
            "quick_cycle": 0, "trend_ride": 0, "defensive": 0,
            "hybrid_70_30": 0, "fixed_tp": 0,
        }
        self._mode_pnl: Dict[str, float] = {
            "quick_cycle": 0.0, "trend_ride": 0.0, "defensive": 0.0,
            "hybrid_70_30": 0.0, "fixed_tp": 0.0,
        }

    # ── Adaptive parameters ────────────────────────────────────────────

    def _adaptive_tp(self, regime: str, atr_pct: float) -> float:
        p = self.profile
        if atr_pct <= 0:
            return p.tp_baseline
        atr_ratio = atr_pct / p.atr_baseline_pct
        tp = p.tp_baseline * atr_ratio
        tp *= REGIME_TP_MULT.get(regime, 1.0)
        return max(p.tp_min, min(p.tp_max, round(tp, 3)))

    def _adaptive_deviation(self, regime: str, atr_pct: float, current_tp: float) -> float:
        p = self.profile
        if atr_pct <= 0:
            return p.deviation_baseline
        atr_ratio = atr_pct / p.atr_baseline_pct
        dev = p.deviation_baseline * atr_ratio
        dev *= REGIME_DEV_MULT.get(regime, 1.0)
        dev = max(p.deviation_min, min(p.deviation_max, dev))
        dev = max(dev, current_tp * 1.5)
        return min(p.deviation_max, round(dev, 3))

    def _so_trigger_price(self, base_price: float, so_index: int, deviation: float) -> float:
        total_drop = deviation * so_index / 100.0
        return base_price * (1.0 - total_drop)

    def _so_cost(self, base_cost: float, so_index: int) -> float:
        # Profile's exponential scaling stays unchanged (e.g. 2.0^so_index)
        cost = base_cost * (self.profile.so_size_multiplier ** so_index)
        # Conviction/Wyckoff applies as a LINEAR multiplier on the result
        # This nudges SO cost up/down without distorting the exponential curve
        if self.conviction_mode and self._last_conviction:
            cost = cost * self._last_conviction.so_size_multiplier
        return cost

    def _sizing_equity(self) -> float:
        """Equity proxy for order sizing: cash + cost basis of open positions."""
        open_cost = sum(l.cost_usd for d in self.deals for l in d.lots
                        if not l.is_sold)
        return self.cash + open_cost

    def _base_cost(self) -> float:
        """Base order cost, using current equity if compounding."""
        base_pct = self.profile.base_order_pct
        if self.conviction_mode and self._last_conviction:
            base_pct = base_pct * self._last_conviction.base_order_multiplier
        if self.compounding:
            return self._sizing_equity() * base_pct
        return self.initial_capital * base_pct

    def _compute_conviction(self, df, i, price, regime, regime_trans):
        """Compute conviction score for current candle. Returns ConvictionResult."""
        active_deal = self.deals[0] if self.deals else None
        deal_profit = 0.0
        deal_so_count = 0
        if active_deal:
            avg_entry = sum(l.buy_price * l.cost_usd for l in active_deal.lots) / max(active_deal.total_invested, 1)
            deal_profit = (price - avg_entry) / avg_entry * 100 if avg_entry > 0 else 0
            deal_so_count = max(0, len(active_deal.lots) - 1)

        r_stab = float(regime_trans["regime_stability"].iloc[i]) if i < len(regime_trans) else 0.5
        r_trans = float(regime_trans["regime_transition_pressure"].iloc[i]) if i < len(regime_trans) else 0.0

        # Look up historical F&G for this candle's date
        macro_data = None
        if self._fear_greed_history:
            candle_ts = df.iloc[i]["timestamp"]
            if isinstance(candle_ts, (int, float)):
                from datetime import datetime, timezone
                date_str = datetime.fromtimestamp(candle_ts / 1000, tz=timezone.utc).strftime("%Y-%m-%d")
            else:
                date_str = pd.to_datetime(candle_ts).strftime("%Y-%m-%d")
            fg_val = self._fear_greed_history.get(date_str)
            if fg_val is not None:
                if fg_val <= 25:
                    classification = "Extreme Fear"
                elif fg_val <= 45:
                    classification = "Fear"
                elif fg_val <= 55:
                    classification = "Neutral"
                elif fg_val <= 75:
                    classification = "Greed"
                else:
                    classification = "Extreme Greed"
                macro_data = {"fear_greed": {"value": fg_val, "classification": classification}}

        conviction = compute_conviction_from_df(
            df, i, regime=regime,
            regime_stability=r_stab,
            regime_transition_pressure=r_trans,
            smart_entry_score=self._smart_entry_score,
            deal_open=bool(self.deals),
            deal_profit_pct=deal_profit,
            deal_so_count=deal_so_count,
            exit_pressure=0.0,
            trend_bullish=self._trend_bullish,
            macro_data=macro_data,
        )
        self._last_conviction = conviction
        return conviction

    def _apply_conviction_to_params(self, tp_pct, dev_pct, conviction):
        """Apply conviction multipliers to TP and deviation."""
        tp_pct = max(self.profile.tp_min,
                     min(self.profile.tp_max * 1.5,
                         tp_pct * conviction.tp_multiplier))
        dev_pct = max(self.profile.deviation_min * 0.7,
                      min(self.profile.deviation_max * 1.5,
                          dev_pct * conviction.deviation_multiplier))
        dev_pct = max(dev_pct, tp_pct * 1.5)
        return tp_pct, dev_pct

    def _get_exit_mode(self, regime: str) -> ExitModeParams:
        """Get exit mode params based on variant and risk profile."""
        if self.variant == "fixed_tp":
            return ExitModeParams("fixed_tp", 1.0, 0.0, 0.0, 0)
        elif self.variant == "hybrid_70_30":
            return HYBRID_FIXED
        elif self.variant == "hybrid_custom" and self._custom_exit_params:
            return self._custom_exit_params
        elif self.variant == "regime_adaptive":
            return get_regime_exit_mode(regime, self._trend_bullish, self.profile.name)
        return ExitModeParams("fixed_tp", 1.0, 0.0, 0.0, 0)

    # ── Core simulation ────────────────────────────────────────────────

    def run(self, df: pd.DataFrame) -> BacktestResult:
        if len(df) < 100:
            logger.warning("Not enough data for backtest (%d rows)", len(df))
            return BacktestResult()

        logger.info("Computing regimes and indicators...")
        if self.conviction_mode:
            df = compute_all_indicators(df, include_leading=True)
        regimes = classify_regime_v2(df, self.timeframe)
        atr_pct_series = compute_atr_pct(df, 14)
        atr_abs_series = compute_atr(df, 14)
        sma50 = df["close"].rolling(50).mean()

        # Regime transition signals for conviction
        regime_trans = None
        if self.conviction_mode:
            regime_trans = regime_transition_signals(df, regimes)

        logger.info("Running V3 backtest (variant=%s): %s %s, capital=$%.0f, profile=%s%s",
                     self.variant, self.symbol, self.timeframe,
                     self.initial_capital, self.profile.name,
                     " [conviction]" if self.conviction_mode else "")

        peak_equity = self.initial_capital

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

            exit_mode = self._get_exit_mode(regime)
            self._mode_candle_counts[exit_mode.name] = self._mode_candle_counts.get(exit_mode.name, 0) + 1

            tp_pct = self._adaptive_tp(regime, self._current_atr_pct)
            dev_pct = self._adaptive_deviation(regime, self._current_atr_pct, tp_pct)

            if self.conviction_mode and regime_trans is not None:
                conviction = self._compute_conviction(df, i, price, regime, regime_trans)
                tp_pct, dev_pct = self._apply_conviction_to_params(tp_pct, dev_pct, conviction)

            if self._halted:
                self._check_exits(high, low, price, ts, regime, exit_mode)
            else:
                self._check_safety_order_fills(low, price, ts, regime, dev_pct, tp_pct)
                self._check_exits(high, low, price, ts, regime, exit_mode)
                if not self.deals and regime not in BLOCKED_REGIMES:
                    self._open_deal(price, ts, regime, tp_pct)

            equity = self._equity(price)
            self.equity_snapshots.append({"timestamp": ts, "equity": equity, "cash": self.cash, "price": price})

            deployed = sum(d.capital_deployed for d in self.deals)
            self._utilization_samples.append(deployed / self.initial_capital * 100 if self.initial_capital > 0 else 0)

            if equity > peak_equity:
                peak_equity = equity
            dd = (peak_equity - equity) / peak_equity * 100
            if dd >= self.profile.max_drawdown_pct and not self._halted:
                logger.warning("Drawdown halt triggered: %.1f%% >= %.1f%%", dd, self.profile.max_drawdown_pct)
                self._halted = True

            if i % 500 == 0:
                conv_str = ""
                if self.conviction_mode and self._last_conviction:
                    c = self._last_conviction
                    conv_str = f", conv={c.score:.0f}({c.band}) tp×{c.tp_multiplier:.2f} dev×{c.deviation_multiplier:.2f}"
                logger.info("  [%d/%d] equity=$%.0f, deals_open=%d, completed=%d, mode=%s%s",
                            i, len(df), equity, len(self.deals), len(self.completed_deals), exit_mode.name, conv_str)

        # Force-close remaining
        last_price = float(df.iloc[-1]["close"])
        last_ts = str(df.iloc[-1]["timestamp"])
        for deal in list(self.deals):
            self._force_close_deal(deal, last_price, last_ts)

        return self._compile_results(df)

    # ── Deal management ────────────────────────────────────────────────

    def _open_deal(self, price: float, ts: str, regime: str, tp_pct: float):
        base_cost = self._base_cost()
        if base_cost > self.cash:
            return
        fee = base_cost * self.taker_fee
        qty = (base_cost - fee) / price

        self._deal_counter += 1
        lot = Lot(
            lot_id=0, buy_price=price, qty=qty,
            cost_usd=base_cost, buy_fee=fee, buy_time=ts,
            tp_target=price * (1 + tp_pct / 100),
        )
        deal = Deal(
            deal_id=self._deal_counter, symbol=self.symbol,
            lots=[lot], open_time=ts, regime_at_open=regime,
        )
        self.deals.append(deal)
        self.cash -= base_cost

        self.trade_log.append(TradeLogEntry(
            timestamp=ts, action="BUY", deal_id=deal.deal_id, lot_id=0,
            price=price, qty=qty, cost_usd=base_cost, fee=fee, regime=regime,
        ))

    def _check_safety_order_fills(self, low: float, close: float, ts: str,
                                   regime: str, dev_pct: float, tp_pct: float):
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
            spacing_mult = BEARISH_SPACING_MULT if not self._trend_bullish else 1.0
            trigger = self._so_trigger_price(base_price, next_so, dev_pct * spacing_mult)

            if low <= trigger:
                fill_price = trigger
                base_cost = self._base_cost()
                so_cost = self._so_cost(base_cost, next_so)
                so_cost = min(so_cost, self.cash)
                so_cost = min(so_cost, self.cash)
                if so_cost < 5.0:
                    continue
                fee = so_cost * self.taker_fee
                qty = (so_cost - fee) / fill_price

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

    def _sell_secured(self, deal: Deal, lot: Lot, sell_price: float, sell_qty: float,
                      ts: str, regime: str, reason: str, exit_mode: ExitModeParams):
        """Sell the secured portion of a lot."""
        revenue = sell_qty * sell_price
        fee = revenue * self.maker_fee
        net_revenue = revenue - fee
        cost_portion = lot.cost_usd * (sell_qty / lot.qty) if lot.qty > 0 else 0.0
        pnl = net_revenue - cost_portion

        lot.sell_price = sell_price
        lot.sell_fee = fee
        lot.sell_time = ts
        lot.pnl = pnl
        lot.actual_sell_reason = reason
        lot.secured_sold = True
        self.cash += net_revenue

        self._mode_pnl[exit_mode.name] = self._mode_pnl.get(exit_mode.name, 0) + pnl

        self.trade_log.append(TradeLogEntry(
            timestamp=ts, action="SELL", deal_id=deal.deal_id, lot_id=lot.lot_id,
            price=sell_price, qty=sell_qty, cost_usd=revenue, fee=fee,
            pnl=pnl, regime=regime, sell_reason=reason, exit_mode=exit_mode.name,
        ))

    def _sell_runner(self, deal: Deal, lot: Lot, runner: Runner, sell_price: float,
                     ts: str, regime: str, reason: str, exit_mode_name: str):
        """Sell a runner."""
        # Enforce floor: never sell below TP price
        actual_price = max(sell_price, runner.tp_price)
        revenue = runner.qty * actual_price
        fee = revenue * self.maker_fee
        net_revenue = revenue - fee
        pnl = net_revenue - runner.cost_usd

        runner.sell_price = actual_price
        runner.sell_time = ts
        runner.sell_reason = reason
        runner.pnl = pnl
        self.cash += net_revenue

        # Track runner stats
        extra_pct = (actual_price - runner.tp_price) / runner.entry_price * 100 if runner.entry_price > 0 else 0.0
        self._runner_extra_profits.append(extra_pct)

        if actual_price > runner.tp_price * 1.001:
            self._runners_improved += 1
        else:
            self._runners_at_floor += 1

        if reason == "timeout":
            self._runners_timed_out += 1
        else:
            self._runners_trail_stopped += 1

        ride_pct = (runner.best_high - runner.tp_price) / runner.entry_price * 100 if runner.entry_price > 0 else 0.0
        if ride_pct > self._runner_best_ride_pct:
            self._runner_best_ride_pct = ride_pct

        self._mode_pnl[exit_mode_name] = self._mode_pnl.get(exit_mode_name, 0) + pnl

        self.trade_log.append(TradeLogEntry(
            timestamp=ts, action="SELL_RUNNER", deal_id=deal.deal_id, lot_id=lot.lot_id,
            price=actual_price, qty=runner.qty, cost_usd=revenue, fee=fee,
            pnl=pnl, regime=regime, sell_reason=reason, exit_mode=exit_mode_name,
        ))

    def _check_exits(self, high: float, low: float, close: float, ts: str,
                     regime: str, exit_mode: ExitModeParams):
        for deal in list(self.deals):
            unsold = sorted(deal.unsold_lots, key=lambda l: l.lot_id, reverse=True)
            current_tp_pct = self._adaptive_tp(regime, self._current_atr_pct)

            for lot in unsold:
                # Update TP target dynamically if not yet hit
                if not lot.secured_sold:
                    lot.tp_target = lot.buy_price * (1 + current_tp_pct / 100)

                # ── Handle active runner ──
                if lot.secured_sold and lot.runner and not lot.runner.is_sold:
                    runner = lot.runner
                    # Update trail high
                    if high > runner.trail_high:
                        runner.trail_high = high
                        runner.best_high = max(runner.best_high, high)
                        runner.candles_since_improvement = 0
                    else:
                        runner.candles_since_improvement += 1

                    # Recalculate trail distance based on current mode
                    runner.trail_distance = self._current_atr_abs * exit_mode.trail_distance_atr
                    if runner.trail_distance <= 0:
                        runner.trail_distance = runner.entry_price * 0.005  # fallback 0.5%

                    trail_stop = runner.trail_high - runner.trail_distance

                    # 1. Trail stop hit
                    if low <= trail_stop:
                        self._sell_runner(deal, lot, runner, max(trail_stop, runner.tp_price),
                                         ts, regime, "trail_stop", exit_mode.name)
                        continue

                    # 2. Timeout
                    if runner.candles_since_improvement >= runner.timeout_candles:
                        self._sell_runner(deal, lot, runner, max(close, runner.tp_price),
                                         ts, regime, "timeout", exit_mode.name)
                        continue

                # ── Check TP hit for unsold lots ──
                elif not lot.secured_sold and high >= lot.tp_target:
                    if exit_mode.runner_pct > 0:
                        # Hybrid exit: sell secured, create runner
                        secured_qty = lot.qty * exit_mode.secured_pct
                        runner_qty = lot.qty * exit_mode.runner_pct

                        # Sell secured portion at TP
                        self._sell_secured(deal, lot, lot.tp_target, secured_qty,
                                          ts, regime, "secured_tp", exit_mode)

                        # Create runner
                        runner_cost = lot.cost_usd * exit_mode.runner_pct
                        trail_dist = self._current_atr_abs * exit_mode.trail_distance_atr
                        if trail_dist <= 0:
                            trail_dist = lot.buy_price * 0.005

                        runner = Runner(
                            qty=runner_qty,
                            entry_price=lot.buy_price,
                            tp_price=lot.tp_target,  # floor = original TP
                            trail_high=high,
                            trail_distance=trail_dist,
                            timeout_candles=exit_mode.runner_timeout,
                            cost_usd=runner_cost,
                            best_high=high,
                        )
                        lot.runner = runner
                        self._runners_created += 1

                        # Check if trail stop already triggered this candle
                        trail_stop = runner.trail_high - runner.trail_distance
                        if low <= trail_stop:
                            self._sell_runner(deal, lot, runner,
                                            max(trail_stop, runner.tp_price),
                                            ts, regime, "trail_stop", exit_mode.name)
                    else:
                        # Fixed TP: sell everything at TP
                        self._sell_secured(deal, lot, lot.tp_target, lot.qty,
                                          ts, regime, "fixed_tp", exit_mode)

            if deal.is_complete:
                deal.close_time = ts
                self.completed_deals.append(deal)
                self.deals.remove(deal)

    def _force_close_deal(self, deal: Deal, price: float, ts: str):
        for lot in deal.lots:
            if not lot.secured_sold:
                revenue = lot.qty * price
                fee = revenue * self.taker_fee
                net_revenue = revenue - fee
                pnl = net_revenue - lot.cost_usd
                lot.sell_price = price
                lot.sell_fee = fee
                lot.sell_time = ts
                lot.pnl = pnl
                lot.actual_sell_reason = "force_close"
                lot.secured_sold = True
                self.cash += net_revenue
                self.trade_log.append(TradeLogEntry(
                    timestamp=ts, action="SELL(FORCE)", deal_id=deal.deal_id, lot_id=lot.lot_id,
                    price=price, qty=lot.qty, cost_usd=revenue, fee=fee, pnl=pnl,
                ))
            if lot.runner and not lot.runner.is_sold:
                runner = lot.runner
                actual_price = max(price, runner.tp_price) if price > runner.entry_price else price
                revenue = runner.qty * actual_price
                fee = revenue * self.taker_fee
                net_revenue = revenue - fee
                pnl = net_revenue - runner.cost_usd
                runner.sell_price = actual_price
                runner.sell_time = ts
                runner.sell_reason = "force_close"
                runner.pnl = pnl
                self.cash += net_revenue
                self.trade_log.append(TradeLogEntry(
                    timestamp=ts, action="SELL_RUNNER(FORCE)", deal_id=deal.deal_id,
                    lot_id=lot.lot_id, price=actual_price, qty=runner.qty,
                    cost_usd=revenue, fee=fee, pnl=pnl,
                ))
        deal.close_time = ts
        self.completed_deals.append(deal)
        self.deals.remove(deal)

    def _equity(self, current_price: float) -> float:
        unsold_value = 0.0
        for deal in self.deals:
            for lot in deal.lots:
                if not lot.secured_sold:
                    unsold_value += lot.qty * current_price
                elif lot.runner and not lot.runner.is_sold:
                    unsold_value += lot.runner.qty * current_price
        return self.cash + unsold_value

    # ── Results compilation ────────────────────────────────────────────

    def _compile_results(self, df: pd.DataFrame) -> BacktestResult:
        all_deals = self.completed_deals
        final_equity = self.cash

        total_return = (final_equity - self.initial_capital) / self.initial_capital * 100

        eq = pd.Series([s["equity"] for s in self.equity_snapshots])
        peak = eq.cummax()
        dd = (peak - eq) / peak * 100
        max_dd = float(dd.max()) if len(dd) > 0 else 0.0

        if len(self.equity_snapshots) > 1:
            eq_df = pd.DataFrame(self.equity_snapshots)
            # Handle both epoch ms and string timestamps
            ts_sample = eq_df["timestamp"].iloc[0]
            if isinstance(ts_sample, (int, float)) or (isinstance(ts_sample, str) and ts_sample.replace('.','').isdigit()):
                eq_df["timestamp"] = pd.to_datetime(pd.to_numeric(eq_df["timestamp"]), unit="ms")
            else:
                eq_df["timestamp"] = pd.to_datetime(eq_df["timestamp"])
            daily = eq_df.set_index("timestamp")["equity"].resample("1D").last().dropna()
            daily_ret = daily.pct_change().dropna()
            if len(daily_ret) > 1 and daily_ret.std() > 0:
                sharpe = float(daily_ret.mean() / daily_ret.std() * np.sqrt(365))
            else:
                sharpe = 0.0
        else:
            sharpe = 0.0

        if len(df) > 1:
            ts0 = df.iloc[0]["timestamp"]
            ts1 = df.iloc[-1]["timestamp"]
            if isinstance(ts0, (int, float)):
                t0 = pd.to_datetime(ts0, unit="ms")
                t1 = pd.to_datetime(ts1, unit="ms")
            else:
                t0 = pd.to_datetime(ts0)
                t1 = pd.to_datetime(ts1)
            days = max((t1 - t0).total_seconds() / 86400, 1)
        else:
            days = 1

        completed = [d for d in all_deals if d.is_complete or d.close_time is not None]
        n_completed = len(completed)

        deal_pnls = [d.total_pnl for d in completed]
        deal_pnl_pcts = [d.total_pnl / d.total_invested * 100 if d.total_invested > 0 else 0 for d in completed]

        def _parse_ts(ts):
            if isinstance(ts, (int, float)) or (isinstance(ts, str) and ts.replace('.','').isdigit()):
                return pd.to_datetime(float(ts), unit="ms")
            return pd.to_datetime(ts)

        hold_times = []
        for d in completed:
            if d.open_time and d.close_time:
                t_open = _parse_ts(d.open_time)
                t_close = _parse_ts(d.close_time)
                hold_times.append((t_close - t_open).total_seconds() / 3600)

        wins = sum(1 for p in deal_pnls if p > 0)

        # Runner stats
        runner_stats = {
            "runners_created": self._runners_created,
            "runners_improved": self._runners_improved,
            "runners_at_floor": self._runners_at_floor,
            "runners_timed_out": self._runners_timed_out,
            "runners_trail_stopped": self._runners_trail_stopped,
            "avg_extra_profit_pct": round(np.mean(self._runner_extra_profits), 4) if self._runner_extra_profits else 0,
            "median_extra_profit_pct": round(np.median(self._runner_extra_profits), 4) if self._runner_extra_profits else 0,
            "best_runner_ride_pct": round(self._runner_best_ride_pct, 4),
            "improvement_rate": round(self._runners_improved / self._runners_created * 100, 1) if self._runners_created > 0 else 0,
        }

        regime_mode_stats = {
            "candle_counts": dict(self._mode_candle_counts),
            "mode_pnl": {k: round(v, 2) for k, v in self._mode_pnl.items()},
        }

        total_fees = sum(d.total_fees for d in completed)

        return BacktestResult(
            total_return_pct=round(total_return, 2),
            max_drawdown_pct=round(max_dd, 2),
            sharpe_ratio=round(sharpe, 2),
            deals_per_day=round(n_completed / days, 2),
            avg_profit_per_deal_usd=round(np.mean(deal_pnls), 2) if deal_pnls else 0,
            avg_profit_per_deal_pct=round(np.mean(deal_pnl_pcts), 2) if deal_pnl_pcts else 0,
            avg_hold_time_hours=round(np.mean(hold_times), 2) if hold_times else 0,
            capital_utilization_pct=round(np.mean(self._utilization_samples), 2) if self._utilization_samples else 0,
            win_rate=round(wins / n_completed * 100, 1) if n_completed > 0 else 0,
            largest_single_loss=round(min(deal_pnls), 2) if deal_pnls else 0,
            total_fees_paid=round(total_fees, 2),
            total_deals_completed=n_completed,
            total_deals_open=len(self.deals),
            initial_capital=self.initial_capital,
            final_equity=round(final_equity, 2),
            trade_log=[t.to_dict() for t in self.trade_log],
            deals=[d.to_dict() for d in all_deals],
            equity_curve=[{"timestamp": s["timestamp"], "equity": round(s["equity"], 2)}
                         for s in self.equity_snapshots[::max(1, len(self.equity_snapshots)//500)]],
            profile=self.profile.name,
            symbol=self.symbol,
            timeframe=self.timeframe,
            exchange=self.exchange,
            variant=self.variant,
            compounding=self.compounding,
            runner_stats=runner_stats,
            regime_mode_stats=regime_mode_stats,
        )


# ── Smart Exit Engine (extends V3 with exit pressure scoring) ──────────

class SpotBacktestEngineV3SmartExit(SpotBacktestEngineV3):
    """V3 engine with Smart Exit scoring overlay.

    Every `smart_exit_interval` candles, computes exit pressure for active
    deals and can TIGHTEN trails, do PARTIAL/MAJOR/FULL exits based on
    technical + position context scoring.

    Does NOT modify any parent class methods — only overrides `run()` to
    inject the smart exit check, and adds new helper methods.
    """

    def __init__(
        self,
        smart_exit: bool = True,
        smart_exit_interval: int = 4,
        smart_exit_coin_id: str = "",
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.smart_exit = smart_exit
        self.smart_exit_interval = max(1, smart_exit_interval)
        self.smart_exit_coin_id = smart_exit_coin_id
        self._exit_scorer = BacktestExitScorer()

        # Smart exit tracking
        self._smart_exit_events: List[dict] = []
        self._smart_exit_triggers = 0
        self._smart_exit_pressures: List[float] = []

    def run(self, df: pd.DataFrame) -> BacktestResult:
        """Override run() to inject smart exit scoring into the candle loop."""
        if not self.smart_exit:
            return super().run(df)

        if len(df) < 100:
            logger.warning("Not enough data for backtest (%d rows)", len(df))
            return BacktestResult()

        logger.info("Computing regimes and indicators...")
        regimes = classify_regime_v2(df, self.timeframe)
        atr_pct_series = compute_atr_pct(df, 14)
        atr_abs_series = compute_atr(df, 14)
        sma50 = df["close"].rolling(50).mean()

        logger.info("Running V3+SmartExit backtest: %s %s, capital=$%.0f, profile=%s, interval=%d",
                     self.symbol, self.timeframe, self.initial_capital,
                     self.profile.name, self.smart_exit_interval)

        peak_equity = self.initial_capital

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

            exit_mode = self._get_exit_mode(regime)
            self._mode_candle_counts[exit_mode.name] = self._mode_candle_counts.get(exit_mode.name, 0) + 1

            tp_pct = self._adaptive_tp(regime, self._current_atr_pct)
            dev_pct = self._adaptive_deviation(regime, self._current_atr_pct, tp_pct)

            if self._halted:
                self._check_exits(high, low, price, ts, regime, exit_mode)
            else:
                self._check_safety_order_fills(low, price, ts, regime, dev_pct, tp_pct)
                self._check_exits(high, low, price, ts, regime, exit_mode)
                if not self.deals and regime not in BLOCKED_REGIMES:
                    self._open_deal(price, ts, regime, tp_pct)

            # ── Smart Exit scoring ──
            if self.deals and (i - 100) % self.smart_exit_interval == 0:
                self._apply_smart_exit(df, i, price, ts, regime, exit_mode)

            equity = self._equity(price)
            self.equity_snapshots.append({"timestamp": ts, "equity": equity, "cash": self.cash, "price": price})

            deployed = sum(d.capital_deployed for d in self.deals)
            self._utilization_samples.append(deployed / self.initial_capital * 100 if self.initial_capital > 0 else 0)

            if equity > peak_equity:
                peak_equity = equity
            dd = (peak_equity - equity) / peak_equity * 100
            if dd >= self.profile.max_drawdown_pct and not self._halted:
                logger.warning("Drawdown halt triggered: %.1f%% >= %.1f%%", dd, self.profile.max_drawdown_pct)
                self._halted = True

            if i % 500 == 0:
                logger.info("  [%d/%d] equity=$%.0f, deals_open=%d, completed=%d, smart_exits=%d",
                            i, len(df), equity, len(self.deals), len(self.completed_deals),
                            self._smart_exit_triggers)

        # Force-close remaining
        last_price = float(df.iloc[-1]["close"])
        last_ts = str(df.iloc[-1]["timestamp"])
        for deal in list(self.deals):
            self._force_close_deal(deal, last_price, last_ts)

        result = self._compile_results(df)
        # Attach smart exit metadata
        result.runner_stats["smart_exit_triggers"] = self._smart_exit_triggers
        result.runner_stats["smart_exit_avg_pressure"] = (
            round(np.mean(self._smart_exit_pressures), 1) if self._smart_exit_pressures else 0
        )
        result.runner_stats["smart_exit_events"] = self._smart_exit_events[:50]  # cap for JSON size
        return result

    def _apply_smart_exit(self, df: pd.DataFrame, candle_idx: int,
                          price: float, ts: str, regime: str,
                          exit_mode: ExitModeParams):
        """Score exit pressure for each active deal and act on it."""
        def _parse_ts(t):
            if isinstance(t, (int, float)) or (isinstance(t, str) and t.replace('.', '').isdigit()):
                return pd.to_datetime(float(t), unit="ms")
            return pd.to_datetime(t)

        # Minimum position age guards:
        # 1. Don't smart-exit deals younger than 3 days (let them breathe)
        # 2. Don't force-close underwater deals (only TIGHTEN allowed if losing)
        # 3. Need at least 3 completed deals before smart exit activates
        #    (system needs history to avoid killing early positions)
        MIN_DEAL_AGE_DAYS = 3.0
        MIN_COMPLETED_DEALS = 3

        completed_count = len(self.completed_deals)
        if completed_count < MIN_COMPLETED_DEALS:
            return  # Too early — let the system establish itself

        for deal in list(self.deals):
            unsold = deal.unsold_lots
            if not unsold:
                continue

            # Compute deal-level position context
            avg_entry = sum(l.buy_price * l.cost_usd for l in deal.lots) / max(deal.total_invested, 1)
            profit_pct = (price - avg_entry) / avg_entry * 100
            open_ts = _parse_ts(deal.open_time)
            current_ts = _parse_ts(ts)
            hold_days = (current_ts - open_ts).total_seconds() / 86400

            # Guard 1: Don't smart-exit young deals
            if hold_days < MIN_DEAL_AGE_DAYS:
                continue

            # Track peak price since deal open
            deal_start_idx = max(0, candle_idx - int(hold_days * (24 / {"1h": 1, "4h": 4, "1d": 24}.get(self.timeframe, 4))))
            deal_start_idx = max(100, deal_start_idx)
            peak_price = float(df.iloc[deal_start_idx:candle_idx + 1]["high"].max())

            result = self._exit_scorer.score(
                df=df, candle_idx=candle_idx,
                profit_pct=profit_pct, hold_days=hold_days,
                peak_price=peak_price, current_price=price,
                regime=regime,
                trend_direction="bullish" if self._trend_bullish else "bearish",
            )

            action = result["action"]
            pressure = result["exit_pressure"]

            if action == "HOLD":
                continue

            # Guard 2: Minimum profit for exit in non-bearish regimes.
            # DCA deals accumulate inventory over weeks; exiting a barely-profitable
            # position in a bull market destroys compounding for no reason.
            # In bearish regimes/direction: let exits happen at ANY profit level
            # (cutting losers early is the whole point of bear protection).
            MIN_EXIT_PROFIT_BULL = 2.0   # Need 2%+ profit to exit in bull/neutral
            if action in ("PARTIAL_EXIT", "MAJOR_EXIT", "FULL_EXIT"):
                bearish_regime = regime.upper() in ("DISTRIBUTION", "EXTREME", "CHOPPY")
                bearish_direction = not self._trend_bullish
                is_bearish = bearish_regime or bearish_direction
                if not is_bearish and profit_pct < MIN_EXIT_PROFIT_BULL:
                    action = "TIGHTEN"  # Don't liquidate low-profit positions in bull

            self._smart_exit_pressures.append(pressure)

            if action == "TIGHTEN":
                # Tighten trail distance on active runners
                for lot in unsold:
                    if lot.secured_sold and lot.runner and not lot.runner.is_sold:
                        lot.runner.trail_distance *= result["trail_multiplier"]
                continue

            # For PARTIAL_EXIT, MAJOR_EXIT, FULL_EXIT — sell portions at market
            sell_pct = result["partial_exit_pct"] / 100.0
            self._smart_exit_triggers += 1
            self._smart_exit_events.append({
                "deal_id": deal.deal_id, "candle": candle_idx,
                "timestamp": ts, "pressure": pressure,
                "action": action, "price": price, "profit_pct": round(profit_pct, 2),
            })

            for lot in list(unsold):
                if lot.secured_sold and lot.runner and not lot.runner.is_sold:
                    # Sell runner (partial runners not supported — sell full runner)
                    if sell_pct >= 0.5:
                        self._sell_runner(deal, lot, lot.runner, price, ts, regime,
                                         f"smart_exit_{action.lower()}", exit_mode.name)
                elif not lot.secured_sold:
                    if action == "FULL_EXIT":
                        # Sell entire lot at market
                        self._sell_secured(deal, lot, price, lot.qty, ts, regime,
                                          "smart_exit_full", exit_mode)
                    elif sell_pct > 0:
                        # Partial sell: sell sell_pct of qty, reduce lot
                        sell_qty = lot.qty * sell_pct
                        remain_qty = lot.qty - sell_qty

                        # Sell the partial amount
                        revenue = sell_qty * price
                        fee = revenue * self.maker_fee
                        net_revenue = revenue - fee
                        cost_portion = lot.cost_usd * sell_pct
                        pnl = net_revenue - cost_portion
                        self.cash += net_revenue

                        self._mode_pnl[exit_mode.name] = self._mode_pnl.get(exit_mode.name, 0) + pnl

                        self.trade_log.append(TradeLogEntry(
                            timestamp=ts, action=f"SELL_SMART({action})",
                            deal_id=deal.deal_id, lot_id=lot.lot_id,
                            price=price, qty=sell_qty, cost_usd=revenue,
                            fee=fee, pnl=pnl, regime=regime,
                            sell_reason=f"smart_exit_{action.lower()}",
                            exit_mode=exit_mode.name,
                        ))

                        # Adjust lot in-place
                        lot.qty = remain_qty
                        lot.cost_usd *= (1 - sell_pct)

            # Check if deal is complete after smart exit sells
            if deal.is_complete:
                deal.close_time = ts
                self.completed_deals.append(deal)
                self.deals.remove(deal)
