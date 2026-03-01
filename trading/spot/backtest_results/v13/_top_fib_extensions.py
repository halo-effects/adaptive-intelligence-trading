"""
Dynamic Fibonacci Extensions for Top Detection

From each cycle bottom, project Fib extension levels as top targets.
Fib levels: 1.0, 1.272, 1.618, 2.0, 2.272, 2.618, 3.0, 3.618, 4.236

Method:
1. Find cycle lows (significant bottoms)
2. Find the first major swing high after the low
3. Find the retracement low
4. Project extensions: low + fib * (swing_high - retracement_low)

Also test simpler: just fib multiples from the absolute cycle low.
- Level = cycle_low * fib_multiplier
- Or: Level = cycle_low + (swing_range * fib_multiplier)

ETF era, 4 paper bot coins. Show where Fib levels land vs actual peaks.
"""

import sqlite3
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

DB = r"C:\Users\Never\.openclaw\workspace\trading\spot\data\candles.db"
COINS = ["ETH/USDT", "SOL/USDT", "LINK/USDT", "XRP/USDT"]

FIB_LEVELS = [1.0, 1.272, 1.618, 2.0, 2.272, 2.618, 3.0, 3.618, 4.236]


def load_daily(coin):
    conn = sqlite3.connect(DB)
    df = pd.read_sql_query(
        f"SELECT * FROM candles_daily WHERE symbol='{coin}' ORDER BY timestamp", conn)
    conn.close()
    df["date"] = pd.to_datetime(df["timestamp"], unit="ms")
    return df


def find_cycle_lows(df, window=60):
    """Find significant cycle lows (local minimums in rolling window)."""
    df = df.copy()
    df["is_low"] = df["low"] == df["low"].rolling(window * 2 + 1, center=True).min()
    lows = df[df["is_low"]].copy()
    # Filter: must be >20% below prior high
    significant = []
    for _, row in lows.iterrows():
        prior = df[df["date"] < row["date"]]
        if len(prior) > 30:
            prior_high = prior["high"].rolling(60).max().iloc[-1]
            if prior_high > 0 and (row["low"] / prior_high - 1) < -0.20:
                significant.append(row)
    return significant


def find_swing_high_after(df, low_date, max_days=180):
    """Find the first significant swing high after a low."""
    future = df[(df["date"] > low_date) & (df["date"] <= low_date + timedelta(days=max_days))]
    if len(future) == 0:
        return None
    # Rolling max with 30-day window
    future = future.copy()
    future["is_high"] = future["high"] == future["high"].rolling(61, center=True, min_periods=1).max()
    highs = future[future["is_high"]]
    if len(highs) > 0:
        return highs.iloc[0]
    return future.loc[future["high"].idxmax()]


def find_retracement_after(df, high_date, max_days=90):
    """Find retracement low after the swing high."""
    future = df[(df["date"] > high_date) & (df["date"] <= high_date + timedelta(days=max_days))]
    if len(future) == 0:
        return None
    return future.loc[future["low"].idxmin()]


print("DYNAMIC FIBONACCI EXTENSIONS FOR TOP DETECTION")
print("=" * 70)

