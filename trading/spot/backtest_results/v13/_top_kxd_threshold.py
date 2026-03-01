"""
K×D Crossover Threshold Test

Bottom pattern: K was < 5, then K crosses above D = bottom signal
Top mirror:     K was > X, then K crosses below D = top signal

Test: require K to have been above threshold within N 2W candles
before the K×D cross fires. This filters out weak crossovers.

Thresholds: 80, 85, 90, 93, 95
Lookback: 1, 2, 3, 5 candles (2-10 weeks)
"""

import sqlite3
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

DB = r"C:\Users\Never\.openclaw\workspace\trading\spot\data\candles.db"
COINS = ["ETH/USDT", "SOL/USDT", "LINK/USDT", "XRP/USDT"]
ETF_START = "2023-01-01"


def load_daily(coin):
    conn = sqlite3.connect(DB)
    df = pd.read_sql_query(
        f"SELECT * FROM candles_daily WHERE symbol='{coin}' ORDER BY timestamp", conn)
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


def compute_stochrsi(close, rsi_period=14, stoch_period=14, k_smooth=3, d_smooth=3):
    rsi = compute_rsi(close, rsi_period)
    min_rsi = rsi.rolling(stoch_period).min()
    max_rsi = rsi.rolling(stoch_period).max()
    stoch_rsi = (rsi - min_rsi) / (max_rsi - min_rsi) * 100
    k = stoch_rsi.rolling(k_smooth).mean()
    d = k.rolling(d_smooth).mean()
    return k, d


def resample(df, rule):
    df2 = df.set_index("date")
    ohlcv = df2[["open", "high", "low", "close", "volume"]].resample(rule).agg({
        "open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"
    }).dropna()
    return ohlcv.reset_index()


def get_peak(d2):
    d2_etf = d2[d2["date"] >= ETF_START]
    idx = d2_etf["close"].idxmax()
    return d2_etf.loc[idx, "date"], d2_etf.loc[idx, "close"]


def find_gated_crosses(w2, k_threshold, lookback_candles):
    """Find K cross below D events where K was > threshold within lookback candles."""
    w2_etf = w2[w2["date"] >= ETF_START].reset_index(drop=True)
    signals = []
    for i in range(1, len(w2_etf)):
        # Is this a K cross below D?
        if w2_etf.iloc[i]["k"] < w2_etf.iloc[i]["d"] and w2_etf.iloc[i-1]["k"] >= w2_etf.iloc[i-1]["d"]:
            # Was K > threshold within lookback candles?
            start = max(0, i - lookback_candles)
            recent_k_max = w2_etf.iloc[start:i+1]["k"].max()
            if recent_k_max > k_threshold:
                signals.append({
                    "date": w2_etf.iloc[i]["date"],
                    "price": w2_etf.iloc[i]["close"],
                    "k_at_cross": w2_etf.iloc[i]["k"],
                    "d_at_cross": w2_etf.iloc[i]["d"],
                    "recent_k_max": recent_k_max,
                })
    return signals


print("K x D CROSSOVER THRESHOLD TEST")
print("=" * 70)
print("Require K was above threshold within N candles before cross")
print()

# First show ALL crosses (unfiltered) for reference
for coin in COINS:
    base = coin.split("/")[0]
    df = load_daily(coin)
    w2 = resample(df, "2W")
    w2["k"], w2["d"] = compute_stochrsi(w2["close"])
    d2 = resample(df, "2D")
    peak_date, peak_price = get_peak(d2)
    
    print(f"\n{base} - Peak: {peak_date.strftime('%Y-%m-%d')} ${peak_price:.2f}")
    print(f"  ALL K x D crosses (unfiltered):")
    
    w2_etf = w2[w2["date"] >= ETF_START].reset_index(drop=True)
    for i in range(1, len(w2_etf)):
        if w2_etf.iloc[i]["k"] < w2_etf.iloc[i]["d"] and w2_etf.iloc[i-1]["k"] >= w2_etf.iloc[i-1]["d"]:
            row = w2_etf.iloc[i]
            # Find max K in last 5 candles
            start = max(0, i - 5)
            recent_max = w2_etf.iloc[start:i+1]["k"].max()
            days = (peak_date - row["date"]).days
            quality = "***" if recent_max > 93 else "**" if recent_max > 85 else "*" if recent_max > 75 else ""
            print(f"    {row['date'].strftime('%Y-%m-%d')} K={row['k']:.1f} D={row['d']:.1f} "
                  f"(max K in 5 candles: {recent_max:.1f}) ({days:+d}d) {quality}")

