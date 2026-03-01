"""Inspect XRP trades to find failed markdown impact."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from v13_phase_backtest_v8 import V13BacktestV8, V13Config, Phase
from v13_signals import V13SignalPack

DB = r'C:\Users\Never\.openclaw\workspace\trading\spot\data\candles.db'

cfg = V13Config()
cfg.CAPITAL = 2500
cfg.START_DATE = '2023-01-01'
cfg.END_DATE = '2026-02-27'
cfg.TIER1_PCT = 0.60; cfg.TIER2_PCT = 0.20; cfg.TIER3_PCT = 0.10
cfg.SHORT_TIER1_PCT = 0.60; cfg.SHORT_TIER2_PCT = 0.20; cfg.SHORT_TIER3_PCT = 0.10
cfg.SHORTS_ENABLED = True

pack = V13SignalPack('XRP/USDC', db_path=DB)
e = V13BacktestV8(pack, cfg)
r = e.run()

print("XRP ALL TRADES:")
for t in e.trades:
    action = t.get('action', '')
    pnl = t.get('pnl_pct', None)
    price = t.get('price', 0)
    amt = t.get('amount', 0)
    phase = t.get('phase', '')
    if hasattr(phase, 'name'):
        phase = phase.name
    pnl_str = f"pnl={pnl:+.1f}%" if pnl is not None else ""
    dt = str(t['date'])[:10]
    print(f"  {dt}  {action:<45} price={price:.4f}  amt=${amt:>8.1f}  {phase:<12} {pnl_str}")

print(f"\nTotal ROI: {r['roi']:+.1f}%  Final equity: ${r['final_equity']:.0f}")
print(f"DCA PnL: ${e.dca_pnl:.1f} ({e.dca_trades} trades)")
print(f"Markup cycles: {r['markup_cycles']}")

# Phase equity changes
print("\nPHASE EQUITY TIMELINE:")
for p in e.phase_log:
    fr = p.get('from', '-')
    to = p.get('to', '-')
    if hasattr(fr, 'name'): fr = fr.name
    if hasattr(to, 'name'): to = to.name
    eq = p.get('equity', 0)
    reason = p.get('reason', '')
    dt = str(p['date'])[:10]
    print(f"  {dt}  {str(fr):>12} -> {str(to):<12} eq=${eq:>8.0f}  {reason}")
