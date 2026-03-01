"""Compare standalone run() vs wrapper.backfill_direct() equity."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from v13_phase_backtest_v8 import V13BacktestV8, V13Config
from v13_signals import V13SignalPack
from v13_lifecycle_engine_v2 import V13LifecycleEngineV2, V13Config as WCfg

DB = r'C:\Users\Never\.openclaw\workspace\trading\spot\data\candles.db'

for coin in ['XRP/USDC']:
    # Standalone
    cfg = V13Config()
    cfg.CAPITAL = 2500
    cfg.START_DATE = '2024-10-01'
    cfg.END_DATE = '2026-02-27'
    pack = V13SignalPack(coin, db_path=DB)
    eng = V13BacktestV8(pack, cfg)
    r = eng.run()
    print(f"STANDALONE: equity=${r['final_equity']:,.1f}, capital=${eng.capital:,.1f}, trades={len(eng.trades)}")
    print(f"  pos_coins={eng.position_coins}, dca_coins={eng.dca_coins}, short_coins={eng.short_coins:.4f}")
    
    # Wrapper backfill_direct
    w_cfg = WCfg.from_profile('high', capital=2500)
    wrapper = V13LifecycleEngineV2(symbol=coin, capital=2500, config=w_cfg)
    actions = wrapper.backfill_direct('2024-10-01', '2026-02-27')
    w_eng = wrapper._engine
    print(f"WRAPPER:    equity=N/A (need _results), capital=${w_eng.capital:,.1f}, trades={len(w_eng.trades)}")
    print(f"  pos_coins={w_eng.position_coins}, dca_coins={w_eng.dca_coins}, short_coins={w_eng.short_coins:.4f}")
    
    # Check if they ran the same code
    print(f"\n  Trade count: standalone={len(eng.trades)}, wrapper={len(w_eng.trades)}")
    
    # Compare first 5 and last 5 trades
    print(f"\n  FIRST 5 TRADES:")
    for i in range(min(5, len(eng.trades))):
        st = eng.trades[i]
        wt = w_eng.trades[i]
        s_act = st.get('action','')[:30]
        w_act = wt.get('action','')[:30]
        s_amt = st.get('amount',0)
        w_amt = wt.get('amount',0)
        match = 'OK' if abs(s_amt - w_amt) < 0.01 else 'DIFF'
        print(f"    S: {s_act:<30} ${s_amt:>10.2f}   W: {w_act:<30} ${w_amt:>10.2f}  [{match}]")
    
    print(f"\n  LAST 5 TRADES:")
    for i in range(-5, 0):
        st = eng.trades[i]
        wt = w_eng.trades[i]
        s_act = st.get('action','')[:30]
        w_act = wt.get('action','')[:30]
        s_amt = st.get('amount',0)
        w_amt = wt.get('amount',0)
        match = 'OK' if abs(s_amt - w_amt) < 0.01 else 'DIFF'
        print(f"    S: {s_act:<30} ${s_amt:>10.2f}   W: {w_act:<30} ${w_amt:>10.2f}  [{match}]")
