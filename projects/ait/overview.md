# AIT — Project Overview
_Last updated: 2026-03-10_

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
- `projects/ait-product/CLOUD_MIGRATION_GUIDE.md` (v1.2) — Linux deployment guide
- `projects/ait-product/LIVE_VS_PAPER_DIFFERENCES.md` — Live vs paper architecture, production checklist
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
| V14PM = production target | 2026-03-18 | Exchange-as-truth architecture, V14 Live is legacy |
| LIVE GUARD mandatory on live bots | 2026-03-18 | Rollback engine state when exchange TP order exists |
| Equity = usdt_total + unrealized_pnl | 2026-03-20 | Matches V14 Live pattern; USDT.free excluded locked margin |

## Current State (2026-03-20)
- **V14PM Live (Aster Perps)**: ~$350 real USDT, GRASS/USDT, 13 deals, 100% WR, $24 realized PnL
- **V14PM Paper**: $56.8K equity, 173 deals, 100% WR, 5 active coin slots
- **V14 Paper**: $52.6K equity, 403 deals, 97.8% WR
- **V14 Live (Aster Spot, LEGACY)**: ~$350 real, ASTER/USDT — being retired
- **V14-ETF**: RETIRED (2026-03-17)
- **V14PM vs V14 Live audit (2026-03-19)**: 20 critical paths, 12 gaps (3× P0). Equity bug fixed 2026-03-20.
- **Equity computation bug fixed (2026-03-20)**: `fetch_balance()` returned `USDT.free` (excluded margin). Now uses `usdt_total + unrealized_pnl`, matching V14 Live pattern. Dashboard donut also fixed.

## Next Steps
1. Cloud migration (Linux server, Hyperliquid mainnet)
2. Create `run_v14_portfolio_live.py` (live runner with real orders)
3. Centralize DB_PATH into single config module
4. Correlation gate (halt new entries when >60% of coins at L4+)
5. Rename V13SignalPack → SignalPack (maintenance window)
