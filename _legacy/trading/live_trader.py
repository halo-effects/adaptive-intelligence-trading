"""Live spot trading bot for Martingale DCA strategy on Hyperliquid."""
import json
import csv
import time
import os
import traceback
import requests
from datetime import datetime, timezone, timedelta
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Optional, Dict

import ccxt
import pandas as pd
import numpy as np

from .config import MartingaleConfig
from .regime_detector import classify_regime_v2, is_martingale_friendly_v2

LIVE_DIR = Path(__file__).parent / "live"
LIVE_DIR.mkdir(exist_ok=True)

TF_SECONDS = {
    "1m": 60, "3m": 180, "5m": 300, "15m": 900, "30m": 1800,
    "1h": 3600, "2h": 7200, "4h": 14400, "1d": 86400,
}

# ── Telegram ──────────────────────────────────────────────────────────────
_TG_TOKEN = "8528958079:AAF90HSJ5Ck1urUydzS5CUvyf2EEeB7LUwc"
_TG_CHAT = "5221941584"


def send_telegram(msg: str):
    try:
        requests.post(
            f"https://api.telegram.org/bot{_TG_TOKEN}/sendMessage",
            json={"chat_id": _TG_CHAT, "text": msg, "parse_mode": "HTML"},
            timeout=10,
        )
    except Exception:
        pass  # non-critical


# ── Order / Deal dataclasses ─────────────────────────────────────────────

@dataclass
class LiveOrder:
    order_id: str          # exchange order id
    price: float
    size_usd: float
    qty: float
    fee: float
    side: str              # "buy" or "sell"
    status: str            # "open", "filled", "canceled"
    timestamp: str
    so_index: int = 0      # 0 = base order, 1..N = safety orders

    def to_dict(self):
        return vars(self)


@dataclass
class LiveDeal:
    symbol: str
    deal_id: int
    base_order: Optional[dict] = None       # filled order dict
    safety_orders: List[dict] = field(default_factory=list)  # filled SO dicts
    pending_so_ids: List[str] = field(default_factory=list)  # open SO order ids
    tp_order_id: Optional[str] = None
    close_price: Optional[float] = None
    close_time: Optional[str] = None
    close_fee: float = 0.0
    open_time: Optional[str] = None
    regime_at_open: str = ""

    @property
    def is_open(self) -> bool:
        return self.close_price is None

    @property
    def total_invested(self) -> float:
        t = self.base_order["size_usd"] if self.base_order else 0
        return t + sum(so["size_usd"] for so in self.safety_orders)

    @property
    def total_qty(self) -> float:
        t = self.base_order["qty"] if self.base_order else 0
        return t + sum(so["qty"] for so in self.safety_orders)

    @property
    def avg_entry(self) -> float:
        return self.total_invested / self.total_qty if self.total_qty > 0 else 0

    @property
    def total_fees(self) -> float:
        t = self.base_order["fee"] if self.base_order else 0
        return t + sum(so["fee"] for so in self.safety_orders) + self.close_fee

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
            "base_order": self.base_order,
            "safety_orders": self.safety_orders,
            "pending_so_ids": self.pending_so_ids,
            "tp_order_id": self.tp_order_id,
            "close_price": self.close_price, "close_time": self.close_time,
            "close_fee": self.close_fee, "open_time": self.open_time,
            "regime_at_open": self.regime_at_open,
        }

    @classmethod
    def from_dict(cls, d):
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


