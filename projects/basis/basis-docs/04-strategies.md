# Strategy Playbooks

**What this covers:** All 5 strategy playbooks with step-by-step instructions and method cross-references.
**Related sections:** → See: [03-atomic-skills.md](03-atomic-skills.md) for method signatures · → See: [05-decision-trees.md](05-decision-trees.md) for situational decisions · → See: [09-fees.md](09-fees.md) for cost calculations · → See: [02-archetypes.md](02-archetypes.md) for which archetype each strategy serves

---

## Part 5 — Strategy Playbooks

---

### Strategy A: Predict Leverage Play

**Goal**: Maximum price exposure on a prediction market you create.

**Archetype**: Trader + Market Maker

```
1. Create prediction market on trending topic → earn 20% creator fees
2. Buy Predict+ tokens with leverage → amplified exposure
3. Hold during market activity → token price rises from slippage retention
4. (Optional) Bet on outcome with separate USDB
5. After resolution → wait through sell wave → exit LAST for highest price
```

**Income**: Creator fees + token appreciation + optional bet winnings.

**Method cross-references**:
- Step 1: → see: `predictionMarkets.createMarketWithMetadata()`
- Step 2: → see: `leverageSimulator.simulateLeverage()` (always simulate first), then → see: `trading.leverageBuy()`
- Step 4: → see: `predictionMarkets.buy()`
- Step 5: → see: `trading.sell()` or → see: `trading.sellPercentage()`

---

### Strategy B: Predict Loan-Bet Play

**Goal**: Multiple income streams from a single prediction market.

**Archetype**: Market Maker + Capital Manager

```
1. Create prediction market → earn 20% fees
2. Buy Predict+ tokens (no leverage) → tokens free to use as collateral
3. Take loan against Predict+ tokens → receive USDB
4. Bet on your conviction outcome using borrowed USDB
5. After resolution: collect winnings → repay loan → unlock tokens → exit at peak
```

**Income**: Creator fees + token appreciation + bet winnings + capital recycling.

**Method cross-references**:
- Step 1: → see: `predictionMarkets.createMarketWithMetadata()`
- Step 2: → see: `trading.buy()` (buy the Predict+ token itself, not outcome shares)
- Step 3: → see: `loans.takeLoan()` — use Predict+ token as collateral
- Step 4: → see: `predictionMarkets.buy()` — buy outcome shares with borrowed USDB
- Step 5a: → see: `predictionMarkets.redeem()`
- Step 5b: → see: `loans.repayLoan()`
- Step 5c: → see: `trading.sell()` — exit Predict+ token position

---

### Strategy C: Vault Compound

**Goal**: Set-and-forget treasury that auto-compounds.

**Archetype**: Capital Manager

```
1. Buy STASIS → stake in vault (wSTASIS)
2. Lock wSTASIS → borrow against it
3. Deploy borrowed capital into active strategies
4. When wSTASIS appreciates past threshold → refinance → extract more capital
5. Extend loan as needed (0.005%/day) → redeploy
```

**Income**: Vault yield + returns on deployed capital + refinance extractions.
**Agent manages**: Two variables — refinance threshold and loan timer.

**Method cross-references**:
- Step 1a: → see: `trading.buy()` — buy STASIS (use MAINTOKEN address)
- Step 1b: → see: `staking.buy()` — wrap STASIS into wSTASIS
- Step 2a: → see: `staking.lock()` — lock wSTASIS as collateral
- Step 2b: → see: `staking.borrow()` — borrow USDB against locked wSTASIS
- Step 4: → see: `staking.extendLoan()` with `refinance=true`
- Monitor: → see: `staking.convertToAssets()` — track wSTASIS appreciation

---

### Strategy D: Polymarket Mirror

**Goal**: Same events, better economics.

**Archetype**: Market Maker + Trader

```
1. Monitor Polymarket for popular markets
2. Create the SAME market on Basis (permissionless) → you're the creator
3. Promote: "Same predictions, bigger payouts"
4. Trade/bet on the Basis version
5. Earn creator fees + personal position returns
```

**Agent alpha**: Arbitraging the prediction market structure itself.

**Why this works**: Basis winners split the ENTIRE losing pool (not capped at $1/share like Polymarket). As creator, you earn 20% of all trading fees on your market forever.

**Method cross-references**:
- Step 2: → see: `predictionMarkets.createMarketWithMetadata()`
- Step 4: → see: `predictionMarkets.buy()` — bet on outcomes
- Step 4 (alt): → see: `trading.buy()` — buy Predict+ token for appreciation play
- Monitor creator fees: → see: `api.getToken(address)` — check market volume

---

### Strategy E: Capital Recycler

**Goal**: Never let capital sit idle. Continuous earn → lend → deploy → earn loop.

**Archetype**: Capital Manager + Any

```
1. Earn tokens from any activity
2. Lock as collateral → borrow at 2% flat fee
3. Deploy into next opportunity
4. When collateral appreciates → refinance → extract more
5. Repeat — compound indefinitely without selling
```

**Income**: Compounding returns across all deployed positions, with original position intact.

**The key insight**: You never sell your appreciating assets. You borrow against them at low flat cost (2% origination), deploy the borrowed capital, and let both pools work simultaneously.

**Method cross-references**:
- Step 2 (factory token collateral): → see: `loans.takeLoan()`
- Step 2 (STASIS collateral): → see: `staking.lock()` then → see: `staking.borrow()`
- Step 4 (hub loan refinance): → see: `loans.extendLoan()` with `refinance=true`
- Step 4 (vault refinance): → see: `staking.extendLoan()` with `refinance=true`
- Optimal: extend don't re-originate — → see: [09-fees.md](09-fees.md) for cost comparison
