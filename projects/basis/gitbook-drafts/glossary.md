# Glossary

## Basis Comprehensive Glossary <a href="#docs-internal-guid-3c15106c-7fff-4d50-cdde-b91ddd078551" id="docs-internal-guid-3c15106c-7fff-4d50-cdde-b91ddd078551"></a>

{% hint style="info" %}
This glossary provides definitions for all key terms and concepts used throughout the Basis ecosystem, organized by category to assist readers in understanding the technical, operational, and economic aspects of the platform.
{% endhint %}

***

### Core Platform Terms

**STASIS:** The native liquidity pair token of the Basis ecosystem, implemented as a Stable+ token initially paired with USDC. STASIS serves as the primary liquidity pair for all other Basis Tokens launched through the Token Factory. It appreciates slowly through slippage retention driven by ecosystem-wide trading volume.

**Basis Token:** Any token created using the Basis Token Factory, including Stable+, Floor+, and Predict+ variants. All Basis Tokens have 100% elastic supply (minted on buy, burned on sell), start at $1.00, and are ERC-20 compatible.

**Basis Ecosystem:** The permissionless DeFi platform consisting of four interconnected components: Token Launchpad, Predict+ Marketplace, Lending Facility, and Decentralized Exchange (DEX), where success anywhere benefits all participants through structured fee distribution.

**DEX (Decentralized Exchange):** Basis's native decentralized exchange serving as the exclusive marketplace for all Basis Tokens. Features MEV-resistant architecture, internal liquidity mechanisms, and dynamic leverage up to 36x with no liquidation risk for Stable+ tokens. Trading fees vary by token type: Stable+ 0.5%, Floor+ 1.5%, Predict+ 1.5%.

**Token Factory/Token Launchpad:** A permissionless, no-code platform allowing anyone to create branded tokens with either Stable+ (up-only) or Floor+ (rising floor) mechanics. All tokens start at $1.00 with creator-configurable starting liquidity ($100–$10,000). Gas fees only (~$0.14 BNB on BNB Chain).

**Cascading Growth Effect:** The ecosystem-wide phenomenon where STASIS appreciation (through slippage retention from platform-wide trading volume) directly increases the value of all tokens paired against it, creating compound benefits even for inactive tokens due to the universal STASIS pairing requirement.

**Fee Waterfall:** The structured distribution path for trading fees: Trading Fee → Creator (20%) → Bonding phase buyers (3.33%) → STASIS Vault (portion) → Platform Revenue (remainder) → 90% to BASIS Vault stakers as USDC + 10% platform operations.

***

### Token Framework Terms

#### Stable+ Technology

**Stable+:** "Up-only" token framework where smart contract mechanics guarantee the token price can only increase or maintain value, never decrease from any previously achieved level.

**Slippage Retention:** The core mechanism behind Stable+ appreciation. When someone buys or sells, the price impact (slippage) stays in the liquidity pool, increasing the liquidity-to-supply ratio. This is NOT fee injection — trading fees are distributed separately to creators, bonding participants, and the platform.

**Liquidity-to-Supply Ratio:** The relationship between liquidity depth and circulating supply in a Stable+ pool. As slippage is retained, this ratio increases, producing gradual price appreciation. The effect is strongest at low supply and diminishes at scale. Active circulation (buy → use → sell → buy) is needed for meaningful appreciation.

**Mathematical Certainty:** The guarantee that Stable+ price protection isn't a promise but programmed impossibility enforced by immutable smart contract code.

**Stable+ Applications:** Ideal for utility tokens, branded stablecoins, access passes, e-commerce payments, event tickets, corporate tokens, employee rewards, community governance, loyalty programs, and any use case requiring absolute downside protection with growth potential.

#### Floor+ Technology

**Floor+:** "Rising floor" token framework featuring 100% liquidity backing at the floor price, allowing normal market volatility and price discovery above a mathematically enforced minimum that only increases over time. Price goes up on buys and down on sells — unlike Stable+ which is up-only.

**Rising Floor Mechanism:** The smart contract feature where trading activity continuously raises the floor price, creating a one-way ratchet effect upward while allowing dynamic trading above this rising minimum.

**Stability Dial:** A creator-configurable setting (0% to 100%) that controls how volatile a Floor+ token is. 0% = most volatile (largest price movements per trade), 100% = most stable. Set at creation and **immutable** — cannot be changed after launch.

**100% Liquidity Backing:** Unlike traditional meme tokens with \~25% backing, every dollar of Floor+ market cap at the floor price is backed by real, accessible liquidity through smart contract architecture.

