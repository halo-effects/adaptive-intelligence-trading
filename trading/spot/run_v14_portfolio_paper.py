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

DB_PATH = Path(os.environ.get("AIT_CANDLES_DB", str(_WORKSPACE / "trading" / "spot" / "data" / "candles.db")))
DEFAULT_OUTPUT_DIR = _WORKSPACE / "trading" / "spot" / "paper" / "v14_portfolio"
DEFAULT_START_DATE = "2024-10-01"
DEFAULT_CAPITAL = 10000.0
LIVE_POLL_INTERVAL = 60  # seconds
SCANNER_PATH = Path(os.environ.get("AIT_SCANNER_JSON", str(_WORKSPACE / "docs" / "data" / "v14" / "cycle_scanner.json")))

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
                            "recorded_at": datetime.now(timezone.utc).isoformat(),
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
                            "recorded_at": datetime.now(timezone.utc).isoformat(),
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
                    "recorded_at",
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
            # Track earliest trade time for accurate uptime/daily ROI
            if self.trades:
                earliest = min(t.get("open_time", "") for t in self.trades)
                if earliest:
                    self.earliest_trade_time = earliest
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
        fresh: bool = False,
    ):
        self.capital = capital
        self.exchange = exchange
        self.profile = profile
        self.timeframe = timeframe
        self.output_dir = Path(output_dir or DEFAULT_OUTPUT_DIR)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.start_date = start_date
        self.leverage = leverage if leverage is not None else V14_PROFILES.get(profile, V14_PROFILES['medium'])['leverage']
        self.fresh = fresh
        # If fresh mode, record start time as floor for candle processing.
        # Any candle that closed before this timestamp is skipped — for ALL engines,
        # including ones created later by rebalance. This prevents phantom trades.
        self._fresh_floor_ms = int(time.time() * 1000) if fresh else 0

        self.router = CapitalRouter(initial_capital=self.capital)
        self.engines: Dict[str, V14LifecycleEngine] = {}
        
        self.tracker = TradeTracker(self.output_dir, leverage=self.leverage)
        self.tracker.load_existing()  # Preserve trade history across restarts
        self.tracker.on_losing_trade = self._capture_incident

        # Use earliest trade time for accurate uptime/daily ROI across restarts
        if hasattr(self.tracker, 'earliest_trade_time') and self.tracker.earliest_trade_time:
            try:
                self._trading_start_time = datetime.fromisoformat(self.tracker.earliest_trade_time)
                if self._trading_start_time.tzinfo is None:
                    self._trading_start_time = self._trading_start_time.replace(tzinfo=timezone.utc)
                logger.info(f"Trading start time set from CSV history: {self._trading_start_time.isoformat()}")
            except Exception:
                pass

        self._incidents_dir = self.output_dir / "incidents"
        self._incidents_dir.mkdir(parents=True, exist_ok=True)

        self._shutdown = False
        self._start_time = datetime.now(timezone.utc)
        # _trading_start_time may already be set from CSV history above; don't overwrite
        if not hasattr(self, '_trading_start_time') or self._trading_start_time is None:
            self._trading_start_time = self._start_time
        self._last_rebalance_date = None

        # Tier / approved-symbol tracking
        # _approved_symbols: set of coin symbols the current rebalance approved for T1 entry.
        # Coins NOT in this set are blocked from new T1 entries — existing open positions
        # continue running and exit gracefully on their own TP/SL.
        self._approved_symbols: set = set()
        self._tier_coin_cap: int = self.router.tier_coin_cap
        self._prev_tier_coin_cap: int = self._tier_coin_cap

        # Current equity snapshot (updated each write-status cycle)
        self._current_equity: float = self.capital

        # CFGI / Fear & Greed
        self._cfgi_market: Optional[float] = None
        self._cfgi_coins: Dict[str, float] = {}
        self._cfgi_last_poll: float = 0.0

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

    # -------------------------------------------------------------------
    # State Persistence
    # -------------------------------------------------------------------

    def _save_state(self):
        """Save full bot state to engine_state.json for restart recovery."""
        state = {
            "version": 1,
            "saved_at": datetime.now(timezone.utc).isoformat(),
            "last_rebalance_date": str(self._last_rebalance_date) if self._last_rebalance_date else None,
            "approved_symbols": sorted(self._approved_symbols),
            "current_equity": self._current_equity,
            "engines": {},
            "last_candle_ts": {},
            "open_deals": dict(self.tracker._open_deals),
            "router": {
                "active_pool_cash": self.router.active_pool_cash,
                "reserve_pool_cash": self.router.reserve_pool_cash,
                "active_allocations": dict(self.router.active_allocations),
                "reserve_allocations": dict(self.router.reserve_allocations),
            },
        }
        for sym, engine in self.engines.items():
            state["engines"][sym] = engine.snapshot_state()
            state["last_candle_ts"][sym] = engine._last_candle_ts

        path = self.output_dir / "engine_state.json"
        tmp = path.with_suffix(".tmp")
        try:
            with open(tmp, "w") as f:
                json.dump(state, f, indent=2, default=str)
            tmp.replace(path)
        except Exception as e:
            logger.error(f"Failed to save engine state: {e}")

    def _load_state(self) -> bool:
        """Load saved engine state. Returns True if state was restored."""
        path = self.output_dir / "engine_state.json"
        if not path.exists():
            logger.info("No saved engine state found — starting fresh")
            return False

        try:
            with open(path, "r") as f:
                state = json.load(f)
        except Exception as e:
            logger.error(f"Failed to read engine state: {e}")
            return False

        if state.get("version") != 1:
            logger.warning(f"Unknown state version {state.get('version')} — ignoring")
            return False

        saved_at = state.get("saved_at", "unknown")
        engine_states = state.get("engines", {})
        if not engine_states:
            logger.info("Saved state has no engines — starting fresh")
            return False

        logger.info(f"Restoring state from {saved_at} ({len(engine_states)} engines)")

        # Restore engines
        for sym, engine_state in engine_states.items():
            try:
                capital = engine_state.get("initial_capital", 1000)
                engine = V14LifecycleEngine(
                    symbol=sym, capital=capital, profile=self.profile, leverage=self.leverage
                )
                engine.restore_state(engine_state)
                engine._live_mode = True
                # Restore last candle timestamp so candle processing resumes correctly
                saved_ts = state.get("last_candle_ts", {}).get(sym, 0)
                engine._last_candle_ts = saved_ts
                self.engines[sym] = engine
                phase_str = engine.phase.name if hasattr(engine.phase, 'name') else str(engine.phase)
                logger.info(f"  {sym}: phase={phase_str}, last_candle_ts={saved_ts}")
            except Exception as e:
                logger.error(f"  Failed to restore engine {sym}: {e}")

        # Restore tracker open deals (in-progress trades)
        open_deals = state.get("open_deals", {})
        for key, deal in open_deals.items():
            if "deal_id" in deal:
                deal["deal_id"] = int(deal["deal_id"])
            if "layers" in deal:
                deal["layers"] = int(deal["layers"])
            if "invested" in deal:
                deal["invested"] = float(deal["invested"])
            self.tracker._open_deals[key] = deal
            # Ensure deal counter stays ahead
            if deal.get("deal_id", 0) > self.tracker._deal_counter:
                self.tracker._deal_counter = deal["deal_id"]
        if open_deals:
            logger.info(f"  Restored {len(open_deals)} open deals")

        # Restore router state
        router_state = state.get("router", {})
        if router_state:
            self.router.active_pool_cash = router_state.get("active_pool_cash", self.router.active_pool_cash)
            self.router.reserve_pool_cash = router_state.get("reserve_pool_cash", self.router.reserve_pool_cash)
            self.router.active_allocations = router_state.get("active_allocations", {})
            self.router.reserve_allocations = router_state.get("reserve_allocations", {})

        # Restore rebalance tracking
        last_reb = state.get("last_rebalance_date")
        if last_reb:
            from datetime import date as date_type
            try:
                parts = last_reb.split("-")
                self._last_rebalance_date = date_type(int(parts[0]), int(parts[1]), int(parts[2]))
            except Exception:
                pass

        self._approved_symbols = set(state.get("approved_symbols", []))
        self._current_equity = state.get("current_equity", self.capital)

        logger.info(f"State restore complete. {len(self.engines)} engines, "
                    f"equity=${self._current_equity:.2f}")
        return True

    def _compute_current_equity(self) -> float:
        """Compute equity from ground truth: capital + realized - fees + unrealized."""
        total_realized = 0.0
        total_fees = 0.0
        total_unrealized = 0.0
        for sym, engine in self.engines.items():
            try:
                st = engine.get_status()
                total_realized += st.get("total_realized_pnl", 0.0)
                total_fees += st.get("total_fees", 0.0)
                for coin_data in st.get("coins", {}).values():
                    total_unrealized += coin_data.get("unrealized_pnl", 0.0)
            except Exception:
                pass
        equity = self.capital + total_realized - total_fees + total_unrealized
        return equity if equity > 0 else self.capital

    def _check_and_rebalance(self, current_date_utc: datetime):
        today = current_date_utc.date()
        if self._last_rebalance_date == today:
            return

        logger.info(f"Triggering daily rebalance for {today}")
        scanner_data = self.router.load_scanner_json(str(SCANNER_PATH))

        # Pass current equity so the router can adjust the tier cap dynamically
        current_equity = self._current_equity
        allocations = self.router.rebalance_daily(scanner_data, current_equity=current_equity)

        # Detect tier change and alert
        new_tier = self.router.tier_coin_cap
        if new_tier != self._prev_tier_coin_cap:
            direction = "dropped" if new_tier < self._prev_tier_coin_cap else "increased"
            msg = (
                f"⚠️ [V14-PM] Tier {direction}: {self._prev_tier_coin_cap} → {new_tier} coins "
                f"(equity=${current_equity:.2f})\n"
                f"New T1 entries blocked for coins outside top-{new_tier}. "
                f"Existing positions will exit gracefully."
            )
            logger.warning(msg)
            send_telegram(msg)
            self._prev_tier_coin_cap = new_tier
        self._tier_coin_cap = new_tier

        # Update approved symbols — only these coins may receive new T1 (layer-1) entries
        self._approved_symbols = set(allocations.keys())
        logger.info(f"Approved symbols for T1 entry: {sorted(self._approved_symbols)}")

        for sym, alloc in allocations.items():
            if sym not in self.engines:
                logger.info(f"Creating new V14Engine for {sym} (initial alloc=${alloc:.2f})")
                self.engines[sym] = V14LifecycleEngine(
                    symbol=sym, capital=alloc, profile=self.profile, leverage=self.leverage
                )
                self.engines[sym]._live_mode = True
            else:
                eng = self.engines[sym]._engine
                if eng:
                    invested = eng.long_cost + eng.short_cost
                    new_cash = max(0.0, alloc - invested)
                    eng.capital = max(eng.capital, new_cash)

        self._last_rebalance_date = today

    def _is_t1_entry(self, symbol: str, action_type: str) -> bool:
        """Return True if this BUY/SHORT_OPEN would be a layer-1 (first) entry for this symbol."""
        key = f"{symbol}:long" if action_type == "BUY" else f"{symbol}:short"
        return key not in self.tracker._open_deals

    def _process_actions(self, symbol: str, actions: List[dict], ts: datetime):
        """Intercepts actions. If BUY/SHORT_OPEN, requests capital. If rejected, rolls back.

        Tier enforcement:
        - T1 (layer-1) entries are blocked for symbols not in self._approved_symbols.
        - DCA add-on layers (L2+) on existing positions are always allowed — we never
          strand an open position without capital to defend it.
        - SELL / SHORT_CLOSE always passes through so positions can exit gracefully.
        """
        valid_actions = []
        for act in actions:
            action_type = act.get("action", "")
            qty = act.get("qty", 0)
            price = act.get("price", 0)
            cost = price * qty if price and qty else 0
            
            # The engine already mutated its state. We act as the "bouncer" and rollback if denied.
            if action_type in ("BUY", "SHORT_OPEN"):
                # Tier gate: block T1 entries for out-of-tier coins
                if self._is_t1_entry(symbol, action_type):
                    if self._approved_symbols and symbol not in self._approved_symbols:
                        logger.info(
                            f"Tier gate: blocking T1 entry for {symbol} "
                            f"(not in approved top-{self._tier_coin_cap}). "
                            f"Position will be allowed to exit naturally."
                        )
                        self.engines[symbol].reject_action(act)
                        continue

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
                    self.engines[symbol].reject_action(act)
                    continue
                elif granted < cost:
                    logger.warning(
                        f"Router granted partial capital for {symbol} (${granted:.2f} of ${cost:.2f}). "
                        f"Rejecting — partial fills not supported."
                    )
                    self.engines[symbol].reject_action(act)
                    self.router.return_capital(symbol, granted)
                    continue
                
                logger.info(f"Router approved {action_type} for {symbol} L{layer}: ${granted:.2f}")
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

            token_map = {}
            for sym in self.engines.keys():
                base = sym.split("/")[0]
                token_map[sym] = base

            # Filter to CFGI-supported tokens only; request MARKET separately
            # to avoid unsupported coins (SNX, PENDLE, etc.) breaking the whole batch
            from trading.spot.cfgi_client import VALID_TOKENS
            valid_set = set(VALID_TOKENS)
            supported_coins = [t for t in set(token_map.values()) if t in valid_set]

            # Always fetch MARKET first (standalone so it never fails due to bad coins)
            market_resp = client.get_current(["MARKET"], period=4, fields="cfgi")
            market_data = market_resp.get("MARKET", {})

            # Fetch per-coin data only for supported tokens
            data = {}
            if supported_coins:
                data = client.get_current(supported_coins, period=4, fields="cfgi")
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

    def _write_status(self):
        """Write combined status.json from all engines for dashboard."""
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

        # Compute equity from ground truth: capital + realized - fees + unrealized
        # (Engine-internal equity can drift due to rebalance cash injections)
        total_unrealized = sum(
            coin_data.get("unrealized_pnl", 0) for coin_data in coins.values()
        )
        total_equity = self.capital + total_realized - total_fees + total_unrealized

        # Cash = capital not currently invested in open positions
        total_invested = sum(
            coin_data.get("invested", 0) for coin_data in coins.values()
        )
        total_cash = self.capital + total_realized - total_fees - total_invested

        pnl_pct = ((total_equity - self.capital) / self.capital * 100
                    if self.capital > 0 else 0.0)
        win_rate = (total_won / total_deals * 100) if total_deals > 0 else 0.0
        uptime_h = (datetime.now(timezone.utc) - self._trading_start_time).total_seconds() / 3600

        # Read trades.csv for accurate deal counts and historical realized PnL
        # (engines lose state on restart; trades.csv is the source of truth)
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
                    # (engine counters drift on restart; CSV is the ledger)
                    csv_realized = sum(float(t.get('pnl', 0)) for t in csv_trades)
                    total_realized = csv_realized
                    # Recompute equity with CSV-based realized
                    total_equity = self.capital + total_realized - total_fees + total_unrealized
                    total_cash = self.capital + total_realized - total_fees - total_invested
                    pnl_pct = ((total_equity - self.capital) / self.capital * 100
                                if self.capital > 0 else 0.0)
            except Exception:
                pass

        # Derive regime from router state
        regime = "RANGING"
        trend_direction = "neutral"
        long_count = sum(1 for c in coins.values()
                         if c.get("lifecycle_phase") == "LONG_DCA")
        short_count = sum(1 for c in coins.values()
                          if c.get("lifecycle_phase") == "SHORT_DCA")
        if long_count > short_count:
            trend_direction = "bullish"
        elif short_count > long_count:
            trend_direction = "bearish"

        symbols = list(self.engines.keys())

        # Keep equity snapshot fresh for next rebalance tier check
        self._current_equity = total_equity if total_equity > 0 else self.capital

        status = {
            "running": True,
            "mode": "paper",
            "engine": "v14-pm",
            "profile": self.profile,
            "leverage": self.leverage,
            "exchange": self.exchange,
            "capital": self.capital,
            "equity": round(total_equity, 2),
            "cash": round(total_cash, 2),
            "pnl_pct": round(pnl_pct, 2),
            "coins": coins,
            "symbols": symbols,
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
            "tier_coin_cap": self._tier_coin_cap,
            "approved_symbols": sorted(self._approved_symbols),
            "router": {
                "active_cash": round(self.router.active_pool_cash, 2),
                "reserve_cash": round(self.router.reserve_pool_cash, 2),
                "total_active_allocated": round(sum(
                    self.router.active_allocations.values()
                ), 2),
                "total_reserve_allocated": round(sum(
                    self.router.reserve_allocations.values()
                ), 2),
            },
        }

        path = self.output_dir / "status.json"
        tmp = path.with_suffix(".tmp")
        try:
            with open(tmp, "w") as f:
                json.dump(status, f, indent=2, default=str)
            tmp.replace(path)
        except Exception as e:
            logger.error(f"Failed to write status.json: {e}")

    def run_live(self):
        import ccxt
        logger.info("Starting V14 Portfolio live trading loop")
        if self.fresh:
            logger.info("FRESH mode: will skip historical candles, trading from NOW only")
        exchange = ccxt.hyperliquid()
        exchange.load_markets()

        last_candle_ts: Dict[str, int] = {}
        
        # In fresh mode, seed last_candle_ts to skip all historical candles
        if self.fresh:
            now_ms = int(time.time() * 1000)
            # Pre-seed all engines: fetch latest candle for each coin and skip to it
            for sym in list(self.engines.keys()):
                base = sym.split('/')[0]
                hl_sym = f"{base}/USDC:USDC"
                try:
                    ohlcv = exchange.fetch_ohlcv(hl_sym, self.timeframe, limit=2)
                    if ohlcv:
                        # Set to the second-to-last candle so we only process the current/latest
                        latest_closed = ohlcv[-2][0] if len(ohlcv) > 1 else ohlcv[-1][0]
                        last_candle_ts[sym] = latest_closed
                        self.engines[sym]._last_candle_ts = latest_closed
                        logger.info(f"FRESH: Skipping history for {sym}, starting from ts={latest_closed}")
                except Exception as e:
                    logger.warning(f"FRESH: Failed to seed {sym}: {e}")

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

                        # FRESH MODE FLOOR: skip any candle that closed before bot started.
                        # This catches new engines created by rebalance mid-run that
                        # would otherwise replay all 200 historical candles.
                        if self._fresh_floor_ms and candle_end < self._fresh_floor_ms:
                            last_candle_ts[sym] = ts_ms
                            engine._last_candle_ts = ts_ms
                            continue

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
                try:
                    self._poll_cfgi()
                except Exception as e:
                    logger.warning(f"CFGI poll error: {e}")
                self._write_status()
                self._save_state()

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

        # Try to restore saved state (engines, router, open deals)
        if not self.fresh:
            restored = self._load_state()
        else:
            restored = False
            logger.info("FRESH mode — skipping state restore")

        # Rebalance immediately (if engines were restored, this updates allocations;
        # if fresh start, this creates new engines)
        self._check_and_rebalance(datetime.now(timezone.utc))
        self.run_live()

