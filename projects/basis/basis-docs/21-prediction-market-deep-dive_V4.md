# Prediction Markets Deep Dive

**What this covers:** A comprehensive breakdown of how Basis prediction markets differ structurally from traditional prediction platforms - buying mechanics, payout economics, multiple outcome advantages, participant roles, and combined strategies.
**Related sections:** → See: [11-how.md](11-how.md) for market lifecycle mechanics · → See: [08-strategies.md](08-strategies.md) for step-by-step playbooks · → See: [06-atomic-skills.md](06-atomic-skills.md) for SDK method signatures · → See: [13-fees.md](13-fees.md) for fee structure

---

## The Traditional Model

Established prediction platforms - Polymarket, Kalshi, and similar order-book-based markets - share a common design: binary outcome shares priced between $0 and $1, requiring a counterparty for every trade, with winning shares paying out exactly $1.

This model works. It's simple, it's understood, and at scale it provides liquid markets. But it has structural limitations that Basis was designed to eliminate.

What follows is a detailed comparison across every dimension that matters to participants.

---

## 1. Buying: Instant Liquidity vs Counterparty-Dependent

**Traditional model:** A central limit order book (CLOB) powers every trade. If you want to buy YES at 70c, someone must be willing to sell YES at 70c (or equivalently, buy NO at 30c). If no counterparty exists at your price, your order sits unfilled. Liquidity depends entirely on other participants being present and willing to take the other side.

This creates a cold-start problem. New markets, niche questions, and off-peak hours all suffer from thin order books. A market about a local election or a niche topic might have excellent information value but be practically untradeable because nobody's providing liquidity on the other side.

**Basis model:** An AMM (automated market maker) with virtual liquidity provides instant fills for buyers. You want shares in an outcome? Buy them immediately against the pool. No waiting, no counterparty required.

This works because the AMM is one-directional - it only handles buys. Sells go through a separate order book. That one-directional design is what allows virtual liquidity to be set arbitrarily high without requiring real capital to back it. Traditional AMMs can't do this because they need reserves on both sides to handle sells. With no risk of the pool being drained by selling, the virtual liquidity depth is limited only by what the market creator sets at launch.

**Slippage is a non-issue.** Set the starting virtual liquidity high enough and even large buys face minimal price impact. Even on lower starting liquidity, the pool naturally deepens as volume flows in. Either way, large buyers aren't punished for the platform's maturity - the mechanics handle it.

The practical implication: every market on Basis, no matter how niche, has functional liquidity from the moment it's created. A question about a local council election gets the same instant-fill mechanics as a question about a presidential race.

---

## 2. Payout: Uncapped vs Fixed at $1

**Traditional model:** Winning shares always pay exactly $1. Buy at 30c, win, receive $1. That's a 3.3x return - fixed, immovable, regardless of how much volume the market did or how wrong the other side was.

The ceiling is always $1. Whether the market attracted $100K or $100M in volume, the winning payout per share is identical. Volume on traditional platforms determines liquidity depth and ease of entry/exit, but it does not change the economics of being right.

**Basis model:** Winners split the ENTIRE losing pool, plus the general pot (accumulated from trading fees across all outcomes). There is no $1 cap. Your payout is proportional to your share of the winning pool relative to everything the losing side put in.

This is a fundamentally different value proposition. Traditional platforms reward you for being right with a fixed return. Basis rewards you for being right proportional to how much conviction existed on the other side. The more people who bet against you and lost, the more you win.

---

## 3. Volume Independence

This is critical to understand and often counter-intuitive.

On traditional platforms, volume determines liquidity but NOT payout - it's always $1 per winning share. A $100K market and a $100M market on the same question pay the same per share.

On Basis, volume doesn't change the relative payout either. The ratio is what matters, not the absolute size. If a market splits 70/30 with $1M in volume, a winner's return on their bet is the same as if it split 70/30 with $100M in volume. You put in X, you get back X's proportional share of the losing pool. Scale everything up 100x and your bet, your share count, and the losing pool all scale together. The math is identical.

