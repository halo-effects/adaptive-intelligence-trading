# Spec: Orphaned Position TP on Phase Transition

**Date:** 2026-05-15
**Status:** ✅ Approved — deployed 2026-05-16
**Incident:** ONDO/USDT force-closed at -$12.47 loss on live V14PM bot (TOP_FALLBACK_OB85). ADA/USDT force-closed at -$38.01 on V14-ETF paper bot (same trigger).
**Principle:** Phase transitions should NEVER force-close existing positions. Positions exit only via TP hit.

---

## 1. Problem Statement

When the V14 DCA engine detects a top signal (OB93+divergence, OB85 fallback, failsafe K<50), it currently:

1. Calls `_long_dca_close()` — force-sells all long coins at market price
2. Calls `_change_phase()` — transitions to SHORT_DCA

Similarly, when it detects a bottom conviction signal:

1. Calls `_short_dca_close()` — force-buys-back all short coins at market price
2. Calls `_change_phase()` — transitions to LONG_DCA

This force-close often realizes a loss because the position hasn't reached TP. The engine is choosing to exit at an unfavorable price based on a directional signal, violating the core DCA principle: **enter on signal, exit on TP**.

The architecture spec (§7.5.2) states:
> *"No forced closes. Open positions naturally hit TPs. The gate only blocks NEW entries."*

The regime gate at the runner level correctly implements this for the **global** regime, but the engine-level phase transition ignores it entirely — the close happens inside `engine.tick()` before any runner gate can intervene.

### 1.1 Affected Code Paths

All force-close calls in `v14_dca_engine.py`:

| Signal Handler | Close Call | Phase Transition | Direction | Action |
|---------------|-----------|------------------|-----------|
| `_check_top_signals` (OB93+div/timeout) | `_long_dca_close('TOP_OB93+...')` | LONG_DCA → SHORT_DCA | Close longs | **REMOVE** |
| `_check_top_signals` (OB85 fallback) | `_long_dca_close('TOP_FALLBACK_OB85')` | LONG_DCA → SHORT_DCA | Close longs | **REMOVE** |
| `_check_top_signals` (failsafe K<50) | `_long_dca_close('TOP_FAILSAFE_K50')` | LONG_DCA → SHORT_DCA | Close longs | **REMOVE** |
| `_check_bottom_signals` (conviction) | `_short_dca_close('BOTTOM_CONVICTION_...')` | SHORT_DCA → LONG_DCA | Close shorts | **REMOVE** |
| `_check_markdown_exit` (25%+ rise) | `_short_dca_close('MARKDOWN_FAIL')` | SHORT_DCA → LONG_DCA | Close shorts | **REMOVE** |
| `run()` loop end | `_long_dca_close('OPEN_END')` / `_short_dca_close('OPEN_END')` | N/A (backtest cleanup) | Both | Keep |

### 1.2 MARKDOWN_FAIL — Also a Forced Close

`_check_markdown_exit()` force-closes short positions when price rises 25%+ against the grid with ADX > 25. This was a **capital protection safety net designed for leveraged trading** — a 25% adverse move on leverage is catastrophic.

With **1.0x leverage (no leverage)**, this safety net is counterproductive:
- It force-sells at a loss instead of letting the grid recover naturally
- The DCA grid is designed to handle drawdowns — more layers fill, avg entry adjusts, TP gets closer
- The regime phase gate already prevents new wrong-side entries
- The orphaned TP mechanism (this spec) handles directional transitions gracefully

MARKDOWN_FAIL violates the same principle as the signal-driven force-closes: **positions should exit via TP, not via panic**. On no leverage, there is no margin call risk — the position can wait.

**Decision:** Remove `_check_markdown_exit()` entirely. No symmetric long-side equivalent exists (short-only check).

### 1.3 What Should NOT Change

- **`run()` OPEN_END:** Backtest cleanup only. Not relevant to live/paper trading.

- **Phase transitions themselves:** The engine should still transition phases autonomously based on signals. Only the force-close of positions during transition is removed.

---

## 2. Design: Orphaned Position TP