def _acquire_pid_lock(lock_path: Path) -> bool:
    """Acquire a PID lock file. Returns True if lock acquired, False if another instance is running."""
    if lock_path.exists():
        try:
            old_pid = int(lock_path.read_text().strip())
            # Check if the old process is still alive
            try:
                os.kill(old_pid, 0)  # Signal 0 = just check existence
                # Process exists — is it actually a PM bot?
                import subprocess
                result = subprocess.run(
                    ["wmic", "process", "where", f"ProcessId={old_pid}", "get", "CommandLine"],
                    capture_output=True, text=True, timeout=5
                )
                if "run_v14_portfolio_paper" in result.stdout:
                    return False  # Another PM bot is genuinely running
                else:
                    logger.warning(f"Stale PID lock (PID {old_pid} exists but isn't a PM bot). Overwriting.")
            except OSError:
                logger.warning(f"Stale PID lock (PID {old_pid} no longer running). Overwriting.")
        except (ValueError, IOError):
            logger.warning("Corrupt PID lock file. Overwriting.")

    # Write our PID
    lock_path.write_text(str(os.getpid()))
    return True


def _release_pid_lock(lock_path: Path):
    """Release the PID lock file if it belongs to us."""
    try:
        if lock_path.exists():
            stored_pid = int(lock_path.read_text().strip())
            if stored_pid == os.getpid():
                lock_path.unlink()
    except Exception:
        pass


