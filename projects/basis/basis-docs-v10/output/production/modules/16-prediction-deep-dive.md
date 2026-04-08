# Prediction Markets Deep Dive

**What this covers:** A comprehensive breakdown of how Basis prediction markets differ structurally from traditional prediction platforms - buying mechanics, payout economics, multiple outcome advantages, participant roles, and combined strategies.
**Related sections:** → See: [12-how-everything-works.md](12-how-everything-works.md) for market lifecycle mechanics · → See: [14-strategy-playbooks.md](14-strategy-playbooks.md) for step-by-step playbooks · → See: [10-atomic-skills.md](10-atomic-skills.md) for SDK method signatures · → See: [18-fee-cost-reference.md](18-fee-cost-reference.md) for fee structure · → See: [15-token-types-deepdive.md](15-token-types-deepdive.md) for complete token type mechanics

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

**Basis model:** All pools - winners, losers, and general pot - merge into one big pot on resolution. There is no $1 cap. Your payout is your proportional share of the entire pot based on how many winning outcome shares you hold. Winners don't get their original stake back separately - their money is in the pot too, being redistributed.

This is a fundamentally different value proposition. Traditional platforms reward you for being right with a fixed return. Basis rewards you for being right proportional to how much conviction existed on the other side. The more people who bet against you and lost, the more you win.

---

## 3. Volume Independence

This is critical to understand and often counter-intuitive.

On traditional platforms, volume determines liquidity but NOT payout - it's always $1 per winning share. A $100K market and a $100M market on the same question pay the same per share.

A participant doesn't need to wait for deep liquidity to see better returns. They see better returns immediately because they're receiving a proportional share of one big pot containing everyone's money - not collecting a fixed $1 bounty.

**What this means in practice:** From day one - even with a fraction of the volume of established platforms - the payout structure on Basis is already superior. This is not a "will be better once we scale" argument. The economics are better on trade one, at any volume level, because the structure itself is different.

---

## 4. Multiple Outcomes: The Multiplier Effect

This is where the structural advantage compounds dramatically.

**Traditional model:** A multi-outcome market (e.g., "Who wins the election?" with 5 candidates) is implemented as multiple separate binary pairs. Each candidate gets their own YES/NO book. You buy YES on Candidate C at 10c, they win, you get $1. A 10x return - but still capped.

The outcomes are economically isolated from each other. What happens in the Candidate A book doesn't affect your payout from the Candidate C book.

**Basis model:** A 5-outcome market means all five outcome pools plus the general pot merge into one big pot on resolution. Every dollar from every side - winners and losers alike - goes into that pot. The pot is then distributed proportionally to holders of the winning outcome's shares.

If the odds are roughly even (20% each) and you back the winner, the entire pot (100% of all money) is distributed to winning share holders. The payout multiplier scales with the number of outcomes in a way that binary-capped platforms structurally cannot match.

**Early entry amplifies this further.** In a multi-outcome market, getting in early on an outcome when shares are cheap means you hold a disproportionate chunk of winning shares. If you bought at the equivalent of 5% probability and that outcome wins, you're receiving a massive share of the one big pot. The per-share value can be many multiples of the original purchase price.

On traditional platforms, early entry just means cheaper shares approaching the same $1 ceiling. On Basis, early entry means a larger slice of an uncapped pot that grows with every bet placed across every outcome.

---

## 5. Selling: Both Sides Win

Because share value on Basis can vastly exceed the current AMM buy price, selling creates a dynamic that doesn't exist on fixed-payout platforms.

**Example:** Someone bought outcome shares at 5c. The market evolves, sentiment shifts, and those shares now look likely to win. The potential resolution value - what the shares will actually be worth when the one big pot is distributed - might be $4 per share.

The holder lists shares on the order book at 90c. They make 18x on their entry. They're happy to sell because the outcome is still uncertain, and 18x is a great return on conviction.

The buyer pays 90c for shares that could pay out $4 if the outcome wins. They're buying at what looks expensive relative to entry but is deeply discounted relative to potential resolution value.

