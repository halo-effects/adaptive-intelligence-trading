import csv
from collections import Counter, defaultdict
from datetime import datetime

with open(r'C:\Users\Never\.openclaw\workspace\trading\spot\paper\v14_portfolio\trades.csv') as f:
    rows = list(csv.DictReader(f))

print(f'Total deals: {len(rows)}')

ids = [int(r['deal_id']) for r in rows]
print(f'ID range: {min(ids)} to {max(ids)}')
print(f'Missing IDs in range: {max(ids) - min(ids) + 1 - len(ids)}')

# Backdated replay artifacts
backdated = 0
real = 0
for r in rows:
    if not r['recorded_at']:
        backdated += 1
        continue
    try:
        close = datetime.fromisoformat(r['close_time'])
        recorded = datetime.fromisoformat(r['recorded_at'])
        if (recorded - close).total_seconds() > 86400:
            backdated += 1
        else:
            real += 1
    except:
        real += 1

print(f'\nBackdated/replay artifacts: {backdated}')
print(f'Real-time deals: {real}')

# Sum PnL
total_pnl = sum(float(r['pnl']) for r in rows)
print(f'\nSum of all PnL: ${total_pnl:.2f}')

# Check for losses
losses = [r for r in rows if float(r['pnl']) < 0]
print(f'Deals with negative PnL: {len(losses)}')

# Deals per day
daily = defaultdict(int)
for r in rows:
    ct = r.get('close_time', '')
    if ct:
        try:
            day = datetime.fromisoformat(ct).strftime('%Y-%m-%d')
            daily[day] += 1
        except:
            pass

print(f'\nDeals per day (by close_time):')
for day in sorted(daily.keys()):
    print(f'  {day}: {daily[day]}')

# Check for exact duplicate deals (same symbol + open_time + close_time)
seen = set()
dupes = []
for r in rows:
    key = (r['symbol'], r['open_time'], r['close_time'])
    if key in seen:
        dupes.append(r)
    seen.add(key)
print(f'\nExact duplicate deals (same symbol+open+close): {len(dupes)}')
for d in dupes[:5]:
    print(f'  {d["deal_id"]}: {d["symbol"]} {d["open_time"]} -> {d["close_time"]} pnl={d["pnl"]}')
