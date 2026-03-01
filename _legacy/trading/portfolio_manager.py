"""Multi-coin portfolio manager for Aster DEX DCA trading.

Manages multiple CoinSlots, each running independent dual-tracking DCA.
Uses scanner results for coin selection and rotation.
"""
import json
import time
import os
import traceback
import subprocess
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import List, Optional, Dict, Any, Tuple

import requests
import pandas as pd
import numpy as np

from .aster_trader import (
    AsterAPI, LiveDeal, send_telegram,
    REGIME_ALLOC, DIRECTIONAL_REGIMES,
)
from .regime_detector import classify_regime_v2

LIVE_DIR = Path(__file__).parent / "live"
LIVE_DIR.mkdir(exist_ok=True)

# Portfolio constants
MAX_COINS = 3
CAPITAL_RESERVE_PCT = 0.10       # 10% always kept free
MIN_ALLOC_PCT = 0.15             # minimum 15% allocation per coin
MIN_HOLD_HOURS = 4               # minimum hold time before rotation
WIND_DOWN_TIMEOUT_S = 7200       # 2 hours max to wind down departing coin
SCANNER_INTERVAL_CYCLES = 720    # ~6 hours at 30s cycle
CYCLE_SLEEP = 30                 # seconds between cycles


def _fetch_exchange_info(api: AsterAPI, symbol: str) -> Dict[str, Any]:
    """Fetch market rules (tick size, step size, etc.) for a symbol."""
    try:
        info = api._get("/fapi/v1/exchangeInfo", {})
        for s in info.get("symbols", []):
            if s["symbol"] == symbol:
                tick_size = 0.001
                step_size = 0.01
                min_qty = 0.01
                min_notional = 5.0
                price_precision = 3
                qty_precision = 2
                for f in s.get("filters", []):
                    if f["filterType"] == "PRICE_FILTER":
                        tick_size = float(f.get("tickSize", tick_size))
                        price_precision = max(0, len(str(tick_size).rstrip('0').split('.')[-1]))
                    elif f["filterType"] == "LOT_SIZE":
                        step_size = float(f.get("stepSize", step_size))
                        min_qty = float(f.get("minQty", min_qty))
                        qty_precision = max(0, len(str(step_size).rstrip('0').split('.')[-1]))
                    elif f["filterType"] == "MIN_NOTIONAL":
                        min_notional = float(f.get("notional", f.get("minNotional", min_notional)))
                return {
                    "tick_size": tick_size, "step_size": step_size,
                    "min_qty": min_qty, "min_notional": min_notional,
                    "price_precision": price_precision, "qty_precision": qty_precision,
                }
    except Exception as e:
        print(f"  [WARN] exchangeInfo fetch failed for {symbol}: {e}")
    # Defaults
    return {
        "tick_size": 0.001, "step_size": 0.01,
        "min_qty": 0.01, "min_notional": 5.0,
        "price_precision": 3, "qty_precision": 2,
    }


