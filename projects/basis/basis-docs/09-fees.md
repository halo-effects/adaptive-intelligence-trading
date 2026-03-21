# Fee & Cost Master Reference

**What this covers:** Complete fee reference — trading fees by token type, loan cost model, vault costs, gas estimates.
**Related sections:** → See: [07-how.md](07-how.md) for mechanics · → See: [13-mistakes.md](13-mistakes.md) for common cost mistakes · → See: [06-why.md](06-why.md) for loan cost strategy

---

## Part 7 — Fee & Cost Master Reference

### Trading Fees

| Action | Fee | Notes |
|--------|-----|-------|
| Buy/sell Stable+ (incl. STASIS) | 0.50% per swap | Creator gets 0.1% (20%) |
| Buy/sell Floor+ | 1.50% per swap | Creator gets 0.3% (20%) |
| Buy/sell Predict+ | 1.50% per swap | Creator gets 0.3% (20%) |
| Surge tax (if active) | Variable | Anti-dump mechanism, rare |

### Loan Fees

| Action | Fee | Notes |
|--------|-----|-------|
| Origination | 2% flat | Deducted upfront. One-time, non-refundable. |
| Extension | 0.005% per day | On collateral value, paid upfront when extending |
| Repayment | Full collateral value | No discount for early repay |
| Expiry (no repay) | Loss of collateral | Collateral burned — irreversible |

**Total cost by duration**:

| Duration | Origination | Extension | Total |
|----------|------------|-----------|-------|
| 10 days (min) | 2.00% | 0.00% | **2.00%** |
| 30 days | 2.00% | 0.10% | **2.10%** |
| 90 days | 2.00% | 0.40% | **2.40%** |
| 365 days | 2.00% | 1.78% | **3.78%** |

**Key takeaway**: A year-long loan costs ~3.78% total — NOT 2% × 365 days. The 2% is a flat origination fee, not an annual rate.

### Vault Costs

| Action | Fee |
|--------|-----|
| Wrap / unwrap | 0% (lossless) |
| Lock / unlock | 0% (gas only) |
| Entry (buy STASIS + wrap) | ~0.81% + gas |
| Exit (unwrap + sell STASIS) | ~0.81% + gas |
| Quick exit (sell claimUSDB) | ~0.81% + gas (1 tx) |
| Full round-trip | ~1.62% (break-even yield needed) |

### Gas Costs (BSC)

| Operation | Estimated Cost |
|-----------|---------------|
| Simple swap | $0.27-0.45 |
| Approval + swap | $0.36-0.60 |
| Vault wrap/unwrap | $0.22-0.45 |
| Lock/unlock | $0.14-0.24 |
| Borrow/repay | $0.32-0.60 |
| Token creation | $0.54-0.90 |
| Market creation | $0.72-1.20 |

**Break-even note**: Small vault positions need enough yield to cover ~1.62% swap fees + gas costs ($0.50-$1.00 entry/exit). Calculate whether expected yield exceeds total costs for your position size before staking for short periods.
