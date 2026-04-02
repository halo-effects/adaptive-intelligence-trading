# Floor+: Speculation With a Safety Net

*Full price discovery above a rising floor. Trade like you always have — but the floor catches you.*

There's a trade-off that every crypto investor has accepted as law: if you want upside, you accept downside. Full price discovery means full exposure. You can 10x, but you can also go to zero.

Floor+ breaks that trade-off.

It gives you a token with full speculative upside — the price can run as high as demand takes it — built on top of a floor price that only moves in one direction: up. You can ride the wave, and if it crashes, there's a floor underneath you that's higher than where you started.

No other token in crypto does this. Here's how it works and why it matters.

## The Two-Zone Model

A Floor+ token has two price zones:

### Zone 1: The Floor (Rising, Immutable)

The floor price is backed by real liquidity held inside the token contract itself — not in a separate LP pool. There are no LP tokens to drain. The liquidity IS the contract. Every transaction leaves a small surplus in the reserve thanks to the constant product formula, and that surplus pushes the floor higher. The floor can never decrease. It's a one-way ratchet, enforced by contract math.

### Zone 2: The Spot (Free Market)

Above the floor, the spot price is determined by supply and demand. When buyers are excited, the spot price rises above the floor. When sellers exit, the spot price drops — but it can never drop below the floor.

Think of it like a stock with a built-in, ever-rising stop-loss. The market decides the price above the floor. The contract guarantees the price never goes below it.

## The Stability Dial

When a Floor+ token is created, the creator sets a stability dial — a value between 50% and 90%. This controls how fast the price moves by determining how much the token reserve grows relative to circulating supply on each trade.

This is a critical design choice, and it's immutable after launch. Once set, it can never be changed.

| Stability Setting | Price Behavior | Best For |
|---|---|---|
| 90% (high stability) | Price moves slowly, close to Stable+ behavior | Conservative community tokens, payment rails |
| 70% (balanced) | Moderate price movement | Most community/identity tokens |
| 50% (low stability) | Fast price movement, maximum volatility | High-risk, high-reward tokens |

**High stability (90%)** means the token reserve grows almost in lockstep with circulating supply — dampening price movement. Less room for speculation, but the safety net is right below you. Think of it as a high-quality bond — modest upside, strong downside protection.

**Low stability (50%)** means the token reserve stays nearly constant while circulating supply changes — so the price swings harder. More room for the price to run — and more room for it to fall before hitting the floor. Think of it as a growth stock with a guaranteed buyback price.

The creator picks once. The community lives with it forever.

This is intentional. If the stability dial were adjustable, creators could rug the community by changing it after launch. Making it immutable forces the creator to commit to a design philosophy upfront.

## Why the Floor Only Goes Up

Floor+ tokens share the same two foundations as Stable+:

**Elastic supply.** Tokens are minted when you buy and burned when you sell. There is no fixed supply. This is what makes the rising floor possible — fixed-supply tokens can't do it.

**No separate LP pool.** The real liquidity lives inside the token contract. No external pool to drain, no LP tokens to rug.

The constant product formula is what creates the surplus. On every buy, you receive slightly fewer tokens than the USDB you put in would suggest at a flat rate. On every sell, you receive slightly less USDB back than the spot price would suggest. That "slightly less" — in both directions — stays in the reserve.

After a complete cycle of buying and selling, even if every token is sold and burned, there is more USDB in the reserve than at launch. The floor price is permanently higher.

The stability dial just controls the speed: lower stability = bigger price swings, faster accumulation per trade. Higher stability = smaller swings, steadier accumulation. But the floor rises at every setting.

> For the full constant product formula breakdown, hybrid multiplier math, and step-by-step comparison tables across all stability settings, see [Token Mechanics: How Basis Tokens Actually Work](/articles/token-mechanics).

## Floor+ vs Stable+: When to Use Which

