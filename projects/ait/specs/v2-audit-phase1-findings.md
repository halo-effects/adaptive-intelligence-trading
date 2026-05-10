# V2 Audit — Phase 1: Data Pipeline Findings

**Date**: 2026-05-10  
**Auditor**: OpenClaw AI  
**Files reviewed**: `collect_scanner_candles.py` (235 lines), `resample_daily.py` (117 lines), `run_candle_collector.ps1` (59 lines), `cfgi_client.py` (223 lines), `candles.db` (515 MB)

---

## FINDING 1: CRITICAL — Candle Collector Broken Since May 5 (Missing `import os`)

**File**: `collect_scanner_candles.py`, line 32  
**Code**: `DB_PATH = Path(os.environ.get("AIT_CANDLES_DB", ...))`  
**Bug**: `os` is never imported. The file uses `os.environ.get()` on line 32 but has no `import os`.

**Impact**:
- Collector crashes with `NameError: name 'os' is not defined` on every run
- **No new candles have been collected since May 5, 2026 19:00 UTC**
- 26 of 45 scanner coins have stale 1h data (~4.8 days old)
- 7 additional coins have USDC pair data that's 62+ days old
- The scanner runs on stale data, producing potentially wrong rankings and scores

**History**: This exact bug has struck twice:
1. **March 9 – April 17** (39 days broken): A git commit removed `import os`
2. **May 5 – present** (5 days broken): Data sync cron overwrote the file with broken version

The pipeline script (`run_candle_collector.ps1`) logs the error as a WARNING but continues to Step 2 (scanner), which runs on stale data without any staleness detection.

**Severity**: CRITICAL — directly affects coin selection, scoring accuracy, and signal freshness  
**Migration impact**: Must-fix before migration  
**Recommendation**: 
1. Emergency fix: Add `import os` to line 17 of `collect_scanner_candles.py`
2. Add `import os` validation to the pipeline script (pre-flight check)
3. Add data freshness check: if any scanner coin's last candle is >2h old, WARN; if >24h old, FAIL

---

## FINDING 2: HIGH — Massive Daily Candle Duplicates (500K+ table, ~50% duplicates)

**File**: `candles_daily` table in `candles.db`  
**Bug**: 502,167 rows in `candles_daily` but many coins have extreme duplication:

| Coin | Total Rows | Unique Timestamps | Duplicates | Duplication Factor |
|------|-----------|-------------------|------------|-------------------|
| APT/USDT | 25,727 | 1,297 | 24,430 | 19.8x |
| COMP/USDT | 16,072 | 857 | 15,215 | 18.8x |
| DYDX/USDT | 16,072 | 857 | 15,215 | 18.8x |
| HBAR/USDT | 16,946 | 857 | 16,089 | 19.8x |
| PEPE/USDT | 21,766 | 1,098 | 20,668 | 19.8x |
| HYPE/USDT | 6,620 | 342 | 6,278 | 19.4x |
| GRASS/USDT | 10,680 | 545 | 10,135 | 19.6x |

**Root cause**: The `candles_daily` table has a PRIMARY KEY of `(symbol, timestamp)`, and `resample_daily.py` uses `INSERT OR IGNORE`. However, the massive duplication (19-20 copies per day) suggests the table was created WITHOUT the primary key constraint by an earlier migration or `build_daily_candles.py`, then the constraint was added later but existing duplicates were never cleaned.

APT has exactly 19-20 rows per day, suggesting 19-20 resample runs inserted duplicate rows before the PK constraint was added.

**Impact**:
- `V13SignalPack.load_daily()` does `df = pd.read_sql(...)` which returns ALL duplicates
- The signal pack has a dedup line: `df = df[~df.index.duplicated(keep='last')]` — so downstream signals are correct
- However: 500K rows instead of ~30K slows queries and wastes memory
- The dedup silently masks the data integrity issue

**Severity**: HIGH (data corruption, masked by dedup)  
**Migration impact**: Should fix before migration to start clean  
**Recommendation**: 
1. Create a clean `candles_daily_clean` table with proper PK
2. `INSERT OR REPLACE INTO candles_daily_clean SELECT DISTINCT ... FROM candles_daily`
3. Drop old table, rename clean table
4. Verify `resample_daily.py` INSERT OR IGNORE works with proper PK

---

## FINDING 3: MEDIUM — Pipeline Continues on Failure (No Circuit Breaker)

**File**: `run_candle_collector.ps1`, lines 27-35  
**Code**: 
```powershell
if ($exitCode -ne 0) {
    Log "WARNING: Candle collector exited with code 1"
} else {
    Log "Step 1 complete."
}
```

**Bug**: When the collector fails (exit code 1), the pipeline continues to Step 1.5 (resample) and Step 2 (scanner). There's no circuit breaker. The scanner runs on stale data and produces stale rankings that the bot consumes for capital allocation.

**Impact**: The collector has been failing for 5 days, and the scanner has been running on 5-day-old data for 26 coins. The bot's daily rebalance uses these stale rankings to allocate real money.

**Severity**: MEDIUM (stale data leads to suboptimal but not catastrophic allocation)  
**Migration impact**: Must-fix  
**Recommendation**: Add staleness check after Step 1. If any scanner coin's last candle is >4h old, log ERROR and skip scanner (use last good output).

