# Prediction Marketplace

## Introducing Predict+

Predict+ token technology combines the excitement of event-based markets with the stability of investment-grade assets. Unlike traditional platforms that force users into binary win-or-lose scenarios, Predict+ creates a comprehensive prediction economy where participants can invest, trade, borrow, and bet—all within the same market, backed by Basis's Stable+ price protection technology.

{% hint style="info" %}
**Critical distinction:** Each prediction market has **one Predict+ token** that represents the market itself — not individual outcomes. Buying the token is separate from betting on outcomes. The token trades on the DEX; betting happens through a separate USDC pool.
{% endhint %}

### The Problem with Traditional Prediction Markets

#### Centralization Creates Systemic Risk

Traditional prediction markets face fundamental challenges that limit their potential and accessibility. Centralized platforms like Polymarket suffer from regulatory vulnerabilities, geographic restrictions, and single points of failure. These platforms control event creation, resolution, and fund custody, creating trust issues that deter mainstream adoption. When platforms can be shut down, censored, or manipulated, users rightfully hesitate to commit significant capital.

#### Capped Payouts Reduce Upside

Conventional prediction markets cap payouts at $1 per share. On Basis, winners split the **entire** losing pool — payouts are uncapped. In multi-outcome markets (elections, tournaments, price brackets), this produces dramatically higher payouts for correct underdogs. More outcomes = bigger edge vs. traditional platforms.

#### Binary Outcomes Limit Participation

The biggest limitation of current prediction markets is their binary nature—you either win everything or lose everything. This all-or-nothing approach excludes conservative investors, limits market depth, and creates unnecessary volatility. Participants who believe in an event's popularity but are uncertain about its outcome have no way to profit from their insight. Predict+ solves this by separating token investment from outcome betting.

### The Predict+ Solution: One Token Per Market

#### One Token Per Market — Not One Per Outcome

Each prediction market launches with a **single Predict+ token** (Stable+ type) that represents the market itself. This token trades freely on the DEX for price appreciation through slippage retention mechanics — the same up-only mechanism as all Stable+ tokens. Betting on specific outcomes happens through a **separate USDC betting pool**.

#### Four Ways to Participate in Every Event

The separation of token trading and outcome betting creates unprecedented flexibility:

1. **Hold for appreciation:** The Predict+ token can only go up in price as trading volume generates slippage retention — invest in event popularity without gambling on outcomes
2. **Trade on the DEX:** Buy and sell the token to capture volatility from news and sentiment shifts
3. **Use as collateral:** Take 100% LTV loans against your Predict+ tokens without selling your position
4. **Bet on outcomes:** Traditional prediction betting with USDC payouts through the separate betting pool — winners split the entire losing pool (uncapped)

#### Permissionless Event Creation

Unlike centralized platforms that restrict who can create markets, Predict+ empowers anyone to launch prediction events through a decentralized, permissionless system. Creators describe their event and potential outcomes (minimum 2, mutually exclusive), and let the community fund it. Event creators earn 20% of all trading fees on their event's Predict+ token in perpetuity.

### How Predict+ Works

#### Event Creation

**Step 1 — Event Basics:** Event name, symbol, icon, description, optional end date, at least 2 mutually exclusive answers, and optional social links.

**Step 2 — Tokenomics & Resolution:**
* Bonding Phase USDC target ($0–$150,000 — predictions can skip bonding entirely)
* Optional Freeze Token for whitelist-only initial access
* Resolution Style: **Basis Managed** (community votes via Basis Voting Army, disputes allowed) or **Creator Managed** (creator or up to 10 voter wallets, majority vote, no disputes)
* Event Type (Creator Managed only): **Public** or **Private** (whitelisted wallets only for betting; token buying open to all)

**Step 3 — Review & Launch**

Starting liquidity is currently fixed at $1,000 for all predictions.

### The Bonding Phase: Optional Early Access Period

Creators can choose to implement an optional bonding phase that serves as a freeze period for early token purchases before public trading begins. When enabled, this phase allows creators to purchase initial tokens themselves or conduct whitelisted presales to specific wallets at starting bonding curve prices. Participants who buy during this optional phase benefit from better pricing and earn perpetual reward shares (3.33% of all future trading fees). Creators who prefer immediate public access can skip the bonding phase entirely for a fair launch where anyone can purchase tokens right away.

### The Betting Interface

The prediction event page provides:

* **Total Pot** — cumulative USDC from all bets
* **Total Bounty** — trader-to-bettor pot (a portion of Predict+ trading fees that supplements the winning pool)
* **"Visit Trading Page"** link — the token's DEX page (separate from betting)
* **Market Chart** tab — Implied Probability History (colored lines per outcome, 0-100%)
* **Resolution Status** tab — Three-phase progress: Trading (T) → Resolution (🔨) → Resolved (R)
* **Discussion** tab — Wallet-signed comments (requires at least 1 trade ≥ $5 on that market to post)

### Betting Mechanics

**How betting works:**

