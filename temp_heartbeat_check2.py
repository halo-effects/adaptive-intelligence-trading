import json
from datetime import datetime, timezone

now = datetime.now(timezone.utc)

bots = {
    'V14PM Live': r'C:\Users\Never\.openclaw\workspace\trading\spot\live\v14pm\status.json',
    'V14 Paper': r'C:\Users\Never\.openclaw\workspace\trading\spot\paper\v14\status.json',
    'V14PM Paper': r'C:\Users\Never\.openclaw\workspace\trading\spot\paper\v14_portfolio\status.json',
}

for name, path in bots.items():
    try:
        with open(path) as f:
            d = json.load(f)
            ts = datetime.fromisoformat(d.get('last_update', '1970-01-01T00:00:00+00:00'))
            age_min = int((now - ts).total_seconds() / 60)
            running = d.get('running')
            pnl = d.get('pnl_pct')
            max_dd = d.get('max_drawdown_pct', 0)
            
            alerts = []
            if not running:
                alerts.append('NOT_RUNNING')
            if age_min > 65:
                alerts.append(f'STALE_{age_min}min')
            if max_dd and max_dd > 15:
                alerts.append(f'DRAWDOWN_{max_dd}%')
            
            status = ' ALERT: ' + ','.join(alerts) if alerts else ' OK'
            print(f'{name}: age={age_min}min, running={running}, pnl={pnl}%, max_dd={max_dd}%{status}')
    except Exception as e:
        print(f'{name}: ERROR - {e}')
