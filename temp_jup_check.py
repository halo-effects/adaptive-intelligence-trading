import json

with open(r"C:\Users\Never\.openclaw\workspace\trading\spot\paper\v14_portfolio\status.json") as f:
    d = json.load(f)

jup = d.get("coins", {}).get("JUP/USDT", {})
print("=== JUP/USDT ===")
print(f"  Layers: {jup.get('layers')}")
print(f"  Avg entry: ${jup.get('avg_entry', 0):.6f}")
print(f"  Current: ${jup.get('current_price', 0):.6f}")
print(f"  TP: ${jup.get('next_tp_price', 0):.6f}")
print(f"  Invested: ${jup.get('invested', 0):,.2f}")
print(f"  Unrealized: ${jup.get('unrealized_pnl', 0):,.2f}")

entry = jup.get('avg_entry', 0)
tp = jup.get('next_tp_price', 0)
current = jup.get('current_price', 0)
if entry and tp:
    dist = (tp - current) / current * 100
    print(f"  Distance to TP: {dist:.2f}%")
    print(f"  {'LIKELY TO CLOSE SOON' if dist < 0.5 else 'Still some distance'}")

# Check total cash after JUP closes
total_inv = sum(c.get("invested", 0) for c in d.get("coins", {}).values() if c.get("layers", 0) > 0)
capital = d.get("capital", 0)
realized = d.get("total_realized_pnl", 0)
fees = d.get("total_fees", 0)
jup_inv = jup.get("invested", 0)
jup_pnl = jup.get("unrealized_pnl", 0)
cash_after = capital + realized + jup_pnl - fees - (total_inv - jup_inv)
print(f"\n  Cash AFTER JUP closes (est): ${cash_after:,.2f}")
