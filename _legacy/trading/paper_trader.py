"""Live paper trading bot for Martingale DCA strategy."""
import json
import csv
import time
import os
import traceback
from datetime import datetime, timezone, timedelta
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import List, Optional, Dict

import ccxt
import pandas as pd
import numpy as np

from .config import MartingaleConfig
from .regime_detector import classify_regime_v2, is_martingale_friendly_v2, classify_regime, is_martingale_friendly

PAPER_DIR = Path(__file__).parent / "paper"
PAPER_DIR.mkdir(exist_ok=True)

TF_SECONDS = {
    "1m": 60, "3m": 180, "5m": 300, "15m": 900, "30m": 1800,
    "1h": 3600, "2h": 7200, "4h": 14400, "1d": 86400,
}


@dataclass
class PaperOrder:
    price: float
    size_usd: float
    qty: float
    fee: float
    timestamp: str  # ISO string for JSON serialization

    def to_dict(self):
        return {"price": self.price, "size_usd": self.size_usd, "qty": self.qty, "fee": self.fee, "timestamp": self.timestamp}


@dataclass
class PaperDeal:
    symbol: str
    deal_id: int
    base_order: PaperOrder
    safety_orders: List[PaperOrder] = field(default_factory=list)
    close_price: Optional[float] = None
    close_time: Optional[str] = None
    close_fee: float = 0.0
    trailing_high: float = 0.0

    @property
    def is_open(self) -> bool:
        return self.close_price is None

    @property
    def total_invested(self) -> float:
        return self.base_order.size_usd + sum(so.size_usd for so in self.safety_orders)

    @property
    def total_qty(self) -> float:
        return self.base_order.qty + sum(so.qty for so in self.safety_orders)

    @property
    def avg_entry(self) -> float:
        return self.total_invested / self.total_qty if self.total_qty > 0 else 0

    @property
    def total_fees(self) -> float:
        return self.base_order.fee + sum(so.fee for so in self.safety_orders) + self.close_fee

    @property
    def so_count(self) -> int:
        return len(self.safety_orders)

    def unrealized_pnl(self, current_price: float) -> float:
        if not self.is_open:
            return 0.0
        return self.total_qty * current_price - self.total_invested - self.total_fees

    def realized_pnl(self) -> float:
        if self.close_price is None:
            return 0.0
        return self.total_qty * self.close_price - self.close_fee - self.total_invested - (self.total_fees - self.close_fee)

    def to_dict(self):
        return {
            "symbol": self.symbol, "deal_id": self.deal_id,
            "base_order": self.base_order.to_dict(),
            "safety_orders": [so.to_dict() for so in self.safety_orders],
            "close_price": self.close_price, "close_time": self.close_time,
            "close_fee": self.close_fee, "trailing_high": self.trailing_high,
        }

    @classmethod
    def from_dict(cls, d):
        return cls(
            symbol=d["symbol"], deal_id=d["deal_id"],
            base_order=PaperOrder(**d["base_order"]),
            safety_orders=[PaperOrder(**so) for so in d["safety_orders"]],
            close_price=d.get("close_price"), close_time=d.get("close_time"),
            close_fee=d.get("close_fee", 0.0), trailing_high=d.get("trailing_high", 0.0),
        )


