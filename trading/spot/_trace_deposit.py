"""Trace how a deposit flows through the V14PM Live system."""
import json, csv, time

print("=" * 60)
print("DEPOSIT TRACE — $40 USDT into Aster Live Account")
print("=" * 60)

# 1. STATUS.JSON — what the bot currently reports
with open("trading/spot/live/v14pm/status.json") as f:
    s = json.load(f)

print("\n=== 1. BOT STATE (status.json) ===")
print(f"  seed_capital:        ${s.get('seed_capital')}")
print(f"  capital:             ${s.get('capital')}")
print(f"  tracked_capital:     ${s.get('tracked_capital')}")
print(f"  equity:              ${s.get('equity')}")
print(f"  cash:                ${s.get('cash')}")
print(f"  invested:            ${s.get('invested')}")
print(f"  total_realized_pnl:  ${s.get('total_realized_pnl')}")
print(f"  total_fees:          ${s.get('total_fees')}")
print(f"  deals_completed:     {s.get('deals_completed')}")

# 2. EXCHANGE BALANCE — what the bot reads from DEX
eb = s.get("exchange_balance", {})
print(f"\n  Exchange balance (last sync):")
print(f"    free:  ${eb.get('free', 'N/A')}")
print(f"    used:  ${eb.get('used', 'N/A')}")
print(f"    total: ${eb.get('total', 'N/A')}")

# 3. CAPITAL LEDGER
print("\n=== 2. CAPITAL LEDGER ===")
try:
    with open("trading/spot/live/v14pm/capital_ledger.json") as f:
        ledger = json.load(f)
    print(f"  seed_capital:    ${ledger.get('seed_capital')}")
    print(f"  current_capital: ${ledger.get('current_capital')}")
    txns = ledger.get("transactions", [])
    print(f"  Transactions:    {len(txns)}")
    for t in txns[-5:]:
        print(f"    {t.get('timestamp','?')}: {t.get('type','')} ${t.get('amount',0):.2f} → ${t.get('balance_after',0):.2f}")
except Exception as e:
    print(f"  Error reading ledger: {e}")

# 4. ROUTER STATE
router = s.get("router", {})
print("\n=== 3. CAPITAL ROUTER ===")
print(f"  active_pool_total:  {router.get('active_pool_total')}")
print(f"  reserve_pool_total: {router.get('reserve_pool_total')}")
print(f"  total_equity:       {router.get('total_equity')}")
print(f"  tier_coin_cap:      {s.get('tier_coin_cap')}")

# 5. DASHBOARD DATA
print("\n=== 4. DASHBOARD DATA (docs/data/v14-pm-live/) ===")
with open("docs/data/v14-pm-live/status.json") as f:
    ds = json.load(f)
print(f"  seed_capital:        ${ds.get('seed_capital')}")
print(f"  equity:              ${ds.get('equity')}")
print(f"  capital:             ${ds.get('capital')}")

# 6. ANALYSIS
print("\n=== 5. DEPOSIT IMPACT ANALYSIS ===")
seed = s.get("seed_capital", 300)
equity_before = s.get("equity", 0)
capital_before = s.get("capital", 0)
print(f"  Before deposit:")
print(f"    seed_capital = ${seed} (immutable, will NOT change)")
print(f"    equity       = ${equity_before}")
print(f"    capital      = ${capital_before}")
print(f"  After deposit ($40 USDT):")
print(f"    seed_capital = ${seed} (stays same — Hard Rule #26)")
expected_eq = equity_before + 40
print(f"    equity       ≈ ${expected_eq:.2f} (DEX balance + 40)")
print(f"    capital      ≈ ${capital_before + 40:.2f} (tracked_capital + 40)")
print()
print(f"  Growth % impact:")
old_growth = (equity_before - seed) / seed * 100 if seed > 0 else 0
new_growth = (expected_eq - seed) / seed * 100 if seed > 0 else 0
print(f"    Before: ({equity_before} - {seed}) / {seed} × 100 = +{old_growth:.2f}%")
print(f"    After:  ({expected_eq:.2f} - {seed}) / {seed} × 100 = +{new_growth:.2f}%")
print(f"    ⚠️  Growth jumps from +{old_growth:.2f}% to +{new_growth:.2f}%")
print(f"    ⚠️  The deposit inflates growth because seed_capital stays at ${seed}")
print()

# Check: is auto deposit detection enabled or disabled?
print("=== 6. DEPOSIT DETECTION STATUS ===")
print("  Auto deposit/withdrawal detection: DISABLED (2026-05-08)")
print("  Manual DEPOSIT/WITHDRAW Telegram commands: still work")
print("  DEX-as-truth startup: will absorb the $40 silently on next restart")
print("  During runtime: exchange sync reads DEX balance every 60s")
print("  The $40 will appear in exchange_balance.free on next sync cycle")
