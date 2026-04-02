# Stable+: The Token That Can Only Go Up

*A token with a mathematically enforced price that only rises. Basis tokens can be paired with any value token — BTC, ETH, SOL, or a stablecoin like USDT. For simplicity, we'll use USDT throughout this article.*

Every token in crypto history has had one thing in common: the price can go down.

Bitcoin crashes 50% in bear markets. Stablecoins depeg and wipe billions (ask anyone who held UST). Even blue-chip DeFi tokens bleed 80% from their highs and take years to recover — if they ever do.

What if a token simply... couldn't do that?

Not because of a peg. Not because of reserves. Not because a team promises to buy back. But because the smart contract's math makes a price decrease physically impossible.

That's Stable+. And it's the strangest thing in DeFi right now.

## How It Actually Works

Two foundational properties make Stable+ possible — properties that don't exist in traditional tokens:

**Elastic supply.** Tokens are minted when you buy and burned when you sell. There is no fixed supply. Fixed-supply tokens can't have rising prices because there's no mechanism to create the surplus.

**No separate LP pool.** The real liquidity (USDT in this case) lives inside the token contract itself. There are no LP tokens to drain. No external pool to rug. The liquidity IS the contract.

### The Simple Version

Start with the basics. Imagine a token with a 100% liquidity reserve — no fancy math:

- Liquidity: $1,000 · Tokens: 1,000 · Price: $1.00
- Someone buys $1 → Liquidity: $1,001 · Tokens: 1,001 · Price: $1.00

Every token is backed 1:1. The price never moves. Simple. All Basis tokens start at $1.

Now here's what Stable+ does differently: it uses a constant product formula, so your $1 buy mints *slightly less* than 1 token. The extra stays in the pool.

- Liquidity: $1,001 · Tokens: 1,000.99 · Price: $1.00001

Sells work the same way. Burning 1 token at a $1 price gives you $0.99 back — the difference stays in the liquidity reserve.

Every trade — buy or sell — leaves slightly more liquidity backing each remaining token. Multiply across thousands of trades and the price ratchets up permanently.

The price is a property of two things working together: the 1:1 full liquidity reserve and the constant product math. The price can only increase.

### The One-Way Ratchet

Even in a scenario where everyone sells:

If 90% of holders sell, each sell leaves a tiny surplus in the reserve. The remaining 10% of holders now have their tokens backed by more USDT per token. The price has risen.

There is no death spiral. There is no bank run scenario. The last holder standing always has a higher price than the first buyer.

> For a detailed walkthrough with the constant product formula, hybrid multiplier math, and step-by-step tables, see [Token Mechanics: How Basis Tokens Actually Work](/articles/token-mechanics).

## What Stable+ Is NOT

Let's clear up the obvious comparisons:

### It's not a stablecoin.

Stablecoins (USDT, USDC, DAI) are pegged to $1. Their price is supposed to stay flat. They can depeg downward — and have.

Stable+ is not pegged to anything. Every Basis token starts at $1, but the price only goes up from there. It's not stable in the "stays at $1" sense — it's stable in the "never goes down" sense. Different concept entirely.

### It's not an algorithmic stablecoin.

UST/LUNA was an algorithmic stablecoin. It maintained a $1 peg through mint/burn mechanics with a paired token — LUNA. The critical flaw: LUNA's price could fluctuate freely, so the peg was only as strong as LUNA's market value. When confidence broke, LUNA's price collapsed, and the algorithm that was supposed to maintain the peg instead accelerated the death spiral.

Stable+ also pairs with a token (like USDT), but the mechanics are fundamentally different. Stable+ isn't trying to maintain a fixed dollar peg — it maintains an ever-increasing price *denominated in the paired token itself*. If paired with USDT, the price in USDT only goes up. If paired with BTC, the price in BTC only goes up. The paired token's dollar value can fluctuate — that doesn't matter. The Stable+ price in the paired token can never decrease. There is no peg to defend, no target to maintain, and nothing to "break."

### It's not a Ponzi or pyramid.

The common skeptic response: "If the price can only go up, someone has to lose."

Here's why that doesn't apply: every buy adds real USDT to the pool. There are no phantom assets. No leverage. No borrowed reserves. The pool holds exactly the USDT that was put in (minus what was withdrawn through sells, plus the surplus retained by the constant product formula).

When a seller exits, they get real USDT from the pool, and the remaining holders have a higher price. The "last person in" isn't left holding depreciating tokens — they're holding a token at the highest price in the token's history.

## Why This Matters

### For Treasuries

DAOs and protocols need a place to park capital that doesn't lose value. Treasury management in crypto is a nightmare — hold ETH and it might drop 40%. Hold stablecoins and you earn nothing (and carry depeg risk).

