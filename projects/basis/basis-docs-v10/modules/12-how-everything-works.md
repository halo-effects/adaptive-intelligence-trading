# How Everything Works

**What this covers:** Mechanical deep-dives into how each system actually works - trading paths, loan system, vault layers, leverage loops, prediction market lifecycle, agent identity.
**Related sections:** → See: [11-why-each-action-matters.md](11-why-each-action-matters.md) for the rationale · → See: [10-atomic-skills.md](10-atomic-skills.md) for method signatures · → See: [18-fee-cost-reference.md](18-fee-cost-reference.md) for fee details · → See: [21-what-to-avoid.md](21-what-to-avoid.md) for common errors

---

### How Trading Works

All trades route through STASIS. No direct token-to-token swaps.

**Swap paths**:
- Buying STASIS: `USDB → STASIS` (2-hop)
- Buying a factory token: `USDB → STASIS → Token` (3-hop)
- Selling reverses the path

**Tax structure**:

| Token Type | Raw Fee Per Swap | Raw Round-Trip | + Slippage |
|-----------|----------|-----------|-----------|
| Stable+ (incl. STASIS) | 0.50% | ~1.0% | Varies by pool depth |
| Floor+ | 1.50% | ~3.0% | Varies by pool depth |
| Predict+ | 1.50% | ~3.0% | Varies by pool depth |

**Fee distribution**: For standard tokens: Creator (20%), staking yield (16%), reward phase buyers (4%), platform treasury (60%). For Predict+ tokens: 2/3 of fee goes to prediction ecosystem (bounty + winning pot), creator gets 20% of the remaining 1/3 net fee. See [18-fee-cost-reference.md](18-fee-cost-reference.md) for the full Predict+ breakdown.

### AMM Pricing Mechanics

