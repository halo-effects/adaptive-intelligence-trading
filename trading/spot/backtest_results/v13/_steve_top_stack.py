"""
Steve Courtney Top Conviction Stack - 2D Chart
Mirror of bottom 3-checkmarks:
  Bottom: below SMA200 + RSI<26 + StochRSI K&D<20
  Top:    above SMA200 + RSI>80 + StochRSI K&D>80 + MFI>80

Tests convergence (2/4, 3/4, 4/4) against known cycle tops.
Compares timing vs our current 2W StochRSI OB93 top detection.
"""

import sqlite3
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

DB = r"C:\Users\Never\.openclaw\workspace\trading\spot\data\candles.db"
COINS = ["ETH/USDT", "SOL/USDT", "BTC/USDT", "LINK/USDT", "XRP/USDT"]


def load_daily(coin):
    conn = sqlite3.connect(DB)
    df = pd.read_sql_query(
        f"SELECT * FROM candles_daily WHERE symbol='{coin}' ORDER BY timestamp",
        conn
    )
    conn.close()
    df["date"] = pd.to_datetime(df["timestamp"], unit="ms")
    return df


def resample_2d(df):
    """Resample daily OHLCV to 2-day candles."""
    df = df.set_index("date")
    ohlcv = df[["open", "high", "low", "close", "volume"]].resample("2D").agg({
        "open": "first",
        "high": "max",
        "low": "min",
        "close": "last",
        "volume": "sum"
    }).dropna()
    return ohlcv.reset_index()


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
    """Money Flow Index - volume-weighted RSI."""
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


def analyze_coin(coin):
    print(f"\n{'='*60}")
    print(f"  {coin}")
    print(f"{'='*60}")

    df = load_daily(coin)
    if len(df) < 500:
        print(f"  Only {len(df)} daily candles, need 500+ for 2D SMA200")
        return None

    # Resample to 2D
    d2 = resample_2d(df)
    print(f"  {len(df)} daily -> {len(d2)} 2D candles")
    print(f"  Range: {d2['date'].iloc[0].strftime('%Y-%m-%d')} to {d2['date'].iloc[-1].strftime('%Y-%m-%d')}")

    # Compute indicators on 2D
    d2["sma200"] = compute_sma(d2["close"], 200)
    d2["rsi"] = compute_rsi(d2["close"], 14)
    d2["stoch_k"], d2["stoch_d"] = compute_stochrsi(d2["close"], 14, 14, 3, 3)
    d2["mfi"] = compute_mfi(d2["high"], d2["low"], d2["close"], d2["volume"], 14)

    # Top signals (each is boolean)
    d2["above_sma200"] = d2["close"] > d2["sma200"]
    d2["rsi_ob"] = d2["rsi"] > 80
    d2["stoch_ob"] = (d2["stoch_k"] > 80) & (d2["stoch_d"] > 80)
    d2["mfi_ob"] = d2["mfi"] > 80

    # Score
    d2["score"] = (
        d2["above_sma200"].astype(int) +
        d2["rsi_ob"].astype(int) +
        d2["stoch_ob"].astype(int) +
        d2["mfi_ob"].astype(int)
    )

    # Show all dates where score >= 2
    print(f"\n  Signal hits (score >= 2):")
    print(f"  {'Date':12} {'Close':>10} {'SMA200':>10} {'RSI':>6} {'StoK':>6} {'StoD':>6} {'MFI':>6} {'Score':>5}")
    print(f"  {'-'*68}")

    hits = d2[d2["score"] >= 2].copy()
    # Group consecutive hits (within 10 days)
    if len(hits) > 0:
        hits["group"] = (hits["date"].diff() > timedelta(days=10)).cumsum()
        for grp, gdf in hits.groupby("group"):
            peak_row = gdf.loc[gdf["score"].idxmax()]
            for _, row in gdf.iterrows():
                marker = " <-- PEAK" if row.name == peak_row.name else ""
                print(f"  {row['date'].strftime('%Y-%m-%d'):12} {row['close']:10.2f} {row['sma200']:10.2f} "
                      f"{row['rsi']:6.1f} {row['stoch_k']:6.1f} {row['stoch_d']:6.1f} {row['mfi']:6.1f} {row['score']:5.0f}{marker}")
            print()
    else:
        print("  No hits found")

    # Also show 3/4 and 4/4 counts
    for thresh in [2, 3, 4]:
        count = (d2["score"] >= thresh).sum()
        print(f"  Score >= {thresh}: {count} candles")

    # Find actual price peaks (local max within 60-day window)
    d2["peak"] = d2["close"] == d2["close"].rolling(61, center=True).max()
    peaks = d2[d2["peak"] & (d2["close"] > d2["sma200"])].copy()
    if len(peaks) > 0:
        # Only keep peaks that are real tops (>20% above SMA200 or significant)
        peaks = peaks[peaks["close"] > peaks["sma200"] * 1.1]
        print(f"\n  Major price peaks (>10% above SMA200):")
        for _, row in peaks.iterrows():
            pct_above = (row["close"] / row["sma200"] - 1) * 100
            print(f"  {row['date'].strftime('%Y-%m-%d'):12} {row['close']:10.2f} (+{pct_above:.1f}% above SMA200)  "
                  f"RSI={row['rsi']:.1f} StoK={row['stoch_k']:.1f} MFI={row['mfi']:.1f} Score={row['score']:.0f}")

    return d2


