"""Check why markdown entries aren't triggering."""
from v13_signals import V13SignalPack
import pandas as pd
import numpy as np

for coin in ['ETH', 'SOL', 'LINK', 'XRP']:
    pack = V13SignalPack(coin)
    ob_exits = pack.stoch_2w.ob_exits(threshold=95)
    ob_exits = ob_exits[ob_exits.index >= '2024-09-01']
    print(f'{coin}: 2W OB exits (>95): {len(ob_exits)}')
    for dt, row in ob_exits.iterrows():
        vs_sma50 = pack.structure.price_vs_sma50(dt)
        below_sma50 = vs_sma50 < 0 if not pd.isna(vs_sma50) else False
        bmsb_below = pack.bmsb.sustained_below(dt, weeks=2)
        k_val = row['K']
        print(f'  {dt.date()}: K={k_val:.0f}, below_SMA50={below_sma50} (vs={vs_sma50:.1f}%), BMSB_sustained={bmsb_below}')
        if below_sma50 and bmsb_below:
            print(f'    ** ALL CONDITIONS MET - SHOULD ENTER MARKDOWN **')
    print()
