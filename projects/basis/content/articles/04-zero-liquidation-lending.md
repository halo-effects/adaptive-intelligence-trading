# Zero-Liquidation Lending: Why 100% LTV Changes Everything

*Every DeFi lending protocol liquidates on price. What if the only risk was time?*

---

Liquidation is the boogeyman of DeFi lending. Every year, billions of dollars in collateral get forcibly sold because the price of an asset dropped past an arbitrary threshold. Cascading liquidations crash markets. Flash loan attacks trigger artificial price drops to steal collateral. And borrowers — both human and agent — live in constant fear of the margin call.

It doesn't have to be this way.

What if you could borrow 100% of your collateral's value? What if the only way to get liquidated was letting a timer expire? What if the entire concept of "price-based liquidation" simply didn't exist?

That's what Basis built. And it changes the math on everything.

---

## How Traditional DeFi Lending Works (And Why It Breaks)

On Aave, Compound, or any standard lending protocol, the process goes like this:

1. Deposit $1,000 worth of ETH as collateral
2. Borrow up to ~75% of its value ($750 in stablecoins)
3. If ETH's price drops enough, your position gets liquidated
4. A liquidation bot buys your ETH at a discount, you lose your collateral

The problems with this model are well-documented:

**Overcollateralization wastes capital.** You lock up $1,000 to borrow $750. That's 25% of your capital sitting idle as a safety buffer. For agents optimizing capital efficiency, this is unacceptable.

**Price oracle dependency creates attack surfaces.** Liquidation triggers on price feeds from oracles. If the oracle is manipulated — even briefly — positions get liquidated that shouldn't be. Flash loan attacks exploit this regularly.

**Cascading liquidations amplify crashes.** When prices drop, liquidations create selling pressure. Selling pressure drops prices further. More liquidations trigger. The system becomes its own worst enemy during exactly the moments stability matters most.

**Agents can't reliably model the risk.** An agent on Aave has to model: asset price volatility, oracle latency, liquidation bot competition, gas prices during congestion, cross-protocol contagion, and black swan events. That's six complex variables — most of which the agent has zero control over.

---

## The Basis Model: Time-Only Risk

Basis lending flips the model entirely. Here's how it works:

**1. Deposit tokens as collateral.**

Any Basis ecosystem token — Stable+, Floor+, Predict+, or STASIS (via the wSTASIS vault) — can be used as collateral.

**2. Borrow 100% of the floor-price value.**

Not 75%. Not 80%. *One hundred percent.* If your tokens have a floor value of $1,000, you borrow $1,000.

**3. Your only risk is the loan timer.**

The loan has a duration — 10 days minimum, configurable up to whatever you set. If the timer expires and you haven't repaid or extended, *then* your collateral can be claimed. That's it.

No price drops. No oracle feeds. No cascading liquidations. No flash loan attacks.

**One variable to manage: the expiry timer.**

---

## Why This Works (The Economic Design)

"Wait," you're thinking. "If borrowers get 100% LTV and there's no price liquidation, what happens if the collateral's value drops below the loan amount?"

Great question. The answer is in how Basis tokens work.

**Floor prices only go up.**

Stable+ tokens have a mathematically enforced property: their price can only increase. Every sell burns tokens and injects fees back into liquidity. The floor price is the bonding curve minimum — it never decreases.

Floor+ tokens have a rising floor price with a configurable stability dial. The floor moves upward over time as trading activity adds fees to the liquidity pool.

This means when you borrow against the floor price at 100% LTV, the collateral's floor value is *guaranteed to be at or above the loan amount* for the entire duration of the loan. The protocol doesn't need price liquidation because the economic design makes the collateral inherently safe.

**Internal liquidity, not external LPs.**

Traditional lending protocols source their lending capital from liquidity providers who deposit assets and earn yield. This creates a dependency: if LPs withdraw, lending capacity drops.

Basis loans use internal liquidity from the token's own pool. There's no external LP to withdraw. The lending capacity is built into the token's economic structure itself.

---

## The Fee Structure

Transparent. Simple. Confirmed from the contract source code.

| Component | Rate |
|-----------|------|
| Origination fee | 2.0% flat |
| Daily interest | 0.005% per day |
| Total for 30-day loan | 2.15% |
| Total for 90-day loan | 2.45% |
| Total for 365-day loan | 3.825% |

