"""
2W K touches 100 + 2D K×D Bearish Cross as Top Signal

Flow:
  1. 2W StochRSI K reaches 100 (even briefly) -> "we're at a top zone"
  2. 2D K crosses below D (from >70) -> execution trigger
  Gate resets when 2W K drops below 10 (new cycle bottom)
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


print("2W K TOUCHES 100 + 2D K x D BEARISH CROSS: TOP SIGNAL")
print("=" * 90)
print("Flow: 2W K reaches 100 (even once) -> armed -> 2D K crosses below D = trigger")
print("Gate resets when 2W K < 10 (bottom zone)")
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

    # Show 2W K max values to see if 100 is reached
    max_k = w2k.max()
    print(f"  2W K max: {max_k:.1f}")

    # Find all dates where 2W K >= 99.5 (effectively 100, floating point)
    k100_dates = w2k[w2k >= 99.5].index.tolist()
    if not k100_dates:
        # Try lower thresholds
        for thresh in [98, 95, 90]:
            kt = w2k[w2k >= thresh]
            if len(kt) > 0:
                print(f"  Never reached 100. Max={max_k:.1f}. Reached >={thresh} on {len(kt)} candles.")
                break
        else:
            print(f"  Never reached 90+. Max={max_k:.1f}")
        continue

    print(f"  2W K=100 dates: {len(k100_dates)}")

    # Group into cycles (gap > 90 days = new cycle)
    cycles = []
    current_start = k100_dates[0]
    current_end = k100_dates[0]
    for dt in k100_dates[1:]:
        if (dt - current_end).days > 90:
            cycles.append((current_start, current_end))
            current_start = dt
        current_end = dt
    cycles.append((current_start, current_end))

    print(f"  Cycles where K hit 100: {len(cycles)}")

    print(f"\n  {'K=100 Date':12} {'Price':>11} {'2D Cross':12} {'Cross$':>11} {'Wait':>5} {'Chg':>7} {'DD30':>7} {'DD60':>7} {'DD90':>7} {'Real':>5}")
    print(f"  {'-'*90}")

    for cs, ce in cycles:
        # Price at first K=100
        p_dates = daily_close.index[daily_close.index <= cs]
        k100_price = daily_close.loc[p_dates[-1]] if len(p_dates) else 0

        # Find first 2D bearish K×D cross AFTER K=100
        # Must have been recently overbought on 2D (K > 70)
        d2k_after = d2k[d2k.index >= cs]
        d2d_after = d2d[d2d.index >= cs]
        common = d2k_after.dropna().index.intersection(d2d_after.dropna().index)

        cross_date = None
        cross_price = None
        for i in range(1, len(common)):
            dt = common[i]
            prev = common[i - 1]
            if d2k.loc[dt] < d2d.loc[dt] and d2k.loc[prev] >= d2d.loc[prev]:
                recent = d2k[(d2k.index >= dt - timedelta(days=20)) & (d2k.index <= dt)]
                if len(recent) > 0 and recent.max() > 70:
                    cross_date = dt
                    p2 = daily_close.index[daily_close.index <= dt]
                    cross_price = daily_close.loc[p2[-1]] if len(p2) else 0
                    break

        if cross_date and cross_price:
            days = (cross_date - cs).days
            price_chg = (cross_price / k100_price - 1) * 100

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

            print(f"  {cs.strftime('%Y-%m-%d'):12} ${k100_price:>10,.2f} "
                  f"{cross_date.strftime('%Y-%m-%d'):12} ${cross_price:>10,.2f} {days:>5d} "
                  f"{price_chg:>+6.1f}% {dd_30:>+6.1f}% {dd_60:>+6.1f}% {dd_90:>+6.1f}% {real_s:>5}")

            all_results.append({
                "coin": base, "k100_date": cs, "k100_price": k100_price,
                "cross_date": cross_date, "cross_price": cross_price,
                "days": days, "price_chg": price_chg,
                "dd_30": dd_30, "dd_60": dd_60, "dd_90": dd_90,
                "is_real": is_real,
            })
        else:
            print(f"  {cs.strftime('%Y-%m-%d'):12} ${k100_price:>10,.2f} {'NO 2D CROSS YET':12}")

conn.close()

# Summary
print(f"\n{'='*90}")
print(f"SUMMARY: 2W K=100 + 2D K x D")
print(f"{'='*90}")
total = len(all_results)
real = sum(1 for r in all_results if r["is_real"])
false = total - real
print(f"\n  Total signals: {total}")
print(f"  Real tops (>15% DD in 60d): {real}")
print(f"  False: {false}")
if total:
    print(f"  Accuracy: {real/total*100:.0f}%")
    print(f"  False positive rate: {false/total*100:.0f}%")
    avg_days = sum(r["days"] for r in all_results) / total
    avg_chg = sum(r["price_chg"] for r in all_results) / total
    print(f"  Avg wait (K=100 to 2D cross): {avg_days:.0f} days")
    print(f"  Avg price change while waiting: {avg_chg:+.1f}%")
print(f"\n  OB93 alone: 36% false positive rate")
print(f"  2D alone: 64% false positive rate")
