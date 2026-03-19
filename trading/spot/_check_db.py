import sqlite3
from datetime import datetime, timezone
conn = sqlite3.connect(r'C:\Users\Never\.openclaw\workspace\trading\spot\data\candles.db')
rows = conn.execute(
    "SELECT symbol, COUNT(*), MIN(timestamp), MAX(timestamp) "
    "FROM candles WHERE timeframe='1h' GROUP BY symbol ORDER BY symbol"
).fetchall()
print(f"{len(rows)} symbols in DB:")
for sym, cnt, mn, mx in rows:
    d1 = datetime.fromtimestamp(mn/1000, tz=timezone.utc).strftime('%Y-%m-%d')
    d2 = datetime.fromtimestamp(mx/1000, tz=timezone.utc).strftime('%Y-%m-%d')
    days = (mx - mn) / (1000 * 86400)
    print(f"  {sym:16s} {cnt:6d} candles  {d1} -> {d2}  ({days:.0f}d)")
conn.close()
