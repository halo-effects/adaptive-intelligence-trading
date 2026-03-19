# APrivateTradingMarket — Contract Analysis

_Prepared for simulation discussion with Diamond. Source: MarketPrivate contract from Alex, 2026-03-17._

---

## Overview

This is the **creator-managed prediction market** contract. Creators control resolution (via voter panel), can restrict participation (private/whitelisted), and earn 100% of dev fee share. It combines a **bonding curve AMM** for price discovery with a **P2P order book** for secondary trading.

---

## Key Constants

| Constant | Value | Meaning |
|---|---|---|
| `INITIAL_VIRTUAL_RESERVE` | 1,000 USDB (1e21 in 18-decimal) | Starting virtual liquidity per outcome |
| `MAX_OUTCOMES` | 50 | Max outcomes per market |
| `ONE_USD` | 1e18 | USDB decimal precision (18 decimals) |
| `VOTING_WINDOW` | 15 minutes | Time between first vote and finalization |

---

## Bonding Curve Mechanics

### How share pricing works

Each outcome starts with a **virtual reserve** of 1,000 USDB. The price of an outcome is:

```
Price = outcomeVirtualReserve / totalVirtualReserve
```

For a 2-outcome market:
- Initial: each outcome = 1,000 / 2,000 = $0.50 (50%)
- For a 5-outcome market: each = 1,000 / 5,000 = $0.20 (20%)

### Buy mechanics (`_executeBuy`)

When buying shares of outcome `i`:

1. Tax is deducted first: `tax = usdcAmount × taxRate / 10000`
2. `netUsdc = usdcAmount - tax`
3. Both the outcome's reserve AND the total reserve increase by `netUsdc`
4. Shares minted: `sharesOut = (netUsdc × newTotal) / newVirt`
5. Slippage penalty applied if outcome probability exceeds 95%

**This means:** Buying an outcome increases its probability (reserve grows relative to total). The more you buy, the more expensive subsequent shares become — classic bonding curve behavior.

### Slippage protection (`_applySlippage`)

When an outcome's probability exceeds 95%:
```
remaining = 10000 - probBP   (e.g., if 96%, remaining = 400)
adjustedShares = sharesOut × remaining² / 250000
```

At 96% probability: shares reduced to (400² / 250000) = 64% of raw output
At 98% probability: shares reduced to (200² / 250000) = 16% of raw output
At 99%: (100² / 250000) = 4% of raw output

**This aggressively penalizes pushing any outcome above 95%.** It prevents one whale from cornering an outcome to near-certainty.

---

## Market Creation Parameters

```solidity
createMarket(
    marketName,      // "Who wins the election?"
    symbol,          // Token symbol
    endTime,         // When voting opens (0 = creator decides)
    _optionNames,    // ["Trump", "Biden", "Other"] — 2 to 50
    maintoken,       // Ecosystem token address
    privateEvent,    // true = whitelisted buyers only
    frozen,          // true = starts frozen (whitelist-only trading)
    bonding          // USDC for bonding phase
)
```

Key details:
- Creates a **Stable+ token** (hybridMultiplier = 100) via `ATokenFactory`
- Creator gets **100% dev share** (`addDevShare` with 10000 bps)
- Creator is auto-whitelisted and auto-added as first voter
- Token starts frozen if `frozen = true` — only whitelisted wallets can trade
- `bonding` parameter sets USDC allocated to initial bonding curve of the underlying token
- `startLP` hardcoded to 1000 (starting liquidity pool)

### What `bonding` and `startLP` control:

The `bonding` value is passed to `ATokenFactory.createToken()` as `usdcForBonding`. This determines:
- How much USDC seeds the underlying token's bonding curve
- Higher bonding = deeper initial liquidity = less price impact per trade
- `startLP = 1000` is the initial LP allocation for the underlying token AMM

**⚠️ This is separate from the prediction market virtual reserves.** The prediction market has its own virtual reserve system (1,000 USDB per outcome). The `bonding` parameter affects the underlying Stable+ token that the market is built on.

---

## Payout Mechanics

### Normal resolution (winning outcome exists with shares):

```
totalPool = generalPot + sum(all outcomes' totalCost)
payout = (userShares × totalPool) / winningOutcome.circulatingShares
```

