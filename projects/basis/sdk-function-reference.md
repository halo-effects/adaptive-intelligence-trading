# Basis SDK — Function Reference & Agent Context

Every function: what it does, when an agent would use it, constraints discovered from live testing (2026-03-20).

---

## Trading Module

### `buy(token, usdbAmount, minOut?, wrapTokens?)`
**What**: Buys a token using USDB. Auto-builds the swap path (USDB → STASIS → token for factory tokens, USDB → STASIS for MAINTOKEN).
**When**: Agent wants to acquire a position in any token. Most common entry point.
**Constraints**: Minimum trade ~$1 but recommended $50+ for meaningful positions. Auto-approves USDB spend.
**Risk**: Slippage on low-liquidity tokens. Use `minOut` for protection.
**Combines with**: `sell()`, `leverageBuy()`, `getTokenPrice()` for pre-trade analysis.
**Points**: 1 pt per $1 traded.

### `sell(token, amount, toUsdb?, minOut?, swapToETH?)`
**What**: Sells a token. For factory tokens, `toUsdb=True` sells all the way to USDB (3-hop), otherwise stops at STASIS (2-hop).
**When**: Agent wants to exit a position or take profit.
**Constraints**: Must have sufficient token balance. Auto-approves.
**Risk**: 3-hop sells have more slippage. Check `getAmountsOut()` first.

### `sellPercentage(token, percentage, toUsdb?, minOut?, swapToETH?)`
**What**: Sells a percentage (1-100) of your token balance. Reads balance on-chain, calculates amount, executes sell.
**When**: "Sell 50% of my position" — more natural for portfolio management than exact amounts.
**Constraints**: Percentage must be 1-100.

### `buyTokens(amount, minOut, path, wrapTokens)` / `sellTokens(amount, minOut, path, swapToETH)`
**What**: Raw buy/sell with explicit swap path. Power user functions.
**When**: Agent needs custom routing (e.g., specific intermediate tokens).
**Constraints**: Path must be valid (token pairs must have liquidity).

### `leverageBuy(amount, minOut, path, numberOfDays)`
**What**: Opens a leveraged long position. Borrows against the purchased tokens automatically.
**When**: Agent wants amplified exposure. The loan duration is the leverage window.
**Constraints**: 
- **Minimum 10 days duration** (discovered in testing — contract rejects shorter)
- Path determines the collateral token
- Position tracked via `getLeverageCount()` / `getLeveragePosition()`
**Risk**: Liquidation if token drops enough. Check leverage simulator first.
**Combines with**: `partialLoanSell()` to exit, `getLeveragePosition()` to monitor.
**Points**: 200 pts for opening + 1 pt per $1.

### `partialLoanSell(loanId, percentage, isLeverage, minOut?)`
**What**: Sells a percentage of a leverage OR loan position. Dual purpose.
**When**: Taking partial profit on leverage, or reducing loan collateral.
**Constraints**: 
- `isLeverage=True` for leverage positions, `False` for direct loans
- Loan ID comes from position index (use `getLeverageCount() - 1` for latest)
- **Must be called by the position owner** ("Not user" error otherwise)
**Risk**: Selling too much can trigger liquidation on remaining position.

### `convertToNative(marketToken, inputToken, inputAmount)`
**What**: Converts prediction market tokens back to USDB via the AMM.
**When**: Agent wants to exit a prediction market position without waiting for resolution.
**Constraints**: Only works for prediction market tokens. Market must still be active.

### `getAmountsOut(amount, path)`
**What**: Simulates a swap to see how many tokens you'd receive.
**When**: Pre-trade analysis, slippage estimation, comparing routes.
**Returns**: Expected output amount in the final token.

### `getTokenPrice(token)` / `getUSDPrice(token)`
**What**: Gets the current token price in STASIS terms (`getTokenPrice`) or USD terms (`getUSDPrice`).
**When**: Dashboard display, position valuation, entry/exit decisions.
**Note**: For MAINTOKEN (STASIS), both return the same value since STASIS/USDB ≈ 1:1.

