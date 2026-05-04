import json

with open(r"C:\Users\Never\.openclaw\workspace\trading\spot\paper\v14_portfolio\engine_state.json") as f:
    state = json.load(f)

print("Engine capitals vs invested:")
total_engine_capital = 0
for sym, eng in state.get("engines", {}).items():
    cap = eng.get("initial_capital", 0)
    long_cost = eng.get("long_cost", 0)
    short_cost = eng.get("short_cost", 0)
    invested = long_cost + short_cost
    total_engine_capital += cap
    if cap > 0 or invested > 0:
        print(f"  {sym}: engine_capital=${cap:,.2f}, invested=${invested:,.2f}")

print(f"\nTotal engine capital: ${total_engine_capital:,.2f}")
print(f"\nRouter state:")
router = state.get("router", {})
print(f"  active_pool_cash: ${router.get('active_pool_cash', 0):,.2f}")
print(f"  reserve_pool_cash: ${router.get('reserve_pool_cash', 0):,.2f}")
print(f"  active_allocations: {router.get('active_allocations', {})}")
