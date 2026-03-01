# V13 Gate Test Plan — Signal Validation & Results

**Created:** 2026-02-25
**Last updated:** 2026-02-26
**Status:** Tests 1-6 complete. LH_LL gate implemented and validated. Bias system: **CFGI_RSI < 35 identified as leading candidate** (Section 4h). 8 approaches tested, 1 leading, 7 rejected.

---

## 1. Data Setup

### 1.1 Database
- **Path:** `trading/spot/data/candles.db` (SQLite)
- **1h candles:** `candles_1h` table — raw hourly OHLCV from Binance
- **Daily candles:** `daily_candles` table — aggregated from 1h by `build_daily_candles.py`
- **Indicators:** `daily_indicators` table — SMA50/200, ADX, ATR, RSI, StochRSI, structure streaks, etc.
- **CFGI:** `cfgi_daily` table — Crypto Fear & Greed Index (available from Jul 2022+)

### 1.2 Data Depth (Critical for Valid Signals)

| Coin | 1h Start | Daily Rows | 2W StochRSI Valid From |
|------|----------|------------|----------------------|
| **BTC/USDC** | Jan 2019 | 2,600 | ~Oct 2020 |
| **ETH/USDC** | Jan 2019 | 2,600 | ~Oct 2020 |
| **SOL/USDC** | Aug 2020 (merged from USDT) | 2,015 | ~mid-2022 (bootstrap problem) |

**2W StochRSI warmup:** ~784 days of daily data required. SOL only had ~450 days by Nov 2021 — top detection unreliable for SOL's first cycle.

### 1.3 Backfill Scripts
| Script | Purpose |
|--------|---------|
| `backfill_deep.py` | BTC/ETH 1h candles from Jan 2019 (Binance) |
| `backfill_warmup.py` | SOL/USDT Aug 2020 → Jun 2021, merged into SOL/USDC |
| `build_daily_candles.py` | Aggregate 1h → daily OHLCV |
| `recompute_indicators.py` | Compute all technical indicators on daily candles |

**Data integrity warning:** The daily collector cron (`daily_collector.py`) does DELETE+rebuild of daily candles from 1h. It will wipe backfilled USDT data. Always use USDC pairs for backtesting.

### 1.4 Test Coins
Primary: **ETH/USDC, BTC/USDC, SOL/USDC** (Oct 2020 → Feb 2026, $10K capital)
Paper bot validation: **ETH/USDC, SOL/USDC** (Oct 2024 → Feb 2026, $2,500/coin)

### 1.5 Signal Pack
`V13SignalPack(coin)` — read-only signal provider. Safe to share across profile runs.

Provides: Structure (HH_HL, LH_LL streaks), Fibonacci (support/break), Indicators (ADX, SMA200 distance, SMA50 slope), StochRSI (2W/1W K values), CFGI, Price data.

---

## 2. Engine Configuration

### 2.1 Risk Profiles
| Parameter | Low | Medium | High |
|-----------|-----|--------|------|
| `DCA_BO_PCT` | 3% | 4% | 5% |
| `DCA_SO_DEVIATION` | 3.0% | 2.5% | 2.0% |
| `DCA_SO_MULTIPLIER` | 2.0x | 2.0x | 2.0x |
| `DCA_TP_PCT` | 1.5% | 1.5% | 1.0% |
| `DCA_MAX_LAYERS` | 5 | 8 | 12 |

### 2.2 Phase/Tier Settings (constant across profiles)
- Markup tiers: T1=60%, T2=20%, T3=10% (front-loaded)
- Short tiers: T1=60%, T2=20%, T3=10% (symmetric with markup)
- Top detection: 2W OB93 (primary), 1W OB85 (fallback), 1W K<50 (failsafe)
- ADX threshold: 20
- Structure lookback: 60 days
- SMA200 overextension: 20 (percentage units, not decimal)

---

## 3. Tests Conducted

### Test 1: Daily Score Smoothing
**Status:** ✅ Superseded — V13 uses phase state machine, not score-based transitions.
**Finding:** The V13 engine doesn't use TATopScorer. Phase transitions are driven by specific signal gates (structure + indicators + StochRSI), not a composite score. Daily candle granularity eliminates the noise that plagued 1h scoring.

---

### Test 2: Ranging Detection
**Status:** ✅ Tested via `test_signal_candidates.py`
**Signals evaluated:** ADX < 20 sustained streaks, BB width, ATR% change, CFGI stability

**Findings:**
- **ADX < 20 for 21+ consecutive days** is the engine's ranging exit signal (MARKDOWN → FLAT)
- **ADX < 20 for 14+ days** triggers FLAT → DCA (ranging confirmed)
- Works reliably across all 3 coins — no false ranging detections observed
- ADX alone is sufficient; BB width and ATR% add no discriminatory value

