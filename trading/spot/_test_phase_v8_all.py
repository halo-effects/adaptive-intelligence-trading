"""Run v13_phase_backtest_v8.py on all 8 coins."""
import sys, importlib.util
sys.path.insert(0, '.')
spec = importlib.util.spec_from_file_location('pv8', 'trading/spot/backtest_results/v13/v13_phase_backtest_v8.py')
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
from trading.spot.backtest_results.v13.v13_signals import V13SignalPack

coins = ['ETH', 'XRP', 'BTC', 'SOL', 'LINK', 'NEAR', 'ZEC', 'PEPE']
cfg = mod.V13Config()
per_coin = cfg.CAPITAL / len(coins)  # Equal split

total_equity = 0
total_capital = 0

for coin in coins:
    try:
        pack = V13SignalPack(coin)
        c = mod.V13Config()
        c.CAPITAL = per_coin
        eng = mod.V13BacktestV8(pack, c)
        result = eng.run()
        if result:
            closed = result.get('closed_roi', 0)
            print(f"{coin:>5}: ROI={result['roi']:>+7.1f}%  Closed={closed:>+7.1f}%  "
                  f"Equity=${result['final_equity']:>8,.2f}  Trades={len(eng.trades):>3}  "
                  f"Cycles={result.get('markup_cycles', 0)}")
            total_equity += result['final_equity']
            total_capital += per_coin
        else:
            print(f"{coin:>5}: no result")
            total_capital += per_coin
    except Exception as e:
        print(f"{coin:>5}: SKIP - {e}")
        total_capital += per_coin

if total_capital > 0:
    portfolio_roi = (total_equity - total_capital) / total_capital * 100
    print(f"\n{'='*70}")
    print(f"Portfolio: ${total_capital:,.0f} -> ${total_equity:,.2f}  ROI={portfolio_roi:+.1f}%")
