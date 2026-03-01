"""
Compare 2D K×D crossover timing vs 2W K>=5 at historical bottoms.

For each bottom:
  - When does 2W K first go < 5? (zone entry)
  - When does 2W K first >= 5? (old gate)
  - When does 2D K cross above D (after 2W pinned)? (new trigger)
  - Price at each, % from bottom
"""
import sqlite3
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

DB = r"C:\Users\Never\.openclaw\workspace\trading\spot\data\candles.db"
conn = sqlite3.connect(DB)

COINS = ["ETH/USDT", "SOL/USDT", "BTC/USDT", "LINK/USDT", "XRP/USDT"]

# Known significant bottoms (ETF-era focus but include 2022 for ETH/BTC)
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


print("2D K x D CROSSOVER vs 2W K>=5: TIMING COMPARISON")
print("=" * 90)
print()

summary = []

for sym in COINS:
    base = sym.split("/")[0]
    if base not in BOTTOMS:
        continue

    # Load daily
    df = pd.read_sql_query(
        "SELECT timestamp, open, high, low, close, volume FROM candles_daily WHERE symbol=? ORDER BY timestamp",
        conn, params=[sym]
    )
    df["dt"] = pd.to_datetime(df["timestamp"], unit="ms")
    df = df.set_index("dt").sort_index()
    df = df[~df.index.duplicated(keep="last")]

    # 2W StochRSI
    w2 = df["close"].resample("2W").last().dropna()
    w2k, w2d = compute_stochrsi(w2)

    # 2D StochRSI
    d2 = df["close"].resample("2D").last().dropna()
    d2k, d2d = compute_stochrsi(d2)

    # Also get daily prices for lookups
    daily_close = df["close"]

    print(f"{'='*90}")
    print(f"  {base}")
    print(f"{'='*90}")

    for bdate_s, bprice in BOTTOMS[base]:
        bdate = pd.Timestamp(bdate_s)
        print(f"\n  Bottom: {bdate_s} @ ${bprice:,.2f}")

        # Find when 2W K first < 5 (before or at bottom)
        w2k_before = w2k[w2k.index <= bdate + timedelta(days=30)]
        pinned_dates = w2k_before[w2k_before < 5]
        if len(pinned_dates) > 0:
            # Find the start of the pinned period containing the bottom
            pin_start = None
            for i in range(len(pinned_dates) - 1, -1, -1):
                dt = pinned_dates.index[i]
                if i == 0 or (pinned_dates.index[i] - pinned_dates.index[i-1]).days > 30:
                    pin_start = dt
                    break
                pin_start = dt
            print(f"  2W K < 5 from: {pin_start.strftime('%Y-%m-%d')}")

        # Find when 2W K first >= 5 after bottom
        w2k_after = w2k[w2k.index >= bdate]
        w2_lift = w2k_after[w2k_after >= 5]
        w2_lift_date = None
        w2_lift_price = None
        if len(w2_lift) > 0:
            w2_lift_date = w2_lift.index[0]
            # Get price at that date
            p_dates = daily_close.index[daily_close.index <= w2_lift_date]
            if len(p_dates):
                w2_lift_price = daily_close.loc[p_dates[-1]]

        # Find when 2D K crosses above D after bottom (while 2W was pinned)
        d2k_after = d2k[d2k.index >= bdate - timedelta(days=7)]
        d2d_after = d2d[d2d.index >= bdate - timedelta(days=7)]
        common_idx = d2k_after.index.intersection(d2d_after.index)
        
        d2_cross_date = None
        d2_cross_price = None
        for i in range(1, len(common_idx)):
            dt = common_idx[i]
            prev_dt = common_idx[i-1]
            k_now = d2k_after.loc[dt]
            d_now = d2d_after.loc[dt]
            k_prev = d2k_after.loc[prev_dt]
            d_prev = d2d_after.loc[prev_dt]
            
            # K crosses above D, and K was recently low (< 30 to filter noise)
            if k_now > d_now and k_prev <= d_prev and k_now < 50:
                # Only count if after the actual bottom date
                if dt >= bdate:
                    d2_cross_date = dt
                    p_dates = daily_close.index[daily_close.index <= dt]
                    if len(p_dates):
                        d2_cross_price = daily_close.loc[p_dates[-1]]
                    break

        # Print comparison
        if w2_lift_date and w2_lift_price:
            w2_days = (w2_lift_date - bdate).days
            w2_pct = (w2_lift_price / bprice - 1) * 100
            print(f"  2W K>=5:    {w2_lift_date.strftime('%Y-%m-%d')} ({w2_days:3d}d) @ ${w2_lift_price:>10,.2f} ({w2_pct:+.1f}%)")
        else:
            print(f"  2W K>=5:    NOT YET")
            w2_days = None
            w2_pct = None

        if d2_cross_date and d2_cross_price:
            d2_days = (d2_cross_date - bdate).days
            d2_pct = (d2_cross_price / bprice - 1) * 100
            print(f"  2D K x D:   {d2_cross_date.strftime('%Y-%m-%d')} ({d2_days:3d}d) @ ${d2_cross_price:>10,.2f} ({d2_pct:+.1f}%)")
        else:
            print(f"  2D K x D:   NOT YET")
            d2_days = None
            d2_pct = None

        if w2_days is not None and d2_days is not None:
            saved = w2_days - d2_days
            pct_saved = (w2_pct or 0) - (d2_pct or 0)
            print(f"  --> 2D is {saved}d faster, saves {pct_saved:.1f}% of missed move")
            summary.append((base, bdate_s, d2_days, d2_pct, w2_days, w2_pct, saved))
        elif d2_days is not None:
            summary.append((base, bdate_s, d2_days, d2_pct, None, None, None))

        # Show 2D K/D around the bottom for context
        print(f"\n  2D StochRSI around bottom:")
        print(f"  {'Date':12} {'Close':>10} {'K':>8} {'D':>8} {'K>D':>5}")
        print(f"  {'-'*48}")
        window = d2k[(d2k.index >= bdate - timedelta(days=14)) & 
                      (d2k.index <= bdate + timedelta(days=60))]
        for dt in window.index:
            kv = d2k.loc[dt] if dt in d2k.index else np.nan
            dv = d2d.loc[dt] if dt in d2d.index else np.nan
            p_dates = daily_close.index[daily_close.index <= dt]
            price = daily_close.loc[p_dates[-1]] if len(p_dates) else 0
            cross = "<<<" if (not np.isnan(kv) and not np.isnan(dv) and kv > dv and 
                             dt == d2_cross_date) else ("Y" if kv > dv else "")
            print(f"  {dt.strftime('%Y-%m-%d'):12} ${price:>9.2f} {kv:>8.1f} {dv:>8.1f} {cross:>5}")

