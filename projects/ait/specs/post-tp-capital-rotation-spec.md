# Post-TP Capital Rotation — Specification

**Date**: 2026-05-29 (updated 2026-05-30)
**Status**: Deployed (Live + Paper)
**Author**: Brett + Gee Gee
**Severity**: Production change (V14PM Live on Aster — real money)
**Affects**: `run_v14_portfolio_live_aster.py`, `run_v14_portfolio_paper.py`

---

## 1. Problem Statement

When a position closes via TP, the bot currently checks whether the coin is still in the scanner top-N. If yes, the engine stays alive and immediately re-enters on the next qualifying candle. This is wrong.

**Example (2026-05-29):** INJ/USDT hit TP and re-entered L1 within minutes. Scanner rankings at the time:
1. NEAR — Trade Score 50.2
2. HYPE — Trade Score 43.4
3. INJ — Trade Score 42.2

INJ re-entered because it was still in the top-3 (`tier_coin_cap = 3`). NEAR had no active slot and a higher score. The freed capital should have gone to NEAR.

**Root cause**: `_prune_stale_coin_after_tp()` only removes coins that fell **out of** the top-N. It never considers whether a higher-ranked unallocated coin should take the slot instead. The incumbent coin has an unfair advantage — it keeps its slot simply by being "good enough" rather than being the **best available**.

---

## 2. Design Principle

> Capital at allocation time goes to the highest-ranked available opportunity. No incumbent advantage.

This aligns with the existing design doc (§4.4 of `portfolio-capital-management.md`):
> *"When a cycle completes (TP hit), freed capital goes back to the pool. Re-allocation happens based on current scores + trend at that moment."*

The spec was correct; the implementation drifted.

---

## 3. Scope Assessment

### 3.1 Is this surgical or systemic?

**Surgical.** The change is confined to the post-TP decision point. Here's why:

| System Component | Affected? | Reason |
|---|---|---|
| `CapitalRouter.rebalance_daily()` | ❌ No | Daily rebalance already ranks correctly. No changes needed. |
| `CapitalRouter.request_capital()` | ❌ No | Capital granting logic unchanged. |
| `CapitalRouter.return_capital()` | ❌ No | Capital return logic unchanged. |
| `_execute_action()` T1 gate | ❌ No | T1 gate checks `active_allocations` — already correct. The change is in *what gets seeded* into `active_allocations` after TP. |
| `_do_rebalance()` | ❌ No | Daily rebalance already handles engine creation and allocation seeding. |
| `_prune_stale_coin_after_tp()` | ✅ **Replace** | Current logic is the wrong question ("still in top-N?"). Replace with rotation logic ("is there a better unallocated coin?"). |
| `_get_scanner_top_n_symbols()` | ✅ **Extend** | Needs to return ranked list (not just a set) so we can compare scores. |
| Engine creation (new coin) | ✅ **New path** | After TP, if rotation selects a different coin, create its engine inline (same pattern as `_do_rebalance`). |
| Engine cleanup (evicted coin) | ✅ **New path** | Remove evicted coin's engine and allocation when it has no open position. |
| `status.json` / `approved_symbols` | ❌ No | Already derived from `router.active_allocations.keys()`. Rotation naturally updates this. |
| Dashboard | ❌ No | Reads `status.json`. No change needed. |
| Telegram alerts | ✅ **New message** | Alert on coin rotation: "Rotated INJ → NEAR (score 42.2 → 50.2)". |
| Equity / PnL calculation | ❌ No | Ground-truth formula unchanged. |
| Deposit detection | ❌ No | Independent system. |
| Regime system | ❌ No | Regime gate is checked at action execution time, not allocation time. New coin enters regime check naturally. |
| State persistence | ✅ **Minor** | New engine must be included in `engine_state.json` save. Already handled — `_save_state()` iterates `self.coins`. |
| Trailing TP / order management | ❌ No | New coin's TP orders managed by existing infrastructure. |

### 3.2 Upstream dependencies (inputs to the change)

| Input | Source | Change needed? |
|---|---|---|
| Scanner rankings | `cycle_scanner.json` | ❌ No — already produces ranked scores |
| Trend multipliers | `cycle_scanner.json` → `trend_scores` | ❌ No — already included |
| Tier coin cap | `CapitalRouter.tier_coin_cap` | ❌ No |
| Current allocations | `router.active_allocations` | ❌ No — read-only for decision |
| Open positions | `self.coins[sym].engine._engine.long_coins` | ❌ No — read-only for decision |

### 3.3 Downstream effects (outputs of the change)

| Output | Consumer | Risk |
|---|---|---|
| `router.active_allocations` | T1 gate, `approved_symbols`, daily rebalance | **Low** — rotation updates allocations the same way `_do_rebalance` does. T1 gate will correctly allow the new coin and block the old one. |
| `self.coins` dict | Main loop, candle processing, status writer | **Low** — adding/removing entries is the same pattern as `_do_rebalance`. |
| `engine_state.json` | Restart recovery | **Low** — new engine auto-included in next `_save_state()` call. |
| Telegram alerts | Operator | **Informational** — new rotation alert. |
| Exchange leverage | Aster API | **Low** — `ensure_leverage()` called for new coin, same as rebalance. |

