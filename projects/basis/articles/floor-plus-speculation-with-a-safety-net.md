---
title: "Floor+: Speculation With a Safety Net"
excerpt: "Full price discovery above a rising floor. Trade like you always have — but the floor catches you."
author: "Basis Team"
date: "2026-04-04"
readTime: 12
category: "Token Mechanics"
tags: ["Floor+", "Token Design", "Stability Dial", "Rising Floor"]
coverImage: ""
---


# Floor+: Speculation With a Safety Net

*Full price discovery above a rising floor. Trade like you always have — but the floor catches you.*

> **TL;DR**
> - Floor+ gives you full speculative upside with a mathematically enforced floor price that only rises — you can moon, but you can't go to zero.
> - A creator-set stability dial (permanent at launch) controls the volatility vs. safety trade-off — from near-Stable+ calm to full degen energy.
> - Sells that would kill a normal token actually raise the floor for remaining holders. The death spiral is structurally impossible.

There's a trade-off that every crypto investor has accepted as law: if you want upside, you accept downside. Full price discovery means full exposure. You can 10x, but you can also go to zero.

Floor+ breaks that trade-off.

It gives you a token with full speculative upside — the price can run as high as demand takes it — built on top of a floor price that only moves in one direction: up. You can ride the wave, and if it crashes, there's a floor underneath you that's higher than where you started.

No other token in crypto does this. Here's how it works and why it matters.

## The Two-Zone Model

A Floor+ token has two price zones:

### Zone 1: The Floor (Rising, Immutable)

The floor price is backed by fully embedded reserves. Every transaction pushes the floor higher. The floor can never decrease. It's a one-way ratchet, enforced by the contract and the Basis DEX working together.

### Zone 2: The Spot (Free Market)

Above the floor, the spot price is determined by supply and demand. When buyers are excited, the spot price rises above the floor. When sellers exit, the spot price drops — but it can never drop below the floor.

Think of it like a stock with a built-in, ever-rising stop-loss. The market decides the price above the floor. The contract guarantees the price never goes below it.

## The Stability Dial

When a Floor+ token is created, the creator sets a stability percentage from 0% to 100%. This controls how fast the price moves and how much volatility the token experiences.

This is a critical design choice, and it's immutable after launch. Once set, it can never be changed.

| Stability | Price Behavior | Best For |
|---|---|---|
| 100% (high stability) | Price moves slowly, close to Stable+ behavior | Conservative community tokens, payment rails |
| ~55% (balanced) | Moderate price movement | Most community/identity tokens |
| 0% (low stability) | Fast price movement, maximum volatility | High-risk, high-reward tokens |

**High stability** dampens price movement. Less room for speculation, but the safety net is right below you. Think of it as a high-quality bond — modest upside, strong downside protection.

**Low stability** means the price swings harder. More room for the price to run — and more room for it to fall before hitting the floor. Think of it as a growth stock with a guaranteed buyback price.

The creator picks once. The community lives with it forever.

This is intentional. If the stability dial were adjustable, creators could rug the community by changing it after launch. Making it immutable forces the creator to commit to a design philosophy upfront.

## Why the Floor Only Goes Up

Floor+ tokens share the same foundations as Stable+:

**Adaptive supply.** The token supply adjusts dynamically to maintain a floor price that can only move upward. This is what makes the rising floor possible — fixed-supply tokens can't do it.

**Fully embedded reserves.** The reserves backing each token are built into the contract itself. No external pool to drain, no LP tokens to rug.

The Basis pricing engine ensures that every trade — buy or sell — leaves the floor higher than before. After a complete cycle of buying and selling, there is more value in the reserve than at launch. The floor price is permanently higher.

The stability dial controls the balance: lower stability = bigger price swings, but slower floor accumulation per trade. Higher stability = smaller swings, faster floor accumulation. A Stable+ token (the maximum setting) accumulates floor value the fastest; a Floor+ set to 0% accumulates the slowest. Every setting in between falls on a gradient. But the floor rises at every setting.

**What if trading goes quiet?** The floor freezes — it doesn't drop. A dormant Floor+ token still has its last floor price fully backed by embedded reserves. When trading resumes, the floor starts climbing again. A frozen floor is still infinitely better than no floor at all.

## Floor+ vs Stable+: When to Use Which

