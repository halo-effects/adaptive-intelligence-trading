# MEMORY.md - Long-Term Memory

## Brett
- Direct, no-fluff communicator. Values security/governance deeply.
- Timezone: America/Los_Angeles
- Uses Telegram for personal, Slack for Halo Effects business
- No desktop Slack - browser only via Gmail login
- Quote: "It's about finding the right coin at the right time and running the strategy and getting out with your shirt"

## Adaptive Intelligence Trading (AIT)
- **Product name**: Adaptive Intelligence Trading (AIT) - decided 2026-02-14
- **GitHub**: github.com/halo-effects/adaptive-intelligence-trading (account: halo-effects, geegee@haloeffects.net)
- **Product page**: https://halo-effects.github.io/adaptive-intelligence-trading/ (served from `docs/` on main branch)
- **Dashboards**: V13 (`dashboardV13.html`), V14 (`dashboardV14.html`), V14 Live (`d-984ae0d4ab9dc1a5.html`), hidden pages: `adaptive-intelligence.html`, `wyckoff-lifecycle.html`
- GitHub PAT: `openclaw-deploy` (repo scope, expires ~Mar 16 2026)
- **Dashboard sync**: Windows Scheduled Task `AIT_DashboardSync` runs every 10 min, pushes status.json/trades.csv to `docs/data/` via `trading/sync_dashboard.ps1`
- GitHub Pages config: Deploy from branch `main`, folder `/docs`

## Current Live Bots

### V14 Live Bot (Aster - ASTER/USDT) - LIVE as of 2026-03-03
- **Engine**: V14 DCA-only with ROUTER v2 signals (same as paper)
- **Runner**: `trading/spot/run_v14_live_aster.py`
- **Exchange**: Aster (spot for LONG_DCA, futures available for SHORT_DCA)
- Coin: ASTER/USDT - 1h candles, daily signal ticks
- Profile: High (1.5x leverage), BO=40%, Dev=1.5%, Mult=1.5x, 12 layers, TP=1.5%
- Capital: $300 real USDT (started with $310.58)
- State/status: `trading/spot/live/v14/`
- Dashboard: `docs/d-984ae0d4ab9dc1a5.html` (coin-agnostic, no "Aster" in UI)
- Dashboard URL: https://halo-effects.github.io/adaptive-intelligence-trading/d-984ae0d4ab9dc1a5.html
- Sync: `docs/data/v14-live/` (also mirrors to `docs/data/live-aster/` for old dashboard)
- Telegram: `[V14-LIVE]` prefix
- API keys: `trading/spot/live/v14/.env` (gitignored)
- Scheduled Task: `V14LiveAster` - created by Brett 2026-03-03
- **NEAR rejected**: Only perpetuals on Aster (no spot), funding fees would destroy $300 account
- **ASTER chosen**: Only coin with both spot AND futures on Aster exchange
- **Signal limitation**: Only ~5 months data - 2W StochRSI/top detection NaN, stays in LONG_DCA
- **Coin is swappable**: Brett said "if NEAR doesn't work out, we can switch coins to something like HYPE"
- **First trades**: L1 126.11 @ $0.7136 ($90), L2 90.78 @ $0.6939 ($63)
- **Bugs fixed at launch**: CCXT precision-as-float TypeError, Windows cp1252 emoji encoding
- **Leverage**: 1.0x for spot (no margin trading available on Aster spot)
- **Scheduled Task**: `V14LiveAster` - created by Brett 2026-03-03
- **Silent hang bug**: Bot hung ~1AM 2026-03-03 with no errors. Same pattern across all 3 bots. Root cause unknown.
- **last_candle_ts bug**: State.json had future timestamp → bot skipped all candles. Fixed manually.

### V14 Paper Bot (Hyperliquid - HBAR/ATOM/LINK/NEAR) - LIVE as of 2026-02-28
- **Engine**: `trading/spot/backtest_results/v13/v14_dca_engine.py` (DCA-only with ROUTER v2 signals)
- **Wrapper**: `trading/spot/v14_lifecycle_engine.py`
- **Runner**: `trading/spot/run_v14_paper.py`
- Coins: HBAR/USDT, ATOM/USDT, LINK/USDC, NEAR/USDT - 1h candles, daily signal ticks
- Profile: Medium (1.5x leverage), BO=40%, Dev=2%, Mult=1.5x, 10 layers, TP=1.5%
- Capital: $10,000 paper, $2,500/coin (equal weight)
- State/status: `trading/spot/paper/v14/`
- Task: `V14PaperBot` (IdleSettings fixed 2026-03-01)
- Dashboard: `docs/dashboardV14.html`, scanner: `docs/data/v14/scanner.json`
- **Backfill verified**: +552% on $10K, matches standalone backtest
- **Current state (2026-03-01)**: All 4 coins LONG_DCA, equity ~$66,515 (+565%), 361 trades, 97.5% win rate, $760 fees
- **Daily scanner**: runs once/day after 00:30 UTC, backtests 15 coins, qualifies top performers
- **Incidents**: `trading/spot/incident_schema.py` + `trading/spot/paper/v14/incidents/`
- **Leverage note**: Engine always runs at 1.0 internally; wrapper tracks leverage for liq price only
- **Price feeds**: `HL_PRICE_MAP` → perps (HBAR/ATOM/NEAR have no spot on Hyperliquid)

