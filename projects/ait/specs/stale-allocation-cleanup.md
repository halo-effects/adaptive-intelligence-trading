# Spec: Stale Allocation Cleanup — Reconcile Router After Daily Rebalance

**Status**: DEPLOYED
**Date**: 2026-05-10
**Priority**: MEDIUM
**Restart Required**: YES

## Problem

`router.active_allocations` accumulates coins over time and never gets cleaned up during
daily rebalance. The dict grows through `request_capital()` calls (on every buy order) but
only shrinks through `_maybe_prune_stale_coin()` (on trade completion when the coin falls
out of scanner top-N).

This means:
- Coins allocated capital months ago remain in `active_allocations` forever if they never
  complete a trade (e.g., engine created but scanner ranking changed before L1 entry)
- `approved_symbols` in status.json shows stale coins (GRASS, FET, ZEC, RENDER, PYTH)
  that aren't in the current scanner top 3 (TON, JUP, INJ)
- The dashboard Portfolio Allocation section showed $0.00 entries for ghost coins

## Root Cause

`router.rebalance_daily()` returns fresh target allocations based on the current scanner,
but the runner never reconciles `router.active_allocations` against those targets. The
rebalance output is used to create/update engines and set `cs.allocated_capital`, but the
router's internal `active_allocations` dict is left untouched.

### Data flow today:
```
Scanner → rebalance_daily() → returns {TON: $X, JUP: $Y, INJ: $Z}
                                         ↓
                              Runner iterates, creates/updates engines
                              Router's active_allocations: UNCHANGED
                                         ↓
                              request_capital() adds coins on buy
                              _maybe_prune_stale_coin() removes on TP + not-in-top-N
                                         ↓
                              active_allocations accumulates stale entries
```

### Data flow after fix:
```
Scanner → rebalance_daily() → returns {TON: $X, JUP: $Y, INJ: $Z}
                                         ↓
                              Runner iterates, creates/updates engines
                                         ↓
                              Reconcile: remove coins from active_allocations
                              that are NOT in new targets AND have no open position
                                         ↓
                              active_allocations stays clean
```

## The Fix

**Single change in `_rebalance_daily()` in `run_v14_portfolio_live_aster.py`, after the
existing engine creation/update loop and before `self._last_rebalance_date = today`.**

```python
# Reconcile router allocations: remove stale coins not in new targets
# that have no open position. Coins with open positions stay (need
# capital to defend DCA layers).
new_target_syms = set(allocations.keys())
stale_syms = []
for sym in list(self.router.active_allocations.keys()):
    if sym in new_target_syms:
        continue  # Still a target — keep
    # Check if coin has an open position
    cs = self.coins.get(sym)
    has_position = (
        cs and cs.engine and cs.engine._engine
        and (cs.engine._engine.long_coins > 0 or cs.engine._engine.short_coins > 0)
    )
    if not has_position:
        stale_syms.append(sym)
        del self.router.active_allocations[sym]

# Same for reserve allocations
for sym in list(self.router.reserve_allocations.keys()):
    if sym in new_target_syms:
        continue
    cs = self.coins.get(sym)
    has_position = (
        cs and cs.engine and cs.engine._engine
        and (cs.engine._engine.long_coins > 0 or cs.engine._engine.short_coins > 0)
    )
    if not has_position:
        if sym not in stale_syms:
            stale_syms.append(sym)
        del self.router.reserve_allocations[sym]

if stale_syms:
    logger.info(
        f"Allocation cleanup: removed {len(stale_syms)} stale coins "
        f"not in new targets and no open position: {sorted(stale_syms)}"
    )
```

## Edge Cases

| Scenario | Behavior | Correct? |
|----------|----------|----------|
| Coin in new targets, in active_allocations | Kept | ✅ |
| Coin NOT in targets, no position | Removed | ✅ |
| Coin NOT in targets, HAS open position | Kept (needs capital for DCA defense) | ✅ |
| Coin was pruned by _maybe_prune, rebalance re-adds | Re-added by request_capital on next buy | ✅ |
| Coin regime-flagged, excluded from scanner input | Not in targets, but may have position → kept if position exists | ✅ |
| Scanner returns empty (failure) | rebalance_daily returns {} → no allocations loop runs → no cleanup runs | ✅ Safe |
| First rebalance after restart | active_allocations loaded from state.json → cleaned against fresh scanner | ✅ |

## What This Does NOT Change

- Scanner logic (v14_cycle_scanner.py)
- Capital manager's rebalance_daily() (v14_capital_manager.py)
- request_capital() / return_capital() flow
- Engine creation/destruction
- T1 gate logic (still checks active_allocations for entry eligibility)

## Dependencies

- `approved_symbols` in status.json derives from `router.active_allocations.keys()` — will now be accurate
- Dashboard Portfolio Allocation already fixed to show only invested > 0 coins — this fix makes the underlying data correct too
- T1 gate checks `router.active_allocations` — stale coins being removed means they correctly can't enter new T1 trades

## Testing

1. Pre-flight import test
2. Verify after restart: active_allocations should contain only current scanner top-N coins
   plus any coins with open positions
3. Verify approved_symbols in status.json matches
4. Verify T1 gate still allows entry for scanner top coins
5. Verify coins with open positions but outside top-N are preserved
