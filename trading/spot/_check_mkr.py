import sqlite3
db = sqlite3.connect(r'C:\Users\Never\.openclaw\workspace\trading\spot\data\candles.db')

# Check MKR data
for pair in ['MKR/USDT', 'MKR/USDC']:
    rows = db.execute("SELECT COUNT(*) FROM candles WHERE symbol=? AND timeframe='1h'", (pair,)).fetchone()[0]
    latest = db.execute("SELECT MAX(timestamp) FROM candles WHERE symbol=? AND timeframe='1h'", (pair,)).fetchone()[0]
    print(f'{pair}: {rows} candles, latest: {latest}')

db.close()
