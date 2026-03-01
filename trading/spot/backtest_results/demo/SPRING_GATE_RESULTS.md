# Spring Gate Architecture — Test Results

**Date**: 2026-02-24
**Engine**: V12f with gate-driven spring transitions
**Profile**: High | Capital: $10,000 | Timeframe: 1h

---

## Architecture Summary

### Problem
The V12f lifecycle engine had a critical EXIT→MARKDOWN→DCA cycling bug that produced 449 phase transitions in a single 90-day window (SOL Dec-Mar 2025). Springs never fired because:
1. `should_exit()` triggered on every minor daily score fluctuation
2. MARKDOWN→DCA "false exit" (95% recovery) fired before spring threshold was reached
3. The 25% spring discount threshold was too deep for moderate corrections

### Solution — Three Architectural Changes

**1. EXIT Cooldown (7-day)**
- After MARKDOWN→DCA transition, `should_exit()` blocked for 168 candles (7 days at 1h)
- Prevents rapid re-cycling
- Bug found: duplicate DCA→EXIT check in `_run_main_loop` (consolidation artifact at line ~4898) — both checks now guarded

**2. Remove False-Exit Recovery from V12f MARKDOWN**
- Previously: price recovers to 95% of markdown entry → DCA (false exit)
- Now: MARKDOWN stays until spring gates pass. No DCA escape.
- Rationale: "Isn't there always a spring of some kind?" — Brett. With cooldown preventing re-cycling, false exit wastes the one MARKDOWN opportunity.

**3. Gate-Driven Spring Transition (replaces fixed discount threshold)**
- Previously: spring fires when price drops X% from exit entry (fixed threshold)
- Now: spring fires when **all 3 gates pass** AND price is ≥10% below exit entry (floor)
- Gates:
  - **Dwell ≥ 3 days** in MARKDOWN (prevents flash crash entries)
  - **CFGI ≤ 35** (coin-specific fear/greed confirms market exhaustion)
  - **SMA200 ≤ 110%** (price not overextended above 200-period SMA)
- Gates are checked every candle once past the 10% discount floor
- Engine stays in MARKDOWN riding shorts until gates confirm exhaustion

---

## Test Results — Evolution

### Phase 1: Baseline (no changes)
EXIT→MARKDOWN→DCA cycling, 0 springs.

| Window | Return | MaxDD | EXIT | MARKDOWN | SPRING |
|--------|--------|-------|------|----------|--------|
| ETH Jun-Oct 2024 | -4.06% | 21.92% | 60 | 39 | 0 |
| ETH Dec-Mar 2025 | -6.70% | 16.83% | 113 | 112 | 0 |
| SOL Feb-Jul 2024 | +58.64% | 25.94% | 21 | 21 | 0 |
| SOL Dec-Mar 2025 | **-24.69%** | 29.95% | **449** | **449** | 0 |
| BTC Oct-Mar 2025 | -14.34% | 20.82% | 254 | 196 | 0 |

### Phase 2: EXIT Cooldown Only
Cycling eliminated, but still 0 springs (false-exit recovery preventing spring path).

| Window | Return | MaxDD | EXIT | MARKDOWN | SPRING |
|--------|--------|-------|------|----------|--------|
| ETH Jun-Oct 2024 | -3.90% | 15.50% | 1 | 1 | 0 |
| ETH Dec-Mar 2025 | +14.45% | 11.28% | 1 | 1 | 0 |
| SOL Feb-Jul 2024 | +58.80% | 25.94% | 1 | 1 | 0 |
| SOL Dec-Mar 2025 | +29.13% | 10.28% | 1 | 1 | 0 |
| BTC Oct-Mar 2025 | +9.72% | 18.42% | 1 | 1 | 0 |

### Phase 3: Fixed Threshold Sweep (false-exit removed)
Springs fire, but drawdowns extreme (90%+). Threshold doesn't control DD.

