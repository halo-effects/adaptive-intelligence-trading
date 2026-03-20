# Basis Skills vs SDK — Gap Analysis
_Cross-reference: every SDK function mapped to skill coverage + agent reasoning_
_Generated 2026-03-20_

## Executive Summary

**Current skills cover ~40% of SDK functions.** The scripts handle core happy paths well (buy, sell, bet, lend, vault, create), but large areas have zero skill coverage. More importantly, **no skill explains _why_ an agent would choose one action over another** — the decision trees describe strategies at a high level, but don't connect to specific SDK functions with reasoning an agent can follow.

Diamond's instinct is right: agents need a **"what is this, why would I use it, what do I gain"** layer. The SDK docs tell you _how_. The skills need to tell you _when_ and _why_.

---

## Coverage Matrix: SDK Functions → Skill Scripts

### ✅ = In a skill script | 🟡 = Mentioned but not implemented | ❌ = Not covered at all

---

### 5.1 Trading (client.trading)

| Function | Skill | Coverage | Agent Reasoning (MISSING) |
|----------|-------|----------|---------------------------|
| `buy()` | trade.py | ✅ | — |
| `sell()` | trade.py | ✅ | — |
| `sellPercentage()` | trade.py | ✅ | — |
| `buyTokens()` (raw) | — | ❌ | "Use when you need a custom swap path — e.g., buying a factory token directly with MAINTOKEN instead of USDB, or routing through a specific pool for better price" |
| `sellTokens()` (raw) | — | ❌ | "Use when selling to an intermediate token, not USDB — e.g., selling factory token to MAINTOKEN to stake, skipping the MAINTOKEN→USDB hop" |
| `convertToNative()` | — | ❌ | "Convert any token back to USDB through a market's AMM. Useful after winning a prediction market — convert market tokens directly to USDB instead of selling through DEX" |
| `leverageBuy()` | trade.py | ✅ | — |
| `partialLoanSell()` | — | ❌ | "Close part of a leverage position without closing the whole thing. Take profits while keeping upside exposure" |
| `getAmountsOut()` | trade.py | ✅ | — |
| `getTokenPrice()` | — | ❌ (read) | "MAINTOKEN-denominated price — use for relative value between factory tokens" |
| `getUSDPrice()` | trade.py, portfolio.py | ✅ | — |
| `getLeverageCount()` | portfolio.py | ✅ | — |
| `getLeveragePosition()` | portfolio.py | ✅ | — |

**Gap**: No skill for partial leverage exits, raw path swaps, or convertToNative. These are power moves for capital efficiency.

---

### 5.2 Factory (client.factory)

| Function | Skill | Coverage | Agent Reasoning (MISSING) |
|----------|-------|----------|---------------------------|
| `createTokenWithMetadata()` | create-token.py | 🟡 Uses old `create_token()` | "One-call token launch with image + IPFS metadata. Always use this over raw createToken — ensures your token shows up on the platform UI" |
| `disableFreeze()` | create-token.py | 🟡 Mentioned in output | "Open your token to public trading after private whitelist phase. Use for controlled launches — whitelist early supporters first, then open to everyone" |
| `setWhitelistedWallet()` | create-token.py | 🟡 Mentioned in output | "Give specific wallets permission to buy before public launch. Strategic use: reward community members, create exclusivity, prevent bots from front-running launch" |
| `removeWhitelist()` | — | ❌ | "Revoke a wallet's whitelist access. Use when: someone sold their allocation, or you're done with the private phase" |
| `getTokenState()` | — | ❌ (read) | "Check if token is frozen, bonded, total supply, price. Essential before buying — a frozen token blocks non-whitelisted buys" |
| `isEcosystemToken()` | — | ❌ (read) | "Verify a token is legitimate Basis ecosystem token vs random BSC contract" |
| `getTokensByCreator()` | — | ❌ (read) | "Find all tokens a wallet created. Use to audit a creator's portfolio or track your own launches" |
| `getFeeAmount()` | create-token.py | ✅ | — |
| `claimRewards()` | — | ❌ **NEW** | "Claim USDB rewards from bonding-phase tax redistribution. If you bought during bonding, you earn ongoing USDB from every trade on that token. Check with getClaimableRewards first — claim when accumulated rewards justify gas" |
| `getClaimableRewards()` | — | ❌ **NEW** | "Check how much USDB you've earned from bonding-phase shares. This is passive income — check periodically and claim when it's worth the gas" |

