"""Replicate backfill_direct step by step."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from v13_phase_backtest_v8 import V13BacktestV8, V13Config
from v13_signals import V13SignalPack
from v13_lifecycle_engine_v2 import V13LifecycleEngineV2, V13Config as WCfg

# Step 1: Create wrapper (exactly like paper bot)
w_cfg = WCfg.from_profile('high', capital=2500)
wrapper = V13LifecycleEngineV2(symbol='XRP/USDC', capital=2500, config=w_cfg)
eng = wrapper._engine

# Step 2: What backfill_direct does
eng.cfg.START_DATE = '2024-10-01'
eng.cfg.END_DATE = '2026-02-27'

# Step 3: run()
result = eng.run()
print(f"Via wrapper engine: equity=${result['final_equity']:,.1f}, trades={len(eng.trades)}")

# Step 4: Compare with fresh engine
cfg = V13Config()
cfg.CAPITAL = 2500
cfg.START_DATE = '2024-10-01'
cfg.END_DATE = '2026-02-27'
pack = V13SignalPack('XRP/USDC')
eng2 = V13BacktestV8(pack, cfg)
r2 = eng2.run()
print(f"Fresh engine:       equity=${r2['final_equity']:,.1f}, trades={len(eng2.trades)}")

# Check engine state before run
print(f"\nWrapper engine pack.coin = {wrapper._engine.coin}")
print(f"Fresh engine pack.coin = {eng2.coin}")
print(f"Wrapper engine pack is eng.pack: {wrapper._engine.pack is eng.pack}")