def main():
    parser = argparse.ArgumentParser(description="V14 Portfolio Paper Trading Bot")
    parser.add_argument("--capital", type=float, default=DEFAULT_CAPITAL)
    parser.add_argument("--profile", type=str, default="medium")
    parser.add_argument("--leverage", type=float, default=None)
    parser.add_argument("--exchange", type=str, default="hyperliquid")
    parser.add_argument("--fresh", action="store_true", help="Start fresh — skip historical candles, trade from now only")
    args = parser.parse_args()

    # PID lock — prevent duplicate instances
    output_dir = Path(DEFAULT_OUTPUT_DIR)
    output_dir.mkdir(parents=True, exist_ok=True)
    lock_path = output_dir / "bot.pid"

    if not _acquire_pid_lock(lock_path):
        old_pid = lock_path.read_text().strip()
        logger.error(f"Another PM bot instance is already running (PID {old_pid}). Exiting.")
        sys.exit(1)

    logger.info(f"PID lock acquired: {lock_path} (PID {os.getpid()})")

    try:
        bot = V14PortfolioPaperBot(
            capital=args.capital,
            exchange=args.exchange,
            profile=args.profile,
            leverage=args.leverage,
            fresh=args.fresh,
        )
        bot.run()
    finally:
        _release_pid_lock(lock_path)
        logger.info("PID lock released.")

if __name__ == "__main__":
    main()
