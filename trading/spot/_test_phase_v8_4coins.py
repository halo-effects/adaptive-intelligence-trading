"""Run v13_phase_backtest_v8 on the 4 paper bot coins with $2500 each."""
import sys, importlib.util
sys.path.insert(0, '.')
spec = importlib.util.spec_from_file_location('pv8', 'trading/spot/backtest_results/v13/v13_phase_backtest_v8.py')
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
from trading.spot.backtest_results.v13.v13_signals import V13SignalPack

coins = ['ETH', 'SOL', 'LINK', 'XRP']
total_pnl = 0
total_deals = 0

for coin in coins:
    pack = V13SignalPack(coin)
    cfg = mod.V13Config()
    cfg.CAPITAL = 2500
    eng = mod.V13BacktestV8(pack, cfg)
    result = eng.run()
    print(f"{coin}: DCA deals={eng.dca_trades}, DCA PnL=${eng.dca_pnl:.2f}, trades={len(eng.trades)}")
    for p in eng.phase_log:
        d = p['date'].strftime('%Y-%m-%d')
        print(f"  {d}  {str(p.get('from','None')):>10} -> {p['to']:<10} | {p['reason'][:60]}")
    total_pnl += eng.dca_pnl
    total_deals += eng.dca_trades
    print()

print(f"Total DCA PnL: ${total_pnl:.2f}, Total deals: {total_deals}")
