import sqlite3
from pathlib import Path
DB = Path(__file__).parent.parent.parent / 'data' / 'candles.db'
conn = sqlite3.connect(DB)

# Check what timeframes exist
tfs = conn.execute("SELECT DISTINCT timeframe FROM candles LIMIT 20").fetchall()
print("Timeframes:", [t[0] for t in tfs])

for sym in ['ETH/USDC','ETH/USDT','BTC/USDC','BTC/USDT','SOL/USDC','SOL/USDT']:
    for tf in ['1h','15m','5m']:
        r = conn.execute('SELECT COUNT(*), MIN(timestamp), MAX(timestamp) FROM candles WHERE symbol=? AND timeframe=?', (sym,tf)).fetchone()
        if r[0] > 0:
            from datetime import datetime
            mn = datetime.fromtimestamp(r[1]/1000).strftime('%Y-%m-%d') if r[1] else '?'
            mx = datetime.fromtimestamp(r[2]/1000).strftime('%Y-%m-%d') if r[2] else '?'
            print(f'{sym} {tf}: {r[0]:,} candles, {mn} to {mx}')
