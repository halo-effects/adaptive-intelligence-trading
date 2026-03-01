"""Quick comparison: V14 accumulate vs V13 baseline on same period."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from v13_phase_backtest_v8 import V13BacktestV8, V13Config as V8Config
from v13_signals import V13SignalPack

coins = ['ETH/USDC', 'SOL/USDC', 'LINK/USDC', 'XRP/USDC']
capital = 10000
per_coin = capital / len(coins)

print("V13 BASELINE (Oct 2024 start, $2,500/coin)")
print("=" * 60)
total = 0
for coin in coins:
    pack = V13SignalPack(coin)
    cfg = V8Config()
    cfg.CAPITAL = per_coin
    cfg.START_DATE = '2024-10-01'
    eng = V13BacktestV8(pack, cfg)
    r = eng.run()
    total += r['final_equity']
    print(f"  {coin:<12} ${r['final_equity']:>10,.2f} ({r['roi']:>+8.1f}%)")

print(f"  {'TOTAL':<12} ${total:>10,.2f} ({(total-capital)/capital*100:>+8.1f}%)")