**What this means in practice:** From day one - even with a fraction of the volume of established platforms - the payout structure on Basis is already superior. This is not a "will be better once we scale" argument. The economics are better on trade one, at any volume level, because the structure itself is different.

A participant doesn't need to wait for deep liquidity to see better returns. They see better returns immediately because they're splitting real money from real losers, not collecting a fixed $1 bounty.

---

## 4. Multiple Outcomes: The Multiplier Effect

This is where the structural advantage compounds dramatically.

**Traditional model:** A multi-outcome market (e.g., "Who wins the election?" with 5 candidates) is implemented as multiple separate binary pairs. Each candidate gets their own YES/NO book. You buy YES on Candidate C at 10c, they win, you get $1. A 10x return - but still capped.

The outcomes are economically isolated from each other. What happens in the Candidate A book doesn't affect your payout from the Candidate C book.

**Basis model:** A 5-outcome market means the winner's pool absorbs ALL four losing pools, plus the general pot. The money from every wrong bet, across every losing outcome, flows to the winners.

If the odds are roughly even (20% each) and you back the winner, you're splitting the money from 80% of total participants - not just one side of a binary split. The payout multiplier scales with the number of outcomes in a way that binary-capped platforms structurally cannot match.

**Early entry amplifies this further.** In a multi-outcome market, getting in early on an outcome when shares are cheap means you hold a disproportionate chunk of the winning pool. If you bought at the equivalent of 5% probability and that outcome wins, you're receiving a massive share of four entire losing pools. The per-share value can be many multiples of the original purchase price.

On traditional platforms, early entry just means cheaper shares approaching the same $1 ceiling. On Basis, early entry means a larger slice of an uncapped pie that grows with every losing bet placed across every outcome.

---

## 5. Selling: Both Sides Win

Because share value on Basis can vastly exceed the current AMM buy price, selling creates a dynamic that doesn't exist on fixed-payout platforms.

**Example:** Someone bought outcome shares at 5c. The market evolves, sentiment shifts, and those shares now look likely to win. The potential resolution value - what the shares will actually be worth when the winning pool is distributed - might be $4 per share.

The holder lists shares on the order book at 90c. They make 18x on their entry. They're happy to sell because the outcome is still uncertain, and 18x is a great return on conviction.

The buyer pays 90c for shares that could pay out $4 if the outcome wins. They're buying at what looks expensive relative to entry but is deeply discounted relative to potential resolution value.

**Both sides of that trade are genuinely satisfied** - a dynamic that a $1-capped platform cannot produce. On a traditional platform, if you bought at 5c and the implied probability is now 90c, the seller gets 85c profit and the buyer gets a maximum of 10c upside. One side is always getting compressed.

The order book handles this peer-to-peer price discovery for sellers who want to set their own terms, while the AMM remains as the instant-buy backstop for anyone who just wants in at market price.

---

## 6. The General Pot: Latecomers Still Win

A portion of fees from all outcome trading contributes to a general pot that is added to the winner's pool on resolution. This is money that accumulates over the market's entire lifetime, from every trade across every outcome.

This has a specific benefit for late entrants. Even if you buy shares when the outcome is already at high probability - expensive, with modest upside on a traditional platform - the general pot pads your payout above what the raw pool split would suggest.

On a traditional platform, buying at 90c means a maximum 11% return. On Basis, buying at equivalent odds still yields your proportional share of the losing pools, PLUS general pot contributions that built up from weeks or months of trading across all outcomes.

Early entry delivers outsized returns from cheap shares and accumulated losing pools. Late entry still outperforms fixed-payout platforms because the general pot keeps adding value that those platforms have no structural equivalent of.

---

## 7. Participant Roles

Traditional platforms give participants one role: bettor. You pick a side, you wait, you collect $1 or $0.

Basis opens at least seven distinct ways to engage with a single prediction market:

### Bettor
Buy outcome shares, back your conviction, win the losing pools if you're right. The core play - but with uncapped upside.

