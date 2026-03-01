"""Compare current results against Run 4 expected values.
Run 4 used START_DATE=2024-10-01 (cfg default).

Run 4 results (from session):
ETH High: +284%, Short P&L: +$5,757
BTC High: +167%, Short P&L: -$164  
SOL High: +54%, Short P&L: +$3,365

Current results: ETH ~58%, BTC ~34%, SOL ~145%
"""
from v13_phase_backtest_v8 import V13BacktestV8, V13Config
from v13_signals import V13SignalPack
from run_new_coins_profiles import make_config

for coin in ['ETH/USDC', 'BTC/USDC', 'SOL/USDC']:
    pack = V13SignalPack(coin)
    cfg = make_config('high')
    print(f"\n{coin} — START={cfg.START_DATE}, END={cfg.END_DATE}")
    bt = V13BacktestV8(pack, cfg)
    r = bt.run()
    
    print(f"  ROI: {r['roi']:.1f}%, Closed: {r['closed_roi']:.1f}%, Equity: ${r['final_equity']:.0f}")
    print(f"  Markup cycles: {r['markup_cycles']}, Trades: {r['closed_trades']} ({r['wins']}W/{r['losses']}L)")
    
    # Dump phase transitions with equity
    for t in bt.phase_log:
        d = t.get('date', '')
        reason = t.get('reason', t.get('note', ''))
        eq = t.get('equity', 0)
        phase = t.get('to', t.get('phase', ''))
        print(f"    {str(d)[:10]} ${eq:>8.0f} -> {phase}: {reason}")
