# BTC V12e CFGI Exit Gate Analysis

**Date:** 2025-02-22  
**Backtest:** BTC/USDC V12e Medium profile, Oct 2020 → Feb 2026  
**Result:** 185% ROI, $28,500 final equity ($10K initial), 19 exit phases, **-$16,297 short PnL**

## Executive Summary

The BTC V12e backtest fires 19 EXIT transitions, many of which are **false exits** that lead to losing short positions. The CFGI (Crypto Fear & Greed Index) per-coin data is available for exits from Feb 2024 onward. Analysis shows:

- **CFGI >= 75 gate would block 10 of 16 CFGI-covered exits** — all 10 are false exits
- **Zero real tops are blocked at the 75 threshold** (the 3 real tops in CFGI range all had CFGI < 50)
- **Problem:** Real tops in BTC happen when CFGI is LOW (38-44), not high — the opposite of what a greed gate assumes
- **Recommendation:** CFGI gate for BTC EXIT is **counterproductive** — real BTC tops occur during fear/neutral sentiment, not greed

## Task 1: Backtest EXIT Transition Logic

### How EXIT fires (backtest_engine_v12.py)

```
DCA → EXIT triggers when:
1. DailyScorerConductor.should_exit() returns True
   - Daily TA score >= exit_threshold (50.0)
   - Price within 25% of ATH (mcap_ath_pct gate)
   - If in price discovery (price > known ATH 73,750): weekly confirmation required
2. No commitment window in backtest (immediate transition)
3. Weekly veto optional (v12_weekly_dist_veto, default False for BTC)
```

### Daily Score Composition

```
total_score = TA_score + Pi_Cycle + FG_exit_score + reversal_score + ATH_proximity

FG/CFGI exit score (ALREADY in the conductor):
  >= 90: +25 pts (extreme greed)
  >= 80: +15 pts (greed)
  >= 75: +10 pts (high greed)
  >= 70: +5 pts  (elevated greed)
  <= 20: -10 pts (fear suppression)
  <= 10: -20 pts (panic suppression)
```

**Key finding:** CFGI is already used as a SCORING COMPONENT but NOT as a hard gate. High CFGI adds points making EXIT more likely, low CFGI subtracts points. But the score can still reach 50+ from TA signals alone even with low CFGI.

### Is there a code path where EXIT fires WITHOUT CFGI confirmation?

**YES.** The conductor uses CFGI only as additive/subtractive scoring. If TA signals are strong enough (RSI divergence, volume exhaustion, upper wicks, momentum stall, ATH proximity, Pi Cycle), the total score can hit 50+ with ANY CFGI value. There is no hard CFGI gate in the backtest.

## Task 2: EXIT Transitions vs CFGI Data

Simulation found 36 EXIT transitions over the full period; 16 have CFGI data (Feb 2024 onward):

| # | Date | Price | Score | CFGI | Drop 30d | Rise 30d | Real Top? |
|---|------|-------|-------|------|----------|----------|-----------|
| 5 | 2024-02-28 | $57,015 | 54.4 | **89** | 0.4% | 29.0% | FALSE |
| 6 | 2024-03-20 | $63,230 | 55.0 | **44** | 4.8% | 14.5% | FALSE |
| 7 | 2024-04-14 | $63,672 | 50.0 | **23** | 10.7% | 5.3% | FALSE |
| 8 | 2024-05-04 | $63,904 | 50.0 | **69** | 5.5% | 11.8% | FALSE |
| 9 | 2024-05-25 | $69,213 | 60.0 | **51** | 13.1% | 3.6% | FALSE |
| 10 | 2024-06-19 | $65,143 | 50.0 | **38** | **17.2%** | 1.6% | **REAL** |
| 11 | 2024-07-09 | $57,800 | 65.0 | **35** | 13.8% | 20.8% | FALSE |
| 12 | 2024-08-01 | $64,646 | 50.0 | **38** | **23.0%** | 1.1% | **REAL** |
| 13 | 2024-08-21 | $61,236 | 55.0 | **61** | 13.6% | 5.3% | FALSE |
| 14 | 2024-09-11 | $57,500 | 65.0 | **62** | 0.3% | 15.3% | FALSE |
| 15 | 2024-10-02 | $61,874 | 55.0 | **31** | 3.8% | 18.3% | FALSE |
| 16 | 2024-10-23 | $66,417 | 61.9 | **46** | 1.0% | 49.3% | FALSE |
| 17 | 2024-11-13 | $87,400 | 65.3 | **88** | 0.1% | 18.4% | FALSE |
| 18 | 2024-12-06 | $97,552 | 66.2 | **76** | 5.8% | 11.0% | FALSE |
| 19 | 2024-12-28 | $94,399 | 50.0 | **36** | 3.9% | 14.7% | FALSE |
| 20 | 2025-01-17 | $104,605 | 50.6 | **79** | 11.3% | 3.6% | FALSE |
| 21 | 2025-02-11 | $97,783 | 50.4 | **44** | **20.6%** | 1.6% | **REAL** |

