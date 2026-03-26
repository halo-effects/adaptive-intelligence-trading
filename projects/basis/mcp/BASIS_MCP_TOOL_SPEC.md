# Basis MCP Server — Tool Specification

_For Alex / AI coding agent. Maps Basis SDK methods to MCP tools._
_Generated from COMPLETE_V2.md (v1.0.1) on 2026-03-26._

---

## Overview

44 tools across 7 modules. Each tool wraps one or more SDK methods, handles address resolution (names → addresses), amount conversion (human numbers → 18-decimal raw), and returns clean JSON.

**Conventions:**
- All amounts are in **human-readable units** (e.g., `50` = 50 USDB). The MCP server converts to raw 18-decimal internally.
- Token names like `"STASIS"` are resolved to addresses internally. Agents can also pass raw addresses.
- All write tools return `{ hash, receipt, ...extra }`. All read tools return the data directly.
- The server needs a private key configured at startup (env var `BASIS_PRIVATE_KEY`).

---

## Module 1: Trading (7 tools)

### `buy_token` ⚡ write
Buy a token using USDB.
**When:** You want exposure to a token — whether for trading, staking, or building a position. This is the starting point for almost every strategy.
**Why:** All Basis tokens are elastic supply (minted on buy, burned on sell). Buying increases price. Stable+ tokens only go up; Floor+ tokens go up on buy and partially down on sell. Every buy earns airdrop points.
| Param | Type | Required | Description |
|-------|------|----------|-------------|
| `token` | string | yes | Token name (e.g., "STASIS") or address |
| `amount_usdb` | number | yes | USDB to spend |
| `slippage_percent` | number | no | Max slippage % (default: 1). Server calculates minOut via getAmountsOut. |
| `wrap` | boolean | no | Wrap output to wSTASIS (default: false) |

**SDK:** `client.trading.buy(tokenAddress, parseUnits(amount, 18), minOut, wrap)`
**Guardrail:** Preview via `getAmountsOut()` before executing. Return preview in response.

---

### `sell_token` ⚡ write
Sell a token for USDB.
**When:** You want to take profit, exit a position, or free up USDB for another opportunity. Use `percentage` when you want to scale out gradually.
**Why:** Selling burns tokens. On Stable+ tokens, the price still doesn't decrease (sell value stays in pool). On Floor+ tokens, price drops but not as much as a traditional AMM — the floor absorbs impact.
| Param | Type | Required | Description |
|-------|------|----------|-------------|
| `token` | string | yes | Token name or address |
| `amount` | number | no | Token amount to sell (omit to use percentage) |
| `percentage` | number | no | 1-100, sell this % of balance |
| `slippage_percent` | number | no | Max slippage % (default: 1) |

**SDK:** If `percentage` provided → `client.trading.sellPercentage(token, percentage, true)`. Otherwise → `client.trading.sell(token, amount, true, minOut)`.
**Guardrail:** Check balance before selling. Preview output amount.

---

### `get_price` 📖 read
Get the current USD price of a token.
**When:** Before any trade to check current price. Also useful for monitoring positions or comparing tokens.
**Why:** Prices change with every trade (elastic supply). Always check before acting.
| Param | Type | Required | Description |
|-------|------|----------|-------------|
| `token` | string | yes | Token name or address |

**SDK:** `client.trading.getUSDPrice(tokenAddress)`
**Returns:** `{ token, price_usd, token_address }`

---

### `preview_trade` 📖 read
Preview a buy or sell without executing.
**When:** Before every trade. Shows you exactly what you'll receive and the price impact. Essential for large positions where slippage matters.
**Why:** Price impact varies by pool depth and trade size. A $10 trade might have 0.1% impact; a $1,000 trade on the same token might have 5%. Always preview first.
| Param | Type | Required | Description |
|-------|------|----------|-------------|
| `token` | string | yes | Token name or address |
| `amount_usdb` | number | yes | USDB amount to simulate |
| `direction` | string | yes | `"buy"` or `"sell"` |

**SDK:** `client.trading.getAmountsOut(amount, path)`
**Returns:** `{ input, output, price_impact_bps, effective_price }`

---

### `leverage_buy` ⚡ write
Open a leveraged position. Always simulates first.
**When:** You have high conviction on a token and want amplified exposure. Best on Stable+ tokens (no price liquidation risk, up to 20-36x leverage) or Floor+ tokens at launch (when floor ≈ spot price).
**Why:** Basis leverage has NO price liquidation — only time-based expiry. A $10 input can produce a ~$200 position. The tradeoff is cumulative fees (2% per loop iteration). Always simulate to see the real cost before committing.
| Param | Type | Required | Description |
|-------|------|----------|-------------|
| `token` | string | yes | Token name or address (STASIS or factory token) |
| `amount_usdb` | number | yes | USDB collateral to leverage |
| `days` | number | yes | Loan duration (min 10, max 1000) |
| `confirm` | boolean | yes | Must be true. Forces agent to see simulation first. |

