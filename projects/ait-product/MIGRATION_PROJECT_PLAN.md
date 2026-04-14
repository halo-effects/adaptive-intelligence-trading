# AIT V14PM — Production Migration Project Plan
_Owner: Brett | Agent: Gee Gee | Created: 2026-03-09 | Status: ACTIVE_

---

## Objective

Produce a complete **System Architecture & Migration Guide** that a systems engineer with no prior context can use to stand up the full AIT V14PM trading system on a production Linux cloud server, connected to Hyperliquid for live trading.

## Product Clarity

**V14PM is the MVP.** This is the product being sold to customers and integrated with Hyperliquid for live trading. Everything else serves it:

| Component | Role |
|-----------|------|
| **V14PM** | ✅ **The product** — MVP for customer sales + Hyperliquid live trading |
| V14 Paper (HBAR/ATOM/LINK/NEAR) | Demo account — shows the DCA engine performing |
| V14-ETF Paper (SOL/XRP/LTC/HBAR/ADA) | Demo account — shows multi-coin ETF-style strategy |
| V14 Live (ASTER/USDT) | Live proof-of-concept — validates engine with real capital |
| Dashboards | Customer-facing — demo the PM and strategy performance |

The architecture doc and migration guide lead with **V14PM**. The paper bots are supporting cast — demos that must stay running but are not the migration target.

**Constraint:** The three paper trading bots (V14, V14-ETF, V14-PM) and their dashboards must remain running and uninterrupted throughout. They are live demos for customers and partners.

---

## Approach

We work in five sequential phases. Cleanup happens *before* final documentation, so the architecture doc reflects the actual clean system — not the current state with inherited debt.

```
Phase 1: Audit          ← inventory everything (code, docs, data, tasks)
Phase 2: Document Gather ← collect and link all existing specs into one index
Phase 3: Cleanup        ← fix broken paths, move engine files, restore sources
Phase 4: Architecture   ← write the definitive system architecture document
Phase 5: Migration Guide ← step-by-step sysadmin runbook for cloud deployment
```

---

## Phase 1 — Full System Audit
**Goal:** Complete inventory of every system component, file, dependency, and scheduled task.
**Status:** ✅ COMPLETE (2026-03-09)
**Output:** `projects/ait-product/V14_ARCHITECTURE_AUDIT.md`

### Completed
- [x] All Python source files mapped
- [x] Full dependency graph traced (runner → lifecycle engine → DCA engine → V13 signal stack)
- [x] All Windows Scheduled Tasks inventoried
- [x] Missing source files identified (6 files recovered from `.pyc` cache today)
- [x] `__init__.py` files created for `trading/` and `trading/spot/` packages
- [x] Confirmed: `exchange_client.py`, `cfgi_client.py`, `incident_schema.py`, all V13 engine files now restored

