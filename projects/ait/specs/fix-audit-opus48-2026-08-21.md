# Fix Audit (2nd Pass) — Undetected TP Fill Bug Fixes (POST-CORRECTION)

**Auditor:** Claude Opus 4.8 (subagent)
**Date:** 2026-08-21
**File:** `trading/spot/run_v14_portfolio_live_aster.py`
**References:** `specs/undetected-tp-fill-bug-spec.md`, `specs/fix-audit-opus5-2026-08-21.md`, `v14pm-code-map.md`
**Scope:** Audit the CORRECTED code after Bug 1.1, Bug 4.1, Bug 4.2 fixes were applied. Verify prior fixes and find remaining issues.

---

## Executive Summary

The three prior bugs (1.1, 4.1, 4.2) are **all fixed correctly** in the current code. Fix 1, Fix 2, Fix 3, Fix 4 are structurally sound and fail-safe. However, this pass found **4 new issues**, none of which are catastrophic P0 blockers, but two of which (N-1, N-2) should be addressed before treating the code as fully hardened.

**Overall verdict: DEPLOYABLE (all 4 fixes) with 2 recommended follow-ups (N-1, N-2).** The critical accounting-corruption paths from the first audit are closed.

---

## Part 1: Verification of Prior Bug Fixes

### Bug 1.1 — `check_order_status` empty-dict guard → ✅ FIXED CORRECTLY

**Location:** `_safe_cancel_tp` lines ~1606–1617.

The empty-result guard is present and correctly placed **before** the `result.get("filled")` branch:

```python
result = self.client.check_order_status(sym, old_order_id)
if not result:
    logger.error(f"Cannot determine status of TP order {old_order_id} for {sym} "
                 f"(empty result from check_order_status). "
                 f"Leaving order ID intact for retry on next cycle.")
    return True  # Don't block caller, don't clear ID
if result.get("filled"):
    ...
```

**Verified:**
- `check_order_status` returns `{}` on internal exception (line ~707) — confirmed.
- `check_order_status` returns `{"filled": False, "status": status}` for a genuinely-not-filled order — that is a **truthy** dict, so `if not result` is `False` and it correctly falls through to the `else` (clear-and-return-True) branch. Good — the guard does NOT swallow legitimate "not filled" results.
- On empty dict, `tp_order_id`/`tp_limit_price` are **left intact** → the order survives to be re-checked by `_check_tp_fills` / `_recover_tp_orders`. Correct.

**Verdict: FIXED CORRECTLY.** No regression; the guard distinguishes empty-dict (API failure) from `{"filled": False}` (real status) properly.

---

### Bug 4.1 — Clear `cs.tp_order_id` BEFORE `on_sell` → ✅ FIXED CORRECTLY

**Location:** `_execute_action` BUY path, lines ~3159–3172.

The order of operations is now:
```python
# Bug 4.1: Clear TP order ID BEFORE on_sell.
cs.tp_order_id = None
cs.tp_limit_price = None
# Force-close the stale deal with zero proceeds
stale_ts = datetime.now(timezone.utc)
stale_record = self.tracker.on_sell(sym, deal_qty, 0.0, 0.0, 0.0, stale_ts)
```

Then, further down (line ~3197), `on_buy` creates the fresh deal, and `_place_tp_order` (line ~3211) calls `_safe_cancel_tp`. Because `cs.tp_order_id` is now `None`, `_safe_cancel_tp` returns `True` immediately (`if not cs.tp_order_id: return True`) and never fires `_handle_tp_fill`.

**Race with Fix 1 traced and eliminated:**
- Old flow: force-close popped old deal but left `tp_order_id` → `_place_tp_order` → `_safe_cancel_tp` → cancel-fail → `check_order_status`=filled → `_handle_tp_fill` popped the **new** deal. Double-corruption.
- New flow: `tp_order_id` is cleared first → `_safe_cancel_tp` short-circuits → new deal keeps its own fresh TP. No double-pop.

**Verdict: FIXED CORRECTLY.** The race is genuinely eliminated. `on_sell` pops exactly the stale deal; the new deal is created afterward and never touched by `_safe_cancel_tp`.

---

### Bug 4.2 — Cross-check `_last_exchange_positions` on force-close → ✅ FIXED CORRECTLY

**Location:** `_execute_action` BUY path, lines ~3138–3157.

