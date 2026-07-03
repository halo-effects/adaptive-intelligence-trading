# Overflow Entry v2 — Soft-Ceiling Deposit Deployment
_Version: 1.2 | Date: 2026-07-03 | Status: SPEC — pending approval (Hard Rule #21)_
_v1.1: D-GRID resolved to the bull-phase grid (implementation-handoff-prompt.md rev. 3, Part 2):
_v1.2: added admission condition 8 — overflow defers to same-rebalance normal entries (zombie-freed slots deploy first); explicit priority order top-up → normal → overflow._
`L1_COST_FRACTION = 0.40`, imported from `GridModel` — the §3.4 placeholder is now concrete._
_Supersedes: overflow-entry logic in `_do_rebalance()` (OVERFLOW_ENTRY_ENABLED, 2026-06-19)_
_References: V14PM_SYSTEM_ARCHITECTURE.md §7.3/§7.6/§7.7, layer-reconstruction-capital-flow-zombie-slots.md,
AIT_V14PM_Audit_Report_2026-07-03.md finding H4_

---

## 1. Problem Statement

### 1.1 The v1 overflow branch is unreachable

Audit finding H4 (2026-07-03): the existing overflow gate inside `_do_rebalance()` can never
fire. Mechanical verification across 7,680 enumerated scenarios produced zero admissions.

Root cause — candidate starvation:

1. The new-coin loop iterates only over `allocations`, the output of
   `rebalance_daily()`, which slices candidates to the tier cap
   (`top_coins = qualifying_coins[:max_coins]`).
2. Overflow requires `all_maxed` over non-zombie positions. A maxed position that is
   **not** approved is a zombie (excluded from the count); therefore every position that
   survives into `all_maxed` is maxed **and approved**.
3. Those maxed-and-approved incumbents occupy every slot of the cap-sliced allocations
   dict → the loop never encounters a new symbol → the overflow check is never consulted.
4. In the only case where a new symbol *does* appear (an incumbent decayed out of the
   top-N), the maxed incumbent is a zombie, the slot is freed, and the new coin enters
   through the **normal** path before overflow is evaluated.

The zombie mechanism (Fix 3, same 2026-06-19 release) covers every scenario overflow v1
could have handled. Its unreachability has been invisible because nothing ever depended on it.

### 1.2 The uncovered production scenario

The scenario overflow was designed for remains unhandled:

```
Tier cap 3. Held: A, B, C — all at L4 (max), all still top-3 ranked.
User deposits weekly capital (core DCA product behavior).

Deposit flow:  _detect_capital_change() → router.resize() → cash lands in active_pool_cash
Next rebalance: allocations = {A, B, C} (same incumbents, cap-sliced)
                _top_up_engine_capital() skips all three (layer_count >= max_layers)
                4th-ranked coin D never appears as a candidate

Result: deposit idles in active_pool_cash until a TP frees a slot.
```

This violates the system's own design principle (layer-reconstruction spec §2):

> **Capital should always seek the best available opportunity. Idle capital is a system failure.**
> **The tier cap limits diversification, not capital deployment.**

---

## 2. Design Principles

> **The tier ladder governs diversification by capital scale. Overflow governs deployment
> timing within those bounds.** Two jobs, two mechanisms — neither substitutes for the other.

> **Idle cash is ammunition until the grids are full.** Active-pool cash defends open
> positions through L2–L4. It becomes dead capital only when every grid has exhausted its
> tiers — and that is the only moment overflow may deploy it.

> **Overflow grows the book; TP rotation shrinks it.** No forced closes, ever (Hard Rule #34).
> The book contracts naturally as positions take profit and slots rotate.

> **Fail-closed on missing data.** Normal rotation fails open (keep incumbent — safe default).
> Overflow *adds* exposure, so absent or stale scanner data means **no admission**.

---

## 3. Specification

### 3.1 Trigger point

Evaluated **once per daily rebalance**, inside `_do_rebalance()`, **after**
`_top_up_engine_capital()`. Maximum **one admission per rebalance day**.

Rationale for ordering: top-up has first claim on idle cash (defending existing grids
outranks opening new ones — Hard Rule #36). Whatever cash remains after top-up is
genuinely idle. Note that in the canonical overflow scenario (all grids maxed) top-up
grants nothing, so in practice the full deposit is available.

Rationale for once-daily: weekly/monthly deposit cadence tolerates a ≤24h wait; one
admission per day preserves the one-change-per-cycle operational discipline and lets the
24h post-change audit (Hard Rule #6) observe each admission in isolation.

### 3.2 Admission conditions (ALL must pass)

| # | Condition | Detail |
|---|-----------|--------|
| 1 | Feature flag | `OVERFLOW_ENTRY_ENABLED = True` |
| 2 | Bot state | `bot_state == RUNNING` (no admissions in PAUSED / WIND_DOWN) |
| 3 | All grids exhausted | Every **non-zombie** open position has `layer_count >= max_layers` (and at least one such position exists) |
| 4 | Soft ceiling | `total_open_positions < next_tier_coin_cap(equity)` — see §3.3 |
| 5 | Idle cash | `active_pool_cash × 0.9 >= fair_slot_alloc × L1_COST_FRACTION` — see §3.4 |
| 6 | Candidate exists | Best coin in **full** scanner rankings (`_get_scanner_rankings()`, hurdle-filtered, trend-adjusted, sorted desc) that is not already held, not regime-flagged, and passes the liquidity filter |
| 7 | Scanner freshness | `cycle_scanner.json` mtime < 24h — **fail-closed** if stale or missing |
| 8 | Defers to normal entries | **No new engine was created by the normal entry path in this same rebalance** (e.g., a zombie-freed slot admitting an approved coin). The normal-path coin deploys first; overflow re-evaluates at the next rebalance if the book is still all-maxed with idle cash. Priority order per rebalance: top-up → normal entries → overflow, at most one admission mechanism per day. |

Condition 6 is the structural fix: candidates come from the full ranking list (the
proven `_rotate_after_tp()` pattern), never from the cap-sliced allocations dict.

### 3.3 Soft ceiling — bounded by the next tier

```
next_tier_coin_cap(equity):
    return the coin cap of the tier ONE STEP ABOVE the current equity tier
    (e.g., current tier $100–$3K → 3 coins; next tier → 4)
    If already at the top tier, ceiling = current cap (no overflow at 10 coins).
```

The book may grow via overflow to at most the cap the ladder would grant at the next
equity level. This makes the mechanism **self-reconciling**: as deposits push equity into
the next tier, the ladder catches up and overflow coins simply become regular slots.
There is no scenario where a long drawdown plus persistent deposits fragments the book
beyond what the ladder itself would eventually permit.

**The ceiling counts TOTAL open positions — zombies included.** This is a deliberate
divergence from the zombie rule (§7.7), stated explicitly:

- Zombie exclusion exists to let an approved coin replace a decayed one **1:1 within the
  tier cap** (slot replacement).
- The soft ceiling exists to bound **total grid fragmentation**. A zombie's capital is
  still locked in a live grid; it still fragments the bankroll. Excluding zombies from
  the ceiling would let the book chain upward (overflow coin decays → zombifies → frees
  a ceiling slot → another overflow) without bound.

Worked example (tier cap 3, next tier 4):

```
A, B, C held at L4, all approved. Deposit arrives.
→ Overflow admits D (total positions 3 → 4 = ceiling reached).
D fills to L4. Another deposit arrives.
→ Condition 4 fails (4 positions = ceiling). Cash waits for a TP or a tier upgrade.
C later decays out of top-N → zombie. Normal entry path: active_count = 3 (A,B,D) = cap → no entry.
→ Overflow: total positions still 4 = ceiling → still blocked. Book bounded. ✅
A takes profit → slot rotation (_rotate_after_tp) redeploys normally. Book returns toward cap. ✅
```

### 3.4 Allocation sizing

```
fair_slot_alloc  = active_pool_total / tier_coin_cap          # a normal slot's share
overflow_alloc   = min(active_pool_cash × 0.9, fair_slot_alloc)
```

The deposit itself becomes the new coin's grid (matching the product intent: "your
deposit goes to work on the highest-scored available coin"), capped so an overflow slot
is never larger than a regular slot. The 10% cash buffer mirrors
`_top_up_engine_capital()`.

`L1_COST_FRACTION` in condition 5 is **imported from `GridModel`** (audit recommendation F1).

**RESOLVED (v1.1, D-GRID d):** the canonical grid is the bull-phase grid — layer fractions
40/24/20/16% of allocated capital — so `L1_COST_FRACTION = 0.40`. The value must still be
**imported from `GridModel`, never hardcoded** in the overflow code: a hardcoded constant
repeats the C1 drift class this spec's predecessor already suffered from (v1's
`min_l1_capital = alloc * 0.4`), and future grid-profile-per-regime work (handoff Task 4.5)
will make the fraction profile-dependent.

### 3.5 Admission procedure

Identical to the proven engine-creation pattern in `_rotate_after_tp()` / `_do_rebalance()`:

```python
# After _top_up_engine_capital() in _do_rebalance():
if self._overflow_conditions_met():                      # §3.2 conditions 1–5, 7
    candidate = self._find_overflow_candidate()          # §3.2 condition 6
    if candidate:
        alloc = min(self.router.active_pool_cash * 0.9,
                    self.router.active_pool_total / max(self.router.tier_coin_cap, 1))
        cs = CoinState(candidate, alloc)
        cs.engine = V14LifecycleEngine(symbol=candidate, capital=alloc,
                                       profile=self.profile, leverage=self.leverage)
        cs.engine._live_mode = True
        if cs.engine._engine:
            cs.engine._engine.live_mode = True
        cs.engine._warmed_up = True
        cs.engine._last_candle_ts = int(time.time() * 1000)   # candle replay guard (§7.8)
        self.coins[candidate] = cs
        self.router.active_allocations[candidate] = 0.0        # seed T1 gate
        self.client.ensure_leverage(candidate, self.leverage)
        # Telegram + log (§5)
```

Entry then proceeds through the normal path: engine emits BUY on the next current
candle → T1 gate passes (seeded allocation) → `request_capital()` draws from
`active_pool_cash` → regime gate / pause / dedup / balance pre-checks all apply unchanged.

The old overflow block inside the allocations loop is **deleted** (it is dead code).

### 3.6 Candidate selection detail

```python
def _find_overflow_candidate(self) -> Optional[str]:
    rankings = self._get_scanner_rankings()      # full list, hurdle-filtered, trend-adjusted
    if not rankings:
        return None                              # fail-closed (§2)
    held = set(self.coins.keys())                # engines with OR without positions
    flagged_bases = {s.split("/")[0] for s, c in self.coins.items() if c.regime_flagged}
    for sym, score in rankings:
        if sym in held: continue
        if sym.split("/")[0] in flagged_bases: continue
        if not self._passes_liquidity_filter(sym, alloc):   # requires audit fix H1 first
            continue
        return sym
    return None
```

Excluding all engines in `self.coins` (not just position-holders) prevents admitting a
coin that already has an idle engine awaiting entry.

---

## 4. Interactions with Existing Systems

| System | Interaction |
|--------|-------------|
| **Zombie slots (§7.7)** | Unchanged for normal entries. Overflow's soft ceiling counts zombies (§3.3, deliberate divergence documented there). |
| **Capital top-up (§7.6, Rule #36)** | Top-up runs first and has first claim on cash. Overflow deploys only the remainder. |
| **TP rotation (`_rotate_after_tp`)** | Unchanged — it is the book's shrink mechanism. When positions above the tier cap exist, rotation's own cap logic (1:1 swap) naturally declines to backfill closed overflow slots once the book is back at cap. |
| **Stale allocation cleanup (§7.3 step 9)** | Unchanged. An overflow coin that TPs and is not in rebalance targets gets its allocation pruned normally. |
| **Regime gate (§7.5.2)** | Fully applies. Overflow engines start LONG_DCA; if global regime is SHORT_DCA the entry is blocked and rolled back like any other. Regime-flagged bases are excluded at candidate selection. |
| **Deposit detection (§7.4)** | No change. Overflow reads `active_pool_cash`, which `resize()` already populates on deposit. |
| **Candle replay guard (§7.8)** | Applied — `_last_candle_ts = now` on creation. |
| **Hard Rule #34** | No forced closes anywhere in this spec. Book contraction is TP-only. |
| **Tier downgrade (equity drop + hysteresis)** | If equity falls, `total_positions` may exceed the (new, lower) next-tier ceiling → condition 4 blocks all admissions until TPs shrink the book. No positions touched. |

---

## 5. Observability

**Telegram on admission:**
```
📈 [V14PM-LIVE] Overflow Entry
All N grids at max depth — deploying idle capital
In: TAO/USDT (score 11.3, rank #3)
Allocation: $XX.XX | Book: 4/3 (soft ceiling 4)
```

**status.json additions** (computed dynamically, like zombies — no new persisted state):
- Top-level: `overflow_active: true|false`, `soft_ceiling: N`, `book_size: N`
- The condition "all grids maxed + idle cash > threshold + **no admission possible**"
  (ceiling hit or no candidate) emits a daily ⚠️ Telegram notice — idle capital must
  never be silent (audit P7 / Rule #14 in spirit).

---

## 6. Dependencies & Sequencing

| # | Dependency | Why |
|---|-----------|-----|
| 1 | Audit P0 fix H1 (liquidity filter attribute errors) | Condition 6 gates on the liquidity filter; today it throws and is swallowed. Overflow must not ship gated by a dead check. |
| 2 | GridModel (handoff Task 1.1) | `L1_COST_FRACTION` (= 0.40 per D-GRID d) imported from GridModel, never hardcoded (§3.4). |
| 3 | Audit P0 fix C2 (`_prune_stale_coin_after_tp`) | Shares the sell/rotation path this feature exercises more often. |

Sequencing: P0 fixes → 24h audit → C1 decision → this spec's implementation → paper → live.

---

## 7. Test Plan

1. **Unit — gate logic:** port the audit's enumeration harness (7,680-scenario sweep) to
   the v2 gate; assert admissions fire in Scenario 1 (all maxed + all approved + deposit)
   and are correctly blocked at the soft ceiling, on stale scanner, in PAUSED/WIND_DOWN,
   with a mid-grid position present, and with regime-flagged candidates.
2. **Paper first:** deploy to the V14PM paper bot. Simulate the trigger by (a) letting
   positions max naturally or (b) temporarily lowering `max_layers` in a paper-only run,
   then injecting a paper deposit. Verify: one admission per day, correct allocation
   sizing, T1 entry succeeds, status.json fields, Telegram messages.
3. **Live rollout:** pre-flight import test (Rule #19), one-change restart (Rule #20),
   24h post-launch trade audit (Rule #6). First live admission reviewed manually against
   the scanner ranking of that day.
4. **Regression:** confirm zombie replacement (Scenario 2 class) still enters via the
   normal path and never double-admits through overflow.

---

## 8. Out of Scope

- Multiple admissions per day (revisit only if deposit cadence becomes daily).
- Deposit-triggered immediate evaluation (revisit if the ≤24h wait proves material).
- Refining the tier ladder bands — explicitly rejected in favor of this mechanism:
  a finer ladder adds slots on an equity schedule regardless of grid state, fragmenting
  grids before they need help. Deployment timing is state-dependent; the ladder cannot
  express it.

---

## 9. Summary of Changes vs. v1

| Aspect | v1 (2026-06-19, unreachable) | v2 (this spec) |
|--------|------------------------------|----------------|
| Candidate source | Cap-sliced `allocations` dict | Full `_get_scanner_rankings()` list |
| Evaluation point | Inside allocations loop, before top-up | After `_top_up_engine_capital()` |
| Ceiling | Hard +1 (`active_count == tier_cap`), one-shot forever | Soft ceiling = next tier's cap, counted over total positions, repeatable one/day |
| Cash check | `alloc × 0.4` (documented grid, wrong) | `fair_slot_alloc × L1_COST_FRACTION` from canonical grid |
| Missing scanner | n/a (never reached) | Fail-closed |
| Liquidity filter | Not applied | Required (post-H1 fix) |
| Shrink path | Undefined | TP rotation + stale cleanup (existing, unchanged, Rule #34) |
