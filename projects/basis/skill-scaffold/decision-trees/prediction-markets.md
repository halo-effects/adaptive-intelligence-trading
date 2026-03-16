# Basis Agent Strategy Decision Tree
_Multi-path strategy guide for autonomous agents. Not prescriptive — shows what's possible._
_Last updated: 2026-03-16_

---

## Philosophy

This isn't a playbook. It's a **map**. Agents evaluate their own capital, risk tolerance, time horizon, and market conviction to navigate the decision tree. Every node presents options with tradeoffs. The agent decides.

---

## Master Flow

```
┌─────────────────────────────────────────────────────────────┐
│                    🔍 PHASE 1: DISCOVER                      │
│         Scout → Identify → Evaluate → Decide to Act          │
└──────────────────────────┬──────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────┐
│                    🏗️ PHASE 2: CREATE                        │
│           Create Market on Basis (or join existing)           │
└──────────────────────────┬──────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────┐
│                    📊 PHASE 3: ANALYZE                       │
│       Probability differential · Liquidity · Timing           │
└──────────────────────────┬──────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────┐
│                    💰 PHASE 4: POSITION                      │
│        Choose capital deployment path(s) — see tree below     │
└──────────────────────────┬──────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────┐
│                    📢 PHASE 5: AMPLIFY                       │
│           Promote market → drive volume → earn fees           │
└──────────────────────────┬──────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────┐
│                    🔄 PHASE 6: MANAGE                        │
│          Monitor · Rebalance · Extend · Compound              │
└──────────────────────────┬──────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────┐
│                    🚪 PHASE 7: EXIT                          │
│           Timing · Method · Reinvestment decision             │
└─────────────────────────────────────────────────────────────┘
```

---

## Phase 1: DISCOVER

### Source: Polymarket Scout
- Run `polymarket-scout` → ranked markets by volume × outcomes
- Filter: multi-outcome (3+), high volume, active, time-bounded

### Source: Trending Topics
- News feeds, social signals, crypto events
- Agent's own domain knowledge or community signals

### Source: Existing Basis Markets
- Scan live Basis markets for undervalued positions or low-competition creator opportunities

### Decision: Act or Pass?

| Factor | Act | Pass |
|---|---|---|
| Volume on source market | High (>$100K) | Low (<$5K) |
| Outcome count | 3+ ideal, 2 acceptable | Single binary with no edge |
| Time to resolution | Days to weeks (active trading) | Already resolved or years out |
| Probability edge | Clear mispricing vs. source | Efficient pricing, no edge |
| Basis market exists? | No → create (earn fees). Yes → join | Already saturated with creators |

**→ If Act: proceed to Phase 2**
**→ If Pass: return to scouting**

---

## Phase 2: CREATE (or JOIN)

### Decision: Create new market or join existing?

```
Market exists on Basis?
├── NO → Create new market
│   ├── Earn 20% of ALL trading fees forever (creator privilege)
│   ├── Set outcomes from Polymarket data or custom
│   ├── Choose resolution type:
│   │   ├── Basis Managed (decentralized, dispute process)
│   │   └── Creator Managed (you resolve, or whitelist voters)
│   └── Set bonding phase target ($0–$150K)
│
└── YES → Join existing market
    ├── No creator fee revenue (already taken)
    ├── But: bonding phase may still be open (earn 3.33% reward shares)
    └── Lower risk — market is proven, has liquidity
```

### Decision: Bonding phase participation?

| Factor | Enter during bonding | Wait for post-bonding |
|---|---|---|
| Capital efficiency | Locked until target hit | Immediate liquidity |
| Reward shares | Earn 3.33% of ALL future fees forever | None |
| Entry price | Better (earlier = cheaper) | Market price |
| Selling penalty | Yes (during bonding) | None |
| Conviction level | High | Uncertain |

---

## Phase 3: ANALYZE

### Probability Differential Analysis

```
Polymarket price for outcome X:         $0.35 (implies 35% probability)
Basis market price for same outcome:    $0.28 (implies 28% probability)
                                        ─────
Differential:                           +7% (Basis underpriced vs. Polymarket)
```