**Result:** ADX-based ranging detection validated. No changes needed.

---

### Test 3: Markup Confirmation
**Status:** ✅ Tested via `test_signal_candidates.py`, `test_markup_weekly_gate.py`

#### 3a. Daily Structure Gate (Current Engine)
**Gate:** HH_HL ≥ 2 + Fib_support
**Results:**
| Coin | Good Markup Recall | False Alarm Rate | Avg Latency |
|------|-------------------|-----------------|-------------|
| ETH | 100% (4/4) | Low | ~5 days after bottom |
| BTC | 100% (5/5) | Low | ~3 days after bottom |
| SOL | 100% (3/3 good + 3/3 bad) | 3 bear bounces pass | ~2 days |

**Issue found:** SOL 2022 bear bounces produce valid HH_HL ≥ 2 + Fib_support. Gate can't distinguish bear bounces from real bull starts on daily alone.

#### 3b. Weekly Structure Gate Variants (Test Matrix)
**Script:** `test_markup_weekly_gate.py`
**Tested 5 variants across ETH/BTC/SOL:**

| Variant | ETH Recall | BTC Recall | SOL Recall | SOL Bad Blocked |
|---------|-----------|-----------|-----------|----------------|
| Daily HH_HL ≥ 2 (current) | 100% | 100% | 100% | 0/3 |
| Weekly HH_HL ≥ 1 only | 100% | 100% | 100% | 0/3 |
| Weekly HH_HL ≥ 2 only | **50%** ❌ | 100% | 100% | 2/3 |
| Daily ≥ 2 + Weekly ≥ 1 | 100% ✅ | 100% ✅ | 100% ✅ | 0/3 |
| Daily ≥ 2 + Weekly ≥ 2 | **25%** ❌ | 100% | 100% | 2/3 |

**Decisions:**
- ❌ Weekly HH_HL ≥ 2 **REJECTED** — kills ETH recall (50%), blocks bear bottom recoveries
- ❌ Daily + Weekly ≥ 2 **REJECTED** — even worse ETH recall (25%)
- ✅ Daily HH_HL ≥ 2 **KEPT** as current gate (no weekly addition for MARKUP)
- ℹ️ Daily + Weekly ≥ 1 is best precision/recall combo but doesn't solve SOL bear bounces

#### 3c. Additional Signals Evaluated for Markup
**Script:** `test_signal_candidates.py`

| Signal | Recall | Precision | Verdict |
|--------|--------|-----------|---------|
| SMA50 slope positive | High | Low | Too common, not discriminative |
| Volume expansion (>20d avg) | Medium | Low | Noisy |
| CFGI > 50 | Medium | Medium | Gaps before Jul 2022 |
| Price > SMA200 | Blocks SOL bad ✅ | Kills ETH/BTC good ❌ | REJECTED as universal gate |
| Golden Cross (SMA50 > SMA200) | Slow | High | REJECTED — 16 months to flip after 2022 bear |

---

### Test 4: Distribution / Top Detection
**Status:** ✅ Validated — engine's 3-layer system works correctly

**Engine's top detection (validated by Brett):**
1. **Primary:** 2W StochRSI K > 93 → sell all, enable shorts
2. **Fallback:** 1W StochRSI K > 85 (if 2W never reaches 93) → sell all, enable shorts
3. **Failsafe:** 1W StochRSI K < 50 → sell all (capital protection)

**Validation results:**
| Event | Detection | Signal Used |
|-------|-----------|-------------|
| BTC Nov 2021 top | ✅ | 1W OB85 fallback (2W peaked at ~67) |
| ETH Nov 2021 top | ✅ | 1W OB85 fallback |
| SOL Nov 2021 top | ✅ | 1W OB85 fallback |
| ETH Dec 2024 top | ✅ | 1W OB85 fallback (2W peaked at 61) |
| SOL Dec 2024 top | ✅ | 1W OB85 fallback (2W peaked at 90) |
| BTC Jan 2025 top | ✅ | 2W OB93 primary |
| SOL Sep 2025 top | ✅ | 1W OB85 fallback (2W peaked at 84) |

**Key insight:** BTC Nov 2021 double-top compressed 2W StochRSI to max ~67 (structural behavior, not a bug). The fallback layer caught it correctly.

**HVF (High Volume Funnel) evaluation:**
**Script:** `check_hvf_at_markup_fails.py`
- Tested as potential top confirmation signal
- SOL good markups score 0.00-0.02, bad markups score 0.00-0.14 (backwards!)
- Works for BTC (3/5 good markups >0.4) but fails SOL/ETH
- **CONFIRMED DEAD CODE** — logged only, not used for routing. Correctly excluded.

---

### Test 5: Markdown Confirmation
**Status:** ✅ Tested and **LH_LL gate implemented**

