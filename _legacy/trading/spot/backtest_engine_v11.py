"""Spot DCA Backtest Engine V11 — V9 Distribution Exit + V10 Short DCA Grid.

Combines V9's distribution exit overlay with V10's real short DCA engine:
  - Uses V9's distribution scoring and exit triggers
  - Replaces V9's simplified short profit model with V10's ShortDeal/ShortLot DCA grid
  - Short grid: base order opens short, safety orders on bounces UP, TP on drops DOWN
  - Tracks short PnL and funding costs separately
  - Same re-entry logic: exit SHORT when dist_phase returns to NORMAL + spring signals
"""
import logging
from typing import Optional, List
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from .backtest_engine_v9 import SpotBacktestEngineV9
from .backtest_engine_v3 import BacktestResult, TradeLogEntry
from .distribution_scorer import DistributionPhase
from .ta_top_scorer import TATopScorer
from .fetch_eth_mcap import fetch_eth_mcap_history, interpolate_mcap_to_hourly

logger = logging.getLogger(__name__)


# ── McapGatedScorer: wraps DistributionScorer to gate EXIT on mcap ATH ──

def _resample_to_daily(df_1h: pd.DataFrame) -> pd.DataFrame:
    """Resample 1h OHLCV data to daily candles for multi-timeframe scoring."""
    df = df_1h.copy()
    df["dt"] = pd.to_datetime(df["timestamp"], unit="ms", utc=True)
    df = df.set_index("dt")
    
    daily = df.resample("1D").agg({
        "timestamp": "first",
        "open": "first",
        "high": "max",
        "low": "min",
        "close": "last",
        "volume": "sum",
    }).dropna(subset=["timestamp"]).reset_index(drop=True)
    return daily


def _resample_to_4h(df_1h: pd.DataFrame) -> pd.DataFrame:
    """Resample 1h OHLCV data to 4h candles."""
    df = df_1h.copy()
    df["dt"] = pd.to_datetime(df["timestamp"], unit="ms", utc=True)
    df = df.set_index("dt")
    
    resampled = df.resample("4h").agg({
        "timestamp": "first",
        "open": "first",
        "high": "max",
        "low": "min",
        "close": "last",
        "volume": "sum",
    }).dropna(subset=["timestamp"]).reset_index(drop=True)
    return resampled


