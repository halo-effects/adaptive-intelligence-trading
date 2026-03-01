"""
Divergence Confirmation Signal Analysis

After 2D divergence arms the system, what signals confirm the top has actually arrived?

Candidates:
1. Price drops X% from post-divergence high (trailing stop)
2. Daily SMA50 cross below (price or SMA200)  
3. ADX < 20 sustained (ranging = momentum gone)
4. LH_LL structure appears (bearish structure)
5. Weekly StochRSI K crosses below threshold (80, 70, 50)
6. Price loses Bull Market Support Band
7. Daily RSI drops below 50 (momentum flip)
8. 1W K×D bearish cross

For each coin: track divergence arm date, actual top, and when each
confirmation signal fires. Find what consistently fires AFTER the top
but BEFORE too much downside.
"""

import sqlite3
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

DB = r"C:\Users\Never\.openclaw\workspace\trading\spot\data\candles.db"

# Known tops and first divergence dates (from our testing)
ANALYSIS = {
    "ETH": {
        "div_date": "2024-11-12", "top_date": "2024-12-06", "top_price": 4107,
        "symbol": "ETH/USDT"
    },
    "SOL": {
        "div_date": "2024-11-25", "top_date": "2025-01-19", "top_price": 294,  
        "symbol": "SOL/USDT"
    },
    "BTC": {
        "div_date": "2024-11-25", "top_date": "2025-01-20", "top_price": 109350,
        "symbol": "BTC/USDT"
    },
    "LINK": {
        "div_date": "2024-12-08", "top_date": "2024-12-08", "top_price": 30.8,
        "symbol": "LINK/USDT"
    },
    "XRP": {
        "div_date": "2024-12-03", "top_date": "2025-01-16", "top_price": 3.39,
        "symbol": "XRP/USDT"
    },
}


def load_daily(symbol):
    conn = sqlite3.connect(DB)
    df = pd.read_sql_query(
        f"SELECT * FROM candles_daily WHERE symbol='{symbol}' ORDER BY timestamp", conn)
    conn.close()
    df["date"] = pd.to_datetime(df["timestamp"], unit="ms")
    df = df.set_index("date")
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


def resample_weekly(df):
    return df[["open", "high", "low", "close", "volume"]].resample("W").agg({
        "open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"
    }).dropna()


