"""Check 24h volume for scanner coins from candles.db."""
import sqlite3
from datetime import datetime, timezone, timedelta

DB = r"C:\Users\Never\.openclaw\workspace\trading\spot\data\candles.db"
conn = sqlite3.connect(DB)

# Get last 24h of 1h candles volume per coin
now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
day_ago_ms = now_ms - 24 * 3600 * 1000

rows = conn.execute("""
    SELECT symbol, 
           SUM(volume) as total_vol,
           COUNT(*) as candle_count,
           AVG(close) as avg_price,
           SUM(volume * close) as dollar_volume
    FROM candles 
    WHERE timeframe = '1h' 
      AND timestamp >= ?
    GROUP BY symbol
    ORDER BY dollar_volume ASC
""", (day_ago_ms,)).fetchall()

print(f"{'Symbol':<20} {'24h $ Vol':>15} {'Avg Price':>12} {'Candles':>8}")
print("-" * 60)
for sym, vol, count, price, dvol in rows:
    if dvol and price:
        print(f"{sym:<20} ${dvol:>14,.0f} ${price:>10.4f} {count:>8}")

conn.close()
