# V14PM System Architecture — Index

> **Use this file first.** Read specific line ranges from `V14PM_SYSTEM_ARCHITECTURE.md` (2,234 lines / 111KB) instead of loading the full document. Line numbers are stable until the next edit.
>
> **Last updated:** 2026-04-15 (v2.0 — trailing stop callback 0.5%→0.2%, git source protection, backtest validation)

## Quick Lookup by Topic

| Topic | Section | Lines | What's There |
|-------|---------|-------|-------------|
| **How the system works** | Exec Summary | 6–98 | Plain-English overview, components, capital flow, safety |
| **Architecture diagram** | §7.1 | 1061–1113 | Full component tree with data flows |
| **Current bot status** | §7.10 | 1424–1447 | Which bots are running, equity, active coins |
| **Tier table & pool split** | §7.2 | 1114–1157 | Equity-tiered coin caps, pool splits, hysteresis rules |
| **Dynamic capital (deposits)** | §7.2.1 | 1158–1191 | Capital ledger, auto-detect, resize(), Telegram commands |
| **Per-coin pause** | §7.7 | 1284–1390 | PAUSE/RESUME per-coin, behavior, state persistence |
| **Per-coin regime flagging** | §7.7.1 | 1329–1390 | Detection, auto-clear, cooldown, interaction matrix |
| **Telegram commands** | §7.8 | 1391–1411 | Full command table (governance, capital, per-coin) |
| **DCA engine mechanics** | §5.2 | 569–613 | Grid layers, BO/Dev/Mult, TP calculation |
| **Signal stack (ROUTER v2)** | §4.5 | 498–544 | Phase transition signals, top/bottom detection |
| **Exchange-as-truth** | §6.8.1 | 930–958 | Core architecture principle, what was removed |
| **TP trailing stop orders** | §6.8.2 | 959–976 | Trailing stop mechanism: activation at +1.5%, 0.2% callback, Aster native. Updated 2026-04-15 |
| **Pre-order exchange checks** | Safety table | 40 | Every BUY checks balance, every SELL checks position |
| **Leverage enforcement** | Safety table | 41 | 1x enforcement on Aster (defaults 5x), persistence gap note |
| **Regime monitor (global)** | §7.5 | 1217–1247 | Daily signal evaluation, tiered alerts, APPROVE/DENY |
| **Wind-down phase** | §7.6 | 1248–1283 | Direction change procedure |
| **Exchange client** | §8 | 1448–1574 | Supported exchanges, methods, API calls, credentials |
| **Dashboard** | §9 | 1575–1632 | Files, data flow, data files |
| **Scheduled tasks** | §10 | 1633–1655 | Windows scheduled tasks |
| **CLI launch commands** | §13 | 1719–1781 | All bot launch commands with flags |
| **Environment variables** | §12 | 1698–1718 | Complete env var reference |
| **Risk profiles** | §5.3 | 614–650 | Production profile, legacy profiles |
| **Database schema** | §3.2 | 309–369 | candles.db tables and columns |
| **State persistence** | §6.2 | 690–749 | state.json format, what's saved |
| **Startup sequence** | §6.5 | 867–900 | PM bot boot process, warmup |
| **Equity calculation** | §6.3 | 750–842 | How equity is computed, live vs paper |
| **Funding rate tracking** | §7.9 | 1412–1423 | 8-hour settlements, PnL integration |
| **Future architecture** | §16 | 1831–1969 | Production scaling plan, DB schema target, migration |
| **Incident log** | §17 | 1970–2097 | All production incidents and fixes |
| **Code audit (2026-03-21+)** | §18 | 2098–2234 | 16 gaps found and resolved (GAPs 1-16) |
| **Design decisions** | §15 | 1804–1830 | Key rationale for architectural choices |
| **Repo structure** | §2 | 188–273 | File layout, module map |
| **DCA cycle scanner** | §4.1 | 391–425 | Velocity scoring, coin ranking |
| **Trend multiplier** | §4.2 | 426–445 | Acceleration/decline detection |
| **Coin universe** | §4.3 | 446–475 | 45-coin scanner universe |
| **Daily rebalance** | §7.3 | 1192–1202 | Midnight UTC rebalance procedure |
| **Candle pipeline** | §3.1 | 276–308 | Collection, 1h/1d resampling |

## Full Table of Contents