### V13 Paper Bot (Hyperliquid - ETH/SOL/LINK/XRP USDC) - LIVE as of 2026-02-25
- **Engine**: `v13_phase_backtest_v8.py` (43KB) - the CORRECT v8, NOT `v13_backtest_v8.py` (38KB)
- **Wrapper**: `v13_lifecycle_engine_v2.py` - live wrapper around the phase backtest engine
- **Runner**: `trading/spot/run_v13_paper.py`
- Coins: ETH/USDC, SOL/USDC, LINK/USDC, XRP/USDC - 1h candles, daily signal ticks at midnight UTC
- Profile: High (T1=60%, T2=20%, T3=10%, symmetric shorts, DCA 5% BO, 12 layers)
- Capital: $10,000 paper, $2,500/coin
- State/status: `trading/spot/paper/v13/`
- **Current state (2026-03-01)**: All 4 coins in MARKDOWN, tier 3 shorts, equity ~$28,564 (+186%)
- **LH_LL gate active** since 2026-02-26 restart
- **4 phases**: DCA → MARKUP → ROUTER → MARKDOWN (FLAT renamed to ROUTER 2026-02-27)
- **Entry gates (updated 2026-02-26)**:
  - MARKUP: HH_HL ≥ 2 + Fib_support (original)
  - MARKDOWN: **LH_LL ≥ 2** + ADX>20 + Fib_break (LH_LL added 2026-02-26)
  - FLAT→MARKDOWN: **LH_LL ≥ 2** + ADX>20 + Fib_break
- **Top detection**: **2D RSI bearish divergence** (primary, replaces OB93 as of 2026-02-28) / OB93 deprecated (missed ETH/BTC)
- **Front-loaded tiers**: 60/20/10 for both markup AND shorts (symmetric)
- **Failure detectors**: Markup fail (DD>25%+ADX>25), Markdown fail (rise>25%+ADX>25)
- **ROUTER (was FLAT) routing**: Central nervous system for ALL phase transitions. Phase cycle: `DCA ↔ ROUTER ↔ MARKUP ↔ ROUTER ↔ MARKDOWN ↔ ROUTER`. No 42-day timeout. 3-day min eval. Confidence scoring evaluates all 3 exit paths simultaneously. Design doc: `projects/ait-product/intelligent-flat-conductor.md`
- **Min phase hold**: 3 days (not 2 weeks!)
- **HVF**: Dead code - logged only, not used for routing (confirmed 2026-02-26)
- **ROUTER is always-on orchestration layer (2026-02-27)**: NOT a phase you enter between transitions. It monitors signals during EVERY phase and triggers ALL transitions. Phases just execute, ROUTER decides when to change. Replaces `_check_dca()`, `_check_markup()`, `_check_flat()`, `_check_markdown()` with single `_router_evaluate()`. Brett's vision: scales from phase routing → dynamic tier sizing → coin selection → portfolio orchestration.
- **Min phase hold**: 3 days (not 2 weeks!)
- **HVF**: Dead code - logged only, not used for routing (confirmed 2026-02-26)
- Scheduled Task: **Not yet created** - needs elevated PS from Brett
- **State persistence**: state.json + trades.csv. Bot loads state.json on restart, overwrites disk edits from memory. Cannot easily void historical trades without code changes.
- **CRITICAL**: Multiple v8 backtest files exist - only `v13_phase_backtest_v8.py` is correct. `v13_backtest_v8.py` produces -15% ROI on same coins.

### V14-ETF Paper Bot (Hyperliquid - SOL/XRP/LTC/HBAR/ADA) - LIVE as of 2026-03-02
- **Engine**: Same V14 DCA-only with ROUTER v2 signals
- **Runner**: `trading/spot/run_v14etf_paper.py`
- Coins: SOL/USDT, XRP/USDT, LTC/USDT, HBAR/USDT, ADA/USDT - 1h candles, daily signal ticks
- Profile: High (1.5x leverage), BO=40%, Dev=1.5%, Mult=1.5x, 12 layers, TP=1.5%
- Capital: $10,000 paper, $2,000/coin (equal weight)
- State/status: `trading/spot/paper/v14etf/`
- Dashboard: `docs/dashboardV14ETF.html`
- Dashboard URL: https://halo-effects.github.io/adaptive-intelligence-trading/dashboardV14ETF.html
- **Fresh start**: No backfill history, started 2026-03-02 with clean $10K
- **Thesis**: ETF-candidate coins (pending/filed US spot ETFs) may have structural tailwind
- Telegram: All notifications prefixed `[V14-ETF]`
- Scheduled Task: **Not yet created** - needs elevated PS from Brett
- `--fresh` flag: skips all historical candles, only processes new ones from startup time
- Restart: `--skip-backfill` (loads existing state.json)

