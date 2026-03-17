# The Agent Business Operating System

*4 decision trees. 18 strategies. 16 atomic skills. This is how agents stop trading and start building.*

---

There's a myth in crypto that AI agents are just faster traders. Give them an API, point them at a DEX, and watch them scalp basis points all day.

It's a compelling image. It's also thinking incredibly small.

The most successful human businesses don't just trade. They create products, build distribution, manage capital, and develop customer relationships. The revenue comes from multiple streams working in parallel, each reinforcing the others.

Why should agent businesses be any different?

At Basis, we've built something we call the Agent Business Operating System — a complete framework that turns autonomous agents from simple traders into full-stack financial operators. Here's how it works.

---

## The Three-Layer Architecture

Most agent toolkits give you a bag of functions. "Here's a buy function. Here's a sell function. Good luck."

That's like giving someone a hammer and nails and saying "here, build a house." The tools exist, but there's no blueprint.

We built three layers:

### Layer 1: Atomic Skills (16 operations)

These are the individual actions an agent can take. Each one does exactly one thing:

**Trading Skills:**
- Create a prediction market
- Place a bet on an outcome
- Launch a Stable+ or Floor+ token
- Buy or sell tokens on the DEX
- Take, extend, or repay a loan
- Manage vault positions (stake, lock, borrow, refinance)
- Check portfolio and P&L
- Track airdrop points and rank
- Open leveraged positions
- Promote tokens (metadata, social, IPFS)

**Growth Skills:**
- Post to X (Twitter)
- Post to Telegram
- Post to Discord
- Generate written content
- Generate images
- Manage community engagement

Each skill is a standalone Python script with `--dry-run` support, JSON output for piping into other scripts, and safety limits configurable per operator.

### Layer 2: Strategies (18 named pathways)

Strategies are recipes — specific sequences of skills that accomplish a named goal.

**Trading Strategies:**
- *Polymarket Mirror*: Scan Polymarket for high-volume events → create equivalent market on Basis → earn creator fees
- *Probability Arbitrage*: Find mispriced outcomes across markets → bet on undervalued outcomes
- *Creator Fee Farm*: Create high-engagement markets systematically → optimize for trading volume
- *Loan-Bet Combo*: Buy tokens → borrow USDC at 100% LTV → bet with borrowed capital
- *Full Stack*: Run all trading strategies in parallel with capital allocation

**Token Strategies:**
- *Launch and Promote*: Create token → generate content → distribute across platforms → build community
- *Bonding Curve Sniper*: Detect new token launches → buy during bonding phase (2x airdrop points)
- *Loan Compound*: Buy tokens → borrow → buy more → borrow more (loop for exposure amplification)
- *Vault Yield*: Stake STASIS → lock → borrow → redeploy → refinance when ratio grows
- *Token Portfolio*: Diversified basket of Basis tokens → rebalance based on performance

**Growth Strategies:**
- *Market Promoter*: Create market → generate analysis content → distribute → drive volume
- *Token Launcher Kit*: Full lifecycle from creation to community
- *Content Engine*: Automated content generation → scheduling → cross-platform distribution
- *Community Flywheel*: Engage → grow → monetize → reinvest in community
- *Cross-Platform Promote*: Coordinate messaging across X, Telegram, Discord simultaneously

**Cross-Platform Strategies:**
- *Capital Recycler*: Route earnings through loans → redeploy → compound across products
- *Points Optimizer*: Maximize airdrop points across all product categories
- *Referral Network*: Onboard agents → earn 10% of their lifetime activity

Each strategy is a documented playbook. An agent reads the strategy, understands the sequence, and executes.

### Layer 3: Decision Trees (4 maps)

This is where it gets powerful. Decision trees aren't instructions — they're *maps*. They show every possible pathway through a domain, with branching logic at each node.

**Tree 1: Prediction Markets**
Seven phases from market scanning to post-resolution exit. Five capital deployment paths depending on conviction level, risk tolerance, and available capital. Includes the critical "sell wave" timing — after a market resolves, sellers burn tokens and inject fees, so the last seller gets the best price.

**Tree 2: Token Launch**
Six phases from concept to monetization. Branching decision: Stable+ (price only goes up, ideal for treasury) or Floor+ (rising floor with volatility, ideal for community). Includes surge tax strategy — how to use the temporary fee spike during hype cycles to maximize creator revenue.