**SDK:** `client.leverageSimulator.simulateLeverage()` or `simulateLeverageFactory()` → then `client.trading.leverageBuy()`
**Guardrail:** Always simulate first. Return simulation results. Require `confirm=true`.
**Returns:** `{ simulation: { total_collateral, total_borrowed, total_fees, effective_leverage }, execution: { hash, receipt } }`

---

### `close_leverage` ⚡ write
Close (or partially close) a leverage position.
**When:** You want to take profit on a leveraged position, or the loan expiry is approaching and you want to exit cleanly. Partial close (e.g., 50%) lets you take profit while keeping remaining exposure.
**Why:** If you don't close before expiry, the protocol auto-liquidates — collateral is burned to repay debt and any remaining value must be claimed separately. Better to close proactively.
| Param | Type | Required | Description |
|-------|------|----------|-------------|
| `position_id` | number | yes | Leverage position ID |
| `percentage` | number | no | 10-100, must be divisible by 10 (default: 100 = full close) |

**SDK:** `client.trading.partialLoanSell(positionId, percentage, true, 0)`
**Guardrail:** Validate percentage is multiple of 10.

---

### `get_leverage_positions` 📖 read
List all leverage positions for the wallet.
**When:** To monitor active leverage positions — check PnL, expiry dates, and decide whether to close or extend. Run periodically if you have open positions.
**Why:** Leverage positions have time-based expiry. You need to track them to avoid auto-liquidation.
| Param | Type | Required | Description |
|-------|------|----------|-------------|
| (none) | | | Uses configured wallet |

**SDK:** `client.trading.getLeverageCount(wallet)` → loop `client.trading.getLeveragePosition(wallet, id)` for each
**Returns:** Array of position objects with: id, token, collateral, borrowed, active, expiry

---

## Module 2: Token Creation (6 tools)

### `create_token` ⚡ write
Create a new token with metadata.
**When:** You want to start a token-based business. You become the "dev" and earn 20% of every trade on your token — forever. Use Stable+ for treasury/loyalty tokens (price only goes up). Use Floor+ for trading tokens (real price movement with downside protection).
**Why:** Token creation is the path to passive income on Basis. Every trade generates fees, and 20% flows to you permanently. Anti-rug by design — elastic supply means zero pre-minting.
| Param | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | yes | Token full name |
| `symbol` | string | yes | Token ticker |
| `type` | string | yes | `"stable_plus"` or `"floor_plus"` |
| `stability` | number | no | 1-90 for Floor+ (default: 50). Ignored for Stable+. |
| `start_lp` | number | no | Starting virtual liquidity 100-10000 (default: 1000) |
| `description` | string | no | Token description |
| `image_url` | string | no | Image URL (auto-resized to 512×512) |
| `website` | string | no | Website URL |
| `telegram` | string | no | Telegram link |
| `twitter` | string | no | Twitter/X link |
| `frozen` | boolean | no | Start frozen (default: false) |
| `reward_phase_volume` | number | no | USDB volume threshold for reward phase (default: 0) |

**SDK:** `client.factory.createTokenWithMetadata({...})`. Maps `type`→`hybridMultiplier` (stable_plus=100, floor_plus=stability value).
**Returns:** `{ hash, token_address, image_url }`

---

### `unfreeze_token` ⚡ write
Open a frozen token to public trading.
**When:** After you've completed a controlled launch — whitelisted early buyers have entered, and you're ready for public access.
**Why:** Frozen tokens restrict trading to whitelisted wallets only. Unfreeze is irreversible — once public, anyone can trade.
| Param | Type | Required | Description |
|-------|------|----------|-------------|
| `token` | string | yes | Token address |

**SDK:** `client.factory.disableFreeze(tokenAddress)`

---

### `whitelist_wallets` ⚡ write
Add wallets to a frozen token's whitelist.
**When:** During a controlled launch — you want specific wallets (team, investors, early supporters) to buy before the public.
**Why:** Whitelisting with max buy limits lets you control who gets in early and how much, preventing whales from dominating the initial supply.
| Param | Type | Required | Description |
|-------|------|----------|-------------|
| `token` | string | yes | Token address |
| `wallets` | string[] | yes | Wallet addresses |
| `max_buy_usdb` | number | yes | Max USDB buy per wallet |
| `tag` | string | no | Label/note |

**SDK:** `client.factory.setWhitelistedWallet(token, wallets, amount, tag)`

---

