import json
with open(r"C:\Users\Never\.openclaw\workspace\trading\spot\live\v14pm\status.json") as f:
    s = json.load(f)
for sym in ["TAO/USDT", "JTO/USDT", "HYPE/USDT", "ZEC/USDT", "FET/USDT"]:
    c = s.get("coins", {}).get(sym, {})
    if not c:
        print(f"{sym}: not in status.json")
        continue
    print(f"{sym}:")
    print(f"  tp_type: {c.get('tp_type', 'NOT SET')}")
    print(f"  next_tp_price: {c.get('next_tp_price', 'NOT SET')}")
    print(f"  trailing_callback_pct: {c.get('trailing_callback_pct', 'NOT SET')}")
    print(f"  layers: {c.get('layers', '?')}")
    print()