### `getLeverageCount(user)` / `getLeveragePosition(user, id)`
**What**: Returns total leverage positions count and individual position details.
**When**: Monitoring open leverage, checking liquidation risk, finding position IDs.
**Constraints**: Position IDs are 0-indexed. Use `count - 1` for the latest.
**Returns**: Position struct with user, token, collateralAmount, fullAmount, borrowedAmount, liquidationTime, isLiquidated, active, creationTime.

---

## Loans Module

### `takeLoan(ecosystem, collateral, amount, daysCount)`
**What**: Takes a loan using tokens as collateral. Borrows USDB against your tokens.
**When**: Agent needs liquidity without selling. Classic DeFi leverage play.
**Constraints**:
- **Minimum 10 days duration** (contract enforced)
- `ecosystem` = MAINTOKEN address (always)
- `collateral` = the token you're pledging
- `amount` = collateral amount in wei
- Auto-approves collateral to LoanHub
**Risk**: Liquidation if collateral value drops below threshold.
**Points**: 200 pts for taking + 1 pt per day held.

### `getUserLoanDetails(user, hubId)` 
**What**: Returns full loan details struct.
**When**: Checking loan health, calculating repayment, monitoring liquidation.
**Constraints**: 
- ⚠️ **Hub IDs are 1-indexed, NOT 0-indexed!** Calling with `hubId=0` returns "Loan does not exist"
- `getUserLoanCount()` returns total count, but first valid ID is 1
- This is a known SDK gap — the SDK doesn't parse hub IDs from transaction receipts
**Returns**: Struct with hubId, ecosystem, coreLoanId, collateralToken, token, collateralAmount, liquidatedAmount, fullAmount, borrowedAmount, liquidationTime, liquidationClaim, isLiquidated, active, creationTime.

### `repayLoan(hubId)`
**What**: Repays a loan in full, releasing collateral.
**When**: Agent wants to close the loan position and reclaim tokens.
**Constraints**: Auto-approves USDB for repayment. Hub ID must be valid (1-indexed).

### `extendLoan(hubId, addDays, payInStable, refinance)`
**What**: Extends the loan duration.
**When**: Loan approaching expiry but agent wants to keep position open.
**Constraints**: `payInStable=True` pays extension fee in USDB; `refinance=False` for simple extension.

### `increaseLoan(hubId, amountToAdd)`
**What**: Adds more collateral to an existing loan, reducing liquidation risk.
**When**: Collateral value dropping, agent wants to shore up the position.
**Constraints**: Reads loan details to find collateral token, auto-approves.

### `hubPartialLoanSell(hubId, percentage, isLeverage, minOut?)`
**What**: Partial sell through the LoanHub (alternative to `trading.partialLoanSell()`).
**When**: Closing part of a hub-routed loan/leverage position.

### `claimLiquidation(hubId)`
**What**: Claims remaining value from a liquidated loan.
**When**: After a loan has been liquidated, recover any excess collateral.
**Constraints**: Loan must actually be liquidated (`isLiquidated=true`).

### `getUserLoanCount(user)`
**What**: Returns total number of loans for a user.
**Constraints**: ⚠️ Count includes all loans (active + repaid). IDs are 1-indexed.

---

## Staking Module

### `buy(amount)` — Wrap STASIS → wSTASIS
**What**: Wraps STASIS tokens into wSTASIS (yield-bearing vault shares).
**When**: Agent wants to earn staking yield on STASIS holdings.
**Constraints**: Must hold STASIS tokens. Auto-approves.
**Points**: 2 pts per $1 per day staked.

### `sell(shares, claimUsdb?, minUsdb?)` — Unwrap wSTASIS → STASIS
**What**: Unwraps wSTASIS back to STASIS.
**When**: Agent wants to exit staking position or needs liquid STASIS.

### `lock(shares)` / `unlock(shares)`
**What**: Locks wSTASIS shares as collateral for borrowing. Unlock releases them.
**When**: Agent wants to borrow against staked position.
**Constraints**: Must lock before borrowing. Can only unlock after repaying any active loan.

