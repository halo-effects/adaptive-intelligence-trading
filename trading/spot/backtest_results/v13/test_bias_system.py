"""
V13 Bias System Simulation
Symmetric two-tier gate based on bull/bear macro bias.

Bull bias:
  - MARKUP: Daily HH_HL >= 2 (easy, with trend)
  - MARKDOWN: Daily LH_LL >= 2 + Weekly LH_LL >= 2 (strict, against trend)

Bear bias:
  - MARKUP: Daily HH_HL >= 2 + Weekly HH_HL >= 2 (strict, against trend)
  - MARKDOWN: Daily LH_LL >= 2 (easy, with trend)

Bias triggers:
  - Top signal fires → bear bias
  - Bull flip: tested with multiple triggers
"""
import sys, os
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from v13_signals import V13SignalPack
from build_weekly_signals import build_weekly_candles, compute_weekly_structure, map_weekly_to_daily
from test_signal_candidates import GROUND_TRUTH
import pandas as pd
import numpy as np
from datetime import timedelta

# Known top signals from the engine (2W OB93, 1W OB85, failsafe)
# These are when the engine would detect "top is in"
TOPS = {
    'ETH': [
        ('2021-03-07', '1W K<50 failsafe'),
        ('2021-11-21', 'Nov 2021 blow-off top'),
        ('2024-04-15', 'Rejection at $3.6K'),
        ('2024-12-22', '1W OB85 exit'),
    ],
    'BTC': [
        ('2021-01-25', 'First leg top ~$42K'),
        ('2021-04-27', 'Pre-China ban'),
        ('2024-04-15', 'ETF sell-the-news'),
        ('2025-01-12', '$109K top'),
    ],
    'SOL': [
        ('2024-01-09', '2W OB93 exit at $99'),
        ('2025-09-28', '1W OB85 exit'),
    ],
}

MARKUP_ENTRIES = {
    'ETH': {
        'good': [
            ('2020-10-05', 'DeFi summer recovery'),
            ('2022-09-27', 'Bear bottom attempt'),
            ('2023-10-22', 'Recovery rally'),
            ('2024-10-15', 'Q4 rally'),
        ],
        'bad': [],
    },
    'SOL': {
        'good': [
            ('2023-10-02', 'Big recovery $23→$100'),
            ('2024-04-18', 'Spring rally'),
            ('2025-08-05', 'Recovery'),
        ],
        'bad': [
            ('2022-03-28', 'Bear bounce -25.4%'),
            ('2022-07-29', 'Bear bounce -25.5%'),
            ('2022-11-05', 'FTX -55.4%'),
        ],
    },
    'BTC': {
        'good': [
            ('2020-10-01', 'Post-halving breakout'),
            ('2023-01-09', 'Bear bottom recovery'),
            ('2024-01-29', 'ETF approval rally'),
            ('2024-06-04', 'Post-halving accumulation'),
            ('2025-06-24', 'Recovery rally'),
        ],
        'bad': [],
    },
}

MARKDOWN_ENTRIES = {
    'ETH': {
        'good': [
            ('2022-03-04', 'Bear continuation'),
            ('2025-02-02', 'Post-top decline'),
            ('2025-11-12', 'Year-end decline'),
        ],
        'bad': [],  # bad shorts already blocked by LH_LL gate
    },
    'BTC': {
        'good': [
            ('2022-05-09', 'Luna crash'),
            ('2022-08-19', 'Bear continuation'),
            ('2023-08-22', 'Summer selloff'),
            ('2025-02-26', 'Post-ATH correction'),
        ],
        'bad': [],
    },
    'SOL': {
        'good': [
            ('2021-07-20', 'Early bear'),
            ('2024-08-04', 'Summer selloff'),
            ('2025-10-17', 'Year-end decline'),
        ],
        'bad': [],
    },
}

# Corrections (should NOT trigger markdown)
CORRECTIONS = {
    'ETH': [
        ('2021-05-26', 'China ban dip'),
        ('2024-06-16', 'Summer range'),
    ],
    'BTC': [
        ('2021-09-07', 'El Salvador dip'),
        ('2024-08-05', 'Yen carry unwind'),
    ],
    'SOL': [
        ('2022-03-28', 'Bear bounce (MARKUP_FAIL context)'),
        ('2022-07-29', 'Bear bounce'),
        ('2022-11-05', 'FTX'),
    ],
}


