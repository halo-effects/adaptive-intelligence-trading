"""Fetch LINK/USDT 1h candles from Binance back to 2023-06-01."""
import ccxt
import sqlite3
import time
from datetime import datetime

DB_PATH = 'trading/spot/data/candles.db'

ex = ccxt.binance({'enableRateLimit': True})
db = sqlite3.connect(DB_PATH)

# Get earliest existing timestamp
r = db.execute("SELECT MIN(timestamp) FROM candles WHERE symbol='LINK/USDT'").fetchone()
existing_min = r[0]
print(f"Existing earliest: {datetime.fromtimestamp(existing_min/1000)}")

target_start = datetime(2023, 6, 1)
since_ms = int(target_start.timestamp() * 1000)
total = 0

while since_ms < existing_min:
    candles = ex.fetch_ohlcv('LINK/USDT', '1h', since=since_ms, limit=1000)
    if not candles:
        break
    candles = [c for c in candles if c[0] < existing_min]
    if not candles:
        break
    
    for c in candles:
        db.execute(
            "INSERT OR REPLACE INTO candles (symbol, timeframe, timestamp, open, high, low, close, volume) VALUES (?,?,?,?,?,?,?,?)",
            ('LINK/USDT', '1h', c[0], c[1], c[2], c[3], c[4], c[5]))
    db.commit()
    total += len(candles)
    print(f"  +{total} candles, latest: {datetime.fromtimestamp(candles[-1][0]/1000).date()}")
    since_ms = candles[-1][0] + 1
    if len(candles) < 1000:
        break
    time.sleep(0.3)

print(f"\nInserted {total} new candles")
r = db.execute("SELECT COUNT(*), MIN(timestamp), MAX(timestamp) FROM candles WHERE symbol='LINK/USDT'").fetchone()
print(f"Final: {r[0]} candles, {datetime.fromtimestamp(r[1]/1000).date()} -> {datetime.fromtimestamp(r[2]/1000).date()}")
db.close()
