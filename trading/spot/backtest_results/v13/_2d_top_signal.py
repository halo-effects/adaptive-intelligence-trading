"""
2D K×D Bearish Cross as Top Signal (with 2W overbought confirmation)

Test: 2W K pinned > 95 (overbought zone) + 2D K crosses below D
Compare timing and false positive rate vs OB93.

For each coin:
  - Find all 2D bearish K×D crosses from overbought
  - Check if 2W was in overbought zone
  - Compare to actual tops
  - Measure false positive rate
"""
import sqlite3
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

DB = r"C:\Users\Never\.openclaw\workspace\trading\spot\data\candles.db"
conn = sqlite3.connect(DB)

COINS = ["ETH/USDT", "SOL/USDT", "LINK/USDT", "XRP/USDT", "BTC/USDT"]

# Known significant tops (>25% decline after)
TOPS = {
    "ETH": [("2024-12-06", 4106.96), ("2025-07-24", 3872.10), ("2025-11-09", 3615.0)],
    "BTC": [("2025-01-20", 109350.0), ("2025-07-24", 112000.0), ("2025-11-09", 98000.0)],
    "SOL": [("2025-01-19", 295.0), ("2025-08-14", 245.0), ("2025-11-22", 245.0)],
    "LINK": [("2024-12-12", 30.80), ("2025-07-14", 30.0), ("2025-12-03", 14.64)],
    "XRP": [("2025-01-15", 3.40), ("2025-05-12", 2.65), ("2025-11-30", 2.90)],
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


print("2D K x D BEARISH CROSS AS TOP SIGNAL")
print("(with 2W overbought confirmation)")
print("=" * 85)
print()

all_signals = []

for sym in COINS:
    base = sym.split("/")[0]

    df = pd.read_sql_query(
        "SELECT timestamp, open, high, low, close, volume FROM candles_daily WHERE symbol=? ORDER BY timestamp",
        conn, params=[sym]
    )
    df["dt"] = pd.to_datetime(df["timestamp"], unit="ms")
    df = df.set_index("dt").sort_index()
    df = df[~df.index.duplicated(keep="last")]

    # Only ETF era
    df = df[df.index >= "2023-01-01"]

    # 2W StochRSI
    w2 = df["close"].resample("2W").last().dropna()
    w2k, w2d = compute_stochrsi(w2)

    # 2D StochRSI
    d2 = df["close"].resample("2D").last().dropna()
    d2k, d2d = compute_stochrsi(d2)

    daily_close = df["close"]

    # Find 2W overbought periods (K > 95)
    w2_ob = w2k > 95
    # Forward-fill to daily: was 2W K > 95 recently (within last 3 2W candles = 6 weeks)?
    w2_ob_daily = w2_ob.reindex(daily_close.index, method="ffill").fillna(False)
    # Create "recently overbought" - was K > 95 in last 42 days?
    w2_recently_ob = pd.Series(False, index=daily_close.index)
    for i, dt in enumerate(daily_close.index):
        window_start = dt - timedelta(days=42)
        w2_in_window = w2k[(w2k.index >= window_start) & (w2k.index <= dt)]
        if len(w2_in_window) > 0 and w2_in_window.max() > 95:
            w2_recently_ob.loc[dt] = True

    # Find all 2D bearish K×D crosses (K drops below D from above)
    # Filter: K must have been > 80 recently (coming from overbought)
    signals = []
    common_idx = d2k.dropna().index.intersection(d2d.dropna().index)

    for i in range(1, len(common_idx)):
        dt = common_idx[i]
        prev = common_idx[i - 1]

        k_now = d2k.loc[dt]
        d_now = d2d.loc[dt]
        k_prev = d2k.loc[prev]
        d_prev = d2d.loc[prev]

        # K crosses below D
        if k_now < d_now and k_prev >= d_prev:
            # Was K > 80 recently (within last 10 2D candles = 20 days)?
            recent_k = d2k[(d2k.index >= dt - timedelta(days=30)) & (d2k.index <= dt)]
            was_ob_2d = recent_k.max() > 80 if len(recent_k) > 0 else False

            # Was 2W recently overbought?
            was_ob_2w = False
            if dt in w2_recently_ob.index:
                was_ob_2w = w2_recently_ob.loc[dt]

            if was_ob_2d:  # At minimum, 2D must have been overbought
                p_dates = daily_close.index[daily_close.index <= dt]
                price = daily_close.loc[p_dates[-1]] if len(p_dates) else 0

                # Check what happened next: max drawdown in 30/60/90 days
                future = daily_close[daily_close.index > dt]
                dd_30 = dd_60 = dd_90 = 0
                if len(future) > 0:
                    f30 = future.iloc[:15]  # ~30 days of daily
                    f60 = future.iloc[:30]
                    f90 = future.iloc[:45]
                    if len(f30): dd_30 = (f30.min() / price - 1) * 100
                    if len(f60): dd_60 = (f60.min() / price - 1) * 100
                    if len(f90): dd_90 = (f90.min() / price - 1) * 100

                # Find nearest actual top
                nearest_top = None
                nearest_gap = None
                if base in TOPS:
                    for tdate_s, tprice in TOPS[base]:
                        tdate = pd.Timestamp(tdate_s)
                        gap = (dt - tdate).days
                        if nearest_gap is None or abs(gap) < abs(nearest_gap):
                            nearest_top = tdate_s
                            nearest_gap = gap

                is_real = dd_60 < -15  # >15% drop in 60 days = real top

                signals.append({
                    "date": dt,
                    "price": price,
                    "k": k_now,
                    "d": d_now,
                    "w2_ob": was_ob_2w,
                    "dd_30": dd_30,
                    "dd_60": dd_60,
                    "dd_90": dd_90,
                    "nearest_top": nearest_top,
                    "gap_days": nearest_gap,
                    "is_real": is_real,
                })
                all_signals.append({"coin": base, **signals[-1]})

    print(f"\n{'='*85}")
    print(f"  {base}")
    print(f"{'='*85}")

    # Show all signals
    print(f"\n  2D Bearish K x D crosses (K was >80 recently):")
    print(f"  {'Date':12} {'Price':>10} {'K':>6} {'2W_OB':>6} {'DD30':>7} {'DD60':>7} {'DD90':>7} {'Real':>5} {'Near Top':>12} {'Gap':>6}")
    print(f"  {'-'*82}")

    for s in signals:
        real = "YES" if s["is_real"] else "no"
        w2ob = "YES" if s["w2_ob"] else "no"
        nt = s["nearest_top"] or ""
        gap = f"{s['gap_days']:+d}d" if s["gap_days"] is not None else ""
        print(f"  {s['date'].strftime('%Y-%m-%d'):12} ${s['price']:>9.2f} {s['k']:>6.1f} {w2ob:>6} "
              f"{s['dd_30']:>+6.1f}% {s['dd_60']:>+6.1f}% {s['dd_90']:>+6.1f}% {real:>5} {nt:>12} {gap:>6}")

    # Stats
    total = len(signals)
    real = sum(1 for s in signals if s["is_real"])
    w2_filtered = [s for s in signals if s["w2_ob"]]
    w2_real = sum(1 for s in w2_filtered if s["is_real"])

    print(f"\n  2D only: {total} signals, {real} real tops = {real/total*100:.0f}% accuracy" if total else "")
    if w2_filtered:
        print(f"  2W+2D:   {len(w2_filtered)} signals, {w2_real} real tops = {w2_real/len(w2_filtered)*100:.0f}% accuracy")
    else:
        print(f"  2W+2D:   0 signals (2W never confirmed overbought)")

conn.close()

# Overall summary
print(f"\n{'='*85}")
print(f"OVERALL SUMMARY")
print(f"{'='*85}")

total_2d = len(all_signals)
real_2d = sum(1 for s in all_signals if s["is_real"])
w2_signals = [s for s in all_signals if s["w2_ob"]]
real_w2 = sum(1 for s in w2_signals if s["is_real"])

print(f"\n  2D bearish cross only:")
print(f"    Signals: {total_2d}, Real tops: {real_2d}, False: {total_2d - real_2d}")
print(f"    Accuracy: {real_2d/total_2d*100:.0f}%" if total_2d else "")
print(f"    False positive rate: {(total_2d-real_2d)/total_2d*100:.0f}%" if total_2d else "")

print(f"\n  2W overbought + 2D bearish cross:")
print(f"    Signals: {len(w2_signals)}, Real tops: {real_w2}, False: {len(w2_signals) - real_w2}")
print(f"    Accuracy: {real_w2/len(w2_signals)*100:.0f}%" if w2_signals else "")
print(f"    False positive rate: {(len(w2_signals)-real_w2)/len(w2_signals)*100:.0f}%" if w2_signals else "")

print(f"\n  For reference: OB93 = 36% false positive rate")
