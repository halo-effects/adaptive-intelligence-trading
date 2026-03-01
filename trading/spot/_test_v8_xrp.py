"""Quick test: run v8 backtest on XRP and print phase log."""
import sys
sys.path.insert(0, '.')
from trading.spot.backtest_results.v13.v13_backtest_v8 import V13BacktestV8, V8Config
from trading.spot.backtest_results.v13.v13_signals import V13SignalPack

pack = V13SignalPack('XRP')
cfg = V8Config()
cfg.CAPITAL = 2500
eng = V13BacktestV8(pack, cfg)
result = eng.run()

print("=== XRP Phase Log ===")
for p in eng.phase_log:
    d = p['date'].strftime('%Y-%m-%d')
    f = str(p.get('from', 'None'))
    t = p['to']
    r = p['reason']
    print(f"  {d}  {f:>10} -> {t:<10} | {r}")

print(f"\nDCA deals: {eng.dca_trades}, DCA PnL: ${eng.dca_total_pnl:.2f}")
print(f"Total trades: {len(eng.trades)}")
if result:
    print(f"ROI: {result['roi']:.1f}%, Final equity: ${result['final_equity']:.2f}")
