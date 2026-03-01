"""
OB93 + 2D K×D Bearish Cross as Top Signal

Flow:
  1. 2W StochRSI K hits > 93 (OB93 fires) -> "we're at a top zone"
  2. 2D K crosses below D -> execution trigger (sell/enter MARKDOWN)

Compare timing vs OB93 alone and vs actual tops.
"""
import sqlite3
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

DB = r"C:\Users\Never\.openclaw\workspace\trading\spot\data\candles.db"
conn = sqlite3.connect(DB)

COINS = ["ETH/USDT", "SOL/USDT", "LINK/USDT", "XRP/USDT", "BTC/USDT"]


def compute_stochrsi(close, rsi_period=14, stoch_period=14, k_smooth=3, d_smooth=3):
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = (-delta).clip(lower=0)
    avg_gain = gain.ewm(alpha=1/rsi_period, min_periods=rsi_period).mean()
    avg_loss = loss.ewm(alpha=1/rsi_period, min_periods=rsi_period).mean()
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    rsi_low = rsi.rolling(stoch_period).min()
    rsi_high = rsi.rolling(stoch_period).max()
    stoch = ((rsi - rsi_low) / (rsi_high - rsi_low).replace(0, np.nan)) * 100
    k = stoch.rolling(k_smooth).mean()
    d = k.rolling(d_smooth).mean()
    return k, d


print("OB93 + 2D K x D BEARISH CROSS: TOP SIGNAL TEST")
print("=" * 90)
print("Flow: 2W K > 93 (OB93) arms the gate -> 2D K crosses below D = trigger")
print("Gate resets when 2W K drops below 20 (new cycle bottom)")
print()

all_results = []