class _McapGatedScorer:
    """Multi-timeframe proxy around DistributionScorer + TA scoring.
    
    Key insight: daily TA signals detect cycle tops that 1h misses entirely.
    This wrapper:
    1. Runs macro scorer on 1h data (as before)
    2. Runs TA scorer on DAILY resampled data (new — catches tops)
    3. Optionally also runs TA on 4h for additional confirmation
    4. Uses the HIGHEST score across all timeframes
    5. If score >= threshold AND near mcap ATH → force EXIT
    """
    
    def __init__(self, real_scorer, engine, exit_score_threshold: float):
        self._real = real_scorer
        self._ta_scorer_1h = TATopScorer()  # min_lookback=168 (default, for 1h)
        self._ta_scorer_daily = TATopScorer(min_lookback=50)  # 50 days lookback for daily
        self._ta_scorer_4h = TATopScorer(min_lookback=100)  # 100 4h-candles (~17 days)
        self._engine = engine
        self._exit_threshold = exit_score_threshold
        
        # Multi-timeframe data (set by prepare_mtf_data)
        self._daily_df = None
        self._daily_regimes = None
        self._daily_indicators_computed = False
        self._4h_df = None
        self._4h_regimes = None
        self._4h_indicators_computed = False
        
        # Timestamp → index mapping for daily/4h lookup
        self._daily_ts_to_idx = {}
        self._4h_ts_to_idx = {}
    
    def prepare_mtf_data(self, df_1h: pd.DataFrame):
        """Resample 1h data to daily and 4h, compute indicators.
        
        Called once at start of V11 run (and each chunk in chained mode).
        """
        from ..regime_detector import classify_regime_v2
        from ..indicators import compute_all as compute_all_indicators
        
        # Daily
        self._daily_df = _resample_to_daily(df_1h)
        if len(self._daily_df) > 50:
            self._daily_df = compute_all_indicators(self._daily_df)
            self._daily_regimes = classify_regime_v2(self._daily_df, "1h")
            self._daily_indicators_computed = True
            # Build timestamp lookup: map each daily timestamp to its index
            self._daily_ts_to_idx = {}
            for idx in range(len(self._daily_df)):
                ts = int(self._daily_df.iloc[idx]["timestamp"])
                self._daily_ts_to_idx[ts] = idx
            logger.info("  MTF: Prepared %d daily candles for TA scoring", len(self._daily_df))
        else:
            self._daily_indicators_computed = False
            logger.warning("  MTF: Not enough daily candles (%d), skipping daily TA", len(self._daily_df))
        
        # 4h
        self._4h_df = _resample_to_4h(df_1h)
        if len(self._4h_df) > 100:
            self._4h_df = compute_all_indicators(self._4h_df)
            self._4h_regimes = classify_regime_v2(self._4h_df, "1h")
            self._4h_indicators_computed = True
            self._4h_ts_to_idx = {}
            for idx in range(len(self._4h_df)):
                ts = int(self._4h_df.iloc[idx]["timestamp"])
                self._4h_ts_to_idx[ts] = idx
            logger.info("  MTF: Prepared %d 4h candles for TA scoring", len(self._4h_df))
        else:
            self._4h_indicators_computed = False
    
    def _find_daily_idx(self, ts_1h) -> Optional[int]:
        """Find the daily candle index corresponding to a 1h timestamp."""
        if not self._daily_indicators_computed or self._daily_df is None:
            return None
        
        # Convert 1h timestamp to day start
        ts_ms = int(ts_1h) if not isinstance(ts_1h, (int, float)) else int(ts_1h)
        dt = pd.Timestamp(ts_ms, unit="ms", tz="UTC")
        day_start = dt.normalize()
        day_start_ms = int(day_start.timestamp() * 1000)
        
        # Look up in the daily index map
        idx = self._daily_ts_to_idx.get(day_start_ms)
        if idx is not None:
            return idx
        
        # Fallback: find closest daily candle
        if len(self._daily_df) == 0:
            return None
        daily_ts = self._daily_df["timestamp"].values
        diffs = np.abs(daily_ts - ts_ms)
        closest = int(np.argmin(diffs))
        # Only use if within 24 hours
        if diffs[closest] < 86400000:
            return closest
        return None
    
    def _find_4h_idx(self, ts_1h) -> Optional[int]:
        """Find the 4h candle index corresponding to a 1h timestamp."""
        if not self._4h_indicators_computed or self._4h_df is None:
            return None
        
        ts_ms = int(ts_1h) if not isinstance(ts_1h, (int, float)) else int(ts_1h)
        
        if len(self._4h_df) == 0:
            return None
        ts_4h = self._4h_df["timestamp"].values
        diffs = np.abs(ts_4h - ts_ms)
        closest = int(np.argmin(diffs))
        if diffs[closest] < 14400000:  # Within 4 hours
            return closest
        return None
    
    def score(self, df, i, regime, fg_value, regimes):
        from .distribution_scorer import DistributionPhase
        
        # 1. Macro scorer on 1h (original)
        macro_result = self._real.score(df, i, regime, fg_value, regimes)
        
        # 2. TA scorer on 1h (for completeness, though usually weak)
        ta_1h_result = self._ta_scorer_1h.score(df, i, regime, fg_value, regimes)
        
        # Start with best of macro and 1h TA
        if ta_1h_result.score >= macro_result.score:
            best_result = ta_1h_result
            best_source = "TA_1h"
        else:
            best_result = macro_result
            best_source = "macro"
        
        # 3. TA scorer on daily (the key improvement)
        ts_1h = df.iloc[i]["timestamp"]
        daily_idx = self._find_daily_idx(ts_1h)
        if daily_idx is not None and daily_idx >= 50:
            daily_regime = self._daily_regimes.iloc[daily_idx] if daily_idx < len(self._daily_regimes) else "UNKNOWN"
            ta_daily_result = self._ta_scorer_daily.score(
                self._daily_df, daily_idx, daily_regime, fg_value, self._daily_regimes
            )
            if ta_daily_result.score > best_result.score:
                best_result = ta_daily_result
                best_source = "TA_daily"
        
        # 4. TA scorer on 4h
        idx_4h = self._find_4h_idx(ts_1h)
        if idx_4h is not None and idx_4h >= 100:
            regime_4h = self._4h_regimes.iloc[idx_4h] if idx_4h < len(self._4h_regimes) else "UNKNOWN"
            ta_4h_result = self._ta_scorer_4h.score(
                self._4h_df, idx_4h, regime_4h, fg_value, self._4h_regimes
            )
            if ta_4h_result.score > best_result.score:
                best_result = ta_4h_result
                best_source = "TA_4h"
        
        # 5. Gate EXIT on mcap ATH proximity
        if best_result.score >= self._exit_threshold:
            near_ath = self._engine._is_near_mcap_ath(df, i)
            if near_ath:
                logger.info("  🎯 V11 MTF EXIT (%s): score=%.0f >= %.0f, near mcap ATH → EXIT",
                           best_source, best_result.score, self._exit_threshold)
                best_result.phase = DistributionPhase.EXIT
            else:
                self._engine._v11_shorts_gated_by_mcap += 1
                if best_result.phase == DistributionPhase.EXIT:
                    best_result.phase = DistributionPhase.WIND_DOWN
        
        return best_result
    
    def __getattr__(self, name):
        return getattr(self._real, name)


# ── Short position tracking (copied from V10) ──────────────────────

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


