"""Martingale DCA backtesting engine with bidirectional support."""
import numpy as np
import pandas as pd
from dataclasses import dataclass, field
from typing import List, Optional
from .config import MartingaleConfig
from .regime_detector import classify_regime, is_martingale_friendly


@dataclass
class Order:
    price: float
    size_usd: float
    qty: float
    fee: float
    timestamp: pd.Timestamp


@dataclass
class Deal:
    symbol: str
    base_order: Order
    direction: str = "LONG"  # "LONG" or "SHORT"
    safety_orders: List[Order] = field(default_factory=list)
    close_price: Optional[float] = None
    close_time: Optional[pd.Timestamp] = None
    close_fee: float = 0.0
    trailing_high: float = 0.0
    trailing_low: float = float("inf")

    @property
    def is_open(self) -> bool:
        return self.close_price is None

    @property
    def total_invested(self) -> float:
        t = self.base_order.size_usd
        for so in self.safety_orders:
            t += so.size_usd
        return t

    @property
    def total_qty(self) -> float:
        t = self.base_order.qty
        for so in self.safety_orders:
            t += so.qty
        return t

    @property
    def avg_entry(self) -> float:
        return self.total_invested / self.total_qty if self.total_qty > 0 else 0

    @property
    def total_fees(self) -> float:
        f = self.base_order.fee
        for so in self.safety_orders:
            f += so.fee
        return f + self.close_fee

    @property
    def pnl(self) -> float:
        if self.close_price is None:
            return 0.0
        if self.direction == "LONG":
            revenue = self.total_qty * self.close_price - self.close_fee
            return revenue - self.total_invested - self.total_fees + self.close_fee
        else:  # SHORT
            # Sold at avg_entry, bought back at close_price
            # Profit = sold_value - bought_back_value - fees
            sold_value = self.total_invested - (self.total_fees - self.close_fee)  # net USD from selling
            cover_cost = self.total_qty * self.close_price + self.close_fee
            return sold_value - cover_cost

    @property
    def pnl_pct(self) -> float:
        return self.pnl / self.total_invested * 100 if self.total_invested > 0 else 0

    @property
    def so_count(self) -> int:
        return len(self.safety_orders)

    @property
    def entry_time(self) -> pd.Timestamp:
        return self.base_order.timestamp

    @property
    def tp_price(self) -> float:
        """Direction-aware take-profit price (needs config tp%)."""
        return 0.0  # Computed in bot logic

    @property
    def max_deal_drawdown(self) -> float:
        return 0.0


@dataclass
class BacktestResult:
    closed_deals: List[Deal]
    open_deals: List[Deal]
    equity_curve: pd.DataFrame
    regimes: pd.Series
    config: MartingaleConfig
    symbol: str
    timeframe: str

    @property
    def total_trades(self) -> int:
        return len(self.closed_deals)

    @property
    def win_rate(self) -> float:
        if not self.closed_deals:
            return 0
        wins = sum(1 for d in self.closed_deals if d.pnl > 0)
        return wins / len(self.closed_deals) * 100

    @property
    def total_profit(self) -> float:
        return sum(d.pnl for d in self.closed_deals)

    @property
    def total_profit_pct(self) -> float:
        return self.total_profit / self.config.initial_capital * 100

    @property
    def max_drawdown(self) -> float:
        eq = self.equity_curve["equity"].values
        peak = np.maximum.accumulate(eq)
        dd = (eq - peak) / peak * 100
        return float(dd.min()) if len(dd) > 0 else 0

    @property
    def profit_factor(self) -> float:
        gross_profit = sum(d.pnl for d in self.closed_deals if d.pnl > 0)
        gross_loss = abs(sum(d.pnl for d in self.closed_deals if d.pnl < 0))
        return gross_profit / gross_loss if gross_loss > 0 else float("inf")

    @property
    def sharpe_ratio(self) -> float:
        if len(self.equity_curve) < 2:
            return 0
        returns = self.equity_curve["equity"].pct_change().dropna()
        if returns.std() == 0:
            return 0
        return float(returns.mean() / returns.std() * np.sqrt(252 * 24))

    @property
    def max_concurrent_capital(self) -> float:
        if "capital_used" in self.equity_curve.columns:
            return float(self.equity_curve["capital_used"].max())
        return 0

    @property
    def direction_stats(self) -> dict:
        long_deals = [d for d in self.closed_deals if d.direction == "LONG"]
        short_deals = [d for d in self.closed_deals if d.direction == "SHORT"]
        return {
            "long_count": len(long_deals),
            "short_count": len(short_deals),
            "long_pnl": sum(d.pnl for d in long_deals),
            "short_pnl": sum(d.pnl for d in short_deals),
            "long_win_rate": (sum(1 for d in long_deals if d.pnl > 0) / len(long_deals) * 100) if long_deals else 0,
            "short_win_rate": (sum(1 for d in short_deals if d.pnl > 0) / len(short_deals) * 100) if short_deals else 0,
        }

    def summary_dict(self) -> dict:
        return {
            "symbol": self.symbol,
            "timeframe": self.timeframe,
            "total_trades": self.total_trades,
            "win_rate": round(self.win_rate, 1),
            "total_profit": round(self.total_profit, 2),
            "total_profit_pct": round(self.total_profit_pct, 2),
            "max_drawdown_pct": round(self.max_drawdown, 2),
            "profit_factor": round(self.profit_factor, 2),
            "sharpe_ratio": round(self.sharpe_ratio, 2),
            "max_concurrent_capital": round(self.max_concurrent_capital, 2),
            "avg_so_per_deal": round(np.mean([d.so_count for d in self.closed_deals]), 1) if self.closed_deals else 0,
        }


