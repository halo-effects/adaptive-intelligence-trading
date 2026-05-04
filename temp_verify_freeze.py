import json

with open(r"C:\Users\Never\.openclaw\workspace\trading\spot\paper\v14_portfolio\status.json") as f:
    d = json.load(f)

invested = sum(c.get("invested", 0) for c in d.get("coins", {}).values() if c.get("layers", 0) > 0)
available = d.get("capital", 0) + d.get("total_realized_pnl", 0) - d.get("total_fees", 0)
cash = available - invested
active = sum(1 for c in d.get("coins", {}).values() if c.get("layers", 0) > 0)
utilization = (invested / available * 100) if available > 0 else 0

print(f"Equity: ${d.get('equity', 0):,.2f}")
print(f"Available capital: ${available:,.2f}")
print(f"Total invested: ${invested:,.2f}")
print(f"Cash: ${cash:,.2f}")
print(f"Utilization: {utilization:.1f}%")
print(f"Active coins: {active}")
print(f"Last update: {d.get('last_update', '?')[:19]}")
print(f"\nStatus: {'FROZEN (no new buys)' if cash < 0 else 'NORMAL'}")