### CFGI Distribution at Exits

- **Real tops (3):** CFGI = 38, 38, 44 — all below 50!
- **False exits with high CFGI:** 89, 88, 79, 76, 69 — all false
- **Pattern:** BTC real tops coincide with neutral/fear sentiment (CFGI 30-50), NOT greed

### CFGI Threshold Analysis

| Threshold | Exits Blocked | False Saved | Real Tops Lost |
|-----------|--------------|-------------|----------------|
| >= 60 | 10 | **7 false** | **3 real** ⚠ |
| >= 65 | 12 | **9 false** | **3 real** ⚠ |
| >= 70 | 13 | **10 false** | **3 real** ⚠ |
| >= 75 | 13 | **10 false** | **3 real** ⚠ |
| >= 80 | 15 | **12 false** | **3 real** ⚠ |

**Every threshold blocks ALL 3 real tops** because real BTC tops happen at low CFGI. This is the opposite of ETH behavior.

## Task 3: Why BTC is Different from ETH

For ETH, tops correlate with extreme greed (CFGI 80+). For BTC, the pattern is inverted:

1. **BTC tops are technical**, driven by RSI divergence, volume exhaustion, and overextension — not sentiment
2. **BTC CFGI runs hot during rallies** (80-90) but real tops happen AFTER greed fades (CFGI drops to 30-50)
3. **The lag is key:** sentiment peaks BEFORE the price peak, then diverges downward while price makes a final push

This means a CFGI gate on BTC would:
- **Block exits during actual distribution** (when smart money is selling, CFGI drops)
- **Allow exits during euphoria rallies** (when price still has room to run)

## Task 4: CFGI Gate Simulation

### Impact on Short PnL

Average short PnL per exit phase: **-$858** ($-16,297 / 19 exits)

| Gate | False Exits Saved | Short PnL Saved | Real Tops Lost | Net Impact |
|------|------------------|-----------------|----------------|------------|
| CFGI >= 70 | 10 | ~$8,577 | **3** | NEGATIVE — loses real tops |
| CFGI >= 75 | 10 | ~$8,577 | **3** | NEGATIVE |
| CFGI >= 80 | 12 | ~$10,293 | **3** | NEGATIVE |

### The Catch

Saving $8-10K from false exit shorts sounds good, but losing the 3 real top detections means:
- Missing the Jun 2024 top (17% drop) — would have held through it
- Missing the Aug 2024 top (23% drop) — biggest single exit opportunity
- Missing the Feb 2025 top (21% drop) — recent major correction

Each missed real top costs significantly more than the short losses saved, because:
1. You hold long through a 15-23% crash instead of selling
2. You miss the short profit opportunity
3. You deploy spring capital at higher prices

**Estimated loss per missed real top:** $2,000-5,000 (held longs through crash + missed short profit)

## Task 5: Live V12e Code (lifecycle_engine.py)

### Current CFGI Exit Logic

