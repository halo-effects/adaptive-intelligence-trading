# Conviction-Weighted Bottom Stack — Engine Changes Spec

**Date:** 2026-02-27  
**Status:** Testing — ready for router engine integration  
**Goal:** Detect market bottoms during MARKDOWN phase, close shorts early, flip to spot longs

---

## The Problem

Current V13 engine stays in MARKDOWN until the failure detector fires (>25% rise + ADX>25). By then, we've missed most of the bottom move. We need a conviction-based signal stack to:
1. Detect the bottom during MARKDOWN
2. Close shorts (lock in profit)
3. Flip to MARKUP immediately (buy spot)
4. Never re-short after a conviction flip (hold spot longs)

## Signal Stack (5 signals, all on 2D candles except CFGI)

| # | Signal | Source | Threshold | Notes |
|---|--------|--------|-----------|-------|
| 1 | **Price below 2D SMA(200)** | Steve Courtney / CCU | price < SMA200 on 2-day resampled candles | Universal at bottoms (100%) |
| 2 | **2D RSI(14)** | Steve Courtney / CCU | < 26 | Extreme oversold |
| 3 | **2D StochRSI(3,3,14,14)** | Steve Courtney / CCU | K < 20 AND D < 20 | Momentum capitulation |
| 4 | **Coin-specific CFGI** | Our addition | < 35 | Raw fear index, NOT CFGI RSI |
| 5 | **Pi Cycle Bottom** | Bitcoin indicator | 150 SMA < 471×0.745 SMA (daily) | Macro cycle — very rare, only fires in deep bears |

**Minimum conviction: 4/5** — requires Steve's full 3-check OR any 3 + CFGI + Pi Cycle

## Trigger Rules

1. **Fires during MARKDOWN phase** — not just ROUTER/FLAT
2. **One trigger per cycle** — first 4/5 signal after a top detection, then locked until next full cycle
3. **No re-shorting after conviction flip** — `_no_reshort = True` persists, blocks `_open_short()`
4. **Closes existing short** via `_close_short()` before entering MARKUP
5. **Deploys T1 (60%)** immediately on trigger

## Indicator Computation Details

### 2D Candle Resampling
```python
daily.resample('2D').agg({
    'open': 'first', 'high': 'max', 'low': 'min',
    'close': 'last', 'volume': 'sum'
}).dropna()
```

### 2D RSI(14) — Wilder's RSI
```python
delta = close.diff()
gain = delta.clip(lower=0)
loss = (-delta).clip(lower=0)
avg_gain = gain.ewm(alpha=1/14, min_periods=14).mean()
avg_loss = loss.ewm(alpha=1/14, min_periods=14).mean()
rs = avg_gain / avg_loss
rsi = 100 - (100 / (1 + rs))
```

### 2D StochRSI(3, 3, 14, 14)
```python
# StochRSI of RSI(14) over 14 periods, K smooth=3, D smooth=3
rsi_low = rsi.rolling(14).min()
rsi_high = rsi.rolling(14).max()
stoch_raw = ((rsi - rsi_low) / (rsi_high - rsi_low)) * 100
K = stoch_raw.rolling(3).mean()
D = K.rolling(3).mean()
```

### CFGI < 35
- Source: `cfgi_daily` table in candles.db
- Symbol: base coin (e.g., `BTC`, not `BTC/USDC`)
- Raw value, NOT RSI of CFGI

### Pi Cycle Bottom
```python
sma150 = daily_close.rolling(150).mean()
sma471_scaled = daily_close.rolling(471).mean() * 0.745
pi_bottom_zone = sma150 < sma471_scaled
```
- Computed on daily candles (not 2D)
- Very rare — only fired once per coin (2022 bear)
- Not currently active for any coin (Feb 2026)

## Engine Changes (vs baseline V13 v8)

### 1. New: `_check_markdown()` override
```
IF phase == MARKDOWN AND score >= 4:
    _close_short(date, 'CONVICTION')
    _no_reshort = True
    _change_phase(MARKUP)
    _buy(T1 60%)
    RETURN (skip normal markdown check)
ELSE:
    super()._check_markdown()  # normal failure detector
```

### 2. New: `_check_flat()` override  
Same conviction check during ROUTER/FLAT phase (for cases where shorts already closed via normal TP/failure).

### 3. New: `_open_short()` override
```
IF _no_reshort:
    RETURN (block)
ELSE:
    super()._open_short()
```

### 4. New flag: `_no_reshort`
- Initialized `False`
- Set `True` on conviction flip from MARKDOWN
- Persists through all subsequent phase transitions
- Blocks ALL future short entries for that coin's lifecycle
- Reset: only on full engine restart (new backtest run)

### 5. One trigger per cycle (TODO — not yet implemented)
- After conviction fires, lock out further triggers until next top signal → MARKDOWN → ROUTER cycle completes
- Prevents multiple buys at different price levels during extended bottoms

## Test Results Summary

| Variant | Total | Delta | Notes |
|---------|-------|-------|-------|
| BASELINE | $30,196 | — | Standard v8 |
| 4/5 T1 (no reshort) | $30,100 | -$96 | Flat — BTC whipsaw offsets ETH gains |
| 4/5 T1 (with reshort) | $33,781 | +$3,585 | ETH +$5,940, but BTC -$2,211 |
| Steve pure 3/3 (post-MD only) | $32,817 | +$2,622 | ETH only, no BTC trigger |
| Hybrid 3/4 (post-MD only) | $32,871 | +$2,675 | Catches BTC too |