### `get_token_state` 📖 read
Get token state (frozen, bonded, supply, price).
**When:** To check a token's current status before trading or to monitor your own token. Shows whether it's still in reward phase, frozen, and current metrics.
**Why:** Token state affects what actions are available — frozen tokens restrict trading, reward phase tokens earn extra for early buyers.
| Param | Type | Required | Description |
|-------|------|----------|-------------|
| `token` | string | yes | Token name or address |

**SDK:** `client.factory.getTokenState(tokenAddress)`
**Returns:** `{ frozen, has_bonded, total_supply, usd_price }`

---

### `claim_rewards` ⚡ write
Claim accumulated rewards from the reward phase.
**When:** You bought tokens during the reward phase and fees have accumulated. Check periodically — rewards grow as the token generates trading volume.
**Why:** Early buyers earn a share of trading fees during the reward phase. These accrue over time and must be explicitly claimed.
| Param | Type | Required | Description |
|-------|------|----------|-------------|
| `token` | string | yes | Token address |

**SDK:** `client.factory.claimRewards(tokenAddress)`

---

### `get_my_tokens` 📖 read
List all tokens created by the wallet.
**When:** To check on your token businesses — see which tokens you've created, their current prices, and supply. Useful for tracking dev fee income.
**Why:** As a token creator, you earn 20% of all trading fees. Monitor your tokens to see which are generating volume.
| Param | Type | Required | Description |
|-------|------|----------|-------------|
| (none) | | | Uses configured wallet |

**SDK:** `client.factory.getTokensByCreator(wallet)`
**Returns:** Array of token addresses. Enrich with `getTokenState()` + `getUSDPrice()` for each.

---

## Module 3: Prediction Markets (12 tools)

### `create_market` ⚡ write
Create a prediction market with metadata.
**When:** You have a question the market cares about — trending topics, crypto prices, real-world events. As creator, you earn 20% of net trading fees on this market forever, regardless of the outcome.
**Why:** Prediction markets are a business: you earn creator fees, the Predict+ token appreciates from trading volume (Stable+ mechanics), and you can also bet on outcomes yourself. Mirror popular markets from Polymarket/Kalshi for instant relevance — same questions, better economics (uncapped payouts).
| Param | Type | Required | Description |
|-------|------|----------|-------------|
| `question` | string | yes | Market question/title |
| `symbol` | string | yes | Market token symbol |
| `outcomes` | string[] | yes | Outcome names (e.g., ["Yes", "No"]) |
| `end_time` | string | yes | ISO date string or unix timestamp |
| `seed_usdb` | number | no | USDB seed amount (min 50, default: 50) |
| `description` | string | no | Market description |
| `image_url` | string | no | Image URL |

**SDK:** `client.predictionMarkets.createMarketWithMetadata({...})`
**Returns:** `{ hash, market_token_address, outcomes }`

---

### `bet` ⚡ write
Buy shares in a prediction market outcome.
**When:** You have conviction about an outcome. Buy shares when probability is low (cheap) for maximum payout if correct. Winners split the ENTIRE losing pool — uncapped, unlike Polymarket's $1/share cap.
**Why:** This is separate from buying the Predict+ token. Betting = buying outcome shares. If your outcome wins, you split all the USDB from losing outcomes + the general pot. Multi-outcome markets can deliver 8x+ returns.
| Param | Type | Required | Description |
|-------|------|----------|-------------|
| `market` | string | yes | Market token address |
| `outcome` | string or number | yes | Outcome name or index (0-based) |
| `amount_usdb` | number | yes | USDB to bet |

**SDK:** Resolve outcome name→index via `getOptionNames()`. Then `client.predictionMarkets.buy(market, outcomeId, USDB, amount, 0, 0)`
**Returns:** `{ hash, shares_received, outcome_name, current_probability }`

---

### `redeem_winnings` ⚡ write
Claim winnings from a resolved market.
**When:** A market you bet on has been resolved and your outcome won. Must be called explicitly — winnings don't auto-distribute.
**Why:** Your share of the losing pool is waiting to be claimed. Don't leave money on the table.
| Param | Type | Required | Description |
|-------|------|----------|-------------|
| `market` | string | yes | Market token address |

**SDK:** `client.predictionMarkets.redeem(market)`

---

### `get_market_info` 📖 read
Get market data including probabilities.
**When:** Before betting — check current probabilities to find mispriced outcomes. Also for monitoring markets you've created or bet on.
**Why:** Probabilities shift with every trade. An outcome at 20% probability that you believe is 60% likely is a strong buy. Use this to find edges.
| Param | Type | Required | Description |
|-------|------|----------|-------------|
| `market` | string | yes | Market token address |

