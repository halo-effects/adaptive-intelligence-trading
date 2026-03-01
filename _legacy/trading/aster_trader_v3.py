"""Paper Trading Bot v3 with Multi-Coin Support and Risk Profiles
Simulates trading using real market data across multiple coins simultaneously.
"""
import hashlib
import hmac
import json
import csv
import time
import os
import traceback
import urllib.parse
from datetime import datetime, timezone, timedelta
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import List, Optional, Dict, Any, Tuple

import requests
import pandas as pd
import numpy as np

# Import regime detection from the live bot
try:
    from .regime_detector import classify_regime_v2, is_martingale_friendly_v2
except ImportError:
    try:
        from regime_detector import classify_regime_v2, is_martingale_friendly_v2
    except ImportError:
        # Fallback for standalone testing
        def classify_regime_v2(df, timeframe):
            return pd.Series(["UNKNOWN"] * len(df))
        def is_martingale_friendly_v2(df):
            return True

PAPER_DIR = Path(__file__).parent / "paper"
LIVE_DIR = Path(__file__).parent / "live"
PAPER_DIR.mkdir(exist_ok=True)

# Telegram config (same as live)
TG_TOKEN = "8528958079:AAF90HSJ5Ck1urUydzS5CUvyf2EEeB7LUwc"
TG_CHAT_ID = "5221941584"
TG_ENABLED = True

# Market rules (defaults for USDT pairs)
DEFAULT_TICK_SIZE = 0.001
DEFAULT_STEP_SIZE = 0.01
DEFAULT_MIN_QTY = 0.01
DEFAULT_MIN_NOTIONAL = 5.0
DEFAULT_PRICE_PRECISION = 3
DEFAULT_QTY_PRECISION = 2

# Multi-coin constants
MAX_COINS_DEFAULT = 3
CAPITAL_RESERVE_PCT = 0.10  # 10% always kept free
MIN_ALLOC_PCT = 0.15        # minimum 15% allocation per coin

# Regime-based capital allocation
REGIME_ALLOC = {
    "ACCUMULATION": (0.70, 0.30),
    "CHOPPY": (0.50, 0.50),
    "RANGING": (0.50, 0.50),
    "DISTRIBUTION": (0.30, 0.70),
    "MILD_TREND": (0.60, 0.40),
    "TRENDING": (0.75, 0.25),
    "EXTREME": (0.0, 0.0),
    "BREAKOUT_WARNING": (0.0, 0.0),
    "UNKNOWN": (0.50, 0.50),
}
DIRECTIONAL_REGIMES = {"TRENDING", "MILD_TREND", "DISTRIBUTION"}

# Risk Profile Definitions
PROFILES = {
    "low": {
        "name": "Low Risk",
        "leverage": 1,
        "max_safety_orders": 8,
        "so_volume_mult": 2.0,
        "base_order_pct": 4.0,
        "capital_reserve": 10.0,
        "tp_range": (0.6, 2.5),
        "deviation_range": (1.2, 4.0),
        "extreme_allocation": (0, 0),  # Halt in extreme
        "max_directional_bias": (75, 25),
    },
    "medium": {
        "name": "Medium Risk", 
        "leverage": 2,
        "max_safety_orders": 12,
        "so_volume_mult": 2.5,
        "base_order_pct": 6.0,
        "capital_reserve": 5.0,
        "tp_range": (0.4, 2.0),
        "deviation_range": (0.8, 3.0),
        "extreme_allocation": (20, 20),  # Reduce in extreme
        "max_directional_bias": (85, 15),
    },
    "high": {
        "name": "High Risk",
        "leverage": 5,
        "max_safety_orders": 16,
        "so_volume_mult": 3.0,
        "base_order_pct": 8.0,
        "capital_reserve": 2.0,
        "tp_range": (0.2, 1.5),
        "deviation_range": (0.5, 2.0),
        "extreme_allocation": (40, 40),  # Continue in extreme
        "max_directional_bias": (95, 5),
    }
}


def normalize_symbol(symbol: str) -> str:
    """Normalize symbol format."""
    if "/" in symbol:
        return symbol.replace("/", "")
    return symbol