**Customizable Starting Liquidity:** Creators can set initial liquidity from $100 to $10,000, with lower starting amounts enabling higher multiplier potential (up to 250x with $100 start vs 25x with $1,000).

**Floor+ Use Cases:** Perfect for sustainable community building, ethical fundraising, speculation with safety nets, brand token launches, and projects prioritizing long-term value over quick flips.

#### Predict+ Technology

**Predict+:** Event-specific tokens using Stable+ technology for prediction markets. **One Predict+ token per market** — the token represents the market itself, not individual outcomes.

**One Token Per Market:** Each prediction market has exactly one Predict+ token. Buying the token is separate from betting on outcomes. The token trades on the DEX for price appreciation through slippage retention; betting on specific outcomes uses a separate USDC pool.

**Multi-Utility Design:** Predict+ tokens can be: (1) held for price appreciation as event excitement builds, (2) traded on DEX to capture volatility, (3) used as 100% LTV loan collateral, or (4) held while betting on outcomes through the separate USDC pool for USDC payouts.

**Trader-to-Bettor Pot:** A portion of Predict+ token trading fees that flows into a general pot, always paid out to the winning outcome. Creates a symbiotic loop: more token traders → bigger pot → attracts more bettors → more excitement → more traders.

**Investment-Grade Prediction Assets:** Unlike traditional bet-or-lose models, Predict+ tokens maintain value through Stable+ backing, allowing investors to profit from event hype without gambling on outcomes.

***

### Predict+ Marketplace Terms

**Predict+ Marketplace:** The first decentralized prediction market with stable token technology, where permissionless event creation meets multi-utility tokens that can appreciate but never decrease below their floor price.

**Event Creation:** Completely permissionless system with zero upfront costs, no deposits, and no approval requirements. AI-powered categorization automatically validates events and filters prohibited content. Minimum 2 mutually exclusive answers required.

**Event Creator:** Any user who launches a prediction event at zero cost, earning 20% of all trading fees generated by their event's Predict+ token in perpetuity.

**Event Categories:** Unlimited possibilities including sports championships, political elections, cryptocurrency prices, entertainment awards, economic indicators, product launches, weather events, and social media milestones.

**Bonding Phase (Events):** Optional initial period where creators can purchase tokens or conduct whitelisted presales. No minimum thresholds required — events proceed regardless of bonding amount. Can be skipped entirely for immediate public access.

#### **Betting Mechanics:**

* **Currency Options:** Bet using either Predict+ tokens or USDC directly into the separate betting pool
* **Dynamic Odds:** Share prices adjust based on betting volume
* **Initial Odds:** All outcomes begin with equal odds (e.g., 50/50 for binary events, 33/33/33 for three-way)
* **Share Price Range:** $0.001 to $0.999 — can never reach $1.00 (certainty has no risk premium)
* **Exit Options:** Sell shares before resolution through the order book to lock profits or cut losses
* **Uncapped Payouts:** Winners split the entire losing pool — not capped at $1/share

#### Betting Order Book:

* **Market (Best):** Lists at current market price — queued until next buyer matches (not instant)
* **Limit (Custom):** Set custom price ($0.001–$0.999) — fills when price reached
* **Underwater Matching:** Buyer sees simple "Buy" UI; system routes to best source (sell orders first if cheaper, then pool)

#### Resolution System:

* **Open Resolution:** Creator or any community member can propose an outcome
* **Creator Priority (Basis Managed):** Creator proposes first; community can resolve if creator doesn't
* **Community Resolution:** Anyone can resolve by posting bond (10x the bounty pool)
* **Bounty Pool:** Accumulated fees (portion of transaction volume) paid to successful resolver
* **Dispute Process:** Outcomes can be challenged within 2-hour window by posting equal bond
* **Basis Army Voting:** Final arbitration for disputed outcomes within 24–48 hours
* **Army Compensation:** Basis Army members split forfeited bonds from losing disputants

#### Resolution Timeline:

* **Time-Based Events:** Creator has priority post-expiration, then community can resolve
* **Non-Time Events:** Open for creator or community resolution at any time
* **Dispute Window:** 2 hours for initial challenges
* **Army Voting Period:** 24 hours for time-based, 48 hours for non-time events

**Creator Managed Resolution:** Creator resolves directly (no bond) or up to 10 whitelisted voter wallets decide by majority. Resolution is final — no dispute process.

