"""
Bottom Skid Analysis: What happens between conviction fire and 2W K×D cross?

For each bottom event, show daily price path from bottom to K×D cross.
Classify: V-recovery vs flat skid vs choppy.
Focus on ETF-era (2023+) events.
"""
import sqlite3
import numpy as np
import pandas as pd
from datetime import datetime

DB = r"C:\Users\Never\.openclaw\workspace\trading\spot\data\candles.db"

# Bottom events with K<5 threshold from _2w_stochrsi_bottom.py
# Format: (coin, bottom_date, bottom_price, kxd_date, kxd_price)
events = [
    ("ETH", "2021-06-22", 1700.48, "2021-08-01", 2555.69),
    ("ETH", "2022-02-24", 2300.00, "2022-03-27", 3295.65),
    ("ETH", "2022-06-18", 881.56, "2022-07-17", 1338.65),
    ("ETH", "2023-10-12", 1521.00, "2023-10-22", 1663.70),
    ("ETH", "2025-04-09", 1385.05, "2025-05-04", 1808.86),
    ("BTC", "2022-09-21", 18125.98, "2022-10-09", 19439.02),
    ("BTC", "2024-09-06", 52550.00, "2024-09-22", 63578.76),
    ("SOL", "2025-04-07", 95.26, "2025-04-20", 137.86),
    ("LINK", "2022-02-24", 11.40, "2022-03-27", 16.87),
    ("LINK", "2024-08-05", 8.08, "2024-08-25", 12.10),
    ("XRP", "2024-07-05", 0.38, "2024-07-14", 0.52),
    ("XRP", "2025-12-19", 1.77, "2026-01-11", 2.07),
]

conn = sqlite3.connect(DB)

print("BOTTOM SKID ANALYSIS: Price Path from Bottom to 2W K×D Cross")
print("=" * 80)
print()

for coin, bd_s, bp, cd_s, cp in events:
    bd = datetime.strptime(bd_s, "%Y-%m-%d")
    cd = datetime.strptime(cd_s, "%Y-%m-%d")
    days = (cd - bd).days
    total_pct = (cp / bp - 1) * 100
    
    # Determine era
    era = "ETF-ERA" if bd.year >= 2023 else "PRE-ETF"
    
    # Load daily prices for this period
    symbol = f"{coin}/USDT"
    bd_ms = int(bd.timestamp() * 1000)
    cd_ms = int(cd.timestamp() * 1000)
    
    df = pd.read_sql_query(
        "SELECT timestamp, close FROM candles_daily WHERE symbol=? AND timestamp>=? AND timestamp<=? ORDER BY timestamp",
        conn, params=[symbol, bd_ms, cd_ms]
    )
    df["date"] = pd.to_datetime(df["timestamp"], unit="ms")
    
    print(f"{'='*80}")
    print(f"  {coin} | {bd_s} -> {cd_s} | {days}d | +{total_pct:.1f}% | {era}")
    print(f"{'='*80}")
    
    if len(df) < 2:
        print(f"  (insufficient daily data)")
        print()
        continue
    
    # Show weekly snapshots
    bottom = df["close"].iloc[0]
    
    # Calculate key metrics
    prices = df["close"].values
    min_price = prices.min()
    max_price = prices.max()
    
    # What % of total move happened in each third of the period?
    n = len(prices)
    if n >= 3:
        third = n // 3
        p1_start, p1_end = prices[0], prices[third]
        p2_start, p2_end = prices[third], prices[2*third]
        p3_start, p3_end = prices[2*third], prices[-1]
        
        pct1 = (p1_end / p1_start - 1) * 100
        pct2 = (p2_end / p2_start - 1) * 100
        pct3 = (p3_end / p3_start - 1) * 100
        
        print(f"  First third:  {pct1:+.1f}%")
        print(f"  Middle third: {pct2:+.1f}%")
        print(f"  Final third:  {pct3:+.1f}%")
    
    # Max drawdown from bottom (did it retest?)
    retest_low = prices.min()
    retest_pct = (retest_low / bp - 1) * 100
    
    # Price at midpoint
    mid_idx = n // 2
    mid_price = prices[mid_idx]
    mid_pct = (mid_price / bp - 1) * 100
    mid_date = df["date"].iloc[mid_idx].strftime("%Y-%m-%d")
    
    print(f"  Midpoint ({mid_date}): {mid_pct:+.1f}% from bottom")
    print(f"  Retest low: {retest_pct:+.1f}% from bottom")
    print(f"  Final: +{total_pct:.1f}%")
    
    # Classify
    if mid_pct < total_pct * 0.3:
        shape = "SKID (flat then late ramp)"
    elif mid_pct > total_pct * 0.7:
        shape = "V-RECOVERY (early ramp then flat)"
    else:
        shape = "GRADUAL (steady climb)"
    print(f"  Shape: {shape}")
    
    # Show daily price path (sampled every 3-5 days)
    step = max(1, n // 8)
    print(f"  Daily path (sampled):")
    for i in range(0, n, step):
        d = df["date"].iloc[i].strftime("%m-%d")
        p = prices[i]
        pct_from_bottom = (p / bp - 1) * 100
        bar_len = max(0, int(pct_from_bottom / 2))
        bar = "#" * bar_len
        print(f"    {d} ${p:>10.2f} ({pct_from_bottom:+5.1f}%) {bar}")
    # Always show last
    if (n - 1) % step != 0:
        d = df["date"].iloc[-1].strftime("%m-%d")
        p = prices[-1]
        pct_from_bottom = (p / bp - 1) * 100
        bar_len = max(0, int(pct_from_bottom / 2))
        bar = "#" * bar_len
        print(f"    {d} ${p:>10.2f} ({pct_from_bottom:+5.1f}%) {bar}")
    
    print()

conn.close()

# Summary
print("\n" + "=" * 80)
print("SUMMARY BY ERA")
print("=" * 80)
etf_events = [(c, b, bp, cd, cp) for c, b, bp, cd, cp in events 
              if datetime.strptime(b, "%Y-%m-%d").year >= 2023]
pre_events = [(c, b, bp, cd, cp) for c, b, bp, cd, cp in events 
              if datetime.strptime(b, "%Y-%m-%d").year < 2023]

for label, evts in [("PRE-ETF (before 2023)", pre_events), ("ETF-ERA (2023+)", etf_events)]:
    if not evts:
        continue
    pcts = [(float(cp)/float(bp) - 1)*100 for _, _, bp, _, cp in evts]
    days = [(datetime.strptime(cd, "%Y-%m-%d") - datetime.strptime(b, "%Y-%m-%d")).days 
            for _, b, _, cd, _ in evts]
    print(f"\n  {label}: {len(evts)} events")
    print(f"    Avg: {sum(days)/len(days):.0f} days, +{sum(pcts)/len(pcts):.1f}%")
    print(f"    Range: {min(pcts):+.1f}% to {max(pcts):+.1f}%")
