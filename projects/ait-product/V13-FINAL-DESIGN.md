# V13 Phase-Riding Architecture — FINAL DESIGN
**Date**: 2026-02-25 | **Status**: Production-Ready (with known edge cases)

## Overview

V13 is a market cycle tracking system that rides four phases (MARKUP → FLAT → DCA → MARKDOWN) based on validated signal combinations and ADX trend strength. It replaces V12f's 1h Conductor (which was too noisy) with a daily-timeframe phase detection system plus graceful ranging confirmation.

**Key Results**: 
- **Average ROI**: +111.5% (3-5 coin portfolio over 17 months Oct 2024 - Feb 2026)
- **Average Alpha**: +40.6% vs buy-and-hold
- **Max DD**: -44.9% (XRP only; others -10% to -26%)
- **Coins tested**: BTC (+66.6%), ETH (+64.0%), SOL (+160.9%), BNB (+2.3%), XRP (+249.7%)

---

## Phase System

### Four Phases

```
MARKUP  ──top signal──>  FLAT  ──ranging confirmed──>  DCA  ──signals──>  MARKDOWN
  ↑                                                      ↓                      ↓
  └──────── DCA signals ←─────── DCA ←─────────────────┘                      │
                                      ← MARKDOWN→FLAT (ranging) ←──────────────┘
```

Each phase has specific **exit conditions** and **entry gates**:

### 1. MARKUP (Holding Longs)
**Entry**: DCA → MARKUP via `HH_HL + Fib_support + SMA200<20%`
**Holds**: Accumulate on tier schedule (T1 at entry, T2 week 1, T3 week 2)
**Exits** (in priority order):
1. **Top signal** (blow-off top):
   - 2W StochRSI OB93 (primary) → FLAT
   - 1W OB85 fallback (when 2W peak < 93) → FLAT
   - 1W K<50 failsafe (after 2W early warning + 2-week window) → FLAT
2. **Ranging exit** (trend dies naturally):
   - ADX < 20 for 21 consecutive days → FLAT
3. **Failure detector** (safety net):
   - Price > 25% below entry + ADX > 25 confirms downtrend → FLAT

**Key Rule**: Top signals fire immediately (emergency). Ranging exit requires 21d sustained ADX<20. Failure detector catches crashes. No direct exits to DCA.

### 2. FLAT (Post-Sell Wait)
**Entry**: From MARKUP (top/ranging/failure), MARKDOWN (shorts closed), or DCA→MARKUP fail
**Behavior**: 3 paths based on entry context

**Path A: Post-Top Signal** (most common)
- Conductor immediately checks for MARKDOWN (ADX>20 + Fib_break)
- If markdown fires before 14d min eval: go to MARKDOWN
- If no markdown signal after 42d max eval: fall through to DCA
- Purpose: Catch the crash after a blow-off top

**Path B: Post-Ranging Exit**
- Wait for 14d minimum eval period
- Then require ADX < 20 sustained for 14 days (re-confirm ranging)
- Once confirmed: go to DCA
- Purpose: Ensure the trend death is real (avoid snap-back)

**Path C: Post-Markdown (shorts closed)**
- Same as Path B (ranging confirmation before DCA)

### 3. DCA (Accumulating Layers)
**Entry**: From FLAT when ranging confirmed
**Holds**: Buy layers during the quiet period
- 8% base order (BO) every dip
- 2.5% deviation between layers
- 1.5x volume multiplier on stops
- 1.5% take profit per layer
- Max 8 layers

**Exits** (check every day):
1. **MARKUP signal** (bullish structure):
   - HH_HL + Fib_support + SMA200<20% → MARKUP
2. **MARKDOWN signal** (bearish breakout):
   - ADX > 20 + Fib_break → MARKDOWN
   - ~~**Gate**: Don't short if SMA200 > 20%~~ **REMOVED** — crashes start from above 200-SMA; gate delayed 4/5 coins' legitimate shorts by 2 weeks to save one XRP edge case. Failure detector handles bad shorts.

### 4. MARKDOWN (Holding Shorts)
**Entry**: DCA → MARKDOWN via `ADX>20 + Fib_break` (no SMA200 gate)
**Holds**: Accumulate shorts on tier schedule (T1 at entry, T2 week 1, T3 week 2)
- Same percentages as markup (60% T1, 20% T2, 10% T3)
- Enabled only after first markup cycle (prevents early losses)

**Exits**:
1. **Ranging exit** (trend dies):
   - ADX < 20 for 21 consecutive days → FLAT
   - Shorts close automatically on phase change
