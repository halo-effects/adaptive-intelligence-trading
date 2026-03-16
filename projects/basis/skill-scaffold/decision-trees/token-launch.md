# Token Launch Decision Tree
_Multi-path strategy guide for agents launching and trading tokens on Basis._
_Last updated: 2026-03-16_

---

## Philosophy

Tokens on Basis aren't just assets — they're revenue-generating businesses. Creating a token = owning 20% of all trading fees forever. The decision tree below maps every path from ideation to ongoing management.

---

## Master Flow

```
┌─────────────────────────────────────────────────────────────┐
│                    💡 PHASE 1: IDEATE                        │
│         What token? What type? What audience?                 │
└──────────────────────────┬──────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────┐
│                    ⚙️ PHASE 2: CONFIGURE                     │
│         Token type · Stability dial · Bonding target          │
└──────────────────────────┬──────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────┐
│                    🚀 PHASE 3: LAUNCH                        │
│            Deploy · Seed bonding · Announce                   │
└──────────────────────────┬──────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────┐
│                    📈 PHASE 4: GROW                          │
│        Drive volume · Promote · Build community               │
└──────────────────────────┬──────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────┐
│                    💰 PHASE 5: MONETIZE                      │
│        Fee harvesting · Loans · Leverage · Vault              │
└──────────────────────────┬──────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────┐
│                    🔄 PHASE 6: SUSTAIN                       │
│        Ongoing management · Surge tax · Community ops         │
└─────────────────────────────────────────────────────────────┘
```

---

## Phase 1: IDEATE

### Decision: What kind of token?

```
What's the PURPOSE?
│
├── 💎 Store of value / savings
│   └── Stable+ (up-only, floor = spot)
│       Best for: payments, corporate tokens, loyalty programs
│
├── 🎮 Community / meme / identity
│   └── Floor+ (price discovery + rising floor protection)
│       Best for: communities, DAOs, agent identities, fan tokens
│
├── 📊 Prediction market
│   └── Predict+ (Stable+ type, paired with betting pool)
│       → See prediction-markets.md decision tree
│
└── 🏗️ Utility / ecosystem
    ├── Stable+ if utility requires price stability
    └── Floor+ if utility benefits from speculation + floor protection
```

### Decision: What audience?

| Audience | Token Type | Strategy Focus |
|---|---|---|
| Other agents | Either | SDK integration guides, API examples |
| Crypto community | Floor+ | Meme appeal, social virality |
| Businesses | Stable+ | Stability guarantees, payment use case |
| Niche community | Floor+ | Identity/belonging, exclusive access |
| DeFi degens | Floor+ (low stability dial) | Volatility, leverage opportunities |

---

## Phase 2: CONFIGURE

### Token Type Decision Matrix

```
Stable+ vs Floor+?
│
├── STABLE+ (hybridMultiplier = 100)
│   ├── Price: up-only, floor = spot price, CANNOT decrease
│   ├── Trading fee: 0.5%
│   ├── Leverage: maximum always available (floor = spot)
│   ├── Loans: 100% LTV at spot price
│   ├── Surge tax: max 0.50% (limited)
│   ├── Best for: value storage, payments, prediction markets
│   └── Tradeoff: no price discovery, no speculation excitement
│
└── FLOOR+ (hybridMultiplier = 1–90)
    ├── Price: goes up AND down, but floor only rises
    ├── Trading fee: 1.5%
    ├── Leverage: max at launch (floor ≈ spot), decreases as spot > floor
    ├── Loans: 100% LTV at FLOOR price (not spot)
    ├── Surge tax: up to 15% (powerful creator tool)
    ├── Best for: communities, memes, speculation, agent identities
    └── Tradeoff: price can drop (to floor), more complex dynamics
```

### Stability Dial (Floor+ only)

```
hybridMultiplier setting (1–90):
│
├── 1–10: Maximum volatility
│   ├── Price swings wildly above floor
│   ├── Highest leverage available at launch
│   ├── Surge tax up to 15% (powerful snipe protection)
│   ├── Most exciting for traders / degens
│   └── Floor rises slowly (most value stays above floor)
│
├── 30–50: Balanced
│   ├── Moderate price discovery
│   ├── Good leverage, reasonable stability
│   ├── Surge tax up to ~7–10%
│   └── Good for most community tokens
│
├── 70–90: Near-stable
│   ├── Minimal price swings
│   ├── Floor tracks close to spot
│   ├── Surge tax limited (~1–3%)
│   ├── Almost like Stable+ but with slight volatility
│   └── Good for utility tokens that need some flexibility
│
└── 100: This IS Stable+ (use Stable+ type instead)
```

### Bonding Phase Configuration

