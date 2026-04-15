import json, os
path = r"C:\Users\Never\.openclaw\workspace\trading\spot\live\v14pm\state.json"
with open(path) as f:
    state = json.load(f)

keep = {"TAO/USDT", "HYPE/USDT", "JTO/USDT"}
coins = state.get("coins", {})
before = list(coins.keys())
for s in [k for k in coins if k not in keep]:
    del coins[s]

tracked = state.get("tracked_capital", 374)
active_pool = tracked * 0.9
per_coin = active_pool / max(len(keep), 1)
for sym in keep:
    if sym in coins:
        coins[sym]["allocated_capital"] = per_coin

tmp = path + ".tmp"
with open(tmp, "w") as f:
    json.dump(state, f, indent=2)
os.replace(tmp, path)
print(f"Before: {before}")
print(f"After: {list(coins.keys())}")
print(f"Per-coin: ${per_coin:.2f}")
