import sqlite3
conn = sqlite3.connect('trading/spot/data/candles.db')
for coin in ['ZEC', 'DOGE', 'BTC', 'ETH']:
    r = conn.execute("SELECT COUNT(*), MIN(date), MAX(date) FROM cfgi_daily WHERE symbol LIKE ?", (f'{coin}%',)).fetchone()
    print(f'{coin} CFGI: {r[0]} entries, {r[1]} to {r[2]}')
conn.close()
