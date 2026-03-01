"""Evaluate HBAR and AAVE as V14 coin candidates vs current SOL/XRP."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from v13_signals import V13SignalPack
from v14_dca_engine import V14DCAEngine, V14Config

# Test coins — USDT pairs for HBAR/AAVE
test_coins = {
    # Current portfolio
    'ETH/USDC': 'ETH/USDC',
    'SOL/USDC': 'SOL/USDC',
    'LINK/USDC': 'LINK/USDC',  # LINK is actually USDT in DB
    'XRP/USDC': 'XRP/USDC',
    # Candidates
    'HBAR/USDT': 'HBAR/USDT',
    'AAVE/USDT': 'AAVE/USDT',
    # Other qualified coins to compare
    'ADA/USDT': 'ADA/USDT',
    'AVAX/USDT': 'AVAX/USDT',
    'DOT/USDT': 'DOT/USDT',
    'UNI/USDT': 'UNI/USDT',
    'BNB/USDT': 'BNB/USDT',
    'LTC/USDT': 'LTC/USDT',
    'NEAR/USDT': 'NEAR/USDT',
    'ATOM/USDT': 'ATOM/USDT',
}

CAPITAL = 2500  # per-coin allocation

print("V14 COIN EVALUATION (Oct 2024 start, $2,500/coin, NO OB85)")
print("=" * 80)

results = []
for label, coin in test_coins.items():
    try:
        pack = V13SignalPack(coin)
        cfg = V14Config()
        cfg.CAPITAL = CAPITAL
        cfg.OB_FALLBACK_1W = 99  # No OB85 (locked decision)
        eng = V14DCAEngine(pack, cfg)
        r = eng.run()
        results.append((label, r))
        phases_str = ' | '.join(
            f"{p['date'].date()} {p['from'][:5]}->{p['to'][:5]} ({p['reason'][:30]})"
            for p in r['phases']
        )
        print(f"{label:<12} ${r['final_equity']:>8,.2f} ({r['roi']:>+7.1f}%)"
              f"  DD:{r['max_drawdown']:>+6.1f}%  L:{r['long_pnl']:>+8.1f} S:{r['short_pnl']:>+8.1f}"
              f"  phases:{r['phase_changes']}")
        for p in r['phases']:
            print(f"  {p['date'].date()}: {p['from']}->{p['to']} ({p['reason']})")
        for ct in r.get('conviction_triggers', []):
            print(f"  CONVICTION: {ct['date'].date()} score={ct['score']} @ ${float(ct['details']['price']):.2f}")
        for tt in r.get('top_triggers', []):
            print(f"  TOP: {tt['date'].date()} {tt['reason']} @ ${tt['price']:.2f}")
    except Exception as e:
        print(f"{label:<12} FAILED: {e}")
    print()

# Rank by ROI
print("\nRANKED BY ROI")
print("-" * 60)
results.sort(key=lambda x: x[1]['roi'], reverse=True)
for i, (label, r) in enumerate(results, 1):
    flag = " *** CURRENT" if label in ['ETH/USDC', 'SOL/USDC', 'LINK/USDC', 'XRP/USDC'] else ""
    print(f"  {i:>2}. {label:<12} {r['roi']:>+7.1f}%  (${r['final_equity']:>8,.2f})  DD:{r['max_drawdown']:>+6.1f}%{flag}")

# Best 4-coin portfolio combinations
print("\nBEST 4-COIN PORTFOLIOS (top 5)")
print("-" * 60)
from itertools import combinations
all_labels = [label for label, _ in results]
all_results = {label: r for label, r in results}
combos = []
for combo in combinations(all_labels, 4):
    total = sum(all_results[c]['final_equity'] for c in combo)
    worst_dd = min(all_results[c]['max_drawdown'] for c in combo)
    combos.append((combo, total, worst_dd))
combos.sort(key=lambda x: x[1], reverse=True)
for combo, total, worst_dd in combos[:10]:
    roi = (total - 10000) / 10000 * 100
    coins_str = ', '.join(c.split('/')[0] for c in combo)
    print(f"  ${total:>9,.2f} ({roi:>+7.1f}%)  DD:{worst_dd:>+6.1f}%  [{coins_str}]")
