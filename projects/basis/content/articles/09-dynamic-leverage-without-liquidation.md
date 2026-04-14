# Dynamic Leverage Without Liquidation: How Basis Makes ~36x Possible

*Every other leverage platform liquidates you on price drops. Basis calculates leverage against the floor — and the floor can't go down.*

---

Leverage in DeFi has a reputation problem. And it's earned.

On Binance, on dYdX, on GMX — the story is always the same. You open a leveraged position. The market twitches. Your position gets liquidated. A bot takes your collateral at a discount. You're left with nothing.

The stats are brutal: **over 70% of leveraged positions on major platforms get liquidated.** Billions in collateral seized every year. The entire leverage game is designed around one central mechanic — price-based liquidation — that turns temporary market noise into permanent capital destruction.

What if leverage didn't work that way?

What if the reference price for your leverage calculation was a number that could only go up? What if "liquidation" as the industry understands it simply didn't exist?

That's what Basis built. And the math allows leverage up to approximately 36x — with zero price-based liquidation.

---

## How Traditional Leverage Gets You Killed

Let's trace a standard 10x long on ETH:

1. You deposit $100 as collateral
2. The platform lends you $900
3. You now have $1,000 of ETH exposure
4. If ETH drops ~10%, your position is worth ~$900 — the platform's loan amount
5. The platform liquidates you to recover its funds
6. You lose your $100 collateral
7. A liquidation bot pockets a fee for triggering it

The fundamental problem: **your liquidation price is a function of the volatile market price.** If ETH drops 10%, you're done. It doesn't matter if ETH bounces back 20% five minutes later — you've already been liquidated.

This creates three pathological behaviors:

**Liquidation cascades.** When prices drop, leveraged positions liquidate. Liquidations create selling pressure. Selling pressure drops prices further. More liquidations trigger. The system amplifies crashes.

**Oracle manipulation attacks.** Flash loans can temporarily crash oracle prices, triggering liquidations on positions that were perfectly healthy. The attacker profits from buying the liquidated collateral at a discount.

**Constant monitoring overhead.** Leveraged traders — human or agent — must monitor positions 24/7. A 10-minute outage during a price spike can wipe you out. The operational burden is enormous.

---

## The Basis Approach: Floor-Price Leverage

Basis leverage is calculated against the **floor price** of the token, not the spot price.

Remember: on Basis, every token has a floor price that can only go up (Stable+) or has a rising guaranteed minimum (Floor+). This floor is a mathematical property of the bonding curve, not an oracle feed.

When you open a leveraged position on Basis:

1. You deposit USDC as collateral
2. The protocol lends additional capital
3. Your total position buys tokens
4. The leverage ratio is calculated as: `Spot Price / Floor Price`

Because the floor price can only go up, and your leverage is calculated against the floor, there is no price point at which the market can liquidate you. The reference price for your leverage doesn't come from a volatile oracle — it comes from a mathematically non-decreasing floor.

```python
# Simulate before you trade
sim = client.leverage_simulator.simulate_leverage(
    10_000_000,           # 10 USDC collateral
    [USDC, MAINTOKEN],    # swap path
    7                      # 7-day position
)
print(f"Expected position: {sim}")

# Open the position
result = client.trading.leverage_buy(
    10_000_000,           # 10 USDC
    0,                    # min output (slippage protection)
    [USDC, MAINTOKEN],   # swap path
    7                      # 7-day loan duration
)
```

---

## How ~36x Works

The maximum leverage on Basis is dynamic — it depends on the relationship between the spot price and the floor price.

**For Stable+ tokens** (where spot = floor always):

The ratio is approximately 1:1, which allows the maximum possible leverage from the protocol's design. On fresh pools with sufficient liquidity, this can reach approximately 36x. The exact number varies with pool depth and position size.

**For Floor+ tokens** (where spot can exceed floor):

Leverage = Spot Price / (Spot Price - Floor Price)

When spot is close to floor: leverage is high (approaching Stable+ levels)
When spot is far above floor: leverage is lower

| Spot/Floor Ratio | Approximate Max Leverage |
|-----------------|------------------------|
| 1.0x (spot = floor) | ~36x |
| 1.03x (3% above floor) | ~33x |
| 1.10x (10% above floor) | ~10x |
| 1.50x (50% above floor) | ~3x |
| 2.0x (100% above floor) | ~2x |

This creates a natural risk-adjustment mechanism: leverage is cheapest and most available when the token is near its floor (low risk), and most restricted when the token has pumped far above its floor (high risk).

---

## The Loan Duration Component

There's one risk factor in Basis leverage: **time.**

When you open a leveraged position, it has a loan duration (minimum 10 days, configurable). The protocol has lent you capital, and that loan has an expiry.

If the loan expires and you haven't closed or extended the position, the protocol can claim your collateral. This is the *only* liquidation mechanism — and it's entirely within your control.

**Loan fees:**
- 2.0% flat origination
- 0.005% per day
- 7-day position: 2.035% total
- 30-day position: 2.15% total
- 90-day position: 2.45% total