class MartingaleBot:
    def __init__(self, config: MartingaleConfig, bidirectional: bool = False):
        self.cfg = config
        self.bidirectional = bidirectional

    def _fill_price(self, price: float, side: str) -> float:
        slip = price * self.cfg.slippage_pct / 100
        return price + slip if side == "buy" else price - slip

    def _fee(self, size_usd: float) -> float:
        return size_usd * self.cfg.fee_pct / 100

    def _make_order(self, price: float, size_usd: float, ts: pd.Timestamp, side: str = "buy") -> Order:
        fill = self._fill_price(price, side)
        fee = self._fee(size_usd)
        qty = (size_usd - fee) / fill
        return Order(price=fill, size_usd=size_usd, qty=qty, fee=fee, timestamp=ts)

    def _decide_direction(self, df: pd.DataFrame, i: int, regime: str) -> str:
        """Decide LONG or SHORT with trend confirmation to avoid shorting uptrends."""
        if not self.bidirectional:
            return "LONG"

        if i < 50:
            return "LONG"

        # --- Bollinger Band position ---
        closes = df["close"].iloc[max(0, i - 50):i + 1].values
        bb_closes = closes[-21:]  # last 20+1 for BB
        sma = np.mean(bb_closes)
        std = np.std(bb_closes)
        if std == 0:
            return "LONG"

        upper = sma + 2 * std
        lower = sma - 2 * std
        price = closes[-1]
        band_range = upper - lower
        if band_range == 0:
            return "LONG"
        position = (price - lower) / band_range

        # --- Trend indicators ---
        # EMA20 and EMA50 (use pandas for accuracy)
        close_series = df["close"].iloc[:i + 1]
        ema20 = close_series.ewm(span=20, adjust=False).mean().iloc[-1]
        ema50 = close_series.ewm(span=50, adjust=False).mean().iloc[-1]

        # EMA50 slope: pct change per candle over last 5 candles
        ema50_series = close_series.ewm(span=50, adjust=False).mean()
        ema50_now = ema50_series.iloc[-1]
        ema50_prev = ema50_series.iloc[-6] if len(ema50_series) >= 6 else ema50_now
        ema50_slope_pct = ((ema50_now - ema50_prev) / ema50_prev * 100 / 5) if ema50_prev != 0 else 0

        golden_cross = ema20 > ema50

        # RSI 14
        delta = close_series.diff()
        gain = delta.clip(lower=0).rolling(14).mean().iloc[-1]
        loss = (-delta.clip(upper=0)).rolling(14).mean().iloc[-1]
        rs = gain / loss if loss != 0 else 100
        rsi = 100 - (100 / (1 + rs))

        # --- Strong uptrend override ---
        if ema50_slope_pct > 0.1:
            return "LONG"

        # --- Never short during ACCUMULATION ---
        if regime == "ACCUMULATION":
            return "LONG"

        # --- SHORT criteria: ALL must be true ---
        regime_ok = regime in ("DISTRIBUTION", "CHOPPY", "RANGING", "MARKDOWN")
        band_ok = position > 0.8
        slope_ok = ema50_slope_pct <= 0.02
        rsi_ok = rsi < 65
        no_golden = not golden_cross

        if regime_ok and band_ok and slope_ok and rsi_ok and no_golden:
            return "SHORT"

        # --- LONG criteria (permissive) ---
        if position <= 0.5 or regime == "ACCUMULATION":
            return "LONG"

        # Default LONG
        return "LONG"

    def run(self, df: pd.DataFrame, symbol: str, timeframe: str, precomputed_regimes: pd.Series = None, friendly_fn=None) -> BacktestResult:
        regimes = precomputed_regimes if precomputed_regimes is not None else classify_regime(df, timeframe)
        if friendly_fn is None:
            friendly_fn = is_martingale_friendly
        open_deals: List[Deal] = []
        closed_deals: List[Deal] = []
        equity = self.cfg.initial_capital
        eq_records = []

        for i in range(len(df)):
            row = df.iloc[i]
            ts = row["timestamp"]
            high, low, close = row["high"], row["low"], row["close"]
            regime = regimes.iloc[i]

            # Check existing deals
            for deal in list(open_deals):
                if deal.direction == "LONG":
                    self._process_long_deal(deal, high, low, close, ts, i)
                else:
                    self._process_short_deal(deal, high, low, close, ts, i)

                if not deal.is_open:
                    if deal.direction == "LONG":
                        equity += deal.total_qty * deal.close_price - deal.close_fee
                    else:
                        # Short close: we buy back — cost is qty * close_price + fee
                        # Return collateral + profit
                        equity += deal.total_invested + deal.pnl
                    closed_deals.append(deal)
                    open_deals.remove(deal)

            # Open new deal if regime is friendly and we have capacity
            friendly = friendly_fn(regime)
            can_open = friendly and (friendly is not False)
            if (can_open
                    and len(open_deals) < self.cfg.max_active_deals
                    and equity > self.cfg.base_order_size):
                direction = self._decide_direction(df, i, regime)
                side = "buy" if direction == "LONG" else "sell"
                order = self._make_order(close, self.cfg.base_order_size, ts, side)
                deal = Deal(symbol=symbol, base_order=order, direction=direction)
                open_deals.append(deal)
                equity -= self.cfg.base_order_size

            capital_used = sum(d.total_invested for d in open_deals)
            # Mark-to-market
            open_value = 0.0
            for d in open_deals:
                if d.direction == "LONG":
                    open_value += d.total_qty * close
                else:
                    # Short MTM: collateral + unrealized PnL
                    open_value += d.total_invested + (d.total_invested - d.total_qty * close - d.total_fees)
            mtm_equity = equity + open_value
            eq_records.append({"timestamp": ts, "equity": mtm_equity, "capital_used": capital_used})

        eq_df = pd.DataFrame(eq_records)
        return BacktestResult(
            closed_deals=closed_deals,
            open_deals=open_deals,
            equity_curve=eq_df,
            regimes=regimes,
            config=self.cfg,
            symbol=symbol,
            timeframe=timeframe,
        )

    def _process_long_deal(self, deal: Deal, high: float, low: float, close: float, ts, i: int):
        """Process safety orders and TP for a LONG deal."""
        # Check safety orders
        if deal.so_count < self.cfg.max_safety_orders:
            next_so = deal.so_count + 1
            dev = self.cfg.so_deviation(next_so)
            so_trigger = deal.base_order.price * (1 - dev / 100)
            if low <= so_trigger:
                so_size = self.cfg.so_size(next_so)
                order = self._make_order(so_trigger, so_size, ts, "buy")
                deal.safety_orders.append(order)

        # Check take profit
        tp_price = deal.avg_entry * (1 + self.cfg.take_profit_pct / 100)

        if self.cfg.trailing_tp_pct and high >= tp_price:
            deal.trailing_high = max(deal.trailing_high, high)
            trail_trigger = deal.trailing_high * (1 - self.cfg.trailing_tp_pct / 100)
            if low <= trail_trigger:
                sell_price = self._fill_price(trail_trigger, "sell")
                fee = self._fee(deal.total_qty * sell_price)
                deal.close_price = sell_price
                deal.close_time = ts
                deal.close_fee = fee
        elif not self.cfg.trailing_tp_pct and high >= tp_price:
            sell_price = self._fill_price(tp_price, "sell")
            fee = self._fee(deal.total_qty * sell_price)
            deal.close_price = sell_price
            deal.close_time = ts
            deal.close_fee = fee

    def _process_short_deal(self, deal: Deal, high: float, low: float, close: float, ts, i: int):
        """Process safety orders and TP for a SHORT deal."""
        # Check safety orders: price RISES above entry + deviation
        if deal.so_count < self.cfg.max_safety_orders:
            next_so = deal.so_count + 1
            dev = self.cfg.so_deviation(next_so)
            so_trigger = deal.base_order.price * (1 + dev / 100)
            if high >= so_trigger:
                so_size = self.cfg.so_size(next_so)
                order = self._make_order(so_trigger, so_size, ts, "sell")
                deal.safety_orders.append(order)

        # Check take profit: price DROPS below avg_entry - tp%
        tp_price = deal.avg_entry * (1 - self.cfg.take_profit_pct / 100)

        if self.cfg.trailing_tp_pct and low <= tp_price:
            deal.trailing_low = min(deal.trailing_low, low)
            trail_trigger = deal.trailing_low * (1 + self.cfg.trailing_tp_pct / 100)
            if high >= trail_trigger:
                buy_price = self._fill_price(trail_trigger, "buy")
                fee = self._fee(deal.total_qty * buy_price)
                deal.close_price = buy_price
                deal.close_time = ts
                deal.close_fee = fee
        elif not self.cfg.trailing_tp_pct and low <= tp_price:
            buy_price = self._fill_price(tp_price, "buy")
            fee = self._fee(deal.total_qty * buy_price)
            deal.close_price = buy_price
            deal.close_time = ts
            deal.close_fee = fee