#### 5a. Problem Identified: Asymmetric Gates
- MARKUP had structure gate: HH_HL ≥ 2 + Fib_support
- MARKDOWN only had: ADX > 20 + Fib_break (NO structure confirmation!)
- This allowed 5 bad ETH shorts with ADX=21-24 but zero bearish structure
- XRP trade #34 (Apr–May 2025, -$1,675 / -34%) also entered with Daily LH_LL = 0

#### 5b. LH_LL ≥ 2 Gate — Implemented & Validated
**Gate added:** `LH_LL ≥ 2` required for both DCA→MARKDOWN and FLAT→MARKDOWN paths
**Mirrors:** MARKUP's `HH_HL ≥ 2` — perfect structural symmetry

**ETH Short Analysis (before vs after LH_LL gate):**
| Short Entry | ADX | LH_LL | Outcome | Gate Result |
|-------------|-----|-------|---------|-------------|
| 2021-05-22 | 24 | 0 | MARKDOWN_FAIL (-$2,108) | 🚫 **BLOCKED** |
| 2022-01-22 | 21 | 0 | MARKDOWN_FAIL (-$1,745) | 🚫 **BLOCKED** |
| 2022-06-18 | 24 | 3 | Profitable (+$816) | ✅ Passed |
| 2023-08-23 | 24 | 0 | MARKDOWN_FAIL (-$2,419) | 🚫 **BLOCKED** |
| 2024-04-19 | 23 | 0 | MARKDOWN_FAIL (-$3,092) | 🚫 **BLOCKED** |
| 2024-07-05 | 22 | 0 | MARKDOWN_FAIL (-$2,523) | 🚫 **BLOCKED** |
| 2025-02-02 | 24 | 4 | Profitable (+$199) | ✅ Passed |
| 2025-11-12 | 39 | 5 | Profitable (+$922, open) | ✅ Passed |

**Result:** 5 bad shorts blocked, 3 profitable shorts kept. ETH short P&L: **-$11K → +$5.7K** (swing of +$16.7K).

**XRP Markdown Fail — Trade #34 (Paper Bot):**
**Script:** `check_xrp_markdown_fail.py`
- Entry: 2025-04-08 at $1.7963
- Exit: 2025-05-13 at -$1,675 (-34%)
- **Daily LH_LL at entry: 0** (was 2 on Apr 7, reset on Apr 8)
- **ADX: 24.4** (above threshold)
- Gate check: LH_LL = 0 < 2 → **BLOCKED** ✅
- Price context: Apr 3-5 had HH streak (bounce), then sharp drop Apr 6-8, but daily structure reset
- The LH_LL gate would have saved $1,675 on this single trade

**BTC validation:** All 3 existing shorts already had LH_LL ≥ 2 at entry. Gate changed nothing — confirms BTC shorts were always well-filtered.

#### 5c. Additional Markdown Signals Evaluated
**Script:** `test_signal_candidates.py`

| Signal | Recall (real markdowns) | False Alarm (corrections) | Verdict |
|--------|------------------------|--------------------------|---------|
| Daily LH_LL ≥ 2 | 100% ETH, 100% BTC, 100% SOL | Fires on corrections too | **Implemented** (with ADX+Fib) |
| CFGI < 30 | 60-80% | Low false alarm | Gaps before Jul 2022 |
| Price < SMA200 | Variable | High for recovery entries | Blocks good bottom shorts |
| SMA50 slope negative | High | Very high | Too common, not discriminative |
| Death Cross | 0-50% SOL (too lagging) | 100% false alarm | **REJECTED** |
| Weekly LH_LL ≥ 1 | 100% | Lower than daily-only | Good complement (not yet added) |

---

### Test 6: Mid-Cycle Correction vs Distribution
**Status:** ✅ Tested — **no single daily signal cleanly separates them**

**Script:** `test_signal_candidates.py` (comprehensive evaluation across Tests 2-6)

**Key finding:** Every structural signal that detects real distributions also fires during corrections:
- LH_LL ≥ 2 fires on corrections (bear structure forms in any pullback)
- ADX > 20 fires on corrections (trend strengthens during sharp drops)
- Price < SMA50 fires on corrections
- The signals are measuring the same thing: "is the market going down?" — yes, in both cases

**What DOES separate them (in hindsight):**
- Duration: corrections resolve in 2-4 weeks, distributions extend 2-6 months
- Depth: corrections hold SMA200, distributions break it
- CFGI: corrections stay 30-50, distributions go below 25
- Weekly structure: corrections hold weekly higher lows, distributions break them

**Problem:** These distinguishing features are only clear AFTER the fact. At the point of entry, both look the same.

