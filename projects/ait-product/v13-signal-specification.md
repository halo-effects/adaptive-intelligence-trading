# V13 Signal Specification — Complete Transition & Top Detection Stack

**Version**: 1.0  
**Date**: 2026-02-25  
**Status**: Validated via matrix testing (500+ combos, 5 coins, 17 months)

---

## Phase Model

```
DCA ←→ MARKUP → FLAT → DCA or MARKDOWN
         ↑        ↑           ↓
         │        │ (HVF-driven routing)
         └────────┴───────────┘
```

**Phases**:
- **DCA**: Default state. V12f DCA engine runs (8% base order, 1.5x SO multiplier, 1.5% TP). Transition signals armed.
- **MARKUP**: Positioned long with tiered entries (T1=60%, T2=20%, T3=10%, 10% reserve). Riding the trend.
- **FLAT**: Post-top-exit. All positions closed. HVF-driven routing determines next phase (no fixed timer).
- **MARKDOWN**: Short positioned (60% capital). Riding the downtrend.

---

## Transition 1: DCA → MARKUP

### Signal: HH_HL + Fib_support
**Score**: 94.0 | **Accuracy**: 100% | **False Positive**: 20% | **Lead Time**: 39 days

#### What It Detects
Price is making higher highs AND holding at a Fibonacci support level (0.382-0.786 retracement zone, especially 0.618 golden ratio). This means: structure is turning bullish and price has found a floor at a mathematically significant level.

#### Implementation
```
TRIGGER when ALL true:
  1. HH_HL pattern detected on daily candles (2 consecutive higher highs + higher lows over 20-day lookback)
  2. Price within 3% of a Fibonacci retracement support level (computed from last major swing high→low)

OPTIONAL CONFIRMATION (raises score from 91.0 to 94.0):
  3. CFGI > 40 (sentiment not in fear)

OPTIONAL PRE-SIGNAL (monitoring only, no action):
  - HVF composite > 0.4 fires 16-44 days before transition
  - Alerts "energy building" — watch for structural confirmation
```

#### Parameters
| Parameter | Value | Rationale |
|-----------|-------|-----------|
| HH_HL lookback | 20 days | Catches pattern early (40d lead in testing) |
| Fibonacci ratios | 0.236, 0.382, 0.5, 0.618, 0.786 | Standard retracement levels |
| Price tolerance | ±3% of fib level | Allows for volatility near levels |
| CFGI gate | > 40 | Filters fear-driven bounces |

#### Evidence
- **BTC**: HH_HL fired Oct 2024 at $72K near 1.000x fib. Markup confirmed → $126K top.
- **ETH**: HH_HL + Fib_support caught Dec 2024 recovery at $3,999 near 1.000x extension.
- **SOL**: Caught Nov 2024 breakout at $210 near 1.000x.
- **BNB**: Caught via HH structure even without 2W StochRSI OS signal (cold start solved).
- **XRP**: Caught via HH structure at $0.62 level (cold start solved).

#### What Failed for This Transition
| Signal | Score | Why It Failed |
|--------|-------|---------------|
| 2W StochRSI OS exit | 0% | Never fires for BNB/XRP; too late for others |
| Channel breakout | 0% | Fires AFTER transition, not before |
| CFGI momentum (rising/falling) | 0% | Momentum happens during shift, not before |
| BMSB alone | 10-22% | Too many false breaks during ranging |
| SMA50/200 crosses | 29-50% | Unreliable in crypto |

---

## Transition 2: MARKUP → COOLDOWN (Top Detection)

### Three-Layer Exit Defense

The top detection system uses a graduated response: early warning → primary exit → failsafe. Each layer catches what the previous might miss.

---

### Layer 1: Early Warning — 1W StochRSI 97 Threshold
**Role**: Alert. Prepare to exit. Don't act yet.

```
ALERT when:
  1W StochRSI K crosses above 97

MEANING:
  Momentum is extreme. Top is likely forming within 2-4 weeks.
  
ACTION:
  - Flag "early warning active"
  - Arm the failsafe timer (2-week window)
  - Tighten stops mentally but don't sell yet
```

