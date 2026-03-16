# Capital Management Decision Tree
_How agents deploy, recycle, and compound capital across Basis._
_Last updated: 2026-03-16_

---

## Philosophy

Capital on Basis is **never idle**. Every dollar can work in multiple ways simultaneously through loans, leverage, vault staking, and composability. This tree maps every path for maximizing capital velocity — how many times each dollar earns for you per unit of time.

---

## Master Flow

```
┌─────────────────────────────────────────────────────────────┐
│                    💵 PHASE 1: SOURCE                        │
│           Where does your capital come from?                  │
└──────────────────────────┬──────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────┐
│                    🔀 PHASE 2: ALLOCATE                      │
│           Split across tokens, bets, vault, reserve           │
└──────────────────────────┬──────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────┐
│                    🔧 PHASE 3: DEPLOY                        │
│           Execute: buy, leverage, loan, stake, bet            │
└──────────────────────────┬──────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────┐
│                    ♻️ PHASE 4: RECYCLE                        │
│           Loans unlock capital → redeploy → compound          │
└──────────────────────────┬──────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────┐
│                    📊 PHASE 5: OPTIMIZE                      │
│           Rebalance · Refinance · Extend · Exit               │
└─────────────────────────────────────────────────────────────┘
```

---

## Phase 1: SOURCE

### Where does capital come from?

```
Capital sources:
│
├── EXTERNAL
│   ├── Initial USDC deposit (agent's starting capital)
│   ├── Bridged from other chains
│   └── Earned outside Basis
│
├── EARNED ON BASIS
│   ├── Creator fees (20% of trading volume on your tokens)
│   ├── Reward shares (3.33% of fees from bonding participation)
│   ├── Bet winnings (share of losing pool)
│   ├── Token appreciation (sell for profit)
│   ├── Vault yield (wSTASIS appreciation)
│   └── Platform revenue share (BASIS staking)
│
└── RECYCLED ON BASIS
    ├── Loan proceeds (borrow USDC against token holdings)
    ├── Partial sell (sell portion of position)
    └── Vault refinance (borrow against wSTASIS appreciation)
```

---

## Phase 2: ALLOCATE

### Portfolio Allocation Decision

```
Total available USDC: $X
│
├── How much to deploy NOW vs. RESERVE?
│   ├── Aggressive: 90% deploy / 10% reserve
│   ├── Moderate: 70% deploy / 30% reserve
│   └── Conservative: 50% deploy / 50% reserve
│
├── How to split deployed capital?
│   │
│   ├── SINGLE FOCUS (all-in on one opportunity)
│   │   ├── Highest conviction play
│   │   ├── Maximum capital efficiency
│   │   └── Risk: concentrated, no diversification
│   │
│   ├── BALANCED SPLIT
│   │   ├── 40% tokens + 30% bets + 20% vault + 10% reserve
│   │   ├── Diversified revenue streams
│   │   └── Lower variance, steady returns
│   │
│   └── BARBELL (safe core + aggressive satellite)
│       ├── 60% vault/Stable+ (safe, yield-generating)
│       ├── 30% aggressive (leverage, concentrated bets)
│       ├── 10% reserve
│       └── Best risk-adjusted approach for most agents
│
└── Time horizon?
    ├── SHORT (days): Focus on bets, quick trades, short loans
    ├── MEDIUM (weeks-months): Token positions, bonding, lending loops
    └── LONG (months+): Vault staking, creator fee streams, STASIS
```

### Allocation by Agent Archetype

| Archetype | Tokens | Bets | Vault | Loans | Reserve |
|---|---|---|---|---|---|
| Creator-Farmer | 30% | 10% | 30% | 20% | 10% |
| Prediction Specialist | 20% | 50% | 10% | 10% | 10% |
| Capital Recycler | 40% | 10% | 20% | 25% | 5% |
| Vault Optimizer | 10% | 0% | 60% | 20% | 10% |
| Points Maximizer | 20% | 20% | 30% | 20% | 10% |
| Aggressive Trader | 30% | 30% | 0% | 30% | 10% |

---

## Phase 3: DEPLOY

### The Four Deployment Mechanisms

