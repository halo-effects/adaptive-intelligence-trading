"""
2W StochRSI Top Exhaustion Analysis
Mirror of bottom exhaustion (K<5 pinned, K crosses above D).
Top: K>95 pinned for N candles, then K crosses below D.

For each coin: find periods where 2W StochRSI K stays above threshold,
measure duration, find K cross below D, compare to actual price top.
"""

import sqlite3
import numpy as np
import pandas as pd
from datetime import datetime

DB = r"C:\Users\Never\.openclaw\workspace\trading\spot\data\candles.db"
COINS = ["ETH/USDT", "SOL/USDT", "BTC/USDT", "LINK/USDT", "XRP/USDT"]


def load_daily(coin):
    conn = sqlite3.connect(DB)
    df = pd.read_sql_query(
        f"SELECT * FROM candles_daily WHERE symbol='{coin}' ORDER BY timestamp", conn)
    conn.close()
    df["date"] = pd.to_datetime(df["timestamp"], unit="ms")
    return df


def resample_2w(df):
    df = df.set_index("date")
    ohlcv = df[["open", "high", "low", "close", "volume"]].resample("2W").agg({
        "open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"
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


for coin in COINS:
    base = coin.split("/")[0]
    print(f"\n{'='*70}")
    print(f"  {base} — 2W StochRSI Top Exhaustion")
    print(f"{'='*70}")

    df = load_daily(coin)
    w2 = resample_2w(df)
    w2["k"], w2["d"] = compute_stochrsi(w2["close"])

    print(f"  {len(w2)} 2W candles, {w2['date'].iloc[0].strftime('%Y-%m-%d')} to {w2['date'].iloc[-1].strftime('%Y-%m-%d')}")

    # Find overbought periods (K > threshold)
    for threshold in [90, 93, 95]:
        print(f"\n  --- K > {threshold} Exhaustion Periods ---")
        print(f"  {'Start':12} {'End':12} {'Candles':>7} {'Peak Price':>11} {'Peak Date':12} {'K xD Date':12} {'Price@xD':>10} {'Drop%':>7}")
        print(f"  {'-'*85}")

        ob = w2["k"] > threshold
        # Find contiguous groups
        groups = []
        in_group = False
        start_idx = None
        for i in range(len(w2)):
            if ob.iloc[i] and not in_group:
                in_group = True
                start_idx = i
            elif not ob.iloc[i] and in_group:
                in_group = False
                groups.append((start_idx, i - 1))
        if in_group:
            groups.append((start_idx, len(w2) - 1))

        for start_i, end_i in groups:
            n_candles = end_i - start_i + 1
            period = w2.iloc[start_i:end_i + 1]
            peak_idx = period["close"].idxmax()
            peak_price = w2.loc[peak_idx, "close"]
            peak_date = w2.loc[peak_idx, "date"].strftime("%Y-%m-%d")
            start_date = w2.iloc[start_i]["date"].strftime("%Y-%m-%d")
            end_date = w2.iloc[end_i]["date"].strftime("%Y-%m-%d")

            # Find K cross below D after this period
            cross_date = ""
            cross_price = ""
            drop_pct = ""
            for j in range(end_i + 1, min(end_i + 20, len(w2))):
                if w2.iloc[j]["k"] < w2.iloc[j]["d"] and (j == 0 or w2.iloc[j-1]["k"] >= w2.iloc[j-1]["d"]):
                    cross_date = w2.iloc[j]["date"].strftime("%Y-%m-%d")
                    cross_price = f"{w2.iloc[j]['close']:.2f}"
                    drop_pct = f"{(w2.iloc[j]['close'] / peak_price - 1) * 100:.1f}%"
                    break

            print(f"  {start_date:12} {end_date:12} {n_candles:7d} {peak_price:11.2f} {peak_date:12} {cross_date:12} {cross_price:>10} {drop_pct:>7}")

    # Show the actual K and D values around known tops for context
    print(f"\n  --- Recent 2W K/D Values ---")
    recent = w2.tail(20)
    print(f"  {'Date':12} {'Close':>10} {'K':>7} {'D':>7} {'K>D':>5}")
    for _, row in recent.iterrows():
        kgd = "YES" if row["k"] > row["d"] else "no"
        print(f"  {row['date'].strftime('%Y-%m-%d'):12} {row['close']:10.2f} {row['k']:7.1f} {row['d']:7.1f} {kgd:>5}")