**SDK:** `client.predictionMarkets.getMarketData(market)` + `client.marketReader.getAllOutcomes(PREDICTION_CONTRACT, market)`
**Returns:** `{ name, end_time, resolved, outcomes: [{ name, probability_pct, price_per_share, total_cost, shares }] }`

---

### `propose_outcome` ⚡ write
Propose the winning outcome for an ended market (costs 5 USDB bond).
**When:** A market has passed its end time and no one has proposed the outcome yet. First proposer who goes uncontested gets their bond back + 100% of the bounty pool.
**Why:** Resolution bounties are free money for honest reporting. If you know the correct outcome and propose first, you earn the full bounty. Use `get_market_list` with status "awaiting_proposal" to find opportunities.
| Param | Type | Required | Description |
|-------|------|----------|-------------|
| `market` | string | yes | Market token address |
| `outcome` | string or number | yes | Winning outcome name or index |

**SDK:** `client.resolver.proposeOutcome(market, outcomeId)`

---

### `dispute_outcome` ⚡ write
Dispute a proposed outcome with an alternative (costs 5 USDB bond).
**When:** Someone proposed the wrong outcome. Disputing costs 5 USDB but if voters agree with you, you win both bonds. Only dispute if you're confident the proposal is incorrect.
**Why:** The dispute system ensures honest resolution. If you see a wrong proposal, disputing protects the market's integrity and earns you the proposer's bond.
| Param | Type | Required | Description |
|-------|------|----------|-------------|
| `market` | string | yes | Market token address |
| `outcome` | string or number | yes | Alternative outcome name or index |

**SDK:** `client.resolver.dispute(market, outcomeId)`

---

### `vote_on_dispute` ⚡ write
Vote during a dispute (requires prior staking via `resolver_stake`).
**When:** A market is in dispute and you know the correct outcome. You must have staked first (use `resolver_stake`). Correct voters share the bounty pool equally.
**Why:** Voting earns bounty rewards and maintains platform integrity. But it locks your staked tokens for 24 hours — don't stake tokens you need liquid access to.
| Param | Type | Required | Description |
|-------|------|----------|-------------|
| `market` | string | yes | Market token address |
| `outcome` | string or number | yes | Outcome to vote for |

**SDK:** `client.resolver.vote(market, outcomeId)`
**Guardrail:** Check `hasVoted()` first. Warn about 24h stake lock.

---

### `finalize_market` ⚡ write
Finalize a market (uncontested or after voting).
**When:** The challenge period has passed (uncontested proposal) or voting has completed with quorum + 70% supermajority. Anyone can call this — it's a public service.
**Why:** Markets must be finalized before winners can redeem. If you proposed the outcome, finalizing releases your bond + bounty.
| Param | Type | Required | Description |
|-------|------|----------|-------------|
| `market` | string | yes | Market token address |

**SDK:** Checks `isInDispute()` → calls `finalizeMarket()` or `finalizeUncontested()` accordingly.

---

### `claim_bounty` ⚡ write
Claim resolver bounty for correct dispute participation.
**When:** After a market you proposed, disputed, or voted on has been finalized and your side won. Must be claimed explicitly.
**Why:** Bounties are your reward for keeping the platform honest. Uncontested proposals earn 100% of the bounty pool. Correct voters split it equally.
| Param | Type | Required | Description |
|-------|------|----------|-------------|
| `market` | string | yes | Market token address |
| `round` | number | no | Round number (only needed for EARLY bounties) |

**SDK:** If `round` provided → `client.resolver.claimEarlyBounty(market, round)`. Otherwise → `client.resolver.claimBounty(market)`.
**Guardrail:** Check `hasClaimed()` first to avoid wasted gas.

---

### `get_my_shares` 📖 read
Check how many shares you hold in a prediction market outcome.
**When:** To monitor your prediction market positions — see what you hold, current probabilities, and whether you should buy more or sell via the order book.
**Why:** You need to know your exposure before deciding to add, hold, or exit. Also useful after resolution to check if you have shares to redeem.
| Param | Type | Required | Description |
|-------|------|----------|-------------|
| `market` | string | yes | Market token address |
| `outcome` | string or number | no | Specific outcome (omit for all outcomes) |

**SDK:** If outcome specified → `client.predictionMarkets.getUserShares(market, wallet, outcomeId)`. Otherwise → loop all outcomes via `getNumOutcomes()` then `getUserShares()` for each.
**Returns:** `{ market, outcomes: [{ name, outcome_id, shares, current_probability }] }`

---

### `resolver_stake` ⚡ write
Stake tokens to become eligible for dispute voting.
**When:** Before you want to vote on any dispute. Staking is a prerequisite — you can't vote without it. Unstake when you're done resolving markets and want your tokens back.
**Why:** Staking is an anti-spam measure (minimum 5 tokens). It ensures voters have skin in the game. Warning: tokens are locked for 24h after voting — plan your capital accordingly.
| Param | Type | Required | Description |
|-------|------|----------|-------------|
| `action` | string | yes | `"stake"` or `"unstake"` |

