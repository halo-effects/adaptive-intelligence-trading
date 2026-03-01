import sqlite3
from datetime import datetime
c = sqlite3.connect('trading/spot/data/candles.db')
r = c.execute("SELECT symbol, COUNT(*), MIN(timestamp), MAX(timestamp) FROM candles WHERE symbol LIKE 'LINK%' GROUP BY symbol").fetchall()
for sym, count, mn, mx in r:
    print(f"{sym}: {count} candles, {datetime.fromtimestamp(mn/1000).date()} -> {datetime.fromtimestamp(mx/1000).date()}")
r2 = c.execute("SELECT symbol, COUNT(*) FROM candles_daily WHERE symbol LIKE 'LINK%' GROUP BY symbol").fetchall()
print(f"\nDaily: {r2}")
c.close()
