import sqlite3
from pathlib import Path

db = Path(__file__).resolve().parent.parent.parent / 'data' / 'candles.db'
conn = sqlite3.connect(db)

# List tables
tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
print("Tables:", tables)

# Find the right table
table = tables[0][0] if tables else None
if not table:
    print("No tables!")
    exit()

# Get columns
cols = conn.execute(f"PRAGMA table_info({table})").fetchall()
print("Columns:", [c[1] for c in cols])

# Get all coins
coins = [r[0] for r in conn.execute(f"SELECT DISTINCT symbol FROM {table}").fetchall()]
print(f"\nCoins in DB ({len(coins)}): {sorted(coins)}\n")

print(f"{'Coin':12s}  {'Oct 2024':>12s}  {'Peak':>12s}  {'Now':>12s}  {'Peak/Oct':>8s}  {'Now/Oct':>8s}")
print("-" * 75)

results = []
for coin in sorted(coins):
    # timestamp is epoch ms
    oct1 = 1727740800000  # 2024-10-01 UTC
    early = conn.execute(f"SELECT close FROM {table} WHERE symbol=? AND timestamp >= ? ORDER BY timestamp ASC LIMIT 1", (coin, oct1)).fetchone()
    late = conn.execute(f"SELECT close FROM {table} WHERE symbol=? ORDER BY timestamp DESC LIMIT 1", (coin,)).fetchone()
    peak = conn.execute(f"SELECT MAX(close) FROM {table} WHERE symbol=? AND timestamp >= ?", (coin, oct1)).fetchone()
    
    if early and late and peak and early[0] > 0:
        ratio_now = late[0] / early[0]
        ratio_peak = peak[0] / early[0]
        results.append((coin, early[0], peak[0], late[0], ratio_peak, ratio_now))
    elif late:
        print(f"{coin:12s}  No Oct 2024 data")

# Sort by peak multiple
results.sort(key=lambda x: x[4], reverse=True)
for coin, start, peak, now, peak_x, now_x in results:
    marker = " ***5X+***" if peak_x >= 5.0 else ""
    print(f"{coin:12s}  ${start:>11.4f}  ${peak:>11.4f}  ${now:>11.4f}  {peak_x:>7.2f}x  {now_x:>7.2f}x{marker}")

conn.close()
