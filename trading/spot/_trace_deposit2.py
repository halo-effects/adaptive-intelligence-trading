import json, sys
sys.stdout.reconfigure(encoding='utf-8')

with open("trading/spot/live/v14pm/status.json") as f:
    s = json.load(f)

seed = s.get("seed_capital", 300)
equity = s.get("equity", 0)
capital = s.get("capital", 0)
tracked = s.get("tracked_capital", 0)
rpnl = s.get("total_realized_pnl", 0)

print("CURRENT STATE (deposit already absorbed):")
print(f"  seed_capital:     ${seed}")
print(f"  equity:           ${equity}")
print(f"  capital:          ${capital}")
print(f"  tracked_capital:  ${tracked}")
print(f"  realized_pnl:    ${rpnl}")
print(f"  deals_completed:  {s.get('deals_completed')}")
print()

print("HOW THE $40 FLOWED:")
print(f"  1. DEX balance went from ~$378 to ~$418")
print(f"  2. Exchange sync (every 60s) read new balance")
print(f"  3. tracked_capital updated to ${tracked}")
print(f"  4. capital updated to ${capital}")
print(f"  5. seed_capital stayed at ${seed} (immutable)")
print()

print("DASHBOARD GROWTH CALCULATION:")
growth = (equity - seed) / seed * 100 if seed > 0 else 0
print(f"  (equity - seed) / seed = ({equity} - {seed}) / {seed}")
print(f"  = +{growth:.2f}%")
print()
print(f"  PROBLEM: This includes the $40 deposit as 'growth'")
print(f"  Real trading growth = ${rpnl:.2f} realized PnL on ${seed} seed")
print(f"  Real growth % = {rpnl/seed*100:.2f}%")
print(f"  Deposit inflates growth by {40/seed*100:.2f}%")
print()

print("WHAT'S NOT HANDLED:")
print("  - Capital ledger NOT updated (auto deposit detection DISABLED)")
print("  - seed_capital NOT adjusted (correct - Hard Rule #26)")
print("  - Dashboard growth % now inflated (+13.3% from deposit alone)")
print("  - No Telegram notification of the deposit")
print("  - Router pool sizes recalculated on next rebalance (larger pools)")
print()

print("WHAT WORKS CORRECTLY:")
print("  - Bot trades with the full balance (more buying power)")
print("  - Equity card shows true DEX balance")
print("  - Realized PnL unaffected (CSV-based)")
print("  - Win rate unaffected")
