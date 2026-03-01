import sqlite3
c = sqlite3.connect('trading/spot/data/candles.db')
tables = [t[0] for t in c.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
print("Tables:", tables)
for t in tables:
    cols = [d[0] for d in c.execute(f"SELECT * FROM [{t}] LIMIT 1").description]
    cnt = c.execute(f"SELECT COUNT(*) FROM [{t}]").fetchone()[0]
    print(f"  {t} ({cnt} rows): {cols}")