class DualMartingaleBot:
    """Simultaneously runs LONG and SHORT deals. Both sides always active."""

    # Dynamic regime-based allocation: {regime: (long_frac, short_frac)}
    REGIME_ALLOC = {
        "ACCUMULATION": (0.70, 0.30),
        "CHOPPY":       (0.50, 0.50),
        "RANGING":      (0.50, 0.50),
        "DISTRIBUTION": (0.30, 0.70),
        "MILD_TREND":   (0.60, 0.40),
        "TRENDING":     (0.75, 0.25),
        "EXTREME":      (0.0,  0.0),   # no new opens
        "BREAKOUT_WARNING": (0.50, 0.50),
    }

    # Volatility-adjusted SO deviation multipliers based on ATR%
    ATR_DEV_MULT = [
        (1.0, 0.75),   # ATR% < 1%
        (2.5, 1.0),    # 1% <= ATR% < 2.5%
        (4.0, 1.5),    # 2.5% <= ATR% < 4%
        (float('inf'), 2.0),  # ATR% >= 4%
    ]

    def __init__(self, config: MartingaleConfig, long_alloc: float = 0.5,
                 dynamic_alloc: bool = False, vol_adjusted_so: bool = False):
        self.cfg = config
        self.long_alloc = long_alloc  # fraction of capital for longs (used when dynamic_alloc=False)
        self.dynamic_alloc = dynamic_alloc
        self.vol_adjusted_so = vol_adjusted_so

    def _get_alloc(self, regime: str) -> tuple:
        """Get (long_frac, short_frac) for current regime."""
        if not self.dynamic_alloc:
            return (self.long_alloc, 1 - self.long_alloc)
        return self.REGIME_ALLOC.get(regime, (0.50, 0.50))

    def _get_so_dev_multiplier(self, atr_pct_val: float) -> float:
        """Get SO deviation multiplier based on current ATR%."""
        if not self.vol_adjusted_so or np.isnan(atr_pct_val):
            return 1.0
        for threshold, mult in self.ATR_DEV_MULT:
            if atr_pct_val < threshold:
                return mult
        return 2.0

    def _fill_price(self, price: float, side: str) -> float:
        slip = price * self.cfg.slippage_pct / 100
        return price + slip if side == "buy" else price - slip

    def _fee(self, size_usd: float) -> float:
        return size_usd * self.cfg.fee_pct / 100

    def _make_order(self, price: float, size_usd: float, ts: pd.Timestamp, side: str = "buy") -> Order:
        fill = self._fill_price(price, side)
        fee = self._fee(size_usd)
        qty = (size_usd - fee) / fill
        return Order(price=fill, size_usd=size_usd, qty=qty, fee=fee, timestamp=ts)

    def _process_long_deal(self, deal: Deal, high, low, close, ts, available_capital: float = float('inf'), so_dev_mult: float = 1.0):
        if deal.so_count < self.cfg.max_safety_orders:
            next_so = deal.so_count + 1
            dev = self.cfg.so_deviation(next_so) * so_dev_mult
            so_trigger = deal.base_order.price * (1 - dev / 100)
            if low <= so_trigger:
                so_size = self.cfg.so_size(next_so)
                if so_size <= available_capital:
                    order = self._make_order(so_trigger, so_size, ts, "buy")
                    deal.safety_orders.append(order)
        tp_price = deal.avg_entry * (1 + self.cfg.take_profit_pct / 100)
        if self.cfg.trailing_tp_pct and high >= tp_price:
            deal.trailing_high = max(deal.trailing_high, high)
            trail_trigger = deal.trailing_high * (1 - self.cfg.trailing_tp_pct / 100)
            if low <= trail_trigger:
                sell_price = self._fill_price(trail_trigger, "sell")
                fee = self._fee(deal.total_qty * sell_price)
                deal.close_price = sell_price
                deal.close_time = ts
                deal.close_fee = fee
        elif not self.cfg.trailing_tp_pct and high >= tp_price:
            sell_price = self._fill_price(tp_price, "sell")
            fee = self._fee(deal.total_qty * sell_price)
            deal.close_price = sell_price
            deal.close_time = ts
            deal.close_fee = fee

    def _process_short_deal(self, deal: Deal, high, low, close, ts, available_capital: float = float('inf'), so_dev_mult: float = 1.0):
        if deal.so_count < self.cfg.max_safety_orders:
            next_so = deal.so_count + 1
            dev = self.cfg.so_deviation(next_so) * so_dev_mult
            so_trigger = deal.base_order.price * (1 + dev / 100)
            if high >= so_trigger:
                so_size = self.cfg.so_size(next_so)
                if so_size <= available_capital:
                    order = self._make_order(so_trigger, so_size, ts, "sell")
                    deal.safety_orders.append(order)
        tp_price = deal.avg_entry * (1 - self.cfg.take_profit_pct / 100)
        if self.cfg.trailing_tp_pct and low <= tp_price:
            deal.trailing_low = min(deal.trailing_low, low)
            trail_trigger = deal.trailing_low * (1 + self.cfg.trailing_tp_pct / 100)
            if high >= trail_trigger:
                buy_price = self._fill_price(trail_trigger, "buy")
                fee = self._fee(deal.total_qty * buy_price)
                deal.close_price = buy_price
                deal.close_time = ts
                deal.close_fee = fee
        elif not self.cfg.trailing_tp_pct and low <= tp_price:
            buy_price = self._fill_price(tp_price, "buy")
            fee = self._fee(deal.total_qty * buy_price)
            deal.close_price = buy_price
            deal.close_time = ts
            deal.close_fee = fee

    def run(self, df: pd.DataFrame, symbol: str, timeframe: str,
            precomputed_regimes: pd.Series = None, friendly_fn=None) -> BacktestResult:
        from .regime_detector import classify_regime, is_martingale_friendly
        from . import indicators as ind
        regimes = precomputed_regimes if precomputed_regimes is not None else classify_regime(df, timeframe)
        if friendly_fn is None:
            friendly_fn = is_martingale_friendly

        # Precompute ATR% for volatility-adjusted SOs
        atr_pct_series = ind.atr_pct(df) if self.vol_adjusted_so else None

        open_deals: List[Deal] = []
        closed_deals: List[Deal] = []
        equity = self.cfg.initial_capital
        # Always start with 50/50 — dynamic alloc rebalances each candle
        long_capital = self.cfg.initial_capital * 0.5
        short_capital = self.cfg.initial_capital * 0.5
        eq_records = []

        for i in range(len(df)):
            row = df.iloc[i]
            ts = row["timestamp"]
            high, low, close = row["high"], row["low"], row["close"]
            regime = regimes.iloc[i]

            # Dynamic rebalance: adjust free capital split each candle
            if self.dynamic_alloc:
                new_long_frac, new_short_frac = self._get_alloc(regime)
                total_free = long_capital + short_capital
                if total_free > 0 and (new_long_frac + new_short_frac) > 0:
                    target_long = total_free * new_long_frac / (new_long_frac + new_short_frac)
                    long_capital = target_long
                    short_capital = total_free - target_long
                # If EXTREME (0,0), keep capital as-is but block new opens below

            # Get SO deviation multiplier for this candle
            so_dev_mult = self._get_so_dev_multiplier(atr_pct_series.iloc[i]) if atr_pct_series is not None else 1.0

            # Process existing deals — check SO fills and TP hits
            for deal in list(open_deals):
                # Track SO cost before processing
                old_invested = deal.total_invested
                if deal.direction == "LONG":
                    self._process_long_deal(deal, high, low, close, ts, long_capital, so_dev_mult)
                else:
                    self._process_short_deal(deal, high, low, close, ts, short_capital, so_dev_mult)
                # Deduct new SO cost from side capital
                new_invested = deal.total_invested
                so_cost = new_invested - old_invested
                if so_cost > 0:
                    if deal.direction == "LONG":
                        long_capital -= so_cost
                    else:
                        short_capital -= so_cost

                if not deal.is_open:
                    # Return capital + PnL to the side
                    if deal.direction == "LONG":
                        returned = deal.total_qty * deal.close_price - deal.close_fee
                        long_capital += returned
                    else:
                        returned = deal.total_invested + deal.pnl
                        short_capital += returned
                    closed_deals.append(deal)
                    open_deals.remove(deal)

            # Try to open deals — always want both sides running
            friendly = friendly_fn(regime)
            extreme = (regime == "EXTREME")
            can_open_new = not extreme  # only block on EXTREME

            long_deals = [d for d in open_deals if d.direction == "LONG"]
            short_deals = [d for d in open_deals if d.direction == "SHORT"]

            if can_open_new and len(long_deals) < self.cfg.max_active_deals and long_capital > self.cfg.base_order_size:
                order = self._make_order(close, self.cfg.base_order_size, ts, "buy")
                deal = Deal(symbol=symbol, base_order=order, direction="LONG")
                open_deals.append(deal)
                long_capital -= self.cfg.base_order_size

            if can_open_new and len(short_deals) < self.cfg.max_active_deals and short_capital > self.cfg.base_order_size:
                order = self._make_order(close, self.cfg.base_order_size, ts, "sell")
                deal = Deal(symbol=symbol, base_order=order, direction="SHORT")
                open_deals.append(deal)
                short_capital -= self.cfg.base_order_size

            # MTM equity
            capital_used = sum(d.total_invested for d in open_deals)
            open_value = 0.0
            for d in open_deals:
                if d.direction == "LONG":
                    open_value += d.total_qty * close
                else:
                    open_value += d.total_invested + (d.total_invested - d.total_qty * close - d.total_fees)
            mtm_equity = long_capital + short_capital + open_value
            eq_records.append({"timestamp": ts, "equity": mtm_equity, "capital_used": capital_used})

        eq_df = pd.DataFrame(eq_records)
        return BacktestResult(
            closed_deals=closed_deals,
            open_deals=open_deals,
            equity_curve=eq_df,
            regimes=regimes,
            config=self.cfg,
            symbol=symbol,
            timeframe=timeframe,
        )