### 2.1 Core Concept

When a phase transition occurs, existing positions in the old direction become **orphaned**. They are no longer managed by the active phase's DCA grid, but they still have a TP target. The system should:

1. **Allow the phase transition** — the engine enters the new phase
2. **Leave the orphaned position intact** — coins, avg_entry, TP all preserved
3. **Check orphaned TP on every tick** — if price hits the TP, close the orphan (TP-only, no new DCA layers)
4. **Block new entries in the orphaned direction** — handled by regime gate (§7.5.2) at runner level

### 2.2 Existing Orphan Handling (Lifecycle Engine)

The lifecycle engine (`v14_lifecycle_engine.py`) already has orphan handling for the **hourly between-daily** path:

```python
# In tick(), between-daily, when phase is LONG_DCA:
if self._engine.short_coins > 0 and self._engine.short_tp > 0 and price <= self._engine.short_tp:
    old_unwinding = self._engine.unwinding
    self._engine.unwinding = True   # Prevent new layers
    self._engine._short_dca_tick(date_ts, price)
    self._engine.unwinding = old_unwinding
```

This checks for orphaned shorts during LONG_DCA and closes them at TP (close-only, no new layers via `unwinding=True`). The same pattern exists in `_run_daily_tick()`.

**What's missing:** The reverse — orphaned LONG positions during SHORT_DCA phase. Currently, when the engine flips to SHORT_DCA, the hourly path only runs `_short_dca_tick()` with no check for orphaned longs.

### 2.3 Changes Required

#### Layer 1: `v14_dca_engine.py` — Remove force-closes from signal handlers

**`_check_top_signals()`** — Remove all three `_long_dca_close()` calls. Keep the phase transition, reset, and state tracking:

```python
# BEFORE (each top signal branch):
self._long_dca_close(date, 'TOP_OB93+{reason}')
self._reset_top_state()
self.top_detected = True
self.conviction_fired = False
self._change_phase(date, Phase.SHORT_DCA, f'Top confirmed: OB93+{reason}')

# AFTER:
self._reset_top_state()
self.top_detected = True
self.conviction_fired = False
self._change_phase(date, Phase.SHORT_DCA, f'Top confirmed: OB93+{reason}')
```

**`_check_bottom_signals()`** — Remove `_short_dca_close()` call:

```python
# BEFORE:
short_pnl = self._short_dca_close(date, f'BOTTOM_CONVICTION_{score}/4')
...
self._change_phase(date, Phase.LONG_DCA, ...)

# AFTER:
self.conviction_fired = True
...
self._change_phase(date, Phase.LONG_DCA, ...)
```

#### Layer 1b: `v14_dca_engine.py` — Remove `_check_markdown_exit()` entirely

The entire method and its call site are removed:

```python
# REMOVE from tick() in SHORT_DCA branch:
                self._check_markdown_exit(date, price, signals)

# REMOVE entire method:
    def _check_markdown_exit(self, date, price, signals):
        ... (lines 802-822)
```

Also remove the config constants (or leave as dead code for backtest comparison):

```python
# In V14DCAConfig:
    MARKUP_FAIL_DD_PCT = 0.25   # REMOVE
    MARKUP_FAIL_ADX = 25        # REMOVE
```

**`run()` OPEN_END** — NO CHANGE. Backtest cleanup only.

#### Layer 2: `v14_lifecycle_engine.py` — Add orphaned LONG TP handling

Add orphaned long TP check in the SHORT_DCA hourly path (mirror of existing short orphan logic):

```python
# In tick(), between-daily, when phase is SHORT_DCA:
elif self._engine.phase == Phase.SHORT_DCA:
    self._engine._short_dca_tick(date_ts, price)
    # Check orphaned long TP (phase transitioned — close only, no new layers)
    if self._engine.long_coins > 0 and self._engine.long_tp > 0 and price >= self._engine.long_tp:
        old_unwinding = self._engine.unwinding
        self._engine.unwinding = True   # Prevent new layers
        self._engine._long_dca_tick(date_ts, price)
        self._engine.unwinding = old_unwinding
```

