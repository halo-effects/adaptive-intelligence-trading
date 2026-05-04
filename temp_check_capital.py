import json
with open(r"C:\Users\Never\.openclaw\workspace\trading\spot\live\v14pm\state.json", encoding="utf-8") as f:
    state = json.load(f)
print(f"Capital: {state.get('capital')}")
print(f"Tracked capital: {state.get('tracked_capital')}")
