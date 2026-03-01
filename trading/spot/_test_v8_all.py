"""Run v8 backtest on all 4 coins and print summary."""
import sys
sys.path.insert(0, '.')
from trading.spot.backtest_results.v13.v13_backtest_v8 import V13BacktestV8, V8Config
from trading.spot.backtest_results.v13.v13_signals import V13SignalPack

coins = ['ETH', 'SOL', 'LINK', 'XRP']
total_pnl = 0
total_deals = 0

for coin in coins:
    pack = V13SignalPack(coin)
    cfg = V8Config()
    cfg.CAPITAL = 2500
    eng = V13BacktestV8(pack, cfg)
    result = eng.run()
    roi = result['roi'] if result else 0
    eq = result['final_equity'] if result else 2500
    print(f"{coin}: DCA deals={eng.dca_trades}, DCA PnL=${eng.dca_total_pnl:.2f}, "
          f"trades={len(eng.trades)}, ROI={roi:.1f}%, equity=${eq:.2f}")
    total_pnl += eng.dca_total_pnl
    total_deals += eng.dca_trades

print(f"\nTotal DCA PnL: ${total_pnl:.2f}, Total deals: {total_deals}")
