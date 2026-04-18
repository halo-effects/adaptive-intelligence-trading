# AIT — Project Overview
_Last updated: 2026-04-18_

## Product
**Adaptive Intelligence Trading** — Automated crypto DCA trading system with signal-directed phase transitions and dynamic capital rotation.

## Architecture
- **V14 DCA Engine**: Signal-directed continuous DCA with LONG/SHORT phases
- **V14PM Portfolio Manager**: Capital rotation across 10 coin slots using DCA Cycle Velocity scoring + trend multipliers
- **Signal Stack**: V13SignalPack (StochRSI, ADX, structure), HybridDetector2D (top/bottom), Steve 3-Check, CFGI
- **Exchange**: Hyperliquid perps (production), Aster DEX (proof-of-concept)
- **Data Pipeline**: Hourly candle collection (Aster DEX) → daily resampling → DCA cycle scanner
- **Dashboards**: GitHub Pages (2 dashboards, synced every 10 min)

## Architecture Documents
- `projects/ait-product/V14PM_SYSTEM_ARCHITECTURE.md` (v1.3) — Complete system reference
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
| Aster DEX for candle collection | 2026-04-17 | Switched from Hyperliquid; 15 scanner coins only exist on Aster |
| 50-coin scanner universe | 2026-04-17 | Expanded from 45 to match PM bot's Aster universe |
| Trend multiplier gap resilience | 2026-04-18 | Fallback to nearest-pair comparison when no standard window has data |

## Current State (2026-04-18)
- **V14PM**: Running, 10/10 coin slots, trend multipliers restored
- **V14 Paper**: Running
- **V14-ETF Paper**: Running
- **V14 Live (Aster)**: $300 real, ASTER/USDT, running
- **Candle collector**: Aster DEX, 50-coin universe, hourly
- **Scanner**: 50 coins, trend scores active with gap-resilient fallback
- **Dashboard sync**: Every 10 min via GitHub Pages

## Next Steps
1. Cloud migration (Linux server, Hyperliquid mainnet)
2. Create `run_v14_portfolio_live.py` (live runner with real orders)
3. Centralize DB_PATH into single config module
4. Correlation gate (halt new entries when >60% of coins at L4+)
5. Rename V13SignalPack → SignalPack (maintenance window)

## Recent Changes (2026-04-17/18)
- **Candle collector switched to Aster DEX** from Hyperliquid. 15 coins only exist on Aster.
- **Scanner expanded to 50 coins** to match PM bot's universe.
- **Trend multiplier gap resilience**: `compute_trend_scores()` now falls back to comparing the two most recent snapshots when standard windows (7/14/30d) have insufficient data due to collection gaps. Previously, a >30-day gap left `trend_scores` empty, causing dashboard Trend Mult columns to show `--`.
- **Merge revert fixed**: Git merge from remote reverted the Aster collector; detected and restored.
