# V2 Audit — Phase 2: Intelligence / Signal Stack Findings

**Date**: 2026-05-10  
**Auditor**: OpenClaw AI  
**Files reviewed**: `v13_signals.py` (509), `v13_router_engine_v2.py` (522), `v13_router_engine_v1.py` (887), `_steve_3check.py` (226), `v14_dca_engine.py` (801), `test_hvf_daily.py` (275), `v13_phase_backtest_v8.py` (880)  
**Status**: IN PROGRESS (first pass complete, deeper analysis continuing)

---

## FINDING 9: CRITICAL — 9 Scanner Coins Have No Pre-Computed Indicators

**Files**: `engine/build_daily_candles.py` (computes indicators), `resample_daily.py` (does NOT)  
**Impact**: `DailyStructure` class reads `sma50`, `adx`, `consec_hh_hl`, `consec_lh_ll`, `price_vs_sma50`, `price_vs_sma200` from `candles_daily`. For 9 of 45 scanner coins, ALL these columns are NULL.

**Affected coins**:
| Coin | Symbol Selected | Issue |
|------|----------------|-------|
| **BTC** | BTC/USDC | Picks USDC (wider range) but it has 0 indicators. BTC/USDT has them. |
| **ETH** | ETH/USDC | Same as BTC — USDC pair has no indicators, USDT pair does |
| COMP | COMP/USDT | Only symbol, never had indicators computed |
| DYDX | DYDX/USDT | Same |
| ENS | ENS/USDT | Same |
| KAS | KAS/USDT | Same |
| LDO | LDO/USDT | Same |
| MKR | MKR/USDT | Same |
| OP | OP/USDT | Same |
| **W** | W/USDT | Same — plus W/USDT hasn't been updated since Mar 9 (62 days stale) |

**Root cause**: `build_daily_candles.py` computes SMA50, SMA200, ADX, RSI, HH/HL streaks, slopes.
But it's NOT in the hourly pipeline (`run_candle_collector.ps1`). It was run once manually for
some coins. `resample_daily.py` (which IS in the pipeline) only writes OHLCV + candle_count.

**Downstream impact for these 9 coins**:
- `DailyStructure.sma50_slope_at()` → NaN → structure signals blind
- `DailyStructure.hh_hl_streak()` → always False → no bullish detection
- `DailyStructure.lh_ll_streak()` → always False → no bearish detection
- `DailyStructure.adx_at()` → NaN → trending/ranging detection blind
- `V14DCAEngine._check_router()` → can't detect bullish/bearish structure → defaults to timeout (42d → LONG_DCA)
- ROUTER phase for these coins always times out to LONG_DCA — never enters SHORT_DCA via structure

**Additional BTC/ETH problem**: `load_daily()` picks the symbol with widest date range.
BTC/USDC has 2,625 days (from Binance backfill), BTC/USDT has 2,436 days. So BTC/USDC
wins — but it has zero indicators. If load_daily preferred the symbol WITH indicators,
BTC/USDT would be chosen and signals would work.

