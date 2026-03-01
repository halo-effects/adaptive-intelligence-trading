"""Debug why ZEC never entered MARKUP during its 25x rally."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from v13_signals import V13SignalPack
from test_hvf_daily import composite_hvf_score, detect_swing_points
import pandas as pd
import numpy as np

pack = V13SignalPack('ZEC')
daily = pack.daily

print(f"ZEC daily data: {daily.index[0].date()} to {daily.index[-1].date()}")
print(f"Price range: ${daily['close'].min():.2f} - ${daily['close'].max():.2f}")
print()

# Check HH_HL signals (markup entry requirement)
print("=" * 70)
print("HH_HL STREAKS (markup entry signal)")
print("=" * 70)

for date in pd.date_range('2024-10-01', '2025-12-01', freq='W'):
    date = pd.Timestamp(date)
    if date not in daily.index:
        nearest = daily.index[daily.index.get_indexer([date], method='pad')[0]]
        date = nearest
    streak = pack.structure.hh_hl_streak(date)
    price = daily.loc[date, 'close'] if date in daily.index else None
    if streak >= 2 and price:
        print(f"  {date.date()}: HH_HL streak={streak}, price=${price:.2f}")

print()
print("=" * 70)
print("FIBONACCI SUPPORT CHECK during rally")
print("=" * 70)

# Import the fib functions from v8
from v13_phase_backtest_v8 import (
    compute_fib_levels, price_near_fib_support, FIB_TOLERANCE
)

for date in pd.date_range('2024-10-01', '2025-12-01', freq='W'):
    date = pd.Timestamp(date)
    if date not in daily.index:
        idx = daily.index.get_indexer([date], method='pad')[0]
        if idx < 0: continue
        date = daily.index[idx]
    
    price = daily.loc[date, 'close']
    fib = compute_fib_levels(daily, date, lookback=120)
    near_fib = price_near_fib_support(price, fib) if fib else False
    streak = pack.structure.hh_hl_streak(date)
    adx = pack.structure.adx_at(date)
    
    # SMA200 overextension
    sma200_val = pack.sma200.overextension_at(date)
    
    if streak >= 1 or near_fib:
        fib_info = ""
        if fib:
            for ratio in [0.236, 0.382, 0.5, 0.618, 0.786]:
                level = fib.get(ratio, 0)
                dist = abs(price - level) / level * 100 if level > 0 else 999
                if dist < 10:
                    fib_info += f" Fib{ratio}=${level:.2f}({dist:.1f}%)"
        
        markup_ok = streak >= 2 and near_fib and (sma200_val is not None and sma200_val <= 0.20)
        flag = " *** MARKUP ENTRY ***" if markup_ok else ""
        sma_str = f"{sma200_val:.1%}" if sma200_val is not None else "N/A"
        print(f"  {date.date()}: price=${price:.2f}, HH_HL={streak}, near_fib={near_fib}, "
              f"ADX={adx:.0f}, SMA200={sma_str}{fib_info}{flag}")

print()
print("=" * 70)
print("SMA200 OVEREXTENSION during rally")
print("=" * 70)

for date in pd.date_range('2024-10-01', '2025-12-01', freq='2W'):
    date = pd.Timestamp(date)
    if date not in daily.index:
        idx = daily.index.get_indexer([date], method='pad')[0]
        if idx < 0: continue
        date = daily.index[idx]
    
    price = daily.loc[date, 'close']
    sma200_val = pack.sma200.overextension_at(date)
    blocked = sma200_val is not None and sma200_val > 0.20
    
    sma_str = f"{sma200_val:.1%}" if sma200_val is not None else "N/A"
    print(f"  {date.date()}: price=${price:.2f}, SMA200_overext={sma_str}"
          f"{'  *** BLOCKED ***' if blocked else ''}")

print()
print("=" * 70)
print("WEEKLY STOCHRSI (top signals)")
print("=" * 70)

# Check if 2W stochRSI ever went OB
for date in pd.date_range('2024-10-01', '2026-02-01', freq='W'):
    date = pd.Timestamp(date)
    k_2w = pack.stoch_2w.get_k_at(date)
    k_1w = pack.stoch_1w.get_k_at(date)
    if date in daily.index:
        price = daily.loc[date, 'close']
    else:
        continue
    
    if k_2w and k_2w > 80:
        print(f"  {date.date()}: 2W K={k_2w:.0f}, 1W K={k_1w:.0f}, price=${price:.2f}")
    elif k_1w and k_1w > 80:
        print(f"  {date.date()}: 2W K={k_2w:.0f}, 1W K={k_1w:.0f}, price=${price:.2f}")
