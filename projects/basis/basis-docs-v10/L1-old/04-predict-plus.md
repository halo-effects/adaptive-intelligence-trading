# Predict+ & Outcome Shares — L1 What/Why/How

## WHAT: Predict+ & Outcome Shares

Every prediction market on Basis creates two distinct assets. The first is a **Predict+ token** — a Stable+ subtype whose price can only go up, driven by trading volume on the market. The second is **outcome shares** — these are what you actually buy to bet on a specific result.

The two are completely separate. Trading the Predict+ token is a volume play — you're betting on market activity, not on who wins. Buying outcome shares is a conviction play — you're betting on a specific outcome being correct.

On resolution, all outcome pools merge into one big pot. Winners claim their proportional share of the entire pot — not a capped $1 per share like Polymarket. A share bought at 5¢ can pay out $4+ if the pot is large enough. This uncapped payout model means conviction sizing actually matters.

Buying shares happens through a one-directional AMM (instant fills, no counterparty needed). Selling shares happens on a P2P order book. This separation means buy liquidity is always available from creation, while sell prices reflect real market conviction.

## WHY: Why Would I Use Predict+ & Outcome Shares?

Because you can play both sides of a prediction market independently — and both can be profitable regardless of which outcome wins.

**As a token trader**: The Predict+ token appreciates from trading volume alone. A controversial, high-activity market pushes the token price up whether the outcome is yes, no, or invalid. You don't need to be right about the prediction — you just need to identify markets that will attract attention.

**As a bettor**: Uncapped payouts change the math entirely. On capped platforms, a 95% consensus outcome pays almost nothing. On Basis, the winning pot absorbs all losing pools, so even high-probability bets can return multiples if the total pool is large. Early conviction is rewarded — buying shares cheap before consensus forms is the edge.

**As a creator**: You earn 20% of every trade fee on your market forever (0.1% of all trade volume). You don't need to bet. You don't need to be right. You just need to create markets people care about. Controversial questions with natural disagreement generate the most volume and the most creator revenue.

**As a strategist**: You can collateralise your Predict+ tokens — take a loan against them, use the borrowed USDB to buy outcome shares, and have your capital working twice. The token can't lose value (it's Stable+), so the loan is low-risk while your outcome shares carry the conviction bet.

## HOW: How Do I Use Predict+ & Outcome Shares?

**To trade the market token**: Buy Predict+ tokens like any other token on the DEX. Hold while market activity is high, sell when volume peaks. The token appreciates from every trade — buy or sell — so active markets are what you're looking for.

**To bet on an outcome**: Buy outcome shares for the result you believe in. You pay USDB and receive shares in your chosen outcome. Hold to resolution — if your outcome wins, redeem your shares for your proportional cut of the entire merged pot. If you change your mind before resolution, list your shares on the order book at whatever price the market will bear.

**To create a market**: Define your question, set the outcomes (up to 150), choose an end time, and seed it with USDB for initial liquidity. Your market goes live immediately. You start earning creator fees from the first trade.

**To resolve a market**: After the end time, anyone can propose an outcome by posting a 5 USDB bond. If nobody disputes within the challenge period, the proposal finalises and the proposer earns a bounty. If disputed, it goes to a vote among staked token holders — 70% supermajority decides.

## Deep Dive

For full details, see these reference modules:
- [03-what-is-basis](../modules/03-what-is-basis.md) — Predict+ token lifecycle, pool merging
- [26-prediction-deep-dive](../modules/26-prediction-deep-dive.md) — structural comparison, 7 participant roles
- [27-prediction-arb-engine](../modules/27-prediction-arb-engine.md) — cross-platform arb strategies
- [12-defi-primitive-playbooks](../modules/12-defi-primitive-playbooks.md) — Predict+ dual-profit structure
- [18-fee-cost-reference](../modules/18-fee-cost-reference.md) — Predict+ fee breakdown
