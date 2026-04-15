# AIT V14PM — Production Migration Project Plan
_Owner: Brett | Agent: Gee Gee | Created: 2026-03-09 | Status: ACTIVE_
_Last updated: 2026-03-19 — All production decisions locked. See PRODUCTION_DECISIONS_2026-03-19.md_

---

## Objective

Produce a complete **System Architecture & Migration Guide** that a systems engineer with no prior context can use to stand up the full AIT V14PM trading system on a production Linux cloud server, connected to Hyperliquid for live trading.

## Product Clarity

**V14PM is the MVP.** This is the product being sold to customers and integrated with Hyperliquid for live trading. Everything else serves it:

| Component | Role |
|-----------|------|
| **V14PM** | ✅ **The product** — MVP for customer sales + Hyperliquid live trading |
| V14 Paper (HBAR/ATOM/LINK/NEAR) | Demo account — shows the DCA engine performing |
| V14 Live (ASTER/USDT) | Live proof-of-concept — validates engine with real capital ($340 seed, $351.20 exchange-verified). LIVE GUARD active. |
| Dashboards | Customer-facing — demo the PM and strategy performance |

> **V14-ETF Paper RETIRED (2026-03-17):** HBAR autonomously switched to DCA Short, causing
> losses. Lesson: Long↔Short direction changes need human-in-the-loop approval. Scheduled task
> unregistered. `status.json` renamed to `status.json.retired`. Files are no longer protected
> under the safety rules (can be archived or deleted without risk).

**Constraint:** The paper trading bots (V14, V14-PM) and their dashboards must remain running
and uninterrupted throughout. They are live demos for customers and partners.

---

## Approach

We work in six sequential phases. Cleanup happens *before* final documentation, so the architecture doc reflects the actual clean system — not the current state with inherited debt.

```
Phase 1: Audit          ← inventory everything (code, docs, data, tasks)
Phase 2: Document Gather ← collect and link all existing specs into one index
Phase 3: Cleanup        ← fix broken paths, move engine files, restore sources
Phase 4: Architecture   ← write the definitive system architecture document
Phase 5: Migration Guide ← step-by-step sysadmin runbook for cloud deployment
Phase 6: Aster Production Architecture ← build exchange-as-truth for live trading
```

> **Phase 6 added 2026-03-18** after the live Aster false TP sell incident ($22 loss) exposed
> the fundamental flaw in the current engine-as-truth architecture. The incident proved that
> the current design — engine state as primary truth with exchange as correction layer — is
> structurally wrong for live trading. Phase 6 builds the correct architecture: exchange and
> database as truth, engine as decision-maker only. See Architecture doc §16.

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

## Phase 3 — Codebase Cleanup
**Goal:** Clean, documented, deployable set of source files with no path hacks or mystery dependencies.
**Status:** 🔄 IN PROGRESS (engine files moved, requirements.txt created, some cleanup done)
**Output:** Clean git commit tagged `v14pm-cloud-ready`

### Task List

#### 3.1 — Fix `sync_dashboard.ps1` (URGENT — caused today's outage)
- [ ] Audit exactly what `sync_dashboard.ps1` copies and why it could overwrite `.py` files
- [ ] Add explicit exclusions for all source `.py` files
- [ ] Test sync doesn't touch anything outside `docs/` and `trading/spot/live|paper/*/`

#### 3.2 — Promote V13 engine files to proper package
- [x] Create `trading/spot/engine/` directory with `__init__.py`
- [x] Move 7 files from `backtest_results/v13/` → `trading/spot/engine/`
- [ ] Update `v14_lifecycle_engine.py`: replace `sys.path.insert()` with proper `from trading.spot.engine.X import Y`
- [ ] Update `coin_scanner_v13.py`: update any direct imports
- [ ] Verify all running bots still import cleanly after move
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
- [x] Audit all imports across all `.py` files for third-party packages
- [x] Generate `requirements.txt` with pinned versions from current environment
- [x] Add dev/backtest extras in `requirements-dev.txt`

#### 3.7 — Create `.env.template` for Hyperliquid
- [ ] Create `trading/spot/live/v14pm/.env.template` for V14 PM live bot
- [ ] Document all required env vars: API keys, Telegram token, DB path, etc.

#### 3.8 — Clean up workspace root
- [ ] Move `trading/test_api.py`, `trading/test_api2.py`, `trading/test_api3.py` → `trading/tests/` or delete
- [ ] Move `trading/_check_rejected.py`, `trading/_fix_tp.py` → archive or delete
- [ ] Confirm `trading/live/` (old legacy dir) vs `trading/spot/live/` — remove if obsolete

