"""Check XRP MARKDOWN_FAIL trade #34 — would new gates have prevented it?"""
import sys, os
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from v13_signals import V13SignalPack
from build_weekly_signals import build_weekly_candles, compute_weekly_structure, map_weekly_to_daily
import pandas as pd
import numpy as np

# XRP MARKDOWN_FAIL: entered short 2025-04-08, closed 2025-05-13, -34%
# Check what signals looked like at entry

pack = V13SignalPack('XRP')
daily = pack.daily

weekly = build_weekly_candles(daily)
weekly = compute_weekly_structure(weekly)
mapped = map_weekly_to_daily(daily, weekly, ['weekly_hh_hl', 'weekly_lh_ll'])

date = pd.Timestamp('2025-04-08')
idx = daily.index.get_indexer([date], method='pad')[0]
row = daily.iloc[idx]

w_idx = mapped.index.get_indexer([date], method='pad')[0]

print("=" * 80)
print("  XRP MARKDOWN_FAIL Analysis — Trade #34")
print("  Entry: 2025-04-08 | Exit: 2025-05-13 | P&L: -$1,675 (-34%)")
print("=" * 80)

print(f"\n  Date: {daily.index[idx].strftime('%Y-%m-%d')}")
print(f"  Close: ${row['close']:.4f}")
print(f"  SMA50: ${row.get('sma50', float('nan')):.4f}")
print(f"  SMA200: ${row.get('sma200', float('nan')):.4f}")
print(f"  ADX: {row.get('adx', float('nan')):.1f}")
print(f"  Daily LH_LL streak: {int(row.get('consec_lh_ll', 0))}")
print(f"  Daily HH_HL streak: {int(row.get('consec_hh_hl', 0))}")
print(f"  Weekly LH_LL: {int(mapped.iloc[w_idx]['weekly_lh_ll'])}")
print(f"  Weekly HH_HL: {int(mapped.iloc[w_idx]['weekly_hh_hl'])}")

sma50 = row.get('sma50', float('nan'))
sma200 = row.get('sma200', float('nan'))
close = row['close']

print(f"\n  ── BIAS DETERMINATION ──")
death_cross = sma50 < sma200 if not (np.isnan(sma50) or np.isnan(sma200)) else None
above_sma200 = close > sma200 if not np.isnan(sma200) else None
print(f"  Death Cross (SMA50 < SMA200): {death_cross}")
print(f"  Price > SMA200: {above_sma200}")
if death_cross:
    print(f"  → Bias would be: BEAR (death cross active)")
else:
    print(f"  → Bias would be: BULL")

d_ll = int(row.get('consec_lh_ll', 0))
w_ll = int(mapped.iloc[w_idx]['weekly_lh_ll'])

print(f"\n  ── GATE CHECK ──")
print(f"  Current engine (Daily LH_LL ≥ 2 + ADX > 20):")
print(f"    Daily LH_LL = {d_ll} {'≥ 2 ✅' if d_ll >= 2 else '< 2 🚫'}")
print(f"    ADX = {row.get('adx', float('nan')):.1f} {'> 20 ✅' if row.get('adx', 0) > 20 else '≤ 20 🚫'}")

print(f"\n  With bias system (bear bias → easy gate, bull bias → strict):")
if death_cross:
    print(f"    Bear bias → Daily LH_LL ≥ 2 only")
    print(f"    Daily LH_LL = {d_ll} → {'PASS (would enter short)' if d_ll >= 2 else 'BLOCK'}")
else:
    print(f"    Bull bias → Daily LH_LL ≥ 2 + Weekly LH_LL ≥ 1")
    print(f"    Daily LH_LL = {d_ll}, Weekly LH_LL = {w_ll}")
    passes = d_ll >= 2 and w_ll >= 1
    print(f"    → {'PASS (would enter short)' if passes else 'BLOCK ✅ (would prevent this bad trade!)'}")

# Also check nearby dates for context
print(f"\n  ── CONTEXT: 10 days around entry ──")
for offset in range(-5, 6):
    check_idx = idx + offset
    if check_idx < 0 or check_idx >= len(daily):
        continue
    r = daily.iloc[check_idx]
    d = daily.index[check_idx]
    wi = mapped.index.get_indexer([d], method='pad')[0]
    wll = int(mapped.iloc[wi]['weekly_lh_ll']) if wi >= 0 else 0
    whh = int(mapped.iloc[wi]['weekly_hh_hl']) if wi >= 0 else 0
    marker = ' ◄── ENTRY' if offset == 0 else ''
    print(f"  {d.strftime('%Y-%m-%d')}  ${r['close']:.4f}  D_LL={int(r.get('consec_lh_ll', 0))}  D_HH={int(r.get('consec_hh_hl', 0))}  W_LL={wll}  W_HH={whh}  ADX={r.get('adx', 0):.0f}{marker}")
