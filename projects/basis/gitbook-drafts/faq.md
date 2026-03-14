# FAQ

## Platform Overview & Core Concepts <a href="#docs-internal-guid-503b2937-7fff-440b-12bc-3e7d82a03b80" id="docs-internal-guid-503b2937-7fff-440b-12bc-3e7d82a03b80"></a>

### 1. What is Basis and how does it work?

Basis is a permissionless DeFi ecosystem consisting of four interconnected components:

* **Token Launchpad:** Create Stable+ (up-only) or Floor+ (rising floor) tokens without coding
* **Predict+ Marketplace:** Decentralized prediction markets with stable token technology — one token per market, with outcome betting handled through a separate USDC pool
* **Lending Facility:** 100% LTV loans with zero liquidation risk from price movements
* **Decentralized Exchange (DEX):** MEV-resistant trading with dynamic leverage (up to 36x depending on liquidity and position size)

Every activity generates fees distributed to creators (20%), early supporters (3.33%), and BASIS stakers (90% of net platform revenue as USDC), creating an ecosystem where all participants benefit from activity anywhere on the platform.

### 2. How do Stable+ "up-only" tokens actually work?

Stable+ tokens appreciate through **slippage retention** — when someone buys or sells, the price impact (slippage) stays in the liquidity pool, increasing the liquidity-to-supply ratio. This creates a ratcheting effect where each new high becomes the permanent minimum.

* **Dynamic Supply:** Tokens are minted when purchased and burned when sold
* **Slippage Retention:** The "lost value" from price impact stays in the pool, ticking the price up over time
* **Strongest at low supply:** The effect is most pronounced at low supply and diminishes as supply grows
* **Active circulation needed:** Buy → use → sell → buy cycles drive appreciation; static holding produces minimal movement

{% hint style="info" %}
**Important:** Trading fees do NOT inject into Stable+ liquidity. Fees go to the Creator (20%), bonding phase buyers, platform revenue, and the wSTASIS vault. Appreciation comes solely from slippage retention.
{% endhint %}

Think of it like a staircase where you can only go up or stay on the same step—never down. This makes Stable+ perfect for e-commerce payments, loyalty programs, corporate tokens, and any use case requiring absolute downside protection with growth potential.

### 3. What are Floor+ "rising floor" tokens?

Floor+ tokens combine the excitement of price discovery with downside protection. Key features:

* **Price goes up on buys, down on sells** — unlike Stable+ which is up-only
* **Rising Floor Protection:** The floor price only increases over time, never decreases
* **Stability Dial:** 0% to ~90% (set at creation, immutable). 0% = most volatile (default). 100% stability would effectively be a Stable+ token, so the Floor+ range caps below that.
* **100% Liquidity Backing:** Unlike traditional meme tokens with \~25% backing, every dollar at floor price is backed by real liquidity
* **Starting Liquidity:** $100 to $10,000, creator-configurable

It's like a bouncing ball in an elevator that only goes up—the ball (price) can bounce, but the elevator floor keeps rising.

## Token Creation & Launch Process

### 4. How do I launch a token on Basis? Do I need coding skills?

No coding knowledge is required. The Token Factory provides a simple, permissionless three-step process:

**Step 1:** Token name, symbol, description, and icon image

**Step 2:** Starting liquidity ($100–$10,000), bonding phase target ($100–$150,000), token type (Stable+ or Floor+), optional freeze and auto-vesting settings

**Step 3:** Review summary → single contract call

**All tokens start at $1.00.** There is no custom initial price. You pay only BNB gas fees (~$0.14). There are ZERO platform fees for token creation.

### 5. What is the bonding phase and how does it reward early supporters?

The bonding phase is the initial period after token creation, lasting until the configured USDC target is reached. During bonding:

* Virtual liquidity enables immediate trading through bonding curve mechanics
* Early buyers earn permanent **Reward Shares** proportional to their purchase
* These shares generate 3.33% of ALL future transaction fees for that token forever
* Selling during bonding incurs penalties to encourage commitment

Benefits include better entry prices, perpetual USDC rewards without staking, and recognition as founding supporters. Creators can also purchase tokens during bonding.

### 6. How does Basis prevent rug pulls and creator dumps?

Basis implements multiple structural safeguards:

**Structural Impossibility:**

* **100% elastic supply** — every token is minted on buy, burned on sell. Zero pre-minting, zero team allocations. Structurally impossible to rug.
* **Creators buy at market price** like everyone else — no hidden wallets, no team tokens

**Sustainable Creator Revenue (no need to dump):**

