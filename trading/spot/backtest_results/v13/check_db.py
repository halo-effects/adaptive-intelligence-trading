import sqlite3
conn = sqlite3.connect('../../data/candles.db')
c = conn.cursor()

for sym in ['ETH/USDC', 'BTC/USDC', 'SOL/USDC']:
    c.execute('SELECT COUNT(*) FROM candles_daily WHERE symbol=?', (sym,))
    n = c.fetchone()[0]
    c.execute('SELECT date FROM candles_daily WHERE symbol=? ORDER BY date DESC LIMIT 1', (sym,))
    last = c.fetchone()
    c.execute('SELECT date FROM candles_daily WHERE symbol=? ORDER BY date ASC LIMIT 1', (sym,))
    first = c.fetchone()
    print(f"{sym}: {n} rows ({first[0] if first else '?'} to {last[0] if last else '?'})")

# Check columns
c.execute('PRAGMA table_info(candles_daily)')
cols = [r[1] for r in c.fetchall()]
print(f"\nColumns: {cols}")

# Check a few indicator values
c.execute("SELECT date, sma_200 FROM candles_daily WHERE symbol='ETH/USDC' AND date LIKE '2020-10%' LIMIT 3")
rows = c.fetchall()
if rows:
    print("\nETH Oct 2020 sma_200:")
    for r in rows:
        print(f"  {r}")
else:
    # maybe column name different
    c.execute("SELECT date FROM candles_daily WHERE symbol='ETH/USDC' AND date LIKE '2020-10%' LIMIT 3")
    for r in c.fetchall():
        print(f"  {r}")
