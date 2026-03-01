"""
V13 v8 backtest: PEPE, NEAR, LINK across Low/Medium/High risk profiles.
Daily candles, Oct 2024 -> Feb 2026. Cold start: DCA for all.

Risk Profile Settings (from risk-profiles-spec.md):
  Low:    5 SOs, 3% BO, 2.0x mult, 3.0% dev, 1.5% TP, max 2 coins
  Medium: 8 SOs, 4% BO, 2.0x mult, 2.5% dev, 1.5% TP, max 3 coins
  High:  12 SOs, 5% BO, 2.0x mult, 2.0% dev, 1.0% TP, max 5 coins

Markup/Short tiers remain same across profiles (phase-riding is strategy, not risk).
"""
import sys
import numpy as np
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from v13_phase_backtest_v8 import V13BacktestV8, V13Config, print_results
from v13_signals import V13SignalPack


def make_config(profile):
    """Create V13Config with risk profile DCA settings."""
    cfg = V13Config()
    
    if profile == 'low':
        cfg.DCA_BO_PCT = 0.03       # 3% base order
        cfg.DCA_SO_DEVIATION = 0.03  # 3.0% between layers
        cfg.DCA_SO_MULTIPLIER = 2.0  # 2.0x volume mult
        cfg.DCA_TP_PCT = 0.015       # 1.5% take profit
        cfg.DCA_MAX_LAYERS = 5       # 5 safety orders
    elif profile == 'medium':
        cfg.DCA_BO_PCT = 0.04       # 4% base order
        cfg.DCA_SO_DEVIATION = 0.025 # 2.5% between layers
        cfg.DCA_SO_MULTIPLIER = 2.0  # 2.0x volume mult
        cfg.DCA_TP_PCT = 0.015       # 1.5% take profit
        cfg.DCA_MAX_LAYERS = 8       # 8 safety orders
    elif profile == 'high':
        cfg.DCA_BO_PCT = 0.05       # 5% base order
        cfg.DCA_SO_DEVIATION = 0.02  # 2.0% between layers
        cfg.DCA_SO_MULTIPLIER = 2.0  # 2.0x volume mult
        cfg.DCA_TP_PCT = 0.010       # 1.0% take profit
        cfg.DCA_MAX_LAYERS = 12      # 12 safety orders
    
    return cfg


def run_profile(profile, coins):
    """Run all coins under a single profile, return results list."""
    cfg = make_config(profile)
    results = []
    
    print(f"\n  DCA Settings: BO={cfg.DCA_BO_PCT:.0%}, SO_dev={cfg.DCA_SO_DEVIATION:.1%}, "
          f"SO_mult={cfg.DCA_SO_MULTIPLIER}x, TP={cfg.DCA_TP_PCT:.1%}, max_layers={cfg.DCA_MAX_LAYERS}")
    
    for coin in coins:
        try:
            pack = V13SignalPack(coin)
        except Exception as e:
            print(f"  {coin}: SKIP ({e})")
            continue
        
        bt = V13BacktestV8(pack, cfg)
        r = bt.run()
        if r:
            results.append(r)
            print(f"  {r['coin']:<6} Closed: {r['closed_roi']:>+7.1f}%  Total: {r['roi']:>+7.1f}%  "
                  f"B&H: {r['buy_hold_return']:>+7.1f}%  Alpha: {r['closed_roi'] - r['buy_hold_return']:>+7.1f}%  "
                  f"DD: {r['max_drawdown']:>6.1f}%  Cycles: {r['markup_cycles']}  "
                  f"Trades: {r['closed_trades']} ({r['wins']}W/{r['losses']}L)")
    
    return results


def main():
    coins = ['PEPE', 'NEAR', 'LINK']
    profiles = ['low', 'medium', 'high']
    
    print("=" * 90)
    print("  V13 v8 — PEPE / NEAR / LINK — Risk Profile Comparison")
    print("  Daily candles, Oct 2024 -> Feb 2026, Cold start: DCA")
    print("=" * 90)
    
    all_profile_results = {}
    
    for profile in profiles:
        print(f"\n{'=' * 90}")
        print(f"  [{profile.upper()} RISK PROFILE]")
        print(f"{'=' * 90}")
        
        results = run_profile(profile, coins)
        all_profile_results[profile] = results
    
    # ── Comparison Table ────────────────────────────────────────────────
    print(f"\n{'=' * 90}")
    print(f"  COMPARISON: All Profiles x All Coins")
    print(f"{'=' * 90}")
    
    print(f"\n  {'Coin':<6} {'Profile':<8} {'Closed':>8} {'Total':>8} {'B&H':>8} {'Alpha':>8} {'MaxDD':>8} {'DCA PnL':>9} {'Trades':>7}")
    print(f"  {'-' * 76}")
    
    for coin in coins:
        for profile in profiles:
            results = all_profile_results[profile]
            r = next((x for x in results if x['coin'].startswith(coin[:4])), None)
            if r:
                alpha = r['closed_roi'] - r['buy_hold_return']
                print(f"  {r['coin']:<6} {profile:<8} {r['closed_roi']:>+7.1f}% {r['roi']:>+7.1f}% "
                      f"{r['buy_hold_return']:>+7.1f}% {alpha:>+7.1f}% {r['max_drawdown']:>7.1f}% "
                      f"${r['dca_pnl']:>+8,.0f} {r['closed_trades']:>7}")
        print()  # Blank line between coins
    
    # ── Portfolio-level comparison ──────────────────────────────────────
    print(f"\n  {'Profile':<8} {'Avg Closed':>10} {'Avg Total':>10} {'Avg B&H':>10} {'Avg Alpha':>10} {'Worst DD':>10}")
    print(f"  {'-' * 58}")
    for profile in profiles:
        results = all_profile_results[profile]
        if results:
            avg_closed = np.mean([r['closed_roi'] for r in results])
            avg_total = np.mean([r['roi'] for r in results])
            avg_bh = np.mean([r['buy_hold_return'] for r in results])
            worst_dd = min(r['max_drawdown'] for r in results)
            print(f"  {profile:<8} {avg_closed:>+9.1f}% {avg_total:>+9.1f}% {avg_bh:>+9.1f}% "
                  f"{avg_closed - avg_bh:>+9.1f}% {worst_dd:>9.1f}%")
    
    # ── Phase timelines for each (abbreviated) ─────────────────────────
    print(f"\n{'=' * 90}")
    print(f"  PHASE TIMELINES (Medium profile)")
    print(f"{'=' * 90}")
    
    for r in all_profile_results.get('medium', []):
        print(f"\n  {r['coin']}:")
        for p in r['phases']:
            print(f"    {p['date'].date()}: {p['from'] or 'START'} -> {p['to']} | "
                  f"{p['reason'][:60]} | eq=${p['equity']:,.0f}")


if __name__ == '__main__':
    main()
