"""Test OB85 refinements — conditional firing, threshold tuning."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from v13_signals import V13SignalPack
from v14_dca_engine import V14DCAEngine, V14Config

coins = ['ETH/USDC', 'SOL/USDC', 'LINK/USDC', 'XRP/USDC']
CAPITAL = 10000
PER_COIN = CAPITAL / len(coins)

def run_portfolio(label, config_fn=None):
    total = 0
    details = {}
    for coin in coins:
        pack = V13SignalPack(coin)
        cfg = V14Config()
        cfg.CAPITAL = PER_COIN
        if config_fn:
            config_fn(cfg)
        eng = V14DCAEngine(pack, cfg)
        r = eng.run()
        total += r['final_equity']
        details[coin] = r
    roi = (total - CAPITAL) / CAPITAL * 100
    print(f"\n{label}: ${total:,.2f} ({roi:+.1f}%)")
    for coin in coins:
        r = details[coin]
        print(f"  {coin:<12} ${r['final_equity']:>8,.2f} ({r['roi']:>+7.1f}%)  L:{r['long_pnl']:>+8.1f} S:{r['short_pnl']:>+8.1f}")
        # Show phase transitions
        for p in r['phases']:
            print(f"    {p['date'].date()}: {p['from']}->{p['to']} ({p['reason']})")
    return total, details

# BASELINE
print("=" * 70)
run_portfolio("BASELINE (OB85=85)")

# Raise OB85 threshold
print("\n" + "=" * 70)
for thresh in [87, 88, 89, 90, 92]:
    def set_t(cfg, t=thresh):
        cfg.OB_FALLBACK_1W = t
    run_portfolio(f"OB85 threshold = {thresh}", set_t)

# No OB85 (for reference)
print("\n" + "=" * 70)
def no_ob85(cfg):
    cfg.OB_FALLBACK_1W = 99
run_portfolio("NO OB85 (threshold=99)", no_ob85)
