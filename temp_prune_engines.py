"""Prune idle engines down to 3 coins: TAO + JTO (active) + top scanner coin."""
import json, os

# 1. Check scanner for top-ranked coin (excluding TAO, JTO)
scanner_path = r"C:\Users\Never\.openclaw\workspace\docs\data\v14\cycle_scanner.json"
with open(scanner_path) as f:
    scanner = json.load(f)

rankings = scanner.get("rankings", []) or scanner.get("coins", [])
active_bases = {"TAO", "JTO"}

print("Scanner top 10:")
for i, r in enumerate(rankings[:10]):
    coin = r.get("coin", r.get("symbol", "?"))
    score = r.get("dca_score", 0)
    trend = r.get("trend_multiplier", 1.0)
    adj = float(score) * float(trend)
    marker = " <-- ACTIVE" if coin in active_bases else ""
    print(f"  {i+1}. {coin}: score={score}, trend={trend}, adj={adj:.1f}{marker}")

# Find top qualifying coin not in active set
top_pick = None
for r in rankings:
    coin = r.get("coin", r.get("symbol", "?"))
    score = float(r.get("dca_score", 0))
    if coin not in active_bases and score >= 5.0:
        top_pick = coin
        break

print(f"\nTop pick for 3rd slot: {top_pick}")
keep_symbols = {"TAO/USDT", "JTO/USDT"}
if top_pick:
    keep_symbols.add(f"{top_pick}/USDT")

print(f"Keeping: {keep_symbols}")

# 2. Prune state.json
state_path = r"C:\Users\Never\.openclaw\workspace\trading\spot\live\v14pm\state.json"
with open(state_path) as f:
    state = json.load(f)

coins = state.get("coins", {})
to_remove = []
for sym, cs in coins.items():
    if sym not in keep_symbols:
        eng = cs.get("engine_state", {})
        has_position = eng.get("long_coins", 0) > 0 or eng.get("short_coins", 0) > 0
        if has_position:
            print(f"  WARNING: {sym} has open position, NOT removing")
        else:
            to_remove.append(sym)
            print(f"  Removing idle engine: {sym}")

for sym in to_remove:
    del coins[sym]

# 3. Reallocate capital among 3 coins
# At $374 equity, 3-coin tier, 90/10 split = $337 active pool
# Equal split for now since rebalance will adjust on next daily
tracked = state.get("tracked_capital", 374)
active_pool = tracked * 0.9  # 90/10 split
per_coin = active_pool / len(keep_symbols)

print(f"\nCapital: ${tracked:.2f}, active pool: ${active_pool:.2f}, per coin: ${per_coin:.2f}")

for sym in keep_symbols:
    if sym in coins:
        coins[sym]["allocated_capital"] = per_coin
        eng = coins[sym].get("engine_state", {})
        # Only update engine capital if no position (avoid messing with active deals)
        if eng.get("long_coins", 0) == 0 and eng.get("short_coins", 0) == 0:
            eng["capital"] = per_coin
            print(f"  {sym}: alloc=${per_coin:.2f}, engine capital updated")
        else:
            print(f"  {sym}: alloc=${per_coin:.2f}, engine capital unchanged (has position)")
    else:
        # New engine placeholder — bot will create on next tick
        print(f"  {sym}: NOT in state yet — bot will create on next rebalance")

# Save
tmp = state_path + ".tmp"
with open(tmp, "w") as f:
    json.dump(state, f, indent=2)
os.replace(tmp, state_path)
print("\nState file saved")
print(f"Remaining engines: {list(coins.keys())}")
