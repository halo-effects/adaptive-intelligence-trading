import json

with open(r"C:\Users\Never\.openclaw\workspace\trading\spot\paper\v14_portfolio\status.json") as f:
    d = json.load(f)

coins = d.get("coins", {})
total_inv = sum(c.get("invested", 0) for c in coins.values() if c.get("layers", 0) > 0)
active = [(sym, c.get("layers", 0), c.get("invested", 0)) for sym, c in coins.items() if c.get("layers", 0) > 0]
active.sort(key=lambda x: -x[2])

capital = d.get("capital", 0)
realized = d.get("total_realized_pnl", 0)
fees = d.get("total_fees", 0)
available = capital + realized - fees
cash = available - total_inv

print(f"Capital: ${capital:,.2f}")
print(f"Realized PnL: ${realized:,.2f}")
print(f"Total fees: ${fees:,.2f}")
print(f"Available: ${available:,.2f}")
print(f"Total invested: ${total_inv:,.2f}")
print(f"Cash: ${cash:,.2f}")
print(f"Utilization: {total_inv/available*100:.1f}%")
print(f"Equity: ${d.get('equity', 0):,.2f}")
print(f"Deals: {d.get('deals_completed', 0)}")
print(f"\nActive positions ({len(active)}):")
for sym, layers, inv in active:
    print(f"  {sym}: L{layers}, ${inv:,.2f}")
