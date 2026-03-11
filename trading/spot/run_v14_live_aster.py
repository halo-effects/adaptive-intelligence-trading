#!/usr/bin/env python3
"""
V14 Live Trading Bot — Aster Exchange
=======================================
⚠️ REAL MONEY. This places actual orders on Aster.

Architecture:
  - V14 DCA engine (same as paper bot) handles all trading logic
  - SpotExchangeClient (CCXT) handles Aster API calls
  - Engine ticks on 1h candles → produces actions → executor places real orders
  - Spot LONG_DCA only initially (SHORT_DCA via futures when needed)
  - Balance reconciliation every cycle
  - All orders logged to Telegram with [V14-LIVE] prefix

Usage:
    python -m trading.spot.run_v14_live_aster --confirm
    python -m trading.spot.run_v14_live_aster --dry-run   # Log orders, don't execute
    python -m trading.spot.run_v14_live_aster --test       # Connectivity test only
"""

import argparse
import csv
import json
import logging
import os
import signal
import sqlite3
import sys
import time
import traceback
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

# Ensure workspace root is on path
_WORKSPACE = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_WORKSPACE))

from trading.spot.v14_lifecycle_engine import V14LifecycleEngine, V14_PROFILES
from trading.spot.exchange_client import SpotExchangeClient

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SYMBOL = "ASTER/USDT"
DB_SYMBOL = "ASTER/USDT"
DEFAULT_OUTPUT_DIR = _WORKSPACE / "trading" / "spot" / "live" / "v14"
DEFAULT_CAPITAL = 300.0
DEFAULT_PROFILE = "high"
DEFAULT_START_DATE = "2025-10-01"
LIVE_POLL_INTERVAL = 65  # seconds (slightly over 1 min to avoid rate limits)

DB_PATH = Path(os.environ.get("AIT_CANDLES_DB", str(_WORKSPACE / "trading" / "spot" / "data" / "candles.db")))

logger = logging.getLogger("v14_live")

# Telegram prefix for all live notifications
TG_PREFIX = "[V14-LIVE]"


# ---------------------------------------------------------------------------
# Telegram
# ---------------------------------------------------------------------------

def send_telegram(msg: str):
    """Send a Telegram notification with [V14-LIVE] prefix."""
    token = os.environ.get("AIT_TG_TOKEN", "")
    chat_id = os.environ.get("AIT_TG_CHAT_ID", "")
    if not (token and chat_id):
        return
    try:
        import requests
        requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat_id, "text": msg, "parse_mode": "HTML"},
            timeout=10,
        )
    except Exception as e:
        logger.warning(f"Telegram send failed: {e}")


# ---------------------------------------------------------------------------
# Database helpers (for backfill signal context)
# ---------------------------------------------------------------------------

def load_hourly_candles(symbol: str, start_ts: float = 0) -> pd.DataFrame:
    """Load 1h candles from candles.db."""
    conn = sqlite3.connect(str(DB_PATH))
    query = """
        SELECT timestamp, open, high, low, close, volume
        FROM candles
        WHERE symbol = ? AND timeframe = '1h' AND timestamp >= ?
        ORDER BY timestamp ASC
    """
    df = pd.read_sql_query(query, conn, params=(symbol, start_ts))
    conn.close()
    if not df.empty:
        df["timestamp_ms"] = df["timestamp"]
        df["dt"] = pd.to_datetime(df["timestamp"], unit="ms", utc=True)
        df.set_index("dt", inplace=True)
    return df


def load_daily_candles(symbol: str) -> pd.DataFrame:
    """Load daily candles from candles_daily table."""
    conn = sqlite3.connect(str(DB_PATH))
    query = """
        SELECT timestamp, open, high, low, close, volume
        FROM candles_daily
        WHERE symbol = ?
        ORDER BY timestamp ASC
    """
    df = pd.read_sql_query(query, conn, params=(symbol,))
    conn.close()
    if not df.empty:
        df["dt"] = pd.to_datetime(df["timestamp"], unit="ms", utc=True)
        df.set_index("dt", inplace=True)
    return df


# ---------------------------------------------------------------------------
# Order Executor — bridges engine actions to real Aster orders
# ---------------------------------------------------------------------------

