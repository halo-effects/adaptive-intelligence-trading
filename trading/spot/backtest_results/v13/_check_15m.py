import sqlite3
from datetime import datetime
conn = sqlite3.connect(r'C:\Users\Never\.openclaw\workspace\trading\spot\data\candles.db')
c = conn.cursor()
c.execute("SELECT symbol, timeframe, COUNT(*), MIN(timestamp), MAX(timestamp) FROM candles WHERE timeframe IN ('15m','5m') GROUP BY symbol, timeframe ORDER BY symbol, timeframe")
rows = c.fetchall()
if not rows:
    print("No 15m/5m data found")
for r in rows:
    mn = datetime.utcfromtimestamp(r[3]/1000).strftime('%Y-%m-%d') if isinstance(r[3], (int,float)) else str(r[3])[:10]
    mx = datetime.utcfromtimestamp(r[4]/1000).strftime('%Y-%m-%d') if isinstance(r[4], (int,float)) else str(r[4])[:10]
    print(f'{r[0]:15} {r[1]:4} {r[2]:>8} rows  {mn}..{mx}')
conn.close()
