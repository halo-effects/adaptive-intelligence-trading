"""Audit MARKDOWN entries against the FULL gate spec from the test plan."""
import sys, os
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from v13_signals import V13SignalPack
from v13_phase_backtest_v8 import compute_fib_levels, price_broke_fib_support
import pandas as pd
import numpy as np

# All MARKDOWN entries from the backtest (ETH, BTC, SOL)
MARKDOWN_ENTRIES = [
    # (coin, date, source_phase, outcome: profit/loss on the short)
    ('ETH', '2021-05-22', 'DCA', 'LOSS -25.7% in 4d'),
    ('ETH', '2022-03-04', 'DCA', 'LOSS -25.1% in 27d'),
    ('ETH', '2022-09-21', 'DCA', 'LOSS -25.7% in 35d'),
    ('ETH', '2022-12-26', 'DCA', 'LOSS -26.2% in 19d'),
    ('ETH', '2024-05-13', 'FLAT', 'LOSS -27.1% in 12d'),
    ('ETH', '2025-02-02', 'FLAT', 'WIN +10.4% in 150d'),
    ('ETH', '2025-11-05', 'FLAT', 'WIN +41.8% in 104d (open)'),
    ('BTC', '2022-08-19', 'DCA', 'WIN +3.6% in 67d'),
    ('BTC', '2023-08-19', 'DCA', 'LOSS -3.3% in 42d'),
    ('BTC', '2025-02-26', 'DCA', 'LOSS -0.8% in 50d'),
    ('SOL', '2021-07-20', 'DCA', 'N/A (no shorts yet)'),
    ('SOL', '2022-10-22', 'DCA', 'WIN +25.1% in 133d'),
    ('SOL', '2024-08-04', 'DCA', 'LOSS -5.2% in 68d'),
    ('SOL', '2025-10-17', 'FLAT', 'WIN +53.3% in 123d (open)'),
]

packs = {}
for coin in ['ETH', 'BTC', 'SOL']:
    packs[coin] = V13SignalPack(coin)

print(f"{'='*90}")
print(f"  MARKDOWN Entry Gate Audit — Test Plan vs Engine")
print(f"{'='*90}")
print(f"\n  Test Plan (Test 5) requires for MARKDOWN confirmation:")
print(f"    1. ADX > 20 (trending)")
print(f"    2. Fib break (price below 0.618)")  
print(f"    3. CFGI < 30 (deep fear)          <-- NOT IN ENGINE")
print(f"    4. Price < SMA200                  <-- NOT IN ENGINE")
print(f"    5. SMA50 slope negative 5+ days    <-- NOT IN ENGINE")
print(f"    6. LH/LL structure                 <-- NOT IN ENGINE")
print(f"\n  Test Plan (Test 6) correction filter:")
print(f"    - CFGI > 40 = correction, not distribution")
print(f"    - Price > SMA200 = correction, not distribution")

print(f"\n{'Date':<12} {'Coin':<5} {'Src':<5} {'ADX':>5} {'CFGI':>5} {'vsSMA200':>9} {'SMA50slp':>9} {'LH/LL':>6} {'FibBrk':>7} {'Outcome':<30} {'Would Test Plan Block?'}")
print(f"{'-'*12} {'-'*5} {'-'*5} {'-'*5} {'-'*5} {'-'*9} {'-'*9} {'-'*6} {'-'*7} {'-'*30} {'-'*22}")

for coin, date_str, src, outcome in MARKDOWN_ENTRIES:
    pack = packs[coin]
    date = pd.Timestamp(date_str)
    
    adx = pack.structure.adx_at(date)
    cfgi = pack.cfgi.value_at(date)
    
    daily = pack.daily
    row = daily[daily.index <= date].iloc[-1]
    sma200_pct = row.get('price_vs_sma200', np.nan)
    sma50_slope = row.get('sma50_slope', np.nan)
    lh_ll = row.get('consec_lh_ll', 0)
    
    fib = compute_fib_levels(daily, date)
    price = row['close']
    fib_broke = price_broke_fib_support(price, fib)
    
    # Would the test plan gates block this?
    blocks = []
    if not np.isnan(cfgi) and cfgi >= 30:
        blocks.append(f"CFGI={cfgi:.0f}>=30")
    if not np.isnan(sma200_pct) and sma200_pct > 0:
        blocks.append(f"above SMA200")
    if not np.isnan(sma50_slope) and sma50_slope >= 0:
        blocks.append(f"SMA50 rising")
    if lh_ll < 2:
        blocks.append(f"no LH/LL")
    
    blocked = "YES: " + ", ".join(blocks) if blocks else "NO (all gates pass)"
    is_loss = "LOSS" in outcome
    
    marker = " <-- SAVED" if (blocks and is_loss) else (" <-- FALSE BLOCK" if (blocks and not is_loss) else "")
    
    print(f"{date_str:<12} {coin:<5} {src:<5} {adx:>5.1f} {cfgi:>5.0f} {sma200_pct:>+8.1f}% {sma50_slope:>+8.2f}% {lh_ll:>6} {str(fib_broke):>7} {outcome:<30} {blocked}{marker}")

# Summary
print(f"\n{'='*90}")
print(f"  SUMMARY")
print(f"{'='*90}")
