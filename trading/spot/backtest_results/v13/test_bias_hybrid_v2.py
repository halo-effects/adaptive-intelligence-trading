"""
V13 Hybrid Bias System V2 — Fixed cross detection

Bear triggers (need NEW event, not persistent state):
  - Engine top signal fires
  - NEW Death Cross: SMA50 crosses below SMA200 (was above yesterday, below today)

Bull trigger:
  - Price reclaims SMA200 (closes above after being below)

Once bull is set, death cross state alone doesn't flip it — needs a NEW crossing.
"""
import sys, os
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from v13_signals import V13SignalPack
from build_weekly_signals import build_weekly_candles, compute_weekly_structure, map_weekly_to_daily
import pandas as pd
import numpy as np

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
    'SOL': {
        'good': [('2023-10-02', 'Big recovery'), ('2024-04-18', 'Spring rally'), ('2025-08-05', 'Recovery')],
        'bad': [('2022-03-28', 'Bear bounce -25%'), ('2022-07-29', 'Bear bounce -26%'), ('2022-11-05', 'FTX -55%')],
    },
    'ETH': {
        'good': [('2020-10-05', 'DeFi summer'), ('2022-09-27', 'Bear bottom'), ('2023-10-22', 'Recovery'), ('2024-10-15', 'Q4 rally')],
        'bad': [],
    },
    'BTC': {
        'good': [('2020-10-01', 'Post-halving'), ('2023-01-09', 'Bear recovery'), ('2024-01-29', 'ETF rally'), ('2024-06-04', 'Post-halving'), ('2025-06-24', 'Recovery')],
        'bad': [],
    },
}

MARKDOWN_ENTRIES = {
    'ETH': {'good': [('2022-03-04', 'Bear cont.'), ('2025-02-02', 'Post-top'), ('2025-11-12', 'Year-end')]},
    'BTC': {'good': [('2022-05-09', 'Luna'), ('2022-08-19', 'Bear cont.'), ('2023-08-22', 'Summer'), ('2025-02-26', 'Post-ATH')]},
    'SOL': {'good': [('2021-07-20', 'Early bear'), ('2024-08-04', 'Summer'), ('2025-10-17', 'Year-end')]},
}

CORRECTIONS = {
    'ETH': [('2021-05-26', 'China ban dip'), ('2024-06-16', 'Summer range')],
    'BTC': [('2021-09-07', 'El Salvador dip'), ('2024-08-05', 'Yen carry')],
    'SOL': [('2022-03-28', 'Bear bounce'), ('2022-07-29', 'Bear bounce'), ('2022-11-05', 'FTX')],
}


def compute_bias_v2(daily, tops):
    """
    Compute bias with proper cross detection:
    - NEW death cross (SMA50 was >= SMA200 yesterday, < today) → bear
    - Engine top signal → bear
    - Price closes above SMA200 after being below → bull
    """
    bias = pd.Series('bull', index=daily.index)
    current = 'bull'
    top_dates = set(pd.Timestamp(d) for d, _ in tops)
    transitions = []
    
    prev_sma50 = np.nan
    prev_sma200 = np.nan
    prev_close = np.nan
    
    for i, date in enumerate(daily.index):
        close = daily.iloc[i]['close']
        sma50 = daily.iloc[i].get('sma50', np.nan)
        sma200 = daily.iloc[i].get('sma200', np.nan)
        
        if current == 'bull':
            # Check for bear triggers
            if date in top_dates:
                current = 'bear'
                transitions.append((date, 'TOP SIGNAL', close, sma200))
            elif (not np.isnan(sma50) and not np.isnan(sma200) and 
                  not np.isnan(prev_sma50) and not np.isnan(prev_sma200)):
                # NEW death cross: was above or equal yesterday, below today
                if prev_sma50 >= prev_sma200 and sma50 < sma200:
                    current = 'bear'
                    transitions.append((date, 'NEW DEATH CROSS', close, sma200))
        
        elif current == 'bear':
            # Bull trigger: price reclaims SMA200
            if not np.isnan(sma200) and not np.isnan(prev_close):
                if prev_close <= sma200 and close > sma200:
                    current = 'bull'
                    transitions.append((date, 'PRICE > SMA200', close, sma200))
        
        bias.iloc[i] = current
        prev_sma50 = sma50
        prev_sma200 = sma200
        prev_close = close
    
    return bias, transitions


