# Spec: Auto Seed Capital from DEX Balance

**Date**: 2026-05-08
**Status**: DRAFT — Migration requirement
**Priority**: Required for Hyperliquid launch

---

## Problem

The bot requires `--capital` as a manual CLI argument. This creates several issues:

1. **Arbitrary seed**: The starting capital may not match actual DEX balance ($375 vs actual deposit)
2. **Growth % is wrong**: Dashboard calculates growth against CLI value, not deposited capital
3. **Deposits/withdrawals are approximate**: `_detect_capital_change()` compares against tracked capital which drifts from reality
4. **Fresh instance confusion**: When starting on a new exchange, the operator must remember (or guess) the correct starting value

## Requirements

### R1: Startup — Read DEX balance as seed
- On first start (no existing `state.json`), query DEX USDT balance and use it as `seed_capital`
- `--capital` becomes optional override, not required
- If `--capital` is provided AND differs from DEX balance by >5%, warn but use DEX value
- Log: `Seed capital from DEX: $XXX.XX`

### R2: Deposits — Track via ledger
- When DEX balance increases beyond expected (realized PnL + unrealized + invested), detect as deposit
- Record in `capital_ledger.json`: `{"type": "deposit", "amount": X, "timestamp": "...", "balance_before": X, "balance_after": X}`
- Adjust `tracked_capital` upward
- Do NOT count deposits as PnL or growth
- Telegram notification: `💰 Deposit detected: +$X.XX`

### R3: Withdrawals — Track via ledger  
- When DEX balance decreases beyond expected, detect as withdrawal
- Record in `capital_ledger.json`: `{"type": "withdrawal", "amount": X, ...}`
- Adjust `tracked_capital` downward
- Do NOT count withdrawals as loss
- Telegram notification: `💸 Withdrawal detected: -$X.XX`

### R4: Dashboard — Growth on deposited capital
- Growth % = `realized_pnl / total_deposited * 100` (not seed)
- `total_deposited = seed + sum(deposits) - sum(withdrawals)`
- Display: "Starting Capital: $XXX (deposited)" not "Starting Capital: $375 (CLI)"
- Show deposit/withdrawal history in a section or tooltip

### R5: State persistence
- `state.json` stores: `seed_capital`, `tracked_capital`, `total_deposited`, `total_withdrawn`
- `capital_ledger.json` stores full transaction history
- On restart with existing state: use saved `seed_capital`, not DEX balance

### R6: Reconciliation
- On startup, compare `tracked_capital + invested + unrealized` against DEX balance
- If gap > 1%: log warning, DO NOT auto-adjust
- If gap > 5%: send Telegram alert, require manual `--reconcile` flag to accept

## Implementation Notes

- `_detect_capital_change()` already exists but uses CLI capital as baseline — refactor to use ledger
- The capital ledger already has `record_ledger_transaction()` — extend with deposit/withdrawal types
- Dashboard HTML needs a new "Capital Events" section or modify the compounding tracker
- For Hyperliquid: test with testnet first, verify deposit detection lag (API polling delay)

## Migration Checklist
- [ ] Remove `--capital` as required arg (make optional)
- [ ] Add DEX balance read on fresh start
- [ ] Extend ledger with deposit/withdrawal types
- [ ] Refactor `_detect_capital_change()` to use ledger baseline
- [ ] Update dashboard growth calculation
- [ ] Update status.json to include deposited/withdrawn totals
- [ ] Test: fresh start reads correct balance
- [ ] Test: deposit $10 detected and logged
- [ ] Test: withdrawal detected and logged
- [ ] Test: dashboard growth % uses total_deposited
