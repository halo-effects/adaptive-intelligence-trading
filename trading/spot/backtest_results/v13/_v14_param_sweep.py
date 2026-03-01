"""Sweep remaining V14 parameters on best coins with cycling mode."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from v13_signals import V13SignalPack
from v14_dca_engine import V14DCAEngine, V14Config

best = ['HBAR/USDT', 'ADA/USDT', 'LINK/USDC', 'ATOM/USDT']
CAPITAL = 10000

def run(label, cfg_fn=None):
    total = 0
    per = CAPITAL / len(best)
    for coin in best:
        pack = V13SignalPack(coin)
        cfg = V14Config()
        cfg.CAPITAL = per
        cfg.OB_FALLBACK_1W = 99
        cfg.DCA_ACCUMULATE = False
        cfg.DCA_TP_PCT = 0.015
        if cfg_fn:
            cfg_fn(cfg)
        eng = V14DCAEngine(pack, cfg)
        r = eng.run()
        total += r['final_equity']
    roi = (total - CAPITAL) / CAPITAL * 100
    print(f"  {label:<50} ${total:>9,.2f} ({roi:>+7.1f}%)", flush=True)
    return total

def run_detail(label, cfg_fn=None):
    total = 0
    per = CAPITAL / len(best)
    for coin in best:
        pack = V13SignalPack(coin)
        cfg = V14Config()
        cfg.CAPITAL = per
        cfg.OB_FALLBACK_1W = 99
        cfg.DCA_ACCUMULATE = False
        cfg.DCA_TP_PCT = 0.015
        if cfg_fn:
            cfg_fn(cfg)
        eng = V14DCAEngine(pack, cfg)
        r = eng.run()
        total += r['final_equity']
        print(f"    {coin:<12} ${r['final_equity']:>8,.2f} ({r['roi']:>+7.1f}%) DD:{r['max_drawdown']:>+6.1f}% trades:L={r['total_long_trades']} S={r['total_short_trades']}", flush=True)
    roi = (total - CAPITAL) / CAPITAL * 100
    print(f"    {'TOTAL':<12} ${total:>8,.2f} ({roi:>+7.1f}%)", flush=True)
    return total

print("V14 PARAMETER SWEEP — BEST COINS (HBAR/ADA/LINK/ATOM)", flush=True)
print("Baseline: Cycling TP=1.5%, BO=30%, Dev=2.5%, Mult=1.5x, 8 layers", flush=True)
print("=" * 70, flush=True)

# Baseline
print("\nBASELINE:", flush=True)
run_detail("Cycling TP=1.5% BO=30% Dev=2.5% Mult=1.5x L=8")

# --- BO% sweep ---
print("\nBO% SWEEP:", flush=True)
for bo in [0.15, 0.20, 0.25, 0.30, 0.40, 0.50]:
    run(f"BO={int(bo*100)}%", lambda c, b=bo: setattr(c, 'DCA_BO_PCT', b))

# --- Deviation sweep ---
print("\nDEVIATION SWEEP:", flush=True)
for dev in [0.015, 0.02, 0.025, 0.03, 0.035, 0.04]:
    run(f"Dev={dev*100:.1f}%", lambda c, d=dev: setattr(c, 'DCA_SO_DEVIATION', d))

# --- Multiplier sweep ---
print("\nMULTIPLIER SWEEP:", flush=True)
for mult in [1.0, 1.2, 1.3, 1.5, 1.8, 2.0, 2.5]:
    run(f"Mult={mult}x", lambda c, m=mult: setattr(c, 'DCA_SO_MULTIPLIER', m))

# --- Max layers sweep ---
print("\nMAX LAYERS SWEEP:", flush=True)
for layers in [4, 6, 8, 10, 12]:
    run(f"Layers={layers}", lambda c, l=layers: setattr(c, 'DCA_MAX_LAYERS', l))

# --- TP per coin (test if different TPs help) ---
print("\nTP SWEEP:", flush=True)
for tp in [0.01, 0.012, 0.015, 0.018, 0.02, 0.025, 0.03]:
    run(f"TP={tp*100:.1f}%", lambda c, t=tp: setattr(c, 'DCA_TP_PCT', t))

# --- Capital allocation (weighted) ---
print("\nCAPITAL ALLOCATION:", flush=True)
# Equal (baseline)
run("Equal $2,500 each")
# Performance-weighted
print("  (Manual weighted allocations:)", flush=True)
weights = {'HBAR/USDT': 0.40, 'ADA/USDT': 0.20, 'LINK/USDC': 0.20, 'ATOM/USDT': 0.20}
total = 0
for coin in best:
    pack = V13SignalPack(coin)
    cfg = V14Config()
    cfg.CAPITAL = CAPITAL * weights[coin]
    cfg.OB_FALLBACK_1W = 99; cfg.DCA_ACCUMULATE = False; cfg.DCA_TP_PCT = 0.015
    eng = V14DCAEngine(pack, cfg)
    r = eng.run()
    total += r['final_equity']
    print(f"    {coin:<12} alloc={weights[coin]*100:.0f}% ${r['final_equity']:>8,.2f} ({r['roi']:>+7.1f}%)", flush=True)
roi = (total - CAPITAL) / CAPITAL * 100
print(f"  40/20/20/20 weighted:                              ${total:>9,.2f} ({roi:>+7.1f}%)", flush=True)

# 50/20/15/15
weights2 = {'HBAR/USDT': 0.50, 'ADA/USDT': 0.20, 'LINK/USDC': 0.15, 'ATOM/USDT': 0.15}
total = 0
for coin in best:
    pack = V13SignalPack(coin)
    cfg = V14Config()
    cfg.CAPITAL = CAPITAL * weights2[coin]
    cfg.OB_FALLBACK_1W = 99; cfg.DCA_ACCUMULATE = False; cfg.DCA_TP_PCT = 0.015
    eng = V14DCAEngine(pack, cfg)
    r = eng.run()
    total += r['final_equity']
roi = (total - CAPITAL) / CAPITAL * 100
print(f"  50/20/15/15 weighted:                              ${total:>9,.2f} ({roi:>+7.1f}%)", flush=True)

# --- Best combo (will fill in after seeing results) ---
print("\nOPTIMAL COMBO TEST:", flush=True)
# Test a few promising combos from above
combos = [
    ("BO=40% Dev=2.5% Mult=1.5x L=8", lambda c: [setattr(c, 'DCA_BO_PCT', 0.40)]),
    ("BO=30% Dev=2.0% Mult=1.5x L=8", lambda c: [setattr(c, 'DCA_SO_DEVIATION', 0.02)]),
    ("BO=30% Dev=2.5% Mult=1.3x L=10", lambda c: [setattr(c, 'DCA_SO_MULTIPLIER', 1.3), setattr(c, 'DCA_MAX_LAYERS', 10)]),
    ("BO=40% Dev=2.0% Mult=1.5x L=10", lambda c: [setattr(c, 'DCA_BO_PCT', 0.40), setattr(c, 'DCA_SO_DEVIATION', 0.02), setattr(c, 'DCA_MAX_LAYERS', 10)]),
]
for label, fn in combos:
    run_detail(label, fn)
