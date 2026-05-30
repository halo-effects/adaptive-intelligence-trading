"""
Orphan-TP vs Force-Close A/B Backtest Comparison

Runs V14 DCA engine in two modes:
  A) FORCE_CLOSE_ON_SIGNAL=True  (legacy: force-close + MARKDOWN_FAIL)
  B) FORCE_CLOSE_ON_SIGNAL=False (new: orphan-TP, no force-closes)

Compares PnL, drawdown, trade counts, and win rates across key coins.
Uses the live PM profile: High, 4 layers, 3.0% TP, 1.0x leverage.
"""
import sys
import copy
import json
from pathlib import Path
from datetime import datetime

# Ensure project root on path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from trading.spot.engine.v14_dca_engine import V14DCAEngine, V14Config, Phase
from trading.spot.engine.v13_signals import V13SignalPack

# Test coins: approved (INJ, JUP, TON) + incident coins (ONDO, ADA)
# Plus a few extra for broader coverage
TEST_COINS = [
    'INJ/USDT', 'JUP/USDT', 'TON/USDT',   # Approved scanner coins
    'ONDO/USDT', 'ADA/USDT',                 # Incident coins
    'PENDLE/USDT', 'NEAR/USDT', 'HBAR/USDT', # Extra coverage
]

# Live PM profile: High, 3.0% TP, 4 max layers (grid optimization from 2026-05-12)
PM_OVERRIDES = {
    'DCA_TP_PCT': 0.03,           # 3.0% TP
    'DCA_MAX_LAYERS': 4,          # 4 layers (was 12)
    'DCA_BO_PCT': 0.40,           # 40% base order
    'DCA_SO_DEVIATION': 0.015,    # 1.5% deviation
    'DCA_SO_MULTIPLIER': 1.5,     # 1.5x multiplier
    'DCA_ACCUMULATE': False,      # Cycle mode (TP active)
    'CAPITAL': 10000,
    'START_DATE': '2024-10-01',
    'END_DATE': '2026-05-15',
}


def make_config(force_close: bool) -> V14Config:
    """Create a V14Config with PM profile overrides."""
    cfg = V14Config()
    for k, v in PM_OVERRIDES.items():
        setattr(cfg, k, v)
    cfg.FORCE_CLOSE_ON_SIGNAL = force_close
    return cfg


# Cache signal packs (expensive to build, same for both modes)
_pack_cache = {}

def _get_pack(coin: str) -> V13SignalPack:
    if coin not in _pack_cache:
        _pack_cache[coin] = V13SignalPack(coin)
    return _pack_cache[coin]


def run_single(coin: str, force_close: bool) -> dict:
    """Run backtest for a single coin in one mode."""
    cfg = make_config(force_close)
    pack = _get_pack(coin)
    engine = V14DCAEngine(pack, cfg)
    result = engine.run()
    if result is None:
        return None

    # Count force-close events
    force_closes = 0
    markdown_fails = 0
    orphan_tps = 0
    for t in engine.trades:
        action = t.get('action', '')
        if 'LONG_DCA_CLOSE' in action or 'SHORT_DCA_CLOSE' in action:
            if 'OPEN_END' not in action:
                force_closes += 1
                if 'MARKDOWN_FAIL' in action:
                    markdown_fails += 1
        if 'orphan' in action.lower():
            orphan_tps += 1

    # Count orphaned positions (positions open at phase transition in new mode)
    orphan_events = 0
    if not force_close:
        # Track phase transitions where positions were left open
        for t in engine.trades:
            action = t.get('action', '')
            # TP hits after phase transition indicate successful orphan resolution
            if 'DCA_TP' in action:
                orphan_tps += 1

    return {
        'coin': coin,
        'mode': 'legacy' if force_close else 'orphan-tp',
        'final_equity': result['final_equity'],
        'roi': result['roi'],
        'max_drawdown': result['max_drawdown'],
        'total_trades': result['total_long_trades'] + result['total_short_trades'],
        'long_trades': result['total_long_trades'],
        'short_trades': result['total_short_trades'],
        'long_wins': result['long_wins'],
        'short_wins': result['short_wins'],
        'long_pnl': result.get('long_pnl', 0),
        'short_pnl': result.get('short_pnl', 0),
        'force_closes': force_closes,
        'markdown_fails': markdown_fails,
        'phase_changes': result.get('phase_changes', 0),
    }


