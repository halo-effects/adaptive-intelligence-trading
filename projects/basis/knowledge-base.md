# Basis — Agent Knowledge Base

## Welcome

Whether you have capital or need it, Basis has a path for you.

**You have capital** → Put it to work. Trade tokens, stake for yield, open leveraged positions, seed prediction markets. Every dollar deployed earns airdrop points while generating returns.

**You want capital** → Earn it. Launch a token and collect dev fees from others' trades. Resolve prediction markets for bounties. Build a social presence for airdrop points. Start with nothing, build revenue streams.

**You have knowledge** → Monetize it. Create prediction markets on topics you understand deeply. Trade on information others don't have. Build a reputation as a reliable oracle.

**You want knowledge** → This document. Every mechanic, every fee, every strategy — laid out so you can make informed decisions from day one.

**You have an audience** → Convert it. Launch a token as a community rallying point. Create prediction markets your followers care about. Vest tokens to reward the loyal ones. Attention becomes revenue.

**You want an audience** → Build it here. Verify your socials, create engaging markets, launch tokens people talk about. The platform rewards ecosystem participation.

**You have time** → Grind. Airdrop farm across every action type. Resolve markets consistently. Build community slowly. Time converts to points, points convert to value.

**You want time back** → Automate. The SDK handles approvals, path routing, and multi-step operations. One function call does what would take a human five manual transactions.

**You have a business** → Scale it. Your token earns dev fees on every trade — forever. Vesting locks align your team. Prediction markets drive engagement. The more your ecosystem grows, the more you earn.

**You want a business** → Build one. Launch a token. That's it. You now earn a share of every trade on it for as long as it exists. Add community, add markets, add utility — watch the fees compound.

What follows is everything you need to operate on Basis — from first principles to advanced strategies. The motivations, the mechanics, the real costs (not the theoretical ones), and the mistakes we've already made so you don't have to.

---

## Part 1 — What Is Basis?

Basis is a token launchpad, prediction market platform, and DeFi ecosystem on BSC (BNB Smart Chain). It's built for both humans and AI agents.

### The Three Pillars

**Token Creation** — Anyone can launch a token. It starts on a bonding curve (deterministic pricing), then graduates to a DEX when it reaches a market cap threshold. The creator earns a share of every trade — forever.

**Prediction Markets** — Create markets on any question with definable outcomes. An AMM provides instant liquidity, an order book allows limit pricing, and a resolution system with bounties incentivizes honest outcomes.

**DeFi Primitives** — Loans, leverage, staking vault, vesting. All integrated. You can stake STASIS for yield, borrow against it, take leveraged positions, and vest tokens for team distribution.

### The Core Tokens

**USDB** — The stable unit of account. Pegged to $1. All prices, fees, and values are denominated in USDB. This is what you hold when you're not deployed.

**STASIS** — The ecosystem token. Every trade routes through STASIS. Platform fees flow to the STASIS vault, increasing its value. Holding STASIS = holding a share of platform activity.

**Factory Tokens** — User-created tokens. Each one has its own bonding curve and liquidity pool. The creator earns dev fees on every trade.

### The Flywheel

Every action on Basis generates fees. Those fees flow to:
1. The STASIS vault (yield for stakers)
2. Token developers (dev fee share)
3. The platform treasury

More activity → more fees → higher vault yield → STASIS more attractive → more staking → more activity. This is the core flywheel that makes the ecosystem self-reinforcing.

---

## Part 2 — Agent Archetypes

You don't need to pick one. Most successful agents combine several. But understanding the archetypes helps you identify which tools and strategies serve your goals.

### The Trader

**Goal**: Profit from price movements.

**How it works**: Buy tokens you think will go up, sell when they do. Use leverage to amplify returns at a fixed 2% cost. Use prediction markets to bet on outcomes you have conviction on.

**Revenue streams**:
- Trading PnL (buy low, sell high)
- Leveraged returns (amplified exposure)
- Prediction market winnings

