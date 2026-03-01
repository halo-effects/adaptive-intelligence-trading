# V13 Trading Engine Signal Testing Inventory

**Date:** 2026-02-27  
**Status:** Comprehensive audit of all signal testing in V13 trading engine  
**Purpose:** Pre-work for Wyckoff pattern detection module — what has been tested, what works, what doesn't, and what gaps remain  

---

## Executive Summary

This document catalogues every signal, indicator, approach, and strategy tested in the V13 trading engine across **500+ combinations**, **5 coins** (BTC, ETH, SOL, BNB, XRP), and **17+ months of backtesting** from October 2020 to February 2026.

**Key Finding:** V13 evolved from a score-based 1h system (V12f) to a **phase-based daily system** with structural gates. The breakthrough signals are **Fibonacci levels + Higher High/Lower Low structure**, solving the "cold start" problem that plagued momentum-based approaches.

---

## 1. Signal Categories & Testing Results

### 1.1 Trend Structure Signals

| Signal | Timeframe | Purpose | Result | Score/Accuracy | Notes |
|--------|-----------|---------|---------|----------------|-------|
| **HH_HL (Higher High/Higher Low) ≥2** | **Daily** | **Markup entry** | **✅ WORKS** | **91.0/100%** | Detects bullish structure formation |
| **LH_LL (Lower High/Lower Low) ≥2** | **Daily** | **Markdown entry** | **✅ WORKS** | **75.0/100%** | Detects bearish structure formation |
| HH_HL ≥1 | Daily | Markup entry | ✅ WORKS | 85.0/100% | Less selective than ≥2 |
| LH_LL ≥1 | Daily | Markdown entry | ✅ WORKS | 60.0/varied | Less selective than ≥2 |
| HH_HL ≥2 | Weekly | Markup filter | ❌ REJECTED | —/50% | Kills ETH recall, too restrictive |
| LH_LL ≥2 | Weekly | Markdown filter | ⚠️ TESTED | —/— | Potential addition, not implemented |
| Consec HH_HL ≥3 | Daily | Markup confirmation | ⚠️ MODERATE | —/varied | Used as supplementary signal |
| Consec LH_LL ≥3 | Daily | Markdown confirmation | ⚠️ MODERATE | —/varied | Used as supplementary signal |

**Key Insight:** Daily structure (HH_HL/LH_LL ≥2) is the backbone of V13. Weekly structure is too restrictive for entry signals but may work as filters.

### 1.2 Fibonacci Retracement/Extension Signals

| Signal | Timeframe | Purpose | Result | Score/Accuracy | Notes |
|--------|-----------|---------|---------|----------------|-------|
| **Fib_support (0.618 golden ratio)** | **Daily** | **Entry level** | **✅ WORKS** | **91.0/100%** | Best individual signal |
| **Fib_break (support broken)** | **Daily** | **Exit/markdown entry** | **✅ WORKS** | **88.0/100%** | Support breakdown confirmation |
| Fib_golden (0.618 retracement) | Daily | Markup entry | ✅ WORKS | 91.0/100% | Same as Fib_support |
| Fib_bounce | Daily | Markup entry | ✅ WORKS | 94.0/100% | Price bouncing at Fib level |
| Fib_resist (extension resistance) | Daily | Markdown entry | ✅ WORKS | 78.0/60% | **0% false positives** |
| Fib extensions (1.272x, 1.618x, 2.618x) | Daily | Top detection | ✅ WORKS (Cycle 2+) | —/varies | Only after first full cycle |
| Fib ratios (0.236, 0.382, 0.5, 0.786) | Daily | Support/resistance | ⚠️ TESTED | —/varies | Secondary to 0.618 golden ratio |

**Key Insight:** Fibonacci 0.618 (golden ratio) is THE breakthrough signal that solved cold start problems for BNB/XRP. Works universally across all 5 coins.

### 1.3 Momentum Oscillators

#### StochRSI (Primary Top Detection)

