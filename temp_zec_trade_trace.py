"""Trace the ZEC 5L trade to understand the 0.48% return."""
import json, os
os.chdir(r"C:\Users\Never\.openclaw\workspace")

# Load state.json to check ZEC engine state  
with open(r"trading/spot/paper/v14_portfolio/state.json") as f:
    state = json.load(f)

# Find ZEC engine
for sym, eng in state.get("engines", {}).items():
    if "ZEC" in sym:
        print(f"=== {sym} ===")
        for k, v in sorted(eng.items()):
            print(f"  {k}: {v}")
        break
else:
    print("ZEC not found in engines")

# Also look at the tracker for recent ZEC deals
tracker = state.get("tracker", {})
completed = tracker.get("completed_deals", [])
zec_deals = [d for d in completed if "ZEC" in str(d.get("symbol", ""))]
print(f"\n=== ZEC completed deals ({len(zec_deals)} total) ===")
for d in zec_deals[-3:]:
    print(d)