### Decision Inputs

| Metric | What it tells you |
|---|---|
| **Price differential** | Mispricing opportunity (higher = better edge) |
| **Polymarket volume** | Demand validation (proven interest) |
| **Basis liquidity depth** | Slippage cost to enter/exit |
| **Time to resolution** | Holding period, capital lockup |
| **Outcome count** | More outcomes = more complex, more edge potential |
| **Token price trajectory** | Stable+ = up-only via slippage retention |
| **Current pool size** | Small pool = higher leverage available, more price impact |

### Edge Types

1. **Probability edge**: You think the market is wrong (Polymarket says 35%, you think 50%)
2. **Structural edge**: Basis mechanics (slippage retention, leverage, loans) create value that Polymarket can't
3. **Creator edge**: Being the market creator = 20% of all fees regardless of outcome
4. **Timing edge**: Early entry in bonding phase or first on a trending topic
5. **Amplification edge**: You can drive volume through social promotion

---

## Phase 4: POSITION (Capital Deployment Decision Tree)

This is the core branching logic. An agent with $1,000 USDC has many paths:

```
Available capital: $X USDC
│
├── PATH A: Token Only
│   ├── A1: Normal Buy
│   │   • Buy Predict+ token at market price
│   │   • Earns from: slippage retention (up-only appreciation)
│   │   • Risk: capital locked in token, opportunity cost
│   │   • Best when: moderate conviction, want exposure + optionality
│   │
│   ├── A2: Leverage Buy
│   │   • Toggle leverage ON → amplified position
│   │   • Up to 36x effective (depends on pool size + buy amount)
│   │   • Leverage fee: 43–70% of collateral (substantial!)
│   │   • Use simulateLeverage() to preview BEFORE executing
│   │   • Cannot use leveraged tokens as loan collateral
│   │   • Risk: high fee cost, but NO liquidation risk
│   │   • Best when: high conviction, small pool (max leverage)
│   │
│   └── A3: Split Buy (Normal + Leverage)
│       • Allocate X% normal, Y% leveraged
│       • Normal portion: can be used as loan collateral later
│       • Leveraged portion: locked in leverage contract
│       • Best when: want both optionality AND amplified upside
│
├── PATH B: Token + Loan (Capital Recycling)
│   ├── B1: Buy Token → Full Loan
│   │   • Buy Predict+ token (normal)
│   │   • Take 100% LTV loan against tokens
│   │   • Receive USDC (minus 2.0% + 0.005%/day fee)
│   │   • Now have: token position + freed USDC
│   │   • Risk: loan expiry (must repay or lose collateral)
│   │   • Best when: want exposure AND capital to redeploy
│   │
│   ├── B2: Buy → Loan → Bet
│   │   • Buy token → loan → use USDC to bet on outcomes
│   │   • Double exposure: token appreciation + bet payout
│   │   • Risk: loan cost + bet could lose
│   │   • Best when: strong outcome conviction + want token exposure
│   │
│   ├── B3: Buy → Loan → Buy More (Compound)
│   │   • Buy token → loan → buy more of same token
│   │   • Amplified token position (like leverage, but via loans)
│   │   • Cost: loan fee (~2.05% for 10 days) vs leverage fee (43–70%)
│   │   • MUCH cheaper than leverage for short-term amplification!
│   │   • Can repeat: buy → loan → buy → loan (loop)
│   │   • Risk: cascading loan expiries
│   │   • Best when: want leveraged exposure at lower cost
│   │
│   └── B4: Buy → Loan → Deploy Elsewhere
│       • Buy token → loan → use USDC in different market/strategy
│       • Portfolio diversification with capital efficiency
│       • Best when: multiple simultaneous opportunities
│
├── PATH C: Bet Only
│   ├── C1: Direct USDC Bet
│   │   • Bet on specific outcome using USDC pool
│   │   • Win: share of ENTIRE losing pool (uncapped)
│   │   • Lose: lose bet amount
│   │   • No token exposure, no slippage retention benefit
│   │   • Best when: high conviction on specific outcome, pure directional
│   │
│   └── C2: Spread Bets Across Outcomes
│       • Bet on multiple outcomes with different allocations
│       • Hedged exposure — profit if any weighted outcome hits
│       • Best when: uncertain which outcome, but confident in range
│
├── PATH D: Hybrid (Token + Bet + Loan combinations)
│   ├── D1: Normal Buy + Direct Bet
│   │   • Split capital: X% token, Y% bet
│   │   • Token: earns from appreciation regardless of outcome
│   │   • Bet: earns from correct outcome prediction
│   │   • Best when: want both structural and directional upside
│   │
│   ├── D2: Leverage Buy + Loan on Normal + Bet with Loan Proceeds
│   │   • Split: X% leveraged, Y% normal → loan → bet
│   │   • Maximum capital efficiency — every dollar works 2-3 ways
│   │   • Most complex, highest potential return
│   │   • Risk: leverage fee + loan cost + bet risk
│   │   • Best when: high conviction, capital-constrained
│   │
│   ├── D3: Buy + Loan + Bet + Promote (Full Stack)
│   │   • Buy token → loan → bet on outcome → promote on social
│   │   • Earn from: appreciation + bet payout + creator fees + loan redeployment
│   │   • Promotion drives volume → more creator fees + price appreciation
│   │   • Best when: you're the market creator with social reach
│   │
│   └── D4: Conservative Anchor + Aggressive Satellite
│       • Core position: normal token buy (safe, up-only)
│       • Satellite: leveraged position OR aggressive bets
│       • Barbell strategy — protected base with asymmetric upside
│       • Best when: mixed conviction, want downside protection
│
└── PATH E: Creator-First (Fee Harvesting)
    ├── E1: Create → Minimal Position → Promote
    │   • Create market (20% fee revenue forever)
    │   • Buy minimum token amount during bonding
    │   • Focus effort on driving volume through promotion
    │   • Revenue scales with volume, not position size
    │   • Best when: low capital, high social reach
    │
    └── E2: Create Multiple Markets → Portfolio of Fee Streams
        • Create 5-10 markets across trending topics
        • Small positions in each, diversified fee revenue
        • Use Polymarket scout to identify high-volume opportunities
        • Best when: want passive income from creation, not trading
```

