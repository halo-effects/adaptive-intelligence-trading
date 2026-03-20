# Stasis Vault — Use Case Reference

Situational guide for AI agents. Find your current state, understand your goal, follow the solution.

---

## Use Case 1: Earn Yield on Idle Capital

**Status**: You have USDB sitting idle in your wallet doing nothing.
**Goal**: Earn yield with minimal risk instead of letting capital sit.
**Solution**: Buy STASIS, wrap it into wSTASIS, and hold.

### Steps
```
1. trading.buy(MAINTOKEN, amount)         # USDB → STASIS
2. staking.buy(stasis_amount)             # STASIS → wSTASIS (yield-bearing)
3. Hold — your shares appreciate automatically
4. When ready: staking.sell(shares)       # wSTASIS → STASIS (more than you put in)
5. trading.sell(MAINTOKEN, amount)        # STASIS → USDB
```

### Costs
| Cost | Amount | When |
|------|--------|------|
| Buy STASIS swap fee | ~0.81% | Entry (USDB → STASIS) |
| Sell STASIS swap fee | ~0.81% | Exit (STASIS → USDB) |
| Wrap/unwrap | 0% | Lossless conversion both ways |
| Gas (2 txs entry) | ~$0.50 | Buy + wrap |
| Gas (2 txs exit) | ~$0.50 | Unwrap + sell |
| **Total round-trip** | **~1.62% + $1.00 gas** | |

### Break-Even
You need **~1.62% yield** to cover the round-trip swap fees. At the current vault rate (120% accumulated), even a few days of staking should cover this — but the yield rate depends on ongoing platform trading volume generating fees.

### Pre-Flight Checks
```python
# Is it worth it for my amount?
amount_usdb = 100  # your idle capital
round_trip_cost_pct = 1.62
gas_cost_usd = 1.00
min_profitable = gas_cost_usd / (amount_usdb * 0.01)  # gas as % of capital
# If amount < $50, gas costs eat too much of the yield. Minimum practical: ~$50

# What's the current exchange rate? (track over time for APY)
rate = staking.convert_to_assets(10**18)  # STASIS per wSTASIS
```

### Risk
**Low.** Your only risk is STASIS price dropping against USDB. You'll always receive more STASIS back than you deposited, but if STASIS/USDB drops more than your yield earned, you're net negative in USDB terms.

### When NOT To Do This
- You need the capital in the next few hours (gas + swap fees not worth it)
- Amount is under ~$50 (gas costs dominate)
- You're bearish on STASIS price

---

## Use Case 2: Earn Yield AND Keep Liquidity Access

**Status**: You want yield on your capital, but might need access to it quickly.
**Goal**: Earn yield while keeping the option to borrow against your position if needed.
**Solution**: Buy STASIS, wrap it, lock it as collateral. Only borrow if/when you need capital.

### Steps
```
1. trading.buy(MAINTOKEN, amount)         # USDB → STASIS
2. staking.buy(stasis_amount)             # STASIS → wSTASIS
3. staking.lock(shares)                   # Lock as collateral (still earning yield)
4. — Hold here, earning yield —
5. IF you need capital:
   staking.borrow(amount, 10)             # Borrow liquid STASIS (min 10 days)
   trading.sell(MAINTOKEN, borrowed)      # STASIS → USDB for use
6. When done:
   trading.buy(MAINTOKEN, repay_amount)   # Buy STASIS to repay
   staking.repay()                        # Clear the loan
   staking.unlock(shares)                 # Unlock collateral
   staking.sell(shares)                   # Exit if desired
```

### Costs
| Cost | Amount | When |
|------|--------|------|
| All costs from Use Case 1 | ~1.62% + $1.00 | Entry/exit |
| Lock/unlock gas | ~$0.40 | 2 extra transactions |
| Borrow interest | **2.09% per 10 days (~76% annualized)** | Only if you borrow |
| Borrow upfront fee | ~2% of borrowed amount | Deducted at borrow time |
| Borrow/repay gas | ~$0.90 | 2 transactions |
| Selling/rebuying borrowed STASIS | ~1.62% | Round-trip swap on borrowed amount |

### The Real Cost of Borrowing
This is the critical math agents need to understand:

