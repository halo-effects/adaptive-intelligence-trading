import sqlite3
c = sqlite3.connect('../../data/candles.db')
for s in ['LINK/USDC','LINK/USDT','XRP/USDC','XRP/USDT']:
    r = c.execute('SELECT COUNT(*), MIN(date), MAX(date) FROM candles_daily WHERE symbol=?', (s,)).fetchone()
    print(f"{s}: {r[0]} rows, {r[1]} to {r[2]}")

# CFGI coverage
for s in ['LINK','XRP']:
    r = c.execute('SELECT COUNT(*), MIN(date), MAX(date) FROM cfgi_daily WHERE symbol=?', (s,)).fetchone()
    print(f"CFGI {s}: {r[0]} rows, {r[1]} to {r[2]}")