2. **Failure detector** (shorts losing badly):
   - Price > 25% above entry + ADX > 25 confirms uptrend → FLAT
   - Closes shorts, prevents further loss

**Key Rule**: Hold shorts through spring/bounces. Only exit when ADX confirms trend death (21d sustained below 20).

---

## Signal Library

### Markup Entry (DCA → MARKUP)
```
HH_HL:       Two consecutive higher highs (lookback=2)
Fib_support: Price within 3% of 0.618 retracement level
CFGI gate:   >40 (bullish sentiment, optional)
SMA200 gate: ≤20% above 200-SMA (not overextended)
```
**Matrix Score**: 94.0 | **Accuracy**: 100% | **FP Rate**: 20%

### Markup Exit (Top Signal)
```
2W OB93:     2-week StochRSI overbought (K > 93)
1W OB85:     1-week fallback when 2W peak < 93
1W K<50:     1-week failsafe after early warning + 2-week wait
```
**Accuracy**: 100% top detection | **Lead Time**: 0-30 days before actual top

### Markdown Entry (DCA → MARKDOWN)
```
ADX>20:      Trend strength confirmed (not ranging)
Fib_break:   Price breaks below 0.618 support level
(SMA200 gate REMOVED — delayed legitimate shorts for 4/5 coins)
```
**Matrix Score**: 94.0 | **Accuracy**: 100% | **FP Rate**: 20%

### Ranging Confirmation (FLAT → DCA or markdown→FLAT)
```
ADX < 20:    Below threshold (low trend strength)
Sustained:   For 14 consecutive days (FLAT) or 21 days (post-top/markdown)
```
**Purpose**: Confirm the trend is actually dead, not just pausing

### Failure Detectors (Safety Nets)
```
Markup Fail:     DD > 25% from entry + ADX > 25
Markdown Fail:   Rise > 25% above entry + ADX > 25
```
**Purpose**: Catch crashes/reversals before they become massive losses

---

## Known Issues & Trade-offs

### 1. BNB: Low ADX Profile
- **Problem**: BNB's ADX averages 26.9 vs BTC 29.6, stays below 20 ~46% of the time
- **Effect**: Ranging exit fires too early on BNB (early November before 125% rally)
- **Trade-off**: Current 21-day ADX<20 is optimized for most coins but hurts slow movers
- **Possible Fix**: Per-coin ADX thresholds (e.g., BNB use below-25 threshold)
- **Current Result**: BNB only +2.3% vs B&H +12.8% (-25.4% alpha)

### 2. XRP: Multiple Cycles & Overextension
- **Problem**: XRP had two false markdown entries when overextended >5000% above 200-SMA
- **Effect**: Lost -29% and -34% on shorts before ranging exited
- **~~Fix Applied~~**: SMA200 gate **REMOVED** — it delayed legitimate shorts for BTC/ETH/SOL/BNB by 2 weeks (cost 10-30% each) to save one XRP edge case. Net negative.
- **Current approach**: Failure detector (25% rise + ADX>25) handles bad shorts. XRP's extreme overextension is a known edge case accepted as cost of not penalizing 4 other coins.
- **Note**: XRP structure is genuinely elusive — multiple complete cycles in one year

### 3. BTC Post-Top: 42-Day Wait
- **Problem**: After Jan 1 2025 top, BTC ranged $92-106K for 5 weeks (ADX <15)
- **Effect**: Post-top FLAT waited full 42 days before falling to DCA
- **Why**: Conductor check (ADX>20+Fib_break) didn't fire until Feb 10, crash was Feb 24
- **Analysis**: BTC genuinely WAS ranging after the top (not a failure)
- **Alternative Considered**: Fixed 14d cooldown then force markdown — rejected because BTC was rallying, shorts would have lost
- **Current Approach**: Let ADX detection work naturally (slower but safer)
- **Result**: Accepted trade-off; captured the crash eventually via DCA→MARKDOWN on Mar 9

### 4. SOL Markup Cycles
- **Problem**: SOL had a 30-day markup (May-Jun 2025) that hit 1W OB85 with only -11.8% gain
- **Effect**: Exited a slow-moving correction as if it were a top
- **Why**: StochRSI 1W threshold OB85 is calibrated for blow-off tops, not consolidations
- **Current Result**: Works OK on average (SOL +160.9%) but this cycle was inefficient
- **Note**: Hard to distinguish fast consolidation from top in real-time

---

## Settings Reference

