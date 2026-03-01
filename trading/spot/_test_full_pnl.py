"""Show FULL P&L breakdown — not just DCA."""
import sys, importlib.util
sys.path.insert(0, '.')
spec = importlib.util.spec_from_file_location('pv8', 'trading/spot/backtest_results/v13/v13_phase_backtest_v8.py')
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
from trading.spot.backtest_results.v13.v13_signals import V13SignalPack

coins = ['ETH', 'SOL', 'LINK', 'XRP']
total_start = 0
total_end = 0

for coin in coins:
    pack = V13SignalPack(coin)
    cfg = mod.V13Config()
    cfg.CAPITAL = 2500
    eng = mod.V13BacktestV8(pack, cfg)
    result = eng.run()
    if result:
        closed_roi = result.get('closed_roi', 0)
        total_roi = result['roi']
        final_eq = result['final_equity']
        total_start += 2500
        total_end += final_eq
        
        # Count trade types
        buys = [t for t in eng.trades if 'BUY_T' in t.get('action','')]
        sells = [t for t in eng.trades if 'SELL_ALL' in t.get('action','')]
        shorts = [t for t in eng.trades if 'SHORT_T' in t.get('action','')]
        short_closes = [t for t in eng.trades if 'SHORT_CLOSE' in t.get('action','')]
        
        print(f"{coin}:")
        print(f"  Total ROI: {total_roi:+.1f}%  Closed ROI: {closed_roi:+.1f}%  Equity: ${final_eq:,.2f}")
        print(f"  Markup buys: {len(buys)}, Sells: {len(sells)}, Shorts opened: {len(shorts)}, Shorts closed: {len(short_closes)}")
        print(f"  DCA deals: {eng.dca_trades} (${eng.dca_pnl:.2f})")
        
        # Show closed trade P&L
        for t in eng.trades:
            if 'pnl_pct' in t:
                print(f"    {t['date'].strftime('%Y-%m-%d')} {t['action'][:40]:<40} pnl={t['pnl_pct']:+.1f}%")
        print()

portfolio_roi = (total_end - total_start) / total_start * 100
print(f"PORTFOLIO: ${total_start:,} -> ${total_end:,.2f}  ROI: {portfolio_roi:+.1f}%")