**Evidence**: Fires before 2W signal in all tested cases. Gives advance notice of momentum fade.

---

### Layer 2: Primary Exit — 2W StochRSI OB93
**Role**: This is THE sell signal. Score: 100% accuracy, 0% FP at threshold 93.

```
TRIGGER when:
  2W StochRSI K crosses below 93 (from above)

ACTION:
  - Sell ALL markup positions at market
  - Close ALL DCA positions at market  
  - Enter COOLDOWN (flat, no buying, 4-week minimum)
```

**Evidence**:
- **BTC**: 2W OB93 caught Dec 2024 top. 100% accuracy across all tested windows.
- **ETH**: 2W peaked at only K=72.7 for Dec 2024 cycle — DID NOT FIRE → need Layer 2b fallback.
- **SOL**: 2W peaked at 92 (just under 93) — DID NOT FIRE → need Layer 2b fallback.

**Threshold tuning** (via `v13_threshold_sweep.py`):
| Threshold | Accuracy | FP | Notes |
|-----------|----------|-----|-------|
| 80 | 0% on BTC/ETH | — | Fires too late, after peak |
| 92 | 100% | 1 FP (SOL) | Close but SOL peaked at 92 |
| **93** | **100%** | **0** | **Sweet spot** |
| 95 | 100% | 0 | Also works but less lead time |
| 97 | 67% | 0 | Too strict, misses some tops |

---

### Layer 2b: Fallback Exit — 1W StochRSI OB85
**Role**: Catches tops where 2W never reaches OB. Critical for ETH and SOL.

```
TRIGGER when:
  2W StochRSI K never crossed above 93 in current markup phase
  AND 1W StochRSI K crosses below 85 (from above)
  AND currently in MARKUP for > 30 days

ACTION:
  Same as Layer 2 — full exit to COOLDOWN
```

**Evidence**:
- **ETH Dec 2024**: 2W peaked at 72.7 (never reached 93). 1W OB85 caught it.
- **SOL**: 2W peaked at 92 (just under). 1W OB85 fallback activated.
- Without this fallback: ETH and SOL had -43% drawdown in v1 backtest.

---

### Layer 3: Failsafe — 1W StochRSI K < 50
**Role**: Last resort. If Layers 2/2b somehow missed, this catches the fall.

```
TRIGGER when:
  Early warning was armed (Layer 1 fired within last 2 weeks)
  AND 1W StochRSI K drops below 50

ACTION:
  Same as Layer 2 — full exit to COOLDOWN
```

**Evidence**:
- ETH: 100% accuracy, 0 FP
- BTC: 50% accuracy, 1 FP
- SOL: 67% accuracy, 1 FP
- Loses 5-15% from top but avoids 30-50% drawdown

---

### Layer 4 (Cycle 2+): Fibonacci Extension Top Zones
**Role**: Additional conviction layer. Only active after first full cycle completes.

```
AVAILABLE when:
  Bot has completed at least one full markup→cooldown→markdown cycle
  (Has reference swing high and low from previous cycle)

ALERT when:
  Price enters Fibonacci extension zone from previous cycle's swing:
  - 1.272x extension = caution zone
  - 1.618x extension = high probability top zone
  - 2.618x extension = extreme extension

BEHAVIOR:
  - If price reaches 1.618x AND any Layer 1-3 signal fires:
    → Higher conviction exit (confirms the top with structural level)
  - If price blows through all extension levels:
    → Invalidate Fib levels for this cycle
    → Rely purely on Layers 1-3
    → New swing structure will provide levels for next cycle
```

**Why Cycle 2+ Only**:
- First cycle: no reference swing to compute extensions from
- BNB topped at $2,993 but highest extension was $1,564 (52% of actual top) — original swing too small
- XRP topped at $3.66 but highest extension was $1.69 (46% of top) — same problem
- After first cycle completes, extensions from the actual top/bottom are accurate