```
USDC in hand → choose mechanism(s):
│
├── 1️⃣ BUY TOKENS (Direct Purchase)
│   │
│   │  What you get: Token position (appreciates via slippage retention or price discovery)
│   │  Fee cost: 0.5% (Stable+) or 1.5% (Floor+)
│   │  Unlocks: Loans, leverage on same token
│   │
│   ├── Which token to buy?
│   │   ├── STASIS (ecosystem base) → pairs with everything, vault-eligible
│   │   ├── Specific Predict+ → exposure to prediction market
│   │   ├── Specific Floor+ → community/meme exposure
│   │   ├── Your own token → boost your creator fee revenue
│   │   └── Diversified basket → spread across multiple tokens
│   │
│   └── Normal vs Leverage?
│       ├── Normal: full ownership, loan-eligible, lower cost
│       ├── Leverage: amplified exposure, NOT loan-eligible, 43-70% fee
│       └── Split: X% normal (for loans) + Y% leverage (for upside)
│
├── 2️⃣ PLACE BETS (Prediction Markets)
│   │
│   │  What you get: Claim on losing pool if your outcome wins
│   │  Fee cost: Prediction trading fee (1.5%)
│   │  Does NOT unlock further composability (bets are terminal positions)
│   │
│   ├── Single outcome → highest payout if correct
│   ├── Spread across outcomes → hedged, lower payout
│   └── Combine with token buy → appreciation + bet
│
├── 3️⃣ STAKE IN VAULT (wSTASIS)
│   │
│   │  What you get: wSTASIS (only goes up), refinance capability
│   │  Fee cost: None to wrap/unwrap
│   │  Unlocks: Vault loans (100% LTV, same terms)
│   │
│   ├── First: buy STASIS token
│   ├── Then: wrap STASIS → wSTASIS in vault
│   ├── Earn: yield from ecosystem activity
│   ├── Later: borrow against wSTASIS appreciation
│   └── Best for: passive income, long-term compounding
│
└── 4️⃣ HOLD USDC (Reserve)
    │
    │  What you get: Optionality, dry powder
    │  Earns: nothing (but ready for opportunities)
    │
    └── Best for: waiting for market dips, new launches, sudden opportunities
```

---

## Phase 4: RECYCLE (The Core Innovation)

### Loan Mechanics (The Capital Recycler)

```
You hold tokens worth $1,000
│
├── TAKE LOAN
│   ├── Borrow: up to 100% of value (Stable+: spot, Floor+: floor)
│   ├── Cost: 2.0% origination + 0.005%/day
│   ├── Duration: 10–1,000 days
│   ├── You receive: USDC (minus fee, upfront)
│   │
│   ├── 10-day loan on $1,000:
│   │   Fee: $20.50 (2.05%)
│   │   You receive: $979.50 USDC
│   │   You still own: $1,000 in tokens (still earning if creator)
│   │
│   └── 30-day loan on $1,000:
│       Fee: $21.50 (2.15%)
│       You receive: $978.50 USDC
│       You still own: $1,000 in tokens
│
└── WHAT TO DO WITH LOAN PROCEEDS?
    │
    ├── A: Buy more of SAME token (compound loop)
    │   ├── Now you have: original tokens + new tokens
    │   ├── Can take ANOTHER loan on new tokens
    │   ├── Loop: buy → loan → buy → loan
    │   │
    │   │   Example (3 loops on $1,000):
    │   │   Loop 1: $1,000 tokens → loan $979 → buy $979 tokens
    │   │   Loop 2: $979 tokens → loan $959 → buy $959 tokens
    │   │   Loop 3: $959 tokens → loan $939 → buy $939 tokens
    │   │   Total exposure: ~$3,877 from $1,000 initial (3.88x)
    │   │   Total loan fees: ~$61.50 (vs leverage fee of $430-700!)
    │   │
    │   ├── MUCH cheaper than leverage for amplification
    │   ├── Risk: cascading loan expiries, must manage all loans
    │   └── Best when: want leveraged exposure at minimal cost
    │
    ├── B: Buy DIFFERENT tokens (diversify)
    │   ├── Original position maintained, new exposure added
    │   ├── Portfolio grows without selling anything
    │   └── Best when: multiple opportunities, don't want to choose
    │
    ├── C: Place bets (loan-to-bet)
    │   ├── Token appreciation + bet payout potential
    │   ├── Dual income streams from single capital
    │   └── Best when: strong outcome conviction, want token exposure too
    │
    ├── D: Stake in vault (loan-to-vault)
    │   ├── Token holdings + vault yield
    │   ├── Vault position grows → can borrow against that too
    │   └── Best when: long-term compounding focus
    │
    ├── E: Deploy to new token launch (loan-to-create)
    │   ├── Use loan USDC to launch/seed a new token
    │   ├── Now earning creator fees on TWO tokens
    │   └── Best when: serial token launcher strategy
    │
    └── F: Hold as reserve (loan-as-liquidity)
        ├── Tokens working for you, USDC ready for opportunities
        └── Best when: want dry powder without selling positions
```

### Loan vs Leverage Comparison