def determine_bias(date, tops, markup_entries_good):
    """
    Determine bias at a given date.
    Start: bull bias (default)
    Top signal → bear bias
    Next good markup entry after bear bias → bull bias restored
    """
    bias = 'bull'
    events = []
    
    for t_date, t_desc in tops:
        events.append((pd.Timestamp(t_date), 'top', t_desc))
    for m_date, m_desc in markup_entries_good:
        events.append((pd.Timestamp(m_date), 'markup', m_desc))
    
    events.sort(key=lambda x: x[0])
    
    for ev_date, ev_type, ev_desc in events:
        if ev_date > pd.Timestamp(date):
            break
        if ev_type == 'top':
            bias = 'bear'
        elif ev_type == 'markup' and bias == 'bear':
            bias = 'bull'
    
    return bias


def check_weekly_signal(daily, mapped_weekly, date, signal_col, threshold=2):
    """Check if weekly signal meets threshold at date."""
    dt = pd.Timestamp(date)
    if dt in mapped_weekly.index:
        val = mapped_weekly.loc[dt, signal_col]
    else:
        idx = mapped_weekly.index.get_indexer([dt], method='pad')[0]
        if idx < 0:
            return False
        val = mapped_weekly.iloc[idx][signal_col]
    return val >= threshold


print("=" * 110)
print("  V13 BIAS SYSTEM SIMULATION")
print("  Bull bias: easy longs, strict shorts | Bear bias: strict longs, easy shorts")
print("=" * 110)

