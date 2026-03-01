import sqlite3
conn = sqlite3.connect('_legacy/trading/spot/paper/v12e/candles.db')
tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
print("Tables:", [t[0] for t in tables])
for t in tables:
    name = t[0]
    count = conn.execute(f"SELECT COUNT(*) FROM [{name}]").fetchone()[0]
    syms = conn.execute(f"SELECT DISTINCT symbol FROM [{name}]").fetchall()
    print(f"  {name}: {count} rows, symbols: {[s[0] for s in syms]}")
conn.close()