---

## Phase 4 — System Architecture Document
**Goal:** Single authoritative document describing the complete V14PM system.
**Status:** ✅ EXISTS (v1.2 → updating to v1.3 as of 2026-03-18)
**Output:** `projects/ait-product/V14PM_SYSTEM_ARCHITECTURE.md`

v1.3 additions include: LIVE GUARD pattern, resting limit orders, fill price handling,
TP catch-up fix, V14-ETF retirement, production architecture target, incident log (§17).

### Document Structure

```
1. System Overview (design philosophy, layers diagram, active components)
2. Repository Structure
3. Data Pipeline (candle collection, candles.db, daily resampling)
4. Intelligence Layer (DCA score, trend multiplier, signal stack, ROUTER v2)
5. V14 DCA Engine (phase machine, grid mechanics, risk profiles)
6. V14 Lifecycle Engine (runtime loop, state persistence, equity calculation,
   live bot exchange interaction, trade preservation, live trading safeguards,
   TP catch-up)
7. V14PM Portfolio Manager (CapitalRouter, allocation rules, rebalance)
8. Exchange Client (Hyperliquid, Aster, live bot methods)
9. Presentation Layer (dashboards, data flow)
10. Scheduled Tasks (Windows)
11. Monitoring & Alerting (Telegram, heartbeat, watchdog)
12. Environment Variables
13. CLI Reference
14. Python Environment
15. Key Design Decisions & Rationale
16. Future Architecture: Production Trading System
17. Incident Log (2026-03-17, 2026-03-18)
```

---

## Phase 5 — Cloud Migration Guide
**Goal:** Step-by-step runbook for a sysadmin to deploy V14PM on a production Linux server.
**Status:** ✅ EXISTS (v1.2 → updating to v1.3 as of 2026-03-18)
**Output:** `projects/ait-product/CLOUD_MIGRATION_GUIDE.md`

v1.3 additions include: D7 decision (Aster vs Hyperliquid), live bot runner requirements
expanded with LIVE GUARD, resting limit orders, fill price handling, human-in-the-loop for
direction changes, production architecture target section (§14), V14-ETF removed.

---

## Phase 6 — Aster Production Architecture
**Goal:** Build exchange-as-truth architecture for live Aster bot, then scale to V14PM.
**Status:** 🔲 PLANNING (driven by 2026-03-18 incident)
**Output:** Production-grade live trading infrastructure

> This phase was added after the 2026-03-18 incident (live Aster false TP sell, $22 loss)
> exposed the fundamental flaw in treating engine state as primary truth. The incident
> proved that reconciliation-after-the-fact is insufficient — the exchange must be the
> primary source of truth from the start.

### 6.1 — Phase 1: Exchange-as-Truth on Aster (current live bot)

| Task | Status | Notes |
|------|--------|-------|
| LIVE GUARD pattern | ✅ DONE | Engine TP sells blocked when exchange limit order is active |
| Resting limit orders | ✅ DONE | Exchange-native TP; fills without bot involvement |
| Fill price from exchange | ✅ DONE | Never fall back to engine price |
| PnL from actual proceeds | ✅ DONE | Engine capital corrected after sells |
| WebSocket fill listener | 🔲 TODO | Replace 65-second polling with real-time fill push |
| PostgreSQL DB as truth | 🔲 TODO | Replace state.json + trades.csv |
| Order Manager service | 🔲 TODO | Separate from signal engine |

### 6.2 — Phase 2: Scale to V14PM

| Task | Status | Notes |
|------|--------|-------|
| Decision: Aster or Hyperliquid | ⚠️ PENDING (D7) | Aster proven, Hyperliquid enables perps |
| V14PM live runner with full safeguards | 🔲 TODO | Implements items 13-17 from Migration Guide §5.4 |
| Multi-coin Order Manager | 🔲 TODO | Manages TP orders for N simultaneous positions |
| Portfolio-level DB schema | 🔲 TODO | Positions, fills, trades for multi-coin PM |