class CoinSlot:
    """Per-coin trading slot — runs independent dual-tracking DCA."""

    # Strategy defaults (same as AsterTrader)
    TP_PCT = 1.5
    TP_MIN = 0.6
    TP_MAX = 2.5
    TP_UPDATE_THRESHOLD = 0.1
    ATR_PERIOD = 14
    ATR_BASELINE_PCT = 0.8
    MAX_SOS = 8
    DEVIATION_PCT = 2.5
    DEV_MIN = 1.2
    DEV_MAX = 4.0
    DEV_UPDATE_THRESHOLD = 0.15
    DEV_TP_FLOOR_MULT = 1.5
    DEVIATION_MULT = 1.0
    SO_VOL_MULT = 2.0
    BASE_ORDER_PCT = 0.04
    FEE_PCT = 0.05
    MARGIN_RESERVE_PCT = 0.10

    REGIME_TP_MULT = {
        "ACCUMULATION": 0.85, "CHOPPY": 0.90, "RANGING": 0.85,
        "DISTRIBUTION": 0.90, "MILD_TREND": 1.05, "TRENDING": 1.20,
        "EXTREME": 0.70, "BREAKOUT_WARNING": 0.80, "UNKNOWN": 1.0,
    }
    REGIME_DEV_MULT = {
        "ACCUMULATION": 0.85, "CHOPPY": 0.90, "RANGING": 0.80,
        "DISTRIBUTION": 0.90, "MILD_TREND": 1.10, "TRENDING": 1.30,
        "EXTREME": 1.50, "BREAKOUT_WARNING": 1.20, "UNKNOWN": 1.0,
    }

    def __init__(self, api: AsterAPI, symbol: str, alloc_capital: float,
                 alloc_pct: float, scanner_score: float = 0.0,
                 leverage: int = 1, dry_run: bool = False):
        self.api = api
        self.symbol = symbol
        self.alloc_capital = alloc_capital
        self.alloc_pct = alloc_pct
        self.scanner_score = scanner_score
        self.leverage = leverage
        self.dry_run = dry_run

        # Fetch per-coin market rules
        self.market_info = _fetch_exchange_info(api, symbol)

        # Deal tracking
        self.long_deal: Optional[LiveDeal] = None
        self.short_deal: Optional[LiveDeal] = None
        self.deal_counter = 0
        self.deals_completed = 0
        self.total_pnl = 0.0

        # Regime
        self.current_regime = "UNKNOWN"
        self.current_price = 0.0
        self._trend_bullish = True
        self._last_klines_df: Optional[pd.DataFrame] = None

        # Adaptive TP/deviation
        self.current_tp_pct = self.TP_PCT
        self.current_dev_pct = self.DEVIATION_PCT
        self.current_atr_pct = 0.0

        # Margin cache
        self._cached_available_margin = 0.0
        self._margin_cache_time = 0.0

        # Status
        self.status = "active"  # "active", "winding_down"
        self.added_time = time.time()
        self.wind_down_start: Optional[float] = None

        # Hedge mode (shared across portfolio — Aster doesn't support it)
        self.hedge_mode = False

    # ── Market rule helpers ──────────────────────────────────────────

    def round_price(self, p: float) -> float:
        ts = self.market_info["tick_size"]
        prec = self.market_info["price_precision"]
        return round(round(p / ts) * ts, prec)

    def round_qty(self, q: float) -> float:
        ss = self.market_info["step_size"]
        prec = self.market_info["qty_precision"]
        return round(round(q / ss) * ss, prec)

    # ── Safety order math ──────────────────────────────────────────

    def so_deviation(self, n: int) -> float:
        return self.current_dev_pct * n

    def so_price(self, entry: float, n: int, direction: str = "LONG") -> float:
        if direction == "SHORT":
            return self.round_price(entry * (1 + self.so_deviation(n) / 100))
        return self.round_price(entry * (1 - self.so_deviation(n) / 100))

    def so_qty(self, base_qty_usd: float, n: int) -> float:
        return base_qty_usd * (self.SO_VOL_MULT ** n)

    def base_order_usd(self) -> float:
        return self.alloc_capital * self.BASE_ORDER_PCT

    # ── Margin ──────────────────────────────────────────────────────

    def _get_available_margin(self, force: bool = False) -> float:
        if self.dry_run:
            return float('inf')
        now = time.time()
        if not force and (now - self._margin_cache_time) < 25:
            return self._cached_available_margin
        try:
            self._cached_available_margin = self.api.usdt_available()
            self._margin_cache_time = now
        except Exception as e:
            print(f"  [{self.symbol}] Margin check failed: {e}")
        return self._cached_available_margin

    def _margin_reserve(self) -> float:
        return self.alloc_capital * self.MARGIN_RESERVE_PCT

    def _estimate_order_margin(self, qty: float, price: float) -> float:
        notional = qty * price
        margin = notional / self.leverage if self.leverage > 0 else notional
        return margin * 1.2

    def _ensure_tp_margin(self, deal: LiveDeal, tp_qty: float, tp_price: float) -> bool:
        if self.dry_run:
            return True
        needed = self._estimate_order_margin(tp_qty, tp_price)
        available = self._get_available_margin(force=True)
        reserve = self._margin_reserve()
        if available - needed >= reserve:
            return True
        # Cancel deepest SOs to free margin
        cancelled = 0
        while deal.safety_order_ids and (available - needed < reserve):
            deepest_oid = deal.safety_order_ids.pop()
            try:
                self.api.cancel_order(self.symbol, deepest_oid)
                cancelled += 1
                available = self._get_available_margin(force=True)
            except Exception:
                pass
        if cancelled > 0:
            print(f"  [{self.symbol}] Cancelled {cancelled} SO(s) to free margin for TP")
        return (available - needed) >= reserve

    # ── Order helpers ──────────────────────────────────────────────

    def _entry_side(self, direction: str) -> str:
        return "BUY" if direction == "LONG" else "SELL"

    def _exit_side(self, direction: str) -> str:
        return "SELL" if direction == "LONG" else "BUY"

    def _position_side(self, direction: str) -> Optional[str]:
        if self.hedge_mode:
            return "LONG" if direction == "LONG" else "SHORT"
        return None

    # ── Regime ──────────────────────────────────────────────────────

    def detect_regime(self) -> str:
        try:
            df = self.api.klines(self.symbol, "5m", limit=300)
            if len(df) < 100:
                return "UNKNOWN"
            self.current_price = float(df["close"].iloc[-1])
            self._last_klines_df = df
            regimes = classify_regime_v2(df, "5m")
            sma50 = df["close"].rolling(50).mean().iloc[-1]
            self._trend_bullish = self.current_price >= sma50
            return regimes.iloc[-1]
        except Exception as e:
            print(f"  [{self.symbol}] Regime detection error: {e}")
            return self.current_regime

    def get_regime_alloc(self) -> Tuple[float, float]:
        long_alloc, short_alloc = REGIME_ALLOC.get(self.current_regime, (0.5, 0.5))
        if self.current_regime in DIRECTIONAL_REGIMES and not self._trend_bullish:
            long_alloc, short_alloc = short_alloc, long_alloc
        return long_alloc, short_alloc

    # ── Adaptive TP/deviation ──────────────────────────────────────

    def _calculate_atr_pct(self) -> float:
        df = self._last_klines_df
        if df is None or len(df) < self.ATR_PERIOD + 1:
            return 0.0
        high = df["high"].values
        low = df["low"].values
        close = df["close"].values
        tr = np.maximum(high[1:] - low[1:],
                        np.maximum(np.abs(high[1:] - close[:-1]),
                                   np.abs(low[1:] - close[:-1])))
        atr = float(np.mean(tr[-self.ATR_PERIOD:]))
        price = float(close[-1])
        return (atr / price * 100) if price > 0 else 0.0

    def _calculate_adaptive_tp(self) -> float:
        atr_pct = self._calculate_atr_pct()
        self.current_atr_pct = atr_pct
        if atr_pct <= 0:
            return self.TP_PCT
        atr_ratio = atr_pct / self.ATR_BASELINE_PCT
        tp = self.TP_PCT * atr_ratio
        tp *= self.REGIME_TP_MULT.get(self.current_regime, 1.0)
        return round(max(self.TP_MIN, min(self.TP_MAX, tp)), 3)

    def _calculate_adaptive_deviation(self) -> float:
        if self.current_atr_pct <= 0:
            return self.DEVIATION_PCT
        atr_ratio = self.current_atr_pct / self.ATR_BASELINE_PCT
        dev = self.DEVIATION_PCT * atr_ratio
        dev *= self.REGIME_DEV_MULT.get(self.current_regime, 1.0)
        dev = max(self.DEV_MIN, min(self.DEV_MAX, dev))
        tp_floor = self.current_tp_pct * self.DEV_TP_FLOOR_MULT
        dev = max(dev, tp_floor)
        return round(min(dev, self.DEV_MAX), 3)

    def update_adaptive_tp(self):
        new_tp = self._calculate_adaptive_tp()
        new_dev = self._calculate_adaptive_deviation()
        tp_changed = abs(new_tp - self.current_tp_pct) >= self.TP_UPDATE_THRESHOLD
        dev_changed = abs(new_dev - self.current_dev_pct) >= self.DEV_UPDATE_THRESHOLD

        old_tp = self.current_tp_pct
        old_dev = self.current_dev_pct
        self.current_tp_pct = new_tp
        self.current_dev_pct = new_dev

        if tp_changed or dev_changed:
            for deal in self._active_deals():
                if tp_changed:
                    self._update_tp_order(deal)
                if dev_changed:
                    self._update_so_orders_adaptive(deal)

    # ── Deal management ──────────────────────────────────────────

    def _active_deals(self) -> List[LiveDeal]:
        deals = []
        if self.long_deal:
            deals.append(self.long_deal)
        if self.short_deal:
            deals.append(self.short_deal)
        return deals

    def _set_deal(self, direction: str, deal: Optional[LiveDeal]):
        if direction == "LONG":
            self.long_deal = deal
        else:
            self.short_deal = deal

    def has_open_deals(self) -> bool:
        return self.long_deal is not None or self.short_deal is not None

    def open_deal(self, direction: str, alloc_fraction: float = 1.0):
        bo_usd = self.base_order_usd()
        min_notional = self.market_info["min_notional"]
        min_qty = self.market_info["min_qty"]

        if bo_usd < min_notional:
            print(f"  [{self.symbol}] SKIP {direction} — base ${bo_usd:.2f} < min ${min_notional}")
            return

        qty = self.round_qty(bo_usd / self.current_price)
        if qty < min_qty:
            print(f"  [{self.symbol}] SKIP {direction} — qty {qty} < min {min_qty}")
            return

        entry_side = self._entry_side(direction)
        pos_side = self._position_side(direction)
        dir_emoji = "\U0001f7e2" if direction == "LONG" else "\U0001f534"
        now_str = datetime.now(timezone.utc).isoformat()
        self.deal_counter += 1

        if self.dry_run:
            new_deal = LiveDeal(
                deal_id=self.deal_counter, symbol=self.symbol,
                entry_price=self.current_price, entry_qty=qty,
                entry_cost=qty * self.current_price, entry_time=now_str,
                direction=direction,
            )
            self._set_deal(direction, new_deal)
            print(f"  {dir_emoji} [{self.symbol}] [DRY] {direction} deal#{self.deal_counter} @ ${self.current_price:.4f}")
            send_telegram(f"{dir_emoji} <b>[DRY] {self.symbol} {direction} #{self.deal_counter}</b>\nEntry: ${self.current_price:.4f}\nRegime: {self.current_regime}")
            return

        try:
            result = self.api.place_order(self.symbol, entry_side, "MARKET", qty, position_side=pos_side)
            order_id = result.get("orderId")
            fill_price = float(result.get("avgPrice", 0))
            fill_qty = float(result.get("executedQty", 0))

            if fill_qty == 0 or fill_price == 0:
                for _ in range(10):
                    time.sleep(1)
                    status = self.api.query_order(self.symbol, order_id)
                    fill_price = float(status.get("avgPrice", 0))
                    fill_qty = float(status.get("executedQty", 0))
                    if fill_qty > 0 and fill_price > 0:
                        break
                if fill_qty == 0 or fill_price == 0:
                    try:
                        self.api.cancel_order(self.symbol, order_id)
                    except Exception:
                        pass
                    self.deal_counter -= 1
                    return

            cost = fill_price * fill_qty
            new_deal = LiveDeal(
                deal_id=self.deal_counter, symbol=self.symbol,
                entry_price=fill_price, entry_qty=fill_qty,
                entry_cost=cost, entry_time=now_str, direction=direction,
            )
            self._set_deal(direction, new_deal)
            print(f"  {dir_emoji} [{self.symbol}] {direction} #{self.deal_counter} @ ${fill_price:.4f}")

            self._place_so_orders(new_deal)
            self._place_tp_order(new_deal)

            send_telegram(
                f"{dir_emoji} <b>{self.symbol} {direction} #{self.deal_counter}</b>\n"
                f"Entry: ${fill_price:.4f} | TP: ${new_deal.tp_price(self.current_tp_pct):.4f}\n"
                f"Regime: {self.current_regime}"
            )
        except Exception as e:
            print(f"  [{self.symbol}] Failed to open {direction}: {e}")
            self.deal_counter -= 1

    def _place_so_orders(self, deal: LiveDeal):
        if not deal:
            return
        bo_usd = self.base_order_usd()
        direction = deal.direction
        so_side = self._entry_side(direction)
        pos_side = self._position_side(direction)
        deal.safety_order_ids = []
        available = self._get_available_margin()
        reserve = self._margin_reserve()

        for n in range(1, self.MAX_SOS + 1):
            price = self.so_price(deal.entry_price, n, direction)
            size_usd = self.so_qty(bo_usd, n)
            qty = self.round_qty(size_usd / price)
            if qty < self.market_info["min_qty"] or qty * price < self.market_info["min_notional"]:
                break
            margin_needed = self._estimate_order_margin(qty, price)
            if not self.dry_run and (available - margin_needed) < reserve:
                print(f"  [{self.symbol}] {direction} SO#{n}+ skipped — margin")
                break
            try:
                result = self.api.place_order(self.symbol, so_side, "LIMIT", qty, price=price,
                                              position_side=pos_side)
                deal.safety_order_ids.append(int(result["orderId"]))
                available -= margin_needed
            except Exception as e:
                print(f"  [{self.symbol}] SO#{n} failed: {e}")

    def _place_tp_order(self, deal: LiveDeal):
        if not deal:
            return
        tp = deal.tp_price(self.current_tp_pct)
        exit_side = self._exit_side(deal.direction)
        pos_side = self._position_side(deal.direction)
        self._ensure_tp_margin(deal, deal.total_qty, tp)

        if self.dry_run:
            return

        try:
            result = self.api.place_order(
                self.symbol, exit_side, "LIMIT", deal.total_qty,
                price=tp, position_side=pos_side
            )
            deal.tp_order_id = int(result["orderId"])
        except Exception as e:
            print(f"  [{self.symbol}] TP order failed: {e}")
            # Emergency: cancel SOs and retry
            if deal.safety_order_ids:
                self._cancel_remaining_sos(deal)
                try:
                    result = self.api.place_order(
                        self.symbol, exit_side, "LIMIT", deal.total_qty,
                        price=tp, position_side=pos_side
                    )
                    deal.tp_order_id = int(result["orderId"])
                except Exception as e2:
                    print(f"  [{self.symbol}] TP retry FAILED: {e2}")
                    send_telegram(f"🚨 {self.symbol} {deal.direction} TP placement failed: {e2}")

    def _update_tp_order(self, deal: LiveDeal):
        if not deal:
            return
        if deal.tp_order_id and not self.dry_run:
            try:
                self.api.cancel_order(self.symbol, deal.tp_order_id)
            except Exception:
                pass
        deal.tp_order_id = None
        self._place_tp_order(deal)

    def _update_so_orders_adaptive(self, deal: LiveDeal):
        if not deal:
            return
        if not self.dry_run:
            for oid in list(deal.safety_order_ids):
                try:
                    self.api.cancel_order(self.symbol, oid)
                except Exception:
                    pass
        deal.safety_order_ids = []
        remaining = self.MAX_SOS - deal.safety_orders_filled
        if remaining <= 0:
            return
        self._place_remaining_sos(deal)

    def _place_remaining_sos(self, deal: LiveDeal):
        if not deal:
            return
        bo_usd = self.base_order_usd()
        direction = deal.direction
        so_side = self._entry_side(direction)
        pos_side = self._position_side(direction)
        deal.safety_order_ids = []
        available = self._get_available_margin()
        reserve = self._margin_reserve()

        for n in range(deal.safety_orders_filled + 1, self.MAX_SOS + 1):
            price = self.so_price(deal.entry_price, n, direction)
            size_usd = self.so_qty(bo_usd, n)
            qty = self.round_qty(size_usd / price)
            if qty < self.market_info["min_qty"] or qty * price < self.market_info["min_notional"]:
                break
            margin_needed = self._estimate_order_margin(qty, price)
            if not self.dry_run and (available - margin_needed) < reserve:
                break
            try:
                result = self.api.place_order(self.symbol, so_side, "LIMIT", qty, price=price,
                                              position_side=pos_side)
                deal.safety_order_ids.append(int(result["orderId"]))
                available -= margin_needed
            except Exception as e:
                print(f"  [{self.symbol}] SO#{n} failed: {e}")

    def _cancel_remaining_sos(self, deal: LiveDeal):
        if not deal or self.dry_run:
            return
        for oid in deal.safety_order_ids:
            try:
                self.api.cancel_order(self.symbol, oid)
            except Exception:
                pass
        deal.safety_order_ids = []

    def _calc_pnl(self, close_price: float, total_qty: float, total_cost: float, direction: str) -> float:
        if direction == "SHORT":
            return total_cost - (total_qty * close_price)
        return (total_qty * close_price) - total_cost

    def check_orders(self):
        """Check TP/SO fills for all active deals."""
        if self.dry_run:
            self._dry_run_check()
            return
        if self.long_deal:
            self._check_orders_for_deal(self.long_deal)
        if self.short_deal:
            self._check_orders_for_deal(self.short_deal)

    def _check_orders_for_deal(self, deal: LiveDeal) -> bool:
        if not deal:
            return False
        direction = deal.direction

        # Retry missing TP
        if not deal.tp_order_id:
            self._place_tp_order(deal)

        # Check TP
        if deal.tp_order_id:
            try:
                tp_info = self.api.query_order(self.symbol, deal.tp_order_id)
                if tp_info["status"] == "FILLED":
                    fill_price = float(tp_info.get("avgPrice", tp_info.get("price", 0)))
                    pnl = self._calc_pnl(fill_price, deal.total_qty, deal.total_cost, direction)
                    pnl_pct = pnl / deal.total_cost * 100
                    print(f"  ✅ [{self.symbol}] TP HIT {direction} #{deal.deal_id} @ ${fill_price:.4f} | PnL: ${pnl:.2f} ({pnl_pct:+.1f}%)")
                    self._cancel_remaining_sos(deal)
                    send_telegram(
                        f"✅ <b>{self.symbol} TP HIT {direction}</b>\n"
                        f"PnL: <b>${pnl:.2f} ({pnl_pct:+.1f}%)</b>\n"
                        f"SOs: {deal.safety_orders_filled}/{self.MAX_SOS}"
                    )
                    deal.closed = True
                    deal.close_price = fill_price
                    deal.close_time = datetime.now(timezone.utc).isoformat()
                    deal.realized_pnl = pnl
                    self.total_pnl += pnl
                    self.deals_completed += 1
                    self._set_deal(direction, None)
                    return True
            except Exception as e:
                print(f"  [{self.symbol}] TP check error: {e}")

        # Check SOs
        filled_ids = []
        for oid in list(deal.safety_order_ids):
            try:
                info = self.api.query_order(self.symbol, oid)
                if info["status"] == "FILLED":
                    fill_price = float(info.get("avgPrice", info.get("price", 0)))
                    fill_qty = float(info.get("executedQty", 0))
                    cost = fill_price * fill_qty
                    deal.add_fill(fill_price, fill_qty, cost)
                    filled_ids.append(oid)
                    print(f"  📉 [{self.symbol}] {direction} SO#{deal.safety_orders_filled} @ ${fill_price:.4f}")
                    send_telegram(
                        f"📉 <b>{self.symbol} SO#{deal.safety_orders_filled} {direction}</b>\n"
                        f"Avg: ${deal.avg_entry:.4f} | TP: ${deal.tp_price(self.current_tp_pct):.4f}"
                    )
            except Exception:
                pass

        for oid in filled_ids:
            deal.safety_order_ids.remove(oid)

        if filled_ids:
            self._update_tp_order(deal)

        return False

    def _dry_run_check(self):
        for deal in list(self._active_deals()):
            direction = deal.direction
            # Check SOs
            for n in range(deal.safety_orders_filled + 1, self.MAX_SOS + 1):
                so_p = self.so_price(deal.entry_price, n, direction)
                triggered = (direction == "LONG" and self.current_price <= so_p) or \
                            (direction == "SHORT" and self.current_price >= so_p)
                if triggered:
                    bo_usd = self.base_order_usd()
                    size_usd = self.so_qty(bo_usd, n)
                    qty = self.round_qty(size_usd / so_p)
                    deal.add_fill(so_p, qty, size_usd)
                    print(f"  📉 [{self.symbol}] [DRY] {direction} SO#{deal.safety_orders_filled} @ ${so_p:.4f}")
                else:
                    break
            # Check TP
            tp = deal.tp_price(self.current_tp_pct)
            tp_hit = (direction == "LONG" and self.current_price >= tp) or \
                     (direction == "SHORT" and self.current_price <= tp)
            if tp_hit:
                pnl = self._calc_pnl(tp, deal.total_qty, deal.total_cost, direction)
                print(f"  ✅ [{self.symbol}] [DRY] TP {direction} @ ${tp:.4f} | PnL: ${pnl:.2f}")
                self.total_pnl += pnl
                self.deals_completed += 1
                self._set_deal(direction, None)

    def check_position_sync(self):
        """Reconcile deal state with exchange position."""
        if self.dry_run:
            return
        if not self.long_deal and not self.short_deal:
            return
        try:
            positions = self.api.position_risk(self.symbol)
            for p in positions:
                if p["symbol"] != self.symbol:
                    continue
                pos_amt = float(p.get("positionAmt", 0))
                pos_side = p.get("positionSide", "BOTH")

                if pos_side == "BOTH":
                    if pos_amt == 0:
                        if self.long_deal and not self.short_deal:
                            self._cancel_remaining_sos(self.long_deal)
                            self.long_deal = None
                        elif self.short_deal and not self.long_deal:
                            self._cancel_remaining_sos(self.short_deal)
                            self.short_deal = None
                    elif pos_amt > 0 and self.long_deal and self.short_deal:
                        if abs(pos_amt - self.long_deal.total_qty) < 0.01:
                            self._cancel_remaining_sos(self.short_deal)
                            self.short_deal = None
                    elif pos_amt < 0 and self.long_deal and self.short_deal:
                        if abs(abs(pos_amt) - self.short_deal.total_qty) < 0.01:
                            self._cancel_remaining_sos(self.long_deal)
                            self.long_deal = None
        except Exception as e:
            print(f"  [{self.symbol}] Position sync error: {e}")

    def close_all(self):
        """Cancel all orders and close position for this symbol."""
        if self.dry_run:
            self.long_deal = None
            self.short_deal = None
            return
        try:
            self.api.cancel_all_orders(self.symbol)
        except Exception:
            pass
        try:
            positions = self.api.position_risk(self.symbol)
            for p in positions:
                if p["symbol"] == self.symbol:
                    amt = float(p.get("positionAmt", 0))
                    pos_side = p.get("positionSide", "BOTH")
                    if amt > 0:
                        self.api.place_order(self.symbol, "SELL", "MARKET", amt, reduce_only=True)
                    elif amt < 0:
                        self.api.place_order(self.symbol, "BUY", "MARKET", abs(amt), reduce_only=True)
        except Exception as e:
            print(f"  [{self.symbol}] Close position failed: {e}")
        self.long_deal = None
        self.short_deal = None

    def run_cycle(self):
        """Run one trading cycle for this coin."""
        # Detect regime + price
        self.current_regime = self.detect_regime()

        # If EXTREME regime, don't open new deals
        if self.current_regime == "EXTREME":
            # Still check existing orders
            self.check_orders()
            if not self.dry_run:
                self.check_position_sync()
            return

        # Update adaptive TP/deviation
        self.update_adaptive_tp()

        # Check existing orders
        self.check_orders()
        if not self.dry_run:
            self.check_position_sync()

        # Don't open new deals if winding down
        if self.status == "winding_down":
            return

        # Open deals based on regime allocation
        long_alloc, short_alloc = self.get_regime_alloc()

        if not self.long_deal and long_alloc > 0:
            self.open_deal("LONG", long_alloc)
        if not self.short_deal and short_alloc > 0:
            self.open_deal("SHORT", short_alloc)

    def to_state_dict(self) -> dict:
        return {
            "symbol": self.symbol,
            "alloc_capital": self.alloc_capital,
            "alloc_pct": self.alloc_pct,
            "scanner_score": self.scanner_score,
            "long_deal": self.long_deal.to_dict() if self.long_deal else None,
            "short_deal": self.short_deal.to_dict() if self.short_deal else None,
            "deal_counter": self.deal_counter,
            "deals_completed": self.deals_completed,
            "total_pnl": self.total_pnl,
            "current_regime": self.current_regime,
            "current_price": self.current_price,
            "current_tp_pct": self.current_tp_pct,
            "current_dev_pct": self.current_dev_pct,
            "current_atr_pct": self.current_atr_pct,
            "status": self.status,
            "added_time": self.added_time,
            "wind_down_start": self.wind_down_start,
            "_trend_bullish": self._trend_bullish,
        }

    def load_from_state(self, s: dict):
        self.alloc_capital = s.get("alloc_capital", self.alloc_capital)
        self.alloc_pct = s.get("alloc_pct", self.alloc_pct)
        self.scanner_score = s.get("scanner_score", self.scanner_score)
        self.long_deal = LiveDeal.from_dict(s["long_deal"]) if s.get("long_deal") else None
        self.short_deal = LiveDeal.from_dict(s["short_deal"]) if s.get("short_deal") else None
        self.deal_counter = s.get("deal_counter", 0)
        self.deals_completed = s.get("deals_completed", 0)
        self.total_pnl = s.get("total_pnl", 0.0)
        self.current_regime = s.get("current_regime", "UNKNOWN")
        self.current_price = s.get("current_price", 0.0)
        self.current_tp_pct = s.get("current_tp_pct", self.TP_PCT)
        self.current_dev_pct = s.get("current_dev_pct", self.DEVIATION_PCT)
        self.current_atr_pct = s.get("current_atr_pct", 0.0)
        self.status = s.get("status", "active")
        self.added_time = s.get("added_time", time.time())
        self.wind_down_start = s.get("wind_down_start")
        self._trend_bullish = s.get("_trend_bullish", True)

    def to_status_dict(self) -> dict:
        long_alloc, short_alloc = self.get_regime_alloc()
        return {
            "symbol": self.symbol,
            "alloc_pct": round(self.alloc_pct * 100, 1),
            "alloc_capital": round(self.alloc_capital, 2),
            "regime": self.current_regime,
            "trend_direction": "bullish" if self._trend_bullish else "bearish",
            "regime_alloc": {"long": long_alloc, "short": short_alloc},
            "scanner_score": self.scanner_score,
            "status": self.status,
            "long_deal": self.long_deal.to_dict() if self.long_deal else None,
            "short_deal": self.short_deal.to_dict() if self.short_deal else None,
            "adaptive_tp": {
                "current_tp_pct": round(self.current_tp_pct, 3),
                "current_dev_pct": round(self.current_dev_pct, 3),
                "atr_pct": round(self.current_atr_pct, 4),
            },
            "pnl": round(self.total_pnl, 2),
            "deals_completed": self.deals_completed,
        }


