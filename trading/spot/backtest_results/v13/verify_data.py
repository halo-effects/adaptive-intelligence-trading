import sqlite3
from datetime import datetime, timezone
from pathlib import Path

DB = Path(__file__).resolve().parents[2] / 'data' / 'candles.db'
db = sqlite3.connect(str(DB))

print('--- candles_daily full inventory ---')
rows = db.execute(
    'SELECT symbol, MIN(timestamp), MAX(timestamp), COUNT(*) FROM candles_daily GROUP BY symbol ORDER BY symbol'
).fetchall()
for r in rows:
    mn = datetime.fromtimestamp(r[1]/1000, tz=timezone.utc).date()
    mx = datetime.fromtimestamp(r[2]/1000, tz=timezone.utc).date()
    print(f'  {r[0]}: {mn} to {mx}, {r[3]} rows')

# Check for gaps in ETH
print('\n--- ETH gap check (first 5 and around Oct 2021) ---')
rows = db.execute(
    "SELECT timestamp FROM candles_daily WHERE symbol='ETH/USDT' ORDER BY timestamp"
).fetchall()
timestamps = [r[0] for r in rows]
gaps = []
for i in range(1, len(timestamps)):
    diff_days = (timestamps[i] - timestamps[i-1]) / 86400000
    if diff_days > 1.5:
        d1 = datetime.fromtimestamp(timestamps[i-1]/1000, tz=timezone.utc).date()
        d2 = datetime.fromtimestamp(timestamps[i]/1000, tz=timezone.utc).date()
        gaps.append((d1, d2, diff_days))
if gaps:
    print(f'  Found {len(gaps)} gaps:')
    for g in gaps:
        print(f'    {g[0]} -> {g[1]} ({g[2]:.0f} days)')
else:
    print('  No gaps!')

# Same for SOL
print('\n--- SOL gap check ---')
rows = db.execute(
    "SELECT timestamp FROM candles_daily WHERE symbol='SOL/USDT' ORDER BY timestamp"
).fetchall()
timestamps = [r[0] for r in rows]
gaps = []
for i in range(1, len(timestamps)):
    diff_days = (timestamps[i] - timestamps[i-1]) / 86400000
    if diff_days > 1.5:
        d1 = datetime.fromtimestamp(timestamps[i-1]/1000, tz=timezone.utc).date()
        d2 = datetime.fromtimestamp(timestamps[i]/1000, tz=timezone.utc).date()
        gaps.append((d1, d2, diff_days))
if gaps:
    print(f'  Found {len(gaps)} gaps:')
    for g in gaps:
        print(f'    {g[0]} -> {g[1]} ({g[2]:.0f} days)')
else:
    print('  No gaps!')

# BTC
print('\n--- BTC gap check ---')
rows = db.execute(
    "SELECT timestamp FROM candles_daily WHERE symbol='BTC/USDT' ORDER BY timestamp"
).fetchall()
timestamps = [r[0] for r in rows]
gaps = []
for i in range(1, len(timestamps)):
    diff_days = (timestamps[i] - timestamps[i-1]) / 86400000
    if diff_days > 1.5:
        d1 = datetime.fromtimestamp(timestamps[i-1]/1000, tz=timezone.utc).date()
        d2 = datetime.fromtimestamp(timestamps[i]/1000, tz=timezone.utc).date()
        gaps.append((d1, d2, diff_days))
if gaps:
    print(f'  Found {len(gaps)} gaps:')
    for g in gaps:
        print(f'    {g[0]} -> {g[1]} ({g[2]:.0f} days)')
else:
    print('  No gaps!')

# SOL listing date
print(f'\n--- SOL earliest: {datetime.fromtimestamp(timestamps[0]/1000, tz=timezone.utc).date() if "SOL" in "SOL" else "?"}')
r = db.execute("SELECT MIN(timestamp) FROM candles_daily WHERE symbol='SOL/USDT'").fetchone()
print(f'  SOL first candle: {datetime.fromtimestamp(r[0]/1000, tz=timezone.utc).date()}')

db.close()
