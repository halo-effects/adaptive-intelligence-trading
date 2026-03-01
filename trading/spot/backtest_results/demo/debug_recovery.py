"""Quick debug: check what phase transitions happen with recovery override."""
import sys, sqlite3, pandas as pd, os, logging
from pathlib import Path
os.chdir(r'C:\Users\Never\.openclaw\workspace')
sys.path.insert(0, r'C:\Users\Never\.openclaw\workspace')
logging.basicConfig(level=logging.WARNING)

from trading.spot.backtest_engine_consolidated import SpotBacktestEngineV12

DB_PATH = Path('trading/spot/data/candles.db')

TEST_CASES = [
    ("ETH/USDC", "2024-06-01", "2024-10-01"),
    ("ETH/USDT", "2024-12-01", "2025-03-01"),
    ("SOL/USDC", "2024-02-01", "2024-07-01"),
    ("SOL/USDT", "2024-12-01", "2025-03-01"),
    ("BTC/USDC", "2024-10-01", "2025-03-01"),
]

for symbol, start, end in TEST_CASES:
    conn = sqlite3.connect(str(DB_PATH))
    start_ts = int(pd.Timestamp(start).timestamp() * 1000)
    end_ts = int(pd.Timestamp(end).timestamp() * 1000)
    
    warmup_df = pd.read_sql_query(
        'SELECT timestamp, open, high, low, close, volume FROM candles '
        'WHERE symbol=? AND timestamp<? ORDER BY timestamp DESC LIMIT 2500',
        conn, params=(symbol, start_ts))
    warmup_df = warmup_df.sort_values('timestamp').reset_index(drop=True)
    forward_df = pd.read_sql_query(
        'SELECT timestamp, open, high, low, close, volume FROM candles '
        'WHERE symbol=? AND timestamp>=? AND timestamp<=? ORDER BY timestamp',
        conn, params=(symbol, start_ts, end_ts))
    conn.close()
    
    full_df = pd.concat([warmup_df, forward_df]).reset_index(drop=True)
    for col in ['open','high','low','close','volume']:
        full_df[col] = pd.to_numeric(full_df[col], errors='coerce')
    full_df['timestamp'] = full_df['timestamp'].astype(int)

    engine = SpotBacktestEngineV12(
        symbol=symbol, timeframe='1h', capital=10000, profile='high',
        exchange='binance', v12f_gates=True, v12f_markdown_exit=True)
    result = engine.run(full_df)

    # Extract phase transitions from timeline
    timeline = engine._candle_timeline
    phases = [(t['timestamp'], t['lifecycle']) for t in timeline]
    transitions = []
    for i in range(1, len(phases)):
        if phases[i][1] != phases[i-1][1]:
            transitions.append((phases[i][0], phases[i-1][1], phases[i][1]))

    print(f"\n{'='*60}")
    print(f"{symbol} | {start} -> {end} | Return: {result.total_return_pct:+.2f}%")
    print(f"Phase transitions:")
    for ts, frm, to in transitions:
        dt = pd.Timestamp(ts, unit='ms') if isinstance(ts, (int, float)) else ts
        print(f"  {dt}: {frm} -> {to}")
    
    state = engine.snapshot_state()
    print(f"Recovery candles at end: {state.get('v12_markdown_recovery_candles', 'N/A')}")
    print(f"Exit cooldown remaining: {engine._exit_cooldown_candles}")