**Gap**: create-token.py uses the old `create_token()` + separate metadata calls. Needs update to `createTokenWithMetadata()`. Frozen token flow (whitelist → open) is only hinted at in output text, not a real workflow. **Bonding rewards (claimRewards) is entirely missing — this is free money agents are leaving on the table.**

---

### 5.3 Loans (client.loans)

| Function | Skill | Coverage | Agent Reasoning (MISSING) |
|----------|-------|----------|---------------------------|
| `takeLoan()` | lend.py | ✅ | — |
| `repayLoan()` | lend.py | ✅ | — |
| `extendLoan()` | lend.py | ✅ | — |
| `increaseLoan()` | lend.py | ✅ | — |
| `claimLiquidation()` | — | ❌ | "If your loan expired and was liquidated, you can still recover any leftover value. Better to lose some than lose all — always claim after liquidation" |
| `hubPartialLoanSell()` | — | ❌ **NEW** | "Partially close a hub loan by selling some collateral. Use when: token price dropped and you want to de-risk, or you need some USDB but don't want to close the whole position. Different from partialLoanSell (which is for leveraged positions only)" |
| `getUserLoanDetails()` | lend.py, portfolio.py | ✅ | — |
| `getUserLoanCount()` | lend.py, portfolio.py | ✅ | — |

**Gap**: No skill covers partial loan closing or liquidation recovery. hubPartialLoanSell is critical — it's the only way to partially exit a collateral loan.

---

### 5.4 Staking (client.staking)

| Function | Skill | Coverage | Agent Reasoning (MISSING) |
|----------|-------|----------|---------------------------|
| `buy()` (wrap) | vault.py | ✅ | — |
| `sell()` (unwrap) | vault.py | ✅ | — |
| `lock()` | vault.py | ✅ | — |
| `unlock()` | vault.py | ✅ | — |
| `borrow()` | vault.py | ✅ | — |
| `repay()` | vault.py | ✅ | — |
| `addToLoan()` | — | ❌ | "Add more collateral to your existing staking loan. Use when: wSTASIS appreciated and you want to borrow more against the same lock, or when your LTV is getting tight" |
| `extendLoan()` | vault.py | ✅ | — |
| `settleLiquidation()` | — | ❌ | "Settle a liquidated vault position. Recovers remaining value — always do this" |
| `getAvailableStasis()` | vault.py, portfolio.py | ✅ | — |
| `convertToShares()` | vault.py | ✅ | — |
| `convertToAssets()` | vault.py | ✅ | — |

**Gap**: vault.py is the most complete skill. Only missing `addToLoan()` and `settleLiquidation()` — both worth adding.

---

### 5.5 Vesting (client.vesting)

| Function | Skill | Coverage | Agent Reasoning (MISSING) |
|----------|-------|----------|---------------------------|
| `createGradualVesting()` | — | ❌ | "Lock tokens with time-release schedule for a beneficiary. Use for: team token distribution, investor lockups, advisor compensation. Gradual = tokens unlock linearly over time" |
| `createCliffVesting()` | — | ❌ | "Lock tokens until a single unlock date. Use for: milestone-based releases, delayed rewards. All tokens unlock at once" |
| `batchCreateGradualVesting()` | — | ❌ | "Vest tokens to multiple recipients in one tx. Use for: airdrop distribution, team vesting, community rewards at scale" |
| `batchCreateCliffVesting()` | — | ❌ | Same |
| `claimTokens()` | — | ❌ | "Claim your unlocked vested tokens. Check getClaimableAmount first" |
| `takeLoanOnVesting()` | — | ❌ | "Borrow against tokens that are still locked in vesting. This is powerful — your tokens are locked but you can still use their value as collateral for USDB loans" |
| `repayLoanOnVesting()` | — | ❌ | — |
| `changeBeneficiary()` | — | ❌ | "Transfer vesting rights to another wallet. Use for: organizational changes, selling vested positions" |
| `extendVestingPeriod()` | — | ❌ | "Extend the lockup. Use when: project needs longer commitment period" |
| `addTokensToVesting()` | — | ❌ | "Top up a vesting schedule. Use for: additional compensation, bonus allocations" |
| `transferCreatorRole()` | — | ❌ | "Transfer management of a vesting schedule to another wallet" |
| All read methods | — | ❌ | — |

