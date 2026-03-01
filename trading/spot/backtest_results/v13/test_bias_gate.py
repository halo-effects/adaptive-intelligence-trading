"""
Test bull/bear bias gates for MARKUP entry filtering.
Two candidates:
  1. Price > SMA200 (bull bias for longs)
  2. Golden Cross: SMA50 > SMA200 (bull bias for longs)

Test: would these block SOL MARKUP_FAIL bear bounces without blocking good entries?
"""
import sys, os
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from v13_signals import V13SignalPack
import pandas as pd
import numpy as np

COINS = {
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
    'ETH': {
        'good': [
            ('2020-10-05', 'DeFi summer recovery'),
            ('2022-09-27', 'Bear bottom attempt'),
            ('2023-10-22', 'Recovery rally'),
            ('2024-10-15', 'Q4 rally'),
        ],
        'bad': [],
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

# Also test for MARKDOWN (short) bias — would bear bias block bad shorts?
MARKDOWN_ENTRIES = {
    'ETH': {
        'good_shorts': [
            ('2022-03-04', 'Bear continuation'),
            ('2025-02-02', 'Post-top decline'),
            ('2025-11-12', 'Year-end decline'),
        ],
        'bad_shorts': [
            # The 5 shorts blocked by LH_LL gate (for reference)
        ],
    },
    'BTC': {
        'good_shorts': [
            ('2022-05-09', 'Luna crash'),
            ('2022-08-19', 'Bear continuation'),
            ('2023-08-22', 'Summer selloff'),
            ('2025-02-26', 'Post-ATH correction'),
        ],
        'bad_shorts': [],
    },
    'SOL': {
        'good_shorts': [
            ('2021-07-20', 'Early bear'),
            ('2024-08-04', 'Summer selloff'),
            ('2025-10-17', 'Year-end decline'),
        ],
        'bad_shorts': [],
    },
}

print("=" * 100)
print("  BULL/BEAR BIAS GATE TEST")
print("=" * 100)

for coin in ['SOL', 'ETH', 'BTC']:
    pack = V13SignalPack(coin)
    daily = pack.daily
    
    print(f"\n{'═' * 100}")
    print(f"  {coin} — Bias Gate Evaluation")
    print(f"{'═' * 100}")
    
    entries = COINS[coin]
    
    # ── MARKUP (long) bias ──
    print(f"\n  ── MARKUP (LONG) ENTRIES ──")
    print(f"  {'Date':<12} {'Type':<15} {'Price':>8} {'SMA200':>8} {'P/SMA%':>8} {'SMA50':>8} {'GC':>5}  Notes")
    print(f"  {'-'*12} {'-'*15} {'-'*8} {'-'*8} {'-'*8} {'-'*8} {'-'*5}  {'-'*30}")
    
    all_entries = [(d, l, 'GOOD') for d, l in entries['good']] + [(d, l, 'FAIL') for d, l in entries['bad']]
    all_entries.sort(key=lambda x: x[0])
    
    for date_str, label, entry_type in all_entries:
        date = pd.Timestamp(date_str)
        idx = daily.index.get_indexer([date], method='pad')[0]
        row = daily.iloc[idx]
        close = row['close']
        sma200 = row.get('sma200', np.nan)
        sma50 = row.get('sma50', np.nan)
        
        pct_vs_sma200 = ((close - sma200) / sma200 * 100) if not np.isnan(sma200) and sma200 > 0 else np.nan
        golden_cross = 'YES' if (not np.isnan(sma50) and not np.isnan(sma200) and sma50 > sma200) else 'NO'
        above_sma200 = close > sma200 if not np.isnan(sma200) else None
        
        marker = '✅' if entry_type == 'GOOD' else '❌'
        bias_p = '✅' if above_sma200 else '🚫'
        bias_gc = '✅' if golden_cross == 'YES' else '🚫'
        
        print(f"  {date_str:<12} {entry_type:<15} ${close:>7.0f} ${sma200:>7.0f} {pct_vs_sma200:>+7.1f}% ${sma50:>7.0f} {golden_cross:>5}  {marker} {label}")
        print(f"  {'':>12} {'':>15} Price>SMA200: {bias_p}  GoldenCross: {bias_gc}")
    
    # ── MARKDOWN (short) bias ──
    md = MARKDOWN_ENTRIES.get(coin, {})
    if md.get('good_shorts'):
        print(f"\n  ── MARKDOWN (SHORT) ENTRIES ──")
        print(f"  {'Date':<12} {'Type':<15} {'Price':>8} {'SMA200':>8} {'P/SMA%':>8} {'SMA50':>8} {'DC':>5}  Notes")
        print(f"  {'-'*12} {'-'*15} {'-'*8} {'-'*8} {'-'*8} {'-'*8} {'-'*5}  {'-'*30}")
        
        short_entries = [(d, l, 'GOOD') for d, l in md['good_shorts']] + [(d, l, 'FAIL') for d, l in md.get('bad_shorts', [])]
        short_entries.sort(key=lambda x: x[0])
        
        for date_str, label, entry_type in short_entries:
            date = pd.Timestamp(date_str)
            idx = daily.index.get_indexer([date], method='pad')[0]
            row = daily.iloc[idx]
            close = row['close']
            sma200 = row.get('sma200', np.nan)
            sma50 = row.get('sma50', np.nan)
            
            pct_vs_sma200 = ((close - sma200) / sma200 * 100) if not np.isnan(sma200) and sma200 > 0 else np.nan
            death_cross = 'YES' if (not np.isnan(sma50) and not np.isnan(sma200) and sma50 < sma200) else 'NO'
            below_sma200 = close < sma200 if not np.isnan(sma200) else None
            
            bias_p = '✅' if below_sma200 else '🚫'
            bias_dc = '✅' if death_cross == 'YES' else '🚫'
            
            print(f"  {date_str:<12} {entry_type:<15} ${close:>7.0f} ${sma200:>7.0f} {pct_vs_sma200:>+7.1f}% ${sma50:>7.0f} {death_cross:>5}  {label}")
            print(f"  {'':>12} {'':>15} Price<SMA200: {bias_p}  DeathCross: {bias_dc}")

print(f"\n{'═' * 100}")
print("  SUMMARY: Which bias gate is cleaner?")
print(f"{'═' * 100}")
print("""
  For LONGS (MARKUP), bull bias means: only enter long when bias is bullish
    - Price > SMA200: immediate, responsive, but can flip frequently
    - Golden Cross (SMA50 > SMA200): slower, more stable, but lags at transitions

  For SHORTS (MARKDOWN), bear bias means: only enter short when bias is bearish
    - Price < SMA200: immediate
    - Death Cross (SMA50 < SMA200): slower, more stable

  Key question: Does either gate block ALL bad entries while allowing ALL good entries?
""")
