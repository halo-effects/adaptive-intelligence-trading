import json

state_path = r"C:\Users\Never\.openclaw\workspace\trading\spot\paper\v14_portfolio\state.json"
with open(state_path) as f:
    state = json.load(f)

router = state.get("router", {})
print("=== ROUTER STATE (current) ===")
for k in ["total_equity", "active_pool_total", "active_pool_cash", 
           "reserve_pool_total", "reserve_pool_cash"]:
    print(f"  {k}: ${router.get(k, 0):.2f}")

print("\n  Active allocations:")
for sym, amt in sorted(router.get("active_allocations", {}).items()):
    if amt > 0:
        print(f"    {sym}: ${amt:.2f}")

print("\n  Reserve allocations:")
for sym, amt in sorted(router.get("reserve_allocations", {}).items()):
    if amt > 0:
        print(f"    {sym}: ${amt:.2f}")

print("\n=== COIN STATES ===")
coins = state.get("coins", {})
for sym, cs in sorted(coins.items()):
    alloc = cs.get("allocated_capital", 0)
    eng = cs.get("engine_state", {})
    layers = eng.get("long_layers", 0)
    coins_held = eng.get("long_coins", 0)
    cost = eng.get("long_cost", 0)
    avg = cost / coins_held if coins_held > 0 else 0
    cap = eng.get("capital", 0)
    tp = avg * 1.015 if avg > 0 else 0
    print(f"  {sym:12s} alloc=${alloc:>9.2f} | layers={layers:>2} | "
          f"cost=${cost:>10.2f} | avg=${avg:>8.2f} | TP=${tp:>8.2f} | eng_cap=${cap:>10.2f}")

# Now check the status.json for the timestamp of the TAO crash
# Also check bot.log for capital state around Apr 9-10
print("\n=== LOOKING FOR TAO DEAL HISTORY ===")
# Check if there's deal history in state
deals = state.get("deals", [])
tracker = state.get("tracker", {})
open_deals = tracker.get("_open_deals", {}) if tracker else {}
print(f"Open deals: {json.dumps(open_deals, indent=2, default=str)}")
