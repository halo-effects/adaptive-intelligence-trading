# Stable+ — The Token That Can Only Go Up

*Not a stablecoin. Not a memecoin. Something new: a token with a mathematically enforced one-way price ratchet.*

---

Every token in crypto history has had one thing in common: the price can go down.

Bitcoin crashes 50% in bear markets. Stablecoins depeg and wipe billions (ask anyone who held UST). Even blue-chip DeFi tokens bleed 80% from their highs and take years to recover — if they ever do.

What if a token simply... couldn't do that?

Not because of a peg. Not because of reserves. Not because a team promises to buy back. But because the smart contract's math makes a price decrease *physically impossible*.

That's Stable+. And it's the strangest thing in DeFi right now.

---

## How It Actually Works

The core mechanic is elegant. There are exactly two operations:

### Buying Mints New Tokens

When you buy a Stable+ token, you send USDC to the contract. The contract mints new tokens and gives them to you. Your USDC goes into the liquidity pool. The price moves up along the bonding curve.

Every buy increases the total supply and increases the price.

### Selling Burns Tokens

When you sell a Stable+ token, the contract *destroys* your tokens. USDC comes out of the pool and goes to you. But here's the critical detail: a trading fee is charged on every sell, and that fee is injected back into the liquidity pool.

This means when someone sells:
- Tokens are removed from supply (burned)
- USDC leaves the pool (paying the seller)
- BUT the fee goes back into the pool

The net effect: after every sell transaction, the remaining tokens are backed by *more* USDC per token than before. The floor price increases.

### The One-Way Ratchet

Let's trace through an example:

**State 1:** 1,000 tokens exist, backed by $1,000 USDC. Floor price = $1.00.

**Someone buys 100 tokens for $110:** Now 1,100 tokens exist, backed by $1,110 USDC. Floor price ≈ $1.009.

**Someone sells 50 tokens:** They receive $50.50 minus a fee. Say the fee is 0.5% ($0.25). The $0.25 fee goes back into the pool. Now 1,050 tokens exist, backed by $1,059.75 USDC. Floor price ≈ $1.009.

The price after the sell is *the same or higher* than before the sell. This isn't approximate — it's a mathematical property of the contract. The floor can only go up.

**Even in a scenario where everyone sells:**

If 90% of holders sell, they each pay fees that inject back into the pool. The remaining 10% of holders now have their tokens backed by more USDC per token. The floor price has risen.

There is no death spiral. There is no bank run scenario. The last holder standing always has a higher floor price than the first buyer.

---

## What Stable+ Is NOT

Let's clear up the obvious comparisons:

### It's not a stablecoin.

Stablecoins (USDC, USDT, DAI) are pegged to $1. Their price is *supposed* to stay flat. They can depeg downward — and have.

Stable+ is not pegged to anything. Its price starts wherever it starts and goes up from there. It's not stable in the "stays at $1" sense — it's stable in the "never goes down" sense. Different concept entirely.

### It's not an algorithmic stablecoin.

UST/LUNA was an algorithmic stablecoin. It maintained its peg through mint/burn mechanics with a paired token. When confidence broke, the algorithm accelerated the collapse.

Stable+ has no peg to defend. There's no paired governance token propping it up. The floor price is a property of the liquidity pool math, not an algorithm trying to maintain a target. There's nothing to "break."

### It's not a Ponzi or pyramid.

The common skeptic response: "If the price can only go up, someone has to be the bag holder."

Here's why that doesn't apply: every buy adds real USDC to the pool. There are no phantom assets. No leverage. No borrowed reserves. The pool holds exactly the USDC that was put in (minus what was withdrawn through sells, plus the fees recaptured). 

When a seller exits, they get real USDC from the pool, and the remaining holders have a *higher* floor. The "last person in" isn't holding a bag — they're holding a token with the highest floor price in the token's history.

---

## Why This Matters

### For Treasuries

DAOs and protocols need a place to park capital that doesn't lose value. Treasury management in crypto is a nightmare — hold ETH and it might drop 40%. Hold stablecoins and you earn nothing (and carry depeg risk). Hold yield-bearing assets and you're exposed to smart contract risk.

Stable+ is a treasury asset that mechanically appreciates. Every transaction on the token adds to the floor. A project that holds its treasury in Stable+ tokens is holding an asset with a one-way price trajectory. It's not yield farming — it's structural appreciation from trading activity.

### For Agent Treasuries Specifically

AI agents managing capital need predictable base assets. An agent can't build reliable strategies on top of collateral that might crash 30% overnight. Stable+ gives agents a base token with a guaranteed floor — making every calculation about leverage, loans, and capital allocation simpler and more reliable.

### For Loan Collateral

This is where Stable+ unlocks the full Basis ecosystem.

Because the floor price can only increase, loans against Stable+ tokens at 100% LTV are structurally safe. The collateral is *guaranteed* to be worth at least the loan amount at any point during the loan term. This is why Basis can offer 100% LTV with no price-based liquidation — and it's only possible because of the Stable+ floor mechanics.

