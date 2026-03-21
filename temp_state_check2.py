import json
with open(r"C:\Users\Never\.openclaw\workspace\trading\spot\live\v14pm\state.json") as f:
    state = json.load(f)
print("Top-level keys:", list(state.keys()))
for k, v in state.items():
    if isinstance(v, dict):
        print(f"\n{k} keys: {list(v.keys())[:10]}")
        if k == "coins":
            for sym, cv in v.items():
                print(f"  {sym} keys: {list(cv.keys())[:15]}")
                eng = cv.get("engine_snapshot", {})
                if eng:
                    print(f"    engine long_coins={eng.get('long_coins')} long_cost={eng.get('long_cost')}")
                    print(f"    engine long_avg_entry={eng.get('long_avg_entry')} long_layers={eng.get('long_layers')}")
                    print(f"    engine capital={eng.get('capital')}")
    elif isinstance(v, list):
        print(f"\n{k}: list of {len(v)} items")
    else:
        print(f"\n{k}: {v}")