### Key Findings
- **4/5 is the right threshold** — 3/5 fires too often, 5/5 never fires
- **One trigger per cycle needed** — BTC fires 6× in 2022 bear, whipsaws without it
- **ETH is the strongest performer** — 100% bottom detection via Steve's 3-check
- **Pi Cycle rarely fires** — only 2022 deep bear, not current correction
- **LINK/XRP have no signals** — insufficient 2D SMA200 history, need fallback
- **No-reshort is correct** — per Brett: "we hold spot longs"

## Current Market (Feb 2026)

Steve's 3-check is **actively firing** for:
- **ETH**: 4/5 on Feb 5-6 (SMA200+RSI+StochRSI+CFGI)
- **BTC**: 4/5 on Feb 11 (SMA200+RSI+StochRSI+CFGI)
- **SOL**: 4/5 on Feb 4 (SMA200+RSI+StochRSI+CFGI)
- **LINK**: 3/5 on Feb 5 (RSI+StochRSI+CFGI, no 2D SMA200 data)
- **XRP**: 3/5 on Feb 4 (RSI+StochRSI+CFGI, no 2D SMA200 data)

Pi Cycle is NOT active for any coin.

## Macro Confirmation Signals (Index-Level)

*Added 2026-03-08 — sourced from Americana (YouTube) + independent analysis*

The per-coin conviction stack (§Signal Stack above) detects bottoms at the individual asset level. These macro signals provide **portfolio-level confirmation** that the broader crypto market is bottoming. When both per-coin AND macro signals align, conviction is highest.

### Macro Signal Checklist

| # | Signal | Current Status (Mar 2026) | Notes |
|---|--------|--------------------------|-------|
| 1 | **TOTAL market cap oversold on 3D + weekly** | ✅ Active | Historically marks cycle bottoms. 3D bullish divergence forming with rising momentum. |
| 2 | **TOTAL2 (ex-BTC) oversold on 3D** | ✅ Active | Same oversold levels as prior cycle bottoms. Momentum rising on 3D. |
| 3 | **TOTAL3 (ex-BTC/ETH) oversold on weekly** | ✅ Active | Most oversold reading in current cycle. Past cycles: this level = relief + bottom formation. |
| 4 | **OTHERS/BTC building momentum + structure** | ✅ Active | Alt-relative-to-BTC turning up — precursor to alt season. |
| 5 | **ETH/BTC turning up on monthly momentum** | ✅ Active | First monthly momentum upturn since Nov 2020. Major macro shift signal. |
| 6 | **BTC.D (dominance) bearish monthly momentum** | ✅ Active | First bearish month of momentum since Nov 2020. Capital rotation from BTC → alts. |

### Interpretation

- **All 6 macro signals active simultaneously** as of early March 2026
- Historical precedent: every time TOTAL/TOTAL2/TOTAL3 hit these oversold levels together, it marked accumulation zones
- The ETH/BTC + BTC.D flip is particularly significant — Nov 2020 was the last time this happened, preceding the 2021 alt season
- **Not confirmed until upward price action materializes** — signals indicate setup, not trigger
- These are observational/directional — not yet wired into any bot logic

### How This Relates to AIT

- **PM Bot**: Trend multiplier will naturally accelerate allocation into coins that start cycling as the bottom plays out
- **Conviction Stack**: Per-coin 4/5 signals (RSI, StochRSI, CFGI) already firing for BTC/ETH/SOL as of Feb 2026 — macro alignment increases confidence
- **Potential future use**: Macro conviction score could gate portfolio-level risk parameters (e.g., increase Active Pool % from 75% → 85% when macro bottom confirmed)

### Source
- [Americana — "All TOTAL indexes just hit historic oversold zones"](https://youtube.com/shorts/i3_B6HLZg5I) (Mar 7, 2026)
- Cross-referenced with existing conviction stack signals firing since Feb 2026

---

## Outstanding Items

1. **One trigger per cycle lock** — needs implementation
2. **LINK/XRP fallback** — need daily SMA200 or shorter lookback for coins without 2D SMA200 history
3. **Graduated tiers** — tested but no clear win over flat T1 deployment
4. **Paper bot comparison** — need to run router engine with conviction stack from Oct 1, 2024 start date
5. **Pi Cycle top indicator** — could complement existing 2W StochRSI top detection (111 DMA crosses above 350 DMA × 2)

## Files Created

| File | Purpose |
|------|---------|
| `_conviction_weighted_test.py` | Original test with Spring (zero triggers) |
| `_conviction_debug.py` | Signal stack debug at known bottoms |
| `_conviction_nospring.py` | Test without Spring requirement |
| `_conviction_postmarkdown.py` | Post-MARKDOWN only triggers |
| `_conviction_v2.py` | CFGI RSI(7)<40 variant (worse than raw CFGI) |
| `_conviction_hybrid.py` | Steve 3-check + CFGI hybrid |
| `_steve_3check.py` | Steve Courtney's pure 3-checkmark |
| `_pi_cycle_bottom.py` | Full stack with Pi Cycle + markdown override |
| `_2d_golden_top.py` | 2D golden cross → top timing |
