# AIT — Project Log
_Reverse chronological. Key events only._

## 2026-05-15
- **Regime gate fix deployed** (paper + live): Two bugs in the §7.5.2 regime gate (added 2026-05-13):
  1. Gate blocked ALL actions (including exits/TPs) when engine phase ≠ global regime — trapped positions couldn't close. Violated §7.5.2: "open positions ride to TP naturally."
  2. No `reject_action()` rollback on blocked entries — `engine.tick()` mutates state before returning actions, so blocked entries left phantom positions in engine state every hour.
- **Root cause of NEAR short in LONG regime**: NEAR's engine flipped to SHORT_DCA on 04-30 (top signal). SHORT_OPENs were blocked by tier gate and capital limits until 05-12 19:00 when NEAR was promoted to approved symbols and capital freed. No regime gate existed in the running code at that time (committed 05-13 06:42, but bot loaded old code).
- **Fix**: Entry actions (BUY, SHORT_OPEN) blocked + rolled back via `reject_action()`. Exit actions (SELL, SHORT_CLOSE, TP) always pass through. Same `reject_action()` pattern already used by CapitalRouter.
- **Deployed**: Paper bot restarted 06:15 PDT. Live bot restarted 06:29 PDT — pre-flight passed, all 5 TP orders verified open (INJ, TON, JUP, PENDLE, ONDO). Zero impact on open positions (all LONG in LONG_DCA matching global regime). HYPE (only SHORT_DCA engine) has no open position.
- **Files changed**: `run_v14_portfolio_paper.py`, `run_v14_portfolio_live_aster.py`
- **Docs updated**: `V14PM_SYSTEM_ARCHITECTURE.md` §7.5.7 (v1.7), `hard-rules.md` (#32, #33)
- **Hard rules added**: #32 (post-tick gates must rollback + separate entries/exits), #33 (read arch spec before writing fix code)

## 2026-05-12
- **Grid optimization deployed**: TP 1.5% → 3.0%, Max Layers 12 → 4 (high profile only). Spec: `specs/grid-optimization-tp3-4layer.md`.
- **Backtest evidence**: Portfolio-level sim (3 slots, 10 coins, 90 days, real candles, Hyperliquid fees): +26.3% PnL ($23,772 vs $18,824). Higher return per deal outweighs fewer deals. Capital efficiency +40%.
- **Live data analysis**: 96 trades, avg layers used = 1.65. Layers 5-12 never fired. L4+ deals were forced closes from bugs, not grid failures.
- **Per-coin backtest**: TP is the dominant lever. Multiplier (1.5x vs 2.0x) and deviation (1.5% vs 2.0%) made no difference. Layer cap identical to 12 layers (never reached).
- **Open positions grandfathered**: TON (L3), JUP (L1), PENDLE (L2), ONDO (L2) — existing TP orders on Aster untouched. New deals get 3.0% TP.
- **Files changed**: `v14_lifecycle_engine.py` (profile), `run_v14_portfolio_live_aster.py` (fallbacks + docstring), `d-984ae0d4ab9dc1a5.html` (dashboard display).
- **Trailing stop unchanged**: Still enabled, 0.2% callback. Activation now at 3.0% instead of 1.5%.
- **No impact on**: Tiers, capital router, scanner, signal stack, low/medium profiles, deviation, multiplier.
- **Aster single-coin bot**: Dead, excluded from changes.
- **Commit**: `62b26e15a`
- Bot restarted at 16:20 PDT (PID 6600 → 9964). All 4 existing TP orders confirmed open on Aster. Pre-flight passed.
- **Scanner window analysis**: Walk-forward test across 6 windows (7d, 10d, 14d, 21d, 24d, 30d) over 60 days. 30d confirmed optimal: highest avg DCA score (31.6), lowest churn (13.0%), fewest false positives (20%). Shorter windows trade earlier detection for noise (7d: 32% FP rate). 14d is stability sweet-spot (22% FP) but same promotion timing as 30d on most coins. 30d window unchanged. Analysis: `trading/spot/_scanner_window_backtest.py`, results: `trading/spot/data/scanner_window_analysis.json`.
- **Scanner updated**: `v14_cycle_scanner.py` params now match production (TP 3.0%, MAX_LAYERS 4). All future DCA scores reflect actual trading behavior. New 30d top-5: INJ (35.0), DYDX (34.7), PENDLE (31.6), ONDO (27.9), TON (27.4). Commit: `3c320a1cf`.

## 2026-05-11
- **Auto deposit/withdrawal detection deployed** (`deposit-detection-audit.md`): Consecutive balance comparison approach. `expected = prev_balance + pnl_delta + funding_delta`. Immune to unrealized PnL. Fires within 60s of DEX balance change. Full system audit: 16 components traced, 7 findings (1 CRITICAL fixed — cascade from unrealized PnL).
- **Startup reconciliation**: Compares `dex_total` to `ledger_capital + csv_pnl`. Uses only stable values (no unrealized). Cascade-safe: verified 3 consecutive restarts with delta=$0.00.
- **Dashboard growth formula**: `(equity - seed - net_deposits) / seed`. Isolates trading performance from capital flows.
- **Capital ledger baseline set**: seed=$300, deposit=$40, pnl_adjustment=$64.59 (dark PnL gap from CSV truncation).
- **ccxt Aster fix**: Patched `fapiPublicGetV1ExchangeInfo` to filter markets with null baseAsset/quoteAsset. Aster API intermittently returns incomplete data.
- Updated: `run_v14_portfolio_live_aster.py`, `d-984ae0d4ab9dc1a5.html`, `dashboardV14PM.html`, `capital_ledger.json`, `deposit-detection-audit.md`

## 2026-05-10
- **V2 System Audit complete**: 60 findings across 11 phases (~15,000 lines reviewed). 2 CRITICAL + 1 HIGH fixed during audit, 10 more post-audit. See `specs/v2-audit-summary.md`.
- **Post-audit Fix Now batch (6 items)**: #12 Steve symbol selection, #13 HybridDetector USDC preference, #21 scanner freshness warning, #24 candle quality validation, #49 stale task (needs admin), #51 stale lock recovery.
- **Post-audit Quick Wins batch (4 items)**: #20 hurdle rate constant, #27 in-memory PnL reads, #43 phantom open_deal cleanup.
- **Dashboard sync root cause fixed**: `sync_dashboard.ps1` used `git reset --soft origin/main` in sparse-checkout temp repo, populating index with full tree. Non-docs files committed/deleted in feedback loop. Fixed: fresh shallow clone per cycle.
- **Trade history restored**: Git-recovered CSVs merged with current bot data. Paper: 671 + 79 new = 750 trades ($50,415 PnL). Live: 82 + 4 new = 86 trades ($13.96 PnL).
- **seed_capital drift fixed**: DEX-as-truth startup derived seed from `balance - csv_pnl - unrealized`, which breaks on incomplete CSV. Drifted from $300 to $364. Fixed: seed_capital is immutable CLI --capital arg.
- **Stale allocation cleanup deployed** (`stale-allocation-cleanup.md`): `router.active_allocations` accumulated coins forever — only removed on trade completion + not-in-top-N. Fix: reconcile against rebalance targets after each daily rebalance. Coins not in new targets with no open position are removed.
- **Circular dependency fix**: Rebalance created engines for promoted coins (TON, JUP) but T1 gate blocked all entries because `active_allocations` wasn't populated until `request_capital()` ran inside `_execute_action()` — which the gate prevented. Fix: seed new coins into `active_allocations` from rebalance targets.
- **Dashboard allocation filter**: Shows only coins with open positions (invested > 0). Removed stale `approved_symbols` reference that showed ghost coins.
- **Phantom position fix deployed** (`phantom-position-fix.md`): Status.json writer and exchange sync now zero all position fields when exchange reports no position. HYPE shows invested=0, layers=0, side=none while preserving phase=SHORT_DCA.
- **Cron healthcheck fix**: Disabled broken `healthcheck.py` script (job 55882b5c). Updated LLM health check (job ef85844d) to include regime gate status.
- **Verified**: `approved_symbols` now correctly `['INJ/USDT', 'JUP/USDT', 'TON/USDT']` — matches scanner top 3.
- Updated: `run_v14_portfolio_live_aster.py`, `dashboardV14PM.html`, `d-984ae0d4ab9dc1a5.html`, `stale-allocation-cleanup.md`

## 2026-05-09
- **Regime phase gate deployed** (`regime-phase-gate.md`): Coins trade only when engine phase matches global regime. Engine phases are never overwritten — they reflect real signal data that feeds the conviction system.
- **Graduated conviction alerts**: 7 thresholds (15/25/30/35/40/45/50%). Each fires once as conviction climbs. APPROVE available at any level. DENY resets tracker so alerts re-fire.
- **APPROVE flips global regime**: No forced closes. Coins auto-unflag when their phase matches the new global. Open TPs ride naturally.
- **Dashboard regime panel**: Replaced "Market Conditions" with "Portfolio Regime" showing global direction (▲ LONG / ▼ SHORT), long/short counts, conviction bar with %, flipped coin list.
- **Dashboard regime gate card**: Replaced "Phase Status" in Macro Indicators with per-coin phase + ACTIVE/EXCLUDED status tags.
- **Dashboard header badges**: Global regime badge + conviction % badge.
- **Status.json regime data**: `flip_pct`, `flipped_coins`, `aligned_coins`, `long_count`, `short_count`, `total_engines`, `last_alert_pct` added to `regime_detail`.
- **Exchange-truth trade recording deployed** (`exchange-truth-trade-recording.md`): Uses DEX entry price × actual qty, not engine's internal price tracking. Fixes inflated cost basis.
- **Warmup-only candle replay deployed** (`candle-replay-guard.md`): Old candles processed for indicator warmup only; only current candle executes actions. Eliminated spread-reject spam on restart.
- **HYPE engine state**: Restored to truthful SHORT_DCA (was forced to LONG_DCA, corrected per principle that engine phases reflect real signals).
- **6 new hard rules** (#19-25) added to `tacit/hard-rules.md`.
- **Architecture doc updated to v1.5**: §7.5 fully documented with graduated thresholds, dashboard display spec, status.json schema.
- Updated: `run_v14_portfolio_live_aster.py`, `dashboardV14PM.html`, `V14PM_SYSTEM_ARCHITECTURE.md`, `overview.md`

## 2026-05-08
- **INCIDENT: Restart cascade from data sync cron overwriting `v14_capital_manager.py`.** Data sync cron on May 6 committed a truncated paper-bot version of the capital manager to git. Bot ran in memory (masking the break) until manual restart triggered ImportError. 113 spread-reject round trips during attempted restarts, $5.75 lost, CSV corrupted.
- **Candle replay guard deployed** (`candle-replay-guard.md`): Suppresses order execution when candle timestamp >75 min old. Prevents spread-reject churn during restart catch-up. Initial threshold of 300s was too tight for 1h candles (fixed to 4500s).
- **DEX-as-truth startup sequence** (`dex-as-truth-startup.md`): Exchange wallet balance is now the sole source of truth for capital on startup. Calculates seed, realized PnL, and unrealized from DEX + CSV. Eliminates dependency on state.json/ledger for capital.
- **Auto deposit/withdrawal detection DISABLED.** Formula was fundamentally broken: subtracted realized PnL from exchange balance, causing every profitable trade to trigger a phantom withdrawal. Manual DEPOSIT/WITHDRAW Telegram commands still work.
- **Startup reconciliation DISABLED.** Heuristic fill-grouping algorithm created phantom trades from spread-reject churn (-$94.79 TON, -$22.65 PENDLE). TP order recovery already handles missed fills.
- **Data sync script fixed**: `git reset HEAD -- ':!docs/'` pathspec negation broken on Windows — replaced with explicit per-file unstage loop. Sync repo nuked for fresh clone.
- **Capital ledger reset**: Purged 9 phantom deposit/withdrawal entries. Reset to clean seed=$300.
- **Trade history corrected**: DEX-verified ENA (2 deals) and TON (5 deals) trades replaced bad reconciliation entries. 95 trades, 85.3% win rate, $96.74 realized PnL.
- **Incident report**: `projects/ait/specs/incident-2026-05-08-restart.md`
- **Bot-side trailing TP spec**: `projects/ait/specs/bot-side-trailing-tp.md` (deployed)
- **Bot-side TP race fix spec**: `projects/ait/specs/bot-side-tp-race-fix.md` (deployed)
- **Commercial readiness assessment v2**: `projects/ait/specs/commercial-readiness-assessment.md`
- **Auto seed capital spec**: `projects/ait/specs/auto-seed-capital.md` (superseded by DEX-as-truth)
- Updated: `run_v14_portfolio_live_aster.py`, `sync_dashboard.ps1`, `capital_ledger.json`, `state.json`

## 2026-05-05
- **Trade Reconciliation System built.** CSV trade log had drifted from exchange reality: 8 duplicate deal IDs, 3 missing IDs, and a missing profitable PYTH trade (+$0.91) from a forced API close that bypassed TradeTracker.
- **New: `reconcile_trades.py`** — standalone CLI tool that connects to Aster DEX, fetches all fill history, reconstructs deals, and compares against trades.csv. Modes: `--dry-run` (default), `--fix` (exchange-truth rewrite), `--fix-ids` (sort + reassign IDs only).
- **New: Startup reconciliation** — `_reconcile_trades_on_startup()` runs on every bot start, checks last 48h of exchange fills for missing deals, and appends any recovered trades to CSV. Sends Telegram alert on recovery.
- **New: RECONCILE Telegram command** — on-demand 48h reconciliation.
- **Fix: TradeTracker deal_id assignment** — changed from `max(deal_id)` to `len(trades)` to prevent duplicate ID collisions.
- **`--fix-ids` applied:** All 70 trades sorted by close_time, deal IDs reassigned 1-70. Zero duplicates.
- **Discovery:** Aster DEX API has ~30-day fill retention. Older fills are purged. Reconciliation tool handles this gracefully (labels as "unverifiable" instead of "phantom").
- **5 missing trades found** on exchange but absent from CSV, including the PYTH +$0.91 trade and a DYDX -$41.14 loss.
- Updated: `run_v14_portfolio_live_aster.py`, new `reconcile_trades.py`.

## 2026-05-04
- **BUG FIX: Stale coin re-entry prevention.** Coins from prior scanner cycles could keep opening new positions after TP close even when no longer in the current top-N rankings. Root cause: `approved_symbols` was only updated during daily rebalance — if a coin closed a trade mid-day and was no longer top-N, it would immediately re-enter on the next candle.
- **Fix (both live + paper bots):** Added `_prune_stale_coin_after_tp()` — after every TP fill, reads current scanner JSON, checks if the coin is still in the top-N (same hurdle + trend multiplier logic as CapitalRouter). If not, removes it from approved symbols / router allocations. T1 re-entry blocked until next daily rebalance promotes it. Fail-open: if scanner data is unavailable, coin is kept.
- **Live bot T1 gate added:** `_execute_action()` BUY handler now checks `self.router.active_allocations` before allowing first-layer entries (matching paper bot's existing `_approved_symbols` check). DCA L2+ layers on existing positions always pass.
- **Origin:** PYTH/USDT ranked 29th in scanner but kept re-entering after TP close. Live bot had 6 active positions (TAO, JTO, PYTH, DYDX, INJ, ENA) with a tier cap of 3.
- Updated: `run_v14_portfolio_live_aster.py`, `run_v14_portfolio_paper.py`.

## 2026-05-02
- **Liquidity filter implemented** (live bot): Coins must meet min 24h dollar volume = `max(alloc × 100, $50K)`. Scales with capital. Fetches exchange tickers during rebalance. Existing open positions exempt.
- **Entry spread gate** (live bot): BUY fills with >100bps slippage are immediately closed and rolled back. Prevents slippage from eating the TP margin.
- **Tier cap updated**: $100-$10K equity now gets 3 coins (was 1). Minimum viable rotation for small accounts.
- **Origin**: DYDX/USDT negative TP — $761 24h volume on Aster caused 130bps+ entry slippage, trailing stop exit filled below avg entry.
- Updated: `v14_capital_manager.py` (tier table), `run_v14_portfolio_live_aster.py` (filter + spread gate), `portfolio-capital-management.md` (§5.3, §5.2, §10), `V14PM_SYSTEM_ARCHITECTURE.md` (v1.4, tier table).

## 2026-05-01
- **CRITICAL FIX: Phase transitions no longer force-close positions.** Engine was calling `_long_dca_close()` / `_short_dca_close()` on every top/bottom signal — violating the foundational V14 design principle ("gracefully unwind, let TPs hit"). NEAR/USDT paper position force-closed at -$1,021 loss by a top fallback signal.
- **Fix**: Removed all `_close()` calls from `_check_top_signals`, `_check_bottom_signals`, and `_check_markdown_exit` in `v14_dca_engine.py`. Added orphan long TP handling in SHORT_DCA phase (lifecycle engine). Both directions now covered.
- **Documentation corrected**: `V14PM_SYSTEM_ARCHITECTURE.md` §4.5 had wrong spec ("close all longs"). Updated to match original design from `v14-dca-architecture.md`. Hard rules #19 and #20 added.
- **Paper PM budget enforcement** (2026-04-27): `_compute_portfolio_cash()` ground-truth function, budget-aware rebalance, hard budget gate in `_process_actions`. Fixed $90K invested against $50K capital.

## 2026-04-18
- **Candle collector Aster revert fixed**: Git merge from remote `main` had silently reverted `collect_scanner_candles.py` back to Hyperliquid (commit `17c2e37d8`). Restored Aster version from `0d14afd81`. Pipeline script comment updated.
- **Trend multiplier gap resilience**: `compute_trend_scores()` in `v14_cycle_scanner.py` now falls back to comparing the two most recent snapshots when no standard window (7/14/30d) has ≥2 data points. Root cause: 32-day gap in scanner history (March 17 → April 18) meant all prior snapshots fell outside every window, returning empty `trend_scores`. Dashboard Trend Mult columns showed `--` for all coins; Trade Score equaled Base Score (no trend weighting).
- **Scanner history rebuilt**: Ran `--backfill-history 3` to seed April 15/16/17 synthetic snapshots. 24 total snapshots in score_history.json. Trend multipliers now active for 45 of 50 coins (5 new coins need a second snapshot).
- **Architecture doc updated to v1.3**: Added §3.4 (Aster migration), updated §4.2 (gap resilience), §4.3 (50-coin universe), §3.1 (Aster exchange).

## 2026-04-17
- **Candle collector switched from Hyperliquid to Aster DEX**: 24 of 50 scanner coins were stale (3-30 days). Backfilled 4,297 candles, all 50 current.
- **Scanner synced to 50-coin Aster universe**: 15 coins (ORCA, TRUMP, BERA, VIRTUAL, GRASS, IP, INIT, S, MOVE, etc.) were being traded by PM bot but never scored.
- **Impact on rankings**: ZEC invisible→#1 (34.0), JTO invisible→#4, PEPE new #3, HYPE invisible→#15.
- Commits: `e447a33bf` (collector), `735611a3a` (scanner).

## 2026-03-10
- **Full system audit complete**: Read every file in V14PM dependency chain
- **CRITICAL FIX**: `v13_router_engine_v2.py` wrong DB path (`.parent.parent.parent` → `.parent.parent`). HybridDetector2D was reading from 0-byte DB — top/bottom detection completely broken across ALL bots since deployment
- **CRITICAL FIX**: Created `resample_daily.py` — 19 of 45 coins had zero daily candles. Wired into hourly pipeline as Step 1.5
- **CRITICAL FIX**: Added engine state persistence (`engine_state.json`) — root cause of phantom trades. Saves every 60s, restores on startup. 4 restart tests with zero phantoms.
- Removed `--fresh` from PM scheduled task (state persistence handles restarts)
- Updated V14PM_SYSTEM_ARCHITECTURE.md (v1.1) and CLOUD_MIGRATION_GUIDE.md (v1.1)
- Rebuilt QMD structured memory system

## 2026-03-09
- **PM trade reconciliation**: 61 trades → 20 genuine, 41 phantoms removed ($943 fake PnL)
- Added `recorded_at` field to all trades (forensic provenance)
- Added `_fresh_floor_ms` candle replay guard
- Added PID lock (`bot.pid`) — prevented dual-instance bug
- Added engine warmup period (no trading until first daily boundary)
- Upgraded OpenClaw 2026.3.1 → 2026.3.8
- Fixed dashboard sync silent push failure (17 hours of silent failures)

## 2026-03-08
- Macro bottom conviction signals documented (6 index-level signals all active)
- Added to conviction-stack-spec.md, not wired into bot logic

## 2026-03-07
- Scanner run: 38/40 coins in MARKDOWN, ATOM sole MARKUP in top-10
- Fixed ASTER NaN `isnan` bug in `_check_dca`

## 2026-03-06
- **Trend multiplier wired into PM allocation**: `Adjusted Score = DCA Score × Trend Multiplier`
- Scanner backfill feature (`--backfill-history N`, `--as-of YYYY-MM-DD`)
- PM capital confirmed at $50K (was mistakenly set to $10K)
- Expanded COIN_BASE to all 45 scanner coins across all 4 dashboards
- Created V14CycleScanner scheduled task (daily 6 AM)

## 2026-03-05
- **V14 PM paper bot launched**: $10K initial (later corrected to $50K)
- Fixed dashboard JS syntax errors (V14ETF, Live, V14PM)
- Fixed `np.isnan(daily_close)` bug, `InvalidIndexError` in `load_daily()`
- V14 Live bot restarted after silent crash (stale 476 min)
- PM comparison log tool created
- Switched primary model to Claude Opus 4.6

## 2026-03-04
- API rate limit incident (Gemini 1M TPM + Anthropic credit exhaustion)
- V14 Live double-execution bug (two instances, duplicate trades)
- Model config: Gemini → Sonnet as primary
- Git backup switched from OpenClaw cron to Windows bat script

## 2026-03-03
- **V14 Live bot launched** on Aster DEX ($300 real, ASTER/USDT)
- Bear market coin research: DCA Cycle Velocity scoring created
- DCA Cycle Scanner built (`v14_cycle_scanner.py`)
- Full Hyperliquid universe backfill (18 coins from Binance/KuCoin)
- ZRO discovered as surprise champion via backfill data

## 2026-03-02
- **V13 SUNSET** (final: +184.5%, $28,449)
- **V14-ETF paper bot launched** (SOL/XRP/LTC/HBAR/ADA, $10K, High profile)
- OpenClaw security audit + update to 2026.3.1
- Created OpenClaw watchdog scheduled task
