"""
Detailed day-by-day data around each cycle top.
For chart review session with Brett.

Output: CSV-style tables for each coin showing all indicators
in the ±30 day window around the top.
"""

import sqlite3
import numpy as np
import pandas as pd
from datetime import timedelta

DB = r"C:\Users\Never\.openclaw\workspace\trading\spot\data\candles.db"

TOPS = {
    "ETH": {"date": "2024-12-06", "symbol": "ETH/USDT"},
    "SOL": {"date": "2025-01-19", "symbol": "SOL/USDT"},
    "LINK": {"date": "2024-12-08", "symbol": "LINK/USDT"},
    "XRP": {"date": "2025-01-16", "symbol": "XRP/USDT"},
}


def load_daily(symbol):
    conn = sqlite3.connect(DB)
    df = pd.read_sql_query(
        f"SELECT * FROM candles_daily WHERE symbol='{symbol}' ORDER BY timestamp", conn)
    conn.close()
    df["date"] = pd.to_datetime(df["timestamp"], unit="ms")
    df = df.set_index("date")
    return df


def load_cfgi(coin_base):
    conn = sqlite3.connect(DB)
    df = pd.read_sql_query(
        f"SELECT * FROM cfgi_daily WHERE symbol LIKE '{coin_base}%' ORDER BY date", conn)
    conn.close()
    if len(df) == 0:
        return pd.Series(dtype=float)
    df["date"] = pd.to_datetime(df["date"], format="mixed")
    df = df.set_index("date")
    df.index = df.index.normalize()
    df = df[~df.index.duplicated(keep="last")]
    return df["cfgi"].astype(float)


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
    return 100 - (100 / (1 + pos_sum / neg_sum.replace(0, 1e-10)))


def resample(df, rule):
    return df[["open", "high", "low", "close", "volume"]].resample(rule).agg({
        "open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"
    }).dropna()


for coin, info in TOPS.items():
    df = load_daily(info["symbol"])
    cfgi = load_cfgi(coin)
    top_date = pd.Timestamp(info["date"])
    
    # Compute daily indicators
    df["rsi"] = compute_rsi(df["close"], 14)
    df["mfi"] = compute_mfi(df["high"], df["low"], df["close"], df["volume"], 14)
    k, d = compute_stochrsi(df["close"])
    df["stoch_k"] = k
    df["stoch_d"] = d
    df["sma20"] = df["close"].rolling(20).mean()
    df["sma50"] = df["close"].rolling(50).mean()
    df["sma200"] = df["close"].rolling(200).mean()
    df["vol_sma20"] = df["volume"].rolling(20).mean()
    df["vol_ratio"] = df["volume"] / df["vol_sma20"]
    
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
    
    # Pct from high
    df["high_60d"] = df["high"].rolling(60).max()
    df["pct_from_high"] = (df["close"] - df["high_60d"]) / df["high_60d"] * 100
    
    # 2D indicators
    df_2d = resample(df, "2D")
    df_2d["rsi"] = compute_rsi(df_2d["close"], 14)
    df_2d["mfi"] = compute_mfi(df_2d["high"], df_2d["low"], df_2d["close"], df_2d["volume"], 14)
    k2, d2 = compute_stochrsi(df_2d["close"])
    df_2d["stoch_k"] = k2
    df_2d["stoch_d"] = d2
    
    # Weekly
    df_w = resample(df, "W")
    kw, dw = compute_stochrsi(df_w["close"])
    df_w["stoch_k"] = kw
    df_w["stoch_d"] = dw
    df_w["rsi"] = compute_rsi(df_w["close"], 14)
    
    # Window: 30 days before to 45 days after
    window = df[(df.index >= top_date - timedelta(days=30)) & 
                (df.index <= top_date + timedelta(days=45))]
    
    print(f"\n{'='*120}")
    print(f"  {coin} — Top: {info['date']} | Daily indicators ±30/+45 days")
    print(f"{'='*120}")
    print(f"  {'Date':>12s} {'Close':>10s} {'%frHi':>6s} {'RSI':>5s} {'MFI':>5s} {'StK':>5s} {'StD':>5s} "
          f"{'ADX':>5s} {'Vol_r':>5s} {'SMA50':>10s} {'CFGI':>5s} | "
          f"{'2D_RSI':>6s} {'2D_MFI':>6s} {'2D_K':>5s} | {'W_RSI':>5s} {'W_K':>5s}")
    print(f"  {'-'*118}")
    
    for dt, row in window.iterrows():
        marker = " <<<TOP" if dt == top_date else ""
        
        # Get CFGI
        cfgi_val = cfgi.get(dt, np.nan) if len(cfgi) > 0 else np.nan
        
        # Get 2D values (nearest)
        mask_2d = df_2d.index <= dt
        r2d = df_2d[mask_2d].iloc[-1] if mask_2d.any() else None
        r2d_rsi = f"{r2d['rsi']:.0f}" if r2d is not None and not np.isnan(r2d['rsi']) else "  -"
        r2d_mfi = f"{r2d['mfi']:.0f}" if r2d is not None and not np.isnan(r2d['mfi']) else "  -"
        r2d_k = f"{r2d['stoch_k']:.0f}" if r2d is not None and not np.isnan(r2d['stoch_k']) else "  -"
        
        # Get weekly values (nearest)
        mask_w = df_w.index <= dt
        rw = df_w[mask_w].iloc[-1] if mask_w.any() else None
        rw_rsi = f"{rw['rsi']:.0f}" if rw is not None and not np.isnan(rw['rsi']) else "  -"
        rw_k = f"{rw['stoch_k']:.0f}" if rw is not None and not np.isnan(rw['stoch_k']) else "  -"
        
        cfgi_str = f"{cfgi_val:.0f}" if not np.isnan(cfgi_val) else "  -"
        
        print(f"  {dt.strftime('%Y-%m-%d'):>12s} {row['close']:>10,.1f} {row['pct_from_high']:>+5.1f}% "
              f"{row['rsi']:>5.0f} {row['mfi']:>5.0f} {row['stoch_k']:>5.0f} {row['stoch_d']:>5.0f} "
              f"{row['adx']:>5.0f} {row['vol_ratio']:>5.1f} {row['sma50']:>10,.1f} {cfgi_str:>5s} | "
              f"{r2d_rsi:>6s} {r2d_mfi:>6s} {r2d_k:>5s} | {rw_rsi:>5s} {rw_k:>5s}{marker}")
