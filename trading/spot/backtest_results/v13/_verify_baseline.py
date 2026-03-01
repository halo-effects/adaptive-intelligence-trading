"""Verify: reproduce V13_baseline_long result from dca_phase_test.py using dca_long_sweep engine."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from dca_long_sweep import SweepParams, run_single, get_dca_windows
from datetime import datetime

COINS = ['ETH/USDC', 'BTC/USDC', 'SOL/USDC']

# Exact V13_baseline_long params from dca_phase_test.py
p = SweepParams(tp_pct=0.015, dev_pct=0.025, so_mult=2.0, max_layers=8,
                base_pct=0.05, adaptive=False)

print(f"Reproducing V13_baseline_long: TP=1.5%, DEV=2.5%, SO=2.0x, L=8, base=5%, FIXED")
print()

for coin in COINS:
    windows = get_dca_windows(coin, 'high')
    windows = [w for w in windows if w['end'] >= '2023-03-12']
    r = run_single(coin, p, windows, 2500, '15m')
    print(f"  {coin}: ROI={r['roi']:+.1f}%  PnL=${r['pnl']:+.1f}  Lots={r['lots']}  WR={r['wr']:.1f}%  DD={r['max_dd']:.1f}%")
