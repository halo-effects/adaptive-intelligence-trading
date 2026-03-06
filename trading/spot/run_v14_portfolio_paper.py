#!/usr/bin/env python3
"""
V14 Portfolio Paper Trading Bot Runner
=======================================
Paper trading runner using CapitalRouter for portfolio-level funding.
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

from trading.spot.v14_lifecycle_engine import V14LifecycleEngine, V14_PROFILES
from trading.spot.v14_capital_manager import CapitalRouter
from trading.spot.incident_schema import create_incident_report

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DB_PATH = _WORKSPACE / "trading" / "spot" / "data" / "candles.db"
DEFAULT_OUTPUT_DIR = _WORKSPACE / "trading" / "spot" / "paper" / "v14_portfolio"
DEFAULT_START_DATE = "2024-10-01"
DEFAULT_CAPITAL = 10000.0
LIVE_POLL_INTERVAL = 60  # seconds
SCANNER_PATH = _WORKSPACE / "docs" / "data" / "v14" / "cycle_scanner.json"

logger = logging.getLogger("v14_portfolio_paper")

# ---------------------------------------------------------------------------
# Telegram
# ---------------------------------------------------------------------------

def send_telegram(msg: str):
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

def load_daily_candles(symbol_usdt: str) -> pd.DataFrame:
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
    def __init__(self, output_dir: Path, leverage: float = 1.0):
        self.output_dir = output_dir
        self.leverage = leverage
        self.trades: List[dict] = []
        self._deal_counter = 0
        self._open_deals: Dict[str, dict] = {}
        self._existing_keys: set = set()
        self.on_losing_trade = None

    def process_actions(self, symbol: str, actions: List[dict], timestamp: datetime):
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
                        "regime": act.get("phase", "LONG_DCA"),
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
                    pnl = act.get("pnl", 0.0) * self.leverage
                    invested = deal["invested"]
                    ret_pct = (pnl / invested * 100) if invested > 0 else 0.0
                    open_dt = datetime.fromisoformat(deal["open_time"])
                    duration_h = (timestamp - open_dt).total_seconds() / 3600
                    trade_key = f"{symbol}|{deal['open_time']}|{timestamp.isoformat()}"
                    if trade_key not in self._existing_keys:
                        self._existing_keys.add(trade_key)
                        trade_record = {
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
                        }
                        self.trades.append(trade_record)
                        if pnl < 0 and self.on_losing_trade:
                            try:
                                self.on_losing_trade(trade_record, symbol)
                            except Exception:
                                pass

            elif action == "SHORT_OPEN":
                key = f"{symbol}:short"
                if key not in self._open_deals:
                    self._deal_counter += 1
                    self._open_deals[key] = {
                        "deal_id": self._deal_counter,
                        "symbol": symbol,
                        "open_time": timestamp.isoformat(),
                        "regime": "SHORT_DCA",
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
                    pnl = act.get("pnl", 0.0) * self.leverage
                    invested = deal["invested"]
                    ret_pct = (pnl / invested * 100) if invested > 0 else 0.0
                    open_dt = datetime.fromisoformat(deal["open_time"])
                    duration_h = (timestamp - open_dt).total_seconds() / 3600
                    trade_key = f"{symbol}|{deal['open_time']}|{timestamp.isoformat()}"
                    if trade_key not in self._existing_keys:
                        self._existing_keys.add(trade_key)
                        trade_record = {
                            "deal_id": deal["deal_id"],
                            "symbol": symbol,
                            "open_time": deal["open_time"],
                            "close_time": timestamp.isoformat(),
                            "regime": "SHORT_DCA",
                            "layers": deal["layers"],
                            "invested": round(invested, 2),
                            "pnl": round(pnl, 4),
                            "return_pct": round(ret_pct, 2),
                            "duration_h": round(duration_h, 1),
                        }
                        self.trades.append(trade_record)
                        if pnl < 0 and self.on_losing_trade:
                            try:
                                self.on_losing_trade(trade_record, symbol)
                            except Exception:
                                pass

    def save_csv(self):
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
# V14PortfolioPaperBot
# ---------------------------------------------------------------------------

class V14PortfolioPaperBot:
    def __init__(
        self,
        capital: float,
        exchange: str,
        profile: str,
        timeframe: str = "1h",
        output_dir: Optional[Path] = None,
        start_date: str = DEFAULT_START_DATE,
        leverage: float = None,
    ):
        self.capital = capital
        self.exchange = exchange
        self.profile = profile
        self.timeframe = timeframe
        self.output_dir = Path(output_dir or DEFAULT_OUTPUT_DIR)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.start_date = start_date
        self.leverage = leverage if leverage is not None else V14_PROFILES.get(profile, V14_PROFILES['medium'])['leverage']

        self.router = CapitalRouter(initial_capital=self.capital)
        self.engines: Dict[str, V14LifecycleEngine] = {}
        
        self.tracker = TradeTracker(self.output_dir, leverage=self.leverage)
        self.tracker.on_losing_trade = self._capture_incident

        self._incidents_dir = self.output_dir / "incidents"
        self._incidents_dir.mkdir(parents=True, exist_ok=True)

        self._shutdown = False
        self._start_time = datetime.now(timezone.utc)
        self._last_rebalance_date = None

        self._setup_logging()

    def _capture_incident(self, trade: dict, symbol: str):
        pass # Simplified for brevity here

    def _setup_logging(self):
        log_path = self.output_dir / "bot.log"
        handler = logging.FileHandler(str(log_path), encoding='utf-8')
        handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s"))
        root = logging.getLogger()
        root.addHandler(handler)
        root.setLevel(logging.INFO)
        import io
        utf8_stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        stdout_handler = logging.StreamHandler(utf8_stdout)
        stdout_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
        root.addHandler(stdout_handler)

    def _check_and_rebalance(self, current_date_utc: datetime):
        today = current_date_utc.date()
        if self._last_rebalance_date == today:
            return
            
        logger.info(f"Triggering daily rebalance for {today}")
        scanner_data = self.router.load_scanner_json(str(SCANNER_PATH))
        allocations = self.router.rebalance_daily(scanner_data)
        
        for sym, alloc in allocations.items():
            if sym not in self.engines:
                logger.info(f"Creating new V14Engine for {sym} (capital={alloc} initial, funded dynamically)")
                self.engines[sym] = V14LifecycleEngine(symbol=sym, capital=alloc, profile=self.profile)
                self.engines[sym]._live_mode = True
            else:
                eng = self.engines[sym]._engine
                if eng:
                    invested = eng.long_cost + eng.short_cost
                    new_cash = max(0.0, alloc - invested)
                    eng.capital = max(eng.capital, new_cash)
        
        self._last_rebalance_date = today

    def _process_actions(self, symbol: str, actions: List[dict], ts: datetime):
        """Intercepts actions. If BUY/SHORT_OPEN, requests capital. If rejected, rolls back."""
        valid_actions = []
        for act in actions:
            action_type = act.get("action", "")
            qty = act.get("qty", 0)
            price = act.get("price", 0)
            cost = price * qty if price and qty else 0
            
            # The engine already mutated its state. We act as the "bouncer" and rollback if denied.
            if action_type in ("BUY", "SHORT_OPEN"):
                # Which layer is this?
                layer = 1
                key = f"{symbol}:long" if action_type == "BUY" else f"{symbol}:short"
                if key in self.tracker._open_deals:
                    layer = self.tracker._open_deals[key].get("layers", 0) + 1
                
                # Request capital from router
                pool = "reserve" if layer >= 6 else "active"
                granted = self.router.request_capital(symbol, cost, pool=pool)
                
                if granted <= 0:
                    logger.warning(f"Router denied capital for {symbol} {action_type}. Rolling back.")
                    # Rollback the engine trade
                    self.engines[symbol].reject_action(act)
                    # Do not pass this action forward
                    continue
                elif granted < cost:
                    logger.warning(f"Router granted partial capital for {symbol}. Modifying action.")
                    # Technically rolling back and re-submitting partial is complex. 
                    # If granted is > 0 but < cost, for simplicity in paper we reject it, 
                    # OR we could just log it and rollback.
                    logger.warning(f"Rejecting {symbol} because partial fill handling is unsupported in this version.")
                    self.engines[symbol].reject_action(act)
                    self.router.return_capital(symbol, granted) # Return what we just took
                    continue
                
                logger.info(f"Router approved {action_type} for {symbol}: ${granted:.2f}")
                valid_actions.append(act)
                
            elif action_type in ("SELL", "SHORT_CLOSE"):
                # Return capital to the router
                # V14 engine passes `amount` representing original cost + pnl? 
                # Proceeds = cost + pnl.
                # However, the router `return_capital` function takes raw amount.
                proceeds = qty * price if qty and price else 0
                self.router.return_capital(symbol, proceeds)
                valid_actions.append(act)
                
            else:
                valid_actions.append(act)
                
        # Only process valid actions into tracker
        if valid_actions:
            self.tracker.process_actions(symbol, valid_actions, ts)

    def run_live(self):
        import ccxt
        logger.info("Starting V14 Portfolio live trading loop")
        exchange = ccxt.hyperliquid()
        exchange.load_markets()

        last_candle_ts: Dict[str, int] = {}
        
        while not self._shutdown:
            try:
                cycle_start = time.time()
                # Remove static check here since we'll check per candle
                # (Rebalancing is triggered by the earliest unprocessed candle)

                for sym in list(self.engines.keys()):
                    base = sym.split('/')[0]
                    hl_sym = f"{base}/USDC:USDC"
                        
                    try:
                        ohlcv = exchange.fetch_ohlcv(hl_sym, self.timeframe, limit=200)
                    except Exception as e:
                        logger.error(f"Failed to fetch candles for {sym} ({hl_sym}): {e}")
                        continue

                    if not ohlcv:
                        continue

                    engine = self.engines[sym]
                    if sym not in last_candle_ts:
                        last_candle_ts[sym] = engine._last_candle_ts or 0

                    for bar in ohlcv:
                        ts_ms = int(bar[0])
                        if ts_ms <= last_candle_ts[sym]:
                            continue

                        now_ms = int(time.time() * 1000)
                        candle_end = ts_ms + 3600_000
                        if candle_end > now_ms:
                            break

                        ts_dt = datetime.fromtimestamp(ts_ms / 1000, tz=timezone.utc)
                        self._check_and_rebalance(ts_dt)

                        candle = {
                            "timestamp": ts_ms,
                            "open": float(bar[1]),
                            "high": float(bar[2]),
                            "low": float(bar[3]),
                            "close": float(bar[4]),
                            "volume": float(bar[5]),
                        }

                        try:
                            # Use 0 as cash_available since router enforces limits now
                            actions = engine.tick(candle, 0)
                        except Exception as e:
                            logger.error(f"Engine tick failed for {sym}: {e}")
                            continue
                        
                        ts_dt = datetime.fromtimestamp(ts_ms / 1000, tz=timezone.utc)

                        if actions:
                            self._process_actions(sym, actions, ts_dt)

                        last_candle_ts[sym] = ts_ms
                        engine._last_candle_ts = ts_ms

                self.tracker.save_csv()

                elapsed = time.time() - cycle_start
                sleep_time = max(1, LIVE_POLL_INTERVAL - elapsed)
                deadline = time.time() + sleep_time
                while time.time() < deadline and not self._shutdown:
                    time.sleep(1)

            except KeyboardInterrupt:
                break
            except Exception as e:
                logger.error(f"Live loop error: {e}")
                time.sleep(30)

        logger.info("V14 Portfolio live loop stopped")

    def run(self):
        def _shutdown_handler(signum, frame):
            logger.info("Shutting down...")
            self._shutdown = True

        signal.signal(signal.SIGINT, _shutdown_handler)
        signal.signal(signal.SIGTERM, _shutdown_handler)

        # Ensure we rebalance immediately
        self._check_and_rebalance(datetime.now(timezone.utc))
        self.run_live()

def main():
    parser = argparse.ArgumentParser(description="V14 Portfolio Paper Trading Bot")
    parser.add_argument("--capital", type=float, default=DEFAULT_CAPITAL)
    parser.add_argument("--profile", type=str, default="medium")
    parser.add_argument("--leverage", type=float, default=None)
    parser.add_argument("--exchange", type=str, default="hyperliquid")
    args = parser.parse_args()

    bot = V14PortfolioPaperBot(
        capital=args.capital,
        exchange=args.exchange,
        profile=args.profile,
        leverage=args.leverage
    )
    bot.run()

if __name__ == "__main__":
    main()
