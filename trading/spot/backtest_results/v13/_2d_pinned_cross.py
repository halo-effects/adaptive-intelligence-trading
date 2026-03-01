"""
Refined bottom signal: 2W K at 0 + 2D K at 0 + 2D K×D cross up

Both timeframes must show exhaustion before the 2D cross counts.
Compare to previous results.
"""
import sqlite3
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

DB = r"C:\Users\Never\.openclaw\workspace\trading\spot\data\candles.db"
conn = sqlite3.connect(DB)

COINS = ["ETH/USDT", "SOL/USDT", "LINK/USDT", "XRP/USDT", "BTC/USDT"]

BOTTOMS = {
    "ETH": [("2022-06-18", 881.56), ("2023-10-12", 1521.00), ("2025-04-09", 1385.05)],
    "BTC": [("2022-09-21", 18125.98), ("2024-09-06", 52550.00)],
    "SOL": [("2025-04-07", 95.26), ("2025-12-18", 116.88)],
    "LINK": [("2024-08-05", 8.08), ("2025-10-10", 7.90)],
    "XRP": [("2024-07-05", 0.38), ("2025-12-19", 1.77)],
}


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


print("REFINED BOTTOM: 2W K<5 + 2D K<5 + 2D K x D CROSS UP")
print("=" * 90)
print("Both timeframes must show exhaustion (K<5) before 2D cross counts")
print()

for sym in COINS:
    base = sym.split("/")[0]
    if base not in BOTTOMS:
        continue

    df = pd.read_sql_query(
        "SELECT timestamp, open, high, low, close, volume FROM candles_daily WHERE symbol=? ORDER BY timestamp",
        conn, params=[sym]
    )
    df["dt"] = pd.to_datetime(df["timestamp"], unit="ms")
    df = df.set_index("dt").sort_index()
    df = df[~df.index.duplicated(keep="last")]

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

    for bdate_s, bprice in BOTTOMS[base]:
        bdate = pd.Timestamp(bdate_s)

        # Check: was 2W K < 5 around this bottom?
        w2k_around = w2k[(w2k.index >= bdate - timedelta(days=60)) & (w2k.index <= bdate + timedelta(days=60))]
        w2_pinned = w2k_around[w2k_around < 5]
        w2_was_pinned = len(w2_pinned) > 0

        # Check: was 2D K < 5 around this bottom?
        d2k_around = d2k[(d2k.index >= bdate - timedelta(days=30)) & (d2k.index <= bdate + timedelta(days=30))]
        d2_pinned = d2k_around[d2k_around < 5]
        d2_was_pinned = len(d2_pinned) > 0

        print(f"\n  Bottom: {bdate_s} @ ${bprice:,.2f}")
        print(f"  2W K pinned (<5): {'YES' if w2_was_pinned else 'NO'} (min={w2k_around.min():.1f})")
        print(f"  2D K pinned (<5): {'YES' if d2_was_pinned else 'NO'} (min={d2k_around.min():.1f})")

        if not w2_was_pinned:
            print(f"  SKIP: 2W not pinned")
            continue

        if not d2_was_pinned:
            print(f"  SKIP: 2D not pinned")
            continue

        # Find first 2D K×D cross up AFTER 2D was pinned < 5
        # Must happen after the 2D pinned date
        d2_pin_date = d2_pinned.index[-1]  # Last date 2D K was < 5
        
        d2k_after = d2k[d2k.index >= d2_pin_date]
        d2d_after = d2d[d2d.index >= d2_pin_date]
        common = d2k_after.dropna().index.intersection(d2d_after.dropna().index)

        cross_date = None
        cross_price = None
        for i in range(1, len(common)):
            dt = common[i]
            prev = common[i - 1]
            k_now = d2k.loc[dt]
            d_now = d2d.loc[dt]
            k_prev = d2k.loc[prev]
            d_prev = d2d.loc[prev]
            if k_now > d_now and k_prev <= d_prev and k_now >= 5:
                cross_date = dt
                p_dates = daily_close.index[daily_close.index <= dt]
                cross_price = daily_close.loc[p_dates[-1]] if len(p_dates) else 0
                break

        if cross_date:
            days = (cross_date - bdate).days
            pct = (cross_price / bprice - 1) * 100

            # Also get 2W K>=5 date for comparison
            w2k_after = w2k[w2k.index >= bdate]
            w2_lift = w2k_after[w2k_after >= 5]
            w2_date = w2_lift.index[0] if len(w2_lift) > 0 else None
            w2_days = (w2_date - bdate).days if w2_date else None
            w2_p = None
            if w2_date:
                p2 = daily_close.index[daily_close.index <= w2_date]
                w2_p = daily_close.loc[p2[-1]] if len(p2) else None
            w2_pct = ((w2_p / bprice - 1) * 100) if w2_p else None

            print(f"  2D pinned on:  {d2_pin_date.strftime('%Y-%m-%d')}")
            print(f"  2D K x D cross: {cross_date.strftime('%Y-%m-%d')} ({days}d) @ ${cross_price:,.2f} ({pct:+.1f}%)")
            if w2_date:
                print(f"  2W K>=5:        {w2_date.strftime('%Y-%m-%d')} ({w2_days}d) @ ${w2_p:,.2f} ({w2_pct:+.1f}%)")
                saved = w2_days - days
                print(f"  --> 2D is {saved}d faster")
            else:
                print(f"  2W K>=5:        NOT YET")
                print(f"  --> 2D fires, 2W still waiting")

            # Show what price did after cross
            future = daily_close[(daily_close.index > cross_date) & 
                                 (daily_close.index <= cross_date + timedelta(days=30))]
            if len(future) > 0:
                max_dd = (future.min() / cross_price - 1) * 100
                max_up = (future.max() / cross_price - 1) * 100
                print(f"  30d after cross: max up {max_up:+.1f}%, max dd {max_dd:+.1f}%")
        else:
            print(f"  2D K x D cross: NOT YET")

    # Current state
    print(f"\n  Current 2D K/D (last 5):")
    for dt in d2k.dropna().index[-5:]:
        kv = d2k.loc[dt]
        dv = d2d.loc[dt] if dt in d2d.index else np.nan
        cross = "K>D" if kv > dv else "K<D"
        print(f"    {dt.strftime('%Y-%m-%d')} K={kv:.1f} D={dv:.1f} {cross}")

conn.close()