### V13 Paper Bot - SUNSET (2026-03-02)
- **Stopped.** V14 is the go-forward engine. V13 kept for reference only.
- Final state: +184.5% equity ($28,449), all 4 coins in MARKDOWN tier 3 shorts
- Process killed 2026-03-02, HEARTBEAT monitoring removed

### Legacy Bots (DEPRECATED/INACTIVE)
- **Aster Spot Live (V12e)**: ASTER/USDT, $300 real capital. Not running since ~Feb 17. Task `AsterSpotLive` exists but no status.json.
- **V12e Paper**: Hyperliquid ETH/SOL/BTC. Task `SpotPaperHyperliquid`. Deprioritized.
- **V12f Paper**: Broken status (no output dir). Deprioritized.
- **Aster Futures**: HYPE/USDT dual-tracking. Task `AsterTradingBot` **Disabled**.

### Key Technical Lessons
- reduceOnly orders fail in net position mode when opposing side has larger position - don't use reduceOnly
- Base order sizing should NOT scale by allocation % (hits minimums) - allocation only gates open/close
- TP retry logic needed - exchange can reject TP placement, must auto-retry
- 5m timeframe >> 1m for this strategy (less noise)
- 1x leverage >> 2x (counterintuitive - 2x eats capital reducing deal cycling)
- Wider SO deviation (2.5%) strongly preferred over tight (1.5%)
- **Net position mode margin trap**: selling to close a long can flip net short, requiring margin for the flip - must check margin before TP placement
- **TP > SOs priority**: always ensure TP can be placed, cancel deep SOs if needed to free margin
- **Aster fees**: Maker = 0% (free), Taker = 0.04% - limit orders (TP, SO fills) are free
- **Position drift bug (found 2026-02-17)**: old sync function only checked sign/zero, never compared qty. Orders can accumulate orphaned exposure silently. Fixed with qty drift detection + Telegram alerts.
- **Funding fees are the hidden killer**: Aster charges every 4h. Positions held 24h+ with SOs can lose 50-66% of expected TP profit to funding. Must factor into strategy.
- **Aster API quirks**: `/fapi/v1/income` and `/fapi/v1/userTrades` return 400. Use `/fapi/v1/fundingRate` (public) + `/fapi/v1/premiumIndex` (public) instead. `/fapi/v2/balance` works signed, `/fapi/v2/positionRisk` works signed.
- **Force sync tool**: `trading/force_sync.py` - interactive tool to reconcile exchange vs tracked position
- **Multiple backtest files with same class name = disaster (2026-02-25)**: `v13_backtest_v8.py` and `v13_phase_backtest_v8.py` both contain `class V13BacktestV8` but are completely different engines. Went through 3 wrong engines before finding the right one. Always verify backfill matches standalone backtest trade-for-trade.
- **Daily tick timing matters**: First-hour candle price ≠ daily close. Must use `_price(prev_date)` from signal pack for daily ticks, and process at previous day's date. Off-by-one-day shifts cause signal misalignment.
- **DCA PnL ≠ Total PnL**: The real money in V13 is from markup sells (+32-374%) and short profits (+9-52%), not DCA scalps ($1-4%). Track all closed trade P&L, not just `dca_pnl`.
- **candles.db not gitignored = data loss risk**: Git rebase operations can wipe runtime SQLite databases. Restored 72MB candles.db from git history after rebase abort zeroed it.
- **Coin name format inconsistency is a silent killer (2026-02-27)**: `load_cfgi()` used full symbol (`XRP/USDC`) but cfgi_daily stores as `XRP` or `XRP/USDT`. LIKE 'XRP/USDC%' matched nothing → NaN CFGI → tier adds silently disabled. `load_daily()` already extracted base coin; `load_cfgi()` didn't. Fix: `base = coin.split('/')[0]`. This caused $1,459 equity gap between standalone and wrapper backtests. **Always normalize to base coin for DB lookups.**
- **Missing data ≠ error - silent feature degradation (2026-02-27)**: `_cfgi()` returning NaN wasn't raised as error. Engine just skipped CFGI-gated tier adds (T2/T3). No warning. Test what you ship with the same coin name format.
- **Reimplemented loops always diverge (2026-02-27)**: Wrapper's tick-by-tick reimplementation of standalone's `run()` had subtle extra-trade bugs. Added `backfill_direct()` to call `run()` directly during backfill - 100% match guaranteed.
- **Unit mismatch bugs are silent killers (2026-02-26)**: `price_vs_sma200` stored as percentage (32.55 = +32.55%) but `SMA200_OVEREXTENSION` threshold was 0.20 (decimal). Every MARKUP entry blocked for entire backtest. Fix: threshold = 20. Always verify units match between signal values and thresholds.
- **Deep warmup essential for 2W StochRSI**: Needs ~784 days of daily data. Without Jan 2019 backfill, Oct 2020 signals were invalid. Backfill 1h candles then rebuild daily (correct approach).
- **Structure confirmation gates critical (2026-02-26)**: MARKUP required HH_HL ≥ 2 (bullish structure). Adding LH_LL ≥ 2 requirement for MARKDOWN (bearish structure) created perfect symmetry. ETH shorts improved +108% (+$16.2K profit), blocking 5 bad shorts with ADX barely above 20 but zero bearish structure. Gate applies to both DCA→MARKDOWN and FLAT→MARKDOWN paths.
- **Paper bot state persistence is tricky (2026-02-26)**: Bot loads state.json into memory at startup, then periodically saves from memory. Editing state.json on disk while bot runs gets overwritten. Must: stop bot → edit state.json + trades.csv → restart with --skip-backfill. Even then, engine capital, per_coin_cash, AND total cash must all be edited consistently.
- **Backfill rebuilds everything (2026-02-26)**: Running without --skip-backfill regenerates all state from scratch, wiping any manual edits to trades.csv or state.json.
- **Don't claim outcomes before running the numbers (2026-02-27)**: Told Brett equity wouldn't change on re-backfill. It dropped $1,600 because the CFGI fix changed which trades execute. Brett called it out. Always verify before making claims.
- **V13 paper bot live loop crashes silently (2026-02-27)**: Exits code 1 after CFGI update with no error logged. Root cause: exception handler calls send_telegram() which itself can fail, causing unhandled exception. Fixed by wrapping all output writes + telegram calls in individual try/excepts. Added debug logging to pinpoint exact failure point. Still investigating.
- **All bias trigger approaches tested have flaws (2026-02-26)**: Engine top signals miss new coins (SOL bootstrap). Death cross chatters during consolidation (dozens of daily flips). SMA200 kills bear bottom recovery entries. No universal low-frequency regime trigger found yet.
- **Bear bias system finalized (2026-02-27)**: Bear ON = engine top signal (2W OB93/1W OB85/K<50). Bear OFF = **coin-specific Weekly CFGI RSI(7) < 40**. Upgraded from Daily RSI(14)<35 - weekly timeframe + faster period improved BTC by $4.4K combined. StochRSI tested and rejected (normalizes away signal differences on CFGI). CCU "Bottom Is In" tested and rejected (sentiment leads price - CFGI fires first).
- **Timeframe > calculation method (2026-02-27)**: Switching Daily→Weekly RSI improved results more than switching RSI→StochRSI. Weekly RSI(7) on CFGI is a novel indicator unique to our system.
- **Coin-specific CFGI > market average CFGI (2026-02-26)**: BTC Jun 2024 entry correctly allowed by coin-specific CFGI (BTC sentiment had recovered) while market average still showed fear.
- **V13 vs V12f DCA gap (2026-02-27)**: V13 barely trades during DCA phases (daily ticks, ~5-7 trades/5yr). V12f's adaptive DCA on 1h had 110+ ETH trades compounding. ETH: +284% vs +1,283%. Building isolated DCA test harness to matrix-sweep V12f-style params within V13 DCA windows on 15m candles.
- **DCA phases are structurally long-biased (2026-02-27)**: V13 routes bearish ranging to FLAT→MARKDOWN, not through DCA. 79% of DCA windows exit to MARKUP across all coins. Dual-track (long+short) DCA during DCA phase LOSES money - shorts fight the structural bias. Long-only DCA is correct.
- **FLAT phase is the real bottleneck (2026-02-27)**: HVF was designed for FLAT routing but is dead code (logging only). 42-day timeout defaults to DCA when BTC should go MARKDOWN. HVF>0.3 + SMA50_ABOVE → DCA fast-track has 100% accuracy (20/20) saving ~1,434 FLAT days. Predicting MARKDOWN from FLAT is much harder - existing LH_LL+ADX+Fib gate is the right tool.
- **HVF fast-track fails for SOL (2026-02-27)**: ETF-era test showed SOL goes from +381% to -27% with ANY HVF filter variant (SMA50, SMA200, CFGI>40 all tried). SOL's 131-day ranging at $15-25 in 2023 gets split into bad DCA windows. Works for ETH+BTC only. No universal filter found.
- **ETF era is the relevant test period (2026-02-27)**: Brett directive - Jan 2023+ only. Pre-ETF crypto (2020-2022) was structurally different, too volatile. Don't let pre-ETF data skew V13 decisions.
- **Graceful runoff inflates DCA results (2026-02-27)**: First DCA test showed +$494 including longs riding into markup. Pure DCA grinding within windows is much more modest (+1-2% avg). Phase classification speed matters more than DCA parameter tuning.
- **LINK/XRP daily data backfilled (2026-02-26)**: LINK/USDC 3040 rows, XRP/USDC 2819 rows from Jan 2019. V13SignalPack fails to load them ("Index 1-dimensional" error) - needs weekly candles and possible structure fix.