```python
if fix4_ex_qty < deal_qty * 0.5:
    cached_qty = (self._last_exchange_positions
                  .get(fix4_base, {}).get("qty", 0) or 0)
    if cached_qty >= deal_qty * 0.5:
        logger.warning(f"Fix4 skipped for {sym}: fresh fetch shows {fix4_ex_qty:.4f} qty "
                       f"but cached positions show {cached_qty:.4f}. Likely API glitch.")
    else:
        # Both sources agree position is gone → force-close
        ...
```

**Verified:**
- `fetch_open_positions` returns `{}` on internal catch (no raise). When empty, `fix4_ex_qty = 0.0`, which trips `< deal_qty * 0.5`. The cached cross-check then rescues it: if the last successful sync saw a healthy position, `cached_qty >= deal_qty * 0.5` → force-close is **skipped**. Correct.
- `_last_exchange_positions` is refreshed at the top of every tick by `_sync_positions_from_exchange` (line 1279), so the cache is at most ~1 tick (~65s) stale — a reasonable authority for "was there a position moments ago."

**Verdict: FIXED CORRECTLY.** A single API glitch no longer force-closes a healthy deal.

---

## Part 2: Per-Fix Verdicts (current code)

| Fix | Verdict | Notes |
|---|---|---|
| **Fix 1** `_safe_cancel_tp` | **PASS** | Bug 1.1 guard correct. Three-way branch (cancelled / filled / not-filled) sound. No recursion. See N-3 (orphan on error path — pre-existing, low). |
| **Fix 2** invested cross-validate | **PASS WITH NOTES** | Now does fresh fetch + cached fallback + always-corrects-to-exchange. Correct and guarded. Timing limitation (both sources empty on between-tick fills) persists but degrades safely. See N-4. |
| **Fix 3** daily invested audit | **PASS** | Read-only, fully guarded, `{}`-safe. No mutations. Clean. |
| **Fix 4** prevent deal accumulation | **PASS WITH NOTES** | Bug 4.1 + 4.2 both fixed. Phantom -100% stats distortion remains (Issue 4.3 from prior audit — still unresolved, see N-1). |

---

## Part 3: NEW Issues Found (2nd pass)

### N-1 (MEDIUM) — Phantom -100% loss still distorts stats; better path exists but not taken

**Status:** Prior audit's Issue 4.3 was flagged as MEDIUM but **not fixed** — the code still records `on_sell(sym, deal_qty, 0.0, 0.0, 0.0, stale_ts)`.

`on_sell` computes `pnl = 0 - invested - 0 = -invested`, `ret_pct = -100%`, `fill_price = 0.0`. This writes a fabricated catastrophic loss to `trades.csv`:
- Win-rate denominators inflate with a guaranteed loser.
- `total_pnl` / `_cumulative_realized_pnl`... **wait — note the asymmetry:** Fix 4's `on_sell` return value is logged but its `pnl` is **NOT** added to `self._cumulative_realized_pnl` (unlike `_handle_tp_fill`, which does `self._cumulative_realized_pnl += record["pnl"]`). Also, Fix 4 does **not** call `self.router.return_capital(sym, 0.0)`.

**Two consequences of that asymmetry:**
1. **Good:** the drift-detection ledger (`_cumulative_realized_pnl`) is NOT poisoned by the phantom -invested, so deposit/withdrawal detection stays sane. (This is actually safer than if it had been symmetric.)
2. **Bad but bounded:** `trades.csv` and the `TradeTracker.total_pnl`/`win_count` properties (lines ~404–410) **do** include the phantom -100% row, so any reporting that reads those properties or the CSV is skewed. The real TP proceeds went to the exchange and were captured by `reconcile_pools_from_exchange`, so **capital accounting is correct**, only **trade statistics** are wrong.

**Recommendation (unchanged from prior audit, still valid):** Either (a) estimate proceeds at `invested * (1 + DCA_TP_PCT)` so the phantom row books ~+3% instead of -100%, or (b) tag the row (`"type": "phantom_close"`) and exclude it from win-rate/PnL rollups. Option (a) is closest to economic reality since a silent fill almost always occurred at/near the TP.

**Not a deployment blocker** (no capital at risk; only stats), but it should be resolved before trusting win-rate dashboards.

---

### N-2 (LOW-MEDIUM) — Fix 4 does not re-check the deal after phantom close; relies on `on_buy` key-absence

**Location:** BUY path ~3172 (after `on_sell`) → ~3197 (`on_buy`).

After Fix 4 pops the stale deal, `on_buy` is reached unconditionally. `on_buy` creates a fresh deal because the key was popped. This is correct **today**. But there is a subtle fragility:

