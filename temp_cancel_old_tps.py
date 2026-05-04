"""Cancel existing 0.5% trailing stop orders so bot can place fresh 0.25% ones on startup."""
import json, os, sys
sys.path.insert(0, r"C:\Users\Never\.openclaw\workspace")

# Read current state
state_path = r"C:\Users\Never\.openclaw\workspace\trading\spot\live\v14pm\state.json"
with open(state_path, encoding="utf-8") as f:
    state = json.load(f)

# Show current TP orders
tp_orders = {}
for sym, cs in state.get("coins", {}).items():
    tp_id = cs.get("tp_order_id")
    cb = cs.get("trailing_callback_pct", 0)
    act = cs.get("tp_activation_price")
    tp_type = cs.get("tp_type", "limit")
    print(f"{sym}: TP order={tp_id}, type={tp_type}, callback={cb}%, activation=${act}")
    if tp_id:
        tp_orders[sym] = tp_id

# Clear TP order IDs in state so bot places fresh ones on startup
for sym, cs in state.get("coins", {}).items():
    cs["tp_order_id"] = None
    cs["trailing_callback_pct"] = 0.25  # New value
    print(f"  → Cleared TP order for {sym}, set callback to 0.25%")

# Save state
with open(state_path, "w", encoding="utf-8") as f:
    json.dump(state, f, indent=2)
print(f"\nState saved. Bot will place fresh 0.25% trailing stops on startup.")
print(f"\nTP orders to cancel on exchange: {list(tp_orders.values())}")
