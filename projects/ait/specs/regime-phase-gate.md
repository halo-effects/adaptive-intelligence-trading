# Spec: Regime Phase Gate — Block Engine Phase Transitions That Conflict With Macro Regime

**Status**: DRAFT — needs approval
**Date**: 2026-05-09
**Priority**: HIGH (engine can enter SHORT DCA while macro says LONG)
**Restart Required**: YES (both live and paper bots)

## Problem

The V14 DCA engine autonomously transitions between LONG_DCA and SHORT_DCA based on per-coin technical signals (top detection → SHORT, bottom conviction → LONG). The portfolio manager has a macro regime monitor that tracks the overall market direction.

**The gap**: There is no gate preventing an individual engine from transitioning to SHORT_DCA when the macro regime is LONG (or vice versa). The regime conflict checker (`_check_coin_regime_conflict`) only flags coins AFTER the phase transition already happened — it doesn't prevent the transition.

**Result**: HYPE entered SHORT_DCA (top signals fired for that coin individually) while the macro regime says the market is in LONG DCA. The engine is now running a short strategy against the macro trend.

### Current Flow (broken)
```
1. Engine processes candle
2. Engine detects top signals → transitions to SHORT_DCA
3. Engine generates SHORT_OPEN action
4. _check_coin_regime_conflict runs AFTER tick → flags coin (too late)
5. SHORT_OPEN rejected by "not supported in live mode" handler
6. Engine is stuck in SHORT_DCA phase with no way to act
```

### Why `global_direction = "LONG"` Is Hardcoded
Line 1176: The regime flip mechanism requires manual APPROVE/DENY via Telegram. Until a full regime flip is approved, the global direction stays LONG. This is correct — but the engine doesn't know about it.

## Solution

### Option A: Pre-tick Phase Lock (Recommended)
Before calling `engine.tick()`, check if the engine's current phase conflicts with the macro regime. If the engine is about to process a candle that would generate SHORT actions while macro is LONG, override the engine phase back to LONG_DCA before the tick.

```python
# Before engine.tick()
if global_direction == "LONG" and cs.engine.phase == "SHORT_DCA":
    cs.engine._engine.phase = Phase.LONG_DCA
    cs.engine._engine.top_detected = False
    logger.info(f"REGIME OVERRIDE: {sym} forced LONG_DCA (macro regime is LONG)")
```

**Pros**: Simple, deterministic. Engine never enters wrong phase.
**Cons**: Overrides engine's signal-based decision. May miss genuine per-coin tops.

### Option B: Post-tick Action Filter + Phase Rollback
Let the engine tick normally, but if it transitions to a conflicting phase, roll it back immediately.

```python
# After engine.tick()
if global_direction == "LONG" and cs.engine.phase == "SHORT_DCA":
    cs.engine._engine.phase = Phase.LONG_DCA
    cs.engine._engine.top_detected = False
    # Discard any SHORT actions
    actions = [a for a in actions if a["action"] not in ("SHORT_OPEN", "SHORT_CLOSE")]
    logger.info(f"REGIME GATE: {sym} phase rollback SHORT_DCA → LONG_DCA (macro is LONG)")
```

**Pros**: Engine still processes signals (indicators stay accurate). Rollback is clean.
**Cons**: Slightly more complex. Engine may re-trigger top detection on next candle.

### Option C: Feed Macro Regime Into Engine (Long-term)
Pass the macro regime direction as a parameter to `engine.tick()`. The engine itself respects it — top detection is suppressed when macro says LONG, bottom detection suppressed when macro says SHORT.

**Pros**: Cleanest architecture. Engine is regime-aware.
**Cons**: Requires engine code changes, not just portfolio manager changes.

## Recommendation

**Option B for now** (post-tick rollback) — it's the safest because indicators still process all signals correctly, we just prevent the phase change from taking effect. Option C as a future refactor.

### Implementation (Option B)

**Files**: `run_v14_portfolio_live_aster.py` and `run_v14_portfolio_paper.py`

**Location**: In the candle processing loop, right after `engine.tick()` returns actions.

```python
# After: actions = cs.engine.tick(candle, cash_available=cs.allocated_capital)

# Regime phase gate: prevent engine from entering a phase that
# conflicts with the macro regime direction
if actions:
    engine_phase = cs.engine.phase if cs.engine else None
    if global_direction == "LONG" and engine_phase == "SHORT_DCA":
        # Roll back to LONG_DCA — macro says we're in a bull regime
        cs.engine._engine.phase = Phase.LONG_DCA
        cs.engine._engine.top_detected = False
        cs.engine._engine.ob93_armed = False
        cs.engine._engine.early_warning_date = None
        cs.engine._engine.unwinding = False
        actions = [a for a in actions if "SHORT" not in a.get("action", "")]
        logger.info(
            f"REGIME GATE: {sym} phase rollback SHORT_DCA → LONG_DCA "
            f"(macro regime is LONG, top signals overridden)"
        )
    elif global_direction == "SHORT" and engine_phase == "LONG_DCA":
        # Future: roll back to SHORT_DCA when macro is bearish
        pass
```

**Also needed**: Make `global_direction` dynamic instead of hardcoded. Read it from the regime monitor state:
```python
global_direction = "SHORT" if self._regime_signal_type == "TOP" else "LONG"
```

## Why HYPE Flipped to SHORT_DCA

HYPE's engine detected a "top" via one of these signals:
1. **OB93 armed + divergence/timeout**: 2W StochRSI crossed 93, then either bearish divergence appeared or the 35-day timeout expired
2. **1W OB85 fallback**: If 2W peak K was below OB threshold and 1W hit 85
3. **1W K<50 failsafe**: If early warning fired and K dropped below 50 after the failsafe window

This is the engine working as designed for that specific coin's technicals. But the macro portfolio regime says "we're in a bull market, stay long." The engine doesn't know about the macro view — it only sees its own coin's signals.

## What This Doesn't Fix

- The paper bot has the same issue (needs the same gate added to `run_v14_portfolio_paper.py`)
- The hardcoded `global_direction = "LONG"` should eventually be dynamic based on the regime monitor
- Existing SHORT_DCA positions (like HYPE in paper) need manual intervention or will resolve on their own when TP hits