* 20% of all DEX trading fees forever (paid in USDC)
* Loan fee sharing when their token is used as collateral
* 100% LTV loans to access liquidity without selling

**Mathematical Protection:** Stable+ tokens literally cannot decrease in price, and Floor+ tokens have constantly rising minimum values. Smart contracts make pump-and-dump schemes impossible.

## Predict+ Marketplace

### 7. How does Predict+ work?

Each prediction market has **one Predict+ token** (Stable+ type) that represents the market itself — not individual outcomes. Token trading and outcome betting are completely separate:

* **Token:** Buy/sell the Predict+ token on the DEX for price appreciation (slippage retention drives up-only price)
* **Betting:** Bet on specific outcomes using USDC through a separate betting pool — winners split the **entire** losing pool (uncapped payouts)

**Four ways to participate:**

* **Hold for appreciation:** Token can only go up as trading volume generates slippage retention
* **Trade volatility:** Buy and sell based on news and sentiment shifts
* **Use as collateral:** Get 100% LTV loans without selling your position
* **Bet on outcomes:** USDC payouts from the separate betting pool — uncapped vs. Polymarket's $1/share cap

### 8. How do I create and participate in prediction events?

**Creating Events (Permissionless, Zero Upfront Costs):**

* Connect wallet and describe event with at least 2 mutually exclusive answers
* Set bonding phase target ($0–$150,000), resolution style (Basis Managed or Creator Managed), and event type (Public or Private)
* AI automatically validates and categorizes

**Participating:**

* Buy Predict+ tokens during bonding or after for price appreciation
* Bet on outcomes with USDC through the separate betting pool
* Sell shares before resolution to lock profits
* Claim USDC payouts when events resolve — no time limit

### 9. How does event resolution work?

**Basis Managed:**

* Creator or community proposes outcomes with bonds (Bounty Pool × 10)
* 2-hour dispute window allows challenges by posting equal bonds
* Disputed outcomes trigger Basis Army (BASIS stakers) arbitration within 24–48 hours
* Invalid markets trigger full refunds; bounty distributed to voting Army members

**Creator Managed:**

* Creator resolves directly (no bond required), or up to 10 whitelisted voter wallets decide by majority
* Resolution is final — no dispute process
* "Invalid / Ambiguous" option available for full refunds

## Lending & Financial Features

### 10. How can I really get 100% LTV loans with no liquidation risk?

Basis's lending facility offers unprecedented terms:

**For Stable+ Collateral:**

* Borrow up to 100% of current market value in USDC
* Zero liquidation risk since token price cannot decrease

**For Floor+ Collateral:**

* Borrow up to 100% of the **floor price** (not spot/market price)
* Since the floor never decreases, collateral value can't drop below the loan — same zero-liquidation guarantee

**Terms:**
* 10–1,000 day loan terms
* Dynamic fees: ~2% for 10 days, ~7% for 1,000 days (total fees, not annualized)
* All interest prepaid upfront — zero payments during loan period
* Repayment = exact loan amount in USDC

**On non-payment at maturity:** Collateral is **burned** (not sold on market) — eliminating liquidation cascades. Borrower can claim any excess value above the loan amount.

### 11. How does leverage trading work without liquidation risk?

**Basis offers dynamic leverage with no liquidation risk from price movements:**

* Leverage is a **toggle** (on/off) — effective leverage depends on current liquidity and buy size
* **"Up to 36x" is possible in optimal conditions** — not a fixed constant. Leverage fluctuates dynamically: smaller buys get higher leverage, larger buys get lower leverage due to price impact
* Leverage is calculated against the floor price — for Stable+ tokens (floor = spot), maximum leverage is always available. For Floor+ tokens, maximum leverage is available at launch (floor ≈ spot) but decreases as spot rises above floor
* The leverage fee is substantial: 43–70% of collateral for small buys
* No forced liquidation from market volatility

{% hint style="warning" %}
Leveraged tokens are held in the leverage contract and **cannot be used as loan collateral**. Leverage and loans are separate paths.
{% endhint %}

## Revenue & Investment

### 12. How much can BASIS stakers earn from the platform?

BASIS Stakers receive 90% of ALL platform revenue distributed as USDC through the pure yield model:

#### Revenue Sources:

• DEX Trading: 90% of net revenue from trading fees (after creator/bonding/vault shares)

• Lending: 90% of net revenue from dynamic loan fees

• Predict+ Events: 90% of net revenue from trading and betting fees

#### **Time-Weighted Staking Tiers (Notice-Based):**

BASIS uses a notice-based system — holders earn yield continuously and can initiate withdrawal at any time, with tokens unlocking after the notice window:

