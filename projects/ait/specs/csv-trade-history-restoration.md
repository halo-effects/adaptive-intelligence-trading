# CSV Trade History Restoration — Post-Audit Data Loss Report & Fix Spec

**Date**: 2026-05-10  
**Severity**: HIGH (data loss — reporting only, no trading impact)  
**Status**: INVESTIGATION COMPLETE — awaiting approval to restore

---

## Executive Summary

During the May 8-9 audit and restart cycle, **both the V14 PM Paper and V14 PM Live bots had their trade history CSVs truncated**. The bots continued trading correctly (equity/positions/PnL tracking are live and accurate), but the historical trade log — which feeds dashboard charts, daily ROI calculations, and the equity curve — lost significant data.

- **V14 PM Paper**: 711 trades → 171 trades (540 trades / $32,734 in PnL history lost)
- **V14 PM Live**: 96 trades → 77 trades (19 trades / ~$8 in PnL history lost)

**All data is recoverable from git history.** No trades were actually lost from the exchange — this is purely a CSV reporting/recording issue.

---

## Impact

### Dashboard Symptoms
1. **Avg Daily ROI dropped dramatically** — Paper: ~1.35%/day → 0.30%/day (denominator unchanged, numerator slashed)
2. **Equity chart has a flat line / gap** — Mar 16 to May 1 (45 days) on Paper bot; May 5 to May 10 (5 days) on Live bot
3. **Trade log shows fewer total trades** — Paper: 171 vs 711; Live: 77 vs 96
4. **Realized PnL underreported** — Paper: $14K vs $47K; Live: $84 vs $93

### What's NOT Affected
- **Live trading**: Both bots trade correctly using exchange state, not CSV
- **Equity tracking**: Real-time equity is accurate (reads from exchange)
- **Open positions**: Unaffected — tracked via exchange/state.json, not CSV
- **TP orders**: Unaffected — stored on exchange

---

## Root Cause Analysis

### Timeline

| Time | Event | Paper CSV | Live CSV |
|------|-------|-----------|----------|
| May 7, 06:03 | Pre-audit (paper only) | **677** trades | — |
| May 8, 07:33 | Pre-audit | 689 | 89 |
| May 8, ~08:11 | DEX-verified cleanup commits | — | **73** (cleaned) |
| May 8, 21:03 | Bot still running, accumulating | **711** | **96** |
| May 8–9, overnight | **Bot restarts load truncated CSV** | — | — |
| May 9, 06:13 | Post-restart sync | **171** ❌ | **76** ❌ |
| May 10, 14:33 | Current | 171 | 77 |

### What Happened

1. **May 8 Incident**: The restart cascade (documented in `incident-2026-05-08-restart.md`) involved multiple restarts and CSV corrections. The DEX-as-truth fix cleaned the live bot's CSV to 73 verified trades.

2. **Audit CSV Verification**: During the audit, the live bot's CSV was DEX-verified and cleaned to remove phantom/duplicate trades from the restart churn. This was correct at the time.

3. **Paper Bot CSV Truncation**: The paper bot's CSV was truncated from 711 to 171 trades. The mechanism:
   - The bot restarted and loaded `trades.csv` — but loaded a version that had been truncated/overwritten
   - The bot's internal `total_realized_pnl` counter re-synced to match the CSV count
   - The dashboard data sync then propagated the truncated CSV to `docs/data/v14-pm/trades.csv`
   - Deal IDs 27-99 (the entire Mar 16 – May 1 period) are missing

4. **Live Bot Gap**: After the cleaned 73-trade CSV was established, the bot was down from May 5-10 (no scheduled task). Trades that occurred on-exchange during May 5-8 via existing TP orders were never recorded. When the bot restarted May 10, it detected 3 TP fills and recorded those, but 10 unique trades from the gap remain missing.

### Deal ID Gaps

**Paper Bot** (current 171 trades, should be 711):
- deal 26 → 100: **73 missing IDs** (Mar 8 – Mar 10 — entire period)
- deal 168 → 170, 188 → 190, 244 → 246, 252 → 255: small gaps

**Live Bot** (current 77 trades, should be ~87 unique):
- deal 61 → 64: 2 missing
- deal 64 → 71: 6 missing
- deal 73 → 76: 2 missing

---

## Recovery Plan

### Source Data

| Bot | Git Commit | Trades | PnL | Notes |
|-----|-----------|--------|-----|-------|
| Paper | `764cc55a0` (May 8 21:03) | 711 | $46,742 | Last complete version |
| Live | `99aecfd36` (May 8 21:43) | 96 | $93+ | Last version with May 5-8 trades |

### Step 1: Restore Paper Bot CSV

```
# Extract the 711-trade CSV from git
git show 764cc55a0:docs/data/v14-pm/trades.csv > /tmp/paper_full.csv

# Verify no duplicates
# Expected: 711 unique deal_ids, 711 rows, no duplicate symbol+open_time combos
```