**SDK:** `client.resolver.stake(MAINTOKEN)` or `client.resolver.unstake(MAINTOKEN)`. Auto-reads MIN_STAKE_AMOUNT.
**Guardrail:** On stake: warn that tokens are locked for 24h after voting. On unstake: check `VOTE_LOCK_DURATION` hasn't elapsed since last vote.

---

### `get_market_resolution_status` 📖 read
Check the resolution state of an ended market.
**When:** To see where a market is in the resolution pipeline — has it been proposed? Disputed? Is voting active? Can it be finalized? Essential before calling propose, dispute, vote, or finalize.
**Why:** Each resolution action is only valid at specific stages. This tells you exactly what actions are available right now.
| Param | Type | Required | Description |
|-------|------|----------|-------------|
| `market` | string | yes | Market token address |

**SDK:** `client.resolver.getDisputeData(market)` + `client.resolver.isResolved(market)` + `client.resolver.isInDispute(market)` + `client.resolver.isInVeto(market)`
**Returns:** `{ resolved, in_dispute, in_veto, current_round, proposed_outcome, bounty_pool, your_vote, has_claimed }`

---

## Module 4: Staking & Vault (6 tools)

### `stake_stasis` ⚡ write
Buy STASIS and/or wrap into vault for yield. Handles the full flow or any subset.
**When:** You have idle USDB or STASIS and want it earning yield. The vault is the safest passive income on Basis — platform fees flow in automatically. Lock if you plan to borrow against it later.
**Why:** Idle capital earns nothing. The vault converts idle STASIS into yield-bearing wSTASIS that appreciates as the platform generates fees. Locking wSTASIS unlocks the ability to borrow USDB against it while still earning yield — your capital works in two places at once.
| Param | Type | Required | Description |
|-------|------|----------|-------------|
| `amount_usdb` | number | no | Buy this much STASIS with USDB first (skip if you already hold STASIS) |
| `amount_stasis` | number | no | Wrap this much STASIS into wSTASIS (skip if you already hold wSTASIS) |
| `lock` | boolean | no | Also lock as collateral (default: false) |
| `lock_existing_wstasis` | number | no | Lock this amount of already-held wSTASIS (skip buy/wrap steps entirely) |

**SDK:** If `amount_usdb` → `client.trading.buy(MAINTOKEN, amount)`. If `amount_stasis` → `client.staking.buy(stasisAmount)`. If `lock` → `client.staking.lock(shares)`. If `lock_existing_wstasis` → `client.staking.lock(shares)` directly.
**Returns:** `{ wstasis_shares, stasis_value, locked }`

---

### `unstake_stasis` ⚡ write
Unwrap and/or sell staked STASIS.
**When:** You need to exit the vault — either to redeploy capital elsewhere or to sell STASIS entirely. Must repay any active vault loan before unlocking.
**Why:** Your wSTASIS has appreciated from vault yield. Unwrapping gives you back more STASIS than you deposited. Selling all the way to USDB exits the position completely.
| Param | Type | Required | Description |
|-------|------|----------|-------------|
| `unlock` | boolean | no | Unlock from collateral first (default: false) |
| `sell_to_usdb` | boolean | no | Sell all the way to USDB (default: false) |
| `shares` | number | no | wSTASIS shares to unwrap (default: all) |

**SDK:** If `unlock` → `client.staking.unlock(shares)`. Then `client.staking.sell(shares, sellToUsdb)`.

---

### `vault_borrow` ⚡ write
Borrow USDB against locked wSTASIS.
**When:** You need liquid USDB but don't want to sell your STASIS position. Borrow against it instead — keep earning vault yield while deploying the borrowed capital elsewhere.
**Why:** This is the capital efficiency play. 2% flat origination fee + 0.005%/day interest is cheap compared to selling and re-buying STASIS (which costs ~1% round-trip in swap fees plus you lose vault yield during the gap). Best used when you have a short-term opportunity that will return more than the loan cost.
| Param | Type | Required | Description |
|-------|------|----------|-------------|
| `amount_stasis` | number | yes | STASIS-equivalent amount to borrow against |
| `days` | number | yes | Loan duration |

**SDK:** `client.staking.borrow(parseUnits(amount, 18), days)`
**Guardrail:** Check `getAvailableStasis()` first. Show fee breakdown (2% origination + 0.005%/day).
**Returns:** `{ usdb_received, fee_paid, expiry_date }`

---

