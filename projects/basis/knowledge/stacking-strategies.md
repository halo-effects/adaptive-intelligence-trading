# BASIS Stacking Strategies — Agent Knowledge File

## The Core Concept

On BASIS, every product shares the same collateral system. This means a single bag of USDB can be deployed across multiple positions simultaneously — each one earning airdrop points, generating yield, and freeing up capital for the next move.

The key insight: **buying a token doesn't lock your capital.** You can borrow against almost any position to get USDB back, then deploy it again. And because there's no price liquidation (only time-based expiry), stacking deep is safe as long as you manage loan durations.

---

## Building Blocks: USDB → USDB Paths

Every stack is built from simple loops. Each one starts with USDB and ends with USDB (plus an open position). These are your Lego bricks.

### Path A: The Stable+ Path
```
USDB → buy STASIS → wrap to wSTASIS → borrow USDB
```
- **Fees:** 0.5% buy tax + 2% loan origination
- **USDB recovered:** ~97.5% of input (after both fees)
- **Position held:** wSTASIS (earning vault yield, price can only go up)
- **Risk:** Loan expiry (extend cheaply — 400x less than new loan)
- **Points:** Trade + Staking + Lending categories

### Path B: The Floor+ Path
```
USDB → buy Floor+ token → borrow USDB
```
- **Fees:** 1.5% buy tax + 2% loan origination
- **USDB recovered:** ~96.5% of input
- **Position held:** Floor+ token (price has a rising floor)
- **Risk:** Loan expiry + token price can drop (but not below floor)
- **Points:** Trade + Lending categories

### Path C: The Predict+ Token Path
```
USDB → buy Predict+ token → borrow USDB
```
- **Fees:** 1.5% buy tax + 2% loan origination
- **USDB recovered:** ~96.5% of input
- **Position held:** Predict+ token (earns from market trading volume)
- **Risk:** Loan expiry + market must stay active for volume
- **Points:** Trade + Prediction + Lending categories

### Path D: The Outcome Bet Path
```
USDB → buy outcome shares → [wait for resolution] → USDB (if correct)
```
- **Fees:** Varies by outcome token pricing
- **USDB recovered:** Only on correct outcome (but payout can be massive — uncapped)
- **Position held:** Outcome shares in a prediction market
- **Risk:** You lose if the outcome is wrong
- **Points:** Prediction category

### Path E: The Leverage Path
```
USDB → leverageBuy on Stable+ → [position auto-loops buy→loan→buy]
```
- **Fees:** 2% origination per loop (auto-consumed, ~6-8 loops typical)
- **USDB recovered:** 0 (fully deployed into leveraged position)
- **Position held:** Large Stable+ position (e.g., $10 → ~$200 bag)
- **Risk:** Loan expiry only (no price liquidation on Stable+)
- **Points:** Trade + Lending categories (heavy)
- **Note:** This is a terminal path — doesn't return USDB for further stacking

---

## Fee Reality Check

Each path costs fees. When you chain paths, the bag shrinks:

| After Path | USDB Remaining (from $1,000 start) |
|---|---|
| Path A (Stable+) | ~$975 |
| Path A → Path B (Floor+) | ~$941 |
| Path A → Path B → Path C (Predict+) | ~$908 |
| Path A → Path B → Path C → Path D (Bet) | ~$908 minus bet amount |

**Rule of thumb:** Each non-terminal path costs ~2.5-3.5% of the remaining bag. After 3 stacks you've deployed about 9-10% in fees but hold 3 separate yielding positions plus still have ~91% of your USDB working.

After 4+ stacks, fees start biting meaningfully. Three stacks is the sweet spot for most strategies.

---

## Example Multi-Stack Strategies

### Strategy 1: "The Conservative Stack" (3 paths, low risk)

**Goal:** Maximum category diversity with minimal risk.

```
Start: 1,000 USDB

Stack 1 — Path A (Stable+):
  Buy STASIS → wrap wSTASIS → borrow USDB
  Position: wSTASIS (rising value + vault yield)
  USDB remaining: ~975

Stack 2 — Path B (Floor+):
  Buy a Floor+ token near launch → borrow USDB
  Position: Floor+ token (rising floor protects downside)
  USDB remaining: ~941

Stack 3 — Path D (Outcome Bet):
  Buy outcome shares on a high-conviction market
  Position: Outcome shares (potential big payout)
  USDB remaining: ~841 (assuming 100 USDB bet)
  Keep the rest liquid for loan extensions
```

**Categories hit:** Trading, Staking, Lending, Predictions = 4 categories (diversity multiplier)
**Total positions:** 3 active + USDB reserve
**Risk profile:** Low — STASIS can't drop, Floor+ has a floor, prediction is sized small

