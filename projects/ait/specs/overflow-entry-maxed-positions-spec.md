# Overflow Entry — Deploy Idle Capital When Positions Are At Max Layers

**Date**: 2026-05-30
**Status**: Draft — Pending Approval
**Author**: Brett + Gee Gee
**Severity**: Production change (V14PM Live on Aster — real money)
**Affects**: `run_v14_portfolio_live_aster.py`, `run_v14_portfolio_paper.py`

---

## 1. Problem Statement

When all coin positions are at max DCA layers (L4 for high profile), idle capital in the active pool has nowhere to go. The tier coin cap blocks new engine creation regardless of capital availability.

**Example (current live state, 2026-05-30):**
- Equity: ~$431, tier_coin_cap: 3
- TON L1 ($111 invested), JUP L1 ($108), PENDLE L1 ($87) = $306 deployed
- Active pool cash: ~$125 idle (29% of total equity)
- Scanner top scorers: NEAR (49.9), INJ (43.1), EIGEN (20.0)
- Rebalance: "Skipping new coin NEAR — at tier cap (3/3 active positions)"
- Result: $125 sits idle indefinitely until a TP frees a slot

This gets worse as positions go deeper. If all 3 positions reach L4:
- Each L4 position consumes ~$165 (high profile: 40% BO, 1.5x mult, 1.5% dev, 4 layers)
- All capital is deployed in existing positions — but only within 3 coins
- If a user deposits additional capital, it also idles — no mechanism to deploy it

**Root cause:** The rebalance gate at line ~2606 treats the tier coin cap as a hard position limit:
```python
if tier_cap > 0 and active_count >= tier_cap:
    logger.info(f"Skipping new coin {sym} — at tier cap")
    continue
```
It doesn't distinguish between "positions that can absorb more capital via DCA layers" and "positions that are fully maxed out."

---

## 2. Design Principle

> The tier coin cap limits diversification — not capital deployment. When all existing positions are at max layers and idle capital exists, allow one overflow entry to put that capital to work.

This aligns with §4.4 of `portfolio-capital-management.md`:
> *"When a cycle completes (TP hit), freed capital goes back to the pool. Re-allocation happens based on current scores + trend at that moment."*

The spirit of the system is: capital should always be seeking the best available opportunity. The tier cap prevents spreading too thin, but when existing positions literally cannot absorb more capital, the cap becomes a capital trap.

---

## 3. Proposed Rule

Allow **one** additional coin beyond the tier cap when **all** of these conditions are met:

1. **All existing positions with open trades are at max layers** (`layer_count >= DCA_MAX_LAYERS` for current profile)
2. **Adequate idle capital exists** — `active_pool_cash >= min_viable_l1` (enough for at least one L1 base order for the candidate coin)
3. **The candidate coin passes all existing gates** — hurdle rate, regime gate, liquidity filter, not paused/flagged
4. **Only +1 overflow** — never exceed `tier_coin_cap + 1` simultaneous positions. If overflow is already active, no further expansion.
5. **Bot state is RUNNING** — no overflow in PAUSED or WIND_DOWN

---

## 4. Scope Assessment

### 4.1 Is this surgical or systemic?

**Surgical with one caveat.** The primary change is a single gate condition in the rebalance. But the downstream interaction with rebalance cleanup requires careful handling.