print("=" * 110)
print("  V13 HYBRID BIAS SYSTEM V3 — Weekly ≥ 1 Against-Trend Gate")
print("  Bear: Engine top OR NEW Death Cross | Bull: Price reclaims SMA200")
print("  Against-trend gate: Weekly ≥ 1 (relaxed from ≥ 2)")
print("=" * 110)

total = {'mu_pass': 0, 'mu_total': 0, 'mu_block_bad': 0, 'mu_bad_total': 0,
         'md_pass': 0, 'md_total': 0, 'corr_block': 0, 'corr_total': 0}

for coin in ['SOL', 'ETH', 'BTC']:
    pack = V13SignalPack(coin)
    daily = pack.daily
    
    weekly = build_weekly_candles(daily)
    weekly = compute_weekly_structure(weekly)
    mapped = map_weekly_to_daily(daily, weekly, ['weekly_hh_hl', 'weekly_lh_ll'])
    
    bias_series, transitions = compute_bias_v2(daily, TOPS.get(coin, []))
    
    print(f"\n{'═' * 110}")
    print(f"  {coin}")
    print(f"{'═' * 110}")
    
    # Show transitions (filtered to meaningful ones)
    print(f"\n  ── BIAS TRANSITIONS ({len(transitions)} total) ──")
    for date, trigger, close, sma200 in transitions:
        new_bias = 'BEAR' if 'DEATH' in trigger or 'TOP' in trigger else 'BULL'
        print(f"  {date.strftime('%Y-%m-%d')}  → {new_bias}  via {trigger:<18}  (${close:.0f}, SMA200=${sma200:.0f})")
    
    bull_days = (bias_series == 'bull').sum()
    bear_days = (bias_series == 'bear').sum()
    print(f"  Days: {bull_days} bull, {bear_days} bear ({bear_days/(bull_days+bear_days)*100:.0f}% bear)")
    
    def get_bias(date_str):
        dt = pd.Timestamp(date_str)
        idx = bias_series.index.get_indexer([dt], method='pad')[0]
        return bias_series.iloc[idx] if idx >= 0 else 'bull'
    
    def get_signals(date_str):
        dt = pd.Timestamp(date_str)
        idx = daily.index.get_indexer([dt], method='pad')[0]
        d_hh = int(daily.iloc[idx].get('consec_hh_hl', 0))
        d_ll = int(daily.iloc[idx].get('consec_lh_ll', 0))
        w_idx = mapped.index.get_indexer([dt], method='pad')[0]
        w_hh = int(mapped.iloc[w_idx]['weekly_hh_hl']) if w_idx >= 0 else 0
        w_ll = int(mapped.iloc[w_idx]['weekly_lh_ll']) if w_idx >= 0 else 0
        return d_hh, d_ll, w_hh, w_ll
    
    mu = MARKUP_ENTRIES[coin]
    md = MARKDOWN_ENTRIES[coin]
    corr = CORRECTIONS.get(coin, [])
    
    # ── MARKUP ──
    print(f"\n  ── MARKUP (LONG) ──")
    print(f"  {'Date':<12} {'Type':<8} {'Bias':<6} {'Gate':<22} {'D_HH':>5} {'W_HH':>5} {'Result':>6}  Notes")
    print(f"  {'-'*12} {'-'*8} {'-'*6} {'-'*22} {'-'*5} {'-'*5} {'-'*6}  {'-'*25}")
    
    all_mu = [(d, l, 'GOOD') for d, l in mu['good']] + [(d, l, 'FAIL') for d, l in mu['bad']]
    all_mu.sort()
    
    for ds, label, typ in all_mu:
        bias = get_bias(ds)
        d_hh, _, w_hh, _ = get_signals(ds)
        if bias == 'bull':
            gate, passes = 'Daily ≥ 2', d_hh >= 2
        else:
            gate, passes = 'Daily ≥ 2 + Weekly ≥ 1', d_hh >= 2 and w_hh >= 1
        
        ok = (passes and typ == 'GOOD') or (not passes and typ == 'FAIL')
        icon = '✅' if ok else '❌'
        ps = 'PASS' if passes else 'BLOCK'
        
        if typ == 'GOOD':
            total['mu_total'] += 1
            if passes: total['mu_pass'] += 1
        else:
            total['mu_bad_total'] += 1
            if not passes: total['mu_block_bad'] += 1
        
        print(f"  {ds:<12} {typ:<8} {bias:<6} {gate:<22} {d_hh:>5} {w_hh:>5} {ps:>6}  {icon} {label}")
    
    # ── MARKDOWN ──
    print(f"\n  ── MARKDOWN (SHORT) ──")
    print(f"  {'Date':<12} {'Type':<8} {'Bias':<6} {'Gate':<22} {'D_LL':>5} {'W_LL':>5} {'Result':>6}  Notes")
    print(f"  {'-'*12} {'-'*8} {'-'*6} {'-'*22} {'-'*5} {'-'*5} {'-'*6}  {'-'*25}")
    
    for ds, label in md['good']:
        bias = get_bias(ds)
        _, d_ll, _, w_ll = get_signals(ds)
        if bias == 'bear':
            gate, passes = 'Daily ≥ 2', d_ll >= 2
        else:
            gate, passes = 'Daily ≥ 2 + Weekly ≥ 1', d_ll >= 2 and w_ll >= 1
        
        ok = passes
        icon = '✅' if ok else '❌'
        ps = 'PASS' if passes else 'BLOCK'
        total['md_total'] += 1
        if passes: total['md_pass'] += 1
        
        print(f"  {ds:<12} {'GOOD':<8} {bias:<6} {gate:<22} {d_ll:>5} {w_ll:>5} {ps:>6}  {icon} {label}")
    
    # ── CORRECTIONS ──
    if corr:
        print(f"\n  ── CORRECTIONS (should NOT fire) ──")
        for ds, label in corr:
            bias = get_bias(ds)
            _, d_ll, _, w_ll = get_signals(ds)
            if bias == 'bear':
                gate, passes = 'Daily ≥ 2', d_ll >= 2
            else:
                gate, passes = 'Daily ≥ 2 + Weekly ≥ 1', d_ll >= 2 and w_ll >= 1
            
            icon = '✅' if not passes else '⚠️'
            ps = 'PASS' if passes else 'BLOCK'
            total['corr_total'] += 1
            if not passes: total['corr_block'] += 1
            
            print(f"  {ds:<12} {bias:<6} {gate:<22} {d_ll:>5} {w_ll:>5} {ps:>6}  {icon} {label}")

