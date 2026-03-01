"""Debug: Why didn't failsafe fire for ETH after Dec 2024 early warning?"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from v13_signals import V13SignalPack
import pandas as pd

for coin in ['BTC', 'ETH', 'SOL']:
    pack = V13SignalPack(coin)
    stoch_1w = pack.stoch_1w
    stoch_2w = pack.stoch_2w
    df_1w = stoch_1w.df

    print(f"\n{'='*60}")
    print(f"  {coin} — 1W StochRSI K timeline (Oct 2024 → Mar 2025)")
    print(f"{'='*60}")
    
    window = df_1w[(df_1w.index >= '2024-10-01') & (df_1w.index <= '2025-06-01')]
    for dt, row in window.iterrows():
        k = row['K']
        markers = []
        if k > 97: markers.append('OB>97')
        if k > 80: markers.append('OB>80')
        if k < 50: markers.append('K<50 FAILSAFE')
        if k < 20: markers.append('OS<20')
        m = ' | '.join(markers) if markers else ''
        print(f"  {dt.date()}: K={k:6.1f} {m}")

    # 2W timeline
    df_2w = stoch_2w.df
    print(f"\n  {coin} — 2W StochRSI K timeline")
    window2 = df_2w[(df_2w.index >= '2024-10-01') & (df_2w.index <= '2025-06-01')]
    for dt, row in window2.iterrows():
        k = row['K']
        markers = []
        if k > 93: markers.append('OB>93')
        if k > 80: markers.append('OB>80')
        if k < 20: markers.append('OS<20')
        m = ' | '.join(markers) if markers else ''
        print(f"  {dt.date()}: K={k:6.1f} {m}")
