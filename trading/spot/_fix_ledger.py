"""Set the capital ledger to a correct baseline state."""
import json

csv_pnl = 18.46
unrealized = -5.56
dex_total = 423.05
real_deposit = 40.0
seed = 300.0

# dark_pnl_gap = trading gains not recorded in CSV (from truncation period)
dark_pnl_gap = dex_total - seed - real_deposit - csv_pnl - unrealized
# current_capital = value such that current_capital + csv_pnl + unrealized = dex_total
# This is the baseline the cycle-to-cycle detection will use
current_capital = dex_total - csv_pnl - unrealized

ledger = {
    "seed_capital": seed,
    "current_capital": round(current_capital, 2),
    "transactions": [
        {
            "timestamp": "2026-04-15T00:00:00",
            "type": "seed",
            "amount": seed,
            "balance_after": seed,
            "note": "Initial seed capital"
        },
        {
            "timestamp": "2026-05-11T13:02:00",
            "type": "deposit",
            "amount": real_deposit,
            "balance_after": seed + real_deposit,
            "note": "Manual deposit of 40 USDT to Aster account"
        },
        {
            "timestamp": "2026-05-11T13:20:00",
            "type": "pnl_adjustment",
            "amount": round(dark_pnl_gap, 2),
            "balance_after": round(current_capital, 2),
            "note": f"Baseline adjustment: ${dark_pnl_gap:.2f} trading gains from CSV truncation period not in trades.csv"
        }
    ]
}

print(f"seed:            ${seed}")
print(f"deposit:         ${real_deposit}")
print(f"dark_pnl_gap:    ${dark_pnl_gap:.2f}")
print(f"current_capital: ${current_capital:.2f}")
print(f"expected DEX:    ${current_capital + csv_pnl + unrealized:.2f} (actual: ${dex_total})")

with open("trading/spot/live/v14pm/capital_ledger.json", "w") as f:
    json.dump(ledger, f, indent=2)
print("Ledger written successfully")