class AsterOrderExecutor:
    """Executes V14 engine actions as real orders on Aster spot."""

    def __init__(self, client: SpotExchangeClient, symbol: str, dry_run: bool = False):
        self.client = client
        self.symbol = symbol
        self.dry_run = dry_run
        self.base_currency = symbol.split("/")[0]  # ASTER
        self.quote_currency = symbol.split("/")[1]  # USDT

        # Market info (populated on first use)
        self._min_amount: Optional[float] = None
        self._min_cost: Optional[float] = None
        self._amount_precision: Optional[int] = None
        self._price_precision: Optional[int] = None
        self._maker_fee: float = 0.0
        self._taker_fee: float = 0.0004  # 0.04% default

    def initialize(self):
        """Load market info and fee structure from Aster."""
        try:
            info = self.client.get_min_order_size(self.symbol)
            self._min_amount = info.get("min_amount")
            self._min_cost = info.get("min_cost")
            self._amount_precision = info.get("amount_precision")
            self._price_precision = info.get("price_precision")
            logger.info(
                f"Market info for {self.symbol}: "
                f"min_amount={self._min_amount}, min_cost={self._min_cost}, "
                f"amount_prec={self._amount_precision}, price_prec={self._price_precision}"
            )
        except Exception as e:
            logger.warning(f"Failed to load market info: {e}")

        try:
            fees = self.client.get_trading_fees(self.symbol)
            self._maker_fee = fees.get("maker", 0.0) or 0.0
            self._taker_fee = fees.get("taker", 0.0004) or 0.0004
            logger.info(f"Fees: maker={self._maker_fee}, taker={self._taker_fee}")
        except Exception as e:
            logger.warning(f"Failed to load fee info: {e}")

    def get_balance(self) -> Dict[str, float]:
        """Get USDT and base currency balances."""
        try:
            usdt = self.client.fetch_balance(self.quote_currency)
            base = self.client.fetch_balance(self.base_currency)
            return {
                "usdt_free": usdt.get("free", 0) or 0,
                "usdt_total": usdt.get("total", 0) or 0,
                "base_free": base.get("free", 0) or 0,
                "base_total": base.get("total", 0) or 0,
            }
        except Exception as e:
            logger.error(f"Balance fetch failed: {e}")
            return {"usdt_free": 0, "usdt_total": 0, "base_free": 0, "base_total": 0}

    def get_current_price(self) -> Optional[float]:
        """Get current mid price from Aster."""
        try:
            ticker = self.client.fetch_ticker(self.symbol)
            return ticker.get("last") or ticker.get("close")
        except Exception as e:
            logger.error(f"Price fetch failed: {e}")
            return None

    def _round_amount(self, amount: float) -> float:
        """Round amount to exchange precision.

        CCXT returns precision as either:
        - int (number of decimal places): e.g. 2 → round to 2 decimals
        - float (step size): e.g. 0.01 → round to nearest 0.01
        """
        if self._amount_precision is not None:
            p = self._amount_precision
            if isinstance(p, float) and p < 1:
                # Step size: e.g. 0.01 → 2 decimal places
                import math
                decimals = max(0, -int(math.floor(math.log10(p))))
                return round(amount - (amount % p), decimals)
            return round(amount, int(p))
        return round(amount, 8)

    def _round_price(self, price: float) -> float:
        """Round price to exchange precision."""
        if self._price_precision is not None:
            p = self._price_precision
            if isinstance(p, float) and p < 1:
                import math
                decimals = max(0, -int(math.floor(math.log10(p))))
                return round(price - (price % p), decimals)
            return round(price, int(p))
        return round(price, 8)

    def execute_buy(self, qty: float, price: float, reason: str) -> Optional[Dict]:
        """Execute a spot buy order.

        Uses market order for reliability. Returns fill info or None on failure.
        """
        qty = self._round_amount(qty)
        cost = qty * price

        # Pre-flight checks
        if self._min_amount and qty < self._min_amount:
            logger.warning(f"BUY qty {qty} below minimum {self._min_amount}, skipping")
            send_telegram(
                f"⚠️ {TG_PREFIX} BUY skipped — qty {qty} below min {self._min_amount}\n"
                f"Reason: {reason}"
            )
            return None

        if self._min_cost and cost < self._min_cost:
            logger.warning(f"BUY cost ${cost:.2f} below minimum ${self._min_cost}, skipping")
            send_telegram(
                f"⚠️ {TG_PREFIX} BUY skipped — cost ${cost:.2f} below min ${self._min_cost}\n"
                f"Reason: {reason}"
            )
            return None

        # Balance check
        bal = self.get_balance()
        if bal["usdt_free"] < cost * 1.01:  # 1% buffer for fees
            logger.warning(
                f"Insufficient USDT: need ${cost:.2f}, have ${bal['usdt_free']:.2f}"
            )
            send_telegram(
                f"⚠️ {TG_PREFIX} BUY failed — insufficient USDT\n"
                f"Need: ${cost:.2f} | Have: ${bal['usdt_free']:.2f}\n"
                f"Reason: {reason}"
            )
            return None

        if self.dry_run:
            logger.info(f"[DRY RUN] BUY {qty} {self.base_currency} @ ${price:.6f} (${cost:.2f}) — {reason}")
            send_telegram(
                f"🔵 {TG_PREFIX} <b>[DRY RUN] BUY</b> {qty:.4f} {self.base_currency}\n"
                f"Price: ${price:.6f} | Cost: ${cost:.2f}\n"
                f"Reason: {reason}"
            )
            return {"status": "dry_run", "qty": qty, "price": price, "cost": cost}

        # Execute market buy
        try:
            logger.info(f"Executing MARKET BUY {qty} {self.symbol} (${cost:.2f}) — {reason}")
            order = self.client.create_market_buy(self.symbol, qty)

            fill_price = order.get("average") or order.get("price") or price
            fill_qty = order.get("filled") or qty
            fill_cost = order.get("cost") or (fill_price * fill_qty)
            fee_cost = 0
            if order.get("fee"):
                fee_cost = order["fee"].get("cost", 0) or 0

            logger.info(
                f"BUY FILLED: {fill_qty} @ ${fill_price:.6f} = ${fill_cost:.2f} "
                f"(fee: ${fee_cost:.4f}) — {reason}"
            )
            send_telegram(
                f"🟢 {TG_PREFIX} <b>BUY</b> {fill_qty:.4f} {self.base_currency}\n"
                f"Price: ${fill_price:.6f} | Cost: ${fill_cost:.2f}\n"
                f"Fee: ${fee_cost:.4f} | {reason}"
            )
            return {
                "status": "filled",
                "order_id": order.get("id"),
                "qty": fill_qty,
                "price": fill_price,
                "cost": fill_cost,
                "fee": fee_cost,
            }

        except Exception as e:
            logger.error(f"BUY order failed: {e}\n{traceback.format_exc()}")
            send_telegram(
                f"🔴 {TG_PREFIX} <b>BUY FAILED</b>\n"
                f"Qty: {qty:.4f} | Price: ${price:.6f}\n"
                f"Error: {str(e)[:200]}"
            )
            return None

    def execute_sell(self, qty: float, price: float, reason: str) -> Optional[Dict]:
        """Execute a spot sell order.

        Uses market order for reliability. Returns fill info or None on failure.
        """
        qty = self._round_amount(qty)

        # Pre-flight: do we hold enough?
        bal = self.get_balance()
        available = bal["base_free"]
        if available < qty * 0.99:  # 1% tolerance for rounding
            # Far too little — sell what we have if above minimum
            if available > 0 and (not self._min_amount or available >= self._min_amount):
                logger.warning(
                    f"Adjusting sell qty from {qty} to {available} (balance limit)"
                )
                qty = self._round_amount(available)
            else:
                logger.warning(f"Insufficient {self.base_currency}: need {qty}, have {available}")
                send_telegram(
                    f"⚠️ {TG_PREFIX} SELL failed — insufficient {self.base_currency}\n"
                    f"Need: {qty:.4f} | Have: {available:.4f}\n"
                    f"Reason: {reason}"
                )
                return None
        elif available < qty:
            # Close enough but exchange balance is slightly less (fee/rounding drift)
            # Cap at actual balance to avoid "insufficient balance" rejection
            logger.info(
                f"Capping sell qty from {qty:.6f} to {available:.6f} "
                f"(drift: {qty - available:.6f} {self.base_currency})"
            )
            qty = self._round_amount(available)

        if self.dry_run:
            proceeds = qty * price
            logger.info(f"[DRY RUN] SELL {qty} {self.base_currency} @ ${price:.6f} (${proceeds:.2f}) — {reason}")
            send_telegram(
                f"🔵 {TG_PREFIX} <b>[DRY RUN] SELL</b> {qty:.4f} {self.base_currency}\n"
                f"Price: ${price:.6f} | Proceeds: ${proceeds:.2f}\n"
                f"Reason: {reason}"
            )
            return {"status": "dry_run", "qty": qty, "price": price, "proceeds": proceeds}

        # Execute market sell
        try:
            logger.info(f"Executing MARKET SELL {qty} {self.symbol} — {reason}")
            order = self.client.create_market_sell(self.symbol, qty)

            fill_price = order.get("average") or order.get("price") or price
            fill_qty = order.get("filled") or qty
            proceeds = order.get("cost") or (fill_price * fill_qty)
            fee_cost = 0
            if order.get("fee"):
                fee_cost = order["fee"].get("cost", 0) or 0

            logger.info(
                f"SELL FILLED: {fill_qty} @ ${fill_price:.6f} = ${proceeds:.2f} "
                f"(fee: ${fee_cost:.4f}) — {reason}"
            )
            send_telegram(
                f"🟡 {TG_PREFIX} <b>SELL</b> {fill_qty:.4f} {self.base_currency}\n"
                f"Price: ${fill_price:.6f} | Proceeds: ${proceeds:.2f}\n"
                f"Fee: ${fee_cost:.4f} | {reason}"
            )
            return {
                "status": "filled",
                "order_id": order.get("id"),
                "qty": fill_qty,
                "price": fill_price,
                "proceeds": proceeds,
                "fee": fee_cost,
            }

        except Exception as e:
            logger.error(f"SELL order failed: {e}\n{traceback.format_exc()}")
            send_telegram(
                f"🔴 {TG_PREFIX} <b>SELL FAILED</b>\n"
                f"Qty: {qty:.4f} | Price: ${price:.6f}\n"
                f"Error: {str(e)[:200]}"
            )
            return None


