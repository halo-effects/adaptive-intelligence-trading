"""
Bearish Divergence Detector v2 — Rolling Window Approach

Instead of swing high detection (misses parabolic moves), use:
- Price at N-day high (or within X% of it)
- RSI is BELOW its N-day high by at least Y points

This captures the "price pushing higher while momentum fading" dynamic
even in steep rallies where discrete swing highs are hard to find.

Also tests: confirmation by RSI crossing below a threshold after divergence.
"""

import sqlite3
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

DB = r"C:\Users\Never\.openclaw\workspace\trading\spot\data\candles.db"

TOPS = {
    "ETH": {"date": "2024-12-06", "price": 4107},
    "SOL": {"date": "2025-01-19", "price": 294},
    "BTC": {"date": "2025-01-20", "price": 109350},
    "LINK": {"date": "2024-12-08", "price": 30.8},
    "XRP": {"date": "2025-01-16", "price": 3.39},
}

ETF_START = pd.Timestamp("2023-01-01")


def load_daily(symbol):
    conn = sqlite3.connect(DB)
    df = pd.read_sql_query(
        f"SELECT * FROM candles_daily WHERE symbol='{symbol}' ORDER BY timestamp", conn)
    conn.close()
    df["date"] = pd.to_datetime(df["timestamp"], unit="ms")
    return df


def compute_rsi(series, period=14):
    delta = series.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = -delta.where(delta < 0, 0.0)
    avg_gain = gain.ewm(alpha=1/period, min_periods=period).mean()
    avg_loss = loss.ewm(alpha=1/period, min_periods=period).mean()
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


def compute_mfi(high, low, close, volume, period=14):
    tp = (high + low + close) / 3
    rmf = tp * volume
    delta = tp.diff()
    pos_flow = rmf.where(delta > 0, 0.0)
    neg_flow = rmf.where(delta < 0, 0.0)
    pos_sum = pos_flow.rolling(period).sum()
    neg_sum = neg_flow.rolling(period).sum()
    mfi = 100 - (100 / (1 + pos_sum / neg_sum.replace(0, 1e-10)))
    return mfi


def detect_rolling_divergence(df, lookback, rsi_gap, price_pct=2.0, min_rsi=60):
    """
    Detect days where:
    - Price is within price_pct% of its lookback-day high
    - RSI is at least rsi_gap below its lookback-day high
    - RSI is still above min_rsi (we're in overbought territory, not a downtrend)
    
    Returns signal on the FIRST day of each divergence cluster.
    """
    df = df.copy()
    df["rsi"] = compute_rsi(df["close"], 14)
    df["mfi"] = compute_mfi(df["high"], df["low"], df["close"], df["volume"], 14)
    
    df["price_high_N"] = df["high"].rolling(lookback).max()
    df["rsi_high_N"] = df["rsi"].rolling(lookback).max()
    df["mfi_high_N"] = df["mfi"].rolling(lookback).max()
    
    # Price near its high
    df["price_near_high"] = (df["high"] >= df["price_high_N"] * (1 - price_pct / 100))
    # RSI diverging
    df["rsi_diverging"] = (df["rsi_high_N"] - df["rsi"]) >= rsi_gap
    # Still elevated
    df["rsi_elevated"] = df["rsi"] >= min_rsi
    
    df["signal"] = df["price_near_high"] & df["rsi_diverging"] & df["rsi_elevated"]
    
    # Cluster signals: only keep first in each cluster (gap >= 10 days)
    signals = []
    last_signal_date = None
    for idx, row in df[df["signal"]].iterrows():
        if last_signal_date is None or (row["date"] - last_signal_date).days >= 10:
            signals.append({
                "date": row["date"],
                "price": row["close"],
                "rsi": row["rsi"],
                "rsi_peak": row["rsi_high_N"],
                "rsi_gap": row["rsi_high_N"] - row["rsi"],
                "mfi": row["mfi"],
                "mfi_gap": row["mfi_high_N"] - row["mfi"],
            })
            last_signal_date = row["date"]
    
    return signals


def classify(sig_date, top_date):
    days = (top_date - sig_date).days
    if -14 <= days <= 60:
        return "TRUE", days
    elif days < -14:
        return "LATE", days
    else:
        return "FALSE", days


# ============================================================
# PARAMETER SWEEP
# ============================================================
print("=" * 100)
print("BEARISH DIVERGENCE v2 — Rolling Window Parameter Sweep")
print("=" * 100)

