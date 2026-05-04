import json

with open(r"C:\Users\Never\.openclaw\workspace\trading\spot\paper\v14_portfolio\status.json") as f:
    d = json.load(f)

print(f"Cash: ${d['cash']:,.2f}")
print(f"Equity: ${d['equity']:,.2f}")
print(f"Capital: ${d['capital']:,.2f}")
print(f"Router active_cash: ${d['router']['active_cash']:,.2f}")
print(f"Router reserve_cash: ${d['router']['reserve_cash']:,.2f}")
print(f"Total allocated (active): ${d['router']['total_active_allocated']:,.2f}")
print(f"Total allocated (reserve): ${d['router']['total_reserve_allocated']:,.2f}")
print()

total_invested = 0
for sym, coin in d.get("coins", {}).items():
    inv = coin.get("invested", 0)
    layers = coin.get("layers", coin.get("long_layers", 0))
    unrealized = coin.get("unrealized_pnl", 0)
    phase = coin.get("lifecycle_phase", "?")
    total_invested += inv
    if inv > 0 or layers > 0:
        print(f"  {sym}: invested=${inv:,.2f}, layers={layers}, unrealized=${unrealized:,.2f}, phase={phase}")

print(f"\nTotal invested: ${total_invested:,.2f}")
print(f"Capital + router cash: ${d['capital'] + d['router']['active_cash'] + d['router']['reserve_cash']:,.2f}")