### Adaptive TP/Deviation System (Live since 2026-02-14)
- Dynamic TP: 0.6-2.5% based on 14-period ATR + regime multipliers (baseline 1.5%, ATR_BASELINE=0.8%)
- Dynamic deviation: 1.2-4.0% (baseline 2.5%), floor = TP × 1.5
- Regime multipliers: RANGING=0.85×TP/0.80×DEV, TRENDING=1.20×TP/1.30×DEV, EXTREME=0.70×TP/1.50×DEV
- Margin-aware: 10% capital reserve, skips unaffordable SOs, cancels deep SOs to ensure TP placement
- TP-hit analysis logged with duration, adaptive params, ATR, regime insight

### Spot DCA Scale-Out Strategy - Designed 2026-02-17
- Full spec: `projects/ait-product/spot-dca-strategy.md`
- Core idea: spot buy DCA in layers, sell in reverse order (largest lots first) on recovery
- Eliminates funding fees, simpler execution, ~5-8× more profit per cycle vs futures
- Long only - pair with futures short-only for bidirectional hybrid
- Coin selection: mature markets (BTC, ETH, SOL), screen out parabolic/meme coins
- Exchange candidates: Aster spot (no HYPE), Hyperliquid (has HYPE), Bybit/MEXC (KYC required)