```
   1  # Adaptive Intelligence Trading - V14PM System Architecture
   6  ## Executive Summary
  11    ### What It Does
  17    ### How It Makes Decisions
  33    ### Key Safety Features
  45    ### How Capital Flows
  74    ### The Components
  86    ### Current Status (2026-03-21)
  99  ## 1. System Overview
 101    ### 1.1 Product Description
 120    ### 1.2 Design Philosophy
 131    ### 1.3 System Layers
 152    ### 1.4 Active System Components
 166    ### 1.5 Class & Module Quick Reference
 188  ## 2. Repository Structure
 274  ## 3. Data Pipeline
 276    ### 3.1 Candle Collection & Daily Resampling
 309    ### 3.2 Database — candles.db
 370    ### 3.3 Daily Data — Two Paths
 389  ## 4. Intelligence Layer
 391    ### 4.1 DCA Cycle Velocity Score
 426    ### 4.2 Trend Multiplier
 446    ### 4.3 Coin Universe
 476    ### 4.4 Signal Stack (trading.spot.engine)
 498    ### 4.5 ROUTER v2 — Phase Transition Signal Stack
 545  ## 5. V14 DCA Engine
 547    ### 5.1 Phase Machine
 569    ### 5.2 DCA Grid Mechanics
 614    ### 5.3 Risk Profiles
 651    ### 5.4 Configuration (V14Config)
 666  ## 6. V14 Lifecycle Engine
 668    ### 6.1 Runtime Loop
 690    ### 6.2 State Persistence
 750    ### 6.3 Equity Calculation (All Bots)
 780      ### 6.3.1 Live Bot Equity & Exchange Interaction
 843    ### 6.4 Trade History Preservation
 851      ### 6.4.1 --fresh vs Normal Restart
 867    ### 6.5 PM Startup Sequence
 884      ### 6.5.1 Engine Warmup Period
 901    ### 6.6 PID Lock (Paper Trading)
 913    ### 6.7 Trade Provenance (recorded_at)
 924    ### 6.8 Live Trading Safeguards
 930      6.8.1 Exchange-as-Truth Architecture ★
 959      6.8.2 Resting Limit Orders (TP)
 972      6.8.3 Fill Price Handling
 977      6.8.4 PnL from Exchange Fills
 982      6.8.5 Status.json — Exchange Data Only
 992      6.8.6 Human-in-the-Loop Direction Changes
1000      6.8.7 Data Source Map
1039    ### 6.9 TP Catch-Up (Paper Bots)
1059  ## 7. V14PM Portfolio Manager ★
1061    ### 7.1 Architecture
1114    ### 7.2 CapitalRouter — Allocation Rules
1158      ### 7.2.1 Dynamic Capital Management (Upgrade 1)
1192    ### 7.3 Daily Rebalance
1203    ### 7.4 Global Strategy Direction
1217    ### 7.5 Portfolio Regime Monitor
1248    ### 7.6 Direction Change — Wind-Down Phase
1284    ### 7.7 PAUSE / RESUME (Governance Override)
1329      ### 7.7.1 Per-Coin Regime Flagging (Upgrade 3)
1391    ### 7.8 Telegram Command Interface
1412    ### 7.9 Funding Rate Tracking
1424    ### 7.10 Current Bot Status ★
1448  ## 8. Exchange Client
1450    ### 8.1 Supported Exchanges
1464    ### 8.2 Credential Resolution
1475    ### 8.3 Exchange Defaults
1492    ### 8.4 Paper Trading Mode
1498    ### 8.5 Live Bot Methods (Aster Perps)
1520    ### 8.6 External API Dependencies
1575  ## 9. Presentation Layer
1577    ### 9.1 Dashboard Files
1588    ### 9.2 Data Flow
1610    ### 9.3 Dashboard Data Files
1633  ## 10. Scheduled Tasks (Windows)
1656  ## 11. Monitoring & Alerting
1658    ### 11.1 Telegram Notifications
1675    ### 11.2 Heartbeat Health Check
1683    ### 11.3 AIT_Watchdog
1698  ## 12. Environment Variables
1719  ## 13. CLI Reference
1740    ### V14PM Live Bot (production — Aster Perps)
1759    ### V14 Live Bot (Aster)
1766    ### Candle Collector (Linux)
1772    ### DCA Cycle Scanner (manual)
1782  ## 14. Python Environment
1804  ## 15. Key Design Decisions
1831  ## 16. Future Architecture
1837    ### 16.1 Why Current Architecture Cannot Scale
1853    ### 16.2 Target Production Architecture
1878    ### 16.3 Database Schema (Target)
1926    ### 16.4 Migration Strategy: Aster Perps
1960    ### 16.5 CSV Migration Path
1970  ## 17. Incident Log
1972    ### 17.1 V14-ETF Retirement
1989    ### 17.2 TP Fill Model Fix
2002    ### 17.3 Resting Limit Orders on Aster
2014    ### 17.4 TP Catch-Up Bug Fix
2026    ### 17.5 CRITICAL — Live Aster False TP Sell
2051    ### 17.6 Scanner Summary Pick Fix
2062    ### 17.7 False "Bot Frozen" Alerts (TZ bug)
2098  ## 18. Code Audit & Gap Analysis
2104    ### 18.1 Gap Summary Table
2122    ### 18.2 Gap Details
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

## Related Documents

| Document | Purpose | Status |
|----------|---------|--------|
| `V14PM_CHANGE_CONTROL.md` | Production change log (all code changes with dates) | ✅ Current |
| `V14PM_UPGRADE_SCOPE.md` | Detailed scope & test plans for Upgrades 0-3 | ✅ Current |
| `V14PM_PRODUCTION_CLONE_GUIDE.md` | Step-by-step guide to deploy a standalone clone | 🔄 In Progress |
| `PRODUCTION_DECISIONS_2026-03-19.md` | Key architectural decisions (exchange, profile, coins) | ✅ Reference |
| `v14-dca-architecture.md` | DCA engine design rationale | ✅ Stable |
| `V14PM_COMPREHENSIVE_AUDIT_REPORT.md` | Full 3-phase audit: static, logic, doc accuracy | ✅ Current |
| `V14PM_PHASE1_AUDIT_RESULTS.md` | Phase 1: Static analysis (18 files, 13 findings) | ✅ Current |
| `V14PM_PHASE2_AUDIT_RESULTS.md` | Phase 2: Component logic & integration (11 findings) | ✅ Current |
| `V14PM_PHASE3_AUDIT_RESULTS.md` | Phase 3: Documentation accuracy (55 claims checked) | ✅ Current |
| `V14PM_CODE_AUDIT_2026-03-21.md` | Deep code audit (findings merged into §18) | 📦 Archive |
| `CLOUD_MIGRATION_GUIDE.md` | Original migration guide (pre-exchange-as-truth) | ⚠️ Superseded by Production Clone Guide |
| `MIGRATION_PROJECT_PLAN.md` | Phase tracker for original migration | ⚠️ Superseded |
