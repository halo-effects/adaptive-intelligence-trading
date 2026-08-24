"""Import funding rate CSVs into candles.db funding_rates table."""
import csv
import sqlite3
import sys
import io
from pathlib import Path

if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

DB_PATH = Path(__file__).resolve().parent.parent / "trading" / "spot" / "data" / "candles.db"
FUNDING_DIR = Path(__file__).resolve().parent.parent / "exports" / "funding-rate-signal-export" / "funding"

conn = sqlite3.connect(str(DB_PATH))

# Create table
conn.execute("""
    CREATE TABLE IF NOT EXISTS funding_rates (
        symbol TEXT NOT NULL,
        timestamp INTEGER NOT NULL,
        funding_rate REAL NOT NULL,
        PRIMARY KEY (symbol, timestamp)
    )
""")
conn.execute("CREATE INDEX IF NOT EXISTS idx_funding_symbol_ts ON funding_rates(symbol, timestamp)")
conn.commit()

total = 0
for f in sorted(FUNDING_DIR.glob("funding-*.csv")):
    coin = f.stem.replace("funding-", "")
    # Handle legacy TON file → store as GRAM
    if coin == "GRAM-legacy-TON":
        symbol = "GRAM/USDT"
    else:
        symbol = coin + "/USDT"
    
    rows = []
    with open(f, "r") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            # Parse ISO-8601 to epoch ms
            from datetime import datetime, timezone
            ts = datetime.fromisoformat(row["funding_time_utc"].replace("Z", "+00:00"))
            ts_ms = int(ts.timestamp() * 1000)
            rows.append((symbol, ts_ms, float(row["funding_rate"])))
    
    conn.executemany(
        "INSERT OR IGNORE INTO funding_rates (symbol, timestamp, funding_rate) VALUES (?, ?, ?)",
        rows
    )
    total += len(rows)
    print("  %-20s %5d rates" % (symbol, len(rows)))

conn.commit()

# Verify
cur = conn.execute("SELECT COUNT(*), COUNT(DISTINCT symbol) FROM funding_rates")
count, nsym = cur.fetchone()
print("\nTotal: %d rates, %d symbols" % (count, nsym))

conn.close()
