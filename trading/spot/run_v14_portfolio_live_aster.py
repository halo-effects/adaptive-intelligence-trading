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
  - LIVE GUARD (exchange TP orders override engine)
  - Resting limit orders (TP executed by exchange, not polling)
  - Actual fill prices from exchange (never engine fallback)
  - Startup reconciliation (engine capital vs exchange balance)

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
from trading.spot.v14_capital_manager import CapitalRouter
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
REENTRY_COOLDOWN   = 60        # seconds to wait after TP fill before re-entry
TG_PREFIX          = "[V14-PM]"

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
        })
        if not dry_run:
            self._exchange.load_markets()

    def _aster_symbol(self, db_symbol: str) -> str:
        """Convert DB symbol (e.g. PEPE/USDT) to Aster perp symbol.
        Handles 1000-prefix for PEPE, BONK, FLOKI."""
        base = db_symbol.split("/")[0]
        prefix_coins = {"PEPE": "1000PEPE", "BONK": "1000BONK", "FLOKI": "1000FLOKI"}
        exchange_base = prefix_coins.get(base, base)
        return f"{exchange_base}/USDT:USDT"

    def fetch_balance(self) -> float:
        """Return available USDT balance in Perp account."""
        if self.dry_run:
            return 0.0
        try:
            bal = self._exchange.fetch_balance({"type": "future"})
            return float(bal.get("USDT", {}).get("free", 0))
        except Exception as e:
            logger.error(f"fetch_balance failed: {e}")
            return 0.0

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
                base = symbol.split("/")[0].lstrip("1000")
                result[base] = {
                    "qty": contracts,
                    "entry_price": float(p.get("entryPrice") or 0),
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

    def to_dict(self) -> dict:
        return {
            "symbol": self.symbol,
            "allocated_capital": self.allocated_capital,
            "tp_order_id": self.tp_order_id,
            "tp_limit_price": self.tp_limit_price,
            "last_candle_ts": self.last_candle_ts,
            "cumulative_funding": self.cumulative_funding,
            "last_funding_check_ms": self.last_funding_check_ms,
        }


# ── Main Bot ──────────────────────────────────────────────────────────────────

class V14PortfolioLiveAster:
    """
    V14PM Live Bot for Aster DEX Perpetuals.

    Execution layer from run_v14_live_aster.py (battle-tested with real money).
    PM logic from run_v14_portfolio_paper.py (capital rotation, regime detection).

    Key safeguards (all inherited from Aster live bot):
      - LIVE GUARD: Engine TP sells blocked when exchange limit order is active
      - Resting limit orders: Exchange handles TP, not polling
      - Fill price from exchange: Never fall back to engine price
      - PnL from actual proceeds: Not engine estimates
      - Startup reconciliation: Engine capital vs exchange balance
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
        self._reentry_cooldown_until: float = 0.0

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
            },
            "regime": {
                "signal_count": self._regime_signal_count,
                "signal_type": self._regime_signal_type,
                "alert_state": self._regime_alert_state,
            },
            "tg_update_offset": self._tg_update_offset,
            "open_deals": self.tracker._open_deals,
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
                    engine._warmed_up = True
                    cs.engine = engine
                    # Reset candle ts so we process the next candle
                    cs.last_candle_ts = 0
                    logger.info(f"  Created fresh engine for {sym} (no saved state)")
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

        # Restore regime state
        regime = state.get("regime", {})
        self._regime_signal_count = regime.get("signal_count", 0)
        self._regime_signal_type  = regime.get("signal_type")
        self._regime_alert_state  = regime.get("alert_state", "NONE")

        # Restore Telegram offset
        self._tg_update_offset = state.get("tg_update_offset", 0)

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

    # ── Reconciliation ────────────────────────────────────────────────────────

    def _reconcile_with_exchange(self):
        """
        Reconcile engine state against actual exchange state.
        Called on startup. Includes perp positions (Audit #4).

        Compares:
          Exchange: USDT balance + open position values
          Engine: router cash + engine invested amounts

        Uses additive correction (not multiplicative ratio).
        """
        try:
            exchange_usdt = self.client.fetch_balance()
            logger.info(f"Exchange USDT balance: ${exchange_usdt:.2f}")

            # Fetch open perp positions for position-aware reconciliation
            position_value = 0.0
            try:
                positions = self.client.fetch_open_positions()
                for base, pos in positions.items():
                    entry = pos.get("entry_price", 0)
                    pqty = pos.get("qty", 0)
                    unrealized = pos.get("unrealized_pnl", 0)
                    pval = entry * pqty
                    position_value += pval
                    logger.info(
                        f"  Position: {base} {pqty} @ ${entry:.6f} "
                        f"(unrealized: ${unrealized:+.2f})"
                    )
            except Exception as e:
                logger.warning(f"Position fetch failed (using engine data): {e}")

            exchange_total = exchange_usdt + position_value

            # Engine side: router cash + invested across all coin engines
            router_cash = self.router.active_pool_cash + self.router.reserve_pool_cash
            engine_invested = sum(
                cs.engine._engine.long_cost if cs.engine and cs.engine._engine else 0
                for cs in self.coins.values()
            )
            engine_total = router_cash + engine_invested

            drift = exchange_total - engine_total

            logger.info(
                f"RECONCILIATION:\n"
                f"  Exchange: ${exchange_usdt:.2f} USDT + ${position_value:.2f} positions "
                f"= ${exchange_total:.2f} total\n"
                f"  Engine:   ${router_cash:.2f} cash + ${engine_invested:.2f} invested "
                f"= ${engine_total:.2f} total\n"
                f"  Drift: ${drift:+.2f}"
            )

            DRIFT_THRESHOLD = 1.0
            if abs(drift) > DRIFT_THRESHOLD:
                # Additive correction applied to router active pool (Audit #4)
                old_active = self.router.active_pool_cash
                self.router.active_pool_cash += drift
                logger.warning(
                    f"RECONCILIATION ADJUSTMENT: active pool "
                    f"${old_active:.2f} → ${self.router.active_pool_cash:.2f} "
                    f"(adjusted by ${drift:+.2f})"
                )
                send_telegram(
                    f"🔧 {TG_PREFIX} <b>Reconciliation</b>\n"
                    f"Exchange: ${exchange_total:.2f} | Engine: ${engine_total:.2f}\n"
                    f"Drift: ${drift:+.2f} — corrected (active pool)"
                )
            else:
                logger.info(f"Reconciliation OK: drift=${drift:+.2f}")

        except Exception as e:
            logger.error(f"Reconciliation failed: {e}\n{traceback.format_exc()}")

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
        eng.long_tp which can shift after engine ticks."""
        if not cs.engine or not cs.engine._engine:
            return
        eng = cs.engine._engine
        tp_price = eng.long_tp
        qty = eng.long_coins
        if not tp_price or not qty:
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
        """Audit #6: On startup, check if any saved TP orders filled while bot was down."""
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
            # Use stored TP price (Audit #8), not eng.long_tp which may have shifted
            stored_tp = cs.tp_limit_price or eng.long_tp or actual_price
            engine_expected = stored_tp * actual_qty
            correction = actual_proceeds - engine_expected
            if abs(correction) > 0.01:
                eng.capital += correction
                logger.info(f"Engine capital corrected by ${correction:+.2f} for {sym}")
            else:
                eng.capital += actual_proceeds

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

        # Clean up
        cs.tp_order_id = None
        cs.tp_limit_price = None
        cs.cumulative_funding = 0.0
        self.tracker.save_csv()

        # Immediate re-entry: reset candle timestamp so the engine re-evaluates
        # on the next poll cycle (after cooldown). No need to wait for next hour.
        cs.last_candle_ts = 0
        self._reentry_cooldown_until = time.time() + REENTRY_COOLDOWN
        logger.info(f"Re-entry enabled for {sym} after {REENTRY_COOLDOWN}s cooldown")

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

    # ── Pre-tick snapshot (Audit #1) ─────────────────────────────────────────

    def _snapshot_engine(self, eng) -> dict:
        """Take a full snapshot of engine state before tick.
        Enables complete rollback on LIVE GUARD or failed orders."""
        if eng is None:
            return {}
        return {
            "long_coins": eng.long_coins,
            "long_avg_entry": eng.long_avg_entry,
            "long_layers": eng.long_layers,
            "long_last_buy": eng.long_last_buy,
            "long_tp": eng.long_tp,
            "long_cost": eng.long_cost,
            "long_trades": eng.long_trades,
            "long_wins": eng.long_wins,
            "long_pnl": eng.long_pnl,
            "capital": eng.capital,
            "_trades_len": len(eng.trades),
        }

    def _rollback_engine(self, eng, snapshot: dict):
        """Restore engine to pre-tick snapshot. Trims phantom trades."""
        if not snapshot or eng is None:
            return
        old_trades_len = snapshot.pop("_trades_len", None)
        for k, v in snapshot.items():
            setattr(eng, k, v)
        if old_trades_len is not None and len(eng.trades) > old_trades_len:
            removed = eng.trades[old_trades_len:]
            eng.trades = eng.trades[:old_trades_len]
            logger.warning(
                f"Rolled back {len(removed)} phantom trade(s): "
                f"{[t.get('action','?') for t in removed]}"
            )

    # ── Action execution ──────────────────────────────────────────────────────

    def _execute_action(self, sym: str, cs: CoinState, action: dict,
                        pre_tick_snapshot: dict = None):
        """
        Execute a single engine action against the exchange.

        Audit fixes applied:
          #1: Full pre-tick snapshot for LIVE GUARD rollback
          #2: Complete engine cleanup on TP fill
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

            # Re-entry cooldown: block buys immediately after TP fill
            if time.time() < self._reentry_cooldown_until:
                remaining = self._reentry_cooldown_until - time.time()
                logger.info(f"BUY blocked for {sym} — re-entry cooldown ({remaining:.0f}s remaining)")
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

                # Correct engine for actual fill vs expected
                if cs.engine and cs.engine._engine:
                    eng = cs.engine._engine
                    correction = actual_cost - cost
                    if abs(correction) > 0.01:
                        eng.capital -= correction
                        logger.info(f"BUY capital correction for {sym}: ${correction:+.4f}")

                    # Recalculate TP from actual fill price (not engine's candle close)
                    if eng.long_coins > 0 and eng.long_cost > 0:
                        old_cost = eng.long_cost - actual_cost
                        corrected_cost = old_cost + (actual_price * actual_qty)
                        eng.long_cost = corrected_cost
                        eng.long_avg_entry = corrected_cost / eng.long_coins
                        tp_pct = 1.0 + (eng.tp_pct if hasattr(eng, 'tp_pct') else 0.015)
                        eng.long_tp = eng.long_avg_entry * tp_pct
                        logger.info(
                            f"TP recalculated from actual fill: avg=${eng.long_avg_entry:.6f}, "
                            f"TP=${eng.long_tp:.6f} (engine was ${price:.6f})"
                        )

                self.tracker.on_buy(sym, actual_qty, actual_price,
                                    datetime.now(timezone.utc))

                # Place TP limit order (using corrected TP)
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
            # ── LIVE GUARD (Audit #1: full rollback) ──────────────────────
            # If a TP limit order is on the exchange, the exchange handles TP.
            # Block engine-generated TP sells. Roll back ALL engine state.
            if cs.tp_order_id and "TP" in reason:
                logger.info(
                    f"LIVE GUARD: Blocking engine TP sell for {sym} — "
                    f"TP order {cs.tp_order_id} is active on exchange. "
                    f"Engine price: ${price:.6f}"
                )
                # Full rollback from pre-tick snapshot
                if pre_tick_snapshot and cs.engine and cs.engine._engine:
                    self._rollback_engine(cs.engine._engine, pre_tick_snapshot.copy())
                    logger.info(
                        f"LIVE GUARD: Full engine rollback for {sym} — "
                        f"restored to pre-tick state"
                    )
                return

            # Non-TP sell: cancel TP order first, then market sell
            if cs.tp_order_id:
                logger.info(f"Cancelling TP order for {sym} before {reason} sell")
                self.client.cancel_tp_order(sym, cs.tp_order_id)
                cs.tp_order_id = None
                cs.tp_limit_price = None

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

                # Audit #2: Complete engine cleanup after sell
                if cs.engine and cs.engine._engine:
                    eng = cs.engine._engine
                    eng.capital += actual_proceeds
                    eng.long_trades = (eng.long_trades or 0) + 1
                    pnl = record.get("pnl", 0) if record else 0
                    if pnl >= 0:
                        eng.long_wins = (eng.long_wins or 0) + 1
                    eng.long_pnl = (eng.long_pnl or 0.0) + pnl
                    # Zero out ALL position fields
                    eng.long_coins = 0.0
                    eng.long_avg_entry = 0.0
                    eng.long_layers = 0
                    eng.long_last_buy = None
                    eng.long_tp = 0.0
                    eng.long_cost = 0.0

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
                # SELL FAILED — full rollback from pre-tick snapshot
                if pre_tick_snapshot and cs.engine and cs.engine._engine:
                    self._rollback_engine(cs.engine._engine, pre_tick_snapshot.copy())
                    logger.warning(
                        f"SELL FAILED for {sym} — full engine rollback. "
                        f"Will retry on next candle."
                    )
                    send_telegram(
                        f"⚠️ {TG_PREFIX} <b>SELL FAILED — engine rolled back</b>\n"
                        f"Symbol: {sym} | Reason: {reason}\n"
                        f"Will retry on next candle"
                    )
                else:
                    logger.error(
                        f"SELL FAILED for {sym} and no pre-tick snapshot! "
                        f"Engine state may be inconsistent."
                    )
                    send_telegram(
                        f"🔴 {TG_PREFIX} <b>SELL FAILED — NO ROLLBACK</b>\n"
                        f"Symbol: {sym} | Manual intervention may be needed"
                    )

    # ── Capital Router integration ────────────────────────────────────────────

    def _do_rebalance(self, current_dt: datetime):
        """Daily rebalance: update scanner, adjust allocations, spin up new engines."""
        today = current_dt.date()
        if self._last_rebalance_date == today:
            return

        logger.info(f"Daily rebalance for {today}")
        try:
            scanner_data = self.router.load_scanner_json(str(SCANNER_PATH))
            current_equity = self._compute_equity()
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
                    # Force warmup for live trading — we're trading against real
                    # exchange data, no need to wait for a daily boundary.
                    # The engine is initialized in LONG_DCA phase and ready to trade.
                    cs.engine._warmed_up = True
                    self.coins[sym] = cs
                else:
                    # Update allocation if no open position
                    cs = self.coins[sym]
                    cs.allocated_capital = alloc

            self._last_rebalance_date = today
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
                f"⏸️ {TG_PREFIX} <b>Trading Paused</b>\n"
                f"Grids frozen. No new entries or DCA layers.\n"
                f"Existing TP orders remain active on exchange.\n"
                f"Reply RESUME to restart trading.\n"
                f"Reply CLOSE <SYMBOL> to force-close a position."
            )
            logger.info("PAUSE: trading frozen by operator")
            self._save_state()

        elif text == "RESUME" or text == "RESUME TRADING":
            if self.bot_state != BotState.PAUSED:
                send_telegram(f"ℹ️ {TG_PREFIX} Not currently paused.")
                return
            self.bot_state = BotState.RUNNING
            send_telegram(
                f"▶️ {TG_PREFIX} <b>Trading Resumed</b>\n"
                f"Grids active. Normal operations resumed."
            )
            logger.info("RESUME: trading resumed")
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

        else:
            # Unknown command — silently ignore
            pass

    def _force_close_coin(self, sym: str):
        """Force-close a single position at market price."""
        cs = self.coins.get(sym)
        if not cs or not cs.engine or not cs.engine._engine:
            send_telegram(f"❓ {TG_PREFIX} No open position for {sym}")
            return

        eng = cs.engine._engine
        qty = eng.long_coins
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
        """Compute equity: capital + realized PnL + unrealized."""
        total_pnl = self.tracker.total_pnl
        unrealized = 0.0
        for cs in self.coins.values():
            if cs.engine and cs.engine._engine:
                eng = cs.engine._engine
                if eng.long_coins and eng.long_cost:
                    current_price = self.client.fetch_ticker_price(cs.symbol)
                    if current_price:
                        unrealized += (current_price - eng.long_tp or 0) * eng.long_coins
        return self.capital + total_pnl + unrealized

    def _write_status(self):
        """Write status.json for dashboard and heartbeat monitoring."""
        now = time.time()
        if now - self._last_status_write < STATUS_WRITE_INTERVAL:
            return
        self._last_status_write = now

        coins = {}
        for sym, cs in self.coins.items():
            if not cs.engine:
                continue
            try:
                st = cs.engine.get_status()
                if "coins" in st:
                    coin_data = st["coins"].get(sym, {})
                    coin_data["cumulative_funding"] = round(cs.cumulative_funding, 6)
                    coin_data["tp_order_id"] = cs.tp_order_id
                    if sym in self._cfgi_coins:
                        coin_data["cfgi"] = round(self._cfgi_coins[sym], 1)
                    coins[sym] = coin_data
            except Exception as e:
                logger.error(f"get_status failed for {sym}: {e}")

        equity = self._compute_equity()
        pnl_pct = ((equity - self.capital) / self.capital * 100) if self.capital > 0 else 0.0

        status = {
            "running": True,
            "mode": "live",
            "engine": "v14-pm",
            "exchange": "aster_perp",
            "profile": self.profile,
            "leverage": self.leverage,
            "bot_state": self.bot_state,
            "capital": self.capital,
            "equity": round(equity, 2),
            "pnl_pct": round(pnl_pct, 2),
            "total_pnl": round(self.tracker.total_pnl, 4),
            "deals_completed": self.tracker.deal_count,
            "win_rate": round(
                self.tracker.win_count / self.tracker.deal_count * 100
                if self.tracker.deal_count else 0, 1
            ),
            "coins": coins,
            "symbols": list(self.coins.keys()),
            "tier_coin_cap": self.router.tier_coin_cap,
            "approved_symbols": sorted(
                self.router.active_allocations.keys()
            ),
            "regime": {
                "alert_state": self._regime_alert_state,
                "signal_type": self._regime_signal_type,
                "signal_count": self._regime_signal_count,
            },
            "fear_greed_index": self._cfgi_market,
            "router": {
                "active_cash": round(self.router.active_pool_cash, 2),
                "reserve_cash": round(self.router.reserve_pool_cash, 2),
            },
            "uptime_hours": round(
                (datetime.now(timezone.utc) - self._start_time).total_seconds() / 3600, 2
            ),
            "last_update": datetime.now(timezone.utc).isoformat(),
        }

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

        # PID lock
        pid_path = OUTPUT_DIR / "bot.pid"
        if pid_path.exists():
            try:
                old_pid = int(pid_path.read_text().strip())
                try:
                    os.kill(old_pid, 0)
                    logger.error(f"Another instance running (PID {old_pid}). Exiting.")
                    sys.exit(1)
                except OSError:
                    logger.warning(f"Stale PID lock (PID {old_pid}). Overwriting.")
            except Exception:
                pass
        pid_path.write_text(str(os.getpid()))

        try:
            # Restore state or start fresh
            if not self.fresh:
                restored = self._load_state()
                if restored:
                    logger.info(f"Restored state: bot_state={self.bot_state}")
            else:
                logger.info("FRESH start — clean state")

            # Initial rebalance to set up coin engines
            self._do_rebalance(datetime.now(timezone.utc))

            # Startup reconciliation
            self._reconcile_with_exchange()

            # Audit #6: TP recovery — check if any TP orders filled while bot was down
            self._recover_tp_orders()

            # Announce startup
            mode_str = "PAUSED" if self.bot_state == BotState.PAUSED else "RUNNING"
            send_telegram(
                f"🚀 {TG_PREFIX} <b>Live Bot Started</b>\n"
                f"Capital: ${self.capital:.2f} | Profile: {self.profile} | "
                f"1x leverage | Aster Perps\n"
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

                    # Process each active coin (Audit #5: 50 candles, process all missed)
                    for sym, cs in list(self.coins.items()):
                        if not cs.engine:
                            continue

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

                            # Audit #1: Take pre-tick snapshot for rollback
                            eng = cs.engine._engine if cs.engine else None
                            pre_tick = self._snapshot_engine(eng)

                            # Run engine tick
                            try:
                                actions = cs.engine.tick(candle, cash_available=0)
                            except Exception as e:
                                logger.error(f"Engine tick failed for {sym}: {e}")
                                continue

                            if actions:
                                logger.info(f"Engine actions for {sym}: {actions}")
                                for action in actions:
                                    self._execute_action(sym, cs, action,
                                                         pre_tick_snapshot=pre_tick)
                            else:
                                logger.info(
                                    f"Engine tick {sym}: no action "
                                    f"(warmed_up={cs.engine._warmed_up})"
                                )

                            cs.last_candle_ts = ts_ms
                            cs.engine._last_candle_ts = ts_ms

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
                    stored = int(pid_path.read_text().strip())
                    if stored == os.getpid():
                        pid_path.unlink()
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
    args = parser.parse_args()

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

    bot = V14PortfolioLiveAster(
        capital=args.capital,
        confirm=args.confirm,
        skip_backfill=args.skip_backfill,
        fresh=args.fresh,
    )
    bot.run()


if __name__ == "__main__":
    main()
