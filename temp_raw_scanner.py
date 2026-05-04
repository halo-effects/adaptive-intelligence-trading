import json

with open(r"C:\Users\Never\.openclaw\workspace\docs\data\v14\cycle_scanner.json", encoding="utf-8") as f:
    data = json.load(f)

# Show the 30d window structure
w30 = data.get("windows", {}).get("30d", {})
print(f"30d window type: {type(w30)}")
if isinstance(w30, dict):
    print(f"Keys: {list(w30.keys())[:5]}")
    first_key = list(w30.keys())[0] if w30 else None
    if first_key:
        print(f"First entry ({first_key}): {json.dumps(w30[first_key], indent=2)[:500]}")
elif isinstance(w30, list):
    print(f"Length: {len(w30)}")
    if w30:
        print(f"First: {json.dumps(w30[0], indent=2)[:500]}")

# Also check the trend_scores structure more carefully
ts = data.get("trend_scores", {})
first_ts = list(ts.items())[0] if ts else None
if first_ts:
    print(f"\nTrend score sample ({first_ts[0]}): {json.dumps(first_ts[1], indent=2)[:500]}")

# Check liquidity
lf = data.get("liquidity_filter", {})
print(f"\nLiquidity filter keys: {list(lf.keys())}")
for k, v in lf.items():
    if isinstance(v, list):
        print(f"  {k}: {len(v)} items, first: {v[0] if v else 'empty'}")
    else:
        print(f"  {k}: {v}")
