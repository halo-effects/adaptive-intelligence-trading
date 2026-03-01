"""
Top Signal Inventory — What signals are present at EVERY cycle top?

For each coin, identify the cycle top (highest price in ETF era markup phases),
then check EVERY available signal within a window around that top.

Goal: Find what's universally present at tops that we might be missing.
"""

import sqlite3
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

DB = r"C:\Users\Never\.openclaw\workspace\trading\spot\data\candles.db"

# Known ETF-era cycle tops (approximate dates, highest close)
# These are the peaks we want to detect
TOPS = {
    "ETH": {"date": "2024-12-06", "price": 4107},
    "SOL": {"date": "2025-01-19", "price": 294},
    "BTC": {"date": "2025-01-20", "price": 109350},
    "LINK": {"date": "2024-12-08", "price": 30.8},
    "XRP": {"date": "2025-01-16", "price": 3.39},
}

COINS_DAILY = {
    "ETH": "ETH/USDT", "SOL": "SOL/USDT", "BTC": "BTC/USDT",
    "LINK": "LINK/USDT", "XRP": "XRP/USDT"
}


def load_daily(symbol):
    conn = sqlite3.connect(DB)
    df = pd.read_sql_query(
        f"SELECT * FROM candles_daily WHERE symbol='{symbol}' ORDER BY timestamp", conn)
    conn.close()
    df["date"] = pd.to_datetime(df["timestamp"], unit="ms")
    return df


def load_cfgi(coin_base):
    conn = sqlite3.connect(DB)
    df = pd.read_sql_query(
        f"SELECT * FROM cfgi_daily WHERE symbol LIKE '{coin_base}%' ORDER BY date", conn)
    conn.close()
    df["date"] = pd.to_datetime(df["date"], format="mixed")
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
    tp = (high + low + close) / 3
    rmf = tp * volume
    delta = tp.diff()
    pos_flow = rmf.where(delta > 0, 0.0)
    neg_flow = rmf.where(delta < 0, 0.0)
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


