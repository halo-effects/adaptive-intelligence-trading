"""Check ADX values during ETH's Oct 2025 - Feb 2026 markdown period."""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))

import pandas as pd
import numpy as np
from v13_signals import V13SignalPack

pack = V13SignalPack('ETH')
daily = pack.daily

start = pd.Timestamp('2025-10-01')
end = pd.Timestamp('2026-02-25')
mask = (daily.index >= start) & (daily.index <= end)
data = daily[mask]

print("ETH ADX during markdown period (Oct 2025 - Feb 2026)")
print("=" * 70)
print(f"{'Date':<12} {'Close':>8} {'ADX':>6} {'Status':>10}")
print("-" * 70)

adx_values = []
prev_adx = None
for date, row in data.iterrows():
    try:
        adx_val = pack.structure.adx_at(date)
    except:
        adx_val = np.nan
    
    close = row['close']
    
    if not np.isnan(adx_val):
        adx_values.append((date, adx_val))
        status = ""
        if adx_val < 20:
            status = "RANGING"
        elif adx_val < 25:
            status = "weak"
        elif adx_val > 40:
            status = "STRONG"
        else:
            status = "trending"
        
        # Print every Monday
        if date.weekday() == 0:
            print(f"{date.strftime('%Y-%m-%d'):<12} ${close:>7,.0f} {adx_val:>6.1f} {status:>10}")
        prev_adx = adx_val

# Stats
print("\n" + "=" * 70)
if adx_values:
    vals = [v for _, v in adx_values]
    print(f"ADX Stats: min={min(vals):.1f}, max={max(vals):.1f}, avg={np.mean(vals):.1f}")
    below_20 = sum(1 for v in vals if v < 20)
    print(f"Days below 20: {below_20}/{len(vals)} ({below_20/len(vals)*100:.0f}%)")
    
    # Find first time ADX drops below 20
    for date, v in adx_values:
        if v < 20:
            print(f"First ADX < 20: {date.strftime('%Y-%m-%d')} (ADX={v:.1f})")
            break
    else:
        print("ADX never dropped below 20 in this period!")
    
    # Find sustained periods below 20 (7+ consecutive days)
    streak = 0
    streak_start = None
    for date, v in adx_values:
        if v < 20:
            if streak == 0:
                streak_start = date
            streak += 1
        else:
            if streak >= 7:
                print(f"Sustained ranging: {streak_start.strftime('%Y-%m-%d')} - {date.strftime('%Y-%m-%d')} ({streak}d)")
            streak = 0
    if streak >= 7:
        print(f"Sustained ranging: {streak_start.strftime('%Y-%m-%d')} - ongoing ({streak}d)")