class PortfolioManager:
    """Manages multiple CoinSlots with scanner-based rotation."""

    def __init__(self, api: AsterAPI, max_coins: int = MAX_COINS,
                 total_capital: float = None, leverage: int = 1,
                 dry_run: bool = False, scanner_interval: int = SCANNER_INTERVAL_CYCLES):
        self.api = api
        self.max_coins = max_coins
        self.total_capital = total_capital
        self.leverage = leverage
        self.dry_run = dry_run
        self.scanner_interval = scanner_interval

        self.slots: Dict[str, CoinSlot] = {}
        self.rotation_history: List[dict] = []
        self.cycle_count = 0
        self.scanner_last_run: Optional[str] = None
        self.scanner_next_run: Optional[str] = None
        self._running = False
        self.start_time = ""
        self.consecutive_errors = 0
        self.halted = False
        self.halt_reason = ""

    def _normalize_symbol(self, symbol: str) -> str:
        """Convert scanner format (HYPE/USDT) to exchange format (HYPEUSDT)."""
        return symbol.replace("/", "")

    def _scanner_symbol(self, symbol: str) -> str:
        """Convert exchange format (HYPEUSDT) to scanner format (HYPE/USDT)."""
        if "/" in symbol:
            return symbol
        if symbol.endswith("USDT"):
            return symbol[:-4] + "/USDT"
        return symbol

    def add_coin(self, symbol: str, alloc_pct: float, scanner_score: float = 0.0, reason: str = "manual"):
        """Add a new coin slot."""
        symbol = self._normalize_symbol(symbol)
        if symbol in self.slots:
            print(f"  [{symbol}] Already in portfolio")
            return

        alloc_capital = (self.total_capital or 0) * alloc_pct * (1 - CAPITAL_RESERVE_PCT)
        slot = CoinSlot(
            api=self.api, symbol=symbol, alloc_capital=alloc_capital,
            alloc_pct=alloc_pct, scanner_score=scanner_score,
            leverage=self.leverage, dry_run=self.dry_run,
        )

        # Set leverage
        if not self.dry_run:
            try:
                self.api.set_leverage(symbol, self.leverage)
            except Exception as e:
                print(f"  [{symbol}] Set leverage failed: {e}")

        self.slots[symbol] = slot
        self.rotation_history.append({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "action": "added", "symbol": symbol, "reason": reason,
        })
        print(f"  ➕ Added {symbol} (alloc: {alloc_pct:.0%}, capital: ${alloc_capital:.2f}, score: {scanner_score})")
        send_telegram(f"➕ <b>Portfolio: Added {symbol}</b>\nAlloc: {alloc_pct:.0%} (${alloc_capital:.2f})\nScore: {scanner_score}\nReason: {reason}")

    def remove_coin(self, symbol: str, reason: str = "manual"):
        """Immediately close and remove a coin slot."""
        symbol = self._normalize_symbol(symbol)
        if symbol not in self.slots:
            return
        slot = self.slots[symbol]
        slot.close_all()
        del self.slots[symbol]
        self.rotation_history.append({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "action": "removed", "symbol": symbol, "reason": reason,
        })
        print(f"  ➖ Removed {symbol} ({reason})")
        send_telegram(f"➖ <b>Portfolio: Removed {symbol}</b>\nReason: {reason}\nPnL: ${slot.total_pnl:.2f}")

    def wind_down_coin(self, symbol: str, reason: str = "rotation"):
        """Mark coin for wind-down — no new deals, wait for existing to close."""
        symbol = self._normalize_symbol(symbol)
        if symbol not in self.slots:
            return
        slot = self.slots[symbol]
        slot.status = "winding_down"
        slot.wind_down_start = time.time()
        print(f"  ⏳ {symbol} winding down ({reason})")
        send_telegram(f"⏳ <b>{symbol} winding down</b>\nReason: {reason}")

    def _check_wind_downs(self):
        """Check winding-down coins — force close if timed out or deals done."""
        for symbol in list(self.slots.keys()):
            slot = self.slots[symbol]
            if slot.status != "winding_down":
                continue

            if not slot.has_open_deals():
                self.remove_coin(symbol, reason="wind_down_complete")
                continue

            if slot.wind_down_start and (time.time() - slot.wind_down_start) > WIND_DOWN_TIMEOUT_S:
                print(f"  ⏰ {symbol} wind-down timeout — force closing")
                self.remove_coin(symbol, reason="wind_down_timeout")

    def rebalance(self, scanner_results: list):
        """Adjust allocations and rotate coins based on scanner results."""
        if not scanner_results:
            return

        # Normalize symbols
        scored = []
        for r in scanner_results:
            sym = self._normalize_symbol(r["symbol"])
            scored.append({"symbol": sym, "score": r["score"]})

        # Filter out coins below minimum score threshold
        scored = [s for s in scored if s["score"] > 0]

        # Determine target coins (top N by score)
        target_coins = scored[:self.max_coins]
        target_symbols = {s["symbol"] for s in target_coins}

        # Current active (non-winding-down) symbols
        current_symbols = {s for s, slot in self.slots.items() if slot.status == "active"}

        # Coins to potentially remove (in current but not in target)
        to_remove = current_symbols - target_symbols
        # Coins to potentially add (in target but not in current)
        to_add = target_symbols - current_symbols - {s for s, slot in self.slots.items() if slot.status == "winding_down"}

        # Only remove if held long enough
        for sym in to_remove:
            slot = self.slots.get(sym)
            if slot and (time.time() - slot.added_time) < MIN_HOLD_HOURS * 3600:
                print(f"  [{sym}] Held < {MIN_HOLD_HOURS}h — skipping rotation")
                continue
            # Check if replacement scores 20%+ better
            current_score = slot.scanner_score if slot else 0
            best_replacement = next((s for s in scored if s["symbol"] not in current_symbols), None)
            if best_replacement and current_score > 0:
                improvement = (best_replacement["score"] - current_score) / current_score
                if improvement < 0.20:
                    print(f"  [{sym}] Replacement only +{improvement:.0%} — below 20% threshold")
                    continue
            self.wind_down_coin(sym, reason=f"scanner_rotation")

        # Calculate allocations for target coins
        total_score = sum(s["score"] for s in target_coins)
        if total_score <= 0:
            return

        for tc in target_coins:
            alloc_pct = tc["score"] / total_score
            if alloc_pct < MIN_ALLOC_PCT:
                alloc_pct = 0  # too small
                continue

            sym = tc["symbol"]
            alloc_capital = (self.total_capital or 0) * alloc_pct * (1 - CAPITAL_RESERVE_PCT)

            if sym in self.slots and self.slots[sym].status == "active":
                # Update existing
                slot = self.slots[sym]
                slot.alloc_pct = alloc_pct
                slot.alloc_capital = alloc_capital
                slot.scanner_score = tc["score"]
            elif sym in to_add:
                # Add new
                self.add_coin(sym, alloc_pct, scanner_score=tc["score"], reason="scanner_rotation")

    def run_scanner(self):
        """Run the coin scanner and apply results."""
        print(f"\n  🔍 Running scanner...")
        self.scanner_last_run = datetime.now(timezone.utc).isoformat()

        try:
            # Run scanner as subprocess
            python = sys.executable
            result = subprocess.run(
                [python, "-m", "trading.run_scanner"],
                capture_output=True, text=True, timeout=300,
                cwd=str(Path(__file__).parent.parent),
                encoding='utf-8', errors='replace',
            )
            if result.returncode != 0:
                print(f"  Scanner failed: {result.stderr[:500]}")
                return

            # Read recommendation
            rec_path = LIVE_DIR / "scanner_recommendation.json"
            if not rec_path.exists():
                print("  Scanner produced no recommendation")
                return

            with open(rec_path) as f:
                rec = json.load(f)

            print(f"  Scanner result: {rec.get('action')} | Best: {rec.get('best_coin')} ({rec.get('best_score')})")

            # Apply top coins
            top = rec.get("top_5", [])
            if top:
                self.rebalance(top)

        except Exception as e:
            print(f"  Scanner error: {e}")
            traceback.print_exc()

        # Schedule next run
        next_time = datetime.now(timezone.utc) + timedelta(seconds=self.scanner_interval * CYCLE_SLEEP)
        self.scanner_next_run = next_time.isoformat()

    def save_state(self):
        state = {
            "slots": {sym: slot.to_state_dict() for sym, slot in self.slots.items()},
            "rotation_history": self.rotation_history[-50:],  # keep last 50
            "cycle_count": self.cycle_count,
            "scanner_last_run": self.scanner_last_run,
            "scanner_next_run": self.scanner_next_run,
            "total_capital": self.total_capital,
            "max_coins": self.max_coins,
            "halted": self.halted,
            "halt_reason": self.halt_reason,
            "start_time": self.start_time,
        }
        with open(LIVE_DIR / "portfolio_state.json", "w") as f:
            json.dump(state, f, indent=2)

    def load_state(self):
        path = LIVE_DIR / "portfolio_state.json"
        if not path.exists():
            return
        try:
            with open(path) as f:
                s = json.load(f)

            self.cycle_count = s.get("cycle_count", 0)
            self.scanner_last_run = s.get("scanner_last_run")
            self.scanner_next_run = s.get("scanner_next_run")
            self.rotation_history = s.get("rotation_history", [])
            self.halted = s.get("halted", False)
            self.halt_reason = s.get("halt_reason", "")
            self.start_time = s.get("start_time", "")

            if s.get("total_capital"):
                self.total_capital = s["total_capital"]

            for sym, slot_state in s.get("slots", {}).items():
                slot = CoinSlot(
                    api=self.api, symbol=sym,
                    alloc_capital=slot_state.get("alloc_capital", 0),
                    alloc_pct=slot_state.get("alloc_pct", 0),
                    scanner_score=slot_state.get("scanner_score", 0),
                    leverage=self.leverage, dry_run=self.dry_run,
                )
                slot.load_from_state(slot_state)
                self.slots[sym] = slot

            print(f"  ♻️  Loaded portfolio state: {len(self.slots)} coins, cycle {self.cycle_count}")
            for sym, slot in self.slots.items():
                long_str = f"L#{slot.long_deal.deal_id}" if slot.long_deal else "—"
                short_str = f"S#{slot.short_deal.deal_id}" if slot.short_deal else "—"
                print(f"    {sym}: {slot.status} | {long_str} {short_str} | PnL: ${slot.total_pnl:.2f}")

        except Exception as e:
            print(f"  [WARN] Portfolio state load failed: {e}")

    def write_status(self):
        try:
            equity = self.api.usdt_equity() if not self.dry_run else (self.total_capital or 1000)
            available = self.api.usdt_available() if not self.dry_run else 0
        except Exception:
            equity = self.total_capital or 0
            available = 0

        total_pnl = sum(s.total_pnl for s in self.slots.values())
        start_eq = self.total_capital or equity

        status = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "mode": "portfolio",
            "total_equity": round(equity, 2),
            "total_pnl": round(total_pnl, 2),
            "total_pnl_pct": round(total_pnl / start_eq * 100, 2) if start_eq > 0 else 0,
            "available_balance": round(available, 2),
            "capital_reserve_pct": round(CAPITAL_RESERVE_PCT * 100),
            "max_coins": self.max_coins,
            "active_coins": len([s for s in self.slots.values() if s.status == "active"]),
            "scanner_last_run": self.scanner_last_run,
            "scanner_next_run": self.scanner_next_run,
            "coins": {sym: slot.to_status_dict() for sym, slot in self.slots.items()},
            "rotation_history": self.rotation_history[-20:],
        }
        with open(LIVE_DIR / "portfolio_status.json", "w") as f:
            json.dump(status, f, indent=2)

        # Append to history
        self._write_history(status)

    def _write_history(self, status: dict):
        history_path = LIVE_DIR / "history.json"
        try:
            if history_path.exists():
                with open(history_path) as f:
                    history = json.load(f)
            else:
                history = []

            coins_summary = ", ".join(
                f"{sym[:4]}({'L' if s.long_deal else ''}{'S' if s.short_deal else ''})"
                for sym, s in self.slots.items()
            )
            history.append({
                "t": status["timestamp"],
                "eq": status["total_equity"],
                "pnl": status["total_pnl"],
                "coins": len(self.slots),
                "summary": coins_summary,
                "mode": "portfolio",
            })
            if len(history) > 2000:
                history = history[-2000:]
            with open(history_path, "w") as f:
                json.dump(history, f)
        except Exception:
            pass

    def _get_equity(self) -> float:
        if self.dry_run:
            return self.total_capital or 1000
        try:
            return self.api.usdt_equity()
        except Exception:
            return self.total_capital or 0

    def _check_kill_switches(self) -> bool:
        """Portfolio-level kill switches."""
        equity = self._get_equity()
        if self.total_capital and self.total_capital > 0:
            loss_pct = (self.total_capital - equity) / self.total_capital * 100
            if loss_pct >= 25:
                self._trigger_halt(f"Portfolio drawdown {loss_pct:.1f}% >= 25%")
                return True
        return False

    def _trigger_halt(self, reason: str):
        self.halted = True
        self.halt_reason = reason
        print(f"\n  🚨 PORTFOLIO HALT: {reason}")
        for sym, slot in self.slots.items():
            slot.close_all()
        send_telegram(f"🚨 <b>PORTFOLIO HALT</b>\n{reason}\nAll positions closed.")

    def start(self):
        """Main portfolio loop."""
        self._running = True
        if not self.start_time:
            self.start_time = datetime.now(timezone.utc).isoformat()

        # Init capital
        if self.total_capital is None:
            if self.dry_run:
                self.total_capital = 1000
            else:
                self.total_capital = self.api.usdt_balance()

        # Load saved state
        self.load_state()

        # Update capital to current equity
        eq = self._get_equity()
        if eq > 0:
            self.total_capital = eq

        mode = "DRY RUN" if self.dry_run else "LIVE"
        print(f"\n  🚀 Portfolio Manager [{mode}] started!")
        print(f"  Capital: ${self.total_capital:.2f} | Max coins: {self.max_coins} | Reserve: {CAPITAL_RESERVE_PCT:.0%}")
        print(f"  Scanner interval: {self.scanner_interval} cycles (~{self.scanner_interval * CYCLE_SLEEP / 3600:.1f}h)")

        send_telegram(
            f"🚀 <b>Portfolio Manager [{mode}]</b>\n"
            f"Capital: ${self.total_capital:.2f}\n"
            f"Max coins: {self.max_coins}\n"
            f"Active: {len(self.slots)} coins"
        )

        # Initial scan if no coins loaded
        if not self.slots:
            self.run_scanner()

        while self._running:
            try:
                self.cycle_count += 1

                # Connectivity
                if not self.dry_run and not self.api.ping():
                    self.consecutive_errors += 1
                    if self.consecutive_errors >= 3:
                        self._trigger_halt("3+ consecutive API errors")
                        break
                    time.sleep(10)
                    continue
                self.consecutive_errors = 0

                # Kill switches
                if self.halted:
                    print(f"  🛑 Halted: {self.halt_reason}")
                    break
                if self._check_kill_switches():
                    break

                # Update capital
                eq = self._get_equity()
                if eq > 0:
                    self.total_capital = eq
                    # Update slot allocations
                    for slot in self.slots.values():
                        slot.alloc_capital = self.total_capital * slot.alloc_pct * (1 - CAPITAL_RESERVE_PCT)

                # Run scanner periodically
                if self.cycle_count % self.scanner_interval == 0:
                    self.run_scanner()

                # Check wind-downs
                self._check_wind_downs()

                # Run each coin's cycle
                coin_summaries = []
                for sym, slot in list(self.slots.items()):
                    try:
                        slot.run_cycle()
                        trend = "▲" if slot._trend_bullish else "▼"
                        long_str = f"L#{slot.long_deal.deal_id}({slot.long_deal.safety_orders_filled}SO)" if slot.long_deal else "—"
                        short_str = f"S#{slot.short_deal.deal_id}({slot.short_deal.safety_orders_filled}SO)" if slot.short_deal else "—"
                        coin_summaries.append(f"{sym}:${slot.current_price:.3f}|{slot.current_regime[:3]}{trend}|{long_str} {short_str}")
                    except Exception as e:
                        print(f"  [{sym}] Cycle error: {e}")
                        traceback.print_exc()

                # Print summary line
                ts = datetime.now().strftime('%H:%M:%S')
                print(f"\n  [{ts}] Cycle {self.cycle_count} | Coins: {len(self.slots)} | Eq: ${self.total_capital:.2f}")
                for cs in coin_summaries:
                    print(f"    {cs}")

                # Persist
                self.save_state()
                self.write_status()

                time.sleep(CYCLE_SLEEP)

            except KeyboardInterrupt:
                break
            except Exception as e:
                self.consecutive_errors += 1
                print(f"\n  ❌ Portfolio error (#{self.consecutive_errors}): {e}")
                traceback.print_exc()
                if self.consecutive_errors >= 3:
                    self._trigger_halt(f"3+ errors: {e}")
                    break
                time.sleep(15)

        self._shutdown()

    def _shutdown(self):
        self._running = False
        print("\n  🛑 Portfolio Manager shutting down...")
        self.save_state()
        self.write_status()
        send_telegram("🛑 <b>Portfolio Manager Stopped</b>")

    def stop(self):
        self._running = False
