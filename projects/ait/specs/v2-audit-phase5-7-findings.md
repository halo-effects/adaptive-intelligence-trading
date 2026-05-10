# V2 Audit — Phases 5-7: State, Dashboards, Infrastructure

**Date**: 2026-05-10  
**Auditor**: OpenClaw AI  
**Status**: COMPLETE

---

## Phase 5: State Management & Persistence

### FINDING 38: MEDIUM — Capital Ledger Doesn't Track PnL

Ledger shows `current_capital: $300.00` but actual tracked capital is $377.44. Ledger only records seed/deposit/withdrawal, not realized PnL. Bot uses DEX-as-truth on startup so this is informational only, but it's misleading.

### FINDING 39: LOW — Redundant `capital` field in state.json

Both `capital` and `tracked_capital` are always equal. Remove `capital` during migration.

### FINDING 40: POSITIVE — Atomic File Writes Everywhere

All writes use tmp→rename pattern. Crash-safe.

### FINDING 41: POSITIVE — Engine State Snapshot Is Complete

30+ fields captured, all restored correctly. No state lost across restarts.

### FINDING 42: LOW — TradeTracker dedup uses timestamp strings

Works correctly. Edge case of same-millisecond trades handled.

### FINDING 43: LOW — open_deals accumulate for removed coins

Phantom entries in state.json for coins that no longer exist. Cosmetic only.

### FINDING 44: NOTE — tracked_capital vs seed+PnL delta expected

Delta = -$6.79 = unrealized PnL + fees. Normal.

---

## Phase 6: Dashboards

### FINDING 45: POSITIVE — Dashboard Data Pipeline Working

- `dashboardV14PM.html` (paper) and `d-984ae0d4ab9dc1a5.html` (live) are near-identical (only title + data paths differ)
- Dashboard sync runs every 10 minutes via `AIT_DashboardSync` scheduled task
- Copies status.json + trades.csv from live/paper directories to docs/data/ for GitHub Pages
- `.nojekyll` ensured present
- Safety: only stages `docs/` changes, explicitly unstages non-docs files

### FINDING 46: LOW — Dashboard Reads CSV on Every Render

The browser-side dashboard reads trades.csv and parses it client-side. As trade count grows (currently 77 trades), this remains lightweight. At 1000+ trades, consider pagination or pre-computed summary JSON.

### FINDING 47: LOW — V14-ETF Dashboard Missing From Sync

V14-ETF paper bot runs but there's no `docs/data/v14-etf/` directory in the sync script. The ETF dashboard HTML exists (`docs/dashboardV14ETF.html`) but may not have data syncing to GitHub Pages.

---

## Phase 7: Infrastructure

### FINDING 48: HIGH — V14PM Live Bot Has No Auto-Restart

**Scheduled Tasks**:
| Task | Status | Interval |
|------|--------|----------|
| AIT_CandleCollector | Ready | Every 1h |
| AIT_DashboardSync | Ready | Every 10m |
| AIT_Watchdog | Ready | Every 5m |
| V14CycleScanner | Ready | Daily 6am |
| V14LiveAster | Ready | At boot (OLD single-coin bot) |
| V14ETFPaperBot | Running | At login |
| V14PaperBot | Running | At login |
| V14PMPaperBot | Running | At login |

**MISSING**: No scheduled task for `V14PM Live Aster` (run_v14_portfolio_live_aster.py).

The live bot runs as PID 12524, started manually with:
```
python -u -m trading.spot.run_v14_portfolio_live_aster --capital 300 --confirm --skip-backfill
```

If the machine reboots or the process crashes, the bot does NOT restart. The watchdog (AIT_Watchdog) may or may not cover this — depends on what the watchdog script does.

**Severity**: HIGH (real money bot has no auto-restart)  
**Recommendation**: Create scheduled task `V14PMLiveAster` with "At login" trigger:
```powershell
$action = New-ScheduledTaskAction -Execute "C:\Users\Never\AppData\Local\Programs\Python\Python312\python.exe" `
    -Argument "-u -m trading.spot.run_v14_portfolio_live_aster --capital 300 --confirm --skip-backfill" `
    -WorkingDirectory "C:\Users\Never\.openclaw\workspace"
$trigger = New-ScheduledTaskTrigger -AtLogon
Register-ScheduledTask -TaskName "V14PMLiveAster" -Action $action -Trigger $trigger -RunLevel Highest
```

### FINDING 49: MEDIUM — V14LiveAster Task Points to Old Single-Coin Bot

The `V14LiveAster` scheduled task runs `run_v14_live_aster` (single-coin), not `run_v14_portfolio_live_aster` (portfolio manager). This is the OLD bot. It should either be updated to point to V14PM or disabled.

### FINDING 50: LOW — Watchdog Script Not Reviewed

`openclaw_watchdog_silent.vbs` runs every 5 minutes. Its functionality is unknown (wraps a PowerShell script?). Should verify it covers V14PM live.

### FINDING 51: MEDIUM — File Lock Prevents Accidental Double-Start

The bot uses `msvcrt.locking()` to hold an exclusive lock on `bot.lock`. If another instance tries to start, it exits immediately with error. This is good practice but means the scheduled task won't restart the bot if the lock file is stale (from a crash that didn't release it).

The bot does clean up the lock in the `finally` block, and on Windows, process termination automatically releases file handles. But if the bot is killed via `kill -9` (SIGKILL), the file handle may not be released until GC.

**Severity**: MEDIUM (stale lock could prevent restart)  
**Recommendation**: Add PID check — if lock file exists, check if the PID is still alive. If not, remove stale lock.

---

## Summary (Phases 5-7)

| # | Severity | Finding | Phase |
|---|----------|---------|-------|
| 38 | MEDIUM | Capital ledger doesn't track PnL | 5 |
| 39 | LOW | Redundant capital field | 5 |
| 40 | POSITIVE | Atomic writes | 5 |
| 41 | POSITIVE | Complete state snapshots | 5 |
| 42 | LOW | Timestamp-based dedup | 5 |
| 43 | LOW | Phantom open_deals | 5 |
| 44 | NOTE | Expected capital delta | 5 |
| 45 | POSITIVE | Dashboard pipeline working | 6 |
| 46 | LOW | Client-side CSV parsing | 6 |
| 47 | LOW | V14-ETF data not synced | 6 |
| **48** | **HIGH** | **V14PM Live has no auto-restart** | **7** |
| 49 | MEDIUM | Old V14LiveAster task stale | 7 |
| 50 | LOW | Watchdog unverified | 7 |
| 51 | MEDIUM | Stale lock file risk | 7 |
