# V14PM System Architecture — Index

> **Use this file first.** Read specific line ranges from `V14PM_SYSTEM_ARCHITECTURE.md` (2,208 lines / 109KB) instead of loading the full document. Line numbers are stable until the next edit.
>
> **Last updated:** 2026-03-24 (all 4 upgrades deployed)

## Quick Lookup by Topic

| Topic | Section | Lines | What's There |
|-------|---------|-------|-------------|
| **How the system works** | Exec Summary | 6–96 | Plain-English overview, components, capital flow, safety |
| **Architecture diagram** | §7.1 | 1060–1112 | Full component tree with data flows |
| **Current bot status** | §7.10 | 1423–1446 | Which bots are running, equity, active coins |
| **Tier table & pool split** | §7.2 | 1113–1156 | Equity-tiered coin caps, pool splits, hysteresis rules |
| **Dynamic capital (deposits)** | §7.2.1 | 1157–1190 | Capital ledger, auto-detect, resize(), Telegram commands |
| **Per-coin pause** | §7.7 | 1283–1327 | PAUSE/RESUME per-coin, behavior, state persistence |
| **Per-coin regime flagging** | §7.7.1 | 1328–1389 | Detection, auto-clear, cooldown, interaction matrix |
| **Telegram commands** | §7.8 | 1390–1410 | Full command table (governance, capital, per-coin) |
| **DCA engine mechanics** | §5.2 | 568–612 | Grid layers, BO/Dev/Mult, TP calculation |
| **Signal stack (ROUTER v2)** | §4.5 | 497–543 | Phase transition signals, top/bottom detection |
| **Exchange-as-truth** | §6.8.1 | 929–957 | Core architecture principle, what was removed |
| **TP limit orders** | §6.8.2 | 958–975 | Resting orders on exchange, fill handling |
| **Regime monitor (global)** | §7.5 | 1216–1246 | Daily signal evaluation, tiered alerts, APPROVE/DENY |
| **Wind-down phase** | §7.6 | 1247–1282 | Direction change procedure |
| **Exchange client** | §8 | 1447–1573 | Supported exchanges, methods, API calls, credentials |
| **Dashboard** | §9 | 1574–1631 | Files, data flow, data files |
| **Scheduled tasks** | §10 | 1632–1654 | Windows scheduled tasks |
| **CLI launch commands** | §13 | 1718–1780 | All bot launch commands with flags |
| **Environment variables** | §12 | 1697–1717 | Complete env var reference |
| **Risk profiles** | §5.3 | 613–649 | Production profile, legacy profiles |
| **Database schema** | §3.2 | 308–368 | candles.db tables and columns |
| **State persistence** | §6.2 | 689–748 | state.json format, what's saved |
| **Startup sequence** | §6.5 | 866–899 | PM bot boot process, warmup |
| **Equity calculation** | §6.3 | 749–841 | How equity is computed, live vs paper |
| **Funding rate tracking** | §7.9 | 1411–1422 | 8-hour settlements, PnL integration |
| **Future architecture** | §16 | 1830–1968 | Production scaling plan, DB schema target, migration |
| **Incident log** | §17 | 1969–2096 | All production incidents and fixes |
| **Code audit (2026-03-21)** | §18 | 2097–2208 | 13 gaps found and resolved |
| **Design decisions** | §15 | 1803–1829 | Key rationale for architectural choices |
| **Repo structure** | §2 | 187–272 | File layout, module map |
| **DCA cycle scanner** | §4.1 | 390–424 | Velocity scoring, coin ranking |
| **Trend multiplier** | §4.2 | 425–444 | Acceleration/decline detection |
| **Coin universe** | §4.3 | 445–474 | 45-coin scanner universe |
| **Daily rebalance** | §7.3 | 1191–1201 | Midnight UTC rebalance procedure |
| **Candle pipeline** | §3.1 | 275–307 | Collection, 1h/1d resampling |

## Full Table of Contents