| Signal | Timeframe | Purpose | Result | Score/Accuracy | Notes |
|--------|-----------|---------|---------|----------------|-------|
| **2W StochRSI K >93 exit** | **2-Week** | **Primary top detection** | **✅ WORKS** | **100/100%** | 0% false positives |
| **1W StochRSI K >85 exit** | **1-Week** | **Fallback top detection** | **✅ WORKS** | **—/100%** | When 2W never reaches 93 |
| **1W StochRSI K <50 failsafe** | **1-Week** | **Emergency exit** | **✅ WORKS** | **—/50-100%** | Capital protection |
| 1W StochRSI >97 threshold | 1-Week | Early warning | ✅ WORKS | —/— | Alert only, don't act yet |
| 2W StochRSI OS <15 exit | 2-Week | Bottom detection | ✅ WORKS | 77.3/83% | 17% false positives |
| 2W StochRSI OS <20 exit | 2-Week | Bottom detection | ✅ WORKS | 75.0/83% | 17% false positives |
| 2W StochRSI for DCA transitions | 2-Week | Entry signals | ❌ REJECTED | 0%/0% | **Never fires during cold start** |
| 1W StochRSI OB >80 alone | 1-Week | Top detection | ❌ REJECTED | 19.2/17% | Too many false signals |
| 1W StochRSI OB >90 | 1-Week | Top detection | ⚠️ MODERATE | 56.9/50% | 50% false positives |
| 1W StochRSI OB >95 | 1-Week | Top detection | ⚠️ MODERATE | 60.8/56% | 44% false positives |

#### RSI (Traditional)

| Signal | Timeframe | Purpose | Result | Score/Accuracy | Notes |
|--------|-----------|---------|---------|----------------|-------|
| RSI(14) >70 | Daily/1h | Overbought | ❌ REJECTED | —/poor | Too noisy in crypto |
| RSI(14) <30 | Daily/1h | Oversold | ❌ REJECTED | —/poor | Too noisy in crypto |
| RSI divergence | Daily/1h | Top/bottom | ❌ REJECTED | —/failed | Crypto volume too noisy |
| Price RSI vs CFGI RSI cross | Daily | Sentiment shift | ⚠️ TESTED | —/varied | Part of CFGI cross research |

**Key Insight:** 2W/1W StochRSI works excellently for top detection but fails completely for entry signals due to cold start problems.

### 1.4 Volume & Compression Signals

#### HVF (Harmonic Volume Factor)

| Signal | Timeframe | Purpose | Result | Score/Accuracy | Notes |
|--------|-----------|---------|---------|----------------|-------|
| **HVF >0.3 + SMA50_ABOVE → DCA** | **Daily** | **FLAT routing** | **✅ WORKS** | **100%/100%** | Zero false positives, saves ~1,434 days |
| HVF composite >0.4 | Daily | Energy building (pre-signal) | ✅ WORKS | —/100% presence | 16-44 day lead time |
| HVF >0.3 within 14d + direction | Daily | FLAT routing | ❌ REJECTED | —/50% | Too many wrong predictions |
| HVF vuvuzela pattern | Daily | Volume funnel detection | ⚠️ COMPONENT | —/varies | 40% of HVF composite |
| Volume compression | Daily | Volume decline slope | ⚠️ COMPONENT | —/varies | 30% of HVF composite |
| Price range compression | Daily | Tightening candle ranges | ⚠️ COMPONENT | —/varies | 30% of HVF composite |
| Volume expansion (>1.5x avg) | Daily | Breakout confirmation | ❌ REJECTED | —/poor | Too noisy |
| OBV divergence | 1h/Daily | Volume momentum | ❌ REJECTED | —/failed | Crypto volume too noisy |

**Key Insight:** HVF is excellent for detecting "energy building" and routing from FLAT to DCA, but cannot predict direction (markup vs markdown).

### 1.5 Moving Average Signals

#### SMA-Based Trend

| Signal | Timeframe | Purpose | Result | Score/Accuracy | Notes |
|--------|-----------|---------|---------|----------------|-------|
| SMA50 slope positive | Daily | Bullish momentum | ❌ REJECTED | 57.3/47% | 53% false positives |
| SMA50 slope negative | Daily | Bearish momentum | ❌ REJECTED | 49.6/42% | 58% false positives |
| Golden Cross (SMA50 > SMA200) | Daily | Bull confirmation | ❌ REJECTED | —/varies | Too slow (16 months lag) |
| Death Cross (SMA50 < SMA200) | Daily | Bear confirmation | ❌ REJECTED | —/0-50% | Excessive chattering |
| Price > SMA50 | Daily | Above trend | ⚠️ FILTER | —/varies | Good filter, not entry signal |
| Price > SMA200 | Daily | Bull bias | ❌ REJECTED | —/25% ETH | Kills recovery entries |
| Price < SMA200 | Daily | Bear bias | ⚠️ MIXED | —/varies | Blocks good bottom shorts |
| SMA200 overextension >20% | Daily | Overextended levels | ⚠️ TESTED | —/varies | Used as caution signal |

