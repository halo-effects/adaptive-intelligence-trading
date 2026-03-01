"""
V13 Hybrid Bias System — Asymmetric Triggers

Into bear bias (fast):
  - Engine top signal (2W OB93 / 1W OB85 / failsafe)
  - OR Death Cross (SMA50 < SMA200) as fallback

Back to bull bias (fast):
  - Price reclaims SMA200

Gate logic:
  Bull bias: Daily HH_HL ≥ 2 for markup, Daily LH_LL ≥ 2 + Weekly LH_LL ≥ 2 for markdown
  Bear bias: Daily HH_HL ≥ 2 + Weekly HH_HL ≥ 2 for markup, Daily LH_LL ≥ 2 for markdown
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

# Engine top signals
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
        'bad': [],
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


def compute_bias_timeline(daily, tops, start_date='2020-01-01', end_date='2026-03-01'):
    """
    Compute daily bias using hybrid triggers:
    - Bear: engine top signal OR death cross (SMA50 < SMA200)
    - Bull: price reclaims SMA200
    
    Returns Series of 'bull'/'bear' indexed by date.
    """
    bias = pd.Series('bull', index=daily.index)
    current = 'bull'
    
    top_dates = set(pd.Timestamp(d) for d, _ in tops)
    
    for i, date in enumerate(daily.index):
        close = daily.iloc[i]['close']
        sma50 = daily.iloc[i].get('sma50', np.nan)
        sma200 = daily.iloc[i].get('sma200', np.nan)
        
        if current == 'bull':
            # Check for bear triggers
            # 1. Engine top signal
            if date in top_dates:
                current = 'bear'
            # 2. Death cross fallback
            elif not np.isnan(sma50) and not np.isnan(sma200) and sma50 < sma200:
                current = 'bear'
        
        elif current == 'bear':
            # Check for bull trigger: price reclaims SMA200
            if not np.isnan(sma200) and close > sma200:
                current = 'bull'
        
        bias.iloc[i] = current
    
    return bias


def get_bias_at(bias_series, date):
    """Get bias at a specific date."""
    dt = pd.Timestamp(date)
    idx = bias_series.index.get_indexer([dt], method='pad')[0]
    if idx < 0:
        return 'bull'
    return bias_series.iloc[idx]


print("=" * 110)
print("  V13 HYBRID BIAS SYSTEM")
print("  Bear trigger: Engine top OR Death Cross | Bull trigger: Price > SMA200")
print("=" * 110)

# Track scores
total_good_markup_pass = 0
total_good_markup_total = 0
total_bad_markup_block = 0
total_bad_markup_total = 0
total_good_md_pass = 0
total_good_md_total = 0
total_corr_block = 0
total_corr_total = 0

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
    
    # Compute bias timeline
    bias_series = compute_bias_timeline(daily, tops)
    
    print(f"\n{'═' * 110}")
    print(f"  {coin}")
    print(f"{'═' * 110}")
    
    # ── Bias transitions ──
    print(f"\n  ── BIAS TRANSITIONS ──")
    prev = None
    transitions = []
    for i, date in enumerate(daily.index):
        b = bias_series.iloc[i]
        if b != prev:
            close = daily.iloc[i]['close']
            sma50 = daily.iloc[i].get('sma50', np.nan)
            sma200 = daily.iloc[i].get('sma200', np.nan)
            
            # Determine trigger
            if b == 'bear':
                if date in set(pd.Timestamp(d) for d, _ in tops):
                    trigger = 'TOP SIGNAL'
                else:
                    trigger = 'DEATH CROSS'
            else:
                trigger = 'PRICE > SMA200'
            
            if prev is not None:  # skip initial
                transitions.append((date, prev, b, trigger, close, sma200))
                print(f"  {date.strftime('%Y-%m-%d')}  {prev} → {b}  via {trigger:<15}  (price=${close:.0f}, SMA200=${sma200:.0f})")
            prev = b
    
    # Count time in each bias
    bull_days = (bias_series == 'bull').sum()
    bear_days = (bias_series == 'bear').sum()
    print(f"  Total: {bull_days} bull days, {bear_days} bear days ({bear_days/(bull_days+bear_days)*100:.0f}% bear)")
    
    # ── MARKUP entries ──
    print(f"\n  ── MARKUP (LONG) ENTRIES ──")
    print(f"  {'Date':<12} {'Type':<10} {'Bias':<6} {'Gate':<22} {'D_HH':>5} {'W_HH':>5} {'Pass?':>6}  Notes")
    print(f"  {'-'*12} {'-'*10} {'-'*6} {'-'*22} {'-'*5} {'-'*5} {'-'*6}  {'-'*35}")
    
    all_mu = [(d, l, 'GOOD') for d, l in mu['good']] + [(d, l, 'FAIL') for d, l in mu['bad']]
    all_mu.sort(key=lambda x: x[0])
    
    for date_str, label, entry_type in all_mu:
        bias = get_bias_at(bias_series, date_str)
        
        dt = pd.Timestamp(date_str)
        idx = daily.index.get_indexer([dt], method='pad')[0]
        d_hh = int(daily.iloc[idx].get('consec_hh_hl', 0))
        
        w_idx = mapped.index.get_indexer([dt], method='pad')[0]
        w_hh = int(mapped.iloc[w_idx]['weekly_hh_hl']) if w_idx >= 0 else 0
        
        if bias == 'bull':
            gate = 'Daily ≥ 2'
            passes = d_hh >= 2
        else:
            gate = 'Daily ≥ 2 + Weekly ≥ 2'
            passes = d_hh >= 2 and w_hh >= 2
        
        correct = (passes and entry_type == 'GOOD') or (not passes and entry_type == 'FAIL')
        icon = '✅' if correct else '❌'
        pass_str = 'PASS' if passes else 'BLOCK'
        
        if entry_type == 'GOOD':
            total_good_markup_total += 1
            if passes: total_good_markup_pass += 1
        else:
            total_bad_markup_total += 1
            if not passes: total_bad_markup_block += 1
        
        print(f"  {date_str:<12} {entry_type:<10} {bias:<6} {gate:<22} {d_hh:>5} {w_hh:>5} {pass_str:>6}  {icon} {label}")
    
    # ── MARKDOWN entries ──
    print(f"\n  ── MARKDOWN (SHORT) ENTRIES ──")
    print(f"  {'Date':<12} {'Type':<10} {'Bias':<6} {'Gate':<22} {'D_LL':>5} {'W_LL':>5} {'Pass?':>6}  Notes")
    print(f"  {'-'*12} {'-'*10} {'-'*6} {'-'*22} {'-'*5} {'-'*5} {'-'*6}  {'-'*35}")
    
    all_md = [(d, l, 'GOOD') for d, l in md['good']]
    all_md.sort(key=lambda x: x[0])
    
    for date_str, label, entry_type in all_md:
        bias = get_bias_at(bias_series, date_str)
        
        dt = pd.Timestamp(date_str)
        idx = daily.index.get_indexer([dt], method='pad')[0]
        d_ll = int(daily.iloc[idx].get('consec_lh_ll', 0))
        
        w_idx = mapped.index.get_indexer([dt], method='pad')[0]
        w_ll = int(mapped.iloc[w_idx]['weekly_lh_ll']) if w_idx >= 0 else 0
        
        if bias == 'bear':
            gate = 'Daily ≥ 2'
            passes = d_ll >= 2
        else:
            gate = 'Daily ≥ 2 + Weekly ≥ 2'
            passes = d_ll >= 2 and w_ll >= 2
        
        correct = passes and entry_type == 'GOOD'
        icon = '✅' if correct else '❌'
        pass_str = 'PASS' if passes else 'BLOCK'
        
        total_good_md_total += 1
        if passes: total_good_md_pass += 1
        
        print(f"  {date_str:<12} {entry_type:<10} {bias:<6} {gate:<22} {d_ll:>5} {w_ll:>5} {pass_str:>6}  {icon} {label}")
    
    # ── Corrections ──
    if corr:
        print(f"\n  ── CORRECTIONS (should NOT trigger markdown) ──")
        print(f"  {'Date':<12} {'Bias':<6} {'Gate':<22} {'D_LL':>5} {'W_LL':>5} {'Pass?':>6}  Notes")
        print(f"  {'-'*12} {'-'*6} {'-'*22} {'-'*5} {'-'*5} {'-'*6}  {'-'*35}")
        
        for date_str, label in corr:
            bias = get_bias_at(bias_series, date_str)
            
            dt = pd.Timestamp(date_str)
            idx = daily.index.get_indexer([dt], method='pad')[0]
            d_ll = int(daily.iloc[idx].get('consec_lh_ll', 0))
            
            w_idx = mapped.index.get_indexer([dt], method='pad')[0]
            w_ll = int(mapped.iloc[w_idx]['weekly_lh_ll']) if w_idx >= 0 else 0
            
            if bias == 'bear':
                gate = 'Daily ≥ 2'
                passes = d_ll >= 2
            else:
                gate = 'Daily ≥ 2 + Weekly ≥ 2'
                passes = d_ll >= 2 and w_ll >= 2
            
            icon = '✅ BLOCKED' if not passes else '⚠️ FALSE ALARM'
            pass_str = 'PASS' if passes else 'BLOCK'
            
            total_corr_total += 1
            if not passes: total_corr_block += 1
            
            print(f"  {date_str:<12} {bias:<6} {gate:<22} {d_ll:>5} {w_ll:>5} {pass_str:>6}  {icon} {label}")

print(f"\n{'═' * 110}")
print(f"  SCORECARD")
print(f"{'═' * 110}")
print(f"""
  Good MARKUP entries passed:    {total_good_markup_pass}/{total_good_markup_total} ({total_good_markup_pass/total_good_markup_total*100:.0f}%)
  Bad MARKUP entries blocked:    {total_bad_markup_block}/{total_bad_markup_total} ({total_bad_markup_block/total_bad_markup_total*100:.0f}%) 
  Good MARKDOWN entries passed:  {total_good_md_pass}/{total_good_md_total} ({total_good_md_pass/total_good_md_total*100:.0f}%)
  Corrections blocked:           {total_corr_block}/{total_corr_total} ({total_corr_block/total_corr_total*100:.0f}%)
""")

if total_good_markup_pass == total_good_markup_total and \
   total_bad_markup_block == total_bad_markup_total and \
   total_good_md_pass == total_good_md_total and \
   total_corr_block == total_corr_total:
    print("  🏆 PERFECT SCORE — All entries correct!")
else:
    fails = []
    if total_good_markup_pass < total_good_markup_total:
        fails.append(f"  ❌ {total_good_markup_total - total_good_markup_pass} good markup(s) blocked")
    if total_bad_markup_block < total_bad_markup_total:
        fails.append(f"  ❌ {total_bad_markup_total - total_bad_markup_block} bad markup(s) not blocked")
    if total_good_md_pass < total_good_md_total:
        fails.append(f"  ❌ {total_good_md_total - total_good_md_pass} good markdown(s) blocked")
    if total_corr_block < total_corr_total:
        fails.append(f"  ❌ {total_corr_total - total_corr_block} correction(s) not blocked")
    print('\n'.join(fails))