class SpotBacktestEngineV11(SpotBacktestEngineV9):
    """V11: V9 Distribution Exit + V10 Real Short DCA Grid."""

    def __init__(self, **kwargs):
        # V11-specific short params (from V10) with TIGHTER STOP-LOSS
        self._v11_short_tp_pct: float = kwargs.pop("short_tp_pct", 2.5)
        self._v11_short_sl_pct: float = kwargs.pop("short_sl_pct", 5.0)  # CHANGED: 15% → 5%
        self._v11_short_max_entries: int = kwargs.pop("short_max_entries", 8)
        self._v11_short_deviation_pct: float = kwargs.pop("short_deviation_pct", 2.5)
        self._v11_funding_rate_daily: float = kwargs.pop("funding_rate_daily", 0.0003)
        
        # V11 market cap ATH gating params
        self._v11_mcap_ath_pct: float = kwargs.pop("mcap_ath_pct", 0.20)  # 20% from mcap ATH
        self._v11_use_mcap_gating: bool = kwargs.pop("use_mcap_gating", True)
        
        # V11 fast invalidation params
        self._v11_short_tight_sl_pct: float = kwargs.pop("short_tight_sl_pct", 3.0)  # Fast exit at 3%
        self._v11_enable_fast_invalidation: bool = kwargs.pop("enable_fast_invalidation", True)
        
        # V11 structural exit for 1h candles
        self._v11_structural_exit: bool = kwargs.pop("structural_exit", False)
        self._v11_dist_exit_threshold_1h: float = kwargs.pop("dist_exit_threshold_1h", 30.0)

        # Store timeframe before super().__init__ for use in scorer setup
        self._v11_timeframe = kwargs.get("timeframe", "15m")
        self._v11_exit_score_threshold: float = self._v11_dist_exit_threshold_1h if self._v11_timeframe == "1h" else kwargs.get("dist_exit_threshold", 60)

        super().__init__(**kwargs)

        # Wrap the dist scorer to gate EXIT phase on mcap ATH proximity
        self._original_dist_scorer = self._dist_scorer
        self._dist_scorer = _McapGatedScorer(
            self._original_dist_scorer, self, self._v11_exit_score_threshold
        )

        # Short engine state
        self._short_deals: List[ShortDeal] = []
        self._completed_short_deals: List[ShortDeal] = []
        self._short_deal_counter: int = 0
        self._short_allocated: float = 0.0

        # Market cap ATH tracking
        self._mcap_data: Optional[pd.DataFrame] = None
        # Known ATH prices for major coins (used as starting reference)
        _KNOWN_ATH = {
            "ETH/USDT": 4878.0, "ETH/USDC": 4878.0,
            "BTC/USDT": 73750.0, "BTC/USDC": 73750.0,
            "SOL/USDT": 260.0, "SOL/USDC": 260.0,
            "HYPE/USDC": 35.0,
        }
        _sym = kwargs.get("symbol", "")
        self._price_ath: float = _KNOWN_ATH.get(_sym, 0.0)
        if self._price_ath > 0:
            logger.info("  V11 initialized price ATH for %s: $%.0f", _sym, self._price_ath)
        
        # V11 metrics
        self._v11_short_pnl: float = 0.0
        self._v11_short_funding: float = 0.0
        self._v11_short_deals_completed: int = 0
        self._v11_shorts_gated_by_mcap: int = 0
        self._v11_fast_invalidations: int = 0

    @property
    def v11_params(self) -> dict:
        return {
            **self.v9_params,
            "short_tp_pct": self._v11_short_tp_pct,
            "short_sl_pct": self._v11_short_sl_pct,
            "short_max_entries": self._v11_short_max_entries,
            "short_deviation_pct": self._v11_short_deviation_pct,
            "funding_rate_daily": self._v11_funding_rate_daily,
            "mcap_ath_pct": self._v11_mcap_ath_pct,
            "use_mcap_gating": self._v11_use_mcap_gating,
            "short_tight_sl_pct": self._v11_short_tight_sl_pct,
            "enable_fast_invalidation": self._v11_enable_fast_invalidation,
            "structural_exit": self._v11_structural_exit,
            "dist_exit_threshold_1h": self._v11_dist_exit_threshold_1h,
        }

    def snapshot_state(self) -> dict:
        """V11: extend V9 snapshot with short engine state."""
        state = super().snapshot_state()
        state["short_deals"] = [deal.to_dict() for deal in self._short_deals]
        state["completed_short_deals"] = [deal.to_dict() for deal in self._completed_short_deals]
        state["short_deal_counter"] = self._short_deal_counter
        state["short_allocated"] = self._short_allocated
        state["price_ath"] = self._price_ath
        state["v11_short_pnl"] = self._v11_short_pnl
        state["v11_short_funding"] = self._v11_short_funding
        state["v11_short_deals_completed"] = self._v11_short_deals_completed
        state["v11_shorts_gated_by_mcap"] = self._v11_shorts_gated_by_mcap
        state["v11_fast_invalidations"] = self._v11_fast_invalidations
        state["v11_normal_count"] = getattr(self, '_v11_normal_count', 0)
        state["v11_short_cooldown"] = getattr(self, '_v11_short_cooldown', 0)
        state["v11_short_stopped_out"] = getattr(self, '_v11_short_stopped_out', False)
        return state

    def restore_state(self, state: dict):
        """V11: extend V9 restore with short engine state."""
        super().restore_state(state)
        # Restore short deals
        self._short_deals = []
        for deal_data in state.get("short_deals", []):
            deal = ShortDeal(
                deal_id=deal_data["deal_id"],
                symbol=deal_data["symbol"],
                open_time=deal_data["open_time"],
                close_time=deal_data.get("close_time"),
                funding_cost=deal_data.get("funding_cost", 0.0),
            )
            for lot_data in deal_data["lots"]:
                lot = ShortLot(
                    lot_id=lot_data["lot_id"],
                    entry_price=lot_data["entry_price"],
                    qty=lot_data["qty"],
                    cost_usd=lot_data["cost_usd"],
                    entry_time=lot_data["entry_time"],
                    tp_target=lot_data.get("tp_target", 0.0),
                    sl_target=lot_data.get("sl_target", 0.0),
                    sell_price=lot_data.get("sell_price"),
                    sell_time=lot_data.get("sell_time"),
                    pnl=lot_data.get("pnl", 0.0),
                    sell_reason=lot_data.get("sell_reason", ""),
                )
                deal.lots.append(lot)
            self._short_deals.append(deal)

        # Restore completed short deals
        self._completed_short_deals = []
        for deal_data in state.get("completed_short_deals", []):
            deal = ShortDeal(
                deal_id=deal_data["deal_id"],
                symbol=deal_data["symbol"],
                open_time=deal_data["open_time"],
                close_time=deal_data.get("close_time"),
                funding_cost=deal_data.get("funding_cost", 0.0),
            )
            for lot_data in deal_data["lots"]:
                lot = ShortLot(
                    lot_id=lot_data["lot_id"],
                    entry_price=lot_data["entry_price"],
                    qty=lot_data["qty"],
                    cost_usd=lot_data["cost_usd"],
                    entry_time=lot_data["entry_time"],
                    tp_target=lot_data.get("tp_target", 0.0),
                    sl_target=lot_data.get("sl_target", 0.0),
                    sell_price=lot_data.get("sell_price"),
                    sell_time=lot_data.get("sell_time"),
                    pnl=lot_data.get("pnl", 0.0),
                    sell_reason=lot_data.get("sell_reason", ""),
                )
                deal.lots.append(lot)
            self._completed_short_deals.append(deal)

        self._short_deal_counter = state.get("short_deal_counter", 0)
        self._short_allocated = state.get("short_allocated", 0.0)
        self._price_ath = state.get("price_ath", 0.0)
        self._v11_short_pnl = state.get("v11_short_pnl", 0.0)
        self._v11_short_funding = state.get("v11_short_funding", 0.0)
        self._v11_short_deals_completed = state.get("v11_short_deals_completed", 0)
        self._v11_shorts_gated_by_mcap = state.get("v11_shorts_gated_by_mcap", 0)
        self._v11_fast_invalidations = state.get("v11_fast_invalidations", 0)
        self._v11_normal_count = state.get("v11_normal_count", 0)
        self._v11_short_cooldown = state.get("v11_short_cooldown", 0)
        self._v11_short_stopped_out = state.get("v11_short_stopped_out", False)

    # ── Market cap ATH tracking and gating methods ─────────────────

    def _load_mcap_data(self, df: pd.DataFrame):
        """Load and interpolate market cap data for the backtest period."""
        try:
            if self.symbol == "ETH/USDT":
                # Fetch ETH market cap data
                mcap_df = fetch_eth_mcap_history()
                if not mcap_df.empty:
                    self._mcap_data = interpolate_mcap_to_hourly(mcap_df, df)
                    logger.info(f"Loaded {len(mcap_df)} days of ETH market cap data")
                else:
                    logger.warning("Failed to load ETH market cap data, falling back to price-based ATH")
                    self._mcap_data = None
            else:
                # For non-ETH symbols, use price-based ATH only
                logger.info(f"Using price-based ATH tracking for {self.symbol}")
                self._mcap_data = None
        except Exception as e:
            logger.warning(f"Failed to load market cap data: {e}, falling back to price-based ATH")
            self._mcap_data = None

    def _is_near_mcap_ath(self, df: pd.DataFrame, i: int) -> bool:
        """Check if current price is near mcap ATH (used by _McapGatedScorer)."""
        if not self._v11_use_mcap_gating:
            return True  # If gating disabled, always allow
        price = float(df.iloc[i]["close"])
        ts = str(df.iloc[i]["timestamp"])
        return self._check_mcap_ath_gate(price, ts)

    def _check_mcap_ath_gate(self, price: float, ts: str) -> bool:
        """Check if current conditions allow SHORT entry based on market cap ATH proximity."""
        # Update price-based ATH
        if price > self._price_ath:
            self._price_ath = price
        
        # If we have market cap data, use it
        if self._mcap_data is not None:
            try:
                # Find the market cap data for current timestamp
                current_mcap_data = self._mcap_data[self._mcap_data['timestamp'] == int(pd.Timestamp(ts).timestamp() * 1000)]
                if not current_mcap_data.empty:
                    mcap_ath_pct = current_mcap_data['mcap_ath_pct'].iloc[0]
                    # Allow SHORT if within threshold % of market cap ATH
                    return mcap_ath_pct <= (self._v11_mcap_ath_pct * 100)
                else:
                    logger.debug(f"No mcap data found for timestamp {ts}")
            except Exception as e:
                logger.debug(f"Error checking mcap data: {e}")
        
        # Fallback to price-based ATH gating
        if self._price_ath > 0:
            price_ath_pct = (self._price_ath - price) / self._price_ath
            return price_ath_pct <= self._v11_mcap_ath_pct
        
        # If no ATH data available, allow (conservative fallback)
        return True

    def _check_fast_invalidation(self, high: float, low: float, price: float, ts: str, 
                                regime: str, dist_result) -> bool:
        """Check for fast invalidation signals while in SHORT mode."""
        if not self._v11_enable_fast_invalidation or not self._short_deals:
            return False
            
        invalidation_reason = None
        
        for deal in self._short_deals:
            if deal.is_complete:
                continue
                
            avg_entry = deal.avg_entry
            if avg_entry <= 0:
                continue
                
            # a) Price breaks above SHORT entry price → invalidate
            if high > avg_entry:
                invalidation_reason = "price_break_above_entry"
                break
                
            # b) New market cap ATH hit while SHORT → invalidate (if mcap data available)
            if self._mcap_data is not None:
                try:
                    current_mcap_data = self._mcap_data[self._mcap_data['timestamp'] == int(pd.Timestamp(ts).timestamp() * 1000)]
                    if not current_mcap_data.empty:
                        mcap_ath_pct = current_mcap_data['mcap_ath_pct'].iloc[0]
                        if mcap_ath_pct <= 0.01:  # Within 0.01% of new ATH
                            invalidation_reason = "new_mcap_ath"
                            break
                except:
                    pass
                    
            # c) Regime flips to TRENDING with bullish direction → invalidate
            if regime == "TRENDING" and hasattr(self, '_current_regime'):
                if self._current_regime != "TRENDING":  # Just flipped to trending
                    # Check if bullish (simplified heuristic: price above entry)
                    if price > avg_entry:
                        invalidation_reason = "trending_bullish_flip"
                        break
                        
            # d) Short position loss exceeds tight SL → invalidate
            unrealized_loss_pct = max(0, (price - avg_entry) / avg_entry * 100)
            if unrealized_loss_pct >= self._v11_short_tight_sl_pct:
                invalidation_reason = "tight_stop_loss"
                break
        
        if invalidation_reason:
            logger.info(f"  ⚡ V11 FAST INVALIDATION: {invalidation_reason}")
            self._close_all_shorts(price, ts, f"fast_invalidation_{invalidation_reason}")
            self._v11_fast_invalidations += 1
            # Return to SPOT mode immediately
            if self._v9_cash_mode:
                self._v9_cash_mode = False
                self._v9_exit_price = None
                self._v9_last_short_check_price = None
                logger.info("  🔄 V11 EXITED CASH MODE via fast invalidation")
            return True
            
        return False

    # ── Short engine methods (adapted from V10) ─────────────────────

    def _open_short(self, price: float, ts: str):
        """Open a new short deal when entering cash mode with market cap ATH gating."""
        # Market cap ATH gating check
        if self._v11_use_mcap_gating and not self._check_mcap_ath_gate(price, ts):
            self._v11_shorts_gated_by_mcap += 1
            logger.info("  🚫 V11 SHORT GATED: price not near mcap ATH")
            return
            
        # Use 50% of available cash for short allocation
        alloc = self.cash * 0.5
        if alloc < 10.0:
            return

        self._short_deal_counter += 1
        base_cost = min(alloc * 0.3, self.cash)  # First entry = 30% of allocation
        if base_cost < 5.0:
            return

        qty = base_cost / price
        tp_target = price * (1 - self._v11_short_tp_pct / 100)
        sl_target = price * (1 + self._v11_short_sl_pct / 100)

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
        logger.info("  📉 V11 SHORT OPEN: $%.0f at $%.2f, TP=$%.2f, SL=$%.2f",
                     base_cost, price, tp_target, sl_target)

    def _process_short_deals(self, high: float, low: float, price: float, ts: str):
        """Check short safety orders, exits, and funding costs."""
        self._check_short_safety_orders(high, price, ts)
        self._check_short_exits(low, high, price, ts)
        self._apply_funding_costs()

    def _check_short_safety_orders(self, high: float, price: float, ts: str):
        """Add to short position on bounces UP (inverted SO logic)."""
        for deal in self._short_deals:
            if deal.is_complete:
                continue
            if len(deal.lots) >= self._v11_short_max_entries:
                continue

            avg = deal.avg_entry
            if avg <= 0:
                continue

            next_so = len(deal.lots)
            # Trigger on bounce UP above avg entry + deviation
            trigger = avg * (1 + self._v11_short_deviation_pct * next_so / 100)

            if high >= trigger:
                so_cost = min(self.cash * 0.2, self.cash)
                if so_cost < 5.0:
                    continue

                qty = so_cost / trigger
                tp_target = trigger * (1 - self._v11_short_tp_pct / 100)
                sl_target = trigger * (1 + self._v11_short_sl_pct / 100)

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
                logger.info("  📉 V11 SHORT SO #%d: $%.0f at $%.2f (bounce from $%.2f)",
                             next_so, so_cost, trigger, avg)

    def _check_short_exits(self, low: float, high: float, price: float, ts: str):
        """Check short TP (price drops) and SL (price rises)."""
        for deal in list(self._short_deals):
            if deal.is_complete:
                continue

            avg = deal.avg_entry
            total_qty = deal.total_qty

            # Take profit: price dropped below avg - TP%
            tp_price = avg * (1 - self._v11_short_tp_pct / 100)
            if low <= tp_price and total_qty > 0:
                self._close_short_deal(deal, tp_price, ts, "short_tp")
                continue

            # Stop loss: price above avg + SL%
            sl_price = avg * (1 + self._v11_short_sl_pct / 100)
            if high >= sl_price and total_qty > 0:
                self._close_short_deal(deal, sl_price, ts, "short_sl")
                continue

    def _close_short_deal(self, deal: ShortDeal, close_price: float, ts: str, reason: str):
        """Close all lots in a short deal."""
        total_pnl = 0.0
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
            self._v11_short_pnl += pnl
            total_pnl += pnl

            self.trade_log.append(TradeLogEntry(
                timestamp=ts, action="SHORT_CLOSE", deal_id=deal.deal_id,
                lot_id=lot.lot_id, price=close_price, qty=lot.qty,
                cost_usd=lot.cost_usd, fee=0.0, pnl=pnl,
                regime=self._current_regime, sell_reason=reason,
            ))

        deal.close_time = ts
        self._completed_short_deals.append(deal)
        self._short_deals.remove(deal)
        self._v11_short_deals_completed += 1
        logger.info("  📈 V11 SHORT CLOSE (%s): deal_pnl=$%.2f (after funding=$%.2f)",
                     reason, total_pnl, deal.total_pnl)

    def _close_all_shorts(self, price: float, ts: str, reason: str = "phase_exit"):
        """Close all short deals."""
        for deal in list(self._short_deals):
            self._close_short_deal(deal, price, ts, reason)

    def _apply_funding_costs(self):
        """Apply estimated funding costs to open short positions."""
        if not self._short_deals:
            return
            
        # Determine funding rate per candle based on timeframe
        if self.timeframe == "15m":
            rate_per_candle = self._v11_funding_rate_daily / 96.0  # 96 candles per day
        elif self.timeframe == "1h":
            rate_per_candle = self._v11_funding_rate_daily / 24.0  # 24 candles per day
        else:
            rate_per_candle = self._v11_funding_rate_daily / 96.0  # default to 15m

        for deal in self._short_deals:
            margin = deal.total_margin
            cost = margin * rate_per_candle
            if cost > self.cash:
                cost = max(0, self.cash * 0.01)  # cap at 1% of remaining cash
            if cost > 0:
                deal.funding_cost += cost
                self._v11_short_funding += cost
                self.cash -= cost

    def _check_structural_exit(self, df: pd.DataFrame, i: int, price: float) -> bool:
        """Check for structural exit signals (death cross + decline > 15%)."""
        if not self._v11_structural_exit:
            return False
            
        if i < 500:  # Need enough data for lookback
            return False
            
        # Check for death cross (50 SMA < 200 SMA)
        sma50 = df["close"].rolling(50).mean()
        sma200 = df["close"].rolling(200).mean()
        
        if i < 200 or pd.isna(sma50.iloc[i]) or pd.isna(sma200.iloc[i]):
            return False
            
        death_cross = sma50.iloc[i] < sma200.iloc[i]
        
        if not death_cross:
            return False
            
        # Check for > 15% decline from local peak in last 500 candles
        lookback_start = max(0, i - 500)
        recent_high = df["high"].iloc[lookback_start:i+1].max()
        decline_pct = (recent_high - price) / recent_high * 100
        
        # Simple bearish regime check (price below both SMAs)
        bearish_regime = price < sma50.iloc[i] and price < sma200.iloc[i]
        
        return death_cross and decline_pct > 15.0 and bearish_regime

    def _get_effective_exit_threshold(self, df: pd.DataFrame, i: int, dist_score: float, price: float) -> bool:
        """Get effective exit threshold based on timeframe and structural signals.
        
        Logic: dist_score must meet threshold. Structural signals (if enabled) can
        LOWER the required threshold, not bypass the score entirely. This means
        distribution scoring is always the primary trigger.
        """
        if self.timeframe == "1h":
            threshold = self._v11_dist_exit_threshold_1h
        else:
            threshold = self._v9_exit_threshold
        
        # Structural signals lower the bar by 30% (e.g. threshold 20 -> 14)
        if self._v11_structural_exit and self._check_structural_exit(df, i, price):
            threshold *= 0.7
            if dist_score >= threshold:
                logger.info("  📉 STRUCTURAL BOOST: dist_score=%.0f >= lowered_threshold=%.0f", dist_score, threshold)
        
        return dist_score >= threshold

    # ── Override V9's short profit simulation ──────────────────────

    def _simulate_short_profit(self, current_price: float):
        """V11: Hook called by V9 every candle in cash mode.
        
        Uses instance attrs set by V9: _current_high, _current_low, _current_ts, _current_price,
        plus indicator attrs: _cur_vol, _cur_vol_avg, _cur_stoch_k/d, _cur_fg, _cur_adx/_prev,
        _cur_bbw/_prev/_med for spring scoring.
        
        Lifecycle:
        1. On cash mode entry → open ONE short position
        2. Process short DCA grid (SOs, TPs, funding) + fast invalidation
        3. After short TP → cooldown 24 candles, then open new short (price may keep falling)
        4. After short SL → NO reopen (distribution thesis invalidated, wait for spring re-entry)
        5. Re-entry: spring scorer fires (oversold + volume + compression) → close shorts, resume DCA
        """
        high = getattr(self, '_current_high', current_price)
        low = getattr(self, '_current_low', current_price)
        ts = getattr(self, '_current_ts', '0')
        regime = getattr(self, '_current_regime', 'UNKNOWN')
        
        # Initialize tracking state
        if not hasattr(self, '_v11_short_cooldown'):
            self._v11_short_cooldown = 0  # candles to wait before opening new short
        if not hasattr(self, '_v11_short_stopped_out'):
            self._v11_short_stopped_out = False  # SL hit = don't reopen
        if not hasattr(self, '_v11_normal_count'):
            self._v11_normal_count = 0
        
        # ── Fast invalidation check (before processing) ──
        if self._short_deals and self._v11_enable_fast_invalidation:
            if self._check_fast_invalidation(high, low, current_price, ts, regime, None):
                # Fast invalidation closed shorts and exited cash mode
                return
        
        # ── Open initial short on cash mode entry ──
        if not self._short_deals and self._v9_exit_price:
            if self._v11_short_stopped_out:
                pass  # SL was hit — don't reopen, wait for spring re-entry
            elif self._v11_short_cooldown > 0:
                self._v11_short_cooldown -= 1  # Cooling down after TP
            else:
                self._open_short(current_price, ts)
                if self._short_deals:  # Only log if not gated
                    logger.info("  📉 V11 OPENED SHORT at $%.0f", current_price)
        
        # ── Process existing short positions ──
        shorts_before = len(self._short_deals)
        if self._short_deals:
            self._process_short_deals(high, low, current_price, ts)
        
        # Detect if a short just closed (TP or SL)
        if shorts_before > 0 and not self._short_deals:
            # Check the last completed deal's close reason
            if self._completed_short_deals:
                last = self._completed_short_deals[-1]
                last_reason = last.lots[-1].sell_reason if last.lots else ""
                if "sl" in last_reason or "stop" in last_reason or "invalidation" in last_reason:
                    self._v11_short_stopped_out = True
                    logger.info("  ⛔ V11 SHORT STOPPED OUT — no more shorts this cycle")
                else:
                    # TP hit — cooldown then reopen
                    self._v11_short_cooldown = 24  # 24 candles (24h on 1h TF)
                    logger.info("  ⏳ V11 SHORT TP HIT — cooldown 24 candles before next short")
        
        # ── Spring-scored re-entry ──
        # Compute spring score using indicator values stored by V9
        spring_score = self._compute_spring_score(
            getattr(self, '_cur_vol', 0.0),
            getattr(self, '_cur_vol_avg', 1.0),
            getattr(self, '_cur_stoch_k', float('nan')),
            getattr(self, '_cur_stoch_d', float('nan')),
            getattr(self, '_cur_fg', 0.0),
            getattr(self, '_cur_adx', float('nan')),
            getattr(self, '_cur_adx_prev', float('nan')),
            getattr(self, '_cur_bbw', 0.0),
            getattr(self, '_cur_bbw_prev', float('nan')),
            getattr(self, '_cur_bbw_med', 0.0),
        )
        self._spring_score = spring_score
        
        # Log spring score periodically (every 24 candles) for diagnostics
        if not hasattr(self, '_v11_spring_diag_count'):
            self._v11_spring_diag_count = 0
        self._v11_spring_diag_count += 1
        if self._v11_spring_diag_count % 24 == 0:
            price_vs_exit = (current_price / self._v9_exit_price * 100) if self._v9_exit_price else 0
            logger.info("  📊 CASH DIAG: spring=%.0f (need %.0f), price=$%.0f (%.0f%% of exit), shorts=%d, cooldown=%d, stopped=%s",
                       spring_score, self._v8_spring_score_threshold, current_price, price_vs_exit,
                       len(self._short_deals), self._v11_short_cooldown, self._v11_short_stopped_out)
        
        # Two re-entry paths:
        # (A) Spring scorer fires: oversold conditions detected → immediate re-entry
        #     Requires price below exit price (confirmed some decline happened)
        if (spring_score >= self._v8_spring_score_threshold 
                and self._v9_exit_price 
                and current_price < self._v9_exit_price * 0.95):
            self._close_all_shorts(current_price, ts, "spring_reentry")
            self._v9_cash_mode = False
            self._v9_exit_price = None
            self._v11_normal_count = 0
            self._v11_short_cooldown = 0
            self._v11_short_stopped_out = False
            logger.info("  🌱 V11 SPRING RE-ENTRY: spring_score=%.0f, price=$%.0f, short_pnl=$%.0f, cash=$%.0f",
                        spring_score, current_price, self._v11_short_pnl, self.cash)
            return
        
        # (B) Extended decline fallback: price 15%+ below exit for 168 candles (1 week on 1h)
        #     Catches cases where spring scorer doesn't fire but markdown is clearly over
        if self._v9_exit_price and current_price < self._v9_exit_price * 0.85:
            self._v11_normal_count += 1
        else:
            self._v11_normal_count = 0
        
        if self._v11_normal_count >= 168:
            self._close_all_shorts(current_price, ts, "reentry_extended_decline")
            self._v9_cash_mode = False
            self._v9_exit_price = None
            self._v11_normal_count = 0
            self._v11_short_cooldown = 0
            self._v11_short_stopped_out = False
            logger.info("  🔄 V11 FALLBACK RE-ENTRY: price=$%.0f, 168h below 85%% of exit, short_pnl=$%.0f, cash=$%.0f",
                        current_price, self._v11_short_pnl, self.cash)

    # ── Override V9's cash mode handling ───────────────────────────

    def _handle_cash_mode(self, df: pd.DataFrame, i: int, row: pd.Series, 
                         high: float, low: float, price: float, ts: str,
                         vol: pd.Series, vol_avg: pd.Series, stoch: dict, 
                         bbw: pd.Series, bbw_median: pd.Series, adx_series: pd.Series, 
                         fg_value: float, dist_result) -> bool:
        """V11: Handle cash mode with real short DCA grid instead of profit simulation."""
        if not self._v9_cash_mode:
            return False
            
        # Check for fast invalidation signals first
        regime = getattr(self, '_current_regime', 'SIDEWAYS')
        if self._check_fast_invalidation(high, low, price, ts, regime, dist_result):
            return False  # Exited cash mode via fast invalidation
            
        # Process existing short positions
        self._process_short_deals(high, low, price, ts)

        # Check for spring-based re-entry
        if dist_result.phase == DistributionPhase.NORMAL:
            # Score dropped below reentry threshold AND spring signals
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
                # Exit cash mode, close shorts, deploy spring buys
                self._close_all_shorts(price, ts, "spring_reentry")
                self._v9_cash_mode = False
                self._v9_exit_price = None
                self._v9_last_short_check_price = None
                logger.info("  🔄 V11 EXIT CASH MODE (spring): score=%.0f, cash=$%.0f, short_pnl=$%.0f",
                             self._spring_score, self.cash, self._v11_short_pnl)
                return False  # Continue to normal trading logic
        
        return True  # Still in cash mode, skip normal trading

    # ── Override V9's distribution exit check ──────────────────────

    def _check_distribution_exit(self, df: pd.DataFrame, i: int, dist_result, price: float, ts: str) -> bool:
        """V11: Check for distribution exit with structural signals support."""
        exit_triggered = self._get_effective_exit_threshold(df, i, dist_result.score, price)
        
        if exit_triggered:
            # Force close everything
            if self.deals:
                logger.info("  🚨 V11 DISTRIBUTION EXIT: score=%.0f, force-closing %d deals",
                             dist_result.score, len(self.deals))
                for deal in list(self.deals):
                    self._force_close_deal(deal, price, ts)
                self._v9_force_exits += 1

            # Enter cash mode and open short position
            if not self._v9_cash_mode:
                self._v9_cash_mode = True
                self._v9_exit_price = price
                self._v9_last_short_check_price = price
                self._open_short(price, ts)
                
            return True  # Exit triggered
        
        return False  # No exit

    def accumulate_1h_data(self, df: pd.DataFrame):
        """Accumulate 1h candle data across chunks for MTF scoring.
        
        Called by the chained runner before each chunk to build up
        the full historical dataset that the daily scorer needs.
        """
        if not hasattr(self, '_accumulated_1h'):
            self._accumulated_1h = df.copy()
        else:
            self._accumulated_1h = pd.concat([self._accumulated_1h, df], ignore_index=True)
            self._accumulated_1h = self._accumulated_1h.drop_duplicates(
                subset=["timestamp"]
            ).sort_values("timestamp").reset_index(drop=True)
    
    def _run_main_loop(self, df: pd.DataFrame):
        """Override V9's main loop entry to prepare multi-timeframe data first."""
        # Accumulate current chunk's 1h data
        self.accumulate_1h_data(df)
        
        # Prepare MTF data using ALL accumulated 1h data (not just this chunk)
        if hasattr(self._dist_scorer, 'prepare_mtf_data'):
            self._dist_scorer.prepare_mtf_data(self._accumulated_1h)
        
        # Load market cap data for ATH gating (once per chunk)
        if self._v11_use_mcap_gating and self._mcap_data is None:
            self._load_mcap_data(df)
        
        # Delegate to V9's main loop
        super()._run_main_loop(df)

    def run(self, df: pd.DataFrame) -> BacktestResult:
        """Run V11 backtest with real short DCA grid + mcap ATH gating + MTF scoring."""
        if len(df) < 100:
            logger.warning("Not enough data (%d rows)", len(df))
            return BacktestResult()

        logger.info("Running V11 backtest (MTF scorer + short grid + mcap ATH gating): %s %s, $%.0f, "
                     "exit_thresh=%.0f, short_sl=%.1f%%, mcap_gating=%s, fast_invalidation=%s",
                     self.symbol, self.timeframe, self.initial_capital,
                     self._v9_exit_threshold if not self._v11_structural_exit or self.timeframe != "1h" else self._v11_dist_exit_threshold_1h,
                     self._v11_short_sl_pct, self._v11_use_mcap_gating, self._v11_enable_fast_invalidation)

        # Let V9 handle most of the logic — _run_main_loop override adds MTF prep
        result = super().run(df)

        # Force-close remaining shorts at the end
        if self._short_deals:
            last_price = float(df.iloc[-1]["close"])
            last_ts = str(df.iloc[-1]["timestamp"])
            self._close_all_shorts(last_price, last_ts, "backtest_end")

        # Update result metadata
        result.variant = "v11_dist_exit_short_grid"

        if hasattr(result, 'extra') and result.extra:
            result.extra.update({
                "v11_params": self.v11_params,
                "v11_short_pnl": round(self._v11_short_pnl, 2),
                "v11_short_funding": round(self._v11_short_funding, 2),
                "v11_short_deals_completed": self._v11_short_deals_completed,
                "v11_shorts_gated_by_mcap": self._v11_shorts_gated_by_mcap,
                "v11_fast_invalidations": self._v11_fast_invalidations,
                "v11_mcap_data_available": self._mcap_data is not None,
            })
        else:
            result.extra = {
                "v11_params": self.v11_params,
                "v8_spring_buys": getattr(self, '_v8_spring_buys', 0),
                "v8_phase_candles": getattr(self, '_v8_phase_candles', {}),
                "v9_dist_phase_candles": getattr(self, '_v9_phase_candles', {}),
                "v9_force_exits": getattr(self, '_v9_force_exits', 0),
                "v11_short_pnl": round(self._v11_short_pnl, 2),
                "v11_short_funding": round(self._v11_short_funding, 2),
                "v11_short_deals_completed": self._v11_short_deals_completed,
                "v11_shorts_gated_by_mcap": self._v11_shorts_gated_by_mcap,
                "v11_fast_invalidations": self._v11_fast_invalidations,
                "v11_mcap_data_available": self._mcap_data is not None,
            }

        return result