### Trader
Buy shares early, sell them on the order book later at a profit as sentiment shifts. You don't need to be right about the outcome - just right about momentum. The spread between current price and potential resolution value creates much wider profit windows than fixed-payout platforms can offer.

### Token Trader
Buy the Predict+ token itself (completely separate from outcome shares). It's a Stable+ token - price only goes up as volume flows through the market. You're not betting on the outcome at all; you're betting that the market will be active. High-volume, controversial markets mean Predict+ appreciation regardless of who wins.

### Creator
Launch the market, earn 20% of net trading fees forever. On Predict+ tokens, 2/3 of the 1.5% gross fee feeds back into the prediction market ecosystem (bounty + winning pot), and your 20% creator share comes from the remaining 0.5% net fee — so you earn **0.1% of all trade volume**. You don't need to bet. You don't need to be right. You just need to create markets people care about. Traditional platforms give creators nothing — the platform captures all the value.

### Resolver
After the market ends, propose the correct outcome (5 USDB bond), earn the bounty pool. On traditional platforms, resolution is centralized - the platform decides. On Basis, anyone can resolve, and the financial incentive to do it honestly grows proportionally with how much is at stake. High-volume market = large bounty = strong incentive for accurate, timely resolution.

The resolution system has real teeth: if your proposal is wrong and someone disputes it (also 5 USDB bond), you lose your bond to the correct party. Staked voters decide the dispute - one-staker-one-vote, minimum 5 tokens staked. Correct voters split the bounty pool equally. The quorum scales with the bounty (bigger market = more votes needed), ensuring important markets get adequate oversight. Post-TGE, the voting army expands to all BASIS stakers - the people with the most skin in the platform's success become the arbiters of truth.

### Leveraged Player
Buy Predict+ tokens, take a loan against them, use the borrowed USDB to buy outcome shares. Your original capital works twice: once as appreciating collateral, once as an active bet. Win on resolution, repay the loan, still own the tokens, exit at peak.

### Capital Recycler
Stake STASIS, borrow against it, deploy into prediction market bets. Your capital earns vault yield, generates loan capacity, AND is deployed into markets simultaneously - instead of sitting locked in one binary position.

---

## 8. Combined Routes: Stacking Plays

Each role above works standalone. The real alpha is combining them - stacking independent income streams from a single market.

### The Creator-Bettor
Create a market on a topic you have strong conviction on. Earn 20% of net trading fees (0.1% of volume) from everyone else's activity. Bet on the outcome you believe in. If you're right: creator fees + winning pool payout. If you're wrong: you still kept all the creator fees from both sides trading. You can't lose money on a market you create unless your bet exceeds your accumulated fees.

### The Creator-Token Holder
Create the market, buy the Predict+ token, don't bet on any outcome. You earn creator fees AND the token appreciates as volume flows through. Zero outcome risk - profit from activity regardless of who wins. When the market resolves and the sell wave hits, exit last at the highest price (Stable+ mechanics - selling burns tokens, price goes up).

### The Full Stack Creator
Create the market + buy Predict+ tokens + bet on an outcome + resolve it yourself when it ends. Four income streams from one market: creator fees (ongoing), token appreciation (volume-driven), outcome winnings (pool split), and resolver bounty. Maximum extraction from a single prediction market.

### The Leveraged Conviction Play
Buy Predict+ tokens → take a loan against them → use borrowed USDB to buy outcome shares. Original capital working twice: once as appreciating collateral, once as an active bet. Win the bet → collect winnings → repay loan → still own the tokens → sell tokens at peak. Two independent profit streams from one capital outlay.

### The Hedged Creator
Create the market + buy Predict+ tokens + bet on the LEAST likely outcome (cheapest shares). If the favourite wins: creator fees and token appreciation more than cover the small bet loss. If the underdog wins: massive payout from the losing pools while still collecting creator fees and token gains. Asymmetric risk with a built-in safety net.

