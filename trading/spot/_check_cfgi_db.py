import sqlite3
db = sqlite3.connect('C:/Users/Never/.openclaw/workspace/trading/spot/data/candles.db')

# Check cfgi_daily table
try:
    cur = db.execute("SELECT COUNT(*) FROM cfgi_daily")
    print(f"cfgi_daily total rows: {cur.fetchone()[0]}")
    cur = db.execute("SELECT symbol, COUNT(*), MIN(date), MAX(date) FROM cfgi_daily GROUP BY symbol ORDER BY symbol")
    for r in cur.fetchall():
        print(f"  {r[0]}: {r[1]} rows, {r[2]} to {r[3]}")
except Exception as e:
    print(f"cfgi_daily error: {e}")

# Check all tables
cur = db.execute("SELECT name FROM sqlite_master WHERE type='table'")
print(f"\nAll tables: {[r[0] for r in cur.fetchall()]}")
db.close()