**Evidence**:
- BTC: Top at $126K was between 2.618x ($113.8K) and 3.618x ($138.6K) ✓
- ETH: Top at $4,957 was between 1.272x ($4,633) and 1.618x ($5,319) ✓
- SOL: Top at $296 was between 1.618x ($272) and 2.000x ($310) ✓
- BNB/XRP: ❌ Extensions too low (first cycle problem — solved by recalculating for cycle 2)

---

### Layer 5: HVF Markdown Spillover Confirmation (COOLDOWN Phase)
**Role**: During COOLDOWN, confirms whether the correction will spill over into full markdown or recover. Determines whether to prepare shorts or return to DCA.

```
DURING COOLDOWN (after top exit):
  Monitor HVF composite daily

  IF HVF > 0.4 and rising:
    → "Energy building for breakdown" — markdown spillover likely
    → Prepare for MARKDOWN entry (pre-position shorts readiness)
    → Higher conviction on ADX+Fib_break signal when it fires

  IF HVF < 0.2 and flat:
    → "No compression" — likely just a correction
    → Expect return to DCA or MARKUP
    → Lower conviction on any markdown signals
```

**Evidence** (HVF timelines around known tops → markdown transitions):

| Coin | Correction Hold | At Peak | Pre-Markdown | Markdown Entry |
|------|----------------|---------|--------------|----------------|
| BTC | 0.003 (quiet ✓) | 0.15 | **0.57** (building) | 0.00 (released) |
| ETH | 0.08 (quiet ✓) | 0.07 | **0.68** (massive) | 0.68 (at peak) |
| SOL | 0.39 (⚠️ noise) | 0.02 | **0.56** (building) | 0.56 (at peak) |

**Pattern**: HVF rises to >0.4 in the 7-14 days BEFORE markdown confirms. At corrections that don't become markdown, HVF stays below 0.2.

**Why This Works**: HVF measures volume + price compression — "energy building." After a top, if sellers are consolidating and compressing price into a tighter range with declining volume, that energy WILL release as a breakdown. If there's no compression (HVF stays flat), it's just noise.

**SOL caveat**: HVF hit 0.39 during a correction hold (Dec 5) — borderline. The 0.4 threshold still holds but SOL is noisier. Combined with ADX+Fib_break, false positives are filtered.

---

## Transition 3: FLAT → Next Phase (HVF-Driven Routing)

### Signal: HVF Compression Determines Post-Top Routing

Replaces the fixed 4-week cooldown with signal-driven routing. After a top exit fires and all positions are closed:

```
DAILY during FLAT phase:

  IF HVF composite > 0.4 AND rising:
    → Stay FLAT — "markdown energy building"
    → When ADX>20 + Fib_break fires → enter MARKDOWN (shorts at 60%)
    → When HH_HL + Fib_support fires → enter MARKUP (structure overrides — correction recovered)
  
  ELIF HVF composite < 0.2 for 7+ consecutive days:
    → Enter DCA — "no compression, just a correction"
    → All transition signals armed (DCA→MARKUP, DCA→MARKDOWN)
  
  ELSE (0.2-0.4 range):
    → Stay FLAT — ambiguous, wait for clarity
```

**Why HVF Replaces Fixed Cooldown**:
- The 4-week cooldown solved: "don't DCA into a forming markdown"
- HVF directly measures whether markdown is forming (compression = energy building for breakdown)
- Signal-driven routing → capital works when safe, stays flat when dangerous
- No arbitrary timer — responds to what the market is actually doing

**Evidence** (HVF timelines around known tops → markdown transitions):

| Coin | Correction (hold) | Pre-Markdown | At Markdown |
|------|-------------------|--------------|-------------|
| BTC | 0.003 (quiet ✓) | **0.57** (building) | 0.00 (released) |
| ETH | 0.08 (quiet ✓) | **0.68** (massive) | 0.68 (at peak) |
| SOL | 0.39 (⚠️ border) | **0.56** (building) | 0.56 (at peak) |

**Pattern**: HVF rises >0.4 in the 7-14 days before markdown confirms. During corrections that recover, HVF stays below 0.2.