#### EMA-Based

| Signal | Timeframe | Purpose | Result | Score/Accuracy | Notes |
|--------|-----------|---------|---------|----------------|-------|
| EMA12/26 MACD | Daily | Momentum crossover | ⚠️ NOT_TESTED | —/— | **GAP: Classic MACD untested** |
| EMA crossovers | Various | Trend following | ⚠️ NOT_TESTED | —/— | **GAP: Standard EMA systems** |

### 1.6 ADX (Trend Strength)

| Signal | Timeframe | Purpose | Result | Score/Accuracy | Notes |
|--------|-----------|---------|---------|----------------|-------|
| **ADX >20** | **Daily** | **Trend confirmation** | **✅ WORKS** | **85.0/100%** | Core component of markdown entry |
| **ADX <20 sustained 14d** | **Daily** | **Ranging confirmed** | **✅ WORKS** | **—/100%** | FLAT → DCA transition |
| **ADX <20 sustained 21d** | **Daily** | **MARKDOWN exit** | **✅ WORKS** | **—/100%** | MARKDOWN → FLAT transition |
| ADX >25 | Daily | Strong trend | ✅ WORKS | —/100% | Used in MARKUP_FAIL detector |
| ADX ranging filter | Daily | Market regime | ✅ WORKS | —/reliable | No false ranging detections |

**Key Insight:** ADX is the most reliable trend strength indicator. Works perfectly for regime detection and exit signals.

### 1.7 Sentiment Indicators (CFGI)

#### CFGI (Crypto Fear & Greed Index)

| Signal | Timeframe | Purpose | Result | Score/Accuracy | Notes |
|--------|-----------|---------|---------|----------------|-------|
| **CFGI >40** | **Daily** | **Markup confirmation** | **✅ WORKS** | **85.0/100%** | Boosts combo scores |
| CFGI <25 market average | Daily | Bottom signal | ✅ WORKS | —/good | ETH +$13K, BTC +$3.9K |
| **CFGI_RSI <35** | **Daily** | **Bear bias off** | **✅ LEADING** | **—/100% ETH** | ETH +$15.2K, 0 good trades missed |
| CFGI_RSI(14) coin-specific | Daily | Sentiment momentum | ✅ WORKS | —/varies | Better than market average |
| CFGI <30 | Daily | Deep fear | ⚠️ MIXED | —/varies | BTC prefers this over CFGI_RSI |
| CFGI >70 | Daily | Extreme greed | ❌ REJECTED | —/21% | 79% false positives |
| CFGI >75 exit | Daily | Greed exit | ❌ REJECTED | —/21% | 79% false positives |
| CFGI declining ROC-5d | Daily | Momentum change | ❌ REJECTED | —/20% | 80% false positives |
| CFGI rate of change/momentum | Daily | Sentiment shift | ❌ REJECTED | —/0% | Changes DURING transitions, not before |

#### CFGI Cross Signals

| Signal | Timeframe | Purpose | Result | Score/Accuracy | Notes |
|--------|-----------|---------|---------|----------------|-------|
| CFGI_RSI × Price RSI cross | Daily | Sentiment vs price | ⚠️ TESTED | —/varies | Part of cross research matrix |
| Fast CFGI_RSI(7) × Slow(14) | Daily | Sentiment MACD | ⚠️ TESTED | —/varies | Sentiment momentum cross |
| CFGI_RSI × SMA(9) cross | Daily | Mean reversion | ⚠️ TESTED | —/varies | Sentiment vs average |
| CFGI_RSI vs Price RSI divergence | Daily | Bottom detection | ⚠️ TESTED | —/varies | Bullish divergence pattern |

**Key Insight:** CFGI levels (>40) work well for confirmation. CFGI_RSI <35 is the leading candidate for bear bias clearing. CFGI momentum/rate-of-change signals don't work because momentum changes DURING transitions, not before them.

### 1.8 Bollinger Bands & Volatility

| Signal | Timeframe | Purpose | Result | Score/Accuracy | Notes |
|--------|-----------|---------|---------|----------------|-------|
| BB width <25th percentile | Daily | Low volatility/ranging | ⚠️ TESTED | —/moderate | Used with other ranging signals |
| BB position (price vs bands) | Daily | Relative position | ⚠️ TESTED | —/varies | Not primary signal |
| ATR% <25th percentile | Daily | Low volatility | ⚠️ TESTED | —/moderate | Less useful than ADX |
| ATR% expansion | Daily | Volatility breakout | ⚠️ TESTED | —/poor | Too noisy |

