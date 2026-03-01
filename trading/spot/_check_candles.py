import sqlite3
db = sqlite3.connect('C:/Users/Never/.openclaw/workspace/trading/spot/data/candles.db')
cur = db.execute("SELECT symbol, COUNT(*) FROM candles WHERE timeframe='1h' GROUP BY symbol ORDER BY symbol")
for r in cur.fetchall():
    print(r)
