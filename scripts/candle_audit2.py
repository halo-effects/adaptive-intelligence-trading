import sqlite3
from datetime import datetime, timezone

conn = sqlite3.connect('trading/spot/data/candles.db')
cur = conn.cursor()

# Check timeframe distribution
print("=== Timeframe breakdown ===")
cur.execute("SELECT timeframe, COUNT(*) FROM candles GROUP BY timeframe ORDER BY COUNT(*) DESC")
for row in cur.fetchall():
    print(f"  {row[0]}: {row[1]:,} candles")

# Check candles_daily table
print("\n=== candles_daily table ===")
cur.execute("PRAGMA table_info(candles_daily)")
schema = cur.fetchall()
print(f"Schema: {[(s[1], s[2]) for s in schema]}")
cur.execute("SELECT COUNT(*) FROM candles_daily")
print(f"Total rows: {cur.fetchone()[0]:,}")

cur.execute("""
    SELECT symbol, COUNT(*) as candles,
           MIN(timestamp) as earliest,
           MAX(timestamp) as latest
    FROM candles_daily
    GROUP BY symbol
    ORDER BY candles DESC
    LIMIT 20
""")
rows = cur.fetchall()
print(f"\n{'Symbol':<20} {'Candles':>8} {'Earliest':>15} {'Latest':>15} {'Days':>6}")
print("-" * 70)
for row in rows:
    sym, count, earliest, latest = row
    try:
        if earliest > 1e12:
            e = datetime.fromtimestamp(earliest/1000, tz=timezone.utc)
            l = datetime.fromtimestamp(latest/1000, tz=timezone.utc)
        else:
            e = datetime.fromtimestamp(earliest, tz=timezone.utc)
            l = datetime.fromtimestamp(latest, tz=timezone.utc)
        days = (l - e).days
        print(f"{sym:<20} {count:>8,} {e.strftime('%Y-%m-%d'):>15} {l.strftime('%Y-%m-%d'):>15} {days:>6}")
    except:
        print(f"{sym:<20} {count:>8,} {earliest} {latest}")

# Identify stale coins (latest < today) in 1h candles
print("\n=== Stale 1h candles (latest not today) ===")
cur.execute("""
    SELECT symbol, MAX(timestamp) as latest, COUNT(*) as candles
    FROM candles
    WHERE timeframe = '1h'
    GROUP BY symbol
    HAVING latest < strftime('%s', '2026-07-05') * 1000
    ORDER BY latest ASC
""")
rows = cur.fetchall()
if not rows:
    # try seconds
    cur.execute("""
        SELECT symbol, MAX(timestamp) as latest, COUNT(*) as candles
        FROM candles
        WHERE timeframe = '1h'
        GROUP BY symbol
        HAVING latest < 1751673600
        ORDER BY latest ASC
    """)
    rows = cur.fetchall()

if rows:
    for row in rows:
        sym, latest, count = row
        try:
            if latest > 1e12:
                l = datetime.fromtimestamp(latest/1000, tz=timezone.utc)
            else:
                l = datetime.fromtimestamp(latest, tz=timezone.utc)
            print(f"  {sym:<20} last: {l.strftime('%Y-%m-%d %H:%M')} ({count:,} candles)")
        except:
            print(f"  {sym:<20} last: {latest} ({count:,} candles)")
else:
    print("  None found (all current)")

# Summary stats
print("\n=== Summary ===")
cur.execute("SELECT COUNT(DISTINCT symbol) FROM candles WHERE timeframe='1h'")
print(f"Total 1h symbols: {cur.fetchone()[0]}")
cur.execute("SELECT COUNT(DISTINCT symbol) FROM candles_daily")
print(f"Total daily symbols: {cur.fetchone()[0]}")
cur.execute("SELECT COUNT(*) FROM candles WHERE timeframe='1h'")
print(f"Total 1h candles: {cur.fetchone()[0]:,}")

conn.close()