| System Component | Affected? | Reason |
|---|---|---|
| `_do_rebalance()` — engine creation gate | ✅ **Modify** | Add overflow exception to the tier cap check |
| `_do_rebalance()` — allocation cleanup | ✅ **Modify** | Must not clean up an overflow engine that has an open position |
| `_do_rebalance()` — allocation seeding | ❌ No | Overflow coin gets seeded the same way as any new target |
| `CapitalRouter.rebalance_daily()` | ❌ No | Router allocates to top-N by score. Overflow coin may or may not be in the router's target list. If not, its allocation comes from idle active cash directly. |
| `CapitalRouter.tier_coin_cap` | ❌ No | Cap value unchanged. Overflow is an exception in the runner, not the router. |
| `_execute_action()` — T1 gate | ❌ No | T1 gate checks `active_allocations`. If overflow coin is seeded there, T1 passes. Already works correctly. |
| `_execute_action()` — Regime gate | ❌ No | Overflow coin enters the same regime check as any other coin. If its engine phase conflicts with global regime, entry is blocked. |
| `_rotate_after_tp()` — post-TP rotation | ⚠️ **Verify** | When the overflow coin TPs, rotation should evaluate normally. The tier cap check in rotation is already a pass-through for 1:1 swaps. No change needed. |
| `_rotate_after_tp()` — when a CAPPED coin TPs | ⚠️ **Verify** | When one of the original capped positions TPs (freeing a slot), the overflow coin should naturally become a "regular" position (now within cap). No explicit action needed — the next rebalance will include it in normal allocations. |
| Deposit detection | ❌ No | Independent system. Overflow doesn't affect balance tracking. |
| Status writer / `status.json` | ❌ No | Overflow coin is a regular CoinState — automatically included in status. |
| Dashboard | ❌ No | Reads status.json. No change needed. |
| State persistence | ❌ No | Overflow engine persisted via `_save_state()` like any other engine. |
| Trailing TP / order management | ❌ No | Same infrastructure as any other coin. |

### 4.2 The Rebalance Cleanup Risk (Critical)

This is the **one interaction that needs careful handling.** The daily rebalance cleans up stale allocations:

```python
# Current code (line ~2655):
for sym_r in list(self.router.active_allocations.keys()):
    if sym_r in new_target_syms:
        continue
    if not has_position:
        stale_syms.append(sym_r)
        del self.router.active_allocations[sym_r]
```

**Scenario:** Overflow coin enters L1 on Day 1. On Day 2, rebalance runs. The overflow coin might NOT be in the router's top-N targets (because the router only selects `tier_coin_cap` coins). The cleanup would then see the overflow coin as "not in new targets" — but it HAS an open position, so the `has_position` check protects it. The cleanup only removes coins with NO open position.

