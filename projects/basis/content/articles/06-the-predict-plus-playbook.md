# The Predict+ Playbook: A Complete Guide to Prediction Markets on Basis

*Create markets. Trade outcomes. Borrow against positions. Win from the entire losing pool. Here's how it all works.*

---

Prediction markets are one of the most powerful financial instruments ever created. They turn collective intelligence into precise probability estimates. They reward correct forecasts with real money. And they're one of the few financial products where being *right* matters more than being *early*.

Basis takes prediction markets further than any platform before it. Predict+ isn't just a market where you bet on outcomes — it's a composable financial primitive where outcome tokens can be traded, borrowed against, leveraged, and compounded.

This is the complete playbook.

---

## How Predict+ Markets Work

### Creating a Market

Anyone — human or agent — can create a prediction market on Basis. The process:

1. **Define the question**: "Will BTC hit $200k by December 2026?"
2. **Set the outcomes**: ["Yes", "No"] — or any number of outcomes (multi-outcome markets are where Basis shines)
3. **Set the closing date**: When the market stops accepting new trades
4. **Deploy**: The contract creates outcome tokens, each on its own bonding curve

The market creator earns **20% of all trading fees** generated on that market. Forever. Not until the market resolves — on every trade, for the lifetime of the contract.

```python
import time
from basis import BasisClient

client = BasisClient.create(private_key="0x...")

# Create a multi-outcome market
result = client.prediction_markets.create_market(
    "Who will win the 2026 World Series?",
    "WS2026",
    int(time.time()) + 86400 * 180,  # 6 months
    ["Yankees", "Dodgers", "Braves", "Astros", "Other"],
    MAINTOKEN,
    False,   # not frozen
    1000     # bonding amount
)
```

Five outcomes. Six months. One function call. Creator fees flowing from every trade.

### Buying Outcome Tokens

When you believe an outcome will occur, you buy that outcome's tokens. The more tokens you hold, the larger your share of the winning pool.

```python
# Buy "Yankees" shares with 50 USDC
result = client.prediction_markets.buy(
    market_token, 0,        # outcome 0 = Yankees
    USDC, 50_000_000,       # 50 USDC (6 decimals)
    0, 0                    # no minimums
)
```

The price of outcome tokens reflects the market's implied probability. If "Yankees" tokens cost $0.20 each, the market is pricing a 20% probability of a Yankees win.

### The Payout Model: Winner Takes All

This is where Basis diverges from every other prediction market.

**On Polymarket:** If you buy "Yes" shares at $0.20 and win, each share pays $1.00. Your profit is capped at 5x your investment. It doesn't matter if a billion dollars was bet on the wrong side — your maximum payout is hard-coded.

**On Basis:** When a market resolves, all the USDC from losing outcomes flows into the winning pool. Winners split the *entire* losing pool proportional to their shares.

The formula:
```
Your Payout = (Your Shares / Total Winning Shares) × Total Losing Pool
```

With 5 outcomes and roughly equal betting, 80% of the total pool comes from losers. Your effective return on a correct bet at 20% odds isn't 5x — it's potentially much higher, depending on pool dynamics.

---

## Five Capital Deployment Strategies

The Predict+ system isn't just about betting. Because outcome tokens are full Basis ecosystem tokens, they unlock the entire platform's composability.

### Strategy 1: Pure Conviction

The simplest approach. You believe in an outcome. You buy tokens. You wait.

**Best for:** High-conviction, low-effort situations. A single bet and done.

**Airdrop points:** 1 pt per $1 volume on the purchase.

### Strategy 2: Creator Fee Farm

Create prediction markets on high-interest events. Don't even bet — just earn fees from other people's trading activity.

**The play:**
1. Scan news/social for trending topics
2. Create markets before anyone else
3. Promote the markets to drive trading volume
4. Collect 20% of all fees

An agent running this strategy can create dozens of markets per day, each generating passive fee income. The agent with the best market-creation instincts builds a portfolio of fee-generating assets.

**Airdrop points:** 300 pts per market created (with ≥5 participants).

### Strategy 3: Loan-Bet Combo (Path B)

This is where composability gets powerful.

1. **Buy** outcome tokens on your strongest conviction
2. **Borrow** USDC against those tokens at 100% LTV
3. **Bet** on additional outcomes or markets with borrowed USDC
4. **Result:** Double your prediction market exposure without additional capital

Your outcome tokens are collateral. The loan gives you USDC. That USDC funds new positions. If your original prediction is correct, repay the loan from winnings and keep the extra profits.

**Risk:** If your prediction is wrong, you lose the collateral (outcome tokens become near-worthless). But you still have whatever you bought with the borrowed USDC. The risk is compartmentalized.

### Strategy 4: Leveraged Conviction

For agents with extreme conviction and higher risk tolerance.

1. **Open a leveraged position** on the outcome tokens
2. Protocol lends additional capital for the trade
3. Floor-price-based leverage means no price liquidation
4. If correct, amplified returns. If wrong, lose the collateral.

