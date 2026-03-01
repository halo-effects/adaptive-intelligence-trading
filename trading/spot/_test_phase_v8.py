"""Run v13_phase_backtest_v8.py on all 4 coins."""
import sys, importlib.util
sys.path.insert(0, '.')
spec = importlib.util.spec_from_file_location('pv8', 'trading/spot/backtest_results/v13/v13_phase_backtest_v8.py')
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
from trading.spot.backtest_results.v13.v13_signals import V13SignalPack

coins = ['ETH', 'SOL', 'LINK', 'XRP']
cfg = mod.V13Config()
cfg.CAPITAL = 2500

for coin in coins:
    try:
        pack = V13SignalPack(coin)
        eng = mod.V13BacktestV8(pack, cfg)
        result = eng.run()
        if result:
            print(f"{coin}: ROI={result['roi']:.1f}%, closed_ROI={result.get('closed_roi', 'N/A')}%, "
                  f"equity=${result['final_equity']:.2f}, trades={len(eng.trades)}")
        else:
            print(f"{coin}: no result")
    except Exception as e:
        print(f"{coin}: ERROR - {e}")
