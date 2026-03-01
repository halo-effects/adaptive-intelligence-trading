import sqlite3
DB = r"C:\Users\Never\.openclaw\workspace\trading\spot\data\candles.db"
conn = sqlite3.connect(DB)
cur = conn.execute("PRAGMA table_info(candles_daily)")
print("candles_daily columns:", [r[1] for r in cur.fetchall()])
cur = conn.execute("SELECT symbol, timestamp, open, high, low, close, volume FROM candles_daily WHERE symbol LIKE 'ETH%' ORDER BY timestamp DESC LIMIT 5")
for r in cur.fetchall():
    print(r)
print()
# Check 1h candles too
cur = conn.execute("PRAGMA table_info(candles)")
print("candles columns:", [r[1] for r in cur.fetchall()])
cur = conn.execute("SELECT symbol, timestamp, volume FROM candles WHERE symbol LIKE 'ETH%' ORDER BY timestamp DESC LIMIT 3")
for r in cur.fetchall():
    print(r)
conn.close()
