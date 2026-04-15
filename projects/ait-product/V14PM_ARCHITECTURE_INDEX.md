# V14PM System Architecture — Index

> **Use this file first.** Read specific line ranges from `V14PM_SYSTEM_ARCHITECTURE.md` (2,329 lines / ~116KB) instead of loading the full document. Line numbers are stable until the next edit.
>
> **Last updated:** 2026-04-15 (v1.8 — trailing stop live, incident §17.8, GAP-17, safeguard)

## Quick Lookup by Topic

| Topic | Section | Lines | What's There |
|-------|---------|-------|-------------|
| **How the system works** | Exec Summary | 6–98 | Plain-English overview, components, capital flow, safety |
| **Architecture diagram** | §7.1 | 1108–1160 | Full component tree with data flows |
| **Current bot status** | §7.10 | 1471–1495 | Which bots are running, equity, active coins |
| **Tier table & pool split** | §7.2 | 1161–1204 | Equity-tiered coin caps, pool splits, hysteresis rules |
| **Dynamic capital (deposits)** | §7.2.1 | 1205–1238 | Capital ledger, auto-detect, resize(), Telegram commands |
| **Per-coin pause** | §7.7 | 1331–1437 | PAUSE/RESUME per-coin, behavior, state persistence |
| **Per-coin regime flagging** | §7.7.1 | 1376–1437 | Detection, auto-clear, cooldown, interaction matrix |
| **Telegram commands** | §7.8 | 1438–1458 | Full command table (governance, capital, per-coin) |
| **DCA engine mechanics** | §5.2 | 571–617 | Grid layers, BO/Dev/Mult, TP calculation, trailing stop note |
| **Signal stack (ROUTER v2)** | §4.5 | 500–546 | Phase transition signals, top/bottom detection |
| **Exchange-as-truth** | §6.8.1 | 953–981 | Core architecture principle, what was removed |
| **Trailing stop TP** | §6.8.2 | 982–1018 | Exchange TRAILING_STOP_MARKET, paper simulation, feature flag, config |
| **Pre-order exchange checks** | Safety table | 40 | Every BUY checks balance, every SELL checks position |
| **Leverage enforcement** | Safety table | 41 | 1x enforcement on Aster (defaults 5x), persistence gap note |
| **Regime monitor (global)** | §7.5 | 1264–1294 | Daily signal evaluation, tiered alerts, APPROVE/DENY |
| **Wind-down phase** | §7.6 | 1295–1330 | Direction change procedure |
| **Exchange client** | §8 | 1497–1623 | Supported exchanges, methods, API calls, credentials |
| **Dashboard** | §9 | 1624–1681 | Files, data flow, data files |
| **Scheduled tasks** | §10 | 1682–1704 | Windows scheduled tasks |
| **CLI launch commands** | §13 | 1768–1830 | All bot launch commands with flags |
| **Environment variables** | §12 | 1747–1767 | Complete env var reference |
| **Risk profiles** | §5.3 | 618–673 | Production profile, legacy profiles |
| **Database schema** | §3.2 | 311–371 | candles.db tables and columns |
| **State persistence** | §6.2 | 713–772 | state.json format, what's saved |
| **Startup sequence** | §6.5 | 890–923 | PM bot boot process, warmup |
| **Equity calculation** | §6.3 | 773–865 | How equity is computed, live vs paper |
| **Funding rate tracking** | §7.9 | 1459–1470 | 8-hour settlements, PnL integration |
| **Future architecture** | §16 | 1880–2018 | Production scaling plan, DB schema target, migration |
| **Incident log** | §17 | 2019–2178 | All production incidents and fixes (incl. §17.8 revert) |
| **Accidental revert incident** | §17.8 | 2145–2178 | Code revert, .gitignore safeguard, root cause |
| **Code audit (2026-03-21+)** | §18 | 2179–2325 | 17 gaps found and resolved (GAPs 1-17) |
| **GAP-17 (low param bug)** | §18 | 2305–2315 | _long_dca_tick missing low, trailing callback detection |
| **Design decisions** | §15 | 1853–1879 | Key rationale for architectural choices |
| **Repo structure** | §2 | 190–275 | File layout, module map |
| **DCA cycle scanner** | §4.1 | 393–427 | Velocity scoring, coin ranking |
| **Trend multiplier** | §4.2 | 428–447 | Acceleration/decline detection |
| **Coin universe** | §4.3 | 448–477 | 45-coin scanner universe |
| **Daily rebalance** | §7.3 | 1239–1249 | Midnight UTC rebalance procedure |
| **Candle pipeline** | §3.1 | 278–310 | Collection, 1h/1d resampling |

