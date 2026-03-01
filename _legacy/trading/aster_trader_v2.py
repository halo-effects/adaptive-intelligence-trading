"""Paper Trading Bot for AIT with Risk Profiles
Simulates trading using real market data but no actual orders placed.
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
from typing import List, Optional, Dict, Any

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
PAPER_DIR.mkdir(exist_ok=True)

# Tier-based coin scaling
TIER_COIN_LIMITS = {
    5000: 1,    # Starter
    10000: 2,   # Trader 
    25000: 3,   # Pro
    50000: 5,   # Elite
    100000: 8   # Whale
}

# Telegram config (same as live)
TG_TOKEN = "8528958079:AAF90HSJ5Ck1urUydzS5CUvyf2EEeB7LUwc"
TG_CHAT_ID = "5221941584"
TG_ENABLED = True

# HYPEUSDT market rules
TICK_SIZE = 0.001
STEP_SIZE = 0.01
MIN_QTY = 0.01
MIN_NOTIONAL = 5.0
PRICE_PRECISION = 3
QTY_PRECISION = 2

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


def round_price(p: float) -> float:
    return round(round(p / TICK_SIZE) * TICK_SIZE, PRICE_PRECISION)


def round_qty(q: float) -> float:
    return round(round(q / STEP_SIZE) * STEP_SIZE, QTY_PRECISION)


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


def get_max_coins_for_capital(capital: float) -> int:
    """Determine max coins based on capital tier."""
    for tier_capital in sorted(TIER_COIN_LIMITS.keys(), reverse=True):
        if capital >= tier_capital:
            return TIER_COIN_LIMITS[tier_capital]
    return 1  # Default to 1 coin for very low capital


def load_scanner_recommendations() -> List[Dict]:
    """Load scanner results from live directory."""
    scanner_path = Path(__file__).parent / "live" / "scanner_recommendation.json"
    try:
        with open(scanner_path) as f:
            data = json.load(f)
            
        # Check if data is stale (>24h)
        timestamp = datetime.fromisoformat(data["timestamp"].replace("Z", "+00:00"))
        age = datetime.now(timezone.utc) - timestamp
        if age > timedelta(hours=24):
            print(f"[WARN] Scanner data is {age.total_seconds()/3600:.1f}h old, falling back to HYPEUSDT")
            return [{"symbol": "HYPE/USDT", "score": 100.0}]
            
        # Convert top_5 to standardized format
        coins = []
        for coin in data.get("top_5", []):
            symbol = coin["symbol"]
            # Convert from format like "HYPE/USDT" to "HYPEUSDT"
            if "/" in symbol:
                symbol = symbol.replace("/", "")
            coins.append({"symbol": symbol, "score": coin["score"]})
            
        return coins
    except Exception as e:
        print(f"[WARN] Failed to load scanner data: {e}, falling back to HYPEUSDT")
        return [{"symbol": "HYPEUSDT", "score": 100.0}]


def get_coins_for_trading(capital: float, max_coins_override: Optional[int] = None) -> List[Dict]:
    """Get top coins for trading based on capital tier and scanner results."""
    max_coins = max_coins_override or get_max_coins_for_capital(capital)
    scanner_coins = load_scanner_recommendations()
    
    # Take top N coins up to max_coins limit
    selected_coins = scanner_coins[:max_coins]
    
    # Calculate total score for proportional allocation
    total_score = sum(coin["score"] for coin in selected_coins)
    
    # Calculate capital allocation per coin with $3K minimum floor
    min_per_coin = 3000
    available_capital = capital * 0.9  # 10% reserve
    
    # First pass: calculate proportional allocation
    for coin in selected_coins:
        coin["allocation"] = (coin["score"] / total_score) * available_capital
    
    # Check if any coin falls below minimum - if so, reduce max coins
    coins_below_min = [c for c in selected_coins if c["allocation"] < min_per_coin]
    while coins_below_min and len(selected_coins) > 1:
        # Remove lowest scoring coin below minimum
        lowest_coin = min(coins_below_min, key=lambda x: x["score"])
        selected_coins.remove(lowest_coin)
        
        # Recalculate allocations
        total_score = sum(coin["score"] for coin in selected_coins)
        for coin in selected_coins:
            coin["allocation"] = (coin["score"] / total_score) * available_capital
        
        coins_below_min = [c for c in selected_coins if c["allocation"] < min_per_coin]
    
    print(f"Selected {len(selected_coins)} coins for ${capital:,.0f} capital (max: {max_coins})")
    for coin in selected_coins:
        print(f"  {coin['symbol']}: ${coin['allocation']:,.0f} (score: {coin['score']:.1f})")
    
    return selected_coins


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


class VirtualAccount:
    """Simulates exchange account for paper trading."""
    
    def __init__(self, initial_balance: float):
        self.balance = initial_balance
        self.start_balance = initial_balance
        self.equity = initial_balance
        self.virtual_positions = {}  # symbol -> {direction: {qty, cost}}
        
    def get_equity(self) -> float:
        """Return current equity (balance + unrealized PnL)."""
        return self.equity
        
    def get_balance(self) -> float:
        """Return available balance."""
        return self.balance
        
    def apply_fill(self, price: float, qty: float, direction: str, symbol: str = "HYPEUSDT"):
        """Apply a virtual fill to the account."""
        cost = price * qty
        
        if symbol not in self.virtual_positions:
            self.virtual_positions[symbol] = {"LONG": {"qty": 0, "cost": 0}, "SHORT": {"qty": 0, "cost": 0}}
        
        pos = self.virtual_positions[symbol][direction]
        pos["qty"] += qty
        pos["cost"] += cost
        
    def close_position(self, close_price: float, close_qty: float, direction: str, symbol: str = "HYPEUSDT") -> float:
        """Close position and return realized PnL."""
        if symbol not in self.virtual_positions:
            return 0.0
            
        pos = self.virtual_positions[symbol][direction]
        if pos["qty"] <= 0:
            return 0.0
            
        # Calculate PnL
        avg_cost = pos["cost"] / pos["qty"]
        if direction == "LONG":
            pnl = (close_price - avg_cost) * close_qty
        else:  # SHORT
            pnl = (avg_cost - close_price) * close_qty
            
        # Subtract fill from position
        ratio = close_qty / pos["qty"]
        pos["qty"] -= close_qty
        pos["cost"] -= pos["cost"] * ratio
        
        # Add PnL to balance
        self.balance += pnl
        self.equity = self.balance
        
        return pnl


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
            return {"low": 0, "medium": 100, "high": 0, "total_capital": 10000}
    
    def get_active_profile(self) -> str:
        """Get the currently active profile (single profile for Phase 1)."""
        for profile, pct in self.allocation.items():
            if profile in PROFILES and pct > 0:
                return profile
        return "medium"  # Default fallback
        
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
        
        # Check if profile changed
        old_active = None
        new_active = None
        
        for profile, pct in old_allocation.items():
            if profile in PROFILES and pct > 0:
                old_active = profile
                break
                
        for profile, pct in self.allocation.items():
            if profile in PROFILES and pct > 0:
                new_active = profile
                break
                
        if old_active != new_active and new_active:
            print(f"Profile changed: {old_active or 'none'} -> {new_active}")
            send_telegram(f"Risk profile changed to {PROFILES[new_active]['name']}")
            return True
        return False


class PaperDealManager:
    """Manages virtual deals like the live DealManager."""
    
    def __init__(self, profile_manager: ProfileManager, virtual_account: VirtualAccount, symbol: str = "HYPEUSDT"):
        self.profile_manager = profile_manager
        self.virtual_account = virtual_account
        self.symbol = symbol
        self.long_deal: Optional[VirtualDeal] = None
        self.short_deal: Optional[VirtualDeal] = None
        self.deal_counter = 0
        self.current_price = 0.0
        self.current_tp_pct = 1.5
        self.current_dev_pct = 2.5
        
    def _get_deal(self, direction: str) -> Optional[VirtualDeal]:
        return self.long_deal if direction == "LONG" else self.short_deal
        
    def _set_deal(self, direction: str, deal: Optional[VirtualDeal]):
        if direction == "LONG":
            self.long_deal = deal
        else:
            self.short_deal = deal
            
    def _calc_pnl(self, close_price: float, total_qty: float, total_cost: float, direction: str) -> float:
        if direction == "SHORT":
            return total_cost - (total_qty * close_price)
        else:
            return (total_qty * close_price) - total_cost
            
    def create_so_levels(self, deal: VirtualDeal, params: dict):
        """Create virtual SO levels for a deal."""
        deal.virtual_so_levels = []
        
        base_order_usd = params["base_order_pct"] / 100 * self.profile_manager.get_profile_capital(
            self.profile_manager.get_active_profile()
        )
        
        for n in range(1, params["max_safety_orders"] + 1):
            deviation_pct = params["deviation_range"][0] + (
                params["deviation_range"][1] - params["deviation_range"][0]
            ) * min(n / params["max_safety_orders"], 1.0)
            
            if deal.direction == "LONG":
                so_price = round_price(deal.entry_price * (1 - (deviation_pct * n) / 100))
            else:
                so_price = round_price(deal.entry_price * (1 + (deviation_pct * n) / 100))
                
            size_usd = base_order_usd * (params["so_volume_mult"] ** n)
            qty = round_qty(size_usd / so_price)
            
            if qty < MIN_QTY or qty * so_price < MIN_NOTIONAL:
                break
                
            deal.virtual_so_levels.append({
                "level": n,
                "price": so_price,
                "qty": qty,
                "size_usd": size_usd,
                "filled": False
            })
            
    def open_deal(self, direction: str, profile: str, alloc_fraction: float = 1.0):
        """Open a new virtual deal."""
        if self.current_price <= 0:
            print(f"  [SKIP] {direction} deal - no valid price data")
            return
            
        params = self.profile_manager.get_profile_params(profile)
        capital = self.profile_manager.get_profile_capital(profile)
        
        base_order_usd = params["base_order_pct"] / 100 * capital
        if base_order_usd < MIN_NOTIONAL:
            print(f"  [SKIP] {direction} base order ${base_order_usd:.2f} < min notional ${MIN_NOTIONAL}")
            return
            
        # Apply small slippage (0.01%) to simulate realistic entry
        slippage = 0.0001 if direction == "LONG" else -0.0001
        entry_price = round_price(self.current_price * (1 + slippage))
        
        qty = round_qty(base_order_usd / entry_price)
        if qty < MIN_QTY:
            print(f"  [SKIP] {direction} qty {qty} < min {MIN_QTY}")
            return
            
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
        self.create_so_levels(deal, params)
        
        # Set initial TP
        tp_pct = params["tp_range"][0] + (params["tp_range"][1] - params["tp_range"][0]) * 0.5  # Mid-range
        deal.tp_price = deal.calc_tp_price(tp_pct)
        self.current_tp_pct = tp_pct
        
        # Apply fill to virtual account
        self.virtual_account.apply_fill(entry_price, qty, direction)
        
        self._set_deal(direction, deal)
        
        dir_emoji = "[LONG]" if direction == "LONG" else "[SHORT]"
        print(f"  {dir_emoji} [PAPER] Deal #{self.deal_counter} {direction}: {qty} @ ${entry_price:.3f}")
        print(f"    TP: ${deal.tp_price:.3f} | SOs: {len(deal.virtual_so_levels)}")
        
        send_telegram(
            f"{dir_emoji} Deal #{self.deal_counter} {direction}\n"
            f"{self.symbol}\nEntry: ${entry_price:.3f}\nQty: {qty}\n"
            f"TP: ${deal.tp_price:.3f}\nLeverage: {params['leverage']}x\nProfile: {PROFILES[profile]['name']}"
        )
        
    def check_deals_for_fills(self) -> List[str]:
        """Check both deals for SO fills and TP hits."""
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
                    
                    # Apply to virtual account
                    self.virtual_account.apply_fill(fill_price, fill_qty, direction)
                    
                    print(f"[PAPER] {direction} SO#{deal.safety_orders_filled} filled @ ${fill_price:.3f}")
                    print(f"    New avg: ${deal.avg_entry:.3f} | New TP: ${deal.tp_price:.3f}")
                    
                    active = self.profile_manager.get_active_profile()
                    lev = self.profile_manager.get_profile_params(active).get("leverage", 1)
                    send_telegram(
                        f"SO #{deal.safety_orders_filled} Filled ({direction})\n"
                        f"{self.symbol} @ ${fill_price:.3f}\n"
                        f"New avg: ${deal.avg_entry:.3f}\n"
                        f"New TP: ${deal.tp_price:.3f}\n"
                        f"Leverage: {lev}x"
                    )
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
                pnl = self.virtual_account.close_position(fill_price, deal.total_qty, direction)
                
                deal.closed = True
                deal.close_price = fill_price
                deal.close_time = datetime.now(timezone.utc).isoformat()
                deal.realized_pnl = pnl
                
                pnl_pct = pnl / deal.total_cost * 100
                
                print(f"[PAPER] TP HIT! Deal #{deal.deal_id} {direction} @ ${fill_price:.3f}")
                print(f"    PnL: ${pnl:.2f} ({pnl_pct:+.1f}%) | SOs used: {deal.safety_orders_filled}")
                
                active = self.profile_manager.get_active_profile()
                lev = self.profile_manager.get_profile_params(active).get("leverage", 1)
                send_telegram(
                    f"TP HIT - Deal #{deal.deal_id} {direction}\n"
                    f"{self.symbol} closed @ ${fill_price:.3f}\n"
                    f"PnL: ${pnl:.2f} ({pnl_pct:+.1f}%)\n"
                    f"SOs used: {deal.safety_orders_filled}\n"
                    f"Leverage: {lev}x"
                )
                
                self._set_deal(direction, None)
                closed_deals.append(f"{direction}_{deal.deal_id}")
                
        return closed_deals


class AsterTraderV2:
    """Paper Trading Bot with Risk Profiles and Multi-Coin Support."""
    
    def __init__(self, symbol: str = "HYPEUSDT", timeframe: str = "5m",
                 capital: float = 10000, profile: str = "medium", max_coins: Optional[int] = None):
        self.symbol = symbol  # Legacy - kept for backwards compatibility
        self.timeframe = timeframe
        self.capital = capital
        self.max_coins_override = max_coins
        
        self.api = AsterAPI()
        self.virtual_account = VirtualAccount(capital)
        
        # Profile management
        self.profile_manager = ProfileManager(PAPER_DIR / "allocation.json")
        
        # Multi-coin setup
        self.coins = get_coins_for_trading(capital, max_coins)
        self.coin_managers = {}  # symbol -> PaperDealManager
        self.coin_prices = {}    # symbol -> current price
        self.coin_regimes = {}   # symbol -> current regime
        self.coin_trends = {}    # symbol -> bullish/bearish
        
        # Initialize deal managers for each coin
        for coin_data in self.coins:
            symbol = coin_data["symbol"]
            # Create individual profile manager for each coin with allocated capital
            coin_profile_manager = ProfileManager(PAPER_DIR / "allocation.json")
            coin_profile_manager.allocation["total_capital"] = coin_data["allocation"]
            
            self.coin_managers[symbol] = PaperDealManager(coin_profile_manager, self.virtual_account, symbol)
        
        # State
        self.start_equity = capital
        self.start_time = datetime.now(timezone.utc).isoformat()
        self.cycle_count = 0
        self._running = False
        self.guardrail_events = []
        
        coin_list = ", ".join([f"{c['symbol']}(${c['allocation']:,.0f})" for c in self.coins])
        print(f"Paper trading bot initialized: {coin_list} | Total: ${self.capital:,.0f}")
        
    def detect_regime_for_coin(self, symbol: str) -> str:
        """Detect market regime for a specific coin."""
        try:
            df = self.api.klines(symbol, self.timeframe, limit=300)
            if len(df) < 100:
                return "UNKNOWN"
            price = float(df["close"].iloc[-1])
            self.coin_prices[symbol] = price
            
            regimes = classify_regime_v2(df, self.timeframe)
            
            # Detect trend direction via SMA50
            sma50 = df["close"].rolling(50).mean().iloc[-1]
            self.coin_trends[symbol] = price >= sma50
            
            regime = regimes.iloc[-1]
            self.coin_regimes[symbol] = regime
            return regime
        except Exception as e:
            print(f"  [WARN] Regime detection error for {symbol}: {e}")
            return self.coin_regimes.get(symbol, "UNKNOWN")
            
    def write_status(self):
        """Write comprehensive status JSON with multi-coin data."""
        equity = self.virtual_account.get_equity()
        pnl = equity - self.start_equity
        pnl_pct = pnl / self.start_equity * 100 if self.start_equity > 0 else 0
        drawdown_pct = max(0, (self.start_equity - equity) / self.start_equity * 100) if self.start_equity > 0 else 0
        
        active_profile = self.profile_manager.get_active_profile()
        profile_params = self.profile_manager.get_profile_params(active_profile)
        
        # Collect per-coin data
        coin_data = {}
        total_deal_counter = 0
        
        for coin_info in self.coins:
            symbol = coin_info["symbol"]
            manager = self.coin_managers[symbol]
            price = self.coin_prices.get(symbol, 0.0)
            regime = self.coin_regimes.get(symbol, "UNKNOWN")
            trend_bullish = self.coin_trends.get(symbol, True)
            
            # Get regime allocation for this coin
            long_alloc, short_alloc = REGIME_ALLOC.get(regime, (0.5, 0.5))
            if regime in DIRECTIONAL_REGIMES and not trend_bullish:
                long_alloc, short_alloc = short_alloc, long_alloc
            
            coin_data[symbol] = {
                "allocation": coin_info["allocation"],
                "price": price,
                "regime": regime,
                "trend_direction": "bullish" if trend_bullish else "bearish",
                "regime_alloc": {"long": long_alloc, "short": short_alloc},
                "long_deal": manager.long_deal.to_dict() if manager.long_deal else None,
                "short_deal": manager.short_deal.to_dict() if manager.short_deal else None,
                "deal_counter": manager.deal_counter,
                "adaptive_tp": {
                    "current_tp_pct": round(manager.current_tp_pct, 3),
                    "current_dev_pct": round(manager.current_dev_pct, 3),
                }
            }
            total_deal_counter += manager.deal_counter
            
        status = {
            "mode": "paper",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "timeframe": self.timeframe,
            "running": self._running,
            "active_profile": active_profile,
            "allocation": self.profile_manager.allocation,
            "total_capital": self.capital,
            "equity": round(equity, 2),
            "start_equity": round(self.start_equity, 2),
            "pnl": round(pnl, 2),
            "pnl_pct": round(pnl_pct, 2),
            "drawdown_pct": round(drawdown_pct, 2),
            "config": {
                "profile": active_profile,
                "leverage": profile_params["leverage"],
                "max_safety_orders": profile_params["max_safety_orders"],
                "so_volume_mult": profile_params["so_volume_mult"],
                "base_order_pct": profile_params["base_order_pct"],
                "capital_reserve": profile_params["capital_reserve"],
            },
            "total_deal_counter": total_deal_counter,
            "cycle_count": self.cycle_count,
            "start_time": self.start_time,
            "guardrail_events": self.guardrail_events,
            "coins": coin_data,
            "coin_count": len(self.coins),
            "max_coins": self.max_coins_override or get_max_coins_for_capital(self.capital),
            
            # Legacy fields for backwards compatibility
            "symbol": self.coins[0]["symbol"] if self.coins else "UNKNOWN",
            "price": self.coin_prices.get(self.coins[0]["symbol"], 0.0) if self.coins else 0.0,
        }
        
        with open(PAPER_DIR / "status.json", "w") as f:
            json.dump(status, f, indent=2)
            
    def log_trade(self, action: str, symbol: str, price: float, qty: float, notional: float,
                  so_count: int = 0, pnl: float = 0, direction: str = "LONG", deal_id: int = 0, regime: str = "UNKNOWN"):
        """Log trade to CSV file with symbol column."""
        path = PAPER_DIR / "trades.csv"
        write_header = not path.exists()
        with open(path, "a", newline="") as f:
            w = csv.writer(f)
            if write_header:
                w.writerow(["timestamp", "action", "symbol", "deal_id", "direction", "price", "qty",
                            "notional", "so_count", "pnl", "regime"])
            w.writerow([
                datetime.now(timezone.utc).isoformat(), action, symbol,
                deal_id, direction, f"{price:.3f}", f"{qty:.2f}", f"{notional:.2f}", 
                so_count, f"{pnl:.2f}", regime
            ])
            
    def start(self):
        """Main trading loop with multi-coin support."""
        self._running = True
        
        coin_list = ", ".join([f"{c['symbol']}(${c['allocation']:,.0f})" for c in self.coins])
        print(f"\nPaper Trading Bot started!")
        print(f"  Coins: {coin_list} | TF: {self.timeframe} | Total: ${self.capital:,.0f}")
        
        active = self.profile_manager.get_active_profile()
        lev = self.profile_manager.get_profile_params(active).get("leverage", 1)
        send_telegram(
            f"Multi-Coin Paper Trading Bot Started\n"
            f"Coins: {len(self.coins)} | {self.timeframe}\n"
            f"Capital: ${self.capital:,.0f} | Leverage: {lev}x\n"
            f"Profile: {PROFILES[active]['name']}"
        )
        
        while self._running:
            try:
                self.cycle_count += 1
                
                # Check API connectivity
                if not self.api.ping():
                    print(f"API ping failed, retrying...")
                    time.sleep(10)
                    continue
                
                # Check for profile changes
                profile_changed = self.profile_manager.refresh_allocation()
                active_profile = self.profile_manager.get_active_profile()
                params = self.profile_manager.get_profile_params(active_profile)
                
                print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Cycle #{self.cycle_count} | {PROFILES[active_profile]['name']}")
                
                # Process each coin
                for coin_info in self.coins:
                    symbol = coin_info["symbol"]
                    manager = self.coin_managers[symbol]
                    
                    # Detect regime for this coin
                    regime = self.detect_regime_for_coin(symbol)
                    price = self.coin_prices.get(symbol, 0.0)
                    trend_bullish = self.coin_trends.get(symbol, True)
                    
                    # Get regime allocation
                    long_alloc, short_alloc = REGIME_ALLOC.get(regime, (0.5, 0.5))
                    
                    # Handle EXTREME regime per profile
                    if regime == "EXTREME":
                        extreme_alloc = params["extreme_allocation"]
                        long_alloc, short_alloc = extreme_alloc[0] / 100, extreme_alloc[1] / 100
                        
                    # Directional awareness
                    if regime in DIRECTIONAL_REGIMES and not trend_bullish:
                        long_alloc, short_alloc = short_alloc, long_alloc
                        
                    # Apply max directional bias
                    max_bias = params["max_directional_bias"]
                    max_long, max_short = max_bias[0] / 100, max_bias[1] / 100
                    if long_alloc > max_long:
                        excess = long_alloc - max_long
                        long_alloc = max_long
                        short_alloc = min(short_alloc + excess, 1.0)
                    if short_alloc > max_short:
                        excess = short_alloc - max_short
                        short_alloc = max_short  
                        long_alloc = min(long_alloc + excess, 1.0)
                    
                    trend_dir = "^" if trend_bullish else "v"
                    long_str = f"L#{manager.long_deal.deal_id}({manager.long_deal.safety_orders_filled}SO)" if manager.long_deal else "—"
                    short_str = f"S#{manager.short_deal.deal_id}({manager.short_deal.safety_orders_filled}SO)" if manager.short_deal else "—"
                    print(f"  {symbol}: ${price:.3f} | {regime}{trend_dir} | {long_str} {short_str} | L:{long_alloc:.0%}/S:{short_alloc:.0%}")
                    
                    # Update current price in deal manager
                    manager.current_price = price
                    
                    # Check existing deals for fills
                    closed_deals = manager.check_deals_for_fills()
                    
                    # Log closed deals
                    for closed in closed_deals:
                        direction, deal_id = closed.split('_')
                        self.log_trade("TP_HIT", symbol, price, 0, 0, direction=direction, deal_id=int(deal_id), regime=regime)
                    
                    # Open new deals based on allocation (only if we have valid price)
                    if price > 0:
                        if not manager.long_deal and long_alloc > 0:
                            print(f"      Opening LONG deal for {symbol} (alloc: {long_alloc:.0%})")
                            manager.open_deal("LONG", active_profile, long_alloc)
                            if manager.long_deal:
                                self.log_trade("OPEN", symbol, manager.long_deal.entry_price, 
                                             manager.long_deal.entry_qty,
                                             manager.long_deal.entry_cost,
                                             direction="LONG", deal_id=manager.long_deal.deal_id, regime=regime)
                        
                        if not manager.short_deal and short_alloc > 0:
                            print(f"      Opening SHORT deal for {symbol} (alloc: {short_alloc:.0%})")
                            manager.open_deal("SHORT", active_profile, short_alloc)
                            if manager.short_deal:
                                self.log_trade("OPEN", symbol, manager.short_deal.entry_price,
                                             manager.short_deal.entry_qty,
                                             manager.short_deal.entry_cost,
                                             direction="SHORT", deal_id=manager.short_deal.deal_id, regime=regime)
                    else:
                        print(f"      Waiting for {symbol} price data...")
                
                # Write status
                self.write_status()
                
                time.sleep(30)  # 30-second cycle like live bot
                
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
        print("Paper trading bot stopped")
        send_telegram("Paper Trading Bot Stopped")
        
    def stop(self):
        self._running = False