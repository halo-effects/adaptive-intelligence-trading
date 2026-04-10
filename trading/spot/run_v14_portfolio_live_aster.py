#!/usr/bin/env python3
"""
V14 Portfolio Manager — Live Trading Bot (Aster DEX Perpetuals)
==============================================================
Production live trading runner for V14PM on Aster DEX Perps.

Built from run_v14_live_aster.py (proven live execution) with PM components:
  - CapitalRouter (multi-coin capital allocation)
  - Cycle Scanner integration (coin selection and ranking)
  - Portfolio Regime Monitor (weighted composite, tiered alerts)
  - Telegram command interface (APPROVE, DENY, PAUSE, RESUME, CLOSE)
  - Wind-down phase (graceful direction change)
  - Exchange-as-truth: positions synced from exchange every cycle
  - Resting limit orders (TP executed by exchange, not polling)
  - Actual fill prices from exchange (never engine fallback)
  - No LIVE GUARD, no engine rollbacks, no periodic reconciliation

Architecture (2026-03-21):
  Exchange API is the SINGLE source of truth for all position data.
  _sync_positions_from_exchange() overwrites engine state every main loop
  iteration before candle processing. Engine is used only for signal
  generation; all position fields come from exchange.

Unified production profile (locked 2026-03-19):
  - Exchange: Aster DEX Perpetuals (1x leverage, no liquidation risk)
  - Grid: High (BO=40%, Dev=1.5%, Mult=1.5x, 12 layers, TP=1.5%)
  - Scanner: 30d window, Trend Multiplier
  - No --profile or --exchange flags: always Aster, always High

Usage:
  # First launch:
  python -u -m trading.spot.run_v14_portfolio_live_aster --capital 340 --confirm --fresh

  # Restart / crash recovery:
  python -u -m trading.spot.run_v14_portfolio_live_aster --capital 340 --confirm --skip-backfill
"""

import argparse
import csv
import json
import logging
import os
import signal
import sqlite3
import sys
import io
import time
import traceback
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, List, Optional

import ccxt

if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

_WORKSPACE = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_WORKSPACE))

from trading.spot.v14_lifecycle_engine import V14LifecycleEngine
from trading.spot.v14_capital_manager import (
    CapitalRouter, EQUITY_TIER_CAPS, EQUITY_TIER_SPLITS,
    load_capital_ledger, save_capital_ledger, record_ledger_transaction,
    get_ledger_summary,
)
from trading.spot.exchange_client import SpotExchangeClient

# ── Logging ─────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(
            _WORKSPACE / "trading" / "spot" / "live" / "v14pm" / "bot.log",
            encoding="utf-8"
        ),
    ],
)
logger = logging.getLogger("v14_pm_live")

# ── Constants ────────────────────────────────────────────────────────────────

DB_PATH = Path(os.environ.get(
    "AIT_CANDLES_DB",
    str(_WORKSPACE / "trading" / "spot" / "data" / "candles.db")
))
OUTPUT_DIR = _WORKSPACE / "trading" / "spot" / "live" / "v14pm"
SCANNER_PATH = Path(os.environ.get(
    "AIT_SCANNER_JSON",
    str(_WORKSPACE / "docs" / "data" / "v14" / "cycle_scanner.json")
))
LIVE_POLL_INTERVAL = 65        # seconds between exchange polls
TP_CHECK_INTERVAL  = 65        # seconds between TP order status checks
STATUS_WRITE_INTERVAL = 60     # seconds between status.json writes
REGIME_EVAL_HOUR   = 0         # UTC hour for daily regime evaluation (midnight)
# REENTRY_COOLDOWN removed — old bot never had it, it masked bugs
TG_PREFIX          = "[V14-PM]"

# Capital change detection thresholds (Upgrade 1)
CAPITAL_DRIFT_MIN_USD = 5.0    # Minimum absolute change to trigger detection
CAPITAL_DRIFT_MIN_PCT = 0.02   # Minimum percentage change (2%)
LEDGER_PATH = OUTPUT_DIR / "capital_ledger.json"

# ── Unified production profile ────────────────────────────────────────────────
PRODUCTION_PROFILE = "high"
PRODUCTION_LEVERAGE = 1.0

# Bot operational states
class BotState:
    RUNNING   = "RUNNING"    # Normal trading — entries and DCA layers active
    PAUSED    = "PAUSED"     # Operator freeze — no new entries/layers, TPs active
    WIND_DOWN = "WIND_DOWN"  # Regime change approved — winding down before flip


# ── Telegram ─────────────────────────────────────────────────────────────────

def send_telegram(msg: str, buttons: list = None):
    """Send a Telegram message, optionally with inline keyboard buttons."""
    token   = os.environ.get("AIT_TG_TOKEN", "")
    chat_id = os.environ.get("AIT_TG_CHAT_ID", "")
    if not (token and chat_id):
        return
    try:
        import requests
        payload = {
            "chat_id": chat_id,
            "text": msg,
            "parse_mode": "HTML",
        }
        if buttons:
            payload["reply_markup"] = {"inline_keyboard": buttons}
        requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json=payload,
            timeout=10,
        )
    except Exception as e:
        logger.warning(f"Telegram send failed: {e}")


def get_telegram_updates(offset: int = 0) -> list:
    """Fetch new Telegram updates since offset."""
    token = os.environ.get("AIT_TG_TOKEN", "")
    if not token:
        return []
    try:
        import requests
        r = requests.get(
            f"https://api.telegram.org/bot{token}/getUpdates",
            params={"offset": offset, "timeout": 0, "limit": 10},
            timeout=5,
        )
        if r.ok:
            return r.json().get("result", [])
    except Exception:
        pass
    return []


# ── Trade Tracker ─────────────────────────────────────────────────────────────

class TradeTracker:
    """Records closed trade history to CSV. Exchange fills are truth."""

    def __init__(self, output_dir: Path):
        self.output_dir = output_dir
        self.trades: List[dict] = []
        self._deal_counter = 0
        self._open_deals: Dict[str, dict] = {}
        self._existing_keys: set = set()

    def load_existing(self):
        """Load existing trades.csv so history survives restarts."""
        csv_path = self.output_dir / "trades.csv"
        if not csv_path.exists():
            return
        try:
            with open(csv_path, "r") as f:
                reader = csv.DictReader(f)
                rows = list(reader)
            for row in rows:
                key = f"{row['symbol']}|{row.get('open_time','')}|{row.get('close_time','')}"
                self._existing_keys.add(key)
                deal_id = int(row.get("deal_id", 0))
                if deal_id > self._deal_counter:
                    self._deal_counter = deal_id
            self.trades = [{k: v for k, v in r.items()} for r in rows]
            logger.info(f"Loaded {len(self.trades)} existing trades from CSV")
        except Exception as e:
            logger.error(f"Failed to load trades.csv: {e}")

    def on_buy(self, symbol: str, qty: float, price: float, ts: datetime):
        key = f"{symbol}:long"
        if key not in self._open_deals:
            self._deal_counter += 1
            self._open_deals[key] = {
                "deal_id": self._deal_counter,
                "symbol": symbol,
                "open_time": ts.isoformat(),
                "layers": 0,
                "invested": 0.0,
            }
        deal = self._open_deals[key]
        deal["layers"] += 1
        deal["invested"] += qty * price

    def on_sell(self, symbol: str, qty: float, actual_price: float,
                actual_proceeds: float, fee: float, ts: datetime) -> dict:
        key = f"{symbol}:long"
        deal = self._open_deals.pop(key, None)
        if not deal:
            return {}
        invested = deal["invested"]
        pnl = actual_proceeds - invested - fee
        ret_pct = (pnl / invested * 100) if invested > 0 else 0.0
        open_dt = datetime.fromisoformat(deal["open_time"])
        duration_h = (ts - open_dt).total_seconds() / 3600
        trade_key = f"{symbol}|{deal['open_time']}|{ts.isoformat()}"
        if trade_key in self._existing_keys:
            return {}
        self._existing_keys.add(trade_key)
        record = {
            "deal_id": deal["deal_id"],
            "symbol": symbol,
            "open_time": deal["open_time"],
            "close_time": ts.isoformat(),
            "layers": deal["layers"],
            "invested": round(invested, 4),
            "proceeds": round(actual_proceeds, 4),
            "fee": round(fee, 4),
            "pnl": round(pnl, 4),
            "return_pct": round(ret_pct, 2),
            "duration_h": round(duration_h, 1),
            "fill_price": round(actual_price, 8),
            "recorded_at": datetime.now(timezone.utc).isoformat(),
        }
        self.trades.append(record)
        return record

    def save_csv(self):
        if not self.trades:
            return
        fieldnames = [
            "deal_id", "symbol", "open_time", "close_time", "layers",
            "invested", "proceeds", "fee", "pnl", "return_pct",
            "duration_h", "fill_price", "recorded_at",
        ]
        path = self.output_dir / "trades.csv"
        tmp  = path.with_suffix(".tmp")
        try:
            with open(tmp, "w", newline="", encoding="utf-8") as f:
                w = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
                w.writeheader()
                w.writerows(self.trades)
            tmp.replace(path)
        except Exception as e:
            logger.error(f"Failed to save trades.csv: {e}")

    @property
    def deal_count(self) -> int:
        return len(self.trades)

    @property
    def win_count(self) -> int:
        return sum(1 for t in self.trades if float(t.get("pnl", 0)) > 0)

    @property
    def total_pnl(self) -> float:
        return sum(float(t.get("pnl", 0)) for t in self.trades)


# ── Exchange Client Wrapper ───────────────────────────────────────────────────