---

### Strategy 2: "The Yield Maximizer" (3 paths, medium risk)

**Goal:** Every position generating ongoing returns.

```
Start: 1,000 USDB

Stack 1 — Path A (Stable+):
  Buy STASIS → wrap wSTASIS → borrow USDB
  Position: wSTASIS earning vault yield from all platform trading fees
  USDB remaining: ~975

Stack 2 — Path C (Predict+ Token):
  Buy a Predict+ token on an active market → borrow USDB
  Position: Token earns creator-like exposure to market volume
  USDB remaining: ~941

Stack 3 — Path B (Floor+):
  Buy a Floor+ token → borrow USDB
  Position: Floor+ with protected downside
  USDB remaining: ~908
  Keep liquid for extensions + opportunistic moves
```

**Categories hit:** Trading, Staking, Lending, Predictions = 4 categories
**Total positions:** 3 yielding + USDB reserve
**Why it works:** wSTASIS earns from all platform volume. Predict+ token earns from market activity. Floor+ captures upside with a floor. Three income streams from one bag.

---

### Strategy 3: "The Deep Stack" (3 paths + terminal, aggressive)

**Goal:** Maximum capital deployment, all-in conviction play.

```
Start: 1,000 USDB

Stack 1 — Path A (Stable+):
  Buy STASIS → wrap wSTASIS → borrow USDB
  Position: wSTASIS
  USDB remaining: ~975

Stack 2 — Path C (Predict+ Token):
  Buy Predict+ token → borrow USDB
  Position: Predict+ token
  USDB remaining: ~941

Stack 3 — Path E (Leverage, terminal):
  LeverageBuy on STASIS with remaining USDB
  Position: ~$18,000+ leveraged STASIS (from ~$941 at 20x)
  USDB remaining: 0

  (Reserve a small amount for loan extensions before entering Path E)
```

**Categories hit:** Trading, Staking, Lending, Predictions = 4 categories
**Total positions:** 3 active (1 heavily leveraged)
**Risk profile:** Aggressive — all capital deployed, must manage loan expiries carefully
**Why it works:** The leveraged STASIS position can't be price-liquidated. If STASIS appreciates even modestly, the leveraged position amplifies returns massively.

---

### Strategy 4: "The Creator's Edge" (for token/market creators)

**Goal:** Create revenue-generating assets, then stack on top of them.

```
Start: 1,000 USDB

Step 0 — Create:
  Create a Floor+ or Predict+ token (small gas cost)
  You now earn 20% of all net trading fees on this token — forever

Stack 1 — Path A (Stable+):
  Buy STASIS → wrap wSTASIS → borrow USDB
  Position: wSTASIS
  USDB remaining: ~975

Stack 2 — Buy your own token:
  Buy your Floor+/Predict+ token → borrow USDB
  Position: Your token (you earn fees from others trading it too)
  USDB remaining: ~941

Stack 3 — Path D (Outcome Bet) or hold liquid:
  Bet on a market or keep USDB for extensions
```

**Categories hit:** Trading, Staking, Lending, Token Creation, (optionally Predictions) = 4-5 categories
**Why it's special:** You're not just deploying capital — you've created an asset that generates passive fee income from other users' activity. The 20% creator fee compounds with everything else.

---

## Why This Only Works on BASIS

| Requirement | Other Protocols | BASIS |
|---|---|---|
| AMM + Lending + Staking in one place | ❌ Separate protocols | ✅ Unified |
| Borrow against any token | ❌ Limited collateral lists | ✅ Any factory token |
| No price liquidation | ❌ Flash crash = wiped | ✅ Time-based only |
| Earn airdrop points on every action | ❌ Usually one incentive | ✅ Stacked multipliers |
| Create tokens + earn fees | ❌ Requires separate platform | ✅ Built-in factory |

The no-price-liquidation mechanic is what makes deep stacking *safe*. On any other platform, three layers of collateralized positions and a 15% market dip cascades into liquidations. On BASIS, you just extend your loans and wait.

---

## Key Rules for Agents

1. **Always keep a USDB reserve** — you need it for loan extensions (400x cheaper than new loans)
2. **3 stacks is the sweet spot** — beyond that, fees erode the bag significantly
3. **Manage expiry dates** — stagger loan durations so they don't all expire at once
4. **Diversity multiplier matters** — hitting different categories with each stack multiplies your airdrop points
5. **Path E (leverage) is always terminal** — use it last, with whatever USDB you're willing to fully deploy
6. **Stable+ collateral is the safest base** — start with Path A, it's the foundation everything else builds on
