# V14 DCA-Only Engine — Architecture Specification

## Why V14: The Pivot from Lump-Sum to DCA

### Problem Statement
V13's ROUTER v2 combined backtest (bottom conviction + top detection) showed **+$2,905 (+2.6%)** vs baseline — far below the individual component tests (+$9,847 bottom, +$15,160 top). The systems interact in unexpected ways: bottom conviction changes phase sequences, which prevents top detection from firing. More fundamentally:

1. **Timing precision is the fragile point.** Our signals correctly identify tops and bottoms within a 20-50 day window, but lump-sum execution punishes timing errors severely (SOL conviction -$2,820, ETH top detection -$5,795).

2. **Whack-a-mole across coins.** Different coins behave erratically based on idiosyncratic market dynamics. With large capital deployed in a single moment, being wrong on one coin hurts the entire portfolio.

3. **Direction is correct, timing is approximate.** After 98+ signal tests, our conviction and top detection stacks reliably identify cycle direction. They're just not precise enough for all-in/all-out execution.

### The Insight (Brett, 2026-02-28)
> "What if we changed our investment behavior to DCA only strategy? When we sense the bottom is in, we naturally unwind DCA shorts. The router gets confirmation of markup and switches to DCA longs. We stay in DCA longs all the way to the top and exit gracefully."

**Key principle:** Same brain (ROUTER signal stack), different hands (gradual DCA execution). DCA absorbs timing imprecision that kills lump-sum. "Roughly right" becomes an advantage, not a liability.

### What DCA Solves
| Problem | V13 (Lump-Sum) | V14 (DCA) |
|---------|----------------|-----------|
| Timing 20-50d early | Full capital at wrong price | Small initial position, averages into better price |
| Coin behaves differently | Single entry point, all-or-nothing | Grid naturally adapts to price action |
| Direction switch cost | Force-close everything | Gracefully unwind, let TPs hit |
| Capital at risk | 60% deployed instantly | 8% base, layers added only on dips |

## Architecture

### Phase Structure (simplified from V13's 4 phases)

```
LONG_DCA ←→ ROUTER ←→ SHORT_DCA
```

| Phase | Purpose | Execution |
|-------|---------|-----------|
| **LONG_DCA** | Confirmed bullish trend | Full capital in long DCA grid (1h) |
| **SHORT_DCA** | Confirmed bearish trend | Full capital in short DCA grid (1h) |
| **ROUTER** | Evaluation / transition | No new trades, may hold unwinding positions |

- **No dual-track**: Full capital in one direction at a time
- **Graceful transitions**: Early signals stop new deals, let TPs hit. Confirmation flips direction.

### Signal Stack (inherited from ROUTER v2)

#### Top Detection (LONG_DCA → SHORT_DCA)
1. **Early warning** (1W K crosses below 97) → start unwinding (stop new deals)
2. **OB93 fires** → arm top detector, unwind
3. **2D RSI bearish divergence** confirms → close remaining longs, switch to SHORT_DCA
4. **35d timeout** if divergence never comes → close and switch
5. **Fallback layers** (OB85, failsafe K<50) for coins where OB93 never fires

#### Bottom Detection (SHORT_DCA → LONG_DCA)
- **Gate 1**: Top previously detected (LONG_DCA → SHORT_DCA transition)
- **Gate 2**: 3D death cross active (SMA50 < SMA200)
- **Gate 3**: 2W StochRSI K ≥ 5 (after pinned < 5)
- **Trigger**: Conviction score ≥ 3/4 (below SMA200 + RSI<26 + StochRSI K&D<20 + CFGI<35)
- **Action**: Close short grid, switch to LONG_DCA

### DCA Grid Parameters (from V13 sweep results)
- **Timeframe**: 1h (dominated 15m on all 5 coins tested)
- **Take Profit**: 1.5%
- **Deviation**: 2.5% between safety orders
- **SO Multiplier**: 2.5× volume per layer
- **Max Safety Orders**: 8
- **Base Order**: 8% of available capital (90% utilized, 10% reserve)
- **Fixed params beat adaptive** on 4/5 coins

### Capital Flow
```
[LONG_DCA]                    [SHORT_DCA]
Full capital → long grid      Full capital → short grid
TPs cycle profits back        TPs cycle profits back
     ↓ top signals                ↓ bottom signals
[UNWINDING]                   [UNWINDING]
Stop new deals                Stop new deals
Let open TPs hit              Let open TPs hit
     ↓ confirmation               ↓ confirmation
[SHORT_DCA]                   [LONG_DCA]
```

## V14 vs V13 Comparison

| Aspect | V13 | V14 |
|--------|-----|-----|
| Entry | Lump-sum T1=60%, T2=20%, T3=10% | DCA grid: 8% base + safety orders |
| Exit | Sell all on signal | Graceful unwind → switch |
| Capital at risk per entry | 60% | 8% (grows via safety orders on dips) |
| Phases | DCA → MARKUP → ROUTER → MARKDOWN | LONG_DCA ↔ ROUTER ↔ SHORT_DCA |
| Direction switches | Instant flip | Gradual unwind → confirm → flip |
| Wrong timing penalty | Severe (full capital at bad price) | Minimal (small initial, averages in) |
| Right timing benefit | Maximum (full capital at best price) | Moderate (averaged price) |

## First Run Results & Issues (2026-02-28)

### V14 v0.1: -5.7% total (vs V13 +187%)
Expected for first pass. Clear structural issues identified:

1. **SHORT_DCA exits in 3-14 days** — HH_HL bullish structure fires immediately. V13's structure signals were tuned for lump-sum timing, not DCA persistence.
2. **Ranging exit interrupts LONG_DCA** — ADX < 20 for 21d fires repeatedly, bouncing coins into ROUTER for 14-42d of dead time. DCA handles ranging naturally.
3. **Capital utilization tiny** — 8% base order means most capital idle vs V13's 60% instant deployment.
4. **Top/bottom conviction barely fires** — Most direction switches from ranging/structure, not our hardened signal stack.

### Required Fixes
- Remove ranging exit from DCA phases (DCA handles chop naturally)
- Make SHORT_DCA much stickier (conviction-level signals only, not structure)
- Increase capital utilization (larger base orders or more aggressive layers)
- Only switch direction on conviction-level signals, not minor structure changes

## Base Engine
- **Cloned from**: `v13_router_engine_v2.py` (ROUTER v2 with conviction + top detection)
- **File**: `trading/spot/backtest_results/v13/v14_dca_engine.py`
- **Inherits**: V13SignalPack, HybridDetector2D (bottom conviction), 2D divergence (top detection)
- **1h DCA sweep results**: `projects/ait-product/dca-optimization-baseline.md`

## Research Foundation
This engine stands on extensive V13 research:
- 98 distinct signals tested
- DCA timeframe comparison (1h >> 15m on all coins)
- DCA parameter sweep (fixed TP=1.5%, dev=2.5%, mult=2.5x optimal)
- DCA dual-track proven inferior (long-only DCA correct during DCA phases — V14 extends this insight by making the ENTIRE strategy directional DCA)
- Full bottom conviction stack locked (3D DX + 2W K≥5 + 3/4 score)
- Full top detection system (OB93 arm + 2D divergence + 35d timeout)
- 79% of V13 DCA phases exit to MARKUP → confirms structural long bias, supports directional DCA concept

## Status
- [x] Architecture spec (this document)
- [x] V14 engine v0.1 built and tested
- [ ] Fix phase stickiness (remove ranging exit, conviction-only switches)
- [ ] Tune capital utilization
- [ ] Backtest vs V13 baseline
- [ ] Paper bot deployment
