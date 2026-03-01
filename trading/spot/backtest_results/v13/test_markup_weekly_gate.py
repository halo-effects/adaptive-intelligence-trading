"""
V13 MARKUP Gate Test Matrix — Weekly HH_HL Evaluation
Tests 3 variants for markup entry confirmation:
  1. Daily HH_HL ≥ 2 only (current baseline)
  2. Weekly HH_HL ≥ 1 only
  3. Daily HH_HL ≥ 2 + Weekly HH_HL ≥ 1 (mirroring markdown approach)

For each variant, measures:
  - Recall: catches all real markup starts?
  - False alarm: fires on MARKUP_FAIL entries (bear bounces)?
  - Entry latency: how many days after the real start?
  - Entry price impact: % difference from ideal entry price
"""
import sys, os
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from v13_signals import V13SignalPack
from build_weekly_signals import build_weekly_candles, compute_weekly_structure, map_weekly_to_daily
from test_signal_candidates import GROUND_TRUTH, evaluate_signal, evaluate_correction_filter
import pandas as pd
import numpy as np
from datetime import timedelta

# ═══════════════════════════════════════════════════════════
# MARKUP_FAIL ground truth — bear bounces that looked like markup
# These are the entries we WANT to block
# ═══════════════════════════════════════════════════════════

MARKUP_FAILS = {
    'ETH': {
        'good_markups': [
            ('2020-10-05', 'DeFi summer recovery', None),
            ('2022-09-27', 'Bear market bottom attempt', None),
            ('2023-10-22', 'Recovery rally begins', None),
            ('2024-10-15', 'Q4 rally', None),
        ],
        'bad_markups': [
            # These had HH_HL ≥ 2 but were MARKUP_FAIL
            # From audit_all_markup_entries.py results
        ],
    },
    'SOL': {
        'good_markups': [
            ('2023-10-02', 'Big recovery $23→$100', None),
            ('2024-04-18', 'Spring rally', None),
            ('2025-08-05', 'Recovery', None),
        ],
        'bad_markups': [
            ('2022-03-28', 'Bear bounce, -25.4% ($106→$79)', -25.4),
            ('2022-07-29', 'Bear bounce, -25.5% ($42→$31)', -25.5),
            ('2022-11-05', 'FTX collapse, -55.4% ($37→$16)', -55.4),
        ],
    },
    'BTC': {
        'good_markups': [
            ('2020-10-01', 'Post-halving breakout', None),
            ('2023-01-09', 'Bear bottom recovery', None),
            ('2024-01-29', 'ETF approval rally', None),
            ('2024-06-04', 'Post-halving accumulation', None),
            ('2025-06-24', 'Recovery rally', None),
        ],
        'bad_markups': [
            # BTC had 2 MARKUP_FAIL from audit
            # Need to identify from backtest data
        ],
    },
}

COINS = ['ETH', 'BTC', 'SOL']

print("=" * 120)
print("  V13 MARKUP GATE TEST MATRIX — Weekly HH_HL Evaluation")
print("=" * 120)

