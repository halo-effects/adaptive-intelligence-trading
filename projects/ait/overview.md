# AIT — Project Overview
_Last updated: 2026-07-05_

## Product
**Adaptive Intelligence Trading** — Automated crypto DCA trading system with signal-directed phase transitions and dynamic capital rotation.

## Architecture
- **V14 DCA Engine**: Signal-directed continuous DCA with LONG/SHORT phases
- **V14PM Portfolio Manager**: Capital rotation across coin slots using DCA Cycle Velocity scoring + trend multipliers
- **GridModel v2.0**: Canonical leaf module — single source of truth for DCA grid fractions (G-SPLIT: 48/32/20% of allocation, 3 layers). Used by engine, scanner, and capital top-up. Zero engine imports.
- **GateModel**: Signal-aware entry veto (Part A) + layer deployment gates (Part B, retired). Leaf dependency. ATR-normalized extension, side-resolved divergence, NEAR fixture, V-4 guard.
- **Signal Stack**: V13SignalPack (StochRSI, ADX, structure), HybridDetector2D (top/bottom), Steve 3-Check, CFGI
- **Exchange**: Hyperliquid perps (production), Aster DEX (proof-of-concept)
- **Data Pipeline**: Hourly candle collection (45 active + 9 watchlist coins, Hyperliquid) → daily resampling → DCA cycle scanner → veto evaluation
- **Regime Persistence**: Append-only `regime_events.db` — GLOBAL_FLIP, COIN_PHASE, ALERT events (RH-1)
- **Dashboards**: GitHub Pages (4 dashboards, synced every 10 min)

