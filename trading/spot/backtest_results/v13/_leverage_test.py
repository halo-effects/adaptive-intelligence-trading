"""Test low leverage (2-3x) on V14 optimal config."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from v13_signals import V13SignalPack
from v14_dca_engine import V14DCAEngine, V14Config

best = ['HBAR/USDT', 'ADA/USDT', 'LINK/USDC', 'ATOM/USDT']
current = ['ETH/USDC', 'SOL/USDC', 'LINK/USDC', 'XRP/USDC']
CAPITAL = 10000

def run(label, coins, cfg_fn=None, leverage=1.0):
    """Run with simulated leverage by multiplying capital utilization."""
    total = 0
    per = CAPITAL / len(coins)
    for coin in coins:
        pack = V13SignalPack(coin)
        cfg = V14Config()
        cfg.CAPITAL = per
        cfg.OB_FALLBACK_1W = 99
        cfg.DCA_ACCUMULATE = False
        # Optimal params
        cfg.DCA_BO_PCT = 0.40
        cfg.DCA_SO_DEVIATION = 0.02
        cfg.DCA_MAX_LAYERS = 10
        cfg.DCA_TP_PCT = 0.015
        if cfg_fn:
            cfg_fn(cfg)
        # Simulate leverage: multiply capital utilization
        # In practice, leverage means your $2500 acts like $5000 (2x) or $7500 (3x)
        # But drawdowns are also amplified
        cfg.DCA_CAPITAL_PCT = min(cfg.DCA_CAPITAL_PCT * leverage, 1.0)
        eng = V14DCAEngine(pack, cfg)
        r = eng.run()
        # Scale PnL by leverage (simplified - actual leverage amplifies both gains and losses)
        # More accurate: the engine already uses more capital via DCA_CAPITAL_PCT
        total += r['final_equity']
        if leverage > 1:
            # Approximate: equity = capital + (equity - capital) * leverage
            leveraged_pnl = (r['final_equity'] - per) * leverage
            # But cap at liquidation (-90% of capital)
            if leveraged_pnl < -per * 0.9:
                leveraged_pnl = -per * 0.9  # Liquidated
            leveraged_eq = per + leveraged_pnl
            total = total - r['final_equity'] + leveraged_eq
    roi = (total - CAPITAL) / CAPITAL * 100
    print(f"  {label:<55} ${total:>9,.2f} ({roi:>+7.1f}%)", flush=True)
    return total

def run_detail(label, coins, leverage=1.0):
    total = 0
    per = CAPITAL / len(coins)
    for coin in coins:
        pack = V13SignalPack(coin)
        cfg = V14Config()
        cfg.CAPITAL = per
        cfg.OB_FALLBACK_1W = 99
        cfg.DCA_ACCUMULATE = False
        cfg.DCA_BO_PCT = 0.40
        cfg.DCA_SO_DEVIATION = 0.02
        cfg.DCA_MAX_LAYERS = 10
        cfg.DCA_TP_PCT = 0.015
        eng = V14DCAEngine(pack, cfg)
        r = eng.run()
        pnl = r['final_equity'] - per
        lev_pnl = pnl * leverage
        if lev_pnl < -per * 0.9:
            lev_pnl = -per * 0.9
        lev_eq = per + lev_pnl
        lev_roi = lev_pnl / per * 100
        # DD also amplified
        lev_dd = r['max_drawdown'] * leverage
        total += lev_eq
        print(f"    {coin:<12} ${lev_eq:>8,.2f} ({lev_roi:>+7.1f}%) DD:{lev_dd:>+6.1f}%", flush=True)
    roi = (total - CAPITAL) / CAPITAL * 100
    print(f"    {'TOTAL':<12} ${total:>8,.2f} ({roi:>+7.1f}%)", flush=True)
    return total

print("LEVERAGE TEST — V14 OPTIMAL CONFIG", flush=True)
print("Config: BO=40%, Dev=2.0%, Mult=1.5x, L=10, TP=1.5%, No OB85", flush=True)
print("=" * 70, flush=True)

print("\nBEST COINS (HBAR/ADA/LINK/ATOM):", flush=True)
for lev in [1.0, 1.5, 2.0, 2.5, 3.0]:
    print(f"\n  {lev}x leverage:", flush=True)
    run_detail(f"Best coins {lev}x", best, lev)

print("\nCURRENT COINS (ETH/SOL/LINK/XRP):", flush=True)
for lev in [1.0, 1.5, 2.0, 2.5, 3.0]:
    print(f"\n  {lev}x leverage:", flush=True)
    run_detail(f"Current coins {lev}x", current, lev)

print("\nSUMMARY:", flush=True)
print("-" * 70, flush=True)
for lev in [1.0, 1.5, 2.0, 2.5, 3.0]:
    for label, coins in [("Best", best), ("Current", current)]:
        total = 0
        per = CAPITAL / len(coins)
        for coin in coins:
            pack = V13SignalPack(coin)
            cfg = V14Config()
            cfg.CAPITAL = per
            cfg.OB_FALLBACK_1W = 99; cfg.DCA_ACCUMULATE = False
            cfg.DCA_BO_PCT = 0.40; cfg.DCA_SO_DEVIATION = 0.02
            cfg.DCA_MAX_LAYERS = 10; cfg.DCA_TP_PCT = 0.015
            eng = V14DCAEngine(pack, cfg)
            r = eng.run()
            pnl = (r['final_equity'] - per) * lev
            if pnl < -per * 0.9: pnl = -per * 0.9
            total += per + pnl
        roi = (total - CAPITAL) / CAPITAL * 100
        worst_dd = 0
        for coin in coins:
            pack = V13SignalPack(coin)
            cfg = V14Config()
            cfg.CAPITAL = per; cfg.OB_FALLBACK_1W = 99; cfg.DCA_ACCUMULATE = False
            cfg.DCA_BO_PCT = 0.40; cfg.DCA_SO_DEVIATION = 0.02
            cfg.DCA_MAX_LAYERS = 10; cfg.DCA_TP_PCT = 0.015
            eng = V14DCAEngine(pack, cfg)
            r = eng.run()
            dd = r['max_drawdown'] * lev
            if dd < worst_dd: worst_dd = dd
        print(f"  {label:<8} {lev}x: ${total:>9,.2f} ({roi:>+7.1f}%)  worst DD: {worst_dd:>+6.1f}%", flush=True)
