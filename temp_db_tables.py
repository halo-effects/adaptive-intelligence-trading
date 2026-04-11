import sqlite3
db = sqlite3.connect(r"C:\Users\Never\.openclaw\workspace\trading\spot\data\candles.db")
tables = [r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
print("Tables:", tables)
for t in tables:
    cols = db.execute(f"PRAGMA table_info({t})").fetchall()
    print(f"\n{t}: {[c[1] for c in cols]}")
    row = db.execute(f"SELECT * FROM {t} WHERE symbol LIKE '%TAO%' ORDER BY timestamp DESC LIMIT 1").fetchone()
    if row:
        print(f"  Latest TAO row: {row}")
db.close()