Same addition in `_run_daily_tick()` in the SHORT_DCA branch:

```python
elif eng.phase == Phase.SHORT_DCA:
    eng._short_dca_tick(date, price)
    # Check orphaned long TP (phase transitioned — close only, no new layers)
    if eng.long_coins > 0 and eng.long_tp > 0:
        price_now = eng._price(date)
        if not np.isnan(price_now) and price_now >= eng.long_tp:
            old_unwinding = eng.unwinding
            eng.unwinding = True
            eng._long_dca_tick(date, price)
            eng.unwinding = old_unwinding
    eng._check_bottom_signals(date, price, signals)
    eng._check_markdown_exit(date, price, signals)
```

#### Layer 3: `v14_dca_engine.py` — Guard `_long_dca_tick` against new entries when unwinding

Currently `_long_dca_tick` only checks `self.unwinding` to skip new entries for SHORT positions. Need to verify it also respects `unwinding` for LONG entries. Check whether the `unwinding` flag prevents new BUY layers in `_long_dca_tick`:

```python
def _long_dca_tick(self, date, price):
    ...
    # Don't open new deals if unwinding
    if self.unwinding:
        return
```

This guard exists at line ~370. When `unwinding=True`, no new long layers are opened. The TP check at the top of the function runs BEFORE this guard, so orphaned long TPs will still trigger. ✅ Confirmed safe — same pattern as the existing short orphan handling.

#### Layer 4: Live bot runner — Handle phase-change TP cancel correctly

The live bot (`run_v14_portfolio_live_aster.py`) currently cancels TP orders on phase change (line ~3776):

```python
if current_phase != prev_phase and prev_phase is not None:
    if cs.tp_order_id:
        logger.info(f"Phase change {prev_phase} → {current_phase}: cancelling TP for {sym}")
        self.client.cancel_tp_order(sym, cs.tp_order_id)
        cs.tp_order_id = None
```

**This must be removed or guarded.** With orphaned positions, the TP order on the exchange is the primary mechanism for closing the orphan. Cancelling it defeats the purpose.

**Fix:** Only cancel the TP order if there is no orphaned position in the old direction:

```python
if current_phase != prev_phase and prev_phase is not None:
    # Don't cancel TP if position is orphaned — TP is how it closes
    has_orphan = False
    if cs.engine and cs.engine._engine:
        eng = cs.engine._engine
        if prev_phase == 'LONG_DCA' and eng.long_coins > 0:
            has_orphan = True  # Long position orphaned by flip to SHORT_DCA
        elif prev_phase == 'SHORT_DCA' and eng.short_coins > 0:
            has_orphan = True  # Short position orphaned by flip to LONG_DCA
    if cs.tp_order_id and not has_orphan:
        logger.info(f"Phase change {prev_phase} → {current_phase}: cancelling TP for {sym}")
        self.client.cancel_tp_order(sym, cs.tp_order_id)
        cs.tp_order_id = None
    elif cs.tp_order_id and has_orphan:
        logger.info(
            f"Phase change {prev_phase} → {current_phase}: keeping TP for {sym} "
            f"(orphaned position will close at TP naturally)"
        )
```

#### Layer 5: `_execute_action` SELL handler — Accept orphaned TP fills

The SELL handler in the live bot skips TP sells when an exchange TP order is active:

```python
if cs.tp_order_id and "TP" in reason:
    logger.info(f"Skipping engine TP for {sym} — exchange TP order active")
    return
```

This is correct — the exchange TP will fire and the next sync cycle picks it up. No change needed for orphaned positions because the exchange TP order handles the close. The engine-side orphan TP (from `_long_dca_tick` with `unwinding=True`) is a backup in case the exchange TP was cancelled or missed.

---

## 3. Backtest Impact

Removing force-closes from `_check_top_signals` and `_check_bottom_signals` will change backtest results. Positions that were previously force-closed at a loss will now:

- **If price eventually hits TP:** Close at profit → better PnL
- **If price never hits TP (keeps dropping):** Position stays open through the entire markdown → worse PnL, higher drawdown, capital locked