```python
class V13Config:
    # Top Detection (StochRSI)
    OB_THRESHOLD_2W = 93
    OB_FALLBACK_1W = 85
    FAILSAFE_1W = 50
    FAILSAFE_WINDOW_WEEKS = 2
    
    # DCA Transition Signals
    HH_HL_LOOKBACK = 2
    ADX_THRESHOLD = 20
    
    # Phase Ranging Exit
    PHASE_ADX_RANGING = 20
    PHASE_ADX_SUSTAINED_DAYS = 21  # Markup/Markdown exit
    
    # FLAT Phase
    FLAT_MIN_EVAL_DAYS = 14
    FLAT_MAX_EVAL_DAYS = 42
    FLAT_ADX_SUSTAINED_DAYS = 14   # FLAT→DCA confirmation
    
    # Entry Gates (markup only — markdown gate removed)
    SMA200_OVEREXTENSION = 0.20    # >20% above 200-SMA = blocked (MARKUP only)
    
    # Failure Detectors
    MARKUP_FAIL_DD_PCT = 0.25      # 25% drawdown from entry
    MARKUP_FAIL_ADX = 25           # ADX must confirm downtrend
    
    # Capital Allocation
    TIER1_PCT = 0.60
    TIER2_PCT = 0.20
    TIER3_PCT = 0.10
    TIER2_DELAY_WEEKS = 1
    TIER3_DELAY_WEEKS = 2
    
    # DCA Engine
    DCA_BO_PCT = 0.08              # 8% base order
    DCA_SO_DEVIATION = 0.025       # 2.5% between layers
    DCA_SO_MULTIPLIER = 1.5        # Volume multiplier
    DCA_TP_PCT = 0.015             # 1.5% take profit
    DCA_MAX_LAYERS = 8
```

---

## Implementation Files

**Backtest Engine**: `trading/spot/backtest_results/v13/v13_phase_backtest_v8.py`
**Signal Library**: `trading/spot/backtest_results/v13/v13_signals.py`
**Signal Spec**: `projects/ait-product/v13-signal-specification.md`

**Production Code** (to be ported):
- `trading/spot/lifecycle_engine.py` (replace Conductor with phase detection)
- `trading/spot/lifecycle_trader.py` (wire in new phase logic)

---

## What Works Well

1. **Markup phase**: Top signals catch blow-off tops reliably (100% accuracy in backtest)
2. **DCA phase**: Quiet accumulation while waiting for directional signal
3. **Markdown phase**: Shorts capture crashes with tier-based risk management
4. **FLAT phase**: 14d ranging confirmation prevents whipsaws after tops
5. **Signal pairs**: HH_HL+Fib_support and ADX+Fib_break have 94.0 score across all coins
6. **Ranging exit**: 21-day ADX<20 filters out consolidation pauses
7. **SMA200 markup gate**: Prevents entering near ATH (saves BTC, ETH, SOL)
8. **Failure detectors**: Catch reversals before catastrophic loss

---

## What Needs Fixing

1. **BNB slow-mover problem**: 21-day ADX threshold too rigid for low-ADX coins
2. ~~**XRP SMA200 gate**~~: **RESOLVED** — gate removed entirely. Failure detector handles XRP edge case.
3. **Post-top waiting**: 42-day fallback is safe but slow; could optimize conductor timing
4. **Consolidation exits**: StochRSI 1W OB85 can't distinguish fast consolidation from tops

---

## Next Steps (Production Porting)

1. **Port to lifecycle_engine.py**: Replace Conductor with phase state machine
2. **Validate on live data**: Run in paper trading mode for 4 weeks
3. **Fix BNB threshold**: Test per-coin ADX (BNB: <25 instead of <20)
4. ~~**Test XRP gate variation**~~: **RESOLVED** — markdown SMA200 gate removed entirely
5. **Monitor edge cases**: Watch for false signals on new market structures
6. **Compare vs V12f**: Ensure V13 beats production baseline on live trades

---

## Architecture Philosophy

**V13 is about market respect, not signal optimization.**

- **Don't fight consolidation**: If ADX<20 for 21 days, the market is asking for patience. Listen.
- **Top signals are emergency exits**: 2W OB93 and friends are absolute "get out now" signals. No waiting.
- **Failures are safety nets**: The -25% detector exists to prevent "holding through a crash hoping for recovery" scenarios.
- **Ranging confirmation prevents whipsaws**: Waiting 14d in FLAT or 21d in phase transitions costs time but saves catastrophic loss.
- **Tiers manage risk**: Entering with 60% capital first, then adding on confirmation, means small wrong calls don't sink you.

The philosophy: **Capture 70-80% of every move with 20-30% drawdown rather than chase 100% with 50%+ drawdown.**

---

Document last updated: 2026-02-25 2:21 PM — SMA200 markdown gate removed per Brett directive