**Both sides of that trade are genuinely satisfied** - a dynamic that a $1-capped platform cannot produce. On a traditional platform, if you bought at 5c and the implied probability is now 90c, the seller gets 85c profit and the buyer gets a maximum of 10c upside. One side is always getting compressed.

The order book handles this peer-to-peer price discovery for sellers who want to set their own terms, while the AMM remains as the instant-buy backstop for anyone who just wants in at market price.

---

## 6. The General Pot: Latecomers Still Win

A portion of fees from all outcome trading contributes to a general pot that accumulates over the market's entire lifetime, from every trade across every outcome. On resolution, this general pot merges with all outcome pools (winners and losers) into one big pot, distributed to winning share holders. This benefits all participants - especially latecomers who enter at high probability - by growing the total pot above what outcome pools alone would deliver.

This has a specific benefit for late entrants. Even if you buy shares when the outcome is already at high probability - expensive, with modest upside on a traditional platform - the one big pot includes contributions that those platforms have no structural equivalent of.

On a traditional platform, buying at 90c means a maximum 11% return. On Basis, buying at equivalent odds still yields your proportional share of the one big pot - which includes the general pot that built up from weeks or months of trading across all outcomes.

---

## 7. Participant Roles

Traditional platforms give participants one role: bettor. You pick a side, you wait, you collect $1 or $0.

Basis opens at least seven distinct ways to engage with a single prediction market:

### Bettor
Buy outcome shares, back your conviction, claim your proportional share of the one big pot if you're right. The core play - with uncapped upside.

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
Create a market on a topic you have strong conviction on. Earn 20% of net trading fees (0.1% of volume) from everyone else's activity. Bet on the outcome you believe in. If you're right: creator fees + your proportional share of the one big pot. If you're wrong: you still kept all the creator fees from both sides trading. You can't lose money on a market you create unless your bet exceeds your accumulated fees.

### The Creator-Token Holder
Create the market, buy the Predict+ token, don't bet on any outcome. You earn creator fees AND the token appreciates as volume flows through. Zero outcome risk - profit from activity regardless of who wins. When the market resolves and the sell wave hits, exit last at the highest price (Stable+ mechanics - selling burns tokens, price goes up).

### The Full Stack Creator
Create the market + buy Predict+ tokens + bet on an outcome + resolve it yourself when it ends. Four income streams from one market: creator fees (ongoing), token appreciation (volume-driven), outcome winnings (pool split), and resolver bounty. Maximum extraction from a single prediction market.

### The Leveraged Conviction Play
Buy Predict+ tokens → take a loan against them → use borrowed USDB to buy outcome shares. Original capital working twice: once as appreciating collateral, once as an active bet. Win the bet → collect winnings → repay loan → still own the tokens → sell tokens at peak. Two independent profit streams from one capital outlay.

### The Hedged Creator
Create the market + buy Predict+ tokens + bet on the LEAST likely outcome (cheapest shares). If the favourite wins: creator fees and token appreciation more than cover the small bet loss. If the underdog wins: massive payout from the one big pot (your small winning share pool claims the entire pot) while still collecting creator fees and token gains. Asymmetric risk with a built-in safety net.

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

1. **Winners** - bigger one big pot (all outcome pools + general pot merge on resolution)
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

The structural differences are not marginal improvements - they're architectural. Instant liquidity without counterparties. Uncapped payouts from one big pot where every dollar from every side is redistributed to winners. Multiple outcomes that multiply returns instead of isolating them. Seven participant roles instead of one. Combined strategies that stack independent income streams.

And none of it requires scale to deliver. The economics are superior from trade one.

---

_Basis - where being right pays what it should._ 🦞

---

## 10. Strategy Stacking Reference

**What this covers:** Formal rules for constructing multi-position capital plays on prediction markets. This section formalizes the combined strategies from §8 into composable, machine-readable modules — suitable for AI agents generating valid strategy trees.
**Related sections:** → See: §8 above for narrative descriptions of each strategy · → See: [10-atomic-skills.md](10-atomic-skills.md) for SDK method signatures · → See: [02-what-is-basis.md](02-what-is-basis.md) for leverage and loan mechanics