## Full Table of Contents

```
   1  # Adaptive Intelligence Trading - V14PM System Architecture
   6  ## Executive Summary
  11    ### What It Does
  17    ### How It Makes Decisions
  33    ### Key Safety Features
  46    ### How Capital Flows
  75    ### The Components
  87    ### Current Status (2026-04-15)
 101  ## 1. System Overview
 103    ### 1.1 Product Description
 122    ### 1.2 Design Philosophy
 133    ### 1.3 System Layers
 154    ### 1.4 Active System Components
 168    ### 1.5 Class & Module Quick Reference
 190  ## 2. Repository Structure
 276  ## 3. Data Pipeline
 278    ### 3.1 Candle Collection & Daily Resampling
 311    ### 3.2 Database — candles.db
 372    ### 3.3 Daily Data — Two Paths
 391  ## 4. Intelligence Layer
 393    ### 4.1 DCA Cycle Velocity Score
 428    ### 4.2 Trend Multiplier
 448    ### 4.3 Coin Universe
 478    ### 4.4 Signal Stack (trading.spot.engine)
 500    ### 4.5 ROUTER v2 — Phase Transition Signal Stack
 547  ## 5. V14 DCA Engine
 549    ### 5.1 Phase Machine
 571    ### 5.2 DCA Grid Mechanics
 618    ### 5.3 Risk Profiles
 674    ### 5.4 Configuration (V14Config)
 689  ## 6. V14 Lifecycle Engine
 691    ### 6.1 Runtime Loop
 713    ### 6.2 State Persistence
 773    ### 6.3 Equity Calculation (All Bots)
 803      ### 6.3.1 Live Bot Equity & Exchange Interaction
 866    ### 6.4 Trade History Preservation
 874      ### 6.4.1 --fresh vs Normal Restart
 890    ### 6.5 PM Startup Sequence
 907      ### 6.5.1 Engine Warmup Period
 924    ### 6.6 PID Lock (Paper Trading)
 936    ### 6.7 Trade Provenance (recorded_at)
 947    ### 6.8 Live Trading Safeguards
 953      6.8.1 Exchange-as-Truth Architecture ★
 982      6.8.2 Trailing Stop as Primary TP Mechanism
1019      6.8.3 Fill Price Handling
1024      6.8.4 PnL from Exchange Fills
1029      6.8.5 Status.json — Exchange Data Only
1039      6.8.6 Human-in-the-Loop Direction Changes
1047      6.8.7 Data Source Map
1086    ### 6.9 TP Catch-Up (Paper Bots)
1106  ## 7. V14PM Portfolio Manager ★
1108    ### 7.1 Architecture
1161    ### 7.2 CapitalRouter — Allocation Rules
1205      ### 7.2.1 Dynamic Capital Management (Upgrade 1)
1239    ### 7.3 Daily Rebalance
1250    ### 7.4 Global Strategy Direction
1264    ### 7.5 Portfolio Regime Monitor
1295    ### 7.6 Direction Change — Wind-Down Phase
1331    ### 7.7 PAUSE / RESUME (Governance Override)
1376      ### 7.7.1 Per-Coin Regime Flagging (Upgrade 3)
1438    ### 7.8 Telegram Command Interface
1459    ### 7.9 Funding Rate Tracking
1471    ### 7.10 Current Bot Status ★
1497  ## 8. Exchange Client
1499    ### 8.1 Supported Exchanges
1513    ### 8.2 Credential Resolution
1524    ### 8.3 Exchange Defaults
1541    ### 8.4 Paper Trading Mode
1547    ### 8.5 Live Bot Methods (Aster Perps)
1569    ### 8.6 External API Dependencies
1624  ## 9. Presentation Layer
1626    ### 9.1 Dashboard Files
1637    ### 9.2 Data Flow
1659    ### 9.3 Dashboard Data Files
1682  ## 10. Scheduled Tasks (Windows)
1705  ## 11. Monitoring & Alerting
1707    ### 11.1 Telegram Notifications
1724    ### 11.2 Heartbeat Health Check
1732    ### 11.3 AIT_Watchdog
1747  ## 12. Environment Variables
1768  ## 13. CLI Reference
1789    ### V14PM Live Bot (production — Aster Perps)
1808    ### V14 Live Bot (Aster)
1815    ### Candle Collector (Linux)
1821    ### DCA Cycle Scanner (manual)
1831  ## 14. Python Environment
1853  ## 15. Key Design Decisions
1880  ## 16. Future Architecture
1886    ### 16.1 Why Current Architecture Cannot Scale
1902    ### 16.2 Target Production Architecture
1927    ### 16.3 Database Schema (Target)
1975    ### 16.4 Migration Strategy: Aster Perps
2009    ### 16.5 CSV Migration Path
2019  ## 17. Incident Log
2021    ### 17.1 V14-ETF Retirement
2038    ### 17.2 TP Fill Model Fix
2051    ### 17.3 Resting Limit Orders on Aster
2063    ### 17.4 TP Catch-Up Bug Fix
2075    ### 17.5 CRITICAL — Live Aster False TP Sell
2100    ### 17.6 Scanner Summary Pick Fix
2111    ### 17.7 False "Bot Frozen" Alerts (TZ bug)
2145    ### 17.8 CRITICAL — Accidental Code Revert
2179  ## 18. Code Audit & Gap Analysis
2185    ### 18.1 Gap Summary Table
2207    ### 18.2 Gap Details
```