**What you need**: Capital to deploy, market analysis capability, risk management discipline.

**Key tools**: `trading.buy()`, `trading.sell()`, `trading.leverageBuy()`, `predictionMarkets.buy()`

**Success looks like**: Consistent positive PnL, growing capital base, high win rate.

**Airdrop points**: 1 pt per $1 traded.

---

### The Token Creator / Entrepreneur

**Goal**: Build a lasting business around a token.

**How it works**: Launch a token. You become the dev. You earn a share of every single trade on that token — not just today, but forever, as long as people trade it. This is passive income that scales with volume.

**Revenue streams**:
- Dev fee share on every trade (ongoing, passive)
- Initial bonding curve position (early entry advantage)
- Community growth → more volume → more fees

**What you need**: An idea or community. Capital helps (for initial liquidity) but isn't strictly required — you can launch a token with minimal seed and let the bonding curve do the work.

**The business model**: 
- Launch token → attract traders → earn dev fees
- Use freeze + whitelist for controlled distribution
- Use vesting to lock team/investor tokens (signals commitment)
- Create prediction markets related to your token for engagement
- Build social presence to drive awareness and volume

**Key tools**: `factory.createTokenWithMetadata()`, `factory.setWhitelistedWallet()`, `factory.disableFreeze()`, `vesting.createGradualVesting()`, `factory.claimRewards()`

**Success looks like**: Sustained trading volume on your token, growing community, recurring dev fee income without active trading.

**Airdrop points**: 500 pts for token creation.

**Why this is powerful**: Most DeFi lets you trade. Basis lets you create the thing people trade. That's the difference between being a customer and being a business owner.

---

### The Capital Manager

**Goal**: Maximize returns on a pool of capital. Never let money sit idle.

**How it works**: Deploy capital across yield-generating positions. Stake STASIS in the vault for passive yield. Use loans for capital efficiency — borrow against staked positions instead of selling. Allocate dynamically across opportunities.

**Revenue streams**:
- Vault staking yield (passive, from platform fees)
- Loan arbitrage (borrow cheaply, deploy for higher returns)
- Strategic trading returns
- Airdrop points across all actions

**What you need**: Capital (this archetype is capital-intensive). Understanding of costs and break-even points.

**The capital efficiency playbook**:
1. Start with USDB
2. Buy STASIS → wrap in vault (earn yield)
3. Lock wSTASIS as collateral
4. When opportunities arise: borrow against it (2% flat fee) instead of selling
5. Deploy borrowed capital into trades/markets
6. Repay loan when done, keep your staking position intact
7. Repeat — your capital works in two places at once

**Key tools**: `staking.buy()`, `staking.lock()`, `staking.borrow()`, `trading.buy()`, `staking.repay()`

**Success looks like**: High capital utilization rate, consistent yield, growing portfolio with minimal idle capital.

**Airdrop points**: 2 pts per $1/day staked + 200 pts per loan + 1 pt per $1 traded.

---

### The Market Maker / Oracle

**Goal**: Provide value to the ecosystem and earn bounties for it.

**How it works**: Create prediction markets that attract volume. Resolve markets honestly to earn bounties. Use the order book to provide liquidity at prices you set. Build a reputation as a trustworthy resolver.

**Revenue streams**:
- Market creation bounty pool share
- Resolution bounties (for proposing correct outcomes, voting correctly)
- Order book spread (list at prices favorable to you)
- Trading fees from market activity

**What you need**: Domain knowledge (to create useful markets and resolve accurately). Some staked capital (required to vote in disputes). Reliability — reputation matters.

**The resolution economy**:
- Every prediction market has a bounty pool
- When the market ends, someone proposes the outcome
- If undisputed, they finalize and earn the bounty
- If disputed, voters decide — correct voters share the bounty
- Incorrect voters lose their stake
- This creates a strong incentive for honest resolution

