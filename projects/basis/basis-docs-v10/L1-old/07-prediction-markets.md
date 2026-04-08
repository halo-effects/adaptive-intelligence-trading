# Prediction Markets — L1 What/Why/How

## WHAT: Prediction Markets

Prediction markets on Basis let anyone create a tradeable question — "Will ETH hit $5K by year end?", "Which project ships first?", anything with definable outcomes. Markets support up to 150 outcomes, trade via both AMM and P2P order book, and resolve through a decentralised dispute system.

Each market generates two separate assets: a Predict+ token (the market token, appreciates from volume) and outcome shares (what you buy to bet). The AMM handles buying shares — one-directional, instant liquidity from creation. The order book handles selling — P2P, price set by the seller.

Markets come in two flavours. Public markets use a proposal-dispute-vote resolution system open to anyone. Private markets let the creator and a whitelisted group of voters resolve directly. Both types generate creator fees and airdrop points.

Resolution works in phases: someone proposes an outcome with a 5 USDB bond. If nobody disputes during the challenge period, it finalises and the proposer earns a bounty. If disputed, staked token holders vote — 70% supermajority decides. Special outcomes include INVALID (proportional refund to all) and EARLY (resets the market for a fresh cycle).

## WHY: Why Would I Use Prediction Markets?

Because there are multiple ways to profit, and you don't need to be right about the prediction to make money.

**As a creator**: You earn 20% of all trading fees forever. You don't bet, you don't resolve, you just create compelling questions that people trade on. Controversial, high-volume markets generate the most revenue. This is a permanent passive income stream attached to every market you create.

**As a bettor**: Uncapped payouts change the economics fundamentally. On platforms like Polymarket, shares resolve to $1 — so a share at 90¢ can only gain 10¢. On Basis, all pools merge into one pot on resolution. A share bought at 5¢ could pay out $4+ depending on total pool size. Early conviction is richly rewarded.

**As a resolver**: Proposing correct outcomes earns bounties funded by trading fees. If your proposal goes uncontested, you keep the full bounty plus your bond. If it goes to a vote and you're on the winning side, you share the bounty with other correct voters. There's a financial incentive to resolve markets accurately and promptly.

**As a trader**: The Predict+ market token appreciates from volume regardless of which outcome wins. Active, contentious markets push the token price up. You can trade in and out based on market activity without ever touching outcome shares.

**Combining strategies**: Collateralise your Predict+ tokens to borrow USDB, then use that USDB to buy outcome shares. Your token position earns from volume, your shares carry the conviction bet, and the loan lets you deploy capital twice.

## HOW: How Do I Use Prediction Markets?

**Create a market**: Define your question, set the possible outcomes, choose an end time, and seed it with USDB to provide initial liquidity. The market goes live immediately. You can add metadata — description, image, links — and optionally start it frozen (whitelisted buyers only) until you're ready to open it up.

**Buy outcome shares**: Pick the outcome you believe in and buy shares through the AMM. You pay USDB and receive shares instantly. If you want to sell before resolution, list your shares on the order book at your chosen price — another user buys them P2P.

**Trade the market token**: Buy and sell the Predict+ token on the DEX like any other token. It's a Stable+ subtype, so the price can only go up. Trade based on market activity levels, not outcome conviction.

**Resolve a market**: After the end time passes, propose the correct outcome with a 5 USDB bond. If nobody disputes within the challenge period, you finalise and earn the bounty. If someone disputes, the market goes to a vote among staked token holders.

**Redeem winnings**: After resolution, if you hold winning outcome shares, redeem them for your proportional share of the entire merged pot — all outcome pools combined. The more winning shares you hold relative to total winning supply, the bigger your payout.

## Deep Dive

For full details, see these reference modules:
- [16-how-everything-works](../modules/16-how-everything-works.md) — market lifecycle, dispute phases
- [26-prediction-deep-dive](../modules/26-prediction-deep-dive.md) — structural comparison, uncapped payouts, strategy stacking
- [27-prediction-arb-engine](../modules/27-prediction-arb-engine.md) — cross-platform arbitrage
- [10-atomic-skills](../modules/10-atomic-skills.md) — Prediction Markets, Order Book, Market Resolver, Private Markets modules
- [13-strategy-playbooks](../modules/13-strategy-playbooks.md) — Polymarket Mirror, Predict Leverage strategies
- [25-code-examples](../modules/25-code-examples.md) — prediction market and resolver examples