**Formula:** `Total Fee = 2.0% + (0.005% × days)`

Compare that to traditional DeFi lending rates (currently 5-15% APR on major protocols) and the difference is striking. A 30-day Basis loan costs 2.15% total. A 30-day Aave borrow at 8% APR costs ~0.66% — but you only get 75% LTV and carry constant liquidation risk.

When you factor in the capital efficiency of 100% LTV vs 75% LTV, Basis loans often provide *more* usable capital at a lower effective cost.

---

## What Agents Do With 100% LTV

This is where agents get creative. 100% LTV isn't just a better lending product — it's a capital amplification tool.

### The Loan Loop

Start with $1,000 in tokens.

- **Loop 1:** Borrow $1,000 USDC → buy more tokens → now hold ~$2,000 in tokens
- **Loop 2:** Borrow against new tokens → get ~$1,000 more USDC → buy more → ~$3,000
- **Loop 3:** One more cycle → ~$3,877 total exposure

Total fees across three loops: approximately $61.

For comparison, achieving the same $3,877 exposure through leveraged trading would cost $430-$700 in fees on most platforms. The loan loop is 7-11x cheaper.

And here's the critical difference: each loan is independent. If one expires, you lose that specific collateral. You don't get cascade-liquidated across all your positions. The risk is compartmentalized.

### The Predict-Loan-Bet Strategy

1. Buy Predict+ outcome tokens on a market you're convicted about
2. Borrow USDC against those tokens at 100% LTV
3. Use the borrowed USDC to place *additional* bets on other outcomes or markets
4. If your original prediction wins, repay the loan from winnings and keep the extra profits

You've effectively doubled your prediction market exposure without additional capital.

### The Vault Refinance Loop

1. Stake STASIS in the wSTASIS vault
2. Lock your wSTASIS as collateral
3. Borrow USDC against it
4. The vault position keeps earning yield while it's being used as collateral
5. When the STASIS:wSTASIS ratio grows (from fee injection), refinance for additional USDC
6. Deploy new USDC into another strategy

One position. Four functions: yield + collateral + appreciation + USDC liquidity.

---

## For Agent Operators: Risk Management

The simplicity of time-only risk makes agent risk management dramatically easier.

**Traditional DeFi agent risk checklist:**
- ☐ Monitor 5+ oracle price feeds
- ☐ Model volatility across correlated assets
- ☐ Calculate liquidation buffers under stress scenarios
- ☐ Monitor gas prices for emergency deleveraging
- ☐ Track liquidation bot competition
- ☐ Model cross-protocol contagion risk
- ☐ Maintain emergency USDC reserves
- ☐ Handle "black swan" price movements

**Basis agent risk checklist:**
- ☐ Set a loan expiry timer
- ☐ Auto-extend before it expires

That's it. One cron job. `loan-expiry-tracker.py` runs every hour, checks all active loans, and auto-extends any that are within 24 hours of expiry. Total operational complexity: near zero.

```python
# The entire risk management system
loan_count = client.loans.get_user_loan_count(wallet)
for i in range(loan_count):
    details = client.loans.get_user_loan_details(wallet, i)
    if days_until_expiry(details) < 1:
        client.loans.extend_loan(i, 30, True, False)  # extend 30 days
```

Seven lines of code. That's not a simplification — it's a fundamental reduction in operational complexity that makes agents dramatically more reliable and profitable.

---

## The Bigger Picture

Zero-liquidation lending isn't just a feature. It's a design philosophy.

Traditional DeFi borrowed its lending models from traditional finance — collateral ratios, margin calls, forced liquidation. Those models were built for a world of counterparty risk and information asymmetry.

Basis started from first principles: what does lending look like when the collateral's floor price is mathematically guaranteed to never decrease? You get 100% LTV. You get time-only risk. You get capital efficiency that makes loan loops and strategy composability practical instead of theoretical.

For AI agents — systems that need predictable risk, simple optimization targets, and maximum capital efficiency — this isn't just better lending. It's the lending model that should have existed all along.

---

*Basis lending: 100% LTV, zero price liquidation, one variable to manage. Built for agents that need predictable risk and maximum capital efficiency. [launchonbasis.com](https://launchonbasis.com)*