# Summary table
print(f"\n{'='*90}")
print(f"SUMMARY: 2D K x D vs 2W K>=5")
print(f"{'='*90}")
print(f"  {'Coin':6} {'Bottom':12} {'2D Days':>8} {'2D %':>8} {'2W Days':>8} {'2W %':>8} {'Saved':>8}")
print(f"  {'-'*62}")
for base, bdate, d2d_val, d2p, w2d_val, w2p, saved in summary:
    d2d_s = f"{d2d_val}d" if d2d_val is not None else "N/A"
    d2p_s = f"{d2p:+.1f}%" if d2p is not None else "N/A"
    w2d_s = f"{w2d_val}d" if w2d_val is not None else "N/A"
    w2p_s = f"{w2p:+.1f}%" if w2p is not None else "N/A"
    saved_s = f"{saved}d" if saved is not None else "-"
    print(f"  {base:6} {bdate:12} {d2d_s:>8} {d2p_s:>8} {w2d_s:>8} {w2p_s:>8} {saved_s:>8}")

# Averages
d2_days_all = [s[2] for s in summary if s[2] is not None]
d2_pcts_all = [s[3] for s in summary if s[3] is not None]
w2_days_all = [s[4] for s in summary if s[4] is not None]
w2_pcts_all = [s[5] for s in summary if s[5] is not None]
saved_all = [s[6] for s in summary if s[6] is not None]

if d2_days_all:
    print(f"\n  2D avg: {sum(d2_days_all)/len(d2_days_all):.0f}d, {sum(d2_pcts_all)/len(d2_pcts_all):+.1f}%")
if w2_days_all:
    print(f"  2W avg: {sum(w2_days_all)/len(w2_days_all):.0f}d, {sum(w2_pcts_all)/len(w2_pcts_all):+.1f}%")
if saved_all:
    print(f"  Avg saved: {sum(saved_all)/len(saved_all):.0f}d faster with 2D")

conn.close()