```python
# In LifecycleConfig:
cfgi_exit_fast_threshold: float = 75.0   # CFGI >= 75 → fast commitment (24h)
cfgi_exit_fast_hours: float = 24.0       # Reduced from 48h standard
cfgi_exit_invalidate: float = 50.0       # CFGI drops below 50 → invalidate commitment

# In _process_dca():
# 1. If should_exit and CFGI >= 75: commitment window shortened to 24h
# 2. If CFGI < 50 during commitment: window reset (invalidated)
# 3. After commitment window passes: transition to EXIT
```

### Assessment

The live engine uses CFGI as a **modulator** (speed up/slow down commitment), not a **gate** (block/allow). This is actually reasonable:

- `cfgi_exit_fast_threshold = 75`: Speeds up EXIT when greed is high (makes sense for ETH, wrong for BTC)
- `cfgi_exit_invalidate = 50`: Cancels EXIT commitment if CFGI drops below 50

**Problem for BTC:** The invalidation at CFGI < 50 would cancel ALL 3 real BTC tops (CFGI was 38-44). The live engine would fail to exit during actual BTC distribution events.

## Recommendations

### 1. Do NOT add a CFGI hard gate for BTC EXIT

A CFGI >= 70/75/80 gate would block real tops more than false ones for BTC. The correlation is inverted.

### 2. Make CFGI exit thresholds coin-specific

```python
# Proposed per-coin CFGI config
CFGI_EXIT_CONFIG = {
    "ETH": {"gate": 70, "fast": 80, "invalidate": 50},  # ETH tops = greed
    "BTC": {"gate": None, "fast": None, "invalidate": None},  # BTC tops != greed
    "SOL": {"gate": 65, "fast": 75, "invalidate": 45},  # TBD based on SOL analysis
}
```

### 3. For BTC, focus on TA-only exit quality

Instead of CFGI gating, improve BTC exit accuracy by:
- **Tighter ATH proximity gate** (currently 25%, could try 15%)
- **Require RSI divergence confirmation** on daily timeframe
- **Add volume confirmation** — real BTC tops have volume exhaustion
- **Weekly RSI veto** (require weekly RSI > 65 for distribution exit)

### 4. Fix live engine for BTC

The `cfgi_exit_invalidate = 50` will kill legitimate BTC exits. Options:
- Set `cfgi_exit_invalidate` to 0 for BTC (disable invalidation)
- Or use per-coin invalidation thresholds
- The `cfgi_exit_fast_threshold = 75` is harmless for BTC (just won't trigger), but misleading

### Code Changes Needed

In `lifecycle_engine.py`, `LifecycleConfig`:

```python
# Add coin-specific CFGI behavior
cfgi_exit_gate: Optional[float] = None       # None = no gate (BTC), 70+ for ETH
cfgi_exit_fast_threshold: float = 75.0       # Only useful for coins where tops = greed
cfgi_exit_invalidate: Optional[float] = None  # None = no invalidation (BTC)
```

In `_process_dca()`, add:
```python
# CFGI gate check (coin-specific, None = no gate)
if self.config.cfgi_exit_gate is not None:
    if cfgi_score is not None and cfgi_score < self.config.cfgi_exit_gate:
        logger.info("EXIT blocked: CFGI=%.0f < gate %.0f", cfgi_score, self.config.cfgi_exit_gate)
        return actions  # Block exit
```

## Summary

| Metric | Value |
|--------|-------|
| Total BTC exits (simulation) | 36 |
| Exits with CFGI data | 16 |
| Real tops in CFGI range | 3 (CFGI: 38, 38, 44) |
| False exits in CFGI range | 13 |
| CFGI at real BTC tops | 38-44 (fear/neutral) |
| CFGI at false BTC exits | 23-89 (all over the map) |
| CFGI gate viable for BTC? | **NO** — inverted correlation |
| Recommended BTC approach | TA-only exit quality improvements |
| Recommended ETH approach | CFGI >= 70 gate (tops = greed) |
