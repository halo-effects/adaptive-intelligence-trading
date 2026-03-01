"""Debug: check what conviction signals look like at known bottoms."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pandas as pd
from _conviction_weighted_test import BottomStackDetector

# Known ETF-era bottoms (from _bottom_signals.py analysis)
BOTTOMS = {
    'ETH': ['2023-01-01', '2023-06-15', '2023-09-11', '2023-10-19', '2024-08-05', '2024-09-06', '2024-11-04', '2025-04-07', '2026-02-03'],
    'BTC': ['2023-01-01', '2023-06-15', '2023-09-11', '2024-08-05', '2024-09-06', '2024-11-04', '2025-04-07', '2026-02-03'],
    'SOL': ['2023-01-01', '2024-08-05', '2024-09-06', '2025-04-07', '2026-02-03'],
    'LINK': ['2023-01-01', '2023-06-15', '2023-10-19', '2024-08-05', '2025-04-07', '2026-02-03'],
    'XRP': ['2023-01-01', '2023-06-15', '2024-08-05', '2025-04-07', '2026-02-03'],
}

for coin_base in ['ETH', 'BTC', 'SOL', 'LINK', 'XRP']:
    print(f"\n{'='*60}")
    print(f"  {coin_base} - Signal Stack at Known Bottoms")
    print(f"{'='*60}")
    
    det = BottomStackDetector(coin_base)
    if det.daily is None:
        print("  No data")
        continue
    
    for date_str in BOTTOMS.get(coin_base, []):
        date = pd.Timestamp(date_str)
        # Find closest available date
        if date not in det.daily.index:
            mask = det.daily.index >= date
            if mask.any():
                date = det.daily.index[mask][0]
            else:
                continue
        
        score, signals = det.get_conviction_score(date)
        dc = signals.get('death_cross_2d', False)
        sma = signals.get('below_sma200', False)
        cfgi = signals.get('cfgi_fear', False)
        rsi = signals.get('weekly_rsi_os', False)
        spring = signals.get('spring', False)
        cfgi_val = signals.get('cfgi', float('nan'))
        rsi_val = signals.get('weekly_rsi', float('nan'))
        
        flags = []
        if dc: flags.append('DC')
        if sma: flags.append('SMA')
        if cfgi: flags.append('CFGI')
        if rsi: flags.append('RSI')
        if spring: flags.append('SPRING')
        
        print(f"  {date_str:12s} | score={score}/5 | {'+'.join(flags) if flags else 'NONE':20s} | cfgi={cfgi_val:.0f} rsi={rsi_val:.1f} spring={spring}")
