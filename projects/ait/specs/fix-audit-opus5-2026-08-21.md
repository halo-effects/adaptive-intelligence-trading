# Fix Audit — Undetected TP Fill Bug Fixes

**Auditor:** Claude Opus (subagent)
**Date:** 2026-08-21
**File:** `trading/spot/run_v14_portfolio_live_aster.py`
**Reference:** `specs/undetected-tp-fill-bug-spec.md`, `v14pm-code-map.md`

---

## Fix 1: `_safe_cancel_tp()` — PASS WITH NOTES

**Location:** Line 1576 (method), called from lines 1696, 3185, 4162, 4955

### Correctness Analysis

**Filled vs cancelled vs error distinction — Mostly correct, one gap:**

The three-way branch (`cancelled` → `check_order_status: filled` → `check_order_status: not filled/error`) is well-designed. However, there is a gap in how `check_order_status` failures are handled (see Bug 1.1 below).

**Infinite recursion check — SAFE:**

Traced all call chains:
- `_place_tp_order` → `_safe_cancel_tp` → `_handle_tp_fill` → (terminal, no callback)
- `_execute_action SELL` → `_safe_cancel_tp` → `_handle_tp_fill` → (terminal)
- `force_close` → `_safe_cancel_tp` → `_handle_tp_fill` → (terminal)
- `phase_change` → `_safe_cancel_tp` → `_handle_tp_fill` → (terminal)

`_handle_tp_fill` never calls `_safe_cancel_tp` or `_place_tp_order`. No recursion possible. ✅

**Return value handling at call sites:**

| Call Site | Line | Checks Return? | Behavior on `False` | Verdict |
|---|---|---|---|---|
| `_place_tp_order` | 1696 | ✅ Yes | Returns early (no new TP placed) | Correct |
| `_execute_action` SELL | 3185 | ✅ Yes | Rejects action, returns | Correct |
| Force-close | 4162 | ✅ Yes | Skips force-close, returns | Correct |
| Phase-change | 4955 | ❌ No | Continues to next code | Acceptable* |

*Phase-change: If `_safe_cancel_tp` returns `False` (TP filled), `_handle_tp_fill` already processed the fill, zeroed engine, and popped `open_deals`. The phase-change code continues harmlessly — subsequent operations (CFGI poll, grid freeze check, save state) don't depend on position state being consistent mid-loop. Next tick sync restores everything. Acceptable.

### Bug 1.1: `check_order_status` silent catch bypasses exception path (MEDIUM)

**The issue:** `check_order_status()` (line 659) catches ALL exceptions internally and returns `{}`:
```python
except Exception as e:
    logger.warning(f"check_order_status({order_id}): {e}")
    return {}
```

In `_safe_cancel_tp`, the exception handler (line 1631) is designed to leave `cs.tp_order_id` intact for retry:
```python
except Exception as e:
    logger.error(f"Cannot determine status...")
    return True  # Don't clear the ID
```

**But this path is unreachable.** Since `check_order_status` never raises to its caller, `_safe_cancel_tp` receives `{}` as a "normal" result. Then:
1. `result.get("filled")` → `None` → falsy
2. Enters the `else` branch (line 1625)
3. **Clears `cs.tp_order_id` and `cs.tp_limit_price`**
4. Returns `True`

**Impact:** A transient API failure (network timeout, rate limit) during `check_order_status` causes `_safe_cancel_tp` to clear the tp_order_id, losing tracking of a potentially live or filled order. This is the same class of bug as the original Bug A.

**Fix:** Add an empty-result guard before the filled check:
```python
result = self.client.check_order_status(sym, old_order_id)
if not result:
    # check_order_status failed internally — can't determine status
    logger.error(
        f"Cannot determine status of TP order {old_order_id} for {sym} "
        f"(empty result). Leaving order ID intact for retry."
    )
    return True  # Don't block caller, don't clear ID
if result.get("filled"):
    ...
```

### Note 1.2: Error path + `_place_tp_order` interaction (LOW)