def compare_vs_current_top(d2, coin):
    """Compare Steve top stack vs our current 2W StochRSI OB93."""
    print(f"\n  --- vs Current 2W OB93 Top Detection ---")

    # Resample to 2W from our daily data
    df = load_daily(coin)
    df["date"] = pd.to_datetime(df["timestamp"], unit="ms")
    df = df.set_index("date")
    w2 = df[["open", "high", "low", "close", "volume"]].resample("2W").agg({
        "open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"
    }).dropna().reset_index()

    w2["stoch_k"], w2["stoch_d"] = compute_stochrsi(w2["close"], 14, 14, 3, 3)
    w2["ob93"] = w2["stoch_k"] > 93

    print(f"  2W OB93 triggers:")
    ob_hits = w2[w2["ob93"]]
    if len(ob_hits) > 0:
        for _, row in ob_hits.iterrows():
            print(f"    {row['date'].strftime('%Y-%m-%d'):12} Close={row['close']:.2f} K={row['stoch_k']:.1f}")
    else:
        print(f"    None found")


# ETF era filter: Jan 2023+
print("STEVE COURTNEY TOP CONVICTION STACK - 2D CHART")
print("=" * 60)
print("Signals: Above SMA200 + RSI>80 + StochRSI K&D>80 + MFI>80")
print("Testing convergence thresholds: 2/4, 3/4, 4/4")
print()

# Also test relaxed thresholds
THRESHOLDS = {
    "strict": {"rsi": 80, "stoch": 80, "mfi": 80},
    "moderate": {"rsi": 74, "stoch": 75, "mfi": 75},
    "relaxed": {"rsi": 70, "stoch": 70, "mfi": 70},
}

for coin in COINS:
    d2 = analyze_coin(coin)
    if d2 is not None:
        compare_vs_current_top(d2, coin)

# Summary: test moderate/relaxed thresholds too
print(f"\n{'='*60}")
print("THRESHOLD SENSITIVITY")
print(f"{'='*60}")
for label, thresh in THRESHOLDS.items():
    print(f"\n  --- {label}: RSI>{thresh['rsi']}, StochRSI>{thresh['stoch']}, MFI>{thresh['mfi']} ---")
    for coin in COINS:
        df = load_daily(coin)
        if len(df) < 500:
            continue
        d2 = resample_2d(df)
        d2["sma200"] = compute_sma(d2["close"], 200)
        d2["rsi"] = compute_rsi(d2["close"], 14)
        d2["stoch_k"], d2["stoch_d"] = compute_stochrsi(d2["close"], 14, 14, 3, 3)
        d2["mfi"] = compute_mfi(d2["high"], d2["low"], d2["close"], d2["volume"], 14)

        score = (
            (d2["close"] > d2["sma200"]).astype(int) +
            (d2["rsi"] > thresh["rsi"]).astype(int) +
            ((d2["stoch_k"] > thresh["stoch"]) & (d2["stoch_d"] > thresh["stoch"])).astype(int) +
            (d2["mfi"] > thresh["mfi"]).astype(int)
        )
        base = coin.split("/")[0]
        for s in [2, 3, 4]:
            print(f"    {base}: score >= {s}: {(score >= s).sum()} candles")