### Core Concept

You start with USDB. You deploy it into a **module**. Some modules end by returning USDB (via a loan), which you then feed into the next module. You keep chaining until you hit a **terminal** (hold, bet, or leverage). The result is a multi-layered position stack built from one pool of capital.

### Actions (9 Total)

| # | Action | Prerequisite | Output |
|---|--------|-------------|--------|
| 1 | Buy Predict+ token | Have USDB | Own Predict+ token |
| 2 | Buy STASIS | Have USDB | Own STASIS |
| 3 | Take loan on Predict+ | Own Predict+ token | Get USDB (token locked as collateral) |
| 4 | Wrap STASIS to wSTASIS | Own STASIS | Own wSTASIS (earning vault yield) |
| 5 | Take loan on wSTASIS | Own wSTASIS | Get USDB (wSTASIS locked as collateral) |
| 6 | Take loan on STASIS | Own STASIS | Get USDB (STASIS locked as collateral) — valid but suboptimal; no vault yield. Prefer wrapping first. |
| 7 | Bet on an outcome | Have USDB or Predict+ token | Own shares in that outcome |
| 8 | Leverage buy Predict+ | Have USDB | Own leveraged Predict+ position |
| 9 | Leverage buy STASIS | Have USDB | Own leveraged STASIS position |

### Terminals

These actions end a chain. Nothing can follow them.

- **Hold** — keep the position (Predict+ token, STASIS, wSTASIS, or shares), wait for resolution or yield
- **Bet on outcome** — USDB or Predict+ token is converted to shares, no capital left to extract
- **Leverage buy** — all capital is consumed in the recursive buy→loan→buy loop (~20x multiplier; bounded by the 2% origination fee per loop until input is fully consumed). Nothing remains to chain.

**Rule: If leverage is used, it MUST be the final action. No exceptions.**

### Modules

A module is a self-contained sequence that starts with capital (USDB or a Predict+ token) and either ends at a terminal or returns USDB via a loan.

#### Module A: Predict+ (aka "Quick Stack" entry point)

```
Buy Predict+ →
  Option 1: Hold (TERMINAL)
  Option 2: Bet with the Predict+ token (TERMINAL)
  Option 3: Take loan on Predict+ → USDB out (feeds next module)
```

Using Option 3 to feed a bet or another module is the **Quick Stack** — the minimum viable version of capital stacking on Basis. Two positions from one bag: Predict+ tokens appreciating from volume, plus whatever the borrowed USDB funds.

#### Module B: STASIS

```
Buy STASIS →
  Option 1: Hold (TERMINAL)
  Option 2: Take loan on STASIS → USDB out (valid but suboptimal — no vault yield)
  Option 3: Wrap to wSTASIS →
    Option 3a: Hold wSTASIS (TERMINAL, earning vault yield)
    Option 3b: Take loan on wSTASIS → USDB out (preferred — collateral earns vault yield while locked)
```

**Agent preference:** Default to Option 3b over Option 2 unless there is a specific reason to skip wrapping (e.g., time sensitivity, gas optimization). Wrapping earns vault yield on the locked collateral at no additional cost.

#### Module C: Bet

```
Bet USDB on outcome → Hold shares (TERMINAL)
```

Betting with a Predict+ token directly (Module A Option 2) is a distinct action — the token itself is consumed as the bet input instead of USDB. This is useful when you want full exposure to an outcome without converting back through USDB, and when you believe the outcome shares will pay out more than the Predict+ token would appreciate.

#### Module D: Leverage (always terminal)

```
Leverage buy Predict+ (TERMINAL)
— or —
Leverage buy STASIS (TERMINAL)
```

`leverageBuy()` recursively loops: buy → loan → buy → loan until the 2% origination fee per loop consumes the remaining balance. A $10 input produces approximately a $200 position (~20x). Daily interest of 0.005% also applies across the position lifetime.