```
Bonding target ($0–$150,000):
│
├── $0 (no bonding)
│   ├── Immediate real liquidity
│   ├── No reward shares for early buyers
│   └── Best when: you want instant tradability
│
├── $100–$1,000 (micro)
│   ├── Quick bonding completion
│   ├── Small early supporter pool
│   └── Best when: testing, low-risk launch
│
├── $1,000–$10,000 (standard)
│   ├── Meaningful early community
│   ├── Good reward share incentive
│   └── Best when: most community launches
│
├── $10,000–$50,000 (premium)
│   ├── Larger initial liquidity after bonding
│   ├── Longer bonding period = more early supporters
│   └── Best when: high-conviction, established audience
│
└── $50,000–$150,000 (major)
    ├── Deep liquidity post-bonding
    ├── Significant capital commitment from community
    └── Best when: flagship token, strong pre-launch demand
```

### Starting Liquidity ($100–$10,000)

| Amount | Effect |
|---|---|
| $100 (minimum) | Maximum price impact per trade, wildest moves, highest initial leverage |
| $500–$1,000 | Good balance for small communities |
| $2,000–$5,000 | Smoother trading, moderate leverage |
| $10,000 (maximum) | Most stable trading, lowest leverage, institutional feel |

### Optional Settings

```
Additional configuration:
│
├── Freeze function?
│   ├── YES → Can pause trading (emergency brake)
│   └── NO → Fully permissionless, cannot be stopped
│
├── Auto-vesting?
│   ├── YES → Buyers' tokens vest over time (reduces dumps)
│   └── NO → Instant full ownership
│
└── Whitelist?
    ├── YES → Restricted buyers initially (private launch)
    └── NO → Open to all (permissionless)
```

---

## Phase 3: LAUNCH

### Launch Sequence

```
1. Deploy token (single contract call, ~$0.14 BNB gas)
   └── Token starts at $1.00 (always)

2. Enter bonding phase (if target > $0)
   ├── Buy your own tokens? (creator can participate)
   │   ├── YES → Get reward shares + show conviction
   │   └── NO → Save capital for post-bonding strategies
   │
   └── Announce and recruit early buyers
       ├── Share bonding link on social channels
       ├── Highlight reward shares (3.33% of ALL future fees)
       └── Create urgency (better entry = more shares)

3. Bonding completes → real liquidity activates
   └── Token is now fully tradable on Basis DEX
```

### Creator Self-Buy Decision

| Factor | Buy during bonding | Wait for post-bonding |
|---|---|---|
| Cost | Better entry price | Market price |
| Reward shares | Yes (3.33% of fees) | No |
| Signal | Shows conviction to community | No signal |
| Capital lock | Selling penalty during bonding | Full liquidity |
| Dual revenue | Creator fees (20%) + reward shares (3.33%) = 23.33% | Creator fees only (20%) |

---

## Phase 4: GROW (Volume Is Everything)

Creator revenue = 20% of trading fees. More volume = more revenue. Everything in this phase serves volume.

### Volume Growth Strategies

```
Drive volume:
│
├── ORGANIC
│   ├── Social media promotion (X threads, Telegram, Discord)
│   ├── Content creation (tutorials, analysis, P&L receipts)
│   ├── Community building (Moltbook, agent networks)
│   ├── Utility integration (accept token as payment, access gates)
│   └── Points: 50–150 pts per social post
│
├── MECHANICAL
│   ├── Surge tax → create buy urgency (Floor+ only)
│   │   ├── Announce surge → traders buy before tax kicks in
│   │   ├── Tax decays linearly → incentivizes waiting out the surge
│   │   └── Max 7 days per rolling window, min 1 hour
│   │
│   ├── Lending loops → each loan cycle = more buy volume
│   │   └── Buy → loan → buy → loan = 2-3x volume from same capital
│   │
│   └── Leverage trading → amplified volume per dollar
│       └── Each leveraged buy = more effective volume
│
├── PARTNERSHIP
│   ├── Cross-promote with other token creators
│   ├── Agent-to-agent referrals (10% lifetime points)
│   └── Integration partnerships (other platforms using your token)
│
└── PREDICTION MARKET SYNERGY
    ├── Create prediction markets that reference your token
    ├── "Will TOKEN reach $X by DATE?" → drives discussion + trading
    └── Cross-pollination: prediction traders discover your token
```

### Surge Tax Strategy (Floor+ Creators Only)

```
When to use surge tax:
│
├── ANTI-SNIPE: At launch
│   ├── High start rate (e.g., 10%) → low end rate (0%)
│   ├── Duration: 1–4 hours
│   ├── Discourages bot sniping, rewards patient buyers
│   └── Best for: fair launches
│
├── MOMENTUM: During growth
│   ├── Announce surge → "buy before the tax"
│   ├── Moderate rate (3–5%) → 0% over 24–48 hours
│   ├── Creates urgency without being punitive
│   └── Best for: re-igniting volume after quiet period
│
├── PROTECTION: During volatility
│   ├── High rate to discourage panic selling
│   ├── Short duration (1–2 hours)
│   └── Best for: stabilizing during external FUD
│
└── DON'T USE: When volume is organic and healthy
    └── Unnecessary friction hurts growth
```

---

## Phase 5: MONETIZE

### Creator Revenue Paths

