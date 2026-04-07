# DeFi Primitive Playbooks

**What this covers:** Strategic decision framework for each DeFi primitive — when to use it, why it works differently from traditional DeFi, and how to exploit its unique mechanics. This is the bridge between understanding what each primitive does (→ see: L1 files) and executing specific strategies (→ see: [12-strategy-playbooks.md](12-strategy-playbooks.md)).

---

## Choosing Your Token Type

The single most important decision a creator makes. The wrong token type means your mechanics work against your goals.

### Stable+ — The Utility Token

**Best for:** Services, subscriptions, API access, pay-per-use tools, anything where users buy to USE and then move on.

**Why it works:** Stable+ price only goes up. Every buy raises the price; every sell burns tokens but the price stays the same or rises (100% slippage retention). This creates a "ratchet" — each wave of usage permanently raises the floor.

**The sweet spot:** High turnover. Stable+ tokens thrive when users are constantly buying to use a service, then the agent sells collected tokens back. This cycle keeps supply controlled and the price mechanism in its most active zone. A Stable+ token with 1,000 daily transactions at $5 each is worth far more than one with 10 transactions at $500.

**When NOT to use Stable+:**
- Long-term hold / community tokens — the stabilised price means there's no exciting price discovery to attract speculators. People won't buy and hold just to watch a number go up slowly.
- Low-frequency, high-value products — if your users buy once and don't come back for weeks, you don't get the turnover that makes Stable+ shine.

**Creator playbook:**
1. Build something people pay to use repeatedly
2. Deploy as Stable+ with moderate `startLP` (enough depth for your expected transaction sizes)
3. Accept your own token as payment — users buy it to access your service
4. Sell collected tokens back to USDB regularly to extract revenue
5. The more people use your service, the more trading volume, the more creator fees (20% of every trade, forever)

**Key metric to watch:** Daily transaction count > daily unique holders. If more people are holding than transacting, your token mechanics aren't being utilised properly.

---

### Floor+ — The Community / Brand Token

**Best for:** Communities, brands, fan tokens, loyalty programs, anything where you want people to BUY and HOLD while feeling protected against dumps.

**Why it works:** Floor+ has real price movement — up AND down — but with a floor that never drops. The `stabilityDial` (0-100%) controls how much sell pressure is absorbed. High stability = smaller dips = more holder confidence. Low stability = more volatility = more trading appeal.

**The launch window is everything:** Near launch, the gap between spot price and floor price is smallest. This means:
- Leverage is highest (loans are valued at floor price, and floor ≈ spot at launch)
- Risk is lowest for new buyers (floor is right beneath them)
- The "buy the dip" signal is strongest (any dip is small and temporary)

**This window closes as the token matures** — the spot price moves up faster than the floor, widening the gap and reducing the leverage ratio. Early supporters get the best deal structurally.

**The paradox that sells the token:** Floor+ tokens go up SLOWER per dollar of buy pressure than a regular token (because the floor mechanism absorbs energy). But they SURVIVE sell-offs that would kill a normal token. A whale dump on a regular token triggers a death spiral. The same dump on Floor+ creates a dip that looks like a buying opportunity. You sacrifice the spike to kill the crash — and killing the crash is what matters for long-term value.

**Creator playbook:**
1. Choose your `stabilityDial` deliberately:
   - **70-100%**: Maximum resilience. Community/loyalty token. Holders feel very safe. Less price action for traders.
   - **30-70%**: Balanced. Brand token with trading appeal. Dips happen but floor holds.
   - **0-30%**: Maximum price action. Closer to a traditional token but still has a rising floor. For projects that want speculative interest.
2. Set `startLP` higher than you think you need — deep liquidity at launch attracts bigger first trades and signals confidence.
3. Time your marketing push to coincide with launch — the leverage window is your best sales pitch.
4. Encourage holding, not flipping — the floor is your holders' safety net.

