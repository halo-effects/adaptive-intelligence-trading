# Stasis Vault — Deep Dive & Agent Strategy Guide

## What Is It?

The Stasis Vault (`AStasisVault`) is a **yield-bearing wrapper** around STASIS (the Basis ecosystem token). You deposit STASIS, receive wSTASIS (wrapped STASIS) shares, and those shares appreciate over time as yield flows into the vault.

**Core concept**: wSTASIS is like a savings account. 1 wSTASIS currently equals **2.20 STASIS** — meaning the vault has generated **120% yield** since launch. The exchange rate only goes up as fees/yield are injected.

**Contract**: `0xb4D72acEa5E26B8438e3604b49A153eB58A7C578`

---

## The Vault's Three Layers

### Layer 1 — Passive Yield (wrap/unwrap)
Deposit STASIS → receive wSTASIS shares → share price increases over time → unwrap for more STASIS than you put in.

**Functions**: `buy()` → hold → `sell()`

### Layer 2 — Locked Collateral (lock/unlock)  
Lock your wSTASIS shares inside the vault, enabling borrowing. Locked shares still earn yield but can't be transferred or sold.

**Functions**: `lock()` / `unlock()`

### Layer 3 — Borrowing (borrow/repay)
Borrow liquid STASIS against your locked wSTASIS. The vault creates a loan through the LoanHub, using your locked shares as collateral.

**Functions**: `borrow()` / `repay()` / `addToLoan()` / `extendLoan()`

---

## Live Contract State (2026-03-20)

| Metric | Value |
|--------|-------|
| Total wSTASIS Supply | 37.36 shares |
| Total STASIS in Vault | 82.26 STASIS |
| Total STASIS Pledged (loans) | 44.43 STASIS |
| Total STASIS Available | 37.83 STASIS |
| Exchange Rate | 1 wSTASIS = 2.2019 STASIS |
| Accumulated Yield | ~120% |
| Min Buy Amount | 1.0 STASIS |

---

## Agent Strategies

### Strategy 1: Simple Staking (Low Risk)
**Goal**: Earn passive yield on STASIS holdings.

```
1. Buy STASIS via trading.buy(MAINTOKEN, $50)
2. Wrap: staking.buy(50 * 10**18)     → receive ~22.7 wSTASIS
3. Hold — shares appreciate as yield accrues
4. Later: staking.sell(shares)          → receive STASIS (more than deposited)
```

**When to use**: Agent has idle STASIS and wants yield without risk.
**Risk**: Minimal. Only risk is if STASIS price drops vs USDB (but you still have more STASIS).
**Points**: 2 pts per $1 per day staked.

**Decision factors**:
- Is the agent holding STASIS for >24 hours? → Stake it
- Is the yield rate competitive? → Check `convertToAssets(1e18)` over time
- Does the agent need liquidity soon? → Don't stake, or use Layer 3

---

### Strategy 2: Leveraged Staking Loop (Medium Risk)
**Goal**: Amplify staking yield by looping — stake, borrow, re-stake.

```
1. Buy $100 STASIS
2. staking.buy(100 STASIS)             → ~45.4 wSTASIS
3. staking.lock(45.4 wSTASIS)          → locked as collateral
4. staking.borrow(40 STASIS, 30)       → receive 40 liquid STASIS
5. staking.buy(40 STASIS)              → ~18.2 more wSTASIS (these are unlocked)
6. Hold both positions — earning yield on ~63.6 wSTASIS total
7. Before loan expires: repay or extend
```

**When to use**: Agent is bullish on STASIS yield continuing and wants to amplify.
**Risk**: 
- Liquidation if STASIS drops sharply
- Loan interest eats into yield
- Must repay before expiry or face liquidation
**Key math**: Yield must exceed borrowing cost. If vault yields 120% over X months but borrowing costs Y% per 30 days, the spread is your profit.

**Decision factors**:
- What's the current vault APY? (track `convertToAssets` over time)
- What's the borrowing cost? (check loan details for interest)
- What's the liquidation threshold? (from `getUserStakeDetails`)
- How long has the vault been running? (longer = more yield history to project)

---

### Strategy 3: Borrow for Liquidity (Medium Risk)
**Goal**: Get liquid capital without selling your staked position.

```
1. Already have wSTASIS from previous staking
2. staking.lock(shares)
3. staking.borrow(amount, 30)           → receive liquid STASIS
4. trading.sell(MAINTOKEN, amount)       → convert to USDB
5. Use USDB for other trades (tokens, prediction markets, etc.)
6. When trades profit: buy STASIS back, repay loan
```

**When to use**: Agent sees a trading opportunity but capital is locked in staking.
**Risk**: 
- If the trades lose money, agent still owes the loan
- Must manage loan expiry
- Double exposure: staking position + active trades
**Combines with**: Any trading strategy — this is a capital efficiency play.

**Decision factors**:
- Is the trading opportunity strong enough to justify the borrowing cost?
- Can the agent repay before liquidation?
- Is the borrowed amount conservative enough to survive a STASIS dip?

---

### Strategy 4: Yield-Boosted Prediction Markets (Advanced)
**Goal**: Use vault yield to fund prediction market positions.

```
1. Stake STASIS in vault (earning yield)
2. Borrow against it
3. Buy prediction market shares with borrowed funds
4. If market wins: profit from prediction + keep staking yield
5. If market loses: still have staking position, just owe the loan
```

**Risk**: High — combining leverage with prediction market risk.
**When to use**: Agent has high conviction on a prediction AND wants to maintain staking exposure.

---

## The Complete Function Flow

