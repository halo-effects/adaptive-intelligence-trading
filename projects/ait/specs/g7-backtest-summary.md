# G-7 — Full Signal-Gating Backtest Results
_Date: 2026-07-04 | Window: 90 days | Coins: NEAR, TAO, INJ, TON, JUP, DYDX, ASTER, HYPE_
_Grid: D-GRID(d) [40/24/20/16%] | TP: 3.0% | Dev: 1.5% | Max 4 layers_
_Gate: B1 stall (≥3 candles, no new low) + higher-low | B2 StochRSI K↑D (K<40) + higher-low | Cooldown 4h_
_Veto: A1 RSI>78/<22 | A2 ATR-normalized extension (3.0×ATR14) | A3 side-resolved divergence_

## Results by Arm

| Arm | Deals | PnL | Win Rate | Max DD (avg) | Avg Duration | L3+ Fills | Vetoed | Gated |
|-----|-------|-----|----------|--------------|-------------|-----------|--------|-------|
| **Mechanical** | 197 | $36,429 | 100% | **23.88%** | 35.5h | 58 | 0 | 0 |
| **Veto only** | 168 | $32,467 | 100% | **18.80%** | 47.0h | 50 | 2,444 | 0 |
| **Gate only** | 169 | $27,280 | 100% | **6.02%** | 42.8h | 1 | 0 | 10,835 |
| **Veto + Gate** | 125 | $20,546 | 100% | **3.55%** | 63.3h | 0 | 2,032 | 9,395 |

## Key Findings

### 1. 100% win rate across ALL arms
The grid never produces a losing deal when allowed to complete. Every closed trade is profitable at +2.97% avg return.

### 2. Gate is a drawdown killer
Max drawdown drops from **23.88% → 6.02%** (gate only) or **3.55%** (veto+gate). This is a 75-85% reduction in drawdown exposure.

### 3. PnL tradeoff is explicit and favorable
- Gate costs ~25% of gross PnL ($36K → $27K) but reduces risk by 75%
- Risk-adjusted return (PnL / MaxDD) improves: $36K/24% = $1,518/% vs $27K/6% = $4,547/% — **3× better risk-adjusted**
- At live capital ($400), the 24% max DD = -$96 potential; with gate = -$24 potential

### 4. L3/L4 fills are almost entirely gated
- Mechanical: 58 L3+ fills across 8 coins
- Gate: 1 L3+ fill (INJ, one legitimate admission during basing)
- The higher-low anchor prevents fills during waterfall legs (G-6 verified: 0 fills during NEAR/INJ crashes)

### 5. Veto reduces entry into overextended coins
- 2,444 entry attempts blocked across 8 coins (veto-only arm)
- Most active on: INJ (644), TON (550), NEAR (527), DYDX (513)
- ASTER and HYPE: 0 vetoed (never overextended in the window)

## Anchor Assertions

### NEAR (41 mechanical deals → 33 veto+gate deals)
- ✅ Veto triggers in late May (RSI 78.6 on May 21)
- ✅ Gate blocks ALL L3/L4 during Jun 4-12 waterfall (verified in G-6: 0 admitted, 193 gated)
- ✅ Max DD drops: 22.16% → 2.74% (gate) — the waterfall is fully absorbed
- ✅ 100% win rate preserved

### INJ (45 mechanical deals → 25 veto+gate deals)
- ✅ Veto triggers in late April/May (RSI 79.5 on May 12)
- ✅ Gate blocks ALL L3/L4 during Jun 1-6 waterfall (verified in G-6: 0 admitted, 96 gated)
- ✅ Max DD drops: 22.46% → 9.82% (gate) — significant but INJ had a deeper correction
- ✅ 1 legitimate L3+ fill admitted (during genuine basing period)
- ✅ 100% win rate preserved

## Recommendation
**Part B is GO** — the gate with higher-low anchor:
1. Blocks all L3/L4 fills during waterfall legs (verified on both anchor coins)
2. Reduces max drawdown by 75-85%
3. Preserves 100% win rate
4. Risk-adjusted return improves 3×
5. PnL cost is acceptable given the drawdown reduction

Pending: Brett approval → engine restart