When `_safe_cancel_tp`'s exception handler fires (if it ever could), it returns `True` but leaves `cs.tp_order_id` intact. `_place_tp_order` then proceeds past the cancel block and places a NEW TP, overwriting `cs.tp_order_id` with the new order ID. The old order is now untracked.

**Mitigated by:** This only happens during severe API outages where the new TP placement would also likely fail (same API). Additionally, the orphan cleanup at TP fill (line 2230) and startup recovery (Phase 2) would eventually catch duplicate orders.

### Note 1.3: Force-close call site doesn't send Telegram on skip (COSMETIC)

At line 4165, when `_safe_cancel_tp` returns `False` (TP silently filled during force-close attempt), the function logs and returns, but doesn't notify the user via Telegram that the force-close was unnecessary because the TP had already filled. Consider adding a Telegram message for operator awareness.

---

## Fix 2: Cross-validate invested in `_handle_tp_fill` — PASS WITH NOTES

**Location:** Line ~2083

### Correctness Analysis

**Fresh fetch timing — Problematic but degraded gracefully:**

When `_handle_tp_fill` fires, the TP has already filled and the position is closed on the exchange. There are two scenarios:

| Scenario | Fresh Fetch | `_last_exchange_positions` | Fix 2 Effective? |
|---|---|---|---|
| TP fills BETWEEN ticks | No position (correct) | No position (sync ran first, updated cache) | ❌ No — both sources empty |
| TP fills DURING tick (after sync, before TP check) | No position | HAS position (sync captured it pre-fill) | ✅ Yes — fallback works |
| Silent fill detected by Fix 1 (new position exists) | HAS new position | HAS new position | ⚠️ Partial — uses new entry, not old |

**The most common scenario (TP fills between ticks) renders Fix 2 inoperative.** The fresh fetch returns no position, and the fallback to `_last_exchange_positions` also has no position because `_sync_positions_from_exchange()` runs at the top of every tick and already removed the closed position from the cache (line 1279: `self._last_exchange_positions = positions`).

**Severity:** MEDIUM — but mitigated because Fix 1 prevents the invested inflation from being created in the first place. Fix 2 is defense-in-depth for cases where the mismatch already exists.

**Could this set invested to 0? — No. ✅**

The guard `if ex_entry > 0:` (line 2103) prevents the override when no exchange data is available. When both sources return nothing, `open_deals.invested` is preserved unchanged.

**Does the fallback to cached positions work correctly? — Conditionally.**

`_last_exchange_positions` is populated from `_sync_positions_from_exchange()` with the full positions dict. For between-tick fills, it's empty for the closed coin. For during-tick fills, it has the pre-fill data and the fallback works correctly.

### Note 2.1: Fix 2 + Fix 1 interaction

When Fix 1 (`_safe_cancel_tp`) detects a silent fill and calls `_handle_tp_fill`, the exchange may have a NEW position (from recent buys). Fix 2's fresh fetch returns the new position's entry price. Then `new_invested = new_entry * old_tp_qty` — mixing the new entry with the old fill quantity. This is approximately correct (entry prices are close) but not exact. Acceptable for defense-in-depth.

### Recommendation

Consider caching the exchange entry price at the time `_place_tp_order` runs (when the position is definitely still open) in `CoinState`. This cached value could be used by Fix 2 as a reliable fallback when both fresh fetch and `_last_exchange_positions` are empty.

---

## Fix 3: Daily invested audit in `_daily_health_digest` — PASS

**Location:** Line ~3648

### Correctness Analysis

**Log-only (no mutations) — Confirmed. ✅**

Fix 3 reads `open_deals.invested` and exchange positions, computes divergence, and adds lines to `digest_lines` and logger output. It never modifies `open_deals.invested` or any other state. This is a pure observation/alerting mechanism.

**API call impact — Acceptable. ✅**

One additional `fetch_open_positions()` call per daily digest (once per 24h). Negligible API impact. The call is batched with other daily operations (zombie detection, book status, grid freeze check).

**API failure handling — Correct. ✅**

```python
except Exception as e:
    logger.warning(f"Invested audit failed: {e}")
```

The entire audit block is wrapped in try/except. API failures log a warning and the digest continues without the audit section. No impact on other digest items or bot operations.

