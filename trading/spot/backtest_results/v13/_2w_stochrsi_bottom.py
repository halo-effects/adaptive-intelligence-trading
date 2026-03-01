"""
2W StochRSI Bottom Exhaustion Validation

Symmetric to 2W OB93 top detection:
- Bottom: K < 5 pinned for N 2W candles, then K crosses above D
- Measure timing vs actual bottoms for ETH, SOL, LINK, XRP, BTC

Parameters: RSI(14), Stochastic(14), K smooth 3, D smooth 3
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
        "SELECT * FROM candles_daily WHERE symbol=? ORDER BY timestamp",
        conn, params=[coin])
    conn.close()
    df["date"] = pd.to_datetime(df["timestamp"], unit="ms")
    return df


def resample_2w(df):
    df2 = df.set_index("date")
    ohlcv = df2[["open", "high", "low", "close", "volume"]].resample("2W").agg({
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


print("2W STOCHRSI BOTTOM EXHAUSTION VALIDATION")
print("=" * 70)
print("Signal: K < threshold pinned for N candles, then K crosses above D")
print()

for coin in COINS:
    base = coin.split("/")[0]
    df = load_daily(coin)
    w2 = resample_2w(df)
    w2["k"], w2["d"] = compute_stochrsi(w2["close"])
    
    print(f"\n{'='*70}")
    print(f"  {base}")
    print(f"{'='*70}")
    print(f"  {len(w2)} 2W candles: {w2['date'].iloc[0].strftime('%Y-%m-%d')} to {w2['date'].iloc[-1].strftime('%Y-%m-%d')}")
    
    # Find actual bottoms (local min in 90-day window, >20% below prior high)
    daily_etf = df[df["date"] >= "2020-01-01"].copy()
    daily_etf["roll_min"] = daily_etf["low"].rolling(61, center=True).min()
    daily_etf["is_bottom"] = daily_etf["low"] == daily_etf["roll_min"]
    bottoms = daily_etf[daily_etf["is_bottom"]].copy()
    # Keep significant ones
    sig_bottoms = []
    for _, row in bottoms.iterrows():
        prior = daily_etf[daily_etf["date"] < row["date"]]
        if len(prior) > 30:
            prior_high = prior["high"].rolling(90).max().iloc[-1]
            if prior_high > 0 and (row["low"] / prior_high - 1) < -0.25:
                sig_bottoms.append({"date": row["date"], "price": row["low"]})
    
    # Deduplicate bottoms within 60 days
    deduped = []
    for b in sig_bottoms:
        if not deduped or (b["date"] - deduped[-1]["date"]).days > 60:
            deduped.append(b)
    
    print(f"\n  Significant bottoms (>25% drawdown):")
    for b in deduped:
        dt_str = b["date"].strftime("%Y-%m-%d")
        print(f"    {dt_str} ${b['price']:.2f}")
    
    # Test thresholds
    for threshold in [5, 10, 15, 20]:
        print(f"\n  --- K < {threshold} Oversold Periods ---")
        print(f"  {'Start':12} {'End':12} {'Candles':>7} {'Low Price':>10} {'KxD Date':12} {'Price@KxD':>10} {'Nearest Bottom':>16} {'Gap Days':>8}")
        print(f"  {'-'*95}")
        
        os = w2["k"] < threshold
        groups = []
        in_group = False
        start_idx = None
        for i in range(len(w2)):
            if os.iloc[i] and not in_group:
                in_group = True
                start_idx = i
            elif not os.iloc[i] and in_group:
                in_group = False
                groups.append((start_idx, i - 1))
        if in_group:
            groups.append((start_idx, len(w2) - 1))
        
        for start_i, end_i in groups:
            n_candles = end_i - start_i + 1
            period_data = w2.iloc[start_i:end_i + 1]
            low_price = period_data["close"].min()
            start_date = w2.iloc[start_i]["date"]
            end_date = w2.iloc[end_i]["date"]
            
            # Find K cross above D after this period
            cross_date_str = ""
            cross_price = ""
            cross_dt = None
            for j in range(end_i + 1, min(end_i + 20, len(w2))):
                if w2.iloc[j]["k"] > w2.iloc[j]["d"]:
                    if j == 0 or w2.iloc[j-1]["k"] <= w2.iloc[j-1]["d"]:
                        cross_dt = w2.iloc[j]["date"]
                        cross_date_str = cross_dt.strftime("%Y-%m-%d")
                        cross_price = f"${w2.iloc[j]['close']:.2f}"
                        break
            
            # Find nearest actual bottom
            nearest = ""
            gap = ""
            ref_date = cross_dt if cross_dt else end_date
            if deduped:
                closest = min(deduped, key=lambda b: abs((b["date"] - ref_date).days))
                nearest = closest["date"].strftime("%Y-%m-%d")
                gap_days = (ref_date - closest["date"]).days
                gap = f"{gap_days:+d}d"
            
            print(f"  {start_date.strftime('%Y-%m-%d'):12} {end_date.strftime('%Y-%m-%d'):12} "
                  f"{n_candles:7d} {low_price:10.2f} {cross_date_str:12} {cross_price:>10} "
                  f"{nearest:>16} {gap:>8}")

    # Current status
    latest = w2.iloc[-5:]
    print(f"\n  Current 2W K/D:")
    for _, row in latest.iterrows():
        kgd = "K>D" if row["k"] > row["d"] else "K<D"
        print(f"    {row['date'].strftime('%Y-%m-%d')} Close=${row['close']:.2f} K={row['k']:.1f} D={row['d']:.1f} {kgd}")