class LiveTrader:
    def __init__(self, config: MartingaleConfig, symbol: str = "HYPE/USDC",
                 timeframe: str = "5m", max_drawdown_pct: float = 25.0,
                 dry_run: bool = False):
        self.cfg = config
        self.symbol = symbol
        self.timeframe = timeframe
        self.max_drawdown_pct = max_drawdown_pct
        self.dry_run = dry_run

        self.cash = config.initial_capital
        self.open_deals: List[LiveDeal] = []
        self.closed_deals: List[LiveDeal] = []
        self.equity_history: List[dict] = []
        self.deal_counter = 0
        self.current_regime: str = "UNKNOWN"
        self.current_price: float = 0.0
        self.circuit_breaker_triggered = False
        self.daily_pause_until: Optional[str] = None
        self.start_time: Optional[str] = None
        self.consecutive_errors = 0
        self._running = False
        self._exchange = None
        self._last_daily_summary: Optional[str] = None

        self.load_state()

    # ── Exchange ──────────────────────────────────────────────────────
    def _get_exchange(self):
        if self._exchange is None:
            pk = os.environ.get("HL_PRIVATE_KEY", "")
            wallet = os.environ.get("HL_WALLET_ADDRESS", "")
            if not pk or not wallet:
                raise RuntimeError("HL_PRIVATE_KEY and HL_WALLET_ADDRESS env vars required")
            self._exchange = ccxt.hyperliquid({
                "enableRateLimit": True,
                "privateKey": pk,
                "walletAddress": wallet,
            })
            self._exchange.load_markets()
        return self._exchange

    # ── Candles & regime ──────────────────────────────────────────────
    def _fetch_candles(self, limit: int = 300) -> pd.DataFrame:
        ex = self._get_exchange()
        data = ex.fetch_ohlcv(self.symbol, self.timeframe, limit=limit)
        df = pd.DataFrame(data, columns=["timestamp", "open", "high", "low", "close", "volume"])
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms", utc=True)
        return df

    def _detect_regime(self, df: pd.DataFrame) -> str:
        try:
            regimes = classify_regime_v2(df, self.timeframe)
            return regimes.iloc[-1]
        except Exception as e:
            print(f"  [WARN] Regime detection failed: {e}, defaulting to RANGING")
            return "RANGING"

    # ── Order execution ───────────────────────────────────────────────
    def _place_limit_buy(self, price: float, qty: float, so_index: int = 0) -> Optional[dict]:
        """Place limit buy. Returns order info dict or None."""
        if self.dry_run:
            print(f"  [DRY-RUN] Would place limit BUY {qty:.6f} @ ${price:.4f} (SO#{so_index})")
            return {"id": f"dry-{int(time.time())}-{so_index}", "price": price, "amount": qty, "status": "open"}
        try:
            ex = self._get_exchange()
            order = ex.create_order(self.symbol, "limit", "buy", qty, price)
            self.consecutive_errors = 0
            return order
        except Exception as e:
            self.consecutive_errors += 1
            print(f"  ❌ Order error: {e}")
            if self.consecutive_errors >= 3:
                self._trigger_kill_switch(f"3+ consecutive API errors: {e}")
            return None

    def _place_limit_sell(self, price: float, qty: float) -> Optional[dict]:
        """Place limit sell (take profit)."""
        if self.dry_run:
            print(f"  [DRY-RUN] Would place limit SELL {qty:.6f} @ ${price:.4f} (TP)")
            return {"id": f"dry-tp-{int(time.time())}", "price": price, "amount": qty, "status": "open"}
        try:
            ex = self._get_exchange()
            order = ex.create_order(self.symbol, "limit", "sell", qty, price)
            self.consecutive_errors = 0
            return order
        except Exception as e:
            self.consecutive_errors += 1
            print(f"  ❌ TP order error: {e}")
            if self.consecutive_errors >= 3:
                self._trigger_kill_switch(f"3+ consecutive API errors: {e}")
            return None

    def _cancel_order(self, order_id: str):
        if self.dry_run:
            return
        try:
            self._get_exchange().cancel_order(order_id, self.symbol)
        except Exception as e:
            print(f"  [WARN] Cancel failed for {order_id}: {e}")

    def _fetch_order(self, order_id: str) -> Optional[dict]:
        if self.dry_run:
            return None
        try:
            return self._get_exchange().fetch_order(order_id, self.symbol)
        except Exception:
            return None

    # ── Deal management ───────────────────────────────────────────────
    def _open_new_deal(self, price: float):
        """Open a new deal with base order + safety orders."""
        ts = datetime.now(timezone.utc).isoformat()
        self.deal_counter += 1
        deal = LiveDeal(
            symbol=self.symbol,
            deal_id=self.deal_counter,
            open_time=ts,
            regime_at_open=self.current_regime,
        )

        # Base order: market-like limit at current price
        bo_size = self.cfg.base_order_size
        fee = bo_size * self.cfg.fee_pct / 100
        qty = (bo_size - fee) / price

        result = self._place_limit_buy(price, qty, so_index=0)
        if result is None:
            self.deal_counter -= 1
            return

        deal.base_order = {
            "order_id": result["id"], "price": price, "size_usd": bo_size,
            "qty": qty, "fee": fee, "timestamp": ts, "so_index": 0,
        }
        self.cash -= bo_size

        # Place safety orders
        for i in range(1, self.cfg.max_safety_orders + 1):
            dev = self.cfg.so_deviation(i)
            so_price = price * (1 - dev / 100)
            so_size = self.cfg.so_size(i)
            if self.cash < so_size:
                break
            so_fee = so_size * self.cfg.fee_pct / 100
            so_qty = (so_size - so_fee) / so_price

            so_result = self._place_limit_buy(so_price, so_qty, so_index=i)
            if so_result:
                deal.pending_so_ids.append(so_result["id"])

        # Place TP order
        tp_price = price * (1 + self.cfg.take_profit_pct / 100)
        tp_result = self._place_limit_sell(tp_price, qty)
        if tp_result:
            deal.tp_order_id = tp_result["id"]

        self.open_deals.append(deal)
        msg = (f"🟢 <b>New Deal #{deal.deal_id}</b>\n"
               f"Symbol: {self.symbol}\nPrice: ${price:.4f}\n"
               f"Size: ${bo_size:.0f}\nRegime: {self.current_regime}")
        print(f"  {msg.replace('<b>','').replace('</b>','')}")
        send_telegram(msg)
        self._log_trade("NEW_DEAL", deal.deal_id, price, bo_size, 0)

    def _check_deal_orders(self, deal: LiveDeal):
        """Poll exchange for filled safety orders and TP."""
        if not deal.is_open:
            return

        # Check safety orders
        filled_ids = []
        for oid in list(deal.pending_so_ids):
            info = self._fetch_order(oid)
            if info and info.get("status") == "closed":
                filled_ids.append(oid)
                filled_price = info.get("average", info.get("price", 0))
                filled_qty = info.get("filled", info.get("amount", 0))
                filled_cost = filled_price * filled_qty if filled_price and filled_qty else 0
                fee = filled_cost * self.cfg.fee_pct / 100

                so_idx = deal.so_count + 1
                deal.safety_orders.append({
                    "order_id": oid, "price": filled_price, "size_usd": filled_cost,
                    "qty": filled_qty, "fee": fee,
                    "timestamp": datetime.now(timezone.utc).isoformat(), "so_index": so_idx,
                })
                deal.pending_so_ids.remove(oid)
                self.cash -= filled_cost

                msg = (f"📉 <b>SO #{so_idx} Filled</b>\n"
                       f"Price: ${filled_price:.4f}\nNew Avg: ${deal.avg_entry:.4f}\n"
                       f"Total Invested: ${deal.total_invested:.0f}")
                print(f"  {msg.replace('<b>','').replace('</b>','')}")
                send_telegram(msg)
                self._log_trade("SAFETY_ORDER", deal.deal_id, filled_price, filled_cost, so_idx)

                # Update TP order
                self._update_tp_order(deal)

        # Check TP order
        if deal.tp_order_id:
            tp_info = self._fetch_order(deal.tp_order_id)
            if tp_info and tp_info.get("status") == "closed":
                self._close_deal(deal, tp_info)

    def _update_tp_order(self, deal: LiveDeal):
        """Cancel old TP and place new one at updated avg_entry + TP%."""
        if deal.tp_order_id:
            self._cancel_order(deal.tp_order_id)

        tp_price = deal.avg_entry * (1 + self.cfg.take_profit_pct / 100)
        tp_result = self._place_limit_sell(tp_price, deal.total_qty)
        if tp_result:
            deal.tp_order_id = tp_result["id"]

    def _close_deal(self, deal: LiveDeal, tp_info: dict):
        """Process a TP fill."""
        sell_price = tp_info.get("average", tp_info.get("price", 0))
        fee = deal.total_qty * sell_price * self.cfg.fee_pct / 100
        deal.close_price = sell_price
        deal.close_time = datetime.now(timezone.utc).isoformat()
        deal.close_fee = fee
        revenue = deal.total_qty * sell_price - fee
        self.cash += revenue

        # Cancel remaining SOs
        for oid in deal.pending_so_ids:
            self._cancel_order(oid)
        deal.pending_so_ids.clear()
        deal.tp_order_id = None

        self.open_deals.remove(deal)
        self.closed_deals.append(deal)
        pnl = deal.realized_pnl()
        duration = ""
        if deal.open_time:
            try:
                dt_open = datetime.fromisoformat(deal.open_time)
                dt_close = datetime.fromisoformat(deal.close_time)
                duration = str(dt_close - dt_open)
            except Exception:
                pass

        msg = (f"✅ <b>Deal #{deal.deal_id} Closed</b>\n"
               f"TP @ ${sell_price:.4f}\nPnL: ${pnl:+.2f} ({pnl/deal.total_invested*100:+.1f}%)\n"
               f"SOs: {deal.so_count} | Duration: {duration}")
        print(f"  {msg.replace('<b>','').replace('</b>','')}")
        send_telegram(msg)
        self._log_trade("TAKE_PROFIT", deal.deal_id, sell_price, revenue, deal.so_count)

    # ── Kill switches ─────────────────────────────────────────────────
    def _trigger_kill_switch(self, reason: str):
        self.circuit_breaker_triggered = True
        msg = f"🚨 <b>KILL SWITCH</b>\n{reason}"
        print(f"\n  {msg.replace('<b>','').replace('</b>','')}")
        send_telegram(msg)

    def _check_circuit_breaker(self) -> bool:
        if not self.equity_history:
            return False
        peak = max(e["equity"] for e in self.equity_history)
        current = self.equity_history[-1]["equity"]
        dd_pct = (peak - current) / peak * 100 if peak > 0 else 0
        if dd_pct >= self.max_drawdown_pct:
            self._trigger_kill_switch(f"Max drawdown {dd_pct:.1f}% >= {self.max_drawdown_pct}%")
            return True
        return False

    def _check_daily_loss(self) -> bool:
        """Pause if daily loss > 15%."""
        if self.daily_pause_until:
            if datetime.now(timezone.utc).isoformat() < self.daily_pause_until:
                return True
            self.daily_pause_until = None

        today = datetime.now(timezone.utc).date().isoformat()
        today_equity = [e for e in self.equity_history if e["timestamp"][:10] == today]
        if len(today_equity) < 2:
            return False
        day_start = today_equity[0]["equity"]
        current = today_equity[-1]["equity"]
        loss_pct = (day_start - current) / day_start * 100 if day_start > 0 else 0
        if loss_pct > 15:
            self.daily_pause_until = (datetime.now(timezone.utc) + timedelta(hours=24)).isoformat()
            self._trigger_kill_switch(f"Daily loss {loss_pct:.1f}% > 15%, pausing 24h")
            return True
        return False

    def _is_regime_friendly(self) -> bool:
        return is_martingale_friendly_v2(self.current_regime) is True

    # ── Equity & logging ──────────────────────────────────────────────
    def _calc_equity(self) -> float:
        open_value = sum(d.total_qty * self.current_price for d in self.open_deals)
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
        path = LIVE_DIR / "equity.csv"
        write_header = not path.exists()
        with open(path, "a", newline="") as f:
            w = csv.writer(f)
            if write_header:
                w.writerow(["timestamp", "equity", "cash", "open_deals"])
            w.writerow([rec["timestamp"], rec["equity"], rec["cash"], rec["open_deals"]])

    def _log_trade(self, action: str, deal_id: int, price: float, amount: float, so_count: int):
        path = LIVE_DIR / "trades.csv"
        write_header = not path.exists()
        with open(path, "a", newline="") as f:
            w = csv.writer(f)
            if write_header:
                w.writerow(["timestamp", "action", "symbol", "deal_id", "price", "amount", "so_count", "cash", "equity"])
            equity = self._calc_equity()
            w.writerow([datetime.now(timezone.utc).isoformat(), action, self.symbol, deal_id,
                        f"{price:.6f}", f"{amount:.2f}", so_count, f"{self.cash:.2f}", f"{equity:.2f}"])

    def _send_daily_summary(self):
        now = datetime.now(timezone.utc)
        today = now.strftime("%Y-%m-%d")
        if self._last_daily_summary == today:
            return
        if now.hour == 0 and now.minute < (TF_SECONDS.get(self.timeframe, 300) // 60 + 1):
            equity = self._calc_equity()
            pnl = equity - self.cfg.initial_capital
            msg = (f"📊 <b>Daily Summary</b> ({today})\n"
                   f"Equity: ${equity:.2f}\nPnL: ${pnl:+.2f} ({pnl/self.cfg.initial_capital*100:+.1f}%)\n"
                   f"Open Deals: {len(self.open_deals)}\nRegime: {self.current_regime}")
            send_telegram(msg)
            self._last_daily_summary = today

    def _print_status(self):
        equity = self._calc_equity()
        pnl = equity - self.cfg.initial_capital
        pnl_pct = pnl / self.cfg.initial_capital * 100
        peak = max((e["equity"] for e in self.equity_history), default=equity)
        dd = (peak - equity) / peak * 100 if peak > 0 else 0
        mode = "[DRY-RUN] " if self.dry_run else ""

        print(f"\n{'='*70}")
        print(f"  {mode}📊 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | Equity: ${equity:.2f} | PnL: ${pnl:+.2f} ({pnl_pct:+.1f}%) | DD: {dd:.1f}%")
        print(f"  {self.symbol}: ${self.current_price:.4f} | Regime: {self.current_regime} | Open: {len(self.open_deals)}")
        for d in self.open_deals:
            upnl = d.unrealized_pnl(self.current_price)
            print(f"    Deal#{d.deal_id}: entry=${d.avg_entry:.4f} SOs={d.so_count} uPnL=${upnl:+.2f} pending_SOs={len(d.pending_so_ids)}")
        print(f"  Closed: {len(self.closed_deals)} | Cash: ${self.cash:.2f}")
        cb = "🔴 TRIGGERED" if self.circuit_breaker_triggered else "🟢 OK"
        print(f"  Circuit Breaker: {cb}")
        print(f"{'='*70}")

    # ── Status for dashboard ──────────────────────────────────────────
    def status(self) -> dict:
        equity = self._calc_equity()
        pnl = equity - self.cfg.initial_capital
        peak = max((e["equity"] for e in self.equity_history), default=equity)
        dd = (peak - equity) / peak * 100 if peak > 0 else 0
        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "running": self._running,
            "dry_run": self.dry_run,
            "equity": round(equity, 2),
            "cash": round(self.cash, 2),
            "pnl": round(pnl, 2),
            "pnl_pct": round(pnl / self.cfg.initial_capital * 100, 2),
            "drawdown_pct": round(dd, 2),
            "peak_equity": round(peak, 2),
            "initial_capital": self.cfg.initial_capital,
            "circuit_breaker": self.circuit_breaker_triggered,
            "max_drawdown_threshold": self.max_drawdown_pct,
            "symbol": self.symbol,
            "current_price": self.current_price,
            "timeframe": self.timeframe,
            "regime": self.current_regime,
            "open_deals": [{
                "deal_id": d.deal_id, "symbol": d.symbol,
                "avg_entry": round(d.avg_entry, 6), "so_count": d.so_count,
                "invested": round(d.total_invested, 2), "qty": round(d.total_qty, 6),
                "current_price": round(self.current_price, 6),
                "unrealized_pnl": round(d.unrealized_pnl(self.current_price), 2),
                "pending_sos": len(d.pending_so_ids),
                "regime_at_open": d.regime_at_open,
            } for d in self.open_deals],
            "closed_deals_count": len(self.closed_deals),
            "closed_deals_recent": [{
                "deal_id": d.deal_id, "symbol": d.symbol,
                "avg_entry": round(d.avg_entry, 6),
                "close_price": round(d.close_price, 6) if d.close_price else None,
                "so_count": d.so_count, "pnl": round(d.realized_pnl(), 2),
                "close_time": d.close_time,
            } for d in self.closed_deals[-50:]],
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
            "equity_history": self.equity_history[-200:],
        }

    # ── State persistence ─────────────────────────────────────────────
    def save_state(self):
        state = {
            "cash": self.cash,
            "deal_counter": self.deal_counter,
            "open_deals": [d.to_dict() for d in self.open_deals],
            "closed_deals": [d.to_dict() for d in self.closed_deals],
            "equity_history": self.equity_history,
            "current_regime": self.current_regime,
            "current_price": self.current_price,
            "circuit_breaker_triggered": self.circuit_breaker_triggered,
            "daily_pause_until": self.daily_pause_until,
            "start_time": self.start_time,
            "deal_counter": self.deal_counter,
            "_last_daily_summary": self._last_daily_summary,
        }
        with open(LIVE_DIR / "state.json", "w") as f:
            json.dump(state, f, indent=2)
        with open(LIVE_DIR / "status.json", "w") as f:
            json.dump(self.status(), f, indent=2)

    def load_state(self):
        path = LIVE_DIR / "state.json"
        if not path.exists():
            return
        try:
            with open(path) as f:
                state = json.load(f)
            self.cash = state["cash"]
            self.deal_counter = state["deal_counter"]
            self.open_deals = [LiveDeal.from_dict(d) for d in state["open_deals"]]
            self.closed_deals = [LiveDeal.from_dict(d) for d in state["closed_deals"]]
            self.equity_history = state.get("equity_history", [])
            self.current_regime = state.get("current_regime", "UNKNOWN")
            self.current_price = state.get("current_price", 0)
            self.circuit_breaker_triggered = state.get("circuit_breaker_triggered", False)
            self.daily_pause_until = state.get("daily_pause_until")
            self.start_time = state.get("start_time")
            self._last_daily_summary = state.get("_last_daily_summary")
            print(f"  ♻️  Loaded state: {len(self.open_deals)} open, {len(self.closed_deals)} closed, cash=${self.cash:.2f}")
        except Exception as e:
            print(f"  [WARN] Failed to load state: {e}")

    def stop(self):
        self._running = False

    # ── Main loop ─────────────────────────────────────────────────────
    def start(self):
        self._running = True
        if not self.start_time:
            self.start_time = datetime.now(timezone.utc).isoformat()

        poll_seconds = TF_SECONDS.get(self.timeframe, 300)
        mode = "DRY-RUN" if self.dry_run else "LIVE"
        print(f"\n  🚀 {mode} trader started! Polling every {poll_seconds}s ({self.timeframe})")
        print(f"  Symbol: {self.symbol} | Capital: ${self.cfg.initial_capital:.0f} | Cash: ${self.cash:.2f}")
        print(f"  TP: {self.cfg.take_profit_pct}% | Max SOs: {self.cfg.max_safety_orders}")
        print(f"  Max Drawdown: {self.max_drawdown_pct}%")

        if not self.dry_run:
            send_telegram(f"🚀 <b>Live Trader Started</b>\nSymbol: {self.symbol}\nCapital: ${self.cfg.initial_capital:.0f}")

        while self._running:
            try:
                # Fetch candles
                df = self._fetch_candles(limit=300)
                if df.empty:
                    print("  [WARN] No candles returned")
                    time.sleep(30)
                    continue

                self.current_price = float(df.iloc[-1]["close"])
                self.consecutive_errors = 0

                # Detect regime
                old_regime = self.current_regime
                self.current_regime = self._detect_regime(df)
                if old_regime != self.current_regime and old_regime != "UNKNOWN":
                    print(f"  🔄 Regime: {old_regime} → {self.current_regime}")

                # Check existing deals
                for deal in list(self.open_deals):
                    if self.dry_run:
                        # In dry-run, simulate TP check
                        tp_price = deal.avg_entry * (1 + self.cfg.take_profit_pct / 100)
                        if self.current_price >= tp_price:
                            print(f"  [DRY-RUN] TP would trigger for deal#{deal.deal_id} @ ${tp_price:.4f}")
                    else:
                        self._check_deal_orders(deal)

                # Kill switch checks
                paused = self._check_daily_loss()
                self._check_circuit_breaker()

                # Open new deal?
                can_trade = (
                    not self.circuit_breaker_triggered
                    and not paused
                    and self._is_regime_friendly()
                    and len(self.open_deals) < self.cfg.max_active_deals
                    and self.cash >= self.cfg.base_order_size
                )
                if can_trade:
                    self._open_new_deal(self.current_price)
                elif self.dry_run and len(self.open_deals) == 0:
                    friendly = self._is_regime_friendly()
                    print(f"  [DRY-RUN] Regime={self.current_regime} friendly={friendly} "
                          f"cb={self.circuit_breaker_triggered} cash=${self.cash:.2f}")
                    if friendly:
                        print(f"  [DRY-RUN] WOULD open deal @ ${self.current_price:.4f}")

                # Record equity & save
                self._record_equity()
                self._send_daily_summary()
                self._print_status()
                self.save_state()

                time.sleep(poll_seconds)

            except KeyboardInterrupt:
                break
            except Exception as e:
                self.consecutive_errors += 1
                print(f"\n  ❌ Error: {e}")
                traceback.print_exc()
                if self.consecutive_errors >= 3:
                    self._trigger_kill_switch(f"3+ errors: {e}")
                time.sleep(30)

        print("\n  Trader stopped. Saving state...")
        self.save_state()
        if not self.dry_run:
            send_telegram("⏹ <b>Live Trader Stopped</b>")
