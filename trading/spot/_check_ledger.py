import json

with open("trading/spot/live/v14pm/capital_ledger.json") as f:
    d = json.load(f)

print(f"seed_capital:    ${d.get('seed_capital')}")
print(f"current_capital: ${d.get('current_capital')}")
print()
print("Transactions:")
for t in d.get("transactions", []):
    ts = t.get("timestamp", "?")[:19]
    typ = t.get("type", "?")
    amt = t.get("amount", 0)
    bal = t.get("balance_after", 0)
    note = t.get("note", "")
    print(f"  {ts} | {typ:12s} | ${amt:>10.2f} | bal=${bal:.2f} | {note}")