### `borrow(stasisAmountToBorrow, days)`
**What**: Borrows STASIS against locked wSTASIS.
**When**: Agent needs STASIS liquidity without unstaking.
**Constraints**:
- **Minimum borrow amount exists** — 0.5 STASIS too small, try 5+ STASIS
- **Minimum 10 days duration** (same as regular loans)
- Must have locked shares first

### `repay()`
**What**: Repays the active staking loan.
**When**: Closing the borrow position. Auto-approves repayment.

### `addToLoan(additionalStasisToBorrow)`
**What**: Increases the borrowed amount on an active staking loan.
**When**: Agent needs more liquidity from same collateral.
**Constraints**: ⚠️ "Duration too short" error seen — may require minimum remaining duration on the existing loan.

### `extendLoan(daysToAdd, payInUsdb, refinance)`
**What**: Extends staking loan duration.
**Constraints**: ⚠️ "not possible" error seen — may require specific loan state (e.g., not too close to expiry, or minimum extension period).

### `getAvailableStasis(user)` / `convertToShares(assets)` / `convertToAssets(shares)` / `getUserStakeDetails(user)`
**What**: Read functions for staking state.
**When**: Checking position size, conversion rates, available collateral.
**`getUserStakeDetails` returns**: [unlockedShares, lockedShares, borrowedAmount, loanFullAmount]

---

## Vesting Module

### `createGradualVesting(beneficiary, token, totalAmount, startTime, durationInDays, timeUnit, memo, ecosystem)`
**What**: Creates a vesting schedule that unlocks tokens gradually over time.
**When**: Token creator wants to vest tokens for team members, investors, or advisors.
**Constraints**:
- ⚠️ **startTime must be in the future** — by the time tx confirms, `time.time()` is already past. Use `time.time() + 60` minimum buffer.
- `timeUnit`: 0 = per-second (fastest), 1 = per-day, 2 = per-month
- `durationInDays`: minimum 1
- Auto-approves tokens + pays creation fee in BNB
**Points**: Vesting creator earns points for ecosystem building.

### `createCliffVesting(beneficiary, token, totalAmount, unlockTime, memo, ecosystem)`
**What**: Creates a cliff vesting — all tokens unlock at once at `unlockTime`.
**When**: Simple lockup with single unlock date.
**Constraints**: ⚠️ **Minimum 1 hour duration** from creation time (contract enforced).

### `batchCreateGradualVesting(beneficiaries[], ...)` / `batchCreateCliffVesting(beneficiaries[], ...)`
**What**: Creates vestings for multiple beneficiaries in one transaction.
**When**: Team token distributions, airdrop lockups.
**Constraints**: Arrays must match in length (beneficiaries, amounts, memos).

### `claimTokens(vestingId)`
**What**: Claims unlocked tokens from a vesting schedule.
**When**: Tokens have become available based on the vesting schedule.

### `takeLoanOnVesting(vestingId)` / `repayLoanOnVesting(vestingId)`
**What**: Borrow against unvested tokens / repay that loan.
**When**: Agent needs liquidity before full vesting completes.

### `changeBeneficiary(vestingId, newBeneficiary)` / `transferCreatorRole(vestingId, newCreator)`
**What**: Management functions for vesting schedules.
**Constraints**: `changeBeneficiary` requires creator role. `transferCreatorRole` transfers management.

### `extendVestingPeriod(vestingId, additionalDays)` / `addTokensToVesting(vestingId, additionalAmount)`
**What**: Extends the vesting schedule or adds more tokens.
**Constraints**: Creator role required.

### `getVestingDetails(id)` / `getClaimableAmount(id)` / `getVestingsByBeneficiary(user)` / `getVestingsByCreator(user)`
**What**: Read functions for vesting state.

---

## Prediction Markets Module

### `createMarketWithMetadata(marketName, symbol, endTime, optionNames, maintoken, seedAmount, description?, imageUrl?)`
**What**: Creates a new prediction market with on-chain + IPFS metadata.
**When**: Agent wants to create a betting market on any yes/no or multi-outcome question.
**Constraints**: 
- `seedAmount` in USDB — higher seed = deeper liquidity
- `endTime` = Unix timestamp when betting closes
- `optionNames` = array of outcome labels
- Returns `market_token_address` — save this, it's the market's identity
**Points**: 300 pts for market creation.

