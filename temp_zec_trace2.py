"""Trace the ZEC 5L trade to understand the 0.48% return."""
import json

with open(r"C:\Users\Never\.openclaw\workspace\trading\spot\paper\v14_portfolio\engine_state.json") as f:
    state = json.load(f)

# Find ZEC engine
for sym, eng in state.get("engines", {}).items():
    if "ZEC" in sym:
        print(f"=== {sym} engine state ===")
        for k, v in sorted(eng.items()):
            if isinstance(v, dict):
                print(f"  {k}:")
                for k2, v2 in sorted(v.items()):
                    print(f"    {k2}: {v2}")
            else:
                print(f"  {k}: {v}")

# Look at the actual trades from the engine
print("\n=== All keys at top level ===")
for k in state.keys():
    if isinstance(state[k], dict):
        print(f"  {k}: dict with {len(state[k])} keys")
    elif isinstance(state[k], list):
        print(f"  {k}: list with {len(state[k])} items")
    else:
        print(f"  {k}: {state[k]}")
