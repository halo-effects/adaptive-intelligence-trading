# AIT — Project Overview
_Last updated: 2026-05-15_

## Product
**Adaptive Intelligence Trading** — Automated crypto DCA trading system with signal-directed phase transitions and dynamic capital rotation.

## Architecture
- **V14 DCA Engine**: Signal-directed continuous DCA with LONG/SHORT phases
- **V14PM Portfolio Manager**: Capital rotation across 10 coin slots using DCA Cycle Velocity scoring + trend multipliers
- **Signal Stack**: V13SignalPack (StochRSI, ADX, structure), HybridDetector2D (top/bottom), Steve 3-Check, CFGI
- **Exchange**: Hyperliquid perps (production), Aster DEX (proof-of-concept)
- **Data Pipeline**: Hourly candle collection → daily resampling → DCA cycle scanner
- **Dashboards**: GitHub Pages (4 dashboards, synced every 10 min)

## Architecture Documents
- `projects/ait-product/V14PM_SYSTEM_ARCHITECTURE.md` (v1.7) — Complete system reference
- `projects/ait-product/CLOUD_MIGRATION_GUIDE.md` (v1.1) — Linux deployment guide
- `projects/ait-product/V14PM_FULL_AUDIT.md` — End-to-end code audit (2026-03-10)
- `projects/ait-product/CODE_AUDIT_FINDINGS.md` — Bug tracker
- `projects/ait-product/conviction-stack-spec.md` — Signal stack specification
- `projects/ait-product/portfolio-capital-management.md` — Capital allocation spec

## Key Decisions (Locked)
| Decision | Date | Detail |
|----------|------|--------|
| V14 is sole engine | 2026-03-02 | V13 sunset (+184.5% final), V14 only go-forward |
| Hyperliquid is production exchange | 2026-03-03 | Aster too limited; HL has 45+ quality perps |
| DCA Cycle Velocity scoring | 2026-03-03 | `Score = Realized_PnL × (1-MaxDD%) × Capital_Freedom / 100` |
| PM capital = $50K, 10 coin slots | 2026-03-06 | Equity tier at $50K+ = 10 simultaneous coins |
| Trend multiplier in allocation | 2026-03-06 | `Adjusted Score = DCA Score × Trend Multiplier` [0.30, 1.50] |
| High profile, 1.0x leverage for PM | 2026-05-12 | **4 layers, 3.0% TP**, 1.5% dev, 1.5x SO mult, no liquidation risk (was 12L/1.5% TP before 2026-05-12) |
| Conviction: 3D DX + 2W K≥5 + score≥3/4 | 2026-02-28 | Bottom detection locked |
| Top: OB93 arm + 2D divergence (35d timeout) | 2026-02-28 | Top detection locked |
| Ground-truth equity formula | 2026-03-08 | `Capital + Realized PnL - Fees + Unrealized PnL` |
| State persistence via engine_state.json | 2026-03-10 | Engines save/restore across restarts, no phantom trades |
| Daily resampling in pipeline | 2026-03-10 | 1h→daily ensures all coins have signal data |
| --fresh for first launch only | 2026-03-10 | Normal restarts use engine_state.json |
| Macro conviction signals observational | 2026-03-08 | 6 index-level signals documented, not wired into bot logic |
| Trend multiplier gates entry not exit | 2026-03-06 | Declining coins get less capital but existing positions stay |

