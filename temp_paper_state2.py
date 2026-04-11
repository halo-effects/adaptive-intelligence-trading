import json

# Check engine_state.json for the PM paper bot
state_path = r"C:\Users\Never\.openclaw\workspace\trading\spot\paper\v14_portfolio\engine_state.json"
with open(state_path) as f:
    state = json.load(f)

# Print top-level keys
print("Top-level keys:", list(state.keys()))
print()

# Check for router/capital info
if "router" in state:
    router = state["router"]
    print("=== ROUTER ===")
    for k, v in router.items():
        if isinstance(v, (int, float)):
            print(f"  {k}: ${v:.2f}")
        elif isinstance(v, dict) and len(v) < 20:
            print(f"  {k}: {json.dumps(v, indent=4)}")
        else:
            print(f"  {k}: {type(v).__name__}")

# Check coins/engines
for key in ["coins", "engines", "coin_states", "symbols"]:
    if key in state:
        data = state[key]
        print(f"\n=== {key.upper()} ({len(data)} entries) ===")
        if isinstance(data, dict):
            for sym, info in sorted(data.items()):
                if isinstance(info, dict):
                    layers = info.get("long_layers", info.get("layers", "?"))
                    cost = info.get("long_cost", info.get("cost", 0))
                    coins = info.get("long_coins", info.get("coins", 0))
                    cap = info.get("capital", info.get("allocated_capital", "?"))
                    avg = cost / coins if coins and coins > 0 else 0
                    print(f"  {sym:12s} layers={layers} cost=${cost:.0f} avg=${avg:.2f} capital={cap}")

# Also check status.json for equity/capital info
status_path = r"C:\Users\Never\.openclaw\workspace\trading\spot\paper\v14_portfolio\status.json"
with open(status_path) as f:
    status = json.load(f)
print("\n=== STATUS.JSON ===")
for k in ["equity", "initial_capital", "cash", "total_invested", "running",
           "active_coins", "timestamp", "halted", "max_drawdown_pct"]:
    if k in status:
        print(f"  {k}: {status[k]}")

# Check for deals/trade log
if "completed_deals" in state:
    deals = state["completed_deals"]
    print(f"\n=== COMPLETED DEALS: {len(deals)} ===")
elif "tracker" in state:
    tracker = state["tracker"]
    print(f"\n=== TRACKER ===")
    for k, v in tracker.items():
        if isinstance(v, (int, float, str)):
            print(f"  {k}: {v}")
        elif isinstance(v, dict):
            print(f"  {k}: {len(v)} entries")
        elif isinstance(v, list):
            print(f"  {k}: {len(v)} items")