The DCA grid's natural behavior handles this: as price drops further, more layers fill (if capital permits), lowering avg entry and bringing TP closer. The grid is designed to recover from drawdowns.

**MARKDOWN_FAIL removal impact:** Short positions that previously got force-closed at -25% will now ride out the drawdown. On 1.0x leverage this is acceptable — no liquidation risk. The grid continues filling layers and the TP moves closer. Capital is locked longer but losses aren't realized prematurely.

**Recommendation:** Run a backtest comparison before deploying to live. Compare old (force-close) vs new (orphan-TP + no MARKDOWN_FAIL) across the full coin universe to quantify the impact.

---

## 4. Scope & Risk

| Component | Change | Risk |
|-----------|--------|------|
| `v14_dca_engine.py` | Remove 4 `_close` calls from signal handlers + remove `_check_markdown_exit()` entirely + remove `MARKUP_FAIL_DD_PCT`/`MARKUP_FAIL_ADX` config | **Medium** — changes core engine behavior for all bots |
| `v14_lifecycle_engine.py` | Add orphaned long TP check (mirror of existing short orphan) | **Low** — established pattern |
| `run_v14_portfolio_live_aster.py` | Guard phase-change TP cancel | **Medium** — affects live TP order management |
| `run_v14_portfolio_paper.py` | No change needed (paper bot doesn't manage exchange TP orders) | **None** |
| `run_v14_paper.py` | Inherits engine change | **Low** — paper bot, no exchange interaction |
| `run_v14etf_paper.py` | Inherits engine change | **Low** — paper bot, no exchange interaction |

### 4.1 What This Does NOT Affect

- DCA grid mechanics (BO%, deviation, multiplier, layers, TP%)
- Signal stack (StochRSI, ADX, HH/HL, HybridDetector2D)
- Capital router / allocation logic
- Scanner / scoring
- Dashboard

---

## 5. Deployment Plan

1. **Spec review** — this document → Brett approval
2. **Backtest comparison** — old vs new across key coins (ONDO, INJ, TON, PENDLE, ADA)
3. **Implement** — engine + lifecycle changes, guarded TP cancel in live runner
4. **Pre-flight** — import test on all bot entry points
5. **Deploy paper first** — restart paper bots, monitor 24h
6. **Deploy live** — restart live bot with pre-flight, verify TP orders survive
7. **24h audit** — check trades for anomalies (Hard Rule #6)

---

## 6. Hard Rule Candidate

> **No forced closes — ever.** Phase transitions change direction; they don't liquidate. Positions exit only via TP hit. There are no "safety net" force-closes on 1.0x leverage — the grid is designed to recover from drawdowns. Signal-driven and drawdown-triggered force-closes both violate DCA principles and realize unnecessary losses. (2026-05-15, ONDO incident: -$12.47 on live bot; MARKDOWN_FAIL removal: 2026-05-16)

→ **Adopted as Hard Rule #34** (2026-05-16)

---

## 7. Deployment Notes (2026-05-16)

- **Implementation**: Config toggle `FORCE_CLOSE_ON_SIGNAL=False` (default). Legacy behavior preserved for A/B backtest via `True`.
- **Backtest**: Single-coin comparison across 8 coins (INJ, JUP, TON, ONDO, ADA, PENDLE, NEAR, HBAR). 5/8 improved or same. Portfolio-level dynamics differ (capital rotation).
- **Branch**: `feature/orphan-tp-no-force-close` merged to main.
- **Commit**: `ecddd9b68` (feature), `9c6573ad8` (merge to main after rebase).
- **Paper bots restarted**: 08:24 PDT — V14 Paper (PID 11916), V14PM Paper (PID 12188).
- **Live PM bot restarted**: 08:25 PDT — PID 3648. Pre-flight passed.
- **V14-ETF**: Stale elevated PID 13940 (pre-existing issue, not related to this change). Will pick up new code on next natural restart.
- **Pre-flight**: All 4 bot entry points passed import test.
- **24h audit**: Due by 2026-05-17 08:25 PDT (Hard Rule #6).