### `vault_repay` ⚡ write
Repay vault loan.
**When:** You're done with the borrowed capital and want to free your locked collateral. Also when loan expiry is approaching — repaying early doesn't save money (interest is prepaid) but avoids auto-liquidation.
**Why:** Repaying clears the debt so you can unlock your wSTASIS. Note: you already paid for all the days upfront, so there's no discount for early repayment — but it does free your collateral for other uses.
| Param | Type | Required | Description |
|-------|------|----------|-------------|
| (none) | | | Repays full outstanding loan |

**SDK:** `client.staking.repay()`

---

### `get_vault_status` 📖 read
Get your complete vault position.
**When:** To check your staking position — how much is staked, locked, available to borrow, and whether you have an active loan. Run before borrowing to see your capacity.
**Why:** You need to know your available collateral before borrowing, and your lock status before trying to unstake.
| Param | Type | Required | Description |
|-------|------|----------|-------------|
| (none) | | | Uses configured wallet |

**SDK:** `client.staking.getUserStakeDetails(wallet)` + `client.staking.getAvailableStasis(wallet)` + `client.staking.convertToAssets(totalShares)`
**Returns:** `{ liquid_shares, locked_shares, total_stasis_value, available_to_borrow, has_active_loan }`

---

### `extend_loan` ⚡ write
Extend any active loan (vault or hub).
**When:** Your loan is approaching expiry and you want to keep the position open. ALWAYS extend rather than repaying and re-originating — extending costs 0.005%/day vs 2% flat for a new loan.
**Why:** Extension is ~400x cheaper per day than a new loan. With `refinance=true`, you can also extract additional capital if your collateral has appreciated since origination.
| Param | Type | Required | Description |
|-------|------|----------|-------------|
| `loan_type` | string | yes | `"vault"` or `"hub"` |
| `hub_id` | number | no | Required if loan_type is "hub" |
| `days` | number | yes | Days to add |
| `refinance` | boolean | no | Refinance at current rates (default: false) |

**SDK:** `client.staking.extendLoan(days, true, refinance)` or `client.loans.extendLoan(hubId, days, true, refinance)`

---

## Module 5: Loans (6 tools)

### `take_loan` ⚡ write
Take a loan against any token.
**When:** You hold a token you don't want to sell but need liquid USDB. Works with any Basis token as collateral. For STASIS specifically, prefer `vault_borrow` instead (earns yield while borrowed against).
**Why:** Loans let you keep exposure to appreciating assets while accessing capital. No price liquidation risk — loans are valued at floor price. The only risk is time-based expiry. Take minimum duration (10 days) and extend as needed.
| Param | Type | Required | Description |
|-------|------|----------|-------------|
| `collateral_token` | string | yes | Token name or address to use as collateral |
| `amount` | number | yes | Collateral amount |
| `days` | number | yes | Loan duration (min 10) |

**SDK:** `client.loans.takeLoan(MAINTOKEN, collateralToken, parseUnits(amount, 18), days)`
**Guardrail:** Show fee breakdown. Warn about early repay not saving money.
**Returns:** `{ hub_id, usdb_received, fee_paid, expiry_date, collateral_locked }`

---

### `repay_loan` ⚡ write
Repay a hub loan.
**When:** You're done with the borrowed capital or want to free your collateral for other uses. No benefit to early repayment — interest is prepaid.
**Why:** Repaying returns your locked collateral tokens. If you don't repay before expiry, collateral is auto-burned to cover debt (any excess is claimable via `claim_liquidation`).
| Param | Type | Required | Description |
|-------|------|----------|-------------|
| `hub_id` | number | yes | Loan hub ID |

**SDK:** `client.loans.repayLoan(hubId)`

---

### `get_loans` 📖 read
List all active loans.
**When:** To monitor your loan positions — check expiry dates, collateral values, and decide whether to repay, extend, or let them run. Run periodically if you have active loans.
**Why:** Loans expire silently. If you miss an expiry, your collateral gets auto-liquidated. Regular monitoring prevents surprises.
| Param | Type | Required | Description |
|-------|------|----------|-------------|
| `active_only` | boolean | no | Only show active loans (default: true) |

**SDK:** `client.api.getLoans({ active: true })` or iterate via `getUserLoanCount()` + `getUserLoanDetails()`
**Returns:** Array of loan objects with: hub_id, token, collateral, borrowed, expiry, active, source

---

### `increase_loan_collateral` ⚡ write
Add more collateral to an existing loan.
**When:** You want to increase your borrowing capacity on an existing loan without originating a new one (which would cost another 2% fee).
**Why:** Adding collateral increases the loan's backing and may allow you to borrow more via refinancing. Much cheaper than opening a new loan.
| Param | Type | Required | Description |
|-------|------|----------|-------------|
| `loan_type` | string | yes | `"hub"` or `"vault"` |
| `hub_id` | number | no | Required if loan_type is "hub" |
| `amount` | number | yes | Additional collateral amount |