1. Each outcome has a share price starting at equal split (e.g., 2 outcomes = $0.50 each, 3 outcomes = $0.33 each)
2. Betting = buying shares in an outcome at current price using USDC
3. As shares are purchased for one outcome, its price/probability rises and others fall
4. When resolved: winning outcome shareholders split the total pot (all losing stakes + bounty) proportionally
5. Payout = (Your Winning Shares / Total Winning Shares) × Total Prize Pool

**Share price range:** $0.001 to $0.999 — can never reach $1.00 (certainty has no risk premium).

**Selling Shares (Order Book):**

* **Market (Best):** Lists at current market price — queued until a buyer matches (not instant)
* **Limit (Custom):** Set custom price per share ($0.001–$0.999) — fills when price reached
* **Underwater matching:** The buyer sees a simple "Buy" UI; the system routes to the best source (existing sell orders first if cheaper, then the pool)

This lets participants exit positions before resolution by selling when probability shifts favorably.

### The Trader-to-Bettor Pot

A portion of Predict+ token trading fees flows into a general pot that always pays out to the winning outcome. This creates a symbiotic loop:

More token traders → bigger bounty pot → attracts more bettors → more market excitement → more token traders

This pot supplements the winning pool without affecting any outcome's token price.

### Smart Contract Infrastructure

The technical foundation of Predict+ leverages audited smart contracts deployed on BNB Chain, ensuring transparency and security. Each event's smart contract manages the betting pool mechanics, where odds adjust dynamically based on betting volume. Anti-manipulation mechanisms protect market integrity.

### Resolution and Payouts

#### Basis Managed Resolution

For Basis-created or community markets:
1. Creator or community members propose an outcome
2. Community resolvers post bonds (Bounty Pool × 10)
3. 2-hour dispute window allows challenges by posting equal bonds and proposing alternatives
4. Disputes trigger Basis Voting Army arbitration (24 hours for time-based events, 48 hours for non-time events)
5. Successful resolvers receive the bounty pool; failed disputants forfeit bonds to the Basis Army
6. Invalid markets trigger full refunds with bounty pool distributed to voting Army members

#### Creator Managed Resolution

1. Voting available **immediately** — runs simultaneously with trading
2. Creator votes to resolve (no bond required), or up to 10 whitelisted voter wallets decide by majority
3. Resolution is **final** — no dispute process
4. "Invalid / Ambiguous" option available — triggers full refund to all bettors

#### Payouts

Winners claim their USDC payouts through the dApp with **no time limit**, receiving their proportional share of all losing stakes plus the trader-to-bettor bounty.

**Post-resolution selling dynamic:** After resolution, holders sell Predict+ tokens → tokens are burned → selling fees inject into liquidity → price goes UP during sell waves. Patient holders who wait through the sell frenzy exit at a **higher** price than those who sell first.

## The Competitive Advantage

### Superior to Polymarket's Centralized Model

While Polymarket proved the massive demand for prediction markets with $3.2 billion in election volume, their centralized model creates vulnerabilities that Predict+ eliminates. Basis's decentralized architecture means no geographic restrictions, no regulatory shutdown risk, and no centralized control over events or resolutions. Critically, Predict+ offers uncapped payouts (winners split entire losing pool) vs. Polymarket's $1/share cap — making multi-outcome markets dramatically more rewarding.

### Beyond Traditional Limitations

Predict+ eliminates traditional prediction market issues through its innovative liquidity model where tokens are minted on demand with dynamic supply. There's no idle capital sitting in pools, no impermanent loss for liquidity providers, and no ability for whales to manipulate through sandwich attacks. The MEV-resistant architecture and internal liquidity mechanisms create a fairer, more efficient market.

### Stable Backing Changes Everything

The integration with Basis's Stable+ technology fundamentally transforms prediction market economics. Predict+ tokens maintain their floor price regardless of broader market conditions, meaning participants only need to evaluate event-specific risks rather than systemic crypto risks. This expands the addressable market to include investors and mainstream users who previously avoided prediction markets due to volatility concerns.

## Revenue Model and Distribution

### Trading Fees

Predict+ token trading fee: **1.5%** on buys and sells (platform-set).

### Fee Distribution

* Event creator: 20% of trading fees (perpetual)
* Bonding phase participants: 3.33% (perpetual, if bonding phase used)
* A portion flows to the trader-to-bettor bounty pot
* Remainder follows standard fee waterfall → STASIS Vault → Platform Revenue → 90% to BASIS Vault stakers as USDC

### The Volume Multiplier Effect

The separation of token trading and outcome betting creates multiple revenue streams from each event. Trading volume generates fees as investors buy and sell tokens based on event sentiment. Betting volume creates activity as participants stake on outcomes. Lending activity produces fees when token holders use their positions as collateral. This multiplication of use cases means each successful event can generate significantly more fee revenue than traditional single-purpose prediction markets.

### Discussion Tab

Each prediction market includes a **wallet-signed discussion** feature:

* Comments are cryptographically tied to wallet addresses
* Requires at least 1 trade ≥ $5 on that market to comment (anti-spam gate)
* **"CREATOR" badge** shown on creator's comments
* Creator can delete comments (moderation)
* Timestamped with truncated wallet address display