# Now test threshold × lookback matrix
print(f"\n\n{'='*70}")
print("THRESHOLD x LOOKBACK MATRIX")
print("Showing: signals / false (>20% rise after) / last signal timing")
print(f"{'='*70}")

THRESHOLDS = [80, 85, 90, 93, 95]
LOOKBACKS = [1, 2, 3, 5]

for k_thresh in THRESHOLDS:
    print(f"\n--- K must have been > {k_thresh} ---")
    print(f"  {'Lookback':>8} | ", end="")
    for coin in COINS:
        print(f"{coin.split('/')[0]:>12}", end="")
    print(f" | {'Total':>8} {'False%':>7}")
    
    for lb in LOOKBACKS:
        print(f"  {lb} candle{'s' if lb > 1 else ' ':1} | ", end="")
        total_sig = 0
        total_false = 0
        for coin in COINS:
            base = coin.split("/")[0]
            df = load_daily(coin)
            w2 = resample(df, "2W")
            w2["k"], w2["d"] = compute_stochrsi(w2["close"])
            d2 = resample(df, "2D")
            d2_etf = d2[d2["date"] >= ETF_START]
            peak_date, peak_price = get_peak(d2)
            
            signals = find_gated_crosses(w2, k_thresh, lb)
            
            # Count false: price rises >20% in 90d
            false_count = 0
            for s in signals:
                future = d2_etf[(d2_etf["date"] > s["date"]) & 
                               (d2_etf["date"] <= s["date"] + timedelta(days=90))]
                if len(future) > 0:
                    near = d2_etf[d2_etf["date"] <= s["date"]]
                    price_at = near["close"].iloc[-1] if len(near) > 0 else s["price"]
                    if price_at > 0 and (future["close"].max() / price_at - 1) > 0.20:
                        false_count += 1
            
            total_sig += len(signals)
            total_false += false_count
            
            # Last signal timing
            if signals:
                last_days = (peak_date - signals[-1]["date"]).days
                print(f"  {len(signals)}s/{false_count}f {last_days:+d}d", end="")
            else:
                print(f"     0s/0f    ", end="")
        
        false_pct = total_false / max(total_sig, 1) * 100
        print(f" | {total_sig:>4}sig {false_pct:5.0f}%")


# Best combos detail
print(f"\n\n{'='*70}")
print("DETAIL: Best Combos (K>90, lookback 3)")
print(f"{'='*70}")

for coin in COINS:
    base = coin.split("/")[0]
    df = load_daily(coin)
    w2 = resample(df, "2W")
    w2["k"], w2["d"] = compute_stochrsi(w2["close"])
    d2 = resample(df, "2D")
    peak_date, peak_price = get_peak(d2)
    
    print(f"\n  {base} (peak {peak_date.strftime('%Y-%m-%d')}):")
    for k_thresh in [85, 90, 93]:
        signals = find_gated_crosses(w2, k_thresh, 3)
        print(f"    K>{k_thresh}, 3 candle lookback: {len(signals)} signals")
        for s in signals:
            days = (peak_date - s["date"]).days
            print(f"      {s['date'].strftime('%Y-%m-%d')} K={s['k_at_cross']:.1f} D={s['d_at_cross']:.1f} "
                  f"(recent max K={s['recent_k_max']:.1f}, price=${s['price']:.2f})  ({days:+d}d)")
