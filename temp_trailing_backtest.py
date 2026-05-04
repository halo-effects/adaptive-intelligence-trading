"""Backtest 4 trailing stop configs against historical candle data.
Uses the same 5 coins from the original backtest: TAO, ZEC, FET, JTO, HYPE.
365-day window, $50K capital, high profile."""

import sqlite3, json, os, sys
from datetime import datetime, timedelta
import numpy as np

sys.path.insert(0, r"C:\Users\Never\.openclaw\workspace")

DB_PATH = r"C:\Users\Never\.openclaw\workspace\trading\spot\data\candles.db"

# Configs to test
CONFIGS = [
    {"name": "Current (1.5%/0.5%)", "activation_pct": 1.5, "callback_pct": 0.5},
    {"name": "Option 1 (1.5%/0.25%)", "activation_pct": 1.5, "callback_pct": 0.25},
    {"name": "Option 2 (2.0%/0.5%)", "activation_pct": 2.0, "callback_pct": 0.5},
    {"name": "Option 3 (1.75%/0.25%)", "activation_pct": 1.75, "callback_pct": 0.25},
    {"name": "Fixed TP (1.5%)", "activation_pct": None, "callback_pct": None},
]

COINS = ["TAO/USDT", "ZEC/USDT", "FET/USDT", "JTO/USDT", "HYPE/USDT"]
CAPITAL = 50000
BO_PCT = 0.30
TP_PCT = 0.015
SO_DEV = 0.025
SO_MULT = 1.5
MAX_LAYERS = 12
TAKER_FEE = 0.00035
MAKER_FEE = 0.00025

conn = sqlite3.connect(DB_PATH)

def get_candles(symbol, days=365):
    """Get hourly candles for a symbol."""
    # Try different table names
    base = symbol.replace("/USDT", "").replace("/USDC", "")
    for tbl in [f"{base}USDT_1h", f"{base}_USDT_1h", f"{symbol.replace('/', '')}_1h"]:
        try:
            df = conn.execute(
                f"SELECT timestamp, open, high, low, close FROM [{tbl}] ORDER BY timestamp"
            ).fetchall()
            if df:
                return df
        except:
            pass
    return []

def simulate_coin(candles, config, per_coin_capital):
    """Simulate DCA grid with trailing stop on one coin."""
    capital = per_coin_capital
    total_pnl = 0
    trades = 0
    wins = 0
    
    # Position state
    coins_held = 0.0
    avg_entry = 0.0
    layers = 0
    cost = 0.0
    tp_price = 0.0
    
    # Trailing state
    trail_active = False
    trail_peak = 0.0
    
    is_fixed = config["activation_pct"] is None
    act_pct = (config["activation_pct"] or 0) / 100
    cb_pct = (config["callback_pct"] or 0) / 100
    
    for ts, open_p, high, low, close in candles:
        if np.isnan(close) or close <= 0:
            continue
        
        # Check TP / Trailing
        if coins_held > 0 and tp_price > 0:
            fill_price = None
            is_taker = False
            
            if is_fixed:
                # Fixed TP: sell at tp_price if high touches it
                if high >= tp_price:
                    fill_price = tp_price
                    is_taker = False  # limit order
            else:
                # Trailing stop simulation
                activation = avg_entry * (1 + act_pct)
                
                if trail_active:
                    trail_peak = max(trail_peak, high)
                    trigger = trail_peak * (1 - cb_pct)
                    if low <= trigger:
                        fill_price = trigger
                        is_taker = True
                elif high >= activation:
                    trail_active = True
                    trail_peak = high
                    trigger = trail_peak * (1 - cb_pct)
                    if low <= trigger:
                        fill_price = trigger
                        is_taker = True
            
            if fill_price is not None:
                proceeds = coins_held * fill_price
                fee = proceeds * (TAKER_FEE if is_taker else MAKER_FEE)
                pnl = proceeds - cost - fee
                total_pnl += pnl
                capital += proceeds - fee
                trades += 1
                if pnl > 0:
                    wins += 1
                
                # Reset
                coins_held = 0
                avg_entry = 0
                layers = 0
                cost = 0
                tp_price = 0
                trail_active = False
                trail_peak = 0
                continue
        
        # DCA entry logic
        if layers >= MAX_LAYERS:
            continue
        
        should_buy = False
        if layers == 0:
            should_buy = True  # Always enter L1
        elif layers >= 1:
            # SO trigger: price drops SO_DEV below avg entry
            so_trigger = avg_entry * (1 - SO_DEV * layers)
            if close <= so_trigger:
                should_buy = True
        
        if should_buy and capital > 0:
            if layers == 0:
                order_usd = min(per_coin_capital * BO_PCT, capital)
            else:
                prev_order = per_coin_capital * BO_PCT * (SO_MULT ** (layers))
                order_usd = min(prev_order, capital)
            
            if order_usd < 1:
                continue
            
            fee = order_usd * TAKER_FEE
            capital -= (order_usd + fee)
            new_coins = order_usd / close
            
            total_cost_before = coins_held * avg_entry if coins_held > 0 else 0
            coins_held += new_coins
            avg_entry = (total_cost_before + order_usd) / coins_held if coins_held > 0 else close
            cost += order_usd + fee
            layers += 1
            tp_price = avg_entry * (1 + TP_PCT)
            
            # Reset trail on new layer
            trail_active = False
            trail_peak = 0
    
    # Close any remaining position at last price
    if coins_held > 0:
        last_close = candles[-1][4]
        proceeds = coins_held * last_close
        fee = proceeds * TAKER_FEE
        pnl = proceeds - cost - fee
        total_pnl += pnl
        trades += 1
        if pnl > 0:
            wins += 1
    
    return total_pnl, trades, wins