**Merge strategy**: The current CSV has 171 trades. The full CSV has 711. We need to:
1. Start with the 711-trade version from `764cc55a0`
2. Append any trades from the current CSV with deal_id > max in the 711 version (deals 253-255 closed May 9-10)
3. De-duplicate by `deal_id` (keep the most recent version if conflict)
4. Sort by `close_time`

### Step 2: Restore Live Bot CSV

```
# Extract the 96-trade CSV from git  
git show 99aecfd36:docs/data/v14-pm-live/trades.csv > /tmp/live_full.csv
```

**Merge strategy**:
1. Start with the 96-trade version from `99aecfd36`
2. De-duplicate: deal IDs 78-97 had some duplicated trades (same open_time+symbol, different deal_id). Identify true duplicates by matching `symbol + open_time + layers + pnl` and keep only one.
3. Append new trades from current CSV that postdate the 96-trade version (deal 76/JUP from May 10 13:35)
4. Sort by `close_time`

### Step 3: Update Dashboard Data

1. Copy restored CSVs to `docs/data/v14-pm/trades.csv` and `docs/data/v14-pm-live/trades.csv`
2. Let next dashboard sync push to GitHub Pages
3. Verify dashboard equity chart, trade count, and daily ROI

### Step 4: Fix Bot Internal Counters

**Paper bot** (`trading/spot/paper/v14_portfolio/status.json`):
- `total_realized_pnl`: Currently $14,008.43. Should be sum of restored CSV PnL (~$46,742)
- `deals_completed`: Currently 171. Should be count of restored CSV trades (711+)
- `total_fees`: Currently $649.31 (coin-level sum is correct — this one may be OK)
- ⚠️ **Caution**: Changing `total_realized_pnl` will affect equity calculation if equity = capital + realized - fees + unrealized. Need to verify the equity formula doesn't double-count.

**Live bot** (`trading/spot/live/v14pm/status.json`):
- `total_fees`: Currently $0.10 (should be ~$19.77 from coin-level sum). The dashboard's `Math.max(total_fees, coin_fees_sum)` fallback catches this, but the field itself is wrong.
- `total_realized_pnl`: Currently $84.23. Needs to match restored CSV sum.
- ⚠️ **REAL MONEY BOT**: Changes to status.json require pre-flight verification. The bot reads from exchange for trading decisions, not from status.json, so this is safe — but verify.

### Step 5: Verify Dashboard Calculations Post-Restore

After restoration, dashboard should show:
- **Paper**: ~711+ trades, ~$47K realized PnL, ~1.0%/day avg daily ROI, continuous equity curve
- **Live**: ~87+ trades, ~$93 realized PnL, ~0.4%/day avg daily ROI, filled gap

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|-----------|
| Restored CSV has duplicates | Medium | Low (inflates PnL) | De-duplicate by symbol+open_time+pnl |
| Bot overwrites restored CSV on restart | Medium | High (data loss again) | Restore CSV, then immediately sync to dashboard. Consider making CSV append-only. |
| status.json counter fix breaks equity | Low | Medium | Verify equity formula first. Paper bot only — low risk. |
| Live bot counter fix causes trading issue | Very Low | High | Bot uses exchange state, not status.json, for decisions. Pre-flight test. |

---

## Prevention

### Why This Happened
The bot's CSV is both the **append log** (new trades written here) and the **source of truth for history** (dashboard reads from here). When the bot restarts, it loads the CSV and sets its internal counter to match. If the CSV is truncated, the counter resets and all future writes start from the truncated state.

### Recommendations
1. **Immutable trade log**: Write trades to an append-only log that the bot never truncates. Dashboard reads from this log.
2. **Backup before restart**: Any restart script should backup `trades.csv` before starting.
3. **Counter persistence**: Store `deals_completed` and `total_realized_pnl` in state.json independently of CSV row count.
4. **Data sync validation**: Dashboard sync should warn if trade count decreases between syncs.
5. **Scheduled task for live bot**: Already done (V14PMLiveAster created 2026-05-10) — prevents multi-day downtime gaps.

---

## Files Affected

| File | Current | Should Be | Source |
|------|---------|-----------|--------|
| `docs/data/v14-pm/trades.csv` | 171 trades | ~711+ trades | git `764cc55a0` + merge |
| `docs/data/v14-pm-live/trades.csv` | 77 trades | ~87+ trades | git `99aecfd36` + merge |
| `trading/spot/paper/v14_portfolio/status.json` | PnL $14K / 171 deals | PnL ~$47K / ~711 deals | Calculated from restored CSV |
| `trading/spot/live/v14pm/status.json` | fees $0.10 / PnL $84 | fees ~$20 / PnL ~$93 | Calculated from restored CSV |
| `trading/spot/paper/v14_portfolio/trades.csv` | 171 trades | ~711+ trades | Copy from dashboard restore |
| `trading/spot/live/v14pm/trades.csv` | 77 trades | ~87+ trades | Copy from dashboard restore |

---

## Approval Required

- [ ] Brett reviews restoration approach
- [ ] Confirm merge strategy (full replace vs. surgical merge)
- [ ] Confirm whether to update bot internal counters or just dashboard CSVs
- [ ] Execute restoration
- [ ] Verify dashboards post-restore
