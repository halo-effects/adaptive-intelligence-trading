"""Run all 17 qualified coins through V14 at Low/Medium/High risk profiles."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from v13_signals import V13SignalPack
from v14_dca_engine import V14DCAEngine, V14Config

# Full qualified universe
ALL_COINS = [
    'BTC/USDC', 'ETH/USDC', 'XRP/USDC', 'BNB/USDT', 'SOL/USDC',
    'LINK/USDC', 'ADA/USDT', 'LTC/USDT', 'AVAX/USDT', 'DOT/USDT',
    'UNI/USDT', 'AAVE/USDT', 'NEAR/USDT', 'HBAR/USDT', 'ATOM/USDT',
    # MATIC, MKR — check if data exists
]

# Try adding MATIC and MKR
for extra in ['MATIC/USDT', 'MKR/USDT']:
    try:
        pack = V13SignalPack(extra)
        ALL_COINS.append(extra)
    except:
        print(f"  {extra}: No data, skipping", flush=True)

PROFILES = {
    'Low': {'leverage': 1.0, 'dev': 0.02, 'layers': 10},
    'Medium': {'leverage': 1.5, 'dev': 0.02, 'layers': 10},
    'High': {'leverage': 1.5, 'dev': 0.015, 'layers': 12},
}

CAPITAL_PER_COIN = 2500  # Standard per-coin for comparison

def run_coin(coin, profile_name, profile):
    try:
        pack = V13SignalPack(coin)
        cfg = V14Config()
        cfg.CAPITAL = CAPITAL_PER_COIN
        cfg.OB_FALLBACK_1W = 99
        cfg.DCA_ACCUMULATE = False
        cfg.DCA_TP_PCT = 0.015
        cfg.DCA_BO_PCT = 0.40
        cfg.DCA_SO_DEVIATION = profile['dev']
        cfg.DCA_SO_MULTIPLIER = 1.5
        cfg.DCA_MAX_LAYERS = profile['layers']
        eng = V14DCAEngine(pack, cfg)
        r = eng.run()
        # Apply leverage
        lev = profile['leverage']
        pnl = (r['final_equity'] - CAPITAL_PER_COIN) * lev
        if pnl < -CAPITAL_PER_COIN * 0.9:
            pnl = -CAPITAL_PER_COIN * 0.9  # Liquidation
        lev_eq = CAPITAL_PER_COIN + pnl
        lev_roi = pnl / CAPITAL_PER_COIN * 100
        lev_dd = r['max_drawdown'] * lev
        return {
            'coin': coin, 'profile': profile_name,
            'equity': lev_eq, 'roi': lev_roi, 'dd': lev_dd,
            'long_trades': r['total_long_trades'],
            'short_trades': r['total_short_trades'],
            'long_wins': r['long_wins'], 'short_wins': r['short_wins'],
            'long_pnl': r['long_pnl'] * lev,
            'short_pnl': r['short_pnl'] * lev,
            'phases': r['phase_changes'],
            'phase_log': r['phases'],
            'conviction_triggers': r.get('conviction_triggers', []),
            'top_triggers': r.get('top_triggers', []),
        }
    except Exception as e:
        return {'coin': coin, 'profile': profile_name, 'error': str(e)}


print("V14 FULL UNIVERSE — ALL RISK PROFILES", flush=True)
print(f"Coins: {len(ALL_COINS)} | Capital: ${CAPITAL_PER_COIN}/coin | TP=1.5% BO=40%", flush=True)
print("=" * 90, flush=True)

all_results = []

for pname, pconfig in PROFILES.items():
    print(f"\n{'='*90}", flush=True)
    print(f"  {pname.upper()} PROFILE — Leverage={pconfig['leverage']}x Dev={pconfig['dev']*100:.1f}% Layers={pconfig['layers']}", flush=True)
    print(f"{'='*90}", flush=True)

    results = []
    for coin in ALL_COINS:
        r = run_coin(coin, pname, pconfig)
        if 'error' in r:
            print(f"  {coin:<12} ERROR: {r['error']}", flush=True)
            continue
        results.append(r)
        total_trades = r['long_trades'] + r['short_trades']
        print(f"  {coin:<12} ${r['equity']:>8,.2f} ({r['roi']:>+7.1f}%) DD:{r['dd']:>+6.1f}%"
              f"  trades:{total_trades:>3} phases:{r['phases']}"
              f"  L:{r['long_pnl']:>+8.0f} S:{r['short_pnl']:>+8.0f}", flush=True)
        all_results.append(r)

    # Rank
    results.sort(key=lambda x: x['roi'], reverse=True)
    print(f"\n  RANKED ({pname}):", flush=True)
    for i, r in enumerate(results, 1):
        total_trades = r['long_trades'] + r['short_trades']
        cycle_rate = total_trades / max(r['phases'], 1)
        print(f"  {i:>2}. {r['coin']:<12} {r['roi']:>+7.1f}% DD:{r['dd']:>+6.1f}%"
              f"  trades:{total_trades:>3} phases:{r['phases']}"
              f"  cycles/phase:{cycle_rate:>5.1f}", flush=True)

    # Best 4-coin portfolio
    from itertools import combinations
    best_combo = None
    best_total = 0
    for combo in combinations(results, 4):
        total = sum(c['equity'] for c in combo)
        if total > best_total:
            best_total = total
            best_combo = combo
    if best_combo:
        roi = (best_total - 10000) / 10000 * 100
        coins_str = ', '.join(c['coin'].split('/')[0] for c in best_combo)
        worst_dd = min(c['dd'] for c in best_combo)
        print(f"\n  BEST 4-COIN ({pname}): [{coins_str}]", flush=True)
        print(f"  Total: ${best_total:,.2f} ({roi:+.1f}%) Worst DD: {worst_dd:.1f}%", flush=True)

# Cross-profile summary
print(f"\n{'='*90}", flush=True)
print("CROSS-PROFILE COMPARISON — COIN SCORING DATA", flush=True)
print(f"{'='*90}", flush=True)
print(f"{'Coin':<12} {'Low ROI':>8} {'Med ROI':>8} {'High ROI':>9} {'Low DD':>7} {'Med DD':>7} {'High DD':>8} {'Trades':>7} {'Phases':>7}", flush=True)
print("-" * 90, flush=True)

for coin in ALL_COINS:
    coin_results = [r for r in all_results if r['coin'] == coin and 'error' not in r]
    if len(coin_results) < 3:
        continue
    low = next((r for r in coin_results if r['profile'] == 'Low'), None)
    med = next((r for r in coin_results if r['profile'] == 'Medium'), None)
    high = next((r for r in coin_results if r['profile'] == 'High'), None)
    if low and med and high:
        total_trades = low['long_trades'] + low['short_trades']
        print(f"{coin:<12} {low['roi']:>+7.1f}% {med['roi']:>+7.1f}% {high['roi']:>+8.1f}%"
              f" {low['dd']:>+6.1f}% {med['dd']:>+6.1f}% {high['dd']:>+7.1f}%"
              f" {total_trades:>6} {low['phases']:>6}", flush=True)
