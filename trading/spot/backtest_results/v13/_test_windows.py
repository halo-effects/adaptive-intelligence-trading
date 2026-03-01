import sys; sys.path.insert(0, '.')
from dca_long_sweep import get_dca_windows
for coin in ['LINK/USDC', 'XRP/USDC', 'ETH/USDC', 'SOL/USDC']:
    windows = get_dca_windows(coin, 'high')
    w2024 = [w for w in windows if w['end'] >= '2024-09-01']
    print(f'{coin}: {len(windows)} total, {len(w2024)} from Sep 2024+')
    for w in w2024:
        print(f"  {w['start']} -> {w['end']} exit={w['exit_to']}")
