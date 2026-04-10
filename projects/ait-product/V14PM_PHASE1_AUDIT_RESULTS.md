# V14PM Phase 1 — Static Analysis Audit Results
_Date: 2026-04-09 | Auditor: Gee Gee | Scope: All 18 production Python files + dashboard HTML_

---

## Summary

| Check | Count | Severity |
|-------|-------|----------|
| **Syntax errors** | 0 | — |
| **Import issues** | 2 | P3 (non-blocking) |
| **Hardcoded Windows paths** | 0 | — |
| **TODO/FIXME markers** | 2 | P4 (informational) |
| **Broad exception handlers** | 82 | P2 (review in Phase 2) |
| **Unguarded divisions** | 13 | P2–P3 (mixed) |
| **Credential leaks** | 0 | — |
| **Non-atomic file writes** | 6 | P3 (non-critical files) |
| **Dashboard issues** | 0 | — |

**Overall: No blockers for production deployment.** The code is structurally sound — no syntax
errors, no hardcoded paths, no credential leaks. The critical state files (state.json,
status.json) already use atomic writes. The findings below are improvement opportunities,
not showstoppers.

---

## Finding 1: Missing Module — `db_migrate_v13_analytics` (P3)

**Files:** `coin_scanner.py:192`, `run_daily_collector.py:22`

Both files import `trading.spot.db_migrate_v13_analytics` which doesn't exist. However:
- `coin_scanner.py` wraps it in `try/except: pass` — silent fallback, no crash
- `run_daily_collector.py` wraps it in `try/except ImportError` with a log message

**Impact:** None for production. The migration module was removed after tables were created.
**Recommendation:** Remove the dead imports to avoid confusion during future audits.

---

## Finding 2: Broad Exception Handlers — 82 instances (P2 — Phase 2 Review)

**Breakdown by file:**

| File | Count | Notes |
|------|-------|-------|
| `run_v14_portfolio_live_aster.py` | 47 | Main bot — most critical |
| `exchange_client.py` | 7 | API calls — broad catch is reasonable |
| `coin_scanner.py` | 5 | |
| `v14_lifecycle_engine.py` | 4 | |
| `backfill_binance.py` | 3 | |
| `collect_scanner_candles.py` | 3 | |
| `v14_capital_manager.py` | 2 | |
| `v13_router_engine_v2.py` | 3 | |
| Others | 8 | |

**Context:** In a trading bot, broad `except Exception` is often intentional — you'd rather
log and continue than crash and leave positions unmanaged. However, some of these could mask
bugs (e.g., catching `KeyError` when a field was renamed).

**Phase 2 action:** Review each handler in the main bot. Classify as:
- **Intentional catch-all** (exchange calls, Telegram sends, file I/O) — keep
- **Should be specific** (data parsing, dict access, math) — narrow
- **Silently swallowing** (`except: pass`) — flag

---

## Finding 3: Unguarded Division Operations — 13 confirmed risks (P2–P3)

### P2 — Could affect production under edge conditions

| File | Line | Variable | Context | Risk |
|------|------|----------|---------|------|
| `v14_capital_manager.py` | 352 | `total_score` | `raw_allocation = (c["adjusted_score"] / total_score) * active_pool` | If all coins have 0 score, total_score = 0. Would crash during rebalance. |
| `v14_dca_engine.py` | 409 | `price` | `coins = order / price` | Candle with price=0 (data error) would crash the engine. |
| `v14_dca_engine.py` | 525 | `price` | Same pattern, short side | Same risk. |

### P3 — Low risk (scanner/utility code, not live trading path)

| File | Line | Variable | Context | Risk |
|------|------|----------|---------|------|
| `v14_lifecycle_engine.py` | 173 | `peak` | `dd = (eq - peak) / peak * 100` | pandas Series division — NaN on 0, doesn't crash. |
| `v14_cycle_scanner.py` | 196, 220 | `total_qty` | `avg_entry = total_cost / total_qty` | qty derived from `order_cost / price` — only 0 if price=0 (data error). |
| `v14_cycle_scanner.py` | 323 | `alloc` | `net_return_pct = total_pnl / alloc * 100` | alloc comes from capital allocation — 0 only if system misconfigured. |
| `v14_dca_engine.py` | 950 | `capital` | `roi = (total - capital) / capital * 100` | Backtest summary only, not live path. |
| `v13_router_engine_v2.py` | 116 | `loss` | `rs = gain / loss` | pandas — produces inf/NaN, handled by RSI formula (`100 - 100/(1+rs)`). |
| `v13_signals.py` | 36 | `avg_loss` | Same RSI pattern | Same — NaN propagates safely. |
| `v13_signals.py` | 42 | `denom` | StochRSI denominator | Explicitly guarded: `denom.replace(0, np.nan)` on line 41. ✅ |
| `generate_daily_equity.py` | 158 | `INITIAL_CAPITAL` | `return_pct = ... / INITIAL_CAPITAL * 100` | Constant, never 0. ✅ |

**✅ FIXED (2026-04-09):** Zero-guards added to all 3 P2 items:
- `v14_capital_manager.py:343` — `if total_score <= 0: return {}` before the loop
- `v14_dca_engine.py:409,527` — `if price <= 0: return` before division (both long and short)

---

## Finding 4: Non-Atomic File Writes — 6 instances (P3)

| File | Line | What's Written | Risk |
|------|------|----------------|------|
| `run_v14_portfolio_live_aster.py` | 2685 | `bot.lock` | Lock file — acceptable |
| `v14_cycle_scanner.py` | 606 | `score_history.json` | Scanner state — non-critical |
| `v14_cycle_scanner.py` | 877 | `cycle_scanner.json` | Scanner output — read by bot at rebalance |
| `coin_scanner.py` | 475 | Cache file | Non-critical |
| `cfgi_client.py` | 177 | CFGI cache | Non-critical |
| `generate_daily_equity.py` | 182 | Equity CSV | Dashboard data — non-critical |

**Note:** The two critical files (state.json, status.json) already use atomic write-to-tmp-then-rename.

**✅ FIXED (2026-04-09):** `cycle_scanner.json` now uses atomic write (write to `.tmp`, then
`replace()`), matching the pattern used by state.json and status.json.

---

## Finding 5: TODO Markers — 2 instances (P4)

Both in the signal stack (v13 codebase), referencing feature `2C.19` (bias trigger):
- `v13_router_engine_v1.py:745`
- `v13_phase_backtest_v8.py:715`

**Impact:** None. These are deferred feature flags, not bugs.

---

## Finding 6: Dashboard HTML — Clean (P4)

- **External dependencies:** 2 CDN scripts (Chart.js, date-fns adapter), Google Fonts
- **Zero-division guards:** All JS divisions use ternary guards (`x>0 ? a/x : 0`)
- **`days` variable:** Guarded with `Math.max(..., 1)` — can never be zero
- **Status fields:** Dashboard reads 22 status fields and 18 coin fields — all should be
  verified against actual `_write_status()` output in Phase 2
- **Title says "Paper Trading"** — should be updated if deployed for live trading

---

## Phase 2 Priorities (informed by Phase 1)

Based on these findings, Phase 2 should focus on:

1. **Main bot exception handlers** (47 in `run_v14_portfolio_live_aster.py`) — classify each
2. **3 P2 division risks** — add zero-guards before production deployment
3. **Exchange client error paths** (7 broad handlers) — verify retry/recovery behavior
4. **State round-trip fidelity** — save state, kill bot, restore, compare
5. **Candle dedup** — still flagged as a known issue from prior work

---

_Phase 1 complete. Proceed to Phase 2 (Component-Level Logic Audit) on approval._