Paper bots remain on Windows with JSON/CSV architecture throughout.

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
trading/spot/paper/v14_portfolio/      ← V14-PM paper bot (entire dir)
docs/                                  ← dashboard HTML + data (customer-facing)
```

> **V14-ETF files no longer protected (2026-03-17):** Bot retired. The following files
> can be archived or deleted without risk:
> ```
> trading/spot/paper/v14etf/             ← RETIRED bot state (safe to archive)
> trading/spot/paper/v14etf/status.json.retired
> ```

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

## Active System Components (2026-03-18)

| Component | Entry Point | Exchange | Capital | Status |
|-----------|------------|----------|---------|--------|
| **V14PM Paper** | `run_v14_portfolio_paper.py` | Hyperliquid | $50K paper (~$53,815 equity) | ✅ Running — 102 deals, 100% win rate |
| **V14 Paper** | `run_v14_paper.py` | Hyperliquid | $10K paper (~$53,500 equity) | ✅ Running — 400 deals, 97.8% win rate |
| **V14 Live (Aster)** | `run_v14_live_aster.py` | Aster DEX | $340 seed ($351.20 actual) | ✅ Running — LIVE GUARD active |
| ~~V14-ETF Paper~~ | ~~`run_v14etf_paper.py`~~ | ~~Hyperliquid~~ | ~~$10K paper~~ | ❌ RETIRED 2026-03-17 |

---

## Work Gee Gee Can Do Autonomously

The following can be completed without interrupting Brett:

- Phase 2: Read and summarize all existing docs into `DOCUMENT_INDEX.md`
- Phase 3, tasks 3.1–3.8: All code cleanup (with the paper bots kept running)
- Phase 3: Generate `requirements.txt` from current Python env
- Phase 4: Write full architecture doc (from code + existing specs)
- Phase 5: Write migration guide skeleton (infrastructure decisions need Brett input)
- Phase 6.1: Continue implementing exchange-as-truth on Aster bot

## Decisions Needed from Brett

| Decision | Context | Phase |
|----------|---------|-------|
| Cloud provider preference | AWS/GCP/DigitalOcean/Hetzner/other | 5 |
| Instance size budget | Recommend 4 vCPU / 8GB RAM for headroom | 5 |
| Initial live capital for V14PM | How much USDT to start with on Hyperliquid mainnet | 5 |
| Paper bots: keep on Windows long-term or migrate too? | If migrated, demo continuity plan changes | 5 |
| Hyperliquid API key creation | Brett must do this on Hyperliquid UI | 5 |
| Coin universe for live PM | Same 45 coins as paper? Subset? | 4/5 |
| **Aster or Hyperliquid for V14PM production? (D7)** | Aster proven with live capital; Hyperliquid enables perps/leverage. Affects Phase 6.2 scope. | 6 |

---

## Timeline Estimate

| Phase | Effort | Who | ETA | Status |
|-------|--------|-----|-----|--------|
| 1 — Audit | ✅ Done | Gee Gee | 2026-03-09 | ✅ COMPLETE |
| 2 — Doc Gather | ~2h | Gee Gee (autonomous) | 2026-03-09 | 🔄 IN PROGRESS |
| 3 — Cleanup | ~4h | Gee Gee (autonomous) | 2026-03-10 | 🔄 IN PROGRESS (engine files moved, requirements.txt created) |
| 4 — Architecture Doc | ~3h | Gee Gee (autonomous) | 2026-03-11 | ✅ EXISTS (v1.3 as of 2026-03-18) |
| 5 — Migration Guide | ~4h | Gee Gee + Brett decisions | 2026-03-12 | ✅ EXISTS (v1.3 as of 2026-03-18) |
| 6 — Aster Production Architecture | ~20h+ | Gee Gee + Brett decisions | TBD | 🔲 PLANNING |

> **Phase 6 estimate:** Significantly larger than previous phases. WebSocket integration,
> PostgreSQL setup, and Order Manager service are production infrastructure work, not
> documentation. Phase 6.1 (Aster) estimated at ~20h engineering. Phase 6.2 (V14PM scale)
> depends on D7 decision.

---

## Output File Map

```
projects/ait-product/
├── MIGRATION_PROJECT_PLAN.md          ← this file
├── V14_ARCHITECTURE_AUDIT.md          ← Phase 1 output ✅
├── DOCUMENT_INDEX.md                  ← Phase 2 output (in progress)
├── V14PM_SYSTEM_ARCHITECTURE.md       ← Phase 4 output ✅ (v1.3)
└── CLOUD_MIGRATION_GUIDE.md           ← Phase 5 output ✅ (v1.3)
```

---

_Created: 2026-03-09 by Gee Gee_
_Updated: 2026-03-18 — Phase statuses updated, Phase 6 added (Aster Production Architecture),
V14-ETF retired, active components updated, safety rules updated, timeline revised.
Driven by 2026-03-18 live incident exposing engine-as-truth flaw._