**Conclusion:** The engine handles this correctly through its safety nets:
- **MARKUP_FAIL detector:** Exits at 25% DD + ADX>25 (limits damage from bad entries)
- **Phase hold minimums:** 3-day minimum prevents whipsawing
- **Structure gates:** LH_LL/HH_HL filter out the worst entries

---

## 4. Bias System Investigation (In Progress)

### 4a. SMA200 as Universal Bias Gate
**Script:** `test_bias_gate.py`

| Coin | Good Markup Pass | Bad Markup Block | Verdict |
|------|-----------------|-----------------|---------|
| SOL | 3/3 (100%) | 3/3 (100%) ✅ | Perfect for SOL |
| ETH | 1/4 (25%) ❌ | N/A | Kills recovery entries |
| BTC | 4/5 (80%) | N/A | Acceptable but lossy |

**REJECTED:** Can't use for ETH/BTC where best entries start from below SMA200 during bear bottom recoveries.

### 4b. Engine Top Signals as Bias Trigger
**Script:** `test_bias_system.py`

Concept: Engine's own top signals (2W OB93/1W OB85) flip bias to bearish after a top is detected.

| Coin | Good Markup Pass | Good Markdown Pass | Bad Markup Block |
|------|-----------------|-------------------|-----------------|
| ETH | 100% ✅ | 100% ✅ | N/A |
| BTC | 60% (2 misses) | 80% | N/A |
| SOL | 100% (incl 3 bad) ❌ | 100% | 0/3 blocked |

**Issue:** SOL had no top signal before 2022 because 2W StochRSI needed ~784 days warmup; SOL only had ~450 days by the Nov 2021 top. Bootstrap problem — can't detect tops you haven't observed yet.

### 4c. Hybrid Bias System (Engine Top + Death Cross + SMA200 Reclaim)
**Script:** `test_bias_hybrid.py`

Design:
- Bear trigger: Engine top signal OR Death Cross (SMA50 < SMA200)
- Bull trigger: Price reclaims SMA200
- Bull bias: easy longs (daily HH_HL≥2), strict shorts (daily+weekly LH_LL≥2)
- Bear bias: easy shorts (daily LH_LL≥2), strict longs (daily+weekly HH_HL≥2)

**Results:**
| Metric | Value | Assessment |
|--------|-------|------------|
| Good markup pass rate | 58% (7/12) | ❌ Too many good entries blocked |
| Bad markup block rate | 67% (2/3) | Mediocre |
| Good markdown pass rate | **30% (3/10)** | ❌ Severe failure |
| Correction block rate | 100% (7/7) | ✅ But at too high a cost |

**Root cause:** Death Cross / SMA200 reclaim oscillation causes **dozens of daily transitions** during consolidation periods. BTC, ETH, and SOL all affected. Price hovering near SMA200 flips bias back and forth constantly.

**REJECTED:** Trigger mechanism too noisy. Blocking 70% of good markdown entries is unacceptable.

### 4d. Brett's Endorsed Direction
Brett endorsed **Approach #2**: Build real structure-based gates, not soft bias triggers.
- System should work symmetrically in both directions
- Bull bias = easy longs (daily HH_HL≥2), strict shorts (daily+weekly LH_LL≥2)
- Bear bias = easy shorts (daily LH_LL≥2), strict longs (daily+weekly HH_HL≥2)
- **Constraint:** Trigger mechanism must be stable and low-frequency

**Status:** ~~Need to identify a bias trigger that doesn't chatter.~~ **CFGI_RSI < 35 identified as leading candidate (see 4e-4h).**

### 4e. 3D Death Cross / Golden Cross Bias
**Scripts:** `build_3d_signals.py`, `test_3d_bias.py`, `test_3d_bias_v2.py`

3-day candle aggregation eliminates daily noise. Transitions: ETH 0.7/year, BTC 0.4/year, SOL 1.1/year — near zero chattering.

| Variant | ETH | BTC | SOL | Status |
|---------|-----|-----|-----|--------|
| Symmetric (blocks markups in bear AND shorts in bull) | HURTS | +$3.6K | HURTS | REJECTED — too aggressive |
| Bear-only (blocks markups in bear, shorts always) | HURTS | HURTS | HURTS | REJECTED — misses ETH Oct 2023 |
| 3D HH_HL structure clear | Minimal | Minimal | No effect | REJECTED — clears too fast |

**REJECTED:** Despite stable trigger, every implementation either over-blocks or under-filters.

### 4f. Trailing Stops on Markup Positions
**Script:** `test_trailing_stop.py`

Tested 5 variants (aggressive to tight) on all markup positions.

**Catastrophic failure:** ETH Oct 2020 markup (+260%, $22K profit) gets cut at +27% ($2.7K) by every variant. The early volatility triggers the trailing stop before the massive run.

| Variant | ETH | BTC | SOL |
|---------|-----|-----|-----|
| All 5 variants | -$18K to -$24K | -$7.6K to +$1.4K | -$2K to -$3.8K |

