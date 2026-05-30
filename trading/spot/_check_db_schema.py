import sqlite3
from pathlib import Path

db = Path('trading/spot/data/candles.db')
conn = sqlite3.connect(db)
cur = conn.cursor()
cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
print("Tables:", cur.fetchall())

cur.execute("SELECT DISTINCT symbol FROM candles ORDER BY symbol")
syms = [r[0] for r in cur.fetchall()]
print(f"{len(syms)} symbols: {syms}")

cur.execute("SELECT MIN(timestamp), MAX(timestamp) FROM candles")
print("Range:", cur.fetchone())
conn.close()
