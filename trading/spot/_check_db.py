import sqlite3
conn = sqlite3.connect('trading/spot/data/candles.db')
tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
print("Tables:", [t[0] for t in tables])
for t in tables:
    name = t[0]
    count = conn.execute(f"SELECT COUNT(*) FROM [{name}]").fetchone()[0]
    if count > 0:
        first = conn.execute(f"SELECT MIN(timestamp) FROM [{name}]").fetchone()[0]
        last = conn.execute(f"SELECT MAX(timestamp) FROM [{name}]").fetchone()[0]
        print(f"  {name}: {count} rows, {first} -> {last}")
    else:
        print(f"  {name}: empty")
# Check for LINK specifically
for pattern in ['LINK', 'link']:
    matches = [t[0] for t in tables if pattern in t[0].upper()]
    if matches:
        print(f"\nLINK tables: {matches}")
conn.close()
