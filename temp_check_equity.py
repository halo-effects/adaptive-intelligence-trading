import csv, json

# Check true equity
csv_pnl = 0
today_pnl = 0
today_count = 0
with open(r"C:\Users\Never\.openclaw\workspace\trading\spot\paper\v14_portfolio\trades.csv") as f:
    for row in csv.DictReader(f):
        pnl = float(row["pnl"])
        csv_pnl += pnl
        rt = row.get("recorded_at", "")
        if "2026-03-19" in rt or "2026-03-20" in rt:
            today_pnl += pnl
            today_count += 1
            print(f"  {row['symbol']}: L{row['layers']}, pnl=${pnl:.2f}")

with open(r"C:\Users\Never\.openclaw\workspace\trading\spot\paper\v14_portfolio\status.json") as f:
    s = json.load(f)

coins = s.get("coins", {})
fees = sum(v.get("total_fees", 0) or 0 for v in coins.values())
unrealized = sum(v.get("unrealized_pnl", 0) or 0 for v in coins.values())

capital = 50000
correct = capital + csv_pnl - fees + unrealized
status_eq = s.get("equity")

print(f"\nToday: {today_count} trades, PnL: ${today_pnl:.2f}")
print(f"All-time CSV PnL: ${csv_pnl:.2f}")
print(f"Fees: ${fees:.2f}")
print(f"Unrealized: ${unrealized:.2f}")
print(f"\nTrue equity = {capital} + {csv_pnl:.2f} - {fees:.2f} + ({unrealized:.2f})")
print(f"           = ${correct:.2f}")
print(f"Status equity: ${status_eq}")
print(f"Difference: ${status_eq - correct:.2f}")
print(f"\nYesterday equity was ~$53,100 (+6.2%)")
print(f"Expected today: $53,100 + ${today_pnl:.2f} = ${53100 + today_pnl:.2f}")
print(f"Actual today: ${status_eq}")
print(f"Extra growth: ${status_eq - (53100 + today_pnl):.2f}")
