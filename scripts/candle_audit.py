import sqlite3
from datetime import datetime, timezone

conn = sqlite3.connect('trading/spot/data/candles.db')
cur = conn.cursor()

# Get tables
cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = [r[0] for r in cur.fetchall()]
print(f"Tables: {tables}\n")

for t in tables[:3]:
    cur.execute(f"PRAGMA table_info({t})")
    cols = [(r[1], r[2]) for r in cur.fetchall()]
    print(f"{t} schema: {cols}")
    cur.execute(f"SELECT COUNT(*) FROM {t}")
    print(f"{t} rows: {cur.fetchone()[0]}")
    print()

# Now query candle coverage per symbol
# Guess the main table and columns
main_table = tables[0]
cur.execute(f"PRAGMA table_info({main_table})")
schema = cur.fetchall()
print(f"Full schema of {main_table}:")
for col in schema:
    print(f"  {col}")

# Try to get distinct symbols/pairs
print("\n--- Trying to find symbol column ---")
col_names = [s[1] for s in schema]
print(f"Columns: {col_names}")

# Look for symbol-like column
sym_col = None
for c in col_names:
    if c.lower() in ('symbol', 'pair', 'coin', 'market'):
        sym_col = c
        break

if sym_col:
    print(f"\nUsing symbol column: {sym_col}")
    # Get per-symbol stats
    ts_col = None
    for c in col_names:
        if c.lower() in ('timestamp', 'time', 'ts', 'date', 'open_time', 'datetime'):
            ts_col = c
            break
    
    if ts_col:
        print(f"Using timestamp column: {ts_col}")
        cur.execute(f"""
            SELECT {sym_col}, 
                   COUNT(*) as candles,
                   MIN({ts_col}) as earliest,
                   MAX({ts_col}) as latest
            FROM {main_table}
            GROUP BY {sym_col}
            ORDER BY candles DESC
        """)
        rows = cur.fetchall()
        print(f"\n{'Symbol':<20} {'Candles':>10} {'Earliest':>25} {'Latest':>25} {'Days':>8}")
        print("-" * 95)
        for row in rows:
            sym, count, earliest, latest = row
            # Try to parse timestamps
            try:
                if isinstance(earliest, (int, float)):
                    if earliest > 1e12:  # milliseconds
                        e = datetime.fromtimestamp(earliest/1000, tz=timezone.utc)
                        l = datetime.fromtimestamp(latest/1000, tz=timezone.utc)
                    else:
                        e = datetime.fromtimestamp(earliest, tz=timezone.utc)
                        l = datetime.fromtimestamp(latest, tz=timezone.utc)
                    days = (l - e).days
                    print(f"{sym:<20} {count:>10,} {e.strftime('%Y-%m-%d %H:%M'):>25} {l.strftime('%Y-%m-%d %H:%M'):>25} {days:>8}")
                else:
                    print(f"{sym:<20} {count:>10,} {str(earliest):>25} {str(latest):>25}")
            except:
                print(f"{sym:<20} {count:>10,} {str(earliest):>25} {str(latest):>25}")
    else:
        print("No timestamp column found")
        cur.execute(f"SELECT DISTINCT {sym_col} FROM {main_table}")
        syms = [r[0] for r in cur.fetchall()]
        print(f"Symbols ({len(syms)}): {syms}")
else:
    print("No symbol column found, showing sample rows:")
    cur.execute(f"SELECT * FROM {main_table} LIMIT 5")
    for row in cur.fetchall():
        print(row)

conn.close()