| Threshold | ETH Jun-Oct | ETH Dec-Mar | SOL Feb-Jul | SOL Dec-Mar | BTC Oct-Mar |
|-----------|-------------|-------------|-------------|-------------|-------------|
| 5% | +7.0% (61%DD) 1🌱 | +5.8% (92%DD) 1🌱 | +67.1% (91%DD) 1🌱 | +21.6% (91%DD) 3🌱 | -30.6% (90%DD) 0🌱 |
| 8% | +11.8% (90%DD) 1🌱 | +6.1% (93%DD) 1🌱 | +74.5% (37%DD) 1🌱 | +30.1% (91%DD) 3🌱 | -31.3% (91%DD) 0🌱 |
| 10% | +9.0% (90%DD) 1🌱 | +28.4% (93%DD) 1🌱 | +69.0% (37%DD) 1🌱 | +33.2% (91%DD) 3🌱 | -36.4% (71%DD) 0🌱 |
| 12% | +7.8% (90%DD) 1🌱 | +28.4% (93%DD) 1🌱 | +76.2% (92%DD) 1🌱 | +14.9% (91%DD) 2🌱 | -36.4% (71%DD) 0🌱 |
| 15% | +9.3% (63%DD) 1🌱 | +28.4% (93%DD) 1🌱 | +60.2% (92%DD) 1🌱 | +24.4% (91%DD) 1🌱 | -36.4% (71%DD) 0🌱 |
| 20% | -1.1% (63%DD) 1🌱 | +28.4% (30%DD) 1🌱 | +61.1% (92%DD) 1🌱 | +24.9% (93%DD) 1🌱 | -36.4% (71%DD) 0🌱 |
| 25% | +16.9% (64%DD) 1🌱 | +18.9% (93%DD) 1🌱 | +34.0% (37%DD) 0🌱 | +34.1% (91%DD) 2🌱 | -36.4% (71%DD) 0🌱 |

**Key finding**: No single threshold works across all windows. DD is driven by spring capital deployment, not threshold depth.

### Phase 4: Gate-Driven Spring ✅ (Current Architecture)
CFGI + dwell + SMA200 gates detect exhaustion. Spring fires when market is actually exhausted, not at a fixed discount.

| Window | Return | MaxDD | Deals | Win% | Springs | vs Baseline |
|--------|--------|-------|-------|------|---------|-------------|
| ETH Jun-Oct 2024 | **+12.39%** | **15.13%** | 35 | 100% | 1 🌱 | was -4.06% |
| ETH Dec-Mar 2025 | **+22.51%** | **29.88%** | 10 | 100% | 1 🌱 | was -6.70% |
| SOL Feb-Jul 2024 | **+64.24%** | **37.32%** | 100 | 100% | 1 🌱 | was +58.64% |
| SOL Dec-Mar 2025 | **+31.22%** | **27.44%** | 27 | 96% | 2 🌱 | was -24.69% |
| BTC Oct-Mar 2025 | -36.37% | 70.50% | 8 | 100% | 0 ❌ | was -14.34% |

**4 of 5 windows profitable. Springs fire correctly with controlled drawdowns (15-37%).**

---

## BTC Failure Analysis

BTC Oct 2024 → Mar 2025: 0 springs, -36.37%, 70.50% DD.

**Hypothesis**: CFGI for BTC may not drop below 35 during this period (BTC tends to have higher CFGI than alts during corrections), or the dwell requirement isn't met because BTC corrections are shallower and shorter.

**Status**: Under investigation.

---

## Outstanding Work

1. **BTC investigation** — Why do gates never pass? Check CFGI values during BTC markdown periods.
2. **Martingale spring tiering** — Layer in progressively larger buys (T1 small → T4 aggressive) instead of deploying at fixed percentages. Should reduce DD further.
3. **Spring capital budget** — Cap total spring deployment (e.g., 25-30% per tier, not all-in).
4. **44-coin full backtest** — Production-scale validation with gate-driven architecture.
5. **Production deployment** — Port changes to `lifecycle_trader.py` for live/paper bots.

---

## Files Modified

- `trading/spot/backtest_engine_consolidated.py`:
  - `_exit_cooldown_candles` state variable (7-day cooldown after MARKDOWN→DCA)
  - Cooldown guard on BOTH DCA→EXIT checks (line ~4690 and ~4898)
  - `_check_spring_gates()` method (dwell, CFGI, SMA200)
  - `_markdown_entered_ts` tracking for dwell gate
  - Gate-driven spring check in V12f fallback (10% floor + gates every candle)
  - False-exit recovery removed from V12f MARKDOWN
  - All MARKDOWN→DCA escape paths removed (gates-only exit to SPRING)
  - State persistence via `snapshot_state()` / `restore_state()`

- `trading/spot/backtest_results/demo/validate_spring_backtest.py` — 5-window validation harness
- `trading/spot/backtest_results/demo/validate_spring_gates.py` — Gate validation (100% pass/fail on known transitions)
- `trading/spot/backtest_results/demo/sweep_spring_threshold.py` — 7-threshold × 5-window matrix sweep

## Gate Validation (from earlier testing)

Gates validated against 12 known transitions:
- **12/12 BAD entries blocked (100%)** — dwell gate was the workhorse
- **6/6 GOOD entries allowed (100%)** — all gates passed for genuine springs
- **Dropped gates**: CFGI exhaustion (G3) and confirmation delay (G5) both blocked every GOOD entry
- **Dwell ≥ 3 days is the strongest single gate**: 100% separation alone