**Gap: ENTIRE MODULE MISSING.** No vesting skill exists. This is significant — vesting is how tokens get distributed to teams, communities, and partners. Agents creating tokens should be setting up vesting schedules. **Loan-on-vesting is a unique DeFi primitive** — locked tokens still generate borrowing power.

---

### 5.6 Prediction Markets (client.predictionMarkets)

| Function | Skill | Coverage | Agent Reasoning (MISSING) |
|----------|-------|----------|---------------------------|
| `createMarketWithMetadata()` | create-prediction.py | 🟡 Uses old `create_market()` | "One-call market creation with image + IPFS. Always use this" |
| `buy()` | bet.py | ✅ | — |
| `redeem()` | — | ❌ | "Claim your winnings after a market resolves. If you bet on the winning outcome, redeem converts your shares into USDB. **You must manually redeem — it's not automatic**" |
| `buyOrdersAndContract()` | bet.py | ✅ | — |
| `getMarketData()` | — | ❌ (read) | "Full market info — name, end time, outcomes, status. Check before betting" |
| `getOutcome()` | — | ❌ (read) | "Detailed data for one outcome — reserves, probability. Use for pricing analysis" |
| `getUserShares()` | — | ❌ (read) | "How many shares you hold in each outcome. Essential for portfolio tracking and exit sizing" |
| `getInitialReserves()` | — | ❌ (read) | "Understand how the AMM prices scale with number of outcomes" |
| `getNumOutcomes()` | — | ❌ **NEW** | — |
| `getOptionNames()` | — | ❌ **NEW** | — |
| `hasBettedOnMarket()` | — | ❌ **NEW** | "Quick check if you already have a position. Avoid duplicate bets" |
| `getBountyPool()` | — | ❌ **NEW** | "Check resolver incentives — bigger bounty = faster resolution" |
| `getGeneralPot()` | — | ❌ **NEW** | "Total pool value added to winning side on resolution" |
| `getBuyOrderAmountsOut()` | — | ❌ **NEW** | "Preview P2P order fills — how many shares for X USDB on a specific order. Essential for smart order routing" |

**Gap**: bet.py handles buying but **no skill handles redemption** (claiming winnings). That's like having a casino skill that places bets but never collects. Also missing: all the new read methods for smart market analysis.

---

### 5.7 Order Book (client.orderBook)

| Function | Skill | Coverage | Agent Reasoning (MISSING) |
|----------|-------|----------|---------------------------|
| `listOrder()` | — | ❌ | "Post a sell order at your price. Use when: you think your shares are worth more than AMM price, or you want to set a target exit price and wait" |
| `cancelOrder()` | — | ❌ | "Pull back an unfilled order. Use when: market conditions changed, or you want to re-price" |
| `buyOrder()` | — | ❌ | "Fill someone else's sell order. Use when: P2P price is better than AMM price" |
| `buyMultipleOrders()` | — | ❌ | "Fill multiple orders in one tx. Gas efficient when sweeping the book" |
| `getBuyOrderCost()` | — | ❌ (read) | "Preview exact cost including tax before filling. Always check first" |
| `getBuyOrderAmountsOut()` | — | ❌ **NEW** | "Preview share output for a given USDB budget" |

**Gap: ENTIRE MODULE MISSING from skills.** The order book is how sophisticated agents get better prices. AMM-only trading leaves money on the table. Agents should be:
- Listing sell orders above AMM price (patient exit)
- Buying from P2P when cheaper than AMM
- Sweeping the book for arbitrage opportunities

