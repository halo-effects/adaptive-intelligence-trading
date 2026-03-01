"""
Divergence Detector v3 — Best config from v2 + gate filters to reduce false positives

Best v2 config: lb=60, gap>=8, price within 2%, min_rsi=60 → 5/5, 26% false

Filters to test:
1. Require price > SMA200 (in an uptrend)
2. Require RSI peak was > 75 (a real overbought reading existed)
3. Require price made a new 120-day high in lookback period
4. Combine: divergence + price > SMA200 + RSI peak > 75
5. Combine with OB93 (if 2W StochRSI was > 93 in prior 120 days)
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
    return 100 - (100 / (1 + pos_sum / neg_sum.replace(0, 1e-10)))


def prepare_df(symbol):
    df = load_daily(symbol)
    df = df[df["date"] >= pd.Timestamp("2022-01-01")].reset_index(drop=True)  # warmup from 2022
    df["rsi"] = compute_rsi(df["close"], 14)
    df["mfi"] = compute_mfi(df["high"], df["low"], df["close"], df["volume"], 14)
    df["sma200"] = df["close"].rolling(200).mean()
    df["price_high_60"] = df["high"].rolling(60).max()
    df["rsi_high_60"] = df["rsi"].rolling(60).max()
    df["price_high_120"] = df["high"].rolling(120).max()
    
    # Divergence base signal
    df["price_near_high"] = df["high"] >= df["price_high_60"] * 0.98
    df["rsi_diverging"] = (df["rsi_high_60"] - df["rsi"]) >= 8
    df["rsi_elevated"] = df["rsi"] >= 60
    df["div_base"] = df["price_near_high"] & df["rsi_diverging"] & df["rsi_elevated"]
    
    # Gates
    df["above_sma200"] = df["close"] > df["sma200"]
    df["rsi_peak_gt75"] = df["rsi_high_60"] > 75
    df["new_120d_high"] = df["high"] >= df["price_high_120"] * 0.98
    
    return df[df["date"] >= ETF_START].reset_index(drop=True)


def cluster_signals(df, mask, min_gap=10):
    signals = []
    last_date = None
    for idx in df[mask].index:
        row = df.loc[idx]
        if last_date is None or (row["date"] - last_date).days >= min_gap:
            signals.append(row)
            last_date = row["date"]
    return signals


def classify(sig_date, top_date):
    days = (top_date - sig_date).days
    if -14 <= days <= 60:
        return "TRUE", days
    elif days < -14:
        return "LATE", days
    else:
        return "FALSE", days


def test_filter(name, gate_fn):
    total_true = 0
    total_false = 0
    total_late = 0
    coins_caught = set()
    timing_list = []
    details = {}
    
    for coin, top_info in TOPS.items():
        symbol = f"{coin}/USDT"
        df = prepare_df(symbol)
        top_date = pd.Timestamp(top_info["date"])
        
        mask = df["div_base"] & gate_fn(df)
        signals = cluster_signals(df, mask)
        
        coin_sigs = []
        for sig in signals:
            cls, days = classify(sig["date"], top_date)
            coin_sigs.append((sig, cls, days))
            if cls == "TRUE":
                total_true += 1
                coins_caught.add(coin)
                timing_list.append(days)
            elif cls == "FALSE":
                total_false += 1
            else:
                total_late += 1
        
        details[coin] = coin_sigs
    
    total = total_true + total_false + total_late
    false_rate = total_false / total * 100 if total > 0 else 0
    avg_timing = sum(timing_list) / len(timing_list) if timing_list else 0
    
    return {
        "name": name,
        "caught": len(coins_caught),
        "coins": coins_caught,
        "true": total_true,
        "false": total_false,
        "late": total_late,
        "total": total,
        "false_rate": false_rate,
        "avg_timing": avg_timing,
        "details": details,
    }


# ============================================================
# TEST ALL FILTERS
# ============================================================
print("=" * 100)
print("DIVERGENCE v3 — Gate Filters to Reduce False Positives")
print("=" * 100)

filters = [
    ("No filter (baseline)", lambda df: pd.Series(True, index=df.index)),
    ("+ Above SMA200", lambda df: df["above_sma200"]),
    ("+ RSI peak > 75", lambda df: df["rsi_peak_gt75"]),
    ("+ New 120d high", lambda df: df["new_120d_high"]),
    ("+ SMA200 + RSI peak > 75", lambda df: df["above_sma200"] & df["rsi_peak_gt75"]),
    ("+ SMA200 + 120d high", lambda df: df["above_sma200"] & df["new_120d_high"]),
    ("+ RSI peak > 75 + 120d high", lambda df: df["rsi_peak_gt75"] & df["new_120d_high"]),
    ("+ ALL THREE", lambda df: df["above_sma200"] & df["rsi_peak_gt75"] & df["new_120d_high"]),
]

print(f"\n{'Filter':>35s} | caught | true | false | late | total | false% | timing")
print("-" * 100)

all_results = []
for name, gate_fn in filters:
    r = test_filter(name, gate_fn)
    all_results.append(r)
    missing = set(TOPS.keys()) - r["coins"]
    miss_str = f"  MISS: {','.join(sorted(missing))}" if missing else ""
    print(f"  {name:>33s} | {r['caught']}/5  | {r['true']:3d}  | {r['false']:3d}   | {r['late']:3d}  | "
          f"{r['total']:3d}   | {r['false_rate']:4.0f}%  | {r['avg_timing']:4.0f}d{miss_str}")

# Show detail for best 5/5 filter
best_5 = [r for r in all_results if r["caught"] == 5]
if best_5:
    best_5.sort(key=lambda x: x["false_rate"])
    best = best_5[0]
    print(f"\n{'='*100}")
    print(f"BEST 5/5 FILTER: {best['name']}")
    print(f"False rate: {best['false_rate']:.0f}%, Avg timing: {best['avg_timing']:.0f}d before top")
    print(f"{'='*100}")
    
    for coin, sigs in best["details"].items():
        top_info = TOPS[coin]
        print(f"\n  {coin} (top: {top_info['date']})")
        for sig, cls, days in sigs:
            marker = ">>TRUE<<" if cls == "TRUE" else f"  {cls:6s}"
            print(f"    {marker} {sig['date'].strftime('%Y-%m-%d')} "
                  f"${sig['close']:,.1f} RSI={sig['rsi']:.1f} "
                  f"(peak={sig['rsi_high_60']:.1f} gap={sig['rsi_high_60']-sig['rsi']:.1f}) [{days:+d}d]")

# Also show best overall (lowest false rate with >=4 caught)
best_all = [r for r in all_results if r["caught"] >= 4]
best_all.sort(key=lambda x: x["false_rate"])
if best_all and best_all[0] != best_5[0]:
    r = best_all[0]
    print(f"\nLowest false rate (>= 4/5): {r['name']} — {r['caught']}/5, {r['false_rate']:.0f}% false")
    missing = set(TOPS.keys()) - r["coins"]
    if missing:
        print(f"  Missing: {','.join(sorted(missing))}")
