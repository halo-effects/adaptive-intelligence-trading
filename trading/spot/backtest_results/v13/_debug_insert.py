import sqlite3, ccxt
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "candles.db"
print(f"DB: {DB_PATH}")

db = sqlite3.connect(str(DB_PATH))

# Check table schema
schema = db.execute("SELECT sql FROM sqlite_master WHERE name='candles'").fetchone()
print(f"Schema: {schema[0]}")

# Try inserting one PEPE candle manually
ex = ccxt.binance({'enableRateLimit': True})
candles = ex.fetch_ohlcv('PEPE/USDT', '1h', limit=5)
print(f"Fetched {len(candles)} test candles")
print(f"Sample: {candles[0]}")

try:
    db.execute(
        "INSERT OR REPLACE INTO candles (symbol, timestamp, open, high, low, close, volume) VALUES (?,?,?,?,?,?,?)",
        ('PEPE/USDT', candles[0][0], candles[0][1], candles[0][2], candles[0][3], candles[0][4], candles[0][5])
    )
    db.commit()
    print("INSERT succeeded")
except Exception as e:
    print(f"INSERT failed: {e}")

r = db.execute("SELECT COUNT(*) FROM candles WHERE symbol='PEPE/USDT'").fetchone()
print(f"PEPE/USDT count after insert: {r[0]}")

db.close()
