"""
Bearish Divergence Top Detection

Price makes higher high, but RSI/MFI/StochRSI make lower high = distribution.
This catches the actual peak that Steve's blow-off score misses.

Method:
1. On 2D chart, find each new price high (higher than prev swing high)
2. Compare RSI/MFI at that price high vs RSI/MFI at previous price high
3. If price HH but indicator LH = bearish divergence
4. Score: count how many indicators show divergence (RSI, MFI, StochRSI)

ETF era, 4 paper bot coins.
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


def compute_mfi(high, low, close, volume, period=14):
    typical_price = (high + low + close) / 3
    money_flow = typical_price * volume
    delta = typical_price.diff()
    pos_flow = money_flow.where(delta > 0, 0.0)
    neg_flow = money_flow.where(delta < 0, 0.0)
    pos_sum = pos_flow.rolling(period).sum()
    neg_sum = neg_flow.rolling(period).sum()
    mfi = 100 - (100 / (1 + pos_sum / neg_sum.replace(0, 1e-10)))
    return mfi


def compute_sma(series, period):
    return series.rolling(period).mean()


def resample(df, rule):
    df2 = df.set_index("date")
    ohlcv = df2[["open", "high", "low", "close", "volume"]].resample(rule).agg({
        "open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"
    }).dropna()
    return ohlcv.reset_index()


def find_swing_highs(df, window=15):
    """Find swing highs: local maxima in rolling window."""
    df = df.copy()
    df["swing_high"] = df["high"] == df["high"].rolling(window * 2 + 1, center=True).max()
    # Must be above SMA50 (in an uptrend)
    df["sma50"] = compute_sma(df["close"], 50)
    df["valid"] = df["swing_high"] & (df["close"] > df["sma50"])
    return df[df["valid"]].copy()


def detect_divergences(d2, swing_highs):
    """Detect bearish divergences between consecutive swing highs."""
    divergences = []
    
    for i in range(1, len(swing_highs)):
        prev = swing_highs.iloc[i-1]
        curr = swing_highs.iloc[i]
        
        # Price must make higher high
        if curr["high"] <= prev["high"]:
            continue
        
        # Check each indicator for lower high (divergence)
        div_count = 0
        div_indicators = []
        
        if curr["rsi"] < prev["rsi"]:
            div_count += 1
            div_indicators.append(f"RSI({prev['rsi']:.0f}->{curr['rsi']:.0f})")
        
        if curr["mfi"] < prev["mfi"]:
            div_count += 1
            div_indicators.append(f"MFI({prev['mfi']:.0f}->{curr['mfi']:.0f})")
        
        if curr["stoch_k"] < prev["stoch_k"]:
            div_count += 1
            div_indicators.append(f"StoK({prev['stoch_k']:.0f}->{curr['stoch_k']:.0f})")
        
        if div_count > 0:
            divergences.append({
                "date": curr["date"],
                "price": curr["high"],
                "prev_date": prev["date"],
                "prev_price": prev["high"],
                "div_count": div_count,
                "indicators": ", ".join(div_indicators),
                "rsi": curr["rsi"],
                "mfi": curr["mfi"],
                "stoch_k": curr["stoch_k"],
            })
    
    return divergences


print("BEARISH DIVERGENCE TOP DETECTION")
print("=" * 70)
print("Price Higher High + Indicator Lower High = Distribution")
print()

for coin in COINS:
    base = coin.split("/")[0]
    df = load_daily(coin)
    d2 = resample(df, "2D")
    
    # Compute indicators
    d2["rsi"] = compute_rsi(d2["close"], 14)
    d2["stoch_k"], d2["stoch_d"] = compute_stochrsi(d2["close"], 14, 14, 3, 3)
    d2["mfi"] = compute_mfi(d2["high"], d2["low"], d2["close"], d2["volume"], 14)
    d2["sma200"] = compute_sma(d2["close"], 200)
    
    # Filter to ETF era
    d2_etf = d2[d2["date"] >= ETF_START].copy()
    
    # Find actual peak
    peak_idx = d2_etf["high"].idxmax()
    peak_date = d2_etf.loc[peak_idx, "date"]
    peak_price = d2_etf.loc[peak_idx, "high"]
    
    print(f"\n{'='*70}")
    print(f"  {base} - Peak: {peak_date.strftime('%Y-%m-%d')} ${peak_price:.2f}")
    print(f"{'='*70}")
    
    # Find swing highs
    swings = find_swing_highs(d2_etf, window=15)
    print(f"  Found {len(swings)} swing highs")
    
    # Detect divergences
    divs = detect_divergences(d2_etf, swings)
    
    # Filter to significant ones (price above SMA200, div_count >= 2)
    print(f"\n  All divergences (div >= 2, above SMA200):")
    print(f"  {'Date':12} {'Price':>10} {'Prev':>10} {'#Div':>5} {'Indicators':40} {'Days to Peak':>12}")
    print(f"  {'-'*95}")
    
    sig_divs = [d for d in divs if d["div_count"] >= 2]
    for d in sig_divs:
        days = (peak_date - d["date"]).days
        # Check if above SMA200
        row = d2_etf[d2_etf["date"] == d["date"]]
        if len(row) > 0 and not np.isnan(row.iloc[0]["sma200"]):
            if row.iloc[0]["close"] <= row.iloc[0]["sma200"]:
                continue
        marker = " <-- NEAR TOP" if abs(days) < 60 else ""
        print(f"  {d['date'].strftime('%Y-%m-%d'):12} {d['price']:10.2f} {d['prev_price']:10.2f} "
              f"{d['div_count']:5d} {d['indicators']:40} {days:+12d}{marker}")
    
    # Triple divergence (all 3 indicators)
    triple = [d for d in divs if d["div_count"] == 3]
    print(f"\n  TRIPLE divergence (all 3: RSI + MFI + StochRSI):")
    if triple:
        for d in triple:
            days = (peak_date - d["date"]).days
            marker = " <-- NEAR TOP" if abs(days) < 60 else ""
            print(f"    {d['date'].strftime('%Y-%m-%d')} ${d['price']:.2f} "
                  f"(prev: {d['prev_date'].strftime('%Y-%m-%d')} ${d['prev_price']:.2f}) "
                  f"({days:+d}d){marker}")
    else:
        print(f"    None found")

    # Show what happened at the actual peak — was there divergence?
    print(f"\n  At actual peak ({peak_date.strftime('%Y-%m-%d')}):")
    peak_row = d2_etf.loc[peak_idx]
    # Find the previous swing high before peak
    prior_swings = swings[swings["date"] < peak_date - timedelta(days=14)]
    if len(prior_swings) > 0:
        prev_sw = prior_swings.iloc[-1]
        div_items = []
        if peak_row["rsi"] < prev_sw["rsi"]:
            div_items.append(f"RSI: {prev_sw['rsi']:.0f} -> {peak_row['rsi']:.0f} (DIVERGING)")
        else:
            div_items.append(f"RSI: {prev_sw['rsi']:.0f} -> {peak_row['rsi']:.0f} (confirming)")
        if peak_row["mfi"] < prev_sw["mfi"]:
            div_items.append(f"MFI: {prev_sw['mfi']:.0f} -> {peak_row['mfi']:.0f} (DIVERGING)")
        else:
            div_items.append(f"MFI: {prev_sw['mfi']:.0f} -> {peak_row['mfi']:.0f} (confirming)")
        if peak_row["stoch_k"] < prev_sw["stoch_k"]:
            div_items.append(f"StoK: {prev_sw['stoch_k']:.0f} -> {peak_row['stoch_k']:.0f} (DIVERGING)")
        else:
            div_items.append(f"StoK: {prev_sw['stoch_k']:.0f} -> {peak_row['stoch_k']:.0f} (confirming)")
        
        print(f"    vs prior swing {prev_sw['date'].strftime('%Y-%m-%d')} ${prev_sw['high']:.2f}:")
        for item in div_items:
            print(f"      {item}")


# Also test on 2W timeframe
print(f"\n\n{'='*70}")
print("2W TIMEFRAME DIVERGENCE")
print(f"{'='*70}")

for coin in COINS:
    base = coin.split("/")[0]
    df = load_daily(coin)
    w2 = resample(df, "2W")
    
    w2["rsi"] = compute_rsi(w2["close"], 14)
    w2["stoch_k"], w2["stoch_d"] = compute_stochrsi(w2["close"], 14, 14, 3, 3)
    w2["mfi"] = compute_mfi(w2["high"], w2["low"], w2["close"], w2["volume"], 14)
    w2["sma50"] = compute_sma(w2["close"], 50)
    
    w2_etf = w2[w2["date"] >= ETF_START].copy()
    
    peak_idx = w2_etf["high"].idxmax()
    peak_date = w2_etf.loc[peak_idx, "date"]
    peak_price = w2_etf.loc[peak_idx, "high"]
    
    print(f"\n  {base} - Peak: {peak_date.strftime('%Y-%m-%d')} ${peak_price:.2f}")
    
    # Find swing highs on 2W (smaller window)
    swings = find_swing_highs(w2_etf, window=5)
    divs = detect_divergences(w2_etf, swings)
    
    triple = [d for d in divs if d["div_count"] >= 2]
    if triple:
        for d in triple:
            days = (peak_date - d["date"]).days
            marker = " <-- NEAR TOP" if abs(days) < 90 else ""
            print(f"    {d['date'].strftime('%Y-%m-%d')} ${d['price']:.2f} div={d['div_count']}/3 "
                  f"{d['indicators']} ({days:+d}d){marker}")
    else:
        print(f"    No divergences >= 2 found")
