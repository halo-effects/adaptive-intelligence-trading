import json

with open(r"C:\Users\Never\.openclaw\workspace\trading\spot\paper\v14_portfolio\state.json", encoding="utf-8") as f:
    state = json.load(f)

engines = state.get("engines", {})
print(f"Active engines: {len(engines)}")
for sym, eng in engines.items():
    layers = eng.get("long_layers", 0)
    cost = eng.get("long_cost", 0)
    avg = eng.get("long_avg_entry", 0)
    tp = eng.get("long_tp", 0)
    print(f"  {sym}: L{layers}, cost=${cost:.0f}, avg={avg:.6f}, tp={tp:.6f}")

tier = state.get("tier", state.get("coin_cap", state.get("max_coins", "?")))
print(f"Tier/coin cap: {tier}")

eq = state.get("equity", state.get("total_equity", 0))
cap = state.get("capital", 0)
print(f"Equity: ${eq:,.0f}, Capital: ${cap:,.0f}")

# Check if rebalance has happened since restart
alloc = state.get("allocations", state.get("coin_allocations", {}))
print(f"\nAllocations: {len(alloc)} coins")
for sym, a in alloc.items():
    if isinstance(a, dict):
        print(f"  {sym}: ${a.get('capital', 0):,.0f}")
    else:
        print(f"  {sym}: {a}")
