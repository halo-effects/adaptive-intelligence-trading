# V13 Signal Matrix Results

**Date:** 2026-02-25
**Coins:** BTC, ETH, SOL
**Period:** Jun 2024 → Feb 2026
**Scoring:** 40% accuracy + 30% (1-FP rate) + 15% timing + 15% coverage

---

## Top Individual Signals (Cross-Coin Average)

### TOP DETECTION (Markup End)
| Rank | Signal | Accuracy | FP Rate | Coverage | Avg Lag | Weighted |
|------|--------|----------|---------|----------|---------|----------|
| 1 | **2W StochRSI OB>95 exit** | 100% | 0% | 50% | 13.0d | **86.0** |
| 2 | 1W StochRSI OB>95 exit | 56% | 44% | 83% | 11.2d | 60.8 |
| 3 | 1W StochRSI OB>90 exit | 50% | 50% | 83% | 11.2d | 56.9 |

### BOTTOM DETECTION (Markup Start / Markdown End)
| Rank | Signal | Accuracy | FP Rate | Coverage | Avg Lag | Weighted |
|------|--------|----------|---------|----------|---------|----------|
| 1 | **2W StochRSI OS<15 exit** | 83% | 17% | 61% | 10.3d | **77.3** |
| 2 | 2W StochRSI OS<20 exit | 83% | 17% | 61% | 15.0d | 75.0 |
| 3 | 2W StochRSI OS<10 exit | 69% | 31% | 89% | 9.2d | 72.3 |

### DAILY CONFIRMATION
| Rank | Signal | Accuracy | FP Rate | Coverage | Avg Lag | Weighted |
|------|--------|----------|---------|----------|---------|----------|
| 1 | SMA50 slope 14d (bullish) | 47% | 53% | 100% | 11.5d | 57.3 |
| 2 | SMA50 slope 14d (bearish) | 42% | 58% | 67% | 9.7d | 49.6 |
| 3 | SMA50 slope 10d (bullish) | 36% | 64% | 100% | 12.2d | 49.2 |

### SENTIMENT (standalone — noisy, best as confirmation)
| Signal | Accuracy | FP Rate | Coverage |
|--------|----------|---------|----------|
| CFGI greed>75 exit | 21% | 79% | 67% |
| CFGI declining ROC-5d | 20% | 80% | 100% |
| CFGI fear<35 exit | 16% | 84% | 89% |

---

## Combination Test Results (Cross-Coin Average)

### MARKUP ENTRY (DCA → MARKUP) — **STRONG**
| Combo | Accuracy | FP Rate | Coverage | Weighted |
|-------|----------|---------|----------|----------|
| **2W OS<20 alone** | **83%** | **17%** | 61% | **75.0** |
| 2W OS<20 + daily confirm | 83% | 17% | 61% | 75.0 |
| 2W OS<20 + BMSB above | 83% | 17% | 61% | 75.0 |
| 2W OS<20 + overext<20% | 83% | 17% | 61% | 75.0 |
| 1W OS<20 alone | 37% | 63% | 89% | — |

**Verdict:** 2W OS<20 is already clean — filters don't improve it. All combos tied because filters pass the same signals. Coverage limited to 61% because some transitions are too recent for 2W to fire.

### MARKUP EXIT (MARKUP → DCA) — **PROBLEM AREA**
| Combo | Accuracy | FP Rate | Coverage | Weighted |
|-------|----------|---------|----------|----------|
| **1W OB>97 alone** | **56%** | **44%** | **83%** | **60.8** |
| 1W OB>80 alone | 36% | 64% | 50% | 43.9 |
| 2W OB>80 alone | 17% | 83% | 17% | 19.2 |
| 2W OB>80 + daily confirm | 0% | 67% | 0% | 0.0 |

**Verdict:** 2W StochRSI OB exit MISSES most tops in the combo test. 1W OB>97 is the best combo but still only 56% accurate with 44% FP. This is the hardest transition — needs rework.

### MARKDOWN ENTRY (DCA → MARKDOWN) — **MODERATE**
| Combo | Accuracy | FP Rate | Coverage | Weighted |
|-------|----------|---------|----------|----------|
| **2W OB>80 alone** | **67%** | **33%** | 50% | **60.1** |
| 2W OB>80 + daily confirm | 33% | 33% | 17% | 29.5 |
| 2W OB>80 + BMSB below | 0% | 0% | 0% | 0.0 |