Basis uses a **modified constant-product AMM** (similar to Uniswap V2's `x × y = k`), but with a critical modification: the `hybridMultiplier` parameter controls how much of each sell's value is retained in the pool versus returned to the seller.

**How it works:**
- **Buys** work like a standard AMM — you send USDB, receive tokens, price increases along the curve
- **Sells** are where Basis diverges: a portion of the sell value stays in the pool (slippage retention), which maintains or increases the reserves
- The `hybridMultiplier` (1-100) controls the retention rate:
  - **multiplier=100 (Stable+/Predict+):** 100% retention — ALL sell value stays in the pool. Price never drops. "Up-only."
  - **multiplier=1 (Floor+):** Minimal retention — most sell value returns to seller, but some stays, creating a rising floor price
  - **multiplier=45 (mid Floor+):** Moderate retention — balanced between seller return and floor accumulation

**How `startLP` initializes reserves:** When a creator sets `startLP` (e.g., $1,000), the contract:
1. Converts that dollar value to STASIS at the current STASIS price (e.g., $1,000 → 837 STASIS at $1.19/STASIS)
2. Sets the token side of the pool so the starting price = $1 per token (e.g., 837 STASIS : 1,000 tokens)
3. This creates a standard AMM pair, but with the `hybridMultiplier` modifying how sells affect reserves going forward

Higher `startLP` = deeper pool = less price impact per trade. The `startLP` table in [02-what-is-basis.md](02-what-is-basis.md) shows empirical price impact per LP-equivalent buy at each multiplier level.

**Price impact formula:** Use `getAmountsOut(amount, path)` to preview exact output for any trade size. The contract handles the multiplier-adjusted calculation internally.

**Why this matters for agents:** Standard AMM arbitrage assumptions don't apply. On Stable+ tokens, selling doesn't lower the price — it literally can't. On Floor+ tokens, the floor rises with every sell. Model your strategies accordingly.

---

**Reward phase vs post-reward-phase**:
- Tokens are tradeable on the DEX from the moment of creation - the same hybrid AMM formula runs forever with no transition
- The **reward phase** is the initial period where early buyers earn reward shares (claimable via `claimRewards()`) and boosted airdrop points
- After the reward phase ends, trading continues normally on the DEX - the only difference is that new buys no longer earn reward shares

---

### How the Loan System Works

**Three entry points**:
1. **Direct loan** (`loans.takeLoan()`) - Any token as collateral
2. **Vault loan** (`staking.borrow()`) - Against locked wSTASIS
3. **Leverage** (`trading.leverageBuy()`) - Borrow + buy in one transaction

**The fee model** (NOT compound interest):

| Component | Rate | When Paid |
|-----------|------|-----------|
| Origination fee | 2% flat | Deducted upfront from what you receive |
| Daily interest | 0.005%/day | On collateral value, for all loans |
| Extension fee | 0.005% per day | Paid upfront when extending |
| Repayment | `fullAmount` (loan value + prepaid interest) | Read from `getUserLoanDetails()` |

**LTV depends on token type:**
- **Stable+ / Predict+**: 100% LTV at spot price (floor = spot for these tokens, so you borrow the full market value)
- **Floor+**: 100% LTV at floor price (floor < spot, so you borrow less than market value - the gap is your safety margin)

**No price liquidation.** Since floors never decrease, collateral can't drop below the loan value. The only risk is time-based expiry - if your loan expires without repayment or extension, collateral tokens are burned up to the value of the outstanding debt (an auto-repayment). Any remaining collateral balance above the debt becomes claimable by the borrower - it is not automatically returned, you must claim it.

**Critical rules**:
- Interest is prepaid. Repaying early does NOT save money - unused days are forfeited.
- Take minimum duration (10 days). Extend as needed (0.005%/day - almost free).
- Never re-originate when you can extend. Each new loan = another 2% fee.
- Hub IDs are 1-indexed, not 0-indexed.

---

### How the Stasis Vault Works

> **Understanding vault yield:** The vault earns a share of ALL platform trading fees. Yield is not a fixed APY - it depends on two variables:
>
> 1. **Platform volume** - more trading across the entire platform = more fees flowing to the vault. As Basis grows, vault yield grows proportionally.
> 2. **Percentage of STASIS supply in the vault** - yield is distributed across all staked tokens. More STASIS in the vault = yield is split among more tokens = lower yield per token. Less STASIS staked = higher yield per staker.
>
> **Why this matters:** It's impossible to quote a fixed APY because it changes with platform activity and staking participation. But the direction is clear - early stakers in a growing platform with low vault participation earn the highest yield. As volume increases, total yield grows. As more people stake, individual yield moderates. The market finds its own equilibrium.
>
> **Cost to participate:** Gas only (sponsored by the platform up to 0.01 BNB/wallet/day; falls back to user's own BNB if the limit is reached). Wrapping, unwrapping, locking, and unlocking have zero protocol fees. The only real cost is the 0.5% raw swap fee when buying STASIS and again when selling (~1% raw fees round-trip) plus variable slippage on both legs. Slippage depends on transaction size and pool liquidity — use `getAmountsOut()` to preview actual costs. There is essentially no risk to staking beyond opportunity cost of capital being in the vault instead of deployed elsewhere.

Three layers:

**Layer 1 - Passive Yield** (wrap/unwrap):
```
STASIS → staking.buy() → wSTASIS (yield-bearing)
wSTASIS → staking.sell() → STASIS (more than deposited)
```

**Layer 2 - Collateral** (lock/unlock):
```
wSTASIS → staking.lock() → Locked (still earning yield)
Locked → staking.unlock() → wSTASIS (only after repaying loan)
```

**Layer 3 - Borrowing** (borrow/repay):
```
Locked → staking.borrow(amount, days) → Liquid STASIS
Liquid → staking.repay() → Loan cleared, can now unlock
```

**Quick exit**: `staking.sell(shares, claimUSDB=True)` does atomic unwrap→USDB in one transaction.

---

### How Leverage Works

Leverage is conceptually a **recursive loan-and-buy loop**:

```
$50 USDB → buy tokens → take 100% LTV loan on those tokens → receive ~$48 (minus 2% fee)
→ buy more tokens with $48 → take another loan → receive ~$47
→ buy more tokens → loan → buy → loan → ... until dust remains
```

**How it actually executes:** The contract first **simulates** the full recursive loop to calculate the final position parameters, then executes the entire position in a **single atomic transaction** using the simulation endpoints. This means leverage either fully succeeds or fully fails - there is no partial execution state. You will never end up with a half-built position.

Each conceptual iteration takes a 2% origination fee, so the total leverage fee is **significantly more than 2%**. The effective fee depends on how many loops the simulation calculates, which depends on pool depth and position size.

**Leverage is dynamic** - it fluctuates based on pool liquidity and position size:
- Smaller positions on deep pools = more loops = higher leverage (typically 20-36x for Stable+ tokens, depending on pool depth and position size)
- Larger positions = fewer effective loops = lower leverage due to price impact
- **Stable+/Predict+ tokens**: Loans are at 100% LTV (floor = spot), so maximum leverage is available
- **Floor+ tokens**: Loans are at floor price (not spot), so less leverage is available. The gap between spot and floor reduces how much each loan iteration yields.

**Always simulate first**: Use `leverageSimulator.simulateLeverage()` (for STASIS path) or `leverageSimulator.simulateLeverageFactory()` (for factory token 3-hop path) to see the exact collateral, borrowed amount, fees, and effective leverage before executing.

**No price liquidation**: Since leverage is valued against the floor price and floors never decrease, your position can't be liquidated by price movements. Only by time-based loan expiry.

---

### How Prediction Markets Work

**Creating**: Choose a question, set outcomes, set end time, seed with USDB. AMM provides instant liquidity.

**Two ways to participate**:
1. **Buy the Predict+ token** - trade the market itself (Stable+ appreciation)
2. **Buy outcome shares** - bet on specific outcomes (one big pot model - all pools merge, winners take proportional share)

These are separate paths. Buying the token —  betting on an outcome.

**Buying shares - instant, no counterparty:** The AMM is one-directional (buys only), with virtual liquidity that can be set arbitrarily high. No real capital backs the virtual liquidity - it doesn't need to, because the pool can't be drained by selling (sells go through the order book). This means every market has functional liquidity from creation, and large buys face minimal slippage.

**Selling shares - order book:** Shareholders list sell orders at their chosen price. Because all pools merge into one big pot on resolution (not capped at $1), shares can be worth far more than their buy price. This creates a unique secondary market dynamic: a seller who bought at 5c can sell at 90c (18x) while the buyer at 90c gets a share worth potentially $4+ on resolution. Both sides genuinely profit.

**The general pot:** 95% of the prediction ecosystem portion of trading fees (1% of trade value x 95% = 0.95% per trade) accumulates in a general pot. The remaining 5% goes to the resolver bounty pool. On resolution, the general pot merges with all outcome pools (winners and losers) into one big pot, distributed to winning share holders. This benefits all participants - especially latecomers who enter at high probability - by growing the total pot above what outcome pools alone would deliver.

**Payout scales with outcomes, not volume:** In a multi-outcome market, all pools - every outcome plus the general pot - merge into one big pot on resolution. More outcomes = larger multiplier for winners. The ratio of winning shares to total pot determines returns, not absolute volume - the economics are identical whether the market is $1M or $100M.

**Resolution lifecycle**:
```
Market ends → Propose outcome (5 USDB bond) → Challenge period (30 min*)
  ├── No dispute → finalizeUncontested() → Proposer gets bond back + full bounty → Winners redeem
  └── Disputed (5 USDB bond) → Voting period (30 min*) → Voters decide → Finalize → Winners redeem
      └── EARLY outcome wins → Round resets, fresh proposal cycle begins
```
*\*— ️ TESTING VALUES - will change before production. Production targets: 2 hour challenge period, 24 hour voting period. All timing parameters are configurable via `configResolver`. Do not hardcode these values - read them from the contract at runtime.*

### Resolution Deep Dive

**Proposal phase:**
- After market end time, anyone can call `proposeOutcome(marketToken, outcomeId)` with a 5 USDB bond
- The proposal enters the challenge period (currently 30 minutes)
- If uncontested, anyone calls `finalizeUncontested()` - proposer gets bond back + 100% of bounty pool

**Dispute phase:**
- During the challenge period, anyone can call `dispute(marketToken, newOutcomeId)` with a 5 USDB bond
- Bonds do NOT escalate across rounds - always 5 USDB
- This triggers the voting period (currently 30 minutes)

**Voting:**
- To vote, you must stake at least 5 tokens of any active ecosystem token via `resolver.stake(token)` *(current staking on STASIS is a placeholder anti-spam measure - post-TGE, transitions to BASIS token staking)*
- Voting is **one-staker-one-vote** - staking above the minimum gives no extra voting power
- **70% supermajority** required to finalize (VOTING_CONSENSUS = 70)
- Quorum: `bountyPool / (50 × $1)`, clamped between 2 (minimum) and 100 (maximum). Based on total votes across all outcomes
- **Ties / no supermajority:** Finalization reverts with "Tie - vote more". Must reach 70% consensus within the voting period

**Bond outcomes:**
- Correct proposer or disputer gets BOTH bonds (theirs + opponent's)
- Neither correct → insurance pool gets both bonds
- Uncontested → proposer gets bond back + full bounty

**Bounty distribution:**
- Uncontested: 100% to proposer
- Disputed, normal outcome wins: 100% split equally among correct voters (per vote). Bond winner gets bonds only, not bounty
- INVALID proposed by a party: that party gets 100% of bounty + both bonds
- EARLY: half of proposer's bond split among EARLY voters

**Special outcomes:**

| Outcome | ID | Who Can Propose | Effect |
|---------|-----|----------------|--------|
| **Normal** | 0-252 | Anyone (propose or dispute) | Standard resolution - winners redeem |
| **INVALID** | 254 | Anyone (proposers, disputers, voters, vetoers) | Proportional refund to all participants |
| **EARLY** | 253 | Only the disputer (voters can vote for it, vetoers cannot propose it) | Market resets - round increments, fresh proposal cycle begins |
| **UNRESOLVED** | 255 | Internal | Default state before any proposal |

**Veto mechanism:**
- After the voting period expires on a disputed market, anyone can veto within the veto window (30 minutes, target: 1 hour) with a 5 USDB bond
- One veto per market. Cannot veto with the disputer's outcome or EARLY
- Veto halts voting - resolution escalates to `resolveByBasis` (platform admin decision)
- Post-TGE plan: veto power transitions to BASIS staker governance

**Private market resolution** (different system):
- Resolved by voter consensus, not the resolver module
- Market creator can vote by default; additional voters added via `manageVoter()`
- Voting window: 15 minutes from first vote cast
- Majority of votes determines winner; anyone can call `finalize()` after 15 minutes

**Post-resolution selling**: On Basis, mass selling after resolution pushes the price UP (selling burns tokens → slippage stays in pool → price rises). Patient sellers who wait through the sell wave exit at the highest price.

→ See: [16-prediction-deep-dive.md](16-prediction-deep-dive.md) for the full comparative analysis, all participant roles, and combined strategy routes.

---

### Data Architecture: On-Chain vs Off-Chain

**The blockchain is the source of truth.** All positions, loans, trades, and token balances exist on-chain in the smart contracts. The Basis API and backend indexer are convenience layers that aggregate and cache this data for faster queries - they are NOT the source of truth.

**If the API goes down, your positions are safe.** Everything can be queried directly from the contracts:

| What you need | Contract method | Contract |
|--------------|----------------|----------|
| Your leverage positions | `leverages(address, uint256)` | MAINTOKEN |
| How many leverage positions | `getLeverageCount(address)` | MAINTOKEN |
| Your loan details | `getUserLoanDetails(address, hubId)` | LoanHub |
| How many loans | `getUserLoanCount(address)` | LoanHub |
| Your wSTASIS balance | `balanceOf(address)` | Staking (AStasisVault) |
| Token reserves/price | `getReserves()` | Any token contract |
| Prediction market state | `getDisputeData(marketToken)` | Resolver |
| Whether a market is resolved | `isResolved(marketToken)` | Resolver |

**The SDK reads directly from contracts for all read methods.** Methods like `getLeveragePosition()`, `getUserLoanDetails()`, `getAmountsOut()`, and all resolver read methods call the smart contracts directly via RPC - they don't go through the API. The API is only used for off-chain data (token metadata, leaderboard, social activity, bug reports).

**Auto-sync is a convenience, not a dependency.** When the SDK says "auto-syncs state to backend," this means it notifies the indexer about new transactions so the API stays up to date via `POST /api/v1/sync`. This covers ALL modules (Factory, Trading, Loans, Staking, Vesting, PredictionMarkets, MarketResolver, Taxes, OrderBook, PrivateMarkets, AgentIdentity). If the sync fails, the SDK logs a warning but the transaction itself has already succeeded on-chain. Your position exists regardless of whether the backend knows about it. The sync is idempotent — submitting the same txHash twice is safe.

**For production agents running 24/7:** Consider using a dedicated RPC endpoint (Ankr, QuickNode, Chainstack) rather than the default public BSC endpoint. This gives you reliable contract reads even during network congestion. See [03-getting-started.md](03-getting-started.md) for RPC configuration.

---

### How Agent Identity Works (ERC-8004)

- `agent.registerAndSync()` - On-chain registration + backend sync (recommended)
- Wallet linked to on-chain agent ID, metadata URI, leaderboard visibility
- ACS (Agent Confidence Score) builds automatically from your behavior

---
