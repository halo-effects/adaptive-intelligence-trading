# V14PM System Architecture — Section Index
_Use this to find sections by line number. Read with `offset` and `limit` instead of loading the full 64KB doc._

**Source:** `V14PM_SYSTEM_ARCHITECTURE.md` (v1.6, 2026-05-12, 1406 lines)

## Quick Lookup

| § | Section | Lines | Size | Key Content |
|---|---------|-------|------|-------------|
| 1 | **System Overview** | 1–53 | ~2KB | Product description, design philosophy, system layers diagram, active components table |
| 2 | **Repository Structure** | 55–114 | ~3KB | Full directory tree with file descriptions |
| 3 | **Data Pipeline** | 116–219 | ~5KB | Candle collection, DB schema, daily resampling, two-path daily data |
| 3.1 | Candle Collection & Resampling | 120–159 | | Three-step hourly pipeline, why resample exists |
| 3.2 | Database (`candles.db`) | 161–199 | | Tables, row counts, schema SQL, DB path warning |
| 3.3 | Daily Data — Two Paths | 201–219 | | `build_daily_candles.py` vs `resample_daily.py` |
| 4 | **Intelligence Layer** | 221–315 | ~5KB | DCA Score formula, trend multiplier, coin universe, signal stack |
| 4.1 | DCA Cycle Velocity Score | 223–250 | | Score formula, sim params (3.0% TP, 4 layers), scan windows |
| 4.2 | Trend Multiplier | 252–270 | | Adjusted Score formula, slope weights, output range [0.30, 1.50] |
| 4.3 | Coin Universe | 272–283 | | 44 coins across categories |
| 4.4 | Signal Stack | 285–304 | | All signals table (StochRSI, ADX, HVF, 3-check, Fib, HybridDetector2D, CFGI) |
| 4.5 | ROUTER v2 — Phase Transitions | 306–355 | | Top detection (OB93, divergence, timeout), bottom detection (triple gate, conviction) |
| 5 | **V14 DCA Engine** | 357–430 | ~4KB | Phase machine, grid mechanics, risk profiles, config |
| 5.1 | Phase Machine | 359–382 | | LONG_DCA / ROUTER / SHORT_DCA state diagram |
| 5.2 | DCA Grid Mechanics | 384–405 | | Layer formula, TP formula, no cooldown policy |
| 5.3 | Risk Profiles | 407–416 | | Low/Medium/High table (High = 4L, 3.0% TP, 1.0x leverage) |
| 5.4 | Configuration (`V14Config`) | 418–430 | | Default values, profile override notes |
| 6 | **Lifecycle Engine** | 432–620 | ~10KB | Runtime loop, state persistence, equity calc, trade history, startup |
| 6.1 | Runtime Loop | 434–452 | | Hourly tick + daily signal eval |
| 6.2 | State Persistence | 454–490 | | `engine_state.json` schema, `status.json` schema |
| 6.3 | Equity Calculation | 492–530 | | Ground-truth formula, CSV-as-source, live bot exchange API |
| 6.4 | Trade History Preservation | 532–565 | | `load_existing()`, `--fresh` vs normal restart, trade provenance |
| 6.5 | PM Startup Sequence | 567–590 | | 6-step boot sequence, warmup period |
| 6.6 | PID Lock | 592–600 | | Paper bot duplicate prevention |
| 6.7 | Trade Provenance (`recorded_at`) | 602–610 | | Forensic timestamp for phantom detection |
| 6.8 | Trade Reconciliation | 612–680 | | Standalone tool, startup reconciliation, RECONCILE command, deal ID fix |
| 7 | **V14PM Portfolio Manager** | 682–920 | ~12KB | Architecture, allocation rules, daily rebalance, regime system |
| 7.1 | Architecture | 684–698 | | PM structure diagram |
| 7.2 | CapitalRouter — Allocation Rules | 700–730 | | Pool split, equity tiers, entry qualification, capital rotation |
| 7.3 | Daily Rebalance | 732–755 | | 9-step midnight UTC rebalance, allocation lifecycle |
| 7.4 | Deposit/Withdrawal Detection | 766–820 | | Runtime detection formula, startup reconciliation, capital ledger, dashboard growth |
| 7.5 | Portfolio Regime System | 822–920 | | Two-level architecture, regime gate rule, graduated conviction alerts, dashboard display |
| 7.5.1 | Two-Level Regime Architecture | 825–850 | | Global vs per-coin regime diagram |
| 7.5.2 | Regime Gate Rule | 852–870 | | Phase match table, no forced closes |
| 7.5.3 | Graduated Conviction Alerts | 872–900 | | 7 thresholds (15%–50%), APPROVE/DENY flow |
| 7.5.4 | Dashboard Display | 902–920 | | Regime panel, gate card, header badges |
| 8 | **Exchange Client** | 935–975 | ~2KB | Supported exchanges, credential resolution, paper mode |
| 9 | **Presentation Layer** | 977–1030 | ~3KB | Dashboard files, data flow, data file paths |
| 10 | **Scheduled Tasks** | 1032–1060 | ~1.5KB | All Windows scheduled tasks table with triggers |
| 11 | **Monitoring & Alerting** | 1062–1100 | ~2KB | Telegram notifications, heartbeat health check, watchdog |
| 12 | **Environment Variables** | 1102–1125 | ~1.5KB | Complete env var reference table |
| 13 | **CLI Reference** | 1127–1175 | ~2.5KB | Launch commands for all bots, scanner, collector |
| 14 | **Python Environment** | 1177–1195 | ~1KB | Python 3.12, pip, 3 production deps |
| 15 | **Key Design Decisions** | 1197–1220 | ~1.5KB | Decision/rationale table (all locked decisions) |
| 16 | **Future: Trade DB Migration** | 1222–1400 | ~5KB | Why CSV won't scale, target schema, migration path |

## Common Tasks — Where to Look

| I need to... | Read § |
|-------------|--------|
| Understand how DCA scoring works | 4.1 (lines 223–250) |
| Check grid params / risk profiles | 5.3 (lines 407–416) |
| Debug a startup issue | 6.5 (lines 567–590) |
| Understand capital allocation | 7.2 (lines 700–730) |
| Check the regime gate logic | 7.5.2 (lines 852–870) |
| Find a scheduled task | 10 (lines 1032–1060) |
| Look up env vars | 12 (lines 1102–1125) |
| Get launch commands | 13 (lines 1127–1175) |
| Understand top/bottom detection | 4.5 (lines 306–355) |
| Check deposit detection logic | 7.4 (lines 766–820) |
| Review equity calculation | 6.3 (lines 492–530) |
| Find the daily rebalance flow | 7.3 (lines 732–755) |

## Version History
- v1.6 (2026-05-12): Grid optimization (3.0% TP, 4 layers). Scanner synced to production params. 30d window confirmed via walk-forward analysis.
