import json
with open(r"C:\Users\Never\.openclaw\workspace\trading\spot\paper\v14_portfolio\status.json") as f:
    d = json.load(f)
jto = d.get("coins", {}).get("JTO/USDT", {})
print(f"Layers: {jto.get('layers', '?')}")
print(f"Price: {jto.get('current_price', '?')}")
print(f"TP: {jto.get('next_tp_price', '?')}")
print(f"Unrealized: {jto.get('unrealized_pnl', '?')}")
print(f"Updated: {d.get('last_update', '?')[:19]}")
print(f"Deals: {d.get('deals_completed', '?')}")