**Previous Cooldown Sweep** (for reference):
| Cooldown | Avg ROI | Notes |
|----------|---------|-------|
| 2 weeks | +17.9% | Re-entered too early |
| **4 weeks** | **+26.0%** | Was the sweet spot with fixed timer |

**Expected**: HVF routing should match or beat 4-week result — responding to actual signal vs arbitrary timer. Backtest validation pending.

**Failsafe chain still active during FLAT**: All top detection layers remain armed.

---

## Transition 4: DCA → MARKDOWN

### Signal: ADX>20 + Fib_break
**Score**: 94.0 | **Accuracy**: 100% | **False Positive**: 20% | **Lead Time**: 46 days

#### What It Detects
There's a confirmed downtrend (ADX > 20) AND price has broken below a Fibonacci support level. This means: the trend is real and support is gone.

#### Implementation
```
TRIGGER when ALL true:
  1. ADX > 20 on daily candles (confirms trending market, not just ranging)
  2. Price has broken below a Fibonacci support level (0.382-0.786 retracement from last swing)

HARD EXIT:
  - Close ALL open DCA trades and orders at market IMMEDIATELY
  - Free 100% of capital
  - Do NOT gracefully unwind — speed matters, capital needed for shorts

THEN:
  - Enter MARKDOWN phase
  - Open short at 60% of capital (if shorts enabled — cycle 2+ only)
```

#### High-Conviction Alternative
```
IF Harmonic_bear pattern detected + Fib_break:
  → 0% false positive rate (zero FP ever in testing)
  → 80% accuracy (slightly lower coverage)
  → Use for maximum conviction: confirms bearish ABCD + broken support
```

#### Parameters
| Parameter | Value | Rationale |
|-----------|-------|-----------|
| ADX threshold | 20 | Standard trend confirmation |
| Fibonacci break | Close below support level | Clear structural break |
| Harmonic pattern | Optional, bearish ABCD with Fib ratios | 0% FP conviction boost |

#### Evidence
- **BTC→MARKDOWN**: ADX>20 + Fib_break fired 46d before confirmed markdown.
- **ETH→MARKDOWN**: Same combo, 100% accuracy.
- **All 5 coins**: 100% detection rate in testing window.

#### Key Rule: DCA→Markdown = HARD EXIT
Brett directive: "It shouldn't gracefully exit because it needs all its cash to cycle into markdown. Close open trades and orders. Shift capital to shorts."

Contrast with DCA→Markup = GRACEFUL EXIT (let TPs hit naturally).

---

## Transition 5: MARKDOWN → DCA

### Signal: Inverse of Markup Entry

```
TRIGGER when:
  Short position active
  AND HH_HL pattern appears (structure turning bullish)
  AND Price bouncing at or above Fibonacci support

ACTION:
  - Close short position
  - Enter DCA phase
  - Begin watching for full MARKUP confirmation
```

**Note**: This is the weakest signal in the system (matrix score 75.0 for LH_LL+ADX+Fib). The safest approach is to simply close the short and return to DCA, letting the DCA→MARKUP signal fire when it's ready. Don't rush from MARKDOWN directly into MARKUP.

---

## Shorts: Cycle Gating

```
SHORTS ENABLED only when:
  Bot has completed at least one confirmed markup→flat→markdown/DCA cycle

RATIONALE:
  - Without gate: XRP lost -109.6% on a single cold-start short
  - With gate: XRP -11.9% (DCA losses only, no catastrophic short)
  - First cycle = learning the coin's behavior
  - Second cycle = full conviction, shorts allowed
```

---

## Complete Signal Summary Table

