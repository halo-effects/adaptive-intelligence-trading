import json

# Live PM status (source of truth)
with open(r"C:\Users\Never\.openclaw\workspace\trading\spot\live\v14pm\status.json") as f:
    live = json.load(f)
print("=== Live PM status.json ===")
for k in ["equity", "capital", "pnl_pct", "cash", "mode", "running", "bot_state"]:
    print(f"  {k}: {live.get(k)}")
eb = live.get("exchange_balance", {})
print(f"  exchange_balance: free={eb.get('usdt_free')}, total={eb.get('usdt_total')}")
coins = live.get("coins", {})
for sym, v in coins.items():
    print(f"  {sym}:")
    for fld in ["layers", "invested", "avg_entry", "next_tp_price", "unrealized_pnl", 
                "current_price", "side", "realized_pnl", "tp_order_id"]:
        print(f"    {fld}: {v.get(fld)}")
router = live.get("router", {})
print(f"  router: active_cash={router.get('active_cash')}, reserve_cash={router.get('reserve_cash')}")

# Dashboard synced data
print("\n=== Dashboard v14-pm/status.json ===")
with open(r"C:\Users\Never\.openclaw\workspace\docs\data\v14-pm\status.json") as f:
    dash = json.load(f)
for k in ["equity", "capital", "pnl_pct", "mode"]:
    print(f"  {k}: {dash.get(k)}")

# Paper PM (for comparison - dashboard may show this instead)
print("\n=== Paper PM status.json ===")
with open(r"C:\Users\Never\.openclaw\workspace\trading\spot\paper\v14_portfolio\status.json") as f:
    paper = json.load(f)
for k in ["equity", "capital", "pnl_pct", "mode"]:
    print(f"  {k}: {paper.get(k)}")

# Check sync script routing
print("\n=== Sync script routing ===")
import os
live_age = os.path.getmtime(r"C:\Users\Never\.openclaw\workspace\trading\spot\live\v14pm\status.json")
paper_age = os.path.getmtime(r"C:\Users\Never\.openclaw\workspace\trading\spot\paper\v14_portfolio\status.json")
dash_age = os.path.getmtime(r"C:\Users\Never\.openclaw\workspace\docs\data\v14-pm\status.json")
import time
now = time.time()
print(f"  Live PM status age: {(now - live_age):.0f}s")
print(f"  Paper PM status age: {(now - paper_age):.0f}s")
print(f"  Dashboard data age: {(now - dash_age):.0f}s")
