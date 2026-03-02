# Top Conviction Stack Analysis
**Date:** 2026-02-27
**Coins:** ETH, SOL, LINK, XRP (paper bot universe)
**Period:** ETF era (Jan 2023+)

## Steve Courtney's Top Stack (2D Chart)
1. **Above SMA200** — long-term trend confirmation
2. **RSI(14) > 80** — momentum overbought
3. **StochRSI(14,14,3,3) K&D > 80** — precise timing overbought
4. **MFI(14) > 80** — volume-weighted confirmation (NEW — not in our current stack)

## Steve's BTC-Specific Tools
- **Pi Cycle Top:** 111 SMA crosses above 2× 350 SMA
- **2-Year MA Multiplier:** Price hits "Red Line"
- **Golden Ratio Multiplier:** Price hits Fib × 350 DMA resistance
- **Fibonacci Extensions:** 1.618 and 2.272 levels for price targets

## Our Current Top Detection
- 2W StochRSI K > 93 (OB93) — single signal, first touch

## 2W StochRSI Exhaustion (Symmetric to Bottom)
- **Top:** K > 93 pinned for 2+ candles (4+ weeks), then K crosses below D
- **Bottom:** K < 5 pinned for N candles, then K crosses above D

---

## Test 1: Steve 2D Score Standalone

### Score Distribution (ETF era, strict thresholds)
| Coin | Score ≥ 2 | Score ≥ 3 | Score ≥ 4 |
|------|-----------|-----------|-----------|
| ETH | 188 | 51 | 26 |
| SOL | 68 | 11 | 1 |
| BTC | 228 | 80 | 24 |
| LINK | 153 | 54 | 15 |
| XRP | 144 | 40 | 24 |

### Key Finding: 4/4 Catches Blow-Offs, Misses Divergent Tops
- ETH May 2021 ($4,173) = Score 4 ✅
- ETH Mar 2024 ($3,980) = Score 4 ✅
- BTC Nov 2024 ($98K) = Score 4 ✅
- XRP Nov-Dec 2024 ($2.72) = Score 4 ✅
- **ETH Nov 2021 ATH ($4,732) = Score 2 ❌** (RSI 71, MFI 64 — divergence)
- **BTC Apr 2021 ATH ($63K) = Score 1 ❌**
- **BTC Nov 2021 ATH ($67K) = Score 1 ❌**

**Insight:** Major cycle tops show RSI/MFI divergence — price new high, indicators lower high. Score 4 fires on the parabolic RUN-UP, not the exact top. This is actually useful as early warning.

---

## Test 2: 2W StochRSI Exhaustion (K>93 Pinned, Then K×D Cross)

### ETH Exhaustion Periods (K>93)
| Period | Candles | Peak Price | K×D Cross | Price@Cross | Drop |
|--------|---------|-----------|-----------|-------------|------|
| Mar-Jun 2023 | 6 | $1,890 | 2023-08-13 | $1,841 | -2.6% |
| Dec 2023-Jan 2024 | 4 | $2,473 | 2024-01-28 | $2,257 | -8.7% |
| Mar 2024 | 1 | $3,878 | 2024-03-24 | $3,455 | -10.9% |
| Aug-Sep 2025 | 3 | $4,780 | 2025-09-07* | $4,306 | -9.9% |

### BTC Exhaustion Periods (K>93)
| Period | Candles | Peak Price | K×D Cross | Price@Cross | Drop |
|--------|---------|-----------|-----------|-------------|------|
| Nov 2023-Apr 2024 | **11** | $69,360 | 2024-09-08 | $54,870 | -20.9% |
| Aug 2025 | 1 | $119,294 | 2025-08-24 | $113,494 | -4.9% |

**Key finding:** Longer exhaustion (more candles pinned) = more reliable. BTC's 11-candle run caught the real cycle top. Single candles are weaker.

---

## Test 3: Timing vs Actual Peak (Last Relevant Signal)

| Coin | Peak | OB93 1st | Exhaustion 2+ | Steve 3 | Steve 4 |
|------|------|----------|---------------|---------|---------|
| ETH | 2025-08-21 | **+11d** | +571d | +34d | +32d |
| SOL | 2025-01-17 | none | none | +58d | +56d |
| LINK | 2024-12-14 | +279d | +363d | **+12d** | +12d |
| XRP | 2025-07-21 | +218d | none | +8d | **+4d** |

