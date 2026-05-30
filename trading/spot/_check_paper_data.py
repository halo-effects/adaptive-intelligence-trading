import json, csv

with open("trading/spot/paper/v14_portfolio/status.json") as f:
    d = json.load(f)

print("=== PAPER STATUS.JSON ===")
for k in ["seed_capital", "equity", "capital", "total_realized_pnl", "deals_completed", "win_rate"]:
    print(f"  {k}: {d.get(k)}")

print()
print("=== PAPER TRADES.CSV ===")
with open("trading/spot/paper/v14_portfolio/trades.csv") as f:
    trades = list(csv.DictReader(f))
print(f"  Total trades: {len(trades)}")
total_pnl = sum(float(t.get("pnl", 0) or 0) for t in trades)
wins = sum(1 for t in trades if float(t.get("pnl", 0) or 0) > 0)
losses = sum(1 for t in trades if float(t.get("pnl", 0) or 0) <= 0)
print(f"  CSV total PnL: ${total_pnl:.2f}")
print(f"  Wins: {wins}, Losses: {losses}")

# The dashboard shows 750 trades, 748W/2L, $3,823 realized PnL
# But CSV should have $50K PnL. Let's check the discrepancy.
# The status.json total_realized_pnl is what the dashboard reads for "Realized PnL"
# The bot's internal counter may have been reset when it restarted

print()
print("=== ANALYSIS ===")
print(f"  CSV PnL sum:                ${total_pnl:.2f}")
print(f"  status.json realized_pnl:   ${d.get('total_realized_pnl', 0)}")
print(f"  Delta:                      ${total_pnl - (d.get('total_realized_pnl') or 0):.2f}")
print()
if abs(total_pnl - (d.get("total_realized_pnl") or 0)) > 100:
    print("  !! MISMATCH: Bot internal PnL counter doesn't match CSV")
    print("     The bot restarted with the merged CSV but its internal counter")
    print("     only accumulated PnL from trades it SAW (not historical ones)")
