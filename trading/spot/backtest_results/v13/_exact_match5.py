"""Test backfill_direct specifically."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from v13_lifecycle_engine_v2 import V13LifecycleEngineV2, V13Config as WCfg

# Create wrapper exactly like paper bot does
w_cfg = WCfg.from_profile('high', capital=2500)
wrapper = V13LifecycleEngineV2(symbol='XRP/USDC', capital=2500, config=w_cfg)

# Check config BEFORE backfill_direct
eng = wrapper._engine
print(f"Before backfill_direct:")
print(f"  cfg.START_DATE = {eng.cfg.START_DATE}")
print(f"  cfg.END_DATE = {eng.cfg.END_DATE}")
print(f"  cfg.CAPITAL = {eng.cfg.CAPITAL}")

# Run backfill_direct
actions = wrapper.backfill_direct('2024-10-01', '2026-02-27')

print(f"\nAfter backfill_direct:")
print(f"  trades = {len(eng.trades)}")
print(f"  capital = ${eng.capital:,.1f}")

# Check if the issue is that run() already ran during __init__
print(f"\n  phase_log entries = {len(eng.phase_log)}")