### Spot Backtests - Completed 2026-02-17
- 47 combinations: 4 coins × 3 profiles × 3 timeframes × 2 exchanges
- Results: `trading/spot/backtest_results/SUMMARY.md`
- **Winners**: HYPE/USDC on Hyperliquid dominates (Medium 15m: +8.8%, Sharpe 11.35), ETH/USDT on Aster solid (Medium 15m: +6.5%)
- **Losers**: BTC and BNB negative across board (extended downtrend)
- **Best timeframe**: 15m (best Sharpe), 5m too noisy, 1h similar returns worse DD
- **100% win rate** on all profitable combos - scale-out exits work
- Parameter optimization sweeps in `trading/spot/backtest_results/optimization/`

### Spot Paper Bots - Evolution
- Originally launched 2026-02-17 as v11 (ETH/USDT 15m Aster, HYPE/USDC 15m Hyperliquid)
- **Current**: V12e paper on Hyperliquid (ETH/SOL/BTC USDC, 1h, pipeline enabled) - see "Current Live Bots" above
- Old tasks `SpotPaperAster` and `SpotPaperHyperliquid` still exist but are from v11 era

### WhiteHatFX History
- Brett previously traded MT4 Martingale (WhiteHatFX v2) on FTMO 100k prop firms: BTC, currencies, gold, US30
- Dual-engine bidirectional grid - same core concept as Aster
- Key diff: 4x lot multiplier (vs 2x now), fixed params, no equity protection
- Evolution: from static hardcoded → dynamic regime-adaptive ("Breathing Grid")

### V13 Coin Scanner - Built 2026-02-25
- `trading/spot/coin_scanner_v13.py` + `trading/spot/run_scanner_v13.py`
- Runs all 44 CFGI tokens through `v13_phase_backtest_v8.py` (the REAL engine)
- 90-day rolling window, high profile, $2,500/coin, Binance 1h candles
- Output: `docs/data/scanner_t2.json` (dashboard reads) + `trading/spot/data/scanner_v13.json`
- Score: 35% closed_roi + 25% win_rate + 20% outperformance + 20% risk_adjusted
- Cold start accurate: scanner phase = exact phase paper bot would start in
- Known issues: ASTER isnan error (short data), HYPE not on Binance, FTM/MATIC delisted

### V13 Analytics DB - Built 2026-02-25
- 5 new tables: `scanner_results`, `phase_transitions`, `signal_snapshots`, `coin_correlations`, `trade_context`
- Daily collector: `trading/spot/daily_collector.py` (candles → daily → CFGI → signals → correlations)
- Runner: `python -u -m trading.spot.run_daily_collector`
- Scanner stores analytics after each run (scanner_results + phase_transitions + trade_context)