def analyze_coin(coin, info):
    df = load_daily(info["symbol"])
    div_date = pd.Timestamp(info["div_date"])
    top_date = pd.Timestamp(info["top_date"])
    top_price = info["top_price"]
    
    # Compute daily indicators
    df["sma20"] = df["close"].rolling(20).mean()
    df["sma50"] = df["close"].rolling(50).mean()
    df["sma200"] = df["close"].rolling(200).mean()
    df["rsi"] = compute_rsi(df["close"], 14)
    df["ema21w"] = df["close"].ewm(span=147).mean()
    
    # ADX
    df["tr"] = np.maximum(df["high"] - df["low"],
        np.maximum(abs(df["high"] - df["close"].shift(1)),
                   abs(df["low"] - df["close"].shift(1))))
    df["atr14"] = df["tr"].rolling(14).mean()
    plus_dm = (df["high"] - df["high"].shift(1)).where(
        (df["high"] - df["high"].shift(1)) > (df["low"].shift(1) - df["low"]), 0).clip(lower=0)
    minus_dm = (df["low"].shift(1) - df["low"]).where(
        (df["low"].shift(1) - df["low"]) > (df["high"] - df["high"].shift(1)), 0).clip(lower=0)
    plus_di = 100 * (plus_dm.rolling(14).mean() / df["atr14"])
    minus_di = 100 * (minus_dm.rolling(14).mean() / df["atr14"])
    dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di)
    df["adx"] = dx.rolling(14).mean()
    
    # HH/HL and LH/LL
    df["high_20"] = df["high"].rolling(20).max()
    df["low_20"] = df["low"].rolling(20).min()
    df["prev_high_20"] = df["high_20"].shift(20)
    df["prev_low_20"] = df["low_20"].shift(20)
    df["hh"] = df["high_20"] > df["prev_high_20"]
    df["lh"] = df["high_20"] < df["prev_high_20"]
    df["hl"] = df["low_20"] > df["prev_low_20"]
    df["ll"] = df["low_20"] < df["prev_low_20"]
    
    # Weekly StochRSI
    df_w = resample_weekly(df)
    k_w, d_w = compute_stochrsi(df_w["close"])
    df_w["stoch_k"] = k_w
    df_w["stoch_d"] = d_w
    
    # Analysis window: from divergence to 90 days after top
    window_start = div_date
    window_end = top_date + timedelta(days=90)
    window = df[(df.index >= window_start) & (df.index <= window_end)]
    
    # Track post-divergence high
    post_div = df[df.index >= div_date]
    running_high = post_div["high"].expanding().max()
    
    print(f"\n{'='*70}")
    print(f"  {coin} — Div armed: {info['div_date']}, Top: {info['top_date']} @ ${top_price:,}")
    print(f"  Gap: {(top_date - div_date).days} days between divergence and actual top")
    print(f"{'='*70}")
    
    # For each confirmation signal, find FIRST date it fires after divergence
    confirms = {}
    
    # 1. Trailing stop: price drops X% from post-div high
    for pct in [5, 8, 10, 15]:
        for i, (dt, row) in enumerate(post_div.iterrows()):
            high_so_far = running_high.iloc[i]
            drop = (row["close"] - high_so_far) / high_so_far * 100
            if drop <= -pct:
                days_from_top = (dt - top_date).days
                price_at_signal = row["close"]
                price_loss = (price_at_signal - top_price) / top_price * 100
                confirms[f"Trail_{pct}%"] = {
                    "date": dt, "days_from_top": days_from_top,
                    "price": price_at_signal, "price_loss": price_loss
                }
                break
    
    # 2. Price drops below SMA50
    for dt, row in post_div.iterrows():
        if not np.isnan(row["sma50"]) and row["close"] < row["sma50"]:
            days_from_top = (dt - top_date).days
            confirms["Below_SMA50"] = {
                "date": dt, "days_from_top": days_from_top,
                "price": row["close"], "price_loss": (row["close"] - top_price) / top_price * 100
            }
            break
    
    # 3. Daily RSI < 50
    for dt, row in post_div.iterrows():
        if not np.isnan(row["rsi"]) and row["rsi"] < 50:
            days_from_top = (dt - top_date).days
            confirms["RSI_below_50"] = {
                "date": dt, "days_from_top": days_from_top,
                "price": row["close"], "price_loss": (row["close"] - top_price) / top_price * 100
            }
            break
    
    # 4. Daily RSI < 40
    for dt, row in post_div.iterrows():
        if not np.isnan(row["rsi"]) and row["rsi"] < 40:
            days_from_top = (dt - top_date).days
            confirms["RSI_below_40"] = {
                "date": dt, "days_from_top": days_from_top,
                "price": row["close"], "price_loss": (row["close"] - top_price) / top_price * 100
            }
            break
    
    # 5. ADX < 20 (ranging)
    adx_streak = 0
    for dt, row in post_div.iterrows():
        if not np.isnan(row["adx"]) and row["adx"] < 20:
            adx_streak += 1
            if adx_streak >= 7:  # 7 days sustained
                days_from_top = (dt - top_date).days
                confirms["ADX_below_20_7d"] = {
                    "date": dt, "days_from_top": days_from_top,
                    "price": row["close"], "price_loss": (row["close"] - top_price) / top_price * 100
                }
                break
        else:
            adx_streak = 0
    
    # 6. LH+LL (bearish structure)
    for dt, row in post_div.iterrows():
        if row.get("lh", False) and row.get("ll", False):
            days_from_top = (dt - top_date).days
            confirms["LH_LL"] = {
                "date": dt, "days_from_top": days_from_top,
                "price": row["close"], "price_loss": (row["close"] - top_price) / top_price * 100
            }
            break
    
    # 7. Weekly K drops below thresholds
    post_div_w = df_w[df_w.index >= div_date]
    for thresh in [80, 70, 50]:
        for dt, row in post_div_w.iterrows():
            if not np.isnan(row["stoch_k"]) and row["stoch_k"] < thresh:
                days_from_top = (dt - top_date).days
                # Get daily close nearest to this weekly date
                daily_near = df[df.index <= dt].tail(1)
                p = daily_near["close"].iloc[0] if len(daily_near) > 0 else 0
                confirms[f"1W_K_below_{thresh}"] = {
                    "date": dt, "days_from_top": days_from_top,
                    "price": p, "price_loss": (p - top_price) / top_price * 100
                }
                break
    
    # 8. Price loses BMSB (20w SMA)
    for dt, row in post_div.iterrows():
        sma_20w = row["close"]  # approximate with ema21w
        if not np.isnan(row.get("ema21w", np.nan)) and row["close"] < row["ema21w"]:
            days_from_top = (dt - top_date).days
            confirms["Lost_BMSB"] = {
                "date": dt, "days_from_top": days_from_top,
                "price": row["close"], "price_loss": (row["close"] - top_price) / top_price * 100
            }
            break
    
    # Print results sorted by timing
    sorted_confirms = sorted(confirms.items(), key=lambda x: x[1]["days_from_top"])
    
    print(f"\n  {'Signal':<20s} {'Date':>12s} {'Days from top':>14s} {'Price':>12s} {'Loss from top':>14s}")
    print(f"  {'-'*74}")
    for name, c in sorted_confirms:
        marker = " <-- BEST" if c["days_from_top"] >= 0 and c["price_loss"] > -15 else ""
        if c["days_from_top"] < 0:
            marker = " (before top!)"
        print(f"  {name:<20s} {c['date'].strftime('%Y-%m-%d'):>12s} {c['days_from_top']:>+12d}d {c['price']:>12,.1f} {c['price_loss']:>+12.1f}%{marker}")
    
    return confirms