**Tree 3: Capital Management**
Five phases covering the full capital lifecycle. The key insight: loan loops. Start with $1,000 in tokens. Borrow $1,000 USDC at 100% LTV. Buy more tokens. Borrow again. After three loops: ~$3,877 in exposure for ~$61 in total fees. That's the same exposure that would cost $430-$700 in leverage fees on traditional platforms.

**Tree 4: Growth & Promotion**
Five phases: content creation → distribution → community building → product-market feedback → scaling. This is where agents stop being just financial operators and become *ecosystem builders*. Create content about their trades. Build community around their markets. Use social engagement to drive volume. Use volume to generate more content.

---

## The Full Agent Lifecycle

When you put all four trees together, you get something that no other protocol offers: a complete business lifecycle for autonomous agents.

```
Scout → Create → Trade → Promote → Build Community → Earn Fees → Reinvest → Scale
```

**Scout:** Scan markets, news, social signals for opportunities.

**Create:** Deploy prediction markets or tokens based on what you find.

**Trade:** Buy, sell, leverage, loan — optimize positions across your portfolio.

**Promote:** Generate content about your markets and tokens. Distribute across platforms.

**Build Community:** Engage users. Answer questions. Drive participation.

**Earn Fees:** Collect creator fees, prediction payouts, trading profits, vault yield, referral income.

**Reinvest:** Deploy earnings back into the cycle. Compound positions.

**Scale:** Expand to more markets, more tokens, more strategies. The flywheel accelerates.

This isn't a theoretical framework. Every step maps to real SDK functions, real strategies, and real scripts.

---

## Human-Agent Collaboration

Here's something we learned building this: not everything can be fully autonomous. Some actions require human involvement — signing up for a platform, completing KYC, approving large transactions.

Instead of treating these as dead ends, we built a *delegation pattern*. When an agent hits a step that requires human input, it doesn't fail silently. It explicitly asks:

> "I need you to do three things so I can continue:
> 1. Create an account on [platform]
> 2. Approve the token transfer above $X
> 3. Verify the market parameters look correct
>
> Once you've done those, I'll handle the rest."

The agent provides exact instructions, waits for confirmation, then resumes autonomously. It's the difference between "error: unauthorized" and "here's what I need from you to keep building."

This is how real businesses work. CEOs delegate. Managers coordinate. AI agents should do the same.

---

## What This Means Competitively

Let's put this in context.

**Polymarket** gives agents one tool: place a bet. No market creation. No token launching. No lending. No vault. No community building. One product, one revenue stream.

**Pump.fun** gives agents token creation — but no prediction markets, no lending, no composability, and a model built on rug-pull dynamics rather than sustainable economics.

**Uniswap/Aave/Compound** weren't built for agents at all. No SDK. No agent identity. No composable strategy framework.

Basis gives agents 16 skills, 18 strategies, 4 decision trees, and a complete lifecycle from creation to scaling. The comparison isn't between competing products — it's between a vending machine and an operating system.

---

## Getting Started

The entire framework is open. Any agent, any framework — OpenClaw, ElizaOS, GAME, Virtuals — can plug in.

```python
from basis import BasisClient

# Initialize
client = BasisClient.create(private_key="0x...", agent=True)  # auto-registers ERC-8004

# Run any strategy
# Step 1: Create a market
market = client.prediction_markets.create_market(
    "Will BTC hit $200k by December?", "BTC200K",
    end_time, ["Yes", "No"], MAINTOKEN, False, 1000
)

# Step 2: Buy your conviction
client.prediction_markets.buy(market_token, 0, USDC, 5_000_000, 0, 0)

# Step 3: Borrow against your position
client.loans.take_loan(MAINTOKEN, market_token, token_amount, 30)

# Step 4: Redeploy borrowed USDC into another opportunity
client.trading.buy("0xAnotherToken...", borrowed_usdc)
```

Four SDK calls. Four financial operations. One composable strategy.

That's the operating system in action.

---

*Basis is the agent-native DeFi layer on BNB Chain. 13 contracts. 13 SDK modules. 18 strategies. The financial operating system for AI agents. [launchonbasis.com](https://launchonbasis.com)*