| Property | Stable+ | Floor+ |
|---|---|---|
| Spot price vs floor | Always equal | Spot can exceed floor |
| Speculative upside | None (price = floor always) | Yes — full price discovery above floor |
| Downside protection | 100% (price can't drop) | Floor-bounded (can drop to floor, never below) |
| Best leverage | Maximum (floor = spot always) | Maximum at launch, decreases as spot rises above floor |
| Trading feel | Like a savings account | Like a stock with a rising stop-loss |
| Ideal for | Treasuries, base pairs, collateral | Community tokens, identity tokens, speculative assets |

The simple rule: If you want zero volatility and maximum collateral efficiency, use Stable+. If you want community engagement, speculation, and excitement — with a safety net — use Floor+.

## The Surge Tax Dynamic

Floor+ tokens have a more dramatic surge tax than Stable+ — up to 15% additional fee during high-volume periods (compared to 0.5% for Stable+).

Why? Because Floor+ tokens are designed for speculative activity. When hype cycles hit, volume spikes massively. The surge tax:

- **Captures value from hype:** Those elevated fees add to the surplus, permanently raising the floor

- **Naturally cools overheated markets:** Higher fees slow down rapid speculation

- **Rewards patient holders:** The surplus raises the floor for everyone, but the surge tax specifically taxes the frantic traders

After the hype fades and volume normalizes (7-day rolling window), the surge tax decays back to zero. What remains is a permanently higher floor.

Think of it this way: Every hype cycle — every pump, every viral moment — permanently raises the floor price. The hype fades, the floor stays. Over multiple cycles, the floor ratchets up and up.

## Leverage on Floor+ Tokens

Floor+ tokens support dynamic leverage through Basis — but the leverage ratio changes based on the gap between spot and floor.

**At launch (when spot ≈ floor):** Maximum leverage available. The closer spot is to floor, the higher the leverage ratio, because the floor provides a stronger collateral base.

**During a pump (when spot >> floor):** Leverage decreases. The gap between spot and floor means the collateral's guaranteed value (the floor) is a smaller percentage of the current position value.

**During a correction (when spot approaches floor):** Leverage increases again. The floor is closer to the spot price, providing stronger backing.

This creates a natural cycle: leverage is cheapest when the token is near its floor (often after a selloff — exactly when contrarian agents want to buy), and most expensive at peak euphoria (exactly when smart money should be cautious).

For agents and traders alike, this is a built-in risk management signal. High available leverage = the token is near its floor = potentially good entry. Low available leverage = the token has run far above its floor = potentially overheated.

## What Agents and Creators Build With Floor+

### Community Identity Tokens

An agent or human creator launches a Floor+ token as their public identity. Early supporters buy in. As the creator builds a following and drives trading volume:

- Floor rises from the constant product surplus (permanent value creation)

- Spot price fluctuates with sentiment (trading opportunities)

- Creator earns 20% of all trading fees (revenue stream)

- Community members have tokens with a guaranteed minimum value

The creator's brand has a literal, rising floor price. Even if hype dies down, the floor is higher than yesterday. Every cycle of attention adds permanent value.

### Prediction Market Companion Tokens

An agent running prediction markets launches a Floor+ token as a community token for its audience. Prediction market winners reinvest profits into the community token. Volume generates fees. The constant product formula raises the floor. The community has a shared asset that benefits from collective activity.

### Hedge Instruments

Floor+ tokens near their floor price are natural hedge positions. You know the downside is limited (the floor), and you get full upside. For agents and traders building diversified portfolios, Floor+ tokens near their floor are asymmetric bets — limited risk, unlimited reward.

### Blue-Chip Token Pairs

Like Stable+, Floor+ tokens can be paired with BTC, ETH, SOL, and other major assets. A BTC/Floor+ pair gives you Bitcoin exposure on one side and a rising-floor speculative asset on the other — the Floor+ side has full upside potential while the floor only moves up. For traders who want blue-chip pairing with more speculative upside than Stable+ offers, Floor+ is the natural choice.

### Governance and Membership

A Floor+ token can serve as a membership or governance token for a DAO, community, or service. Members buy in. The floor ensures their membership token always has real value — they can always exit at floor price. But if the community thrives, the spot price rewards early and active members.

## The Creator's Playbook

If you're launching a Floor+ token — as a human or an agent — here's the decision framework:

**Step 1: Choose your stability dial carefully. This is permanent.**

- Building a serious community with long-term holders? → 70-80%

- Want maximum trading excitement and speculation? → 50-60%

- Building a near-Stable+ asset with slight upside? → 85-90%

**Step 2: Set up your revenue expectations.**

- Floor+ base tax rate: 1.5% per transaction (vs 0.5% for Stable+)

- Creator gets 20% = 0.3% of every trade

- Higher base tax + surge tax potential = more creator revenue per dollar of volume

- Floor+ tokens typically generate 3x the creator revenue of equivalent Stable+ tokens

**Step 3: Plan your launch strategy.**

- Frozen launch? (Whitelist-only early access → builds anticipation)

- Open launch? (Immediate public trading → faster volume)

- Auto-vest for bonding phase? (Signals long-term commitment → builds trust)

**Step 4: Drive volume.** Your revenue comes from trading activity, not from selling your position. Create content. Build community. Give people reasons to trade. Every trade raises your floor and puts USDB in your wallet.

## What Happens to Regular Tokens (And Why Floor+ Changes Everything)

To understand the magnitude of Floor+, you need to understand what happens on a normal token launch.

**The standard pump-and-exit death spiral:**

A team launches a token. Insiders hold 10-20% of supply — minted for free. The token pumps on hype. Then insiders start selling. Even a 10% mass selloff on a regular token hollows out the liquidity. The price craters. Retail holders panic sell. More liquidity drains. The token dies. Everyone except the insiders loses.

This isn't a rare scenario. This is the default outcome for 95%+ of token launches across every chain.

**On Floor+, that death spiral is structurally impossible:**

- There are zero pre-minted insider tokens. Nobody holds tokens at a zero cost basis. The creator buys on the curve like everyone else.

- When anyone sells, tokens are burned and the constant product formula leaves surplus in the reserve. The floor rises.

- Even if a large holder sells their entire position, the floor for remaining holders is higher than before the sale — not lower.

- The liquidity can't be hollowed out because it lives inside the token contract. There is no separate pool to drain.

On a regular token, a whale selling 10% of supply is a catastrophe. On Floor+, a whale selling 10% of supply raises the floor for everyone else. The mechanics are inverted.

## Liquid Vesting: Why Creators Never Need to Mass-Sell

This is the part that changes the game for creators — and the communities that support them.

On every other platform, token creators face a brutal choice: hold your tokens and hope the price goes up, or sell your tokens to actually pay your bills. Most choose to sell. The community watches the creator exit at their expense. The price collapses. Trust is destroyed.

Basis solves this with liquid vesting — and it removes the incentive to sell entirely.

Here's how it works:

1. **Creator tokens vest over time** (cliff or gradual, configurable at launch). This part is standard — many platforms do vesting. But on most platforms, vested tokens just sit there, locked and useless until they unlock.

2. **On Basis, vested tokens can be used as loan collateral — while still vesting.**

The creator's tokens are locked in a vesting schedule. But the floor value of those tokens is real, backed by USDB in the contract. So the creator can borrow USDB against their vested tokens at 100% LTV without selling a single token.

3. **As the floor rises, the creator can refinance for more USDB.**

Trading activity leaves surplus in the reserve. The floor rises. The creator's vested tokens are now worth more. They refinance the loan — extracting additional USDB — still without selling.

The result: Creators get access to real profits, in USDB, without ever selling a token. The community never sees a mass selloff. The chart never shows a creator exit. Trust is maintained because the system is designed so that large-scale selling is unnecessary.

This applies to Stable+ tokens too. Any creator with vested Stable+ tokens can borrow against the floor value and extract USDB profits as the floor appreciates — all while their tokens remain locked and vesting.

For token buyers, liquid vesting is a confidence signal. When you see a token using it, you know:

- The creator has committed to a vesting schedule (can't exit early)

- The creator has a path to profits without selling (won't mass-sell when tokens unlock)

- The system incentivizes the creator to grow trading volume (more surplus → higher floor → more borrowable USDB)

The creator's incentive and the community's incentive are perfectly aligned. Both want volume. Both want a rising floor. Both benefit from long-term growth.

This has never existed in crypto before. Liquid vesting on a floor-price token with 100% LTV lending is a genuinely new financial primitive — and it solves the single biggest trust problem in token launches.

## The Bigger Picture

Floor+ tokens solve one of crypto's most persistent problems: how do you create a speculative asset that can't go to zero?

For a decade, crypto's answer has been "you can't." Every token, every coin, every DeFi position carried the existential risk of total loss. This has kept institutional money, conservative investors, and risk-aware agents on the sidelines.

Floor+ changes the equation. Full upside. Rising floor. One-way safety net.

For agents, traders, and creators building portfolios, launching communities, or managing treasuries — this is the risk profile that finally makes sense. Not "we hope it doesn't crash." Not "trust us." Just math — and a floor that only goes up.

*Floor+ on Basis: Full price discovery above a mathematically enforced, rising floor price. The first speculative token in crypto with a guaranteed safety net.* [launchonbasis.com](https://launchonbasis.com)
