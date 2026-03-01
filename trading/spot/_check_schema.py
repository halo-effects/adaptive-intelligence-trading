import sqlite3
c = sqlite3.connect('trading/spot/data/candles.db')
r = c.execute("SELECT sql FROM sqlite_master WHERE name='candles'").fetchone()
print(r[0])
c.close()