```
You lock 100 STASIS worth of wSTASIS.
You borrow against 50 STASIS collateral for 10 days.

What you receive: 49 STASIS (50 minus 2% origination fee)
What you owe at repayment: 50 STASIS (always the full collateral value)
Total cost: 1 STASIS = 2% flat

If you need 30 more days:
  Extension cost: 50 × 0.005% × 30 = 0.075 STASIS
  Still owe: 50 STASIS at repayment
  Total cost for 40 days: 1.075 STASIS = 2.15%

If you converted to USDB and back:
  Sell 49 STASIS → ~48.60 USDB (0.81% swap fee)
  Buy 50 STASIS to repay → ~50.41 USDB (0.81% swap fee)
  Net USDB cost of having ~$48.60 for 10 days: ~$1.81
  For 40 days: ~$1.89 (barely more — extension is cheap)
```

**Key insight**: The 2% origination is the big cost. After that, extending is nearly free (0.005%/day). But since interest is prepaid with no refund on early repayment, take the minimum 10-day loan and extend as needed — don't overshoot the duration.

### Pre-Flight Checks
```python
# Can I borrow enough to be useful?
stake_details = staking.get_user_stake_details(wallet)
available = staking.get_available_stasis(wallet)
# If available is 0, you need to lock more or you're already fully borrowed

# What will the loan actually cost me?
borrow_amount = 50 * 10**18
upfront_fee = borrow_amount * 0.02          # ~2% you don't receive
interest_10d = borrow_amount * 0.0209       # 2.09% owed after 10 days
total_owed = borrow_amount + interest_10d   # what you repay
actual_received = borrow_amount - upfront_fee  # what lands in your wallet
```

### Risk
**Medium.** If STASIS price drops, your locked collateral may not cover the loan → liquidation. You lose your staked position AND still owe the shortfall.

### When NOT To Do This
- You're borrowing to trade something speculative (liquidation risk compounds)
- Loan interest exceeds expected return on whatever you're using the capital for
- You can't repay within the loan duration

---

## Use Case 3: Maximize Yield via Leverage Loop

**Status**: You're confident STASIS vault yield will exceed borrowing costs.
**Goal**: Amplify your yield exposure by staking borrowed STASIS.
**Solution**: Stake → lock → borrow → re-stake. Loop for more exposure.

### Steps
```
1. trading.buy(MAINTOKEN, $100)           # 100 USDB → ~99 STASIS
2. staking.buy(99 * 10**18)              # 99 STASIS → ~45 wSTASIS
3. staking.lock(45_wstasis)              # Lock as collateral
4. staking.borrow(40 * 10**18, 30)       # Borrow 40 STASIS (receive ~39.2)
5. staking.buy(39.2 * 10**18)            # Re-stake → ~17.8 more wSTASIS
   — Now earning yield on ~62.8 wSTASIS with $100 initial —
6. Before day 30: unwind or extend
```

### The Math
```
Initial: $100 → 99 STASIS → 45 wSTASIS
Borrow against 40 STASIS collateral:
  Receive: 39.2 STASIS (40 minus 2% fee)
  Owe at repay: 40 STASIS (full collateral value)
Re-stake: 39.2 STASIS → 17.8 wSTASIS

Total staked: 62.8 wSTASIS = ~138 STASIS equivalent
Effective leverage: 1.39x on your initial $100

Costs:
  Origination fee: 0.8 STASIS (2% of 40) — paid upfront, non-refundable
  Extension: 0.002 STASIS/day (40 × 0.005%) — only pay for days you need
  Strategy: Take 10-day loan, extend as needed. Don't pre-pay for time you won't use.

Break-even: vault yield on extra 39.2 STASIS must exceed 0.8 STASIS + extension costs
  = vault needs to yield >2.04% on the borrowed portion + 0.005%/day ongoing
  = At current vault rates (120% accumulated), this is easily achievable
  
Unwind when done:
  staking.sell(extra_shares) → get STASIS back
  staking.repay() → costs 40 STASIS
  Wait until loan is near expiry to repay (you already paid for those days)
```

### Risk
**High.** You're borrowing to stake. If:
- Vault yield slows down → you're paying interest for nothing
- STASIS price drops → liquidation on borrowed portion
- You can't repay → lose everything in the vault

### When NOT To Do This
- You don't have a clear view on vault yield trajectory
- You can't monitor the position regularly (10-day loan windows)
- Your initial capital is small (<$200, gas costs dominate)

---

## Use Case 4: Fund a Trade Without Selling Your Stake

**Status**: You have STASIS staked in the vault. You see a trading opportunity (prediction market, new token, etc.) but don't want to exit your staking position.
**Goal**: Get liquid USDB to trade with, using your staked position as collateral.
**Solution**: Lock, borrow, sell borrowed STASIS for USDB, make your trade, buy back STASIS, repay.

