# ROUTER Phase 2-3 Findings — Dynamic Tiers & Fast-Track Routing

**Date:** 2026-02-27
**Status:** ❌ Neither Phase 2 nor Phase 3 produced meaningful improvements
**Recommendation:** Skip to Phase 4 (ROUTER→MARKUP direct path)

---

## Phase 2: Dynamic Tier Gates

### Analysis (`_tier_analysis.py`)
- **43 tier adds** across 5 coins (ETH, SOL, BTC, LINK, XRP), ETF era (2023-01 → 2026-02)
- T2 Long: 9W/9L (50%) — avg win +34.1%, avg loss -12.7% → net positive despite coin flip
- T3 Long: 9W/1L (90%) — current 14d delay is already very effective
- T2 Short: 5W/3L (63%), T3 Short: 5W/2L (71%)
- 3 T2 longs within 14d of OB top signal → all 3 were losses

### Backtest (`_dynamic_tiers_test.py`)
17 variants × 5 coins = 85 backtests.

| Variant | Delta vs Baseline | Notes |
|---|---|---|
| OB block 21d | **+$87** | Only net-positive variant |
| OB block 14d | +$17 | Marginal |
| Structure ≥ 1 | +$36 | Marginal |
| ADX > 25 for T2 | -$388 | LINK loses $328 |
| ADX > 25 + OB14d + Struct≥1 | -$475 | More gates = more losses |
| Structure ≥ 2 | **-$2,471** | Destroys LINK (-$1,926) |

### Decision
**Skip Phase 2.** T2's 50% hit rate is net positive because wins are 3× bigger than losses. Any gate that blocks losses also blocks wins. LINK is particularly sensitive — loses $300-$400 in every restrictive variant.

---

## Phase 3: Fast-Track DCA Routing (Confidence Scoring)

### Path Analysis (`_router_path_analysis.py`)
34 ROUTER windows, 2,032 total dwell days:
- **24 (71%)** → DCA → MARKUP (1,540 days, avg 64d each)
- **5 (15%)** → Correctly went MARKDOWN (157 days, avg 31d)  
- **4 (12%)** → SHOULD have gone MARKDOWN but went DCA first (165 days wasted)
- **1** → Still in ROUTER

**Key insight:** 71% of ROUTER windows eventually go to MARKUP. The dominant pattern is post-top → slow ranging → DCA → markup.

**Signal analysis at +7 days:**
- HH_HL ≥ 1: Would correctly fast-track 6/7 windows to DCA, saving 331 days (86% accuracy)
- LH_LL: Not predictive for MARKDOWN (4/5 would be wrong)
- The 4 SHOULD_MARKDOWN windows had no distinguishing signals at entry

### Backtest (`_router_fasttrack_test.py`)
17 variants × 5 coins. Results with corrected baseline:

| Variant | Delta | Days Saved | Notes |
|---|---|---|---|
| HH_HL≥1 @7d | -$876 | +447 | Saves days but loses money |
| SMA50_above @7d | +$1,225 | +308 | First run only; unstable |
| HH_HL≥1 OR SMA50 @7d | -$157 | +591 | Mixed |
| No FT, timeout=28d | -$1,664 to -$4,387 | +214 | Hurts |
| No FT, timeout=21d | +$3,158 to -$4,441 | +523 | Inconsistent across runs |

### Root Cause: Why Saving Days Doesn't Help
The 1,862 dead ROUTER days are a **symptom, not the cause** of underperformance:
1. Routing faster to DCA doesn't help because DCA produces marginal returns (~$79 additive per $10K)
2. The real returns come from MARKUP sells (+32-374%) and MARKDOWN shorts (+9-52%)
3. Getting to DCA 30 days faster just means 30 more days of low-yield DCA grinding
4. Several fast-track variants caused bad MARKDOWN entries for LINK, wiping gains

### Decision
**Skip Phase 3.** Fast-track routing saves days but doesn't translate to portfolio gains. The bottleneck isn't speed through ROUTER→DCA, it's the **absence of ROUTER→MARKUP direct path**.

---

## Phase 4: ROUTER→MARKUP Direct Path (Next)

The missing transition that would actually add value:
- **Current:** ROUTER can only exit to DCA or MARKDOWN
- **Proposed:** Add ROUTER→MARKUP when HH_HL ≥ 2 + Fib_support (same gate as DCA→MARKUP)
- **Why it matters:** Bypasses DCA entirely for V-bottom recoveries, deploying capital at markup tiers immediately
- **Risk:** Must not fire on bear market rallies — needs bias filter or structure confirmation

This is the only remaining ROUTER optimization with theoretical leverage. All "speed up routing" approaches have been tested and failed.

---

## Files Created
| File | Purpose |
|---|---|
| `_tier_analysis.py` | Analyzed all 43 tier adds (win/loss, OB proximity, signals) |
| `_dynamic_tiers_test.py` | 17 dynamic gate variants backtest |
| `_router_path_analysis.py` | Analyzed all 34 ROUTER windows (path taken, signals, ideal path) |
| `_router_fasttrack_test.py` | 17 fast-track routing variants backtest |

## Key Lessons
1. **More restrictive gates ≠ better returns** — LINK consistently punished by any additional filtering
2. **Signal accuracy ≠ portfolio improvement** — HH_HL@7d had 86% accuracy but negative dollar impact
3. **Dead time ≠ lost opportunity** — ROUTER dwell days aren't costing returns; the returns happen in MARKUP/MARKDOWN
4. **The real gap is a missing transition** — ROUTER→MARKUP doesn't exist, forcing all bullish exits through DCA first