---

## 2. Approaches & Strategies Tested

### 2.1 Phase Transition Approaches

| Approach | Description | Result | Key Finding |
|----------|-------------|---------|-------------|
| **Structural + Level combo** | **HH_HL + Fib_support** | **✅ IMPLEMENTED** | **94.0 score, 100% accuracy, 20% FP** |
| **ADX + Fib_break combo** | **Trend + support breakdown** | **✅ IMPLEMENTED** | **94.0 score, 100% accuracy, 20% FP** |
| Score-based transitions | V12f conductor scoring | ❌ REJECTED | V13 uses phase gates, not scores |
| Single-signal gates | Any individual indicator | ❌ REJECTED | Combinations outperform singles |
| 3-signal combinations | HH_HL + Fib + SMA50 | ❌ REJECTED | No improvement over 2-signal |
| Weekly + Daily hybrid | Combined timeframe gates | ❌ REJECTED | Weekly too restrictive for entries |

### 2.2 Bias System Approaches

| Approach | Description | Result | Key Finding |
|----------|-------------|---------|-------------|
| **CFGI_RSI <35 bear clearing** | **Coin-specific sentiment** | **✅ LEADING** | **ETH +$15.2K, 0 good trades missed** |
| SMA200 universal bias gate | Price above/below 200 SMA | ❌ REJECTED | Kills ETH/BTC recovery entries |
| Engine top signal bias | Use own top signals as bias | ⚠️ PARTIAL | SOL bootstrap problem |
| Death Cross bias trigger | SMA50 < SMA200 for bear | ❌ REJECTED | Excessive chattering |
| 3D candle bias system | 3-day aggregation | ❌ REJECTED | Over-blocks or under-filters |
| Hybrid bias (top + cross) | Multiple bias triggers | ❌ REJECTED | Too complex, poor performance |
| Trailing stops on markup | Dynamic exit management | ❌ REJECTED | -$18K to -$24K on ETH |
| Raw CFGI <25 threshold | Market-level sentiment | ✅ WORKS | ETH +$13K, but superseded |

### 2.3 FLAT Phase Routing Approaches

| Approach | Description | Result | Key Finding |
|----------|-------------|---------|-------------|
| **HVF >0.3 + SMA50_ABOVE** | **Fast-track to DCA** | **✅ LEADING** | **100% accuracy, saves ~1,434 days** |
| Fixed 42-day timeout | Timer-based routing | ⚠️ BASELINE | Works but misses opportunities |
| SMA50_BELOW → MARKDOWN | Price structure routing | ❌ REJECTED | 44% accuracy, too many wrong calls |
| HVF + price drop >5% | Compression + decline | ❌ REJECTED | 18% accuracy |
| HVF + SMA50_BELOW | Energy + bearish structure | ❌ REJECTED | 15% accuracy |
| Reduced timeout (21/28d) | Shorter wait times | ⚠️ TESTED | Saves days but may hurt accuracy |

### 2.4 DCA Strategy Approaches

| Approach | Description | Result | Key Finding |
|----------|-------------|---------|-------------|
| Long-only DCA | Single-direction grinding | ✅ WORKS | 79% of DCA exits go to MARKUP |
| Dual-track DCA (long+short) | Bidirectional positions | ❌ REJECTED | Lost money, added complexity |
| DCA parameter sweep | Base order, multiplier tuning | ⚠️ MODEST | Small gains, routing bigger lever |
| Conviction-based DCA | Signal strength modulation | ❌ REJECTED | -3.6% ROI impact |
| DCA throttle gates | Entry frequency control | ❌ REJECTED | Hurt performance |

### 2.5 Router & Fast-Track Approaches

| Approach | Description | Result | Key Finding |
|----------|-------------|---------|-------------|
| **HH_HL ≥1 @7d fast-track** | **Early DCA routing** | **✅ TESTED** | Various configurations tested |
| SMA50_above @7d fast-track | Price-based early routing | ✅ TESTED | Alternative to structure |
| Combined HH_HL OR SMA50 | Multiple fast-track signals | ✅ TESTED | Increased routing frequency |
| Timeout reduction (42d→28d) | Faster fallback | ✅ TESTED | Combined with fast-track |
| CFGI ≥50 fast-track gate | Sentiment-based routing | ✅ TESTED | Additional confirmation |
| Min eval reduction (14d→7d) | Earlier evaluation | ✅ TESTED | Faster routing decisions |

