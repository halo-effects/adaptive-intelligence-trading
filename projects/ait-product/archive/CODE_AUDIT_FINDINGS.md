# V14PM Code Audit — Findings Report
_Date: 2026-03-09 | Auditor: Gee Gee_

---

## Summary

| Severity | Count | Status |
|----------|-------|--------|
| 🔴 Critical (breaks on Linux) | 1 | Fix required |
| 🔴 Critical (crashes all bots) | 1 | ✅ Fixed 2026-03-09 |
| 🔴 Critical (blind signal stack) | 1 | ✅ Fixed 2026-03-10 |
| 🔴 Critical (phantom trades) | 1 | ✅ Fixed 2026-03-10 |
| 🔴 Critical (missing daily data) | 1 | ✅ Fixed 2026-03-10 |
| 🟠 High (cloud migration blocker) | 3 | Fix required |
| 🟡 Medium (inconsistency / cosmetic) | 3 | Fix recommended |
| 🟢 Low / Not an issue | 5 | Document only |

---

## 🔴 Critical

### C1 — `run_candle_collector.ps1` is Windows-only
**File:** `trading/spot/run_candle_collector.ps1`
**Issue:** Hardcodes `C:\Users\Never\AppData\Local\Programs\Python\Python312\python.exe` and
`C:\Users\Never\.openclaw\workspace`. The `AIT_CandleCollector` scheduled task calls this script directly.
On a Linux cloud server this script cannot run at all — PowerShell is not the default shell,
and these paths don't exist.
**Fix:** Create `trading/spot/run_candle_collector.sh` as the Linux equivalent. 
The `.ps1` stays for Windows. Migration guide documents which to use per platform.

### C2 — `_steve_3check.py` wrong DB path (3 parents instead of 2) — ✅ FIXED
**File:** `trading/spot/engine/_steve_3check.py`, line 20
**Issue:** `Path(__file__).resolve().parent.parent.parent / 'data' / 'candles.db'` resolved to
`trading/data/candles.db` (empty 0-byte file) instead of `trading/spot/data/candles.db` (214 MB).
The file lives at `trading/spot/engine/`, so 3 parents goes to `trading/` not `trading/spot/`.
This caused `sqlite3.OperationalError: no such table: candles_daily` on every bot startup,
silently crashing the Live, PM, and ETF bots repeatedly since at least March 3.
**Root cause:** The Steve 3-Check bottom detector was added to the `engine/` subdirectory but
the relative path assumed it was one level higher.
**Fix applied 2026-03-09:** Changed `.parent.parent.parent` to `.parent.parent`.
Also covered by H1 fix (`AIT_CANDLES_DB` env var standardization).

### C3 — `v13_router_engine_v2.py` wrong DB path (3 parents instead of 2) — ✅ FIXED
**File:** `trading/spot/engine/v13_router_engine_v2.py`, line 47
**Issue:** Same bug as C2. `.parent.parent.parent` resolved to `trading/data/candles.db` (0 bytes)
instead of `trading/spot/data/candles.db` (214 MB).
**Impact:** The `HybridDetector2D` class — which computes 2D RSI divergence dates for top detection
and 3D SMA death cross for bottom conviction — was reading from an empty database. This caused:
- `compute_2d_divergence_dates()` always returned empty set → OB93 top detection always timed out
  at 35 days instead of detecting actual divergences
- `_compute_2d_death_cross()` returned None → bottom conviction gate 1 always failed → no
  conviction-based bottom reversals were ever detected
- All engines in ALL bots were affected (V14 Paper, V14-ETF, V14 Live, V14PM)
**Fix applied 2026-03-10:** Changed `.parent.parent.parent` to `.parent.parent`.
**See:** `V14PM_FULL_AUDIT.md` §2.1 for full analysis.