for coin in COINS:
    base = coin.split("/")[0]
    df = load_daily(coin)
    df_etf = df[df["date"] >= "2022-01-01"].copy()  # include pre-ETF for finding cycle lows
    
    # Find actual peak in ETF era
    df_peak = df[df["date"] >= "2023-01-01"]
    peak_idx = df_peak["high"].idxmax()
    peak_date = df_peak.loc[peak_idx, "date"]
    peak_price = df_peak.loc[peak_idx, "high"]
    
    print(f"\n{'='*70}")
    print(f"  {base} - Peak: {peak_date.strftime('%Y-%m-%d')} ${peak_price:.2f}")
    print(f"{'='*70}")
    
    # --- Method 1: Simple multiples from cycle low ---
    # Find the major cycle low (2022 bear bottom or ETF-era low)
    cycle_lows = []
    
    # Find lowest point in 2022-2023 (bear market bottom)
    bear_period = df[(df["date"] >= "2022-06-01") & (df["date"] <= "2023-06-01")]
    if len(bear_period) > 0:
        bear_low_idx = bear_period["low"].idxmin()
        bear_low = bear_period.loc[bear_low_idx]
        cycle_lows.append(("2022 Bear Bottom", bear_low["date"], bear_low["low"]))
    
    # Find lowest point in recent correction (2025-2026)
    recent = df[(df["date"] >= "2025-10-01") & (df["date"] <= "2026-03-01")]
    if len(recent) > 0:
        recent_low_idx = recent["low"].idxmin()
        recent_low = recent.loc[recent_low_idx]
        cycle_lows.append(("2025 Correction Low", recent_low["date"], recent_low["low"]))
    
    for low_label, low_date, low_price in cycle_lows:
        print(f"\n  --- {low_label}: {low_date.strftime('%Y-%m-%d')} ${low_price:.2f} ---")
        
        # Simple multiplier method
        print(f"  Simple Fib Multipliers from low:")
        for fib in FIB_LEVELS:
            target = low_price * fib
            hit = df_etf[(df_etf["date"] > low_date) & (df_etf["high"] >= target)]
            pct_of_peak = (target / peak_price) * 100
            hit_date = hit.iloc[0]["date"].strftime("%Y-%m-%d") if len(hit) > 0 else "never"
            marker = " <-- PEAK ZONE" if 0.9 <= target/peak_price <= 1.1 else ""
            print(f"    {fib:.3f}x = ${target:,.2f} ({pct_of_peak:.0f}% of peak) "
                  f"first hit: {hit_date}{marker}")
    
    # --- Method 2: Extension from swing low -> swing high -> retracement ---
    print(f"\n  --- Fib Extension (Low -> High -> Retrace -> Project) ---")
    
    # Find the swing from bear low
    if len(cycle_lows) > 0:
        _, bear_date, bear_price = cycle_lows[0]
        swing_high = find_swing_high_after(df, bear_date, max_days=365)
        
        if swing_high is not None:
            sh_date = swing_high["date"]
            sh_price = swing_high["high"]
            
            retrace = find_retracement_after(df, sh_date, max_days=120)
            if retrace is not None:
                rt_date = retrace["date"]
                rt_price = retrace["low"]
                
                swing_range = sh_price - rt_price
                
                print(f"  Swing: ${bear_price:.2f} ({bear_date.strftime('%Y-%m-%d')}) "
                      f"-> ${sh_price:.2f} ({sh_date.strftime('%Y-%m-%d')}) "
                      f"-> ${rt_price:.2f} ({rt_date.strftime('%Y-%m-%d')})")
                print(f"  Swing range: ${swing_range:.2f}")
                print()
                
                for fib in FIB_LEVELS:
                    target = rt_price + swing_range * fib
                    pct_of_peak = (target / peak_price) * 100
                    hit = df[(df["date"] > rt_date) & (df["high"] >= target)]
                    hit_date = hit.iloc[0]["date"].strftime("%Y-%m-%d") if len(hit) > 0 else "never"
                    marker = " <-- PEAK ZONE" if 0.9 <= target/peak_price <= 1.1 else ""
                    print(f"    {fib:.3f} ext = ${target:,.2f} ({pct_of_peak:.0f}% of peak) "
                          f"first hit: {hit_date}{marker}")
    
    # --- Method 3: Full range from absolute low to first major high ---
    print(f"\n  --- Full Range Extension (Cycle Low to First Major High) ---")
    if len(cycle_lows) > 0:
        _, bear_date, bear_price = cycle_lows[0]
        # Find the highest point between bear low and actual peak
        between = df[(df["date"] > bear_date) & (df["date"] <= peak_date)]
        if len(between) > 0:
            # Find first significant high (>50% recovery from bear low)
            recovery_thresh = bear_price * 1.5
            first_recovery = between[between["high"] >= recovery_thresh]
            if len(first_recovery) > 0:
                fr = first_recovery.iloc[0]
                swing_range = fr["high"] - bear_price
                
                print(f"  Range: ${bear_price:.2f} -> ${fr['high']:.2f} "
                      f"({fr['date'].strftime('%Y-%m-%d')}), range=${swing_range:.2f}")
                
                for fib in [1.618, 2.0, 2.272, 2.618, 3.0, 3.618, 4.236, 5.0]:
                    target = bear_price + swing_range * fib
                    pct_of_peak = (target / peak_price) * 100
                    hit = df[(df["date"] > fr["date"]) & (df["high"] >= target)]
                    hit_date = hit.iloc[0]["date"].strftime("%Y-%m-%d") if len(hit) > 0 else "never"
                    marker = " <-- PEAK ZONE" if 0.9 <= target/peak_price <= 1.1 else ""
                    print(f"    {fib:.3f} ext = ${target:,.2f} ({pct_of_peak:.0f}% of peak) "
                          f"first hit: {hit_date}{marker}")


# Summary: which fib level is closest to actual peak for each coin?
print(f"\n\n{'='*70}")
print("SUMMARY: Closest Fib Level to Actual Peak")
print(f"{'='*70}")
for coin in COINS:
    base = coin.split("/")[0]
    df = load_daily(coin)
    df_peak = df[df["date"] >= "2023-01-01"]
    peak_price = df_peak["high"].max()
    
    bear_period = df[(df["date"] >= "2022-06-01") & (df["date"] <= "2023-06-01")]
    if len(bear_period) > 0:
        bear_low = bear_period["low"].min()
        ratio = peak_price / bear_low
        
        # Find closest fib
        closest_fib = min(FIB_LEVELS + [1.618, 2.0, 2.272, 2.618, 3.0, 3.618, 4.236, 5.0, 6.0, 7.0, 8.0],
                         key=lambda f: abs(f - ratio))
        print(f"  {base:6} Low=${bear_low:.2f}, Peak=${peak_price:.2f}, "
              f"Ratio={ratio:.2f}x, Closest Fib={closest_fib:.3f}x")