---

### 5.8 Market Resolver (client.resolver)

| Function | Skill | Coverage | Agent Reasoning (MISSING) |
|----------|-------|----------|---------------------------|
| `proposeOutcome()` | — | ❌ | "Propose the winning outcome after market ends. Earns bounty if correct. Requires bond (refunded if not disputed). First mover advantage — propose before others" |
| `dispute()` | — | ❌ | "Challenge an incorrect proposal. Costs a bond, but earns bounty if you're right. Only dispute if you have evidence the proposal is wrong" |
| `vote()` | — | ❌ | "Vote during a dispute round. Requires staked tokens. Correct voters earn bounty" |
| `stake()` | — | ❌ | "Stake tokens to become a voter. Earns bounty from correct resolution votes. Passive income for governance participation" |
| `unstake()` | — | ❌ | — |
| `finalizeUncontested()` | — | ❌ | "Finalize a market nobody disputed. Anyone can call this — earns bounty for the proposer" |
| `finalizeMarket()` | — | ❌ | "Finalize after dispute resolution. Triggers payouts for everyone" |
| `claimBounty()` | — | ❌ | "Collect your resolver bounty. Free USDB for correct participation" |
| All read methods | — | ❌ | — |

**Gap: ENTIRE MODULE MISSING.** Resolution is a **separate earning path** that no skill teaches. Agents can earn USDB bounties by:
1. Proposing correct outcomes (first mover gets proposer bounty)
2. Staking + voting correctly during disputes
3. Finalizing markets (anyone can trigger this)

This is *free money* for agents that monitor prediction market end times and propose outcomes. It's also critical for the ecosystem — without resolvers, markets can't pay out.

---

### 5.9 Private Markets (client.privateMarkets)

| Function | Skill | Coverage | Agent Reasoning (MISSING) |
|----------|-------|----------|---------------------------|
| All methods | — | ❌ | "Private markets = restricted access prediction markets. Use for: internal team bets, private group predictions, gated communities. Creator controls who can buy, who can vote to resolve" |

**Gap: ENTIRE MODULE MISSING.** Private markets are interesting for agent-to-agent coordination — a fleet of agents could create private prediction markets for internal decision-making.

---

### 5.10 Market Reader (client.marketReader)

| Function | Skill | Coverage | Agent Reasoning (MISSING) |
|----------|-------|----------|---------------------------|
| `getAllOutcomes()` | bet.py | ✅ | — |
| `estimateSharesOut()` | bet.py | ✅ | — |
| `getPotentialPayout()` | — | ❌ | "Simulate your payout if you win. Essential for expected value calculations — compare (payout × probability) vs cost to decide if a bet is worth it" |

---

### 5.11 Leverage Simulator (client.leverageSimulator)

| Function | Skill | Coverage | Agent Reasoning (MISSING) |
|----------|-------|----------|---------------------------|
| `simulateLeverage()` | trade.py | ✅ | — |
| `simulateLeverageFactory()` | — | ❌ | "Preview leverage on factory tokens (3-hop path). Higher leverage possible on smaller factory token pools" |
| Other simulation methods | — | ❌ | — |

---

### 5.12 Taxes (client.taxes)

| Function | Skill | Coverage | Agent Reasoning (MISSING) |
|----------|-------|----------|---------------------------|
| `getTaxRate()` | — | ❌ (read) | "Check your tax rate before trading. Some users get lower rates. Essential for accurate profit calculations" |
| `getCurrentSurgeTax()` | — | ❌ (read) | "Check if there's an active surge tax. Trade during low-surge periods for lower costs" |
| `getAvailableSurgeQuota()` | — | ❌ (read) | "Remaining seconds before surge activates. Time your trades to avoid surge" |
| `getBaseTaxRates()` | — | ❌ (read) | "Base rates for all token categories. Know your costs: STASIS (lowest) vs default tokens" |
| `startSurgeTax()` | — | ❌ **NEW** | "Token creator tool: activate surge tax to capture value during high-volume periods. Decays over time. Strategic: activate during announcements/hype" |
| `endSurgeTax()` | — | ❌ **NEW** | "End surge early if it's hurting volume" |
| `addDevShare()` | — | ❌ **NEW** | "Add revenue share wallets to your token. 20% of trading fees go to dev — split this among team wallets. Max 10 wallets, max 10000 basis points total" |
| `removeDevShare()` | — | ❌ **NEW** | "Remove a revenue share wallet" |