print(f"\n{'═' * 110}")
print(f"  SCORECARD")
print(f"{'═' * 110}")
t = total
print(f"  Good MARKUP passed:    {t['mu_pass']}/{t['mu_total']} ({t['mu_pass']/t['mu_total']*100:.0f}%)")
print(f"  Bad MARKUP blocked:    {t['mu_block_bad']}/{t['mu_bad_total']} ({t['mu_block_bad']/t['mu_bad_total']*100:.0f}%)" if t['mu_bad_total'] else "  Bad MARKUP blocked:    N/A")
print(f"  Good MARKDOWN passed:  {t['md_pass']}/{t['md_total']} ({t['md_pass']/t['md_total']*100:.0f}%)")
print(f"  Corrections blocked:   {t['corr_block']}/{t['corr_total']} ({t['corr_block']/t['corr_total']*100:.0f}%)")

if (t['mu_pass'] == t['mu_total'] and t['mu_block_bad'] == t['mu_bad_total'] and 
    t['md_pass'] == t['md_total'] and t['corr_block'] == t['corr_total']):
    print("\n  🏆 PERFECT SCORE!")
else:
    print()
    if t['mu_pass'] < t['mu_total']: print(f"  ❌ {t['mu_total']-t['mu_pass']} good markup(s) blocked")
    if t['mu_block_bad'] < t['mu_bad_total']: print(f"  ❌ {t['mu_bad_total']-t['mu_block_bad']} bad markup(s) passed")
    if t['md_pass'] < t['md_total']: print(f"  ❌ {t['md_total']-t['md_pass']} good markdown(s) blocked")
    if t['corr_block'] < t['corr_total']: print(f"  ❌ {t['corr_total']-t['corr_block']} correction(s) passed")