### Key Findings
1. V13 signal engine files live in `backtest_results/v13/` — loaded via `sys.path.insert()` hack
2. `DB_PATH` in `v14_dca_engine.py` is a relative path — breaks if file is moved
3. No `requirements.txt` exists
4. Two `candles.db` files (primary at `trading/spot/data/`, legacy at `backtest_results/v13/`)
5. `run_scanner_v13.py` is misnamed — runs V14 signal stack
6. `sync_dashboard.ps1` appears to have wiped source `.py` files in the 4:43 AM data sync (root cause of today's outage)

---

## Phase 2 — Document Gathering
**Goal:** Index all existing project docs, specs, and READMEs into a single reference map.
**Status:** 🔄 IN PROGRESS
**Output:** `projects/ait-product/DOCUMENT_INDEX.md`

### Existing Documents (located)

| Document | Location | Coverage | Quality |
|----------|----------|----------|---------|
| V14 System Specification | `projects/ait/v14-system-spec.md` | Full system overview | ✅ Good |
| V14 DCA Architecture | `projects/ait-product/v14-dca-architecture.md` | Engine design, why V14 | ✅ Good |
| V14 Capital Manager Spec | `projects/ait/v14-capital-manager-spec.md` | CapitalRouter rules | ✅ Good |
| Portfolio Capital Management | `projects/ait-product/portfolio-capital-management.md` | PM strategy | ✅ Good |
| Conviction Stack Spec | `projects/ait-product/conviction-stack-spec.md` | Signal stack | ✅ Good |
| Top Conviction Stack Analysis | `projects/ait-product/top-conviction-stack-analysis.md` | Top detection | ✅ Good |
| Bear Market Coin Research | `projects/ait-product/bear-market-coin-research.md` | Coin selection rationale | ✅ Good |
| V14 Architecture Audit | `projects/ait-product/V14_ARCHITECTURE_AUDIT.md` | File/dep audit | ✅ Current |
| Q1 2026 Roadmap | `projects/roadmap-q1-2026.md` | Product roadmap | ⚠️ Needs review |
| Live Bot README | `trading/spot/live/v14/README.md` | Aster bot setup | ✅ Good |
| V14 Test Plan | `projects/ait-product/v14-test-plan.md` | Testing | ⚠️ Needs review |

### Gaps (documents to be created in Phase 4)
- V14 PM Bot Architecture (dedicated spec for the portfolio manager)
- DCA Cycle Scanner spec
- Exchange Client spec (Aster + Hyperliquid API abstraction)
- Candle Data Pipeline spec
- Dashboard & Sync Infrastructure spec
- Cloud Infrastructure spec (new)

---

## ⛔ INVIOLABLE SAFETY RULES (applies to ALL phases)

These rules are non-negotiable. No cleanup task overrides them.

### Files/Directories — NEVER MODIFY
```
trading/spot/live/v14/state.json       ← live bot memory
trading/spot/live/v14/trades.csv       ← live trade log
trading/spot/live/v14/status.json      ← live bot status
trading/spot/paper/v14/state.json      ← V14 paper bot memory
trading/spot/paper/v14/trades.csv
trading/spot/paper/v14etf/state.json   ← V14-ETF paper bot memory
trading/spot/paper/v14etf/trades.csv
trading/spot/paper/v14_portfolio/      ← V14-PM paper bot (entire dir)
docs/                                  ← dashboard HTML + data (customer-facing)
```

### Procedures — ALWAYS
1. **Copy before delete** — new location must exist and be verified before old is removed
2. **Full import test after every change** — `python -c "from trading.spot.X import Y"` before moving on
3. **Git commit after each completed task** — clean rollback point at every step
4. **Scheduled task configs updated AFTER file is verified at new path** — never the other way around
5. **One task at a time** — complete + verify before starting the next

### The Test Suite (run before and after every Phase 3 task)
```powershell
cd C:\Users\Never\.openclaw\workspace
python -c "
from trading.spot.v14_lifecycle_engine import V14LifecycleEngine, V14_PROFILES
from trading.spot.exchange_client import SpotExchangeClient
from trading.spot.cfgi_client import CFGIClient
from trading.spot.incident_schema import create_incident_report
from trading.spot.v14_capital_manager import CapitalRouter
from trading.spot.v14_cycle_scanner import *
print('ALL IMPORTS OK')
"
```
If this fails at any point, stop and rollback before proceeding.

---

## Phase 3 — Codebase Cleanup
**Goal:** Clean, documented, deployable set of source files with no path hacks or mystery dependencies.
**Status:** 🔲 NOT STARTED
**Output:** Clean git commit tagged `v14pm-cloud-ready`

### Task List

#### 3.1 — Fix `sync_dashboard.ps1` (URGENT — caused today's outage)
- [ ] Audit exactly what `sync_dashboard.ps1` copies and why it could overwrite `.py` files
- [ ] Add explicit exclusions for all source `.py` files
- [ ] Test sync doesn't touch anything outside `docs/` and `trading/spot/live|paper/*/`

#### 3.2 — Promote V13 engine files to proper package
- [ ] Create `trading/spot/engine/` directory with `__init__.py`
- [ ] Move these 7 files from `backtest_results/v13/` → `trading/spot/engine/`:
  - `v14_dca_engine.py`
  - `v13_signals.py`
  - `v13_router_engine_v1.py`
  - `v13_router_engine_v2.py`
  - `_steve_3check.py`
  - `test_hvf_daily.py`
  - `v13_phase_backtest_v8.py`
- [ ] Update `v14_lifecycle_engine.py`: replace `sys.path.insert()` with proper `from trading.spot.engine.X import Y`
- [ ] Update `coin_scanner_v13.py`: update any direct imports
- [ ] Verify all 4 running bots still import cleanly after move
- [ ] **Do not move** `backtest_results/v13/candles.db`, `build_daily_candles.py` — these are backtest artifacts

#### 3.3 — Fix hardcoded DB path
- [ ] Update `v14_dca_engine.py`: replace hardcoded `DB_PATH` with `os.environ.get('AIT_CANDLES_DB', fallback)`
- [ ] Update `.env.template` to document `AIT_CANDLES_DB`
- [ ] Verify all callers pass or default to `trading/spot/data/candles.db`

#### 3.4 — Consolidate candle databases
- [ ] Confirm `trading/spot/data/candles.db` is the authoritative live DB
- [ ] Confirm `backtest_results/v13/candles.db` is only used for historical backtests
- [ ] Document which scripts use which DB; add comments to clarify

#### 3.5 — Rename misnamed files
- [ ] Rename `run_scanner_v13.py` → `run_v14_scanner.py`
- [ ] Update `V14CycleScanner` scheduled task to match new name
- [ ] Rename `coin_scanner_v13.py` → `coin_scanner.py`

#### 3.6 — Create `requirements.txt`
- [ ] Audit all imports across all `.py` files for third-party packages
- [ ] Generate `requirements.txt` with pinned versions from current environment
- [ ] Add dev/backtest extras in `requirements-dev.txt`

#### 3.7 — Create `trading/spot/live/v14/.env.template` for Hyperliquid
- [ ] Create `trading/spot/live/v14pm/.env.template` for V14 PM live bot
- [ ] Document all required env vars: API keys, Telegram token, DB path, etc.

#### 3.8 — Clean up workspace root
- [ ] Move `trading/test_api.py`, `trading/test_api2.py`, `trading/test_api3.py` → `trading/tests/` or delete
- [ ] Move `trading/_check_rejected.py`, `trading/_fix_tp.py` → archive or delete
- [ ] Confirm `trading/live/` (old legacy dir) vs `trading/spot/live/` — remove if obsolete

---

## Phase 4 — System Architecture Document
**Goal:** Single authoritative document describing the complete V14PM system.
**Status:** 🔲 NOT STARTED (starts after Phase 3 complete)
**Output:** `projects/ait-product/V14PM_SYSTEM_ARCHITECTURE.md`

### Document Structure

```
1. System Overview
   - Design philosophy
   - System diagram (ASCII)
   - Four-layer architecture

2. Data Pipeline
   - Candle collection (Hyperliquid API)
   - candles.db schema
   - Collector scheduling and failure handling

3. Intelligence Layer
   - DCA Cycle Velocity Score formula
   - Coin scanner (45-coin universe)
   - Signal stack: StochRSI, HVF, 3-check, Fib levels
   - ROUTER v2: HybridDetector2D (top/bottom detection)
   - Score history and trend multiplier

4. V14 DCA Engine
   - Phase machine: LONG_DCA → ROUTER → SHORT_DCA
   - DCA grid mechanics (BO, deviation, multiplier, layers, TP)
   - Risk profiles (Low / Medium / High)
   - Backfill vs live mode

5. V14 Lifecycle Engine
   - Hourly candle loop
   - Daily signal evaluation (midnight UTC)
   - State persistence (snapshot/restore)
   - Reconciliation

6. V14 PM Portfolio Manager
   - CapitalRouter: active/reserve pool split
   - Adjusted Score = Base DCA Score × Trend Multiplier
   - Dynamic coin slot management (10 slots)
   - Capital rotation on deal close
   - Incident schema and logging

7. Exchange Client
   - Hyperliquid API integration (perps)
   - Aster DEX integration (spot)
   - Order execution, balance reconciliation, fee handling
   - Paper trading mode

8. Presentation Layer
   - Dashboard architecture (V14, V14-ETF, V14-PM, Live)
   - Data flow: status.json → GitHub Pages → browser
   - Sync mechanism and scheduling

9. Operations
   - Scheduled tasks (Windows) / systemd units (Linux)
   - Monitoring and alerting (Telegram)
   - Log files and rotation
   - Restart procedures

10. Configuration Reference
    - All environment variables
    - Risk profile parameters
    - Bot launch flags
```

---

## Phase 5 — Cloud Migration Guide
**Goal:** Step-by-step runbook for a sysadmin to deploy V14PM on a production Linux server.
**Status:** 🔲 NOT STARTED (starts after Phase 4 complete)
**Output:** `projects/ait-product/CLOUD_MIGRATION_GUIDE.md`

### Document Structure

```
1. Infrastructure Specification
   - Recommended cloud provider + instance spec
   - OS: Ubuntu 22.04 LTS
   - Network: static IP, firewall rules, VPN considerations
   - Storage: SSD sizing for candles.db growth

2. Server Setup
   - OS hardening baseline
   - Python 3.12 installation
   - pip dependencies (requirements.txt)
   - Git clone + SSH key setup for GitHub Pages sync

3. Configuration
   - Environment variables (.env files)
   - Hyperliquid API credentials (mainnet)
   - Telegram bot token
   - GitHub PAT for dashboard sync

4. Database Migration
   - Copy candles.db from Windows → cloud
   - Verify integrity
   - Set AIT_CANDLES_DB env var

5. Service Deployment (systemd)
   - V14PMBot.service        (portfolio manager live)
   - V14PaperBot.service     (demo — keep running)
   - V14ETFPaperBot.service  (demo — keep running)
   - V14CandleCollector.service
   - V14Scanner.service
   - AIT_DashboardSync.service + .timer

6. Hyperliquid Live Trading Setup
   - Confirm exchange_client.py live mode
   - Mainnet API key generation and scoping
   - Initial capital allocation recommendation
   - Go-live checklist (test → paper → live)

7. Dashboard Sync Migration
   - Replace sync_dashboard.ps1 with shell script
   - cron schedule

8. Monitoring & Alerting
   - Telegram alert setup
   - Log rotation (logrotate config)
   - systemd watchdog for auto-restart

9. Demo Account Continuity Plan
   - Paper bots remain on Windows during cutover
   - GitHub Pages serves both Windows (paper) and cloud (live) data
   - Cutover checklist — zero downtime procedure

10. Rollback Plan
    - How to revert if cloud deployment has issues
    - State file backup procedure
```

---

## Work Gee Gee Can Do Autonomously

The following can be completed without interrupting Brett:

- Phase 2: Read and summarize all existing docs into `DOCUMENT_INDEX.md`
- Phase 3, tasks 3.1–3.8: All code cleanup (with the paper bots kept running)
- Phase 3: Generate `requirements.txt` from current Python env
- Phase 4: Write full architecture doc (from code + existing specs)
- Phase 5: Write migration guide skeleton (infrastructure decisions need Brett input)

## Decisions Needed from Brett

| Decision | Context | Phase |
|----------|---------|-------|
| Cloud provider preference | AWS/GCP/DigitalOcean/Hetzner/other | 5 |
| Instance size budget | Recommend 4 vCPU / 8GB RAM for headroom | 5 |
| Initial live capital for V14PM | How much USDT to start with on Hyperliquid mainnet | 5 |
| Paper bots: keep on Windows long-term or migrate too? | If migrated, demo continuity plan changes | 5 |
| Hyperliquid API key creation | Brett must do this on Hyperliquid UI | 5 |
| Coin universe for live PM | Same 45 coins as paper? Subset? | 4/5 |

---

## Timeline Estimate

| Phase | Effort | Who | ETA |
|-------|--------|-----|-----|
| 1 — Audit | ✅ Done | Gee Gee | 2026-03-09 |
| 2 — Doc Gather | ~2h | Gee Gee (autonomous) | 2026-03-09 |
| 3 — Cleanup | ~4h | Gee Gee (autonomous) | 2026-03-10 |
| 4 — Architecture Doc | ~3h | Gee Gee (autonomous) | 2026-03-11 |
| 5 — Migration Guide | ~4h | Gee Gee + Brett decisions | 2026-03-12 |

---

## Output File Map

```
projects/ait-product/
├── MIGRATION_PROJECT_PLAN.md          ← this file
├── V14_ARCHITECTURE_AUDIT.md          ← Phase 1 output ✅
├── DOCUMENT_INDEX.md                  ← Phase 2 output (TBD)
├── V14PM_SYSTEM_ARCHITECTURE.md       ← Phase 4 output (TBD)
└── CLOUD_MIGRATION_GUIDE.md           ← Phase 5 output (TBD)
```

---

_Last updated: 2026-03-09 by Gee Gee_
