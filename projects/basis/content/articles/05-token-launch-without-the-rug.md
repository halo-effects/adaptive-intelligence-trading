# Token Launch Without the Rug

*What if the creator literally couldn't dump on you? Not "trust me" — mathematically impossible.*

---

The token launch space has a trust problem. And everyone knows it.

On Pump.fun, over 95% of tokens launched go to zero. Creators mint tokens, hype them up, dump their pre-allocated bags, and disappear. The platform itself doesn't care — it takes fees on the way up and the way down. The incentives are aligned against the community from day one.

Solana's token ecosystem has become a speedrun to exit liquidity. "Fair launch" has become an ironic phrase. And the agents operating in this space? They're the fastest rugs of all — deploying, pumping, and dumping in minutes.

There's a different way to build this.

---

## The Core Problem: Pre-Minting

Every rug pull starts with the same mechanic: the creator holds tokens that were minted before anyone else could buy.

It doesn't matter how it's packaged — "team allocation," "dev fund," "strategic reserve" — the result is the same. The creator has tokens at a cost basis of zero. Everyone else buys at market price. The creator sells. The price collapses. Community holds the bag.

This is such a fundamental problem that the entire token launch industry has been built around *managing* it rather than *eliminating* it:

- Vesting schedules (delays the dump, doesn't prevent it)
- Locked liquidity (prevents LP rug, not token dumps)
- Renounced ownership (prevents function changes, not pre-minted selling)
- Audit certificates (checks code, not economic design)

All of these are patches. None of them solve the root cause.

---

## The Basis Solution: 100% Elastic Supply

On Basis, tokens are created with zero pre-minting. Not "low" pre-minting. Not "fair" pre-minting. *Zero.*

Here's how it works:

**When someone buys a token, new tokens are minted.** The buyer's USDC goes into the liquidity pool. Fresh tokens are created and delivered to the buyer. The price moves up along the bonding curve.

**When someone sells a token, those tokens are burned.** The tokens are destroyed. USDC comes out of the liquidity pool and goes to the seller. The price moves down along the bonding curve — but never below the floor.

**The creator holds zero tokens at launch.** There is no "team allocation" in the contract. There is no pre-mint function. The creator, like everyone else, must buy tokens on the bonding curve. At market price. With real money.

This isn't a policy decision or a gentleman's agreement. It's a mathematical property of the contract. The `createToken` function deploys a token with zero supply. The only way supply increases is through `buy`. There is no `mint` function accessible to the creator.

**Mathematically impossible to rug.** Not "difficult." Not "discouraged." Impossible.

---

## Two Token Types, One Anti-Rug Guarantee

Basis offers two token types, both with elastic supply:

### Stable+ — Price Only Goes Up

The Stable+ token has a unique property: its spot price equals its floor price at all times. When you buy, the price goes up. When you sell, the tokens are burned and fees are injected back into the pool — so the price *still* goes up (or stays the same for the remaining holders).

There is no mechanism for the price to decrease. Buying pushes it up. Selling burns tokens and adds fees, pushing the floor up. It's a one-way ratchet.

**Best for:** Treasury tokens, base pair tokens, system tokens. Anything where stability and guaranteed appreciation matter more than speculative upside.

**Leverage available:** Maximum (dynamic, based on pool depth), because the floor always equals the spot price.

### Floor+ — Rising Floor With Volatility

The Floor+ token has a rising floor price with a customizable stability dial (set at launch, immutable afterward). The spot price can rise above the floor based on demand, creating speculative upside. But the floor only moves up — never down.

**The stability dial** (50%-90%) controls how much of the liquidity pool backs the floor vs. allows free trading. Higher stability = tighter spread between floor and spot. Lower stability = more room for speculative price movement.

**Best for:** Community tokens, identity tokens, agent brand tokens. Anything where you want both a safety net and upside potential.

**Leverage available:** Maximum at launch (when floor = spot), decreasing as spot rises above floor.

---

## How Creators Actually Earn

If creators can't pre-mint and dump, how do they make money?

Through *sustainable revenue*, not extraction.

**20% of all trading fees. Forever.**

Every buy and sell on a Basis token generates a trading fee. The creator receives 20% of that fee, paid in USDC, for the lifetime of the token. Not for a month. Not until some milestone. Forever.

The remaining fee split:
- 16% → STASIS Vault (benefits all stakers)
- 4% → Presale participants
- 60% → Platform

This completely realigns incentives. The creator doesn't want to dump — they want *volume*. More trading means more fees. More fees mean more USDC in the creator's wallet. The creator's best strategy is to build a healthy, active community that trades regularly.

**Creator revenue is proportional to the token's success, not its failure.** That's the opposite of the Pump.fun model, where creators profit by extracting value on the way out.

---

## Surge Tax: Monetizing Hype Cycles

Basis includes a mechanism called surge tax that creates additional revenue during high-volume periods.

When trading volume spikes above a rolling 7-day threshold, a temporary additional fee kicks in. This fee decays linearly — it's highest at the start of the surge and drops back to zero as volume normalizes.

For Stable+ tokens, the surge is modest (up to ~0.5%). For Floor+ tokens with high hybrid multipliers, it can reach up to 15%.

Why does this matter for creators? Because hype cycles — the moments when everyone is buying — generate the most creator revenue. The surge tax amplifies this, rewarding creators who build tokens that attract genuine interest.

And here's the anti-gaming property: surge tax makes pump-and-dump *expensive*. If you try to artificially inflate volume, you're paying elevated fees on every trade. The cost of manipulation scales with the manipulation itself.

---

## What Agents Build With This

For AI agents, token creation isn't just about launching a coin. It's about building a *revenue-generating asset*.

**Agent Identity Tokens:** An agent launches a Floor+ token as its public identity. Community members buy in to support the agent. Every trade generates creator fees for the agent. The token becomes both a brand and an income stream.

**Market-Specific Tokens:** An agent creating prediction markets can launch associated tokens. A sports prediction agent launches "SportsBet+" — a token that serves as the base pair for its prediction markets. All prediction market trading generates token trading volume. All token trading generates creator fees.

**Treasury Tokens:** An agent managing capital launches a Stable+ token as its treasury. Deposits from users mint new tokens. The agent manages the treasury, generating returns. Stable+ means the price only goes up — depositors have floor-price guarantees.

**Community Tokens:** An agent building a community around a topic — AI research, market analysis, alpha calls — launches a Floor+ token. Community participation drives volume. Volume drives creator fees. Creator fees fund more community building.

In each case, the token creation isn't the end goal — it's the beginning of a revenue flywheel.

---

## The Vesting Option

For agents or creators who want to signal long-term commitment, Basis offers optional liquid vesting at launch.

When creating a token, you can enable auto-vesting for bonding phase participants. Early buyers receive tokens on a vesting schedule (cliff or gradual, configurable duration). But here's the key innovation — vested tokens can still be used as loan collateral.

You're vesting *and* borrowing against your vested position simultaneously. The tokens are locked for the vesting period, but the capital efficiency isn't sacrificed.

```python
# Launch a token with 90-day gradual vesting for early buyers
result = client.factory.create_token(
    "MYAGENT", "My Agent Token",
    hybrid_multiplier=50,   # Floor+ token
    frozen=False,
    usdc_for_bonding=10000,
    start_lp=1000,
    auto_vest=True,
    auto_vest_duration=90,  # 90 days
    gradual_autovest=True   # Linear unlock (vs cliff)
)
```

---

## The Contrast

| Feature | Pump.fun / Memecoins | Basis |
|---------|---------------------|-------|
| Pre-mint | Yes (creator holds bags) | Zero (mathematically impossible) |
| Rug pull possible | Yes | No |
| Creator revenue model | Dump tokens | 20% of trading fees forever |
| Price floor | None | Enforced by bonding curve |
| Sustainability | Minutes to hours | Permanent revenue stream |
| Token utility | Speculation only | Collateral, lending, prediction markets |
| Community alignment | Adversarial | Cooperative |
| Vesting | Rare, easily circumvented | Built-in, with loan capability |

The difference isn't subtle. One model is built on extraction. The other is built on alignment.

---

## The Punchline

Token launches don't need to be predatory. They don't need to be a race to dump. They don't need "trust me" promises that evaporate the moment the chart goes green.

When you remove pre-minting, replace extraction with fees, and enforce floor prices mathematically, you get something that hasn't existed in crypto before: token launches where the creator's incentive is to *build*, not to *exit*.

For AI agents — systems that can operate 24/7, build communities autonomously, and optimize for long-term revenue — this is the token model that finally makes sense.

Not because it's safer (it is). Not because it's fairer (it is). But because it's *profitable to be honest*. And for an optimizing agent, that's all the incentive it needs.

---

*Basis: Zero pre-mint tokens. 100% elastic supply. Creator fees forever. The token launch model built for builders, not dumpers. [launchonbasis.com](https://launchonbasis.com)*
