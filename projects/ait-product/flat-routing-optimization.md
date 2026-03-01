# FLAT Phase Routing Optimization — HVF Fast-Track

**Date:** 2026-02-27
**Status:** Testing (ETF-era backtest in progress)
**Roadmap ref:** Project 2C (Gate Optimization), V13 Gap #7 (FLAT phase routing)

---

## Problem Statement

V13's FLAT phase acts as the "conductor" — it pauses after a top signal or markdown exit and decides whether the market should enter **DCA** (accumulation, long-biased) or **MARKDOWN** (distribution, short-biased).

**Current behavior:**
- **Post-top (PATH 1):** Check for MARKDOWN via LH_LL + ADX>20 + Fib_break. If no signal after **42 days**, default to DCA.
- **Post-markdown/ranging (PATH 2/3):** Wait for ADX<20 sustained 14 days → DCA.

**The problem:** The 42-day timeout is too slow. In several cases (especially BTC), the market declines 5-15% during FLAT before either entering DCA (wrong — should be MARKDOWN) or finally getting to DCA where the long-only grinder then loses money on the decline.

**Key finding:** HVF (Harmonic Volume Factor) was originally designed for FLAT routing but was disabled — it's logged but never used for routing decisions (dead code since implementation).

---

## Root Cause Analysis

### Why FLAT Takes So Long

| Coin | Total FLAT days (full history) | Avg FLAT duration | Windows > 60 days |
|------|-------------------------------|-------------------|-------------------|
| ETH  | 826 days across 13 windows    | 64 days avg       | 6 windows         |
| BTC  | 815 days across 11 windows    | 74 days avg       | 5 windows         |
| SOL  | 1,012 days across 11 windows  | 92 days avg       | 7 windows         |

Much of this time is unnecessary waiting. The market has already decided its direction, but FLAT doesn't have the signal intelligence to route faster.

### Why BTC DCA Loses Money

BTC has 3/11 DCA windows that exit to MARKDOWN (27%). These windows see 5-15% price declines because:
1. FLAT waited the full 42 days without triggering MARKDOWN gates
2. Defaulted to DCA (wrong classification)
3. DCA ran long-only grinding into a declining market
4. Eventually exited DCA to MARKDOWN after further decline

Specific BTC losers:
- **Jun-Aug 2023:** -14.6% price drop over 58 DCA days, exited to MARKDOWN → -$158 loss
- **Feb 2025:** -8.4% drop in 3 DCA days, exited to MARKDOWN → -$85 loss
- **Apr 2023:** -6.4% drop in 9 DCA days → -$50 loss

---

## HVF Signal Analysis

### What HVF Measures

HVF (composite_hvf_score) combines three components:
1. **Vuvuzela pattern (40%):** Volume funnel — first-half volume spread vs second-half (contraction = energy building)
2. **Volume compression (30%):** Linear regression slope of volume (negative = declining = compressing)
3. **Price range compression (30%):** First-half candle range vs second-half (tightening = squeeze)

HVF detects **energy compression** — the market coiling before a breakout. It does NOT predict direction.

### Routing Rules Tested (34 FLAT windows across ETH/BTC/SOL)

| Rule | Accuracy | Coverage | Wrong | Days Saved |
|------|----------|----------|-------|------------|
| **HVF>0.3 + SMA50_ABOVE → DCA** | **100%** | **59%** | **0** | **~1,434** |
| HVF>0.3 within 14d + direction | 50% | 65% | 11 | ~698 |
| SMA50_BELOW at entry → MARKDOWN | 44% | 100% | 19 | ~960 |
| price_drop>5% + SMA50_BELOW → MD | 33% | 26% | 6 | ~49 |
| HVF>0.4 + price_drop>5% → MD | 18% | 32% | 9 | ~44 |
| HVF>0.3 + SMA50_BELOW → MD | 15% | 38% | 11 | ~44 |

### Key Finding

**HVF>0.3 + SMA50_ABOVE → DCA is the only rule with 100% accuracy.**

- 20 out of 20 predictions correct
- Zero false positives (never routes to DCA when it should go MARKDOWN)
- Saves ~1,434 FLAT days across 3 coins (~71 days per window on average)

**Predicting MARKDOWN from FLAT is unreliable** with any signal combination tested. The existing LH_LL + ADX + Fib_break gate handles this correctly — HVF doesn't improve it.

### Why It Works

When HVF detects energy compression AND price is above SMA50:
- The market is consolidating (not trending down)
- Volatility is compressing into a coil (HVF signal)
- Price structure is bullish relative to medium-term trend (SMA50)
- This is textbook accumulation → breakout to markup is likely

