# AIT Portfolio & Capital Management System — Design Document

**Date**: 2026-03-05  
**Last Updated**: 2026-03-06  
**Status**: ✅ Live — Paper trading on Hyperliquid ($50K, 10 coins)  
**Author**: Brett + Gee Gee  
**Depends on**: V14 DCA Engine, V14 Cycle Scanner, ROUTER v2 Signal Stack

---

## 1. Vision

Scale the V14 DCA grid strategy from a single-coin $300 live bot to a multi-coin portfolio running $100K+ on Hyperliquid perps. The system dynamically allocates capital across coins based on DCA cycle performance, trend momentum, and risk constraints — maximizing capital velocity while controlling concentration risk.

**Core principle**: Same brain (ROUTER signals), same hands (V14 fixed grid), smarter wallet (dynamic capital allocation).

---

## 2. Production Environment

| Component | Decision | Rationale |
|-----------|----------|-----------|
| **Exchange** | Hyperliquid (perps) | Unified margin, short capability, no custody issues |
| **Leverage** | 1.0x | Zero liquidation risk — same safety as spot |
| **Grid profile** | High (12 layers, 1.5% dev, 1.5x mult, 1.5% TP) | Best tested profile on V14 |
| **Grid type** | Fixed (not adaptive) | Fixed beat adaptive on 4/5 coins in V13 sweep |
| **Coin universe** | Hyperliquid perps only | Dynamic — selected daily by cycle scanner scores |
| **Timeframe** | 1h candles | Dominated 15m on all coins tested |
| **Paper capital** | $50K | Reset from $10K on 2026-03-06 (see §5.2 — too diluted at 10 coins) |
| **Runner** | `trading/spot/run_v14_portfolio_paper.py` | Live as of 2026-03-05 |
| **Capital manager** | `trading/spot/v14_capital_manager.py` | `CapitalRouter` class |
| **Scheduled task** | `V14PMPaperBot` (Windows Task Scheduler) | Restarts automatically on reboot |
| **Dashboard** | `docs/dashboardV14PM.html` | Live on GitHub Pages |

### Why 1.0x Leverage (No Liquidation)
- At 1.0x: **zero liquidation risk, ever.** Position is fully collateralized.
- At 1.5x: liquidation possible ~50%+ below L12 fill in a sustained crash. Unlikely but not impossible in crypto.
- The High profile grid (12 layers, 1.5% dev) is already aggressive. Adding leverage on top compounds risk without proportional reward.
- 1.5x was designed for the Medium profile (fewer layers, wider spacing). On High + 12 layers, 1.0x is the right call.

### Grid Depth at 1.0x / High Profile
| Layer | Drop from Entry | Notes |
|-------|----------------|-------|
| L1 | — | Base order (40% of allocation) |
| L2 | -1.5% | |
| L3 | -3.0% | |
| L4 | -4.5% | |
| L5 | -6.0% | |
| L6 | -7.5% | |
| L7 | -9.0% | |
| L8 | -10.5% | |
| L9 | -12.0% | |
| L10 | -13.5% | |
| L11 | -15.0% | |
| **L12** | **-16.5%** | **Last safety order. Fully deployed beyond here.** |

After L12, the bot holds and waits for TP (1.5% above weighted avg entry). In a 40% crash, capital is locked from -16.5% onward with no more layers to add.

---

## 3. Capital Architecture

### 3.1 Two-Pool Structure (Implemented)

> **Note**: The original 3-pool design (Active / Reserve / Cash Buffer) was simplified to a 2-pool model during implementation. The Cash Buffer concept was folded into sidelines cash within the active pool.

```
Total Capital
├── Active Pool  (75%)  → Score-weighted DCA positions
└── Reserve Pool (25%)  → Deep correction buffer (L6+ layers)
    └── Sidelines Cash  → Undeployed portion of Active Pool (leftover after allocation caps)
```

| Pool | Allocation | Purpose | When it deploys |
|------|-----------|---------|-----------------|
| Active | 75% | Score-weighted per-coin engines; base orders + SOs L1–L5 | Always |
| Reserve | 25% | Shared buffer across all coins; supplements deep layers | Coins hitting L6+ |
| Sidelines | Variable | Unallocated active pool cash (after 20% cap per coin) | Never forced — available for re-allocation next rebalance |