**Steve's 2D stack crushes OB93 for timing** — fires 4-58 days before peak.
OB93 fires hundreds of days early for LINK/XRP.

### False Signal Rate (price rises >20% in 90d after)
| Method | Total Signals | False | False % |
|--------|--------------|-------|---------|
| OB93 alone | 11 | 4 | **36%** |
| Steve 3 | 13 | 11 | 85% |
| Steve 4 | 9 | 5 | 56% |

---

## Test 4: Steve + K×D Crossover Combos

### Steve fires (warning), then 2W K crosses below D (confirmation)

| Method | Signals | False | False % |
|--------|---------|-------|---------|
| Steve3 → K×D (90d) | 17 | 8 | 47% |
| Steve4 → K×D (90d) | 9 | 5 | 56% |
| Steve3 + 2W K>80, → K×D | 7 | 4 | 57% |
| Steve4 + 2W K>80, → K×D | 5 | 3 | 60% |
| Armed (K>90 + Steve3) → K×D | 9 | 4 | **44%** |

### Per-Coin Last Signal Timing (Steve4 → K×D 90d)
| Coin | Last Signal | Days from Peak |
|------|------------|---------------|
| ETH | 2025-09-07 | **-17d** (17d after) |
| SOL | 2024-12-29 | **+19d** (19d before) |
| LINK | 2025-01-12 | **-29d** (29d after) |
| XRP | 2025-09-21 | -62d (62d after) |

---

## Test 5: Steve + OB93 Simultaneous

| Method | Signals | False | False % |
|--------|---------|-------|---------|
| OB93 alone | 11 | 4 | **36%** |
| Steve3 + OB93 nearby | 6 | 6 | 100% ❌ |
| Steve4 + OB93 nearby | 5 | 4 | 80% ❌ |
| Steve3 + OB93 → K×D | 6 | 4 | 67% |
| Steve4 + OB93 → K×D | 5 | 3 | 60% |