### 3.4 Invariants that must hold

1. **Never remove a coin with an open position.** Rotation only applies to coins with zero position size after TP close.
2. **Never exceed tier_coin_cap.** Rotation is 1:1 swap (or just eviction if no qualifying replacement).
3. **Existing positions on other coins are untouched.** Only the coin that just TP'd is evaluated for rotation.
4. **DCA layers on surviving positions always allowed.** T1 gate distinction (L1 blocked, L2+ always passes) is unchanged.
5. **Fail-open on scanner error.** If scanner JSON is stale/missing/corrupt, skip rotation (keep incumbent). Same as current prune behavior.
6. **Daily rebalance is still authoritative.** Post-TP rotation is a fast-path optimization. Daily rebalance can override it.
7. **Warmup required for new engines.** New engines from rotation must be warmed up (set `_warmed_up = True` for live, same as rebalance path).

---

## 4. Implementation Plan

### 4.1 Replace `_prune_stale_coin_after_tp()` with `_rotate_after_tp()`

**Current flow (wrong):**
```
TP fill → return_capital → _prune_stale_coin_after_tp()
  └─ Is coin still in top-N?
       Yes → keep, allow re-entry
       No  → remove allocation, block re-entry
```

**New flow (correct):**
```
TP fill → return_capital → _rotate_after_tp(sym)
  └─ 1. Get scanner ranked list (adjusted scores, sorted descending)
     2. Get set of coins with active positions (excluding `sym` which just closed)
     3. Find highest-ranked coin NOT in active positions
     4. Compare:
        a. If best_available == sym → keep (incumbent IS the best choice)
        b. If best_available != sym → rotate:
           i.   Remove sym from active_allocations
           ii.  Remove sym engine (if no open position — should be true post-TP)
           iii. Create engine for best_available with allocation
           iv.  Seed best_available into active_allocations
           v.   Set leverage on exchange for new coin
           vi.  Send Telegram rotation alert
        c. If no qualifying coin available → just remove sym allocation (shrink)
        d. If scanner unavailable → fail-open, keep sym (no rotation)
```

### 4.2 Extend `_get_scanner_top_n_symbols()` → `_get_scanner_rankings()`

Return a ranked list of `(symbol, adjusted_score)` tuples instead of a `set`. The caller needs scores for comparison, not just membership.

```python
def _get_scanner_rankings(self) -> List[Tuple[str, float]]:
    """Return scanner rankings as (symbol, adjusted_score) sorted descending.
    
    Applies hurdle rate and trend multiplier, same logic as
    CapitalRouter.rebalance_daily(). Returns empty list on error (fail-open).
    """
```

### 4.3 `_rotate_after_tp()` method

```python
def _rotate_after_tp(self, sym: str, cs: CoinState):
    """After TP close, evaluate whether this coin's slot should rotate
    to a higher-ranked unallocated coin.
    
    Rules:
    - Freed slot goes to the highest-ranked coin without an active position
    - If incumbent IS the highest-ranked, it keeps the slot (no rotation)
    - Fail-open: if scanner is unavailable, keep incumbent
    - Liquidity filter: new coin must pass MIN_VOLUME check
    - Bot state check: no new engines in PAUSED or WIND_DOWN
    """
```

### 4.4 Engine lifecycle for rotation

Reuse the exact same engine creation pattern from `_do_rebalance()`:
```python
cs = CoinState(sym, alloc)
cs.engine = V14LifecycleEngine(
    symbol=sym, capital=alloc, profile=self.profile, leverage=self.leverage,
)
cs.engine._live_mode = True
if cs.engine._engine:
    cs.engine._engine.live_mode = True
cs.engine._warmed_up = True
self.coins[sym] = cs
self.client.ensure_leverage(sym, self.leverage)
```

### 4.5 Paper runner parity

Apply the same rotation logic to `run_v14_portfolio_paper.py`. The paper runner currently has no post-TP scanner check at all — it just lets engines re-enter freely. Add `_rotate_after_tp()` to the paper runner's SELL action handler.

---

## 5. Risk Assessment