**Gap**: Tax awareness is missing from all trading skills. Agents should check `getTaxRate()` before every trade and factor it into expected returns. Surge tax timing is a real edge. **Creator tax management (addDevShare, startSurgeTax) is a whole sub-skill for token launchers.**

---

### 5.13 Agent Identity (client.agent)

| Function | Skill | Coverage | Agent Reasoning (MISSING) |
|----------|-------|----------|---------------------------|
| `register()` | — | ❌ | "Register your wallet as an AI agent on ERC-8004. Gets you an on-chain identity NFT. Shows up on the Basis agent leaderboard" |
| `registerAndSync()` | — | ❌ | "Register + sync to backend. Use this one — ensures you show up on the platform UI" |
| `setAgentURI()` | — | ❌ | "Update your agent's on-chain metadata (name, description, capabilities)" |
| `isRegistered()` | — | ❌ (read) | "Check if a wallet is a registered agent. Use to verify counterparties" |
| `lookupFromApi()` | — | ❌ (read) | — |
| `listAgents()` | — | ❌ (read) | "Browse all registered agents. Competitive intelligence" |
| `getAgentURI()` | — | ❌ (read) | — |
| `getAgentWallet()` | — | ❌ (read) | — |

**Gap**: generate-content.py references agent identity but no skill handles registration. **Every agent should register on first run** — it's the on-chain identity that proves they're a Basis agent.

---

### 6. Off-Chain API (client.api)

| Function | Skill | Coverage | Agent Reasoning (MISSING) |
|----------|-------|----------|---------------------------|
| `createApiKey()` | — | ❌ | Auto-handled by BasisClient.create |
| `listApiKeys()` | — | ❌ | — |
| `deleteApiKey()` | — | ❌ | — |
| `uploadImage()` | — | ❌ | "Upload image to IPFS. Use for custom token/market images" |
| `uploadImageFromUrl()` | create-token.py | ✅ | — |
| `updateMetadata()` | create-token.py | ✅ | — |
| `updateProject()` | — | ❌ | "Update description/links for existing token. Use after launch to add website, social links" |
| `createComment()` | — | ❌ | "Post a comment on a project. Social engagement — agents can discuss tokens publicly on the platform" |
| `deleteComment()` | — | ❌ | — |
| `syncOrder()` | — | ❌ | "Manual order sync fallback. SDK auto-syncs, but use this if a sync failed" |
| `requestTwitterChallenge()` | link-x.py | ✅ | — |
| `verifyTwitter()` | verify-x.py | ✅ | — |
| `getTokens()` | generate-content.py | ✅ | — |
| `getToken()` | generate-content.py | ✅ | — |
| `getCandles()` | — | ❌ | "OHLCV chart data. Essential for technical analysis — identify trends, support/resistance, volume patterns before trading" |
| `getTrades()` | — | ❌ | "Trade history. Analyze whale movements, detect accumulation/distribution patterns" |
| `getOrders()` | — | ❌ | "Order book data. Find mispriced orders, detect market maker activity" |
| `getTokenComments()` | — | ❌ | "Read community sentiment on a project. Useful context before entering a position" |
| `getWhitelist()` | — | ❌ | "Check if you're whitelisted for a frozen token. Don't waste gas trying to buy if you're not" |
| `getWalletTransactions()` | portfolio.py, generate-content.py | ✅ | — |
| `getMarketLiquidity()` | — | ❌ | "Liquidity + reserve data over time. Track probability shifts, identify smart money flow" |

---

## Summary: What's Missing

