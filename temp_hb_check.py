import json
from datetime import datetime, timezone

now = datetime.now(timezone.utc)

bots = [
    ('V14PM Live', r'C:\Users\Never\.openclaw\workspace\trading\spot\live\v14pm\status.json'),
    ('V14 Paper', r'C:\Users\Never\.openclaw\workspace\trading\spot\paper\v14\status.json'),
    ('V14PM Paper', r'C:\Users\Never\.openclaw\workspace\trading\spot\paper\v14_portfolio\status.json'),
]

for name, path in bots:
    try:
        with open(path) as f:
            d = json.load(f)
            ts = datetime.fromisoformat(d.get('last_update', '1970-01-01T00:00:00+00:00'))
            age_min = int((now - ts).total_seconds() / 60)
            running = d.get('running', False)
            pnl = d.get('pnl_pct', 'N/A')
            max_dd = d.get('max_drawdown_pct', 'N/A')
            alert = ''
            if not running:
                alert = ' ⚠️ NOT RUNNING'
            elif age_min > 65:
                alert = ' ⚠️ STALE (>65 min)'
            elif isinstance(max_dd, (int, float)) and max_dd > 15:
                alert = ' ⚠️ DRAWDOWN >' + str(max_dd) + '%'
            print(name + ': age=' + str(age_min) + 'min, running=' + str(running) + ', pnl=' + str(pnl) + '%, dd=' + str(max_dd) + '%' + alert)
    except Exception as e:
        print(name + ': ERROR - ' + str(e))
