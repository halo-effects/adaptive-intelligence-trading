import json, csv

# Dashboard data (what GitHub Pages serves)
with open("docs/data/v14-pm/status.json") as f:
    d = json.load(f)

print("=== DASHBOARD status.json (docs/data/v14-pm/) ===")
for k in ["seed_capital", "equity", "capital", "total_realized_pnl", "deals_completed", "win_rate"]:
    print(f"  {k}: {d.get(k)}")

print()
with open("docs/data/v14-pm/trades.csv") as f:
    trades = list(csv.DictReader(f))
total_pnl = sum(float(t.get("pnl", 0) or 0) for t in trades)
print(f"  Dashboard CSV trades: {len(trades)}")
print(f"  Dashboard CSV PnL: ${total_pnl:.2f}")

print()
print("=== PAPER BOT status.json (source of truth) ===")
with open("trading/spot/paper/v14_portfolio/status.json") as f:
    d2 = json.load(f)
for k in ["seed_capital", "equity", "capital", "total_realized_pnl", "deals_completed", "win_rate"]:
    print(f"  {k}: {d2.get(k)}")

# The dashboard reads realized PnL from status.json, not from the CSV
# But trades/wins/losses come from the CSV
# If dashboard shows $3,823 realized PnL, that's from an OLD status.json
# The sync copies paper/v14_portfolio/status.json -> docs/data/v14-pm/status.json
print()
print("=== MISMATCH CHECK ===")
dash_pnl = d.get("total_realized_pnl", 0)
src_pnl = d2.get("total_realized_pnl", 0)
print(f"  Dashboard PnL: {dash_pnl}")
print(f"  Source PnL:    {src_pnl}")
if abs(dash_pnl - src_pnl) > 1:
    print(f"  !! Dashboard is STALE. Needs sync.")
else:
    print(f"  OK - in sync")