# ============================================================
# Run analysis
# ============================================================
print("=" * 70)
print("DIVERGENCE CONFIRMATION SIGNAL ANALYSIS")
print("What fires AFTER divergence arms, confirming the top is in?")
print("=" * 70)

all_confirms = {}
for coin, info in ANALYSIS.items():
    all_confirms[coin] = analyze_coin(coin, info)

# Summary: which signals fire after the top with least damage?
print(f"\n{'='*70}")
print("SUMMARY — Best confirmation signals (fire after top, least price loss)")
print(f"{'='*70}")

# For each signal, check across all coins
signal_names = set()
for c in all_confirms.values():
    signal_names.update(c.keys())

print(f"\n  {'Signal':<20s} {'Coins':>6s} {'Avg days':>9s} {'Avg loss':>9s} {'After top?':>10s}")
print(f"  {'-'*58}")

for sig in sorted(signal_names):
    coins_with = []
    days_list = []
    loss_list = []
    after_top = 0
    for coin, confirms in all_confirms.items():
        if sig in confirms:
            coins_with.append(coin)
            d = confirms[sig]["days_from_top"]
            days_list.append(d)
            loss_list.append(confirms[sig]["price_loss"])
            if d >= 0:
                after_top += 1
    
    if len(coins_with) < 3:
        continue  # Skip signals that don't fire for most coins
    
    avg_days = sum(days_list) / len(days_list)
    avg_loss = sum(loss_list) / len(loss_list)
    
    print(f"  {sig:<20s} {len(coins_with):>4d}/5 {avg_days:>+8.0f}d {avg_loss:>+8.1f}% {after_top:>8d}/5")