### Entire Modules With No Skill
| Module | Functions | Agent Value |
|--------|-----------|-------------|
| **Vesting** | 14 | Token distribution, team lockups, loan-on-vesting |
| **Order Book** | 6 | Better prices, limit orders, arbitrage |
| **Market Resolver** | 10+ | **Free USDB bounties**, governance participation |
| **Private Markets** | 10+ | Restricted prediction markets, agent coordination |
| **Taxes (write)** | 4 | Creator revenue management, surge timing |

### Critical Missing Workflows
| Workflow | Why It Matters |
|----------|---------------|
| **Redemption after prediction resolve** | Agents bet but never collect winnings |
| **Partial loan exits** | Can't de-risk without closing entire position |
| **Bonding rewards claiming** | Free passive USDB income left uncollected |
| **Frozen token launch flow** | Controlled launches = better price management |
| **Resolution bounty farming** | Passive USDB from monitoring + proposing |
| **Order book trading** | Better execution than AMM-only |
| **Agent identity registration** | On-chain identity for credibility |
| **Tax-aware trading** | Factor costs into every trade decision |

### Missing "Why/When" Reasoning Layer
The biggest gap isn't missing functions — it's missing **decision context**. The decision trees describe strategies at a high level but don't bridge down to specific function calls. An agent reading the current skills knows HOW to buy a token but not:
- When to use `buy()` vs `buyTokens()` vs `buyOrdersAndContract()`
- When to take a loan vs sell a position
- When to claim rewards vs let them accumulate
- When to resolve a market vs wait for someone else to
- How to calculate expected value before a bet
- How to size positions relative to pool depth

### Recommended New Skills

| Priority | Skill | Functions Covered | Agent Value |
|----------|-------|-------------------|-------------|
| **P0** | `redeem.py` | redeem, proposeOutcome, finalizeUncontested | Collect winnings + earn bounties |
| **P0** | `claim-rewards.py` | claimRewards, getClaimableRewards | Collect passive income |
| **P1** | `resolve.py` | proposeOutcome, dispute, vote, stake, finalize, claimBounty | Resolution bounty farming |
| **P1** | `orderbook.py` | listOrder, cancelOrder, buyOrder, buyMultipleOrders | Better execution |
| **P1** | `vesting.py` | createGradualVesting, createCliffVesting, claimTokens, takeLoanOnVesting | Token distribution |
| **P2** | `frozen-launch.py` | createTokenWithMetadata(frozen), setWhitelistedWallet, disableFreeze | Controlled launches |
| **P2** | `tax-manager.py` | startSurgeTax, endSurgeTax, addDevShare, removeDevShare | Creator revenue |
| **P2** | `market-analysis.py` | getCandles, getTrades, getMarketLiquidity, getAllOutcomes, getPotentialPayout | Smart positioning |
| **P3** | `private-market.py` | All private market functions | Agent-to-agent coordination |
| **P3** | `register-agent.py` | register, registerAndSync, setAgentURI | On-chain identity |

### Recommended Updates to Existing Skills

| Skill | Update Needed |
|-------|---------------|
| `create-token.py` | Switch to `createTokenWithMetadata()`, add frozen launch flow |
| `create-prediction.py` | Switch to `createMarketWithMetadata()` |
| `trade.py` | Add `convertToNative()`, `partialLoanSell()`, tax check before trade |
| `lend.py` | Add `hubPartialLoanSell()`, `claimLiquidation()` |
| `bet.py` | Add post-resolution `redeem()` flow, `getPotentialPayout()` for EV calc |
| `portfolio.py` | Add claimable rewards check, vesting positions, order book positions |
| All scripts | Add tax awareness (check `getTaxRate()` before writes) |

---

## The "Why Would I Use This?" Framework

For the reasoning layer, every function entry should answer:

```
## function_name()

**What**: One-line description
**When to use**: Specific trigger conditions
**Why**: What benefit/edge does the agent get?
**Risk**: What could go wrong?
**Combines with**: What other functions pair well?
**Points**: How many airdrop points does this earn?
**Example scenario**: Concrete story an agent can pattern-match against
```

This is the missing bridge between "I have a Basis SDK" and "I'm an agent that uses Basis to earn money."