def analyze_top(coin, top_info):
    symbol = COINS_DAILY[coin]
    df = load_daily(symbol)
    cfgi = load_cfgi(coin)
    top_date = pd.Timestamp(top_info["date"])
    
    # Window: 30 days before to 7 days after
    window_start = top_date - timedelta(days=30)
    window_end = top_date + timedelta(days=7)
    
    # --- Daily signals at top ---
    at_top = df[df["date"] <= top_date].iloc[-1] if len(df[df["date"] <= top_date]) > 0 else None
    
    # Compute daily indicators on full history
    df["sma50"] = df["close"].rolling(50).mean()
    df["sma200"] = df["close"].rolling(200).mean()
    df["rsi14"] = compute_rsi(df["close"], 14)
    df["rsi7"] = compute_rsi(df["close"], 7)
    df["mfi14"] = compute_mfi(df["high"], df["low"], df["close"], df["volume"], 14)
    k, d = compute_stochrsi(df["close"])
    df["stoch_k"] = k
    df["stoch_d"] = d
    
    # Price vs SMA200
    df["pct_above_sma200"] = (df["close"] / df["sma200"] - 1) * 100
    
    # BB
    df["bb_mid"] = df["close"].rolling(20).mean()
    df["bb_std"] = df["close"].rolling(20).std()
    df["bb_upper"] = df["bb_mid"] + 2 * df["bb_std"]
    df["bb_pct"] = (df["close"] - df["bb_mid"]) / (2 * df["bb_std"]) * 100
    
    # ADX
    df["tr"] = np.maximum(
        df["high"] - df["low"],
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
    
    # HH/HL structure (20-day)
    df["high_20"] = df["high"].rolling(20).max()
    df["low_20"] = df["low"].rolling(20).min()
    
    # Get row at top date
    mask = df["date"] <= top_date
    if mask.sum() == 0:
        return None
    row = df[mask].iloc[-1]
    
    # --- 2D signals ---
    df_2d = resample(df, "2D")
    df_2d["rsi14"] = compute_rsi(df_2d["close"], 14)
    df_2d["mfi14"] = compute_mfi(df_2d["high"], df_2d["low"], df_2d["close"], df_2d["volume"], 14)
    k2, d2 = compute_stochrsi(df_2d["close"])
    df_2d["stoch_k"] = k2
    df_2d["stoch_d"] = d2
    df_2d["sma200"] = df_2d["close"].rolling(200).mean()
    mask_2d = df_2d["date"] <= top_date
    row_2d = df_2d[mask_2d].iloc[-1] if mask_2d.sum() > 0 else None
    
    # --- Weekly signals ---
    df_w = resample(df, "W")
    df_w["rsi14"] = compute_rsi(df_w["close"], 14)
    df_w["rsi7"] = compute_rsi(df_w["close"], 7)
    k_w, d_w = compute_stochrsi(df_w["close"])
    df_w["stoch_k"] = k_w
    df_w["stoch_d"] = d_w
    df_w["sma50"] = df_w["close"].rolling(50).mean()
    mask_w = df_w["date"] <= top_date
    row_w = df_w[mask_w].iloc[-1] if mask_w.sum() > 0 else None
    
    # --- 2W signals ---
    df_2w = resample(df, "2W")
    k_2w, d_2w = compute_stochrsi(df_2w["close"])
    df_2w["stoch_k"] = k_2w
    df_2w["stoch_d"] = d_2w
    df_2w["rsi14"] = compute_rsi(df_2w["close"], 14)
    mask_2w = df_2w["date"] <= top_date
    row_2w = df_2w[mask_2w].iloc[-1] if mask_2w.sum() > 0 else None
    
    # --- CFGI at top ---
    cfgi_at_top = cfgi[cfgi["date"] <= top_date]
    cfgi_val = cfgi_at_top.iloc[-1]["cfgi"] if len(cfgi_at_top) > 0 else None
    cfgi_rsi7 = None
    if len(cfgi_at_top) > 10:
        cfgi_rsi7_series = compute_rsi(cfgi_at_top["cfgi"].astype(float), 7)
        cfgi_rsi7 = cfgi_rsi7_series.iloc[-1]
    
    # --- Find peak values in window (max readings near top) ---
    window_mask = (df["date"] >= window_start) & (df["date"] <= window_end)
    window_df = df[window_mask]
    
    results = {
        "coin": coin,
        "top_date": top_info["date"],
        "top_price": top_info["price"],
        # Daily at top
        "D_RSI14": round(row["rsi14"], 1),
        "D_RSI7": round(row["rsi7"], 1),
        "D_StochK": round(row["stoch_k"], 1),
        "D_StochD": round(row["stoch_d"], 1),
        "D_MFI": round(row["mfi14"], 1),
        "D_above_SMA200": row["close"] > row["sma200"],
        "D_pct_above_SMA200": round(row["pct_above_sma200"], 1),
        "D_SMA50_above_SMA200": row["sma50"] > row["sma200"],
        "D_ADX": round(row["adx"], 1),
        "D_BB_pct": round(row["bb_pct"], 1),
        # Peak values in ±30d window
        "D_peak_RSI14": round(window_df["rsi14"].max(), 1),
        "D_peak_StochK": round(window_df["stoch_k"].max(), 1),
        "D_peak_MFI": round(window_df["mfi14"].max(), 1),
        # 2D at top
        "2D_RSI14": round(row_2d["rsi14"], 1) if row_2d is not None else None,
        "2D_StochK": round(row_2d["stoch_k"], 1) if row_2d is not None else None,
        "2D_StochD": round(row_2d["stoch_d"], 1) if row_2d is not None else None,
        "2D_MFI": round(row_2d["mfi14"], 1) if row_2d is not None else None,
        "2D_above_SMA200": (row_2d["close"] > row_2d["sma200"]) if row_2d is not None else None,
        # Weekly at top
        "W_RSI14": round(row_w["rsi14"], 1) if row_w is not None else None,
        "W_RSI7": round(row_w["rsi7"], 1) if row_w is not None else None,
        "W_StochK": round(row_w["stoch_k"], 1) if row_w is not None else None,
        "W_StochD": round(row_w["stoch_d"], 1) if row_w is not None else None,
        # 2W at top
        "2W_StochK": round(row_2w["stoch_k"], 1) if row_2w is not None else None,
        "2W_StochD": round(row_2w["stoch_d"], 1) if row_2w is not None else None,
        "2W_RSI14": round(row_2w["rsi14"], 1) if row_2w is not None else None,
        # CFGI
        "CFGI": cfgi_val,
        "CFGI_RSI7": round(cfgi_rsi7, 1) if cfgi_rsi7 is not None else None,
        # Steve score (2D)
        "steve_above_sma200": (row_2d["close"] > row_2d["sma200"]) if row_2d is not None else None,
        "steve_rsi_gt80": (row_2d["rsi14"] > 80) if row_2d is not None else None,
        "steve_stoch_gt80": (row_2d["stoch_k"] > 80 and row_2d["stoch_d"] > 80) if row_2d is not None else None,
        "steve_mfi_gt80": (row_2d["mfi14"] > 80) if row_2d is not None else None,
    }
    
    # Steve score
    steve = sum([
        results.get("steve_above_sma200", False) or False,
        results.get("steve_rsi_gt80", False) or False,
        results.get("steve_stoch_gt80", False) or False,
        results.get("steve_mfi_gt80", False) or False,
    ])
    results["steve_score"] = steve
    
    # OB93 check (2W StochRSI K > 93 within 60 days before top)
    if row_2w is not None:
        mask_ob = (df_2w["date"] >= top_date - timedelta(days=90)) & (df_2w["date"] <= top_date)
        ob_window = df_2w[mask_ob]
        results["2W_OB93_hit"] = (ob_window["stoch_k"] > 93).any() if len(ob_window) > 0 else False
        results["2W_peak_K"] = round(ob_window["stoch_k"].max(), 1) if len(ob_window) > 0 else None
    
    return results


print("=" * 80)
print("TOP SIGNAL INVENTORY — What's Present at Every Cycle Top?")
print("=" * 80)

all_results = []
for coin, top_info in TOPS.items():
    r = analyze_top(coin, top_info)
    if r:
        all_results.append(r)
        print(f"\n{'='*60}")
        print(f"  {coin} — Top: {top_info['date']} @ ${top_info['price']:,}")
        print(f"{'='*60}")
        print(f"  DAILY:   RSI={r['D_RSI14']}  StochK={r['D_StochK']}  MFI={r['D_MFI']}  ADX={r['D_ADX']}  BB%={r['D_BB_pct']}")
        print(f"           Above SMA200={r['D_above_SMA200']}  (+{r['D_pct_above_SMA200']}%)  SMA50>200={r['D_SMA50_above_SMA200']}")
        print(f"           Peak (±30d): RSI={r['D_peak_RSI14']}  StochK={r['D_peak_StochK']}  MFI={r['D_peak_MFI']}")
        print(f"  2D:      RSI={r['2D_RSI14']}  StochK={r['2D_StochK']}  MFI={r['2D_MFI']}  Above SMA200={r['2D_above_SMA200']}")
        print(f"  WEEKLY:  RSI14={r['W_RSI14']}  RSI7={r['W_RSI7']}  StochK={r['W_StochK']}")
        print(f"  2W:      StochK={r['2W_StochK']}  RSI={r['2W_RSI14']}  OB93 hit={r.get('2W_OB93_hit')}  Peak K={r.get('2W_peak_K')}")
        print(f"  CFGI:    Value={r['CFGI']}  RSI(7)={r['CFGI_RSI7']}")
        print(f"  STEVE:   Score={r['steve_score']}/4  (SMA200={r['steve_above_sma200']} RSI>80={r['steve_rsi_gt80']} Stoch>80={r['steve_stoch_gt80']} MFI>80={r['steve_mfi_gt80']})")

# Summary: what's universally present?
print(f"\n{'='*80}")
print("UNIVERSAL SIGNAL CHECK — Present at ALL 5 tops?")
print(f"{'='*80}")

checks = {
    "Above SMA200 (daily)": [r["D_above_SMA200"] for r in all_results],
    "SMA50 > SMA200 (golden cross)": [r["D_SMA50_above_SMA200"] for r in all_results],
    "Daily RSI > 60": [r["D_RSI14"] > 60 for r in all_results],
    "Daily RSI > 70": [r["D_RSI14"] > 70 for r in all_results],
    "Daily RSI > 80": [r["D_RSI14"] > 80 for r in all_results],
    "Daily MFI > 60": [r["D_MFI"] > 60 for r in all_results],
    "Daily MFI > 70": [r["D_MFI"] > 70 for r in all_results],
    "Daily MFI > 80": [r["D_MFI"] > 80 for r in all_results],
    "Peak RSI > 80 (±30d)": [r["D_peak_RSI14"] > 80 for r in all_results],
    "Peak StochK > 90 (±30d)": [r["D_peak_StochK"] > 90 for r in all_results],
    "Peak MFI > 80 (±30d)": [r["D_peak_MFI"] > 80 for r in all_results],
    "2D RSI > 70": [r["2D_RSI14"] > 70 for r in all_results],
    "2D RSI > 80": [r["2D_RSI14"] > 80 for r in all_results],
    "2D StochK > 80": [r["2D_StochK"] > 80 for r in all_results],
    "2D MFI > 70": [r["2D_MFI"] > 70 for r in all_results],
    "2D MFI > 80": [r["2D_MFI"] > 80 for r in all_results],
    "Weekly RSI > 70": [r["W_RSI14"] > 70 for r in all_results],
    "Weekly RSI > 80": [r["W_RSI14"] > 80 for r in all_results],
    "Weekly StochK > 80": [r["W_StochK"] > 80 for r in all_results],
    "2W StochK > 80": [r["2W_StochK"] > 80 for r in all_results],
    "2W StochK > 90": [r["2W_StochK"] > 90 for r in all_results],
    "2W OB93 hit (90d before)": [r.get("2W_OB93_hit", False) for r in all_results],
    "CFGI > 60 (greed)": [r["CFGI"] is not None and float(r["CFGI"]) > 60 for r in all_results],
    "CFGI > 70": [r["CFGI"] is not None and float(r["CFGI"]) > 70 for r in all_results],
    "CFGI > 80": [r["CFGI"] is not None and float(r["CFGI"]) > 80 for r in all_results],
    "CFGI RSI(7) > 60": [r["CFGI_RSI7"] is not None and r["CFGI_RSI7"] > 60 for r in all_results],
    "CFGI RSI(7) > 70": [r["CFGI_RSI7"] is not None and r["CFGI_RSI7"] > 70 for r in all_results],
    "+20% above SMA200": [r["D_pct_above_SMA200"] > 20 for r in all_results],
    "+30% above SMA200": [r["D_pct_above_SMA200"] > 30 for r in all_results],
    "+50% above SMA200": [r["D_pct_above_SMA200"] > 50 for r in all_results],
    "Steve ≥ 2/4": [r["steve_score"] >= 2 for r in all_results],
    "Steve ≥ 3/4": [r["steve_score"] >= 3 for r in all_results],
    "Steve = 4/4": [r["steve_score"] >= 4 for r in all_results],
    "ADX > 20": [r["D_ADX"] > 20 for r in all_results],
    "ADX > 30": [r["D_ADX"] > 30 for r in all_results],
}

for label, vals in checks.items():
    count = sum(vals)
    coins_hit = [all_results[i]["coin"] for i, v in enumerate(vals) if v]
    coins_miss = [all_results[i]["coin"] for i, v in enumerate(vals) if not v]
    marker = " ALL" if count == 5 else f"  {count}/5"
    miss_str = f"  MISS: {', '.join(coins_miss)}" if coins_miss else ""
    print(f"  {marker}  {label}{miss_str}")