### C4 — No engine state persistence → phantom trades on restart — ✅ FIXED
**File:** `trading/spot/run_v14_portfolio_paper.py`
**Issue:** `V14LifecycleEngine` has `snapshot_state()` / `restore_state()` methods but the PM
runner never called them. Every restart created blank engines that replayed 200 candles of
history as if they were new, generating phantom trades. 41 phantom trades were generated across
multiple restarts before the root cause was identified.
**Fix applied 2026-03-10:** Added `_save_state()` (writes `engine_state.json` every 60s) and
`_load_state()` (restores on startup). Tested 4 consecutive kill-restart cycles with zero
phantom trades. `--fresh` no longer needed for normal restarts (only for first launch).
**See:** `PM_AUDIT_2026-03-10.md` for full analysis.

### C5 — Missing daily candle resampling pipeline — ✅ FIXED
**Issue:** `collect_scanner_candles.py` writes 1h candles to `candles` table. `V13SignalPack`
reads from `candles_daily`. There was NO code to bridge the gap. 19 of 45 scanner coins had
zero daily candles — their engines ran without signal packs (no phase transitions, no top/bottom
detection).
**Fix applied 2026-03-10:** Created `resample_daily.py` (1h → daily OHLCV aggregation), wired
into hourly pipeline as Step 1.5 in `run_candle_collector.ps1`. First run inserted 24,995 daily
candles for 24 symbols.
**See:** `V14PM_FULL_AUDIT.md` §2.2 for full analysis.

---

## 🟠 High

### H1 — `DB_PATH` not respecting `AIT_CANDLES_DB` env var in runners and scanner
**Files:** `run_v14_paper.py`, `run_v14etf_paper.py`, `run_v14_portfolio_paper.py`,
`run_v14_live_aster.py`, `v14_cycle_scanner.py`, `collect_scanner_candles.py`,
`backfill_scanner_coins.py`, `backfill_etf_candles.py`

**Issue:** All use hardcoded path construction to find `candles.db`:
```python
DB_PATH = _WORKSPACE / "trading" / "spot" / "data" / "candles.db"  # runners
DB_PATH = Path(__file__).parent / "data" / "candles.db"             # collectors
```
Engine files (`v14_dca_engine.py`, `v13_signals.py`, etc.) were already fixed to use
`AIT_CANDLES_DB` env var. Runners and scanner were not. This is inconsistent and means
cloud migration requires finding and editing the DB path in 8 separate files.
**Fix:** Apply `AIT_CANDLES_DB` env var pattern to all 8 files.

### H2 — `SCANNER_PATH` hardcoded in V14PM runner (critical for MVP)
**File:** `run_v14_portfolio_paper.py` line 42
```python
SCANNER_PATH = _WORKSPACE / "docs" / "data" / "v14" / "cycle_scanner.json"
```
**Issue:** The PM bot loads the cycle scanner JSON to drive capital rotation decisions.
This path assumes the workspace directory structure. On a cloud server the `docs/` directory
may live elsewhere (e.g. a separate web server), and this path will silently fail to load
scanner data — causing the PM to run without capital rotation signals.
**Fix:** Add `AIT_SCANNER_JSON` env var with this as default.

### H3 — `exchange_client.py` Windows Registry fallback silently fails on Linux
**File:** `trading/spot/exchange_client.py` lines 56–90
**Issue:** Credential resolution order is:
  1. Explicit config dict
  2. Environment variable (`HYPERLIQUID_API_KEY`, etc.)
  3. Windows Registry (`winreg` — **Windows only**)

The `winreg` import is inside `try/except Exception`, so it **won't crash** on Linux.
But the failure is silent — if env vars aren't set, the bot starts with empty credentials
and connects unauthenticated. On the live PM bot this means orders will fail at execution time,
not at startup. Hard to diagnose.
**Fix:** Add a startup credential validation check: if `api_key` is empty after all resolution
attempts, raise a clear error at init time rather than failing silently later.

---

## 🟡 Medium

