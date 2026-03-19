import json, io, sys
from pathlib import Path
from datetime import datetime, timezone

if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

bots = {
    "V14PM Live (Aster Perps)": "trading/spot/live/v14pm/status.json",
    "V14 Paper": "trading/spot/paper/v14/status.json",
    "V14 PM Paper": "trading/spot/paper/v14_portfolio/status.json",
}

ws = Path("C:/Users/Never/.openclaw/workspace")
print("Heartbeat Bot Check (07:53 UTC):\n")
all_ok = True

for name, rel_path in bots.items():
    p = ws / rel_path
    if not p.exists():
        print(f"MISSING: {name} — no status.json")
        all_ok = False
        continue
    
    age_min = (datetime.now(timezone.utc) - datetime.fromtimestamp(p.stat().st_mtime, tz=timezone.utc)).total_seconds() / 60
    with open(p) as f:
        data = json.load(f)
    
    running = data.get("running", False)
    equity = data.get("equity", 0)
    pnl = data.get("pnl_pct", 0)
    
    if age_min > 65:
        status = f"STALE ({age_min:.0f}m)"
        all_ok = False
    elif not running:
        status = "STOPPED"
        all_ok = False
    else:
        status = "OK"
    
    print(f"{status:12s} | {name:28s} | Equity: ${equity:10.2f} | PnL: {pnl:7.2f}%")

print()
if all_ok:
    print("All bots healthy.")
else:
    print("Alerts needed.")