Stable+ is a treasury asset that mechanically appreciates. Every transaction on the token adds to the price. A project that holds its treasury in Stable+ tokens is holding an asset with a one-way price trajectory. It's not yield farming — it's structural appreciation from trading activity.

### For Agents and Traders Managing Capital

AI agents and human traders both need predictable base assets. Nobody can build reliable strategies on top of collateral that might crash 30% overnight. Stable+ gives any operator — automated or human — a base token with a guaranteed price that can only increase, making every calculation about leverage, loans, and capital allocation simpler and more reliable.

### For Loan Collateral

This is where Stable+ unlocks the full Basis ecosystem.

Because the price can only increase, loans against Stable+ tokens at 100% LTV are structurally safe. The collateral is guaranteed to be worth at least the loan amount at any point during the loan term. This is why Basis can offer 100% LTV with no price-based liquidation — and it's only possible because of the Stable+ price mechanics.

Your Stable+ tokens are locked as collateral. You get USDT equal to their full value. The price continues to rise while your tokens are locked (from other people's trading activity). When you repay the loan, your tokens are worth more than when you deposited them.

### For Leverage

Stable+ tokens are the ideal collateral for leveraged positions on Basis. Because there's no gap between the price and the collateral value — they're the same thing — you get the maximum possible leverage ratio.

On Floor+ tokens, the spot price can trade above the floor, meaning leverage is calculated against the lower floor value. On Stable+, every dollar of collateral counts at full value. This is why Stable+ supports the highest leverage ratios on the platform.

Leverage on Basis works through recursive loans: buy → lock as collateral → borrow → buy again. No liquidation risk at any level because your collateral's price can never decrease. The loan is always covered.

> For a full breakdown of how leverage works on Basis, see [Leverage: Zero-Liquidation Leverage](/articles/leverage-zero-liquidation).

### For Prediction Markets

Every Predict+ prediction market creates an outcome token — and that token is a Stable+ token. This means the token's price can only increase from trading activity.

But here's what makes it powerful: the outcome token gives you ways to profit beyond just betting. You can buy the token for price appreciation. You can use it as loan collateral. You can combine strategies — buy the token, take a loan against it, and use the borrowed USDT to place bets. The token and the prediction market are separate instruments that work together.

> For more on Predict+ mechanics, see [Prediction Markets: Uncapped One-Big-Pot](/articles/prediction-markets).

## Real-World Use Cases

Stable+ tokens thrive on *velocity* — they perform best where tokens are regularly bought, used, and sold/burned, keeping supply low and the appreciation engine running. The more the token cycles through buy → use → sell, the better it works.

This makes Stable+ ideal for use cases with high circulation:

**Online Casinos and Gambling:** Players buy tokens to play. The house burns tokens on wins. Winners sell. This constant cycle keeps supply low and the price steadily appreciating. Every round of play adds permanent value to the token.

**Platform Currencies:** Any platform that needs an internal token — gaming, marketplaces, service platforms — gets a currency that mechanically appreciates from user activity. The platform's economy generates value for all token holders automatically.

**In-Game Currencies:** Players buy tokens, spend them in-game (burned on use), and the cycle repeats. Unlike traditional in-game currencies that inflate to zero, Stable+ game tokens increase in value as the game grows.

**Agent Identity Tokens:** AI agents launching Stable+ tokens as their on-chain identity. Community members buy to support the agent. Every trade raises the price. The agent's "brand" has a literal price that can only go up.

**Creator Brand Tokens:** Human creators, analysts, and community builders launching Stable+ tokens as their on-chain brand. Every trade from supporters raises the price and generates creator fees. The price never drops — so supporters never feel like they're buying into something that can go to zero.

**Loyalty and Reward Tokens:** Earn tokens, spend at merchants, earn again. The circulation keeps the engine running while every participant benefits from the rising price.

**Access Tokens:** Buy to use a service, token burned on use. Each use cycle raises the price for remaining holders.

**Tipping and Creator Tokens:** Fans buy, tip the creator, creator sells. The buy-sell cycle drives appreciation while giving creators a direct revenue stream.

**Event Currencies:** Conferences, communities, and DAOs creating Stable+ tokens as event currencies. Participants buy in, trade among themselves, and when the event ends, every holder has tokens worth more than they paid.

**Savings Instruments:** Users parking USDT in Stable+ tokens as a savings strategy. Not yield farming with its risks — just a token that mathematically can't lose value.

## The Bottom Line

Crypto has had thousands of token models. All of them share one property: the price can go down. Every portfolio strategy, every risk model, every investment thesis in crypto accounts for the possibility of loss.

Stable+ removes that variable. Not with promises. Not with reserves. Not with governance. With math.

The token that can only go up. Not a meme. A mechanism.

*Stable+ on Basis: Mathematically enforced price. One-way ratchet. 100% LTV loan eligible. The first token in crypto that can only go up.* [launchonbasis.com](https://launchonbasis.com)