### M1 — `v14_lifecycle_engine.py` stale docstring
**File:** `trading/spot/v14_lifecycle_engine.py` line 4
```python
# Wraps the V14 DCA-only engine (from backtest_results/v13/v14_dca_engine.py) for
```
**Issue:** Engine files were moved to `trading/spot/engine/`. Reference is now wrong.
**Fix:** Update to reflect new location.

### M2 — `sys.path.insert(_WORKSPACE)` in all runners
**Files:** `run_v14_paper.py`, `run_v14etf_paper.py`, `run_v14_portfolio_paper.py`,
`run_v14_live_aster.py`, `run_v14_scanner.py`
**Issue:** All runners add workspace root to `sys.path` at startup. This is a workaround for
running the module from an arbitrary directory. It works, but on a cloud server the preferred
pattern is either:
  - Run with `python -m trading.spot.X` from workspace root, OR
  - Set `PYTHONPATH=/opt/ait` in the systemd service environment
**Fix:** Not a code change — document in migration guide. Add `PYTHONPATH` to cloud env setup.

### M3 — `run_candle_collector.ps1` has no `WorkingDirectory` in scheduled task
**Task:** `AIT_CandleCollector`
**Issue:** `WorkingDirectory` is blank. The script uses absolute paths throughout so this
doesn't cause failures, but it's inconsistent with all other tasks and makes the task
harder to port to Linux.
**Fix:** Set `WorkingDirectory` on the task.

---

## 🟢 Low / Not an Issue

### L1 — `sys.platform == "win32"` blocks
**Files:** `collect_scanner_candles.py`, `v14_cycle_scanner.py`, `run_v14_live_aster.py`
**Finding:** All three use this pattern exclusively for UTF-8 stdout wrapping:
```python
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
```
**Status:** ✅ Safe. On Linux these blocks are simply skipped. No action needed.

### L2 — `cfgi_path sys.path.insert` in `coin_scanner.py` and `daily_collector.py`
**Finding:** Adds `trading/spot/` to `sys.path` to locate the CFGI local cache directory.
Not an engine dependency — benign on any platform.
**Status:** ✅ Safe. No action needed.

### L3 — `winreg` ImportError is caught silently
**Finding:** `_try_winreg()` imports `winreg` inside `try/except Exception`.
On Linux, `ImportError` is caught, returns `("", "")`. No crash.
**Status:** ✅ Safe. Covered by H3 fix (startup validation).

### L4 — No hardcoded absolute Windows paths in Python code
**Finding:** Sweep found zero `C:\Users\Never` or similar hardcoded paths in any `.py` file.
All paths use `Path(__file__).resolve()` or `_WORKSPACE` (derived from file location).
**Status:** ✅ Clean.

### L5 — `collect_scanner_candles.py` / `backfill_*.py` use `Path(__file__).parent / "data"`
**Finding:** Resolves `candles.db` relative to the script file location. Since the file lives
at `trading/spot/`, this correctly resolves to `trading/spot/data/candles.db`.
Will work correctly on any OS as long as directory structure is maintained.
Covered by H1 fix (env var standardization).

---

## Fix Plan

| Fix | Effort | Risk to running bots |
|-----|--------|----------------------|
| C1 — Create `run_candle_collector.sh` | Low | None |
| H1 — `AIT_CANDLES_DB` in all 8 files | Medium | None (running bots don't restart) |
| H2 — `AIT_SCANNER_JSON` in PM runner | Low | None |
| H3 — Startup credential validation in exchange_client | Low | None |
| M1 — Fix stale docstring | Trivial | None |
| M2 — Document `PYTHONPATH` in migration guide | None (doc only) | None |
| M3 — Set WorkingDirectory on AIT_CandleCollector | Trivial | None |

_Total estimated time: ~1.5 hours_

---

_After all fixes applied → proceed to Phase 4 (Architecture Document)_