def main():
    print("=" * 90)
    print("ORPHAN-TP vs FORCE-CLOSE A/B BACKTEST")
    print(f"Profile: High PM | TP={PM_OVERRIDES['DCA_TP_PCT']*100:.1f}% | "
          f"Layers={PM_OVERRIDES['DCA_MAX_LAYERS']} | "
          f"Capital=${PM_OVERRIDES['CAPITAL']:,.0f}")
    print(f"Period: {PM_OVERRIDES['START_DATE']} to {PM_OVERRIDES['END_DATE']}")
    print(f"Coins: {', '.join(TEST_COINS)}")
    print("=" * 90)

    results = []
    for coin in TEST_COINS:
        print(f"\n--- {coin} ---")
        for force_close in [True, False]:
            mode = "Legacy (force-close)" if force_close else "Orphan-TP (no force-close)"
            try:
                r = run_single(coin, force_close)
                if r is None:
                    print(f"  {mode}: No data")
                    continue
                results.append(r)
                print(f"  {mode}:")
                print(f"    ROI: {r['roi']:+.1f}% | Equity: ${r['final_equity']:,.0f} | MaxDD: {r['max_drawdown']:.1f}%")
                print(f"    Trades: {r['total_trades']} (L:{r['long_trades']} W:{r['long_wins']} | S:{r['short_trades']} W:{r['short_wins']})")
                print(f"    PnL: Long ${r['long_pnl']:+,.0f} | Short ${r['short_pnl']:+,.0f}")
                print(f"    Force-closes: {r['force_closes']} | MARKDOWN_FAIL: {r['markdown_fails']}")
            except Exception as e:
                print(f"  {mode}: ERROR - {e}")
                import traceback; traceback.print_exc()

    # Summary comparison
    print("\n" + "=" * 90)
    print("SUMMARY COMPARISON")
    print("=" * 90)
    print(f"{'Coin':<15} {'Legacy ROI':>12} {'Orphan ROI':>12} {'Delta':>10} {'Legacy DD':>10} {'Orphan DD':>10} {'DD Delta':>10} {'FC#':>5} {'MF#':>5}")
    print("-" * 90)

    total_legacy_roi = 0
    total_orphan_roi = 0

    for coin in TEST_COINS:
        legacy = next((r for r in results if r['coin'] == coin and r['mode'] == 'legacy'), None)
        orphan = next((r for r in results if r['coin'] == coin and r['mode'] == 'orphan-tp'), None)
        if not legacy or not orphan:
            continue

        delta_roi = orphan['roi'] - legacy['roi']
        delta_dd = orphan['max_drawdown'] - legacy['max_drawdown']
        total_legacy_roi += legacy['roi']
        total_orphan_roi += orphan['roi']

        print(f"{coin:<15} {legacy['roi']:>+11.1f}% {orphan['roi']:>+11.1f}% {delta_roi:>+9.1f}% "
              f"{legacy['max_drawdown']:>9.1f}% {orphan['max_drawdown']:>9.1f}% {delta_dd:>+9.1f}% "
              f"{legacy['force_closes']:>5} {legacy['markdown_fails']:>5}")

    n = len(TEST_COINS)
    if n > 0:
        print("-" * 90)
        print(f"{'AVG':<15} {total_legacy_roi/n:>+11.1f}% {total_orphan_roi/n:>+11.1f}% "
              f"{(total_orphan_roi-total_legacy_roi)/n:>+9.1f}%")

    # Save results
    out_path = Path('trading/spot/backtest_results/orphan_tp_comparison.json')
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    print(f"\nResults saved to {out_path}")


if __name__ == '__main__':
    main()