## Current State (2026-05-10)
- **V14PM Live (Aster)**: $423 capital (seed=$300 + $40 deposit), 96 trades, ~84% win rate
  - **Grid optimization (2026-05-12)**: TP 3.0%, Max 4 layers (was 1.5%/12L). Backtest: +26.3% PnL. Spec: `specs/grid-optimization-tp3-4layer.md`
  - **Trailing stop**: Enabled, 0.2% callback. Activation at new 3.0% TP.
  - DEX-as-truth startup, exchange-truth trade recording, warmup-only candle replay
  - **Auto deposit/withdrawal detection ENABLED** (2026-05-11): Consecutive balance comparison, no unrealized PnL
  - **Regime phase gate deployed + fixed (2026-05-15)**: Coins trade only when engine phase matches global regime. Gate blocks entries (BUY/SHORT_OPEN) with `reject_action()` rollback; exits (SELL/SHORT_CLOSE/TP) always pass through. Initial gate (05-13) had two bugs: blocked exits (trapping positions) and no rollback (phantom state drift).
  - **seed_capital immutable** (Hard Rule #26): CLI --capital arg, never recalculated
  - **Dashboard growth**: `(equity - seed - net_deposits) / seed` — isolates trading from capital flows
  - **Capital ledger baseline**: seed=$300, deposit=$40, pnl_adjustment=$64.59 (dark PnL gap)
  - **V2 System Audit complete**: 60 findings, 15 fixed, 1 HIGH remaining (auto-restart task)
  - **Scanner synced** (2026-05-12): Params match production (3.0% TP, 4L). 30d window confirmed optimal via walk-forward analysis.
  - Approved symbols: `[JUP/USDT, ONDO/USDT, PENDLE/USDT, TON/USDT]` (scanner top)
- **V14 Paper**: Running on Hyperliquid
- **V14-ETF Paper**: Running
- **V14 Live (Aster, single-coin)**: ASTER/USDT, running
- **Data sync cron**: Fixed Windows pathspec bug, runs every 10 min

## Key Decisions (Recent)
| Decision | Date | Detail |
|----------|------|--------|
| DEX-as-truth for capital | 2026-05-08 | Exchange wallet balance IS capital. No more state.json/ledger/CLI for capital. |
| Reconciliation disabled | 2026-05-08 | Heuristic fill-grouping creates phantom trades from churn. TP recovery handles missed fills. |
| Auto deposit detection disabled | 2026-05-08 | Formula broken for DEX-as-truth. Manual DEPOSIT/WITHDRAW commands only. |
| Warmup-only candle replay | 2026-05-09 | Old candles update indicators only; only current candle executes actions. |
| Exchange-truth trade recording | 2026-05-09 | Use DEX entry price × actual qty, not engine's internal price tracking. |
| Regime phase gate | 2026-05-09 | Coins trade only when engine phase matches global regime. Engine phases never overwritten. |
| Graduated conviction alerts | 2026-05-09 | 7 thresholds (15-50%), APPROVE at any level, DENY resets tracker. |
| Engine phases are truth | 2026-05-09 | Never overwrite engine phase to match global—the signal data IS the conviction signal. |
| Allocation reconcile on rebalance | 2026-05-10 | Clean stale coins from router after each rebalance. Seed new targets to unblock T1 gate. |
| Phantom position fix | 2026-05-10 | Status writer + exchange sync zero ALL position fields when DEX has no position. |
| seed_capital immutable | 2026-05-10 | CLI --capital is the seed, period. Never derived from balance - csv_pnl (breaks on incomplete CSV). |
| Dashboard sync: fresh clone | 2026-05-10 | Replaced `git reset --soft` with fresh shallow clone per cycle. Eliminates non-docs file leakage. |
| Hurdle rate configurable | 2026-05-10 | Extracted to `HURDLE_RATE_DCA_SCORE = 5.0` in v14_capital_manager.py. Single source of truth. |
| Auto deposit/withdrawal detection | 2026-05-11 | Consecutive balance comparison. No unrealized PnL (cascade risk). Threshold max($5, 2%). |
| Dashboard growth excludes deposits | 2026-05-11 | `(equity - seed - net_deposits) / seed`. Isolates trading performance. |
| Startup ledger reconciliation | 2026-05-11 | `dex_total - ledger_capital - csv_pnl`. Stable values only. No cascade. |
| Grid optimization: TP 3.0%, 4 layers | 2026-05-12 | Portfolio backtest +26.3% PnL. Layers 5-12 never fired in live data (avg 1.65). Higher return/deal beats higher deal count. |
| Multiplier/deviation unchanged | 2026-05-12 | 1.5x mult and 1.5% dev — backtested 2.0x/2.0%, zero difference. Not worth the change risk. |
| Grandfather open positions | 2026-05-12 | Existing TP orders on Aster untouched. New config applies to new deals only. DCA layers on existing deals recalculate TP at new rate. |
| Scanner synced to production | 2026-05-12 | `v14_cycle_scanner.py` updated: MAX_LAYERS 12→4, TP_PCT 0.015→0.030. DCA scores now reflect actual trading. |
| 30d scanner window confirmed | 2026-05-12 | Walk-forward analysis (6 windows, 60 days). 30d: best score, lowest churn (13%), fewest false positives (20%). No change needed. |

## Next Steps
1. **🔴 Create V14PM Live auto-restart task** (needs admin PowerShell)
2. **🔴 Disable old V14LiveAster task** (needs admin PowerShell)
3. **Database migration**: Replace CSV with SQLite (proper deal IDs, ACID transactions, no corruption)
4. **Cloud migration**: Linux server, Hyperliquid mainnet (Phase 1: 6-10 weeks)
5. **Commercial product**: Signal-as-a-Service, hub-and-spoke architecture ($49/$149/$499 tiers)
6. Centralize DB_PATH into single config module