**REJECTED:** Fundamentally incompatible with phase-riding strategy. Cannot distinguish bull pullbacks from bear reversals.

### 4g. CFGI < 25 as Bottom Signal (Market-Level)
**Script:** `test_cfgi_bias.py`

Bear ON: engine top signal. Bear OFF: market-average CFGI drops below threshold.

| Threshold | ETH | BTC | SOL |
|-----------|-----|-----|-----|
| CFGI < 25 | +$13,019 (saves 4, misses 1) | +$3,954 (saves 2, misses 1) | Neutral (bootstrap) |
| CFGI < 20 | +$9,314 | +$3,954 | Neutral |

**Promising but superseded** by coin-specific CFGI and CFGI RSI approaches.

### 4h. CFGI RSI < 35 as Bottom Signal (Coin-Specific) — LEADING CANDIDATE ✅
**Scripts:** `test_cfgi_rsi_bias.py`, `run_cfgi_rsi_grid.py`, `test_cfgi_bias_v2.py`

**Concept:** Apply RSI(14) to coin-specific CFGI values. Measures sentiment *momentum* — when fear is dropping fast relative to recent levels. CFGI_RSI < 35 = sentiment capitulation.

**Bear ON:** Engine top signal (2W OB93 / 1W OB85 / 1W K<50)
**Bear OFF:** Coin-specific CFGI_RSI < 35

**Why coin-specific > market average:** BTC Jun 2024 entry correctly allowed because BTC sentiment had recovered while market average still showed fear. Raw CFGI < 30 saves $7.8K on BTC vs $3.4K from CFGI_RSI — but CFGI_RSI < 35 has perfect precision on ETH (0 good trades missed).

**Full 9-combo grid (Oct 2020 → Feb 2026):**

| Coin | Profile | Base ROI | + Bias ROI | Delta | Saved | Missed | Blocked |
|------|---------|----------|------------|-------|-------|--------|---------|
| **ETH** | **Low** | +269% | **+422%** | **+153%** | $15,271 | **$0** | 4bad/0good |
| **ETH** | **Med** | +280% | **+438%** | **+158%** | $15,759 | **$0** | 4bad/0good |
| **ETH** | **High** | +284% | **+436%** | **+152%** | $15,241 | **$0** | 4bad/0good |
| BTC | Low | +186% | +200% | +14% | $6,084 | $4,709 | 2bad/1good |
| BTC | Med | +211% | +208% | -2% | $4,892 | $5,111 | 2bad/1good |
| BTC | High | +167% | +201% | +35% | $7,833 | $4,386 | 2bad/1good |

*SOL excluded — bootstrap problem. Average improvement: +181.6% → +227.8% (+46.3%)*

**ETH detail (High profile) — every markup entry:**

| Date | Bias | CFGI | CFGI_RSI | PnL | Quality | Action |
|------|------|------|----------|-----|---------|--------|
| 2020-10-05 | neutral | — | — | +$22,282 (+223%) | GOOD | ✅ Allowed |
| 2021-05-26 | bear | — | — | -$7,385 (-21%) | BAD | 🛑 Blocked |
| 2021-11-21 | bear | — | — | -$3,981 (-14%) | BAD | 🛑 Blocked |
| 2022-09-27 | bear | 36.5 | 46.1 | +$2,205 (+10%) | GOOD | 🛑 Blocked* |
| 2023-05-04 | bear | 54.5 | 52.0 | +$17 (+0.1%) | GOOD | 🛑 Blocked* |
| 2023-06-21 | bear | 66.0 | 61.0 | -$153 (-1%) | BAD | 🛑 Blocked |
| 2023-10-22 | bear | 62.5 | 65.3 | +$6,985 (+30%) | GOOD | 🛑 Blocked* |
| 2024-03-25 | neutral | 72.0 | 55.4 | -$2,555 (-8%) | BAD | ✅ Allowed |
| 2024-06-16 | bear | 56.0 | 53.9 | -$3,722 (-13%) | BAD | 🛑 Blocked |
| 2024-10-15 | bear | 67.5 | 59.1 | +$3,753 (+15%) | GOOD | 🛑 Blocked* |
| 2025-10-01 | neutral | 59.0 | 55.1 | -$461 (-2%) | BAD | ✅ Allowed |

*At threshold < 35: 4 bad blocked ($15,241), 0 good missed. At < 30: 4 bad, 4 good blocked. Threshold 35 is optimal for ETH.*

*\* These entries blocked at < 30 threshold but allowed at < 35. The 4 "good" blocked entries at < 30 are marginal ($17, $2,205) or recovered later. At < 35, all 4 pass through.*

**Comparison of ALL bias approaches tested:**