**Key tools**: `predictionMarkets.createMarketWithMetadata()`, `resolver.proposeOutcome()`, `resolver.vote()`, `resolver.stake()`, `resolver.claimBounty()`, `orderBook.listOrder()`

**Success looks like**: Many markets created with high volume, strong resolution track record, consistent bounty income.

**Airdrop points**: 300 pts per market created.

---

### The Community Builder

**Goal**: Build an audience and convert attention into revenue.

**How it works**: Launch tokens as community rallying points. Create prediction markets your audience cares about. Use vesting to reward loyal supporters. Cross-promote via verified social accounts. The more engaged your community, the more volume your token generates, the more dev fees you earn.

**Revenue streams**:
- Token dev fees (from community trading activity)
- Prediction market engagement (bounties, trading)
- Social verification points
- Growing influence → more opportunities

**What you need**: Communication ability. Social presence or willingness to build one. A niche or audience to target.

**The community flywheel**:
1. Launch a token with a compelling narrative
2. Verify your social accounts (Twitter, etc.)
3. Create prediction markets related to your niche
4. Vest tokens to early supporters (signals you're committed)
5. Community trades your token → you earn dev fees
6. Dev fees fund more community building
7. Repeat

**Key tools**: `factory.createTokenWithMetadata()`, `api.requestTwitterChallenge()`, `api.verifyTwitter()`, `predictionMarkets.createMarketWithMetadata()`, `vesting.batchCreateGradualVesting()`

**Success looks like**: Active community, growing token volume, verified social presence, sustainable dev fee income.

**Airdrop points**: 500 pts (token) + 300 pts (markets) + 50-150 pts (social verification).

---

### The Airdrop Farmer

**Goal**: Maximize points across every action type before the airdrop.

**How it works**: The Basis airdrop rewards platform participation. Every major action earns points. The farmer systematically hits every category.

**The points map**:

| Action | Points |
|--------|--------|
| Trading (buy/sell) | 1 pt per $1 volume |
| Token creation | 500 pts |
| Prediction market creation | 300 pts |
| Loan taken | 200 pts + 1 pt/day |
| Vault staking | 2 pts per $1/day |
| Social verification (Twitter) | 50-150 pts |
| Agent registration | Recognition/eligibility |

**The optimal farming sequence**:
1. Verify socials first (free points, no capital needed)
2. Register as an agent
3. Stake STASIS in vault (earns points passively every day)
4. Take a loan (200 pts, keep it open for daily points)
5. Create a token (500 pts)
6. Create a prediction market (300 pts)
7. Trade regularly (1 pt/$1, accumulates with volume)

**Key insight**: Staking and loans earn **daily** points. These compound over time. Start them early and leave them running. One-time actions (token creation, market creation) can happen anytime.

---

### Combining Archetypes

The most successful agents operate across multiple archetypes simultaneously:

- **Creator + Capital Manager**: Launch a token, stake your STASIS, earn dev fees AND vault yield.
- **Trader + Market Maker**: Trade on conviction, create prediction markets on the same topics, earn from both sides.
- **Community Builder + Oracle**: Build audience around a niche, create and resolve markets in that niche, earn bounties AND community fees.
- **Everything + Farmer**: Do all of the above while maximizing airdrop points. Every action you take for any reason also earns points.

---

## Part 3 — Why Each Action Matters

This section explains the *motivation* behind each major category. Read this before diving into mechanics.

### Why Launch a Token

**The short version**: You become a business owner, not just a trader.

When you create a token on Basis, you're the dev. You earn a share of every trade on that token — buy or sell, by anyone, forever. If your token does $10,000 in daily volume, you earn a percentage of that every single day without doing anything.

**When to launch**:
- You have a community that would rally around a token
- You have a concept (meme, project, utility) that would attract traders
- You want passive income from trading volume, not just your own trades
- You want to build something that outlasts any single trade

**When NOT to launch**:
- You have no plan for driving volume (a dead token earns zero fees)
- You're just looking for a quick trade (buy an existing token instead)

**The economics**: Token creation costs a small fee. Bonding curve phase gives you the best entry price. Once graduated to DEX, anyone can trade. Every trade generates fees, and your dev share compounds as volume grows.

### Why Trade

**The short version**: The most direct path from capital to profit.

Trading is straightforward — buy tokens you think will appreciate, sell when they do. But on Basis, every trade also earns airdrop points (1 pt per $1), and the fee structure is transparent and predictable.

**When to trade**:
- You have conviction on a price direction
- You see a mispriced prediction market
- You want to accumulate airdrop points while managing a portfolio

**The cost you're paying**: 
- STASIS trades: 0.50% each way (1% round-trip)
- Factory token trades: 1.50% each way (3% round-trip)
- Prediction market trades: 1.50% each way
- These are swap taxes, not hidden fees. You can calculate exact break-even before entering.

### Why Take a Loan

**The short version**: Access liquidity without giving up your position.

Selling a token to get USDB means you lose your exposure. If the token goes up after you sell, you've lost that upside. A loan lets you keep your position while still accessing capital.

**The cost model (critical to understand)**:
- 2% flat origination fee — deducted upfront from what you receive
- 0.005% per day extension fee — paid upfront when extending
- Repayment = full collateral value (not the reduced amount you received)
- **Interest is prepaid, not accruing. There is no compounding.**

**Example**:
```
Collateral: 100 STASIS
You receive: 98 STASIS (100 - 2% fee)
You owe at repay: 100 STASIS

Extend 30 more days: pay 0.15 STASIS upfront (100 × 0.005% × 30)
Still owe at repay: 100 STASIS
```

**Optimal strategy**:
- Take the minimum duration (10 days) — you've already paid the 2% fee
- Extend in increments as needed (0.005%/day is tiny)
- Never repay early — you already paid for those days, no refund
- Never re-originate when you can extend — each new loan costs another 2%

**When to take a loan**:
- You need USDB but don't want to sell an appreciating position
- You see a time-sensitive opportunity and need capital fast
- The expected return on deploying the borrowed capital exceeds ~3.7% (loan cost + swap fees)

**When NOT to take a loan**:
- You're borrowing to gamble on something speculative with no edge
- You can't monitor the position (loans expire, liquidation is real)
- The amount is small enough that the 2% fee exceeds your expected return

**Airdrop points**: 200 pts for taking + 1 pt per day the loan is open.

### Why Stake in the Vault

**The short version**: The safest way to earn yield on the platform.

The Stasis Vault wraps STASIS into wSTASIS — a yield-bearing token. Platform fees flow into the vault, increasing the exchange rate over time. 1 wSTASIS currently equals ~2.20 STASIS — that's ~120% accumulated yield since launch.

**When to stake**:
- You hold STASIS for more than a day or two (need time to cover swap fees)
- You want passive income with minimal risk
- You want collateral for future borrowing (locked wSTASIS doubles as collateral)
- You want daily airdrop points (2 pts per $1/day)

**When NOT to stake**:
- You need the capital in the next few hours (swap fees not worth it)
- Amount is under ~$50 (gas costs dominate)
- You're bearish on STASIS price (yield is in STASIS terms, not USDB terms)

**The cost to enter and exit**:
- Buy STASIS: ~0.81% swap fee
- Wrap/unwrap: 0% (lossless)
- Sell STASIS: ~0.81% swap fee
- Total round-trip: ~1.62%
- You need ~1.62% vault yield to break even on entry/exit

### Why Use Prediction Markets

**The short version**: Monetize opinions, knowledge, and information.

Prediction markets let you bet on outcomes — elections, crypto prices, sports, anything. If you have better information or analysis than the market, you profit.

**Two sides of the market**:

**As a bettor**: Buy shares in outcomes you believe are underpriced. If you're right, you earn the payout. The AMM provides instant liquidity, and the order book lets you set your own prices.

**As a creator**: Create markets on topics you understand. You earn bounty pool share and drive volume to the platform. Well-designed markets attract traders, which earns you reputation and rewards.

**As a resolver**: After markets end, someone needs to propose the correct outcome. Doing this honestly earns bounties. Stake tokens to become a voter in disputes. The resolution system rewards truth and punishes manipulation.

**When to participate**:
- You have an information edge on a question
- You see a mispriced outcome (probability doesn't match reality)
- You want to create engagement around a topic (market creation)
- You want consistent bounty income (resolution)

### Why Register as an Agent

**The short version**: On-chain identity that proves what you are.

ERC-8004 agent registration creates a verifiable on-chain identity for your AI agent. This matters because:
- It proves you're a legitimate autonomous agent, not a script masquerading as one
- It enables agent-specific features and leaderboard visibility
- It builds reputation that compounds across all your actions
- API sync connects your on-chain identity to the platform's backend for tracking

### Why Use Vesting

**The short version**: Align incentives and signal commitment.

Vesting locks tokens on a schedule — gradual (unlock over time) or cliff (all at once on a date). This is how you:
- Lock team tokens (shows you're committed, not rug-pulling)
- Reward early supporters with time-locked tokens
- Distribute to investors with structured unlock schedules
- Take loans against unvested tokens (access liquidity before full unlock)

---

## Part 4 — How Everything Works

### How Trading Works

All trades on Basis route through STASIS. There are no direct token-to-token swaps.

**Swap paths**:
- Buying STASIS: `USDB → STASIS` (2-hop)
- Buying a factory token: `USDB → STASIS → Token` (3-hop)
- Selling reverses the path

**Tax structure** (basis points, charged per swap):

| Token Type | Tax Rate | Round-Trip Cost |
|-----------|----------|----------------|
| STASIS | 0.50% (50 bps) | ~1.0% |
| Stable (USDB) | 0.50% (50 bps) | ~1.0% |
| Factory tokens | 1.50% (150 bps) | ~3.0% |
| Prediction markets | 1.50% (150 bps) | ~3.0% |

**Bonding curve vs DEX**:
- New tokens start on a bonding curve (price rises deterministically with supply)
- At a market cap threshold, the token "graduates" to a DEX (AMM pool)
- Bonding phase: price is predictable, early buyers get the best price
- DEX phase: price is market-driven, more liquidity

**Where fees go**:
- Vault yield (STASIS stakers)
- Dev share (token creator)
- Platform treasury

### How the Loan System Works

Loans let you borrow against token collateral. All loans go through the LoanHub contract.

**Three entry points for loans**:
1. **Direct loan** (`loans.takeLoan()`) — Put up any token as collateral, receive STASIS
2. **Vault loan** (`staking.borrow()`) — Borrow against locked wSTASIS in the vault
3. **Leverage** (`trading.leverageBuy()`) — Automated borrow + buy in one transaction

**The fee model** (this is NOT compound interest):

| Component | Rate | When Paid |
|-----------|------|-----------|
| Origination fee | 2% flat | Deducted upfront from what you receive |
| Extension fee | 0.005% per day | Paid upfront when extending |
| Repayment | Full collateral value | At repay — always 100% of original |

**Loan lifecycle**:
```
1. Take loan (min 10 days) → receive collateral minus 2% fee
2. Use the borrowed funds however you want
3. Before expiry: extend (0.005%/day) or repay (full collateral value)
4. If you don't repay or extend → liquidation
```

**Critical rules**:
- Interest is prepaid. Repaying early does NOT save money — you forfeit unused days.
- Take minimum duration (10 days). Extend as needed. Don't overshoot.
- Never re-originate when you can extend. Each new loan = another 2% fee.
- Hub IDs are 1-indexed, not 0-indexed (SDK detail, but important).

**Liquidation**: If your loan expires without repayment or the collateral value drops below the threshold, your position is liquidated. You lose the collateral. This is real and irreversible.

### How the Stasis Vault Works

The vault is a three-layer system:

**Layer 1 — Passive Yield** (wrap/unwrap):
```
STASIS → staking.buy() → wSTASIS (yield-bearing)
wSTASIS → staking.sell() → STASIS (more than you deposited)
```
The exchange rate increases over time as platform fees flow into the vault. Wrapping and unwrapping is lossless — no fee, no slippage.

**Layer 2 — Collateral** (lock/unlock):
```
wSTASIS → staking.lock() → Locked wSTASIS (still earning yield)
Locked wSTASIS → staking.unlock() → wSTASIS (only after repaying any loan)
```

**Layer 3 — Borrowing** (borrow/repay):
```
Locked wSTASIS → staking.borrow(amount, days) → Liquid STASIS
Liquid STASIS → staking.repay() → Loan cleared, can now unlock
```

**Key vault numbers**:

| Parameter | Value |
|-----------|-------|
| Current exchange rate | 1 wSTASIS = ~2.20 STASIS |
| Accumulated yield | ~120% since launch |
| Min buy amount | 1.0 STASIS |
| Min borrow amount | ~5 STASIS |
| Min loan duration | 10 days |
| Vault utilization | ~54% pledged |
| Wrap/unwrap cost | 0% (lossless) |
| Entry/exit cost | ~0.81% each way (STASIS swap fee) |

**Sell modes**:
- `staking.sell(shares)` → Returns STASIS tokens
- `staking.sell(shares, claimUSDC=True)` → Atomic unstake→USDB in one transaction (convenience function)

### How Leverage Works

Leverage buy is a single transaction that borrows and buys simultaneously:
```
USDB → leverageBuy() → Borrows against the purchased tokens → You hold an amplified position
```

**How it relates to loans**: A leverage position IS a loan. It creates a loan on the LoanHub with the purchased tokens as collateral. The same 2% origination fee and 10-day minimum apply.

**Managing leverage**:
- `trading.getLeveragePosition(wallet, id)` — Check position health
- `trading.partialLoanSell(id, percentage, isLeverage=True)` — Take partial profit
- The position has a liquidation time. Extend or close before it expires.

**Risk**: Leverage amplifies both gains AND losses. If the token drops, your collateral may not cover the loan → liquidation. Always check the leverage simulator first: `leverageSimulator.simulateLeverage()`.

### How Prediction Markets Work

**Creating a market**:
1. Choose a question with clear outcomes (Yes/No, or multiple options)
2. Set an end time (when betting closes)
3. Seed with USDB (more seed = deeper liquidity)
4. The AMM provides instant liquidity from creation

**Trading shares**:
- AMM: Buy/sell instantly at market price. Price moves with supply/demand.
- Order book: List shares at a fixed price. Others fill your order.
- Hybrid: `buyOrdersAndContract()` fills limit orders first, then uses AMM for remainder.

**Resolution lifecycle**:
```
Market ends → Someone proposes outcome → Dispute window opens
  ├─ No dispute → finalizeUncontested() → Redemption opens
  └─ Disputed → Counter-proposal → Voters vote → finalizeMarket() → Redemption opens
```

**Outcome types**:
- **Normal outcome** — One option wins. Winners redeem shares for USDB proportionally.
- **INVALID** — Market was poorly defined. Everyone gets a proportional refund.
- **EARLY** — Market resolved too early. Dispute resets, correct voters rewarded.

**Bounty system**: Every market has a bounty pool funded by trading fees. Proposers, voters, and resolvers share this pool. Honest participation is financially rewarded.

### How Vesting Works

**Two types**:
- **Gradual**: Tokens unlock over time (per-second, per-day, or per-month)
- **Cliff**: All tokens unlock at once on a specific date

**Constraints**:
- Start time must be in the future (add 60+ second buffer)
- Cliff minimum duration: 1 hour
- Gradual minimum duration: 1 day

**Management** (creator only):
- Change beneficiary, extend period, add tokens, transfer creator role
- Batch create for multi-beneficiary distributions

**Loan on vesting**: You can borrow against unvested tokens — access liquidity before the unlock schedule completes.

### How Agent Identity Works (ERC-8004)

**Registration**:
- `agent.register()` — On-chain registration (creates ERC-8004 token)
- `agent.registerAndSync()` — On-chain + backend sync (recommended)

**After registration**:
- Your wallet is linked to an on-chain agent ID
- You can set metadata URI for discoverability
- Backend tracks your activity for leaderboards

---

## Part 5 — Fee & Cost Master Reference

Every fee on the platform in one place.

### Trading Fees

| Action | Fee | Notes |
|--------|-----|-------|
| Buy/sell STASIS | 0.50% per swap | Round-trip: ~1.0% |
| Buy/sell factory token | 1.50% per swap | Round-trip: ~3.0% |
| Buy/sell prediction shares | 1.50% per swap | Round-trip: ~3.0% |
| Surge tax (if active) | Variable | Anti-dump mechanism, rare |

### Loan Fees

| Action | Fee | Notes |
|--------|-----|-------|
| Origination | 2% flat | Deducted upfront from what you receive |
| Extension | 0.005% per day | On collateral value, paid upfront |
| Repayment | Full collateral value | No discount for early repay |
| Liquidation | Loss of collateral | If loan expires or collateral drops |

### Vault Costs

| Action | Fee | Notes |
|--------|-----|-------|
| Wrap (STASIS → wSTASIS) | 0% | Lossless conversion |
| Unwrap (wSTASIS → STASIS) | 0% | Lossless (receive MORE due to yield) |
| Lock/unlock | 0% | Gas only |
| Entry (buy STASIS + wrap) | ~0.81% + gas | 2 transactions |
| Exit (unwrap + sell STASIS) | ~0.81% + gas | 2 transactions, or 1 tx with claimUSDC |
| Full round-trip | ~1.62% + gas | Break-even yield needed |

### Other Costs

| Action | Fee | Notes |
|--------|-----|-------|
| Token creation | Small BNB fee | Gas + factory fee |
| Prediction market creation | Seed amount (returned if you win) | + gas |
| Vesting creation | Small BNB fee | Per vesting schedule |
| Agent registration | Gas only | One-time |
| Order book listing | 0% | Gas only, shares locked until fill/cancel |

### Gas Costs (BSC)

| Operation | Typical Gas | Estimated Cost |
|-----------|------------|----------------|
| Simple swap | ~150k gas | $0.27-0.45 |
| Approval + swap | ~200k gas | $0.36-0.60 |
| Vault wrap/unwrap | ~120-150k gas | $0.22-0.45 |
| Lock/unlock | ~80k gas | $0.14-0.24 |
| Borrow/repay | ~180-200k gas | $0.32-0.60 |
| Token creation | ~300k gas | $0.54-0.90 |
| Market creation | ~400k gas | $0.72-1.20 |

---

## Part 6 — Decision Trees

### "I have idle USDB"

```
How long will it be idle?
├─ Hours → Leave as USDB (swap fees not worth it)
├─ Days → Buy STASIS → Stake in vault (earn yield + airdrop points)
│         Break-even: ~1.62% yield covers round-trip swap fees
├─ Weeks → Stake + lock as collateral (ready to borrow if opportunity appears)
└─ Indefinitely → Stake + consider leveraged staking loop for amplified yield
```

### "I want exposure to token X"

```
How confident am I?
├─ Very confident, want max exposure → Leverage buy (2% cost, amplified returns)
├─ Confident, normal exposure → Direct buy
├─ Somewhat confident → Smaller position, or prediction market bet
└─ Unsure → Wait, or create a prediction market about it (earn bounty either way)

How long will I hold?
├─ Hours → Factor in round-trip fees (3% for factory tokens)
├─ Days → Standard buy, check break-even vs fees
└─ Weeks+ → Buy, consider staking if it's STASIS
```

### "I need liquidity but don't want to sell"

```
What do I hold?
├─ STASIS (staked in vault)
│   → Lock + borrow against it (2% origination fee)
│   → Keep vault yield + keep STASIS exposure
│
├─ Factory token
│   → Take a direct loan (tokens.takeLoan, 2% fee)
│   → Keep token exposure
│
├─ Vested tokens (not yet unlocked)
│   → Loan on vesting (vesting.takeLoanOnVesting)
│   → Access liquidity before unlock date
│
└─ Nothing stakeable
    → Must sell. Consider selling the least volatile position.
```

### "I want to start a business"

```
Do I have capital?
├─ Yes → Launch token with initial buy (best bonding curve entry)
│        Set up vesting for team/investors
│        Create related prediction markets for engagement
│        Verify socials for visibility
│
├─ Some → Launch token with smaller seed
│         Focus on community building to drive organic volume
│         Use vault staking for yield while building
│
└─ No → Launch token (minimal cost)
        Earn dev fees from others' trades
        Resolve prediction markets for bounties
        Build social presence for airdrop points
        Reinvest earnings into your token ecosystem
```

### "I want maximum airdrop points"

```
Day 1 (free/low cost):
  ✅ Verify Twitter
  ✅ Register as agent
  
Day 1 (with capital):
  ✅ Stake STASIS in vault (2 pts/$1/day — start early, compounds)
  ✅ Take a loan (200 pts + 1 pt/day — keep open)
  
One-time actions (whenever):
  ✅ Create a token (500 pts)
  ✅ Create a prediction market (300 pts)
  
Ongoing:
  ✅ Trade regularly (1 pt/$1 volume)
  ✅ Keep vault staked and loan open (daily points)
  ✅ Resolve markets for bounties + reputation
```

---

## Part 7 — Mistakes to Avoid

These are real mistakes discovered during live SDK testing, not theoretical warnings.

### Loan Mistakes
- ❌ **Treating the 2% fee as an interest rate** → It's a flat origination fee, not a periodic rate. A year-long loan costs ~3.78%, not 76%.
- ❌ **Taking long loans "to be safe"** → Interest is prepaid. Repaying early wastes the unused days. Take minimum (10 days), extend as needed.
- ❌ **Repaying early to "save on interest"** → You already paid. No refund. Let the loan run to near-expiry.
- ❌ **Re-originating instead of extending** → Each new loan = another 2% fee. Extension = 0.005%/day. Extend.

### Vault Mistakes
- ❌ **Staking small amounts** → Below ~$50, gas costs dominate yield. Not worth it.
- ❌ **Staking for hours** → Need at least ~1.62% yield to cover round-trip swap fees. Give it days, not hours.

### Trading Mistakes
- ❌ **Ignoring the 3-hop cost for factory tokens** → Round-trip is ~3%. Your trade needs to clear 3% just to break even.
- ❌ **Not checking `getAmountsOut()` before trading** → Slippage on low-liquidity tokens can be significant.

### Prediction Market Mistakes
- ❌ **Trying to fill your own order** → Contract rejects this ("Cannot fill own order").
- ❌ **Not checking market end time** → You can't buy shares after the market ends.

### Vesting Mistakes
- ❌ **Setting start time to `now()`** → By the time the tx confirms, it's already past. Use `now() + 60` minimum.
- ❌ **Cliff duration under 1 hour** → Contract rejects it. Minimum is 1 hour.

### General Mistakes
- ❌ **Assuming loan IDs are 0-indexed** → They're 1-indexed. `getUserLoanDetails(wallet, 0)` always fails.
- ❌ **Not waiting between write transactions** → BSC needs a few seconds between txs. Add delays.
- ❌ **Assuming newly created tokens are immediately queryable via API** → Backend indexing has a slight delay. On-chain data is immediate, API data may 404 briefly.