for sym in COINS:
    base = sym.split("/")[0]

    df = pd.read_sql_query(
        "SELECT timestamp, open, high, low, close, volume FROM candles_daily WHERE symbol=? ORDER BY timestamp",
        conn, params=[sym]
    )
    df["dt"] = pd.to_datetime(df["timestamp"], unit="ms")
    df = df.set_index("dt").sort_index()
    df = df[~df.index.duplicated(keep="last")]
    df = df[df.index >= "2023-01-01"]

    daily_close = df["close"]

    # 2W StochRSI
    w2 = df["close"].resample("2W").last().dropna()
    w2k, w2d = compute_stochrsi(w2)

    # 2D StochRSI
    d2 = df["close"].resample("2D").last().dropna()
    d2k, d2d = compute_stochrsi(d2)

    print(f"\n{'='*90}")
    print(f"  {base}")
    print(f"{'='*90}")

    # Find OB93 events on 2W
    ob93_dates = w2k[w2k > 93].index.tolist()

    if not ob93_dates:
        print(f"  No OB93 events found")
        continue

    # Group OB93 into cycles (gap > 60 days = new cycle)
    cycles = []
    current_cycle_start = ob93_dates[0]
    current_cycle_end = ob93_dates[0]
    for dt in ob93_dates[1:]:
        if (dt - current_cycle_end).days > 60:
            cycles.append((current_cycle_start, current_cycle_end))
            current_cycle_start = dt
        current_cycle_end = dt
    cycles.append((current_cycle_start, current_cycle_end))

    print(f"\n  OB93 cycles: {len(cycles)}")
    for cs, ce in cycles:
        print(f"    {cs.strftime('%Y-%m-%d')} to {ce.strftime('%Y-%m-%d')}")

    # For each OB93 cycle, find the first 2D K×D bearish cross AFTER OB93 fires
    print(f"\n  {'OB93 Date':12} {'OB93 Price':>11} {'2D Cross':12} {'Cross Price':>11} {'Days':>5} {'DD30':>7} {'DD60':>7} {'DD90':>7} {'Real':>5}")
    print(f"  {'-'*85}")

    for cycle_start, cycle_end in cycles:
        # OB93 fires on the first candle of this cycle
        ob93_date = cycle_start
        # Get price at OB93
        p_ob = daily_close.index[daily_close.index <= ob93_date]
        ob93_price = daily_close.loc[p_ob[-1]] if len(p_ob) else 0

        # Find first 2D bearish K×D cross after OB93 date
        # K must cross below D, and K should be coming from high (> 50)
        d2k_after = d2k[d2k.index >= ob93_date]
        d2d_after = d2d[d2d.index >= ob93_date]
        common = d2k_after.dropna().index.intersection(d2d_after.dropna().index)

        cross_date = None
        cross_price = None
        for i in range(1, len(common)):
            dt = common[i]
            prev = common[i - 1]
            if d2k.loc[dt] < d2d.loc[dt] and d2k.loc[prev] >= d2d.loc[prev]:
                # Confirm K was recently high (came from overbought on 2D)
                recent = d2k[(d2k.index >= dt - timedelta(days=30)) & (d2k.index <= dt)]
                if len(recent) > 0 and recent.max() > 70:
                    cross_date = dt
                    p_dates = daily_close.index[daily_close.index <= dt]
                    cross_price = daily_close.loc[p_dates[-1]] if len(p_dates) else 0
                    break

        if cross_date and cross_price:
            days_after = (cross_date - ob93_date).days

            # Check drawdown after cross
            future = daily_close[daily_close.index > cross_date]
            dd_30 = dd_60 = dd_90 = 0
            if len(future) > 0:
                f30 = future.iloc[:15]
                f60 = future.iloc[:30]
                f90 = future.iloc[:45]
                if len(f30): dd_30 = (f30.min() / cross_price - 1) * 100
                if len(f60): dd_60 = (f60.min() / cross_price - 1) * 100
                if len(f90): dd_90 = (f90.min() / cross_price - 1) * 100

            is_real = dd_60 < -15
            real_s = "YES" if is_real else "no"

            # Price change from OB93 to 2D cross (how much we gained/lost by waiting)
            price_delta = (cross_price / ob93_price - 1) * 100

            print(f"  {ob93_date.strftime('%Y-%m-%d'):12} ${ob93_price:>10,.2f} "
                  f"{cross_date.strftime('%Y-%m-%d'):12} ${cross_price:>10,.2f} {days_after:>5d} "
                  f"{dd_30:>+6.1f}% {dd_60:>+6.1f}% {dd_90:>+6.1f}% {real_s:>5}")
            print(f"  {'':12} {'':11} Price from OB93: {price_delta:+.1f}%")

            all_results.append({
                "coin": base, "ob93_date": ob93_date, "ob93_price": ob93_price,
                "cross_date": cross_date, "cross_price": cross_price,
                "days": days_after, "dd_30": dd_30, "dd_60": dd_60, "dd_90": dd_90,
                "is_real": is_real, "price_delta": price_delta,
            })
        else:
            print(f"  {ob93_date.strftime('%Y-%m-%d'):12} ${ob93_price:>10,.2f} {'NO CROSS YET':12}")

    # Also show: what if we just used OB93 alone?
    print(f"\n  OB93 alone (sell at OB93 date):")
    for cycle_start, cycle_end in cycles:
        p_ob = daily_close.index[daily_close.index <= cycle_start]
        ob93_price = daily_close.loc[p_ob[-1]] if len(p_ob) else 0
        future = daily_close[daily_close.index > cycle_start]
        dd_60 = 0
        if len(future) > 0:
            f60 = future.iloc[:30]
            if len(f60): dd_60 = (f60.min() / ob93_price - 1) * 100
        is_real = dd_60 < -15
        print(f"    {cycle_start.strftime('%Y-%m-%d')} ${ob93_price:>10,.2f} DD60={dd_60:+.1f}% {'REAL' if is_real else 'false'}")

conn.close()

# Summary
print(f"\n{'='*90}")
print(f"SUMMARY")
print(f"{'='*90}")
total = len(all_results)
real = sum(1 for r in all_results if r["is_real"])
false = total - real
print(f"\n  OB93 + 2D K x D:")
print(f"    Total signals: {total}")
print(f"    Real tops: {real}")
print(f"    False: {false}")
print(f"    Accuracy: {real/total*100:.0f}%" if total else "")
print(f"    False positive rate: {false/total*100:.0f}%" if total else "")
if all_results:
    avg_days = sum(r["days"] for r in all_results) / len(all_results)
    avg_delta = sum(r["price_delta"] for r in all_results) / len(all_results)
    print(f"    Avg days from OB93 to 2D cross: {avg_days:.0f}d")
    print(f"    Avg price change while waiting: {avg_delta:+.1f}%")
print(f"\n  For reference: OB93 alone = 36% false positive rate")
