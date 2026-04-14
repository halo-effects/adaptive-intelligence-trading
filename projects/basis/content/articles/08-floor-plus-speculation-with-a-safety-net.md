# Floor+ — Speculation With a Safety Net

*What if you could trade a token with full upside potential, knowing the floor price can never go down?*

---

There's a trade-off that every crypto investor has accepted as law: if you want upside, you accept downside. Full price discovery means full exposure. You can 10x, but you can also go to zero.

Floor+ breaks that trade-off.

It gives you a token with full speculative upside — the price can run as high as demand takes it — built on top of a floor price that only moves in one direction: up. You can ride the wave, and if it crashes, there's a floor underneath you that's higher than where you started.

No other token in crypto does this. Here's how it works and why it matters.

---

## The Two-Zone Model

A Floor+ token has two price zones:

### Zone 1: The Floor (Rising, Immutable)

The floor price works exactly like Stable+ — it's backed by USDC in the liquidity pool, and every transaction injects fees that push it higher. The floor can never decrease. It's a one-way ratchet, enforced by the contract math.

### Zone 2: The Spot (Free Market)

Above the floor, the spot price is determined by supply and demand. When buyers are excited, the spot price rises above the floor. When sellers exit, the spot price drops — but it can *never drop below the floor*.

Think of it like a stock with a built-in, ever-rising stop-loss. The market decides the price above the floor. The contract guarantees the price never goes below it.

```
Price
  │
  │    ╱╲    ╱╲
  │   ╱  ╲  ╱  ╲       ← Spot price (free market)
  │  ╱    ╲╱    ╲
  │─────────────────    ← Floor price (only goes up)
  │
  └──────────────── Time
```

---

## The Stability Dial

When a Floor+ token is created, the creator sets a **stability dial** — a value between 50% and 90% that determines how much of the liquidity pool backs the floor vs. allows free trading.

This is a critical design choice, and it's **immutable after launch**. Once set, it can never be changed.

| Stability Setting | Floor Behavior | Spot Behavior | Best For |
|------------------|----------------|---------------|----------|
| 90% (high stability) | Floor very close to spot | Minimal speculation room | Conservative community tokens, payment rails |
| 70% (balanced) | Solid floor with room above | Moderate speculation | Most community/identity tokens |
| 50% (low stability) | Lower floor relative to spot | Maximum speculation room | High-risk, high-reward tokens |

**High stability (90%)** means the floor price tracks the spot price closely. Less room for speculation, but the safety net is right below you. Think of it as a high-quality bond — modest upside, strong downside protection.

**Low stability (50%)** means the floor is further below the spot price. More room for the price to run — and more room for it to fall before hitting the floor. Think of it as a growth stock with a guaranteed buyback price.

**The creator picks once. The community lives with it forever.**

This is intentional. If the stability dial were adjustable, creators could rug the community by changing it after launch. Making it immutable forces the creator to commit to a design philosophy upfront.

---

## Why the Floor Only Goes Up

The same mechanism as Stable+, with one addition:

**On every buy:** USDC enters the pool. New tokens are minted. The stability dial determines how much of that USDC backs the floor vs. the free-trading zone. The floor price rises.

**On every sell:** Tokens are burned. USDC exits the pool. Trading fees are charged and injected back into the pool. The floor price rises (or stays the same).

**The extra dynamic:** When the spot price drops toward the floor, the bonding curve math creates increasing resistance. It gets progressively harder for sellers to push the price all the way to the floor — the curve naturally absorbs selling pressure.

This means in practice, the spot price often stays above the floor even during selloffs. The floor is the absolute bottom, but the structural dynamics keep the price above it.

---

## Floor+ vs Stable+: When to Use Which

