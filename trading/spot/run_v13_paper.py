#!/usr/bin/env python3
"""
V13 Paper Trading Bot Runner
=============================
Entry point for V13 lifecycle paper trading across 4 coins on Hyperliquid.

Backfills from DB candles (Sept 2024 -> present), then transitions to live
candle feeds via CCXT. Writes dashboard-compatible status.json and trades.csv.

Usage:
    python -m trading.spot.run_v13_paper [options]
    python trading/spot/run_v13_paper.py [options]
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
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

# Ensure workspace root is on path
_WORKSPACE = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_WORKSPACE))

from trading.spot.v13_lifecycle_engine_v2 import V13LifecycleEngineV2 as V13LifecycleEngine, V13Config

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

CANONICAL_SYMBOLS = ["ETH/USDC", "SOL/USDC", "LINK/USDC", "XRP/USDC"]

# Canonical -> DB symbol (USDT pairs in the database)
DB_SYMBOL_MAP = {
    "ETH/USDC": "ETH/USDT",
    "SOL/USDC": "SOL/USDT",
    "LINK/USDC": "LINK/USDT",
    "XRP/USDC": "XRP/USDT",
}

# Canonical -> Hyperliquid spot ticker
HL_SPOT_MAP = {
    "ETH/USDC": "ETH/USDC",
    "SOL/USDC": "SOL/USDC",
    "LINK/USDC": "LINK0/USDC",
    "XRP/USDC": "FXRP/USDC",
}

# Canonical -> Hyperliquid perp ticker (for markdown shorts)
HL_PERP_MAP = {
    "ETH/USDC": "ETH/USDC:USDC",
    "SOL/USDC": "SOL/USDC:USDC",
    "LINK/USDC": "LINK/USDC:USDC",
    "XRP/USDC": "XRP/USDC:USDC",
}

DB_PATH = _WORKSPACE / "trading" / "spot" / "data" / "candles.db"
DEFAULT_OUTPUT_DIR = _WORKSPACE / "trading" / "spot" / "paper" / "v13"
DEFAULT_START_DATE = "2024-10-01"  # Match v8 backtest START_DATE
DEFAULT_CAPITAL = 10000.0
LIVE_POLL_INTERVAL = 60  # seconds

logger = logging.getLogger("v13_paper")


# ---------------------------------------------------------------------------
# Telegram
# ---------------------------------------------------------------------------

def send_telegram(msg: str):
    """Send a Telegram notification if credentials are configured."""
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
# Database helpers
# ---------------------------------------------------------------------------

def load_hourly_candles(symbol_usdt: str, start_ts: float = 0) -> pd.DataFrame:
    """Load 1h candles from candles.db for a USDT symbol."""
    conn = sqlite3.connect(str(DB_PATH))
    query = """
        SELECT timestamp, open, high, low, close, volume
        FROM candles
        WHERE symbol = ? AND timeframe = '1h' AND timestamp >= ?
        ORDER BY timestamp ASC
    """
    df = pd.read_sql_query(query, conn, params=(symbol_usdt, start_ts))
    conn.close()
    if not df.empty:
        df["timestamp_ms"] = df["timestamp"]
        df["dt"] = pd.to_datetime(df["timestamp"], unit="ms", utc=True)
        df.set_index("dt", inplace=True)
    return df


def load_daily_candles(symbol_usdt: str) -> pd.DataFrame:
    """Load daily candles from candles_daily table."""
    conn = sqlite3.connect(str(DB_PATH))
    query = """
        SELECT timestamp, open, high, low, close, volume
        FROM candles_daily
        WHERE symbol = ?
        ORDER BY timestamp ASC
    """
    df = pd.read_sql_query(query, conn, params=(symbol_usdt,))
    conn.close()
    if not df.empty:
        df["dt"] = pd.to_datetime(df["timestamp"], unit="ms", utc=True)
        df.set_index("dt", inplace=True)
    return df


# ---------------------------------------------------------------------------
# Trade tracking
# ---------------------------------------------------------------------------

class TradeTracker:
    """Tracks trades from engine actions and writes trades.csv."""

    def __init__(self, output_dir: Path):
        self.output_dir = output_dir
        self.trades: List[dict] = []
        self._deal_counter = 0
        # Open deals keyed by (symbol, deal_type)
        self._open_deals: Dict[str, dict] = {}

    def process_actions(self, symbol: str, actions: List[dict], timestamp: datetime):
        """Process engine actions and track trades."""
        for act in actions:
            action = act.get("action", "")
            reason = act.get("reason", "")
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
                        "regime": act.get("phase", "DCA"),
                        "layers": 0,
                        "invested": 0.0,
                    }
                deal = self._open_deals[key]
                deal["layers"] += 1
                deal["invested"] += cost

            elif action == "SELL":
                key = f"{symbol}:long"
                deal = self._open_deals.pop(key, None)
                if deal:
                    pnl = act.get("pnl", 0.0)
                    invested = deal["invested"]
                    ret_pct = (pnl / invested * 100) if invested > 0 else 0.0
                    open_dt = datetime.fromisoformat(deal["open_time"])
                    duration_h = (timestamp - open_dt).total_seconds() / 3600
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

            elif action == "SHORT_OPEN":
                key = f"{symbol}:short"
                if key not in self._open_deals:
                    self._deal_counter += 1
                    self._open_deals[key] = {
                        "deal_id": self._deal_counter,
                        "symbol": symbol,
                        "open_time": timestamp.isoformat(),
                        "regime": "MARKDOWN",
                        "layers": 0,
                        "invested": 0.0,
                    }
                deal = self._open_deals[key]
                deal["layers"] += 1
                deal["invested"] += cost

            elif action == "SHORT_CLOSE":
                key = f"{symbol}:short"
                deal = self._open_deals.pop(key, None)
                if deal:
                    pnl = act.get("pnl", 0.0)
                    invested = deal["invested"]
                    ret_pct = (pnl / invested * 100) if invested > 0 else 0.0
                    open_dt = datetime.fromisoformat(deal["open_time"])
                    duration_h = (timestamp - open_dt).total_seconds() / 3600
                    self.trades.append({
                        "deal_id": deal["deal_id"],
                        "symbol": symbol,
                        "open_time": deal["open_time"],
                        "close_time": timestamp.isoformat(),
                        "regime": "MARKDOWN",
                        "layers": deal["layers"],
                        "invested": round(invested, 2),
                        "pnl": round(pnl, 4),
                        "return_pct": round(ret_pct, 2),
                        "duration_h": round(duration_h, 1),
                    })

    def save_csv(self):
        """Write trades.csv."""
        path = self.output_dir / "trades.csv"
        with open(path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=[
                "deal_id", "symbol", "open_time", "close_time", "regime",
                "layers", "invested", "pnl", "return_pct", "duration_h",
            ])
            writer.writeheader()
            writer.writerows(self.trades)

    def load_existing(self):
        """Load existing trades.csv if present (for skip-backfill restarts)."""
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
                    if row["deal_id"] > self._deal_counter:
                        self._deal_counter = row["deal_id"]
            logger.info(f"Loaded {len(self.trades)} existing trades from CSV")
        except Exception as e:
            logger.warning(f"Failed to load existing trades: {e}")


# ---------------------------------------------------------------------------
# V13PaperBot
# ---------------------------------------------------------------------------

class V13PaperBot:
    def __init__(
        self,
        symbols: List[str],
        capital: float,
        exchange: str,
        profile: str,
        timeframe: str = "1h",
        output_dir: Optional[Path] = None,
        start_date: str = DEFAULT_START_DATE,
    ):
        self.symbols = symbols
        self.capital = capital
        self.exchange = exchange
        self.profile = profile
        self.timeframe = timeframe
        self.output_dir = Path(output_dir or DEFAULT_OUTPUT_DIR)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.start_date = start_date

        # Per-coin capital
        per_coin = capital / len(symbols)

        # Create engines (using profile from backtest)
        self.engines: Dict[str, V13LifecycleEngine] = {}
        for sym in symbols:
            cfg = V13Config.from_profile(profile, capital=per_coin)
            self.engines[sym] = V13LifecycleEngine(
                symbol=sym, capital=per_coin, config=cfg
            )

        # Cash tracking: total cash not in positions
        self.cash = capital
        self.per_coin_cash: Dict[str, float] = {s: per_coin for s in symbols}

        # Trade tracker
        self.tracker = TradeTracker(self.output_dir)

        # Shutdown flag
        self._shutdown = False
        self._start_time = datetime.now(timezone.utc)

        # Setup logging
        self._setup_logging()

    def _setup_logging(self):
        log_path = self.output_dir / "bot.log"
        handler = logging.FileHandler(str(log_path))
        handler.setFormatter(logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
        ))
        root = logging.getLogger()
        root.addHandler(handler)
        root.setLevel(logging.INFO)

        # Also log to stdout
        stdout_handler = logging.StreamHandler(sys.stdout)
        stdout_handler.setFormatter(logging.Formatter(
            "%(asctime)s [%(levelname)s] %(message)s"
        ))
        root.addHandler(stdout_handler)

    # -------------------------------------------------------------------
    # Backfill
    # -------------------------------------------------------------------

    def backfill(self):
        """Run historical backfill from DB candles."""
        logger.info(f"Starting backfill from {self.start_date}")
        send_telegram(f"?? <b>V13 Paper Bot</b> starting backfill from {self.start_date}")

        start_dt = datetime.strptime(self.start_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        start_ts_ms = int(start_dt.timestamp() * 1000)

        # Use today's date as end date for backfill
        end_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")

        for sym in self.symbols:
            db_sym = DB_SYMBOL_MAP[sym]
            engine = self.engines[sym]

            # Run v8 engine directly (guarantees identical results to standalone backtest)
            actions = engine.backfill_direct(self.start_date, end_date)

            # Process all actions for cash tracking and trade logging
            if actions:
                for act in actions:
                    # Use historical date from v8 engine trade, fall back to now
                    trade_date = act.get('date')
                    if trade_date is not None:
                        import pandas as _pd
                        if isinstance(trade_date, _pd.Timestamp):
                            ts = trade_date.to_pydatetime().replace(tzinfo=timezone.utc)
                        elif isinstance(trade_date, datetime):
                            ts = trade_date.replace(tzinfo=timezone.utc) if trade_date.tzinfo is None else trade_date
                        else:
                            ts = datetime.now(timezone.utc)
                    else:
                        ts = datetime.now(timezone.utc)
                    self._process_actions(sym, [act], ts)
                    self.tracker.process_actions(sym, [act], ts)

            logger.info(
                f"{sym}: Backfill done — phase={engine.phase}, "
                f"deals={engine.deals_completed}, "
                f"realized_pnl=${engine.realized_pnl:.2f}, "
                f"dd={engine.max_drawdown_pct:.1f}%"
            )

        # Save state and trades
        self._save_state()
        self.tracker.save_csv()
        self._write_status()

        total_pnl = sum(e.realized_pnl for e in self.engines.values())
        total_deals = sum(e.deals_completed for e in self.engines.values())
        logger.info(f"Backfill complete — total realized PnL: ${total_pnl:.2f}, "
                    f"deals: {total_deals}, trades logged: {len(self.tracker.trades)}")
        send_telegram(
            f"? <b>V13 Backfill Complete</b>\n"
            f"PnL: ${total_pnl:.2f} | Deals: {total_deals} | "
            f"Trades: {len(self.tracker.trades)}"
        )

    def _process_actions(self, symbol: str, actions: List[dict], ts: datetime):
        """Update cash tracking based on engine actions."""
        for act in actions:
            action = act.get("action", "")
            price = act.get("price", 0)
            qty = act.get("qty", 0)
            cost = price * qty if price and qty else 0
            pnl = act.get("pnl", 0.0)

            if action in ("BUY", "SHORT_OPEN"):
                actual_cost = act.get("cost", cost)
                self.per_coin_cash[symbol] -= actual_cost
                self.cash -= actual_cost
            elif action == "SELL":
                # For sells: proceeds = qty * price
                proceeds = qty * price if qty and price else 0
                self.per_coin_cash[symbol] += proceeds
                self.cash += proceeds
            elif action == "SHORT_CLOSE":
                # For short closes: return initial margin + pnl
                # We track what was originally allocated in _open_deals
                key = f"{symbol}:short"
                orig_invested = 0
                if key in self.tracker._open_deals:
                    orig_invested = self.tracker._open_deals[key].get("invested", 0)
                returns = orig_invested + pnl
                self.per_coin_cash[symbol] += returns
                self.cash += returns

                # Notify on trade completion
                emoji = "??" if pnl >= 0 else "??"
                send_telegram(
                    f"{emoji} <b>{symbol}</b> {action} @ ${price:.2f}\n"
                    f"PnL: ${pnl:.2f} | Reason: {act.get('reason', 'N/A')}"
                )

    # -------------------------------------------------------------------
    # Live trading
    # -------------------------------------------------------------------

    def run_live(self):
        """Main live loop — fetch 1h candles from Hyperliquid, tick engines."""
        import ccxt

        logger.info("Starting live trading loop")
        send_telegram("?? <b>V13 Paper Bot</b> entering live trading mode")

        exchange = ccxt.hyperliquid()
        exchange.load_markets()

        # Track last processed candle timestamp per symbol
        last_candle_ts: Dict[str, int] = {s: 0 for s in self.symbols}

        # CFGI polling state
        self._cfgi_market = None  # Market-wide FGI (MARKET token)
        self._cfgi_coins: Dict[str, float] = {}  # Per-coin CFGI
        self._cfgi_last_poll = 0.0  # Epoch of last CFGI fetch
        CFGI_POLL_INTERVAL = 3600  # Poll every hour (daily data doesn't change faster)

        while not self._shutdown:
            try:
                cycle_start = time.time()

                for sym in self.symbols:
                    hl_sym = HL_SPOT_MAP[sym]

                    try:
                        ohlcv = exchange.fetch_ohlcv(hl_sym, self.timeframe, limit=200)
                    except Exception as e:
                        logger.error(f"Failed to fetch candles for {sym} ({hl_sym}): {e}")
                        continue

                    if not ohlcv:
                        continue

                    engine = self.engines[sym]
                    prev_phase = engine.phase

                    # Process only new completed candles (skip the last one if still open)
                    # OHLCV: [timestamp, open, high, low, close, volume]
                    for bar in ohlcv:
                        ts_ms = int(bar[0])
                        if ts_ms <= last_candle_ts[sym]:
                            continue

                        # Skip current (incomplete) candle
                        now_ms = int(time.time() * 1000)
                        candle_end = ts_ms + 3600_000  # 1h
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

                        cash_avail = self.per_coin_cash[sym]
                        actions = engine.tick(candle, cash_avail)
                        ts_dt = datetime.fromtimestamp(ts_ms / 1000, tz=timezone.utc)

                        if actions:
                            self._process_actions(sym, actions, ts_dt)
                            self.tracker.process_actions(sym, actions, ts_dt)
                            for act in actions:
                                logger.info(f"? {sym}: {act}")

                        last_candle_ts[sym] = ts_ms

                    # Log phase transitions
                    if engine.phase != prev_phase:
                        msg = (f"[PHASE] {sym}: Phase {prev_phase} -> {engine.phase} "
                               f"(price=${engine.current_price:.2f})")
                        logger.info(msg)
                        send_telegram(f"[PHASE] <b>{sym}</b> Phase: {prev_phase} -> {engine.phase}")

                # Poll CFGI (once per hour)
                try:
                    logger.info("[DBG] Starting CFGI poll")
                    self._poll_cfgi()
                    logger.info("[DBG] CFGI poll complete")
                except Exception as e:
                    logger.error(f"CFGI polling failed: {e}", exc_info=True)

                # Write outputs
                try:
                    logger.info("[DBG] Writing status")
                    self._write_status()
                    logger.info("[DBG] Status write complete")
                except Exception as e:
                    logger.error(f"Status write failed: {e}", exc_info=True)
                try:
                    logger.info("[DBG] Saving CSV")
                    self.tracker.save_csv()
                    logger.debug("CSV save complete")
                except Exception as e:
                    logger.error(f"CSV save failed: {e}", exc_info=True)
                try:
                    logger.info("[DBG] Saving state")
                    self._save_state()
                    logger.info("[DBG] State save complete")
                except Exception as e:
                    logger.error(f"State save failed: {e}", exc_info=True)
                
                logger.info("[DBG] Cycle outputs complete")

                # Sleep until next cycle
                elapsed = time.time() - cycle_start
                sleep_time = max(1, LIVE_POLL_INTERVAL - elapsed)
                logger.info(f"[DBG] Cycle took {elapsed:.1f}s, sleeping {sleep_time:.0f}s")

                # Interruptible sleep
                deadline = time.time() + sleep_time
                while time.time() < deadline and not self._shutdown:
                    time.sleep(1)

            except KeyboardInterrupt:
                break
            except Exception as e:
                logger.error(f"Live loop error: {e}\n{traceback.format_exc()}")
                try:
                    send_telegram(f"?? <b>V13 Bot Error:</b> {str(e)[:200]}")
                except Exception as te:
                    logger.error(f"Telegram notification failed: {te}")
                time.sleep(30)

        logger.info("Live trading loop stopped")
        send_telegram("?? <b>V13 Paper Bot</b> stopped")

    # -------------------------------------------------------------------
    # State & output
    # -------------------------------------------------------------------

    def _save_state(self):
        """Save engine states to state.json."""
        state = {
            "saved_at": datetime.now(timezone.utc).isoformat(),
            "capital": self.capital,
            "cash": self.cash,
            "per_coin_cash": self.per_coin_cash,
            "deal_counter": self.tracker._deal_counter,
            "open_deals": self.tracker._open_deals,
            "engines": {},
        }
        for sym, engine in self.engines.items():
            state["engines"][sym] = engine.snapshot_state()

        path = self.output_dir / "state.json"
        tmp = path.with_suffix(".tmp")
        with open(tmp, "w") as f:
            json.dump(state, f, indent=2, default=str)
        tmp.replace(path)

    def _load_state(self) -> bool:
        """Load engine states from state.json. Returns True if successful."""
        path = self.output_dir / "state.json"
        if not path.exists():
            return False
        try:
            with open(path) as f:
                state = json.load(f)

            self.cash = state.get("cash", self.capital)
            self.per_coin_cash = state.get("per_coin_cash", self.per_coin_cash)
            self.tracker._deal_counter = state.get("deal_counter", 0)
            self.tracker._open_deals = state.get("open_deals", {})

            for sym, eng_state in state.get("engines", {}).items():
                if sym in self.engines:
                    # Need to feed daily data first for signal context
                    db_sym = DB_SYMBOL_MAP[sym]
                    daily_df = load_daily_candles(db_sym)
                    if not daily_df.empty:
                        self.engines[sym].feed_daily(
                            daily_df[["open", "high", "low", "close", "volume"]]
                        )
                    self.engines[sym].restore_state(eng_state)

            logger.info(f"State restored from {state.get('saved_at', 'unknown')}")
            return True
        except Exception as e:
            logger.error(f"Failed to load state: {e}")
            return False

    def _poll_cfgi(self):
        """Poll CFGI API for market + per-coin sentiment (once per hour)."""
        now = time.time()
        if now - self._cfgi_last_poll < getattr(self, '_cfgi_poll_interval', 3600):
            return

        try:
            from trading.spot.cfgi_client import CFGIClient
            api_key = os.environ.get("CFGI_API_KEY")
            if not api_key:
                return

            client = CFGIClient(api_key)

            # Map our symbols to CFGI tokens
            token_map = {}
            for sym in self.symbols:
                base = sym.split("/")[0]
                token_map[sym] = base

            tokens = list(set(token_map.values())) + ["MARKET"]
            data = client.get_current(tokens, period=4, fields="cfgi")

            # Market-wide FGI
            market_data = data.get("MARKET", {})
            if isinstance(market_data, dict):
                self._cfgi_market = market_data.get("cfgi", market_data.get("value"))
            elif isinstance(market_data, (int, float)):
                self._cfgi_market = float(market_data)

            # Per-coin CFGI
            for sym, token in token_map.items():
                coin_data = data.get(token, {})
                if isinstance(coin_data, dict):
                    val = coin_data.get("cfgi", coin_data.get("value"))
                    if val is not None:
                        self._cfgi_coins[sym] = float(val)
                elif isinstance(coin_data, (int, float)):
                    self._cfgi_coins[sym] = float(coin_data)

            self._cfgi_last_poll = now
            logger.info("CFGI updated: market=%s, coins=%s",
                        self._cfgi_market,
                        {s.split('/')[0]: v for s, v in self._cfgi_coins.items()})

        except Exception as e:
            logger.warning("CFGI poll failed: %s", e)
            self._cfgi_last_poll = now  # Don't retry immediately on failure

    def _write_status(self):
        """Write combined status.json from all engines."""
        # Merge individual engine statuses
        coins = {}
        lifecycle = {}
        total_equity = 0.0
        total_cash = 0.0
        total_realized = 0.0
        total_deals = 0
        total_won = 0
        max_dd = 0.0

        for sym, engine in self.engines.items():
            st = engine.get_status()
            if "coins" in st:
                coins.update(st["coins"])
                # Inject per-coin CFGI
                if hasattr(self, '_cfgi_coins'):
                    for coin_sym in st["coins"]:
                        if coin_sym in self._cfgi_coins and coin_sym in coins:
                            coins[coin_sym]["cfgi"] = round(self._cfgi_coins[coin_sym], 1)
            if "lifecycle" in st:
                lifecycle.update(st["lifecycle"])
            total_equity += st.get("equity", 0)
            total_cash += st.get("cash", 0)
            total_realized += st.get("total_realized_pnl", 0)
            total_deals += st.get("deals_completed", 0)
            total_won += engine.deals_won
            max_dd = max(max_dd, st.get("max_drawdown_pct", 0))

        # Compute realized PnL correctly:
        #   realized = (capital + invested) - starting_capital
        # trades.csv PnL column is incomplete (misses capital growth from tier sizing)
        per_coin_capital = self.capital / len(self.engines) if self.engines else 0
        total_realized = 0.0
        for sym, engine in self.engines.items():
            st = engine.get_status()
            coin_cash = engine._engine.capital if engine._engine else 0
            coin_invested = st.get("coins", {}).get(sym, {}).get("invested", 0)
            coin_unrealized = st.get("coins", {}).get(sym, {}).get("unrealized_pnl", 0)
            coin_realized = (coin_cash + coin_invested) - per_coin_capital
            total_realized += coin_realized
            if sym in coins:
                coins[sym]['realized_pnl'] = round(coin_realized, 2)

        # Read trades.csv for deal counts and win/loss
        csv_path = self.output_dir / "trades.csv"
        if csv_path.exists():
            try:
                import csv
                with open(csv_path, 'r') as f:
                    reader = csv.DictReader(f)
                    csv_trades = list(reader)
                if csv_trades:
                    total_deals = len(csv_trades)
                    total_won = sum(1 for t in csv_trades if float(t.get('pnl', 0)) > 0)
            except Exception as e:
                logger.warning("Failed to read trades.csv for deal counts: %s", e)

        pnl_pct = ((total_equity - self.capital) / self.capital * 100
                    if self.capital > 0 else 0.0)
        win_rate = (total_won / total_deals * 100) if total_deals > 0 else 0.0
        uptime_h = (datetime.now(timezone.utc) - self._start_time).total_seconds() / 3600

        # Use first engine's regime/trend as representative
        first = next(iter(self.engines.values()))
        first_st = first.get_status()

        status = {
            "running": True,
            "mode": "paper",
            "profile": self.profile,
            "exchange": self.exchange,
            "capital": self.capital,
            "equity": round(total_equity, 2),
            "cash": round(total_cash, 2),
            "pnl_pct": round(pnl_pct, 2),
            "coins": coins,
            "lifecycle": lifecycle,
            "symbols": self.symbols,
            "regime": first_st.get("regime", "UNKNOWN"),
            "trend_direction": first_st.get("trend_direction", "unknown"),
            "total_realized_pnl": round(total_realized, 2),
            "deals_completed": total_deals,
            "win_rate": round(win_rate, 1),
            "max_drawdown_pct": round(max_dd, 2),
            "uptime_hours": round(uptime_h, 2),
            "fear_greed_index": self._cfgi_market if hasattr(self, '_cfgi_market') else None,
            "last_update": datetime.now(timezone.utc).isoformat(),
            "timeframe": self.timeframe,
        }

        path = self.output_dir / "status.json"
        tmp = path.with_suffix(".tmp")
        with open(tmp, "w") as f:
            json.dump(status, f, indent=2, default=str)
        tmp.replace(path)

    # -------------------------------------------------------------------
    # Main run
    # -------------------------------------------------------------------

    def run(self, backfill_only=False, skip_backfill=False):
        """Full pipeline: backfill then live."""
        # Register signal handlers
        def _shutdown_handler(signum, frame):
            logger.info(f"Received signal {signum}, shutting down...")
            self._shutdown = True

        signal.signal(signal.SIGINT, _shutdown_handler)
        signal.signal(signal.SIGTERM, _shutdown_handler)

        if skip_backfill:
            if not self._load_state():
                logger.error("--skip-backfill requires existing state.json")
                sys.exit(1)
            self.tracker.load_existing()
            # Enable live signal pack refresh immediately when skipping backfill
            for engine in self.engines.values():
                engine._live_mode = True
        else:
            self.backfill()

        if backfill_only:
            logger.info("Backfill-only mode, exiting")
            return

        # Enable live signal pack refresh for all engines
        for engine in self.engines.values():
            engine._live_mode = True

        self.run_live()

        # Final save
        self._write_status()
        self.tracker.save_csv()
        self._save_state()
        logger.info("V13 Paper Bot shut down cleanly")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="V13 Paper Trading Bot")
    parser.add_argument("--capital", type=float, default=DEFAULT_CAPITAL,
                        help=f"Starting capital (default: {DEFAULT_CAPITAL})")
    parser.add_argument("--profile", type=str, default="medium",
                        choices=["low", "medium", "high"],
                        help="Risk profile (default: medium)")
    parser.add_argument("--exchange", type=str, default="hyperliquid",
                        help="Exchange name (default: hyperliquid)")
    parser.add_argument("--backfill-only", action="store_true",
                        help="Run backfill and exit (no live trading)")
    parser.add_argument("--skip-backfill", action="store_true",
                        help="Skip backfill, start live (requires state.json)")
    parser.add_argument("--start-date", type=str, default=DEFAULT_START_DATE,
                        help=f"Backfill start date (default: {DEFAULT_START_DATE})")
    args = parser.parse_args()

    bot = V13PaperBot(
        symbols=CANONICAL_SYMBOLS,
        capital=args.capital,
        exchange=args.exchange,
        profile=args.profile,
        start_date=args.start_date,
    )
    bot.run(
        backfill_only=args.backfill_only,
        skip_backfill=args.skip_backfill,
    )


if __name__ == "__main__":
    main()


