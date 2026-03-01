"""Debug the three issues Brett raised:
1. BTC/ETH: 42-day wait before markdown from post-top FLAT
2. XRP: How did shorts lose money?
3. BNB: Why did it start in markdown?
"""
import sys, os, importlib.util
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))

spec = importlib.util.spec_from_file_location('v8', os.path.join(os.path.dirname(__file__), 'v13_phase_backtest_v8.py'))
v8 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(v8)

import pandas as pd, numpy as np
from v13_signals import V13SignalPack

# Issue 1: BTC post-top FLAT — why 42 days before markdown?
print("=" * 80)
print("ISSUE 1: BTC post-top FLAT (Jan 1 - Feb 12, 42d) — why no markdown signal?")
print("=" * 80)
pack = V13SignalPack('BTC')
daily = pack.daily
start = pd.Timestamp('2025-01-01')
end = pd.Timestamp('2025-02-24')
mask = (daily.index >= start) & (daily.index <= end)
data = daily[mask]

print("Checking ADX + Fib_break conditions during post-top FLAT:")
for date, row in data.iterrows():
    if date.weekday() != 0 and date != start:
        continue
    adx = pack.structure.adx_at(date)
    price = row['close']
    # Check what Fib levels look like
    print(f"  {date.strftime('%Y-%m-%d')}: ${price:>10,.0f}  ADX={adx:>5.1f}  {'ADX>20' if adx > 20 else 'ranging'}")

print("\nThe FLAT->MARKDOWN check requires ADX>20 + Fib_break.")
print("If ADX stayed below 20 during this period, markdown can't trigger.")
print("FLAT_MAX_EVAL_DAYS=42 is the fallback that pushes to DCA.\n")

# Issue 1b: ETH same pattern
print("=" * 80)
print("ISSUE 1b: ETH post-top FLAT (Dec 22 2024 - Feb 2 2025, 42d)")
print("=" * 80)
pack_eth = V13SignalPack('ETH')
daily_eth = pack_eth.daily
start_eth = pd.Timestamp('2024-12-22')
end_eth = pd.Timestamp('2025-02-10')
mask_eth = (daily_eth.index >= start_eth) & (daily_eth.index <= end_eth)
data_eth = daily_eth[mask_eth]

for date, row in data_eth.iterrows():
    if date.weekday() != 0 and date != start_eth:
        continue
    adx = pack_eth.structure.adx_at(date)
    price = row['close']
    print(f"  {date.strftime('%Y-%m-%d')}: ${price:>10,.0f}  ADX={adx:>5.1f}  {'ADX>20' if adx > 20 else 'ranging'}")

# Issue 2: XRP shorts losing money
print("\n" + "=" * 80)
print("ISSUE 2: XRP — How did shorts lose money?")
print("=" * 80)
cfg = v8.V13Config()
pack_xrp = v8.V13SignalPack('XRP')
engine_xrp = v8.V13BacktestV8(pack_xrp, cfg)
result_xrp = engine_xrp.run()

short_trades = [t for t in engine_xrp.trades if 'SHORT' in t['action'] or 'short' in t['action'].lower()]
for t in short_trades:
    extra = f" pnl={t['pnl_pct']:+.1f}%" if 'pnl_pct' in t else ""
    print(f"  {t['date'].strftime('%Y-%m-%d')}: {t['action']:<45} @ ${t['price']:>6.2f}  amt=${t['amount']:>10,.0f}{extra}")

# Show markdown phases for XRP
print("\n  XRP Markdown phases:")
for i, p in enumerate(engine_xrp.phase_log):
    if p['to'] == 'MARKDOWN':
        end_p = engine_xrp.phase_log[i+1] if i+1 < len(engine_xrp.phase_log) else None
        end_date = end_p['date'] if end_p else pd.Timestamp(cfg.END_DATE)
        days = (end_date - p['date']).days
        print(f"  {p['date'].strftime('%Y-%m-%d')} - {end_date.strftime('%Y-%m-%d')} ({days}d)")
        print(f"    Entry: ${p['price']:.2f}, Exit: ${end_p['price']:.2f if end_p else 0:.2f}")
        print(f"    Reason in: {p['reason']}")
        if end_p:
            print(f"    Reason out: {end_p['reason']}")
            pnl = (end_p['equity'] / p['equity'] - 1) * 100
            print(f"    Equity: ${p['equity']:,.0f} -> ${end_p['equity']:,.0f} ({pnl:+.1f}%)")

# Issue 3: BNB — why markdown so early?
print("\n" + "=" * 80)
print("ISSUE 3: BNB — Why markup ranging exit at Nov 8 after only 34 days?")
print("=" * 80)
pack_bnb = V13SignalPack('BNB')
daily_bnb = pack_bnb.daily
start_bnb = pd.Timestamp('2024-10-05')
end_bnb = pd.Timestamp('2024-11-15')
mask_bnb = (daily_bnb.index >= start_bnb) & (daily_bnb.index <= end_bnb)
data_bnb = daily_bnb[mask_bnb]

print("BNB ADX during first markup (Oct 5 - Nov 8):")
streak = 0
for date, row in data_bnb.iterrows():
    adx = pack_bnb.structure.adx_at(date)
    price = row['close']
    if adx < 20:
        streak += 1
    else:
        streak = 0
    if date.weekday() == 0 or streak == 21 or date == pd.Timestamp('2024-10-05') or date == pd.Timestamp('2024-11-08'):
        print(f"  {date.strftime('%Y-%m-%d')}: ${price:>7,.0f}  ADX={adx:>5.1f}  streak_below_20={streak}d")

print("\nBNB then goes: FLAT -> DCA -> MARKDOWN at Feb 2")
print("BNB ADX around Feb 2 2025:")
start_bnb2 = pd.Timestamp('2025-01-20')
end_bnb2 = pd.Timestamp('2025-02-10')
mask_bnb2 = (daily_bnb.index >= start_bnb2) & (daily_bnb.index <= end_bnb2)
data_bnb2 = daily_bnb[mask_bnb2]
for date, row in data_bnb2.iterrows():
    adx = pack_bnb.structure.adx_at(date)
    price = row['close']
    print(f"  {date.strftime('%Y-%m-%d')}: ${price:>7,.0f}  ADX={adx:>5.1f}")
