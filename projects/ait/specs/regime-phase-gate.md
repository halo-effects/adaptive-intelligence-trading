# Spec: Regime Phase Gate — Portfolio-Level Regime Controls Per-Coin Trading Eligibility

**Status**: DRAFT — needs approval
**Date**: 2026-05-09
**Priority**: HIGH
**Restart Required**: YES (both live and paper bots)
**Architecture Reference**: V14PM_SYSTEM_ARCHITECTURE.md §7.5

## Problem

Individual coin engines autonomously transition between LONG_DCA and SHORT_DCA based
on their own signal stack. There is no gate preventing a coin from trading when its
phase conflicts with the global portfolio regime.

HYPE entered SHORT_DCA (top signals fired) while the global regime is LONG_DCA. The
engine is now running a short strategy against the macro trend direction.

## Design (from §7.5)

**A coin may only open new positions when its engine phase matches the global regime.**

- Engine still processes candles and updates indicators (signals tracked even when excluded)
- No forced closes — open positions ride to TP naturally
- When global regime flips, coins that already match become immediately eligible
- Global regime changes ONLY via manual APPROVE command

## Implementation

### 1. Global Regime State (replace hardcoded direction)

**File**: `run_v14_portfolio_live_aster.py` (and paper equivalent)

Replace:
```python
global_direction = "LONG"  # hardcoded on line 1176
```

With a persisted state variable:
```python
# In __init__:
self._global_regime = "LONG_DCA"  # Default, overridden by state.json on restore

# In _save_state / _load_state:
state["global_regime"] = self._global_regime
self._global_regime = state.get("global_regime", "LONG_DCA")
```

### 2. Regime Gate in Candle Loop

After `engine.tick()` returns actions, before executing:

```python
# Regime gate: coin trades only when its phase matches global regime
engine_phase = cs.engine.phase if cs.engine else None
if engine_phase and engine_phase != self._global_regime:
    # Coin's phase conflicts with global — exclude from trading
    if actions:
        logger.info(
            f"REGIME GATE: {sym} in {engine_phase} but global is "
            f"{self._global_regime} — {len(actions)} action(s) blocked"
        )
    actions = []  # Block all new entries
    # But DON'T rollback the engine phase — it reflects the coin's real signal state
```

### 3. Regime Monitor Updates

The existing `_check_coin_regime_conflict` is replaced by:
- Counting coins whose phase differs from `self._global_regime`
- Alerting at tier thresholds (informational, then APPROVE/DENY prompt)
- Dashboard display of per-coin phase vs global regime

```python
def _update_regime_monitor(self):
    """Count coins that have flipped and alert at thresholds."""
    flipped = []
    for sym, cs in self.coins.items():
        if cs.engine and cs.engine.phase != self._global_regime:
            flipped.append(sym.split("/")[0])

    total = len([c for c in self.coins.values() if c.engine])
    count = len(flipped)

    # Tier thresholds (configurable)
    if count >= total * 0.5 and self._regime_alert_state != "AWAITING_APPROVAL":
        # Tier 2: strong signal
        self._regime_alert_state = "AWAITING_APPROVAL"
        opposing = "SHORT_DCA" if self._global_regime == "LONG_DCA" else "LONG_DCA"
        send_telegram(
            f"🚨 REGIME SIGNAL: {count}/{total} coins flipped to {opposing}\n"
            f"Coins: {', '.join(flipped)}\n"
            f"Reply APPROVE to flip global regime, DENY to dismiss."
        )
    elif count >= total * 0.3:
        # Tier 1: early warning (informational)
        ...
```

### 4. APPROVE/DENY Flow

Already exists in Telegram command handler. Update to:
```python
if text == "APPROVE":
    opposing = "SHORT_DCA" if self._global_regime == "LONG_DCA" else "LONG_DCA"
    self._global_regime = opposing
    self._regime_alert_state = "NONE"
    # Coins already in the new regime phase immediately become eligible
    send_telegram(f"Global regime flipped to {opposing}. Matching coins now eligible.")
```

### 5. Dashboard Updates

Add to status.json:
- `global_regime`: "LONG_DCA" or "SHORT_DCA"
- Per-coin: `trading_status`: "active" or "excluded"
- Per-coin: `regime_conflict`: true/false

### 6. What Changes vs Current Code

| Component | Before | After |
|-----------|--------|-------|
| Global direction | Hardcoded `"LONG"` | Persisted `_global_regime` in state.json |
| Coin phase gate | Post-tick flag (too late) | Pre-action filter (blocks execution) |
| Engine phase | Rolled back on conflict | Preserved (reflects real signal state) |
| Regime monitor | Counts top/bottom signals | Counts phase mismatches vs global |
| Force close on flip | N/A | Never — positions ride to TP |
| Regime change | Manual but didn't actually work | Manual APPROVE changes `_global_regime` |

### 7. No Forced Closes

When the global regime flips:
- Open positions on excluded coins still have their TP orders on the exchange
- TPs fire naturally when price reaches them
- No market sells, no position liquidation
- The coin is simply excluded from opening NEW entries until its phase matches