### Daily Cron Schedule - Set Up 2026-02-25
- **5:30 AM PST** - V13 Daily Collector (cron ID: a520cd05)
- **6:00 AM PST** - V13 Daily Scanner (cron ID: ef85844d)
- Old `AIT_CandleCollector` task broken (script deleted in git rebase) - superseded

### GitHub Pages Deployment - Fixed 2026-02-25
- **Broken submodule** (`repos/intelligent-accumulation-trading`) caused instant build failures - removed
- **`.nojekyll`** file required in `docs/` to prevent Jekyll processing
- **Sync interval** changed from 2 min → 10 min (GitHub Pages rate limit: 10 builds/hour)
- **Auto-backup conflict**: Workspace auto-backup + sync script both push to `main` - auto-backup was deleting files sync script added. Fixed by ensuring workspace git tracks all `docs/` files.
- Sync script updated to always ensure `.nojekyll` exists

### V13 Documentation Suite - Updated 2026-02-26
- **Architecture spec**: `projects/ait-product/v13-architecture-spec.md` - comprehensive system reference (updated with LH_LL gate, validation results, signal test archive)
- **Test setup**: `projects/ait-product/v13-test-setup.md` - complete test infrastructure reference (DB, scripts, data requirements, validation checklist)
- **Gate test plan**: `projects/ait-product/v13-gate-test-plan.md` - all tests conducted with results, decisions, and lessons learned
- **Test backlog**: `projects/ait/v13-test-backlog.md` - proposed improvements (two-layer failure detector)
- **Paper bot update**: `projects/ait-product/v13-paper-bot-update-markdown-fix.md` - LH_LL gate deployment instructions

### V13 Architecture Spec Detail
- Status: LIVE (fully implemented and operational, updated with LH_LL gate and full validation results)
- Covers: phase model, signals, scanner, analytics DB, dashboard, daily pipeline, incident reports, migration readiness
- Brett's intent: use as reference for scaling to production infrastructure

### Legacy Coin Scanner (Two-Tier Architecture) - Built 2026-02-15, SUPERSEDED & DISABLED
- **Tier 1** (`trading/coin_scanner_t1.py`): ADX, ATR%, Hurst, SMA crosses, volume on all 275 Aster pairs (seconds/coin)
- **Tier 2** (`trading/coin_scanner_t2.py`): Full 14-day 5m backtest on shortlisted coins (minutes/coin)
- **Runner**: `trading/run_scanner.py` - ties both tiers, outputs recommendation
- **Maturity filters**: 60+ day age, <120% price swing, <4x volume spike, $1M volume floor
- Latest results: HYPE #1 (52.9), ASTER #2 (46.1), DOGE #3 (41.2), SOL #4, ETH #5
- Cron job: DISABLED (old ID: b9571b56). V12f scanner cron (ID: 830c5a2a) also disabled 2026-02-26 - source files deleted in git rebase, V13 scanner replaces it
- Rotation threshold: 20% improvement required
- Output: `trading/live/scanner_t1.json`, `scanner_t2.json`, `scanner_recommendation.json`

### Risk Profile System - Spec'd 2026-02-16, Updated 2026-02-22
- Spec: `projects/ait-product/risk-profiles-spec.md`
- 3 profiles (all spot, no leverage): Low (5 SOs, 3% BO, 2 coins), Medium (8 SOs, 4% BO, 3 coins), High (12 SOs, 5% BO, 5 coins)
- Halt thresholds: Low 15% DD, Medium 25% DD, High 35% DD
- Auto-guardrails: Medium→Low at 30% DD, High→Medium at 50% DD (spec claim - auto-downgrade not yet implemented in code)
- Competitive differentiator: portfolio theory for bot trading

### Multi-Coin Portfolio Manager - Built 2026-02-15
- `trading/portfolio_manager.py` - PortfolioManager + CoinSlot classes
- `trading/run_portfolio.py` - entry point (--dry-run, --max-coins, --leverage, --capital)
- Up to 3 coins, scanner-driven, score-proportional allocation, 10% reserve, 15% min per coin
- Graceful wind-down: no new deals, 2h force-close, 4h minimum hold time
- **Not yet live** - bot still running single-coin HYPE via `run_aster.py`
- Capital concern: $335 split 3 ways risks hitting $5 minimum notional; recommend max-coins=2

### Paper Trading Bot (aster_trader_v2.py) - Built 2026-02-16
- `trading/aster_trader_v2.py` - paper bot with risk profile engine
- `trading/run_paper.py` - entry point (--symbol, --timeframe, --capital, --profile, --max-coins)
- Three risk profiles: Low (1×/8 SOs), Medium (2×/12 SOs), High (5×/16 SOs)
- Tier-based coin scaling: Starter=1, Trader=2, Pro=3, Elite=5, Whale=8 max coins
- $3K minimum per coin floor, reads scanner results, falls back to HYPEUSDT
- Writes to `trading/paper/` (status.json, trades.csv, allocation.json)
- **Not yet run live** - built and committed but not started as scheduled task