class AsterPerpClient:
    """
    Aster DEX Perpetuals client using native ccxt.aster.
    Uses defaultType=future to route to fapi endpoints.
    Handles order placement, TP limit orders, balance queries,
    and fill price retrieval.
    """

    def __init__(self, api_key: str, api_secret: str, dry_run: bool = False):
        self.dry_run = dry_run
        self._exchange = ccxt.aster({
            "apiKey": api_key,
            "secret": api_secret,
            "enableRateLimit": True,
            "options": {"defaultType": "future"},
            "timeout": 15000,  # 15s hard timeout on all API calls (prevent hangs)
        })
        if not dry_run:
            self._exchange.load_markets()

        # Track which symbols we've already set leverage for (avoid repeat API calls)
        self._leverage_set: set = set()

    def ensure_leverage(self, db_symbol: str, leverage: float = 1.0):
        """Set leverage for a symbol on the exchange. Called once per symbol.
        Aster defaults perp pairs to 5x Cross — we must explicitly set 1x."""
        if self.dry_run or db_symbol in self._leverage_set:
            return
        sym = self._aster_symbol(db_symbol)
        try:
            self._exchange.set_leverage(int(leverage), sym)
            self._leverage_set.add(db_symbol)
            logger.info(f"Exchange leverage set to {int(leverage)}x for {db_symbol} ({sym})")
        except Exception as e:
            logger.warning(f"set_leverage({db_symbol}, {leverage}x) failed: {e}")

    def _aster_symbol(self, db_symbol: str) -> str:
        """Convert DB symbol (e.g. PEPE/USDT) to Aster perp symbol.
        Handles 1000-prefix for PEPE, BONK, FLOKI."""
        base = db_symbol.split("/")[0]
        prefix_coins = {"PEPE": "1000PEPE", "BONK": "1000BONK", "FLOKI": "1000FLOKI"}
        exchange_base = prefix_coins.get(base, base)
        return f"{exchange_base}/USDT:USDT"

    def fetch_balance(self) -> float:
        """Return available (free) USDT balance in Perp account.
        Use for order-sizing checks where you need available margin.
        """
        if self.dry_run:
            return 0.0
        try:
            bal = self._exchange.fetch_balance({"type": "future"})
            return float(bal.get("USDT", {}).get("free", 0))
        except Exception as e:
            logger.error(f"fetch_balance failed: {e}")
            return 0.0

    def fetch_full_balance(self) -> dict:
        """Return full USDT balance breakdown (free + total) for equity calcs.
        Mirrors V14 Live's executor.get_balance() pattern.
        """
        if self.dry_run:
            return {"usdt_free": 0.0, "usdt_total": 0.0}
        try:
            bal = self._exchange.fetch_balance({"type": "future"})
            usdt = bal.get("USDT", {})
            return {
                "usdt_free": float(usdt.get("free", 0)),
                "usdt_total": float(usdt.get("total", 0)),
            }
        except Exception as e:
            logger.error(f"fetch_full_balance failed: {e}")
            return {"usdt_free": 0.0, "usdt_total": 0.0}

    def fetch_ticker_price(self, db_symbol: str) -> float:
        """Fetch current market price."""
        try:
            sym = self._aster_symbol(db_symbol)
            ticker = self._exchange.fetch_ticker(sym)
            price = ticker.get("last") or ticker.get("close") or 0.0
            # Reverse 1000-prefix scaling
            base = db_symbol.split("/")[0]
            if base in ("PEPE", "BONK", "FLOKI"):
                price = price / 1000.0
            return float(price)
        except Exception as e:
            logger.error(f"fetch_ticker_price({db_symbol}) failed: {e}")
            return 0.0

    def create_market_buy(self, db_symbol: str, qty: float) -> dict:
        """Open/add to long position via market buy."""
        sym = self._aster_symbol(db_symbol)
        base = db_symbol.split("/")[0]
        # Scale qty for 1000-prefix coins
        exchange_qty = qty * 1000 if base in ("PEPE", "BONK", "FLOKI") else qty
        if self.dry_run:
            price = self.fetch_ticker_price(db_symbol)
            return {"status": "dry_run", "price": price, "qty": qty,
                    "proceeds": 0, "average": price}
        try:
            logger.info(f"MARKET BUY {db_symbol} qty={qty:.8f} ({sym})")
            order = self._exchange.create_market_buy_order(sym, exchange_qty,
                                                           params={"positionSide": "BOTH"})
            fill = order.get("average") or order.get("price")
            if not fill:
                # Fetch actual trade fills from exchange — more accurate than ticker
                logger.warning(f"Exchange did not return fill price for BUY — fetching trades")
                try:
                    import time as _time
                    _time.sleep(1)  # Give exchange time to settle
                    trades = self._exchange.fetch_my_trades(sym, limit=5)
                    if trades:
                        # Use the most recent trade matching our order
                        latest = trades[-1]
                        fill = float(latest.get("price", 0))
                        logger.info(f"Got fill price from trades: ${fill}")
                except Exception:
                    pass
                if not fill:
                    fill = self.fetch_ticker_price(db_symbol)
                    logger.warning(f"Fell back to ticker price: ${fill}")
            else:
                fill = float(fill)
            # Reverse 1000-prefix scaling on price
            if base in ("PEPE", "BONK", "FLOKI"):
                fill = fill / 1000.0
            filled_qty = float(order.get("filled") or exchange_qty)
            if base in ("PEPE", "BONK", "FLOKI"):
                filled_qty = filled_qty / 1000.0
            cost = float(order.get("cost") or fill * filled_qty)
            fee  = float((order.get("fee") or {}).get("cost") or 0)
            return {
                "status": "filled",
                "price": fill,
                "qty": filled_qty,
                "cost": cost,
                "fee": fee,
                "order_id": order.get("id"),
            }
        except Exception as e:
            logger.error(f"create_market_buy({db_symbol}) failed: {e}")
            return {}

    def create_market_sell(self, db_symbol: str, qty: float) -> dict:
        """Close long position via market sell."""
        sym = self._aster_symbol(db_symbol)
        base = db_symbol.split("/")[0]
        exchange_qty = qty * 1000 if base in ("PEPE", "BONK", "FLOKI") else qty
        if self.dry_run:
            price = self.fetch_ticker_price(db_symbol)
            return {"status": "dry_run", "price": price, "qty": qty,
                    "proceeds": price * qty, "average": price}
        try:
            logger.info(f"MARKET SELL {db_symbol} qty={qty:.8f} ({sym})")
            order = self._exchange.create_market_sell_order(sym, exchange_qty,
                                                            params={"positionSide": "BOTH", "reduceOnly": True})
            fill = order.get("average") or order.get("price")
            if not fill:
                logger.warning(f"Exchange did not return fill price for SELL — fetching ticker")
                fill = self.fetch_ticker_price(db_symbol)
            else:
                if base in ("PEPE", "BONK", "FLOKI"):
                    fill = float(fill) / 1000.0
                else:
                    fill = float(fill)
            filled_qty = float(order.get("filled") or exchange_qty)
            if base in ("PEPE", "BONK", "FLOKI"):
                filled_qty = filled_qty / 1000.0
            proceeds = float(order.get("cost") or fill * filled_qty)
            fee  = float((order.get("fee") or {}).get("cost") or 0)
            return {
                "status": "filled",
                "price": fill,
                "qty": filled_qty,
                "proceeds": proceeds,
                "fee": fee,
                "order_id": order.get("id"),
            }
        except Exception as e:
            logger.error(f"create_market_sell({db_symbol}) failed: {e}")
            return {}

    def place_limit_sell(self, db_symbol: str, qty: float, price: float) -> Optional[str]:
        """Place a resting limit sell (TP order) on the exchange. Returns order_id."""
        sym = self._aster_symbol(db_symbol)
        base = db_symbol.split("/")[0]
        exchange_qty   = qty   * 1000 if base in ("PEPE", "BONK", "FLOKI") else qty
        exchange_price = price * 1000 if base in ("PEPE", "BONK", "FLOKI") else price
        if self.dry_run:
            return f"dry_run_tp_{db_symbol}_{int(time.time())}"
        try:
            logger.info(f"PLACE TP LIMIT SELL {db_symbol} qty={qty:.8f} @ ${price:.8f}")
            order = self._exchange.create_limit_sell_order(
                sym, exchange_qty, exchange_price,
                params={"timeInForce": "GTC", "positionSide": "BOTH", "reduceOnly": True}
            )
            oid = order.get("id")
            logger.info(f"TP limit order placed: {oid}")
            return oid
        except Exception as e:
            logger.error(f"place_limit_sell({db_symbol}) failed: {e}")
            return None

    def cancel_tp_order(self, db_symbol: str, order_id: str) -> bool:
        """Cancel a resting TP limit order."""
        sym = self._aster_symbol(db_symbol)
        if self.dry_run:
            return True
        try:
            self._exchange.cancel_order(order_id, sym)
            logger.info(f"Cancelled TP order {order_id} for {db_symbol}")
            return True
        except Exception as e:
            logger.warning(f"cancel_tp_order({db_symbol}, {order_id}): {e}")
            return False

    def check_order_status(self, db_symbol: str, order_id: str) -> dict:
        """Check if a TP limit order has been filled. Returns fill info or empty."""
        sym = self._aster_symbol(db_symbol)
        if self.dry_run:
            return {}
        try:
            order = self._exchange.fetch_order(order_id, sym)
            status = order.get("status", "")
            if status in ("closed", "filled"):
                base = db_symbol.split("/")[0]
                fill = order.get("average") or order.get("price") or 0
                if base in ("PEPE", "BONK", "FLOKI") and fill:
                    fill = float(fill) / 1000.0
                qty = float(order.get("filled") or 0)
                if base in ("PEPE", "BONK", "FLOKI"):
                    qty = qty / 1000.0
                proceeds = float(order.get("cost") or float(fill) * qty)
                fee = float((order.get("fee") or {}).get("cost") or 0)
                return {
                    "filled": True,
                    "price": float(fill),
                    "qty": qty,
                    "proceeds": proceeds,
                    "fee": fee,
                }
            return {"filled": False, "status": status}
        except Exception as e:
            logger.warning(f"check_order_status({order_id}): {e}")
            return {}

    def fetch_open_orders(self, db_symbol: str = None) -> list:
        """Fetch all open orders, optionally filtered by symbol.
        Returns list of dicts with id, side, type, price, amount, symbol."""
        try:
            sym = self._aster_symbol(db_symbol) if db_symbol else None
            orders = self._exchange.fetch_open_orders(sym)
            return [
                {
                    "id": str(o.get("id")),
                    "side": o.get("side"),
                    "type": o.get("type"),
                    "price": float(o.get("price") or 0),
                    "amount": float(o.get("amount") or 0),
                    "symbol": o.get("symbol", ""),
                    "timestamp": o.get("timestamp", 0),
                }
                for o in orders
            ]
        except Exception as e:
            logger.warning(f"fetch_open_orders failed: {e}")
            return []

    def fetch_open_positions(self) -> dict:
        """Return open perp positions. Keys are base symbols."""
        if self.dry_run:
            return {}
        try:
            positions = self._exchange.fetch_positions()
            result = {}
            for p in positions:
                contracts = float(p.get("contracts") or p.get("contractSize") or 0)
                if contracts == 0:
                    continue
                symbol = p.get("symbol", "")
                raw_base = symbol.split("/")[0]
                is_1000 = raw_base.startswith("1000")
                base = raw_base[4:] if is_1000 else raw_base
                # Reverse 1000-prefix scaling: exchange reports in 1000PEPE units
                qty = contracts / 1000.0 if is_1000 else contracts
                entry = float(p.get("entryPrice") or 0)
                entry = entry / 1000.0 if is_1000 else entry
                result[base] = {
                    "qty": qty,
                    "entry_price": entry,
                    "side": p.get("side", "long"),
                    "unrealized_pnl": float(p.get("unrealizedPnl") or 0),
                }
            return result
        except Exception as e:
            logger.error(f"fetch_open_positions failed: {e}")
            return {}

    def fetch_funding_history(self, db_symbol: str, since_ms: int = None) -> list:
        """Fetch funding payment history for a symbol."""
        sym = self._aster_symbol(db_symbol)
        if self.dry_run:
            return []
        try:
            params = {}
            if since_ms:
                params["startTime"] = since_ms
            history = self._exchange.fetch_funding_history(sym, params=params)
            return history or []
        except Exception as e:
            logger.warning(f"fetch_funding_history({db_symbol}): {e}")
            return []


# ── Coin State ────────────────────────────────────────────────────────────────

class CoinState:
    """Tracks live state for a single coin position."""

    def __init__(self, symbol: str, allocated_capital: float):
        self.symbol = symbol
        self.allocated_capital = allocated_capital
        self.engine: Optional[V14LifecycleEngine] = None
        self.tp_order_id: Optional[str] = None
        self.tp_limit_price: Optional[float] = None   # Audit #8: store TP price separately
        self.last_candle_ts: int = 0
        self.cumulative_funding: float = 0.0
        self.last_funding_check_ms: int = 0
        self._last_buy_time: float = 0.0  # Dedup guard: timestamp of last executed buy
        self.layer_count: int = 0         # Layers in current position (synced from exchange)
        self.paused: bool = False         # Per-coin pause (Upgrade 2): blocks new orders, TPs active
        # Per-coin regime flagging (Upgrade 3)
        self.regime_flagged: bool = False              # True when coin signals conflict with global direction
        self.coin_regime_signal: Optional[str] = None  # "TOP" or "BOTTOM"
        self.flagged_at: Optional[str] = None          # ISO timestamp when flagged
        self.regime_cooldown_until: float = 0.0        # Unix timestamp — no re-flag before this

    def to_dict(self) -> dict:
        return {
            "symbol": self.symbol,
            "allocated_capital": self.allocated_capital,
            "tp_order_id": self.tp_order_id,
            "tp_limit_price": self.tp_limit_price,
            "last_candle_ts": self.last_candle_ts,
            "cumulative_funding": self.cumulative_funding,
            "last_funding_check_ms": self.last_funding_check_ms,
            "layer_count": self.layer_count,
            "paused": self.paused,
            "regime_flagged": self.regime_flagged,
            "coin_regime_signal": self.coin_regime_signal,
            "flagged_at": self.flagged_at,
            "regime_cooldown_until": self.regime_cooldown_until,
        }


# ── Main Bot ──────────────────────────────────────────────────────────────────

