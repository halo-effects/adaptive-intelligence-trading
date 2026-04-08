# Fee & Cost Master Reference

**What this covers:** Complete fee reference - trading fees by token type, loan cost model, vault costs, gas estimates.
**Related sections:** → See: [16-how-everything-works.md](16-how-everything-works.md) for mechanics · → See: [22-mistakes-to-avoid.md](22-mistakes-to-avoid.md) for common cost mistakes · → See: [15-why-each-action-matters.md](15-why-each-action-matters.md) for loan cost strategy

---

### Trading Fees

| Action | Fee | Notes |
|--------|-----|-------|
| Buy/sell Stable+ (incl. STASIS) | 0.50% per swap | Creator gets 0.1% (20%) |
| Buy/sell Floor+ | 1.50% per swap | Creator gets 0.3% (20% of gross fee) |
| Buy/sell Predict+ | 1.50% per swap | **See Predict+ breakdown below** - creator gets 0.1% (20% of net fee) |
| Surge tax (if active) | Variable - see below | Anti-dump mechanism on large sells |

### Predict+ Fee Breakdown

Predict+ tokens have the same 1.5% gross fee as Floor+, but the fee is distributed differently. **2/3 of the fee goes back into the prediction market ecosystem:**

| On a $100 trade | Amount | Destination |
|-----------------|--------|-------------|
| **Prediction ecosystem portion** | **$1.00** (1% of trade) | Fed back into the market |
| - Resolver bounty pool | $0.05 (5% of ecosystem portion) | Rewards for resolvers who finalize the market |
| - General pot | $0.95 (95% of ecosystem portion) | Accumulated from all outcome trading; distributed to winning outcome holders at resolution |
| **Net platform fee** | **$0.50** (0.5% of trade) | Standard platform distribution |
| - Staking yield (16%) | $0.08 | Vault holders |
| - Creator dev fee (20%) | $0.10 | Market creator |
| - Reward phase buyers (4%) | $0.02 | Early supporters who bought during bonding curve phase |
| - Platform treasury (60%) | $0.30 | Platform operations |

**Key insight:** Every trade on a prediction market makes the winning pot bigger. More trading volume = bigger payouts for correct predictions = more incentive to trade. The creator's 20% dev fee is calculated on the **net** 0.5% platform fee (not the gross 1.5%), so the creator earns **0.1% of trade value** on Predict+ tokens - compared to 0.3% on Floor+ tokens.

**No surge tax on Predict+ tokens.** The surge mechanism is disabled for prediction markets entirely.

---

### Surge Tax Details

The surge tax is a temporary extra fee that **token creators manually activate** via `startSurgeTax(startRate, endRate, duration, token)`. It decays linearly from startRate to endRate over the configured duration. Only the token's DEV (creator) can start or end a surge. It applies to all trades (buys and sells) while active.

**Maximum surge tax by token type** (additive on base trading fee):

| hybridMultiplier | Max Surge Tax | Max Total Fee (base + surge) |
|-----------------|---------------|------------------------------|
| 1 (most volatile Floor+) | 15% (1500 BP) | 16.5% |
| 45 (mid Floor+) | 8% (800 BP) | 9.5% |
| 90 (high stability Floor+) | 1% (100 BP) | 2.5% |
| 100 (Stable+) | 0.5% (50 BP) | 1.0% |
| Predict+ | N/A - surge disabled | 1.5% (base only) |

**Timing constraints:**
- Surge duration: ≥ 1 hour (linear decay to zero)
- Quota: maximum 7 days of surge per rolling 30-day window

**How it works:** The creator activates a surge with chosen start/end rates and duration (min 1 hour). The extra fee goes primarily to the creator (all surge basis points are added to the dev portion of fee distribution). The more stable the token (higher hybridMultiplier), the lower the maximum allowed surge - because stable tokens already absorb sell pressure structurally. Check `getAvailableSurgeQuota(token)` before starting a surge to see remaining quota.

---

### Loan Fees

