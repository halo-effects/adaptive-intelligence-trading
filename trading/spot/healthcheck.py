"""Lightweight health check — no LLM needed.

Checks bot status files, returns a simple pass/fail signal.
Exit code 0 = all healthy, exit code 1 = alert needed.
Prints only what's wrong (empty output = healthy).
"""
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

WORKSPACE = Path(r"C:\Users\Never\.openclaw\workspace")
MAX_STALE_MINUTES = 65

BOTS = {
    "V14PM Live": {
        "status": WORKSPACE / "trading" / "spot" / "live" / "v14pm" / "status.json",
        "max_drawdown": 15.0,
        "critical": True,  # real money
    },
    "V14PM Paper": {
        "status": WORKSPACE / "trading" / "spot" / "paper" / "v14_portfolio" / "status.json",
        "max_drawdown": 30.0,
        "critical": False,
    },
    "V14 Paper": {
        "status": WORKSPACE / "trading" / "spot" / "paper" / "v14" / "status.json",
        "max_drawdown": 30.0,
        "critical": False,
    },
}

alerts = []

for name, cfg in BOTS.items():
    path = cfg["status"]
    if not path.exists():
        alerts.append(f"🔴 {name}: status.json MISSING")
        continue

    try:
        with open(path) as f:
            data = json.load(f)
    except Exception as e:
        alerts.append(f"🔴 {name}: status.json unreadable ({e})")
        continue

    # Check running flag
    if not data.get("running", False):
        alerts.append(f"🔴 {name}: running=false")
        continue

    # Check staleness
    last_update = data.get("last_update")
    if last_update:
        try:
            ts = datetime.fromisoformat(last_update)
            age_min = (datetime.now(timezone.utc) - ts).total_seconds() / 60
            if age_min > MAX_STALE_MINUTES:
                alerts.append(f"🔴 {name}: stale ({int(age_min)}m old)")
        except:
            pass

    # Check drawdown (only for live)
    if cfg["critical"]:
        equity = data.get("equity", 0)
        capital = data.get("capital", 0)
        if capital > 0 and equity > 0:
            dd_pct = (1 - equity / capital) * 100
            if dd_pct > cfg["max_drawdown"]:
                alerts.append(f"🔴 {name}: drawdown {dd_pct:.1f}% > {cfg['max_drawdown']}%")

# Check dashboard sync task
try:
    import subprocess
    result = subprocess.run(
        ["powershell", "-NoProfile", "-Command",
         "(Get-ScheduledTaskInfo 'AIT_DashboardSync').LastTaskResult"],
        capture_output=True, text=True, timeout=10
    )
    code = result.stdout.strip()
    if code and code != "0":
        alerts.append(f"⚠️ Dashboard sync: exit code {code}")
except:
    pass

# Output
if alerts:
    print("\n".join(alerts))
    sys.exit(1)
else:
    sys.exit(0)