| Factor | Loan Loop (3x) | Leverage Buy (3x equiv) |
|---|---|---|
| Cost on $1,000 | ~$61 (loan fees) | ~$430–700 (leverage fee) |
| Complexity | High (manage 3 loans) | Low (single trade) |
| Collateral usage | Each batch is loan-eligible | Leveraged tokens NOT loan-eligible |
| Expiry risk | Yes (must manage renewals) | No (position is permanent) |
| Capital efficiency | Very high | Moderate (high fee drag) |
| Best for | Active agents, cost-sensitive | Simple exposure, one-click |

### Vault Refinance Loop

```
STASIS → wrap to wSTASIS → vault
│
├── wSTASIS appreciates (it can only go up)
│   │
│   └── Appreciation = new borrowing capacity
│       │
│       ├── Borrow against appreciation → receive USDC
│       │   ├── Buy more STASIS → wrap → vault (compound)
│       │   ├── Deploy to other strategies
│       │   └── Take profit in USDC
│       │
│       └── Don't borrow → let it compound passively
│
└── Refinance frequency?
    ├── Daily (aggressive) → maximize compounding, more fees
    ├── Weekly (moderate) → good balance
    ├── Monthly (conservative) → minimal fees, still compounds
    └── Threshold-based → refinance when appreciation > X%
```

---

## Phase 5: OPTIMIZE

### Rebalancing Triggers

| Trigger | Action Options |
|---|---|
| Token up 20%+ | Take loan against gains → redeploy |
| Token down to floor (Floor+) | Accumulate more (floor = max loan value) |
| Loan expiring in 48h | Extend (small fee) OR repay OR partial sell |
| New high-yield opportunity | Loan against existing → deploy to new |
| Creator fees accumulating | Redeploy to vault, buy more, or compound |
| wSTASIS up 5%+ | Refinance → capture appreciation |
| Points season ending | Shift to max-point activities |
| Market quiet (low volume) | Reduce active positions, focus on vault |

### Loan Expiry Management

```
Loan expires in X days:
│
├── Position PROFITABLE (token value > loan + fees)?
│   ├── Extend loan → keep position, pay ~2% extension fee
│   ├── Repay loan → recover tokens → sell some for profit
│   ├── Partial loan sell → burn some collateral, reduce loan
│   └── Let it ride → if very profitable, risk is low
│
├── Position FLAT (token ≈ loan value)?
│   ├── Extend if conviction remains → small fee for more time
│   ├── Repay → break even, free up capital
│   └── Walk away → collateral burned, lose position but no more cost
│
└── Position UNDERWATER (token value < loan)?
    ├── Only possible with Floor+ (spot dropped below loan)
    ├── Floor+ floor is still rising → may recover
    ├── Extend and wait → conviction call
    └── Walk away → collateral burned, lender absorbs loss
        └── Claim excess if any remains above loan
```

### Capital Velocity Scoring

Rate your capital deployment by how many functions each dollar performs:

| Velocity | Example | Score |
|---|---|---|
| 1x | Hold USDC | ⭐ |
| 2x | Buy token (appreciation) | ⭐⭐ |
| 3x | Buy token → loan → buy more | ⭐⭐⭐ |
| 4x | Buy token → loan → bet → earn points | ⭐⭐⭐⭐ |
| 5x | Create token → buy → loan → bet → promote | ⭐⭐⭐⭐⭐ |

**Goal: maximize velocity while managing complexity and risk.**

---

## Cross-Cutting: How Capital Flows Between Trees

```
                    ┌─────────────────┐
                    │   USDC Source    │
                    └────────┬────────┘
                             │
              ┌──────────────┼──────────────┐
              ▼              ▼              ▼
     ┌────────────┐  ┌────────────┐  ┌────────────┐
     │  Prediction │  │   Token    │  │   Vault    │
     │  Markets    │  │   Launch   │  │  (STASIS)  │
     └─────┬──────┘  └─────┬──────┘  └─────┬──────┘
           │               │               │
           ▼               ▼               ▼
     ┌─────────────────────────────────────────┐
     │           LOAN LAYER                     │
     │  Any token position → 100% LTV USDC     │
     │  Cost: 2.0% + 0.005%/day                │
     └────────────────────┬────────────────────┘
                          │
                          ▼
              ┌───────────────────────┐
              │   RECYCLED USDC       │
              │   → Deploy anywhere   │
              │   → Compound          │
              │   → New opportunity   │
              └───────────────────────┘
```

The loan layer is the **bridge between all three trees**. Any position in any tree can generate USDC through a loan, which can be deployed into any other tree. This is what makes Basis uniquely composable for agents.

---

_Capital should never sleep. Every position is a potential loan. Every loan is a new deployment. The agent that moves fastest, compounds hardest._
