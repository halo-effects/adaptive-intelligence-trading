import json

# Local status.json
with open(r"C:\Users\Never\.openclaw\workspace\trading\spot\live\v14pm\status.json") as f:
    data = json.load(f)
print("Local status.json last_update:", data.get("last_update"))
for sym, c in data.get("coins", {}).items():
    if c.get("layers", 0) > 0:
        print(f"  {sym}: tp_type={c.get('tp_type')}, callback={c.get('trailing_callback_pct')}, activation={c.get('tp_activation_price')}")

# Check what's in the sync repo
import os
sync_path = os.path.join(os.environ["TEMP"], "ait-dashboard-sync", "docs", "data", "v14-pm-live", "status.json")
if os.path.exists(sync_path):
    with open(sync_path) as f:
        sync = json.load(f)
    print("\nSync repo status.json last_update:", sync.get("last_update"))
    for sym, c in sync.get("coins", {}).items():
        if c.get("layers", 0) > 0:
            print(f"  {sym}: tp_type={c.get('tp_type')}, callback={c.get('trailing_callback_pct')}")
else:
    print("\nSync repo status.json not found")

# Check which dashboard the live bot uses
print("\nDashboard file:", "d-984ae0d4ab9dc1a5.html")