for coin in ['SOL', 'ETH', 'BTC']:
    pack = V13SignalPack(coin)
    daily = pack.daily
    
    # Build weekly signals
    weekly = build_weekly_candles(daily)
    weekly = compute_weekly_structure(weekly)
    weekly_cols = ['weekly_hh_hl', 'weekly_lh_ll']
    mapped = map_weekly_to_daily(daily, weekly, weekly_cols)
    
    tops = TOPS.get(coin, [])
    mu = MARKUP_ENTRIES[coin]
    md = MARKDOWN_ENTRIES[coin]
    corr = CORRECTIONS.get(coin, [])
    
    print(f"\n{'═' * 110}")
    print(f"  {coin}")
    print(f"{'═' * 110}")
    
    # ── MARKUP entries ──
    print(f"\n  ── MARKUP (LONG) ENTRIES ──")
    print(f"  {'Date':<12} {'Type':<10} {'Bias':<6} {'Gate':<20} {'D_HH':>5} {'W_HH':>5} {'Pass?':>6}  Notes")
    print(f"  {'-'*12} {'-'*10} {'-'*6} {'-'*20} {'-'*5} {'-'*5} {'-'*6}  {'-'*35}")
    
    all_mu = [(d, l, 'GOOD') for d, l in mu['good']] + [(d, l, 'FAIL') for d, l in mu['bad']]
    all_mu.sort(key=lambda x: x[0])
    
    for date_str, label, entry_type in all_mu:
        bias = determine_bias(date_str, tops, mu['good'])
        
        # Get daily HH_HL
        dt = pd.Timestamp(date_str)
        idx = daily.index.get_indexer([dt], method='pad')[0]
        d_hh = int(daily.iloc[idx].get('consec_hh_hl', 0))
        
        # Get weekly HH_HL
        w_idx = mapped.index.get_indexer([dt], method='pad')[0]
        w_hh = int(mapped.iloc[w_idx]['weekly_hh_hl']) if w_idx >= 0 else 0
        
        # Determine gate and pass/fail
        if bias == 'bull':
            gate = 'Daily ≥ 2'
            passes = d_hh >= 2
        else:  # bear bias
            gate = 'Daily ≥ 2 + W ≥ 2'
            passes = d_hh >= 2 and w_hh >= 2
        
        icon = '✅' if (passes and entry_type == 'GOOD') or (not passes and entry_type == 'FAIL') else '❌'
        pass_str = 'PASS' if passes else 'BLOCK'
        
        print(f"  {date_str:<12} {entry_type:<10} {bias:<6} {gate:<20} {d_hh:>5} {w_hh:>5} {pass_str:>6}  {icon} {label}")
    
    # ── MARKDOWN entries ──
    print(f"\n  ── MARKDOWN (SHORT) ENTRIES ──")
    print(f"  {'Date':<12} {'Type':<10} {'Bias':<6} {'Gate':<20} {'D_LL':>5} {'W_LL':>5} {'Pass?':>6}  Notes")
    print(f"  {'-'*12} {'-'*10} {'-'*6} {'-'*20} {'-'*5} {'-'*5} {'-'*6}  {'-'*35}")
    
    all_md = [(d, l, 'GOOD') for d, l in md['good']] + [(d, l, 'FAIL') for d, l in md.get('bad', [])]
    all_md.sort(key=lambda x: x[0])
    
    for date_str, label, entry_type in all_md:
        bias = determine_bias(date_str, tops, mu['good'])
        
        dt = pd.Timestamp(date_str)
        idx = daily.index.get_indexer([dt], method='pad')[0]
        d_ll = int(daily.iloc[idx].get('consec_lh_ll', 0))
        
        w_idx = mapped.index.get_indexer([dt], method='pad')[0]
        w_ll = int(mapped.iloc[w_idx]['weekly_lh_ll']) if w_idx >= 0 else 0
        
        if bias == 'bear':
            gate = 'Daily ≥ 2'
            passes = d_ll >= 2
        else:  # bull bias
            gate = 'Daily ≥ 2 + W ≥ 2'
            passes = d_ll >= 2 and w_ll >= 2
        
        icon = '✅' if (passes and entry_type == 'GOOD') or (not passes and entry_type == 'FAIL') else '❌'
        pass_str = 'PASS' if passes else 'BLOCK'
        
        print(f"  {date_str:<12} {entry_type:<10} {bias:<6} {gate:<20} {d_ll:>5} {w_ll:>5} {pass_str:>6}  {icon} {label}")
    
    # ── Correction filter (markdown false alarms) ──
    if corr:
        print(f"\n  ── CORRECTIONS (should NOT trigger markdown) ──")
        print(f"  {'Date':<12} {'Bias':<6} {'Gate':<20} {'D_LL':>5} {'W_LL':>5} {'Pass?':>6}  Notes")
        print(f"  {'-'*12} {'-'*6} {'-'*20} {'-'*5} {'-'*5} {'-'*6}  {'-'*35}")
        
        for date_str, label in corr:
            bias = determine_bias(date_str, tops, mu['good'])
            
            dt = pd.Timestamp(date_str)
            idx = daily.index.get_indexer([dt], method='pad')[0]
            d_ll = int(daily.iloc[idx].get('consec_lh_ll', 0))
            
            w_idx = mapped.index.get_indexer([dt], method='pad')[0]
            w_ll = int(mapped.iloc[w_idx]['weekly_lh_ll']) if w_idx >= 0 else 0
            
            if bias == 'bear':
                gate = 'Daily ≥ 2'
                passes = d_ll >= 2
            else:  # bull bias
                gate = 'Daily ≥ 2 + W ≥ 2'
                passes = d_ll >= 2 and w_ll >= 2
            
            icon = '✅' if not passes else '⚠️ FALSE ALARM'
            pass_str = 'PASS' if passes else 'BLOCK'
            
            print(f"  {date_str:<12} {bias:<6} {gate:<20} {d_ll:>5} {w_ll:>5} {pass_str:>6}  {icon} {label}")

    # ── Bias timeline ──
    print(f"\n  ── BIAS TIMELINE ──")
    events = []
    for t_date, t_desc in tops:
        events.append((t_date, 'TOP → Bear', t_desc))
    for m_date, m_desc in mu['good']:
        events.append((m_date, 'MARKUP → Bull', m_desc))
    events.sort(key=lambda x: x[0])
    
    bias = 'BULL (default)'
    print(f"  Start: {bias}")
    for ev_date, ev_type, ev_desc in events:
        if 'TOP' in ev_type:
            bias = 'BEAR'
        elif 'MARKUP' in ev_type and bias == 'BEAR':
            bias = 'BULL'
        else:
            continue  # markup during bull, no change
        print(f"  {ev_date}  {ev_type:<20} → Now: {bias}  ({ev_desc})")

print(f"\n{'═' * 110}")
print("  SCORING SUMMARY")
print(f"{'═' * 110}")
print("""
  Perfect score:
  ✅ All good MARKUP entries PASS
  ✅ All bad MARKUP entries (MARKUP_FAIL) BLOCKED  
  ✅ All good MARKDOWN entries PASS
  ✅ All corrections BLOCKED (no false alarms)
""")
