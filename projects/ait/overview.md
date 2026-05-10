# AIT — Project Overview
_Last updated: 2026-05-10_

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
- `projects/ait-product/V14PM_SYSTEM_ARCHITECTURE.md` (v1.1) — Complete system reference
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
| High profile, 1.0x leverage for PM | 2026-03-05 | 12 layers, 1.5% TP, 1.5% dev, 1.5x SO mult, no liquidation risk |
| Conviction: 3D DX + 2W K≥5 + score≥3/4 | 2026-02-28 | Bottom detection locked |
| Top: OB93 arm + 2D divergence (35d timeout) | 2026-02-28 | Top detection locked |
| Ground-truth equity formula | 2026-03-08 | `Capital + Realized PnL - Fees + Unrealized PnL` |
| State persistence via engine_state.json | 2026-03-10 | Engines save/restore across restarts, no phantom trades |
| Daily resampling in pipeline | 2026-03-10 | 1h→daily ensures all coins have signal data |
| --fresh for first launch only | 2026-03-10 | Normal restarts use engine_state.json |
| Macro conviction signals observational | 2026-03-08 | 6 index-level signals documented, not wired into bot logic |
| Trend multiplier gates entry not exit | 2026-03-06 | Declining coins get less capital but existing positions stay |

## Current State (2026-05-10)
- **V14PM Live (Aster)**: $376 capital, 9 coin slots, 85% win rate, $85.24 realized PnL
  - DEX-as-truth startup: reads wallet balance directly from exchange
  - Reconciliation & auto deposit detection disabled (caused corruption)
  - Candle replay guard active (warmup-only: old candles update indicators, only current candle executes)
  - Exchange-truth trade recording: uses DEX entry price × actual qty, not engine price
  - **Regime phase gate deployed (§7.5)**: Coins trade only when phase matches global regime
  - **Graduated conviction alerts**: 7 thresholds (15/25/30/35/40/45/50%), APPROVE at any level
  - **Dashboard regime panel**: Global direction, long/short counts, conviction bar, per-coin gate status
  - **Allocation cleanup**: Router reconciled after daily rebalance — stale coins removed, new scanner targets seeded
  - **Phantom position fix**: Status.json + exchange sync zero all position fields when DEX has no position
  - Approved symbols: `[INJ/USDT, JUP/USDT, TON/USDT]` (scanner top 3)
  - Positions: INJ 4.0 qty long (TP active)
  - 1/9 engines in SHORT_DCA (HYPE), 8 aligned with LONG_DCA global regime
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

## Next Steps
1. **Database migration**: Replace CSV with SQLite (proper deal IDs, ACID transactions, no corruption)
2. **Cloud migration**: Linux server, Hyperliquid mainnet (Phase 1: 6-10 weeks)
3. **Commercial product**: Signal-as-a-Service, hub-and-spoke architecture ($49/$149/$499 tiers)
4. Centralize DB_PATH into single config module