### `buy(marketToken, outcomeId, inputToken, inputAmount, minUsdb, minShares)`
**What**: Buys shares in a specific outcome.
**When**: Agent has a prediction and wants to bet on it.
**Constraints**: `outcomeId` starts at 0. `inputToken` is usually USDB.

### `buyOrdersAndContract(marketToken, outcomeId, orderIds[], inputToken, totalInput, minShares)`
**What**: Hybrid buy — fills limit orders first, then uses AMM for remainder.
**When**: Getting the best price by combining order book + AMM liquidity.
**Constraints**: Pass empty `orderIds[]` to use AMM only.

### `redeem(marketToken)`
**What**: Claims winnings after market resolution.
**When**: Market has been resolved and agent holds winning shares.
**Constraints**: Market must be finalized. Returns USDB proportional to winning shares.

### `getMarketData(marketToken)` / `getOutcome(marketToken, outcomeId)` / `getUserShares(marketToken, user, outcomeId)`
**What**: Read current market state, outcome details, user positions.

### `getNumOutcomes(marketToken)` / `getOptionNames(marketToken)` / `hasBettedOnMarket(marketToken, user)`
**What**: Market structure reads.

### `getBountyPool(marketToken)` / `getGeneralPot(marketToken)`
**What**: Bounty pool = resolver rewards. General pot = total USDB in the market.

### `getInitialReserves(numOutcomes)`
**What**: Returns the initial AMM reserve configuration for a given number of outcomes.

### `getBuyOrderAmountsOut(marketToken, orderId, usdbAmount)`
**What**: Simulates buying a limit order — returns [sharesOut, fee, totalCost, netCost].

---

## Order Book Module

### `listOrder(marketToken, outcomeId, amount, pricePerShare)`
**What**: Lists shares for sale on the order book at a fixed price.
**When**: Agent wants to sell shares at a specific price rather than market-selling into the AMM.
**Constraints**: Must hold sufficient shares. Price in wei (e.g., 6×10¹⁷ = 0.60 USDB per share).
**Points**: Orders auto-sync to backend.

### `cancelOrder(marketToken, orderId)`
**What**: Cancels a listed order, returning shares to the seller.

### `buyOrder(marketToken, orderId, fill)`
**What**: Buys shares from a specific limit order.
**Constraints**: ⚠️ **Cannot fill your own order** (contract enforced — "Cannot fill own order").

### `buyMultipleOrders(marketToken, orderIds[], usdbAmount)`
**What**: Fills multiple orders in one transaction.

### `getBuyOrderCost(marketToken, orderId, fill)`
**What**: Simulates order fill cost. Returns [sharesOut, fee, totalCost, netCost].

---

## Market Reader Module

### `getAllOutcomes(routerAddress, marketToken)`
**What**: Returns all outcomes with full data — name, reserves, shares, probability, percentage.
**When**: Dashboard display, market analysis, comparing outcome odds.
**Returns**: Array of tuples: (id, name, reserves, userReserves, userShares, probability, percentBasisPoints, isWinner).

### `estimateSharesOut(routerAddress, marketToken, outcomeId, usdbAmount, orderIds[], user)`
**What**: Estimates shares received for a given USDB input.
**When**: Pre-trade analysis for prediction markets.

### `getPotentialPayout(routerAddress, marketToken, outcomeId, sharesAmount, estimatedUsdbToPool)`
**What**: Estimates the payout if an outcome wins.
**When**: Risk/reward analysis before betting.

---

## Market Resolver Module

### `proposeOutcome(marketToken, outcomeId)`
**What**: Proposes the winning outcome after market end time.
**When**: Market has ended and someone needs to initiate resolution. Requires bond.

### `dispute(marketToken, newOutcomeId)`
**What**: Disputes the proposed outcome with a counter-proposal. Requires higher bond.

### `vote(marketToken, outcomeId)` 
**What**: Votes on the correct outcome during a dispute.
**Constraints**: Must be a staked voter (call `stake()` first).

