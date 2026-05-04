import json

# Paper PM status
with open(r"C:\Users\Never\.openclaw\workspace\trading\spot\paper\v14_portfolio\status.json") as f:
    data = json.load(f)

print(f"Last update: {data.get('last_update')}")
print(f"Equity: ${data.get('equity'):,.0f}")

# Check if any coins have tp_type field
for sym, c in data.get("coins", {}).items():
    if c.get("layers", 0) > 0:
        tp_type = c.get("tp_type", "NOT SET")
        tp = c.get("next_tp_price", 0)
        callback = c.get("trailing_callback_pct", "NOT SET")
        print(f"  {sym}: L{c['layers']}, tp_type={tp_type}, callback={callback}, tp={tp}")

# Check which dashboard file the paper PM uses
print("\nPaper PM dashboard: dashboardV14PM.html")

# Check sync freshness
import os
sync_pm = os.path.join(os.environ["TEMP"], "ait-dashboard-sync", "docs", "data", "v14-pm", "status.json")
if os.path.exists(sync_pm):
    ts = os.path.getmtime(sync_pm)
    from datetime import datetime
    print(f"Sync repo v14-pm/status.json: {datetime.fromtimestamp(ts)}")
else:
    print("Sync repo v14-pm/status.json: NOT FOUND")