```python
from basis import BasisClient

client = BasisClient.create(private_key="0x...")

# Check the floor price of any token
price = client.trading.get_usd_price("0xTokenAddress...")
print(f"Current price: ${price}")

# Take a 100% LTV loan against Stable+ tokens
result = client.loans.take_loan(
    MAINTOKEN,
    "0xStablePlusToken...",
    100 * 10**18,   # 100 tokens as collateral
    30               # 30-day loan
)
```

Your Stable+ tokens are locked as collateral. You get USDC equal to their full floor value. The floor continues to rise while your tokens are locked (from other people's trading activity). When you repay the loan, your tokens are worth more than when you deposited them.

### For Leverage

Because the floor price equals the spot price on Stable+ (there's no gap between them), leverage on Stable+ tokens is maximized. The leverage ratio is calculated against the floor price — and since floor = spot, you get the highest possible leverage.

This is why Stable+ tokens can support dynamic leverage up to ~36x depending on pool liquidity and position size. The math works because the floor gives leverage a natural, non-liquidatable reference point.

### For Prediction Markets

Every Predict+ prediction market creates outcome tokens. These outcome tokens are Stable+ tokens. That means prediction market positions have floor prices, can be borrowed against, and mechanically appreciate from trading activity.

Your prediction bet isn't just a bet — it's a yield-bearing, collateralizable, appreciating asset.

---

## The Trading Fee Engine

The fee structure is what drives Stable+ appreciation. Here's how the fees flow:

| Fee Destination | Percentage | What It Does |
|----------------|------------|--------------|
| Creator (token deployer) | 20% | USDC to the creator's wallet — forever |
| STASIS Vault | 16% | Injected as STASIS, increases wSTASIS ratio |
| Presale participants | 4% | Revenue share for early supporters |
| Platform | 60% | Protocol revenue |

Base trading fees are 0.50% per transaction for Stable+ tokens. On a $100 trade, that's $0.50 in fees. Of that, $0.10 goes to the creator.

That sounds small — until you multiply it by volume. A Stable+ token doing $10,000/day in trading volume generates $50/day in fees, $10/day to the creator. Over a year, that's $3,650 in creator revenue from a single token.

And here's the compounding effect: every fee injection raises the floor price, which can attract more trading, which generates more fees, which raises the floor further. It's a positive feedback loop bounded by real economic activity, not speculation.

---

## Surge Tax: The Hype Amplifier

During periods of high trading volume, Stable+ tokens activate a surge tax — a temporary additional fee that decays linearly over time.

For Stable+ tokens, the surge is modest (up to ~0.5% additional). This serves two purposes:

1. **Accelerates floor appreciation** during peak activity — exactly when the most USDC is flowing through the system
2. **Dampens excessive speculation** by making rapid-fire trading slightly more expensive

The surge tax resets on a 7-day rolling window. Once volume normalizes, the fee returns to its base rate.

---

## Real-World Use Cases Already Emerging

Even in the beta phase, patterns are forming:

**Agent Identity Tokens:** AI agents launching Stable+ tokens as their on-chain identity. Community members buy to support the agent. Every trade raises the floor. The agent's "brand" has a literal price floor that can only go up.

**Event Currencies:** Conferences, communities, and DAOs creating Stable+ tokens as event currencies. Participants buy in, trade among themselves, and when the event ends, every holder has tokens worth more than they paid.

**Savings Instruments:** Users parking USDC in Stable+ tokens as a savings strategy. Not yield farming with its risks — just a token that mathematically can't lose value relative to its floor.

**Base Pair Tokens:** Protocols using Stable+ as trading pairs for other assets, knowing the base pair will never crash.

---

## The Uncomfortable Question

"If the price can only go up, what's the catch?"

Fair question. Here are the honest limitations:

**The price can go up slowly.** If trading volume is low, fee injection is low, and the floor barely moves. Stable+ isn't a get-rich-quick instrument — it's a structural appreciation vehicle. In a dead market, it just... sits there. Not losing value, but not rapidly gaining either.

**Liquidity on exit depends on buyers.** You can always sell at the floor price back to the contract — but if you want to sell a large amount, the bonding curve means you'll move the price. Large exits take a price impact, though the floor remains intact for remaining holders.

**It's new.** The math is sound. The contracts are deployed. But this model hasn't been tested through a full crypto bear market cycle yet. Novelty carries its own risk — even when the mechanics are provably correct.

These aren't hidden gotchas. They're the honest tradeoffs of a new financial primitive. The core property — the floor can only go up — is mathematically guaranteed. Everything else is market dynamics.

---

## The Bottom Line

Crypto has had thousands of token models. All of them share one property: the price can go down. Every portfolio strategy, every risk model, every investment thesis in crypto accounts for the possibility of loss.

Stable+ removes that variable. Not with promises. Not with reserves. Not with governance. With math.

For treasuries, for collateral, for agent base assets, for prediction markets, for anyone who wants exposure to crypto without the existential risk of going to zero — this is something genuinely new.

The token that can only go up. Not a meme. A mechanism.

---

*Stable+ on Basis: Mathematically enforced floor price. One-way ratchet. 100% LTV loan eligible. The first token in crypto that can only go up. [launchonbasis.com](https://launchonbasis.com)*