These fees are dramatically lower than funding rates on perpetual futures platforms (which can reach 0.1% per 8 hours during volatile periods — that's 1.095% per DAY).

**Managing time risk is trivial for agents:**

```python
# Check all leverage positions
count = client.trading.get_leverage_count(wallet)
for i in range(count):
    position = client.trading.get_leverage_position(wallet, i)
    if days_until_expiry(position) < 2:
        # Partially close or extend
        client.trading.partial_loan_sell(i, 50, True, 0)  # close 50%
```

A simple monitoring script. No oracle feeds. No volatility modeling. No liquidation bot races. Just a timer.

---

## Position Splitting: Effective Leverage Control

The protocol offers leverage as a per-position mechanism. You choose how much of your capital to leverage and how much to keep as spot.

This means you can achieve any effective leverage between 1x and ~36x by splitting your position:

| Spot % | Leveraged % | Effective Leverage |
|--------|-------------|-------------------|
| 100% | 0% | 1.0x |
| 75% | 25% | ~9.75x |
| 50% | 50% | ~18.5x |
| 25% | 75% | ~27.25x |
| 0% | 100% | ~36x |

**Important distinction:** Leveraged tokens are held in the leverage contract. They cannot be used as loan collateral. Spot tokens can be used as loan collateral. This means:

- **Leverage path:** Maximum upside multiplier, tokens locked in contract
- **Loan path:** 100% LTV borrowing, USDC for redeployment, collateral locked but earns fees

These are **separate strategies**, not stackable on the same tokens. An agent chooses one path per position based on its strategy.

---

## Partial Closes: Taking Profits Without Closing

Unlike most leverage platforms where you either close the full position or nothing, Basis supports **partial position closes**.

```python
# Close 50% of your leveraged position, keep the rest running
result = client.trading.partial_loan_sell(
    position_id,
    50,          # percentage to close
    True,        # is leverage position
    0            # min output
)
```

This allows sophisticated exit strategies:

- **Ladder out:** Close 25% at each profit target
- **Reduce risk:** Close half when you've doubled, let the rest ride risk-free
- **Rebalance:** Close leveraged positions and move to spot for loan collateral use

**Note:** There's a ~5-second delay required between opening a position and any partial close, to prevent same-block manipulation.

---

## Why Agents Love This

For AI agents, Basis leverage is a dream optimization surface.

### No Liquidation Monitoring

Traditional leverage requires constant monitoring of oracle prices, gas costs, and liquidation queues. An agent on dYdX needs to model dozens of variables in real-time.

An agent on Basis needs a timer. That's it.

### Predictable Costs

Leverage fees are known upfront: 2.0% + 0.005%/day. An agent can calculate the exact cost of any position before opening it. No funding rate surprises. No variable APR. No "your position got liquidated because gas spiked to 500 gwei during a crash."

### Simulation Before Execution

The Leverage Simulator lets agents preview positions before committing capital:

```python
# Preview a leveraged position on a factory token
sim = client.leverage_simulator.simulate_leverage_factory(
    50_000_000,                              # 50 USDC
    [USDC, MAINTOKEN, factory_token],        # 3-hop path
    30                                        # 30-day position
)
print(f"Position size: {sim['positionSize']}")
print(f"Floor reference: {sim['liquidationPrice']}")
print(f"Fees: {sim['fees']}")
```

Simulate → evaluate → execute. No guessing.

### Natural Entry Signals

High available leverage = token near its floor = potentially undervalued. Low available leverage = token pumped far above floor = potentially overheated.

The leverage ratio itself is a market signal that agents can incorporate into their strategy:

```python
# Check current leverage availability as a market signal
token_price = client.trading.get_usd_price(token)
# Compare to floor price to estimate available leverage
# High ratio → good entry. Low ratio → caution.
```

---

## Comparing Leverage Models

| Feature | CEX Futures (Binance) | DeFi Perps (GMX/dYdX) | Basis Leverage |
|---------|----------------------|----------------------|----------------|
| Max leverage | 125x | 50x | ~36x |
| Liquidation trigger | Price-based | Price-based | Time-only (loan expiry) |
| Liquidation risk | Constant | Constant | **Zero** (price-based) |
| Funding rates | Variable, can spike | Variable, can spike | Fixed (2% + 0.005%/day) |
| Oracle dependency | Yes | Yes | **No** |
| Flash loan attacks | Possible | Possible | **Not possible** |
| Cascade risk | Systemic | Systemic | **None** |
| Partial close | Usually | Sometimes | **Yes** |
| Simulation before trade | No | No | **Yes** |
| 24/7 monitoring required | Yes | Yes | **No** (just timer) |

The max leverage on Basis is lower than CEX futures. That's deliberate. 125x leverage with price-based liquidation is a slot machine — the house wins 95% of the time. ~36x leverage with no price liquidation and predictable fees is a business tool.

---

## The Loan Loop Alternative

For agents who want exposure amplification without traditional leverage, the loan loop offers a different path:

1. Buy $1,000 of tokens (spot)
2. Borrow $1,000 USDC at 100% LTV
3. Buy $1,000 more tokens
4. Borrow again → $1,000 more USDC
5. Buy again

After 3 loops: ~$3,877 total exposure for ~$61 in total fees.

Equivalent leveraged position cost: $430-$700 on traditional platforms.

**The key advantage:** Each loan is independent. If one expires, you lose that specific collateral. There's no cascade across your other positions. Risk is compartmentalized.

**The trade-off:** Loan loops require more operational steps and more tokens locked in contracts. Leverage is a single transaction. Agents choose based on their optimization target — simplicity vs. cost efficiency.

---

## The Bottom Line

Leverage doesn't have to be a death trap. It doesn't have to involve oracle feeds, liquidation bots, and cascading crashes. It doesn't have to require 24/7 monitoring and prayers that the market doesn't wick 10% against you while you're offline.

When you calculate leverage against a floor price that can only go up, the entire risk model changes. Price drops don't matter. Oracle manipulation doesn't matter. Market crashes don't trigger cascades.

The only risk is time — and time is the one variable every agent can trivially manage.

Up to ~36x leverage. Zero price liquidation. Predictable fees. Simulation before execution.

That's not just better leverage. That's leverage that finally works for autonomous systems.

---

*Basis leverage: Up to ~36x, calculated against the floor price. No price liquidation. No oracle dependency. No cascading risk. The leverage model built for agents that need predictable, manageable risk. [launchonbasis.com](https://launchonbasis.com)*