| Action | Fee | Notes |
|--------|-----|-------|
| Origination | 2% flat | Deducted upfront. One-time, non-refundable. |
| Daily interest | 0.005% per day | On collateral value, applies to all loans |
| Extension | 0.005% per day | Same rate as daily interest, paid upfront when extending |
| Repayment | Repay USDB debt → collateral returned | You repay the `fullAmount` from `getUserLoanDetails()` — this is the total USDB obligation (original loan value + all prepaid interest). Your collateral tokens are returned to your wallet. No discount for early repay — the full prepaid amount is owed regardless of when you repay. |
| Expiry (no repay) | Collateral burned to cover debt | If you don't repay before loan expiry, collateral tokens are burned (burned = sold on elastic supply tokens). Any remaining collateral value above the debt is claimable via `claimLiquidation(hubId)` - it is NOT automatically returned. |

**Total cost by duration**:

| Duration | Origination | Extension | Total |
|----------|------------|-----------|-------|
| 10 days (min) | 2.00% | 0.00% | **2.00%** |
| 30 days | 2.00% | 0.10% | **2.10%** |
| 90 days | 2.00% | 0.40% | **2.40%** |
| 365 days | 2.00% | 1.78% | **3.78%** |

**How to calculate extension cost:** The minimum loan is 10 days (covered by origination). Extension cost only applies to days beyond the initial 10. Formula: `(totalDays - 10) × 0.005%`. For 365 days: `(365 - 10) × 0.005% = 355 × 0.005% = 1.775% ≈ 1.78%`.

**Key takeaway**: A year-long loan costs ~3.78% total - NOT 2% × 365 days. The 2% is a flat origination fee, not an annual rate.

### Vault Costs & Yield

| Action | Fee |
|--------|-----|
| Wrap / unwrap | 0% (lossless) |
| Lock / unlock | 0% (gas only) |
| Entry (buy STASIS + wrap) | 0.5% swap fee + slippage + gas |
| Exit (unwrap + sell STASIS) | 0.5% swap fee + slippage + gas |
| Quick exit (sell claimUSDB) | 0.5% swap fee + slippage + gas (1 tx) |
| Full round-trip | ~1% raw fees + variable slippage both ways |

**Vault yield is variable, not fixed.** It depends on:
- **Platform trading volume** - the vault receives a share of ALL trading fees across the entire platform. More volume = more yield.
- **% of STASIS supply staked** - yield is distributed across all staked tokens. Fewer stakers = higher yield per token. More stakers = lower individual yield.

There is no fixed APY to quote. Early stakers in a growing platform with low vault participation earn the highest yield. The equilibrium adjusts naturally as more participants stake.

### Prediction Market Resolution Costs

| Action | Cost | Notes |
|--------|------|-------|
| Propose outcome | 5 USDB bond | Returned if correct + uncontested = full bounty |
| Dispute outcome | 5 USDB bond | Winner of dispute gets both bonds |
| Veto | 5 USDB bond | One per market, post-voting only |
| Stake to vote | 5 tokens minimum | Any active ecosystem token. One-staker-one-vote |

**Bond outcomes:** Correct party gets both bonds. Neither correct → insurance gets both. Uncontested → proposer gets bond + 100% bounty. See [16-how-everything-works.md](16-how-everything-works.md) for full distribution rules.

---

### Gas Costs (BSC)

> **Note:** The platform sponsors up to 0.01 BNB of gas per wallet per day. If the daily limit is reached, transactions fall back to the user's own BNB.

| Operation | Estimated Cost |
|-----------|---------------|
| Simple swap | $0.27-0.45 |
| Approval + swap | $0.36-0.60 |
| Vault wrap/unwrap | $0.22-0.45 |
| Lock/unlock | $0.14-0.24 |
| Borrow/repay | $0.32-0.60 |
| Token creation | $0.54-0.90 |
| Market creation | $0.72-1.20 |

**Break-even note**: Vault positions need enough yield to cover the ~1% raw swap fees + slippage on both entry and exit + gas costs. Slippage increases with transaction size relative to pool liquidity - use `getAmountsOut()` to estimate your actual costs before committing. Calculate whether expected yield exceeds total costs for your position size before staking for short periods.

---
