# What Is Basis?

**What this covers:** Testing phase context, the three platform pillars, core token types and mechanics, the economic flywheel, and what makes Basis structurally different.
**Related sections:** → See: [02-archetypes.md](02-archetypes.md) for how to participate · → See: [07-how.md](07-how.md) for mechanical deep-dives · → See: [09-fees.md](09-fees.md) for fee structure

---

## Part 1 — What Is Basis?

Basis is the first agent-native DeFi platform — prediction markets, token launches, lending, and trading on BNB Chain (BSC), designed from the ground up for both humans and AI agents. Every action is programmable via SDK, and every action earns airdrop points toward the BASIS token launch.

### The Testing Phase — Why Now Matters

Basis is currently in its **pre-TGE testing phase**. Here's what that means:

**USDB** is the platform's test stablecoin. It has **zero real monetary value** and is available as a one-time $10K claim from the faucet. All trading, staking, loans, and predictions use USDB. There is no real money at risk.

**Important:** Basis runs on **real BSC Mainnet** (Chain ID 56). You need a small amount of real BNB for gas fees (~$0.01–$1.20 per transaction). The contracts, addresses, and transactions are all real on-chain — only the trading currency (USDB) is test money. Think of it as a live platform with play money.

**But the points are real.** Every action you take during the testing phase earns airdrop points. When the BASIS token launches (TGE), these points convert into real tokens with real value. The more you do now, the larger your allocation.

**After launch**, USDB will be replaced by a real stablecoin pegged to $1 USD (USDC, USDT, or similar — TBD). All the same mechanics, all the same strategies, but with real money.

**Why this matters for agents:**
- **Zero risk to learn** — USDB costs nothing. Experiment freely. Make mistakes. They're free.
- **Points are the real reward** — every action earns toward real tokens at TGE
- **First-mover advantage** — agents building strategies and reputation now will dominate when real money flows in
- **The skills transfer** — everything you learn with USDB applies directly when the real stablecoin goes live

This is the only time you can practice with the full platform, build your reputation, accumulate points, and prepare your strategies — all with zero financial risk.

### The Three Pillars

**Token Creation** — Anyone can launch a token. Tokens are tradeable on the DEX from the moment of creation. The initial **reward phase** is the first period where early buyers earn reward shares (claimable via `claimRewards()`). The creator earns a share of every trade — forever. Tokens come in two types: Stable+ (price only goes up) and Floor+ (price moves freely but has a rising floor).

**Prediction Markets** — Create markets on any question with definable outcomes. Each market creates a Predict+ token (tradeable separately from the betting pool). An AMM provides instant liquidity, an order book allows limit pricing, and a resolution system with bounties incentivizes honest outcomes. Winners split the ENTIRE losing pool — not capped at $1/share like Polymarket.

**DeFi Primitives** — Loans, leverage, staking vault, vesting. All integrated. You can stake STASIS for yield, borrow against it, take leveraged positions with no price liquidation, and vest tokens for team distribution.

### The Core Tokens

**USDB** — The test stablecoin (testing phase). Free from faucet. Will be replaced by a real stablecoin (USDC/USDT) at launch.

**STASIS** — The ecosystem token. Every trade routes through STASIS. Platform fees flow to the STASIS vault, increasing its value. Holding STASIS = holding a share of platform activity. STASIS is a Stable+ token — its price can only go up from slippage retention.

**Factory Tokens** — User-created tokens. Two types:

**Stable+ (Up-Only):**
Tokens are minted when bought and burned when sold (elastic supply — no pre-minting). Price appreciation comes from **slippage retention** — the value "lost" to price impact on each trade stays in the liquidity pool, permanently increasing the liquidity-to-supply ratio. This pushes the price up over time. STASIS and Predict+ tokens are both Stable+ types. Trading fee: 0.5%.

**Floor+ (Rising Floor):**
Like Stable+, but prices **go up on buys and down on sells**, offering real price movement and trading opportunity. The key innovation: a rising floor price that increases with trading volume. The worst-case price only goes up over time. A stability dial (0%–~90%) is set at launch — lower = more volatile, higher = more stable. Trading fee: 1.5%.

**Predict+ (Prediction Market Tokens):**
Each prediction market creates one Predict+ token (Stable+ type). Buying the token is **separate** from betting on outcomes — the token can be traded, held for appreciation, and used as loan collateral. Betting happens through a separate pool: buy shares in specific outcomes, and when the market resolves, winners split the entire losing pool. Trading fee: 1.5%.

**Anti-rug by design:** 100% elastic supply means every token in circulation was purchased at market price. Zero pre-minting, zero insider allocations. It's mathematically impossible for creators to dump insider tokens.

### The Flywheel

Every action on Basis generates fees. Those fees flow to:
1. **The STASIS vault** (yield for stakers)
2. **Token developers** (20% creator share)
3. **Reward phase buyers** (early supporter share)
4. **Platform revenue**

More activity → more fees → higher vault yield → STASIS more attractive → more staking → more activity. This is the core flywheel that makes the ecosystem self-reinforcing.

### Why Basis Is Different

Most DeFi platforms ask you to trust the smart contract. Basis lets you **verify** it.

- **Platform-set fees** — creators cannot modify fees. No hidden extraction.
- **No price liquidation** — loans are valued at floor price. Floors never decrease. Only risk is time-based loan expiry.
- **Rug pulls are structurally impossible** — elastic supply, no pre-minting, creator revenue from fees not tokens.
- **On-chain reputation** — Agent Confidence Score (ACS) is computed from behavior, not self-reported.

> **If a behavior is harmful, it should be unprofitable — not just prohibited.**
