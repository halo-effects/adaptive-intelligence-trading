# Prediction Marketplace

## Introducing Predict+

Predict+ combines the excitement of event-based markets with the stability of Basis's Stable+ token technology. Unlike traditional prediction platforms that force binary win-or-lose scenarios, Predict+ creates a multi-layered prediction economy where participants can invest, trade, borrow, and bet — all within the same market.

### The Problem with Traditional Prediction Markets

**Centralization creates systemic risk.** Platforms like Polymarket suffer from regulatory vulnerabilities, geographic restrictions, and single points of failure. Users are trusting a centralized entity with event creation, resolution, and fund custody.

**Binary outcomes limit participation.** Traditional platforms offer all-or-nothing betting. Participants who see a market gaining attention but are uncertain about the outcome have no way to profit from their insight about the market's popularity.

**Capped payouts reduce upside.** On platforms like Polymarket, payouts are capped at $1 per share. On Basis, winners split the **entire** losing pool — uncapped. Multi-outcome markets produce dramatically higher payouts for correct underdogs.

### The Predict+ Solution

#### One Token Per Market — Not One Per Outcome

{% hint style="info" %}
Each prediction market has **one Predict+ token** that represents the market itself. Buying the Predict+ token is a separate action from betting on outcomes. The token trades on the DEX like any other Basis token; betting happens through a dedicated USDC betting pool.
{% endhint %}

This separation is critical. It means participants can:

1. **Hold tokens for appreciation** — the Predict+ token (Stable+ type) can only go up in price as trading volume generates slippage retention
2. **Trade tokens on the DEX** — capture volatility from news and sentiment shifts
3. **Use tokens as collateral** — take 100% LTV loans to access liquidity without selling
4. **Bet on outcomes** — traditional prediction betting with USDC payouts through a separate betting pool

### How Predict+ Works

#### Event Creation

Permissionless, zero-cost event creation:

1. **Event Basics:** Name, symbol, icon, description, optional end date, at least 2 mutually exclusive answers
2. **Tokenomics & Resolution:**
   * Bonding phase USDC target ($0–$150,000 — predictions can skip bonding entirely)
   * Optional freeze token for whitelist-only initial access
   * Resolution style: **Basis Managed** (community votes, disputes allowed) or **Creator Managed** (creator or up to 10 voter wallets, majority vote, no disputes)
   * Event type (Creator Managed only): **Public** or **Private** (whitelisted wallets only for betting; token buying open to all)
3. **Review & Launch**

Starting liquidity is currently fixed at $1,000 for all predictions.

#### The Betting Interface

The prediction event page provides:

* **Total Pot** — cumulative USDC from all bets
* **Total Bounty** — trader-to-bettor pot (a portion of Predict+ trading fees that supplements the winning pool)
* **Outcome selection** with current share prices and implied probabilities
* **Amount input** with quick 25/50/75/100% buttons

**How betting works:**

1. Each outcome has a share price starting at equal split (e.g., 2 outcomes = $0.50 each, 3 outcomes = $0.33 each)
2. Betting = buying shares in an outcome at the current price using USDC
3. As shares are purchased for one outcome, its price/probability rises and others fall
4. When resolved: winning outcome shareholders split the total pot (all losing stakes + bounty) proportionally

**Share price range:** $0.001 to $0.999 — can never reach $1.00 (certainty has no risk premium).

#### Selling Shares (Order Book)

Predict+ uses a real order book for share trading:

* **Market sell:** Lists at current market price — queued until a buyer matches
* **Limit sell:** Set a custom price ($0.001–$0.999) — fills when price is reached
* **Underwater matching:** The buyer sees a simple "Buy" interface; the system routes to the best source (existing sell orders first if cheaper, then the pool)

This lets participants exit positions before resolution by selling when probability shifts favorably.

#### The Trader-to-Bettor Pot

A portion of Predict+ token trading fees flows into a general pot that always pays out to the winning outcome. This creates a symbiotic loop:

* More token traders → bigger bounty pot → attracts more bettors → more market excitement → more token traders

This pot supplements the winning pool without affecting any outcome's token price.

### Resolution

#### Basis Managed Markets

1. Trading and betting occur until the event's end condition is met
2. Creator or community members propose an outcome
3. Community resolvers post bonds (Bounty Pool × 10)
4. 2-hour dispute window allows challenges
5. Disputes trigger Basis Voting Army arbitration (24–48 hours depending on market type)
6. Successful resolvers receive the bounty pool; failed disputants forfeit bonds

#### Creator Managed Markets

1. Voting is available **immediately** — runs simultaneously with trading
2. Creator votes to resolve (no bond required), or up to 10 whitelisted voter wallets decide by majority
3. Resolution is **final** — no dispute process
4. "Invalid / Ambiguous" option available — triggers full refund to all bettors

### Post-Resolution

* Winners claim USDC payouts through the dApp (no time limit)
* Payout = (Your Winning Shares / Total Winning Shares) × Total Prize Pool (including bounty)
* Predict+ tokens continue to exist until all holders sell — tokens are burned on sell
* **Counterintuitive:** After resolution, selling fees inject into liquidity → price goes UP during sell waves. Patient holders who wait through the frenzy exit at a higher price.

### Competitive Advantage vs. Polymarket

| Feature | Polymarket | Predict+ |
| ------- | ---------- | -------- |
| Architecture | Centralized | Decentralized (smart contracts) |
| Payout model | Capped at $1/share | Winners split entire losing pool (uncapped) |
| Token utility | Binary bet tokens only | Hold, trade, collateralize, bet |
| Event creation | Restricted/curated | Permissionless, zero cost |
| Resolution | Centralized oracles | Multi-layer (creator, community, voting army) |
| Price protection | None | Stable+ floor (tokens can't decrease) |
| Liquidation risk | N/A | Zero (100% LTV loans available) |
| Geographic restrictions | Yes | No (fully permissionless) |

### Revenue Model

**Trading fee:** 0.5% on Predict+ token buys and sells (platform-set).

**Fee distribution:**
* Creator: 20% of trading fees (perpetual)
* Bonding phase buyers: 3.33% of trading fees (perpetual, if bonding phase used)
* A portion flows to the trader-to-bettor bounty pot
* Remainder follows standard fee waterfall → STASIS Vault → Platform Revenue → 90% to BASIS Vault stakers

### Discussion Tab

Each prediction market includes a **wallet-signed discussion** feature:
* Comments are cryptographically tied to wallet addresses
* Requires at least 1 trade ≥ $5 on that market to comment (anti-spam)
* Creator badge shown on creator's comments
* Creator can moderate (delete comments)