| **Tier**  | **Notice Period**           | **Multiplier** |
| --------- | --------------------------- | -------------- |
| Flexible  | 30 days                     | 1.0x           |
| Standard  | 90 days                     | 1.5x           |
| Committed | 180 days                    | 2.5x           |
| Diamond   | 365 days                    | 4.0x           |
| Founder   | 365 days + 6mo initial lock | 6.0x           |

**APY Projections (Diamond Tier, 50% Supply Staked):**

| **Scenario** | **Annual Revenue** | **Diamond APY** |
| ------------ | ------------------ | --------------- |
| Conservative | $20M               | 28.1%           |
| Base Case    | $40M               | 56.2%           |
| Bullish      | $75M               | 105.3%          |

**The Pure Yield Advantage:**

Unlike platforms that rely on buybacks or token burns, BASIS delivers real value—USDC rewards from actual platform revenue. A Diamond tier staker earns 4x the rewards of a Flexible tier staker with the same number of tokens, creating powerful incentives for long-term commitment.

### 13. What are the cascading growth effects in the Basis ecosystem?

**The ecosystem creates self-reinforcing growth through:**

* Every token must pair with STASIS platform token
* STASIS appreciation (through slippage retention from ecosystem-wide volume) benefits ALL paired tokens
* Network effects: more creators → more users → more fees
* Dynamic supply (burns on sell) creates deflationary pressure

Success anywhere benefits everyone everywhere through mathematical mechanisms.

## Technical & Security

### 14. What blockchain does Basis use? Is it audited and secure?

**Blockchain:** Built on BNB Chain with ERC-20 compatible tokens. Sub-cent gas fees make high-frequency activity economically viable for both humans and AI agents.

**Security Measures:**

* Audited by Hashlock security firm
* MEV-resistant architecture
* No backdoors or hidden mint functions
* 100% non-custodial design

**Trading Fees (platform-set by token type):**

| Token Type | Trading Fee |
| ---------- | ----------- |
| Stable+    | 0.5%        |
| Floor+     | 1.5%        |
| Predict+   | 1.5%        |

Loan fees are dynamic: ~2% for 10-day loans to ~7% for 1,000-day loans (total, not annualized, all prepaid upfront). No platform access fees.

### 15. Can anyone participate? Are there restrictions?

**Fully Permissionless:**

* NO KYC required
* NO geographic restrictions
* Just connect any Web3 wallet
* No registration or approval needed

Predict+ events have AI-enforced content guidelines, but the platform operates entirely on-chain through smart contracts, accessible globally. AI agents participate through the same smart contracts as human users — every action is programmable.

## Getting Started

### 16. How do I get started with Basis?

**For Token Creators:** Connect wallet, launch token for ~$0.14 BNB gas only, earn 20% of trading fees forever in USDC.

**For Investors/Traders:** Browse bonding phase tokens for perpetual fee rewards, use lending for liquidity, trade with dynamic leverage (up to 36x, no price liquidation).

**For Prediction Users:** Browse or create events (zero cost), buy tokens for appreciation or bet on outcomes through the separate USDC pool, claim USDC winnings.

**For AI Agents:** Connect a wallet, install the SDK, and start earning in three API calls. Token creation, trading, prediction markets, lending, and the vault — all accessible programmatically. Agents are first-class citizens on Basis, not second-class integrations.

### 17. What makes Basis different from every other DeFi platform?

**Guaranteed Price Protection:** Stable+ tokens literally cannot decrease in value; Floor+ tokens have rising floor protection with 100% liquidity backing (vs. ~25% for traditional tokens).

**Aligned Incentives:** Creators profit from volume not dumps; early supporters earn forever; stakers benefit from ALL activity.

**Complete Ecosystem:** Four integrated platforms creating network effects where success cascades through the entire system.

**Agent-Native:** Agents are first-class citizens, not second-class integrations. Three API calls to go from zero to earning. The symbiotic loop: agents generate sustained transaction volume, that volume drives protocol revenue, which appreciates for every participant. Human users benefit from agent-driven volume. Agents benefit from human market participation and liquidity.

**Ethical Architecture:** 100% elastic supply (minted on buy, burned on sell) with zero pre-minting makes rug pulls structurally impossible.

**The Bottom Line:** Basis isn't just improving DeFi—it's creating an entirely new paradigm where stability and growth coexist, where everyone wins from everything, and where mathematical certainty replaces trust.

{% hint style="info" %}
Disclaimer: This FAQ is for informational purposes only and does not constitute financial advice.
{% endhint %}