**SDK:** If hub → `client.loans.increaseLoan(hubId, parseUnits(amount, 18))`. If vault → `client.staking.addToLoan(parseUnits(amount, 18))`.

---

### `claim_liquidation` ⚡ write
Claim remaining collateral from an expired/liquidated loan.
**When:** A loan expired without repayment. The protocol burned enough collateral to cover the debt — any remaining value above the debt is yours to claim. It does NOT return automatically.
**Why:** If your collateral appreciated significantly, there could be substantial value left after the debt is covered. Don't forget to claim it.
| Param | Type | Required | Description |
|-------|------|----------|-------------|
| `loan_type` | string | yes | `"hub"` or `"vault"` |
| `hub_id` | number | no | Required if loan_type is "hub" |

**SDK:** If hub → `client.loans.claimLiquidation(hubId)`. If vault → `client.staking.settleLiquidation()`.
**Guardrail:** Check loan is actually liquidated before calling.

---

### `partial_loan_sell` ⚡ write
Partially sell collateral from a regular (non-leverage) hub loan.
**When:** You want to take partial profit from a hub loan position without fully closing. Sell 10-100% of collateral (in 10% increments). Proceeds go toward debt repayment.
**Why:** Allows gradual exit from a loan position. Useful when collateral has appreciated and you want to de-risk without fully closing.
| Param | Type | Required | Description |
|-------|------|----------|-------------|
| `hub_id` | number | yes | Hub loan ID |
| `percentage` | number | yes | 10-100, must be divisible by 10 |

**SDK:** `client.loans.hubPartialLoanSell(hubId, percentage, false, 0)`
**Guardrail:** Validate percentage is multiple of 10.

---

## Module 6: Portfolio & Data (6 tools)

### `get_balances` 📖 read
Get token balances for the wallet.
**When:** To see your full portfolio at a glance — USDB available, STASIS held, vault position, and any factory tokens. Essential starting point for deciding what to do next.
**Why:** You need to know what you have before you can deploy it. Shows idle capital (USDB) that could be earning yield, and token positions that could be used as loan collateral.
| Param | Type | Required | Description |
|-------|------|----------|-------------|
| (none) | | | Uses configured wallet |

**SDK:** Read USDB balance, STASIS balance, wSTASIS balance via standard ERC20 `balanceOf()`. Plus `client.api.getWalletTransactions()` to identify held factory tokens.
**Returns:** `{ usdb, stasis, wstasis, wstasis_value_stasis, tokens: [{ address, symbol, balance, usd_value }] }`

---

### `get_market_list` 📖 read
List available prediction markets.
**When:** To discover betting opportunities, find markets to resolve (earn bounties), or research before creating a new market. Filter by status to find actionable markets.
**Why:** Different statuses mean different opportunities: "active" = bet on them, "awaiting_proposal" = earn bounty by proposing outcome, "resolved" = check if you have winnings to redeem.
| Param | Type | Required | Description |
|-------|------|----------|-------------|
| `status` | string | no | Filter: `"active"`, `"awaiting_proposal"`, `"resolved"` |
| `limit` | number | no | Max results (default: 20) |

**SDK:** `client.api.getTokens({ isPrediction: true, limit })`
**Returns:** Array of market summaries with: address, name, symbol, status, end_time

---

### `get_token_list` 📖 read
List available tokens.
**When:** To discover trading opportunities, research tokens before buying, or find tokens to analyze for trends.
**Why:** The token ecosystem is constantly growing. New tokens mean new dev fee opportunities, new trading opportunities, and new collateral options.
| Param | Type | Required | Description |
|-------|------|----------|-------------|
| `search` | string | no | Filter by name/symbol |
| `limit` | number | no | Max results (default: 20) |

**SDK:** `client.api.getTokens({ search, limit })`
**Returns:** Array of token summaries with: address, name, symbol, type, price

---

### `get_price_history` 📖 read
Get OHLC price candles for a token.
**When:** Before entering a position — analyze price trends, identify momentum, spot entry points. Also useful for monitoring held positions over time.
**Why:** Price history reveals patterns. On Stable+ tokens, steady uptrend = healthy volume. On Floor+ tokens, dips below moving average may be buying opportunities (floor provides downside protection).
| Param | Type | Required | Description |
|-------|------|----------|-------------|
| `token` | string | yes | Token name or address |
| `interval` | string | no | `"1m"`, `"5m"`, `"15m"`, `"1h"` (default), `"4h"`, `"1d"` |
| `limit` | number | no | Max candles (default: 100, max: 1000) |

**SDK:** `client.api.getCandles(tokenAddress, { interval, limit })`
**Returns:** `{ token, interval, candles: [{ time, open, high, low, close }] }`

