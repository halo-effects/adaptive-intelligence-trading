"""
Bearish Divergence at Tops — Price makes HH while RSI/MFI make LH

For each coin: find the cycle top, then look for divergence in the 
30 days before. Compare peak RSI/MFI to their value at the actual top.
Also check: was there a PRIOR RSI/MFI peak higher than the top-day reading?
"""

import sqlite3
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

DB = r"C:\Users\Never\.openclaw\workspace\trading\spot\data\candles.db"

TOPS = {
    "ETH": {"date": "2024-12-06", "price": 4107},
    "SOL": {"date": "2025-01-19", "price": 294},
    "BTC": {"date": "2025-01-20", "price": 109350},
    "LINK": {"date": "2024-12-08", "price": 30.8},
    "XRP": {"date": "2025-01-16", "price": 3.39},
}


def load_daily(symbol):
    conn = sqlite3.connect(DB)
    df = pd.read_sql_query(
        f"SELECT * FROM candles_daily WHERE symbol='{symbol}' ORDER BY timestamp", conn)
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


def compute_stochrsi(close, rsi_period=14, stoch_period=14, k_smooth=3, d_smooth=3):
    rsi = compute_rsi(close, rsi_period)
    min_rsi = rsi.rolling(stoch_period).min()
    max_rsi = rsi.rolling(stoch_period).max()
    stoch_rsi = (rsi - min_rsi) / (max_rsi - min_rsi) * 100
    k = stoch_rsi.rolling(k_smooth).mean()
    d = k.rolling(d_smooth).mean()
    return k, d


print("=" * 80)
print("BEARISH DIVERGENCE ANALYSIS AT CYCLE TOPS")
print("=" * 80)

for coin, top_info in TOPS.items():
    symbol = f"{coin}/USDT"
    df = load_daily(symbol)
    top_date = pd.Timestamp(top_info["date"])
    
    df["rsi"] = compute_rsi(df["close"], 14)
    df["mfi"] = compute_mfi(df["high"], df["low"], df["close"], df["volume"], 14)
    k, d = compute_stochrsi(df["close"])
    df["stoch_k"] = k
    
    # Look at 60 days before top
    mask = (df["date"] >= top_date - timedelta(days=60)) & (df["date"] <= top_date)
    window = df[mask].copy()
    
    if len(window) == 0:
        print(f"\n{coin}: No data in window")
        continue
    
    top_row = window.iloc[-1]
    
    # Find peaks in price, RSI, MFI, StochK within window
    price_peak_idx = window["close"].idxmax()
    rsi_peak_idx = window["rsi"].idxmax()
    mfi_peak_idx = window["mfi"].idxmax()
    stoch_peak_idx = window["stoch_k"].idxmax()
    
    price_peak = window.loc[price_peak_idx]
    rsi_peak = window.loc[rsi_peak_idx]
    mfi_peak = window.loc[mfi_peak_idx]
    stoch_peak = window.loc[stoch_peak_idx]
    
    print(f"\n{'='*60}")
    print(f"  {coin} -- Top: {top_info['date']} @ ${top_info['price']:,}")
    print(f"{'='*60}")
    
    print(f"\n  Price peak:  {price_peak['date'].strftime('%Y-%m-%d')} @ ${price_peak['close']:,.0f}")
    print(f"  RSI peak:    {rsi_peak['date'].strftime('%Y-%m-%d')} = {rsi_peak['rsi']:.1f}  (price ${rsi_peak['close']:,.0f})")
    print(f"  MFI peak:    {mfi_peak['date'].strftime('%Y-%m-%d')} = {mfi_peak['mfi']:.1f}  (price ${mfi_peak['close']:,.0f})")
    print(f"  StochK peak: {stoch_peak['date'].strftime('%Y-%m-%d')} = {stoch_peak['stoch_k']:.1f}  (price ${stoch_peak['close']:,.0f})")
    
    # Divergence: price at top >= price at indicator peak, but indicator at top < indicator peak
    days_rsi = (top_date - rsi_peak["date"]).days
    days_mfi = (top_date - mfi_peak["date"]).days
    days_stoch = (top_date - stoch_peak["date"]).days
    
    print(f"\n  AT TOP DAY:  RSI={top_row['rsi']:.1f}  MFI={top_row['mfi']:.1f}  StochK={top_row['stoch_k']:.1f}")
    
    rsi_div = days_rsi > 3 and top_row["rsi"] < rsi_peak["rsi"] - 5
    mfi_div = days_mfi > 3 and top_row["mfi"] < mfi_peak["mfi"] - 5
    stoch_div = days_stoch > 3 and top_row["stoch_k"] < stoch_peak["stoch_k"] - 10
    
    print(f"\n  DIVERGENCE (indicator peaked before price, lower at top):")
    print(f"    RSI:    {'YES' if rsi_div else 'no '}  peak {days_rsi}d before top, drop {rsi_peak['rsi'] - top_row['rsi']:.1f}")
    print(f"    MFI:    {'YES' if mfi_div else 'no '}  peak {days_mfi}d before top, drop {mfi_peak['mfi'] - top_row['mfi']:.1f}")
    print(f"    StochK: {'YES' if stoch_div else 'no '}  peak {days_stoch}d before top, drop {stoch_peak['stoch_k'] - top_row['stoch_k']:.1f}")
    
    # Also look at volume trend
    window["vol_sma20"] = window["volume"].rolling(20).mean()
    vol_at_top = window.iloc[-1]["volume"]
    vol_avg = window.iloc[-1]["vol_sma20"] if not pd.isna(window.iloc[-1]["vol_sma20"]) else window["volume"].mean()
    print(f"\n  Volume at top vs 20d avg: {vol_at_top/vol_avg:.2f}x")
    
    # Check if volume was declining into the top (distribution)
    if len(window) >= 20:
        first_half_vol = window.iloc[:len(window)//2]["volume"].mean()
        second_half_vol = window.iloc[len(window)//2:]["volume"].mean()
        print(f"  Volume trend: first half avg={first_half_vol:,.0f}, second half avg={second_half_vol:,.0f} ({'declining' if second_half_vol < first_half_vol else 'rising'})")

# Summary
print(f"\n{'='*80}")
print("DIVERGENCE SUMMARY")
print("=" * 80)
print("Bearish divergence = price at/near top while indicator already declining")
print("This is the classic distribution signal Brett suggested.")