| # | Approach | ETH | BTC | SOL | Status |
|---|----------|-----|-----|-----|--------|
| 4a | SMA200 bias gate | Kills recovery | Acceptable | Perfect | REJECTED |
| 4b | Engine top bias | Works | Partial | Bootstrap | Superseded |
| 4c | Hybrid (death cross) | 58% pass | Chatters | Chatters | REJECTED |
| 4e | 3D death cross | Over-blocks | +$3.6K | Over-blocks | REJECTED |
| 4f | Trailing stops | -$18K to -$24K | -$7.6K to +$1.4K | -$2K to -$3.8K | REJECTED |
| 4g | Raw CFGI < 25 | +$13K | +$3.9K | Neutral | Superseded |
| **4h** | **CFGI_RSI < 35** | **+$15.2K** | **+$3.4K** | Excluded | **LEADING** |

**Open questions:**
1. BTC may benefit from raw CFGI < 30 (+$7.8K) instead of CFGI_RSI < 35 (+$3.4K) — per-coin thresholds?
2. LINK/XRP validation blocked on V13SignalPack "Index 1-dimensional" error (data backfilled, needs signal pack fix)
3. Engine integration approach: add as config option or always-on?

---

## 5. Backtest Run History

### Run 1 — Initial (Broken SMA200 Gate)
**Date:** 2026-02-26
**Issue:** `SMA200_OVEREXTENSION` threshold was 0.20 (decimal) but `price_vs_sma200` stored as percentage (32.55). Every MARKUP entry blocked when price above SMA200.
**Results:** ETH +5%, BTC +20% — MARKUP never fires during bull runs.
**Root cause:** Unit mismatch. Silent killer — no error, just wrong comparisons.

### Run 2 — SMA200 Threshold Fix
**Change:** `SMA200_OVEREXTENSION = 0.20` → `SMA200_OVEREXTENSION = 20`
**Results:**

| Coin | Low | Med | High | B&H |
|------|-----|-----|------|-----|
| ETH | +110% | ~120% | ~130% | +465% |
| BTC | +115% | ~118% | ~121% | +538% |
| SOL | +368% | ~400% | ~454% | +155% |

**Finding:** SMA200 gate still blocking entries during bull runs (gate checks overextension on MARKUP entry). SOL's monster returns because it had fewer blocked entries.

### Run 3 — SMA200 Gate Removed from MARKUP Entry
**Change:** Removed SMA200 overextension check from DCA→MARKUP transition entirely.
**Rationale:** Bull runs START from above SMA200 — gating on overextension is structurally incompatible.

| Coin | Low | Med | High |
|------|-----|-----|------|
| ETH | +161% | +162% | +161% |
| BTC | +187% | +211% | +167% |
| SOL | +229% | +174% | +142% |

**Finding:** ETH shorts losing -$10-11K. BTC shorts losing -$6K→-$172. SOL shorts profitable but MARKUP_FAIL trades hurting.

### Run 4 — LH_LL ≥ 2 Gate on MARKDOWN (CURRENT)
**Change:** Added `LH_LL ≥ 2` requirement to DCA→MARKDOWN and FLAT→MARKDOWN paths.
**Rationale:** Mirrors MARKUP's HH_HL ≥ 2. Ensures bearish structure exists before entering short.

| Coin | Profile | ROI | Markup$ | DCA$ | Short$ | B&H |
|------|---------|-----|---------|------|--------|-----|
| **ETH** | **Low** | **+269%** | +$16,455 | +$5,015 | **+$5,423** | +465% |
| **ETH** | **Med** | **+280%** | +$16,052 | +$6,309 | **+$5,677** | +465% |
| **ETH** | **High** | **+284%** | +$16,181 | +$6,459 | **+$5,757** | +465% |
| SOL | Low | +106% | +$5,800 | +$308 | +$4,535 | +155% |
| SOL | Med | +69% | +$4,448 | -$1,283 | +$3,709 | +155% |
| SOL | High | +54% | +$3,663 | -$1,654 | +$3,365 | +155% |
| BTC | Low | +186% | +$18,043 | +$761 | -$177 | +538% |
| **BTC** | **Med** | **+211%** | +$19,893 | +$1,363 | -$193 | +538% |
| BTC | High | +167% | +$16,042 | +$777 | -$164 | +538% |

