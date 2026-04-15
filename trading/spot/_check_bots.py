import json, io, sys
from pathlib import Path
from datetime import datetime, timezone

if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

paths = {
    'V14 Live (legacy, Spot)': 'trading/spot/live/v14/status.json',
    'V14 Paper': 'trading/spot/paper/v14/status.json',
    'V14 PM Paper': 'trading/spot/paper/v14_portfolio/status.json',
}

ws = Path('C:/Users/Never/.openclaw/workspace')
print("Bot Status Check (as of 07:48 UTC):\n")
for name, rel_path in paths.items():
    p = ws / rel_path
    if p.exists():
        age_min = (datetime.now(timezone.utc) - datetime.fromtimestamp(p.stat().st_mtime, tz=timezone.utc)).total_seconds() / 60
        with open(p) as f:
            data = json.load(f)
        running = 'YES' if data.get('running') else 'NO'
        equity = data.get('equity', 0)
        pnl = data.get('pnl_pct', 0)
        
        print(f"{name:25s} | Running: {running:3s} | Equity: ${equity:10.2f} | PnL: {pnl:7.2f}%")
