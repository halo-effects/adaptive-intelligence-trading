"""Check RENDER status in paper PM bot."""
import json, csv
from pathlib import Path

# Status.json
with open(r"C:\Users\Never\.openclaw\workspace\trading\spot\paper\v14_portfolio\status.json") as f:
    data = json.load(f)

print(f"Last update: {data.get('last_update')}")
render = data.get("coins", {}).get("RENDER/USDT", {})
print(f"\nRENDER in status.json:")
for k, v in render.items():
    print(f"  {k}: {v}")

# Trades.csv - check for recent RENDER trades
csv_path = Path(r"C:\Users\Never\.openclaw\workspace\trading\spot\paper\v14_portfolio\trades.csv")
if csv_path.exists():
    with open(csv_path) as f:
        reader = csv.DictReader(f)
        render_trades = [r for r in reader if "RENDER" in r.get("symbol", "")]
    print(f"\nRENDER trades in CSV: {len(render_trades)}")
    for t in render_trades[-5:]:
        print(f"  Deal #{t.get('deal_id')}: close={t.get('close_time')}, pnl=${t.get('pnl')}, layers={t.get('layers')}")
else:
    print("\nNo trades.csv found")

# Check all active coins
print(f"\nAll coins with layers > 0:")
for sym, c in data.get("coins", {}).items():
    layers = c.get("layers", 0)
    invested = c.get("invested", 0)
    rpnl = c.get("realized_pnl", 0)
    if layers > 0 or invested > 0:
        print(f"  {sym}: L{layers}, invested=${invested:.2f}, realized=${rpnl:.2f}")

print(f"\nApproved symbols: {data.get('approved_symbols')}")
print(f"Deals completed: {data.get('deals_completed')}")
print(f"Total realized: ${data.get('total_realized_pnl', 0):.2f}")