### Tier-Based Coin Scaling - Spec'd 2026-02-16
- Added to risk-profiles-spec.md, paper bot, pricing page, product page
- Starter($5K)=1, Trader($10K)=2, Pro($25K)=3, Elite($50K)=5, Whale($100K)=8
- $3K minimum per coin floor, 10% global reserve, 20% rotation threshold
- Product page now shows Generation 5 as "Current"

### Directional Awareness - Added 2026-02-15
- SMA50-based trend direction detection in `detect_regime()`
- Directional regimes (TRENDING, MILD_TREND, DISTRIBUTION) flip long/short allocation when bearish
- status.json: `trend_direction: "bullish"/"bearish"`, log shows ▲/▼

### Legacy Coin Screener (superseded)
- Old: `trading/coin_screener.py` - single-tier, no maturity filters
- HYPE ranked #1 (0.876 fitness) for dual-tracking: low trend (2.7%), good range

## Slack Integration
- Workspace: halo-effects.slack.com
- Channel: C092S0TVA0Z
- Full gateway restart needed for Slack socket (SIGUSR1 insufficient)
- Bot name: "Gee Gee"
- **Socket drops silently** - Brett sends messages I never receive. Recurring issue.
- Agent can't restart gateway directly (commands.restart=true not set) - Brett must run `openclaw gateway restart`
- Consider adding Slack health check to HEARTBEAT.md

## TrustedBusinessReviews.com Migration (Active Project)
- **Phase 1 (active):** WordPress → static HTML migration, review system, admin dashboard, Google schema
- Instructions: `projects/tbr/migration-instructions.md`
- FTP access working (Adeel fixed path 2026-02-14)
- **Malware cleanup in progress** - major compromise found, mostly cleaned, ~1,900 spam pages + 2 plugins still need finishing
- Password changes still recommended (credential exfil was active)
- Public crawl done - ~10 business listings across 5-6 categories, Phoenix AZ focused
- Google Doc trick: append `/mobilebasic` to extract text from Google Docs via browser