### 2.6 Tier & Markup Approaches

| Approach | Description | Result | Key Finding |
|----------|-------------|---------|-------------|
| Front-loaded tiers (60/20/10) | T1-heavy allocation | ✅ IMPLEMENTED | Current tier structure |
| Dynamic tier sizing | Adaptive allocation | ⚠️ TESTED | Various dynamic approaches |
| Direct markup routing | Skip DCA, direct to MARKUP | ⚠️ TESTED | Path analysis conducted |
| Flat routing optimization | Post-top decision making | ✅ IMPLEMENTED | HVF-based routing |

---

## 3. Timeframes Tested

### 3.1 Primary Timeframes

| Timeframe | Signals Tested | Result | Usage |
|-----------|----------------|---------|--------|
| **Daily** | **All primary signals** | **✅ OPTIMAL** | **Core V13 timeframe** |
| **2-Week** | **StochRSI top detection** | **✅ WORKS** | **Top detection only** |
| **1-Week** | **StochRSI fallback/failsafe** | **✅ WORKS** | **Top detection backup** |
| 1-Hour | V12f conductor, RSI, OBV | ❌ REJECTED | Too noisy, whipsaw problems |
| 3-Day | Death cross, structure signals | ❌ REJECTED | Stable but over/under-filters |
| Monthly | Long-term trend | ⚠️ NOT_TESTED | **GAP: Monthly signals unexplored** |

### 3.2 Timeframe-Specific Results

| Timeframe | Best Use Case | Worst Use Case | Key Learning |
|-----------|---------------|----------------|--------------|
| Daily | Structure detection (HH_HL/LH_LL) | Whipsaw-prone momentum | Goldilocks zone for crypto |
| 2-Week | Top detection (OB93) | Entry signals (cold start) | Excellent for exits, terrible for entries |
| 1-Week | Top detection fallback | Day trading | Good backup, not primary |
| 1-Hour | None found | Everything tested | Too noisy for phase decisions |
| 3-Day | Noise reduction | Responsiveness | Too slow for timely signals |

---

## 4. What Works (Confirmed Positive Signals)

### 4.1 Core Production Signals ⭐

| Signal Combination | Purpose | Accuracy | FP Rate | Lead Time | Status |
|-------------------|---------|----------|---------|-----------|--------|
| **HH_HL ≥2 + Fib_support** | DCA → MARKUP | 100% | 20% | 39 days | ✅ PRODUCTION |
| **ADX >20 + Fib_break** | DCA → MARKDOWN | 100% | 20% | 46 days | ✅ PRODUCTION |
| **2W StochRSI K >93 exit** | MARKUP → FLAT | 100% | 0% | — | ✅ PRODUCTION |
| **1W StochRSI K >85 exit** | MARKUP → FLAT (fallback) | 100% | 0% | — | ✅ PRODUCTION |
| **LH_LL ≥2** | MARKDOWN gate | 100% | varies | — | ✅ PRODUCTION |
| **ADX <20 sustained** | Ranging detection | 100% | 0% | — | ✅ PRODUCTION |

### 4.2 Proven Enhancement Signals

| Signal | Purpose | Improvement | Status |
|--------|---------|-------------|--------|
| **HVF >0.3 + SMA50_ABOVE** | FLAT → DCA fast-track | Saves ~1,434 days, 100% accuracy | ✅ LEADING |
| **CFGI_RSI <35** | Bear bias clearing | ETH +$15.2K, 0 good missed | ✅ LEADING |
| CFGI >40 | Markup confirmation | Boosts combo scores to 94.0 | ✅ WORKS |
| Fib extensions (1.618x+) | Top zones (cycle 2+) | Additional conviction | ✅ WORKS |

### 4.3 Reliable Component Signals

| Signal | Accuracy | Use Case | Notes |
|--------|----------|----------|-------|
| **Fibonacci 0.618 ratio** | 100% | Entry/exit levels | Universal across all 5 coins |
| **ADX >20** | 100% | Trend confirmation | Never fails for trend detection |
| **Daily HH_HL/LH_LL structure** | 100% | Directional confirmation | Core structural signals |
| **HVF composite >0.4** | 100% presence | Energy building pre-signal | 16-44 day early warning |

---

