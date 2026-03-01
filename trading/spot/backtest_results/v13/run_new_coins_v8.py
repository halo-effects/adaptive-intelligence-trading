"""
Run V13 v8 backtest on PEPE, NEAR, LINK to evaluate for demo set inclusion.

Cold start phase: DCA for all three (all were ranging/accumulating in Oct 2024).
- PEPE: ~$0.000009, ranging after summer decline
- NEAR: ~$4.05, declining from $5.29  
- LINK: ~$11.41, flat/ranging

Same config as the main V13 v8 test: Oct 2024 -> Feb 2026.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from v13_phase_backtest_v8 import V13BacktestV8, V13Config, print_results
from v13_signals import V13SignalPack
import numpy as np

def main():
    print("=" * 80)
    print("  V13 v8 — NEW COIN EVALUATION (PEPE, NEAR, LINK)")
    print("  Cold start: DCA (all coins ranging in Oct 2024)")
    print("  Period: Oct 2024 -> Feb 2026")
    print("=" * 80)

    config = V13Config()
    
    coins = ['PEPE', 'NEAR', 'LINK']
    all_results = []

    for coin in coins:
        print(f"\n{'=' * 60}")
        print(f"  Loading {coin}...")
        try:
            pack = V13SignalPack(coin)
            print(f"  Data: {len(pack.daily)} daily candles, "
                  f"{pack.daily.index[0].date()} to {pack.daily.index[-1].date()}")
        except Exception as e:
            print(f"  SKIP: {e}")
            continue

        bt = V13BacktestV8(pack, config)
        # Default phase is DCA — correct for all three coins
        result = bt.run()
        if result:
            print_results(result)
            all_results.append(result)

    if all_results:
        print(f"\n{'=' * 80}")
        print(f"  SUMMARY — Demo Set Evaluation")
        print(f"{'=' * 80}")
        
        print(f"\n  {'Coin':<6} {'Closed':>8} {'Total':>8} {'B&H':>8} {'Alpha':>8} {'MaxDD':>8} {'Cycles':>8}")
        print(f"  {'-'*58}")
        for r in all_results:
            print(f"  {r['coin']:<6} {r['closed_roi']:>+7.1f}% {r['roi']:>+7.1f}% {r['buy_hold_return']:>+7.1f}% "
                  f"{r['closed_roi'] - r['buy_hold_return']:>+7.1f}% {r['max_drawdown']:>7.1f}% "
                  f"{r['markup_cycles']:>8}")
        
        avg_closed = np.mean([r['closed_roi'] for r in all_results])
        avg_bh = np.mean([r['buy_hold_return'] for r in all_results])
        print(f"\n  Avg Closed ROI: {avg_closed:+.1f}%")
        print(f"  Avg B&H:        {avg_bh:+.1f}%")
        print(f"  Avg Alpha:      {avg_closed - avg_bh:+.1f}%")
        
        print(f"\n  RECOMMENDATION:")
        for r in all_results:
            alpha = r['closed_roi'] - r['buy_hold_return']
            if alpha > 20 and r['closed_roi'] > 0:
                verdict = "INCLUDE in demo set"
            elif alpha > 0 and r['closed_roi'] > 0:
                verdict = "MARGINAL — consider including"
            else:
                verdict = "EXCLUDE from demo set"
            print(f"    {r['coin']}: {verdict} (alpha={alpha:+.1f}%, closed ROI={r['closed_roi']:+.1f}%)")


if __name__ == '__main__':
    main()
