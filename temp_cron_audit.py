"""Audit all cron jobs - what's enabled, what's broken, what's safe."""
import json

with open(r"C:\Users\Never\.openclaw\cron\jobs.json", encoding="utf-8") as f:
    data = json.load(f)

enabled = []
disabled = []

for job in data["jobs"]:
    name = job["name"]
    enabled_flag = job["enabled"]
    state = job.get("state", {})
    last_status = state.get("lastStatus", "never ran")
    errors = state.get("consecutiveErrors", 0)
    last_error = state.get("lastError", "")
    schedule = job.get("schedule", {})
    expr = schedule.get("expr", schedule.get("everyMs", "?"))
    
    # Check if the job touches git, trading, or filesystem
    msg = job.get("payload", {}).get("message", "")
    touches_git = "git" in msg.lower()
    touches_trading = any(k in msg.lower() for k in ["trading", "bot", "v14", "aster", "scanner"])
    touches_memory = any(k in msg.lower() for k in ["memory", "consolidat", "daily note"])
    
    info = {
        "name": name,
        "id": job["id"][:8],
        "enabled": enabled_flag,
        "schedule": expr,
        "status": last_status,
        "errors": errors,
        "touches_git": touches_git,
        "touches_trading": touches_trading,
        "touches_memory": touches_memory,
        "last_error_short": last_error[:80] if last_error else "",
    }
    
    if enabled_flag:
        enabled.append(info)
    else:
        disabled.append(info)

print("=" * 60)
print("ENABLED CRONS")
print("=" * 60)
for j in enabled:
    status_icon = "✅" if j["errors"] == 0 else f"🔴 ({j['errors']} errors)"
    tags = []
    if j["touches_git"]: tags.append("GIT")
    if j["touches_trading"]: tags.append("TRADING")
    if j["touches_memory"]: tags.append("MEMORY")
    tag_str = f" [{', '.join(tags)}]" if tags else ""
    print(f"\n  {j['name']} ({j['id']}) {status_icon}{tag_str}")
    print(f"    Schedule: {j['schedule']}")
    if j["last_error_short"]:
        print(f"    Error: {j['last_error_short']}")

print(f"\n{'=' * 60}")
print("DISABLED CRONS")
print("=" * 60)
for j in disabled:
    tags = []
    if j["touches_git"]: tags.append("GIT")
    if j["touches_trading"]: tags.append("TRADING")
    if j["touches_memory"]: tags.append("MEMORY")
    tag_str = f" [{', '.join(tags)}]" if tags else ""
    print(f"\n  {j['name']} ({j['id']}){tag_str}")
    print(f"    Schedule: {j['schedule']}")
    if j["last_error_short"]:
        print(f"    Last error: {j['last_error_short']}")
