"""
2W and 2D StochRSI behavior around cycle tops.

Focus:
1. When does 2W K start rolling over (peak → decline)?
2. When does 2D K cross below D (bearish cross)?
3. What's the relationship between these two events and the actual top?
4. Are there other 2W/2D signals that consistently mark the top?
"""

import sqlite3
import numpy as np
import pandas as pd
from datetime import timedelta

DB = r"C:\Users\Never\.openclaw\workspace\trading\spot\data\candles.db"

TOPS = {
    "ETH": {"date": "2024-12-06", "symbol": "ETH/USDT"},
    "SOL": {"date": "2025-01-19", "symbol": "SOL/USDT"},
    "BTC": {"date": "2025-01-20", "symbol": "BTC/USDT"},
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
    return k, d, rsi


def resample(df, rule):
    return df[["open", "high", "low", "close", "volume"]].resample(rule).agg({
        "open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"
    }).dropna()


for coin, info in TOPS.items():
    df = load_daily(info["symbol"])
    top_date = pd.Timestamp(info["date"])
    
    # ── 2W candles ──
    df_2w = resample(df, "2W")
    k_2w, d_2w, rsi_2w = compute_stochrsi(df_2w["close"])
    df_2w["K"] = k_2w
    df_2w["D"] = d_2w
    df_2w["RSI"] = rsi_2w
    df_2w["K_prev"] = df_2w["K"].shift(1)
    df_2w["K_rolling_over"] = (df_2w["K"] < df_2w["K_prev"])  # K declining
    df_2w["K_cross_below_D"] = (df_2w["K"] < df_2w["D"]) & (df_2w["K_prev"] >= df_2w["D"].shift(1))
    
    # ── 2D candles ──
    df_2d = resample(df, "2D")
    k_2d, d_2d, rsi_2d = compute_stochrsi(df_2d["close"])
    df_2d["K"] = k_2d
    df_2d["D"] = d_2d
    df_2d["RSI"] = rsi_2d
    df_2d["K_prev"] = df_2d["K"].shift(1)
    df_2d["K_cross_below_D"] = (df_2d["K"] < df_2d["D"]) & (df_2d["K_prev"] >= df_2d["D"].shift(1))
    
    # ── 1W candles ──
    df_1w = resample(df, "W")
    k_1w, d_1w, rsi_1w = compute_stochrsi(df_1w["close"])
    df_1w["K"] = k_1w
    df_1w["D"] = d_1w
    df_1w["RSI"] = rsi_1w
    df_1w["K_prev"] = df_1w["K"].shift(1)
    df_1w["K_cross_below_D"] = (df_1w["K"] < df_1w["D"]) & (df_1w["K_prev"] >= df_1w["D"].shift(1))
    
    print(f"\n{'='*100}")
    print(f"  {coin} — Top: {info['date']}")
    print(f"{'='*100}")
    
    # ── 2W StochRSI around top ──
    window_2w = df_2w[(df_2w.index >= top_date - timedelta(days=120)) & 
                       (df_2w.index <= top_date + timedelta(days=120))]
    
    print(f"\n  2W StochRSI (each row = 2-week candle):")
    print(f"  {'Date':>12s} {'Close':>10s} {'K':>6s} {'D':>6s} {'RSI':>6s} {'K trend':>8s} {'K<D cross':>10s} {'vs top':>8s}")
    print(f"  {'-'*72}")
    
    # Find 2W K peak before top
    pre_top_2w = df_2w[df_2w.index <= top_date + timedelta(days=14)]
    k_peak_idx = None
    if len(pre_top_2w) > 0 and not pre_top_2w["K"].isna().all():
        k_peak_idx = pre_top_2w["K"].idxmax()
        k_peak_val = pre_top_2w.loc[k_peak_idx, "K"]
    
    for dt, row in window_2w.iterrows():
        days_from_top = (dt - top_date).days
        k_trend = "FALLING" if row.get("K_rolling_over", False) else "rising"
        cross = "** CROSS **" if row.get("K_cross_below_D", False) else ""
        marker = " <<<" if abs(days_from_top) <= 7 else ""
        k_str = f"{row['K']:.1f}" if not np.isnan(row['K']) else "  nan"
        d_str = f"{row['D']:.1f}" if not np.isnan(row['D']) else "  nan"
        rsi_str = f"{row['RSI']:.1f}" if not np.isnan(row['RSI']) else "  nan"
        print(f"  {dt.strftime('%Y-%m-%d'):>12s} {row['close']:>10,.1f} {k_str:>6s} {d_str:>6s} {rsi_str:>6s} "
              f"{k_trend:>8s} {cross:>10s} {days_from_top:>+6d}d{marker}")
    
    # ── 2D StochRSI around top ──
    window_2d = df_2d[(df_2d.index >= top_date - timedelta(days=60)) & 
                       (df_2d.index <= top_date + timedelta(days=60))]
    
    print(f"\n  2D StochRSI (each row = 2-day candle):")
    print(f"  {'Date':>12s} {'Close':>10s} {'K':>6s} {'D':>6s} {'RSI':>6s} {'K<D cross':>10s} {'vs top':>8s}")
    print(f"  {'-'*66}")
    
    for dt, row in window_2d.iterrows():
        days_from_top = (dt - top_date).days
        cross = "** CROSS **" if row.get("K_cross_below_D", False) else ""
        marker = " <<<" if abs(days_from_top) <= 1 else ""
        k_str = f"{row['K']:.1f}" if not np.isnan(row['K']) else "  nan"
        d_str = f"{row['D']:.1f}" if not np.isnan(row['D']) else "  nan"
        rsi_str = f"{row['RSI']:.1f}" if not np.isnan(row['RSI']) else "  nan"
        print(f"  {dt.strftime('%Y-%m-%d'):>12s} {row['close']:>10,.1f} {k_str:>6s} {d_str:>6s} {rsi_str:>6s} "
              f"{cross:>10s} {days_from_top:>+6d}d{marker}")
    
    # ── 1W StochRSI around top ──
    window_1w = df_1w[(df_1w.index >= top_date - timedelta(days=90)) & 
                       (df_1w.index <= top_date + timedelta(days=90))]
    
    print(f"\n  1W StochRSI (each row = 1-week candle):")
    print(f"  {'Date':>12s} {'Close':>10s} {'K':>6s} {'D':>6s} {'RSI':>6s} {'K<D cross':>10s} {'vs top':>8s}")
    print(f"  {'-'*66}")
    
    for dt, row in window_1w.iterrows():
        days_from_top = (dt - top_date).days
        cross = "** CROSS **" if row.get("K_cross_below_D", False) else ""
        marker = " <<<" if abs(days_from_top) <= 3 else ""
        k_str = f"{row['K']:.1f}" if not np.isnan(row['K']) else "  nan"
        d_str = f"{row['D']:.1f}" if not np.isnan(row['D']) else "  nan"
        rsi_str = f"{row['RSI']:.1f}" if not np.isnan(row['RSI']) else "  nan"
        print(f"  {dt.strftime('%Y-%m-%d'):>12s} {row['close']:>10,.1f} {k_str:>6s} {d_str:>6s} {rsi_str:>6s} "
              f"{cross:>10s} {days_from_top:>+6d}d{marker}")
    
    # ── Key events summary ──
    print(f"\n  KEY EVENTS:")
    
    # 2W K peak
    pre_top_2w_wide = df_2w[(df_2w.index >= top_date - timedelta(days=180)) & (df_2w.index <= top_date + timedelta(days=30))]
    if len(pre_top_2w_wide) > 0 and not pre_top_2w_wide["K"].isna().all():
        k_peak_idx = pre_top_2w_wide["K"].idxmax()
        k_peak = pre_top_2w_wide.loc[k_peak_idx, "K"]
        days = (top_date - k_peak_idx).days
        print(f"    2W K peak: {k_peak:.1f} on {k_peak_idx.strftime('%Y-%m-%d')} ({days:+d}d from top)")
    
    # First 2W K declining after peak
    post_peak_2w = df_2w[df_2w.index > k_peak_idx] if k_peak_idx is not None else df_2w.iloc[0:0]
    for dt, row in post_peak_2w.iterrows():
        if row.get("K_rolling_over", False):
            days = (top_date - dt).days
            print(f"    2W K first decline: {dt.strftime('%Y-%m-%d')} K={row['K']:.1f} ({days:+d}d from top)")
            break
    
    # First 2W K<D cross
    post_top_2w = df_2w[df_2w.index >= top_date - timedelta(days=30)]
    for dt, row in post_top_2w.iterrows():
        if row.get("K_cross_below_D", False):
            days = (dt - top_date).days
            price = row["close"]
            top_price_approx = df[df.index <= top_date]["close"].iloc[-1]
            loss = (price - top_price_approx) / top_price_approx * 100
            print(f"    2W K<D cross: {dt.strftime('%Y-%m-%d')} K={row['K']:.1f} ({days:+d}d, {loss:+.1f}% from top)")
            break
    else:
        print(f"    2W K<D cross: NOT FOUND in window")
    
    # First 2D K<D cross near/after top
    near_top_2d = df_2d[(df_2d.index >= top_date - timedelta(days=14)) & (df_2d.index <= top_date + timedelta(days=60))]
    for dt, row in near_top_2d.iterrows():
        if row.get("K_cross_below_D", False):
            days = (dt - top_date).days
            price = row["close"]
            top_price_approx = df[df.index <= top_date]["close"].iloc[-1]
            loss = (price - top_price_approx) / top_price_approx * 100
            print(f"    2D K<D cross: {dt.strftime('%Y-%m-%d')} K={row['K']:.1f} ({days:+d}d, {loss:+.1f}% from top)")
            break
    else:
        print(f"    2D K<D cross: NOT FOUND near top")
    
    # First 1W K<D cross
    near_top_1w = df_1w[(df_1w.index >= top_date - timedelta(days=14)) & (df_1w.index <= top_date + timedelta(days=90))]
    for dt, row in near_top_1w.iterrows():
        if row.get("K_cross_below_D", False):
            days = (dt - top_date).days
            price = row["close"]
            top_price_approx = df[df.index <= top_date]["close"].iloc[-1]
            loss = (price - top_price_approx) / top_price_approx * 100
            print(f"    1W K<D cross: {dt.strftime('%Y-%m-%d')} K={row['K']:.1f} ({days:+d}d, {loss:+.1f}% from top)")
            break
    else:
        print(f"    1W K<D cross: NOT FOUND near top")


# ── Summary table ──
print(f"\n{'='*100}")
print("SUMMARY — Sequence of events at each top")
print(f"{'='*100}")
print("""
The question: Is there a consistent sequence?
  1. 2W K peaks and starts rolling over
  2. 2D K crosses below D (faster confirmation)
  3. 1W K crosses below D (intermediate confirmation)
  4. 2W K crosses below D (slowest, most damage)
  
If 2W rollover → 2D K<D cross is consistent, that's our signal:
  ARM when 2W K starts declining from elevated level
  FIRE when 2D K crosses below D
""")
