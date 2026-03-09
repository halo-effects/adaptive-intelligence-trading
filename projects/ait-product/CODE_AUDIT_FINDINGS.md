# V14PM Code Audit — Findings Report
_Date: 2026-03-09 | Auditor: Gee Gee_

---

## Summary

| Severity | Count | Status |
|----------|-------|--------|
| 🔴 Critical (breaks on Linux) | 1 | Fix required |
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