| Property | Stable+ | Floor+ |
|---|---|---|
| Spot price vs floor | Always equal | Spot can exceed floor |
| Speculative upside | None (price = floor always) | Yes — full price discovery above floor |
| Downside protection | 100% (price can't drop) | Floor-bounded (can drop to floor, never below) |
| Best leverage | Maximum (floor = spot always) | Maximum at launch, decreases as spot rises above floor |
| Trading feel | Like a savings account | Like a stock with a rising stop-loss |
| Ideal for | Cyclical use cases (casinos, platforms, gaming) | Community tokens, identity tokens, speculative assets |

The simple rule: If you want zero volatility and maximum collateral efficiency, use Stable+. If you want community engagement, speculation, and excitement — with a safety net — use Floor+.

## The Phantom Value Problem (And How Floor+ Tackles It)

On traditional DEXs, the price you see is almost never the price you can get.

Here's the dirty secret of crypto portfolio values: your token might show a "price" of $50 based on the last trade, and your portfolio might say you're holding $500K worth. But the liquidity pool backing that token might only hold $50K. If you tried to sell even a fraction of your position, the price would collapse through slippage. Your $500K was never real — it was phantom value.

This is the norm on Uniswap, PancakeSwap, and every AMM-based DEX. The "price" is just a spot calculation based on pool ratios. It tells you what the last tiny trade went through at, not what you could actually extract. The bigger your position relative to the pool, the more worthless that price becomes.

**Floor+ massively reduces the phantom value problem.** The reduced volatility and sell absorption mechanics mean the ratio of face value to extractable value is far closer than on any traditional AMM. Above the floor, spot price still fluctuates with demand like any market — but Floor+ delivers more robust liquidity at the same market cap. The gap between what your portfolio says you're worth and what you could actually walk away with is dramatically smaller. The floor is real, and so is the liquidity behind it.

For any serious holder — agents managing capital, treasuries parking funds, traders sizing positions — this is the difference between a portfolio built on hope and one built on structural integrity.

## Leverage on Floor+ Tokens

Floor+ tokens support dynamic leverage through Basis — but the leverage ratio changes based on the gap between spot and floor.

**At launch (when spot ≈ floor):** Maximum leverage available. The closer spot is to floor, the higher the leverage ratio, because the floor provides a stronger collateral base.

**During a pump (when spot >> floor):** Leverage decreases. The gap between spot and floor means the collateral's guaranteed value (the floor) is a smaller percentage of the current position value.

**During a correction (when spot approaches floor):** Leverage increases again. The floor is closer to the spot price, providing stronger backing.

This creates a natural cycle: leverage is cheapest when the token is near its floor (often after a selloff — exactly when contrarian agents want to buy), and most expensive at peak euphoria (exactly when smart money should be cautious).

For agents and traders alike, this is a built-in risk management signal. High available leverage = the token is near its floor = potentially good entry. Low available leverage = the token has run far above its floor = potentially overheated.

No liquidation risk at any level — your collateral's floor price can never decrease. The loan is always covered. Every other leverage platform in DeFi will liquidate you if the price moves against you. Basis structurally can't — the mechanic doesn't allow it.

> For a full breakdown of how leverage works on Basis, see [Leverage: Zero-Liquidation Leverage](/articles/dynamic-leverage-without-liquidation).

## What Agents and Creators Build With Floor+

### Community Identity Tokens

An agent or human creator launches a Floor+ token as their public identity. Early supporters buy in. As the creator builds a following and drives trading volume:

- Floor rises from the trading surplus (permanent value creation)
- Spot price fluctuates with sentiment (trading opportunities)
- Creator earns 20% of all trading fees (revenue stream)
- Community members have tokens with a guaranteed minimum value

The creator's brand has a literal, rising floor price. Even if hype dies down, the floor is higher than yesterday. Every cycle of attention adds permanent value.

### Hedge Instruments

Floor+ tokens near their floor price are natural hedge positions. You know the downside is limited (the floor), and you get full upside. For agents and traders building diversified portfolios, Floor+ tokens near their floor are asymmetric bets — limited risk, unlimited reward.

This is especially powerful in combination with prediction market strategies. Use borrowed capital from a strategy stack to pick up Floor+ tokens near their floor — if the token runs, you've added a high-upside position funded by leverage. If it doesn't, the floor limits your loss to the gap between purchase price and floor (which is small by definition, since you bought near the floor).

## The Creator's Playbook

If you're launching a Floor+ token — as a human or an agent — here's the decision framework:

**Step 1: Choose your stability dial carefully. This is permanent.**

- Building a serious community with long-term holders? → 50-70%
- Want maximum trading excitement and speculation? → 0-30%
- Building a near-Stable+ asset with slight upside? → 80-100%

**Step 2: Set up your revenue expectations.**

- Floor+ trading fee: 1.5% per transaction (vs 0.5% for Stable+)
- Creator gets 20% = 0.3% of every trade
- Higher trading fee = more creator revenue per dollar of volume
- Floor+ tokens typically generate 3x the creator revenue of equivalent Stable+ tokens

**Step 3: Plan your launch strategy.**

- Frozen launch? (Whitelist-only early access → builds anticipation)
- Open launch? (Immediate public trading → faster volume)
- Auto-vest for reward phase? (Signals long-term commitment → builds trust)

**Step 4: Drive volume.** Your revenue comes from trading activity, not from selling your position. Create content. Build community. Give people reasons to trade. Every trade raises your floor and generates creator revenue.

## What Happens to Regular Tokens (And Why Floor+ Changes Everything)

To understand the magnitude of Floor+, you need to understand what happens on a normal token launch.

**The standard pump-and-exit death spiral:**

A team launches a token. Insiders hold 10-20% of supply — minted for free. The token pumps on hype. Then insiders start selling. Even a 10% mass selloff on a regular token hollows out the liquidity. The price craters. Retail holders panic sell. More liquidity drains. The token dies. Everyone except the insiders loses.

This isn't a rare scenario. This is the default outcome for 95%+ of token launches across every chain.

**On Floor+, that death spiral is structurally impossible:**

- There are zero pre-minted insider tokens. Nobody holds tokens at a zero cost basis. The creator buys on the curve like everyone else.

- When anyone sells, the surplus stays in the reserve. The floor rises.

- Even if a large holder sells their entire position, the floor for remaining holders is higher than before the sale — not lower.

- The floor price is supported fully by embedded reserves, which is why the liquidity can't be hollowed out — it can't drop to zero.

On a regular token, a whale selling 10% of supply is a catastrophe. On Floor+, a whale selling 10% of supply raises the floor for everyone else. The mechanics are inverted.

## Why This Actually Matters

Here's the thing most people miss: **tokens don't die from lack of buying. They die from panic selling.**

On every traditional launch platform, a single large sell triggers a cascade. The price craters. Holders see red and panic. Everyone rushes for the exit. More liquidity drains. The token is dead in hours. It's not a bug — it's the inevitable physics of how standard AMMs work. One sell creates a bigger dip, which triggers more sells, which creates a bigger dip. The death spiral feeds itself.

Floor+ breaks that cycle at its root. The same sell that would crater a traditional token creates a smaller dip on Floor+. A dip that looks like a buying opportunity, not a reason to panic. The community holds because there's no reason to run. And as long as the community holds, the token lives.

**The paradox:** Floor+ tokens go up slower per dollar of buy volume than a traditional token. On paper, that sounds like a disadvantage. In practice, it's the entire point. You sacrifice the spike to kill the crash — and killing the crash is what actually matters. A token that rises 50% and holds is worth infinitely more than one that spikes 500% and goes to zero.

This is why Floor+ changes the equation for everyone — agents, traders, creators, communities. Not because it eliminates all risk. Not because it guarantees profits. But because it solves the one problem that has killed more tokens than anything else in crypto: the panic sell death spiral. Remove that, and everything else follows.

Full upside. Rising floor. And a community that doesn't need to panic.

## Why Basis Is the Only DEX That Gets This Right

Most DEXs were built for fixed-supply tokens and external liquidity pools. They can list a Floor+ token, but they can't enforce the rising floor, manage the embedded reserves, or power the stability dial. Those mechanics require a trading engine that understands them natively.

Basis was built for exactly this. The reserve mechanics, pricing engine, and stability dial aren't plugins bolted onto a generic AMM — they're core to how the exchange operates. The token contracts and trading engine work as a single integrated system, and the structural guarantees flow from that architecture.

Floor+ tokens can be listed on other DEXs for broader reach — but Basis is where the full mechanics run, where the reserves live, and where the floor is actually enforced. Other listings are secondary markets, naturally arbitraged back to the Basis price.

## The Bigger Picture

Floor+ tokens solve one of crypto's most persistent problems: how do you create a speculative asset that can't go to zero?

For a decade, every attempt at downside protection in crypto has relied on external mechanisms that failed under stress — algorithmic pegs that broke, insurance pools that drained, structured products that unwound. Floor+ bakes it into the token itself. The reserves are embedded. The floor is enforced by the contract. There's no external dependency to fail.

Full upside. Rising floor. One-way safety net.

For agents, traders, and creators building portfolios, launching communities, or managing treasuries — this is the risk profile that finally makes sense. Not "we hope it doesn't crash." Not "trust us." Just math, embedded reserves, and a floor that only goes up.

*Floor+ on Basis: Full price discovery above a mathematically enforced, rising floor price. The first speculative token in crypto with a guaranteed safety net.* [launchonbasis.com](https://launchonbasis.com)
