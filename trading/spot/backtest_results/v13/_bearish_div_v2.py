"""
Bearish Divergence v2 — Relaxed swing detection

v1 used 15-candle window which was too strict.
v2: use rolling highs with smaller windows and check divergence
between ANY two significant highs within 120 days of each other.
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


def resample(df, rule):
    df2 = df.set_index("date")
    ohlcv = df2[["open", "high", "low", "close", "volume"]].resample(rule).agg({
        "open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"
    }).dropna()
    return ohlcv.reset_index()


def find_swing_highs(df, window=7):
    """Swing high: higher than window candles on each side."""
    df = df.copy()
    df["is_swing"] = df["high"] == df["high"].rolling(window * 2 + 1, center=True).max()
    # Must have meaningful price (above rolling 50 SMA)
    df["sma50"] = df["close"].rolling(50).mean()
    return df[df["is_swing"] & (df["close"] > df["sma50"])].copy()


print("BEARISH DIVERGENCE v2 - RELAXED SWING DETECTION")
print("=" * 70)

for coin in COINS:
    base = coin.split("/")[0]
    df = load_daily(coin)
    
    for tf_label, tf_rule, swing_win in [("2D", "2D", 7), ("Weekly", "W", 5), ("2W", "2W", 4)]:
        d2 = resample(df, tf_rule)
        d2["rsi"] = compute_rsi(d2["close"], 14)
        d2["stoch_k"], d2["stoch_d"] = compute_stochrsi(d2["close"], 14, 14, 3, 3)
        d2["mfi"] = compute_mfi(d2["high"], d2["low"], d2["close"], d2["volume"], 14)
        
        d2_etf = d2[d2["date"] >= ETF_START].copy()
        peak_idx = d2_etf["high"].idxmax()
        peak_date = d2_etf.loc[peak_idx, "date"]
        peak_price = d2_etf.loc[peak_idx, "high"]
        
        swings = find_swing_highs(d2_etf, window=swing_win)
        
        if tf_label == "2D":
            print(f"\n{'='*70}")
            print(f"  {base} - Peak: {peak_date.strftime('%Y-%m-%d')} ${peak_price:.2f}")
            print(f"{'='*70}")
        
        # For each swing high, compare to ALL prior swing highs within 180 days
        # Find the strongest divergence
        best_divs = []
        for i in range(len(swings)):
            curr = swings.iloc[i]
            for j in range(i):
                prev = swings.iloc[j]
                gap_days = (curr["date"] - prev["date"]).days
                if gap_days > 180 or gap_days < 14:
                    continue
                if curr["high"] <= prev["high"]:
                    continue
                
                div_count = 0
                div_items = []
                if curr["rsi"] < prev["rsi"] - 2:  # meaningful divergence (>2pt)
                    div_count += 1
                    div_items.append(f"RSI({prev['rsi']:.0f}>{curr['rsi']:.0f})")
                if curr["mfi"] < prev["mfi"] - 2:
                    div_count += 1
                    div_items.append(f"MFI({prev['mfi']:.0f}>{curr['mfi']:.0f})")
                if curr["stoch_k"] < prev["stoch_k"] - 2:
                    div_count += 1
                    div_items.append(f"StoK({prev['stoch_k']:.0f}>{curr['stoch_k']:.0f})")
                
                if div_count >= 2:
                    best_divs.append({
                        "date": curr["date"],
                        "price": curr["high"],
                        "prev_date": prev["date"],
                        "prev_price": prev["high"],
                        "div_count": div_count,
                        "indicators": " ".join(div_items),
                        "gap_days": gap_days,
                    })
        
        # Deduplicate: keep strongest divergence per date
        seen_dates = {}
        for d in best_divs:
            key = d["date"]
            if key not in seen_dates or d["div_count"] > seen_dates[key]["div_count"]:
                seen_dates[key] = d
        unique_divs = sorted(seen_dates.values(), key=lambda x: x["date"])
        
        # Only show divergences where price is in top 30% of range
        price_range = d2_etf["high"].max() - d2_etf["high"].min()
        price_floor = d2_etf["high"].min() + price_range * 0.5
        
        top_divs = [d for d in unique_divs if d["price"] > price_floor]
        
        print(f"\n  [{tf_label}] {len(swings)} swings, {len(top_divs)} divergences (top 50% of price range):")
        for d in top_divs:
            days = (peak_date - d["date"]).days
            marker = " *** NEAR TOP ***" if abs(days) < 60 else ""
            print(f"    {d['date'].strftime('%Y-%m-%d')} ${d['price']:.2f} div={d['div_count']}/3 "
                  f"vs {d['prev_date'].strftime('%Y-%m-%d')} ${d['prev_price']:.2f} "
                  f"{d['indicators']} ({days:+d}d){marker}")


print(f"\n\n{'='*70}")
print("SUMMARY")
print(f"{'='*70}")
print("""
The key question: Does bearish divergence fire within 60 days of the actual peak?
And does it fire LESS often than Steve's score (reducing false positives)?
""")
