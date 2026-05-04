"""Show scanner results."""
import json

with open(r"C:\Users\Never\.openclaw\workspace\docs\data\v14\cycle_scanner.json", encoding="utf-8") as f:
    data = json.load(f)

print(f"Generated: {data.get('generated_at')}")
print(f"Scanned: {data.get('coins_scanned')}")

# Check structure of top_picks
tp = data.get("top_picks", {})
for window, val in tp.items():
    print(f"\n--- {window} ---")
    print(f"  Type: {type(val)}")
    if isinstance(val, str):
        print(f"  Value: {val}")
    elif isinstance(val, list):
        print(f"  Count: {len(val)}")
        if val and isinstance(val[0], str):
            print(f"  Values: {val[:5]}")

# Check windows (the actual score data)
windows = data.get("windows", {})
print(f"\nWindows: {list(windows.keys())}")
for wname, wdata in windows.items():
    coins = wdata if isinstance(wdata, dict) else {}
    if isinstance(wdata, list):
        coins = {c.get("symbol", str(i)): c for i, c in enumerate(wdata)}
    
    # Sort by score
    scored = sorted(coins.items(), key=lambda kv: (kv[1].get("dca_score", 0) if isinstance(kv[1], dict) else 0), reverse=True)
    
    print(f"\n=== {wname} (top 10) ===")
    above = 0
    for sym, d in scored[:15]:
        if isinstance(d, dict):
            score = d.get("dca_score", 0)
            dpw = d.get("deals_per_week", 0)
            if score >= 5.0: above += 1
            mark = " <<" if score >= 5.0 else ""
            print(f"  {sym:<10} score={score:>6.1f}  dpw={dpw:>5.1f}{mark}")
    print(f"  Above 5.0 hurdle: {above}")

# Trend scores
ts = data.get("trend_scores", {})
if ts:
    print(f"\nTrend scores (top 10):")
    ranked = sorted(ts.items(), key=lambda kv: kv[1].get("adjusted_score", kv[1].get("score", 0)), reverse=True)
    above_t = 0
    for sym, d in ranked[:15]:
        adj = d.get("adjusted_score", d.get("score", 0))
        base = d.get("base_score", d.get("dca_score", 0))
        mult = d.get("trend_multiplier", d.get("multiplier", 1.0))
        if adj >= 5.0: above_t += 1
        mark = " <<" if adj >= 5.0 else ""
        print(f"  {sym:<10} base={base:>6.1f} x{mult:.2f} = {adj:>6.1f}{mark}")
    print(f"  Above 5.0 hurdle: {above_t}")