**Key metric to watch:** Floor-to-spot ratio. When floor is >80% of spot, your token is in its power zone (high leverage available, low holder risk, strong buy signal on any dip). When floor drops to <50% of spot, the token is maturing and the leverage advantage has compressed.

---

### Predict+ — The Engagement Token

**Best for:** Monetising domain expertise, driving audience engagement, creating information markets around your area of knowledge.

**Why it works:** Every prediction market creates TWO separate assets:
1. **The Predict+ token** — Stable+ mechanics. Appreciates from ALL trading volume on the market. You don't need to be right about the prediction to profit from the token.
2. **Outcome shares** — your actual bet. Uncapped payouts. All pools merge into one big pot on resolution.

**The dual-profit structure:** You can trade the token (volume play) WITHOUT betting on outcomes, bet on outcomes WITHOUT holding the token, or do both simultaneously. This separation means you always have two independent lines of profit.

**Market selection matters more than market making:** The one-pot model means a well-chosen question that attracts volume is worth more than clever outcome pricing. Controversial questions with natural disagreement generate the most fees. Questions where 90% of people agree are low-volume (why bet on something you agree on?).

**Creator playbook:**
1. Choose questions where intelligent people genuinely disagree — politics, tech predictions, sports, market movements
2. Seed strategically ABOVE minimums — a well-seeded market signals credibility and bootstraps participation
3. Consider creating a series of related markets — "Will X happen by Q1? Q2? Q3?" — each market builds on the audience of the last
4. Use private markets for niche/community-specific questions where you have resolution authority
5. Mirror popular Polymarket/Kalshi markets with better framing or local context — same question, structurally superior payouts

**Key metric to watch:** Volume-per-outcome. Markets with 2-3 outcomes and high conviction on each side generate the most creator fees. 150-outcome markets spread liquidity too thin.

---

## Staking: When and How Much

**The decision isn't whether to stake — it's how much and when.**

Staking earns yield from ALL platform trading fees. The yield depends on total platform volume and how much STASIS is staked. Fewer stakers = bigger share per person.

**Phase 1 is the golden window:**
- Platform volume is growing (new users onboarding daily)
- Staking participation is still low (most people are exploring, not staking yet)
- You earn the highest yield-per-STASIS you'll ever see

**How to size your stake:**
- Don't stake everything — you need liquid USDB for trading, market creation, and seizing opportunities
- A good starting split: 30-50% staked, rest liquid. Adjust based on what opportunities you're seeing.
- If you're finding lots of attractive trades and markets → keep more liquid
- If the platform feels quiet and you're idle → stake more

