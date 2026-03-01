"""Debug: What signals are present when DCA is buying into the Nov 2025+ crash?"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from v13_signals import V13SignalPack
import pandas as pd
import numpy as np

for coin in ['BTC', 'ETH', 'SOL']:
    pack = V13SignalPack(coin)
    print(f"\n{'='*70}")
    print(f"  {coin} — Signal state during crash periods")
    print(f"{'='*70}")
    
    # Check Oct 2025 → Feb 2026 (the crash we're buying into)
    dates = pd.date_range('2025-10-01', '2026-02-17', freq='W')
    
    print(f"  {'Date':<12} {'Price':>10} {'1W_K':>6} {'2W_K':>6} {'BMSB':>8} {'SMA50slp':>9} {'CFGI':>6} {'ADX':>6}")
    print(f"  {'-'*65}")
    
    for d in dates:
        if d > pack.daily.index[-1]:
            break
        price = pack.daily.loc[pack.daily.index <= d, 'close'].iloc[-1]
        k_1w = pack.stoch_1w.get_k_at(d)
        k_2w = pack.stoch_2w.get_k_at(d)
        bmsb = pack.bmsb.status_at(d)
        slope = pack.structure.sma50_slope_at(d, 10)
        cfgi = pack.cfgi.value_at(d)
        adx = pack.structure.adx_at(d)
        
        # Flag potential markdown signals
        flags = []
        if bmsb == 'BELOW': flags.append('BELOW_BMSB')
        if not np.isnan(slope) and slope < -1: flags.append('SMA50_NEG')
        if not np.isnan(cfgi) and cfgi < 30: flags.append('FEAR')
        if not np.isnan(k_1w) and k_1w < 30: flags.append('1W_WEAK')
        if not np.isnan(k_2w) and k_2w < 30: flags.append('2W_WEAK')
        if not np.isnan(adx) and adx > 25: flags.append('TRENDING')
        
        flag_str = ' | '.join(flags) if flags else ''
        print(f"  {d.date()!s:<12} ${price:>9,.0f} {k_1w:>6.1f} {k_2w:>6.1f} {bmsb:>8} {slope:>8.1f}% {cfgi:>6.0f} {adx:>6.1f}  {flag_str}")
    
    # Also check the BTC May→Aug 2025 DCA period to see what signals say
    if coin == 'BTC':
        print(f"\n  BTC — Jan→Apr 2025 (DCA period, should detect markdown)")
        dates2 = pd.date_range('2025-01-01', '2025-05-01', freq='W')
        print(f"  {'Date':<12} {'Price':>10} {'1W_K':>6} {'2W_K':>6} {'BMSB':>8} {'SMA50slp':>9} {'CFGI':>6}")
        print(f"  {'-'*60}")
        for d in dates2:
            price = pack.daily.loc[pack.daily.index <= d, 'close'].iloc[-1]
            k_1w = pack.stoch_1w.get_k_at(d)
            k_2w = pack.stoch_2w.get_k_at(d)
            bmsb = pack.bmsb.status_at(d)
            slope = pack.structure.sma50_slope_at(d, 10)
            cfgi = pack.cfgi.value_at(d)
            
            flags = []
            if bmsb == 'BELOW': flags.append('BELOW_BMSB')
            if not np.isnan(slope) and slope < -1: flags.append('SMA50_NEG')
            if not np.isnan(cfgi) and cfgi < 30: flags.append('FEAR')
            if not np.isnan(k_1w) and k_1w < 30: flags.append('1W_WEAK')
            if not np.isnan(k_2w) and k_2w < 30: flags.append('2W_WEAK')
            
            flag_str = ' | '.join(flags) if flags else ''
            print(f"  {d.date()!s:<12} ${price:>9,.0f} {k_1w:>6.1f} {k_2w:>6.1f} {bmsb:>8} {slope:>8.1f}% {cfgi:>6.0f}  {flag_str}")
