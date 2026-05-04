import json

with open(r"C:\Users\Never\.openclaw\workspace\trading\spot\live\v14pm\status.json") as f:
    d = json.load(f)

print(f"Capital: ${d.get('capital', 0):.2f}")
print(f"Equity: ${d.get('equity', 0):.2f}")
print(f"PnL: {d.get('pnl_pct', 0):.2f}%")
print(f"Deals: {d.get('deals_completed', 0)}, WR: {d.get('win_rate', 0):.1f}%")
print()

# Check allocations and engine capitals
for sym, coin in d.get("coins", {}).items():
    alloc = coin.get("allocated_capital", 0)
    invested = coin.get("invested", 0)
    eng_cap = coin.get("engine_capital", coin.get("capital", 0))
    layers = coin.get("layers", coin.get("long_layers", 0))
    unrealized = coin.get("unrealized_pnl", 0)
    print(f"  {sym}: alloc=${alloc:.2f}, eng_cap=${eng_cap:.2f}, invested=${invested:.2f}, layers={layers}, unrealized=${unrealized:.2f}")

# Check recent trades
print()
print("Recent trades from trades.csv:")
import csv
from pathlib import Path
csv_path = Path(r"C:\Users\Never\.openclaw\workspace\trading\spot\live\v14pm\trades.csv")
if csv_path.exists():
    with open(csv_path) as f:
        trades = list(csv.DictReader(f))
    for t in trades[-10:]:
        print(f"  {t.get('symbol','?')}: invested=${float(t.get('invested',0)):.2f}, pnl=${float(t.get('pnl',0)):.2f} ({float(t.get('return_pct',0)):.2f}%), layers={t.get('layers','?')}")
else:
    print("  No trades.csv found")

# Check DCA profile
print()
router = d.get("router", {})
print(f"Router active_cash: ${router.get('active_cash', 0):.2f}")
print(f"Router reserve_cash: ${router.get('reserve_cash', 0):.2f}")
