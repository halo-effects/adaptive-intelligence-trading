# ROUTER v1 Engine Refactor — Documentation

**Date:** 2026-02-27
**Status:** ✅ COMPLETE — Verified 100% identical to v8
**File:** `trading/spot/backtest_results/v13/v13_router_engine_v1.py` (43.6 KB)
**Verification:** `trading/spot/backtest_results/v13/_verify_router_v1.py`

---

## Purpose

Phase 1 of the ROUTER migration: pure architectural refactor of `v13_phase_backtest_v8.py` (v8) into a clean, extensible architecture. **Zero behavior changes** — the refactor must produce 100% identical results to v8 for all coins.

This is the foundation for:
- Phase 2: Dynamic tier gates (signal-based T2/T3 instead of fixed 7/14 day delays)
- Phase 3: Confidence scoring (smarter path selection)
- Phase 4: ROUTER→MARKUP direct path (bottom detection bypass)

## What Changed

### 1. FLAT → ROUTER Rename

| v8 (old) | v1 (new) | Notes |
|---|---|---|
| `Phase.FLAT` | `Phase.ROUTER` | Central routing phase |
| `FLAT_MAX_EVAL_DAYS` | `ROUTER_MAX_EVAL_DAYS` | Config param (still 42) |
| `FLAT_ADX_RANGING` | `ROUTER_ADX_RANGING` | Config param (still 20) |
| `FLAT_ADX_SUSTAINED_DAYS` | `ROUTER_ADX_SUSTAINED_DAYS` | Config param (still 14) |
| `FLAT_MIN_EVAL_DAYS` | `ROUTER_MIN_EVAL_DAYS` | Config param (still 14) |
| `_check_flat()` | `_router_check_router()` | Phase-specific handler |
| `flat_from_top` | `router_from_top` | State flag |
| `flat_from_markdown` | `router_from_markdown` | State flag |
| `time_flat_pct` | `time_router_pct` | Output metric |

### 2. Centralized Signal Computation — `_compute_router_signals()`

**Before (v8):** Each phase handler (`_check_dca()`, `_check_markup()`, `_check_flat()`, `_check_markdown()`) independently computed whatever signals it needed. Same signals recomputed in multiple places.

**After (v1):** All signals computed **once per tick** in `_compute_router_signals()`:

```python
def _compute_router_signals(self, date, price):
    return {
        'hh_hl': self._hh_hl(date),           # Bullish structure streak
        'lh_ll': ...,                           # Bearish structure streak
        'adx': self._adx(date),                # Trend strength
        'cfgi': self._cfgi(date),              # Crypto Fear & Greed
        'fib_levels': self._fib_levels(date),  # Fibonacci levels
        'price': price,
        'date': date,
        'days_in_phase': ...,                  # Days since last transition
        'ob_2w_93': ...,                       # 2W StochRSI OB93 (top signal)
        'ob_1w_85': ...,                       # 1W StochRSI OB85 (top fallback)
        'early_warning_1w': ...,               # 1W early warning
        'failsafe_1w': ...,                    # 1W K<50 failsafe
        'sma200_overext': ...,                 # SMA200 overextension %
    }
```

This signal dict is passed to all phase handlers, eliminating redundant computation and making it easy to add new signals in Phase 2+.

### 3. Centralized Dispatch — `_router_evaluate()`

**Before (v8):** The main loop had scattered `if phase == X: self._check_X()` calls.

**After (v1):** Single dispatch point:

```python
def _router_evaluate(self, date, price):
    signals = self._compute_router_signals(date, price)
    if self.phase == Phase.DCA:
        self._router_check_dca(date, price, signals)
    elif self.phase == Phase.MARKUP:
        self._router_check_markup(date, price, signals)
    elif self.phase == Phase.ROUTER:
        self._router_check_router(date, price, signals)
    elif self.phase == Phase.MARKDOWN:
        self._router_check_markdown(date, price, signals)
```

### 4. Phase Handlers Renamed

| v8 method | v1 method | Phase |
|---|---|---|
| `_check_dca()` | `_router_check_dca()` | DCA |
| `_check_markup()` | `_router_check_markup()` | MARKUP |
| `_check_flat()` | `_router_check_router()` | ROUTER (was FLAT) |
| `_check_markdown()` | `_router_check_markdown()` | MARKDOWN |
| `_check_markup_tiers()` | `_router_check_markup_tiers()` | MARKUP tier adds |

