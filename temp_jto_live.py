import json

with open(r"C:\Users\Never\.openclaw\workspace\trading\spot\live\v14pm\status.json") as f:
    d = json.load(f)

jto = d.get("coins", {}).get("JTO/USDT", {})
print("=== JTO/USDT Live Bot ===")
for k, v in jto.items():
    print(f"  {k}: {v}")

print(f"\nLast update: {d.get('last_update', '?')[:19]}")
print(f"Deals completed: {d.get('deals_completed', '?')}")
print(f"Equity: ${d.get('equity', 0):.2f}")