**Invalid Markets:** Basis Army can declare markets invalid when no clear outcome exists, triggering full refunds to all participants with bounty pool distributed to voting Army members.

#### Fee Structure (Predict+ Trading):

* **Trading Fee:** 1.5% on buys and sells of the Predict+ token (platform-set)
* **Distribution:** Creator (20%), bonding phase buyers (3.33%), trader-to-bettor pot (portion), remainder to platform fee waterfall

**Payout Mechanics:** Winners receive proportional share of losing pools plus trader-to-bettor bounty, calculated as (User's Winning Shares / Total Winning Shares) × Total Prize Pool, claimed through dApp with no time limits.

**Discussion Tab:** Wallet-signed comments on each prediction market. Requires at least 1 trade ≥ $5 on that market (anti-spam). Creator badge displayed on creator's comments. Creator can moderate.

***

### Bonding Phase Terms

**Bonding Phase:** The initial period following any Basis Token creation, lasting until the configured USDC target is reached (up to $150,000), during which early participants earn enhanced perpetual rewards.

**Virtual Liquidity:** The system's notional establishment of trading capability at token creation, enabling immediate trading through bonding curve mechanics before real liquidity accumulates.

**Reward Shares:** Permanent, transferable entitlements earned by bonding phase participants, generating 3.33% of all future transaction fees for that specific token in perpetuity.

**Bonding Curve:** The mathematical formula determining token prices during initial distribution, ensuring fair pricing that increases with each purchase.

**Early Supporter Benefits:**

* Better entry prices through bonding curve
* Perpetual USDC rewards from transaction fees
* No staking or lock-up requirements
* Recognition as founding supporters

**Creator Participation:** Creators can purchase tokens during bonding, earning reward shares while demonstrating commitment without unfair advantages.

***

### Lending Platform Terms

**Lending Facility:** Basis's loan platform offering 100% LTV ratios, zero liquidation risk from price movements, and flexible extension options with cash-out refinancing.

**Loan Terms:**

* **Stable+ Collateral:** Up to 100% LTV based on current market value
* **Floor+ Collateral:** Up to 100% LTV based on floor price (not market price)
* **Loan Currency:** All loans disbursed in USDC
* **Term Length:** 10–1,000 days

**Dynamic Loan Fees:** Fees based on duration: ~2% for 10 days, ~2.2% for 30 days, ~7% for 1,000 days. These are **total fees**, not annualized rates. All interest prepaid upfront — deducted from loan proceeds.

**Cash-Out Refinancing:** Ability to extend loans and receive additional USDC if collateral has appreciated, calculated as new max loan value minus outstanding balance minus applicable fees.

**Loan Stacking:** Strategic ability to chain multiple loans by using borrowed USDC to purchase additional tokens as collateral (requires careful fee consideration).

**Zero Price Liquidation:** Loans cannot be liquidated due to collateral price movements — only from non-payment at maturity.

**Collateral Burned on Expiry:** On non-payment at maturity, collateral is burned (not sold on market), eliminating liquidation cascades. Borrower can claim any excess value above the loan amount.

***

### Economic & Fee Distribution Terms

**Dynamic Supply Mechanism:** Tokens are minted on purchase and burned on sale, creating natural supply elasticity that responds to market demand. All tokens start at $1.00.

**Trading Fees by Token Type (Platform-Set):**

| Token Type | Trading Fee | Creator Share (20%) |
| ---------- | ----------- | ------------------- |
| Stable+    | 0.5%        | 0.1% per trade      |
| Floor+     | 1.5%        | 0.3% per trade      |
| Predict+   | 1.5%        | 0.3% per trade      |

Fees are platform-set — not creator-configurable. Creators control the split of their 20% share (up to 10 wallets via Dev Tax Sharing).

**Fee Waterfall:** Trading Fee → Creator (20%) → Bonding phase buyers (3.33%) → STASIS Vault (portion) → Platform Revenue (remainder) → 90% to BASIS Vault stakers as USDC + 10% platform operations.

**Multiple Revenue Streams:** Creators earn from DEX trading fees (20%), loan fee sharing, bonding phase rewards, and 100% LTV loans — without ever selling tokens. All creator revenue is paid in USDC.

***

### Leverage Terms

**Dynamic Leverage:** Leverage that varies based on current pool liquidity and buy amount. Up to 36x theoretical maximum — not a fixed constant. Smaller buys = higher effective leverage; larger buys = lower effective leverage.

**Leverage Toggle:** Leverage is on/off — not a slider. Effective leverage depends on position size relative to pool liquidity.

**Leverage Fee:** A substantial fee separate from the trading fee, ranging from ~43% to ~70% of collateral depending on buy size and pool state.

**Leverage and Loans — Separate Paths:** Leveraged tokens are held in the leverage contract and **cannot be used as loan collateral**. Leverage and loans cannot be combined on the same tokens.

**Open Position:** Leveraged tokens are held in the leverage contract (not in the user's wallet). Tracked as "Open Positions" in the trading interface.

***

### Launch & Creator Tools Terms

**Fair Launch Guarantee:** Zero pre-minted tokens, zero team allocations, zero insider advantages — creators must purchase tokens through public mechanisms like everyone else.

**Dev Panel:** Post-launch creator control panel with: Unfreeze (one-way, cannot re-freeze), Surge Tax, Dev Tax Sharing, Whitelist Management, and Token Info.

**Surge Tax:** Optional creator-controlled feature that temporarily increases trading fees during hype cycles. 7-day total quota — creator picks strategic moments to activate.

**Dev Tax Sharing:** Creator splits their 20% fee share across up to 10 wallets (1%–100% per wallet, displayed in basis points), configured post-launch.

**Freeze Token:** Toggle that restricts trading to whitelisted wallets only. Unfreeze is one-way — once opened, cannot be re-frozen.

**Auto-Vesting:** Optional automatic vesting for bonding phase purchases. Configurable as cliff or gradual with a customizable period in days.

**Liquid Vesting:** Vested token holders can take floor-price loans against their locked tokens — capital is locked but not idle.

***

### Technical Infrastructure Terms

**Smart Contract Architecture:** Audited, immutable code on BNB Chain ensuring transparency, security, and trustless execution of all platform functions.

**MEV-Resistant Design:** Internal liquidity mechanisms and architectural choices that prevent sandwich attacks, front-running, and other value extraction tactics. Because liquidity is managed by the token's smart contract rather than external pools, common MEV strategies are economically non-viable.

**BNB Chain:** The blockchain Basis operates on. Sub-cent gas fees (<$0.01 per transaction) and fast block times (~3 seconds) make it ideal for high-frequency activity from both humans and AI agents.

**ERC-20 Compatibility:** All Basis Tokens follow the ERC-20 standard for broad wallet and tooling support.

**On-Chain Transparency:** All mechanics, fee distributions, vesting schedules, and token operations fully verifiable on the blockchain.

**Security Measures:**

* Hashlock contract audits
* No hidden mint functions or backdoors
* 100% non-custodial design
* Emergency pause capabilities

***

### Market Dynamics Terms

**Volume Multiplier Effect:** How Predict+'s multi-utility design (hold, trade, collateralize, bet) generates significantly more activity than traditional single-purpose prediction tokens.

**Network Effects:** Self-reinforcing growth where more creators → more users → more liquidity → more fees → better returns → more creators.

**Total Value Locked (TVL):** Aggregate value across all tokens, loans, prediction events, and vault positions in the Basis ecosystem.

**Post-Resolution Sell Dynamic:** After prediction resolution, holders sell Predict+ tokens → tokens burned → selling fees inject into liquidity → price goes UP during sell waves. Patient holders who wait exit at a higher price than those who sell first.

***

### Agent Economy Terms

**Agent Economy:** The positioning of AI agents as first-class participants in the Basis ecosystem, capable of autonomous token creation, trading, lending, and prediction market participation.

**Agent SDK:** The `basis-defi` OpenClaw skill providing structured interfaces for agents to interact with Basis smart contracts, including dry-run mode, gas estimation, and configurable risk parameters.

**Founding Lobsters:** Early-stage agents and operators recruited during the pre-launch phase who receive permanent airdrop multipliers, bonding phase whitelist access, and on-chain badges.

**Moltbook:** A planned lightweight on-chain identity and discovery layer for agents — registry, leaderboard, and reputation scoring based on Basis activity. (Upcoming feature.)

**ACS (Agent Confidence Score):** A behavioral scoring system that weights airdrop distribution based on genuine platform activity, framework attestation, and social engagement.

**BASIS Token:** The platform's utility/governance token (1,000,000,000 total supply). Stakers receive 90% of net platform revenue as USDC through the pure yield model, using a notice-based staking system.

**USDB:** USD Basis — a test stablecoin used during the platform testing phase. Functions identically to USDC within the Basis ecosystem. Points earned during USDB testing carry over to the real airdrop.
