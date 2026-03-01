import sqlite3
from pathlib import Path
DB = Path(r'C:\Users\Never\.openclaw\workspace\trading\spot\data\candles.db')
conn = sqlite3.connect(DB)
for sym in ['LINK/USDC','LINK/USDT','XRP/USDC','XRP/USDT']:
    r = conn.execute('SELECT COUNT(*), MIN(timestamp), MAX(timestamp) FROM candles_daily WHERE symbol=? AND timestamp IS NOT NULL AND timestamp > 0', (sym,)).fetchone()
    rng = (r[2] - r[1]) if r[1] and r[2] else 0
    print(f'{sym}: valid={r[0]}, min={r[1]}, max={r[2]}, range={rng}')
conn.close()