---

## FINDING 4: MEDIUM — Resample Skips Coins That Are "Caught Up"

**File**: `resample_daily.py`, lines 96-100  
**Code**:
```python
if latest_daily and latest_hourly:
    if latest_hourly - latest_daily < 86_400_000:
        continue
```

**Bug**: If the hourly data is less than 24h ahead of daily, the coin is skipped. This means today's partial daily candle (the currently-forming day) is never updated until tomorrow. The daily candle for today only gets written after tomorrow's first candle arrives.

**Impact**: The most recent daily candle is always yesterday's — today's is missing until the next day boundary. Signal indicators that depend on the latest daily close (SMA, RSI, etc.) are always 1 day lagged.

**Note**: This may be intentional (avoid writing partial/incomplete daily candles). But it means the signal stack always sees yesterday's data, not today's.

**Severity**: MEDIUM (consistent 1-day lag in signal data)  
**Migration impact**: Should document as known behavior  
**Recommendation**: Verify this is intentional. If signals should reflect today's partial data, change the threshold. If not, document it in the architecture doc.

---

## FINDING 5: MEDIUM — 31 Coins in DB Not in Collector Universe

**Observation**: The hourly DB has 79 symbols, but the collector's COINS list only has 48 (45 + 3 USDC duplicates). The other 31 coins were added by backfill scripts, the ETF bot, or the Aster live bot.

**Affected coins** (in DB but not collected by Hyperliquid collector):
ALGO, APT, ASTER, AXS, BCH, BERA, BNB, BONK, BTC/USDT, ETH/USDT, FLOKI, GALA, GRASS, GRT, HYPE/USDT, INIT, IP, JTO, MANA, MOVE, ORCA, PEPE/USDC, PEPE/USDT, S, SAND, SHIB, TRUMP/USDC, TRUMP/USDT, VIRTUAL, WIF, ZEC

**Impact**: These coins still get daily resampled (from stale hourly data), and their signal packs load from daily data. If any engine trades them (e.g., V14PM's HYPE, JTO, PEPE, ENA are/were active coins), they're running on data that stopped updating when the collector broke.

Some of these are in the live bot's engine list (JTO, PEPE, ENA) — they were demoted by the scanner but still had engines. Now they have stale signal data.

**Severity**: MEDIUM  
**Migration impact**: Must reconcile — decide which coins are in the universe and ensure all are collected  
**Recommendation**: Reconcile the collector COINS list with: (a) the scanner universe, (b) all active engine coins, (c) the signal pack's expected coins. Document which coins come from which source.

---

## FINDING 6: LOW — CFGI Client Has No Staleness Safeguard

**File**: `cfgi_client.py`  
**Observation**: The CFGI client caches responses to disk (`cfgi_cache/`) but has no expiry. `get_bulk_history()` with `cache=True` returns cached data regardless of age. There's no mechanism to detect if CFGI data is weeks old.

**Impact**: If the CFGI API goes down, cached values are used indefinitely. The CFGI signal could be making decisions based on months-old fear/greed data.

**Severity**: LOW (CFGI is one of many signals, not sole decision-maker)  
**Migration impact**: None  
**Recommendation**: Add cache TTL (e.g., 7 days for daily data). Log warning when using stale cache.

---

## FINDING 7: LOW — Duplicate Index on candles Table

**File**: `candles.db` schema  
**Observation**: The `candles` table has BOTH a PRIMARY KEY `(symbol, timeframe, timestamp)` AND an explicit index `idx_candles_sym_tf_ts` on the same three columns. The PK already creates an implicit unique index, so the explicit index is redundant.

**Impact**: Wasted disk space and slightly slower writes (two indexes updated per insert).  
**Severity**: LOW  
**Recommendation**: Drop `idx_candles_sym_tf_ts` (the PK covers it).

---

## FINDING 8: NOTE — Data Quality is Clean

**Positive findings**:
- 0 NULL OHLC values across 2.46M hourly candles and 502K daily candles
- 0 zero-close values
- 0 negative values
- 0 OHLC consistency violations (high < open/close or low > open/close)
- 0 duplicate hourly candles
- Hourly and daily symbol sets match perfectly (79 each)

The data that exists is clean. The problem is freshness, not quality.

---

## Summary

| # | Severity | Finding | Status |
|---|----------|---------|--------|
| 1 | CRITICAL | Collector broken since May 5 (missing `import os`) | 🔴 Active |
| 2 | HIGH | 500K+ daily candle duplicates (~50% of table) | 🟡 Masked by dedup |
| 3 | MEDIUM | Pipeline has no circuit breaker on failure | 🟡 Design gap |
| 4 | MEDIUM | Daily resample always 1 day lagged | 🟡 Possibly intentional |
| 5 | MEDIUM | 31 coins in DB not in collector universe | 🟡 Inconsistency |
| 6 | LOW | CFGI cache has no TTL | 🟢 Minor |
| 7 | LOW | Duplicate index on candles table | 🟢 Minor |
| 8 | NOTE | Data quality (OHLC) is excellent | ✅ Clean |

**Immediate action needed**: Fix the collector (Finding 1). The signal stack is running on 5-day-old data for 26 of 45 scanner coins. This affects coin scoring, trend multipliers, and every downstream decision.