### 3.2 Why a Shared Reserve Pool (Not Per-Coin Reserves)

Naive approach: reserve 100% of grid depth per coin → most capital idle (8% utilization).

Better: shared reserve pool across portfolio. Rationale:
- The probability of ALL coins hitting L12 simultaneously is much lower than any single coin doing so
- Crypto is correlated, but not perfectly — coins enter DCA cycles at different times
- In a broad crash, the reserve deploys progressively as coins fill deeper layers
- More capital-efficient: shared $12.5K reserve (at $50K) vs ~$4K × 10 coins = $40K siloed

**Progressive release schedule:**
```
Normal:          Reserve = 100% idle
Mild correction: 1-3 coins at L4-L6 → Reserve starts supplementing
Broad correction: 5+ coins at L8+ → Reserve fully committed
Black swan:      All coins at L12 → No further capital; hold and wait for TP
```

---

## 4. Score-Weighted Capital Allocation

### 4.1 DCA Score (Existing — Point-in-Time)

The V14 Cycle Scanner already computes:
```
DCA Score = Realized_PnL × (1 - MaxDD%) × Capital_Freedom / 100
```

This measures *current* DCA cycle efficiency — how fast a coin completes profitable cycles with acceptable drawdown and available capital.

### 4.2 DCA Trend Score (New — Momentum)

**Problem**: A coin scoring 85 today but declining from 95 last week is a worse allocation target than a coin scoring 70 and rising from 40.

**Solution**: Track score history over time and compute trajectory.

| Component | What it measures | Timeframe |
|-----------|-----------------|-----------|
| **Base Score** | Current DCA cycle velocity | Rolling 30d/90d (scanner) |
| **Trend Score** | Rate of change of base score | 7d / 14d / 30d slope |

```
Trend Multiplier:
  Score accelerating (>+5% change)  → 1.2 - 1.5x
  Score stable (±5%)                → 1.0x
  Score declining (<-5% change)     → 0.5 - 0.8x
  Score collapsed (near zero)       → 0.0x (don't enter)
```

**Implementation** (added to scanner 2026-03-05):
- `append_score_history()`: Saves daily DCA scores to `trading/spot/data/score_history.json`
- `compute_trend_scores()`: Computes 7d/14d/30d slope + composite trend multiplier
- Keeps 180 days of rolling history
- De-duplicates same-day snapshots

### 4.3 Allocation Formula (Implemented)

> **✅ Implemented 2026-03-06**: The Trend Score multiplier is now wired into the live allocation. `rebalance_daily()` computes `Adjusted Score = Base DCA Score × Trend Multiplier` for ranking, filtering, and proportional weighting. Declining coins (mult < 1.0) get less capital; accelerating coins get more. Collapsed scores (mult → 0) effectively gate entry.

```
Live (current):
  Adjusted Score = Base DCA Score × Trend Multiplier
  Allocation = (Adjusted Score / Sum of qualifying adjusted scores) × Active Pool
  Subject to: Max 20% of Active Pool per coin
```

Real trend multipliers from scanner (2026-03-06 example):
- ZRO: Base 68.9 × 1.30 (accelerating) = **89.3** → top allocation
- HYPE: Base 19.1 × 1.50 (accelerating) = **28.6**
- SNX: Base 41.0 × 0.36 (declining) = **14.7** → penalized despite high base score
- COMP: Base ~18 × 0.58 (declining) = **10.5** → penalized

**Hurdle rate**: Base DCA Score ≥ 5.0. Applied before trend multiplication — coins below this are excluded entirely.

**Tier cap**: Applied after hurdle rate — only top-N by adjusted score receive allocations, where N is determined by equity tier (see §5.2).

**Example** ($100K, 8 coins, Active Pool = $75K):