### Position Sizing Matrix

| Capital Available | Conservative | Moderate | Aggressive |
|---|---|---|---|
| < $100 | 100% normal buy | 70% buy + 30% bet | 100% leverage buy |
| $100–$1,000 | 80% buy + 20% bet | 50% buy → loan → bet | Split: 40% leverage + 30% buy + 30% bet |
| $1,000–$10,000 | Buy + loan + redeploy | Multi-market spread | Full D2 hybrid + promotion |
| $10,000+ | Create markets + anchor positions | Portfolio of fee streams + active trading | Full stack D3 across multiple markets |

---

## Phase 5: AMPLIFY

### Social Promotion Paths

```
Position established
│
├── Post market link on X (Twitter)
│   ├── Thread with analysis (highest engagement)
│   ├── Quick take + link (fastest)
│   └── P&L receipt (social proof)
│
├── Share in agent communities
│   ├── Discord servers
│   ├── Telegram groups
│   └── Agent forums / Moltbook (when live)
│
├── Cross-reference with Polymarket
│   ├── "Basis offers uncapped payouts vs Polymarket's $1 cap"
│   ├── "Same market, better mechanics — here's why"
│   └── Highlight probability differential
│
└── Earn points: 50–150 pts per social post
```

### Volume Flywheel

```
More promotion → More traders → More volume → More fees (creator 20%)
                                            → More slippage retention
                                            → Higher token price
                                            → More lending capacity
                                            → More promotion (show P&L)
                                            → ♻️ REPEAT
```

---

## Phase 6: MANAGE

### Monitoring Triggers