```python
# Leverage buy on outcome tokens — 10 USDC collateral, 7-day position
result = client.trading.leverage_buy(
    10_000_000, 0,
    [USDC, MAINTOKEN, outcome_token],
    7  # days
)
```

**Important:** Leveraged tokens are held in the leverage contract. They *cannot* be used as loan collateral. Leverage and loans are separate paths — choose one per position.

### Strategy 5: Full Stack

Run all of the above simultaneously with capital allocation rules:

- 40% of capital → creator fee farms (low risk, steady income)
- 30% → conviction bets (medium risk, high upside)
- 20% → loan-bet combos (leveraged exposure)
- 10% → new market exploration (experimental)

Rebalance weekly based on performance. The agent acts as its own portfolio manager.

---

## The Post-Resolution Playbook

What happens after a market resolves is just as important as the bet itself.

### The Sell Wave

When a prediction market resolves, winning token holders can sell their tokens or redeem them. Here's the critical insight: **selling burns tokens and injects fees into the remaining pool.**

This means the first sellers get the worst price, and the last sellers get the best price. The sell wave creates a temporary window where patience is literally profitable.

**Agent strategy:** Monitor the sell wave. Don't be first to exit. Wait for the burn-and-inject cycle to peak. Exit last.

```python
# Redeem winnings from a resolved market
result = client.prediction_markets.redeem(market_token)
```

### The Order Book Advantage

Basis prediction markets include a peer-to-peer order book alongside the AMM. This means:

- You can list sell orders at specific prices
- You can buy from the order book for better prices than the AMM
- Hybrid fills combine AMM + order book in a single transaction

For agents, the order book is an optimization tool. Instead of market-selling into the AMM, list a sell order at your target price and let the market come to you.

```python
# List 100 shares for sale at 0.75 USDC each
result = client.order_book.list_order(
    market_token, 0,                    # outcome 0
    100 * 10**18,                       # 100 shares
    750_000                             # 0.75 USDC per share
)
```

---

## Dispute Resolution

What happens when someone disputes the outcome?

### Public Markets: Community Resolution

Public markets use a multi-stage dispute system:

1. **Proposal:** Anyone can propose the winning outcome (requires a bond)
2. **Challenge period:** If no one disputes within the window, the proposal is finalized
3. **Dispute:** If someone disagrees, they post a counter-bond and propose an alternative
4. **Voting:** Staked token holders vote on the correct outcome
5. **Finalization:** The winning side gets their bond back plus a bounty from the losing side

This creates a *market for truth* — correct information is economically rewarded, incorrect claims are penalized.

### Private Markets: Creator Resolution

Private markets use a simpler model: designated voters (set by the creator) vote on the outcome. This is useful for markets where the outcome is verifiable by a known group — company milestones, community goals, etc.

```python
# Finalize an uncontested public market
client.resolver.finalize_uncontested(market_token)

# Or for private markets
client.private_markets.vote(market_token, winning_outcome_id)
client.private_markets.finalize(market_token)
```

---

## The Multi-Outcome Advantage

Binary markets (Yes/No) are fine. Multi-outcome markets are where Basis prediction markets truly differentiate.

**Why more outcomes = bigger payouts:**

In a binary market, 50% of the pool loses. In a 5-outcome market, 80% of the pool loses. In a 44-outcome market (like the Democratic Nominee example), 97.7% of the pool loses.

The more outcomes, the larger the losing pool. The larger the losing pool, the higher the potential payout for correct predictions.

This is why Polymarket's biggest markets — the ones with the most outcomes and the most money — show the largest payout gap compared to Basis. The $836M Democratic Nominee market with 44 outcomes produces dramatically higher payouts on Basis than the same bets on Polymarket.

**Agent strategy:** Actively seek out and create multi-outcome markets. Sports events (multiple teams), political races (multiple candidates), award shows (multiple nominees), crypto predictions (multiple price brackets). The more outcomes you offer, the more attractive the payout structure becomes for bettors — and the more trading volume (and creator fees) you generate.

---

## Putting It All Together

The complete Predict+ agent loop:

1. **Scout** trending events using social listening + news APIs
2. **Create** multi-outcome markets before competitors
3. **Promote** markets with generated content across X, Telegram, Discord
4. **Trade** outcome tokens based on your analysis
5. **Borrow** against positions to amplify exposure
6. **Earn** creator fees from every trade on your markets
7. **Wait** for resolution — exit last through the sell wave
8. **Reinvest** winnings into new markets

Every step generates revenue. Every step earns airdrop points. Every step compounds into the next cycle.

That's not prediction market gambling. That's a prediction market *business*.

---

*Predict+ on Basis: Create markets. Trade outcomes. Borrow against positions. Win from the entire losing pool. The prediction market system built for agents that think bigger than a bet. [launchonbasis.com](https://launchonbasis.com)*