**Winners split the ENTIRE pool** — all losing outcomes' costs flow to winners. This is the "up to 15x vs Polymarket" mechanic.

### Invalid resolution (CEO invalidates or voters vote OUTCOME_INVALID):

Pro-rata refund based on each user's proportional contribution:
```
For each outcome the user holds shares in:
  userContribution = (userShares × outcome.totalCost) / outcome.circulatingShares
Total payout = sum of contributions + proportional share of generalPot
```

### Edge case — winning outcome has 0 circulating shares:

All funds (generalPot + all totalCosts) go to `insuranceWallet`. Market is effectively invalidated even though a "winner" was chosen.

---

## P2P Order Book

### List order:
- Seller locks shares (can't double-sell)
- `pricePerShare = 0` means "sell at current bonding curve price" (market order)
- `pricePerShare` must be between $0.001 and $0.999 per share (1000–999000 in contract units)

### Buy order:
- Buyer pays `baseUsdc + buyerTax`
- Seller receives `baseUsdc - sellerTax`
- Both buyer and seller pay tax (via ATaxes)
- Price validation: `executionPrice <= currentPrice` — can't fill above current market price

### Hybrid fills (`buyOrdersAndContract`):
- Fill P2P orders first, then use remaining USDC on bonding curve
- Single transaction, atomic
- `minShares` applies to total (orders + curve combined)

---

## Resolution System

### Voter management:
- Creator adds/removes voters (max 11 including creator)
- Creator can't be removed
- Each voter picks an outcome (or OUTCOME_INVALID)

### Voting flow:
1. Voting opens at `endTime` (or `creationTime` if endTime = 0)
2. First vote starts 15-minute window
3. After window: anyone can call `finalize()`
4. Simple majority wins
5. **Tie-breaker: creator's vote wins** — so creator always has ultimate control

### CEO override:
- CEO can force `OUTCOME_INVALID` at any time → refunds all participants
- Bounty pool goes to insurance wallet on invalidation

### Bounty system:
- Anyone can donate to `bountyPool` (via `donate` from ATaxes)
- Correct voters split the bounty proportionally
- Incentivizes honest resolution

---

## Simulation Questions for Diamond

### Starting Liquidity
1. **Virtual reserve per outcome (1,000 USDB)** — is this enough? With 5 outcomes, total virtual reserve is $5,000. A $500 buy on one outcome would move its price significantly:
   - Before: 1,000/5,000 = 20%
   - After: 1,500/5,500 = 27.3%
   - That's a +36% relative price move from a $500 trade
   
2. **Should virtual reserve be configurable per market?** High-volume markets (elections, sports) might need 10,000+ per outcome. Low-volume (niche predictions) might be fine at 1,000.

3. **The `bonding` parameter** seeds the underlying token's liquidity, NOT the prediction market's virtual reserves. Are these meant to interact? Currently they seem independent.

### Volume Dynamics
4. **At what volume does the 95% slippage wall matter?** If total reserve is 5,000 and one outcome has 4,750 (95%), the remaining $250 of headroom gets exponentially expensive. Is that the intended behavior?

5. **P2P vs AMM split** — at what liquidity depth do P2P orders start being more efficient than the bonding curve? The hybrid fill (`buyOrdersAndContract`) suggests both should coexist, but the price relationship between them needs modeling.

6. **Tax impact on volume:** At 1.5% prediction tax rate (from ATaxes), round-trip cost is ~3%. How does this affect market efficiency and arbitrage?

### Payout Modeling
7. **Winner-takes-all pool math:** For a 10-outcome market where outcome #3 wins with 10% of total shares — remaining 90% of pool flows to that 10%. What's the effective multiplier curve look like?

8. **generalPot donations** — can creators seed the pot to make their market more attractive? What's the optimal pot-to-reserve ratio for attracting participants?

---

## Key Findings for Our SDK Scripts

- `buy()` accepts USDC, maintoken, OR marketToken as input — auto-converts via ASwap
- Private markets need explicit `togglePrivateEventBuyers()` calls
- Frozen markets need whitelist management
- Order book is integrated — our `bet.py` should check P2P orders before hitting the curve
- Creator gets 100% of trading fees on their market token (via `addDevShare` with 10000 bps)
- Resolution is creator-controlled (not oracle-based) — creator's vote is tiebreaker

---

_Contract saved for reference. Ready for simulation with Diamond._
