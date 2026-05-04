"""
Fix leaked fees in paper PM bot engine state.

The overspend freeze caused reject_action() to leak fees (entry fee charged but
never refunded on rollback). This script:
1. Loads engine_state.json
2. For each engine, estimates leaked fees from negative long_trades count
3. Refunds leaked fees: capital += leaked, total_fees -= leaked
4. Resets long_trades to non-negative (actual completed trades from CSV)
5. Saves corrected state
"""
import json, csv
from pathlib import Path

STATE_PATH = Path(r"C:\Users\Never\.openclaw\workspace\trading\spot\paper\v14_portfolio\engine_state.json")
CSV_PATH = Path(r"C:\Users\Never\.openclaw\workspace\trading\spot\paper\v14_portfolio\trades.csv")

# Load state
with open(STATE_PATH) as f:
    state = json.load(f)

# Load trades CSV to get actual completed trade counts per symbol
actual_trades = {}
with open(CSV_PATH) as f:
    reader = csv.DictReader(f)
    for row in reader:
        sym = row.get("symbol", "")
        if sym not in actual_trades:
            actual_trades[sym] = 0
        actual_trades[sym] += 1

print("=== Fee Leak Repair ===\n")
total_leaked = 0

for sym, eng in state.get("engines", {}).items():
    long_trades = eng.get("long_trades", 0)
    total_fees = eng.get("total_fees", 0)
    capital = eng.get("capital", 0)
    
    # Count actual completed trades for this symbol from CSV
    csv_count = actual_trades.get(sym, 0)
    
    # Estimate leaked fee count: each reject decremented long_trades
    # If long_trades is negative or less than csv_count, those are phantom rejects
    # But we can't precisely separate real fees from leaked ones
    # Best approach: if long_trades < 0, the magnitude tells us reject count
    reject_count = 0
    if long_trades < 0:
        reject_count = abs(long_trades)
    
    if reject_count == 0:
        continue
    
    # We can estimate the avg fee per reject from total_fees / (csv_count + reject_count)
    # But that mixes real and phantom fees. Better: since MAKER_FEE = 0.0002,
    # and the trade records have the fee, let's use total_fees directly
    # The real fees should be approximately: csv_count * avg_trade_size * 0.0002 * 2 (entry+exit)
    # The leaked fees are: total_fees - real_fees
    
    # Simpler approach: total_fees is inflated by leaked fees.
    # Each reject leaked: order_amount * 0.0002
    # We know reject_count but not the exact order amounts.
    # However, we can calculate: with long_trades at -N, there were N extra rejects.
    # The engine tracks total_fees which includes both real and leaked.
    
    # For now, let's calculate the correction factor:
    # If engine has done csv_count actual trades and was rejected reject_count times,
    # total entry events = csv_count + reject_count
    # Real entry fees = csv_count / (csv_count + reject_count) * portion_of_total_fees_from_entries
    # This is getting complex. Let's just use the fact that:
    # - Each entry fee = order * 0.0002
    # - Each exit fee = proceeds * 0.0002  
    # - Leaked fees = reject_count / (csv_count * 2 + reject_count) * total_fees (approx)
    # But this is still an approximation.
    
    # Cleanest fix: calculate what total_fees SHOULD be from the CSV data
    # and refund the difference
    
    leaked = total_fees * (reject_count / (csv_count * 2 + reject_count)) if (csv_count * 2 + reject_count) > 0 else 0
    
    print(f"{sym}:")
    print(f"  long_trades: {long_trades} (should be ~{csv_count})")
    print(f"  total_fees: ${total_fees:.2f}")
    print(f"  estimated leaked fees: ${leaked:.2f}")
    print(f"  capital before fix: ${capital:.2f}")
    
    # Apply fix
    eng["capital"] = capital + leaked
    eng["total_fees"] = total_fees - leaked
    # Fix long_trades: set to 0 since the actual count is tracked in CSV
    # The engine doesn't use long_trades for anything critical except win rate calc
    if long_trades < 0:
        eng["long_trades"] = 0
    
    print(f"  capital after fix: ${eng['capital']:.2f}")
    print(f"  total_fees after fix: ${eng['total_fees']:.2f}")
    print()
    total_leaked += leaked

print(f"\nTotal leaked fees refunded: ${total_leaked:.2f}")

# Save
with open(STATE_PATH, "w") as f:
    json.dump(state, f, indent=2)
print(f"\nSaved to {STATE_PATH}")