def round_price(p: float, precision: int = DEFAULT_PRICE_PRECISION, tick_size: float = DEFAULT_TICK_SIZE) -> float:
    return round(round(p / tick_size) * tick_size, precision)


def round_qty(q: float, precision: int = DEFAULT_QTY_PRECISION, step_size: float = DEFAULT_STEP_SIZE) -> float:
    return round(round(q / step_size) * step_size, precision)


def send_telegram(msg: str):
    if not TG_ENABLED:
        return
    try:
        # Prefix with [PAPER] to distinguish from live
        paper_msg = f"[PAPER] {msg}"
        requests.post(
            f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage",
            json={"chat_id": TG_CHAT_ID, "text": paper_msg, "parse_mode": "HTML"},
            timeout=10,
        )
    except Exception:
        pass


class AsterAPI:
    """Same as live bot but only used for reading data."""
    
    def __init__(self, base_url: str = "https://fapi.asterdex.com"):
        self.base_url = base_url.rstrip("/")
        self.api_key = os.environ.get("ASTER_API_KEY", "")
        self.api_secret = os.environ.get("ASTER_API_SECRET", "")
        # Fallback: read from Windows registry
        if not self.api_key:
            try:
                import winreg
                with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r'Environment') as k:
                    self.api_key = winreg.QueryValueEx(k, 'ASTER_API_KEY')[0]
                    self.api_secret = winreg.QueryValueEx(k, 'ASTER_API_SECRET')[0]
            except Exception:
                pass
        self.session = requests.Session()
        self.session.headers.update({"X-MBX-APIKEY": self.api_key})

    def ping(self) -> bool:
        try:
            r = self.session.get(f"{self.base_url}/fapi/v1/ping", timeout=5)
            r.raise_for_status()
            return True
        except Exception as e:
            print(f"    [PING] {e}")
            return False

    def klines(self, symbol: str, interval: str, limit: int = 300) -> pd.DataFrame:
        data = self.session.get(
            f"{self.base_url}/fapi/v1/klines",
            params={"symbol": symbol, "interval": interval, "limit": limit},
            timeout=15
        ).json()
        
        df = pd.DataFrame(data, columns=[
            "timestamp", "open", "high", "low", "close", "volume",
            "close_time", "quote_vol", "trades", "taker_buy_vol", "taker_buy_quote", "ignore"
        ])
        for c in ["open", "high", "low", "close", "volume"]:
            df[c] = df[c].astype(float)
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms", utc=True)
        return df[["timestamp", "open", "high", "low", "close", "volume"]]