## Architecture Documents
- `projects/ait-product/V14PM_SYSTEM_ARCHITECTURE.md` (v1.14) — Complete system reference
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
| DCA Cycle Velocity scoring | 2026-03-03 | `Score = Realized_PnL × (1-MaxDD%) × Capital_Freedom × Depth_Penalty / 100` |
| Two-tier collector | 2026-07-05 | ACTIVE_UNIVERSE (45 scored) + WATCHLIST (9 collected-only for reinstatement) |
| TON→GRAM rename | 2026-07-05 | Token renamed June 15, 2026. Scanner + collector updated. Legacy TON candles preserved. |
| Per-coin funding rate (RH-3) | 2026-07-05 | Trailing-90d median replaces flat P5 constant. Measured 3× overstatement. 20% deals earn carry. |
| Regime event persistence (RH-1) | 2026-07-05 | Append-only regime_events table. Fail-open writes. Attested history seeded. |
| PM capital = $50K, 10 coin slots | 2026-03-06 | Equity tier at $50K+ = 10 simultaneous coins |
| Trend multiplier in allocation | 2026-03-06 | `Adjusted Score = DCA Score × Trend Multiplier` [0.30, 1.50] |
| G-SPLIT grid (48/32/20) | 2026-07-04 | **3 layers**, L4 removed. +8.6% PnL over 40/24/20/16, best PnL/%DD. Fable-verified. |
| Part A entry veto | 2026-07-04 | ATR-normalized extension (EXT_ATR_MULT=3.0), side-resolved divergence, V-4 guard. LIVE. |
| Part B layer gate | 2026-07-04 | Analyzed, tested, **RETIRED**. Superseded by G-SPLIT removing L4. |
| E-4 dynamic L1 sizing | 2026-07-04 | Tested via E-3a. MAE gap fails ≥2.0 bar. **PARKED** — static grid is the answer. |
| High profile, 1.0x leverage for PM | 2026-05-12 | 3 layers (was 4→12), 3.0% TP, 1.5% dev, no liquidation risk |
| No forced closes (orphan-TP) | 2026-05-16 | `FORCE_CLOSE_ON_SIGNAL=False`. Positions exit via TP only. |
| open_deals is truth for layer count | 2026-06-19 | Engine snapshot resets; open_deals tracks actual fills (Hard Rule #35). |
| seed_capital immutable | 2026-05-10 | CLI --capital, never recalculated (Hard Rule #26). |
| DEX-as-truth for capital | 2026-05-08 | Exchange wallet balance IS capital. |

## Current State (2026-07-05)
- **V14PM Live (Aster)**: $442 capital (seed=$300 + $40 deposit), 119 trades, ~86% win rate
  - **Grid: G-SPLIT (48/32/20) deployed**. GridModel v2.0, 3 layers. L4 removed.
    - Decision: Final Grid Decision Test (Fable spec v1.0). G-SPLIT +8.6% PnL over incumbent, best PnL/%DD ($1,053). Rule 1 survived. Fable-verified.
    - E-4 dynamic L1 sizing tested and FAILED evidence bar (MAE gap +0.52 vs ≥2.0). Static grid is the answer.
  - **Part A Signal Gating LIVE**: Entry veto system active.
    - GateModel: ATR-normalized extension (EXT_ATR_MULT=3.0), side-resolved divergence (G-3/M-5), NEAR fixture (G-1).
    - V-4 guard: veto_clear blocked while any trigger condition still true. May 30 gap closed.
    - Veto filter in all 3 selector paths (rebalance, rotation, overflow). Precedence: veto → hurdle → trend → scoring → tier cap.
    - Stale-daily fail-closed guard (MAX_DAILY_STALE_DAYS=7): coins with old daily data excluded with STALE_DAILY_DATA reason.
  - **Part B Signal Gating**: Analyzed, pivot gate designed and tested, **RETIRED** — G-SPLIT removes L4, so layer gating is moot.
  - **Trade Score (P1-P5 + P1b)**: Capital freedom avg-layer-fraction (P1b), depth penalty (P2, DEPTH_HALF_LIFE_H=72), score logging at deal-open (P3), sim at live scale with $10 minimum (P4), funding cost subtraction (P5).
  - **MAE tracking**: Per-deal max adverse excursion, running max per tick at current avg entry. Legacy deal backfill on first tick. Persists through restarts via open_deals state.
  - **Strategy-native performance**: 116 deals, +$145.46, 87.9% WR, worst loss -$3.80.
  - **Post-orphan-TP era** (after 5/17): 18 deals, 94% WR, +$29.14, ~$28/month run rate.
  - **Pool reconciliation**: `reconcile_pools_from_exchange()` syncs active_pool_cash to DEX every cycle.
  - DEX-as-truth startup, exchange-truth trade recording, warmup-only candle replay
  - **Orphan-TP mode**: FORCE_CLOSE_ON_SIGNAL=False. Positions exit via TP only.
  - **seed_capital immutable** (Hard Rule #26): CLI --capital arg, never recalculated
  - Approved symbols: `[INJ, JUP, GRAM]` (scanner top 3; TON renamed to GRAM 2026-06-15)
  - **Star coin**: TAO (+$72.40, 17/17 wins, 6.25% avg return). Capital traps: PYTH, HYPE.
  - **Cloud migration readiness**: 6/10 current, 4/10 for Hyperliquid target. No HL runner exists.
  - **Collector pipeline**: Two-tier structure (ACTIVE_UNIVERSE + WATCHLIST). ccxt 4.5.x null-market patch. 45 active + 9 watchlist coins.
    - TON→GRAM rename handled (June 15, 2026). HYPE quote fix (USDT matches V14PM). MKR removed (delisted on HL).
    - Watchlist (collected but not scored): APT, JTO, TRUMP, BERA, S, VIRTUAL, GRASS, INIT, MOVE.
    - Dead coins excluded: MKR (delisted), IP (delisted), ORCA (not on HL), PEPE (kPEPE denomination mismatch).
    - Funding rates: 94K rates in `funding_rates` table (45 coins, Binance USDT-M futures).
- **V14PM Paper**: 750+ trades, $50K+ PnL (restored from CSV truncation)
- **V14 Live (Aster)**: ASTER/USDT single-coin, running
- **V14 Paper**: Running on Hyperliquid
- **V14-ETF Paper**: Running

## Audit Trail
| Audit | Date | Status |
|-------|------|--------|
| Fable Comprehensive Audit | 2026-07-03 | 2C/4H/7M findings. All P0 remediated same day. |
| Fable Post-Remediation Verification | 2026-07-04 | All P0 confirmed. New H-1/M-1 through M-5. |
| Fable Final Audit (EOD) | 2026-07-04 | All green. V-4 verified, MAE verified, G-SPLIT verified. |
| Grid Decision (G-SPLIT) | 2026-07-04 | Pre-registered rules. Fable-verified. Brett approved. |
| Part B (Layer Gate) | 2026-07-04 | Analyzed, tested, retired on honest evidence. |
| E-4 (Dynamic L1) | 2026-07-04 | E-3a MAE gap fails bar. Parked by pre-registered rule. |
| Regime-Ladder Final (Fable) | 2026-07-05 | Production +43.5% vs B&H −43.8%. Earlier +90%/yr reconstruction withdrawn. |
| Regime Persistence (RH-1/2/3) | 2026-07-05 | All verified. Arch doc v1.14. Per-coin funding. Event log. |

## Next Steps
1. **🔴 Create V14PM Live auto-restart task** (needs admin PowerShell)
2. **🔴 Disable old V14LiveAster task** (needs admin PowerShell)
3. **M-1 spec** (reconcile_pools reserve zeroing): Safe now, landmine at $10K. Spec while context fresh.
4. **Database migration**: Replace CSV with SQLite (proper deal IDs, ACID transactions, no corruption)
5. **Cloud migration**: Linux server, Hyperliquid mainnet (Phase 1: 6-10 weeks)
6. **Commercial product**: Signal-as-a-Service, hub-and-spoke architecture
7. Centralize DB_PATH into single config module
8. **Funding rate collector**: Add hourly funding rate pull to collector pipeline (currently seeded from one-time Binance export)
