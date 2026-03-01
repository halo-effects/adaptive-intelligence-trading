"""Compare V13Config between standalone and wrapper."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from v13_phase_backtest_v8 import V13Config
from v13_lifecycle_engine_v2 import V13Config as WrapperConfig

# Standalone config (same as _paperbot_compare.py)
s = V13Config()
s.CAPITAL = 2500
s.START_DATE = '2024-10-01'
s.END_DATE = '2026-02-27'
s.TIER1_PCT = 0.60; s.TIER2_PCT = 0.20; s.TIER3_PCT = 0.10
s.SHORT_TIER1_PCT = 0.60; s.SHORT_TIER2_PCT = 0.20; s.SHORT_TIER3_PCT = 0.10
s.SHORTS_ENABLED = True

# Wrapper config (same as paper bot)
w = WrapperConfig.from_profile('high', capital=2500)

# Compare all attributes
s_attrs = {k: v for k, v in vars(s).items() if not k.startswith('_')}
w_attrs = {k: v for k, v in vars(w).items() if not k.startswith('_')}

all_keys = sorted(set(list(s_attrs.keys()) + list(w_attrs.keys())))

print(f"{'Attribute':<30} {'Standalone':>15} {'Wrapper':>15} {'Match':>8}")
print("-" * 70)
for k in all_keys:
    sv = s_attrs.get(k, 'MISSING')
    wv = w_attrs.get(k, 'MISSING')
    match = 'YES' if sv == wv else 'NO'
    print(f"{k:<30} {str(sv):>15} {str(wv):>15} {match:>8}")
