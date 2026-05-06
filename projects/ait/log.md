# AIT — Project Log
_Reverse chronological. Key events only._

## 2026-05-06
- **Critical: Restored v14_capital_manager.py** — dashboard sync script had silently stripped `EQUITY_TIER_SPLITS`, hysteresis logic, and ~120 lines of capital management code on April 15. Bot ran from stale `.pyc` cache; import error surfaced on restart.
- **Fixed T1 gate / rebalance desync** — `_do_rebalance()` selected new coins but never synced `active_allocations` on the router. T1 gate blocked all entries for newly selected coins. Added `active_allocations` sync after rebalance.
- **Fixed liquidity filter crash** — `self.client.exchange` → `self.client._exchange` (attribute name mismatch). Filter had been silently failing since deployment.
- **Coin rotation completed**: Scanner selected PENDLE, LDO, ENA (top 3 by 30d DCA score). LDO below $50K volume floor but passed due to broken filter — will be filtered on next rebalance now that filter is fixed.
- **Dashboard sync script** was deleting source code files from GitHub. Fixed with `git reset HEAD -- ':!docs/'` safety and `.gitignore` for bot.lock.
- **Dashboard data source fixed** — `dashboardV14PM.html` was loading paper bot data (`v14-pm/`) instead of live (`v14-pm-live/`).

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