### Steps
```
1. staking.lock(your_shares)                     # Lock existing wSTASIS
2. staking.borrow(amount, 10)                     # Borrow STASIS
3. trading.sell(MAINTOKEN, borrowed_stasis)        # STASIS → USDB
4. — Make your trade (buy token, bet on market, etc.) —
5. — Trade profits or exits —
6. trading.buy(MAINTOKEN, repay_amount)            # Buy STASIS to repay
7. staking.repay()                                 # Clear loan
8. staking.unlock(shares)                          # Free your collateral
```

### Costs
```
Borrow against 50 STASIS collateral to get trading capital:
  You receive:        49 STASIS (50 minus 2% origination fee)
  Sell to USDB:       ~48.60 USDB (0.81% swap fee)
  
  Your trade needs to return at least:
  Repay amount:       50 STASIS (full collateral value, always)
  Buy cost in USDB:   ~50.41 USDB (0.81% swap fee)
  
  Total cost: ~$1.81 on ~$48.60 capital = ~3.7%
  (And if you need 30 more days, extension only adds ~$0.08)
```

### Decision Framework
```
Expected trade return   vs   Borrowing cost (~3.7% one-time)
─────────────────────────────────────────────────────────────
  > 5%                       Clearly worth it
  3-5%                       Marginal, depends on confidence
  < 3%                       Not worth the complexity and risk

Note: Time barely matters! Holding the loan 10 days or 90 days
costs almost the same (extension is 0.005%/day). Take your time.
```

### Risk
**Medium-High.** You're adding leverage to a trade. If the trade loses AND STASIS drops, you could face liquidation on your staked position.

---

## Use Case 5: Quick Exit — Staked to USDB in One Step

**Status**: You have unlocked wSTASIS and need USDB fast.
**Goal**: Convert your staked position to USDB in the fewest transactions.
**Solution**: Use the `sell(claimUSDC=True)` convenience function.

### Steps
```
1. staking.sell(shares, claim_usdb=True, min_usdb=0)
   # This does: unwrap wSTASIS → sell STASIS → receive USDB
   # All in ONE transaction
```

### Costs
| Cost | Amount |
|------|--------|
| Swap fee (STASIS → USDB) | ~0.81% |
| Gas (1 tx instead of 2) | ~$0.30 |

### When To Use
- Emergency exit
- Want simplicity over optimizing every basis point
- Small position where extra tx gas isn't worth it

### Constraints
- Only works on **unlocked** wSTASIS (not locked collateral)
- Must have no active loan if shares are locked — repay and unlock first
- `min_usdb` parameter lets you set slippage protection

---

## How Loans Actually Work (Critical — Read This)

Loans have a **flat origination fee** model, NOT a compounding interest rate. Getting this wrong will lead to terrible decisions.

### The Fee Structure
| Component | Rate | When Paid | Calculated On |
|-----------|------|-----------|---------------|
| **Origination fee** | 2% flat | Upfront (deducted from what you receive) | Collateral value |
| **Extension fee** | 0.005% per day | Upfront (when you extend) | Collateral value |
| **Repayment amount** | 100% of collateral value | At repay | Always the full original amount |

### How It Works In Practice

```
You put up 100 STASIS as collateral:
  → You RECEIVE: 98 STASIS (100 minus 2% origination fee)
  → You OWE:     100 STASIS (always the full collateral value)
  → The 2 STASIS fee is gone — paid upfront, non-refundable

After 10 days, you want to keep the loan open another 30 days:
  → Extension cost: 100 × 0.005% × 30 = 0.15 STASIS (paid upfront)
  → You still owe: 100 STASIS at repayment (unchanged)

When you repay:
  → You pay back 100 STASIS
  → You get your locked wSTASIS collateral back
```

### Total Cost by Duration

| Loan Duration | Origination | Extension | Total Cost | Cost per Day |
|---------------|-------------|-----------|------------|-------------|
| 10 days (min) | 2.00% | 0.00% | **2.00%** | 0.200% |
| 30 days | 2.00% | 0.10% | **2.10%** | 0.070% |
| 60 days | 2.00% | 0.25% | **2.25%** | 0.038% |
| 90 days | 2.00% | 0.40% | **2.40%** | 0.027% |
| 180 days | 2.00% | 0.85% | **2.85%** | 0.016% |
| 365 days | 2.00% | 1.78% | **3.78%** | 0.010% |

