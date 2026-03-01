"""
CFGI as top gate - does extreme greed filter false tops?

Test: Add coin-specific CFGI > X to the top stack.
Bottom uses CFGI < 35. Top mirror: CFGI > 70, 75, 80.

Also test: Weekly CFGI RSI(7) > 60/70/80 (mirror of < 40 on bottom).
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


def load_cfgi(coin):
    base = coin.split("/")[0].upper()
    conn = sqlite3.connect(DB)
    df = pd.read_sql_query(
        f"SELECT * FROM cfgi_daily WHERE symbol LIKE '{base}%' ORDER BY date", conn)
    conn.close()
    if len(df) == 0:
        return pd.DataFrame()
    df["date"] = pd.to_datetime(df["date"], format="mixed")
    df = df.rename(columns={"value": "cfgi"})
    return df[["date", "cfgi"]].drop_duplicates("date").sort_values("date")


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


def get_peak(d2):
    d2_etf = d2[d2["date"] >= ETF_START]
    idx = d2_etf["close"].idxmax()
    return d2_etf.loc[idx, "date"], d2_etf.loc[idx, "close"]


print("CFGI AS TOP GATE")
print("=" * 70)

for coin in COINS:
    base = coin.split("/")[0]
    df = load_daily(coin)
    cfgi_df = load_cfgi(coin)
    
    d2 = resample(df, "2D")
    d2["sma200"] = d2["close"].rolling(200).mean()
    d2["rsi"] = compute_rsi(d2["close"], 14)
    d2["stoch_k"], d2["stoch_d"] = compute_stochrsi(d2["close"], 14, 14, 3, 3)
    d2["mfi"] = compute_mfi(d2["high"], d2["low"], d2["close"], d2["volume"], 14)
    d2["score"] = (
        (d2["close"] > d2["sma200"]).astype(int) +
        (d2["rsi"] > 80).astype(int) +
        ((d2["stoch_k"] > 80) & (d2["stoch_d"] > 80)).astype(int) +
        (d2["mfi"] > 80).astype(int)
    )
    
    peak_date, peak_price = get_peak(d2)
    
    print(f"\n{'='*70}")
    print(f"  {base} - Peak: {peak_date.strftime('%Y-%m-%d')} ${peak_price:.2f}")
    print(f"{'='*70}")
    
    if len(cfgi_df) == 0:
        print(f"  No CFGI data!")
        continue
    
    # Merge CFGI with 2D data (nearest date)
    d2_etf = d2[d2["date"] >= ETF_START].copy()
    
    # For each 2D candle, find nearest CFGI value
    cfgi_df = cfgi_df.set_index("date")
    d2_etf = d2_etf.set_index("date")
    d2_etf["cfgi"] = np.nan
    for dt in d2_etf.index:
        mask = cfgi_df.index <= dt
        if mask.any():
            d2_etf.loc[dt, "cfgi"] = cfgi_df.loc[mask, "cfgi"].iloc[-1]
    d2_etf = d2_etf.reset_index()
    
    # Compute weekly CFGI RSI(7)
    cfgi_weekly = cfgi_df.resample("W").last().dropna()
    cfgi_weekly["cfgi_rsi7"] = compute_rsi(cfgi_weekly["cfgi"], 7)
    cfgi_weekly = cfgi_weekly.reset_index()
    
    # Merge weekly CFGI RSI with 2D data
    d2_etf["cfgi_rsi7"] = np.nan
    for i, row in d2_etf.iterrows():
        mask = cfgi_weekly["date"] <= row["date"]
        if mask.any():
            d2_etf.loc[i, "cfgi_rsi7"] = cfgi_weekly.loc[mask, "cfgi_rsi7"].iloc[-1]
    
    # Show CFGI at known Steve score >= 3 clusters
    hits = d2_etf[d2_etf["score"] >= 3].copy()
    if len(hits) > 0:
        hits["group"] = (hits["date"].diff() > timedelta(days=30)).cumsum()
        print(f"\n  Steve Score >= 3 clusters with CFGI:")
        print(f"  {'Date':12} {'Score':>5} {'Price':>10} {'CFGI':>6} {'CFGI_RSI7':>10} {'Days to Peak':>12}")
        print(f"  {'-'*60}")
        for grp, gdf in hits.groupby("group"):
            first = gdf.iloc[0]
            days = (peak_date - first["date"]).days
            cfgi_val = f"{first['cfgi']:.0f}" if not np.isnan(first['cfgi']) else "N/A"
            rsi_val = f"{first['cfgi_rsi7']:.1f}" if not np.isnan(first['cfgi_rsi7']) else "N/A"
            true_top = "TRUE" if abs(days) < 60 else "false"
            print(f"  {first['date'].strftime('%Y-%m-%d'):12} {first['score']:5.0f} {first['close']:10.2f} "
                  f"{cfgi_val:>6} {rsi_val:>10} {days:+12d}  {true_top}")
    
    # Test CFGI thresholds as gate on Steve score >= 3
    print(f"\n  CFGI Gate on Steve >= 3:")
    for cfgi_thresh in [65, 70, 75, 80]:
        gated = d2_etf[(d2_etf["score"] >= 3) & (d2_etf["cfgi"] > cfgi_thresh)]
        if len(gated) > 0:
            gated_g = gated.copy()
            gated_g["group"] = (gated_g["date"].diff() > timedelta(days=30)).cumsum()
            n_clusters = gated_g["group"].nunique()
            # Check if any cluster is near the true peak
            near_peak = 0
            for _, gg in gated_g.groupby("group"):
                if abs((peak_date - gg.iloc[0]["date"]).days) < 90:
                    near_peak += 1
            print(f"    CFGI > {cfgi_thresh}: {n_clusters} clusters, {near_peak} near peak (<90d)")
        else:
            print(f"    CFGI > {cfgi_thresh}: 0 clusters")
    
    # Test Weekly CFGI RSI(7) thresholds
    print(f"\n  Weekly CFGI RSI(7) Gate on Steve >= 3:")
    for rsi_thresh in [55, 60, 65, 70, 75, 80]:
        gated = d2_etf[(d2_etf["score"] >= 3) & (d2_etf["cfgi_rsi7"] > rsi_thresh)]
        if len(gated) > 0:
            gated_g = gated.copy()
            gated_g["group"] = (gated_g["date"].diff() > timedelta(days=30)).cumsum()
            n_clusters = gated_g["group"].nunique()
            near_peak = 0
            for _, gg in gated_g.groupby("group"):
                if abs((peak_date - gg.iloc[0]["date"]).days) < 90:
                    near_peak += 1
            print(f"    CFGI RSI(7) > {rsi_thresh}: {n_clusters} clusters, {near_peak} near peak (<90d)")
        else:
            print(f"    CFGI RSI(7) > {rsi_thresh}: 0 clusters")

    # Show CFGI values at actual peak for context
    peak_row = d2_etf.iloc[(d2_etf["date"] - peak_date).abs().argsort()[:1]]
    if len(peak_row) > 0:
        pr = peak_row.iloc[0]
        print(f"\n  At actual peak: CFGI={pr['cfgi']:.0f}, CFGI RSI(7)={pr['cfgi_rsi7']:.1f}")


# Summary: what CFGI was at each coin's actual peak?
print(f"\n\n{'='*70}")
print("CFGI AT ACTUAL PEAKS")
print(f"{'='*70}")
for coin in COINS:
    base = coin.split("/")[0]
    df = load_daily(coin)
    cfgi_df = load_cfgi(coin)
    d2 = resample(df, "2D")
    peak_date, peak_price = get_peak(d2)
    
    if len(cfgi_df) > 0:
        cfgi_df = cfgi_df.set_index("date")
        mask = cfgi_df.index <= peak_date
        if mask.any():
            cfgi_at_peak = cfgi_df.loc[mask, "cfgi"].iloc[-1]
            # Weekly RSI at peak
            cfgi_weekly = cfgi_df.resample("W").last().dropna()
            cfgi_weekly["rsi7"] = compute_rsi(cfgi_weekly["cfgi"], 7)
            mask2 = cfgi_weekly.index <= peak_date
            rsi_at_peak = cfgi_weekly.loc[mask2, "rsi7"].iloc[-1] if mask2.any() else float('nan')
            print(f"  {base:6} Peak {peak_date.strftime('%Y-%m-%d')}: CFGI={cfgi_at_peak:.0f}, Weekly CFGI RSI(7)={rsi_at_peak:.1f}")
