"""Compare wrapper (v13_lifecycle_engine_v2) vs standalone (v13_phase_backtest_v8) 
trade-for-trade for each coin. Uses EXACTLY the same code paths as the paper bot."""
import sys, sqlite3
from pathlib import Path
import pandas as pd
import numpy as np

# Add paths
V13_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(V13_DIR))
TRADING_DIR = V13_DIR.parent.parent  # trading/spot/..  -> trading/
sys.path.insert(0, str(TRADING_DIR))

from v13_phase_backtest_v8 import V13BacktestV8, V13Config, Phase
from v13_signals import V13SignalPack

# Import wrapper
sys.path.insert(0, str(TRADING_DIR / 'spot'))
from v13_lifecycle_engine_v2 import V13LifecycleEngineV2, V13Config as WrapperConfig

DB = r'C:\Users\Never\.openclaw\workspace\trading\spot\data\candles.db'
START = '2024-10-01'
END = '2026-02-27'
COINS = ['ETH/USDC', 'SOL/USDC', 'LINK/USDC', 'XRP/USDC']

# DB symbol mapping (same as run_v13_paper.py)
DB_MAP = {
    'ETH/USDC': 'ETH/USDT', 'SOL/USDC': 'SOL/USDT',
    'LINK/USDC': 'LINK/USDT', 'XRP/USDC': 'XRP/USDT',
}

def load_hourly(symbol_db, start_date):
    """Load 1h candles from DB, same as paper bot."""
    from datetime import datetime, timezone
    start_dt = datetime.strptime(start_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    start_ms = int(start_dt.timestamp() * 1000)
    
    conn = sqlite3.connect(DB)
    df = pd.read_sql_query(
        "SELECT timestamp as timestamp_ms, open, high, low, close, volume FROM candles "
        "WHERE symbol=? AND timeframe='1h' AND timestamp>=? ORDER BY timestamp",
        conn, params=(symbol_db, start_ms)
    )
    conn.close()
    if df.empty:
        return df
    df.index = pd.to_datetime(df['timestamp_ms'], unit='ms', utc=True)
    return df

def load_daily(symbol_db):
    """Load daily candles from DB, same as paper bot."""
    conn = sqlite3.connect(DB)
    df = pd.read_sql_query(
        "SELECT timestamp as timestamp_ms, open, high, low, close, volume FROM candles_daily "
        "WHERE symbol=? ORDER BY timestamp",
        conn, params=(symbol_db,)
    )
    conn.close()
    if df.empty:
        return df
    df.index = pd.to_datetime(df['timestamp_ms'], unit='ms', utc=True)
    return df

for coin in COINS:
    short = coin.split('/')[0]
    db_sym = DB_MAP[coin]
    print(f"\n{'='*100}")
    print(f"  {coin}")
    print(f"{'='*100}")
    
    # ---- STANDALONE BACKTEST ----
    cfg = V13Config()
    cfg.CAPITAL = 2500
    cfg.START_DATE = START
    cfg.END_DATE = END
    cfg.TIER1_PCT = 0.60; cfg.TIER2_PCT = 0.20; cfg.TIER3_PCT = 0.10
    cfg.SHORT_TIER1_PCT = 0.60; cfg.SHORT_TIER2_PCT = 0.20; cfg.SHORT_TIER3_PCT = 0.10
    cfg.SHORTS_ENABLED = True
    
    pack = V13SignalPack(coin, db_path=DB)
    engine = V13BacktestV8(pack, cfg)
    result = engine.run()
    
    standalone_phases = []
    for p in engine.phase_log:
        fr = p.get('from')
        to = p.get('to')
        fr_s = fr.name if hasattr(fr, 'name') else str(fr) if fr else 'None'
        to_s = to.name if hasattr(to, 'name') else str(to) if to else '?'
        standalone_phases.append((str(p['date'])[:10], fr_s, to_s, p.get('reason','')))
    
    standalone_eq = result['final_equity']
    
    # ---- WRAPPER (same as paper bot backfill) ----
    from v13_lifecycle_engine_v2 import V13Config as WCfg
    w_cfg = WCfg.from_profile('high', capital=2500)
    wrapper = V13LifecycleEngineV2(symbol=coin, capital=2500, config=w_cfg)
    
    # Use backfill_direct() — same as new paper bot backfill
    wrapper_actions = wrapper.backfill_direct(START, END)
    
    # Get wrapper phase log
    wrapper_phases = []
    if wrapper._engine:
        for p in wrapper._engine.phase_log:
            fr = p.get('from')
            to = p.get('to')
            fr_s = fr.name if hasattr(fr, 'name') else str(fr) if fr else 'None'
            to_s = to.name if hasattr(to, 'name') else str(to) if to else '?'
            wrapper_phases.append((str(p['date'])[:10], fr_s, to_s, p.get('reason','')))
        
        # Get wrapper equity from run() result
        w_eng = wrapper._engine
        wrapper_eq = w_eng.capital  # After run(), all positions closed with OPEN_END
    else:
        wrapper_eq = 0
    
    # Compare
    print(f"\n  STANDALONE: equity=${standalone_eq:,.1f}, {len(standalone_phases)} phase transitions")
    print(f"  WRAPPER:   equity=${wrapper_eq:,.1f}, {len(wrapper_phases)} phase transitions")
    print(f"  DELTA:     ${wrapper_eq - standalone_eq:+,.1f}")
    
    print(f"\n  PHASE COMPARISON:")
    max_p = max(len(standalone_phases), len(wrapper_phases))
    for i in range(max_p):
        sp = standalone_phases[i] if i < len(standalone_phases) else ('', '', '', '')
        wp = wrapper_phases[i] if i < len(wrapper_phases) else ('', '', '', '')
        match = 'MATCH' if sp[:3] == wp[:3] else 'DIFF'
        print(f"    {i+1:>2}  S: {sp[0]:>12} {sp[1]:>12}->{sp[2]:<12}  W: {wp[0]:>12} {wp[1]:>12}->{wp[2]:<12}  [{match}]")
        if match == 'DIFF':
            print(f"        S reason: {sp[3][:70]}")
            print(f"        W reason: {wp[3][:70]}")

print(f"\n{'='*100}")
print("DONE")