# ---------------------------------------------------------------------------
# Trade Tracker (same pattern as paper bot)
# ---------------------------------------------------------------------------

class TradeTracker:
    """Tracks trades and writes trades.csv."""

    def __init__(self, output_dir: Path):
        self.output_dir = output_dir
        self.trades: List[dict] = []
        self._deal_counter = 0
        self._open_deals: Dict[str, dict] = {}
        self._existing_keys: set = set()

    def process_actions(self, symbol: str, actions: List[dict], timestamp: datetime):
        """Process engine actions and track trades."""
        for act in actions:
            action = act.get("action", "")
            price = act.get("price", 0)
            qty = act.get("qty", 0)
            cost = price * qty if price and qty else 0

            if action == "BUY":
                key = f"{symbol}:long"
                if key not in self._open_deals:
                    self._deal_counter += 1
                    self._open_deals[key] = {
                        "deal_id": self._deal_counter,
                        "symbol": symbol,
                        "open_time": timestamp.isoformat(),
                        "regime": act.get("phase", "LONG_DCA"),
                        "layers": 0,
                        "invested": 0.0,
                    }
                deal = self._open_deals[key]
                deal["layers"] += 1
                deal["invested"] += act.get("cost", cost)

            elif action == "SELL":
                key = f"{symbol}:long"
                deal = self._open_deals.pop(key, None)
                if deal:
                    pnl = act.get("pnl", 0.0)
                    invested = deal["invested"]
                    ret_pct = (pnl / invested * 100) if invested > 0 else 0.0
                    open_dt = datetime.fromisoformat(deal["open_time"])
                    duration_h = (timestamp - open_dt).total_seconds() / 3600
                    trade_key = f"{symbol}|{deal['open_time']}|{timestamp.isoformat()}"
                    if trade_key not in self._existing_keys:
                        self._existing_keys.add(trade_key)
                        self.trades.append({
                            "deal_id": deal["deal_id"],
                            "symbol": symbol,
                            "open_time": deal["open_time"],
                            "close_time": timestamp.isoformat(),
                            "regime": deal["regime"],
                            "layers": deal["layers"],
                            "invested": round(invested, 2),
                            "pnl": round(pnl, 4),
                            "return_pct": round(ret_pct, 2),
                            "duration_h": round(duration_h, 1),
                        })

    def save_csv(self):
        """Write trades.csv."""
        try:
            path = self.output_dir / "trades.csv"
            seen = set()
            unique = []
            for t in self.trades:
                key = f"{t['symbol']}|{t['open_time']}|{t['close_time']}"
                if key not in seen:
                    seen.add(key)
                    unique.append(t)
            unique.sort(key=lambda t: t.get('close_time', t.get('open_time', '')))
            with open(path, "w", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=[
                    "deal_id", "symbol", "open_time", "close_time", "regime",
                    "layers", "invested", "pnl", "return_pct", "duration_h",
                ], extrasaction='ignore')
                writer.writeheader()
                writer.writerows(unique)
        except Exception as e:
            logger.error(f"Failed to save trades CSV: {e}")

    def load_existing(self):
        """Load existing trades.csv for skip-backfill restarts."""
        path = self.output_dir / "trades.csv"
        if not path.exists():
            return
        try:
            with open(path, "r") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    row["deal_id"] = int(row["deal_id"])
                    row["layers"] = int(row["layers"])
                    row["invested"] = float(row["invested"])
                    row["pnl"] = float(row["pnl"])
                    row["return_pct"] = float(row["return_pct"])
                    row["duration_h"] = float(row["duration_h"])
                    self.trades.append(row)
                    key = f"{row['symbol']}|{row['open_time']}|{row['close_time']}"
                    self._existing_keys.add(key)
                    if row["deal_id"] > self._deal_counter:
                        self._deal_counter = row["deal_id"]
            logger.info(f"Loaded {len(self.trades)} existing trades from CSV")
        except Exception as e:
            logger.warning(f"Failed to load existing trades: {e}")


