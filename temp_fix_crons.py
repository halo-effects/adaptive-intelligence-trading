"""Fix crons: lightweight health check, re-enable memory crons."""
import json

path = r"C:\Users\Never\.openclaw\cron\jobs.json"
with open(path, encoding="utf-8") as f:
    data = json.load(f)

for job in data["jobs"]:
    # Fix Health Check: use lightweight script, only call LLM on failure
    if job["id"] == "55882b5c-f2b7-489e-aeb6-1d7a4ccc5552":
        job["enabled"] = True
        job["payload"]["message"] = (
            "Run: C:\\Users\\Never\\AppData\\Local\\Programs\\Python\\Python312\\python.exe "
            "trading/spot/healthcheck.py "
            "(working dir: C:\\Users\\Never\\.openclaw\\workspace). "
            "If exit code is 0 and no output, reply HEARTBEAT_OK. "
            "If there is output, forward it to Brett exactly as printed."
        )
        job["payload"]["timeoutSeconds"] = 60  # script runs in <5s
        job["state"]["consecutiveErrors"] = 0  # reset error counter
        print(f"Fixed: {job['name']} (lightweight script, 60s timeout)")

    # Re-enable Nightly Memory Consolidation
    elif job["id"] == "0a4002b9-0f5f-4e68-923a-14b200279f54":
        job["enabled"] = True
        job["state"]["consecutiveErrors"] = 0
        print(f"Re-enabled: {job['name']}")

    # Re-enable Weekly Memory Review
    elif job["id"] == "17e21621-62f4-4704-808d-ef1092dae59c":
        job["enabled"] = True
        job["payload"]["timeoutSeconds"] = 180  # was 300, keep reasonable
        job["state"]["consecutiveErrors"] = 0
        print(f"Re-enabled: {job['name']}")

with open(path, "w", encoding="utf-8") as f:
    json.dump(data, f, indent=4)
print("\nSaved. All changes applied.")
