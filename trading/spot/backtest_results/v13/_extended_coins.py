"""Test extended coin universe including newer coins with limited history."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from v13_signals import V13SignalPack
from v14_dca_engine import V14DCAEngine, V14Config

# Tier B: Borderline/new coins with ~369 daily candles
TIER_B = [
    'SUI/USDT', 'ALGO/USDT', 'ARB/USDT', 'FIL/USDT', 'INJ/USDT',
    'GRT/USDT', 'MANA/USDT', 'RUNE/USDT', 'CRV/USDT', 'FET/USDT',
    'GALA/USDT', 'TAO/USDT', 'TON/USDT',
]

# Tier C: Memes (test separately to see if volatility helps)
TIER_C = [
    'DOGE/USDT', 'PEPE/USDC', 'SHIB/USDT', 'BONK/USDT', 'WIF/USDT',
    'TRUMP/USDC',
]

CAPITAL = 2500

def test_coin(coin, label=""):
    try:
        pack = V13SignalPack(coin)
        cfg = V14Config()
        cfg.CAPITAL = CAPITAL
        cfg.OB_FALLBACK_1W = 99
        cfg.DCA_ACCUMULATE = False
        cfg.DCA_TP_PCT = 0.015
        cfg.DCA_BO_PCT = 0.40
        cfg.DCA_SO_DEVIATION = 0.02
        cfg.DCA_MAX_LAYERS = 10
        eng = V14DCAEngine(pack, cfg)
        r = eng.run()
        if r is None:
            print(f"  {coin:<14} NO DATA in range", flush=True)
            return None
        total_trades = r['total_long_trades'] + r['total_short_trades']
        print(f"  {coin:<14} ${r['final_equity']:>8,.2f} ({r['roi']:>+7.1f}%) DD:{r['max_drawdown']:>+6.1f}%"
              f"  trades:{total_trades:>3} phases:{r['phase_changes']}"
              f"  L:{r['long_pnl']:>+8.0f} S:{r['short_pnl']:>+8.0f}", flush=True)
        return r
    except Exception as e:
        err = str(e)[:60]
        print(f"  {coin:<14} FAILED: {err}", flush=True)
        return None

print("EXTENDED COIN UNIVERSE — V14 EVALUATION", flush=True)
print("Config: BO=40% Dev=2.0% Mult=1.5x L=10 TP=1.5% No OB85", flush=True)
print("=" * 80, flush=True)

print("\nTIER B — Borderline/Newer Coins:", flush=True)
tier_b_results = {}
for coin in TIER_B:
    r = test_coin(coin)
    if r:
        tier_b_results[coin] = r

print("\nTIER C — Meme Coins (volatility test):", flush=True)
tier_c_results = {}
for coin in TIER_C:
    r = test_coin(coin)
    if r:
        tier_c_results[coin] = r

# Combine with top Tier A results for ranking
print("\n" + "=" * 80, flush=True)
print("COMBINED RANKING (all viable coins, 1x Low profile):", flush=True)
all_results = {}
# Add Tier A top performers
TIER_A = ['HBAR/USDT', 'ATOM/USDT', 'LINK/USDC', 'NEAR/USDT', 'ADA/USDT',
          'UNI/USDT', 'LTC/USDT', 'SOL/USDC', 'DOT/USDT', 'ETH/USDC']
print("\nTier A (reference):", flush=True)
for coin in TIER_A:
    r = test_coin(coin)
    if r:
        all_results[coin] = r

all_results.update(tier_b_results)
all_results.update(tier_c_results)

# Sort by ROI
ranked = sorted(all_results.items(), key=lambda x: x[1]['roi'], reverse=True)
print(f"\nFULL RANKING:", flush=True)
print("-" * 80, flush=True)
for i, (coin, r) in enumerate(ranked, 1):
    total_trades = r['total_long_trades'] + r['total_short_trades']
    tier = "A" if coin in TIER_A else ("B" if coin in TIER_B else "C")
    print(f"  {i:>2}. [{tier}] {coin:<14} {r['roi']:>+7.1f}% DD:{r['max_drawdown']:>+6.1f}%"
          f"  trades:{total_trades:>3} phases:{r['phase_changes']}", flush=True)
