"""Clear TP order references from state.json so bot places fresh trailing stops."""
import json

path = r"C:\Users\Never\.openclaw\workspace\trading\spot\live\v14pm\state.json"
with open(path, encoding="utf-8") as f:
    state = json.load(f)

coins = state.get("coins", {})
for sym, c in coins.items():
    old_oid = c.get("tp_order_id")
    old_type = c.get("tp_type")
    if old_oid:
        print(f"{sym}: clearing tp_order_id={old_oid}, tp_type={old_type}")
        c["tp_order_id"] = None
        c["tp_type"] = "trailing"
        c["tp_activation_price"] = None
        c["trailing_callback_pct"] = 0.2

with open(path, "w", encoding="utf-8") as f:
    json.dump(state, f, indent=2)
print("State updated")