**`fetch_open_positions` returning `{}` on internal error — Handled correctly. ✅**

When `fetch_open_positions` catches internally and returns `{}`, the audit loop processes an empty dict. For each deal, `ex_pos = audit_positions.get(base, {})` returns `{}`, so `ex_qty = 0`. The guard `if ex_qty <= 0 or ex_entry <= 0: continue` skips the deal. No false alarms are generated.

**Log levels — Appropriate. ✅**

- `>10%` divergence: `logger.warning()` + `⚠️` in digest
- `>5%` divergence: `⚠️` in digest only (INFO-level visibility)
- `≤5%`: no output (within normal slippage range)

---

## Fix 4: Prevent deal accumulation in BUY path — FAIL

**Location:** Line ~3088

### Bug 4.1: Race condition with Fix 1 — CRITICAL 🔴

**Scenario:** Silent TP fill occurred, engine generates new BUY, buy fills on exchange.

**Execution trace:**
1. **Fix 4** (line ~3095): `fetch_open_positions()` returns new position (small qty from fresh buy). `fix4_ex_qty < deal_qty * 0.5` → True. Force-closes stale deal with zero proceeds: `on_sell(sym, deal_qty, 0.0, 0.0, 0.0, stale_ts)`. **Does NOT clear `cs.tp_order_id`.**
2. **`on_buy`** (line ~3145): Creates NEW deal (since old was popped by Fix 4).
3. **`_place_tp_order`** (line ~3160): Sees `cs.tp_order_id` is still set (Fix 4 didn't clear it) → calls `_safe_cancel_tp`.
4. **`_safe_cancel_tp`** (Fix 1): Cancel fails (old TP already filled) → `check_order_status` confirms filled → calls `_handle_tp_fill`.
5. **`_handle_tp_fill`**: Pops `open_deals[f"{sym}:long"]` — **which is now the NEW deal** created in step 2, not the old one.

**Consequences:**
- **Two phantom trades in CSV**: Fix 4's -100% loss on old deal + Fix 1's trade using old TP proceeds against new deal's invested
- **New position on exchange has no deal tracking** — `open_deals` is empty
- **Engine zeroed by `_handle_tp_fill`** — temporarily loses sight of new position
- **No TP order placed** for the new position (`_place_tp_order` returns early because `_safe_cancel_tp` returned `False`)

**This is the primary use case these fixes are designed for**, not a rare edge case. Every time the silent-fill bug manifests and a new buy happens, both Fix 4 and Fix 1 would fire in sequence, causing this double-fire corruption.

**Fix:** Add `cs.tp_order_id = None; cs.tp_limit_price = None` after Fix 4's force-close. Or better: have Fix 4 call `_safe_cancel_tp(sym, cs)` first, before the force-close. If the old TP filled, `_handle_tp_fill` processes it with real proceeds (no phantom loss), and Fix 4 can skip the force-close (deal already handled). If the old TP was cancelled/expired, `_safe_cancel_tp` clears the order ID, and Fix 4 proceeds to force-close.

### Bug 4.2: Vulnerable to transient API failure — HIGH 🔴

`fetch_open_positions()` (line 755) catches all exceptions internally and returns `{}`:
```python
except Exception as e:
    logger.error(f"fetch_open_positions failed: {e}")
    return {}
```

Fix 4's outer try/except (line ~3107) catches exceptions raised by the block, but `fetch_open_positions` never raises — it catches internally. So a transient API failure flows through as:
1. `fix4_positions = {}` (empty, not None)
2. `fix4_base` not in `fix4_positions` → `fix4_ex_qty = 0.0`
3. `0.0 < deal_qty * 0.5` → **True** → Fix 4 fires falsely

**Impact:** A single API glitch (network timeout, rate limit, exchange maintenance) causes Fix 4 to force-close a **healthy, valid deal** with zero proceeds, recording a phantom -100% loss. The exchange position survives but loses its deal tracking.

**Fix:** Cross-check against `_last_exchange_positions` before triggering:
```python
if fix4_ex_qty < deal_qty * 0.5:
    # Guard against API failure: check if cached positions disagree
    cached_qty = self._last_exchange_positions.get(fix4_base, {}).get("qty", 0) or 0
    if cached_qty >= deal_qty * 0.5:
        logger.warning(
            f"Fix4 skipped for {sym}: fresh fetch shows {fix4_ex_qty:.4f} qty "
            f"but cached positions show {cached_qty:.4f} (likely API glitch)"
        )
    else:
        # Both sources agree position is gone — safe to force-close
        ...
```

### Issue 4.3: Phantom -100% loss distorts statistics (MEDIUM)

```python
stale_record = self.tracker.on_sell(sym, deal_qty, 0.0, 0.0, 0.0, stale_ts)
```

This records: `pnl = 0 - invested = -invested`, `return_pct = -100%`, `fill_price = 0.0`.

**Effects on trade statistics:**
- Win rate drops (phantom loss counted as a losing trade)
- Total PnL reduced by full invested amount
- Average trade return skewed by -100% entry
- `fill_price = 0.0` is clearly invalid in the CSV

The spec acknowledges this trade-off ("the actual proceeds went to the exchange but weren't recorded"), but the accounting is misleading. The exchange balance is correct (it received the TP proceeds), but the CSV shows a catastrophic loss that didn't happen.

**Recommendation:** Either:
1. Mark phantom trades distinctly (e.g., add a `"type": "phantom_close"` field to the record)
2. Use estimated proceeds: `est_proceeds = invested * 1.03` (since TP was at +3%) to record approximate PnL instead of -100%
3. Add a `notes` field to the CSV for auditability

### Issue 4.4: Fresh deal after force-close works correctly — CONFIRMED ✅

After Fix 4 pops the stale deal via `on_sell`, `on_buy` (line ~3145) checks `if key not in self._open_deals` → True → creates a fresh deal with new `deal_id`, `layers=0`, `invested=0.0`. The new buy is tracked cleanly... **IF Bug 4.1 doesn't fire** and corrupt the new deal.

---

## General Audit

### Race conditions between Fix 1 and Fix 4

**See Bug 4.1 above — CRITICAL.** The fixes interact destructively when both fire on the same BUY execution. Fix 4 force-closes the old deal but leaves `cs.tp_order_id` pointing to the old (filled) TP. Fix 1 then fires and inadvertently closes the brand-new deal.

### Infinite loops or repeated state mutation

**No infinite loops found.** All paths are terminal — `_handle_tp_fill` doesn't call back into any fix method.

**Repeated mutation risk:** In the Bug 4.1 scenario, `on_sell` is called twice for the same coin in one tick (once by Fix 4 with zero proceeds, once by `_handle_tp_fill` with old TP proceeds). Both pop from `open_deals` — the first pops the old deal, the second pops the new deal. The dedup check in `on_sell` (line 315: `trade_key = f"{symbol}|{deal['open_time']}|{ts.isoformat()}"`) does NOT catch this because the deals have different `open_time` values. Both phantom trades are recorded.

### Error paths fail-safety

| Fix | Error Path | Blocks Trading? | Verdict |
|---|---|---|---|
| Fix 1 | `check_order_status` fails → returns `True` | No | ✅ (but see Bug 1.1 for ID clearing issue) |
| Fix 2 | Fresh fetch fails → fallback to cached | No | ✅ |
| Fix 2 | Both sources empty → skips correction | No | ✅ |
| Fix 3 | `fetch_open_positions` fails → warns | No | ✅ |
| Fix 4 | `fetch_open_positions` fails → `{}` → **falsely fires** | **Yes — corrupts deal** | ❌ (Bug 4.2) |
| Fix 4 | Outer exception → warns, proceeds | No | ✅ |

### Log levels

| Event | Level | Appropriate? |
|---|---|---|
| Silent TP fill detected | WARNING + Telegram | ✅ Yes — anomaly requiring attention |
| Invested mismatch >10% | WARNING + Telegram | ✅ Yes — likely bug manifestation |
| Invested mismatch 5-10% | Digest line only | ✅ Yes — may be slippage |
| Cancel TP failed | WARNING | ✅ Yes |
| Stale deal force-close | WARNING + Telegram | ✅ Yes |
| Order status check | INFO/DEBUG | ✅ Yes |
| Fix4 check skipped (API) | WARNING | ✅ Yes |

---

## Summary

| Fix | Verdict | Blocking Issues |
|---|---|---|
| **Fix 1** `_safe_cancel_tp` | **PASS WITH NOTES** | Bug 1.1 (empty-result clearing) is medium-severity; add 3-line guard |
| **Fix 2** invested cross-validation | **PASS WITH NOTES** | Timing limitation reduces effectiveness; acceptable as defense-in-depth |
| **Fix 3** daily invested audit | **PASS** | Clean, read-only, well-guarded |
| **Fix 4** prevent deal accumulation | **FAIL** | Bug 4.1 (race with Fix 1) is critical; Bug 4.2 (API failure false positive) is high |

---

## Recommendations

### Must-fix before deployment (blocks Fix 4):

1. **Bug 4.1 — Add `cs.tp_order_id` clearing to Fix 4:** After force-closing the stale deal, clear `cs.tp_order_id` and `cs.tp_limit_price` to prevent `_safe_cancel_tp` from double-firing in `_place_tp_order`:
   ```python
   stale_record = self.tracker.on_sell(sym, deal_qty, 0.0, 0.0, 0.0, stale_ts)
   if stale_record:
       logger.warning(...)
   # Prevent Fix 1 double-fire: old TP is associated with the stale deal
   cs.tp_order_id = None
   cs.tp_limit_price = None
   ```
   
   **Even better approach:** Have Fix 4 call `_safe_cancel_tp(sym, cs)` BEFORE the force-close. If the old TP filled, `_handle_tp_fill` processes it with real proceeds (correct accounting), and the `on_sell` inside `_handle_tp_fill` pops the old deal. Fix 4 can then check if the deal still exists — if it was popped by `_handle_tp_fill`, skip the force-close. If the TP was cancelled/not filled but the deal is still stale, proceed with force-close.

2. **Bug 4.2 — Add API failure guard to Fix 4:** Cross-reference `_last_exchange_positions` before triggering:
   ```python
   if fix4_ex_qty < deal_qty * 0.5:
       cached_qty = self._last_exchange_positions.get(fix4_base, {}).get("qty", 0) or 0
       if cached_qty >= deal_qty * 0.5:
           logger.warning(f"Fix4 skipped: likely API glitch (fresh={fix4_ex_qty}, cached={cached_qty})")
           # Skip force-close — API may be unreliable
       else:
           # Both sources agree — proceed with force-close
           ...
   ```

### Should-fix (non-blocking):

3. **Bug 1.1 — Add empty-result guard to `_safe_cancel_tp`:** Check for empty dict from `check_order_status` before branching on `filled`:
   ```python
   result = self.client.check_order_status(sym, old_order_id)
   if not result:
       logger.error(f"Cannot determine status of TP {old_order_id} (empty result), leaving intact")
       return True  # Don't clear ID, retry next cycle
   ```

4. **Fix 2 timing — Cache entry price at TP placement:** Store `ex_entry` in `CoinState` when `_place_tp_order` runs (the position is definitely open at that point). Use this cached value as an additional fallback in Fix 2's `_handle_tp_fill` correction.

### Nice-to-have:

5. **Fix 4 phantom trade marking:** Add a distinguishing field to phantom-close records so they can be filtered from statistics.

---

## Overall Deployment Verdict

**Deploy Fixes 1, 2, 3 now** (with the 3-line Bug 1.1 guard added to Fix 1).

**Hold Fix 4 for revision.** The race condition with Fix 1 (Bug 4.1) and vulnerability to API failures (Bug 4.2) make it unsafe for live deployment in its current form. Both issues are straightforward to fix — estimated 15-30 minutes of code changes + testing.

**Rationale:** Fix 1 alone prevents 90%+ of the damage by detecting silent fills at cancel time. Fix 2 provides defense-in-depth PnL correction. Fix 3 gives daily visibility into mismatches. Fix 4 is belt-and-suspenders that adds value but needs the two critical bugs fixed first.
