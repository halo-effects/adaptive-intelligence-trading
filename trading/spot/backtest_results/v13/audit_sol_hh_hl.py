"""Check HH_HL values around SOL MARKUP entries in 2022."""
import sys, os
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from v13_signals import V13SignalPack
from v13_phase_backtest_v8 import compute_fib_levels, price_near_fib_support
import pandas as pd
import numpy as np

pack = V13SignalPack('SOL')
daily = pack.daily

# Check consec_hh_hl around each entry date
entries = ['2022-03-28', '2022-07-29', '2022-11-05']

for entry_str in entries:
    entry = pd.Timestamp(entry_str)
    print(f"\n{'='*80}")
    print(f"  SOL MARKUP entry: {entry_str}")
    print(f"{'='*80}")
    
    # Show 10 days before and 3 after
    window = daily[(daily.index >= entry - pd.Timedelta(days=15)) & (daily.index <= entry + pd.Timedelta(days=3))]
    
    print(f"  {'Date':<12} {'Close':>8} {'HH_HL':>6} {'LH_LL':>6} {'ADX':>6} {'vsSMA200':>9} {'FibNear':>8}")
    print(f"  {'-'*12} {'-'*8} {'-'*6} {'-'*6} {'-'*6} {'-'*9} {'-'*8}")
    
    for idx, row in window.iterrows():
        hh_hl = row.get('consec_hh_hl', 0)
        lh_ll = row.get('consec_lh_ll', 0)
        adx = row.get('adx', np.nan)
        vs_sma200 = row.get('price_vs_sma200', np.nan)
        
        fib = compute_fib_levels(daily, idx)
        price = row['close']
        near_fib = price_near_fib_support(price, fib) if fib else False
        
        marker = " <<< ENTRY" if idx.strftime('%Y-%m-%d') == entry_str else ""
        print(f"  {idx.strftime('%Y-%m-%d'):<12} ${price:>7.2f} {hh_hl:>6} {lh_ll:>6} {adx:>6.1f} {vs_sma200:>+8.1f}% {str(near_fib):>8}{marker}")