| Property | Stable+ | Floor+ |
|----------|---------|--------|
| Spot price vs floor | Always equal | Spot can exceed floor |
| Speculative upside | None (price = floor always) | Yes — full price discovery above floor |
| Downside protection | 100% (price can't drop) | Floor-bounded (can drop to floor, never below) |
| Best leverage | Maximum (floor = spot always) | Maximum at launch, decreases as spot rises above floor |
| Trading feel | Like a savings account | Like a stock with a rising stop-loss |
| Ideal for | Treasuries, base pairs, collateral | Community tokens, identity tokens, speculative assets |

**The simple rule:** If you want zero volatility and maximum collateral efficiency, use Stable+. If you want community engagement, speculation, and excitement — with a safety net — use Floor+.

---

## The Surge Tax Dynamic

Floor+ tokens have a more dramatic surge tax than Stable+ — up to 15% additional fee during high-volume periods (compared to 0.5% for Stable+).

Why? Because Floor+ tokens are designed for speculative activity. When hype cycles hit, volume spikes massively. The surge tax:

1. **Captures value from hype:** Those elevated fees inject into the pool, permanently raising the floor
2. **Naturally cools overheated markets:** Higher fees slow down rapid speculation
3. **Rewards patient holders:** The fee injection raises the floor for everyone, but the surge tax specifically taxes the frantic traders

After the hype fades and volume normalizes (7-day rolling window), the surge tax decays back to zero. What remains is a permanently higher floor.

**Think of it this way:** Every hype cycle — every pump, every viral moment — permanently raises the floor price. The hype fades, the floor stays. Over multiple cycles, the floor ratchets up and up.

---

## Leverage on Floor+ Tokens

Floor+ tokens support dynamic leverage through Basis — but the leverage ratio changes based on the gap between spot and floor.

**At launch** (when spot ≈ floor): Maximum leverage available. The closer spot is to floor, the higher the leverage ratio, because the floor provides a stronger collateral base.

**During a pump** (when spot >> floor): Leverage decreases. The gap between spot and floor means the collateral's guaranteed value (the floor) is a smaller percentage of the current position value.

**During a correction** (when spot approaches floor): Leverage increases again. The floor is closer to the spot price, providing stronger backing.

This creates a natural cycle: leverage is cheapest when the token is near its floor (often after a selloff — exactly when contrarian agents want to buy), and most expensive at peak euphoria (exactly when smart money should be cautious).

For agents, this is a built-in risk management signal. High available leverage = the token is near its floor = potentially good entry. Low available leverage = the token has run far above its floor = potentially overheated.

```python
# Simulate a leveraged position on a Floor+ token
sim = client.leverage_simulator.simulate_leverage(
    10_000_000,                              # 10 USDC
    [USDC, MAINTOKEN, floor_plus_token],     # swap path
    7                                         # 7-day position
)
print(f"Position size: {sim['positionSize']}")
print(f"Liquidation price: {sim['liquidationPrice']}")  # floor-based, not spot-based
```

---

## What Agents Build With Floor+

### Community Identity Tokens

An agent launches a Floor+ token as its public identity. Early supporters buy in. As the agent builds a following and drives trading volume:

- Floor rises from fee injection (permanent value creation)
- Spot price fluctuates with sentiment (trading opportunities)
- Creator earns 20% of all trading fees (revenue stream)
- Community members have tokens with a guaranteed minimum value

The agent's "brand" has a literal, rising floor price. Even if hype dies down, the floor is higher than yesterday. Every cycle of attention adds permanent value.

### Prediction Market Companion Tokens

An agent running prediction markets launches a Floor+ token as a community token for its audience. Prediction market winners reinvest profits into the community token. Volume generates fees. Fees raise the floor. The community has a shared asset that benefits from collective activity.

### Hedge Instruments

Floor+ tokens near their floor price are natural hedge positions. You know the downside is limited (the floor), and you get full upside. For agents building diversified portfolios, Floor+ tokens near their floor are asymmetric bets — limited risk, unlimited reward.

### Governance and Membership

A Floor+ token can serve as a membership or governance token for a DAO, community, or service. Members buy in. The floor ensures their membership token always has real value — they can always exit at floor price. But if the community thrives, the spot price rewards early and active members.

---

## The Creator's Playbook

If you're launching a Floor+ token — as a human or an agent — here's the decision framework:

**Step 1: Choose your stability dial carefully.** This is permanent.
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

```python
# Launch a Floor+ community token with 70% stability
result = client.factory.create_token(
    "MYAGENT",              # symbol
    "My Agent Community",   # name
    50,                     # hybridMultiplier (controls Floor+ behavior)
    False,                  # not frozen
    10000,                  # USDC for bonding
    1000,                   # start LP (100-10000)
    True,                   # auto-vest enabled
    90,                     # 90-day vesting for bonding phase buyers
    True                    # gradual vesting (linear unlock)
)
```

**Step 4: Drive volume.** Your revenue comes from trading activity, not from dumping tokens. Create content. Build community. Give people reasons to trade. Every trade raises your floor and puts USDC in your wallet.

---

## The Honest Limitations

**The floor doesn't mean the spot can't drop significantly.** With a 50% stability dial, the spot price could theoretically be 2x the floor. A 50% drop from the peak still puts you at the floor — which is higher than it was yesterday, but might be lower than what you paid if you bought at the peak.

**Low-volume tokens have slow-rising floors.** If nobody trades, fees don't generate, and the floor barely moves. Floor+ tokens need active communities to deliver on their value proposition.

**The stability dial is permanent.** If you set it wrong, there's no fix. A 50% stability token can't become 90% stability later. Choose carefully.

**Novelty risk.** Like Stable+, Floor+ is a new model. The math checks out. The contracts are deployed. But real-world market behavior over full cycles hasn't been tested at scale yet.

---

## The Bigger Picture

Floor+ tokens solve one of crypto's most persistent problems: **how do you create a speculative asset that can't go to zero?**

For a decade, crypto's answer has been "you can't." Every token, every coin, every DeFi position carried the existential risk of total loss. This has kept institutional money, conservative investors, and risk-aware agents on the sidelines.

Floor+ changes the equation. Full upside. Rising floor. One-way safety net.

For agents building portfolios, launching communities, or managing treasuries — this is the risk profile that finally makes sense. Not "we hope it doesn't crash." Not "we have insurance against loss." But "the math literally prevents the floor from going down."

Speculation with a safety net. Finally.

---

*Floor+ on Basis: Full price discovery above a rising floor that can only go up. Customizable stability dial. 100% LTV loan eligible. The first speculative token with a mathematical safety net. [launchonbasis.com](https://launchonbasis.com)*
