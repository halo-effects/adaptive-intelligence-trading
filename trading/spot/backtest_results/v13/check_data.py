import sqlite3
from datetime import datetime, timezone
from pathlib import Path

DB = Path(__file__).resolve().parents[2] / 'data' / 'candles.db'
db = sqlite3.connect(str(DB))

# Check candles table schema
cols = db.execute("PRAGMA table_info(candles)").fetchall()
print('candles columns:', [c[1] for c in cols])

# Check candles table coverage
print('\n--- candles table (hourly?) ---')
for coin in ['ETH', 'SOL', 'BTC']:
    rows = db.execute(
        "SELECT symbol, MIN(timestamp), MAX(timestamp), COUNT(*) FROM candles WHERE symbol LIKE ?",
        (f'{coin}%',)
    ).fetchall()
    for r in rows:
        mn = datetime.fromtimestamp(r[1]/1000, tz=timezone.utc) if r[1] else None
        mx = datetime.fromtimestamp(r[2]/1000, tz=timezone.utc) if r[2] else None
        print(f'{r[0]}: {mn} to {mx}, {r[3]} rows')

# Check daily coverage
print('\n--- candles_daily ---')
for coin in ['ETH', 'SOL', 'BTC']:
    rows = db.execute(
        "SELECT symbol, MIN(timestamp), MAX(timestamp), COUNT(*) FROM candles_daily WHERE symbol LIKE ?",
        (f'{coin}%',)
    ).fetchall()
    for r in rows:
        mn = datetime.fromtimestamp(r[1]/1000, tz=timezone.utc) if r[1] else None
        mx = datetime.fromtimestamp(r[2]/1000, tz=timezone.utc) if r[2] else None
        print(f'{r[0]}: {mn} to {mx}, {r[3]} rows')

# Check CFGI
print('\n--- cfgi_daily ---')
for coin in ['ETH', 'SOL', 'BTC']:
    rows = db.execute(
        "SELECT symbol, MIN(date), MAX(date), COUNT(*) FROM cfgi_daily WHERE symbol LIKE ?",
        (f'{coin}%',)
    ).fetchall()
    for r in rows:
        print(f'{r[0]}: {r[1]} to {r[2]}, {r[3]} rows')

# What we need: Oct 2020 to present for all 3
# Plus warm-up period for signals (200-day SMA needs ~200 days before start)
print('\n--- GAPS ---')
need_start = datetime(2020, 4, 1, tzinfo=timezone.utc)  # 6 months warmup before Oct 2020
for coin in ['ETH', 'SOL', 'BTC']:
    r = db.execute(
        "SELECT MIN(timestamp) FROM candles_daily WHERE symbol LIKE ?",
        (f'{coin}%',)
    ).fetchone()
    if r[0]:
        actual = datetime.fromtimestamp(r[0]/1000, tz=timezone.utc)
        if actual > need_start:
            print(f'{coin}: MISSING daily data from {need_start.date()} to {actual.date()}')
        else:
            print(f'{coin}: OK (starts {actual.date()})')

db.close()