### Chaining Rules

1. **Any module that outputs USDB can feed any other module** — including the same module type again (e.g., two Predict+ modules in different markets).

2. **Every chain must end at a terminal** — hold, bet, or leverage.

3. **Leverage is always last** — if used, it caps the chain. Nothing follows.

4. **Splitting is allowed** — at any USDB output point, you can divide capital across multiple parallel branches. Each branch follows its own module chain independently.

5. **Multi-market exposure** — you can repeat Module A across different prediction markets, or even different outcomes within the same market, to diversify.

6. **Loan capital is less than input** — each loan takes a 2% origination fee, so deeper chains have diminishing capital. Factor this into allocation decisions: a 3-loan chain retains ~94% of original capital; a 5-loan chain retains ~90%.

7. **Cross-pillar exit** — any module that ends with USDB output can exit the prediction market strategy entirely and deploy into other Basis token types (e.g., buying a Floor+ token). This is a valid terminal branch when the agent wants to diversify exposure beyond prediction markets.

### Loan Risk & Expiry Management

Basis has **no price-based liquidation** on Stable+ collateral (Predict+, STASIS, wSTASIS). The collateral price cannot decrease, so there is nothing to liquidate against. The risks in a stacked strategy are:

- **Loan expiry** — every loan has a time-based expiration. If not repaid or extended before expiry, the position auto-closes: collateral is burned (Stable+) or sold (Floor+) to cover the debt, and the remainder is claimable. In a stacked chain, one expired loan breaks the stack from that point — downstream positions funded by that loan's USDB are unaffected, but the collateral layer is gone.

- **Origination fees (2% per loan)** — the real capital decay in deep chains. Each loan returns less USDB than was spent. An agent should calculate whether a deeper chain's additional exposure justifies the cumulative fee cost.

- **Daily interest (0.005% per loan)** — small per loan, but across a deep serial chain with 3-4 active loans, the total daily interest burden adds up. Calculate aggregate daily cost across the full tree.

**Agent rule:** Track expiry dates across all active loans in the strategy tree. Set alerts or auto-extend before expiry. A loan expiring mid-chain doesn't cascade to other loans — each loan is independent — but it does mean you lose that collateral layer's upside.

### Unwinding a Strategy Tree

Strategies can unwind in two ways:

**Manual unwind (preferred when profitable):**
Unwind in **reverse order** — repay the most recent loan first, unlock that collateral, then work backward to the root.

```
Example (One-Bag Deep Stack):
1. Collect outcome winnings (if bet won)
2. Repay Predict+ loan → unlock Predict+ tokens
3. Sell or hold Predict+ tokens
4. Repay wSTASIS loan → unlock wSTASIS
5. Unwrap wSTASIS → STASIS (if desired)
6. You own everything free and clear
```

**Expiry unwind (passive):**
Let loans expire. Collateral is automatically burned/sold to cover debt. Remainder is claimable. This is acceptable when:
- The position has appreciated enough that the remainder after debt repayment is still profitable
- Gas or time cost of manual repayment exceeds the benefit
- The agent determines that the collateral layer has served its purpose

An agent should compare both paths and choose the one that maximizes net value.

### Structure Types

#### Serial Chain (One-Bag Deep Stack)

Modules connected end-to-end. USDB flows from one to the next.

```
[Module] → USDB → [Module] → USDB → [Terminal]
```

#### Parallel Split

At a USDB output, divide capital across branches.

```
[Module] → USDB →
  ├── X% → [Module or Terminal]
  └── Y% → [Module or Terminal]
```

#### Full Tree

A combination of serial chains and parallel splits.

```
USDB →
  [Module] → USDB →
    ├── 60% → [Module] → USDB → [Terminal]
    └── 40% → [Terminal]
```

### Example Plays

#### Example 1: The One-Bag Deep Stack

