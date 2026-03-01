"""List ALL trades for XRP from both engines."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from v13_phase_backtest_v8 import V13BacktestV8, V13Config
from v13_signals import V13SignalPack
from v13_lifecycle_engine_v2 import V13LifecycleEngineV2, V13Config as WCfg

DB = r'C:\Users\Never\.openclaw\workspace\trading\spot\data\candles.db'

# Standalone
cfg = V13Config()
cfg.CAPITAL = 2500
cfg.START_DATE = '2024-10-01'
cfg.END_DATE = '2026-02-27'
pack = V13SignalPack('XRP/USDC', db_path=DB)
eng1 = V13BacktestV8(pack, cfg)
r1 = eng1.run()

# Wrapper
w_cfg = WCfg.from_profile('high', capital=2500)
wrapper = V13LifecycleEngineV2(symbol='XRP/USDC', capital=2500, config=w_cfg)
actions = wrapper.backfill_direct('2024-10-01', '2026-02-27')
eng2 = wrapper._engine

print("STANDALONE TRADES:")
for i, t in enumerate(eng1.trades):
    a = t.get('action','')
    d = str(t.get('date',''))[:10]
    amt = t.get('amount',0)
    p = t.get('price',0)
    pnl = t.get('pnl_pct','')
    print(f"  {i+1:>3} {d} {a:<45} ${amt:>10.2f} @{p:.4f}  pnl={pnl}")

print(f"\nWRAPPER TRADES:")
for i, t in enumerate(eng2.trades):
    a = t.get('action','')
    d = str(t.get('date',''))[:10]
    amt = t.get('amount',0)
    p = t.get('price',0)
    pnl = t.get('pnl_pct','')
    print(f"  {i+1:>3} {d} {a:<45} ${amt:>10.2f} @{p:.4f}  pnl={pnl}")