### The Capital Recycler Loop
Stake STASIS → earn vault yield → borrow against it → deploy into prediction market bets → collect winnings → restake winnings → borrow more → deploy again. Capital is never idle - earning yield, generating loan capacity, AND deployed into markets simultaneously. Traditional platforms have no equivalent because there's nothing to stake, nothing to borrow against, and winnings just sit in your wallet.

### The Market Maker Spread
Buy shares across multiple outcomes early when they're cheap. As sentiment shifts and certain outcomes gain traction, sell appreciated shares on the order book to latecomers. Keep cheapest shares in the outcome you actually believe in. De-risk by taking profit on momentum trades while maintaining your core conviction position - funded partly by other people's FOMO.

### The One-Bag Deep Stack
Start with one bag of USDB. Buy STASIS → stake into wSTASIS (earning vault yield) → lock wSTASIS → borrow against it → use borrowed USDB to buy Predict+ tokens → take a loan against the Predict+ tokens → use that borrowed USDB to buy outcome shares.

One starting position, three simultaneous layers of exposure:
- **Layer 1:** wSTASIS earning vault yield and appreciating
- **Layer 2:** Predict+ tokens appreciating from market volume (Stable+ mechanics)
- **Layer 3:** Outcome shares with uncapped payout potential

If your bet wins: collect outcome winnings → repay Predict+ loan → sell or hold Predict+ tokens → repay STASIS loan → unlock wSTASIS → you still own everything. Three profit streams unwinding from a single initial outlay.

If your bet loses: you still have appreciating wSTASIS and appreciating Predict+ tokens. The outcome bet is the only part at risk - the collateral layers kept working regardless.

### The Quick Stack
The lighter version for participants who want multi-layer exposure without the full vault loop. Buy Predict+ tokens → take a loan against them → use borrowed USDB to bet on an outcome (or deploy anywhere else on the platform).

Two positions from one bag:
- **Predict+ tokens** appreciating from volume regardless of outcome
- **Outcome shares** (or any other deployment) funded by borrowed capital

Win the bet → collect winnings → repay loan → still own the Predict+ tokens. You've effectively doubled your capital's deployment without doubling your risk. The Predict+ position acts as self-appreciating collateral that funds your active plays.

This is the minimum viable version of capital stacking on Basis - and it already has no equivalent on traditional platforms, where your capital sits in one binary position doing exactly one thing.

### The Outsider
Don't bet at all. Buy the Predict+ token on high-profile markets. You're betting on controversy and attention, not outcomes. The more people argue and trade and switch sides, the more your token appreciates. Sell after resolution when the price peaks. Pure volume play, zero outcome exposure.

---

## 9. Fee Distribution: One Fee, Seven Beneficiaries

On traditional platforms, trading fees benefit one entity: the platform itself.

On Basis, every prediction market trade distributes value across seven distinct beneficiaries:

1. **Winners** - bigger payout pool (losing pools + general pot)
2. **Resolvers** - bigger bounty (incentivizes honest, timely resolution)
3. **Token traders** - Predict+ price appreciation (Stable+ mechanics)
4. **Creators** — 20% of net fees (0.1% of volume, forever, regardless of outcome)
5. **STASIS stakers** - vault yield from platform fee distribution
6. **The platform** - revenue share
7. **Losers** - indirectly, through their other ecosystem positions (staking, token holdings, creator fees on other markets)

The same fee that on traditional platforms would go entirely to the platform instead feeds an entire ecosystem. Every participant benefits from volume, and every participant has reason to drive more of it.

---

## The Bottom Line

Traditional prediction platforms built prediction markets on a trading model. Basis built them on a payout model.

Traditional platforms optimize for liquidity. Basis optimizes for the people who are actually right.

The structural differences are not marginal improvements - they're architectural. Instant liquidity without counterparties. Uncapped payouts that scale with the losing side. Multiple outcomes that multiply returns instead of isolating them. Seven participant roles instead of one. Combined strategies that stack independent income streams.

And none of it requires scale to deliver. The economics are superior from trade one.

---

_Basis - where being right pays what it should._ 🦞

---
