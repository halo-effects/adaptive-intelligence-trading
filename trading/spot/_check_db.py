import sqlite3
from pathlib import Path

DB = Path(__file__).resolve().parent / "data" / "candles.db"
conn = sqlite3.connect(str(DB))
cursor = conn.cursor()

# List tables and row counts
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = cursor.fetchall()
for t in tables:
    name = t[0]
    count = cursor.execute(f"SELECT COUNT(*) FROM [{name}]").fetchone()[0]
    print(f"{name}: {count} rows")

# Check candles_daily: when was data last inserted?
print("\n--- candles_daily recent data ---")
cursor.execute("SELECT symbol, COUNT(*) as cnt, MAX(timestamp) as latest FROM candles_daily GROUP BY symbol ORDER BY symbol")
for row in cursor.fetchall():
    print(f"  {row[0]}: {row[1]} rows, latest ts={row[2]}")

# Check candles (1h): sample of latest timestamps
print("\n--- candles (1h) latest per symbol (sample) ---")
cursor.execute("SELECT symbol, COUNT(*) as cnt, MAX(timestamp) as latest FROM candles GROUP BY symbol ORDER BY cnt DESC LIMIT 10")
for row in cursor.fetchall():
    print(f"  {row[0]}: {row[1]} rows, latest ts={row[2]}")

conn.close()
