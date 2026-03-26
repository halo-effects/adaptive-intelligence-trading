# Basis MCP Server — Tool Specification

_For Alex / AI coding agent. Maps Basis SDK methods to MCP tools._
_Generated from COMPLETE_V2.md (v1.0.1) on 2026-03-26._

---

## Overview

33 tools across 7 modules. Each tool wraps one or more SDK methods, handles address resolution (names → addresses), amount conversion (human numbers → 18-decimal raw), and returns clean JSON.

**Conventions:**
- All amounts are in **human-readable units** (e.g., `50` = 50 USDB). The MCP server converts to raw 18-decimal internally.
- Token names like `"STASIS"` are resolved to addresses internally. Agents can also pass raw addresses.
- All write tools return `{ hash, receipt, ...extra }`. All read tools return the data directly.
- The server needs a private key configured at startup (env var `BASIS_PRIVATE_KEY`).

---

## Module 1: Trading (7 tools)

### `buy_token` ⚡ write
Buy a token using USDB.
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
| Param | Type | Required | Description |
|-------|------|----------|-------------|
| `token` | string | yes | Token name or address |

**SDK:** `client.trading.getUSDPrice(tokenAddress)`
**Returns:** `{ token, price_usd, token_address }`

---

### `preview_trade` 📖 read
Preview a buy or sell without executing.
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
| Param | Type | Required | Description |
|-------|------|----------|-------------|
| `position_id` | number | yes | Leverage position ID |
| `percentage` | number | no | 10-100, must be divisible by 10 (default: 100 = full close) |

**SDK:** `client.trading.partialLoanSell(positionId, percentage, true, 0)`
**Guardrail:** Validate percentage is multiple of 10.

---

### `get_leverage_positions` 📖 read
List all leverage positions for the wallet.
| Param | Type | Required | Description |
|-------|------|----------|-------------|
| (none) | | | Uses configured wallet |

**SDK:** `client.trading.getLeverageCount(wallet)` → loop `client.trading.getLeveragePosition(wallet, id)` for each
**Returns:** Array of position objects with: id, token, collateral, borrowed, active, expiry

---

## Module 2: Token Creation (5 tools)

### `create_token` ⚡ write
Create a new token with metadata.
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
| Param | Type | Required | Description |
|-------|------|----------|-------------|
| `token` | string | yes | Token address |

**SDK:** `client.factory.disableFreeze(tokenAddress)`

---

### `whitelist_wallets` ⚡ write
Add wallets to a frozen token's whitelist.
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
| Param | Type | Required | Description |
|-------|------|----------|-------------|
| `token` | string | yes | Token name or address |

**SDK:** `client.factory.getTokenState(tokenAddress)`
**Returns:** `{ frozen, has_bonded, total_supply, usd_price }`

---

### `claim_rewards` ⚡ write
Claim accumulated rewards from the reward phase.
| Param | Type | Required | Description |
|-------|------|----------|-------------|
| `token` | string | yes | Token address |

**SDK:** `client.factory.claimRewards(tokenAddress)`

---

## Module 3: Prediction Markets (8 tools)

### `create_market` ⚡ write
Create a prediction market with metadata.
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
| Param | Type | Required | Description |
|-------|------|----------|-------------|
| `market` | string | yes | Market token address |

**SDK:** `client.predictionMarkets.redeem(market)`

---

### `get_market_info` 📖 read
Get market data including probabilities.
| Param | Type | Required | Description |
|-------|------|----------|-------------|
| `market` | string | yes | Market token address |

**SDK:** `client.predictionMarkets.getMarketData(market)` + `client.marketReader.getAllOutcomes(PREDICTION_CONTRACT, market)`
**Returns:** `{ name, end_time, resolved, outcomes: [{ name, probability_pct, price_per_share, total_cost, shares }] }`

---

### `propose_outcome` ⚡ write
Propose the winning outcome for an ended market (costs 5 USDB bond).
| Param | Type | Required | Description |
|-------|------|----------|-------------|
| `market` | string | yes | Market token address |
| `outcome` | string or number | yes | Winning outcome name or index |

**SDK:** `client.resolver.proposeOutcome(market, outcomeId)`

---

### `dispute_outcome` ⚡ write
Dispute a proposed outcome with an alternative (costs 5 USDB bond).
| Param | Type | Required | Description |
|-------|------|----------|-------------|
| `market` | string | yes | Market token address |
| `outcome` | string or number | yes | Alternative outcome name or index |

**SDK:** `client.resolver.dispute(market, outcomeId)`

---

### `vote_on_dispute` ⚡ write
Vote during a dispute (requires prior staking).
| Param | Type | Required | Description |
|-------|------|----------|-------------|
| `market` | string | yes | Market token address |
| `outcome` | string or number | yes | Outcome to vote for |

**SDK:** `client.resolver.vote(market, outcomeId)`
**Guardrail:** Check `hasVoted()` first. Warn about 24h stake lock.

---

### `finalize_market` ⚡ write
Finalize a market (uncontested or after voting).
| Param | Type | Required | Description |
|-------|------|----------|-------------|
| `market` | string | yes | Market token address |

**SDK:** Checks `isInDispute()` → calls `finalizeMarket()` or `finalizeUncontested()` accordingly.

---

## Module 4: Staking & Vault (6 tools)

