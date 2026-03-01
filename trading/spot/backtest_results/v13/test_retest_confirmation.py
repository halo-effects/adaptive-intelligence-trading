"""
Test retest confirmation for MARKDOWN entries.
After Fib break, does price retest the broken level?
- Corrections: price bounces back above Fib within days
- Real markdowns: price stays below or retests and gets rejected

Check all known markdown entries + corrections to see if a confirmation
window would have filtered corrections without missing real markdowns.
"""
import sys, os
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from v13_signals import V13SignalPack
from v13_phase_backtest_v8 import compute_fib_levels, price_broke_fib_support
import pandas as pd
import numpy as np

# All MARKDOWN entries from Run 4 (with LH_LL gate)
# Plus the entries that were BLOCKED by LH_LL (to see if retest would have caught them too)
ENTRIES = {
    'ETH': {
        'real_markdowns': [
            ('2022-03-04', 'LH_LL+ADX=21, LOSS -25%'),
            ('2025-02-02', 'LH_LL+ADX=24, WIN +10%'),
            ('2025-11-12', 'LH_LL+ADX=39, WIN +42%'),
        ],
        'blocked_by_lh_ll': [  # Were in Run 3 but blocked by LH_LL gate
            ('2021-05-22', 'No LH_LL, ADX=47, LOSS -26%'),
            ('2022-09-21', 'No LH_LL, ADX=24, LOSS -26%'),
            ('2022-12-26', 'No LH_LL, ADX=21, LOSS -26%'),
            ('2024-05-13', 'No LH_LL, ADX=23, LOSS -27%'),
        ],
    },
    'BTC': {
        'real_markdowns': [
            ('2022-08-19', 'LH_LL+ADX=22, WIN +4%'),
            ('2023-08-22', 'LH_LL+ADX=32, LOSS -3%'),
            ('2025-02-26', 'LH_LL+ADX=42, LOSS -1%'),
        ],
        'blocked_by_lh_ll': [],
    },
    'SOL': {
        'real_markdowns': [
            ('2021-07-20', 'LH_LL+ADX=22'),
            ('2024-08-04', 'LH_LL+ADX=28, LOSS -5%'),
            ('2025-10-17', 'LH_LL+ADX=21, WIN +53%'),
        ],
        'corrections_as_markup': [  # These were MARKUP entries that failed
            ('2022-03-28', 'MARKUP_FAIL -25%'),
            ('2022-07-29', 'MARKUP_FAIL -26%'),
            ('2022-11-05', 'MARKUP_FAIL -55% (FTX)'),
        ],
    },
}

WINDOWS = [3, 5, 7, 10, 14]  # Confirmation window days to test

for coin in ['ETH', 'BTC', 'SOL']:
    pack = V13SignalPack(coin)
    daily = pack.daily
    
    print(f"\n{'═'*110}")
    print(f"  {coin} — Retest Confirmation Analysis")
    print(f"{'═'*110}")
    
    all_entries = []
    for date_str, desc in ENTRIES[coin].get('real_markdowns', []):
        all_entries.append((date_str, desc, 'REAL'))
    for date_str, desc in ENTRIES[coin].get('blocked_by_lh_ll', []):
        all_entries.append((date_str, desc, 'BLOCKED'))
    for date_str, desc in ENTRIES[coin].get('corrections_as_markup', []):
        all_entries.append((date_str, desc, 'CORRECTION'))
    
    for date_str, desc, category in all_entries:
        entry_date = pd.Timestamp(date_str)
        entry_row = daily[daily.index <= entry_date].iloc[-1]
        entry_price = entry_row['close']
        
        # Get Fib levels at entry
        fib = compute_fib_levels(daily, entry_date)
        fib_618 = fib.get(0.618, 0) if fib else 0
        fib_786 = fib.get(0.786, 0) if fib else 0
        fib_500 = fib.get(0.5, 0) if fib else 0
        
        # Get the "resistance level" = the Fib level that was broken
        # (closest Fib level above current price)
        resistance = fib_618 if fib_618 > entry_price else fib_500
        if resistance == 0:
            resistance = entry_price * 1.03  # fallback: 3% above entry
        
        # Also use recent swing high as resistance
        lookback_30d = daily[(daily.index >= entry_date - pd.Timedelta(days=30)) & (daily.index < entry_date)]
        recent_high = lookback_30d['high'].max() if len(lookback_30d) > 0 else entry_price
        
        print(f"\n  {'─'*105}")
        print(f"  {date_str} [{category}] {desc}")
        print(f"  Entry: ${entry_price:.2f} | Fib 0.618: ${fib_618:.2f} | Fib 0.5: ${fib_500:.2f} | Recent high: ${recent_high:.2f}")
        
        # Track what happens in the days after entry
        post = daily[(daily.index > entry_date)][:max(WINDOWS)]
        
        print(f"  {'Day':>5} {'Close':>10} {'High':>10} {'Low':>10} {'vs Entry':>10} {'vs Fib618':>10} {'vs Recent High':>15}")
        
        retested_fib = False
        retested_high = False
        stayed_below_fib = True
        stayed_below_high = True
        
        retest_results = {}
        
        for i, (idx, row) in enumerate(post.iterrows()):
            day_num = i + 1
            vs_entry = (row['close'] / entry_price - 1) * 100
            vs_fib = (row['high'] / fib_618 - 1) * 100 if fib_618 > 0 else 0
            vs_high = (row['high'] / recent_high - 1) * 100
            
            # Did price touch/exceed the resistance level?
            if row['high'] >= fib_618 and fib_618 > 0:
                retested_fib = True
                stayed_below_fib = False
            if row['high'] >= recent_high:
                retested_high = True
                stayed_below_high = False
            
            # For each window size, record if price stayed below
            for w in WINDOWS:
                if day_num == w:
                    retest_results[w] = {
                        'below_fib': stayed_below_fib if fib_618 > 0 else None,
                        'below_high': stayed_below_high,
                        'max_bounce': max([(daily.iloc[j]['high'] / entry_price - 1) * 100 
                                          for j in range(daily.index.get_loc(entry_date) + 1, 
                                                        min(daily.index.get_loc(entry_date) + w + 1, len(daily)))]),
                    }
            
            if day_num <= 14:
                marker = ""
                if row['high'] >= fib_618 and fib_618 > 0:
                    marker += " ← TOUCHED FIB"
                if row['high'] >= recent_high:
                    marker += " ← TOUCHED HIGH"
                print(f"  {day_num:>5} ${row['close']:>9.2f} ${row['high']:>9.2f} ${row['low']:>9.2f} {vs_entry:>+9.1f}% {vs_fib:>+9.1f}% {vs_high:>+14.1f}%{marker}")
        
        # Summary for this entry
        print(f"\n  Retest Summary:")
        for w in WINDOWS:
            if w in retest_results:
                r = retest_results[w]
                fib_status = "BELOW" if r['below_fib'] else "RETESTED" if r['below_fib'] is not None else "N/A"
                high_status = "BELOW" if r['below_high'] else "RETESTED"
                bounce = r['max_bounce']
                would_confirm = "CONFIRMED ✅" if r['below_fib'] or r['below_fib'] is None else "REJECTED ❌"
                if category == 'BLOCKED' or category == 'CORRECTION':
                    would_confirm = "REJECTED ✅ (correctly filtered)" if not r['below_fib'] else "CONFIRMED ❌ (false confirm)"
                print(f"    {w}d window: Fib={fib_status}, High={high_status}, MaxBounce={bounce:+.1f}% → {would_confirm}")

print(f"\n{'═'*110}")
print(f"  CONCLUSION")
print(f"{'═'*110}")