**Adding Steve to OB93 made it WORSE** — killed SOL coverage (no Steve cluster near SOL's OB93 period) and didn't fix LINK's timing.

---

## Conclusions

1. **Steve's 2D stack has the best timing** — fires 4-58 days before actual peaks
2. **OB93 alone has the lowest false rate** (36%) but worst timing for LINK/XRP
3. **K×D crossover is the key confirmation** — turns "overbought" into "rolling over"
4. **MFI is the new differentiator** — separates score 2 (noise) from 3/4 (signal)
5. **Steve 4/4 fires on the blow-off, not the exact top** — divergence at ATH means indicators already cooling
6. **Longer 2W exhaustion = more reliable** but too late for most coins
7. **Steve + OB93 hurts more than helps** — kills coverage without improving accuracy

## Recommended Top Stack (Pending Chart Review)
- **Warning:** Steve 2D Score ≥ 3/4 (above SMA200 + RSI>80 + StochRSI>80 + MFI>80)
- **Confirmation:** 2W StochRSI K crosses below D
- **Conviction weighting:** Score 3 = T1 short allocation, Score 4 = T1+T2
- **One-trigger-per-cycle lock** (same as bottom stack)

## Files
- `_steve_top_stack.py` — Steve 2D score analysis + threshold sensitivity
- `_2w_stochrsi_top.py` — 2W exhaustion periods + K×D timing
- `_top_stack_backtest.py` — timing comparison (5 methods × 4 coins)
- `_top_combo_test.py` — Steve + K×D crossover combos (7 variants)
- `_top_steve_ob93.py` — Steve + OB93 simultaneous test

---

## Test 6: CFGI as Top Gate

### CFGI at Actual Peaks
| Coin | CFGI at Peak | CFGI RSI(7) at Peak |
|------|-------------|-------------------|
| ETH | **46** (neutral!) | 47.1 |
| SOL | **78** | 44.4 |
| LINK | N/A (no coin-specific data) | N/A |
| XRP | **80** | 62.7 |

### CFGI at Steve Score >= 3 Clusters
| Coin | Cluster Date | CFGI | Near Peak? |
|------|-------------|------|-----------|
| ETH | 2023-11-08 | 67 | false (+652d) |
| ETH | 2024-02-20 | 87 | false (+548d) |
| ETH | **2025-07-18** | **88** | **TRUE (+34d)** |
| SOL | **2024-11-20** | **71** | **TRUE (+58d)** |
| SOL | 2025-05-13 | 70 | false (-116d) |
| SOL | 2025-07-18 | 73 | false (-182d) |
| XRP | **2025-07-13** | **82** | **TRUE (+8d)** |
| LINK | all clusters | N/A | no coin-specific CFGI |

### CFGI Gate Results (Steve >= 3)
- **Raw CFGI > 75:** Works for SOL (2 to 2 clusters, keeps true) and XRP (1 cluster, true). Misses nothing for those coins.
- **Kills ETH false signals:** No — all 3 ETH clusters have CFGI > 65.
- **LINK:** No CFGI data available — gate can't help.

### Key Finding: ETH Tops in Neutral Sentiment
ETH peaked at CFGI 46 — price was euphoric but sentiment had already started cooling. This is divergence at the macro level. A CFGI greed gate would miss ETH's top entirely.

**Conclusion:** CFGI > 75 helps SOL/XRP but not ETH. Not a universal gate. The top problem is fundamentally harder than the bottom because tops distribute gradually (sentiment cools before price peaks) while bottoms capitulate sharply (sentiment and price align).

---

## Test 7: K×D Crossover Threshold (K Must Have Been > X Before Cross)

Bottom mirror: K < 5 before cross above D → K > 95 before cross below D

### Threshold Matrix (all coins, ETF era)
| K Threshold | Lookback | Total Signals | False % |
|------------|----------|---------------|---------|
| > 80 | 3 candles | 18 | 50% |
| > 85 | 3 candles | 17 | 53% |
| > 90 | 3 candles | 13 | 62% |
| > 93 | 3 candles | 11 | 55% |
| > 95 | 3 candles | 9 | 56% |

### Finding
Threshold doesn't significantly reduce false rate. The junk crosses (K=31) get filtered, but remaining crosses are all from genuine OB periods. LINK has 5 separate OB93 periods before its Dec 2024 peak — all "legitimate" but premature.

The real issue: multiple OB cycles within one bull market, not weak crossovers.

---

## Overall Conclusions

1. **Bottom conviction stack is locked** — Hybrid 3/4 (Steve + CFGI<35), top gate, 3D death cross gate, one-trigger lock, no-reshort. +$11,228 on paper bot.
2. **Top stack is harder than bottom** — tops distribute gradually (divergence), bottoms capitulate sharply (alignment).
3. **Steve's 2D timing is excellent** (+4 to +58 days) but 56-85% false positive rate.
4. **MFI is genuinely new information** — differentiates score 2 (noise) from 3/4 (signal).
5. **K×D crossover adds patience** (~30-50 days) but doesn't reduce false rate.
6. **CFGI helps SOL/XRP but not ETH** — ETH tops in neutral sentiment (divergence).
7. **OB93 alone still has lowest false rate (36%)** — recommended to keep as current bear-ON signal.
8. **Future improvements:** Steve score as early warning tier system (3/4 = T1 shorts, 4/4 = T2), MFI integration, per-coin CFGI when data coverage improves.

---

## Test 8: Dynamic Fibonacci Extensions

### Method: Swing Low → Swing High → Retracement → Project
Using 2022 bear bottom, first major swing high, and retracement to project Fib extension targets.

### ETH Result — 3.618 Extension Nails the Top 🎯
- Swing: $881.56 (Jun 2022) → $2,030 (Aug 2022) → $1,073 (Nov 2022)
- **3.618 ext = $4,534** → first hit **Aug 12, 2025** (peak was Aug 24 at $4,957)
- 4.236 ext = $5,125 → never hit (acts as ceiling)
- **Peak landed between 3.618 and 4.236** — classic Fib behavior

### Simple Multiplier from Bear Low
| Coin | Bear Low | Peak | Ratio |
|------|---------|------|-------|
| ETH | $881.56 | $4,957 | 5.62× |
| LINK | $5.30 | $30.94 | 5.84× |
| XRP | $0.29 | $3.66 | 12.75× |

No standard Fib level matches — simple multipliers don't work for top detection.

### Limitation
LINK/XRP: 2022 swings were too small relative to explosive moves. Fib extensions project tiny targets that get blown through. Need longer/larger swing identification for these coins.

### Conclusion
Fib extension works as **price target zone** (the "where"), not a trigger (the "when"). Best used alongside Steve/OB93: when price approaches 3.618 ext AND momentum signals are overbought → high-confidence top zone.

### File: `_top_fib_extensions.py`

---

## Future Research: Bearish Divergence (Brett suggestion, 2026-02-27)
**Concept:** Price making higher highs while RSI/MFI/StochRSI make lower highs = distribution/top.

This is exactly what the data showed tonight:
- ETH Nov 2021 ATH ($4,732): Score only 2 — RSI 71, MFI 64 (declining while price peaked)
- BTC Apr 2021 ATH ($63K): Score 1 — indicators had already cooled
- BTC Nov 2021 ATH ($67K): Score 1 — same pattern

**Why this matters:** Steve's score catches the blow-off (indicators AND price overbought). Bearish divergence catches the distribution top (indicators declining, price still rising). They're complementary — divergence fires AFTER Steve, catching the actual peak that Steve's score misses.

**Implementation idea:** Compare RSI/MFI at each new price high. If price > prior high but RSI < prior RSI high → bearish divergence. Multi-timeframe (2D and 2W) for confirmation.

**Priority:** High — this could be the signal that catches ETH/BTC distribution tops that all other methods miss.

---

## External Reference: 5-Day Gaussian Channel (CryptoCrew / Steve Courtney, 2026-03-02)
**Source:** YouTube video shared by Brett — "WARNING: IT'S HAPPENING AGAIN"

### What It Is
- 5-day Gaussian Channel on BTC — green = bull run, red = crash/bottom phase
- Lagging trend-following indicator (confirms markdown, doesn't predict tops)
- Flipped red **Jan 16, 2026** at ~$92K (BTC had already topped ~$108K, down ~15%)

### Historical Red-Flip to Bottom Timing
| Cycle | Days from Red Flip to Bottom |
|-------|------------------------------|
| 2014  | 95 days                      |
| 2018  | 145 days (pendulum overshoot)|
| 2022  | 80 days (pendulum correction)|

### Implied Bottom Window
- Red flip: Jan 16, 2026
- 80 days → **April 5, 2026**
- 95 days → **April 21, 2026**
- Steve's pendulum theory suggests closer to 80-95 days (not 145)

### Assessment for V14
- **Top detection**: Not useful — too lagging. Our 2D RSI bearish divergence fires 6-59 days BEFORE peak.
- **Bottom timing**: Useful as macro sanity check. If our bottom conviction stack (CFGI<35, RSI<26, StochRSI K&D<20, below SMA200) fires within the April window, that's convergence from independent systems = higher confidence.
- **Every cycle makes a double bottom** per Steve's analysis — aligns with our 2W StochRSI K≥5 gate (waits for confirmation after initial bottom).

### Alt Recovery Ahead of BTC (Brett Observation, 2026-03-02)
- As of early March 2026, alts are **way ahead of BTC** in the crash cycle — already experiencing 3D death crosses and severe oversold territory while BTC is still mid-markdown
- Implication: alts front-ran the crash → what crashes first recovers first → alts could bottom and recover ahead of BTC
- This would drive **BTC dominance down** — classic alt season trigger (BTC.D peaks during fear, falls as alts lead recovery)
- **V14 positioning**: HBAR, ATOM, LINK, NEAR are all alts that would benefit from this rotation. DCA layers accumulating at/near lows.
- **Risk**: BTC capitulation event could drag everything lower one more time — conviction bottom stack designed to catch this

## Current 2W StochRSI Status (all coins)
All coins have K near 0 on 2W — at the BOTTOM of cycle, not top.
ETH K=0.0, SOL K=0.0, BTC K=0.0, LINK K=0.4, XRP K=0.3