@dataclass
class VirtualDeal:
    """Virtual deal for paper trading."""
    deal_id: int
    symbol: str
    entry_price: float
    entry_qty: float
    entry_cost: float
    entry_time: str
    direction: str = "LONG"
    safety_orders_filled: int = 0
    virtual_so_levels: List[Dict] = field(default_factory=list)  # [{level: n, price: float, qty: float, size_usd: float}]
    tp_price: float = 0.0
    total_qty: float = 0.0
    total_cost: float = 0.0
    avg_entry: float = 0.0
    closed: bool = False
    close_price: Optional[float] = None
    close_time: Optional[str] = None
    realized_pnl: float = 0.0

    def __post_init__(self):
        if self.total_qty == 0:
            self.total_qty = self.entry_qty
            self.total_cost = self.entry_cost
            self.avg_entry = self.entry_price

    def add_fill(self, price: float, qty: float, cost: float):
        """Simulate SO fill."""
        self.total_qty += qty
        self.total_cost += cost
        self.avg_entry = self.total_cost / self.total_qty if self.total_qty > 0 else 0
        self.safety_orders_filled += 1

    def calc_tp_price(self, tp_pct: float) -> float:
        """Calculate TP price for current avg entry."""
        if self.direction == "SHORT":
            return round_price(self.avg_entry * (1 - tp_pct / 100))
        return round_price(self.avg_entry * (1 + tp_pct / 100))

    def to_dict(self) -> dict:
        return {
            "deal_id": self.deal_id,
            "symbol": self.symbol,
            "entry_price": self.entry_price,
            "entry_qty": self.entry_qty,
            "entry_cost": self.entry_cost,
            "entry_time": self.entry_time,
            "direction": self.direction,
            "safety_orders_filled": self.safety_orders_filled,
            "virtual_so_levels": self.virtual_so_levels,
            "tp_price": self.tp_price,
            "total_qty": self.total_qty,
            "total_cost": self.total_cost,
            "avg_entry": self.avg_entry,
            "closed": self.closed,
            "close_price": self.close_price,
            "close_time": self.close_time,
            "realized_pnl": self.realized_pnl,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "VirtualDeal":
        return cls(**d)


class VirtualCoinSlot:
    """Virtual coin slot for paper trading - manages one coin's trading."""
    
    def __init__(self, symbol: str, alloc_capital: float, alloc_pct: float, 
                 scanner_score: float, profile_params: dict, api: AsterAPI):
        self.symbol = symbol
        self.alloc_capital = alloc_capital
        self.alloc_pct = alloc_pct
        self.scanner_score = scanner_score
        self.profile_params = profile_params
        self.api = api
        
        # Trading state
        self.long_deal: Optional[VirtualDeal] = None
        self.short_deal: Optional[VirtualDeal] = None
        self.deal_counter = 0
        self.deals_completed = 0
        self.total_pnl = 0.0
        
        # Market state
        self.current_price = 0.0
        self.current_regime = "UNKNOWN"
        self.current_tp_pct = (profile_params["tp_range"][0] + profile_params["tp_range"][1]) / 2
        self.current_dev_pct = (profile_params["deviation_range"][0] + profile_params["deviation_range"][1]) / 2
        self.current_atr_pct = 0.0
        self._trend_bullish = True
        self._last_klines_df: Optional[pd.DataFrame] = None
        
        # Status
        self.status = "active"  # active, winding_down, closed
        self.added_time = time.time()
        
    def _get_deal(self, direction: str) -> Optional[VirtualDeal]:
        return self.long_deal if direction == "LONG" else self.short_deal
        
    def _set_deal(self, direction: str, deal: Optional[VirtualDeal]):
        if direction == "LONG":
            self.long_deal = deal
        else:
            self.short_deal = deal
            
    def detect_regime(self) -> str:
        """Detect market regime for this specific coin."""
        try:
            df = self.api.klines(self.symbol, "5m", limit=300)
            if len(df) < 100:
                return "UNKNOWN"
            self.current_price = float(df["close"].iloc[-1])
            self._last_klines_df = df
            regimes = classify_regime_v2(df, "5m")
            
            # Detect trend direction via SMA50
            sma50 = df["close"].rolling(50).mean().iloc[-1]
            self._trend_bullish = self.current_price >= sma50
            
            return regimes.iloc[-1]
        except Exception as e:
            print(f"  [WARN] {self.symbol} regime detection error: {e}")
            return self.current_regime
            
    def get_regime_alloc(self) -> Tuple[float, float]:
        """Get long/short allocation for current regime."""
        long_alloc, short_alloc = REGIME_ALLOC.get(self.current_regime, (0.5, 0.5))
        
        # Handle EXTREME regime per profile
        if self.current_regime == "EXTREME":
            extreme_alloc = self.profile_params["extreme_allocation"]
            long_alloc, short_alloc = extreme_alloc[0] / 100, extreme_alloc[1] / 100
            
        # Directional awareness
        if self.current_regime in DIRECTIONAL_REGIMES and not self._trend_bullish:
            long_alloc, short_alloc = short_alloc, long_alloc
            
        # Apply max directional bias
        max_bias = self.profile_params["max_directional_bias"]
        max_long, max_short = max_bias[0] / 100, max_bias[1] / 100
        if long_alloc > max_long:
            excess = long_alloc - max_long
            long_alloc = max_long
            short_alloc = min(short_alloc + excess, 1.0)
        if short_alloc > max_short:
            excess = short_alloc - max_short
            short_alloc = max_short  
            long_alloc = min(long_alloc + excess, 1.0)
            
        return long_alloc, short_alloc
        
    def create_so_levels(self, deal: VirtualDeal):
        """Create virtual SO levels for a deal."""
        deal.virtual_so_levels = []
        
        base_order_usd = self.profile_params["base_order_pct"] / 100 * self.alloc_capital
        
        for n in range(1, self.profile_params["max_safety_orders"] + 1):
            dev_range = self.profile_params["deviation_range"]
            deviation_pct = dev_range[0] + (dev_range[1] - dev_range[0]) * min(n / self.profile_params["max_safety_orders"], 1.0)
            
            if deal.direction == "LONG":
                so_price = round_price(deal.entry_price * (1 - (deviation_pct * n) / 100))
            else:
                so_price = round_price(deal.entry_price * (1 + (deviation_pct * n) / 100))
                
            size_usd = base_order_usd * (self.profile_params["so_volume_mult"] ** n)
            qty = round_qty(size_usd / so_price)
            
            if qty < DEFAULT_MIN_QTY or qty * so_price < DEFAULT_MIN_NOTIONAL:
                break
                
            deal.virtual_so_levels.append({
                "level": n,
                "price": so_price,
                "qty": qty,
                "size_usd": size_usd,
                "filled": False
            })
            
    def open_deal(self, direction: str) -> bool:
        """Open a new virtual deal. Returns True if successful."""
        if self.current_price <= 0:
            return False
            
        base_order_usd = self.profile_params["base_order_pct"] / 100 * self.alloc_capital
        if base_order_usd < DEFAULT_MIN_NOTIONAL:
            return False
            
        # Apply small slippage (0.01%) to simulate realistic entry
        slippage = 0.0001 if direction == "LONG" else -0.0001
        entry_price = round_price(self.current_price * (1 + slippage))
        
        qty = round_qty(base_order_usd / entry_price)
        if qty < DEFAULT_MIN_QTY:
            return False
            
        cost = entry_price * qty
        self.deal_counter += 1
        now_str = datetime.now(timezone.utc).isoformat()
        
        deal = VirtualDeal(
            deal_id=self.deal_counter,
            symbol=self.symbol,
            entry_price=entry_price,
            entry_qty=qty,
            entry_cost=cost,
            entry_time=now_str,
            direction=direction
        )
        
        # Create SO levels
        self.create_so_levels(deal)
        
        # Set initial TP
        tp_range = self.profile_params["tp_range"]
        tp_pct = tp_range[0] + (tp_range[1] - tp_range[0]) * 0.5  # Mid-range
        deal.tp_price = deal.calc_tp_price(tp_pct)
        self.current_tp_pct = tp_pct
        
        self._set_deal(direction, deal)
        
        dir_label = "[LONG]" if direction == "LONG" else "[SHORT]"
        print(f"  {dir_label} {self.symbol} Deal #{self.deal_counter}: {qty} @ ${entry_price:.3f}")
        
        return True
        
    def check_deals_for_fills(self) -> List[str]:
        """Check both deals for SO fills and TP hits. Returns list of closed deal IDs."""
        if self.current_price <= 0:
            return []
            
        closed_deals = []
        
        for direction in ["LONG", "SHORT"]:
            deal = self._get_deal(direction)
            if not deal or deal.closed:
                continue
                
            # Check SO fills (in order from shallow to deep)
            for so_level in deal.virtual_so_levels:
                if so_level["filled"]:
                    continue
                    
                # Check if price crossed SO level
                so_triggered = False
                if direction == "LONG" and self.current_price <= so_level["price"]:
                    so_triggered = True
                elif direction == "SHORT" and self.current_price >= so_level["price"]:
                    so_triggered = True
                    
                if so_triggered:
                    # Apply slippage
                    fill_price = round_price(so_level["price"] * (1 + 0.0001))
                    fill_qty = so_level["qty"]
                    fill_cost = fill_price * fill_qty
                    
                    deal.add_fill(fill_price, fill_qty, fill_cost)
                    so_level["filled"] = True
                    
                    # Update TP price to new average
                    deal.tp_price = deal.calc_tp_price(self.current_tp_pct)
                    
                    print(f"  {self.symbol} [PAPER] {direction} SO#{deal.safety_orders_filled} filled @ ${fill_price:.3f}")
                else:
                    # SOs must fill in order, so if this one didn't trigger, stop checking deeper ones
                    break
                    
            # Check TP hit
            tp_hit = False
            if direction == "LONG" and self.current_price >= deal.tp_price:
                tp_hit = True
            elif direction == "SHORT" and self.current_price <= deal.tp_price:
                tp_hit = True
                
            if tp_hit:
                # Apply slippage
                fill_price = round_price(deal.tp_price * (1 - 0.0001 if direction == "LONG" else 1 + 0.0001))
                pnl = self._calc_pnl(fill_price, deal.total_qty, deal.total_cost, direction)
                
                deal.closed = True
                deal.close_price = fill_price
                deal.close_time = datetime.now(timezone.utc).isoformat()
                deal.realized_pnl = pnl
                
                # Update slot totals
                self.total_pnl += pnl
                self.deals_completed += 1
                
                pnl_pct = pnl / deal.total_cost * 100
                
                print(f"  {self.symbol} [PAPER] TP HIT! Deal #{deal.deal_id} {direction} @ ${fill_price:.3f}")
                print(f"    PnL: ${pnl:.2f} ({pnl_pct:+.1f}%) | SOs used: {deal.safety_orders_filled}")
                
                self._set_deal(direction, None)
                closed_deals.append(f"{direction}_{deal.deal_id}")
                
        return closed_deals
        
    def _calc_pnl(self, close_price: float, total_qty: float, total_cost: float, direction: str) -> float:
        if direction == "SHORT":
            return total_cost - (total_qty * close_price)
        else:
            return (total_qty * close_price) - total_cost
            
    def run_cycle(self):
        """Run one trading cycle for this coin."""
        # Detect regime + price
        self.current_regime = self.detect_regime()
        
        if self.current_price <= 0:
            return
            
        # Check existing deals for fills
        closed_deals = self.check_deals_for_fills()
        
        # Don't open new deals if winding down
        if self.status == "winding_down":
            return
            
        # Open deals based on regime allocation
        long_alloc, short_alloc = self.get_regime_alloc()
        
        if not self.long_deal and long_alloc > 0:
            self.open_deal("LONG")
        if not self.short_deal and short_alloc > 0:
            self.open_deal("SHORT")
            
    def to_status_dict(self) -> dict:
        long_alloc, short_alloc = self.get_regime_alloc()
        return {
            "symbol": self.symbol,
            "alloc_pct": round(self.alloc_pct * 100, 1),
            "alloc_capital": round(self.alloc_capital, 2),
            "scanner_score": self.scanner_score,
            "regime": self.current_regime,
            "trend_direction": "bullish" if self._trend_bullish else "bearish",
            "regime_alloc": {"long": long_alloc, "short": short_alloc},
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


class VirtualAccount:
    """Simulates exchange account for paper trading."""
    
    def __init__(self, initial_balance: float):
        self.balance = initial_balance
        self.start_balance = initial_balance
        self.equity = initial_balance
        
    def get_equity(self) -> float:
        """Return current equity."""
        return self.equity
        
    def get_balance(self) -> float:
        """Return available balance."""
        return self.balance


class ProfileManager:
    """Manages risk profile allocation and parameters."""
    
    def __init__(self, allocation_path: Path):
        self.allocation_path = allocation_path
        self.allocation = self._load_allocation()
        
    def _load_allocation(self) -> dict:
        """Load allocation from JSON file."""
        try:
            with open(self.allocation_path) as f:
                return json.load(f)
        except Exception as e:
            print(f"[WARN] Failed to load allocation: {e}")
            return {"low": 0, "medium": 100, "high": 0, "total_capital": 10000, "max_coins": 3}
    
    def get_active_profile(self) -> str:
        """Get the currently active profile (single profile for now)."""
        for profile, pct in self.allocation.items():
            if profile in PROFILES and pct > 0:
                return profile
        return "medium"  # Default fallback
        
    def get_max_coins(self) -> int:
        """Get max coins setting."""
        return self.allocation.get("max_coins", MAX_COINS_DEFAULT)
        
    def get_profile_capital(self, profile: str) -> float:
        """Get allocated capital for a profile."""
        pct = self.allocation.get(profile, 0)
        total = self.allocation.get("total_capital", 10000)
        return total * (pct / 100)
        
    def get_profile_params(self, profile: str) -> dict:
        """Get parameters for a profile."""
        return PROFILES.get(profile, PROFILES["medium"])
        
    def refresh_allocation(self):
        """Re-read allocation from disk."""
        old_allocation = self.allocation.copy()
        self.allocation = self._load_allocation()
        return old_allocation != self.allocation


class ScannerReader:
    """Reads scanner results from files."""
    
    @staticmethod
    def read_scanner_results() -> List[Dict]:
        """Read and combine scanner results."""
        results = []
        
        # Try primary scanner first
        rec_path = LIVE_DIR / "scanner_recommendation.json"
        if rec_path.exists():
            try:
                with open(rec_path) as f:
                    data = json.load(f)
                    top_5 = data.get("top_5", [])
                    for coin in top_5:
                        results.append({
                            "symbol": normalize_symbol(coin["symbol"]),
                            "score": coin["score"],
                            "source": "scanner_recommendation"
                        })
            except Exception as e:
                print(f"[WARN] Failed to read scanner_recommendation.json: {e}")
        
        # Try T2 scanner as fallback/supplement
        t2_path = LIVE_DIR / "scanner_t2.json"
        if t2_path.exists() and not results:
            try:
                with open(t2_path) as f:
                    data = json.load(f)
                    rankings = data.get("rankings", [])
                    for coin in rankings[:5]:  # Top 5
                        results.append({
                            "symbol": normalize_symbol(coin["symbol"]),
                            "score": coin["composite_score"],
                            "source": "scanner_t2"
                        })
            except Exception as e:
                print(f"[WARN] Failed to read scanner_t2.json: {e}")
                
        # Fallback to HYPE if no scanner data
        if not results:
            print("[WARN] No scanner data found, using fallback HYPE")
            results = [{"symbol": "HYPEUSDT", "score": 50.0, "source": "fallback"}]
            
        return results


class AsterTraderV3:
    """Multi-Coin Paper Trading Bot with Risk Profiles."""
    
    def __init__(self, timeframe: str = "5m", capital: float = 10000, profile: str = "medium"):
        self.timeframe = timeframe
        self.capital = capital
        
        self.api = AsterAPI()
        self.virtual_account = VirtualAccount(capital)
        
        # Profile management
        self.profile_manager = ProfileManager(PAPER_DIR / "allocation.json")
        
        # Multi-coin slots
        self.coin_slots: Dict[str, VirtualCoinSlot] = {}
        
        # State
        self.start_equity = capital
        self.start_time = datetime.now(timezone.utc).isoformat()
        self.cycle_count = 0
        self._running = False
        self.guardrail_events = []
        self.last_scanner_run = None
        self.scanner_interval_cycles = 480  # ~4 hours at 30s cycle
        
        print(f"Multi-coin paper trading bot initialized | Capital: ${self.capital}")
        
    def read_scanner_and_allocate(self):
        """Read scanner results and allocate capital to top coins."""
        scanner_results = ScannerReader.read_scanner_results()
        if not scanner_results:
            return
            
        active_profile = self.profile_manager.get_active_profile()
        profile_params = self.profile_manager.get_profile_params(active_profile)
        profile_capital = self.profile_manager.get_profile_capital(active_profile)
        max_coins = self.profile_manager.get_max_coins()
        
        # Filter and sort by score
        scored = [r for r in scanner_results if r["score"] > 0]
        scored.sort(key=lambda x: x["score"], reverse=True)
        
        # Take top N coins
        target_coins = scored[:max_coins]
        target_symbols = {c["symbol"] for c in target_coins}
        
        # Calculate allocations (score-proportional)
        total_score = sum(c["score"] for c in target_coins)
        if total_score <= 0:
            return
            
        # Available capital after reserve
        available_capital = profile_capital * (1 - CAPITAL_RESERVE_PCT)
        
        # Current symbols
        current_symbols = set(self.coin_slots.keys())
        
        # Remove coins no longer in target
        to_remove = current_symbols - target_symbols
        for symbol in to_remove:
            print(f"Removing {symbol} from portfolio")
            # Mark for wind down (in a real implementation, we'd gracefully close positions)
            if symbol in self.coin_slots:
                self.coin_slots[symbol].status = "winding_down"
                del self.coin_slots[symbol]
        
        # Add/update target coins
        for coin in target_coins:
            symbol = coin["symbol"]
            score = coin["score"]
            
            # Calculate allocation percentage
            alloc_pct = score / total_score
            if alloc_pct < MIN_ALLOC_PCT:
                continue  # Skip if allocation too small
                
            alloc_capital = available_capital * alloc_pct
            
            if symbol in self.coin_slots:
                # Update existing slot
                slot = self.coin_slots[symbol]
                slot.alloc_pct = alloc_pct
                slot.alloc_capital = alloc_capital
                slot.scanner_score = score
                print(f"Updated {symbol}: {alloc_pct:.1%} (${alloc_capital:.0f})")
            else:
                # Create new slot
                slot = VirtualCoinSlot(
                    symbol=symbol,
                    alloc_capital=alloc_capital,
                    alloc_pct=alloc_pct,
                    scanner_score=score,
                    profile_params=profile_params,
                    api=self.api
                )
                self.coin_slots[symbol] = slot
                print(f"Added {symbol}: {alloc_pct:.1%} (${alloc_capital:.0f})")
        
        print(f"Active coins: {list(self.coin_slots.keys())}")
        
    def write_status(self):
        """Write comprehensive status JSON."""
        equity = self.virtual_account.get_equity()
        
        # Calculate total PnL across all coins
        total_pnl = sum(slot.total_pnl for slot in self.coin_slots.values())
        total_deals = sum(slot.deals_completed for slot in self.coin_slots.values())
        
        pnl_pct = total_pnl / self.start_equity * 100 if self.start_equity > 0 else 0
        drawdown_pct = max(0, (self.start_equity - (self.start_equity + total_pnl)) / self.start_equity * 100) if self.start_equity > 0 else 0
        
        active_profile = self.profile_manager.get_active_profile()
        profile_params = self.profile_manager.get_profile_params(active_profile)
        
        # Per-coin data
        coins_data = {}
        for symbol, slot in self.coin_slots.items():
            coins_data[symbol] = slot.to_status_dict()
        
        status = {
            "mode": "paper_multicoin",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "timeframe": self.timeframe,
            "running": self._running,
            "active_profile": active_profile,
            "allocation": self.profile_manager.allocation,
            "total_capital": self.capital,
            "equity": round(self.start_equity + total_pnl, 2),
            "start_equity": round(self.start_equity, 2),
            "pnl": round(total_pnl, 2),
            "pnl_pct": round(pnl_pct, 2),
            "drawdown_pct": round(drawdown_pct, 2),
            "config": {
                "profile": active_profile,
                "leverage": profile_params["leverage"],
                "max_safety_orders": profile_params["max_safety_orders"],
                "so_volume_mult": profile_params["so_volume_mult"],
                "base_order_pct": profile_params["base_order_pct"],
                "capital_reserve": profile_params["capital_reserve"],
                "max_coins": self.profile_manager.get_max_coins(),
            },
            "coins": coins_data,
            "total_deals_completed": total_deals,
            "active_coins": len(self.coin_slots),
            "cycle_count": self.cycle_count,
            "start_time": self.start_time,
            "last_scanner_run": self.last_scanner_run,
            "guardrail_events": self.guardrail_events,
        }
        
        with open(PAPER_DIR / "status.json", "w") as f:
            json.dump(status, f, indent=2)
            
    def log_trade(self, action: str, symbol: str, price: float, qty: float, notional: float,
                  so_count: int = 0, pnl: float = 0, direction: str = "LONG", deal_id: int = 0):
        """Log trade to CSV file."""
        path = PAPER_DIR / "trades.csv"
        write_header = not path.exists()
        with open(path, "a", newline="") as f:
            w = csv.writer(f)
            if write_header:
                w.writerow(["timestamp", "action", "symbol", "deal_id", "direction", "price", "qty",
                            "notional", "so_count", "pnl", "regime"])
            
            # Get regime for this symbol if we have the slot
            regime = "UNKNOWN"
            if symbol in self.coin_slots:
                regime = self.coin_slots[symbol].current_regime
                
            w.writerow([
                datetime.now(timezone.utc).isoformat(), action, symbol,
                deal_id, direction, f"{price:.3f}", f"{qty:.2f}", f"{notional:.2f}", 
                so_count, f"{pnl:.2f}", regime
            ])
            
    def start(self):
        """Main trading loop."""
        self._running = True
        
        print(f"\nMulti-coin paper trading bot started!")
        print(f"Timeframe: {self.timeframe} | Capital: ${self.capital:.2f}")
        
        send_telegram(
            f"Multi-coin paper trading bot started\n"
            f"Capital: ${self.capital:.2f}\n"
            f"Profile: {PROFILES[self.profile_manager.get_active_profile()]['name']}\n"
            f"Max coins: {self.profile_manager.get_max_coins()}"
        )
        
        # Initial scanner run
        self.read_scanner_and_allocate()
        self.last_scanner_run = datetime.now(timezone.utc).isoformat()
        
        while self._running:
            try:
                self.cycle_count += 1
                
                # Check API connectivity
                if not self.api.ping():
                    print(f"API ping failed, retrying...")
                    time.sleep(10)
                    continue
                    
                # Refresh allocation if changed
                if self.profile_manager.refresh_allocation():
                    print("Allocation changed, re-reading scanner results...")
                    self.read_scanner_and_allocate()
                
                # Periodic scanner run
                if self.cycle_count % self.scanner_interval_cycles == 0:
                    print(f"\nRunning periodic scanner update (cycle {self.cycle_count})...")
                    self.read_scanner_and_allocate()
                    self.last_scanner_run = datetime.now(timezone.utc).isoformat()
                
                # Run trading cycles for all active coins
                print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Running {len(self.coin_slots)} coin slots...")
                
                for symbol, slot in self.coin_slots.items():
                    if slot.status == "active":
                        slot.run_cycle()
                        
                        # Log any closed deals
                        closed_deals = slot.check_deals_for_fills()
                        for closed in closed_deals:
                            direction, deal_id = closed.split('_')
                            self.log_trade("TP_HIT", symbol, slot.current_price, 0, 0, 
                                         direction=direction, deal_id=int(deal_id))
                        
                        # Log any new deals opened
                        if slot.long_deal and slot.long_deal.deal_id == slot.deal_counter and not hasattr(slot, '_last_long_logged'):
                            self.log_trade("OPEN", symbol, slot.long_deal.entry_price,
                                         slot.long_deal.entry_qty, slot.long_deal.entry_cost,
                                         direction="LONG", deal_id=slot.long_deal.deal_id)
                            slot._last_long_logged = True
                            
                        if slot.short_deal and slot.short_deal.deal_id == slot.deal_counter and not hasattr(slot, '_last_short_logged'):
                            self.log_trade("OPEN", symbol, slot.short_deal.entry_price,
                                         slot.short_deal.entry_qty, slot.short_deal.entry_cost,
                                         direction="SHORT", deal_id=slot.short_deal.deal_id)
                            slot._last_short_logged = True
                
                # Print summary
                if self.coin_slots:
                    total_pnl = sum(slot.total_pnl for slot in self.coin_slots.values())
                    active_deals = sum(1 for slot in self.coin_slots.values() 
                                     for deal in [slot.long_deal, slot.short_deal] if deal)
                    print(f"Total PnL: ${total_pnl:.2f} | Active deals: {active_deals}")
                
                # Write status
                self.write_status()
                
                time.sleep(30)  # 30-second cycle
                
            except KeyboardInterrupt:
                print("\nStopping...")
                break
            except Exception as e:
                print(f"\nError: {e}")
                traceback.print_exc()
                time.sleep(15)
                
        self._shutdown()
        
    def _shutdown(self):
        """Graceful shutdown."""
        self._running = False
        self.write_status()
        print("Multi-coin paper trading bot stopped")
        send_telegram("Multi-coin paper trading bot stopped")
        
    def stop(self):
        self._running = False