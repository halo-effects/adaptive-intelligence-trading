#!/usr/bin/env python3
"""
V14 Paper Trading Bot Runner
=============================
Entry point for V14 DCA-only lifecycle paper trading across 4 coins on Hyperliquid.

Backfills from DB candles (Oct 2024 -> present), then transitions to live
candle feeds via CCXT. Writes dashboard-compatible status.json and trades.csv.

Usage:
    python -m trading.spot.run_v14_paper [options]
    python trading/spot/run_v14_paper.py [options]
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
from trading.spot.incident_schema import create_incident_report

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

CANONICAL_SYMBOLS = ["HBAR/USDT", "ATOM/USDT", "LINK/USDC", "NEAR/USDT"]

# Canonical -> DB symbol
DB_SYMBOL_MAP = {
    "HBAR/USDT": "HBAR/USDT",
    "ATOM/USDT": "ATOM/USDT",
    "LINK/USDC": "LINK/USDT",   # DB has USDT
    "NEAR/USDT": "NEAR/USDT",
}

# Canonical -> Aster perp price feed ticker (switched from Hyperliquid 2026-04-19)
# All four coins trade as {COIN}/USDT:USDT on Aster perps.
ASTER_PRICE_MAP = {
    "HBAR/USDT": "HBAR/USDT:USDT",
    "ATOM/USDT": "ATOM/USDT:USDT",
    "LINK/USDC": "LINK/USDT:USDT",
    "NEAR/USDT": "NEAR/USDT:USDT",
}

DB_PATH = Path(os.environ.get("AIT_CANDLES_DB", str(_WORKSPACE / "trading" / "spot" / "data" / "candles.db")))
DEFAULT_OUTPUT_DIR = _WORKSPACE / "trading" / "spot" / "paper" / "v14"
DEFAULT_START_DATE = "2024-10-01"
DEFAULT_CAPITAL = 10000.0
LIVE_POLL_INTERVAL = 60  # seconds

logger = logging.getLogger("v14_paper")


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
    """Load 1h candles from candles.db for a symbol."""
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

    def __init__(self, output_dir: Path, leverage: float = 1.0):
        self.output_dir = output_dir
        self.leverage = leverage
        self.trades: List[dict] = []
        self._deal_counter = 0
        self._open_deals: Dict[str, dict] = {}
        self._existing_keys: set = set()  # keys from loaded trades to prevent re-recording
        self.on_losing_trade = None  # callback(trade_dict, symbol) for incident capture

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
        """Write trades.csv (deduplicated by symbol+close_time)."""
        try:
            path = self.output_dir / "trades.csv"
            # Deduplicate: keep first occurrence of each symbol+open_time+close_time
            seen = set()
            unique = []
            for t in self.trades:
                key = f"{t['symbol']}|{t['open_time']}|{t['close_time']}"
                if key not in seen:
                    seen.add(key)
                    unique.append(t)
            # Sort by close_time for chronological equity charts
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
                    # Track existing trade keys to prevent re-recording on catch-up
                    key = f"{row['symbol']}|{row['open_time']}|{row['close_time']}"
                    self._existing_keys.add(key)
                    if row["deal_id"] > self._deal_counter:
                        self._deal_counter = row["deal_id"]
            logger.info(f"Loaded {len(self.trades)} existing trades from CSV")
        except Exception as e:
            logger.warning(f"Failed to load existing trades: {e}")


# ---------------------------------------------------------------------------
# V14PaperBot
# ---------------------------------------------------------------------------

class V14PaperBot:
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
        self.leverage = V14_PROFILES.get(profile, V14_PROFILES['medium'])['leverage']

        # Per-coin capital
        per_coin = capital / len(symbols)

        # Create engines
        self.engines: Dict[str, V14LifecycleEngine] = {}
        for sym in symbols:
            self.engines[sym] = V14LifecycleEngine(
                symbol=sym, capital=per_coin, profile=profile
            )

        # Cash tracking
        self.cash = capital
        self.per_coin_cash: Dict[str, float] = {s: per_coin for s in symbols}

        # Trade tracker
        self.tracker = TradeTracker(self.output_dir, leverage=self.leverage)
        self.tracker.on_losing_trade = self._capture_incident

        # Incidents directory
        self._incidents_dir = self.output_dir / "incidents"
        self._incidents_dir.mkdir(parents=True, exist_ok=True)

        # Shutdown flag
        self._shutdown = False
        self._start_time = datetime.now(timezone.utc)

        # CFGI state
        self._cfgi_market = None
        self._cfgi_coins: Dict[str, float] = {}
        self._cfgi_last_poll = 0.0
        self._scanner_last_date = None  # Track last scanner run date (UTC)

        # Setup logging
        self._setup_logging()

    def _capture_incident(self, trade: dict, symbol: str):
        """Capture a losing trade incident report. Never crashes the trading loop."""
        try:
            # Build engine state for this coin
            engine_state = self.engines[symbol].get_status() if symbol in self.engines else {}

            # Build peer states
            peer_states = {}
            for sym, eng in self.engines.items():
                if sym != symbol:
                    try:
                        peer_states[sym] = eng.get_status()
                    except Exception:
                        pass

            # Market context
            market_context = {
                "cfgi": self._cfgi_market,
                "regime": None,
                "trend_direction": None,
            }
            # Derive from CFGI
            fgi = self._cfgi_market
            if fgi is not None:
                if fgi <= 20: market_context["regime"] = "EXTREME"
                elif fgi <= 40: market_context["regime"] = "ACCUMULATION"
                elif fgi <= 60: market_context["regime"] = "RANGING"
                elif fgi <= 80: market_context["regime"] = "TRENDING"
                else: market_context["regime"] = "DISTRIBUTION"

            # Config snapshot
            profile_params = V14_PROFILES.get(self.profile, V14_PROFILES['medium'])
            config = {
                "account_id": "paper-v14",
                "profile": self.profile,
                "capital": self.capital,
                "leverage": self.leverage,
                **profile_params,
            }

            # Add close reason from the last engine trade action
            if symbol in self.engines and self.engines[symbol]._engine:
                eng_trades = self.engines[symbol]._engine.trades
                if eng_trades:
                    last_trade = eng_trades[-1]
                    trade["reason"] = last_trade.get("action", "unknown")

            incident = create_incident_report(
                trade=trade,
                engine_state=engine_state,
                peer_states=peer_states,
                market_context=market_context,
                config=config,
            )

            # Write incident file
            incident_id = incident["incident_id"][:8]
            coin = symbol.split("/")[0]
            ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
            filename = f"{ts}_{coin}_{incident_id}.json"
            filepath = self._incidents_dir / filename
            with open(filepath, "w") as f:
                json.dump(incident, f, indent=2, default=str)

            logger.warning(
                f"📋 Incident captured: {coin} {incident['classification']} "
                f"${trade.get('pnl', 0):.2f} [{incident['severity']}] -> {filename}"
            )

            # Telegram alert
            try:
                send_telegram(
                    f"📋 <b>Incident Report</b>\n"
                    f"Coin: {coin} | {incident['classification']}\n"
                    f"Loss: ${trade.get('pnl', 0):.2f} ({trade.get('return_pct', 0):.1f}%)\n"
                    f"Severity: {incident['severity']} | Layers: {trade.get('layers', 0)}\n"
                    f"💡 {incident['recommendation']}"
                )
            except Exception:
                pass

        except Exception as e:
            logger.error(f"Incident capture failed (non-fatal): {e}")

    def _setup_logging(self):
        log_path = self.output_dir / "bot.log"
        handler = logging.FileHandler(str(log_path), encoding='utf-8')
        handler.setFormatter(logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
        ))
        root = logging.getLogger()
        root.addHandler(handler)
        root.setLevel(logging.INFO)

        # Force UTF-8 on stdout to handle emoji on Windows (cp1252)
        import io
        utf8_stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        stdout_handler = logging.StreamHandler(utf8_stdout)
        stdout_handler.setFormatter(logging.Formatter(
            "%(asctime)s [%(levelname)s] %(message)s"
        ))
        root.addHandler(stdout_handler)

    # -------------------------------------------------------------------
    # Backfill
    # -------------------------------------------------------------------

    def backfill(self):
        """Run historical backfill from DB candles via engine.backfill_direct()."""
        logger.info(f"Starting V14 backfill from {self.start_date}")
        try:
            send_telegram(f"📊 <b>V14 Paper Bot</b> starting backfill from {self.start_date}")
        except Exception:
            pass

        end_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")

        for sym in self.symbols:
            engine = self.engines[sym]

            # Run V14 engine directly (identical to standalone backtest)
            actions = engine.backfill_direct(self.start_date, end_date)

            # Process all actions for cash tracking and trade logging
            if actions:
                for act in actions:
                    trade_date = act.get('date')
                    if trade_date is not None:
                        if isinstance(trade_date, pd.Timestamp):
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
        try:
            self._save_state()
        except Exception as e:
            logger.error(f"State save failed after backfill: {e}")
        try:
            self.tracker.save_csv()
        except Exception as e:
            logger.error(f"CSV save failed after backfill: {e}")
        try:
            self._write_status()
        except Exception as e:
            logger.error(f"Status write failed after backfill: {e}")

        total_pnl = sum(e.realized_pnl for e in self.engines.values())
        total_deals = sum(e.deals_completed for e in self.engines.values())
        logger.info(f"V14 Backfill complete — total realized PnL: ${total_pnl:.2f}, "
                    f"deals: {total_deals}, trades logged: {len(self.tracker.trades)}")
        try:
            send_telegram(
                f"✅ <b>V14 Backfill Complete</b>\n"
                f"PnL: ${total_pnl:.2f} | Deals: {total_deals} | "
                f"Trades: {len(self.tracker.trades)}"
            )
        except Exception:
            pass

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
                proceeds = qty * price if qty and price else 0
                self.per_coin_cash[symbol] += proceeds
                self.cash += proceeds
            elif action == "SHORT_CLOSE":
                key = f"{symbol}:short"
                orig_invested = 0
                if key in self.tracker._open_deals:
                    orig_invested = self.tracker._open_deals[key].get("invested", 0)
                returns = orig_invested + pnl
                self.per_coin_cash[symbol] += returns
                self.cash += returns

    # -------------------------------------------------------------------
    # Live trading
    # -------------------------------------------------------------------

    def run_live(self):
        """Main live loop — fetch 1h candles from Aster DEX, tick engines."""
        import ccxt

        logger.info("Starting V14 live trading loop")
        try:
            send_telegram("🔄 <b>V14 Paper Bot</b> entering live trading mode")
        except Exception:
            pass

        # Aster DEX — production exchange (switched from Hyperliquid 2026-04-19)
        exchange = ccxt.aster({
            "apiKey": os.environ.get("ASTER_API_KEY", ""),
            "secret": os.environ.get("ASTER_API_SECRET", ""),
        })
        exchange.load_markets()

        # Initialize last_candle_ts from state to avoid replaying old candles on restart
        last_candle_ts: Dict[str, int] = {}
        for s in self.symbols:
            eng = self.engines[s]
            if eng._last_candle_ts:
                last_candle_ts[s] = eng._last_candle_ts
            else:
                last_candle_ts[s] = 0

        while not self._shutdown:
            try:
                cycle_start = time.time()
                logger.debug(f"Live loop cycle starting at {datetime.now(timezone.utc).isoformat()}")

                for sym in self.symbols:
                    aster_sym = ASTER_PRICE_MAP.get(sym)
                    if not aster_sym:
                        logger.error(f"No Aster price map entry for {sym}")
                        continue

                    try:
                        ohlcv = exchange.fetch_ohlcv(aster_sym, self.timeframe, limit=200)
                    except Exception as e:
                        logger.error(f"Failed to fetch candles for {sym} ({aster_sym}): {e}\n{traceback.format_exc()}")
                        continue

                    if not ohlcv:
                        continue

                    engine = self.engines[sym]
                    prev_phase = engine.phase

                    for bar in ohlcv:
                        ts_ms = int(bar[0])
                        if ts_ms <= last_candle_ts[sym]:
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

                        try:
                            cash_avail = self.per_coin_cash.get(sym, 0)
                            actions = engine.tick(candle, cash_avail)
                        except Exception as e:
                            logger.error(f"Engine tick failed for {sym}: {e}\n{traceback.format_exc()}")
                            continue
                        
                        ts_dt = datetime.fromtimestamp(ts_ms / 1000, tz=timezone.utc)

                        if actions:
                            self._process_actions(sym, actions, ts_dt)
                            self.tracker.process_actions(sym, actions, ts_dt)
                            for act in actions:
                                logger.info(f"⚡ {sym}: {act}")
                                # Notify on trade completions
                                a = act.get('action', '')
                                if a in ('SELL', 'SHORT_CLOSE'):
                                    pnl = act.get('pnl', 0)
                                    emoji = "🟢" if pnl >= 0 else "🔴"
                                    try:
                                        send_telegram(
                                            f"{emoji} <b>{sym}</b> {a} @ ${act.get('price', 0):.4f}\n"
                                            f"PnL: ${pnl:.2f} | {act.get('reason', 'N/A')}"
                                        )
                                    except Exception:
                                        pass
                                elif a == 'PHASE_CHANGE':
                                    try:
                                        send_telegram(
                                            f"🔄 <b>{sym}</b> Phase: {act.get('from')} → {act.get('to')}\n"
                                            f"Reason: {act.get('reason', 'N/A')}"
                                        )
                                    except Exception:
                                        pass

                        last_candle_ts[sym] = ts_ms
                        engine._last_candle_ts = ts_ms

                # Poll CFGI
                try:
                    self._poll_cfgi()
                except Exception as e:
                    logger.error(f"CFGI polling failed: {e}")

                # Write outputs (each wrapped in try/except)
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

                # Scanner moved to separate scheduled task (CPU-intensive, causes live loop crashes)
                # See: trading/run_v14_scanner_task.py

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
                try:
                    send_telegram(f"⚠️ <b>V14 Bot Error:</b> {str(e)[:200]}")
                except Exception:
                    pass
                time.sleep(30)

        logger.info("V14 live trading loop stopped")
        try:
            send_telegram("🛑 <b>V14 Paper Bot</b> stopped")
        except Exception:
            pass

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
                    db_sym = DB_SYMBOL_MAP.get(sym, sym)
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
        if now - self._cfgi_last_poll < 3600:
            return

        try:
            from trading.spot.cfgi_client import CFGIClient
            api_key = os.environ.get("CFGI_API_KEY")
            if not api_key:
                return

            client = CFGIClient(api_key)

            token_map = {}
            for sym in self.symbols:
                base = sym.split("/")[0]
                token_map[sym] = base

            tokens = list(set(token_map.values())) + ["MARKET"]
            data = client.get_current(tokens, period=4, fields="cfgi")

            market_data = data.get("MARKET", {})
            if isinstance(market_data, dict):
                self._cfgi_market = market_data.get("cfgi", market_data.get("value"))
            elif isinstance(market_data, (int, float)):
                self._cfgi_market = float(market_data)

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
            self._cfgi_last_poll = now

    def _maybe_run_scanner(self):
        """Run V14 coin scanner once per day (after 00:30 UTC)."""
        now_utc = datetime.now(timezone.utc)
        today = now_utc.date()

        # Only run after 00:30 UTC to ensure daily candles are fresh
        if now_utc.hour == 0 and now_utc.minute < 30:
            return

        # Already ran today
        if self._scanner_last_date == today:
            return

        logger.info("Running daily V14 scanner refresh...")
        try:
            from trading.scanner.v14_scanner import scan_all, save_json
            output_path = self.output_dir.parent.parent.parent / 'docs' / 'data' / 'v14' / 'scanner.json'
            data = scan_all(capital=self.capital)
            save_json(data, str(output_path))
            self._scanner_last_date = today
            logger.info(f"Scanner refresh complete: {data.get('coins_qualified', 0)} coins qualified")
            try:
                send_telegram(
                    f"📊 <b>V14 Scanner</b> daily refresh complete\n"
                    f"Qualified: {data.get('coins_qualified', 0)}/{data.get('coins_tested', 0)} coins"
                )
            except Exception:
                pass
        except Exception as e:
            logger.error(f"Scanner refresh failed: {e}\n{traceback.format_exc()}")
            self._scanner_last_date = today  # Don't retry endlessly on persistent errors

    def _write_status(self):
        """Write combined status.json from all engines."""
        coins = {}
        total_equity = 0.0
        total_cash = 0.0
        total_realized = 0.0
        total_fees = 0.0
        total_deals = 0
        total_won = 0
        max_dd = 0.0

        for sym, engine in self.engines.items():
            try:
                st = engine.get_status()
            except Exception as e:
                logger.error(f"get_status failed for {sym}: {e}")
                continue

            if "coins" in st:
                coins.update(st["coins"])
                # Inject per-coin CFGI
                if sym in self._cfgi_coins and sym in coins:
                    coins[sym]["cfgi"] = round(self._cfgi_coins[sym], 1)
            total_equity += st.get("equity", 0)
            total_cash += st.get("cash", 0)
            total_realized += st.get("total_realized_pnl", 0)
            total_fees += st.get("total_fees", 0)
            total_deals += st.get("deals_completed", 0)
            total_won += engine.deals_won
            max_dd = max(max_dd, st.get("max_drawdown_pct", 0))

        pnl_pct = ((total_equity - self.capital) / self.capital * 100
                    if self.capital > 0 else 0.0)
        win_rate = (total_won / total_deals * 100) if total_deals > 0 else 0.0
        uptime_h = (datetime.now(timezone.utc) - self._start_time).total_seconds() / 3600

        # Read trades.csv as source of truth for deal counts AND realized PnL
        # (engine counters drift on restart; CSV is the ledger)
        csv_path = self.output_dir / "trades.csv"
        if csv_path.exists():
            try:
                with open(csv_path, 'r') as f:
                    reader = csv.DictReader(f)
                    csv_trades = list(reader)
                if csv_trades:
                    total_deals = len(csv_trades)
                    total_won = sum(1 for t in csv_trades if float(t.get('pnl', 0)) > 0)
                    win_rate = (total_won / total_deals * 100) if total_deals > 0 else 0.0
                    # CSV is always truth for realized PnL
                    csv_realized = sum(float(t.get('pnl', 0)) for t in csv_trades)
                    total_realized = csv_realized
                    # Recompute equity from ground truth
                    total_unrealized = sum(
                        coin_data.get("unrealized_pnl", 0) for coin_data in coins.values()
                    )
                    total_equity = self.capital + total_realized - total_fees + total_unrealized
                    total_cash = self.capital + total_realized - total_fees - sum(
                        coin_data.get("invested", 0) for coin_data in coins.values()
                    )
                    pnl_pct = ((total_equity - self.capital) / self.capital * 100
                                if self.capital > 0 else 0.0)
            except Exception as e:
                logger.warning("Failed to read trades.csv for deal counts: %s", e)

        # Derive regime from market CFGI
        fgi = self._cfgi_market
        if fgi is not None:
            if fgi <= 20:
                regime = "EXTREME"
            elif fgi <= 40:
                regime = "ACCUMULATION"
            elif fgi <= 60:
                regime = "RANGING"
            elif fgi <= 80:
                regime = "TRENDING"
            else:
                regime = "DISTRIBUTION"
        else:
            regime = "RANGING"

        # Derive trend from coin phases
        long_count = sum(1 for sym in self.symbols
                         if coins.get(sym, {}).get("lifecycle_phase") == "LONG_DCA")
        short_count = sum(1 for sym in self.symbols
                          if coins.get(sym, {}).get("lifecycle_phase") == "SHORT_DCA")
        if long_count > short_count:
            trend_direction = "bullish"
        elif short_count > long_count:
            trend_direction = "bearish"
        else:
            trend_direction = "neutral"

        status = {
            "running": True,
            "mode": "paper",
            "engine": "v14",
            "profile": self.profile,
            "leverage": self.leverage,
            "exchange": self.exchange,
            "capital": self.capital,
            "equity": round(total_equity, 2),
            "cash": round(total_cash, 2),
            "pnl_pct": round(pnl_pct, 2),
            "coins": coins,
            "symbols": self.symbols,
            "regime": regime,
            "trend_direction": trend_direction,
            "total_realized_pnl": round(total_realized, 2),
            "total_fees": round(total_fees, 2),
            "deals_completed": total_deals,
            "win_rate": round(win_rate, 1),
            "max_drawdown_pct": round(max_dd, 2),
            "uptime_hours": round(uptime_h, 2),
            "fear_greed_index": self._cfgi_market,
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
        try:
            self._write_status()
        except Exception as e:
            logger.error(f"Final status write failed: {e}")
        try:
            self.tracker.save_csv()
        except Exception as e:
            logger.error(f"Final CSV save failed: {e}")
        try:
            self._save_state()
        except Exception as e:
            logger.error(f"Final state save failed: {e}")
        logger.info("V14 Paper Bot shut down cleanly")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="V14 Paper Trading Bot")
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

    bot = V14PaperBot(
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