class PaperTrader:
    def __init__(self, config: MartingaleConfig, symbols: List[str], timeframe: str = "15m",
                 use_v2_regime: bool = True, max_drawdown_pct: float = 25.0):
        self.cfg = config
        self.symbols = symbols
        self.timeframe = timeframe
        self.use_v2 = use_v2_regime
        self.max_drawdown_pct = max_drawdown_pct

        self.cash = config.initial_capital
        self.open_deals: List[PaperDeal] = []
        self.closed_deals: List[PaperDeal] = []
        self.equity_history: List[dict] = []
        self.deal_counter = 0
        self.current_regimes: Dict[str, str] = {}
        self.current_prices: Dict[str, float] = {}
        self.circuit_breaker_triggered = False
        self.start_time: Optional[str] = None
        self._running = False
        self._exchange = None

        # Try to load existing state
        self.load_state()

    def _get_exchange(self):
        if self._exchange is None:
            self._exchange = ccxt.okx({"enableRateLimit": True})
            self._exchange.load_markets()
        return self._exchange

    def _fill_price(self, price: float, side: str) -> float:
        slip = price * self.cfg.slippage_pct / 100
        return price + slip if side == "buy" else price - slip

    def _fee(self, size_usd: float) -> float:
        return size_usd * self.cfg.fee_pct / 100

    def _make_order(self, price: float, size_usd: float, ts: str) -> PaperOrder:
        fill = self._fill_price(price, "buy")
        fee = self._fee(size_usd)
        qty = (size_usd - fee) / fill
        return PaperOrder(price=fill, size_usd=size_usd, qty=qty, fee=fee, timestamp=ts)

    def _fetch_candles(self, symbol: str, limit: int = 300) -> pd.DataFrame:
        ex = self._get_exchange()
        data = ex.fetch_ohlcv(symbol, self.timeframe, limit=limit)
        df = pd.DataFrame(data, columns=["timestamp", "open", "high", "low", "close", "volume"])
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms", utc=True)
        return df

    def _detect_regime(self, df: pd.DataFrame) -> str:
        """Get current regime for the latest candle."""
        try:
            if self.use_v2:
                regimes = classify_regime_v2(df, self.timeframe)
            else:
                regimes = classify_regime(df, self.timeframe)
            return regimes.iloc[-1]
        except Exception as e:
            print(f"  [WARN] Regime detection failed: {e}, defaulting to RANGING")
            return "RANGING"

    def _is_friendly(self, regime: str):
        if self.use_v2:
            return is_martingale_friendly_v2(regime)
        return is_martingale_friendly(regime)

    def _check_circuit_breaker(self) -> bool:
        if not self.equity_history:
            return False
        peak = max(e["equity"] for e in self.equity_history)
        current = self.equity_history[-1]["equity"]
        dd_pct = (peak - current) / peak * 100 if peak > 0 else 0
        if dd_pct >= self.max_drawdown_pct:
            self.circuit_breaker_triggered = True
            print(f"\n  🚨 CIRCUIT BREAKER: Drawdown {dd_pct:.1f}% >= {self.max_drawdown_pct}% threshold!")
            return True
        return False

    def _process_candle(self, symbol: str, candle_row: pd.Series, ts_str: str):
        high, low, close = candle_row["high"], candle_row["low"], candle_row["close"]
        self.current_prices[symbol] = close

        # Process existing deals for this symbol
        for deal in [d for d in self.open_deals if d.symbol == symbol]:
            # Check safety orders
            if deal.so_count < self.cfg.max_safety_orders:
                next_so = deal.so_count + 1
                dev = self.cfg.so_deviation(next_so)
                so_trigger = deal.base_order.price * (1 - dev / 100)
                if low <= so_trigger:
                    so_size = self.cfg.so_size(next_so)
                    if self.cash >= so_size:
                        order = self._make_order(so_trigger, so_size, ts_str)
                        deal.safety_orders.append(order)
                        self.cash -= so_size
                        print(f"  📉 SO#{next_so} filled for {symbol} @ ${so_trigger:.4f} (${so_size:.0f})")
                        self._log_trade("SAFETY_ORDER", symbol, deal.deal_id, so_trigger, so_size, next_so)

            # Check take profit
            tp_price = deal.avg_entry * (1 + self.cfg.take_profit_pct / 100)

            if self.cfg.trailing_tp_pct and high >= tp_price:
                deal.trailing_high = max(deal.trailing_high, high)
                trail_trigger = deal.trailing_high * (1 - self.cfg.trailing_tp_pct / 100)
                if low <= trail_trigger:
                    self._close_deal(deal, trail_trigger, ts_str)
            elif not self.cfg.trailing_tp_pct and high >= tp_price:
                self._close_deal(deal, tp_price, ts_str)

    def _close_deal(self, deal: PaperDeal, price: float, ts_str: str):
        sell_price = self._fill_price(price, "sell")
        fee = self._fee(deal.total_qty * sell_price)
        deal.close_price = sell_price
        deal.close_time = ts_str
        deal.close_fee = fee
        revenue = deal.total_qty * sell_price - fee
        self.cash += revenue
        self.open_deals.remove(deal)
        self.closed_deals.append(deal)
        pnl = deal.realized_pnl()
        print(f"  ✅ TP hit for {deal.symbol} deal#{deal.deal_id} @ ${sell_price:.4f} | PnL: ${pnl:.2f} ({pnl/deal.total_invested*100:.1f}%) | SOs: {deal.so_count}")
        self._log_trade("TAKE_PROFIT", deal.symbol, deal.deal_id, sell_price, revenue, deal.so_count)

    def _open_new_deal(self, symbol: str, price: float, ts_str: str):
        self.deal_counter += 1
        order = self._make_order(price, self.cfg.base_order_size, ts_str)
        deal = PaperDeal(symbol=symbol, deal_id=self.deal_counter, base_order=order)
        self.open_deals.append(deal)
        self.cash -= self.cfg.base_order_size
        print(f"  🟢 New deal#{deal.deal_id} for {symbol} @ ${price:.4f} (${self.cfg.base_order_size:.0f})")
        self._log_trade("NEW_DEAL", symbol, deal.deal_id, price, self.cfg.base_order_size, 0)

    def _log_trade(self, action: str, symbol: str, deal_id: int, price: float, amount: float, so_count: int):
        path = PAPER_DIR / "trades.csv"
        write_header = not path.exists()
        with open(path, "a", newline="") as f:
            w = csv.writer(f)
            if write_header:
                w.writerow(["timestamp", "action", "symbol", "deal_id", "price", "amount", "so_count", "cash", "equity"])
            equity = self._calc_equity()
            w.writerow([datetime.now(timezone.utc).isoformat(), action, symbol, deal_id,
                        f"{price:.6f}", f"{amount:.2f}", so_count, f"{self.cash:.2f}", f"{equity:.2f}"])

    def _calc_equity(self) -> float:
        open_value = sum(d.total_qty * self.current_prices.get(d.symbol, d.avg_entry) for d in self.open_deals)
        return self.cash + open_value

    def _record_equity(self):
        equity = self._calc_equity()
        rec = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "equity": round(equity, 2),
            "cash": round(self.cash, 2),
            "open_deals": len(self.open_deals),
        }
        self.equity_history.append(rec)
        # Append to CSV
        path = PAPER_DIR / "equity.csv"
        write_header = not path.exists()
        with open(path, "a", newline="") as f:
            w = csv.writer(f)
            if write_header:
                w.writerow(["timestamp", "equity", "cash", "open_deals"])
            w.writerow([rec["timestamp"], rec["equity"], rec["cash"], rec["open_deals"]])

    def _print_status(self):
        equity = self._calc_equity()
        pnl = equity - self.cfg.initial_capital
        pnl_pct = pnl / self.cfg.initial_capital * 100
        peak = max((e["equity"] for e in self.equity_history), default=equity)
        dd = (peak - equity) / peak * 100 if peak > 0 else 0

        print(f"\n{'='*70}")
        print(f"  📊 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | Equity: ${equity:.2f} | PnL: ${pnl:+.2f} ({pnl_pct:+.1f}%) | DD: {dd:.1f}%")
        for sym in self.symbols:
            regime = self.current_regimes.get(sym, "?")
            price = self.current_prices.get(sym, 0)
            sym_deals = [d for d in self.open_deals if d.symbol == sym]
            print(f"  {sym}: ${price:.4f} | Regime: {regime} | Open deals: {len(sym_deals)}")
            for d in sym_deals:
                upnl = d.unrealized_pnl(price)
                print(f"    Deal#{d.deal_id}: entry=${d.avg_entry:.4f} SOs={d.so_count} uPnL=${upnl:+.2f}")
        print(f"  Closed: {len(self.closed_deals)} deals | Cash: ${self.cash:.2f}")
        cb = "🔴 TRIGGERED" if self.circuit_breaker_triggered else "🟢 OK"
        print(f"  Circuit Breaker: {cb}")
        print(f"{'='*70}")

    def status(self) -> dict:
        equity = self._calc_equity()
        pnl = equity - self.cfg.initial_capital
        peak = max((e["equity"] for e in self.equity_history), default=equity)
        dd = (peak - equity) / peak * 100 if peak > 0 else 0
        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "running": self._running,
            "equity": round(equity, 2),
            "cash": round(self.cash, 2),
            "pnl": round(pnl, 2),
            "pnl_pct": round(pnl / self.cfg.initial_capital * 100, 2),
            "drawdown_pct": round(dd, 2),
            "peak_equity": round(peak, 2),
            "initial_capital": self.cfg.initial_capital,
            "circuit_breaker": self.circuit_breaker_triggered,
            "max_drawdown_threshold": self.max_drawdown_pct,
            "symbols": self.symbols,
            "timeframe": self.timeframe,
            "use_v2_regime": self.use_v2,
            "open_deals": [{
                "deal_id": d.deal_id, "symbol": d.symbol,
                "avg_entry": round(d.avg_entry, 6), "so_count": d.so_count,
                "invested": round(d.total_invested, 2), "qty": round(d.total_qty, 6),
                "current_price": round(self.current_prices.get(d.symbol, 0), 6),
                "unrealized_pnl": round(d.unrealized_pnl(self.current_prices.get(d.symbol, d.avg_entry)), 2),
            } for d in self.open_deals],
            "closed_deals_count": len(self.closed_deals),
            "closed_deals_recent": [{
                "deal_id": d.deal_id, "symbol": d.symbol,
                "avg_entry": round(d.avg_entry, 6), "close_price": round(d.close_price, 6) if d.close_price else None,
                "so_count": d.so_count, "pnl": round(d.realized_pnl(), 2),
                "close_time": d.close_time,
            } for d in self.closed_deals[-50:]],
            "regimes": self.current_regimes,
            "start_time": self.start_time,
            "config": {
                "base_order_size": self.cfg.base_order_size,
                "safety_order_size": self.cfg.safety_order_size,
                "max_safety_orders": self.cfg.max_safety_orders,
                "max_active_deals": self.cfg.max_active_deals,
                "take_profit_pct": self.cfg.take_profit_pct,
                "price_deviation_pct": self.cfg.price_deviation_pct,
                "deviation_multiplier": self.cfg.deviation_multiplier,
                "safety_order_multiplier": self.cfg.safety_order_multiplier,
                "fee_pct": self.cfg.fee_pct,
            },
            "equity_history": self.equity_history[-100:],  # Last 100 for dashboard chart
        }

    def save_state(self):
        state = {
            "cash": self.cash,
            "deal_counter": self.deal_counter,
            "open_deals": [d.to_dict() for d in self.open_deals],
            "closed_deals": [d.to_dict() for d in self.closed_deals],
            "equity_history": self.equity_history,
            "current_regimes": self.current_regimes,
            "current_prices": self.current_prices,
            "circuit_breaker_triggered": self.circuit_breaker_triggered,
            "start_time": self.start_time,
        }
        path = PAPER_DIR / "state.json"
        with open(path, "w") as f:
            json.dump(state, f, indent=2)
        # Also write status.json for dashboard
        with open(PAPER_DIR / "status.json", "w") as f:
            json.dump(self.status(), f, indent=2)

    def load_state(self):
        path = PAPER_DIR / "state.json"
        if not path.exists():
            return
        try:
            with open(path) as f:
                state = json.load(f)
            self.cash = state["cash"]
            self.deal_counter = state["deal_counter"]
            self.open_deals = [PaperDeal.from_dict(d) for d in state["open_deals"]]
            self.closed_deals = [PaperDeal.from_dict(d) for d in state["closed_deals"]]
            self.equity_history = state.get("equity_history", [])
            self.current_regimes = state.get("current_regimes", {})
            self.current_prices = state.get("current_prices", {})
            self.circuit_breaker_triggered = state.get("circuit_breaker_triggered", False)
            self.start_time = state.get("start_time")
            print(f"  ♻️  Loaded state: {len(self.open_deals)} open deals, {len(self.closed_deals)} closed, cash=${self.cash:.2f}")
        except Exception as e:
            print(f"  [WARN] Failed to load state: {e}")

    def stop(self):
        self._running = False

    def start(self):
        self._running = True
        if not self.start_time:
            self.start_time = datetime.now(timezone.utc).isoformat()

        poll_seconds = TF_SECONDS.get(self.timeframe, 900)
        print(f"\n  🚀 Paper trader started! Polling every {poll_seconds}s ({self.timeframe} candles)")
        print(f"  Symbols: {', '.join(self.symbols)}")
        print(f"  Capital: ${self.cfg.initial_capital:.0f} | Cash: ${self.cash:.2f}")
        print(f"  TP: {self.cfg.take_profit_pct}% | Max SOs: {self.cfg.max_safety_orders} | Max Deals: {self.cfg.max_active_deals}")

        while self._running:
            try:
                for symbol in self.symbols:
                    # Fetch candles
                    df = self._fetch_candles(symbol, limit=300)
                    if df.empty:
                        continue

                    latest = df.iloc[-1]
                    ts_str = str(latest["timestamp"])

                    # Detect regime
                    regime = self._detect_regime(df)
                    old_regime = self.current_regimes.get(symbol)
                    self.current_regimes[symbol] = regime
                    if old_regime and old_regime != regime:
                        print(f"  🔄 Regime change for {symbol}: {old_regime} → {regime}")

                    # Process candle against open deals
                    self._process_candle(symbol, latest, ts_str)

                    # Open new deal?
                    if not self.circuit_breaker_triggered:
                        friendly = self._is_friendly(regime)
                        symbol_deals = [d for d in self.open_deals if d.symbol == symbol]
                        if (friendly is True and
                                len(self.open_deals) < self.cfg.max_active_deals and
                                len(symbol_deals) == 0 and
                                self.cash >= self.cfg.base_order_size):
                            self._open_new_deal(symbol, latest["close"], ts_str)

                # Record equity & check circuit breaker
                self._record_equity()
                self._check_circuit_breaker()
                self._print_status()
                self.save_state()

                # Sleep until next candle
                time.sleep(poll_seconds)

            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"\n  ❌ Error: {e}")
                traceback.print_exc()
                time.sleep(30)

        print("\n  Paper trader stopped.")
        self.save_state()