**Key insight**: All interest is paid upfront. If you repay early, you do NOT get a refund on unused days. This means:
- Taking a 90-day loan and repaying on day 10 = you paid for 80 wasted days
- Taking a 10-day loan and extending 8 times = you only paid for the days you actually used

**Optimal strategy: Start short, extend as needed.**

### Common Mistakes Agents Must Avoid

❌ **"Borrowing costs 76% annualized"** — WRONG. That treats the 2% flat fee as a rate. The 2% is a one-time origination cost, not a periodic rate.

❌ **"I should take a long loan so it's cheaper per day"** — WRONG. Interest is prepaid. If you repay early, those prepaid days are wasted. Take the minimum (10 days) and extend.

❌ **"I should repay early to save on interest"** — WRONG. You already paid the interest upfront. Repaying early saves nothing — you forfeit the remaining loan period you've already paid for.

❌ **"Extension costs compound"** — WRONG. Extension fee is flat: 0.005% × days × collateral. It doesn't compound. There's no interest-on-interest.

✅ **Correct strategy**: Take the minimum duration (10 days). Extend in small increments as needed (0.005%/day). Only repay when you're truly done — never early, since you can't recover prepaid interest. If you're unsure how long you need the loan, extend day-by-day or in small batches.

---

## Cost Summary Table

| Action | Cost | Type |
|--------|------|------|
| Buy STASIS (USDB → STASIS) | 0.81% | Swap fee + tax |
| Sell STASIS (STASIS → USDB) | 0.81% | Swap fee + tax |
| Wrap (STASIS → wSTASIS) | 0% | Lossless |
| Unwrap (wSTASIS → STASIS) | 0% | Lossless (receive MORE due to yield) |
| Lock / Unlock | 0% | Free (gas only) |
| **Loan origination fee** | **2% flat** | **Deducted upfront from what you receive** |
| **Loan extension fee** | **0.005%/day** | **Paid upfront on collateral value** |
| **Loan repayment** | **Full collateral value** | **Always 100% of original amount** |
| Gas per transaction | $0.15-0.60 | BSC gas costs |
| Full entry (buy + wrap) | ~0.81% + $0.50 gas | 2 transactions |
| Full exit (unwrap + sell) | ~0.81% + $0.50 gas | 2 transactions |
| Quick exit (sell claimUSDC) | ~0.81% + $0.30 gas | 1 transaction |
| Full round-trip (no borrow) | ~1.62% + $1.00 gas | Break-even point for yield |

---

## Key Numbers to Remember

| Parameter | Value | Source |
|-----------|-------|--------|
| STASIS swap tax | 0.50% (50 bps) | `taxes.getBaseTaxRates()` |
| Min buy amount | 1.0 STASIS | `minBuyAmount()` on vault contract |
| Min borrow amount | ~5 STASIS | Empirical (0.5 rejected, 5 works) |
| Min loan duration | 10 days | Contract enforced |
| Loan origination fee | 2% flat | Deducted upfront |
| Loan extension fee | 0.005% per day | On collateral value, paid upfront |
| Loan repayment | Full collateral value | No discount for early repay |
| Vault exchange rate | 1 wSTASIS = 2.20 STASIS | `convertToAssets(1e18)` |
| Accumulated vault yield | ~120% | Since vault launch |
| Vault utilization | 54% pledged | `totalStasisPledged / totalAssets` |
| Practical minimum capital | ~$50 | Below this, gas costs dominate |

---

## Agent Decision Checklist

Before any vault interaction, an agent should evaluate:

1. **Do I have enough capital?** Below $50, gas costs eat the yield.
2. **How long will I hold?** Need at least a few days to cover the 1.62% round-trip swap cost.
3. **Do I need borrowing?** The 2% origination fee is the main cost. Take the minimum 10-day loan and extend as needed (0.005%/day). Never pre-pay for duration you might not use.
4. **Can I monitor the position?** Loans expire. Liquidation is real. Don't borrow and forget. Set a reminder before expiry to either repay or extend.
5. **Am I bullish on STASIS?** If STASIS drops vs USDB, your entire vault position drops in USDB terms — yield or not.
6. **Am I planning to reborrow?** If yes, DON'T repay and retake — extend instead. Each new loan costs another 2% origination fee. Extending costs only 0.005%/day.
7. **When should I repay?** Only when you're truly done. Repaying early wastes prepaid interest — there's no refund. Let the loan run until near expiry, then repay or extend. Extension costs 0.005%/day.
