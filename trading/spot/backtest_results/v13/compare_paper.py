"""Compare backtest engine vs live paper bot for ETH and SOL from Oct 2024."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from v13_phase_backtest_v8 import V13BacktestV8, V13Config, print_results
from v13_signals import V13SignalPack


def make_high_config():
    cfg = V13Config()
    cfg.DCA_BO_PCT = 0.05
    cfg.DCA_SO_DEVIATION = 0.02
    cfg.DCA_SO_MULTIPLIER = 2.0
    cfg.DCA_TP_PCT = 0.010
    cfg.DCA_MAX_LAYERS = 12
    cfg.CAPITAL = 2500
    cfg.START_DATE = '2024-10-01'
    cfg.END_DATE = '2026-02-26'
    return cfg


for coin in ['ETH', 'SOL']:
    print(f"\n{'='*70}")
    print(f"  BACKTEST: {coin}/USDC | High | $2,500 | Oct 2024 - Feb 2026")
    print(f"{'='*70}")
    
    cfg = make_high_config()
    pack = V13SignalPack(coin)
    bt = V13BacktestV8(pack, cfg)
    r = bt.run()
    
    if r:
        print_results(r)
        print(f"\n  KEY METRICS:")
        print(f"  ROI: {r['roi']:+.1f}%  Closed ROI: {r['closed_roi']:+.1f}%")
        print(f"  Final equity: ${r['final_equity']:,.2f}")
        print(f"  Markup PnL: ${r.get('markup_pnl',0):,.2f}")
        print(f"  DCA PnL: ${r.get('dca_pnl',0):,.2f}")
        print(f"  Short PnL: ${r.get('short_pnl',0):,.2f}")
        print(f"  B&H: {r['buy_hold_return']:+.1f}%")