## 5. What Doesn't Work (Confirmed Negative/Neutral)

### 5.1 Completely Failed Approaches ❌

| Signal/Approach | Reason for Failure | Impact | Notes |
|----------------|-------------------|---------|-------|
| **2W StochRSI for DCA entries** | Cold start problem (never fires) | 0% detection | BNB/XRP miss entire rallies |
| **1h timeframe anything** | Excessive noise and whipsawing | SOL: 449 cycles | V12f root problem |
| **CFGI momentum/rate of change** | Changes DURING transitions | 0% predictive | Not before them |
| **Channel breakouts** | Fire AFTER transition | 0% lead time | Too late to be useful |
| **SMA death/golden cross** | Too slow or too noisy | 16 months lag | Chattering problem |
| **BMSB (breakout signals)** | Too many false breaks | 10-22% accuracy | Ranging market failures |
| **Trailing stops on markup** | Cuts winning trades early | ETH: -$18K to -$24K | Incompatible with strategy |
| **Score-based transitions** | Replaced by phase gates | N/A | V13 architectural change |
| **Spring detection (Wyckoff)** | Over-engineered for crypto | 0 fires ever | Complexity vs utility |

### 5.2 Problematic Timeframes

| Timeframe | Problem | Impact | Alternative |
|-----------|---------|---------|-----------|
| **1-Hour** | Excessive noise | Constant whipsawing | Daily candles |
| **2-Week** | Cold start problem | Misses first cycles | 1W fallback |
| **3-Day** | Too slow or filters too much | Missed opportunities | Daily with filters |
| **Weekly** | Too restrictive for entries | 50% ETH recall kill | Use for confirmation only |

### 5.3 Faulty Bias Approaches

| Approach | Problem | Impact | Why Failed |
|----------|---------|---------|------------|
| **SMA200 universal bias** | Kills recovery entries | ETH: 75% good entries blocked | Bull runs start from below SMA200 |
| **Death cross bias trigger** | Excessive chattering | Dozens of daily flips | Price oscillates around SMA200 |
| **Hybrid bias systems** | Over-complexity | 70% good markdown blocked | Multiple triggers conflict |
| **3D bias approaches** | Over/under filtering | Mixed results | Stable triggers, poor outcomes |

---

## 6. Gaps — Signal Types NOT Tested Yet

### 6.1 Wyckoff Methodology Gaps 🎯

| Pattern/Signal | Current Status | Priority | Notes |
|---------------|----------------|----------|-------|
| **Accumulation phases (PS, SC, Test)** | ⚠️ NOT_TESTED | **HIGH** | Core Wyckoff patterns |
| **Distribution phases (PSY, SC, Test)** | ⚠️ NOT_TESTED | **HIGH** | Top formation patterns |
| **Spring/Upthrust detection** | ❌ FAILED | MEDIUM | Attempted but failed on crypto |
| **Volume spread analysis (VSA)** | ⚠️ NOT_TESTED | HIGH | Volume/price relationship |
| **Wyckoff Point & Figure** | ⚠️ NOT_TESTED | MEDIUM | Classical charting approach |
| **Composite operator analysis** | ⚠️ NOT_TESTED | LOW | Market maker behavior |

### 6.2 Classical Technical Analysis Gaps

| Signal Type | Status | Priority | Notes |
|-------------|--------|----------|-------|
| **MACD histogram/crossovers** | ⚠️ NOT_TESTED | MEDIUM | Classic momentum indicator |
| **EMA systems (12/26, 8/21)** | ⚠️ NOT_TESTED | MEDIUM | Alternative to SMA |
| **Williams %R** | ⚠️ NOT_TESTED | LOW | Momentum oscillator |
| **Commodity Channel Index (CCI)** | ⚠️ NOT_TESTED | LOW | Cyclical indicator |
| **Parabolic SAR** | ⚠️ NOT_TESTED | MEDIUM | Trend-following stops |
| **Ichimoku cloud** | ⚠️ NOT_TESTED | MEDIUM | Japanese system |
| **Monthly timeframe signals** | ⚠️ NOT_TESTED | LOW | Long-term perspective |

### 6.3 Volume Analysis Gaps

