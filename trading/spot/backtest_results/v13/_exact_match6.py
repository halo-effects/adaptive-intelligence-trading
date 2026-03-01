"""Monkey-patch run() to check config."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from v13_phase_backtest_v8 import V13BacktestV8
from v13_lifecycle_engine_v2 import V13LifecycleEngineV2, V13Config as WCfg

# Monkey-patch run() to print config
_orig_run = V13BacktestV8.run
def patched_run(self):
    print(f"  [run() called] START={self.cfg.START_DATE} END={self.cfg.END_DATE} CAP={self.cfg.CAPITAL}")
    print(f"  [run() called] TIER2_DELAY={self.cfg.TIER2_DELAY_WEEKS} SHORT_T2_DELAY={self.cfg.SHORT_TIER2_DELAY_WEEKS}")
    return _orig_run(self)
V13BacktestV8.run = patched_run

w_cfg = WCfg.from_profile('high', capital=2500)
wrapper = V13LifecycleEngineV2(symbol='XRP/USDC', capital=2500, config=w_cfg)
actions = wrapper.backfill_direct('2024-10-01', '2026-02-27')
eng = wrapper._engine
print(f"Result: trades={len(eng.trades)}, capital=${eng.capital:,.1f}")