configs = [
    # lookback, rsi_gap, price_pct, min_rsi
    (20, 5, 2, 55),
    (20, 8, 2, 55),
    (20, 10, 2, 55),
    (30, 5, 2, 55),
    (30, 8, 2, 55),
    (30, 10, 2, 55),
    (30, 5, 3, 55),
    (30, 8, 3, 55),
    (40, 5, 2, 55),
    (40, 8, 2, 55),
    (40, 10, 2, 55),
    (40, 5, 3, 55),
    (40, 8, 3, 55),
    (50, 5, 2, 55),
    (50, 8, 2, 55),
    (50, 10, 2, 55),
    (60, 5, 2, 55),
    (60, 8, 2, 55),
    (60, 10, 2, 55),
    # Higher min_rsi to reduce false positives
    (30, 8, 2, 60),
    (40, 8, 2, 60),
    (40, 10, 2, 60),
    (50, 8, 2, 60),
    (50, 10, 2, 60),
    (60, 8, 2, 60),
    (60, 10, 2, 60),
]

results = []
for lookback, rsi_gap, price_pct, min_rsi in configs:
    total_true = 0
    total_false = 0
    total_late = 0
    coins_caught = set()
    timing_list = []
    
    for coin, top_info in TOPS.items():
        symbol = f"{coin}/USDT"
        df = load_daily(symbol)
        df = df[df["date"] >= ETF_START].reset_index(drop=True)
        top_date = pd.Timestamp(top_info["date"])
        
        signals = detect_rolling_divergence(df, lookback, rsi_gap, price_pct, min_rsi)
        
        for sig in signals:
            cls, days = classify(sig["date"], top_date)
            if cls == "TRUE":
                total_true += 1
                coins_caught.add(coin)
                timing_list.append(days)
            elif cls == "FALSE":
                total_false += 1
            else:
                total_late += 1
    
    total = total_true + total_false + total_late
    false_rate = total_false / total * 100 if total > 0 else 0
    avg_timing = sum(timing_list) / len(timing_list) if timing_list else 0
    caught = len(coins_caught)
    
    # Score: prioritize coverage, then low false rate
    score = caught * 25 - false_rate * 0.5 - (5 - caught) * 10
    
    results.append({
        "config": (lookback, rsi_gap, price_pct, min_rsi),
        "caught": caught,
        "true": total_true,
        "false": total_false,
        "late": total_late,
        "total": total,
        "false_rate": false_rate,
        "avg_timing": avg_timing,
        "score": score,
        "coins": coins_caught,
    })

# Sort by score
results.sort(key=lambda x: (-x["caught"], x["false_rate"], -x["score"]))

print(f"\n{'Config':>30s} | caught | true | false | late | total | false% | timing | coins")
print("-" * 110)
for r in results[:20]:
    lb, rg, pp, mr = r["config"]
    coins_str = ",".join(sorted(r["coins"]))
    print(f"  lb={lb:2d} gap={rg:2d} pct={pp} rsi>{mr:2d} | "
          f"  {r['caught']}/5  |  {r['true']:2d}  |  {r['false']:2d}   |  {r['late']:2d}  |  {r['total']:2d}   | "
          f" {r['false_rate']:4.0f}%  |  {r['avg_timing']:4.0f}d  | {coins_str}")

# Pick best: highest coverage with lowest false rate
best = results[0]
print(f"\nBest: lb={best['config'][0]} gap={best['config'][1]} pct={best['config'][2]} min_rsi={best['config'][3]}")
print(f"Caught {best['caught']}/5: {','.join(sorted(best['coins']))}")
print(f"Missing: {','.join(sorted(set(TOPS.keys()) - best['coins']))}")

# ============================================================
# DETAILED OUTPUT FOR BEST
# ============================================================
lb, rg, pp, mr = best["config"]
print(f"\n{'='*100}")
print(f"DETAILED — lb={lb}, gap>={rg}, price within {pp}%, min_rsi={mr}")
print(f"{'='*100}")

for coin, top_info in TOPS.items():
    symbol = f"{coin}/USDT"
    df = load_daily(symbol)
    df = df[df["date"] >= ETF_START].reset_index(drop=True)
    top_date = pd.Timestamp(top_info["date"])
    
    signals = detect_rolling_divergence(df, lb, rg, pp, mr)
    
    print(f"\n  {coin} (top: {top_info['date']} @ ${top_info['price']:,})")
    print(f"  {'─'*80}")
    
    if not signals:
        print(f"    No signals")
        continue
    
    for sig in signals:
        cls, days = classify(sig["date"], top_date)
        marker = ">>TRUE<<" if cls == "TRUE" else f"  {cls:6s}"
        print(f"    {marker} {sig['date'].strftime('%Y-%m-%d')} "
              f"price=${sig['price']:,.1f} RSI={sig['rsi']:.1f} "
              f"(peak RSI={sig['rsi_peak']:.1f}, gap={sig['rsi_gap']:.1f}) "
              f"MFI={sig['mfi']:.1f} (gap={sig['mfi_gap']:.1f}) "
              f"[{days:+d}d]")
