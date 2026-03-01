"""Audit SOL MARKUP_FAIL events — what went wrong at each entry and exit."""
import sys, os
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from v13_signals import V13SignalPack
from v13_phase_backtest_v8 import V13BacktestV8, V13Config, compute_fib_levels
import pandas as pd
import numpy as np

pack = V13SignalPack('SOL')
daily = pack.daily

# SOL's 3 MARKUP_FAIL trades from the backtest
FAILS = [
    ('2022-03-28', '2022-05-07', -25.4, '$105.75', '$78.86', 'ADX=29'),
    ('2022-07-29', '2022-09-02', -25.5, '$41.91', '$31.23', 'ADX=33'),
    ('2022-11-05', '2022-11-11', -55.4, '$36.90', '$16.45', 'ADX=26'),
]

print(f"{'='*100}")
print(f"  SOL MARKUP_FAIL Audit — 3 Failed Long Entries")
print(f"{'='*100}")
print(f"\n  MARKUP_FAIL triggers when: DD > 25% below entry AND ADX > 25 (confirms downtrend)")
print(f"  MARKUP entry requires: HH_HL >= 2 + price near Fib support")

for entry_str, exit_str, pnl, entry_p, exit_p, fail_reason in FAILS:
    entry_date = pd.Timestamp(entry_str)
    exit_date = pd.Timestamp(exit_str)
    
    print(f"\n{'─'*100}")
    print(f"  FAIL #{FAILS.index((entry_str, exit_str, pnl, entry_p, exit_p, fail_reason))+1}: {entry_str} → {exit_str} ({(exit_date - entry_date).days}d) | {pnl:+.1f}% | {entry_p} → {exit_p}")
    print(f"  Exit reason: MARKUP_FAIL ({fail_reason})")
    print(f"{'─'*100}")
    
    # What was happening at entry?
    print(f"\n  === AT ENTRY ({entry_str}) ===")
    row = daily[daily.index <= entry_date].iloc[-1]
    
    hh_hl = pack.structure.hh_hl_streak(entry_date, 14)
    adx = pack.structure.adx_at(entry_date)
    cfgi = pack.cfgi.value_at(entry_date)
    sma200_pct = row.get('price_vs_sma200', np.nan)
    sma50_slope = row.get('sma50_slope', np.nan)
    close = row['close']
    sma50 = row.get('sma50', np.nan)
    sma200 = row.get('sma200', np.nan)
    
    fib = compute_fib_levels(daily, entry_date)
    
    print(f"  Price:        ${close:.2f}")
    print(f"  HH_HL:        {hh_hl} (≥2 required — {'PASS' if hh_hl >= 2 else 'FAIL'})")
    print(f"  ADX:          {adx:.1f}")
    print(f"  CFGI:         {cfgi:.0f}" if not np.isnan(cfgi) else f"  CFGI:         N/A")
    print(f"  vs SMA200:    {sma200_pct:+.1f}%" if not np.isnan(sma200_pct) else f"  vs SMA200:    N/A")
    print(f"  SMA50:        ${sma50:.2f}" if not np.isnan(sma50) else f"  SMA50:        N/A")
    print(f"  SMA200:       ${sma200:.2f}" if not np.isnan(sma200) else f"  SMA200:        N/A")
    print(f"  SMA50 slope:  {sma50_slope:+.2f}%" if not np.isnan(sma50_slope) else f"  SMA50 slope:  N/A")
    
    if fib:
        print(f"  Fib levels:   0.382=${fib.get('0.382',0):.2f}  0.5=${fib.get('0.5',0):.2f}  0.618=${fib.get('0.618',0):.2f}")
        print(f"  Fib high:     ${fib.get('high',0):.2f}  low: ${fib.get('low',0):.2f}")
    
    # What was the broader context? Look at price action 30 days before
    print(f"\n  === PRICE CONTEXT (30d before entry) ===")
    window_start = entry_date - pd.Timedelta(days=30)
    window = daily[(daily.index >= window_start) & (daily.index <= entry_date)]
    if len(window) > 0:
        high_30d = window['high'].max()
        low_30d = window['low'].min()
        print(f"  30d range:    ${low_30d:.2f} — ${high_30d:.2f} (spread: {(high_30d/low_30d - 1)*100:.1f}%)")
        print(f"  Entry vs 30d high: {(close/high_30d - 1)*100:+.1f}%")
    
    # What happened AFTER entry? Day-by-day drawdown
    print(f"\n  === DRAWDOWN TRAJECTORY (after entry) ===")
    post_entry = daily[(daily.index > entry_date) & (daily.index <= exit_date)]
    entry_price = close
    max_dd = 0
    for idx, prow in post_entry.iterrows():
        dd = (prow['low'] / entry_price - 1) * 100
        if dd < max_dd:
            max_dd = dd
        days_in = (idx - entry_date).days
        adx_now = pack.structure.adx_at(idx)
        if days_in <= 3 or dd < -15 or idx == post_entry.index[-1]:
            print(f"    Day {days_in:>3}: close=${prow['close']:.2f}  low=${prow['low']:.2f}  DD={dd:+.1f}%  ADX={adx_now:.1f}")
    
    # What was happening in the broader market?
    print(f"\n  === MARKET CONTEXT ===")
    # Check BTC and ETH on same date
    for other in ['BTC', 'ETH']:
        other_pack = V13SignalPack(other)
        other_daily = other_pack.daily
        other_row = other_daily[other_daily.index <= entry_date].iloc[-1]
        other_sma200 = other_row.get('price_vs_sma200', np.nan)
        other_adx = other_pack.structure.adx_at(entry_date)
        other_hh_hl = other_pack.structure.hh_hl_streak(entry_date, 14)
        other_lh_ll = other_pack.structure.lh_ll_streak(entry_date, 14)
        print(f"  {other}: vs_SMA200={other_sma200:+.1f}%, ADX={other_adx:.1f}, HH_HL={other_hh_hl}, LH_LL={other_lh_ll}")

print(f"\n{'='*100}")
print(f"  COMMON PATTERNS")
print(f"{'='*100}")
print(f"  All 3 failures occurred in 2022 bear market (Luna crash → FTX collapse)")
print(f"  Question: Should MARKUP entry be gated by broader market condition?")
print(f"  Question: Are HH_HL signals during bear market bounces false positives?")