| Trigger | Action Options |
|---|---|
| Probability shift (>5% move) | Rebalance bets, adjust position size |
| New information / news | Add to position or hedge |
| Loan approaching expiry | Extend (pay fee) OR repay OR let collateral burn |
| Token price appreciation | Take partial loan against gains, redeploy |
| Volume spike | Promote more aggressively (momentum) |
| Volume death | Reduce promotion spend, consider exit |
| Better opportunity found | Loan against current → deploy to new market |
| Resolution approaching | Evaluate exit timing (see Phase 7) |

### Loan Management Decision

```
Loan expiry approaching
│
├── Position profitable?
│   ├── YES → Extend loan (pay small fee) → keep compounding
│   └── NO → Evaluate:
│       ├── Repay loan → get tokens back → decide: hold or sell
│       ├── Partial sell → reduce exposure, keep some upside
│       └── Let collateral burn → walk away (if token value < loan)
│           └── Claim excess value if token > loan amount
│
└── New opportunity available?
    ├── YES → Sell collateral via loan → redeploy USDC
    └── NO → Hold and wait
```

---

## Phase 7: EXIT

### Exit Timing Decision Tree

```
Market resolution approaching
│
├── BEFORE resolution
│   ├── Sell token now → lock in appreciation gains
│   ├── Sell partial → reduce risk, keep upside
│   └── Hold → ride post-resolution dynamics
│
├── AT resolution
│   ├── Collect bet winnings (if correct outcome)
│   ├── Token still tradable (Predict+ = Stable+ = up-only)
│   └── Post-resolution selling begins
│
└── AFTER resolution (Post-Resolution Strategy)
    ├── SELL EARLY: Accept current price, move capital to next opportunity
    ├── WAIT FOR WAVE: Others sell first → burns reduce supply →
    │   slippage retention pushes price up → exit at higher price
    │   Risk: takes time, capital locked
    └── HOLD LONG: If token has ongoing utility beyond the prediction
```

### Reinvestment Decision

```
Exit proceeds received
│
├── Compound into same market type
│   └── Find next high-potential prediction market
│
├── Diversify across strategies
│   ├── Some into tokens, some into bets, some into vault
│   └── Spread across multiple markets
│
├── Stake in STASIS vault
│   └── Earn yield + refinance loop (passive income)
│
└── Cash out to USDC
    └── Wait for better opportunities
```

---

## Composability Matrix

Every action on Basis creates optionality for the next action:

| After this... | You can... |
|---|---|
| Buy token | Take loan, leverage up, sell, hold, bet with other capital |
| Take loan | Buy more, bet, deploy elsewhere, stake, create new market |
| Place bet | Wait for resolution, hedge with opposite bet |
| Create market | Earn fees forever, promote, build audience |
| Stake in vault | Borrow against wSTASIS, earn yield, refinance |
| Earn USDC fees | Reinvest anywhere on the platform |
| Earn points | Increase ACS score → better airdrop allocation |

**Key insight**: Nothing is terminal. Every position creates new options. The best agents chain actions to maximize capital velocity — how many times each dollar works for them per unit of time.

---

## Risk Tiers

| Tier | Strategy Pattern | Expected Return | Risk |
|---|---|---|---|
| 🟢 Conservative | Create markets + minimal positions + promote | Low-moderate (fee income) | Very low |
| 🟡 Moderate | Buy + loan + redeploy + bet small | Moderate | Moderate (loan expiry) |
| 🟠 Aggressive | Leverage + loan loops + concentrated bets | High | High (fee costs, bet losses) |
| 🔴 Full Stack | All paths simultaneously + social promotion | Highest potential | Highest complexity |

---

## Points Optimization Layer

Every action above also generates airdrop points:

| Action | Points |
|---|---|
| Create prediction market | 300 pts |
| Launch token | 500 pts |
| Trade (per $1 volume) | 1 pt |
| Bet (per $1 net profit) | 1 pt |
| Take loan | 200 base + 1/day |
| Vault stake | 2 pts/$1/day |
| Social post | 50–150 pts |
| Referral | 10% of referee's lifetime |

Agents should factor point accumulation into every decision — points → ACS score → airdrop multiplier → more capital → more strategies.

---

_This document is the agent's map. The agent is the navigator._
