import json

# Check what the dashboard JS would compute
with open("docs/data/v14-pm-live/status.json") as f:
    d = json.load(f)

cap = d.get("seed_capital") or d.get("capital") or 0
eq = d.get("equity") or 0
rpnl = d.get("total_realized_pnl") or 0
fees = d.get("total_fees") or 0

# Compute per-coin unrealized and fees (same logic as dashboard JS)
coins = d.get("coins", {})
syms = d.get("symbols") or list(coins.keys())
coin_fees = sum((coins.get(s, {}).get("total_fees") or 0) for s in syms)
total_fees = max(fees, coin_fees)
total_upnl = sum((coins.get(s, {}).get("unrealized_pnl") or 0) for s in syms)
total_inv = sum((coins.get(s, {}).get("invested") or 0) for s in syms)

net_pnl = rpnl - total_fees + total_upnl
growth_pct = (net_pnl / cap * 100) if cap > 0 else 0

print("=== DASHBOARD COMPUTATION (live) ===")
print(f"  seed_capital (cap): ${cap}")
print(f"  equity:             ${eq}")
print(f"  total_realized_pnl: ${rpnl}")
print(f"  total_fees:         ${total_fees}")
print(f"  total_upnl:         ${total_upnl}")
print(f"  total_invested:     ${total_inv}")
print()
print(f"  netPnl = rpnl - fees + upnl = {rpnl} - {total_fees} + {total_upnl} = ${net_pnl:.2f}")
print(f"  growthPct = netPnl / cap * 100 = {net_pnl:.2f} / {cap} * 100 = {growth_pct:.2f}%")
print()
print(f"  Dashboard shows: -1.94%")
print(f"  Should show:     {growth_pct:.2f}%")
print()
print(f"  Actual growth from $300 to ${eq}: +{(eq-300)/300*100:.2f}%")
print()

# Check avg daily ROI
# dashboard: (eq - cap) / cap * 100 / days
# But what's "days"? Check trades
import csv
with open("docs/data/v14-pm-live/trades.csv") as f:
    trades = list(csv.DictReader(f))
print(f"  Dashboard trades.csv: {len(trades)} trades")
if trades:
    first_date = trades[0].get("close_time", "")
    last_date = trades[-1].get("close_time", "")
    print(f"  First trade: {first_date}")
    print(f"  Last trade:  {last_date}")