---

### `get_trade_history` 📖 read
Get recent trades for a token.
**When:** To see real trading activity — who's buying/selling, trade sizes, and momentum. Useful for gauging market interest before entering or for monitoring your own token's activity.
**Why:** Volume and trade flow tell you more than price alone. Consistent buy volume on a token you created means growing dev fee income.
| Param | Type | Required | Description |
|-------|------|----------|-------------|
| `token` | string | yes | Token name or address |
| `type` | string | no | Filter: `"buy"`, `"sell"`, `"leverage_buy"`, `"leverage_sell"` |
| `limit` | number | no | Max results (default: 20) |

**SDK:** `client.api.getTrades(tokenAddress, { type, limit })`
**Returns:** Array of trades with: type, amount_token, amount_usdb, user, price, timestamp

---

### `remove_whitelist` ⚡ write
Remove a wallet from a frozen token's whitelist.
**When:** A wallet was whitelisted in error, or you want to revoke access before unfreezing the token.
**Why:** Whitelist management is part of controlled token launches. Remove wallets that shouldn't have early access.
| Param | Type | Required | Description |
|-------|------|----------|-------------|
| `token` | string | yes | Token address |
| `wallet` | string | yes | Wallet to remove |

**SDK:** `client.factory.removeWhitelist(tokenAddress, wallet)`

---

## Module 7: Agent Identity (1 tool)

### `register_agent` ⚡ write
Register as an AI agent on-chain (ERC-8004).
**When:** AFTER you've built real capabilities on the platform (traded, created tokens, resolved markets). Don't register empty — your registration is publicly visible across the entire ERC-8004 ecosystem and acts as a portfolio of what you can do.
**Why:** On-chain identity enables the Agent Confidence Score (ACS), leaderboard visibility, airdrop bonus, and discoverability by other agents and platforms. Every registered Basis agent is organic marketing for the platform.
| Param | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | no | Agent display name |
| `description` | string | no | Agent description |
| `capabilities` | string[] | no | e.g., ["trade", "create", "resolve"] |

**SDK:** `client.agent.registerAndSync({ name, description, capabilities })`

---

## Address Resolution Map

The MCP server should maintain this map so agents can use names instead of addresses:

| Name | Address | Notes |
|------|---------|-------|
| `USDB` | `0x217B82e4bAc4E4647B1F189F33554229Ce27c51A` | Test stablecoin |
| `STASIS` / `MAINTOKEN` | `0xE4b154A81E8E0Cd4CD6aE5F76a28e80C5a2d9E74` | Main ecosystem token |
| `PREDICTION` / `MarketTrading` | `0x69e4b11346f928f29Affe6B52a8e3Ebd115DE7a6` | Market trading contract |

Factory tokens and market tokens are resolved via `client.api.getTokens({ search: name })`.

---

## Implementation Notes for Alex

1. **Language:** TypeScript (Node.js) recommended — Basis JS SDK is more mature than Python.
2. **MCP framework:** Use the official `@modelcontextprotocol/sdk` package.
3. **Amount handling:** All MCP params are human-readable numbers. Convert internally: `parseUnits(amount.toString(), 18)`.
4. **Error handling:** Catch SDK errors, return structured `{ error: true, message: "...", revert_reason: "..." }`.
5. **Address resolution:** Build a token cache from `getTokens()` on startup. Refresh periodically. Fall through to raw address if not found.
6. **Guardrails:** Every write tool should preview first (getAmountsOut, simulate, check balance). Return the preview in the response even on success.
7. **Auth:** `BasisClient.create({ privateKey: process.env.BASIS_PRIVATE_KEY })` at server startup. Single wallet per server instance.
8. **Rate limits:** API key = 60 req/min. Batch reads where possible. Cache token lists.

---

## What's NOT included (intentional — v2 candidates)

These SDK methods are excluded because they're too low-level, rarely needed, or better handled internally:

- **Raw swap methods** (`buyTokens`, `sellTokens`) — `buy_token`/`sell_token` handle path routing automatically
- **Vesting module** — Complex multi-step flows (create/claim/batch). Add if team distribution agents emerge.
- **Private markets** — Niche use case with separate resolution system. Add later.
- **Surge tax management** — Creator-only, rare. Add later.
- **Order book methods** — Complex P2P limit orders for prediction shares. Add for advanced market-making agents.
- **Low-level simulator methods** (`calculateFloor`, `getCollateralValue`, etc.) — Internal to leverage simulation.
- **API key management** — Handled at server setup, not runtime.
- **convertToNative** — Niche routing through market token AMM.
- **Veto mechanism** — Rare escalation path. Add if governance agents emerge.

These can all be added as v2 tools if there's demand.
