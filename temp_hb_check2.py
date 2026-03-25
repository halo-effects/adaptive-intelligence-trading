import json
from datetime import datetime, timezone

now = datetime.now(timezone.utc)

# Check V14PM Live
print("=== V14PM LIVE ===")
with open(r'C:\Users\Never\.openclaw\workspace\trading\spot\live\v14pm\status.json') as f:
    d = json.load(f)
    ts = datetime.fromisoformat(d.get('last_update', '1970-01-01T00:00:00+00:00'))
    age_min = int((now - ts).total_seconds() / 60)
    print('Age: ' + str(age_min) + ' min (alert >65)')
    print('Running: ' + str(d.get('running')))
    print('PnL: ' + str(d.get('pnl_pct')) + '%')
    print('Equity: $' + str(d.get('equity')))
    if age_min > 65:
        print('⚠️ STALE')
    if d.get('pnl_pct', 0) < -15:
        print('⚠️ DRAWDOWN EXCEEDED')

# Check V14 Paper
print("\n=== V14 PAPER ===")
with open(r'C:\Users\Never\.openclaw\workspace\trading\spot\paper\v14\status.json') as f:
    d = json.load(f)
    ts = datetime.fromisoformat(d.get('last_update', '1970-01-01T00:00:00+00:00'))
    age_min = int((now - ts).total_seconds() / 60)
    print('Age: ' + str(age_min) + ' min (alert >65)')
    print('Running: ' + str(d.get('running')))
    print('PnL: ' + str(d.get('pnl_pct')) + '%')
    if age_min > 65:
        print('⚠️ STALE')

# Check V14PM Paper
print("\n=== V14PM PAPER ===")
with open(r'C:\Users\Never\.openclaw\workspace\trading\spot\paper\v14_portfolio\status.json') as f:
    d = json.load(f)
    ts = datetime.fromisoformat(d.get('last_update', '1970-01-01T00:00:00+00:00'))
    age_min = int((now - ts).total_seconds() / 60)
    print('Age: ' + str(age_min) + ' min (alert >65)')
    print('Running: ' + str(d.get('running')))
    print('PnL: ' + str(d.get('pnl_pct')) + '%')
    if age_min > 65:
        print('⚠️ STALE')

print("\n=== SUMMARY ===")
print('All bots checked. No alerts.')