```
Coin    Base  Trend  Weight  Alloc%  Capital   Status
ASTER   85    1.3x   110.5   19%*    $14,250   L1 (cycling fast, score rising)
HBAR    72    0.7x    50.4   10%     $ 7,500   L3 (score declining)
SOL     70    1.4x    98.0   17%     $12,750   L1 (score accelerating)
LINK    55    1.0x    55.0   10%     $ 7,500   Idle
NEAR    50    1.1x    55.0   10%     $ 7,500   L2
ATOM    40    0.8x    32.0    6%     $ 4,500   Idle
XRP     30    1.0x    30.0    5%     $ 3,750   L1
LTC     25    0.6x    15.0    3%*    $ 2,250   Idle (near minimum)
──────────────────────────────────
* ASTER capped at 19% (max 20%)    Reserve: $17,500
* LTC at floor (min 3%)            Buffer:  $7,500
```

HBAR has a higher base score than SOL (72 vs 70), but SOL gets more capital because its trend is accelerating (+1.4x) while HBAR's is declining (0.7x).

### 4.4 Key Rule: Trend Gates Entry, Not Exit

- **Never force-close a grid** because the trend score dropped
- When a cycle completes (TP hit), freed capital goes back to the pool
- Re-allocation happens based on *current* scores + trend at that moment
- A coin with a collapsing trend score simply doesn't get re-entered after its cycle closes
- This provides natural portfolio rotation without jarring rebalancing shocks

---

## 5. Risk Controls

### 5.1 Concentration Limits

| Rule | Value | Purpose |
|------|-------|---------|
| Max per coin | 15-20% of total | No single coin can sink the ship |
| Max top-3 | 45% of total | Prevent 2-3 coin concentration |
| Min per coin | 3-5% of total | Don't waste engine overhead on tiny positions |
| Reserve floor | ≥15% | Always have ammo for corrections |
| Cash buffer | ≥5% | Untouchable emergency fund |

### 5.2 Equity-Tiered Coin Cap

The maximum number of simultaneous coin positions is governed by current portfolio equity. This prevents capital dilution on smaller accounts — a $10K account running 10 coins produces underpowered positions that can't DCA meaningfully.

| Equity Range | Max Coins | Rationale |
|---|---|---|
| < $100 | 0 | Below minimum viable position size |
| $100 – $10K | 1 | Single best scorer only |
| $10K – $20K | 2 | Top 2 scorers |
| $20K – $30K | 3 | Top 3 scorers |
| $30K – $50K | 4 | Top 4 scorers |
| $50K – $100K | 5 | Top 5 scorers |
| $100K+ | 10 | Full universe (up to 10 scorers) |

**Tier evaluation**: Computed at each daily rebalance using current portfolio equity. The tier cap is applied *after* the hurdle rate filter (DCA Score ≥ 5.0) and *before* proportional weighting, so only the top-N qualifying coins receive allocations.

**Tier drop behavior (graceful degradation)**:
- When equity drops to a lower tier, the PM does **not** force-close any open positions.
- Existing DCA positions continue running and exit naturally via their normal TP.
- New T1 (layer-1) entries are **blocked** for coins outside the current top-N approved set.
- DCA add-on layers (L2+) on existing open positions are **always allowed** — a position is never stranded without capital to defend it.
- When a position exits via TP, freed capital is reallocated only to the top-N coins at the current tier cap.
- A Telegram alert fires on any tier change (▼ drop or ▲ rise).

**Tier rise behavior**: When equity crosses a tier boundary upward, the next daily rebalance expands `approved_symbols` to include additional top scorers. New T1 entries are opened on the next qualifying signal.

**Implementation**: `CapitalRouter.get_tier_coin_cap(equity)` + `rebalance_daily(current_equity=...)` in `trading/spot/v14_capital_manager.py`. The runner tracks `_approved_symbols` and enforces the gate in `_process_actions()`.

### 5.3 Correlation Gate

Crypto is highly correlated during crashes. When the portfolio is broadly stressed:

```
IF >60% of active coins are at L4+ simultaneously:
  → HALT new entries for idle coins
  → Preserve Reserve Pool for existing positions
  → Resume new entries only when portfolio stress drops below 40%
```

This prevents the system from opening fresh L1 positions in new coins while most of the portfolio is deep underwater and the Reserve Pool is being consumed.

### 5.4 No Liquidation Triggers (Spot-Like Behavior)

