"""Check HVF values at SOL MARKUP_FAIL dates and good markup dates."""
import sys, os
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from v13_signals import V13SignalPack
from test_hvf_daily import composite_hvf_score
import pandas as pd
import numpy as np

HVF_LOOKBACK = 44

def check_hvf(coin, dates_with_labels):
    pack = V13SignalPack(coin)
    daily = pack.daily
    
    print(f"\n{'='*80}")
    print(f"  {coin} — HVF at MARKUP entry points")
    print(f"{'='*80}")
    print(f"  {'Date':<12} {'Type':<15} {'HVF':>6} {'Vuvu':>6} {'Vol':>6} {'Price':>6}  Notes")
    print(f"  {'-'*12} {'-'*15} {'-'*6} {'-'*6} {'-'*6} {'-'*6}  {'-'*30}")
    
    for date_str, label, entry_type in dates_with_labels:
        date = pd.Timestamp(date_str)
        idx = daily.index.get_indexer([date], method='pad')[0]
        if idx < HVF_LOOKBACK:
            print(f"  {date_str:<12} {entry_type:<15} {'N/A':>6} — insufficient data")
            continue
        
        window = daily.iloc[max(0, idx - HVF_LOOKBACK):idx + 1]
        result = composite_hvf_score(window)
        composite, vuvu, vol_comp, price_comp = result
        
        # Extract scalar values
        def scalar(v):
            if hasattr(v, 'iloc'):
                return float(v.iloc[-1]) if len(v) > 0 else 0.0
            return float(v)
        
        c, v, vc, pc = scalar(composite), scalar(vuvu), scalar(vol_comp), scalar(price_comp)
        close = daily.iloc[idx]['close']
        
        print(f"  {date_str:<12} {entry_type:<15} {c:>6.3f} {v:>6.3f} {vc:>6.3f} {pc:>6.3f}  {label} (${close:.0f})")

# SOL
check_hvf('SOL', [
    # Good markups
    ('2023-10-02', 'Big recovery $23→$100', 'GOOD MARKUP'),
    ('2024-04-18', 'Spring rally', 'GOOD MARKUP'),
    ('2025-08-05', 'Recovery', 'GOOD MARKUP'),
    # Bad markups (MARKUP_FAIL)
    ('2022-03-28', 'Bear bounce -25.4%', 'MARKUP_FAIL'),
    ('2022-07-29', 'Bear bounce -25.5%', 'MARKUP_FAIL'),
    ('2022-11-05', 'FTX collapse -55.4%', 'MARKUP_FAIL'),
])

# ETH
check_hvf('ETH', [
    ('2020-10-05', 'DeFi summer recovery', 'GOOD MARKUP'),
    ('2022-09-27', 'Bear bottom attempt', 'GOOD MARKUP'),
    ('2023-10-22', 'Recovery rally', 'GOOD MARKUP'),
    ('2024-10-15', 'Q4 rally', 'GOOD MARKUP'),
])

# BTC
check_hvf('BTC', [
    ('2020-10-01', 'Post-halving breakout', 'GOOD MARKUP'),
    ('2023-01-09', 'Bear bottom recovery', 'GOOD MARKUP'),
    ('2024-01-29', 'ETF approval rally', 'GOOD MARKUP'),
    ('2024-06-04', 'Post-halving accumulation', 'GOOD MARKUP'),
    ('2025-06-24', 'Recovery rally', 'GOOD MARKUP'),
])

print(f"\n{'='*80}")
print("  INTERPRETATION GUIDE")
print(f"{'='*80}")
print("""
  HVF composite = weighted blend of vuvuzela (volume funnel) + volume + price components
  Range: 0.0 to 1.0
  
  High HVF (>0.4) = energy building, volume contracting into a funnel — breakout imminent
  Low HVF (<0.2)  = no energy accumulation — weak/false breakout likely
  
  Question: Do MARKUP_FAIL entries have LOW HVF (no energy)?
  If so, HVF could gate markup entry: require HVF > threshold to confirm.
""")
