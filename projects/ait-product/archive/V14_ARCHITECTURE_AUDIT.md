# V14 System Architecture Audit
_Generated: 2026-03-09 | Status: Pre-cloud-migration_

---

## Executive Summary

The AIT system runs four live bots, all sharing a single execution engine (`v14_lifecycle_engine.py`). The core signal logic is V14 but carries V13 source files as embedded dependencies inside `backtest_results/v13/` — a dev artifact that needs to be promoted to a proper package before cloud migration. The system is otherwise well-structured and cloud-ready with targeted cleanup.

---

## Current Bot Inventory (DO NOT INTERRUPT)

| Bot | Entry Point | Exchange | Capital | Status Dir |
|-----|------------|----------|---------|-----------|
| V14 Live (ASTER/USDT) | `run_v14_live_aster.py` | Aster DEX | $300 real | `live/v14/` |
| V14 Paper (HBAR/ATOM/LINK/NEAR) | `run_v14_paper.py` | Hyperliquid (paper) | $10K demo | `paper/v14/` |
| V14-ETF Paper (SOL/XRP/LTC/HBAR/ADA) | `run_v14etf_paper.py` | Hyperliquid (paper) | $10K demo | `paper/v14etf/` |
| V14 PM Paper (10-coin dynamic) | `run_v14_portfolio_paper.py` | Hyperliquid (paper) | $50K demo | `paper/v14_portfolio/` |

---

## Dependency Graph

```
run_v14_paper.py
run_v14etf_paper.py          ──▶  trading.spot.v14_lifecycle_engine
run_v14_portfolio_paper.py   ──▶  trading.spot.v14_capital_manager (PM only)
run_v14_live_aster.py        ──▶  trading.spot.exchange_client

                    v14_lifecycle_engine.py
                         │
                         │  sys.path.insert → backtest_results/v13/
                         ▼
                    v14_dca_engine.py          ← V14 DCA core
                    v13_signals.py             ← Signal pack (StochRSI, structure)
                    v13_router_engine_v2.py    ← HybridDetector2D (top/bottom)
                         │
                         ▼
                    v13_router_engine_v1.py    ← Fib levels, base config
                    _steve_3check.py           ← 3-check detector
                    test_hvf_daily.py          ← HVF scoring
                    v13_phase_backtest_v8.py   ← V13Config, Phase enum
```

### Supporting Modules
- `v14_capital_manager.py` — CapitalRouter (PM allocation logic)
- `v14_cycle_scanner.py` — DCA cycle velocity scorer
- `run_scanner_v13.py` — Coin scanner (V13 signals over 45 coins)
- `run_daily_collector.py` — Candle data collector
- `exchange_client.py` — Exchange abstraction (Aster DEX, Hyperliquid)
- `incident_schema.py` — Incident reporting (imported by all runners)

### Data
- `trading/spot/data/candles.db` — Live candle database (primary)
- `trading/spot/backtest_results/v13/candles.db` — Legacy backtest DB (may be redundant)
- `trading/spot/data/*.csv` — Per-coin historical CSVs (45+ coins, 1h + 5m)
- `trading/scanner/` — Scanner output JSONs

---

## Issues Found

### 🔴 Critical (breaks cold-start on clean server)

**1. V13 source files embedded in `backtest_results/v13/`**
- `v14_lifecycle_engine.py` uses `sys.path.insert()` to reach `backtest_results/v13/` at runtime
- Files needed: `v14_dca_engine.py`, `v13_signals.py`, `v13_router_engine_v2.py`, `v13_router_engine_v1.py`, `_steve_3check.py`, `test_hvf_daily.py`, `v13_phase_backtest_v8.py`
- **Problem**: These are buried in a backtest folder, not a proper package. On a cloud server with a fresh clone, if these files are missing or wrong version, bot fails to start (we experienced this today).
- **Fix**: Move all 7 files into `trading/spot/engine/` (or `trading/spot/v14_core/`) as a proper sub-package with `__init__.py`. Update imports in `v14_lifecycle_engine.py`.

**2. Two `candles.db` files**
- `trading/spot/data/candles.db` (primary — used by live bots)
- `trading/spot/backtest_results/v13/candles.db` (legacy — unclear if still referenced)
- **Fix**: Confirm which DB is authoritative, remove or archive the other.

**3. No `incident_schema.py` found**
- All three paper runners import `from trading.spot.incident_schema import create_incident_report`
- File not found in audit scan — may be missing or in an unexpected location
- **Fix**: Locate and verify it exists; if missing, it will crash on import.

### 🟡 Medium (tech debt, confusing for cloud setup)

**4. `run_scanner_v13.py` — V13 naming**
- The coin scanner entry point is named `run_scanner_v13.py` but runs the V14 signal stack
- Misleading for documentation and onboarding
- **Fix**: Rename to `run_scanner.py` or `run_v14_scanner.py`