### `stake(token)` / `unstake(token)`
**What**: Stake tokens to become an eligible voter in disputes.
**Constraints**: Cannot unstake during active vote lock period.

### `finalizeUncontested(marketToken)`
**What**: Finalizes a market where the proposed outcome was not disputed within the dispute period.
**When**: Happy path — propose → wait → finalize → everyone redeems.

### `finalizeMarket(marketToken)`
**What**: Finalizes a market after a dispute has been resolved by voting.

### `claimBounty(marketToken)` / `claimEarlyBounty(marketToken, round)`
**What**: Claims resolver bounty rewards for participating in resolution/disputes.

### Read functions: `isResolved()`, `isInDispute()`, `isInVeto()`, `getCurrentRound()`, `isVoter()`, `getVoteCount()`, `hasVoted()`, `getVoterChoice()`, `getBountyPerVote()`, `hasClaimed()`
**Constraints**: 
- ⚠️ `getDisputeData()`, `getUserStake()`, `getConstants()` are defined in the SDK but **missing from the compiled ABI**. These need ABI updates to work.

---

## Private Markets Module

### `createMarket(marketName, symbol, endTime, optionNames, maintoken, frozen, bonding, seedAmount?)`
**What**: Creates a private prediction market with controlled access.
**Constraints**: ⚠️ **ABI mismatch discovered** — the SDK passes 8 arguments but the contract ABI expects a different signature. Needs SDK fix.

### `buy()` / `redeem()` / `listOrder()` / `cancelOrder()` / `buyOrder()` / `buyMultipleOrders()` / `buyOrdersAndContract()`
**What**: Same as public market equivalents but for private markets.

### `getMarketData()` / `getOutcome()` / `getUserShares()` / `getInitialReserves()` / `getBuyOrderCost()`
**What**: Read functions — same interface as public markets.

---

## Factory Module

### `createTokenWithMetadata(name, symbol, description, imageUrl, frozen?, ...)`
**What**: Creates a new token on the Basis platform with on-chain creation + IPFS metadata.
**When**: Agent is launching a new token/project.
**Constraints**: ⚠️ No `initial_buy_amount` parameter currently — need to create token first, then buy separately.
**Points**: 500 pts for token creation.

### `setWhitelistedWallet(tokenAddress, wallets[], amount, tag)` / `removeWhitelist(tokenAddress, wallet)`
**What**: Manages whitelist for frozen tokens — controls who can buy and how much.
**When**: Token creator wants controlled distribution before public trading.
**Constraints**: Creator/dev only.

### `disableFreeze(tokenAddress)`
**What**: Permanently removes the freeze, allowing unrestricted trading.
**When**: Token creator is ready for public trading.
**Constraints**: Irreversible. Creator/dev only.

### `claimRewards(tokenAddress)`
**What**: Claims accumulated trading fee rewards for a token you created/hold.
**When**: Passive income collection from token trading activity.

### `getClaimableRewards(tokenAddress, investor)` / `getTokenState(tokenAddress)` / `isEcosystemToken(tokenAddress)` / `getTokensByCreator(creator)` / `getFeeAmount()`
**What**: Read functions for factory/token state.
**`getTokenState` returns**: { frozen, hasBonded, totalSupply, usdPrice }

---

## Leverage Simulator Module

### `simulateLeverage(amount, path, numberOfDays)` / `simulateLeverageFactory(amount, path, numberOfDays)`
**What**: Simulates leverage outcomes without executing. `simulateLeverageFactory` for factory tokens (3-hop path).
**When**: Risk analysis before opening leverage. Shows collateral, borrowed, liquidation levels.
**Returns**: Tuple with collateral amounts, borrowed amounts, fees, liquidation thresholds.

---

## Taxes Module

### `getTaxRate(token, user)`
**What**: Returns the current tax rate (in basis points) for a user trading a specific token.
**Returns**: Integer in basis points (e.g., 50 = 0.50%).

### `getCurrentSurgeTax(token)`
**What**: Returns any active surge tax on a token (anti-dump mechanism).
**Returns**: 0 if no surge active.

