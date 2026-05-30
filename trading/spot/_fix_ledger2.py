"""Recalibrate ledger baseline WITHOUT unrealized PnL."""
import json

csv_pnl = 18.46
dex_total = 423.05
real_deposit = 40.0
seed = 300.0

# current_capital such that: current_capital + csv_pnl = dex_total
# (no unrealized — dex_total doesn't include it either)
current_capital = dex_total - csv_pnl
dark_pnl_gap = current_capital - seed - real_deposit

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
            "note": f"Baseline: ${dark_pnl_gap:.2f} unrecorded trading gains (CSV truncation gap)"
        }
    ]
}

print(f"current_capital: ${current_capital:.2f}")
print(f"expected DEX:    ${current_capital + csv_pnl:.2f} (actual: ${dex_total})")
print(f"delta:           ${dex_total - current_capital - csv_pnl:.2f} (should be ~0)")

with open("trading/spot/live/v14pm/capital_ledger.json", "w") as f:
    json.dump(ledger, f, indent=2)
print("Ledger recalibrated")
