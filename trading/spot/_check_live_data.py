import json, csv

with open("trading/spot/live/v14pm/status.json") as f:
    d = json.load(f)

print("=== STATUS.JSON ===")
print(f"  seed_capital:       ${d['seed_capital']}")
print(f"  equity:             ${d['equity']}")
print(f"  capital:            ${d['capital']}")
print(f"  tracked_capital:    ${d['tracked_capital']}")
print(f"  total_realized_pnl: ${d['total_realized_pnl']}")
print(f"  deals_completed:    {d['deals_completed']}")
print(f"  win_rate:           {d['win_rate']}%")
print(f"  invested:           ${d['invested']}")
print(f"  cash:               ${d['cash']}")

print()
print("=== TRADES.CSV ===")
with open("trading/spot/live/v14pm/trades.csv") as f:
    trades = list(csv.DictReader(f))
print(f"  Total trades: {len(trades)}")
total_csv_pnl = sum(float(t.get("pnl", 0) or 0) for t in trades)
wins = sum(1 for t in trades if float(t.get("pnl", 0) or 0) > 0)
losses = sum(1 for t in trades if float(t.get("pnl", 0) or 0) <= 0)
print(f"  CSV total PnL: ${total_csv_pnl:.2f}")
print(f"  Wins: {wins}, Losses: {losses}")

print()
print("=== EQUITY ANALYSIS ===")
# Original capital was $300
ORIGINAL_CAPITAL = 300.0
expected_equity = ORIGINAL_CAPITAL + total_csv_pnl
print(f"  Original deposit:    ${ORIGINAL_CAPITAL}")
print(f"  Expected equity:     ${expected_equity:.2f} (deposit + CSV PnL)")
print(f"  Actual equity:       ${d['equity']}")
print(f"  seed_capital:        ${d['seed_capital']} (should be {ORIGINAL_CAPITAL})")
diff = d["seed_capital"] - ORIGINAL_CAPITAL
print(f"  seed_capital drift:  ${diff:.2f}")
print()
if abs(expected_equity - d["equity"]) > 1.0:
    print(f"  !! MISMATCH: equity off by ${d['equity'] - expected_equity:.2f}")
if d["seed_capital"] != ORIGINAL_CAPITAL:
    print(f"  !! seed_capital drifted from ${ORIGINAL_CAPITAL} to ${d['seed_capital']}")
    print(f"     This makes the equity chart Y-axis start at ${d['seed_capital']} instead of ${ORIGINAL_CAPITAL}")

print()
print("=== DASHBOARD IMPACT ===")
print(f"  Chart shows equity starting at ~${d['seed_capital']:.0f} (should be $300)")
print(f"  The 'drop' on the chart is likely the bot restarting and recalculating")
print(f"  from seed_capital=${d['seed_capital']} minus current positions")

# Check equity_history / router
router = d.get("router", {})
print()
print("=== ROUTER ===")
for k in ["active_pool_total", "reserve_pool_total", "total_equity"]:
    print(f"  {k}: {router.get(k)}")