**Severity**: CRITICAL — BTC and ETH (the two largest coins) have blind structure signals  
**Migration impact**: Must-fix before migration  
**Recommendation**: Two-part fix:
1. Merge `build_daily_candles.py` indicator computation into `resample_daily.py` (or add as Step 1.75 in pipeline)
2. Fix `load_daily()` to prefer symbols WITH indicators when multiple exist (wider range isn't better if the data is incomplete)

---

## FINDING 10: MEDIUM — StochRSI/BMSB/Divergence Signals Are Independent of Indicator Columns

**Positive finding**: The critical signals (StochRSI, BMSB, divergence, Steve 3-Check) do NOT
depend on the pre-computed indicator columns. They compute their own indicators from raw OHLCV:

- `StochRSISignal.__init__()` resamples daily close to N-week and computes RSI + StochRSI
- `BullMarketSupportBand.__init__()` computes SMA(140d) and EMA(147d) from daily close
- `HybridDetector2D._compute_2d_death_cross()` computes SMA50/SMA200 on 3D resampled data
- `Steve3CheckDetector._compute_indicators()` computes SMA200, RSI(14), StochRSI on 2D candles

These all use raw OHLCV data which IS present for all coins. The indicator gap only affects
`DailyStructure` (sma50 slope, HH/HL streaks, ADX) and `SMA200Overextension` (price_vs_sma200).

**What this means**: Top/bottom detection works for all coins. Structure-based ROUTER routing
is blind for 9 coins. The structure signals affect:
- ROUTER → LONG_DCA transition (needs `hh_hl` + `fib_support`)
- ROUTER → SHORT_DCA transition (needs `lh_ll` + ADX + `fib_break`)

---

## FINDING 11: MEDIUM — `_signal_near()` Has a 3-Day Window That May Cause False Matches

**File**: `v14_dca_engine.py`, line 216  
**Code**: 
```python
def _signal_near(self, date, signal_set, window=3):
    for d in range(-window, window + 1):
        check = date + pd.Timedelta(days=d)
        if check in signal_set:
            return True
    return False
```

**Issue**: This checks if a weekly StochRSI signal fired within ±3 days of the daily tick.
This is necessary because daily ticks may not align exactly with weekly period boundaries.
However, the ±3 day window means a signal on Monday could match a tick on Thursday of the
previous week (or vice versa). For 1W signals this is fine (~7 day period). For 2W signals
(~14 day period), ±3 days is still reasonable. For 3W signals (~21 days), ±3 might be too
tight (could miss signals) or too loose (could match the wrong period).

**Severity**: MEDIUM (edge case, but could cause missed or phantom signals)  
**Recommendation**: Verify against backtest results that the window doesn't cause issues

---

## FINDING 12: MEDIUM — `load_daily()` in Steve 3-Check Doesn't Use Widest Range

**File**: `_steve_3check.py`, line 40  
**Code**:
```python
syms = db.execute(
    "SELECT DISTINCT symbol FROM candles_daily WHERE symbol LIKE ?",
    (f'{self.base}%',)).fetchall()
if not syms:
    db.close()
    return None
sym = syms[0][0]  # Takes FIRST symbol, not widest range
```

**Issue**: Steve 3-Check takes the FIRST symbol returned by the query (which depends on
DB insertion order), not the one with the most data. `load_daily()` in v13_signals.py
correctly picks widest range, but Steve 3-Check doesn't.

For BTC, `syms[0]` might be BTC/USDC or BTC/USDT depending on DB order. If it picks
BTC/USDC (no indicators), the 2D SMA200 still computes from raw close (OK for Steve's
own indicators), but the symbol chosen may have less data than optimal.

**Severity**: MEDIUM  
**Migration impact**: Should standardize  
**Recommendation**: Use the same symbol selection logic as `load_daily()` (widest range)

---

## FINDING 13: MEDIUM — HybridDetector2D._load_full_daily() Tries USDC First

**File**: `v13_router_engine_v2.py`, line 88  
**Code**:
```python
for quote in ['USDC', 'USDT']:
    sym = f'{self.base}/{quote}'
```

**Issue**: For the 3D death cross and 2D divergence computation, HybridDetector2D loads
daily data by trying USDC first, then USDT. This is different from `load_daily()` which
tries all pairs and picks widest range. For coins with both pairs (BTC, ETH, SOL, XRP, LINK),
this may pick a different symbol than what `V13SignalPack` uses.

If BTC's USDC pair has no recent data (stale since March 9 — 62 days), the 2D death cross
and 2D divergence dates computed by HybridDetector2D will be based on stale data, while
StochRSI signals use BTC/USDT (which may be more recent).

**Severity**: MEDIUM (signals may be computed from different data sources for the same coin)  
**Recommendation**: Standardize symbol selection across all data loading functions

---

## FINDING 14: LOW — v13_router_engine_v1.py Is Only Used as Base Class

**Observation**: V13RouterV1 (887 lines) is used exclusively as the base class for V13RouterV2.
It's not imported by any runner or production code directly. It contains the full ROUTER v1
logic (Fib levels, swing detection, phase transitions) which v2 inherits and extends.

The `run_combined()` function in v1 is dead code in production (only used for offline backtesting).

**Severity**: LOW (legacy code, but actively needed as v2's base class)

---

## FINDING 15: LOW — test_hvf_daily.py and v13_phase_backtest_v8.py Are Legacy

**Observation**: 
- `test_hvf_daily.py` (275 lines) is imported by `v13_phase_backtest_v8.py` and `v13_router_engine_v1.py` for Fibonacci computation (`compute_fib_levels`, `FIB_RATIOS`, `FIB_TOLERANCE`)
- `v13_phase_backtest_v8.py` (880 lines) is only imported by `_steve_3check.py` for the `V13BacktestV8` base class and `Phase` enum

Both are effectively library code for the signal stack. Not dead code, but their names suggest
they're test files when they're actually production dependencies.

**Severity**: LOW  
**Recommendation**: During migration, rename to reflect actual role (e.g., `fib_calculator.py`, `v13_base_engine.py`)

---

## FINDING 16: NOTE — CFGI Data Quality Unknown

**Observation**: The `cfgi_daily` table in candles.db stores CFGI history. The signal stack
uses it for fear/greed signals (CFGISignal class) and as conviction gate 4 (CFGI < 35).

Questions for production verification:
- How often is cfgi_daily updated?
- How many coins have CFGI data vs those that don't?
- What's the freshness of the most recent CFGI entry?
- If CFGI is missing, the conviction score maxes at 3/4 instead of 4/4 — is this acceptable?

---

## Summary

| # | Severity | Finding | Status |
|---|----------|---------|--------|
| 9 | CRITICAL | 9 scanner coins (inc BTC, ETH) have no pre-computed indicators | 🔴 Active |
| 10 | MEDIUM | Core signals (StochRSI, BMSB, divergence) independent of indicator columns | ✅ OK |
| 11 | MEDIUM | `_signal_near()` ±3 day window may cause edge cases | 🟡 Review |
| 12 | MEDIUM | Steve 3-Check doesn't use widest-range symbol selection | 🟡 Inconsistency |
| 13 | MEDIUM | HybridDetector2D tries USDC before USDT (different from load_daily) | 🟡 Inconsistency |
| 14 | LOW | v13_router_engine_v1 is only a base class | 🟢 Legacy, needed |
| 15 | LOW | test_hvf_daily / v13_phase_backtest_v8 are misnamed production deps | 🟢 Naming |
| 16 | NOTE | CFGI data freshness unverified | 🟡 Needs check |

**Most urgent**: Finding 9 — BTC and ETH structure signals are blind because load_daily()
picks the USDC pair (wider range) which has no indicator columns. The indicator computation
(`build_daily_candles.py`) is not in the pipeline.