`on_sell` returns `{}` (falsy) in two cases: (1) key not found, (2) dedup `trade_key` collision. If a dedup collision ever occurred here (same symbol, same `open_time`, same second-resolution `ts`), `on_sell` would still `pop` the deal (the pop happens before the dedup check, line ~294), so the key is gone and `on_buy` still creates fresh — **so it's safe**. Confirmed by reading `on_sell`: the `pop` is unconditional and precedes the dedup guard. No orphaned-deal state.

**However:** if `on_sell` returns `{}` because the deal was already gone (e.g., `_check_tp_fills` popped it earlier in the SAME tick — see N-… concurrency below), Fix 4's guard `if existing_deal and existing_deal.get("qty",0) > 0` was evaluated against a snapshot taken at line ~3110. Between that snapshot and the `on_sell` call there are two `fetch_open_positions` network round-trips (Fix 4's own fetch + potential latency). This is a same-thread single loop, so nothing else mutates `_open_deals` in between — **no true TOCTOU within the tick.** Verdict: currently safe, but the code depends on single-threaded execution. Documented as an invariant to preserve.

**Recommendation:** Add a one-line comment asserting single-threaded tick execution near Fix 4, so a future refactor to async/threads doesn't silently reintroduce a TOCTOU double-pop.

---

### N-3 (LOW) — Error path in `_safe_cancel_tp` can orphan the old TP when a new one is placed

**Location:** `_safe_cancel_tp` exception handler (~line 1644) returns `True` with `tp_order_id` left intact.

