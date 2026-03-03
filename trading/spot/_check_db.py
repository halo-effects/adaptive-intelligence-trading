import sqlite3
conn = sqlite3.connect('trading/spot/data/candles.db')
cursor = conn.execute("SELECT sql FROM sqlite_master WHERE type='table'")
for r in cursor:
    print(r[0])
print("---")
cursor2 = conn.execute("SELECT symbol, COUNT(*), MIN(timestamp), MAX(timestamp) FROM candles GROUP BY symbol ORDER BY symbol")
for r in cursor2:
    print(r)
print("---")
# Sample row
cursor3 = conn.execute("SELECT * FROM candles LIMIT 3")
print([d[0] for d in cursor3.description])
for r in cursor3:
    print(r)
conn.close()
