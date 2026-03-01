"""Compare V14 accumulate vs cycling mode across all coins."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from v13_signals import V13SignalPack
from v14_dca_engine import V14DCAEngine, V14Config

coins_current = ['ETH/USDC', 'SOL/USDC', 'LINK/USDC', 'XRP/USDC']
coins_best = ['HBAR/USDT', 'ADA/USDT', 'LINK/USDC', 'ATOM/USDT']
CAPITAL = 2500

def run_portfolio(label, coins, accumulate):
    total = 0
    for coin in coins:
        pack = V13SignalPack(coin)
        cfg = V14Config()
        cfg.CAPITAL = CAPITAL
        cfg.OB_FALLBACK_1W = 99  # No OB85
        cfg.DCA_ACCUMULATE = accumulate
        eng = V14DCAEngine(pack, cfg)
        r = eng.run()
        total += r['final_equity']
        print(f"  {coin:<12} ${r['final_equity']:>8,.2f} ({r['roi']:>+7.1f}%)"
              f"  L:{r['long_pnl']:>+8.1f} S:{r['short_pnl']:>+8.1f}"
              f"  trades: L={r['total_long_trades']} S={r['total_short_trades']}")
    roi = (total - 10000) / 10000 * 100
    print(f"  {'TOTAL':<12} ${total:>8,.2f} ({roi:>+7.1f}%)")
    return total

print("=" * 70)
print("CURRENT COINS — ACCUMULATE (hold until signal)")
run_portfolio("Accumulate", coins_current, True)

print("\n" + "=" * 70)
print("CURRENT COINS — CYCLING (TP at 1.5%, restart grid)")
run_portfolio("Cycling", coins_current, False)

# Also test different TP levels for cycling
print("\n" + "=" * 70)
for tp in [0.01, 0.015, 0.02, 0.025, 0.03]:
    total = 0
    for coin in coins_current:
        pack = V13SignalPack(coin)
        cfg = V14Config()
        cfg.CAPITAL = CAPITAL
        cfg.OB_FALLBACK_1W = 99
        cfg.DCA_ACCUMULATE = False
        cfg.DCA_TP_PCT = tp
        eng = V14DCAEngine(pack, cfg)
        r = eng.run()
        total += r['final_equity']
    roi = (total - 10000) / 10000 * 100
    print(f"CYCLING TP={tp*100:.1f}%: ${total:>9,.2f} ({roi:>+7.1f}%)")

# Best coins with cycling
print("\n" + "=" * 70)
print("BEST COINS (HBAR/ADA/LINK/ATOM) — ACCUMULATE")
run_portfolio("Best Accum", coins_best, True)

print("\n" + "=" * 70)
print("BEST COINS (HBAR/ADA/LINK/ATOM) — CYCLING")
run_portfolio("Best Cycle", coins_best, False)

# TP sweep on best coins
print("\n" + "=" * 70)
for tp in [0.01, 0.015, 0.02, 0.025, 0.03]:
    total = 0
    for coin in coins_best:
        pack = V13SignalPack(coin)
        cfg = V14Config()
        cfg.CAPITAL = CAPITAL
        cfg.OB_FALLBACK_1W = 99
        cfg.DCA_ACCUMULATE = False
        cfg.DCA_TP_PCT = tp
        eng = V14DCAEngine(pack, cfg)
        r = eng.run()
        total += r['final_equity']
    roi = (total - 10000) / 10000 * 100
    print(f"BEST CYCLING TP={tp*100:.1f}%: ${total:>9,.2f} ({roi:>+7.1f}%)")
