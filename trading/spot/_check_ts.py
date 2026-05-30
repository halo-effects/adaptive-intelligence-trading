import sqlite3
conn = sqlite3.connect("trading/spot/data/candles.db")
row = conn.execute("SELECT timestamp FROM candles WHERE symbol='GRASS/USDT' AND timeframe='1h' LIMIT 3").fetchall()
for r in row:
    print(f"  timestamp: {r[0]} (type={type(r[0]).__name__})")
conn.close()