class V14PortfolioLiveAster:
    """
    V14PM Live Bot for Aster DEX Perpetuals.

    Execution layer from run_v14_live_aster.py (battle-tested with real money).
    PM logic from run_v14_portfolio_paper.py (capital rotation, regime detection).

    Architecture: Exchange-as-truth
      - _sync_positions_from_exchange() runs at top of every main loop iteration
      - Engine position fields (long_coins, long_cost, etc.) are overwritten from
        exchange every cycle — engine is used only for signal generation
      - Resting limit orders: Exchange handles TP, not polling
      - Fill price from exchange: Never fall back to engine price
      - PnL from actual proceeds: Not engine estimates
      - No LIVE GUARD, no engine rollbacks, no periodic reconciliation
    """

    def __init__(self, capital: float, confirm: bool = False,
                 skip_backfill: bool = False, fresh: bool = False):
        if not confirm:
            raise ValueError("Must pass --confirm for live trading")

        self.capital = capital
        self.skip_backfill = skip_backfill
        self.fresh = fresh
        self.profile = PRODUCTION_PROFILE
        self.leverage = PRODUCTION_LEVERAGE

        # Bot state machine
        self.bot_state = BotState.RUNNING
        self._wind_down_direction: Optional[str] = None  # target direction after wind-down

        # Per-coin state
        self.coins: Dict[str, CoinState] = {}

        # Capital router
        self.router = CapitalRouter(initial_capital=capital)

        # Trade tracker
        self.tracker = TradeTracker(OUTPUT_DIR)
        self.tracker.load_existing()

        # Exchange client
        api_key    = os.environ.get("ASTER_API_KEY", "")
        api_secret = os.environ.get("ASTER_API_SECRET", "")
        if not (api_key and api_secret):
            raise ValueError("ASTER_API_KEY and ASTER_API_SECRET must be set")
        self.client = AsterPerpClient(api_key, api_secret)

        # CFGI state
        self._cfgi_market: Optional[float] = None
        self._cfgi_coins: Dict[str, float] = {}
        self._cfgi_last_poll: float = 0.0

        # Regime monitor state
        self._regime_signal_count: int = 0
        self._regime_signal_type: Optional[str] = None  # "TOP" or "BOTTOM"
        self._regime_alert_state: str = "NONE"  # NONE, AWAITING_APPROVAL
        self._regime_last_eval_date: Optional[object] = None

        # Telegram command processing
        self._tg_update_offset: int = 0
        self._last_tg_check: float = 0.0

        # Startup time
        self._start_time = datetime.now(timezone.utc)

        # Shutdown flag
        self._shutdown = False

        # Daily rebalance tracking
        self._last_rebalance_date = None
        self._last_status_write: float = 0.0

        # Re-entry cooldown (prevents rapid-fire after TP fills)
        # _reentry_cooldown_until removed (dead code — superseded by ORDER_DEDUP_WINDOW)

        # Exchange-as-truth: cached position data (refreshed every cycle by _sync_positions_from_exchange)
        self._exchange_usdt_free: float = 0.0
        self._exchange_usdt_total: float = 0.0
        self._last_exchange_positions: dict = {}

        # Capital tracking (Upgrade 1)
        # self.capital is the bot's tracked capital (seed + deposits - withdrawals).
        # Distinct from equity (which includes unrealized PnL).
        self._tracked_capital: float = capital  # Updated by ledger transactions
        self._init_capital_ledger(capital)

        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        logger.info(
            f"V14PM Live Aster | capital=${capital:.2f} | "
            f"profile={self.profile} | leverage={self.leverage}x | "
            f"30d scanner | Aster Perps"
        )

    # ── State persistence ─────────────────────────────────────────────────────

    def _save_state(self):
        """Persist bot state to state.json (atomic write)."""
        coin_states = {}
        for sym, cs in self.coins.items():
            engine_state = {}
            if cs.engine:
                try:
                    engine_state = cs.engine.snapshot_state()
                except Exception:
                    pass
            coin_states[sym] = {
                **cs.to_dict(),
                "engine_state": engine_state,
            }

        state = {
            "saved_at": datetime.now(timezone.utc).isoformat(),
            "bot_state": self.bot_state,
            "capital": self.capital,
            "coins": coin_states,
            "router": {
                "active_pool_cash": self.router.active_pool_cash,
                "reserve_pool_cash": self.router.reserve_pool_cash,
                "active_allocations": self.router.active_allocations,
                "reserve_allocations": self.router.reserve_allocations,
                "cap_tier_index": self.router._cap_tier_index,
                "split_tier_index": self.router._split_tier_index,
            },
            "regime": {
                "signal_count": self._regime_signal_count,
                "signal_type": self._regime_signal_type,
                "alert_state": self._regime_alert_state,
            },
            "tracked_capital": self._tracked_capital,
            "tg_update_offset": self._tg_update_offset,
            "open_deals": self.tracker._open_deals,
            "last_rebalance_date": str(self._last_rebalance_date) if self._last_rebalance_date else None,
        }

        path = OUTPUT_DIR / "state.json"
        tmp  = path.with_suffix(".tmp")
        try:
            with open(tmp, "w") as f:
                json.dump(state, f, indent=2, default=str)
            tmp.replace(path)
        except Exception as e:
            logger.error(f"Failed to write state.json: {e}")

    def _load_state(self) -> bool:
        """Restore bot state from state.json."""
        path = OUTPUT_DIR / "state.json"
        if not path.exists():
            return False
        try:
            with open(path) as f:
                state = json.load(f)
        except Exception as e:
            logger.error(f"Failed to read state.json: {e}")
            return False

        saved_at = state.get("saved_at", "unknown")
        logger.info(f"Restoring state from {saved_at}")

        self.bot_state = state.get("bot_state", BotState.RUNNING)
        if self.bot_state not in (BotState.RUNNING, BotState.PAUSED, BotState.WIND_DOWN):
            self.bot_state = BotState.RUNNING

        # Restore coin states and engines
        for sym, cs_data in state.get("coins", {}).items():
            cs = CoinState(sym, cs_data.get("allocated_capital", 0))
            cs.tp_order_id = cs_data.get("tp_order_id")
            cs.tp_limit_price = cs_data.get("tp_limit_price")
            cs.last_candle_ts = cs_data.get("last_candle_ts", 0)
            cs.cumulative_funding = cs_data.get("cumulative_funding", 0.0)
            cs.last_funding_check_ms = cs_data.get("last_funding_check_ms", 0)
            cs.layer_count = cs_data.get("layer_count", 0)
            cs.paused = cs_data.get("paused", False)
            cs.regime_flagged = cs_data.get("regime_flagged", False)
            cs.coin_regime_signal = cs_data.get("coin_regime_signal")
            cs.flagged_at = cs_data.get("flagged_at")
            cs.regime_cooldown_until = cs_data.get("regime_cooldown_until", 0.0)

            engine_state = cs_data.get("engine_state", {})
            if engine_state:
                try:
                    capital = engine_state.get("initial_capital", cs.allocated_capital)
                    engine = V14LifecycleEngine(
                        symbol=sym,
                        capital=capital,
                        profile=self.profile,
                        leverage=self.leverage,
                    )
                    engine.restore_state(engine_state)
                    engine._live_mode = True
                    # Propagate live_mode to inner DCA engine (disables paper-trading caps)
                    if engine._engine:
                        engine._engine.live_mode = True

                    # LIVE FIX: Reset engine internal capital to allocated amount.
                    # The engine's paper-capital tracking drifts from reality in live mode
                    # (CapitalRouter manages real capital). A depleted engine capital can
                    # cause order sizes to fall below the $10 minimum, silently blocking
                    # trades via the `order > self.capital` guard in v14_dca_engine.py.
                    #
                    # GAP-13 FIX: Reset capital ALWAYS, not just when no position.
                    # Mid-DCA, the engine capital is irrelevant — the router manages
                    # real capital. But the engine still uses it for order sizing guards.
                    # A depleted paper capital would permanently block further DCA layers.
                    eng_inner = engine._engine
                    if eng_inner:
                        old_cap = eng_inner.capital
                        eng_inner.capital = cs.allocated_capital
                        if eng_inner.long_coins == 0 and eng_inner.short_coins == 0:
                            # No position — also sanitize stale fields
                            eng_inner.long_avg_entry = 0
                            eng_inner.long_tp = 0
                            eng_inner.long_cost = 0
                            eng_inner.long_last_buy = None
                            eng_inner.long_layers = 0
                            if eng_inner.long_trades < 0:
                                eng_inner.long_trades = 0
                        if abs(old_cap - cs.allocated_capital) > 1:
                            logger.info(
                                f"  {sym} engine capital reset: ${old_cap:.2f} -> "
                                f"${cs.allocated_capital:.2f}"
                                f"{' (no position)' if eng_inner.long_coins == 0 else ' (mid-DCA)'}"
                            )

                    cs.engine = engine
                    logger.info(f"  Restored engine for {sym}")
                except Exception as e:
                    logger.error(f"  Failed to restore engine for {sym}: {e}")
            else:
                # No saved engine state — create fresh engine (warmed up for live)
                try:
                    engine = V14LifecycleEngine(
                        symbol=sym,
                        capital=cs.allocated_capital,
                        profile=self.profile,
                        leverage=self.leverage,
                    )
                    engine._live_mode = True
                    if engine._engine:
                        engine._engine.live_mode = True
                    engine._warmed_up = True
                    cs.engine = engine
                    # Set candle ts to NOW — only process future candles, never replay history
                    cs.last_candle_ts = int(time.time() * 1000)
                    logger.info(f"  Created fresh engine for {sym} (no saved state, candle_ts=now)")
                except Exception as e:
                    logger.error(f"  Failed to create engine for {sym}: {e}")

            self.coins[sym] = cs

        # Restore router
        router_state = state.get("router", {})
        if router_state:
            self.router.active_pool_cash     = router_state.get("active_pool_cash",  self.router.active_pool_cash)
            self.router.reserve_pool_cash    = router_state.get("reserve_pool_cash", self.router.reserve_pool_cash)
            self.router.active_allocations   = router_state.get("active_allocations", {})
            self.router.reserve_allocations  = router_state.get("reserve_allocations", {})
            # Restore hysteresis tier indices (survives restart without re-evaluation)
            if "cap_tier_index" in router_state:
                self.router._cap_tier_index = router_state["cap_tier_index"]
                self.router.tier_coin_cap = (
                    EQUITY_TIER_CAPS[self.router._cap_tier_index][1]
                    if self.router._cap_tier_index >= 0 else 0
                )
            if "split_tier_index" in router_state:
                self.router._split_tier_index = router_state["split_tier_index"]

        # Restore regime state
        regime = state.get("regime", {})
        self._regime_signal_count = regime.get("signal_count", 0)
        self._regime_signal_type  = regime.get("signal_type")
        self._regime_alert_state  = regime.get("alert_state", "NONE")

        # Restore tracked capital (Upgrade 1)
        if "tracked_capital" in state:
            self._tracked_capital = state["tracked_capital"]
            self.capital = self._tracked_capital
            logger.info(f"Restored tracked capital: ${self._tracked_capital:.2f}")

        # Restore Telegram offset
        self._tg_update_offset = state.get("tg_update_offset", 0)

        # Restore rebalance date (prevents duplicate rebalance on restart)
        saved_rebalance = state.get("last_rebalance_date")
        if saved_rebalance:
            try:
                from datetime import date as date_cls
                self._last_rebalance_date = date_cls.fromisoformat(saved_rebalance)
                logger.info(f"Restored last rebalance date: {self._last_rebalance_date}")
            except (ValueError, TypeError):
                pass

        # Restore open deals
        open_deals = state.get("open_deals", {})
        for key, deal in open_deals.items():
            self.tracker._open_deals[key] = deal

        logger.info(
            f"State restored: {len(self.coins)} coins, "
            f"bot_state={self.bot_state}, "
            f"regime={self._regime_alert_state}"
        )
        return True

    # ── Exchange-as-truth position sync ──────────────────────────────────────

    def _sync_positions_from_exchange(self):
        """Overwrite engine position state from exchange API every cycle. Exchange is truth."""
        try:
            balance = self.client.fetch_full_balance()
            self._exchange_usdt_free = balance["usdt_free"]
            self._exchange_usdt_total = balance["usdt_total"]
        except Exception as e:
            logger.warning(f"Exchange balance sync failed: {e}")
            return  # Keep previous values

        try:
            positions = self.client.fetch_open_positions()
        except Exception as e:
            logger.warning(f"Exchange position sync failed: {e}")
            return  # Don't overwrite engine with empty data on API failure

        for sym, cs in self.coins.items():
            if not cs.engine or not cs.engine._engine:
                continue
            eng = cs.engine._engine
            base = sym.split("/")[0]
            pos = positions.get(base, {})
            ex_qty = pos.get("qty", 0) or 0
            ex_entry = pos.get("entry_price", 0) or 0

            if ex_qty > 0:
                eng.long_coins = ex_qty
                eng.long_cost = ex_entry * ex_qty
                eng.long_avg_entry = ex_entry
                tp_pct = eng.cfg.DCA_TP_PCT if hasattr(eng, 'cfg') and hasattr(eng.cfg, 'DCA_TP_PCT') else 0.015
                eng.long_tp = ex_entry * (1 + tp_pct)
                # Sync layer count: ensure consistency between CoinState, engine, and exchange
                if cs.layer_count == 0 and ex_qty > 0:
                    # Position exists but layer_count is 0 — derive from engine state
                    cs.layer_count = max(1, eng.long_layers)
                elif cs.layer_count > 0 and ex_qty == 0:
                    # No position but layer_count > 0 — stale, reset
                    cs.layer_count = 0
                # Always sync engine layers to match CoinState
                if eng.long_layers != cs.layer_count:
                    logger.info(
                        f"Layer sync {sym}: eng.long_layers={eng.long_layers} -> "
                        f"cs.layer_count={cs.layer_count}"
                    )
                eng.long_layers = cs.layer_count
            else:
                eng.long_coins = 0.0
                eng.long_cost = 0.0
                eng.long_avg_entry = 0.0
                eng.long_layers = 0
                eng.long_tp = 0.0
                cs.layer_count = 0  # Reset when exchange has no position

        self._last_exchange_positions = positions  # Cache for status write
        logger.debug(
            f"Exchange sync: free=${self._exchange_usdt_free:.2f} "
            f"total=${self._exchange_usdt_total:.2f} "
            f"positions={list(positions.keys())}"
        )

    # ── Capital Ledger & Deposit/Withdrawal Detection (Upgrade 1) ────────────

    def _init_capital_ledger(self, seed_capital: float):
        """Initialize capital ledger with seed entry if it doesn't exist."""
        ledger = load_capital_ledger(LEDGER_PATH)
        if ledger is None:
            record_ledger_transaction(
                LEDGER_PATH, "seed", seed_capital,
                note=f"Initial seed capital at bot startup"
            )
            logger.info(f"Capital ledger initialized with seed=${seed_capital:.2f}")
        else:
            # Ledger exists — use its tracked capital instead of CLI --capital
            self._tracked_capital = ledger.get("current_capital", seed_capital)
            if abs(self._tracked_capital - seed_capital) > 1.0:
                logger.info(
                    f"Capital from ledger: ${self._tracked_capital:.2f} "
                    f"(CLI --capital was ${seed_capital:.2f}, using ledger)"
                )

    def _detect_capital_change(self):
        """Detect deposits/withdrawals by comparing exchange balance to tracked capital.

        Runs every sync cycle. Uses threshold: max($5, 2% of tracked capital).
        When detected:
          - Records to capital ledger
          - Calls router.resize() to adjust pools and tier
          - Sends Telegram alert
        """
        if self._exchange_usdt_total <= 0:
            return  # No exchange data yet

        # Compute drift: exchange total vs tracked capital
        # Exchange total includes unrealized PnL, so subtract it for capital comparison
        total_invested = sum(
            cs.allocated_capital for cs in self.coins.values()
            if cs.engine and cs.engine._engine and cs.engine._engine.long_coins > 0
        )
        total_unrealized = 0.0
        for sym, cs in self.coins.items():
            if not cs.engine or not cs.engine._engine:
                continue
            eng = cs.engine._engine
            if eng.long_coins > 0 and sym in self._last_exchange_positions:
                pos = self._last_exchange_positions.get(sym.split("/")[0], {})
                mark = pos.get("mark_price") or pos.get("entry_price") or 0
                if mark and eng.long_avg_entry:
                    total_unrealized += (mark - eng.long_avg_entry) * eng.long_coins

        # Capital approximation: exchange total minus unrealized PnL
        exchange_capital = self._exchange_usdt_total - total_unrealized
        drift = exchange_capital - self._tracked_capital

        # Threshold: max($5, 2% of tracked capital)
        threshold = max(CAPITAL_DRIFT_MIN_USD,
                        self._tracked_capital * CAPITAL_DRIFT_MIN_PCT)

        if abs(drift) < threshold:
            return  # Within normal range

        # Determine type
        tx_type = "deposit" if drift > 0 else "withdrawal"
        tx_amount = abs(drift)
        drift_pct = abs(drift) / max(self._tracked_capital, 1) * 100

        # Safety: reject withdrawals that would drop capital below total invested
        if tx_type == "withdrawal" and (self._tracked_capital - tx_amount) < total_invested:
            logger.warning(
                f"Withdrawal detected (${tx_amount:.2f}) but would drop capital below "
                f"invested (${total_invested:.2f}). Alerting but not auto-adjusting."
            )
            send_telegram(
                f"⚠️ {TG_PREFIX} <b>Balance drift: -{drift_pct:.1f}%</b>\n"
                f"Exchange capital: ${exchange_capital:.2f}\n"
                f"Tracked capital: ${self._tracked_capital:.2f}\n"
                f"Cannot auto-adjust: invested=${total_invested:.2f}\n"
                f"Use CLOSE positions first, or WITHDRAW {tx_amount:.0f} to force."
            )
            return

        # Record to ledger
        note = f"Auto-detected via exchange sync ({drift_pct:.1f}% drift)"
        record_ledger_transaction(LEDGER_PATH, tx_type, tx_amount, note=note)

        # Update tracked capital
        old_capital = self._tracked_capital
        if tx_type == "deposit":
            self._tracked_capital += tx_amount
        else:
            self._tracked_capital -= tx_amount

        # Resize router (adjusts pools, tier cap, split — all hysteresis-aware)
        self.router.resize(self._tracked_capital)
        self.capital = self._tracked_capital

        emoji = "\U0001f4e5" if tx_type == "deposit" else "\U0001f4e4"  # 📥 / 📤
        send_telegram(
            f"{emoji} {TG_PREFIX} <b>{tx_type.capitalize()} detected: ${tx_amount:.2f}</b>\n"
            f"Drift: {drift_pct:.1f}%\n"
            f"Capital: ${old_capital:.2f} -> ${self._tracked_capital:.2f}\n"
            f"Tier: {self.router.tier_coin_cap} coins | "
            f"Split: {EQUITY_TIER_SPLITS[self.router._split_tier_index][1]*100:.0f}/"
            f"{EQUITY_TIER_SPLITS[self.router._split_tier_index][2]*100:.0f}\n"
            f"Recorded in capital ledger."
        )
        logger.info(
            f"{tx_type.capitalize()} detected: ${tx_amount:.2f} "
            f"(capital ${old_capital:.2f} -> ${self._tracked_capital:.2f})"
        )
        self._save_state()

    # ── Per-Coin Regime Flagging (Upgrade 3) ─────────────────────────────────

    REGIME_COOLDOWN_HOURS = 24  # Hours before a manually-resumed coin can be re-flagged

    def _check_coin_regime_conflict(self, sym: str, cs: 'CoinState'):
        """Check if a coin's engine signals conflict with global direction.
        Runs after each candle tick. Flags the coin if conflict detected.
        """
        if not cs.engine or not cs.engine._engine:
            return
        if cs.regime_flagged:
            return  # Already flagged
        if cs.paused:
            return  # Don't flag paused coins

        # Cooldown check (Q6: 24h after manual RESUME)
        if time.time() < cs.regime_cooldown_until:
            return

        eng = cs.engine._engine

        # Global direction: currently always LONG (until full regime flip is implemented)
        global_direction = "LONG"

        # Check if the engine detected a top (wants SHORT) while global is LONG
        if global_direction == "LONG" and getattr(eng, 'top_detected', False):
            cs.regime_flagged = True
            cs.coin_regime_signal = "TOP"
            cs.flagged_at = datetime.now(timezone.utc).isoformat()
            coin_name = sym.split("/")[0]
            logger.warning(f"REGIME FLAG: {sym} — top detected, conflicts with global LONG")

            # Count total flagged coins for context
            flagged_count = sum(1 for s, c in self.coins.items() if c.regime_flagged)
            flagged_names = [s.split("/")[0] for s, c in self.coins.items() if c.regime_flagged]

            send_telegram(
                f"\U0001f6a9 {TG_PREFIX} <b>Coin Regime Conflict: {coin_name}</b>\n"
                f"Signal: TOP DETECTED (wants Short)\n"
                f"Global direction: LONG\n"
                f"Flagged coins: {flagged_count}/{len(self.coins)} ({', '.join(flagged_names)})\n\n"
                f"Coin removed from active trading.\n"
                f"Open positions can still hit TPs.\n"
                f"Auto-resumes on global regime flip or RESUME {coin_name}."
            )
            self._save_state()

        # Check for SHORT direction with bottom detection (future use)
        elif global_direction == "SHORT" and getattr(eng, 'conviction_fired', False):
            cs.regime_flagged = True
            cs.coin_regime_signal = "BOTTOM"
            cs.flagged_at = datetime.now(timezone.utc).isoformat()
            coin_name = sym.split("/")[0]
            logger.warning(f"REGIME FLAG: {sym} — bottom detected, conflicts with global SHORT")

            flagged_count = sum(1 for s, c in self.coins.items() if c.regime_flagged)
            flagged_names = [s.split("/")[0] for s, c in self.coins.items() if c.regime_flagged]

            send_telegram(
                f"\U0001f6a9 {TG_PREFIX} <b>Coin Regime Conflict: {coin_name}</b>\n"
                f"Signal: BOTTOM DETECTED (wants Long)\n"
                f"Global direction: SHORT\n"
                f"Flagged coins: {flagged_count}/{len(self.coins)} ({', '.join(flagged_names)})\n\n"
                f"Coin removed from active trading.\n"
                f"Open positions can still hit TPs.\n"
                f"Auto-resumes on global regime flip or RESUME {coin_name}."
            )
            self._save_state()

    def _clear_regime_flag_on_tp(self, sym: str, cs: 'CoinState'):
        """Auto-clear regime flag when TP fills and no position remains (Q5: A)."""
        if not cs.regime_flagged:
            return
        # Check if position is fully closed
        eng = cs.engine._engine if cs.engine else None
        if eng and eng.long_coins == 0 and eng.short_coins == 0:
            coin_name = sym.split("/")[0]
            cs.regime_flagged = False
            cs.coin_regime_signal = None
            cs.flagged_at = None
            logger.info(f"REGIME UNFLAG: {sym} — TP filled, no position remaining")
            send_telegram(
                f"\u2705 {TG_PREFIX} <b>{coin_name} Regime Flag Cleared</b>\n"
                f"TP filled, no position remaining.\n"
                f"Coin returned to opportunity list."
            )

    def _clear_matching_regime_flags(self, new_direction: str):
        """After global regime change, unflag coins that now match the new direction."""
        for sym, cs in self.coins.items():
            if cs.regime_flagged:
                # TOP flag + new direction SHORT = match → unflag
                # BOTTOM flag + new direction LONG = match → unflag
                should_clear = (
                    (cs.coin_regime_signal == "TOP" and new_direction == "SHORT") or
                    (cs.coin_regime_signal == "BOTTOM" and new_direction == "LONG")
                )
                if should_clear:
                    coin_name = sym.split("/")[0]
                    cs.regime_flagged = False
                    cs.coin_regime_signal = None
                    cs.flagged_at = None
                    logger.info(f"REGIME UNFLAG: {sym} — matches new global direction {new_direction}")
                    send_telegram(
                        f"\u2705 {TG_PREFIX} <b>{coin_name} Regime Flag Cleared</b>\n"
                        f"Global direction changed to {new_direction}.\n"
                        f"Coin signal now matches — returned to opportunity list."
                    )

    # ── Funding rate tracking ─────────────────────────────────────────────────

    def _update_funding(self):
        """Check funding payments for all open positions."""
        now_ms = int(time.time() * 1000)
        for sym, cs in self.coins.items():
            if not cs.engine:
                continue
            # Only check every 8h
            if now_ms - cs.last_funding_check_ms < 8 * 3600 * 1000:
                continue
            try:
                history = self.client.fetch_funding_history(
                    sym, since_ms=cs.last_funding_check_ms or None
                )
                for entry in history:
                    amount = float(entry.get("amount") or entry.get("fundingFee") or 0)
                    if amount:
                        cs.cumulative_funding += amount
                        logger.info(f"Funding {sym}: {amount:+.6f} USDT (cumulative: {cs.cumulative_funding:+.6f})")
                cs.last_funding_check_ms = now_ms
            except Exception as e:
                logger.warning(f"Funding check failed for {sym}: {e}")

    # ── TP order management ───────────────────────────────────────────────────

    def _place_tp_order(self, sym: str, cs: CoinState):
        """Place (or replace) TP limit order for a coin.
        Stores the TP price in CoinState (Audit #8) so we never rely on
        eng.long_tp which can shift after engine ticks.

        Exchange-as-truth: TP price is calculated from the ACTUAL exchange
        entry price, not the engine's candle-based TP. The engine processes
        historical candles and computes TP from candle close prices, but the
        actual fill price can differ significantly (spread/slippage). Using
        the engine's TP could result in a sell BELOW the actual entry price.
        """
        if not cs.engine or not cs.engine._engine:
            return
        eng = cs.engine._engine
        tp_pct = eng.cfg.DCA_TP_PCT if hasattr(eng, 'cfg') and hasattr(eng.cfg, 'DCA_TP_PCT') else 0.015

        # Use actual exchange position for BOTH qty and entry price (exchange-as-truth).
        qty = eng.long_coins
        tp_price = eng.long_tp  # fallback
        try:
            positions = self.client.fetch_open_positions()
            base = sym.split("/")[0]
            if base in positions and positions[base].get("qty", 0) > 0:
                pos = positions[base]
                exchange_qty = pos["qty"]
                exchange_entry = pos.get("entry_price", 0)
                if abs(exchange_qty - qty) > 0.001:
                    logger.info(
                        f"TP qty for {sym}: using exchange position {exchange_qty:.4f} "
                        f"(engine had {qty:.4f})"
                    )
                    qty = exchange_qty
                # Always compute TP from actual exchange entry price
                if exchange_entry and exchange_entry > 0:
                    exchange_tp = exchange_entry * (1 + tp_pct)
                    if abs(exchange_tp - tp_price) > 0.0001:
                        logger.info(
                            f"TP price for {sym}: using exchange entry ${exchange_entry:.6f} "
                            f"→ TP ${exchange_tp:.6f} (engine had ${tp_price:.6f})"
                        )
                    tp_price = exchange_tp
                    # Update engine TP to match exchange truth
                    eng.long_tp = tp_price
        except Exception as e:
            logger.warning(f"Position fetch for TP failed ({sym}), using engine values: {e}")

        if not tp_price:
            return

        if not qty:
            return

        # Cancel existing TP order if any
        if cs.tp_order_id:
            self.client.cancel_tp_order(sym, cs.tp_order_id)
            cs.tp_order_id = None
            cs.tp_limit_price = None

        # Place new TP order
        oid = self.client.place_limit_sell(sym, qty, tp_price)
        if oid:
            cs.tp_order_id = oid
            cs.tp_limit_price = tp_price  # Audit #8: store separately
            logger.info(f"TP order placed for {sym}: qty={qty:.4f} @ ${tp_price:.8f} | order={oid}")
        else:
            logger.warning(
                f"TP order placement FAILED for {sym}. "
                f"Candle-based TP detection remains as fallback."
            )
            send_telegram(
                f"⚠️ {TG_PREFIX} TP order placement FAILED for {sym}\n"
                f"Qty: {qty:.4f} @ ${tp_price:.6f}\n"
                f"Candle-based TP detection still active as fallback"
            )

    def _check_tp_fills(self):
        """Poll exchange for TP order fills."""
        for sym, cs in list(self.coins.items()):
            if not cs.tp_order_id:
                continue
            try:
                result = self.client.check_order_status(sym, cs.tp_order_id)
                if result.get("filled"):
                    self._handle_tp_fill(sym, cs, result)
            except Exception as e:
                logger.error(f"TP check failed for {sym}: {e}")

    def _recover_tp_orders(self):
        """On startup, reconcile TP orders with exchange state.

        Ported from old bot's _recover_tp_order pattern:
        1. Check saved TP order IDs (filled/cancelled while down?)
        2. Scan exchange for ALL open sell orders (detect orphans)
        3. For each coin:
           - Has position + open sell → adopt order as TP
           - Has position + no order → place new TP
           - No position + stale order → cancel it
        """
        # Phase 1: Check saved TP order IDs
        for sym, cs in list(self.coins.items()):
            if not cs.tp_order_id:
                continue
            logger.info(f"Checking saved TP order for {sym}: {cs.tp_order_id}")
            try:
                result = self.client.check_order_status(sym, cs.tp_order_id)
                if result.get("filled"):
                    logger.info(f"TP order {cs.tp_order_id} FILLED while bot was down!")
                    self._handle_tp_fill(sym, cs, result)
                elif result.get("status") in ("canceled", "cancelled", "expired"):
                    logger.warning(
                        f"TP order {cs.tp_order_id} was {result['status']} while bot was down"
                    )
                    cs.tp_order_id = None
                    cs.tp_limit_price = None
                    send_telegram(
                        f"⚠️ {TG_PREFIX} TP order for {sym} was {result['status']} "
                        f"while bot was down. Will re-place on next cycle."
                    )
                else:
                    logger.info(f"TP order {cs.tp_order_id} still open ({result.get('status', '?')})")
            except Exception as e:
                logger.error(f"TP recovery check failed for {sym}: {e}")

        # Phase 2: Scan exchange for orphaned sell orders (ported from old bot)
        # Skip coins where Phase 1 already confirmed TP order is live
        for sym, cs in list(self.coins.items()):
            if not cs.engine:
                continue
            if cs.tp_order_id:
                continue  # Phase 1 confirmed this order is still open — no scan needed
            eng = cs.engine._engine
            has_position = eng is not None and (eng.long_coins > 0 or eng.long_layers > 0)

            try:
                open_orders = self.client.fetch_open_orders(sym)
                limit_sells = [o for o in open_orders if o.get("side") == "sell"]

                if limit_sells and not cs.tp_order_id:
                    if has_position:
                        # Orphan sell order found + position open → adopt it
                        limit_sells.sort(key=lambda o: o.get("timestamp", 0), reverse=True)
                        tp_order = limit_sells[0]
                        cs.tp_order_id = tp_order["id"]
                        cs.tp_limit_price = tp_order.get("price")
                        logger.info(
                            f"TP RECOVERY: Adopted orphan sell order {cs.tp_order_id} "
                            f"for {sym} @ ${tp_order.get('price', 0):.6f}"
                        )
                        send_telegram(
                            f"🔧 {TG_PREFIX} Orphan TP order adopted for {sym}\n"
                            f"Order: {cs.tp_order_id} @ ${tp_order.get('price', 0):.6f}"
                        )
                        # Cancel any extra sell orders
                        for extra in limit_sells[1:]:
                            logger.info(f"TP RECOVERY: Cancelling duplicate sell {extra['id']} for {sym}")
                            self.client.cancel_tp_order(sym, extra["id"])
                    else:
                        # No position but stale sell orders → cancel all
                        for o in limit_sells:
                            logger.warning(
                                f"TP RECOVERY: Cancelling stale sell order {o['id']} "
                                f"for {sym} (no open position)"
                            )
                            self.client.cancel_tp_order(sym, o["id"])
                        send_telegram(
                            f"🔧 {TG_PREFIX} Cancelled {len(limit_sells)} stale order(s) "
                            f"for {sym} (no open position)"
                        )

                elif has_position and not cs.tp_order_id and not limit_sells:
                    # Position open but no TP order anywhere → place one
                    if eng and eng.long_tp > 0:
                        logger.info(
                            f"TP RECOVERY: Position open for {sym} but no TP order — "
                            f"placing new limit sell @ ${eng.long_tp:.6f}"
                        )
                        self._place_tp_order(sym, cs)

            except Exception as e:
                logger.warning(f"TP RECOVERY exchange scan failed for {sym}: {e}")

    def _handle_tp_fill(self, sym: str, cs: CoinState, fill_result: dict):
        """Handle a TP limit order that filled on the exchange."""
        actual_price    = fill_result["price"]
        actual_qty      = fill_result["qty"]
        actual_proceeds = fill_result["proceeds"]
        fee             = fill_result.get("fee", 0)

        logger.info(
            f"TP FILL {sym}: {actual_qty:.4f} @ ${actual_price:.8f} "
            f"= ${actual_proceeds:.2f} (fee: ${fee:.4f})"
        )

        # Record trade from actual exchange fill
        ts = datetime.now(timezone.utc)
        record = self.tracker.on_sell(
            sym, actual_qty, actual_price, actual_proceeds, fee, ts
        )

        # Calculate actual PnL
        if record:
            pnl = record["pnl"]
            emoji = "🟢" if pnl >= 0 else "🔴"
            total_pnl = record["pnl"] + cs.cumulative_funding
            funding_str = (
                f"\nFunding: {cs.cumulative_funding:+.4f} USDT"
                if abs(cs.cumulative_funding) > 0.001
                else ""
            )
            send_telegram(
                f"{emoji} {TG_PREFIX} <b>Deal Closed (TP Hit)</b>\n"
                f"Symbol: {sym}\n"
                f"Fill: ${actual_price:.6f} × {actual_qty:.4f} = ${actual_proceeds:.2f}\n"
                f"PnL: ${pnl:.2f} ({record['return_pct']:.1f}%)"
                f"{funding_str}\n"
                f"Layers: {record.get('layers', '?')}"
            )

        # Return capital to router
        self.router.return_capital(sym, actual_proceeds)

        # Audit #2: Complete engine cleanup after TP fill
        if cs.engine and cs.engine._engine:
            eng = cs.engine._engine
            # Always add full actual proceeds — the engine never ran a sell tick
            # (exchange handled TP), so eng.capital still has pre-buy minus buy cost.
            eng.capital += actual_proceeds

            # Log correction info if stored TP price differs from actual fill
            stored_tp = cs.tp_limit_price or eng.long_tp or actual_price
            engine_expected = stored_tp * actual_qty
            correction = actual_proceeds - engine_expected
            if abs(correction) > 0.01:
                logger.info(f"TP fill correction for {sym}: ${correction:+.2f} (actual vs expected)")

            # Update trade counters
            eng.long_trades = (eng.long_trades or 0) + 1
            pnl = record.get("pnl", 0) if record else 0
            if pnl >= 0:
                eng.long_wins = (eng.long_wins or 0) + 1
            eng.long_pnl = (eng.long_pnl or 0.0) + pnl

            # Zero out ALL position fields (matching old bot exactly)
            eng.long_coins = 0.0
            eng.long_avg_entry = 0.0
            eng.long_layers = 0
            eng.long_last_buy = None
            eng.long_tp = 0.0
            eng.long_cost = 0.0

            # Reset engine capital to allocated amount (live mode: router manages real capital)
            # Prevents paper-capital depletion over multiple trade cycles
            eng.capital = cs.allocated_capital

        # Clean up
        cs.tp_order_id = None
        cs.tp_limit_price = None
        cs.cumulative_funding = 0.0
        self.tracker.save_csv()

        # Upgrade 3: auto-clear regime flag if position fully closed (Q5: A)
        self._clear_regime_flag_on_tp(sym, cs)

        # Do NOT reset last_candle_ts — the old proven bot never does.
        # The engine naturally re-enters on the next complete candle.
        # Resetting to 0 caused the 635 GRASS incident (replayed 50 historical candles).
        logger.info(f"TP fill complete for {sym} — engine will re-enter on next candle")

        # Orphaned TP order cleanup: cancel any stale sell orders on the exchange
        # that don't belong to our current state. This catches orders left behind
        # from partial fills, replays, or crashes.
        try:
            open_orders = self.client.fetch_open_orders(sym)
            for o in open_orders:
                if o.get("side") == "sell":
                    oid = o.get("id")
                    # cs.tp_order_id is None at this point (cleared above)
                    logger.info(f"Cleaning orphaned sell order {oid} for {sym}")
                    self.client.cancel_tp_order(sym, oid)
        except Exception as e:
            logger.warning(f"Orphaned order cleanup failed for {sym}: {e}")

        # Wind-down check: if in WIND_DOWN and no positions remain, flip direction
        if self.bot_state == BotState.WIND_DOWN:
            self._check_wind_down_complete()

    # ── Candle processing ─────────────────────────────────────────────────────

    def _fetch_candles(self, sym: str) -> List[dict]:
        """Fetch closed 1h candles for a symbol from Aster.

        Returns list of closed candles (incomplete current candle excluded).
        Fetches 50 candles for crash recovery (Audit #5).
        """
        try:
            base = sym.split("/")[0]
            prefix_coins = {"PEPE": "1000PEPE", "BONK": "1000BONK", "FLOKI": "1000FLOKI"}
            exchange_base = prefix_coins.get(base, base)
            aster_sym = f"{exchange_base}/USDT:USDT"

            ohlcv = self.client._exchange.fetch_ohlcv(aster_sym, "1h", limit=50)
            if not ohlcv:
                return []

            now_ms = int(time.time() * 1000)
            scale = 1.0 / 1000.0 if base in ("PEPE", "BONK", "FLOKI") else 1.0
            candles = []
            for bar in ohlcv:
                ts_ms = int(bar[0])
                candle_end = ts_ms + 3600_000
                # Skip incomplete (current) candle
                if candle_end > now_ms:
                    break
                candles.append({
                    "timestamp": ts_ms,
                    "open":   float(bar[1]) * scale,
                    "high":   float(bar[2]) * scale,
                    "low":    float(bar[3]) * scale,
                    "close":  float(bar[4]) * scale,
                    "volume": float(bar[5]),
                })
            return candles
        except Exception as e:
            logger.error(f"fetch_candles({sym}): {e}")
            return []

    # ── Action execution ──────────────────────────────────────────────────────

    def _execute_action(self, sym: str, cs: CoinState, action: dict):
        """
        Execute a single engine action against the exchange.

        Exchange-as-truth architecture: no engine rollbacks needed.
        Engine position state is overwritten from exchange at the top of every
        main loop iteration by _sync_positions_from_exchange().

        Audit fixes applied:
          #3: Pre-flight order validation (min amount, precision)
          #7: Spread logging
          #8: Store TP limit price separately in CoinState
        """
        act_type = action.get("action", "")
        price    = float(action.get("price", 0))
        qty      = float(action.get("qty", 0))
        reason   = action.get("reason", "")

        if act_type == "BUY":
            # PAUSED or WIND_DOWN: block new entries and DCA layers
            if self.bot_state in (BotState.PAUSED, BotState.WIND_DOWN):
                logger.info(f"BUY blocked for {sym} — bot state is {self.bot_state}")
                if cs.engine:
                    cs.engine.reject_action(action)
                return

            # Per-coin pause (Upgrade 2): block buys for individually paused coins
            if cs.paused:
                logger.info(f"BUY blocked for {sym} — coin is paused")
                if cs.engine:
                    cs.engine.reject_action(action)
                return

            # Per-coin regime flag (Upgrade 3): block buys for regime-conflicted coins
            if cs.regime_flagged:
                logger.info(f"BUY blocked for {sym} — regime conflict ({cs.coin_regime_signal})")
                if cs.engine:
                    cs.engine.reject_action(action)
                return

            # Order dedup guard: block duplicate buys within 30 seconds
            ORDER_DEDUP_WINDOW = 30
            if time.time() - cs._last_buy_time < ORDER_DEDUP_WINDOW:
                elapsed_since = time.time() - cs._last_buy_time
                logger.warning(
                    f"DUPLICATE BUY blocked for {sym} — last buy was {elapsed_since:.0f}s ago "
                    f"(dedup window: {ORDER_DEDUP_WINDOW}s)"
                )
                if cs.engine:
                    cs.engine.reject_action(action)
                return

            # Audit #3: Pre-flight checks
            cost = price * qty
            if cost < 5.0:
                logger.warning(f"BUY cost ${cost:.2f} below $5 minimum for {sym}, skipping")
                if cs.engine:
                    cs.engine.reject_action(action)
                return

            # Request capital from router
            key = f"{sym}:long"
            layer = self.tracker._open_deals.get(key, {}).get("layers", 0) + 1
            pool = "reserve" if layer >= 6 else "active"
            granted = self.router.request_capital(sym, cost, pool=pool)

            if granted <= 0:
                logger.warning(f"Router denied capital for {sym} BUY (layer {layer})")
                if cs.engine:
                    cs.engine.reject_action(action)
                return
            if granted < cost:
                logger.warning(f"Router partial capital for {sym} — rejecting")
                if cs.engine:
                    cs.engine.reject_action(action)
                self.router.return_capital(sym, granted)
                return

            # Audit #3: Balance pre-check
            exchange_balance = self.client.fetch_balance()
            if exchange_balance < cost * 1.01:
                logger.warning(
                    f"Insufficient USDT for {sym} BUY: need ${cost:.2f}, "
                    f"have ${exchange_balance:.2f}"
                )
                self.router.return_capital(sym, granted)
                if cs.engine:
                    cs.engine.reject_action(action)
                # Throttle: alert once per coin per hour
                now = time.time()
                last_alert = getattr(cs, '_last_insufficient_alert', 0)
                if now - last_alert > 3600:
                    cs._last_insufficient_alert = now
                    send_telegram(
                        f"⚠️ {TG_PREFIX} BUY skipped — insufficient USDT\n"
                        f"Need: ${cost:.2f} | Have: ${exchange_balance:.2f}\n"
                        f"Symbol: {sym}"
                    )
                return

            result = self.client.create_market_buy(sym, qty)
            if result and result.get("status") in ("filled", "dry_run"):
                actual_price = result.get("price", price)
                actual_qty   = result.get("qty", qty)
                actual_cost  = result.get("cost", actual_price * actual_qty)
                fee = result.get("fee", 0)

                # Audit #7: Spread logging
                spread_bps = abs(actual_price - price) / price * 10000 if price > 0 else 0
                logger.info(
                    f"BUY fill {sym}: engine=${price:.6f}, actual=${actual_price:.6f}, "
                    f"spread={spread_bps:.1f}bps"
                )
                if spread_bps > 50:  # > 0.5%
                    send_telegram(
                        f"⚠️ {TG_PREFIX} High spread on {sym} BUY: {spread_bps:.0f}bps\n"
                        f"Engine: ${price:.6f} | Fill: ${actual_price:.6f}"
                    )

                self.tracker.on_buy(sym, actual_qty, actual_price,
                                    datetime.now(timezone.utc))

                # Record buy timestamp for dedup guard
                cs._last_buy_time = time.time()
                # Track layer count (exchange sync will confirm, but track locally too)
                cs.layer_count += 1

                # GAP-13 FIX: Reset engine capital after each BUY to prevent
                # paper-capital depletion from blocking future DCA layers.
                # The engine decrements eng.capital on each buy (paper tracking),
                # but in live mode the CapitalRouter manages real capital.
                if cs.engine and cs.engine._engine:
                    cs.engine._engine.capital = cs.allocated_capital

                # Place TP limit order
                self._place_tp_order(sym, cs)

                send_telegram(
                    f"🔵 {TG_PREFIX} <b>DCA Layer {layer}</b>\n"
                    f"Symbol: {sym}\n"
                    f"Fill: ${actual_price:.6f} × {actual_qty:.4f} = ${actual_cost:.2f}\n"
                    f"TP: ${cs.tp_limit_price:.6f}\n"
                    f"Reason: {reason}"
                )
            else:
                logger.error(f"BUY failed for {sym} — rolling back router")
                self.router.return_capital(sym, granted)
                if cs.engine:
                    cs.engine.reject_action(action)

        elif act_type == "SELL":
            # If a TP limit order is active on exchange, skip engine TP sells.
            # Exchange will fill the TP; next cycle sync will clear engine state.
            if cs.tp_order_id and "TP" in reason:
                logger.info(f"Skipping engine TP for {sym} — exchange TP order active")
                return

            # Non-TP sell: cancel TP order first, then market sell
            if cs.tp_order_id:
                logger.info(f"Cancelling TP order for {sym} before {reason} sell")
                self.client.cancel_tp_order(sym, cs.tp_order_id)
                cs.tp_order_id = None
                cs.tp_limit_price = None

            # Use exchange position qty (source of truth), not engine qty
            # Old bot: bal["base_free"] with 1% tolerance cap
            sell_qty = qty
            try:
                positions = self.client.fetch_open_positions()
                base = sym.split("/")[0]
                if base in positions and positions[base].get("qty", 0) > 0:
                    exchange_qty = positions[base]["qty"]
                    if abs(exchange_qty - qty) > 0.01:
                        logger.info(
                            f"SELL qty adjusted for {sym}: engine={qty:.4f}, "
                            f"exchange={exchange_qty:.4f} — using exchange"
                        )
                        sell_qty = exchange_qty
            except Exception as e:
                logger.warning(f"Position fetch for sell qty failed ({sym}), using engine qty: {e}")

            result = self.client.create_market_sell(sym, sell_qty)
            if result and result.get("status") in ("filled", "dry_run"):
                actual_price    = result.get("price", 0)
                actual_qty      = result.get("qty", qty)
                actual_proceeds = result.get("proceeds", 0)
                fee             = result.get("fee", 0)

                ts = datetime.now(timezone.utc)
                record = self.tracker.on_sell(
                    sym, actual_qty, actual_price, actual_proceeds, fee, ts
                )
                self.router.return_capital(sym, actual_proceeds)
                # Engine position fields will be zeroed by next _sync_positions_from_exchange()
                cs.layer_count = 0

                if record:
                    pnl = record["pnl"]
                    emoji = "🟢" if pnl >= 0 else "🔴"
                    send_telegram(
                        f"{emoji} {TG_PREFIX} <b>Deal Closed ({reason})</b>\n"
                        f"Symbol: {sym}\n"
                        f"Fill: ${actual_price:.6f} × {actual_qty:.4f} = ${actual_proceeds:.2f}\n"
                        f"PnL: ${pnl:.2f} ({record['return_pct']:.1f}%)"
                    )

                cs.tp_order_id = None
                cs.tp_limit_price = None
                self.tracker.save_csv()

                if self.bot_state == BotState.WIND_DOWN:
                    self._check_wind_down_complete()

            else:
                logger.error(f"SELL FAILED for {sym} — will retry on next candle")
                send_telegram(
                    f"⚠️ {TG_PREFIX} <b>SELL FAILED</b>\n"
                    f"Symbol: {sym} | Reason: {reason}\n"
                    f"Will retry on next candle (exchange synced next cycle)"
                )

        elif act_type in ("SHORT_OPEN", "SHORT_CLOSE"):
            # Short actions are not supported on live Aster Perps (long-only mode).
            # Explicitly reject to keep engine state consistent and prevent silent drift.
            logger.warning(
                f"SHORT action {act_type} for {sym} — not supported in live mode. "
                f"Rejecting to keep engine consistent."
            )
            if cs.engine:
                cs.engine.reject_action(action)

        else:
            logger.warning(f"Unknown action type '{act_type}' for {sym} — ignoring")

    # ── Capital Router integration ────────────────────────────────────────────

    def _do_rebalance(self, current_dt: datetime):
        """Daily rebalance: update scanner, adjust allocations, spin up new engines."""
        today = current_dt.date()
        if self._last_rebalance_date == today:
            return
        # Timing guard: prevent rapid-fire rebalances (e.g. from duplicate loop iterations)
        if hasattr(self, '_last_rebalance_ts') and time.time() - self._last_rebalance_ts < 60:
            logger.warning("Rebalance blocked — less than 60s since last rebalance")
            return

        logger.info(f"Daily rebalance for {today}")
        try:
            scanner_data = self.router.load_scanner_json(str(SCANNER_PATH))
            current_equity = self._compute_equity()

            # Upgrade 2+3: exclude paused and regime-flagged coins from rebalance candidates
            excluded_coins = {
                sym.split("/")[0] for sym, cs in self.coins.items()
                if cs.paused or cs.regime_flagged
            }
            if excluded_coins:
                scanner_data = [
                    entry for entry in scanner_data
                    if entry.get("coin", entry.get("symbol", "").split("/")[0]) not in excluded_coins
                ]
                logger.info(f"Rebalance excluding paused/flagged coins: {excluded_coins}")

            allocations = self.router.rebalance_daily(scanner_data, current_equity=current_equity)

            for sym, alloc in allocations.items():
                if sym not in self.coins:
                    if self.bot_state != BotState.RUNNING:
                        logger.info(f"Skipping new coin {sym} — bot state is {self.bot_state}")
                        continue
                    logger.info(f"Creating engine for new coin {sym} (alloc=${alloc:.2f})")
                    cs = CoinState(sym, alloc)
                    cs.engine = V14LifecycleEngine(
                        symbol=sym,
                        capital=alloc,
                        profile=self.profile,
                        leverage=self.leverage,
                    )
                    cs.engine._live_mode = True
                    if cs.engine._engine:
                        cs.engine._engine.live_mode = True
                    # Force warmup for live trading — we're trading against real
                    # exchange data, no need to wait for a daily boundary.
                    # The engine is initialized in LONG_DCA phase and ready to trade.
                    cs.engine._warmed_up = True
                    self.coins[sym] = cs
                    # Set leverage on exchange for new coin
                    self.client.ensure_leverage(sym, self.leverage)
                else:
                    # Update allocation
                    cs = self.coins[sym]
                    cs.allocated_capital = alloc
                    # Sync engine capital when no position is open (prevents sizing drift)
                    if cs.engine and cs.engine._engine:
                        eng = cs.engine._engine
                        if eng.long_coins == 0 and eng.short_coins == 0:
                            old_cap = eng.capital
                            eng.capital = alloc
                            if abs(old_cap - alloc) > 1:
                                logger.info(f"  {sym} engine capital synced: ${old_cap:.2f} -> ${alloc:.2f}")

            self._last_rebalance_date = today
            self._last_rebalance_ts = time.time()
            logger.info(f"Rebalance complete: {len(self.coins)} active coins")
        except Exception as e:
            logger.error(f"Rebalance failed: {e}")

    # ── Portfolio Regime Monitor ──────────────────────────────────────────────

    def _evaluate_regime(self, current_dt: datetime):
        """
        Evaluate ROUTER v2 signals across all 50 scanner coins.
        Runs once per day at midnight UTC.
        Send tiered Telegram alerts based on signal count thresholds.
        """
        today = current_dt.date()
        if self._regime_last_eval_date == today:
            return
        if current_dt.hour != REGIME_EVAL_HOUR:
            return

        self._regime_last_eval_date = today
        logger.info("Running portfolio regime evaluation")

        try:
            # Load scanner data for per-coin signal states
            if not SCANNER_PATH.exists():
                logger.warning("Scanner JSON not found — skipping regime eval")
                return

            with open(SCANNER_PATH) as f:
                scanner = json.load(f)

            coins_data = scanner.get("rankings", []) or scanner.get("coins", [])
            topping_coins = []
            bottoming_coins = []

            for coin_entry in coins_data:
                sym = coin_entry.get("symbol", coin_entry.get("coin", ""))
                # Use lifecycle_phase / router signals if available
                phase = coin_entry.get("lifecycle_phase", "")
                router_signal = coin_entry.get("router_signal", "")

                if "TOP" in phase.upper() or "TOP" in router_signal.upper():
                    topping_coins.append(sym)
                elif "BOTTOM" in phase.upper() or "BOTTOM" in router_signal.upper():
                    bottoming_coins.append(sym)

            total = max(len(coins_data), 1)
            top_count    = len(topping_coins)
            bottom_count = len(bottoming_coins)

            # Determine dominant signal direction
            if top_count >= bottom_count and top_count >= 5:
                signal_type  = "TOP"
                signal_count = top_count
                signal_coins = topping_coins
            elif bottom_count >= 5:
                signal_type  = "BOTTOM"
                signal_count = bottom_count
                signal_coins = bottoming_coins
            else:
                # No significant signal
                if self._regime_signal_count > 0:
                    logger.info(
                        f"Regime signal faded: was {self._regime_signal_count}/{total} — "
                        f"now below threshold"
                    )
                    self._regime_signal_count = 0
                    self._regime_signal_type  = None
                return

            prev_count = self._regime_signal_count
            self._regime_signal_count = signal_count
            self._regime_signal_type  = signal_type

            # Only alert if count increased to a tier boundary or is new
            def tier_name(n: int) -> str:
                if n >= 25: return "MAJORITY"
                if n >= 12: return "STRONG"
                if n >= 5:  return "EARLY"
                return "NONE"

            current_tier = tier_name(signal_count)
            previous_tier = tier_name(prev_count)

            if current_tier == "NONE":
                return

            # Send alert if new signal, tier escalated, or count increased
            should_alert = (
                prev_count == 0
                or current_tier != previous_tier
                or (signal_count > prev_count and self._regime_alert_state == "AWAITING_APPROVAL")
            )

            if should_alert or self._regime_alert_state == "AWAITING_APPROVAL":
                tier_emoji = {"EARLY": "🟡", "STRONG": "🟠", "MAJORITY": "🔴"}.get(current_tier, "⚠️")
                signal_label = "TOP DETECTED" if signal_type == "TOP" else "BOTTOM DETECTED"

                coin_list = ", ".join(signal_coins[:10])
                if len(signal_coins) > 10:
                    coin_list += f" (+{len(signal_coins)-10} more)"

                cfgi_str = f"CFGI Market: {self._cfgi_market:.0f}" if self._cfgi_market else ""

                msg = (
                    f"{tier_emoji} {TG_PREFIX} <b>REGIME SIGNAL: {signal_label}</b>\n"
                    f"Tier: {current_tier} ({signal_count}/{total} coins)\n\n"
                    f"Signaling: {coin_list}\n"
                )
                if cfgi_str:
                    msg += f"\n{cfgi_str}"

                if self._regime_alert_state != "AWAITING_APPROVAL":
                    msg += (
                        "\n\nAll positions continue normally.\n"
                        "Reply <b>APPROVE</b> to begin graceful wind-down.\n"
                        "Reply <b>DENY</b> to continue current strategy."
                    )
                    self._regime_alert_state = "AWAITING_APPROVAL"
                else:
                    msg += f"\n\n⏳ Still awaiting your decision. ({signal_count}/{total} coins signaling)"

                send_telegram(msg)

        except Exception as e:
            logger.error(f"Regime evaluation failed: {e}")

    # ── Wind-down ─────────────────────────────────────────────────────────────

    def _check_wind_down_complete(self):
        """Check if all positions have closed during wind-down."""
        open_positions = [
            sym for sym, cs in self.coins.items()
            if cs.tp_order_id or (
                cs.engine and cs.engine._engine and
                (cs.engine._engine.long_coins or cs.engine._engine.long_layers)
            )
        ]
        if open_positions:
            logger.info(f"Wind-down: {len(open_positions)} positions still open: {open_positions}")
            return

        # All closed — flip direction
        logger.info("Wind-down complete. All positions closed.")
        send_telegram(
            f"✅ {TG_PREFIX} <b>Wind-Down Complete</b>\n"
            f"All positions closed.\n"
            f"Ready for direction flip."
            f"\n\n⚠️ Direction flip logic not yet implemented — "
            f"please restart bot with new direction config."
        )
        self.bot_state = BotState.PAUSED
        self._regime_alert_state = "NONE"
        self._regime_signal_count = 0
        self._save_state()

    # ── Telegram commands ─────────────────────────────────────────────────────

    def _process_telegram_commands(self):
        """Poll for and process Telegram commands."""
        now = time.time()
        if now - self._last_tg_check < 15:  # Check every 15 seconds
            return
        self._last_tg_check = now

        chat_id = os.environ.get("AIT_TG_CHAT_ID", "")
        updates = get_telegram_updates(offset=self._tg_update_offset)

        for update in updates:
            self._tg_update_offset = max(
                self._tg_update_offset,
                update.get("update_id", 0) + 1
            )
            msg = update.get("message") or update.get("callback_query", {}).get("message")
            if not msg:
                continue

            # Only process messages from authorized chat
            msg_chat_id = str(msg.get("chat", {}).get("id", ""))
            if chat_id and msg_chat_id != chat_id:
                continue

            text = (
                msg.get("text") or
                update.get("callback_query", {}).get("data") or
                ""
            ).strip().upper()

            if not text:
                continue

            logger.info(f"Telegram command: {text!r}")
            self._handle_command(text)

    def _handle_command(self, text: str):
        """Handle a parsed Telegram command."""

        if text == "APPROVE":
            if self._regime_alert_state != "AWAITING_APPROVAL":
                send_telegram(f"ℹ️ {TG_PREFIX} No pending regime change to approve.")
                return
            self.bot_state = BotState.WIND_DOWN
            self._regime_alert_state = "NONE"
            send_telegram(
                f"⏳ {TG_PREFIX} <b>Wind-Down Started</b>\n"
                f"Grids frozen. Existing TPs active.\n"
                f"No new entries or DCA layers until all positions close.\n"
                f"I'll notify you when wind-down is complete."
            )
            logger.info("APPROVE: entering WIND_DOWN state")
            self._save_state()

        elif text == "DENY":
            if self._regime_alert_state != "AWAITING_APPROVAL":
                send_telegram(f"ℹ️ {TG_PREFIX} No pending regime change to deny.")
                return
            self._regime_alert_state = "NONE"
            self._regime_signal_count = 0
            send_telegram(
                f"✅ {TG_PREFIX} Regime change denied. Continuing current strategy."
            )
            logger.info("DENY: regime change declined, resuming normal operation")
            self._save_state()

        elif text == "PAUSE" or text == "PAUSE TRADING":
            if self.bot_state == BotState.PAUSED:
                send_telegram(f"ℹ️ {TG_PREFIX} Already paused.")
                return
            self.bot_state = BotState.PAUSED
            send_telegram(
                f"⏸️ {TG_PREFIX} <b>Trading Paused (Global)</b>\n"
                f"Grids frozen. No new entries or DCA layers.\n"
                f"Existing TP orders remain active on exchange.\n"
                f"Reply RESUME to restart trading.\n"
                f"Reply CLOSE <SYMBOL> to force-close a position."
            )
            logger.info("PAUSE: trading frozen by operator")
            self._save_state()

        elif text.startswith("PAUSE ") and text != "PAUSE TRADING":
            # Per-coin pause (Upgrade 2)
            coin_name = text.split(None, 1)[1].upper().strip()
            target = None
            for sym in self.coins:
                if sym.split("/")[0].upper() == coin_name:
                    target = sym
                    break
            if not target:
                send_telegram(
                    f"❓ {TG_PREFIX} Symbol '{coin_name}' not found.\n"
                    f"Active: {', '.join(s.split('/')[0] for s in self.coins)}"
                )
                return
            cs = self.coins[target]
            if cs.paused:
                send_telegram(f"ℹ️ {TG_PREFIX} {coin_name} is already paused.")
                return
            cs.paused = True
            send_telegram(
                f"⏸️ {TG_PREFIX} <b>{coin_name} Paused</b>\n"
                f"No new orders for {coin_name}.\n"
                f"Existing TP orders remain active.\n"
                f"Reply RESUME {coin_name} to unpause."
            )
            logger.info(f"PAUSE {coin_name}: per-coin pause activated")
            self._save_state()

        elif text == "RESUME" or text == "RESUME TRADING":
            # Global resume — does NOT clear per-coin pauses
            if self.bot_state != BotState.PAUSED:
                send_telegram(f"ℹ️ {TG_PREFIX} Not currently paused.")
                return
            self.bot_state = BotState.RUNNING
            paused_coins = [s.split("/")[0] for s, cs in self.coins.items() if cs.paused]
            note = ""
            if paused_coins:
                note = f"\nNote: {', '.join(paused_coins)} still individually paused."
            send_telegram(
                f"▶️ {TG_PREFIX} <b>Trading Resumed (Global)</b>\n"
                f"Grids active. Normal operations resumed.{note}"
            )
            logger.info("RESUME: trading resumed (per-coin pauses preserved)")
            self._save_state()

        elif text.startswith("RESUME ") and text != "RESUME TRADING":
            # Per-coin resume (Upgrade 2)
            coin_name = text.split(None, 1)[1].upper().strip()
            target = None
            for sym in self.coins:
                if sym.split("/")[0].upper() == coin_name:
                    target = sym
                    break
            if not target:
                send_telegram(
                    f"❓ {TG_PREFIX} Symbol '{coin_name}' not found.\n"
                    f"Active: {', '.join(s.split('/')[0] for s in self.coins)}"
                )
                return
            cs = self.coins[target]
            if not cs.paused and not cs.regime_flagged:
                send_telegram(f"ℹ️ {TG_PREFIX} {coin_name} is not paused or flagged.")
                return
            was_flagged = cs.regime_flagged
            cs.paused = False
            cs.regime_flagged = False
            cs.coin_regime_signal = None
            cs.flagged_at = None
            # Q6: 24h cooldown after manual RESUME of a regime-flagged coin
            if was_flagged:
                cs.regime_cooldown_until = time.time() + (self.REGIME_COOLDOWN_HOURS * 3600)
            status_parts = []
            if was_flagged:
                status_parts.append(f"regime flag cleared (24h cooldown active)")
            status_parts.append("trading active")
            send_telegram(
                f"▶️ {TG_PREFIX} <b>{coin_name} Resumed</b>\n"
                f"{'; '.join(status_parts).capitalize()}."
            )
            logger.info(f"RESUME {coin_name}: pause/flag cleared" +
                        (f" (cooldown until {datetime.fromtimestamp(cs.regime_cooldown_until, tz=timezone.utc).isoformat()})" if was_flagged else ""))
            self._save_state()

        elif text.startswith("CLOSE "):
            parts = text.split(None, 1)
            if len(parts) < 2:
                return
            coin_name = parts[1].upper().strip()

            if coin_name == "ALL":
                self._force_close_all()
            else:
                # Find matching symbol
                target = None
                for sym in self.coins:
                    if sym.split("/")[0].upper() == coin_name:
                        target = sym
                        break
                if target:
                    self._force_close_coin(target)
                else:
                    send_telegram(
                        f"❓ {TG_PREFIX} Symbol '{coin_name}' not found in active positions.\n"
                        f"Active: {', '.join(s.split('/')[0] for s in self.coins)}"
                    )

        elif text.startswith("DEPOSIT ") or text.startswith("DEPOSIT\n"):
            parts = text.split(None, 1)
            if len(parts) < 2:
                send_telegram(f"ℹ️ {TG_PREFIX} Usage: DEPOSIT <amount>")
                return
            try:
                amount = float(parts[1].strip())
            except ValueError:
                send_telegram(f"❌ {TG_PREFIX} Invalid amount: '{parts[1].strip()}'")
                return
            if amount <= 0:
                send_telegram(f"❌ {TG_PREFIX} Amount must be positive.")
                return
            old_capital = self._tracked_capital
            record_ledger_transaction(
                LEDGER_PATH, "deposit", amount,
                note="Manual deposit via Telegram command"
            )
            self._tracked_capital += amount
            self.capital = self._tracked_capital
            self.router.resize(self._tracked_capital)
            send_telegram(
                f"\U0001f4e5 {TG_PREFIX} <b>Manual Deposit: ${amount:.2f}</b>\n"
                f"Capital: ${old_capital:.2f} -> ${self._tracked_capital:.2f}\n"
                f"Tier: {self.router.tier_coin_cap} coins | "
                f"Split: {EQUITY_TIER_SPLITS[self.router._split_tier_index][1]*100:.0f}/"
                f"{EQUITY_TIER_SPLITS[self.router._split_tier_index][2]*100:.0f}\n"
                f"Recorded in capital ledger."
            )
            logger.info(f"Manual deposit: ${amount:.2f} via Telegram")
            self._save_state()

        elif text.startswith("WITHDRAW ") or text.startswith("WITHDRAW\n"):
            parts = text.split(None, 1)
            if len(parts) < 2:
                send_telegram(f"ℹ️ {TG_PREFIX} Usage: WITHDRAW <amount>")
                return
            try:
                amount = float(parts[1].strip())
            except ValueError:
                send_telegram(f"❌ {TG_PREFIX} Invalid amount: '{parts[1].strip()}'")
                return
            if amount <= 0:
                send_telegram(f"❌ {TG_PREFIX} Amount must be positive.")
                return
            # Safety check: can't withdraw below invested
            total_invested = sum(
                cs.allocated_capital for cs in self.coins.values()
                if cs.engine and cs.engine._engine and cs.engine._engine.long_coins > 0
            )
            if (self._tracked_capital - amount) < total_invested:
                send_telegram(
                    f"❌ {TG_PREFIX} Cannot withdraw ${amount:.2f}\n"
                    f"Tracked capital: ${self._tracked_capital:.2f}\n"
                    f"Currently invested: ${total_invested:.2f}\n"
                    f"Max withdrawable: ${self._tracked_capital - total_invested:.2f}\n"
                    f"Close positions first."
                )
                return
            old_capital = self._tracked_capital
            record_ledger_transaction(
                LEDGER_PATH, "withdrawal", amount,
                note="Manual withdrawal via Telegram command"
            )
            self._tracked_capital -= amount
            self.capital = self._tracked_capital
            self.router.resize(self._tracked_capital)
            send_telegram(
                f"\U0001f4e4 {TG_PREFIX} <b>Manual Withdrawal: ${amount:.2f}</b>\n"
                f"Capital: ${old_capital:.2f} -> ${self._tracked_capital:.2f}\n"
                f"Tier: {self.router.tier_coin_cap} coins | "
                f"Split: {EQUITY_TIER_SPLITS[self.router._split_tier_index][1]*100:.0f}/"
                f"{EQUITY_TIER_SPLITS[self.router._split_tier_index][2]*100:.0f}\n"
                f"Recorded in capital ledger."
            )
            logger.info(f"Manual withdrawal: ${amount:.2f} via Telegram")
            self._save_state()

        elif text == "CAPITAL":
            summary = get_ledger_summary(LEDGER_PATH)
            if summary is None:
                send_telegram(
                    f"\U0001f4b0 {TG_PREFIX} <b>Capital Status</b>\n"
                    f"Tracked capital: ${self._tracked_capital:.2f}\n"
                    f"Exchange balance: ${self._exchange_usdt_total:.2f}\n"
                    f"No ledger found."
                )
            else:
                last_tx = summary["last_transaction"]
                last_str = (
                    f"\nLast: {last_tx['type']} ${last_tx['amount']:.2f} "
                    f"({last_tx.get('timestamp', 'unknown')[:10]})"
                    if last_tx else ""
                )
                send_telegram(
                    f"\U0001f4b0 {TG_PREFIX} <b>Capital Status</b>\n"
                    f"Seed: ${summary['seed_capital']:.2f}\n"
                    f"Deposits: ${summary['total_deposits']:.2f}\n"
                    f"Withdrawals: ${summary['total_withdrawals']:.2f}\n"
                    f"Tracked capital: ${summary['current_capital']:.2f}\n"
                    f"Exchange balance: ${self._exchange_usdt_total:.2f}\n"
                    f"Tier: {self.router.tier_coin_cap} coins | "
                    f"Split: {EQUITY_TIER_SPLITS[self.router._split_tier_index][1]*100:.0f}/"
                    f"{EQUITY_TIER_SPLITS[self.router._split_tier_index][2]*100:.0f}"
                    f"{last_str}"
                )

        else:
            # Unknown command — silently ignore
            pass

    def _force_close_coin(self, sym: str):
        """Force-close a single position at market price."""
        cs = self.coins.get(sym)
        if not cs or not cs.engine or not cs.engine._engine:
            send_telegram(f"❓ {TG_PREFIX} No open position for {sym}")
            return

        # Use exchange position as source of truth (not engine qty)
        eng = cs.engine._engine
        qty = eng.long_coins  # fallback
        try:
            positions = self.client.fetch_open_positions()
            base = sym.split("/")[0]
            if base in positions and positions[base].get("qty", 0) > 0:
                qty = positions[base]["qty"]
        except Exception as e:
            logger.warning(f"Position fetch failed for force-close {sym}, using engine qty: {e}")

        if not qty:
            send_telegram(f"❓ {TG_PREFIX} No open position for {sym}")
            return

        send_telegram(f"🔄 {TG_PREFIX} Force-closing {sym} at market...")

        # Cancel TP order first
        if cs.tp_order_id:
            self.client.cancel_tp_order(sym, cs.tp_order_id)
            cs.tp_order_id = None

        result = self.client.create_market_sell(sym, qty)
        if result and result.get("status") in ("filled", "dry_run"):
            actual_price    = result.get("price", 0)
            actual_qty      = result.get("qty", qty)
            actual_proceeds = result.get("proceeds", 0)
            fee             = result.get("fee", 0)

            ts = datetime.now(timezone.utc)
            record = self.tracker.on_sell(
                sym, actual_qty, actual_price, actual_proceeds, fee, ts
            )
            self.router.return_capital(sym, actual_proceeds)

            pnl = record.get("pnl", 0) if record else 0
            emoji = "🟢" if pnl >= 0 else "🔴"
            send_telegram(
                f"{emoji} {TG_PREFIX} <b>Force-Closed: {sym}</b>\n"
                f"Fill: ${actual_price:.6f} × {actual_qty:.4f} = ${actual_proceeds:.2f}\n"
                f"PnL: ${pnl:.2f}"
            )
            logger.info(f"Force-closed {sym}: ${actual_proceeds:.2f} (PnL: ${pnl:.2f})")
            self.tracker.save_csv()

            if self.bot_state == BotState.WIND_DOWN:
                self._check_wind_down_complete()
        else:
            send_telegram(f"❌ {TG_PREFIX} Force-close failed for {sym}. Check logs.")

    def _force_close_all(self):
        """Force-close all open positions at market."""
        open_syms = [
            sym for sym, cs in self.coins.items()
            if cs.engine and cs.engine._engine and cs.engine._engine.long_coins
        ]
        if not open_syms:
            send_telegram(f"ℹ️ {TG_PREFIX} No open positions to close.")
            return
        send_telegram(f"🔄 {TG_PREFIX} Force-closing {len(open_syms)} positions...")
        for sym in open_syms:
            self._force_close_coin(sym)

    # ── Status ────────────────────────────────────────────────────────────────

    def _compute_equity(self) -> float:
        """Compute equity from exchange balance (source of truth) + unrealized PnL.

        Uses USDT.total (includes margin locked in positions) + unrealized PnL
        from open positions.  Mirrors V14 Live's exchange-as-truth pattern.
        """
        try:
            fb = self.client.fetch_full_balance()
            usdt_total = fb["usdt_total"]
            if usdt_total <= 0:
                raise ValueError("Zero total balance returned")
        except Exception as e:
            logger.warning(f"Failed to fetch exchange balance for equity: {e}")
            return self.capital  # fallback
        unrealized = 0.0
        for cs in self.coins.values():
            if cs.engine and cs.engine._engine:
                eng = cs.engine._engine
                if eng.long_coins and eng.long_cost:
                    current_price = self.client.fetch_ticker_price(cs.symbol)
                    if current_price:
                        unrealized += (current_price * eng.long_coins) - eng.long_cost
        return usdt_total + unrealized

    def _write_status(self):
        """Write status.json for dashboard and heartbeat monitoring.

        Uses cached exchange data from _sync_positions_from_exchange() —
        no extra API calls needed. Exchange is source of truth for all
        position and balance data; engine contributes only phase/signal state.
        """
        now = time.time()
        if now - self._last_status_write < STATUS_WRITE_INTERVAL:
            return
        self._last_status_write = now

        # Use cached data from _sync_positions_from_exchange()
        exchange_positions = self._last_exchange_positions
        usdt_free  = self._exchange_usdt_free
        usdt_total = self._exchange_usdt_total

        # Equity = total USDT (includes margin) + unrealized PnL from positions
        unrealized_total = sum(
            p.get("unrealized_pnl", 0) for p in exchange_positions.values()
        )
        equity = round(usdt_total + unrealized_total, 2)
        invested = round(sum(
            p.get("entry_price", 0) * p.get("qty", 0)
            for p in exchange_positions.values()
        ), 2)
        pnl_pct = ((equity - self.capital) / self.capital * 100) if self.capital > 0 else 0.0

        coins = {}
        for sym, cs in self.coins.items():
            if not cs.engine:
                continue
            try:
                # Engine contributes: phase, signal state
                st = cs.engine.get_status()
                coin_data = {}
                if "coins" in st:
                    coin_data = st["coins"].get(sym, {})

                # Override position data from exchange (source of truth)
                base = sym.split("/")[0]
                pos = exchange_positions.get(base, {})
                ex_qty   = pos.get("qty", 0) or 0
                ex_entry = pos.get("entry_price", 0) or 0
                ex_unrealized = pos.get("unrealized_pnl", 0) or 0

                if ex_qty > 0:
                    coin_data["avg_entry"]      = round(ex_entry, 8)
                    coin_data["unrealized_pnl"] = round(ex_unrealized, 4)
                    coin_data["position_size"]  = round(ex_qty, 8)
                else:
                    coin_data["avg_entry"]      = 0
                    coin_data["unrealized_pnl"] = 0
                    coin_data["position_size"]  = 0

                # Live price for display (ticker — still needed for current_price display)
                try:
                    live_price = self.client.fetch_ticker_price(sym)
                    if live_price > 0:
                        coin_data["current_price"] = round(live_price, 6)
                except Exception:
                    pass

                # Per-coin realized PnL from CSV (survives restarts)
                try:
                    csv_path = OUTPUT_DIR / "trades.csv"
                    if csv_path.exists():
                        import csv as csv_mod
                        with open(csv_path) as cf:
                            reader = csv_mod.DictReader(cf)
                            coin_pnl = sum(
                                float(t.get("pnl", 0) or 0)
                                for t in reader if t.get("symbol") == sym
                            )
                        coin_data["realized_pnl"] = round(coin_pnl, 4)
                except Exception as csv_err:
                    logger.warning(f"CSV PnL read failed for {sym}: {csv_err}")

                coin_data["cumulative_funding"] = round(cs.cumulative_funding, 6)
                coin_data["tp_order_id"]  = cs.tp_order_id
                coin_data["layer_count"]  = cs.layer_count
                coin_data["paused"]       = cs.paused
                coin_data["regime_flagged"] = cs.regime_flagged
                if cs.regime_flagged:
                    coin_data["coin_regime_signal"] = cs.coin_regime_signal
                    coin_data["flagged_at"] = cs.flagged_at
                if cs.tp_limit_price:
                    coin_data["next_tp_price"] = cs.tp_limit_price
                if sym in self._cfgi_coins:
                    coin_data["cfgi"] = round(self._cfgi_coins[sym], 1)
                coins[sym] = coin_data
            except Exception as e:
                logger.error(f"get_status failed for {sym}: {e}")

        status = {
            "running": True,
            "mode": "live",
            "engine": "v14-pm",
            "exchange": "aster_perp",
            "profile": self.profile,
            "leverage": self.leverage,
            "bot_state": self.bot_state,
            "capital": self.capital,
            "tracked_capital": round(self._tracked_capital, 2),
            "equity": equity,
            "cash": round(usdt_free, 2),
            "invested": invested,
            "exchange_balance": {
                "usdt_free":  round(usdt_free, 2),
                "usdt_total": round(usdt_total, 2),
            },
            "pnl_pct": round(pnl_pct, 2),
            "total_pnl": round(self.tracker.total_pnl, 4),
            "total_realized_pnl": round(self.tracker.total_pnl, 4),
            "deals_completed": self.tracker.deal_count,
            "win_rate": round(
                self.tracker.win_count / self.tracker.deal_count * 100
                if self.tracker.deal_count else 0, 1
            ),
            "coins": coins,
            "symbols": list(self.coins.keys()),
            "tier_coin_cap": self.router.tier_coin_cap,
            "pool_split": (
                f"{EQUITY_TIER_SPLITS[self.router._split_tier_index][1]*100:.0f}/"
                f"{EQUITY_TIER_SPLITS[self.router._split_tier_index][2]*100:.0f}"
                if self.router._split_tier_index >= 0 else "90/10"
            ),
            "approved_symbols": sorted(self.router.active_allocations.keys()),
            "regime": (self._regime_alert_state
                       if self._regime_alert_state and self._regime_alert_state != "NONE"
                       else "RANGING"),
            "regime_detail": {
                "alert_state":  self._regime_alert_state,
                "signal_type":  self._regime_signal_type,
                "signal_count": self._regime_signal_count,
            },
            "trend_direction": "bearish" if self._regime_signal_type == "TOP" else "bullish",
            "fear_greed_index": self._cfgi_market,
            "cfgi": self._cfgi_market,
            "router": {
                "active_cash":  round(self.router.active_pool_cash, 2),
                "reserve_cash": round(self.router.reserve_pool_cash, 2),
            },
            "uptime_hours": round(
                (datetime.now(timezone.utc) - self._start_time).total_seconds() / 3600, 2
            ),
            "timeframe": "1h",
            "last_update": datetime.now(timezone.utc).isoformat(),
        }

        # Aggregate totals from CSV (survives restarts)
        try:
            csv_path = OUTPUT_DIR / "trades.csv"
            if csv_path.exists():
                import csv as csv_mod
                with open(csv_path) as cf:
                    reader = csv_mod.DictReader(cf)
                    csv_total_pnl  = 0.0
                    csv_total_fees = 0.0
                    csv_deals      = 0
                    csv_wins       = 0
                    for t in reader:
                        pnl = float(t.get("pnl", 0) or 0)
                        fee = float(t.get("fee", 0) or 0)
                        csv_total_pnl  += pnl
                        csv_total_fees += fee
                        csv_deals      += 1
                        if pnl > 0:
                            csv_wins += 1
                    status["total_realized_pnl"] = round(csv_total_pnl, 4)
                    status["total_fees"]         = round(csv_total_fees, 4)
                    status["deals_completed"]    = csv_deals
                    status["win_rate"]           = round(
                        csv_wins / csv_deals * 100 if csv_deals > 0 else 0, 1
                    )
        except Exception as e:
            logger.warning(f"CSV aggregate for status failed: {e}")

        # CANARY: Mark status with code version to detect stale code
        status["_code_version"] = "exchange-truth-v2"

        path = OUTPUT_DIR / "status.json"
        tmp  = path.with_suffix(".tmp")
        try:
            with open(tmp, "w") as f:
                json.dump(status, f, indent=2, default=str)
            tmp.replace(path)
        except Exception as e:
            logger.error(f"Failed to write status.json: {e}")

    # ── CFGI polling ──────────────────────────────────────────────────────────

    def _poll_cfgi(self):
        now = time.time()
        if now - self._cfgi_last_poll < 3600:
            return
        try:
            from trading.spot.cfgi_client import CFGIClient, VALID_TOKENS
            api_key = os.environ.get("CFGI_API_KEY")
            if not api_key:
                return
            client = CFGIClient(api_key)
            valid_set = set(VALID_TOKENS)
            active_bases = {sym.split("/")[0] for sym in self.coins}
            supported = [b for b in active_bases if b in valid_set]

            market_resp = client.get_current(["MARKET"], period=4, fields="cfgi")
            market_data = market_resp.get("MARKET", {})
            if isinstance(market_data, dict):
                self._cfgi_market = market_data.get("cfgi", market_data.get("value"))
            elif isinstance(market_data, (int, float)):
                self._cfgi_market = float(market_data)

            if supported:
                data = client.get_current(supported, period=4, fields="cfgi")
                for sym in self.coins:
                    base = sym.split("/")[0]
                    coin_data = data.get(base, {})
                    if isinstance(coin_data, dict):
                        val = coin_data.get("cfgi")
                        if val is not None:
                            self._cfgi_coins[sym] = float(val)
                    elif isinstance(coin_data, (int, float)):
                        self._cfgi_coins[sym] = float(coin_data)

            self._cfgi_last_poll = now
        except Exception as e:
            logger.warning(f"CFGI poll failed: {e}")
            self._cfgi_last_poll = now

    # ── Main loop ─────────────────────────────────────────────────────────────

    def run(self):
        def _shutdown_handler(signum, frame):
            logger.info("Shutdown signal received")
            self._shutdown = True

        signal.signal(signal.SIGINT,  _shutdown_handler)
        signal.signal(signal.SIGTERM, _shutdown_handler)

        # ── Exclusive file lock (prevents duplicate instances) ────────────
        # Uses msvcrt on Windows, fcntl on Linux/Mac.
        # The lock is held for the entire lifetime of the process.
        # If another instance tries to start, it will fail immediately.
        lock_path = OUTPUT_DIR / "bot.lock"
        self._lock_fh = open(lock_path, "w")
        try:
            if sys.platform == "win32":
                import msvcrt
                msvcrt.locking(self._lock_fh.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(self._lock_fh.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            self._lock_fh.write(f"{os.getpid()}:{int(time.time())}:v14pm\n")
            self._lock_fh.flush()
        except (OSError, IOError):
            logger.error("Another V14PM instance is already running (file lock held). Exiting.")
            self._lock_fh.close()
            sys.exit(1)

        # Also write PID file for monitoring/heartbeat (separate from lock)
        pid_path = OUTPUT_DIR / "bot.pid"
        pid_path.write_text(f"{os.getpid()}:{int(time.time())}:v14pm")

        try:
            # Restore state or start fresh
            if not self.fresh:
                restored = self._load_state()
                if restored:
                    logger.info(f"Restored state: bot_state={self.bot_state}")
            else:
                logger.info("FRESH start — clean state")

            # Initial rebalance: only if starting fresh (no saved state).
            # When restoring from state, engines are already configured —
            # skip startup rebalance to prevent it from overwriting the
            # restored engine state before reconciliation can correct it.
            if self.fresh or not self.coins:
                self._do_rebalance(datetime.now(timezone.utc))

            # Set leverage on exchange for all active coins (Aster defaults to 5x Cross)
            for sym in list(self.coins.keys()):
                self.client.ensure_leverage(sym, self.leverage)

            # Initial exchange sync (exchange-as-truth: overwrite engine state from exchange)
            self._sync_positions_from_exchange()
            logger.info("Initial exchange position sync complete.")

            # Audit #6: TP recovery — check if any TP orders filled while bot was down
            self._recover_tp_orders()

            # Announce startup
            mode_str = "PAUSED" if self.bot_state == BotState.PAUSED else "RUNNING"
            split_str = (
                f"{EQUITY_TIER_SPLITS[self.router._split_tier_index][1]*100:.0f}/"
                f"{EQUITY_TIER_SPLITS[self.router._split_tier_index][2]*100:.0f}"
                if self.router._split_tier_index >= 0 else "90/10"
            )
            send_telegram(
                f"🚀 {TG_PREFIX} <b>Live Bot Started</b>\n"
                f"Capital: ${self._tracked_capital:.2f} | Profile: {self.profile} | "
                f"1x leverage | Aster Perps\n"
                f"Tier: {self.router.tier_coin_cap} coins | Split: {split_str}\n"
                f"Active coins: {len(self.coins)}\n"
                f"State: {mode_str}"
            )

            last_tp_check = time.time()

            # ── Main loop ─────────────────────────────────────────────────
            while not self._shutdown:
                cycle_start = time.time()

                try:
                    current_dt = datetime.now(timezone.utc)

                    # Process Telegram commands
                    self._process_telegram_commands()

                    # Daily rebalance (midnight UTC)
                    self._do_rebalance(current_dt)

                    # Daily regime evaluation (midnight UTC)
                    self._evaluate_regime(current_dt)

                    # Check TP fills every TP_CHECK_INTERVAL seconds
                    if time.time() - last_tp_check >= TP_CHECK_INTERVAL:
                        self._check_tp_fills()
                        self._update_funding()
                        last_tp_check = time.time()

                    # Sync positions from exchange (exchange-as-truth, every cycle)
                    self._sync_positions_from_exchange()

                    # Detect deposits/withdrawals (Upgrade 1)
                    self._detect_capital_change()

                    # Process each active coin (Audit #5: 50 candles, process all missed)
                    for sym, cs in list(self.coins.items()):
                        if not cs.engine:
                            continue

                        # Capture phase before processing candles (for phase change detection)
                        prev_phase = cs.engine.phase if cs.engine else None

                        candles = self._fetch_candles(sym)
                        if not candles:
                            logger.warning(f"No candle data for {sym}")
                            continue

                        for candle in candles:
                            ts_ms = candle["timestamp"]
                            if ts_ms <= cs.last_candle_ts:
                                continue  # Already processed

                            ts_dt = datetime.fromtimestamp(ts_ms / 1000, tz=timezone.utc)
                            logger.info(
                                f"Candle {sym}: {ts_dt.strftime('%H:%M')} UTC | "
                                f"O={candle['open']:.6f} H={candle['high']:.6f} "
                                f"L={candle['low']:.6f} C={candle['close']:.6f}"
                            )

                            # Run engine tick
                            try:
                                actions = cs.engine.tick(candle, cash_available=cs.allocated_capital)
                            except Exception as e:
                                logger.error(f"Engine tick failed for {sym}: {e}")
                                continue

                            if actions:
                                logger.info(f"Engine actions for {sym}: {actions}")
                                for action in actions:
                                    self._execute_action(sym, cs, action)
                            else:
                                logger.info(
                                    f"Engine tick {sym}: no action "
                                    f"(warmed_up={cs.engine._warmed_up})"
                                )

                            # Upgrade 3: check for per-coin regime conflict after each tick
                            self._check_coin_regime_conflict(sym, cs)

                            cs.last_candle_ts = ts_ms
                            cs.engine._last_candle_ts = ts_ms

                        # Phase change detection (ported from old bot)
                        # If phase changed during candle processing, cancel stale TP orders
                        current_phase = cs.engine.phase if cs.engine else None
                        if current_phase != prev_phase and prev_phase is not None:
                            if cs.tp_order_id:
                                logger.info(
                                    f"Phase change {prev_phase} → {current_phase}: "
                                    f"cancelling TP for {sym}"
                                )
                                self.client.cancel_tp_order(sym, cs.tp_order_id)
                                cs.tp_order_id = None
                                cs.tp_limit_price = None

                    # CFGI poll
                    try:
                        self._poll_cfgi()
                    except Exception:
                        pass

                    # Write status
                    self._write_status()

                    # Save state
                    self._save_state()
                    self.tracker.save_csv()

                except Exception as e:
                    logger.error(f"Main loop error: {e}\n{traceback.format_exc()}")
                    time.sleep(10)
                    continue

                # Sleep until next poll
                elapsed = time.time() - cycle_start
                sleep_time = max(1, LIVE_POLL_INTERVAL - elapsed)
                deadline = time.time() + sleep_time
                while time.time() < deadline and not self._shutdown:
                    time.sleep(1)

        finally:
            # Save final state before exit
            self._save_state()
            self.tracker.save_csv()
            try:
                if pid_path.exists():
                    lock_content = pid_path.read_text().strip()
                    stored_pid = int(lock_content.split(":")[0])
                    if stored_pid == os.getpid():
                        pid_path.unlink()
            except Exception:
                pass
            # Release file lock
            try:
                if hasattr(self, '_lock_fh') and self._lock_fh:
                    if sys.platform == "win32":
                        import msvcrt
                        msvcrt.locking(self._lock_fh.fileno(), msvcrt.LK_UNLCK, 1)
                    else:
                        import fcntl
                        fcntl.flock(self._lock_fh.fileno(), fcntl.LOCK_UN)
                    self._lock_fh.close()
            except Exception:
                pass
            logger.info("V14PM Live Aster shut down cleanly")


# ── Entry point ───────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="V14PM Live Trading Bot — Aster DEX Perpetuals"
    )
    parser.add_argument(
        "--capital", type=float, required=True,
        help="Starting capital in USDT"
    )
    parser.add_argument(
        "--confirm", action="store_true",
        help="Required to enable live trading (safety flag)"
    )
    parser.add_argument(
        "--skip-backfill", action="store_true",
        help="Skip candle backfill on startup (use for restarts)"
    )
    parser.add_argument(
        "--fresh", action="store_true",
        help="Start fresh — ignore saved state (use for first launch)"
    )
    parser.add_argument(
        "--deposit", type=float, default=None, metavar="AMOUNT",
        help="Record a manual deposit and adjust capital (then start bot)"
    )
    parser.add_argument(
        "--withdraw", type=float, default=None, metavar="AMOUNT",
        help="Record a manual withdrawal and adjust capital (then start bot)"
    )
    parser.add_argument(
        "--ledger", action="store_true",
        help="Print capital ledger summary and exit"
    )
    args = parser.parse_args()

    # --ledger: print summary and exit
    if args.ledger:
        summary = get_ledger_summary(LEDGER_PATH)
        if summary is None:
            print(f"No capital ledger found at {LEDGER_PATH}")
        else:
            print("=" * 50)
            print("  Capital Ledger Summary")
            print("=" * 50)
            print(f"  Seed capital:      ${summary['seed_capital']:.2f}")
            print(f"  Total deposits:    ${summary['total_deposits']:.2f}")
            print(f"  Total withdrawals: ${summary['total_withdrawals']:.2f}")
            print(f"  Current capital:   ${summary['current_capital']:.2f}")
            print(f"  Transactions:      {summary['transaction_count']}")
            ledger = load_capital_ledger(LEDGER_PATH)
            if ledger:
                print("-" * 50)
                for t in ledger.get("transactions", []):
                    note = f"  [{t.get('note', '')}]" if t.get("note") else ""
                    ts = t.get("timestamp", t.get("date", "unknown"))[:19]
                    print(f"    {ts}  {t['type']:12s}  ${t['amount']:.2f}{note}")
            print("=" * 50)
        sys.exit(0)

    if not args.confirm:
        print("ERROR: --confirm flag required for live trading.")
        print("Usage: python -u -m trading.spot.run_v14_portfolio_live_aster "
              "--capital 340 --confirm --skip-backfill")
        sys.exit(1)

    # Set up log directory
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(OUTPUT_DIR / "bot.log", encoding="utf-8"),
        ],
        force=True,
    )

    # Process --deposit / --withdraw before starting bot
    if args.deposit:
        record_ledger_transaction(
            LEDGER_PATH, "deposit", args.deposit,
            note="Manual deposit via --deposit CLI flag"
        )
        logging.info(f"Recorded deposit: ${args.deposit:.2f}")

    if args.withdraw:
        record_ledger_transaction(
            LEDGER_PATH, "withdrawal", args.withdraw,
            note="Manual withdrawal via --withdraw CLI flag"
        )
        logging.info(f"Recorded withdrawal: ${args.withdraw:.2f}")

    bot = V14PortfolioLiveAster(
        capital=args.capital,
        confirm=args.confirm,
        skip_backfill=args.skip_backfill,
        fresh=args.fresh,
    )
    bot.run()


if __name__ == "__main__":
    main()