### `getAvailableSurgeQuota(token)`
**What**: Returns remaining time before surge tax can be activated.

### `getBaseTaxRates()`
**What**: Returns platform base tax rates.
**Returns**: { stasis: 50, stable: 50, default: 150, prediction: 150 } (basis points).

---

## Agent Identity Module (ERC-8004)

### `register(config?)` / `registerAndSync(config?)`
**What**: Registers an AI agent on-chain. `registerAndSync` also syncs to the Basis backend.
**When**: Agent wants an on-chain identity for autonomous trading.
**Constraints**: One registration per wallet.
**Points**: Agent registration earns platform recognition.

### `isRegistered(wallet)` / `lookupFromApi(wallet)` / `listAgents(page, limit)` / `getAgentUri(agentId)` / `getAgentWallet(agentId)`
**What**: Read functions for agent registry.

### `setAgentUri(agentId, newUri)`
**What**: Updates the agent's metadata URI.

---

## API Module (Off-Chain)

### Auth: `createApiKey(label)` / `listApiKeys()` / `deleteApiKey(keyId)`
**What**: Manage API keys for authenticated access.
**Constraints**: ⚠️ `createApiKey` returns 400 if you already have a key with the same label.

### Media: `uploadImage(filePath)` / `uploadImageFromUrl(imageUrl)`
**What**: Uploads images to IPFS via Pinata. Returns IPFS URL.

### Token data: `getTokens(limit?)` / `getToken(address)` / `getTokenCandles(token, interval, limit)` / `getTokenTrades(token, limit)` / `getTokenOrders(token, limit)` / `getTokenComments(token, limit)` / `getTokenWhitelist(token)`
**What**: Backend data endpoints for token analytics.
**Constraints**: ⚠️ Newly created tokens may return 404 until indexed by backend (slight delay).
**Note**: Python SDK uses `get_token_candles()` etc. (not `get_candles()`).

### Metadata: `updateMetadata(token, description?, ...)` / `updateProject(token, ...)`
**What**: Updates token/project metadata on the backend.
**Constraints**: ⚠️ `updateMetadata` returns 409 Conflict if metadata hasn't changed. `updateProject` signature needs verification.

### Social: `createComment(token, content, authorAddress)` / `deleteComment(commentId, authorAddress)`
**What**: Token discussion comments.
**Constraints**: ⚠️ Python SDK `create_comment` requires `author_address` as a separate positional arg.

### Verification: `requestTwitterChallenge()` / `verifyTwitter(tweetUrl)`
**What**: X/Twitter account verification flow.
**Returns**: Challenge code + tweet template. User tweets it, then calls `verifyTwitter` with tweet URL.

### Orders: `syncOrder(txHash, marketType?)`
**What**: Syncs an on-chain order to the backend for display.

### Wallet: `getWalletTransactions(wallet, limit?)` / `getMarketLiquidity(marketToken, limit?)`
**What**: Transaction history and market liquidity data.

---

## Known Issues & Constraints Summary

| Issue | Type | Status |
|-------|------|--------|
| Loan hub IDs are 1-indexed, not 0 | Contract design | Document |
| Min loan duration: 10 days | Contract constraint | Document |
| Min vesting cliff: 1 hour | Contract constraint | Document |
| Min staking borrow amount: ~5 STASIS | Contract constraint | Document |
| Cannot fill own orders | Contract design | Document |
| Vesting start time must be future (+60s buffer) | Contract constraint | Document |
| `createTokenWithMetadata` missing `initial_buy_amount` | SDK gap | Fix needed |
| `privateMarkets.createMarket` ABI mismatch | SDK bug | Fix needed |
| Resolver ABI missing 3 functions | SDK bug | Fix needed |
| `api.updateProject` wrong kwargs | SDK bug | Fix needed |
| `api.createComment` signature mismatch | SDK bug | Fix needed |
| New tokens 404 on API until indexed | Backend timing | Document |
| `createApiKey` 400 on duplicate label | Backend constraint | Document |
| `staking.addToLoan` "Duration too short" | Unclear constraint | Investigate |
| `staking.extendLoan` "not possible" | Unclear constraint | Investigate |