**Verdict:** 2W OB>80 alone works for SOL/ETH but misses BTC. Adding BMSB below kills ALL signals (too strict). Daily confirm also too strict.

### MARKDOWN EXIT (MARKDOWN → DCA) — **WEAK**
| Combo | Accuracy | FP Rate | Coverage | Weighted |
|-------|----------|---------|----------|----------|
| 1W OS<20 alone | 11% | 89% | 67% | 22.1 |
| 1W OS<20 + daily confirm | 17% | 83% | 33% | 18.8 |
| 2W OS<20 alone | 0% | 100% | 0% | 0.0 |

**Verdict:** Very weak — only 2 ground truth "markdown_end" events (BTC Apr, SOL Apr). Most OS exits are matching "markup_start" instead. Suggests markdown_end and markup_start ground truth overlap — they're often the same event.

### CORRECTION FILTER
| Filter | BTC | ETH | SOL | Average |
|--------|-----|-----|-----|---------|
| 1W NOT OB>80 | 56% | 50% | 77% | **61%** |
| 2W NOT OB>80 | 57% | 43% | 80% | **60%** |

**Verdict:** Only ~60% accuracy — worse than the 85% from our earlier test. Different methodology (this counts all >10% drops, earlier test was more selective). Still directionally useful but not the slam dunk we thought.

---

## Key Findings

### What Works
1. **2W StochRSI OS<15 or OS<20 for bottom/markup entry** — 83% accuracy, 17% FP, best signal in the entire matrix
2. **2W StochRSI OB>95 for individual top detection** — 100% accuracy but only 50% coverage (misses some tops)
3. **1W StochRSI OB>97 for top early warning** — 83% coverage, best we have for exits

### What Doesn't Work
1. **2W StochRSI OB>80 for markup exit in combos** — too few signals, misses most tops
2. **BMSB as a gate** — kills too many signals (both good and bad)
3. **CFGI standalone** — 80%+ FP rate on everything. Good for conviction only.
4. **ADX for ranging** — 71-80% FP rate
5. **3W StochRSI anything** — too slow, misses everything

### Critical Insight
**Top detection (markup exit) is the hardest problem.** The 2W StochRSI that works perfectly for individual signal detection struggles in the combo framework because our ground truth dates require the signal to fire within 21 days. 2W signals often fire 3-4 weeks after the actual top.

**The architecture should use LAYERED response, not single-gate:**
1. 1W OB>97 cross-down → ALERT (tighten, reduce exposure)
2. 2W OB>95 exit → CONFIRM (sell markup layers)
3. If neither fires but daily structure breaks → CAUTIOUS EXIT (daily-only trigger as fallback)

---

## Recommendations for V13 Implementation

### Markup Entry (DCA → MARKUP)
- **Primary:** 2W StochRSI K exits OS (crosses above 15-20)
- **No additional filters needed** — signal is already clean
- **Timing:** ~10-15 day lag is acceptable (captures 75%+ of move)

### Markup Exit (MARKUP → DCA)
- **Early warning:** 1W StochRSI K crosses below 97 → reduce exposure, tighten
- **Confirmation:** 2W StochRSI K crosses below 95 OR (1W OB exit + daily SMA50 slope negative)
- **Fallback:** If daily structure breaks (LH/LL streak ≥ 3) AND SMA50 slope negative for 14d → exit even without weekly signal

### Markdown Entry (DCA → MARKDOWN)
- **Primary:** 2W StochRSI OB exit + sustained below BMSB relaxed (1W not 2W) OR daily confirms
- **Note:** BMSB 2W sustained is too strict. Use 1W or drop BMSB requirement entirely.

### Markdown Exit (MARKDOWN → DCA)
- **Merge with markup entry** — they're often the same event. Use 2W OS exit as the signal for both.
- **Don't separate markdown_end from markup_start in the architecture**

### Correction Filter
- **Use 1W NOT overbought as initial filter** (60% base)
- **Boost with:** BMSB status ABOVE + CFGI > 40 + daily SMA50 still positive
- **Accept:** Some corrections will trigger exit. That's the cost of not missing real tops.