### `stake_stasis` ⚡ write
Buy STASIS and/or wrap into vault for yield.
| Param | Type | Required | Description |
|-------|------|----------|-------------|
| `amount_usdb` | number | no | Buy this much STASIS with USDB first (skip if you already hold STASIS) |
| `amount_stasis` | number | no | Wrap this much STASIS into wSTASIS |
| `lock` | boolean | no | Also lock as collateral (default: false) |

**SDK:** If `amount_usdb` → `client.trading.buy(MAINTOKEN, amount)`. Then `client.staking.buy(stasisAmount)`. If `lock` → `client.staking.lock(shares)`.
**Returns:** `{ wstasis_shares, stasis_value, locked }`

---

### `unstake_stasis` ⚡ write
Unwrap and/or sell staked STASIS.
| Param | Type | Required | Description |
|-------|------|----------|-------------|
| `unlock` | boolean | no | Unlock from collateral first (default: false) |
| `sell_to_usdb` | boolean | no | Sell all the way to USDB (default: false) |
| `shares` | number | no | wSTASIS shares to unwrap (default: all) |

**SDK:** If `unlock` → `client.staking.unlock(shares)`. Then `client.staking.sell(shares, sellToUsdb)`.

---

### `vault_borrow` ⚡ write
Borrow USDB against locked wSTASIS.
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
| Param | Type | Required | Description |
|-------|------|----------|-------------|
| (none) | | | Repays full outstanding loan |

**SDK:** `client.staking.repay()`

---

### `get_vault_status` 📖 read
Get your complete vault position.
| Param | Type | Required | Description |
|-------|------|----------|-------------|
| (none) | | | Uses configured wallet |

**SDK:** `client.staking.getUserStakeDetails(wallet)` + `client.staking.getAvailableStasis(wallet)` + `client.staking.convertToAssets(totalShares)`
**Returns:** `{ liquid_shares, locked_shares, total_stasis_value, available_to_borrow, has_active_loan }`

---

### `extend_loan` ⚡ write
Extend any active loan (vault or hub).
| Param | Type | Required | Description |
|-------|------|----------|-------------|
| `loan_type` | string | yes | `"vault"` or `"hub"` |
| `hub_id` | number | no | Required if loan_type is "hub" |
| `days` | number | yes | Days to add |
| `refinance` | boolean | no | Refinance at current rates (default: false) |

**SDK:** `client.staking.extendLoan(days, true, refinance)` or `client.loans.extendLoan(hubId, days, true, refinance)`

---

## Module 5: Loans (3 tools)

### `take_loan` ⚡ write
Take a loan against any token.
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
| Param | Type | Required | Description |
|-------|------|----------|-------------|
| `hub_id` | number | yes | Loan hub ID |

**SDK:** `client.loans.repayLoan(hubId)`

---

### `get_loans` 📖 read
List all active loans.
| Param | Type | Required | Description |
|-------|------|----------|-------------|
| `active_only` | boolean | no | Only show active loans (default: true) |

**SDK:** `client.api.getLoans({ active: true })` or iterate via `getUserLoanCount()` + `getUserLoanDetails()`
**Returns:** Array of loan objects with: hub_id, token, collateral, borrowed, expiry, active, source

---

## Module 6: Portfolio & Data (3 tools)

### `get_balances` 📖 read
Get token balances for the wallet.
| Param | Type | Required | Description |
|-------|------|----------|-------------|
| (none) | | | Uses configured wallet |

**SDK:** Read USDB balance, STASIS balance, wSTASIS balance via standard ERC20 `balanceOf()`. Plus `client.api.getWalletTransactions()` to identify held factory tokens.
**Returns:** `{ usdb, stasis, wstasis, wstasis_value_stasis, tokens: [{ address, symbol, balance, usd_value }] }`

---

### `get_market_list` 📖 read
List available prediction markets.
| Param | Type | Required | Description |
|-------|------|----------|-------------|
| `status` | string | no | Filter: `"active"`, `"awaiting_proposal"`, `"resolved"` |
| `limit` | number | no | Max results (default: 20) |

**SDK:** `client.api.getTokens({ isPrediction: true, limit })`
**Returns:** Array of market summaries with: address, name, symbol, status, end_time

---

### `get_token_list` 📖 read
List available tokens.
| Param | Type | Required | Description |
|-------|------|----------|-------------|
| `search` | string | no | Filter by name/symbol |
| `limit` | number | no | Max results (default: 20) |

**SDK:** `client.api.getTokens({ search, limit })`
**Returns:** Array of token summaries with: address, name, symbol, type, price

---

## Module 7: Agent Identity (1 tool)

### `register_agent` ⚡ write
Register as an AI agent on-chain (ERC-8004).
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

## What's NOT included (intentional)

These SDK methods are excluded from the MCP spec because they're either too low-level, rarely needed, or better handled internally:

- **Raw swap methods** (`buyTokens`, `sellTokens`) — `buy_token`/`sell_token` handle path routing
- **Vesting module** — Complex, rarely needed by autonomous agents. Add later if demand.
- **Private markets** — Niche use case. Add later.
- **Surge tax management** — Creator-only, rare. Add later.
- **Order book methods** — Complex P2P trading. Add later for advanced agents.
- **Low-level simulator methods** — Internal to leverage simulation.
- **Resolver staking** (`stake`/`unstake`) — Can be added if resolver agents are common.
- **API key management** — Handled at server setup, not runtime.

These can all be added as v2 tools if there's demand. Start lean.
