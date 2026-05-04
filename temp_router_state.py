import json

with open(r"C:\Users\Never\.openclaw\workspace\trading\spot\paper\v14_portfolio\engine_state.json") as f:
    state = json.load(f)

router = state.get("router", {})
print("=== Saved Router State ===")
for k, v in sorted(router.items()):
    if isinstance(v, dict):
        print(f"  {k}: {len(v)} entries")
        for k2, v2 in sorted(v.items()):
            print(f"    {k2}: {v2}")
    else:
        print(f"  {k}: {v}")