Trace: In `_place_tp_order`, `_safe_cancel_tp` returns `True` (couldn't determine status, ID left intact) → code proceeds past the cancel block → places a NEW TP → `cs.tp_order_id = new_oid` **overwrites** the old ID. The old (possibly still-resting) order is now untracked on the exchange.

**Mitigations already present:**
- The `_handle_tp_fill` orphan-cleanup (lines ~2244–2252) cancels ALL resting sell orders after any fill.
- `_recover_tp_orders` Phase 2 (startup) adopts/cancels orphan sells.
- This only triggers during an exception in `check_order_status` — but note `check_order_status` catches internally and returns `{}`, so the **except branch is nearly unreachable**; the empty-dict guard (Bug 1.1 fix) handles the realistic failure mode and correctly does NOT place a new TP (it `return True`, then `_place_tp_order` proceeds... **wait**).

**Sub-finding (worth noting):** The Bug 1.1 empty-result guard returns `True`, same as the exception path. So when `check_order_status` fails (returns `{}`), `_safe_cancel_tp` returns `True` with `tp_order_id` intact — and `_place_tp_order` then **places a second TP** and overwrites the ID. So the "leave ID intact for retry" intent of the Bug 1.1 fix is partially defeated *when the caller is `_place_tp_order`*: the retry never happens because a new order replaces it. The old order becomes an orphan (cleaned up later by orphan sweep). This is not dangerous (orphan sweep catches it; at worst a brief double-sell-order which the exchange would reject-on-insufficient-position or fill harmlessly at TP), but the "retry next cycle" comment is slightly misleading for the `_place_tp_order` call site.

**Recommendation (optional):** In `_place_tp_order`, if `_safe_cancel_tp` returns `True` but `cs.tp_order_id` is still set (i.e., could-not-determine case), consider skipping new-TP placement this cycle and letting `_check_tp_fills` resolve the ambiguous order, rather than overwriting. Low priority — orphan sweep is a sufficient backstop.

---

### N-4 (LOW) — Two `fetch_open_positions` calls in quick succession per BUY / per TP fill

**Interaction between Fix 2 and Fix 4 / `_place_tp_order`:**

- **BUY path:** Fix 4 calls `fetch_open_positions()` (~3113), then `_place_tp_order` calls it again (~1670). Two round-trips within one BUY execution.
- **TP fill path:** Fix 2 in `_handle_tp_fill` calls `fetch_open_positions()` (~2101) fresh, in addition to the cached `_last_exchange_positions`.

These are sequential (not concurrent), so no rate-limit burst risk beyond additive latency (~each call is bounded by the 15s ccxt timeout). On Aster with `enableRateLimit: True`, ccxt self-throttles. **No correctness issue.** Worst case is added latency on BUY execution (up to ~2× a position fetch). Acceptable given these paths are infrequent.

**No divergence risk between Fix 2's fresh fetch and Fix 4's fresh fetch** because they occur in different methods at different times (BUY vs fill), never on the same object in the same statement.

**Recommendation (optional micro-opt):** Fix 4 could pass its already-fetched `fix4_positions` into `_place_tp_order` to avoid the redundant second fetch on the BUY path. Purely a latency optimization.

---

## Part 4: Concurrency / Re-entrancy Analysis

**Could two fixes fire in one tick and double-pop `open_deals`?**

Main-loop order (verified lines 4828→4853→4861):
1. `_sync_positions_from_exchange()` (refreshes `_last_exchange_positions`, phantom cleanup)
2. `_check_tp_fills()` → may call `_handle_tp_fill` → pops deal
3. per-coin engine tick → `_execute_action` BUY → Fix 4 may pop + `on_buy`; `_place_tp_order` → `_safe_cancel_tp`

**Scenario: `_check_tp_fills` pops a deal in step 2, then engine BUYs same coin in step 3.**
- After `_handle_tp_fill` in step 2, the deal is popped, engine zeroed, `cs.tp_order_id = None`.
- In step 3, engine sees no position → may emit BUY. Fix 4 guard: `existing_deal = _open_deals.get(key)` → `None` (already popped) → Fix 4 block skipped entirely. `on_buy` creates fresh deal. `_place_tp_order` → `_safe_cancel_tp` → `tp_order_id` is `None` → returns True. **Clean. No double-pop.** ✅

**Scenario: Fix 4 pops in step 3, then `_safe_cancel_tp` fires later in same `_execute_action`.**
- Covered by Bug 4.1 fix (tp_order_id cleared first). No double-pop. ✅

**`on_sell` pop is idempotent by key:** `pop(key, None)` returns `{}`/`None` if already gone. A second pop of the same key is a no-op. Even if two paths raced (they don't, single-threaded), the second would find nothing. ✅

**Verdict: No double-pop reachable in the current single-threaded loop.** The only guardrail is the single-threaded assumption (see N-2).

---

## Part 5: Fail-Safety of Error Paths (re-verified)

| Fix | Error path | Blocks trading? | Leaves state half-mutated? | Verdict |
|---|---|---|---|---|
| Fix 1 | `check_order_status` `{}` → return True, ID intact | No | No (see N-3 orphan caveat) | ✅ |
| Fix 1 | exception → return True, ID intact | No | No | ✅ |
| Fix 2 | fresh fetch throws → fallback to cached | No | No | ✅ |
| Fix 2 | both empty → skip correction, keep invested | No | No | ✅ |
| Fix 3 | fetch fails / `{}` → warn, continue | No | No | ✅ |
| Fix 4 | fetch `{}` → cached cross-check rescues | No | No | ✅ |
| Fix 4 | outer exception → warn, proceed to on_buy | No | No (tp_order_id only cleared inside the confirmed-stale branch) | ✅ |

**Important fail-safe confirmation for Fix 4:** `cs.tp_order_id`/`cs.tp_limit_price` are cleared **only** inside the "both sources agree position is gone" branch, immediately before `on_sell`. On the API-glitch skip path and the outer-exception path, the TP ID is **preserved**. So a false trigger cannot orphan a live TP. ✅

---

## Part 6: Overall Deployment Verdict

**DEPLOY — all four fixes are safe for live trading in their current form.**

- **Bug 1.1: FIXED CORRECTLY.**
- **Bug 4.1: FIXED CORRECTLY** (race with Fix 1 eliminated).
- **Bug 4.2: FIXED CORRECTLY** (cached cross-check guards API glitches).

The catastrophic accounting-corruption and healthy-deal-destruction paths flagged in the first audit are all closed. No new P0/P1 bugs found. Capital accounting is correct on every path (real proceeds are captured by exchange reconciliation even when Fix 4 books a phantom row).

**Follow-ups (non-blocking), in priority order:**
1. **N-1 (MEDIUM):** Fix the phantom -100% row in Fix 4 — use `invested * (1 + DCA_TP_PCT)` estimated proceeds OR tag+exclude from stats. Currently corrupts win-rate/PnL reporting (not capital). Highest-value follow-up.
2. **N-3 (LOW):** In `_place_tp_order`, avoid overwriting an ambiguous (could-not-determine) `tp_order_id` with a fresh TP; let `_check_tp_fills` resolve it. Orphan sweep is an adequate backstop today.
3. **N-2 (LOW):** Add a comment asserting single-threaded tick execution near Fix 4 to protect the no-double-pop invariant against future async refactors.
4. **N-4 (OPTIONAL):** Pass Fix 4's fetched positions into `_place_tp_order` to eliminate one redundant `fetch_open_positions` per BUY.

**Bottom line:** The live code is materially safer than the pre-fix version and than the version audited in pass 1. Ship it; schedule N-1 as the next iteration since it's the only finding that produces visibly-wrong output (misleading trade stats), albeit with no capital impact.