All handler logic is **identical** to v8 — only renamed and refactored to accept the shared `signals` dict.

## What Did NOT Change

- **All transition logic** — same gates, thresholds, and conditions
- **DCA engine** — same BO/SO/TP behavior
- **Tier system** — same T1=60%, T2=20%, T3=10% allocation
- **Top detection** — same 2W OB93 / 1W OB85 / 1W K<50 failsafe
- **Bear bias** — same Weekly CFGI RSI(7) < 40 bear-OFF signal
- **LH_LL gate** — same requirement for MARKDOWN entry
- **Config defaults** — all numerical values preserved
- **Output format** — same result dict structure

## Verification Results

```
V8 BASELINE VERIFICATION
============================================================
ETH: PASS | phases 27/27 | trades 92/92
SOL: PASS | phases 10/10 | trades 87/87
BTC: PASS | phases 21/21 | trades 66/66
LINK: PASS | phases 21/21 | trades 50/50
XRP: PASS | phases 26/26 | trades 66/66
OVERALL: ALL PASS
```

**Verification checks per coin:**
1. Final equity — $0.00 delta (tolerance: $0.005)
2. Total trade count — identical
3. Phase transition count — identical
4. Phase transition dates — identical (every single transition)
5. Phase transition types — identical (with FLAT↔ROUTER normalization)

**Test period:** Jan 2023 → Feb 25, 2026 (ETF era)
**Capital:** $2,500 per coin

## Architecture Diagram

```
                    ┌──────────────────────┐
                    │   Main Loop (daily)   │
                    │   for each date:      │
                    │     _router_evaluate() │
                    └──────────┬───────────┘
                               │
                    ┌──────────▼───────────┐
                    │ _compute_router_     │
                    │ signals()            │
                    │ (computed ONCE/tick) │
                    └──────────┬───────────┘
                               │
              ┌────────┬───────┴───────┬────────┐
              ▼        ▼               ▼        ▼
         ┌────────┐ ┌────────┐  ┌──────────┐ ┌──────────┐
         │  DCA   │ │ MARKUP │  │  ROUTER  │ │ MARKDOWN │
         │ check  │ │ check  │  │  check   │ │  check   │
         └────────┘ └────────┘  └──────────┘ └──────────┘
```

## Transition Matrix (preserved from v8)

```
FROM → TO         GATE                                    
DCA → MARKUP      HH_HL ≥ 2 + Fib_support + SMA200 < 20%
DCA → MARKDOWN    LH_LL ≥ 2 + ADX > 20 + Fib_break      
MARKUP → ROUTER   2W OB93 / 1W OB85 / 1W K<50 failsafe  
ROUTER → DCA      ADX < 20 sustained 14d OR 42d timeout  
ROUTER → MARKDOWN LH_LL ≥ 2 + ADX > 20 + Fib_break      
MARKDOWN → DCA    HH_HL ≥ 2 + Fib_support (structure flip)
```

## File Inventory

| File | Size | Purpose |
|---|---|---|
| `v13_router_engine_v1.py` | 43.6 KB | ROUTER v1 engine (class: `V13RouterV1`) |
| `_verify_router_v1.py` | 3.6 KB | Verification script (v8 vs v1 comparison) |
| `v13_phase_backtest_v8.py` | 43.0 KB | Original v8 engine (preserved for rollback) |

## Next Steps (Phase 2: Dynamic Tier Gates)

Replace fixed tier delays with signal-based confirmation:

**Current (v8/v1):**
- T2 added after 7 days in MARKUP
- T3 added after 14 days in MARKUP

**Proposed (Phase 2):**
- T2 added when: HH_HL continues + ADX > 25 + volume confirmation
- T3 added when: sustained trend + no OB signals + price making new highs

See design doc: `projects/ait-product/intelligent-flat-conductor.md` (Section: Dynamic Tier Gates)

## Related Documents

- **Design Doc:** `projects/ait-product/intelligent-flat-conductor.md` — Full ROUTER vision (v3), confidence scoring, strategy plugins
- **Roadmap:** `projects/roadmap-q1-2026.md` — Project 2B/2C tracking
- **DCA Baseline:** `projects/ait-product/dca-optimization-baseline.md` — DCA research results
- **FLAT Routing Analysis:** `projects/ait-product/flat-routing-optimization.md` — Why blunt speedups fail
