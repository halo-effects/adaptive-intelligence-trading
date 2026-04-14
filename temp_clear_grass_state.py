import json, os
path = r"C:\Users\Never\.openclaw\workspace\trading\spot\live\v14pm\state.json"
with open(path) as f:
    state = json.load(f)
g = state.get("coins", {}).get("GRASS/USDT", {})
eng = g.get("engine_state", {})
coins = eng.get("long_coins", 0)
tp = g.get("tp_order_id")
print(f"GRASS state: coins={coins}, tp_order={tp}, tp_type={g.get('tp_type')}")

if coins == 0 and tp is None:
    print("Already cleared")
else:
    g["tp_order_id"] = None
    g["tp_limit_price"] = None
    g["tp_type"] = None
    g["tp_activation_price"] = None
    g["trailing_callback_pct"] = None
    for k in ["long_coins","long_avg_entry","long_layers","long_tp","long_cost"]:
        eng[k] = 0
    eng["long_trailing_active"] = False
    eng["long_trailing_peak"] = 0.0
    g["engine_state"] = eng
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        json.dump(state, f, indent=2)
    os.replace(tmp, path)
    print("State cleared")
