"""Test V14 risk profiles: Low (1x), Medium (1.5x), High (1.5x + aggressive grid)."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from v13_signals import V13SignalPack
from v14_dca_engine import V14DCAEngine, V14Config

best = ['HBAR/USDT', 'ADA/USDT', 'LINK/USDC', 'ATOM/USDT']
CAPITAL = 10000

def run_profile(label, leverage=1.0, bo=0.40, dev=0.02, mult=1.5, layers=10, tp=0.015):
    total = 0
    per = CAPITAL / len(best)
    print(f"\n{label}", flush=True)
    print(f"  Leverage={leverage}x BO={int(bo*100)}% Dev={dev*100:.1f}% Mult={mult}x L={layers} TP={tp*100:.1f}%", flush=True)
    for coin in best:
        pack = V13SignalPack(coin)
        cfg = V14Config()
        cfg.CAPITAL = per
        cfg.OB_FALLBACK_1W = 99
        cfg.DCA_ACCUMULATE = False
        cfg.DCA_BO_PCT = bo
        cfg.DCA_SO_DEVIATION = dev
        cfg.DCA_SO_MULTIPLIER = mult
        cfg.DCA_MAX_LAYERS = layers
        cfg.DCA_TP_PCT = tp
        eng = V14DCAEngine(pack, cfg)
        r = eng.run()
        pnl = (r['final_equity'] - per) * leverage
        if pnl < -per * 0.9: pnl = -per * 0.9
        lev_eq = per + pnl
        lev_roi = pnl / per * 100
        lev_dd = r['max_drawdown'] * leverage
        total += lev_eq
        print(f"    {coin:<12} ${lev_eq:>8,.2f} ({lev_roi:>+7.1f}%) DD:{lev_dd:>+6.1f}% trades:L={r['total_long_trades']} S={r['total_short_trades']}", flush=True)
    roi = (total - CAPITAL) / CAPITAL * 100
    print(f"    {'TOTAL':<12} ${total:>8,.2f} ({roi:>+7.1f}%)", flush=True)
    return total

print("V14 RISK PROFILE SWEEP", flush=True)
print("=" * 70, flush=True)

# LOW: 1x leverage, standard optimal grid
run_profile("LOW — 1x, standard grid",
            leverage=1.0, bo=0.40, dev=0.02, mult=1.5, layers=10, tp=0.015)

# MEDIUM: 1.5x leverage, standard grid
run_profile("MEDIUM — 1.5x, standard grid",
            leverage=1.5, bo=0.40, dev=0.02, mult=1.5, layers=10, tp=0.015)

# HIGH candidates: 1.5x leverage + aggressive grid variations
print("\n" + "=" * 70, flush=True)
print("HIGH PROFILE CANDIDATES (1.5x leverage + grid scaling):", flush=True)

# More aggressive BO
run_profile("HIGH-A: 1.5x, BO=50%",
            leverage=1.5, bo=0.50, dev=0.02, mult=1.5, layers=10, tp=0.015)

# Tighter deviation = more layers fill
run_profile("HIGH-B: 1.5x, Dev=1.5%",
            leverage=1.5, bo=0.40, dev=0.015, mult=1.5, layers=10, tp=0.015)

# More layers
run_profile("HIGH-C: 1.5x, Layers=12",
            leverage=1.5, bo=0.40, dev=0.02, mult=1.5, layers=12, tp=0.015)

# Higher multiplier = deeper layers bigger
run_profile("HIGH-D: 1.5x, Mult=2.0x",
            leverage=1.5, bo=0.40, dev=0.02, mult=2.0, layers=10, tp=0.015)

# BO=50% + tighter dev
run_profile("HIGH-E: 1.5x, BO=50% Dev=1.5%",
            leverage=1.5, bo=0.50, dev=0.015, mult=1.5, layers=10, tp=0.015)

# BO=50% + more layers
run_profile("HIGH-F: 1.5x, BO=50% L=12",
            leverage=1.5, bo=0.50, dev=0.02, mult=1.5, layers=12, tp=0.015)

# Tighter dev + more layers
run_profile("HIGH-G: 1.5x, Dev=1.5% L=12",
            leverage=1.5, bo=0.40, dev=0.015, mult=1.5, layers=12, tp=0.015)

# BO=50% + tighter dev + more layers (max aggressive)
run_profile("HIGH-H: 1.5x, BO=50% Dev=1.5% L=12",
            leverage=1.5, bo=0.50, dev=0.015, mult=1.5, layers=12, tp=0.015)

# Also test TP scaling for high
run_profile("HIGH-I: 1.5x, BO=50% TP=1.8%",
            leverage=1.5, bo=0.50, dev=0.02, mult=1.5, layers=10, tp=0.018)

run_profile("HIGH-J: 1.5x, BO=50% Dev=1.5% TP=1.8%",
            leverage=1.5, bo=0.50, dev=0.015, mult=1.5, layers=10, tp=0.018)