for coin in COINS:
    pack = V13SignalPack(coin)
    daily = pack.daily
    
    # Build weekly
    weekly = build_weekly_candles(daily)
    weekly = compute_weekly_structure(weekly)
    
    # Map weekly to daily
    weekly_cols = ['weekly_hh_hl', 'weekly_lh_ll']
    mapped = map_weekly_to_daily(daily, weekly, weekly_cols)
    
    print(f"\n{'═' * 120}")
    print(f"  {coin} — MARKUP Gate Comparison")
    print(f"{'═' * 120}")
    
    # Build signal variants
    signals = pd.DataFrame(index=daily.index)
    signals['close'] = daily['close']
    
    # Variant 1: Daily only (current)
    signals['daily_only'] = daily.get('consec_hh_hl', pd.Series(0, index=daily.index)) >= 2
    
    # Variant 2: Weekly only
    signals['weekly_only'] = mapped['weekly_hh_hl'] >= 1
    
    # Variant 3: Daily + Weekly
    signals['daily_and_weekly'] = signals['daily_only'] & signals['weekly_only']
    
    # Also test Weekly ≥ 2
    signals['weekly_2_only'] = mapped['weekly_hh_hl'] >= 2
    signals['daily_and_weekly_2'] = signals['daily_only'] & (mapped['weekly_hh_hl'] >= 2)
    
    gt = GROUND_TRUTH[coin]
    mf = MARKUP_FAILS[coin]
    
    # ── Part 1: Recall on known good markup starts ──
    print(f"\n  ── PART 1: RECALL — Known good markup starts ({len(gt['markup_starts'])}) ──")
    variants = [
        ('daily_only', 'Daily HH_HL ≥ 2 (CURRENT)'),
        ('weekly_only', 'Weekly HH_HL ≥ 1 only'),
        ('weekly_2_only', 'Weekly HH_HL ≥ 2 only'),
        ('daily_and_weekly', 'Daily ≥ 2 + Weekly ≥ 1'),
        ('daily_and_weekly_2', 'Daily ≥ 2 + Weekly ≥ 2'),
    ]
    
    print(f"  {'Variant':<40} {'Recall':>7} {'Precision':>10} {'AvgLat':>8} {'Fires':>6}  Details")
    print(f"  {'-'*40} {'-'*7} {'-'*10} {'-'*8} {'-'*6}  {'-'*50}")
    
    for sig_name, sig_desc in variants:
        r = evaluate_signal(signals, gt['markup_starts'], sig_name)
        # Show per-event latency
        details = []
        for ev_date, ev_desc in gt['markup_starts']:
            ev_dt = pd.Timestamp(ev_date)
            window_start = ev_dt - timedelta(days=30)
            window_end = ev_dt + timedelta(days=30)
            mask = (signals.index >= window_start) & (signals.index <= window_end) & signals[sig_name]
            if mask.any():
                first_fire = signals.index[mask][0]
                lat = (first_fire - ev_dt).days
                price_at_fire = signals.loc[first_fire, 'close']
                price_at_event = daily.loc[daily.index[daily.index.searchsorted(ev_dt)], 'close'] if ev_dt in daily.index else daily.loc[daily.index[daily.index.get_indexer([ev_dt], method='nearest')[0]], 'close']
                pct_diff = (price_at_fire - price_at_event) / price_at_event * 100
                details.append(f"{ev_date[:7]}:{lat:+d}d({pct_diff:+.1f}%)")
            else:
                details.append(f"{ev_date[:7]}:MISS")
        
        print(f"  {sig_desc:<40} {r['recall']:>6.0f}% {r['precision']:>9.1f}% {r['avg_latency']:>+7.0f}d {r['total_fires']:>6}  {' '.join(details)}")
    
    # ── Part 2: False alarm on MARKUP_FAIL entries ──
    bad = mf['bad_markups']
    if bad:
        print(f"\n  ── PART 2: FALSE ALARM — MARKUP_FAIL bear bounces ({len(bad)}) ──")
        print(f"  (Lower is better — we want to BLOCK these entries)")
        print(f"  {'Variant':<40} {'FalseAlarm%':>11}  Alarms")
        print(f"  {'-'*40} {'-'*11}  {'-'*50}")
        
        for sig_name, sig_desc in variants:
            correction_tuples = [(d, desc) for d, desc, _ in bad]
            r = evaluate_correction_filter(signals, correction_tuples, sig_name)
            alarms = ', '.join([f[0] for f in r['false_alarms']]) if r['false_alarms'] else 'NONE ✅'
            print(f"  {sig_desc:<40} {r['false_alarm_rate']:>10.0f}%  {alarms}")
    else:
        print(f"\n  ── PART 2: No known MARKUP_FAIL entries for {coin} in ground truth ──")
    
    # ── Part 3: Entry price comparison on good markups ──
    print(f"\n  ── PART 3: ENTRY PRICE IMPACT on good markups ──")
    print(f"  (Positive = entered HIGHER than ideal = worse entry for longs)")
    print(f"  {'Event':<25} {'Daily':>12} {'Weekly≥1':>12} {'Daily+W≥1':>12} {'Daily+W≥2':>12}")
    print(f"  {'-'*25} {'-'*12} {'-'*12} {'-'*12} {'-'*12}")
    
    for ev_date, ev_desc in gt['markup_starts']:
        ev_dt = pd.Timestamp(ev_date)
        # Get ideal entry price (at event date)
        nearest_idx = daily.index.get_indexer([ev_dt], method='nearest')[0]
        ideal_price = daily.iloc[nearest_idx]['close']
        
        row = f"  {ev_date} {ev_desc[:14]:<14}"
        for sig_name in ['daily_only', 'weekly_only', 'daily_and_weekly', 'daily_and_weekly_2']:
            window_start = ev_dt - timedelta(days=30)
            window_end = ev_dt + timedelta(days=60)  # allow up to 60d late for weekly
            mask = (signals.index >= window_start) & (signals.index <= window_end) & signals[sig_name]
            if mask.any():
                first_fire = signals.index[mask][0]
                entry_price = signals.loc[first_fire, 'close']
                pct = (entry_price - ideal_price) / ideal_price * 100
                lat = (first_fire - ev_dt).days
                row += f"  {pct:>+5.1f}%/{lat:>+3d}d"
            else:
                row += f"       MISS"
        print(row)

# ═══════════════════════════════════════════════════════════
# CROSS-COIN SUMMARY
# ═══════════════════════════════════════════════════════════
print(f"\n{'═' * 120}")
print(f"  CROSS-COIN SUMMARY")
print(f"{'═' * 120}")
print(f"""
  Question: Which variant should we use for MARKUP entry?
  
  Criteria:
  1. 100% recall on good markups (non-negotiable)
  2. Blocks MARKUP_FAIL bear bounces (especially SOL 2022)
  3. Minimal entry price penalty on good entries
  4. Mirrors MARKDOWN gate symmetry (Daily + Weekly structure)
""")