## Communication Channels
- **Slack** → Halo Effects business (TBR, ShadowQuery, Adeel)
- **Telegram** → Trading bot, personal projects, everything else
- Slack channel: C092DGXUZFW (#team-)
- Slack user IDs: Brett=U092S0TJK5X, Adeel=U092D6SA0JW

## Q1 2026 Roadmap (created 2026-02-26)
- **Roadmap doc**: `projects/roadmap-q1-2026.md` - daily review cadence
- **Project 1**: LLM Engine Config - Gemini 2.5 Pro (reasoning/research), Claude Opus/Sonnet (coding/analytics). Blocked on Gemini API key.
- **Project 2A**: Website V13 update - product, pricing, Wyckoff pages. Collaborative. CSS unchanged, content only.
- **Project 2B**: DCA dual-track optimization - long+short DCA, dynamic BB-based params, risk-profiled tiers. Baseline doc: `projects/ait-product/dca-optimization-baseline.md`
- **Project 2C**: Gate optimization + coin qualification - 17 qualified coins identified from 44. Matrix: `projects/ait-product/coin-qualification-matrix.md`. Backfill, gate accuracy tests, signal stack optimization, light leverage assessment.
- **Project 2D**: Paper bot reset with optimized settings - blocked on 2B+2C.
- **8 V13 gaps** identified and tracked in roadmap (bias trigger, failure detector, FLAT phase, correlation sizing, profit protection, scheduled task, OB85 timing, DCA transitions)

### Qualified Coin Universe (17 coins)
BTC, ETH, XRP, BNB, SOL, LINK, ADA, LTC, AVAX, DOT, UNI, AAVE, NEAR, HBAR, MATIC, ATOM, MKR
- Borderline (could expand to 20): SUI, RENDER, VET
- All meme coins excluded (DOGE, SHIB, PEPE, BONK, WIF, FLOKI)

### Top Conviction Stack Research (2026-02-27 evening)
- **Steve Courtney top sell stack (2D)**: RSI>80 + StochRSI K&D>80 + MFI>80 + Above SMA200
- **MFI (Money Flow Index)**: Volume-weighted RSI - new indicator for us. Differentiates score 2 (noise) from 3/4 (signal).
- **Steve 2D timing crushes OB93**: +4 to +58d before peak vs OB93's +11 to +279d. But 56-85% false positive rate.
- **CFGI at actual tops**: ETH=46 (neutral!), SOL=78, XRP=80. ETH tops in neutral sentiment (divergence).
- **OB93 BROKEN for tops (2026-02-28)**: 2W StochRSI never hit 93 for ETH or BTC in this cycle. Only XRP armed. OB80 still misses BTC. Same bottom/top asymmetry - K pins at 0 at bottoms but oscillates near 100 at tops.
- **2D RSI Bearish Divergence is new top signal (2026-02-28)**: 5/5 coverage, 24% false rate, 24d avg timing. Config: 30-bar 2D lookback, RSI gap≥8, price within 3% of high, RSI>60, RSI peak>75. In V13 MARKUP context: 0% effective false rate (all false positives occur during DCA/FLAT phases). Replaces OB93.
- **RSI bearish divergence present at 100% of cycle tops**: Price HH + RSI LH is the universal top signal. ETH 25d early, BTC 59d early, LINK 6d early.
- **Top harder than bottom**: Tops distribute gradually (divergence), bottoms capitulate sharply (alignment).
- **Doc**: `projects/ait-product/top-conviction-stack-analysis.md`

### Bottom Conviction Stack (LOCKED 2026-02-27)
- Score 0-4 on 2D: (1) Below SMA200, (2) RSI(14)<26, (3) StochRSI K&D<20, (4) CFGI<35
- **Triple gate**: Top detected → 3D death cross active → 2W StochRSI K≥5 (after pinned <5) → score ≥3/4 → FIRE
- One trigger per cycle. No reshort after flip.
- **Action**: Close ALL shorts, flip to MARKUP T1 (60%)
- **Final backtest**: +$9,847 (+98.5%) on $10K, 2 triggers (ETH Jun 2025, LINK Feb 2026), zero false bottoms
- **2W K≥5 gate**: Avg ~17 days / +30% after true bottom - but coins skid at bottom waiting for market turn, so real cost is minimal. Blocked premature SOL Feb 2026 trigger (-0.6% drawdown avoided).
- **Tested and rejected**: No gate (+$11,228 but LINK -7.8% premature), 1W gate (missed ETH), weekly HL (unreliable, XRP 58d delay)
- ROUTER v2 engine: `v13_router_engine_v2.py`, default config = locked params

## Bear Market Coin Research & DCA Cycle Scanner (2026-03-03)
- **Context**: BTC ~$66K, confirmed bear market, Brett believes bear until halving (~2027)
- **Key metric**: DCA cycle velocity - deals completed per week, penalized by drawdown and capital lock-up
- **Composite score**: `DCA Score = Realized_PnL × (1 - MaxDD%) × (1 - open_layers/24) / 100`
- **Top bear market DCA coins (Jan-Mar 2026 backtest, $10K/coin, High profile)**:
  1. ASTER - 3.1 d/wk, +$2,921 realized, 34% DD, 4 layers, **+24.4% net** (only positive)
  2. ATOM - 3.7 d/wk, +$2,692 realized, 30% DD, 7 layers, -10.1% net
  3. INJ - 3.7 d/wk, +$2,667 realized, 45% DD, 7 layers, -27.3% net
  4. HYPE - 3.1 d/wk, +$2,017 realized, 29% DD, 7 layers, -11.8% net
  5. CRV - 2.6 d/wk, +$2,280 realized, 47% DD, 7 layers, -28.9% net
- **Worst for V14 DCA**: BTC (0.9 d/wk), LTC, FIL, ETH (1.4 d/wk) - too slow cycling
- **ASTER outperforms because it doesn't get trapped** (4 open layers vs 7 for all others)
- **ATOM anomaly**: Only -17% DD from Jan 1 while everything else down 35-47%
- **Brett's direction**: Capital rotation - shift capital toward actively cycling coins in real-time
- **Scanner**: `trading/spot/v14_cycle_scanner.py` - rolling window analysis (7d/14d/30d/bear)
- **Output**: `docs/data/v14/cycle_scanner.json` - ranked coins for dashboard consumption
- **Research doc**: `projects/ait-product/bear-market-coin-research.md`
- **Hyperliquid**: 45 quality coins on perps. GRT not available. Aster spot too limited (49 pairs, mostly micro).
- **Production exchange decision (2026-03-03)**: Hyperliquid is the target production exchange. Coin universe built around HL offerings. Aster is small live test only ($300).
- **Lesson**: Simple daily range ≠ DCA profitability. Need to simulate actual cycle completion with capital lock-up.
- **Lesson**: Don't build narrative without data. Brett called out unverified DeFi thesis - "Did you find that in your research or just from what I originally said?"

## Deferred Projects
- **AI GEO / ShadowQuery**: Brett moved discussion to Slack with Adeel; TBR migration is prep for this
- Tutorial notes saved: `reference/shadowquery-tutorials.md`

## Embedding/Memory Search
- Not working - no OpenAI/Google/Voyage API key configured for embeddings
