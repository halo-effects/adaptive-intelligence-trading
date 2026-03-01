import sqlite3
from datetime import datetime
c = sqlite3.connect('trading/spot/data/candles.db')
r = c.execute("SELECT COUNT(*), MIN(timestamp), MAX(timestamp) FROM candles WHERE symbol='LINK/USDT'").fetchone()
print(f"Count: {r[0]}")
if r[0] > 0:
    print(f"Range: {datetime.fromtimestamp(r[1]/1000)} -> {datetime.fromtimestamp(r[2]/1000)}")
# Check if the early ones got in
r2 = c.execute("SELECT COUNT(*) FROM candles WHERE symbol='LINK/USDT' AND timestamp < 1708000000000").fetchone()
print(f"Before Feb 2024: {r2[0]}")
c.close()