- At 1.0x leverage on Hyperliquid perps: **no liquidation possible**
- No stop-loss on individual positions
- No forced selling on drawdown thresholds
- The DCA grid naturally averages into dips
- ROUTER v2 signal stack handles macro phase transitions (top detection → unwind → SHORT_DCA)
- Worst case: capital is locked in a deep position until price recovers to averaged TP

---

## 6. Edge Cases & Flash Crash Analysis

### 6.1 Flash Crash (-20% to -40% in hours)

**What happens:**
- Coins at L1 rapidly fill through L8-L12 in a single session
- Multiple coins fill simultaneously (high correlation in crashes)
- Reserve Pool deploys to supplement active positions
- After all layers fill, positions hold and wait

**Risk:**
- All coins at L12 = 100% capital deployed, no flexibility
- Recovery requires price to reach averaged TP (lower than L12 entry due to DCA averaging)
- Could take days to weeks depending on bounce speed

**Mitigation:**
- Correlation gate halts new entries when >60% of coins stressed
- Reserve Pool provides extra ammo for the deepest layers
- Cash Buffer remains untouched (5-10K escape hatch)
- 1.0x leverage means no liquidation regardless of depth

**Historical reference:** BTC -15% flash crash in Dec 2024, ETH -22% in Apr 2025. Both recovered TP within 48-72h. The DCA grid would have filled L8-L10 and averaged profitably on the bounce.

### 6.2 Sustained Bear Market (-40% to -70% over weeks/months)

**What happens:**
- Coins fill all 12 layers over days/weeks
- Grid is fully deployed at -16.5% from entry
- Price continues dropping beyond grid range
- Capital is 100% locked, no further averaging possible

**Risk:**
- Maximum unrealized loss: depends on how far below L12 price goes
- No additional capital to average further
- Recovery time measured in weeks or months

**Mitigation:**
- ROUTER v2 top detection (OB93 → 2D divergence → 35d timeout) should detect the bear *before* it begins, switching to SHORT_DCA or ROUTER phase
- SHORT_DCA profits from the decline
- If top detection fails and we're caught in LONG_DCA during a bear: the 16.5% grid absorbs the first leg, then capital is trapped until macro conditions improve
- The Cash Buffer ($5-10K) is available for manual intervention if needed

### 6.3 Single-Coin Black Swan (De-peg, Exploit, Delisting)

**What happens:**
- One coin crashes -80%+ while others are fine
- That coin's allocation is effectively wiped
- Grid fills all layers immediately, then holds a near-worthless bag

**Risk:**
- Max loss = that coin's allocation (capped at 15-20% of portfolio)
- Other coins unaffected

**Mitigation:**
- Concentration limit of 15-20% caps single-coin exposure
- Hyperliquid perps settle in USDC — you don't hold the underlying asset
- Perps can be closed at any price (no liquidity freeze like spot DEX tokens)
- Consider: circuit breaker at -30% single-candle drop → force-close that coin's position

### 6.4 Cascading Correlation Event (2022-style crypto winter)

**What happens:**
- Everything drops 60-80% over months
- All coins fill all layers in weeks 1-2
- Then price keeps falling for months
- No ROUTER signal fires because the decline is slow and grinding (no sharp divergence)

**Risk:**
- Entire Active Pool + Reserve Pool trapped in underwater positions
- Only Cash Buffer remains liquid
- Recovery time: months to years

**Mitigation:**
- This is the scenario where SHORT_DCA becomes critical
- If ROUTER correctly switches to SHORT_DCA before the grind, the short grid *profits* from the decline
- Weekly portfolio review: if >80% of positions are at L12 for >14 days, escalate to manual review
- The DCA Trend Score naturally rotates capital away from coins with collapsing scores, reducing future exposure
- Consider: macro-level risk switch (e.g., CFGI <20 for >30 days → reduce Active Pool to 50%, increase Cash Buffer)

### 6.5 Whipsaw / Range-Bound Market

**What happens:**
- Price oscillates ±5-10% for weeks
- DCA grid constantly fills L1-L4 and TPs
- High cycle velocity, small profits per cycle
- This is actually the **best** scenario for the grid

**Impact:**
- Capital is constantly cycling (high velocity)
- DCA scores are high across most coins
- Reserve Pool barely needed
- Portfolio compounds steadily