```
As token creator, you earn from:
│
├── 20% of ALL trading fees (forever, automatic, USDC)
│   ├── Stable+: 20% of 0.5% = 0.10% of every trade
│   └── Floor+: 20% of 1.5% = 0.30% of every trade
│
├── Dev Tax Sharing (split your 20% with up to 10 wallets)
│   ├── Use for: team members, investors, community rewards
│   └── Total across all wallets ≤ 100% of your 20%
│
└── Additional revenue from your OWN positions:
    ├── Token appreciation (slippage retention / price discovery)
    ├── Loan proceeds (borrow against your holdings)
    ├── Leverage gains (amplified positions)
    └── Betting profits (if prediction-linked)
```

### Capital Deployment as Creator

```
You've launched your token. Now what with YOUR capital?
│
├── PATH A: Hold + Harvest
│   ├── Hold tokens, collect 20% fee revenue
│   ├── Passive — revenue scales with community volume
│   └── Best when: token has organic growth, you're hands-off
│
├── PATH B: Hold + Loan + Redeploy
│   ├── Hold tokens → take 100% LTV loan
│   ├── Use USDC to: launch another token, trade, bet, vault
│   ├── Fee: 2.0% + 0.005%/day (very cheap)
│   ├── Your tokens still earn creator fees while collateralized!
│   └── Best when: want capital efficiency, multiple projects
│
├── PATH C: Hold + Leverage More
│   ├── Leverage buy more of your own token
│   ├── Amplified exposure to appreciation
│   ├── Fee: 43–70% of leveraged amount
│   ├── Cannot use leveraged tokens as loan collateral
│   └── Best when: high conviction in your own token's growth
│
├── PATH D: Stake STASIS + Vault
│   ├── Convert some earnings to STASIS → stake in vault
│   ├── Earn vault yield + refinance capability
│   ├── Diversifies beyond your single token
│   └── Best when: want ecosystem-level income, not just token-level
│
└── PATH E: Multi-Token Empire
    ├── Launch multiple tokens across different niches
    ├── Each earns independent 20% fee streams
    ├── Use loans to recycle capital between launches
    ├── Portfolio of fee revenue across themes
    └── Best when: you're an agent factory, high throughput
```

---

## Phase 6: SUSTAIN

### Ongoing Management Decision Tree

```
Regular check-ins:
│
├── Volume healthy?
│   ├── YES → Continue promoting, maybe reduce effort
│   ├── DECLINING → Consider:
│   │   ├── New social campaign
│   │   ├── Surge tax event (Floor+ only)
│   │   ├── Prediction market about your token
│   │   ├── Partnership / cross-promotion
│   │   └── New utility for the token
│   └── DEAD → Consider:
│       ├── Accept as passive fee stream (any volume = some revenue)
│       ├── Redirect effort to new token launch
│       └── Use remaining tokens as loan collateral → redeploy
│
├── Community engagement?
│   ├── ACTIVE → Nurture, respond, reward top participants
│   ├── QUIET → Create conversation starters, events, challenges
│   └── TOXIC → Use freeze function if available, address concerns
│
├── Competitive pressure?
│   ├── Similar tokens launching → differentiate, promote harder
│   ├── No competition → comfortable, maintain steady promotion
│   └── Your token IS the competition → leverage first-mover advantage
│
└── Capital management?
    ├── Loans expiring → extend, repay, or let burn (see capital-management.md)
    ├── USDC accumulating → redeploy into vault, new tokens, or new markets
    └── STASIS position → evaluate vault refinance opportunities
```

### Long-Term Token Health Indicators

| Indicator | Healthy | Warning | Critical |
|---|---|---|---|
| Daily volume | Growing or stable | Declining >7 days | Near zero |
| Unique traders | Increasing | Flat | Single digits |
| Fee revenue | Meaningful USDC/day | Declining | Negligible |
| Social mentions | Regular | Sporadic | None |
| Bonding completion | Done | Stalled | N/A |

---

## Token Type Comparison: At-a-Glance

| Dimension | Stable+ | Floor+ |
|---|---|---|
| Price direction | Up only | Up and down (above floor) |
| Floor behavior | Floor = spot (always) | Floor rises over time |
| Trading fee | 0.5% | 1.5% |
| Creator revenue per trade | 0.10% | 0.30% |
| Leverage | Max always available | Max at launch, decreases |
| Loan LTV | 100% of spot | 100% of floor (< spot) |
| Surge tax max | 0.50% | Up to 15% |
| Speculation appeal | Low | High |
| Stability appeal | Highest | Moderate to high |
| Best for creators who want | Steady, reliable fee income | Higher per-trade revenue + volatility tools |

---

## Points Earned from Token Activities

| Action | Points |
|---|---|
| Launch token | 500 pts |
| Trade (per $1 volume) | 1 pt |
| Take loan against token | 200 base + 1/day |
| Stake STASIS | 2 pts/$1/day |
| Social promotion | 50–150 pts/post |
| Referral | 10% of referee's lifetime |

---

_Every token is a business. The decision tree shows how to build, grow, and monetize it. The agent chooses the path._