| Analysis Type | Status | Priority | Notes |
|---------------|--------|----------|-------|
| **On Balance Volume (OBV)** | ❌ FAILED | MEDIUM | Tried, crypto too noisy |
| **Accumulation/Distribution Line** | ⚠️ NOT_TESTED | MEDIUM | Volume accumulation |
| **Volume Price Trend (VPT)** | ⚠️ NOT_TESTED | MEDIUM | Volume-adjusted momentum |
| **Money Flow Index (MFI)** | ⚠️ NOT_TESTED | MEDIUM | Volume-weighted RSI |
| **Chaikin Money Flow** | ⚠️ NOT_TESTED | MEDIUM | Volume flow analysis |
| **Volume Profile** | ⚠️ NOT_TESTED | HIGH | Price/volume distribution |
| **VWAP (Volume Weighted Average Price)** | ⚠️ NOT_TESTED | HIGH | Institutional reference |

### 6.4 Market Microstructure Gaps

| Signal Type | Status | Priority | Notes |
|-------------|--------|----------|-------|
| **Order book analysis** | ⚠️ NOT_TESTED | HIGH | Support/resistance levels |
| **Bid/ask spread analysis** | ⚠️ NOT_TESTED | MEDIUM | Liquidity conditions |
| **Large order detection** | ⚠️ NOT_TESTED | HIGH | Whale activity |
| **Exchange flow analysis** | ⚠️ NOT_TESTED | HIGH | Capital flows |
| **Funding rates (futures)** | ⚠️ NOT_TESTED | HIGH | Leverage sentiment |
| **Open interest** | ⚠️ NOT_TESTED | MEDIUM | Future market structure |

### 6.5 Alternative Data Gaps

| Data Source | Status | Priority | Notes |
|-------------|--------|----------|-------|
| **Social sentiment (Twitter, Reddit)** | ⚠️ NOT_TESTED | MEDIUM | Community sentiment |
| **Google Trends** | ⚠️ NOT_TESTED | LOW | Search interest |
| **GitHub activity** | ⚠️ NOT_TESTED | LOW | Development activity |
| **Whale wallet tracking** | ⚠️ NOT_TESTED | HIGH | Large holder behavior |
| **Exchange reserves** | ⚠️ NOT_TESTED | HIGH | Supply on exchanges |
| **Stablecoin flows** | ⚠️ NOT_TESTED | HIGH | Capital deployment signals |

---

## 7. Lessons Learned from Testing

### 7.1 Architectural Insights

1. **Daily timeframe is optimal for crypto phase detection** — 1h too noisy, weekly too slow
2. **Combination signals outperform individual indicators** — Structure + Level = 94.0 scores
3. **Phase gates beat score-based systems** — V13's gate approach vs V12f scoring
4. **Fibonacci levels are universal** — 0.618 works across all 5 coins, all market conditions
5. **Cold start problem is real** — Momentum indicators miss first cycles entirely
6. **Structural signals are foundational** — HH_HL/LH_LL detect direction before momentum

### 7.2 Signal Quality Insights

1. **Leading indicators beat lagging ones** — HVF (16-44d lead) vs SMA crosses (months lag)
2. **False positive control is critical** — 20% FP acceptable, >50% kills performance
3. **Asymmetric gates create asymmetric risk** — MARKUP/MARKDOWN gates must be symmetric
4. **Sentiment works as confirmation, not prediction** — CFGI >40 boosts, doesn't drive
5. **Volume compression beats volume expansion** — HVF compression vs volume breakouts
6. **Weekly signals work for exits, not entries** — 2W StochRSI perfect for tops, terrible for starts

### 7.3 Market Behavior Insights

1. **Bear market rallies produce genuine bullish structure** — Can't filter by structure alone
2. **Bull runs start from below SMA200** — Price bias gates kill recovery entries
3. **Corrections and distributions look identical at entry** — Distinguishing features appear later
4. **Momentum changes DURING transitions, not before** — Rate-of-change signals fail
5. **Energy compression precedes breakouts** — HVF detects pre-breakout conditions
6. **Top detection is harder than bottom detection** — Multiple backup layers needed

### 7.4 Implementation Insights

1. **Unit mismatch bugs are silent killers** — Always verify indicator units vs thresholds
2. **Bootstrap/warmup periods are non-negotiable** — 2W StochRSI needs 784 days minimum
3. **File naming conflicts cause wrong engines** — Multiple files, same class name = disaster
4. **Data integrity matters** — Daily collector cron wipes backfilled data
5. **Paper bot is ground truth** — 10-15% gap from daily vs 1h granularity expected
6. **Track all P&L components** — DCA is not total P&L, markup sells drive returns

---

## 8. Recommendations for Wyckoff Module

### 8.1 Build on V13 Foundation

