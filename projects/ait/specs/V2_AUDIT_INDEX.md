# V2 System Audit Plan — Section Index
_Use this to find sections by line number. Read with `offset` and `limit` instead of loading the full 42KB doc._

**Source:** `v2-system-audit-plan.md` (2026-05-10, 665 lines)
**Related findings:** `v2-audit-phase1-findings.md` through `v2-audit-phase8-11-findings.md`, `v2-audit-summary.md`

## Quick Lookup

| § | Section | Lines | Key Content |
|---|---------|-------|-------------|
| — | **Preamble** | 1–10 | Status, scope (25,087 lines, 38 files), goal |
| — | **Why Another Audit** | 11–33 | 8 post-v1 bugs table, pattern analysis |
| — | **Methodology** | 35–64 | Full system mapping approach, evidence standard, ground rules |
| — | **System Domains** | 66–116 | 7 domains overview table, domain dependency diagram |
| **P1** | **Data Pipeline** | 118–152 | Files (5), checklist (candle collection, DB schema, resampling), key questions |
| **P2** | **Intelligence Layer** | 154–218 | Files (6), signal pack audit, ROUTER v2, Steve 3-check, HVF, key questions |
| **P3** | **Coin Selection & Scoring** | 220–260 | Files (3), DCA scanner, score history/trend, legacy scanner, key questions |
| **P4** | **Portfolio Mgmt & Capital** | 262–327 | Files (3), CapitalRouter, rebalance, regime system, coin lifecycle, key questions |
| **P5** | **Trade Execution Engine** | 329–398 | Files (4), V14 DCA engine, lifecycle wrapper, exchange client, order execution, exchange sync |
| **P6** | **State & Persistence** | 400–446 | State files (7), consistency matrix, restart behavior matrix, numerical precision |
| **P7** | **Presentation Layer** | 448–500 | Files (6), PM dashboard, other dashboards, sync script, key questions |
| **P8** | **Infrastructure & Ops** | 502–560 | Files (5), scheduled tasks, sync/pipeline/watchdog scripts, cron jobs, Telegram |
| **P9** | **Integration Testing** | 562–591 | End-to-end lifecycle traces, error propagation, race conditions, accounting integrity |
| **P10** | **Migration Risk Register** | 593–610 | Hyperliquid migration risks and blockers |
| **P11** | **Documentation Reconciliation** | 612–633 | Architecture doc vs code truth, spec currency |
| — | **Deliverables** | 635–645 | Expected outputs |
| — | **Schedule** | 647–665 | Phase estimates (16–20 sessions total) |

## Finding Documents

| Phase | Findings Doc | Lines | Key Findings |
|-------|-------------|-------|-------------|
| P1 | `v2-audit-phase1-findings.md` | 184 | Data pipeline gaps |
| P2 | `v2-audit-phase2-findings.md` | 204 | Signal stack issues |
| P3 | `v2-audit-phase3-findings.md` | 246 | Scanner/scoring issues |
| P4 | `v2-audit-phase4-findings.md` | 237 | Capital allocation bugs |
| P5–7 | `v2-audit-phase5-findings.md` | 151 | Execution engine, state, dashboards |
| P8–11 | `v2-audit-phase8-11-findings.md` | 132 | Infra, integration, migration, docs |
| Summary | `v2-audit-summary.md` | 186 | 60 findings, 15 fixed, priority matrix |

## Common Tasks — Where to Look

| I need to... | Read |
|-------------|------|
| Understand audit scope and why it exists | Lines 1–33 |
| Check what a specific phase covers | See phase table above |
| Find findings for a phase | See findings doc table above |
| Get the overall results | `v2-audit-summary.md` |
| Check migration risks | Phase 10 (lines 593–610) |
| Review cross-cutting concerns | Phase 9 (lines 562–591) |