### 6.6 Exchange Downtime / API Failure

**What happens:**
- Hyperliquid API becomes unreachable
- Bot can't place orders, check balances, or update state
- Market moves while bot is blind

**Risk:**
- Missed TP fills (opportunity cost)
- Missed SO fills (grid gaps — could miss averaging opportunities)
- Stale state file if bot crashes during execution

**Mitigation:**
- Bot already has reconciliation logic (balance check vs engine state every 5 min)
- Drift alert at >10% mismatch
- On restart: skip backfill flag prevents historical re-execution
- Consider: dead-man's switch — if no status update for >2h, alert via Telegram

---

## 7. Portfolio Manager — Architecture

### 7.1 Responsibilities

The Portfolio Manager is a **new layer** above the V14 DCA engines:

```
┌─────────────────────────────────────────┐
│           Portfolio Manager              │
│  ┌───────────┐  ┌──────────┐  ┌──────┐  │
│  │ Allocator │  │ Risk Mgr │  │ Pool │  │
│  │ (scores)  │  │ (limits) │  │ Mgr  │  │
│  └─────┬─────┘  └────┬─────┘  └──┬───┘  │
└────────┼─────────────┼───────────┼───────┘
         │             │           │
    ┌────▼─────┐  ┌────▼───┐  ┌───▼────┐
    │ V14 Eng  │  │ V14 Eng│  │ V14 Eng│  ...per coin
    │ (HBAR)   │  │ (SOL)  │  │ (LINK) │
    └──────────┘  └────────┘  └────────┘
```

| Component | Role |
|-----------|------|
| **Allocator** | Reads scanner scores + trend, computes per-coin allocation targets |
| **Risk Manager** | Enforces concentration caps, correlation gate, reserve floor |
| **Pool Manager** | Tracks Active/Reserve/Buffer pools, releases reserve on stress |
| **V14 Engines** | Individual coin DCA engines (unchanged from current implementation) |

### 7.2 Operational Flow

1. **Daily (on scanner run)**: Allocator reads DCA scores + trend multipliers, computes target allocation per coin
2. **On cycle completion (TP hit)**: Freed capital returns to Active Pool, re-allocated per current targets
3. **On new entry signal**: Allocator checks if coin has allocation headroom, draws from Active Pool
4. **On stress (multiple coins deep)**: Pool Manager releases Reserve into Active; Risk Manager may halt new entries
5. **Never mid-grid**: Allocation changes only affect new capital deployments, not existing grid positions

### 7.3 What Changes for V14 Engines

**Nothing.** Each V14 engine receives a `capital` parameter and runs its fixed grid against that amount. The only change is that `capital` is set dynamically by the Portfolio Manager instead of being hardcoded.

---

## 8. Implementation Roadmap

### Phase 1: Data Collection ✅ Complete
- [x] Score history tracking in cycle scanner (`score_history.json`)
- [x] Trend score computation (7d/14d/30d slope + composite multiplier)
- [x] Scanner scheduled daily (`AIT_DashboardSync` task, every 10 min)
- [ ] Dashboard: add trend score column to scanner output *(deferred)*

### Phase 2: Portfolio Manager Prototype ✅ Complete (2026-03-05)
- [x] `CapitalRouter` class — Active/Reserve pool tracking, `rebalance_daily()`, `request_capital()`, `return_capital()`
- [x] Equity-tiered coin cap — `get_tier_coin_cap()`, tier-aware `rebalance_daily()` (2026-03-06)
- [x] Score-weighted allocation with 20% max cap per coin
- [x] Hurdle rate gate (DCA Score ≥ 5.0)
- [x] T1 entry gate — blocks new layer-1 entries for out-of-tier coins
- [x] Graceful degradation — existing positions run to TP on tier drop
- [x] Telegram alerts on tier changes
- [x] `run_v14_portfolio_paper.py` — live runner with daily rebalance, capital routing, action interception
- [x] Trend Score multiplier wired into allocation — `Adjusted Score = Base DCA Score × Trend Multiplier` (2026-03-06)
- [x] Score history backfill via `--backfill-history N` / `--as-of YYYY-MM-DD` flags on scanner (2026-03-06)
- [ ] Correlation gate (halt new entries when >60% of coins at L4+) *(not yet built)*

