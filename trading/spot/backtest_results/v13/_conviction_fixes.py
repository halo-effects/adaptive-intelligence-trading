"""Test 3 conviction fix approaches for V14."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from v13_signals import V13SignalPack
from v14_dca_engine import V14DCAEngine, V14Config
import copy

coins = ['ETH/USDC', 'SOL/USDC', 'LINK/USDC', 'XRP/USDC']
CAPITAL = 10000
PER_COIN = CAPITAL / len(coins)

def run_portfolio(label, config_fn=None):
    total = 0
    results = {}
    for coin in coins:
        pack = V13SignalPack(coin)
        cfg = V14Config()
        cfg.CAPITAL = PER_COIN
        if config_fn:
            config_fn(cfg)
        eng = V14DCAEngine(pack, cfg)
        r = eng.run()
        total += r['final_equity']
        results[coin] = r
    roi = (total - CAPITAL) / CAPITAL * 100
    print(f"\n{label}: ${total:,.2f} ({roi:+.1f}%)")
    for coin in coins:
        r = results[coin]
        print(f"  {coin:<12} ${r['final_equity']:>8,.2f} ({r['roi']:>+7.1f}%)  L:{r['long_pnl']:>+8.1f} S:{r['short_pnl']:>+8.1f}")
    return total, results

# --- BASELINE ---
print("=" * 70)
base_total, _ = run_portfolio("BASELINE (30% BO, conviction as-is)")

# --- FIX 1: Smaller base order after conviction (10% instead of 30%) ---
# We can't easily change BO per-phase without engine changes, so let's test
# globally reducing BO to see the direction
print("\n" + "=" * 70)
for bo in [0.10, 0.15, 0.20]:
    def set_bo(cfg, b=bo):
        cfg.DCA_BO_PCT = b
    run_portfolio(f"FIX 1a: Global BO={int(bo*100)}%", set_bo)

# --- FIX 2: Disable conviction entirely (stay in SHORT_DCA) ---
print("\n" + "=" * 70)
def no_conviction(cfg):
    cfg.CONVICTION_MIN_SCORE = 99  # effectively disable
run_portfolio("FIX 2: NO CONVICTION (shorts ride to end)", no_conviction)

# --- FIX 3: Conviction closes shorts but goes to ROUTER (not LONG_DCA) ---
# Can't easily test without engine changes, but we can approximate by
# disabling conviction + checking if just holding shorts longer helps

# --- FIX 4: Higher conviction threshold (4/4 instead of 3/4) ---
print("\n" + "=" * 70)
def strict_conviction(cfg):
    cfg.CONVICTION_MIN_SCORE = 4
run_portfolio("FIX 4: STRICT CONVICTION (4/4 required)", strict_conviction)

# --- FIX 5: Disable OB85 fallback (SOL's main problem) ---
print("\n" + "=" * 70)
def no_ob85(cfg):
    cfg.OB_FALLBACK_1W = 99  # effectively disable OB85
run_portfolio("FIX 5: NO OB85 FALLBACK", no_ob85)

# --- FIX 6: No OB85 + No conviction ---
print("\n" + "=" * 70)
def no_ob85_no_conv(cfg):
    cfg.OB_FALLBACK_1W = 99
    cfg.CONVICTION_MIN_SCORE = 99
run_portfolio("FIX 6: NO OB85 + NO CONVICTION", no_ob85_no_conv)

# --- FIX 7: No OB85 + strict conviction ---
print("\n" + "=" * 70)
def no_ob85_strict(cfg):
    cfg.OB_FALLBACK_1W = 99
    cfg.CONVICTION_MIN_SCORE = 4
run_portfolio("FIX 7: NO OB85 + STRICT CONVICTION (4/4)", no_ob85_strict)

# --- FIX 8: Longer divergence timeout ---
print("\n" + "=" * 70)
for timeout in [45, 60, 90]:
    def set_timeout(cfg, t=timeout):
        cfg.TOP_DIVERGENCE_TIMEOUT = t
    run_portfolio(f"FIX 8: TIMEOUT={timeout}d", set_timeout)