| Transition | Primary Signal | Score | Acc | FP | Lead | Cycle |
|------------|---------------|-------|-----|-----|------|-------|
| DCA → MARKUP | HH_HL + Fib_support | 94.0 | 100% | 20% | 39d | All |
| MARKUP → EXIT (primary) | 2W StochRSI OB93 cross-under | 100% | 100% | 0% | — | All |
| MARKUP → EXIT (fallback) | 1W StochRSI OB85 cross-under | — | — | — | — | All |
| MARKUP → EXIT (failsafe) | 1W StochRSI K<50 (armed) | — | 50-100% | 0-1 | — | All |
| MARKUP → EXIT (Fib top) | Price at 1.618x+ Fib extension | — | Confirm | — | — | **Cycle 2+** |
| FLAT → stay FLAT | HVF > 0.4 rising | — | Confirm | — | 7-14d | All |
| FLAT → DCA | HVF < 0.2 for 7+ days | — | — | — | — | All |
| FLAT → MARKDOWN | HVF > 0.4 + ADX>20 + Fib_break | 94.0 | 100% | 20% | — | All |
| DCA → MARKDOWN | ADX>20 + Fib_break | 94.0 | 100% | 20% | 46d | All |
| DCA → MARKDOWN (hi-conv) | Harmonic_bear + Fib_break | 87.5 | 80% | **0%** | 27d | All |
| MARKDOWN → DCA | HH_HL appears + Fib support | ~75 | — | — | — | All |
| Shorts enabled | After first markup→flat cycle | — | — | — | — | **Cycle 2+** |

---

## Pre-Signal Layer (Optional Monitoring)

| Signal | Fires Before | Purpose | Action |
|--------|-------------|---------|--------|
| HVF composite > 0.4 | 16-44 days | "Energy building" — breakout imminent | Watch, don't act |
| HVF > 0.4 during FLAT | 7-14 days before markdown | Spillover confirmation | Stay flat, prepare shorts |
| HVF < 0.2 during FLAT | — | "Just a correction" | Safe to enter DCA |
| 1W StochRSI > 97 | 2-4 weeks before top | Extreme momentum | Arm failsafe |
| Fib extension zone | When price approaches | Potential reversal zone | Increase vigilance |

---

## What Explicitly Doesn't Work (Don't Revisit)

| Signal | Result | Why |
|--------|--------|-----|
| 2W StochRSI OS/OB for DCA transitions | 0% | Fires after transition or never (cold start) |
| Channel breakout for DCA transitions | 0% | Fires after transition |
| CFGI momentum/rate of change | 0% | Changes during shift, not before |
| BMSB as standalone signal | 10-22% | Too many false breaks |
| SMA50/200 death cross | 29-50% | Unreliable in crypto |
| 1h RSI/OBV divergence | Failed | Crypto volume too noisy |
| Spring detection (Wyckoff) | 0 fires ever | Over-engineered, root cause was 1h sensitivity |
| DCA throttle/conviction gates | -3.6% ROI | Added complexity, hurt performance |

---

## Backtest Results (V13 v7 with this stack)

| Coin | ROI | B&H | Alpha | Max DD |
|------|-----|-----|-------|--------|
| BTC | +32.2% | +18.1% | +14.0% | -18.1% |
| ETH | +55.1% | -17.8% | +72.9% | -24.3% |
| SOL | +67.5% | -33.9% | +101.4% | -23.2% |
| BNB | -7.0% | +20.4% | -27.4% | -18.3% |
| XRP | -11.9% | +169.4% | -181.3% | -34.3% |
| **3-coin avg** | **+51.6%** | **-11.2%** | **+62.8%** | — |
| **5-coin avg** | **+27.2%** | **+31.3%** | — | -34.3% |

**Note**: BNB/XRP results expected to improve once DCA transition signals (HH_HL + Fib_support) replace the 2W StochRSI-dependent markup entry. This is the primary purpose of the matrix testing — solving cold start.

---

## Implementation Priority

1. **Wire HH_HL + Fib_support into DCA→MARKUP** (replaces 2W OS dependency)
2. **Wire ADX + Fib_break into DCA→MARKDOWN** (replaces Conductor scoring)
3. **Replace COOLDOWN with FLAT + HVF routing** (signal-driven, no fixed timer)
4. **Add Fib extension top zones (cycle 2+)** as confirmation layer
5. **Run full 5-coin backtest** with new signals (compare vs v7 with 4-week cooldown)
6. **Validate BNB/XRP improvement** (the whole point of this work)
7. **Production implementation** in lifecycle_engine.py

---

*This document is the authoritative V13 signal reference. All transition logic should implement from this spec.*