## Upgrade History

| Upgrade | Date | Sections Added/Modified |
|---------|------|------------------------|
| Exchange-as-truth | 2026-03-21 | §6.8.1, §7.1, §18 (audit) |
| 0: Adaptive Tiers | 2026-03-24 | §7.2 (tier table, hysteresis), §7.10, §15 |
| 1: Dynamic Capital | 2026-03-24 | §7.2.1 (new), §7.8 (commands) |
| 2: Per-Coin Pause | 2026-03-24 | §7.7 (expanded), §7.8 (commands) |
| 3: Regime Flagging | 2026-03-24 | §7.7.1 (new), §7.8 (commands) |
| TZ Bug Incident | 2026-03-24 | §17.7 (new) |
| TP Exchange-as-Truth | 2026-03-24 | §6.8.2 (updated), safety table |
| Pre-order Exchange Checks | 2026-04-09 | Safety table, §18 GAPs 14-16 |
| Comprehensive Audit (3 phases) | 2026-04-09 | BO% 40→30, DCA_MAX_LAYERS clarified, leverage note, status.json fields |
| Trailing Stop TP | 2026-04-13 | §5.2 (note), §6.8.2 (rewritten), safety table |
| Accidental Revert + Safeguard | 2026-04-15 | §7.10 (status), §17.8 (incident), §18 GAP-17, .gitignore |

## Related Documents

| Document | Purpose | Status |
|----------|---------|--------|
| `V14PM_CHANGE_CONTROL.md` | Production change log (all code changes with dates) | ✅ Current |
| `V14PM_UPGRADE_SCOPE.md` | Detailed scope & test plans for Upgrades 0-3 | ✅ Current |
| `V14PM_PRODUCTION_CLONE_GUIDE.md` | Step-by-step guide to deploy a standalone clone | 🔄 In Progress |
| `PRODUCTION_DECISIONS_2026-03-19.md` | Key architectural decisions (exchange, profile, coins) | ✅ Reference |
| `v14-dca-architecture.md` | DCA engine design rationale | ✅ Stable |
| `TRAILING_STOP_DESIGN.md` | Trailing stop TP design and backtest results | ✅ Implemented |
| `V14PM_COMPREHENSIVE_AUDIT_REPORT.md` | Full 3-phase audit: static, logic, doc accuracy | ✅ Current |
| `V14PM_PHASE1_AUDIT_RESULTS.md` | Phase 1: Static analysis (18 files, 13 findings) | ✅ Current |
| `V14PM_PHASE2_AUDIT_RESULTS.md` | Phase 2: Component logic & integration (11 findings) | ✅ Current |
| `V14PM_PHASE3_AUDIT_RESULTS.md` | Phase 3: Documentation accuracy (55 claims checked) | ✅ Current |
| `V14PM_CODE_AUDIT_2026-03-21.md` | Deep code audit (findings merged into §18) | 📦 Archive |
| `CLOUD_MIGRATION_GUIDE.md` | Original migration guide (pre-exchange-as-truth) | ⚠️ Superseded by Production Clone Guide |
| `MIGRATION_PROJECT_PLAN.md` | Phase tracker for original migration | ⚠️ Superseded |