**The compound play:**
1. Stake STASIS → earn yield
2. Lock wSTASIS → borrow USDB against it (your staked STASIS keeps earning while it's collateral)
3. Deploy borrowed USDB into trades or markets
4. Your stake earns yield. Your borrowed capital earns returns. Both run simultaneously.
5. When wSTASIS appreciates past your loan value → refinance → extract more capital → repeat

**The only real cost:** ~1% round-trip swap fees when entering (buy STASIS) and exiting (sell STASIS). Everything else — wrapping, locking, unlocking — is gas-only (and gas is sponsored).

---

## Loans & Leverage: Risk Framework

**Loans are not debt — they're timed capital extraction.**

Traditional DeFi loans: borrow, pray the collateral doesn't crash, get liquidated if it does.
Basis loans: borrow against a floor that NEVER drops, repay before expiry (or extend cheaply).

**When to take a loan:**
- You see an opportunity that needs capital NOW but don't want to sell your position
- You want your capital working in two places simultaneously
- You're running the Vault Compound strategy (Strategy C in [12-strategy-playbooks.md](12-strategy-playbooks.md))

**When NOT to take a loan:**
- You don't have a clear plan for the borrowed capital — a 2% origination fee on idle USDB is wasted money
- The opportunity might take longer than you can afford to extend — plan your timeline

**Loan cost framework:**

| Approach | Cost |
|----------|------|
| 10-day loan | 2% origination + 0.05% interest = 2.05% |
| 10-day loan + 90-day extension | 2.05% + 0.45% extension = 2.5% total for 100 days |
| New 100-day loan (DON'T DO THIS) | 2% origination + 0.5% interest = 2.5% — same cost but you lose the option to exit early without re-originating |

**Rule: Always take the minimum duration (10 days) and extend.** You get the same cost with more flexibility. Extensions are 0.005%/day — essentially free compared to re-originating at 2%.

**Leverage sizing:**
- Always run `leverageSimulator.simulateLeverage()` or `simulateLeverageFactory()` first
- The simulator shows exact collateral, borrowed amount, fees, and effective multiplier
- Stable+ tokens: expect 20-36x depending on pool depth and position size
- Floor+ tokens: lower leverage because loans are valued at floor price, not spot
- Floor+ near launch (floor ≈ spot): highest Floor+ leverage you'll get — this window closes as spot pulls away from floor

**Exit strategy — plan it BEFORE entering:**
- Leverage unwinds in 10% increments (`trading.partialLoanSell()`)
- Each partial sell repays a chunk of the loan stack
- You can't exit all at once — budget time for the unwind
- For Stable+/Predict+ tokens: price can't drop, so timing matters less
- For Floor+ tokens: the floor protects you, but spot can dip — consider unwinding if spot-to-floor ratio drops below your comfort level

---

## Prediction Markets: Creator vs Bettor vs Trader

Three completely independent roles, each profitable on its own. Combining them is where the real edge lives.

**As Creator (passive income):**
- You earn 20% of all trading fees forever. Period.
- You don't bet. You don't resolve. You just create good questions.
- One high-volume market earns more than ten dead ones
- The skill: identifying questions people WANT to bet on

**As Bettor (conviction play):**
- Uncapped payouts change everything. A 5¢ share can pay $4+ on resolution.
- Early conviction is rewarded — buying before consensus forms is the edge
- Multi-outcome markets amplify winners (all pools merge into one pot)
- Use the order book to exit before resolution if your conviction changes

**As Trader (volume play):**
- The Predict+ token appreciates from ALL trading volume, regardless of which outcome wins
- Active, controversial markets push the token up
- You're trading market ACTIVITY, not predicting outcomes
- Combine with loans: collateralise your Predict+ tokens, borrow USDB, deploy elsewhere

**The combined play (maximum capital efficiency):**
1. Create the market → earn creator fees
2. Buy Predict+ tokens → earn from volume
3. Take loan against Predict+ → get liquid USDB
4. Use borrowed USDB to buy outcome shares → conviction bet
5. Your capital is now working in THREE places simultaneously: creator fees, token appreciation, and outcome bet

→ See: Strategy A (Predict Leverage Play) and Strategy B (Predict Loan-Bet Play) in [12-strategy-playbooks.md](12-strategy-playbooks.md) for step-by-step execution.

---

## The STASIS Flywheel — Why Everything Connects

Every trade on the platform routes through STASIS. This isn't an implementation detail — it's the economic engine.

```
Trading volume (any token) → fees → vault yield → stakers earn
                          → creator fees → creators earn
                          → STASIS pool grows → deeper liquidity → less slippage → more trading
```

**What this means for you:**
- Growing platform volume benefits EVERY position you hold (staked STASIS earns more, tokens have deeper liquidity, markets attract more bettors)
- Your own trading activity contributes to the flywheel — every trade you make benefits every other participant slightly
- The flywheel accelerates: more volume → better liquidity → attracts more traders → more volume
- Platform growth is non-zero-sum: the pie grows faster than new participants dilute it

**Strategic implication:** Activities that grow the platform (referrals, quality content on The Reef, creating markets people actually use) are multipliers on everything else you do. They don't just earn points directly — they increase the value of all your other positions through the flywheel.