### Phase 3: Paper Testing 🔄 In Progress (since 2026-03-05)
- [x] Live paper bot running on Hyperliquid — $50K, 10 coins, High profile
- [x] `dashboardV14PM.html` — live on GitHub Pages with tier cap badge
- [ ] Test flash crash scenarios (replay historical data)
- [ ] Test correlation gate triggers *(gate not yet built)*
- [ ] Compare: static allocation vs score-weighted vs score+trend weighted
- [ ] Minimum 30 days paper trading before live consideration

### Phase 4: Live Deployment 🔒 Locked (pending paper results)
- [ ] Evaluate paper results after 30+ days
- [x] ~~Wire Trend Score multiplier into allocation before going live~~ Done (2026-03-06)
- [ ] Build correlation gate
- [ ] Start live with $10K, scale after validation
- [ ] Full monitoring: Telegram alerts ✅, dashboard ✅, drift checks *(pending)*

---

## 9. Open Questions

1. ~~**Optimal number of coins**~~ **Resolved (2026-03-06)**: Equity-tiered cap. See §5.2.
2. **Rebalancing frequency**: Daily (current). Weekly would be less responsive but reduce churn. Monitor how aggressively the daily rebalance rotates coins and revisit after 30 days of data.
3. **Reserve Pool release rules**: Currently L6+ triggers reserve draw. Tiered release (25% at L6, 50% at L8, 100% at L10) would be more controlled — not yet implemented.
4. **SHORT_DCA capital**: When ROUTER flips a coin to SHORT_DCA, does it keep the same allocation? Shorts carry different risk profiles in crypto. *Not yet encountered in paper run.*
5. **Circuit breaker on single-coin crash**: Force-close at -30% single candle? Currently the grid holds and waits for TP at any depth. Consider as a future risk control.
6. **Macro risk switch**: Reduce Active Pool when CFGI < 20 for > 30 days or BTC dominance spikes? Not implemented. Could be a meaningful bear-market defense.
7. ~~**Trend Score multiplier**~~: **Resolved (2026-03-06)**. `Adjusted Score = Base DCA Score × Trend Multiplier` is live in `rebalance_daily()`. Accelerating coins get up to 1.5x boost; declining coins penalized down to 0.36x. All 45 scanner coins have trend data via 7-day backfill.
8. **Correlation gate**: Not yet built. When >60% of active coins hit L4+ simultaneously, halt new T1 entries for idle coins. Needed for broad crash scenarios.

---

## 10. Key Design Decisions (Locked)

| Decision | Choice | Date |
|----------|--------|------|
| Exchange | Hyperliquid perps | 2026-03-05 |
| Leverage | 1.0x (zero liquidation) | 2026-03-05 |
| Grid type | Fixed (not adaptive) | 2026-02-28 |
| Grid profile | High (12L, 1.5% dev, 1.5x mult, 1.5% TP) | 2026-02-28 |
| Pool split | 75% Active / 25% Reserve (no separate cash buffer) | 2026-03-05 |
| Allocation method | DCA Score proportional, 20% max cap per coin | 2026-03-05 |
| Hurdle rate | DCA Score ≥ 5.0 to qualify for allocation | 2026-03-05 |
| Entry/exit rule | Tier gate blocks new T1 entries; existing positions exit naturally | 2026-03-05 |
| Rebalance cadence | Daily (on first new candle of each UTC day) | 2026-03-05 |
| Max coins | Equity-tiered cap — 1 to 10 coins based on equity (see §5.2) | 2026-03-06 |
| Paper capital | $50K (reset from $10K — underpowered at 10 coins) | 2026-03-06 |
| Trend multiplier | Live — `Adjusted Score = Base × Trend Mult` in rebalance_daily() | 2026-03-06 |
| Score backfill | `--backfill-history N` / `--as-of YYYY-MM-DD` on scanner for instant trend data | 2026-03-06 |

---

*This document captures the complete portfolio management design. V14 engine spec (`v14-dca-architecture.md`) and system spec (`v14-system-spec.md`) remain unchanged — this system wraps around them.*