```
STASIS (liquid token)
  │
  ├─ staking.buy(amount) ────────────► wSTASIS (yield-bearing shares)
  │                                       │
  │                                       ├─ Hold → appreciate via yield
  │                                       │
  │                                       ├─ staking.lock(shares) ──► Locked wSTASIS
  │                                       │                              │
  │                                       │                              ├─ staking.borrow(amt, days) ──► Liquid STASIS
  │                                       │                              │     │
  │                                       │                              │     ├─ staking.addToLoan(more)
  │                                       │                              │     ├─ staking.extendLoan(days)
  │                                       │                              │     └─ staking.repay() ◄── returns here
  │                                       │                              │
  │                                       │                              └─ staking.unlock(shares) ◄── (only after repay)
  │                                       │
  │                                       └─ staking.sell(shares) ──► STASIS (more than deposited)
  │                                            │
  │                                            └─ sell(shares, claimUSDC=True) ──► USDB directly
  │
  └─ trading.sell(MAINTOKEN, amt) ──► USDB
```

---

## Critical Constraints (from live testing)

| Constraint | Value | Source |
|-----------|-------|--------|
| Min buy amount | 1.0 STASIS | `minBuyAmount()` on contract |
| Min borrow amount | ~5 STASIS (approx) | "Minimum loan amount not met" at 0.5 |
| Min loan duration | 10 days | Contract enforced |
| Lock before borrow | Required | Must `lock()` before `borrow()` |
| Repay before unlock | Required | Must `repay()` before `unlock()` |
| One active loan per vault | Yes | `userVaults.hasActiveLoan` is boolean |
| `addToLoan` requires sufficient remaining duration | Yes | "Duration too short" error |
| `extendLoan` may have state prerequisites | Yes | "not possible" error — needs investigation |
| `sell(claimUSDC=True)` | Atomic unstake→USDB | One-tx convenience function |

---

## Read Functions for Monitoring

### `getUserStakeDetails(user)` → [liquidShares, lockedShares, totalShares, totalAssetValue]
**What an agent tracks**:
- `liquidShares` — wSTASIS available to sell or lock
- `lockedShares` — wSTASIS locked as collateral
- `totalShares` — sum of liquid + locked
- `totalAssetValue` — total STASIS value of all shares (the "real" value)

### `userVaults(user)` → [lockedWStasis, pledgedStasis, hubId, hasActiveLoan]
**What an agent tracks**:
- `pledgedStasis` — how much STASIS is collateralizing the loan
- `hubId` — the LoanHub ID (use this for `loans.getUserLoanDetails()`)
- `hasActiveLoan` — whether borrow/repay is needed

### `convertToShares(stasisAmount)` / `convertToAssets(sharesAmount)`
**What an agent tracks**:
- The exchange rate over time — if `convertToAssets(1e18)` increases, yield is accruing
- Use for pre-trade calculations ("how many shares will I get for X STASIS?")

### `getAvailableStasis(user)`
**What an agent tracks**:
- How much more the agent can borrow against current collateral
- Zero means either nothing locked, or fully borrowed

### `totalAssets()` / `totalStasisPledged()` / `totalStasisAvailable()`
**What an agent tracks**:
- Vault health: if `pledged / assets` ratio is high, many users are borrowing (systemic risk)
- Currently: 54% pledged (44.4 / 82.3) — moderate leverage in the vault

---

## Events (for indexing/tracking)

| Event | When Emitted |
|-------|-------------|
| `Bought(user, stasisSpent, wStasisReceived)` | After `buy()` |
| `Sold(user, wStasisSold, stasisReceived)` | After `sell()` |
| `Locked(user, amount)` | After `lock()` |
| `Unlocked(user, amount)` | After `unlock()` |
| `LoanTaken(user, hubId, stasisCollateralUsed)` | After `borrow()` |
| `LoanRepaid(user, hubId, stasisCollateralReturned)` | After `repay()` |
| `LoanExtended(user, hubId, daysAdded)` | After `extendLoan()` |
| `LiquidationProcessed(user, wStasisBurned)` | After `settleLiquidation()` |
| `YieldClaimed(user, usdcReceived)` | After `sell(claimUSDC=True)` |

---

## Agent Decision Tree

```
Does agent hold STASIS?
  ├─ No → Buy some? (check STASIS price trend, vault APY)
  └─ Yes → How long will agent hold?
        ├─ <24h → Don't stake (gas costs > yield)
        └─ >24h → Stake it (staking.buy)
              │
              Does agent need liquidity?
              ├─ No → Hold wSTASIS, earn yield (Strategy 1)
              └─ Yes → How much?
                    ├─ Small → Sell some wSTASIS (staking.sell)
                    └─ Large but want to keep position →
                          Lock + Borrow (Strategy 3)
                          │
                          Is agent bullish on STASIS long-term?
                          ├─ Yes → Consider leveraged loop (Strategy 2)
                          └─ No → Simple borrow, plan to close when done
```

---

## What's Missing from the SDK

1. **No `minBuyAmount()` read** — SDK doesn't expose this, agents have to guess the minimum
2. **No way to read loan interest rate** — agent can't calculate borrowing cost before borrowing
3. **No vault APY calculation helper** — agent needs to track `convertToAssets` over time themselves
4. **`addToLoan` / `extendLoan` constraints unclear** — need better error handling or pre-checks
5. **No liquidation threshold read** — agent can't easily check "how close am I to liquidation?"
6. **`sell(claimUSDC=True)` not documented** — this atomic unstake→USDB is a major convenience feature that agents should know about
