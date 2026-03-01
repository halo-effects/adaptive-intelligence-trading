"""Test: does the wrapper produce correct results if we fix the coin name?"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from v13_phase_backtest_v8 import V13BacktestV8, V13Config
from v13_signals import V13SignalPack
from v13_lifecycle_engine_v2 import V13LifecycleEngineV2, V13Config as WCfg

# Test 1: Wrapper with "XRP" coin (strips /USDC)
w_cfg1 = WCfg.from_profile('high', capital=2500)
w1 = V13LifecycleEngineV2(symbol='XRP/USDC', capital=2500, config=w_cfg1)
w1._engine.cfg.START_DATE = '2024-10-01'
w1._engine.cfg.END_DATE = '2026-02-27'
r1 = w1._engine.run()
print(f"Wrapper (coin={w1._engine.coin}): equity=${r1['final_equity']:,.1f}, trades={len(w1._engine.trades)}")

# Test 2: Manual engine with pack coin = "XRP" 
pack = V13SignalPack('XRP')  # Same as wrapper
cfg = V13Config()
cfg.CAPITAL = 2500; cfg.START_DATE = '2024-10-01'; cfg.END_DATE = '2026-02-27'
eng = V13BacktestV8(pack, cfg)
r2 = eng.run()
print(f"Manual (coin={eng.coin}): equity=${r2['final_equity']:,.1f}, trades={len(eng.trades)}")

# Test 3: Manual engine with pack coin = "XRP/USDC"
pack3 = V13SignalPack('XRP/USDC')
cfg3 = V13Config()
cfg3.CAPITAL = 2500; cfg3.START_DATE = '2024-10-01'; cfg3.END_DATE = '2026-02-27'
eng3 = V13BacktestV8(pack3, cfg3)
r3 = eng3.run()
print(f"Manual (coin={eng3.coin}): equity=${r3['final_equity']:,.1f}, trades={len(eng3.trades)}")