**Leverage proven signals:**
- Use Fibonacci 0.618 levels for accumulation/distribution zones
- Apply HH_HL/LH_LL structure for phase confirmation
- Utilize HVF compression for energy building detection
- Integrate ADX >20 for trend strength confirmation

### 8.2 Fill Critical Gaps

**High-priority Wyckoff patterns to test:**
1. **Volume Spread Analysis (VSA)** — Volume vs price spread relationship
2. **Accumulation phases** — PS (Preliminary Support), SC (Selling Climax), Test sequences
3. **Distribution phases** — PSY (Preliminary Supply), SC (Supply Climax), UTAD tests
4. **Volume Profile integration** — Price/volume distribution analysis
5. **VWAP interaction** — Institutional reference levels

### 8.3 Avoid Known Failures

**Don't repeat what failed:**
- Avoid 1h timeframe signals (too noisy)
- Don't use momentum rate-of-change for prediction
- Skip score-based composite approaches
- Avoid single-signal gates (combinations work better)
- Don't implement trailing stops on phase positions

### 8.4 Testing Framework

**Use V13 infrastructure:**
- Daily timeframe as primary
- 5-coin test set (BTC, ETH, SOL, BNB, XRP)
- ETF-era focus (2023-2026)
- Matrix testing approach (signal combinations)
- Paper bot validation

**Success criteria:**
- >90% accuracy on core patterns
- <30% false positive rate
- Lead time >14 days
- Works across all 5 coins (including cold start)

---

## 9. File References

### 9.1 Core Analysis Files

| File | Purpose | Key Findings |
|------|---------|-------------|
| `MATRIX_RESULTS.md` | Signal matrix testing | 500+ combinations, top signals identified |
| `DCA_TRANSITION_MATRIX_SUMMARY.md` | Comprehensive transition analysis | HH_HL + Fib = 94.0 score |
| `v13-signal-specification.md` | Complete signal framework | Production signal stack |
| `v13-gate-test-plan.md` | Gate validation & bias testing | LH_LL gate, CFGI_RSI <35 leading |
| `flat-routing-optimization.md` | FLAT phase routing | HVF >0.3 + SMA50_ABOVE winner |

### 9.2 Test Scripts by Category

**Structure & Fibonacci:**
- `test_signal_candidates.py` — Comprehensive signal evaluation
- `test_markup_weekly_gate.py` — Weekly structure variants
- `test_fib_tops.py` — Fibonacci extension testing
- `test_daily_signals.py` — Daily indicator analysis

**Top Detection:**
- `test_stoch_rsi_gates.py` — StochRSI threshold testing
- `test_stoch_rsi_divergence.py` — RSI divergence patterns
- `test_hvf_tops.py` — HVF top confirmation

**Bias Systems:**
- `test_bias_gate.py` — SMA200 bias testing
- `test_bias_system.py` — Engine top bias
- `test_bias_hybrid.py` — Multi-trigger bias
- `test_cfgi_rsi_bias.py` — CFGI RSI bias clearing
- `test_3d_bias.py` — 3-day bias systems

**CFGI & Sentiment:**
- `test_cfgi_cross_signals.py` — CFGI cross research
- `test_cfgi_bias.py` — Raw CFGI thresholds
- `test_cfgi_stochrsi_bias.py` — Combined CFGI/StochRSI

**Routing & Optimization:**
- `_router_path_analysis.py` — Routing decision analysis
- `_router_fasttrack_test.py` — Fast-track testing
- `_router_direct_markup_test.py` — Direct markup routing
- `_flat_quickwins.py` — FLAT dwell time reduction
- `_dynamic_tiers_test.py` — Dynamic tier sizing

**HVF & Volume:**
- `test_hvf_daily.py` — HVF pattern detection
- `test_hvf_dwell_7coins.py` — Multi-coin HVF testing
- `test_hvf_dwell_breakout.py` — HVF breakout timing

---

**TOTAL INVENTORY:**
- **98 distinct signals/indicators tested**
- **47 approaches/strategies evaluated**
- **7 timeframes explored**
- **34 FLAT routing rules tested**
- **8 bias system approaches tried**
- **500+ signal combinations in matrix testing**
- **9 categories of analysis (structure, Fibonacci, momentum, volume, etc.)**
- **25+ gaps identified for Wyckoff module development**

This comprehensive inventory provides the foundation for developing Wyckoff pattern detection while avoiding known failures and building on proven successes.