```
USDB
→ Buy STASIS
→ Wrap to wSTASIS (earning vault yield)
→ Loan on wSTASIS → USDB
→ Buy Predict+ (Market A)
→ Loan on Predict+ → USDB
→ Bet on outcome (Market B)
```

**End state:** Three simultaneous layers — wSTASIS earning vault yield (locked), Predict+ appreciating from Market A volume (locked), outcome shares in Market B with uncapped payout. One starting position, three exposure layers.

#### Example 2: Chain Ending in Leverage

```
USDB
→ Buy STASIS
→ Wrap to wSTASIS
→ Loan on wSTASIS → USDB
→ Buy Predict+ (Market A)
→ Loan on Predict+ → USDB
→ Leverage buy Predict+ (Market B)
```

**End state:** wSTASIS staking position, Predict+ in Market A (collateral), ~20x leveraged Predict+ in Market B.

#### Example 3: Split Play

```
USDB
→ Buy Predict+ (Market A)
→ Loan on Predict+ → USDB
  ├── 50% → Buy STASIS → Wrap → Hold wSTASIS
  └── 50% → Leverage buy Predict+ (Market C)
```

**End state:** Predict+ in Market A (collateral), wSTASIS earning yield, leveraged Predict+ in Market C.

#### Example 4: Multi-Market Exposure

```
USDB
→ Buy Predict+ (Market A)
→ Loan on Predict+ → USDB
→ Buy Predict+ (Market B)
→ Loan on Predict+ → USDB
→ Bet on outcome (Market C)
```

**End state:** Exposure to three different prediction markets from one starting capital. Each loan takes 2%, so Market C bet is funded with ~96% of original capital.

#### Example 5: Betting with a Predict+ Token

```
USDB
→ Buy Predict+ (Market A)
→ Bet with Predict+ token on outcome in Market A
```

**End state:** Shares in Market A outcome. The Predict+ token itself was used as the bet input — bypassing a USDB conversion step. This is optimal when you have high conviction on a specific outcome and want maximum share allocation rather than retaining the token for appreciation or collateral.

### Agent Instructions

To generate a valid strategy:

1. Start with a USDB amount.
2. Pick a module (A, B, C, or D).
3. If the module outputs USDB, optionally split and pick the next module(s) for each branch.
4. Repeat until every branch hits a terminal.
5. Validate: leverage is only at the end of its branch, prerequisites are met for every action, and no action follows a terminal.
6. Track all loan expiry dates across the tree. Set extension or repayment triggers.
7. Calculate total origination fees (2% per loan) and daily interest (0.005% per loan) across the full tree.

Consider:
- **Market conviction** — if high conviction on a prediction, chain toward deeper exposure there
- **Yield preference** — route through STASIS wrapping (Module B Option 3b) for passive vault yield on locked collateral
- **Risk tolerance** — more modules = more positions but each with less capital (2% fee per loan). A 3-loan chain retains ~94%; a 5-loan chain retains ~90%.
- **Diversification** — split across markets and asset types to reduce concentration
- **Loan management** — every active loan has an expiry. Deeper chains mean more loans to track.
- **Position sizing vs. liquidity** — large buys on early-stage Predict+ markets cause significant price impact. If a buy would move the price by more than 2%, split the capital into smaller strands across more markets instead. Multi-prong strategies at lower dollar values avoid slippage while capturing early-mover upside across multiple markets.

---

## Private Markets

Everything above applies to public prediction markets. Basis also supports **private markets** — restricted-access markets with a simpler resolution model:

- **Access control:** Creator can restrict buying to whitelisted addresses via `togglePrivateEventBuyers()`
- **Resolution:** By voter consensus (not the resolver module). Creator votes by default; additional voters added via `manageVoter()`. Majority wins after a 15-minute voting window from the first vote cast.
- **Use cases:** Community-specific questions, internal governance votes, niche topics where the creator has resolution authority
- **Same economics:** AMM pricing, one-big-pot payouts, and Predict+ token mechanics all work identically

→ See: [10-atomic-skills](10-atomic-skills.md) for all SDK methods.

---

