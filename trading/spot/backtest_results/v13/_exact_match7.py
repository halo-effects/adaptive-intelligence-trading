"""Share exact same pack between standalone and wrapper engine."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from v13_phase_backtest_v8 import V13BacktestV8, V13Config
from v13_signals import V13SignalPack

DB = r'C:\Users\Never\.openclaw\workspace\trading\spot\data\candles.db'

# One pack, two engines
pack = V13SignalPack('XRP/USDC', db_path=DB)

cfg1 = V13Config()
cfg1.CAPITAL = 2500; cfg1.START_DATE = '2024-10-01'; cfg1.END_DATE = '2026-02-27'

cfg2 = V13Config()
cfg2.CAPITAL = 2500; cfg2.START_DATE = '2024-10-01'; cfg2.END_DATE = '2026-02-27'

# Run first
e1 = V13BacktestV8(pack, cfg1)
r1 = e1.run()
print(f"First:  equity=${r1['final_equity']:,.1f}, trades={len(e1.trades)}")

# Run second with SAME pack
e2 = V13BacktestV8(pack, cfg2)
r2 = e2.run()
print(f"Second: equity=${r2['final_equity']:,.1f}, trades={len(e2.trades)}")

# Are they the same?
print(f"Match: {abs(r1['final_equity'] - r2['final_equity']) < 0.01}")
