# Grid-Profile-Per-Regime Spec
_Version: 1.0 | Date: 2026-07-03 | Status: SPEC — pending backtest validation_
_References: GridModel (grid_model.py), D-GRID(d) resolution, audit Task 4.5_

---

## 1. Problem Statement

D-GRID(d) — the bull-phase grid (40/24/20/16%) — is optimized for the current macro
assumption: bottom is in, capital velocity via fast L1-L2 cycles is the dominant return
driver. This is correct for the bull phase.

As the cycle matures, the optimal grid geometry changes:
- **Late-cycle (approaching top)**: Higher L3-L4 allocation defends against deeper
  corrections while the trend is still up. More defensive depth, less L1 aggression.
- **Bear/short regime**: Grid mechanics invert. Short grids add layers into rallies
  (adverse for shorts). Layer sizing should match the volatility characteristics of
  bounces, not dips.

A single fixed grid across all market conditions leaves money on the table.

## 2. Design: Named Grid Profiles

```python
# In grid_model.py:
GRID_PROFILES = {
    "bull": {
        "fractions": [0.40, 0.24, 0.20, 0.16],  # D-GRID(d) — current production
        "description": "Front-loaded for capital velocity. Best when L1-L2 cycles dominate."
    },
    "defensive": {
        "fractions": [0.30, 0.25, 0.25, 0.20],  # More even distribution
        "description": "Balanced depth for late-cycle. Trades L1 speed for L3-L4 defense."
    },
    "bear_short": {
        "fractions": [0.35, 0.25, 0.22, 0.18],  # TBD from backtest
        "description": "Optimized for short DCA during bear legs. Bounce-resilient."
    },
}
```

All profiles sum to 1.00 (fully self-funded). All use the same SO_DEVIATION, TP_PCT,
MAX_LAYERS — only layer volume distribution changes.

## 3. Profile Selection

Selected by the **global regime** at the time a **new deal opens**. Existing positions
always finish under the grid that opened them (Rule #34 corollary — never resize/rebase).

```python
def get_active_profile(global_regime: str) -> str:
    if global_regime == "LONG_DCA":
        return "bull"        # or "defensive" based on cycle phase
    elif global_regime == "SHORT_DCA":
        return "bear_short"
    return "bull"            # default
```

**Transition behavior:**
- Regime flips LONG → SHORT: new short deals use `bear_short` profile
- Existing long positions (orphans) continue with their original `bull` profile
- No positions are resized, closed, or rebased

## 4. Implementation

### 4.1 GridModel Extension

```python
class GridModel:
    def __init__(self, profile: str = "bull"):
        self.profile = profile
        self.fractions = GRID_PROFILES[profile]["fractions"]
    
    def layer_cost(self, layer_idx, allocation):
        return allocation * self.fractions[layer_idx]
```

### 4.2 Per-Deal Profile Tracking

Each open deal records which profile opened it:
```python
# In open_deals:
{
    "NEAR/USDT:long": {
        "layers": 3,
        "invested": 84.0,
        "grid_profile": "bull",  # locked at deal open
        ...
    }
}
```

### 4.3 Engine Integration

The engine receives the active profile via `allocated_capital` + a profile parameter.
When adding DCA layers to an existing deal, it uses the deal's locked profile, not the
current global profile.

## 5. Backtest Required

Before implementing, backtest each profile on historical data:

1. **Bull profile** on bull-leg data (2025-2026): confirm current results
2. **Defensive profile** on late-cycle/correction data: measure drawdown reduction vs velocity loss
3. **Bear_short profile** on bear-leg data (simulated short grids): measure short-specific performance

Acceptance: defensive must show measurably lower max drawdown with ≤15% velocity reduction
on correction windows. Bear_short must outperform bull profile on simulated short grids.

## 6. Out of Scope

- Automatic profile switching based on cycle indicators (manual regime flip controls this)
- More than 3 profiles (keep it simple)
- Changing TP%, deviation, or max layers per profile (only volume distribution varies)
- Retroactive profile changes on open positions (Rule #34)

## 7. Dependencies

- GridModel refactored to support profile parameter (minor extension)
- Global regime already tracked and persisted
- Signal-aware deployment (Task 4.6) — veto/gate system operates independently of profile