# ---------------------------------------------------------------------------
# V14LiveBot
# ---------------------------------------------------------------------------

class V14LiveBot:
    """V14 DCA live trading bot for Aster exchange."""

    def __init__(
        self,
        capital: float = DEFAULT_CAPITAL,
        profile: str = DEFAULT_PROFILE,
        output_dir: Optional[Path] = None,
        start_date: str = DEFAULT_START_DATE,
        dry_run: bool = False,
    ):
        self.symbol = SYMBOL
        self.capital = capital
        self.profile = profile
        self.output_dir = Path(output_dir or DEFAULT_OUTPUT_DIR)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.start_date = start_date
        self.dry_run = dry_run
        # Spot trading = no leverage. Override to 1.0 regardless of profile.
        # High profile DCA params (Dev=1.5%, 12 layers, TP=1.5%) still apply.
        self.leverage = 1.0

        # V14 engine (single coin, full capital allocation)
        self.engine = V14LifecycleEngine(
            symbol=SYMBOL, capital=capital, profile=profile
        )
        # Force engine leverage to 1.0 for spot (profile may say 1.5)
        self.engine.leverage = 1.0

        # Exchange client
        self.exchange_client = SpotExchangeClient()

        # Order executor
        self.executor: Optional[AsterOrderExecutor] = None

        # Cash tracking
        self.cash = capital

        # Trade tracker
        self.tracker = TradeTracker(self.output_dir)

        # Shutdown flag
        self._shutdown = False
        self._start_time = datetime.now(timezone.utc)

        # Last processed candle timestamp
        self._last_candle_ts: int = 0

        # Balance reconciliation
        self._last_recon_time: float = 0
        self._recon_interval: float = 300  # 5 minutes

        # CFGI / Fear & Greed
        self._cfgi_market: Optional[float] = None
        self._cfgi_coins: Dict[str, float] = {}
        self._cfgi_last_poll: float = 0.0

        # Setup logging
        self._setup_logging()

    def _setup_logging(self):
        log_path = self.output_dir / "bot.log"
        handler = logging.FileHandler(str(log_path), encoding='utf-8')
        handler.setFormatter(logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
        ))
        root = logging.getLogger()
        root.addHandler(handler)
        root.setLevel(logging.INFO)

        # Force UTF-8 on stdout
        import io
        utf8_stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        stdout_handler = logging.StreamHandler(utf8_stdout)
        stdout_handler.setFormatter(logging.Formatter(
            "%(asctime)s [%(levelname)s] %(message)s"
        ))
        root.addHandler(stdout_handler)

    # -------------------------------------------------------------------
    # Exchange connection
    # -------------------------------------------------------------------

    def connect_exchange(self) -> bool:
        """Connect to Aster and validate credentials."""
        try:
            # Load .env if present
            env_path = self.output_dir / ".env"
            if env_path.exists():
                self._load_dotenv(env_path)

            self.exchange_client.connect("aster")
            self.executor = AsterOrderExecutor(
                self.exchange_client, self.symbol, dry_run=self.dry_run
            )
            self.executor.initialize()

            # Test balance fetch
            bal = self.executor.get_balance()
            logger.info(
                f"Connected to Aster — USDT: ${bal['usdt_free']:.2f} free / "
                f"${bal['usdt_total']:.2f} total, "
                f"{self.executor.base_currency}: {bal['base_free']:.4f} free"
            )

            if bal['usdt_total'] < 1 and bal['base_total'] < 1:
                logger.warning("Very low balances — is this the right account?")

            return True

        except Exception as e:
            logger.error(f"Failed to connect to Aster: {e}\n{traceback.format_exc()}")
            return False

    def _load_dotenv(self, path: Path):
        """Simple .env file loader."""
        try:
            with open(path) as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue
                    if '=' in line:
                        key, val = line.split('=', 1)
                        os.environ[key.strip()] = val.strip()
            logger.info(f"Loaded environment from {path}")
        except Exception as e:
            logger.warning(f"Failed to load .env: {e}")

    def test_connectivity(self) -> bool:
        """Test exchange connectivity and print account info."""
        if not self.connect_exchange():
            print("❌ Connection failed")
            return False

        bal = self.executor.get_balance()
        price = self.executor.get_current_price()

        print(f"✅ Connected to Aster")
        print(f"   Symbol: {self.symbol}")
        print(f"   Price:  ${price:.6f}" if price else "   Price: N/A")
        print(f"   USDT:   ${bal['usdt_free']:.2f} free / ${bal['usdt_total']:.2f} total")
        print(f"   {self.executor.base_currency}:  {bal['base_free']:.4f} free / {bal['base_total']:.4f} total")
        print(f"   Min amount: {self.executor._min_amount}")
        print(f"   Min cost:   {self.executor._min_cost}")
        print(f"   Fees: maker={self.executor._maker_fee}, taker={self.executor._taker_fee}")

        # Check if we have enough capital
        total_value = bal['usdt_total'] + (bal['base_total'] * price if price else 0)
        print(f"   Total value: ~${total_value:.2f}")

        return True

    # -------------------------------------------------------------------
    # Backfill (signal context only — no real orders)
    # -------------------------------------------------------------------

    def backfill(self):
        """Run historical backfill to build signal context.

        This runs the V14 engine on historical candles (from DB) to establish
        signal state (StochRSI, structure, etc.) WITHOUT executing any orders.
        The engine's position state after backfill represents what WOULD have
        happened — we ignore it and start fresh for live trading.
        """
        logger.info(f"Starting V14 signal backfill from {self.start_date}")
        send_telegram(f"📊 {TG_PREFIX} Starting signal backfill from {self.start_date}")

        end_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")

        # Run backfill through engine (builds signal state)
        actions = self.engine.backfill_direct(self.start_date, end_date)

        # Log what the backfill produced (for reference only)
        engine = self.engine
        logger.info(
            f"Signal backfill complete — engine phase={engine.phase}, "
            f"deals_history={engine.deals_completed}, "
            f"realized_pnl_history=${engine.realized_pnl:.2f}"
        )

        # IMPORTANT: Reset the engine's position state for live trading.
        # We keep the signal state (StochRSI, structure, top/bottom detection)
        # but clear positions — real positions will be built from actual orders.
        self._reset_engine_positions()

        send_telegram(
            f"✅ {TG_PREFIX} Signal backfill complete\n"
            f"Engine phase: {engine.phase}\n"
            f"Historical deals: {engine.deals_completed}\n"
            f"Signal state initialized, positions reset for live"
        )

    def _reset_engine_positions(self):
        """Reset engine position state for fresh live start.

        Preserves: signal state, phase, top/bottom detection state
        Resets: positions, capital, PnL counters
        """
        eng = self.engine._engine
        if eng is None:
            return

        # Reset positions
        eng.capital = self.capital
        eng.long_coins = 0.0
        eng.long_avg_entry = 0.0
        eng.long_layers = 0
        eng.long_last_buy = None
        eng.long_tp = 0.0
        eng.long_cost = 0.0
        eng.short_coins = 0.0
        eng.short_avg_entry = 0.0
        eng.short_layers = 0
        eng.short_last_sell = None
        eng.short_tp = 0.0
        eng.short_cost = 0.0

        # Reset PnL counters (live will track from zero)
        eng.long_trades = 0
        eng.long_wins = 0
        eng.long_pnl = 0.0
        eng.short_trades = 0
        eng.short_wins = 0
        eng.short_pnl = 0.0
        eng.total_fees = 0.0
        eng.equity_curve = []

        # Reset cash tracking
        self.cash = self.capital

        logger.info(
            f"Engine positions reset — capital=${self.capital}, "
            f"phase={eng.phase} (preserved), "
            f"top_detected={eng.top_detected} (preserved)"
        )

    # -------------------------------------------------------------------
    # Live trading
    # -------------------------------------------------------------------

    def run_live(self):
        """Main live loop — fetch candles from Aster, tick engine, execute orders."""
        logger.info(f"Entering live trading loop (dry_run={self.dry_run})")
        mode_str = "DRY RUN" if self.dry_run else "LIVE"
        send_telegram(
            f"🔴 {TG_PREFIX} <b>{mode_str} trading started</b>\n"
            f"Symbol: {self.symbol}\n"
            f"Capital: ${self.capital:.0f} | Profile: {self.profile}\n"
            f"Phase: {self.engine.phase}"
        )

        while not self._shutdown:
            try:
                cycle_start = time.time()

                # Fetch latest candles from Aster
                try:
                    ohlcv = self.exchange_client.fetch_ohlcv(self.symbol, "1h", limit=50)
                except Exception as e:
                    logger.error(f"Failed to fetch candles: {e}")
                    time.sleep(30)
                    continue

                if not ohlcv:
                    logger.warning("No candle data received")
                    time.sleep(30)
                    continue

                prev_phase = self.engine.phase

                # Update current price from latest candle (even if incomplete)
                if ohlcv:
                    latest_price = float(ohlcv[-1][4])
                    self.engine.current_price = latest_price

                for bar in ohlcv:
                    ts_ms = int(bar[0])
                    if ts_ms <= self._last_candle_ts:
                        continue

                    # Skip current (incomplete) candle
                    now_ms = int(time.time() * 1000)
                    candle_end = ts_ms + 3600_000
                    if candle_end > now_ms:
                        break

                    candle = {
                        "timestamp": ts_ms,
                        "open": float(bar[1]),
                        "high": float(bar[2]),
                        "low": float(bar[3]),
                        "close": float(bar[4]),
                        "volume": float(bar[5]),
                    }

                    # Snapshot engine state BEFORE tick so we can roll back
                    # if a sell order fails on the exchange.
                    eng = self.engine._engine
                    _pre_tick_snapshot = None
                    if eng:
                        _pre_tick_snapshot = {
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

                    # Tick the V14 engine
                    try:
                        actions = self.engine.tick(candle, self.cash)
                    except Exception as e:
                        logger.error(f"Engine tick failed: {e}\n{traceback.format_exc()}")
                        continue

                    ts_dt = datetime.fromtimestamp(ts_ms / 1000, tz=timezone.utc)

                    # Execute resulting actions
                    if actions:
                        for act in actions:
                            self._execute_action(act, ts_dt, _pre_tick_snapshot)
                            logger.info(f"⚡ {act}")

                    self._last_candle_ts = ts_ms
                    self.engine._last_candle_ts = ts_ms

                # Phase change notification
                if self.engine.phase != prev_phase:
                    eng = self.engine._engine
                    reason = eng.phase_log[-1]['reason'] if eng and eng.phase_log else 'unknown'
                    send_telegram(
                        f"🔄 {TG_PREFIX} <b>Phase Change</b>\n"
                        f"{prev_phase} → {self.engine.phase}\n"
                        f"Reason: {reason}"
                    )

                # Periodic balance reconciliation
                self._maybe_reconcile()

                # Periodic CFGI poll
                try:
                    self._poll_cfgi()
                except Exception as e:
                    logger.warning(f"CFGI poll error: {e}")

                # Write status & trades
                try:
                    self._write_status()
                except Exception as e:
                    logger.error(f"Status write failed: {e}")
                try:
                    self.tracker.save_csv()
                except Exception as e:
                    logger.error(f"CSV save failed: {e}")
                try:
                    self._save_state()
                except Exception as e:
                    logger.error(f"State save failed: {e}")

                # Sleep until next cycle
                elapsed = time.time() - cycle_start
                sleep_time = max(1, LIVE_POLL_INTERVAL - elapsed)
                deadline = time.time() + sleep_time
                while time.time() < deadline and not self._shutdown:
                    time.sleep(1)

            except KeyboardInterrupt:
                break
            except Exception as e:
                logger.error(f"Live loop error: {e}\n{traceback.format_exc()}")
                send_telegram(f"⚠️ {TG_PREFIX} <b>Error:</b> {str(e)[:200]}")
                time.sleep(30)

        logger.info("Live trading loop stopped")
        send_telegram(f"🛑 {TG_PREFIX} Bot stopped")

    def _execute_action(self, action: dict, ts: datetime, pre_tick_snapshot: dict = None):
        """Execute a single engine action as a real order."""
        act_type = action.get("action", "")
        price = action.get("price", 0)
        qty = action.get("qty", 0)
        reason = action.get("reason", "N/A")

        if act_type == "BUY":
            result = self.executor.execute_buy(qty, price, reason)
            if result and result.get("status") in ("filled", "dry_run"):
                actual_cost = result.get("cost", qty * price)
                self.cash -= actual_cost
                # Update action with actual fill for tracker
                action["price"] = result.get("price", price)
                action["qty"] = result.get("qty", qty)
                action["cost"] = actual_cost
                self.tracker.process_actions(self.symbol, [action], ts)

        elif act_type == "SELL":
            result = self.executor.execute_sell(qty, price, reason)
            if result and result.get("status") in ("filled", "dry_run"):
                proceeds = result.get("proceeds", qty * price)
                self.cash += proceeds
                action["price"] = result.get("price", price)
                action["qty"] = result.get("qty", qty)
                pnl = action.get("pnl", 0)
                emoji = "🟢" if pnl >= 0 else "🔴"
                send_telegram(
                    f"{emoji} {TG_PREFIX} <b>Deal Closed</b>\n"
                    f"PnL: ${pnl:.2f} ({action.get('pnl_pct', 0):.1f}%)\n"
                    f"Reason: {reason}"
                )
                self.tracker.process_actions(self.symbol, [action], ts)
            else:
                # SELL FAILED — roll back engine state so it retries next tick
                eng = self.engine._engine
                if pre_tick_snapshot and eng:
                    old_trades_len = pre_tick_snapshot.pop("_trades_len", None)
                    logger.warning(
                        f"SELL FAILED — rolling back engine state "
                        f"(restoring {pre_tick_snapshot['long_coins']:.4f} coins, "
                        f"{pre_tick_snapshot['long_layers']} layers)"
                    )
                    for k, v in pre_tick_snapshot.items():
                        setattr(eng, k, v)
                    # Also trim the engine's internal trades list to remove
                    # the phantom sell entry that the tick added
                    if old_trades_len is not None and len(eng.trades) > old_trades_len:
                        removed = eng.trades[old_trades_len:]
                        eng.trades = eng.trades[:old_trades_len]
                        logger.warning(
                            f"Removed {len(removed)} phantom trade(s) from engine: "
                            f"{[t.get('action','?') for t in removed]}"
                        )
                    send_telegram(
                        f"⚠️ {TG_PREFIX} <b>SELL FAILED — engine state rolled back</b>\n"
                        f"Position restored: {pre_tick_snapshot['long_coins']:.4f} coins, "
                        f"{pre_tick_snapshot['long_layers']} layers\n"
                        f"Will retry on next candle"
                    )
                else:
                    logger.error(
                        "SELL FAILED but no pre-tick snapshot available! "
                        "Engine state may be inconsistent."
                    )
                    send_telegram(
                        f"🔴 {TG_PREFIX} <b>SELL FAILED — NO ROLLBACK AVAILABLE</b>\n"
                        f"Engine state may be inconsistent. Manual intervention needed."
                    )

        elif act_type == "SHORT_OPEN":
            # Spot-only mode — log but don't execute shorts
            logger.info(f"SHORT_OPEN signal received but spot-only mode — skipping")
            send_telegram(
                f"📝 {TG_PREFIX} Short signal (spot-only, not executed)\n"
                f"Price: ${price:.6f} | Reason: {reason}"
            )

        elif act_type == "SHORT_CLOSE":
            logger.info(f"SHORT_CLOSE signal received but no short position in spot mode")

        elif act_type == "PHASE_CHANGE":
            # Already handled in run_live
            pass

    def _reconcile_on_startup(self):
        """Reconcile engine cash with actual exchange balance on startup.

        Queries the exchange for real USDT + ASTER balances and corrects
        the engine's internal cash (eng.capital) and the bot's self.cash
        if drift exceeds $1. This fixes accumulated discrepancies from
        failed orders that weren't properly rolled back.
        """
        if self.executor is None:
            logger.warning("Cannot reconcile on startup — no executor")
            return

        try:
            bal = self.executor.get_balance()
            price = self.executor.get_current_price() or 0
            if price <= 0:
                logger.warning("Cannot reconcile — price unavailable")
                return

            exchange_usdt = bal["usdt_free"]
            exchange_base = bal["base_total"]

            eng = self.engine._engine
            if eng is None:
                return

            engine_cash = eng.capital
            engine_coins = eng.long_coins

            # --- Cash (USDT) reconciliation ---
            # When no position is open, engine cash should ≈ exchange USDT.
            # When a position IS open, we reconcile total portfolio value.
            exchange_total = exchange_usdt + (exchange_base * price)
            engine_total = engine_cash + (engine_coins * price)

            cash_drift = exchange_usdt - engine_cash
            total_drift = exchange_total - engine_total

            logger.info(
                f"STARTUP RECONCILIATION:\n"
                f"  Exchange: ${exchange_usdt:.2f} USDT + "
                f"{exchange_base:.4f} {self.executor.base_currency} "
                f"(~${exchange_total:.2f} total)\n"
                f"  Engine:   ${engine_cash:.2f} cash + "
                f"{engine_coins:.4f} coins (~${engine_total:.2f} total)\n"
                f"  Cash drift: ${cash_drift:+.2f} | Total drift: ${total_drift:+.2f}"
            )

            # Fix engine capital if total drift exceeds $1
            DRIFT_THRESHOLD = 1.0
            if abs(total_drift) > DRIFT_THRESHOLD:
                old_capital = eng.capital
                eng.capital += total_drift
                logger.warning(
                    f"RECONCILIATION ADJUSTMENT: eng.capital "
                    f"${old_capital:.2f} → ${eng.capital:.2f} "
                    f"(adjusted by ${total_drift:+.2f})"
                )
                send_telegram(
                    f"🔧 {TG_PREFIX} <b>Startup Cash Reconciliation</b>\n"
                    f"Engine capital: ${old_capital:.2f} → ${eng.capital:.2f}\n"
                    f"Adjustment: ${total_drift:+.2f}\n"
                    f"Exchange USDT: ${exchange_usdt:.2f}\n"
                    f"Exchange {self.executor.base_currency}: {exchange_base:.4f}"
                )
            else:
                logger.info(f"Reconciliation OK — drift ${total_drift:+.2f} within threshold")

            # Always sync self.cash to engine capital (self.cash is the
            # V14LiveBot's independent tracker; it should match eng.capital)
            if abs(self.cash - eng.capital) > 0.01:
                logger.info(
                    f"Syncing self.cash: ${self.cash:.2f} → ${eng.capital:.2f}"
                )
                self.cash = eng.capital

        except Exception as e:
            logger.error(f"Startup reconciliation failed: {e}\n{traceback.format_exc()}")
            send_telegram(
                f"⚠️ {TG_PREFIX} Startup reconciliation failed: {str(e)[:200]}"
            )

    def _poll_cfgi(self):
        """Poll CFGI API for market + per-coin sentiment (once per hour)."""
        now = time.time()
        if now - self._cfgi_last_poll < 3600:
            return
        try:
            from trading.spot.cfgi_client import CFGIClient
            import os as _os
            api_key = _os.environ.get("CFGI_API_KEY")
            if not api_key:
                return
            client = CFGIClient(api_key)

            base = self.symbol.split("/")[0]
            tokens = [base, "MARKET"]
            data = client.get_current(tokens, period=4, fields="cfgi")

            market_data = data.get("MARKET", {})
            if isinstance(market_data, dict):
                self._cfgi_market = market_data.get("cfgi", market_data.get("value"))
            elif isinstance(market_data, (int, float)):
                self._cfgi_market = float(market_data)

            coin_data = data.get(base, {})
            if isinstance(coin_data, dict):
                val = coin_data.get("cfgi", coin_data.get("value"))
                if val is not None:
                    self._cfgi_coins[self.symbol] = float(val)
            elif isinstance(coin_data, (int, float)):
                self._cfgi_coins[self.symbol] = float(coin_data)

            self._cfgi_last_poll = now
            logger.info("CFGI updated: market=%s, %s=%s",
                        self._cfgi_market, base,
                        self._cfgi_coins.get(self.symbol))
        except Exception as e:
            logger.warning("CFGI poll failed: %s", e)
            self._cfgi_last_poll = now

    def _maybe_reconcile(self):
        """Periodically reconcile engine state with exchange balances."""
        now = time.time()
        if now - self._last_recon_time < self._recon_interval:
            return
        self._last_recon_time = now

        if self.executor is None:
            return

        try:
            bal = self.executor.get_balance()
            price = self.executor.get_current_price() or 0

            exchange_usdt = bal["usdt_free"]
            exchange_base = bal["base_total"]
            exchange_value = exchange_usdt + (exchange_base * price)

            eng = self.engine._engine
            engine_coins = eng.long_coins if eng else 0
            engine_cash = eng.capital if eng else self.capital
            engine_value = engine_cash + (engine_coins * price)

            drift = exchange_value - engine_value
            drift_pct = abs(drift) / max(engine_value, 1) * 100

            if drift_pct > 10:  # More than 10% drift is suspicious
                logger.warning(
                    f"RECONCILIATION DRIFT: {drift_pct:.1f}% — "
                    f"Exchange: ${exchange_value:.2f} (${exchange_usdt:.2f} USDT + "
                    f"{exchange_base:.4f} {self.executor.base_currency} @ ${price:.6f}), "
                    f"Engine: ${engine_value:.2f} (${engine_cash:.2f} cash + "
                    f"{engine_coins:.4f} coins)"
                )
                send_telegram(
                    f"⚠️ {TG_PREFIX} <b>Balance drift: {drift_pct:.1f}%</b>\n"
                    f"Exchange: ${exchange_value:.2f}\n"
                    f"Engine: ${engine_value:.2f}"
                )
            else:
                logger.debug(f"Reconciliation OK — drift {drift_pct:.1f}%")

            # Sync self.cash to engine capital (prevent self.cash from drifting)
            if eng and abs(self.cash - eng.capital) > 0.01:
                logger.info(
                    f"Periodic sync self.cash: ${self.cash:.2f} → ${eng.capital:.2f}"
                )
                self.cash = eng.capital

        except Exception as e:
            logger.warning(f"Reconciliation failed: {e}")

    # -------------------------------------------------------------------
    # State & output
    # -------------------------------------------------------------------

    def _save_state(self):
        """Save full state for restart recovery."""
        state = {
            "saved_at": datetime.now(timezone.utc).isoformat(),
            "capital": self.capital,
            "cash": self.cash,
            "deal_counter": self.tracker._deal_counter,
            "open_deals": self.tracker._open_deals,
            "last_candle_ts": self._last_candle_ts,
            "engine": self.engine.snapshot_state(),
        }
        path = self.output_dir / "state.json"
        tmp = path.with_suffix(".tmp")
        with open(tmp, "w") as f:
            json.dump(state, f, indent=2, default=str)
        tmp.replace(path)

    def _load_state(self) -> bool:
        """Load state from state.json."""
        path = self.output_dir / "state.json"
        if not path.exists():
            return False
        try:
            with open(path) as f:
                state = json.load(f)

            self.cash = state.get("cash", self.capital)
            self.tracker._deal_counter = state.get("deal_counter", 0)
            self.tracker._open_deals = state.get("open_deals", {})
            self._last_candle_ts = state.get("last_candle_ts", 0)

            eng_state = state.get("engine", {})
            if eng_state:
                # Feed daily data for signal context
                daily_df = load_daily_candles(DB_SYMBOL)
                if not daily_df.empty:
                    self.engine.feed_daily(
                        daily_df[["open", "high", "low", "close", "volume"]]
                    )
                self.engine.restore_state(eng_state)

            logger.info(f"State restored from {state.get('saved_at', 'unknown')}")
            return True
        except Exception as e:
            logger.error(f"Failed to load state: {e}")
            return False

    def _write_status(self):
        """Write status.json for dashboard."""
        try:
            st = self.engine.get_status()
        except Exception as e:
            logger.error(f"get_status failed: {e}")
            return

        # Override with live-specific info
        st["mode"] = "dry_run" if self.dry_run else "live"
        st["engine"] = "v14"
        st["exchange"] = "aster"
        st["capital"] = self.capital
        st["profile"] = self.profile

        # Add exchange balance info
        if self.executor:
            try:
                bal = self.executor.get_balance()
                st["exchange_balance"] = {
                    "usdt_free": round(bal["usdt_free"], 2),
                    "usdt_total": round(bal["usdt_total"], 2),
                    "base_free": round(bal["base_free"], 4),
                    "base_total": round(bal["base_total"], 4),
                }
            except Exception:
                pass

        uptime_h = (datetime.now(timezone.utc) - self._start_time).total_seconds() / 3600
        st["uptime_hours"] = round(uptime_h, 2)
        st["last_update"] = datetime.now(timezone.utc).isoformat()
        st["fear_greed_index"] = self._cfgi_market

        # Inject per-coin CFGI
        if "coins" in st and self.symbol in self._cfgi_coins:
            if self.symbol in st["coins"]:
                st["coins"][self.symbol]["cfgi"] = round(self._cfgi_coins[self.symbol], 1)

        # Read trades.csv as source of truth for deal counts AND realized PnL
        # (engine counters drift on restart; CSV is the ledger)
        csv_path = self.output_dir / "trades.csv"
        if csv_path.exists():
            try:
                with open(csv_path, 'r') as f:
                    reader = csv.DictReader(f)
                    csv_trades = list(reader)
                if csv_trades:
                    csv_realized = sum(float(t.get('pnl', 0)) for t in csv_trades)
                    total_deals = len(csv_trades)
                    total_won = sum(1 for t in csv_trades if float(t.get('pnl', 0)) > 0)
                    win_rate = (total_won / total_deals * 100) if total_deals > 0 else 0.0
                    st["total_realized_pnl"] = round(csv_realized, 2)
                    st["deals_completed"] = total_deals
                    st["win_rate"] = round(win_rate, 1)
            except Exception as e:
                logger.warning("Failed to read trades.csv for status: %s", e)

        # For LIVE bot: equity = actual exchange balances (API truth)
        # Engine-computed equity drifts on restart; exchange balance is reality.
        if st.get("exchange_balance"):
            eb = st["exchange_balance"]
            price = st.get("coins", {}).get(self.symbol, {}).get("current_price", 0)
            if price > 0:
                exchange_equity = eb["usdt_total"] + eb["base_total"] * price
                st["equity"] = round(exchange_equity, 2)
                st["cash"] = round(eb["usdt_total"], 2)
                st["pnl_pct"] = round((exchange_equity - self.capital) / self.capital * 100, 2) if self.capital > 0 else 0.0

        path = self.output_dir / "status.json"
        tmp = path.with_suffix(".tmp")
        with open(tmp, "w") as f:
            json.dump(st, f, indent=2, default=str)
        tmp.replace(path)

    # -------------------------------------------------------------------
    # Main run
    # -------------------------------------------------------------------

    def run(self, skip_backfill: bool = False, fresh: bool = False):
        """Full pipeline: connect → backfill → live."""

        def _shutdown_handler(signum, frame):
            logger.info(f"Received signal {signum}, shutting down...")
            self._shutdown = True

        signal.signal(signal.SIGINT, _shutdown_handler)
        signal.signal(signal.SIGTERM, _shutdown_handler)

        # Connect to exchange
        if not self.connect_exchange():
            logger.error("Failed to connect to Aster — aborting")
            sys.exit(1)

        if fresh:
            # Fresh start: no backfill, clean state, start LONG_DCA immediately
            logger.info("Fresh start — no backfill, entering live immediately")
            self.engine._live_mode = True
            # Load existing trades from CSV so save_csv() doesn't overwrite history
            self.tracker.load_existing()
            send_telegram(
                f"🆕 {TG_PREFIX} Fresh start — ${self.capital:.0f}, "
                f"profile={self.profile}, entering live"
            )
        elif skip_backfill:
            # Resume from saved state
            if not self._load_state():
                logger.error("--skip-backfill requires existing state.json")
                sys.exit(1)
            self.tracker.load_existing()
            self.engine._live_mode = True
        else:
            # Backfill signal context, then go live
            self.backfill()
            self.engine._live_mode = True

        # Reconcile engine cash with actual exchange balance on startup.
        # This fixes accumulated drift from failed orders, rounding, or
        # any other discrepancy between engine state and reality.
        self._reconcile_on_startup()

        # Save initial state
        try:
            self._write_status()
            self._save_state()
        except Exception as e:
            logger.error(f"Initial state save failed: {e}")

        # Enter live loop
        self.run_live()

        # Final save
        try:
            self._write_status()
            self.tracker.save_csv()
            self._save_state()
        except Exception as e:
            logger.error(f"Final save failed: {e}")

        logger.info("V14 Live Bot shut down cleanly")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="V14 Live Trading Bot — Aster Exchange"
    )
    parser.add_argument("--capital", type=float, default=DEFAULT_CAPITAL,
                        help=f"Trading capital in USDT (default: {DEFAULT_CAPITAL})")
    parser.add_argument("--profile", type=str, default=DEFAULT_PROFILE,
                        choices=["low", "medium", "high"],
                        help=f"Risk profile (default: {DEFAULT_PROFILE})")
    parser.add_argument("--skip-backfill", action="store_true",
                        help="Skip backfill, resume from state.json")
    parser.add_argument("--fresh", action="store_true",
                        help="Fresh start — no backfill, clean state, live immediately")
    parser.add_argument("--dry-run", action="store_true",
                        help="Log all orders but don't execute (paper mode on live exchange)")
    parser.add_argument("--test", action="store_true",
                        help="Test connectivity and exit")
    parser.add_argument("--confirm", action="store_true",
                        help="Required to actually trade with real money")

    args = parser.parse_args()

    bot = V14LiveBot(
        capital=args.capital,
        profile=args.profile,
        dry_run=args.dry_run,
    )

    # Force UTF-8 stdout on Windows
    if sys.platform == "win32":
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

    if args.test:
        print("🧪 Testing Aster connectivity...")
        success = bot.test_connectivity()
        sys.exit(0 if success else 1)

    if not args.dry_run and not args.confirm:
        print("⚠️  V14 LIVE TRADING — REAL MONEY")
        print(f"   Symbol:  {SYMBOL}")
        print(f"   Capital: ${args.capital:.0f}")
        print(f"   Profile: {args.profile}")
        print(f"   Exchange: Aster (spot)")
        print()
        print("Run with --confirm to trade live, or --dry-run to test.")
        sys.exit(1)

    bot.run(
        skip_backfill=args.skip_backfill,
        fresh=args.fresh,
    )


if __name__ == "__main__":
    main()
