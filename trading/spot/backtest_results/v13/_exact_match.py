"""Run EXACT same code twice and verify results match."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from v13_phase_backtest_v8 import V13BacktestV8, V13Config
from v13_signals import V13SignalPack

DB = r'C:\Users\Never\.openclaw\workspace\trading\spot\data\candles.db'

cfg1 = V13Config()
cfg1.CAPITAL = 2500
cfg1.START_DATE = '2024-10-01'
cfg1.END_DATE = '2026-02-27'

cfg2 = V13Config()
cfg2.CAPITAL = 2500
cfg2.START_DATE = '2024-10-01'
cfg2.END_DATE = '2026-02-27'

for coin in ['ETH/USDC', 'SOL/USDC', 'LINK/USDC', 'XRP/USDC']:
    pack1 = V13SignalPack(coin, db_path=DB)
    pack2 = V13SignalPack(coin, db_path=DB)
    
    e1 = V13BacktestV8(pack1, cfg1)
    e2 = V13BacktestV8(pack2, cfg2)
    
    r1 = e1.run()
    r2 = e2.run()
    
    eq1 = r1['final_equity']
    eq2 = r2['final_equity']
    trades1 = len(e1.trades)
    trades2 = len(e2.trades)
    
    match = 'MATCH' if abs(eq1 - eq2) < 0.01 else 'DIFF'
    print(f"{coin}: eq1=${eq1:,.1f} eq2=${eq2:,.1f} trades={trades1}/{trades2} [{match}]")