| Risk | Likelihood | Severity | Mitigation |
|---|---|---|---|
| Bug in rotation creates phantom engine | Low | Medium | Engine creation uses proven `_do_rebalance` pattern. State persistence auto-includes new engines. |
| Rotation during exchange downtime | Low | Low | Exchange operations (leverage setting) wrapped in try/except. Engine creates regardless — first trade will set leverage. |
| Scanner stale → wrong rotation | Low | Medium | Fail-open: skip rotation if scanner is stale (>24h, already alerting via Finding #21). |
| Rapid rotation churn (coin rotates in, takes L1, TPs, rotates out, repeat) | Medium | Low | This is actually the desired behavior — capital follows the fastest-cycling coin. Not a bug. |
| New coin enters but has bad candle data | Low | Medium | Warmup guard ensures engine doesn't trade on first tick without signals. Live mode sets `_warmed_up = True` (same as rebalance). |
| Concurrent TP + rebalance race | Very Low | Low | Rebalance is date-gated (once per day). TP rotation and rebalance both write to same structures. The last writer wins, which is correct — rebalance is the authoritative source. |
| Breaking change in CoinState lifecycle | Low | High | Unit test: verify CoinState removal doesn't leave dangling references in tracker, router, or main loop. |

---

## 6. Testing Plan

### 6.1 Pre-deployment (paper bot)

1. Deploy to `run_v14_portfolio_paper.py` first
2. Verify via logs: after a TP, rotation logic runs and correctly identifies the best available coin
3. Verify: if incumbent IS the best, no rotation occurs
4. Verify: new engine processes candles and enters trades
5. Verify: evicted coin's engine is removed from `self.coins` and `active_allocations`
6. Verify: `engine_state.json` round-trips correctly after rotation (restart test)
7. Run for 48-72h on paper before promoting to live

### 6.2 Post-deployment (live bot) monitoring

1. Watch first rotation event via Telegram alert
2. Verify exchange has leverage set for new coin
3. Verify new coin's first L1 entry executes on exchange
4. Verify status.json `approved_symbols` reflects the swap
5. Verify dashboard shows new coin correctly

---

## 7. Files Changed

| File | Change Type | Lines (est.) |
|---|---|---|
| `trading/spot/run_v14_portfolio_live_aster.py` | Modify | ~80 (replace `_prune_stale_coin_after_tp` + `_get_scanner_top_n_symbols`, add `_rotate_after_tp` + `_get_scanner_rankings`) |
| `trading/spot/run_v14_portfolio_paper.py` | Add | ~60 (add `_rotate_after_tp` + `_get_scanner_rankings` to paper runner) |

No changes to: `v14_capital_manager.py`, `v14_cycle_scanner.py`, `v14_lifecycle_engine.py`, `v14_dca_engine.py`, dashboards, or scheduled tasks.

---

## 8. Hard Rules Compliance

| Rule | Status |
|---|---|
| #26: seed_capital immutable | ✅ Not touched |
| #27: No derived constants from seed | ✅ Not touched |
| #30: No unrealized in detection | ✅ Not touched |
| #31: Idempotent restart | ✅ New engine persisted via existing `_save_state()` |
| #32: Post-tick gates rollback | ✅ Not touched — rotation is post-TP, not mid-tick |
| #34: No forced closes on 1.0x | ✅ Rotation only acts on positions that already closed via TP |
| #35: Revalidate params on universe change | ✅ New coin gets fresh engine with current profile params |
| #36: Regime gates action-type-aware | ✅ New coin enters existing regime gate in `_execute_action` |

---

## 9. Bug Fix: Zero-Allocation Inheritance (2026-05-30)

**Incident:** First rotation in production — INJ/USDT (score 0.0) TP'd and rotated to HYPE/USDC (score 57.4). Telegram alert showed "Capital: $0.00". HYPE engine ticked every hour with `no action (warmed_up=True)` because the DCA engine had $0 capital to size orders.

**Root cause:** `_rotate_after_tp()` transferred the incumbent's allocation to the new coin:
```python
alloc = self.router.active_allocations.pop(sym, cs.allocated_capital)
```
INJ had score 0.0 → daily rebalance gave it $0 allocation → HYPE inherited $0.

**Fix:** After popping the incumbent's allocation, check if it's `<= 0`. If so, derive a fair share from `active_pool_total / tier_coin_cap`. The daily rebalance will fine-tune with score-weighted proportions later.

```python
if alloc <= 0:
    alloc = self.router.active_pool_total / max(self.router.tier_coin_cap, 1)
```

**Paper parity note:** The paper runner already had this fallback (added during initial implementation). The live runner was missing it — parity restored.

**Liquidity filter also fixed:** The volume reference for the liquidity check used the incumbent's allocation. With $0 this fell back to `MIN_VOLUME_FLOOR` ($50K) correctly, but now explicitly derives the fair share for accurate volume checks.

**Commit:** `77989855a` (2026-05-30)

---

## 10. Decision Record

| Question | Answer | Rationale |
|---|---|---|
| Should rotation be immediate or wait for next candle? | Immediate (engine creation), trade on next candle | Engine needs to exist to process the next candle. First trade happens naturally on next tick — no artificial delay needed. |
| Should we evict the coin's engine entirely? | Yes, if it has zero position | Dead engines consume candle processing cycles and status.json space. Clean removal is correct. |
| What if the best coin fails liquidity filter? | Try next-best, then next-best, etc. | Same waterfall as `_do_rebalance` liquidity filter. |
| Does this change the daily rebalance? | No | Daily rebalance is independent and authoritative. It may re-seat a coin that rotation evicted, or evict one rotation kept — both are correct. |
| Paper runner parity required? | Yes | Paper is the proving ground. Same logic, same behavior. Deploy there first. |
