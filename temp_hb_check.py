import json
from datetime import datetime, timezone

now = datetime.now(timezone.utc)

# Check V14PM Live
with open(r'C:\Users\Never\.openclaw\workspace\trading\spot\live\v14pm\status.json') as f:
    d = json.load(f)
    ts = datetime.fromisoformat(d.get('last_update', '1970-01-01T00:00:00+00:00'))
    age_min = int((now - ts).total_seconds() / 60)
    print('V14PM Live: age=' + str(age_min) + 'min, running=' + str(d.get('running')) + ', pnl=' + str(d.get('pnl_pct')) + '%')

# Check V14 Paper
with open(r'C:\Users\Never\.openclaw\workspace\trading\spot\paper\v14\status.json') as f:
    d = json.load(f)
    ts = datetime.fromisoformat(d.get('last_update', '1970-01-01T00:00:00+00:00'))
    age_min = int((now - ts).total_seconds() / 60)
    print('V14 Paper: age=' + str(age_min) + 'min, running=' + str(d.get('running')) + ', pnl=' + str(d.get('pnl_pct')) + '%')

# Check V14PM Paper
with open(r'C:\Users\Never\.openclaw\workspace\trading\spot\paper\v14_portfolio\status.json') as f:
    d = json.load(f)
    ts = datetime.fromisoformat(d.get('last_update', '1970-01-01T00:00:00+00:00'))
    age_min = int((now - ts).total_seconds() / 60)
    print('V14PM Paper: age=' + str(age_min) + 'min, running=' + str(d.get('running')) + ', pnl=' + str(d.get('pnl_pct')) + '%')