```
  6  Executive Summary
 11    What It Does
 17    How It Makes Decisions
 33    Key Safety Features
 44    How Capital Flows
 73    The Components
 85    Current Status (2026-03-21)
 98  1. System Overview
100    1.1 Product Description
119    1.2 Design Philosophy
130    1.3 System Layers
151    1.4 Active System Components
165    1.5 Class & Module Quick Reference
187  2. Repository Structure
273  3. Data Pipeline
275    3.1 Candle Collection & Daily Resampling
308    3.2 Database — candles.db
369    3.3 Daily Data — Two Paths
388  4. Intelligence Layer
390    4.1 DCA Cycle Velocity Score
425    4.2 Trend Multiplier
445    4.3 Coin Universe
475    4.4 Signal Stack (trading.spot.engine)
497    4.5 ROUTER v2 — Phase Transition Signal Stack
544  5. V14 DCA Engine
546    5.1 Phase Machine
568    5.2 DCA Grid Mechanics
613    5.3 Risk Profiles
615      Production Profile (Unified)
635      Legacy Profiles
650    5.4 Configuration (V14Config)
665  6. V14 Lifecycle Engine
667    6.1 Runtime Loop
689    6.2 State Persistence
749    6.3 Equity Calculation (All Bots)
779      6.3.1 Live Bot Equity & Exchange Interaction
842    6.4 Trade History Preservation
850      6.4.1 --fresh vs Normal Restart
866    6.5 PM Startup Sequence
883      6.5.1 Engine Warmup Period
900    6.6 PID Lock (Paper Trading)
912    6.7 Trade Provenance (recorded_at)
923    6.8 Live Trading Safeguards
929      6.8.1 Exchange-as-Truth Architecture ★
958      6.8.2 Resting Limit Orders (TP)
971      6.8.3 Fill Price Handling
976      6.8.4 PnL from Exchange Fills
981      6.8.5 Status.json — Exchange Data Only
991      6.8.6 Human-in-the-Loop Direction Changes
999      6.8.7 Data Source Map
1038   6.9 TP Catch-Up (Paper Bots)
1058 7. V14PM Portfolio Manager ★
1060   7.1 Architecture (component diagram)
1113   7.2 CapitalRouter — Allocation Rules
1157     7.2.1 Dynamic Capital Management (Upgrade 1)
1191   7.3 Daily Rebalance
1202   7.4 Global Strategy Direction
1216   7.5 Portfolio Regime Monitor
1247   7.6 Direction Change — Wind-Down Phase
1283   7.7 PAUSE / RESUME (Governance Override)
1328     7.7.1 Per-Coin Regime Flagging (Upgrade 3)
1390   7.8 Telegram Command Interface
1411   7.9 Funding Rate Tracking
1423   7.10 Current Bot Status ★
1447 8. Exchange Client
1449   8.1 Supported Exchanges
1463   8.2 Credential Resolution
1474   8.3 Exchange Defaults
1491   8.4 Paper Trading Mode
1497   8.5 Live Bot Methods (Aster Perps)
1519   8.6 External API Dependencies
1574 9. Presentation Layer
1576   9.1 Dashboard Files
1587   9.2 Data Flow
1609   9.3 Dashboard Data Files
1632 10. Scheduled Tasks (Windows)
1655 11. Monitoring & Alerting
1657   11.1 Telegram Notifications
1674   11.2 Heartbeat Health Check
1682   11.3 AIT_Watchdog
1697 12. Environment Variables
1718 13. CLI Reference
1781 14. Python Environment
1803 15. Key Design Decisions
1830 16. Future Architecture
1836   16.1 Why Current Architecture Cannot Scale
1852   16.2 Target Production Architecture
1877   16.3 Database Schema (Target)
1925   16.4 Migration Strategy: Aster Perps
1959   16.5 CSV Migration Path
1969 17. Incident Log
1971   17.1 V14-ETF Retirement
1988   17.2 TP Fill Model Fix
2001   17.3 Resting Limit Orders on Aster
2013   17.4 TP Catch-Up Bug Fix
2025   17.5 CRITICAL — Live Aster False TP Sell
2050   17.6 Scanner Summary Pick Fix
2061   17.7 False "Bot Frozen" Alerts (TZ bug)
2097 18. Code Audit & Gap Analysis (2026-03-21)
2103   18.1 Gap Summary Table
2121   18.2 Gap Details
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