**Verdict:** ✅ Safe. The existing `has_position` guard already protects coins with open positions from cleanup. The overflow coin will survive rebalance as long as it has a position. When it TPs and has no position, it will be cleaned up — which is correct behavior (it's no longer needed).

**But there's a subtlety:** If the overflow coin's engine was created but it hasn't entered L1 yet (engine exists, no position), the next rebalance would clean it up. This is actually fine — if the engine didn't trigger an entry before the next rebalance, the system gets a fresh evaluation.

### 4.3 Upstream Dependencies

| Input | Source | Change needed? |
|---|---|---|
| `layer_count` per coin | CoinState (synced from exchange) | ❌ No — already tracked |
| `DCA_MAX_LAYERS` | Profile config in `v14_lifecycle_engine.py` | ❌ No — read-only |
| `active_pool_cash` | CapitalRouter | ❌ No — already available |
| Scanner rankings | `cycle_scanner.json` | ❌ No |
| Tier coin cap | CapitalRouter | ❌ No — cap value unchanged |

### 4.4 Downstream Effects

| Output | Consumer | Risk |
|---|---|---|
| New engine in `self.coins` | Main loop, candle processing | **Low** — same as any engine. One more coin to tick per cycle. |
| New entry in `active_allocations` | T1 gate, cleanup | **Low** — `has_position` guard protects it. |
| Active position count > tier_cap | Rebalance gate (next day) | **Medium** — need to ensure the rebalance gate counts the overflow coin as existing (doesn't try to skip it AND create another overflow). See §5 Invariant #3. |
| Status.json `approved_symbols` | Dashboard | **Low** — overflow coin naturally appears. |

---

## 5. Invariants That Must Hold

1. **Never exceed `tier_coin_cap + 1` positions.** One overflow max. If overflow is active and all positions are still maxed, don't create another.
2. **DCA layers on ALL positions are always allowed.** Overflow changes nothing about L2+ layer capital. Existing positions are never starved.
3. **Rebalance must not fight the overflow.** If an overflow position exists, the next rebalance should not try to add ANOTHER overflow. The rebalance should treat the overflow as an existing position and count it toward the cap.
4. **Overflow coin must pass ALL existing gates.** Regime, liquidity, hurdle rate. No exceptions.
5. **Fail-open on error.** If the "all positions maxed" check fails or produces unexpected results, default to the current behavior (no overflow).
6. **Config toggleable.** `OVERFLOW_ENTRY_ENABLED = True` flag. Can be set to False to revert to current behavior without code changes.
7. **When a capped position TPs and frees a slot:** The overflow coin is now within cap. No special handling needed — the natural count goes from `cap+1` to `cap`.

---

## 6. Implementation Plan

### 6.1 Add Config Flag

```python
# Near other config constants (line ~130)
OVERFLOW_ENTRY_ENABLED = True   # Allow +1 coin when all positions at max layers
```

### 6.2 Modify Rebalance Gate (~line 2606)

**Current:**
```python
if tier_cap > 0 and active_count >= tier_cap:
    logger.info(f"Skipping new coin {sym} — at tier cap ({active_count}/{tier_cap})")
    continue
```

**Proposed:**
```python
if tier_cap > 0 and active_count >= tier_cap:
    # Check overflow exception: all positions at max layers + idle capital
    allow_overflow = False
    if OVERFLOW_ENTRY_ENABLED and active_count == tier_cap:  # exactly at cap, not already overflowed
        max_layers = self._get_max_layers()
        positions_with_trades = [
            cs_ for cs_ in self.coins.values()
            if cs_.engine and cs_.engine._engine
            and (cs_.engine._engine.long_coins > 0 or cs_.engine._engine.short_coins > 0)
        ]
        all_maxed = (
            len(positions_with_trades) > 0
            and all(cs_.layer_count >= max_layers for cs_ in positions_with_trades)
        )
        # Check if there's enough capital for at least an L1 base order
        # Base order = allocation * BO_PCT (40% for all profiles)
        min_l1_capital = alloc * 0.4 if alloc > 0 else 10.0
        has_capital = self.router.active_pool_cash >= min_l1_capital
        
        if all_maxed and has_capital:
            allow_overflow = True
            logger.info(
                f"OVERFLOW: all {len(positions_with_trades)} positions at L{max_layers} "
                f"(max layers), idle cash ${self.router.active_pool_cash:.2f} — "
                f"allowing {sym} as +1 overflow"
            )
    
    if not allow_overflow:
        logger.info(
            f"Skipping new coin {sym} — at tier cap "
            f"({active_count}/{tier_cap} active positions)"
        )
        continue
```

**Key detail:** `active_count == tier_cap` (not `>=`) ensures we only overflow ONCE. If overflow is already active, `active_count` will be `tier_cap + 1`, which fails the `==` check and falls through to the skip.

### 6.3 Add `_get_max_layers()` Helper

```python
def _get_max_layers(self) -> int:
    """Return DCA_MAX_LAYERS for the current profile."""
    from trading.spot.v14_lifecycle_engine import PROFILES
    profile_config = PROFILES.get(self.profile, PROFILES['high'])
    return profile_config.get('DCA_MAX_LAYERS', 4)
```

### 6.4 No Changes Needed to Rebalance Cleanup

The existing `has_position` guard protects the overflow coin:
```python
# Already in the code:
if not has_position:
    stale_syms.append(sym_r)  # Only removes coins with NO position
```

### 6.5 No Changes Needed to Rotation

Rotation counts `coins_with_positions` (excluding the coin that just closed). If the overflow coin TPs:
- `coins_with_positions` drops by 1
- `active_count` drops to `tier_cap` or below
- Rotation evaluates normally — natural convergence back to cap

### 6.6 Paper Runner Parity

Apply the same overflow logic to `run_v14_portfolio_paper.py`. The paper runner uses `self.engines` instead of `self.coins` — adapt the max layer check accordingly.

---

## 7. Risk Assessment

| Risk | Likelihood | Severity | Mitigation |
|---|---|---|---|
| Overflow creates permanently stuck extra position | Low | Medium | When the overflow position TPs, it frees a slot. On next rebalance, if it's not in top-N and has no position, cleanup removes it. Natural convergence. |
| Rebalance cleanup removes overflow engine before it enters | Medium | Low | This is correct behavior — if it didn't enter between creation and next rebalance, it gets a fresh evaluation. No stale engines. |
| Capital split too thin with +1 coin | Low | Low | At $431 with 4 coins, each gets ~$97. Still viable for DCA grid. The alternative (capital sitting idle) is worse. |
| Conflicting overflow on next rebalance day | Low | Medium | `active_count == tier_cap` guard (not `>=`) prevents double-overflow. If overflow is active, count is `cap+1`, which doesn't trigger overflow again. |
| Interaction with deposit detection | Very Low | Low | Deposit detection uses balance comparison, not position counts. Independent system. |
| Edge case: all positions max out AND demax between rebalances | Low | Low | Overflow engine exists but positions drop below max layers during the day. Engine continues normally — it doesn't need all others to stay maxed. The check is entry-time only. |
| Equity tier drop during overflow | Low | Medium | If equity drops and tier_cap decreases, we could have `cap+2` positions. But existing behavior already handles this gracefully: "existing positions continue running, exit naturally." The overflow coin is just one more existing position. |

---

## 8. Testing Plan

### 8.1 Pre-deployment (paper bot)

1. Deploy to `run_v14_portfolio_paper.py` first (paper PM has 5 coin cap at $95K)
2. Wait for all 5 positions to be at max layers (L4) — or temporarily reduce `DCA_MAX_LAYERS` to L1 in test to trigger sooner
3. Verify overflow engine is created when all positions are maxed
4. Verify overflow coin enters L1 on next qualifying candle
5. Verify next day's rebalance does NOT remove the overflow engine (it has a position)
6. Verify when a capped position TPs, the overflow coin becomes "regular" (back to ≤cap)
7. Verify `OVERFLOW_ENTRY_ENABLED = False` prevents overflow

### 8.2 Post-deployment (live bot) monitoring

1. Watch rebalance log for "OVERFLOW" message
2. Verify overflow coin enters on exchange
3. Verify TP order placed
4. Verify next rebalance handles it correctly
5. Verify status.json and dashboard show overflow coin correctly

---

## 9. Hard Rules Compliance

| Rule | Status |
|---|---|
| #26: seed_capital immutable | ✅ Not touched |
| #29: Trade CSV append-only | ✅ Not touched |
| #30: No unrealized in detection | ✅ Not touched |
| #31: Idempotent restart | ✅ Overflow engine persisted via `_save_state()`. On restart, engine restored normally. `active_count` recalculated from actual positions — overflow state is implicit, not stored separately. |
| #32: Post-tick gates rollback | ✅ Overflow coin enters the same gate chain as any other coin |
| #33: Read arch spec before fix code | ✅ This spec |
| #34: No forced closes | ✅ Overflow position exits via TP only |
| #35: Check bot data before git ops | ✅ Not a git change |

---

## 10. Decision Record

| Question | Answer | Rationale |
|---|---|---|
| Should overflow be unlimited? | No — cap at +1 | Over-diversification risk. +1 is the minimal fix for idle capital. Can revisit if needed. |
| Should overflow persist across restarts? | Implicitly yes | The engine is in `self.coins`, persisted in `engine_state.json`. On restart, it's restored as a regular engine. `active_count` is recalculated dynamically. |
| What if user deposits capital and positions aren't maxed? | No overflow — DCA layers absorb it | Existing L2-L4 grid mechanics handle capital injection. Overflow is only for the "literally can't deploy anywhere" case. |
| Should the overflow coin get a full allocation? | Yes — same as rebalance target | It's in the allocation list from `rebalance_daily()`. Gets proportional allocation like any other coin. |
| Should we track overflow state explicitly? | No | The state is implicit: `active_count > tier_coin_cap` = overflow is active. No need for a separate flag. Simpler = fewer bugs. |
| Does this change the daily rebalance allocations? | No | `rebalance_daily()` in CapitalRouter still selects top-N by score. The overflow coin may or may not be in those N. If it is, it gets a normal allocation. If not, it keeps its initial allocation and gets cleaned up when it has no position. |

---

## 11. Files Changed

| File | Change Type | Lines (est.) |
|---|---|---|
| `trading/spot/run_v14_portfolio_live_aster.py` | Modify | ~25 (rebalance gate + helper) |
| `trading/spot/run_v14_portfolio_paper.py` | Modify | ~20 (same logic, adapted for paper structure) |

No changes to: `v14_capital_manager.py`, `v14_lifecycle_engine.py`, `v14_dca_engine.py`, `v14_cycle_scanner.py`, dashboards, scheduled tasks, deposit detection.
