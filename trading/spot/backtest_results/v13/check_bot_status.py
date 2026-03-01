import json, os
from datetime import datetime, timezone

os.chdir(r'C:\Users\Never\.openclaw\workspace')

with open('trading/spot/live/aster/status.json') as f:
    aster = json.load(f)
with open('trading/spot/paper/v12f/status.json') as f:
    v12f = json.load(f)

now = datetime.now(timezone.utc)
aster_time = datetime.fromisoformat(aster['last_update'].replace('Z', '+00:00'))
v12f_time = datetime.fromisoformat(v12f['last_update'].replace('Z', '+00:00'))

aster_age_min = (now - aster_time).total_seconds() / 60
v12f_age_min = (now - v12f_time).total_seconds() / 60

print(f'Aster: running={aster["running"]}, age={aster_age_min:.0f}min, dd={aster["max_drawdown_pct"]:.1f}%, capital={aster["capital"]}')
print(f'V12f: running={v12f["running"]}, age={v12f_age_min:.0f}min, dd={v12f["max_drawdown_pct"]:.2f}%, coins={len(v12f["coins"])}')

if aster_age_min > 65:
    print(f'ALERT: Aster status stale ({aster_age_min:.0f}min)')
if v12f_age_min > 65:
    print(f'ALERT: V12f status stale ({v12f_age_min:.0f}min)')