**5. `backtest_results/v13/` directory name**
- The directory containing live production engine files is called `backtest_results/v13/`
- Visually implies legacy/test code; actually contains production signal logic
- **Fix**: After moving to `trading/spot/engine/`, this folder becomes backtest-only artifacts

**6. No `__init__.py` audit**
- Python package structure relies on `__init__.py` files being present
- Cloud server needs clean package layout to import as `trading.spot.*`
- **Fix**: Verify `__init__.py` exists in `trading/`, `trading/spot/` before migration

**7. Scheduled tasks are Windows-only**
- V14PaperBot, V14ETFPaperBot, V14PMPaperBot, AIT_DashboardSync all run via Windows Task Scheduler
- **Fix**: Convert to `systemd` services or `supervisor` for Linux cloud server

### 🟢 Low (polish)

**8. `V14LiveAster` scheduled task not yet created**
- Live bot has no scheduled restart on reboot (HEARTBEAT.md notes this)
- Currently requires manual restart after crashes
- **Fix**: Create scheduled task (Windows) now; convert to systemd on cloud

**9. Dual `candles.db` path in `v14_dca_engine.py`**
- `DB_PATH = Path(__file__).resolve().parent.parent.parent / 'data' / 'candles.db'`
- Relative path depends on file location — breaks if engine is moved
- **Fix**: Make DB path an environment variable or config value

---

## V14 PM Architecture (Current)

The PM bot is the most sophisticated bot and the target for Hyperliquid live production:

```
run_v14_portfolio_paper.py
    │
    ├── V14LifecycleEngine (per coin)     ← shared engine, one instance per slot
    ├── CapitalRouter (v14_capital_manager.py)
    │       ├── active_cash pool          ← deployed capital
    │       ├── reserve_cash pool         ← held back for new opportunities
    │       └── tier_coin_cap (10 slots)
    │
    └── Cycle Scanner (v14_cycle_scanner.py)
            └── Adjusted Score = Base DCA Score × Trend Multiplier
                (1.5x accelerating, 0.36x–0.8x declining)
```

**Live status (2026-03-09):**
- 10 active coins: ZRO, TAO, NEAR, PENDLE, STX, DOT, INJ, ENS, HYPE, ATOM
- Equity: $50,677.97 (+1.36%) on $50K paper
- Realized PnL: $669.09 | Win rate: 100% | Drawdown: 0.0%
- All coins at layer 1 (early in DCA grids) — regime: RANGING

---

## Cloud Migration Checklist (Pre-requisites)

### Code Cleanup (do before migration)
- [ ] Resolve `incident_schema.py` — confirm or create
- [ ] Move V13 engine files → `trading/spot/engine/` package
- [ ] Update `v14_lifecycle_engine.py` imports (remove `sys.path.insert`)
- [ ] Fix `DB_PATH` in `v14_dca_engine.py` → use env var
- [ ] Verify `__init__.py` in all packages
- [ ] Rename `run_scanner_v13.py` → `run_v14_scanner.py`
- [ ] Confirm or remove legacy `backtest_results/v13/candles.db`

### Infrastructure (cloud server setup)
- [ ] Choose cloud provider + instance size (recommend: 2 vCPU / 4GB RAM, Ubuntu 22.04)
- [ ] Python 3.12 + pip dependencies documented in `requirements.txt`
- [ ] Convert Windows Scheduled Tasks → `systemd` service units
- [ ] Set up environment variables (API keys, DB path, Telegram token)
- [ ] Set up `candles.db` sync or migration strategy
- [ ] Dashboard sync: replace Windows Task → cron job + git push

### Hyperliquid Live Trading
- [ ] Confirm `exchange_client.py` has Hyperliquid live (non-paper) mode
- [ ] Audit order execution path in `run_v14_portfolio_paper.py` for paper vs. live flag
- [ ] Set up Hyperliquid API credentials (mainnet)
- [ ] Decide initial capital allocation and coin slot configuration
- [ ] Create `run_v14_portfolio_live.py` (or add `--live` flag to existing runner)
- [ ] Test on Hyperliquid testnet before mainnet

### Demo Account Preservation
- [ ] Paper bots (V14, V14-ETF, V14-PM) continue running on current Windows machine during migration
- [ ] Dashboard sync (`AIT_DashboardSync`) continues uninterrupted
- [ ] No changes to `paper/v14/`, `paper/v14etf/`, `paper/v14_portfolio/` state files

---

## Recommended Migration Sequence

1. **Now (Windows):** Fix `incident_schema.py`, create `V14LiveAster` scheduled task
2. **This week:** Move engine files to proper package, fix imports, test all bots still start
3. **Next:** Provision cloud server, set up Python env, port scheduled tasks to systemd
4. **Then:** Migrate candle DB, run PM bot on cloud in paper mode first
5. **Finally:** Hyperliquid live credentials, start with small capital, PM bot goes live

---

_Audit by Gee Gee — update this doc as items are resolved._