**Key outcomes:**
- **ETH shorts transformed:** -$11K loss → +$5.7K profit. 5 bad shorts blocked (ADX=21-24, no LH_LL).
- **BTC unchanged:** All 3 shorts already had LH_LL — validates gate doesn't break working behavior.
- **SOL regression:** Early profitable shorts delayed. True problem remains 3 MARKUP_FAIL trades in 2022 bear.
- **XRP markdown fail (paper bot trade #34) would be blocked:** Daily LH_LL = 0 at entry, saving $1,675.

---

## 6. Paper Bot Validation (Oct 2024 → Feb 2026)

**Script:** `compare_paper.py`
**Setup:** High profile, $2,500/coin, same engine as backtest

### Phase Transition Alignment
| Transition | ETH Paper | ETH Backtest | Delta |
|-----------|----------|-------------|-------|
| DCA → MARKUP | Oct 13 | Oct 12 | 1 day |
| MARKUP → FLAT | Dec 23 | Dec 22 | 1 day |
| FLAT → MARKDOWN | Feb 3 | Feb 2 | 1 day |
| MARKDOWN → FLAT | Jul 3 | Jul 2 | 1 day |

| Transition | SOL Paper | SOL Backtest | Delta |
|-----------|----------|-------------|-------|
| MARKUP → FLAT | Dec 16 | Dec 15 | 1 day |
| DCA → MARKDOWN | Feb 6 | Feb 6 | 0 days |
| MARKDOWN → FLAT | May 7 | May 6 | 1 day |
| 2nd MARKUP exit | Oct 2 | Sep 28 | 4 days |

### ROI Comparison
| Coin | Paper Bot | Backtest | Gap |
|------|-----------|----------|-----|
| ETH | +75.8% | +65.3% | 10.5% |
| SOL | +193% | +176% | 17% |

**Gap explanation:** Paper bot trades on 1h candles (better intraday fills). Backtest uses daily closes. 10-15% PnL variance is expected and acceptable.

**Conclusion:** Engine behavior validated — same phases, same direction, same structure. Backtest is a reliable proxy for live performance.

---

## 7. Current Engine Gate Summary

| Transition | Gates Required | Status |
|-----------|---------------|--------|
| DCA → MARKUP | HH_HL ≥ 2 + Fib_support + CFGI (advisory) | ✅ Original |
| DCA → MARKDOWN | **LH_LL ≥ 2** + ADX > 20 + Fib_break | ✅ Updated Run 4 |
| FLAT → MARKDOWN | **LH_LL ≥ 2** + ADX > 20 + Fib_break | ✅ Updated Run 4 |
| MARKUP → FLAT | 2W OB93 / 1W OB85 / 1W K<50 | ✅ Original |
| MARKDOWN → FLAT | ADX < 20 for 21+ consecutive days | ✅ Original |
| FLAT → DCA | ADX < 20 for 14+ days | ✅ Original |

### Safety Nets
| Detector | Trigger | Action |
|----------|---------|--------|
| MARKUP_FAIL | DD > 25% + ADX > 25 | Sell all (liquidate position) |
| MARKDOWN_FAIL | Rise > 25% + ADX > 25 | Close short position |

---

## 8. Signals Evaluated & Rejected

| Signal | Tested For | Why Rejected |
|--------|-----------|-------------|
| SMA200 overextension gate on MARKUP | Preventing late entries | Bull runs start from above SMA200 — structurally incompatible |
| Weekly HH_HL ≥ 2 for MARKUP | Filtering bear bounces | Kills ETH recall (50%) |
| SMA50 slope as gate | Filtering bear market entries | Blocks biggest winners across all coins |
| HVF (High Volume Funnel) | Markup confirmation | Doesn't discriminate on SOL/ETH. Dead code confirmed. |
| Price > SMA200 as universal bias | Bull/bear regime | Kills ETH (3/4 good entries below SMA200) and BTC (1/5) |
| Golden Cross as bias trigger | Bull confirmation | Too slow — 16 months to flip after 2022 bear bottom |
| Death Cross + SMA200 reclaim | Bias trigger hybrid | Excessive chattering (dozens of daily transitions during consolidation) |
| CFGI < 30 for markdown | Bear confirmation | Gaps before Jul 2022, incomplete coverage |

---

## 9. Known Limitations & Open Issues

### SOL MARKUP_FAIL (Unsolved)
Three failed longs in 2022 bear market:
| Date | Entry | Exit | Loss | Context |
|------|-------|------|------|---------|
| 2022-03-28 | $106 | $79 | -25.4% | Post-Luna crash bounce |
| 2022-07-29 | $42 | $31 | -25.5% | Bear market capitulation bounce |
| 2022-11-05 | $37 | $16 | -55.4% | FTX collapse |

All had valid HH_HL ≥ 2 at entry. Price was -13% to -46% below SMA200. Bear bounces produced genuine bullish structure on both daily AND weekly timeframes. No signal tested can cleanly filter these without killing good entries on ETH/BTC.

**Current mitigation:** MARKUP_FAIL safety net limits damage. Without it, capital would ride SOL from $106 to $8.

### SOL Bootstrap Problem
SOL had insufficient history for valid 2W StochRSI before mid-2022. Top detection unreliable for SOL's first cycle. This is a fundamental data limitation, not a code bug.

### Bias System Trigger
~~All tested bias trigger mechanisms have critical flaws.~~ **CFGI_RSI < 35 identified as leading candidate** — see Section 4h. Open question: per-coin threshold tuning and LINK/XRP validation.

---

## 10. Test Scripts Reference

| Script | Location | Purpose |
|--------|----------|---------|
| `test_signal_candidates.py` | `trading/spot/backtest_results/v13/` | Comprehensive signal evaluation (Tests 2-6) |
| `test_markup_weekly_gate.py` | same | Weekly HH_HL gate variants for MARKUP |
| `test_bias_gate.py` | same | SMA200/Golden Cross as bias triggers |
| `test_bias_system.py` | same | Engine top signals as bias triggers |
| `test_bias_hybrid.py` | same | Asymmetric bias system with multiple triggers |
| `check_hvf_at_markup_fails.py` | same | HVF evaluation at markup entry points |
| `check_xrp_markdown_fail.py` | same | XRP trade #34 markdown fail analysis |
| `check_shorts.py` | same | Analyze MARKDOWN entry decisions |
| `audit_signals.py` | same | Full signal pipeline audit |
| `audit_all_markup_entries.py` | same | All markup entries with signals at time of entry |
| `audit_sol_markup_fails.py` | same | SOL MARKUP_FAIL deep dive |
| `pnl_attribution.py` | same | P&L breakdown by Markup/DCA/Short |
| `compare_paper.py` | same | Backtest vs live paper bot comparison |
| `build_weekly_signals.py` | same | Aggregate daily → weekly + weekly structure signals |
| `run_new_coins_profiles.py` | same | Full 9-combo backtest runner (3 coins x 3 profiles) |
| `build_3d_signals.py` | same | 3D candle aggregation with death/golden cross signals |
| `test_3d_bias.py` | same | 3D death cross symmetric bias evaluation |
| `test_3d_bias_v2.py` | same | 3D death cross bear-only filter variant |
| `test_top_bottom_bias.py` | same | Top + bottom signal combo testing |
| `test_top_3d_structure_bias.py` | same | Top + 3D HH_HL structure clear |
| `test_top_3d_combo_bias.py` | same | Top + 3D HH_HL + SMA50 combo |
| `test_trailing_stop.py` | same | Trailing stop effectiveness (5 variants) |
| `test_cfgi_bias.py` | same | Raw CFGI < threshold as bottom signal |
| `test_cfgi_bias_v2.py` | same | Coin-specific CFGI + ROC momentum |
| `test_cfgi_rsi_bias.py` | same | CFGI RSI (RSI applied to CFGI) — per-coin, all variants |
| `run_cfgi_rsi_grid.py` | same | Full 9-combo grid with CFGI_RSI < 35 bear bias |
| `backfill_link_xrp.py` | same | LINK/XRP 1h backfill + daily build from Binance |

---

## 11. Lessons Learned

1. **Unit mismatch bugs are silent killers.** `price_vs_sma200` stored as percentage (32.55) but threshold was 0.20 (decimal). Blocked every MARKUP entry for 5+ years. Always verify units match between signal values and thresholds.

2. **Multiple files with same class name = disaster.** `v13_backtest_v8.py` (38KB) and `v13_phase_backtest_v8.py` (43KB) both contain `class V13BacktestV8`. Only the 43KB file is correct. Went through 3 wrong engines before finding the right one.

3. **Deep warmup is non-negotiable.** 2W StochRSI needs ~784 days. Without Jan 2019 backfill, Oct 2020 signals were invalid. Always backfill sufficient history before backtesting.

4. **Daily collector cron wipes backfilled data.** `rebuild_daily()` does DELETE+rebuild from 1h candles. USDT pairs get destroyed. Use USDC pairs only.

5. **Bear market rallies produce genuine bullish structure.** Weekly HH_HL can't distinguish bear bounces from real bull starts because the structure IS bullish on both timeframes during a rally.

6. **Structure confirmation gates must be symmetric.** If MARKUP requires HH_HL ≥ 2, MARKDOWN must require LH_LL ≥ 2. Asymmetric gates create asymmetric risk exposure.

7. **No single daily signal separates corrections from distributions** at the point of entry. Distinguishing features (duration, depth, CFGI) are only clear in hindsight.

8. **Paper bot is ground truth.** When backtest and paper bot disagree, investigate. The 10-15% gap from daily vs 1h granularity is expected.

9. **Death Cross / SMA200 reclaim causes excessive chattering.** During consolidation, price oscillates near SMA200, causing dozens of daily bias flips. Not suitable as a regime trigger.

10. **DCA PnL is not total PnL.** Real money in V13 comes from markup sells (+32-374%) and short profits (+9-52%), not DCA scalps ($1-4). Track all closed trade P&L.