# Run backtests
print("TRAILING STOP BACKTEST — 365 DAYS, 5 COINS, $50K CAPITAL")
print("Coins: TAO, ZEC, FET, JTO, HYPE")
print("=" * 90)

per_coin = CAPITAL / len(COINS)

results = {}
for config in CONFIGS:
    total_pnl = 0
    total_trades = 0
    total_wins = 0
    coin_results = {}
    
    for coin in COINS:
        candles = get_candles(coin)
        if not candles:
            print(f"  WARNING: No candles for {coin}")
            continue
        
        # Use last 365 days
        if len(candles) > 365 * 24:
            candles = candles[-365*24:]
        
        pnl, trades, wins = simulate_coin(candles, config, per_coin)
        total_pnl += pnl
        total_trades += trades
        total_wins += wins
        coin_results[coin] = {"pnl": pnl, "trades": trades, "wins": wins}
    
    roi = (total_pnl / CAPITAL) * 100
    win_rate = (total_wins / total_trades * 100) if total_trades > 0 else 0
    results[config["name"]] = {
        "pnl": total_pnl,
        "roi": roi,
        "trades": total_trades,
        "wins": total_wins,
        "win_rate": win_rate,
        "coins": coin_results,
    }

# Print results
print(f"\n{'Config':<28} {'Total PnL':>12} {'ROI':>8} {'Trades':>8} {'Win%':>7} {'$/Trade':>10}")
print("-" * 80)
for name, r in results.items():
    avg = r["pnl"] / r["trades"] if r["trades"] > 0 else 0
    print(f"{name:<28} ${r['pnl']:>10,.0f} {r['roi']:>7.1f}% {r['trades']:>7} {r['win_rate']:>6.1f}% ${avg:>9.2f}")

# Improvement vs fixed
print(f"\n{'Config':<28} {'vs Fixed TP':>12} {'Extra %':>10}")
print("-" * 55)
fixed_pnl = results["Fixed TP (1.5%)"]["pnl"]
for name, r in results.items():
    if name == "Fixed TP (1.5%)":
        continue
    diff = r["pnl"] - fixed_pnl
    diff_pct = (diff / fixed_pnl * 100) if fixed_pnl != 0 else 0
    print(f"{name:<28} ${diff:>10,.0f} {diff_pct:>9.1f}%")

# Per-coin breakdown for top 2 configs
print(f"\nPer-coin breakdown (Current vs Option 3 vs Fixed):")
print(f"{'Coin':<12} {'Current':>10} {'Option 3':>10} {'Fixed':>10} {'Curr vs Fix':>12} {'Opt3 vs Fix':>12}")
print("-" * 70)
for coin in COINS:
    base = coin.replace("/USDT", "")
    c = results["Current (1.5%/0.5%)"]["coins"].get(coin, {})
    o3 = results["Option 3 (1.75%/0.25%)"]["coins"].get(coin, {})
    f = results["Fixed TP (1.5%)"]["coins"].get(coin, {})
    c_diff = c.get("pnl", 0) - f.get("pnl", 0)
    o3_diff = o3.get("pnl", 0) - f.get("pnl", 0)
    print(f"{base:<12} ${c.get('pnl',0):>9,.0f} ${o3.get('pnl',0):>9,.0f} ${f.get('pnl',0):>9,.0f} ${c_diff:>10,.0f} ${o3_diff:>10,.0f}")
