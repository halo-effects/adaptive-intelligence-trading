"""Dump ALL config attrs before run() for both engines."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from v13_phase_backtest_v8 import V13BacktestV8, V13Config
from v13_signals import V13SignalPack
from v13_lifecycle_engine_v2 import V13LifecycleEngineV2, V13Config as WCfg

DB = r'C:\Users\Never\.openclaw\workspace\trading\spot\data\candles.db'

# Standalone config
s_cfg = V13Config()
s_cfg.CAPITAL = 2500
s_cfg.START_DATE = '2024-10-01'
s_cfg.END_DATE = '2026-02-27'

# Wrapper config (via from_profile)
w_cfg = WCfg.from_profile('high', capital=2500)
w_cfg.START_DATE = '2024-10-01'
w_cfg.END_DATE = '2026-02-27'

# Get ALL attributes from both
s_attrs = {}
w_attrs = {}
for k in dir(s_cfg):
    if not k.startswith('_'):
        s_attrs[k] = getattr(s_cfg, k)
for k in dir(w_cfg):
    if not k.startswith('_'):
        w_attrs[k] = getattr(w_cfg, k)

all_keys = sorted(set(list(s_attrs.keys()) + list(w_attrs.keys())))
diffs = []
for k in all_keys:
    sv = s_attrs.get(k, 'MISSING')
    wv = w_attrs.get(k, 'MISSING')
    if callable(sv):
        continue
    match = sv == wv
    if not match:
        diffs.append(k)
    print(f"{'*' if not match else ' '} {k:<35} S={str(sv):>15}  W={str(wv):>15}")

if diffs:
    print(f"\n*** DIFFS: {diffs}")
else:
    print(f"\n*** ALL CONFIG VALUES IDENTICAL ***")

# Now run both with SAME pack
pack = V13SignalPack('XRP/USDC', db_path=DB)

e1 = V13BacktestV8(pack, s_cfg)
r1 = e1.run()
print(f"\nStandalone: equity=${r1['final_equity']:,.1f}, trades={len(e1.trades)}")

# Re-create pack for wrapper (separate instance)
pack2 = V13SignalPack('XRP/USDC', db_path=DB)
e2 = V13BacktestV8(pack2, w_cfg)
r2 = e2.run()
print(f"Wrapper cfg: equity=${r2['final_equity']:,.1f}, trades={len(e2.trades)}")

# Now try SHARING the same pack
e3 = V13BacktestV8(pack, s_cfg)
# Oops, e1 already modified pack? Let's check
pack3 = V13SignalPack('XRP/USDC', db_path=DB)
s_cfg2 = V13Config()
s_cfg2.CAPITAL = 2500
s_cfg2.START_DATE = '2024-10-01'
s_cfg2.END_DATE = '2026-02-27'
e3 = V13BacktestV8(pack3, s_cfg2)
r3 = e3.run()
print(f"Standalone2: equity=${r3['final_equity']:,.1f}, trades={len(e3.trades)}")