When SMA50 is below (bear market), HVF compression often precedes further downside or bear rallies that fail. The SMA50 filter prevents routing into those traps.

---

## Full-Period Backtest Results (Oct 2020 → Feb 2026)

**⚠️ Note: This period includes pre-ETF era (2020-2022) which Brett has directed should NOT drive V13 decisions. ETF-era (2023+) results pending.**

| Coin | Baseline ROI | Modified ROI | Change | FLAT Days Saved |
|------|-------------|-------------|--------|-----------------|
| ETH  | +223%       | +567%       | +344%  | 278 days        |
| BTC  | +179%       | +236%       | +57%   | 230 days        |
| SOL  | +34%        | -69%        | -103%  | 261 days        |

**SOL regression root cause:** Pre-ETF SOL (2021-2023) had deep, extended bear cycles. The HVF fast-track pushed SOL into DCA during bear markets, triggering more markup entries on bear rallies that all failed. SMA50 wasn't a sufficient bear guard for pre-ETF SOL volatility.

---

## ETF-Era Backtest (Jan 2023 → Feb 2026) — IN PROGRESS

Testing 4 filter variants on ETH, BTC, SOL (2023+ data only):

1. **HVF>0.3 + SMA50_ABOVE** (original winner)
2. **HVF>0.3 + SMA200_ABOVE** (stronger bear guard)
3. **HVF>0.3 + SMA50_ABOVE + CFGI>40** (sentiment guard)
4. **HVF>0.4 + SMA50_ABOVE** (higher HVF threshold)

*Results will be added when test completes.*

---

## Proposed Implementation

### Change to `_check_flat()` in V13

```python
# After min eval period check (days_flat >= FLAT_MIN_EVAL_DAYS):

# HVF Fast-Track: energy compressed + bullish structure → DCA immediately
hvf = self._hvf(date)
sma50 = self.daily['close'].rolling(50).mean()
sma50_val = sma50.iloc[self.daily.index.get_indexer([date], method='pad')[0]]
if hvf > 0.3 and price > sma50_val:
    self._change_phase(date, Phase.DCA,
        f'FLAT->DCA: HVF fast-track (HVF={hvf:.2f}, price>SMA50, {days_flat}d)')
    return
```

This applies to BOTH post-top and post-markdown/ranging paths.

### What Stays the Same
- MARKDOWN routing (LH_LL + ADX + Fib_break) — unchanged
- 42-day timeout as fallback — unchanged (but fires less often)
- Min 14-day eval period — unchanged
- All other phase transitions — unchanged

---

## Decision Log

| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-02-27 | DCA phases are long-only | Dual-track shorts lost money; 79% of DCA exits to MARKUP |
| 2026-02-27 | Fix FLAT routing before optimizing DCA | Phase classification speed > DCA parameter tuning |
| 2026-02-27 | HVF>0.3 + SMA50_ABOVE as DCA fast-track | 100% accuracy, 0 wrong predictions, ~1,434 days saved |
| 2026-02-27 | Keep LH_LL+ADX+Fib for MARKDOWN routing | No HVF-based rule reliably predicts MARKDOWN |
| 2026-02-27 | ETF-era (2023+) is the relevant test period | Brett directive: pre-ETF crypto skews decisions |

---

## Optimization Sequence

1. ✅ **DCA dual-track test** — proved long-only is correct
2. ✅ **DCA long-only parameter sweep** — modest returns, FLAT routing is bigger lever
3. ✅ **FLAT routing signal analysis** — HVF>0.3 + SMA50_ABOVE winner
4. ⏳ **ETF-era HVF backtest** — validating on 2023+ data with 4 filter variants
5. 🔲 **Implement HVF fast-track in V13 engine** — pending test results
6. 🔲 **Re-run DCA optimization** — with correctly routed DCA windows
7. 🔲 **15m DCA grinding integration** — add to V13 DCA phase

---

## Files

| File | Purpose |
|------|---------|
| `test_flat_routing.py` | FLAT window analysis, 7 routing rule evaluation |
| `hvf_flat_routing_test.py` | Full-period V13 backtest with HVF modification |
| `test_hvf_daily.py` | HVF computation module (composite_hvf_score) |
| `dca_phase_test.py` | Dual-track DCA test harness |
| `dca_long_sweep.py` | Long-only DCA parameter sweep |
| `_phase_timeline.py` | Phase timeline viewer |
| `_dca_context.py` | DCA window context analyzer |
| `_btc_windows.py` | BTC per-window DCA breakdown |
