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
- **Live Dashboard**: https://halo-effects.github.io/adaptive-intelligence-trading/dashboard.html (v3.0, data synced every 2 min)
- **Local dashboard**: trading/live/dashboard.html (served on port 8080)
- GitHub PAT: `openclaw-deploy` (repo scope, expires ~Mar 16 2026)
- **Dashboard sync**: Windows Scheduled Task `AIT_DashboardSync` runs every 2 min, pushes status.json/trades.csv to `docs/data/` via `trading/sync_dashboard.ps1`
- GitHub Pages config: Deploy from branch `main`, folder `/docs`

## Current Live Bots

### Aster Spot Live (ASTER/USDT) - V12e
- **Live** on Aster DEX, Medium profile, 1h timeframe, lifecycle enabled
- Task: `AsterSpotLive` (updated to 1h trigger by Brett 2026-02-23)
- Files: `trading/spot/lifecycle_trader.py` (class: `LifecycleTrader`), `trading/spot/run_live.py`
- State/status: `trading/spot/live/aster/`
- Dashboard: `docs/data/live-aster/` → private `d-474521b7c3545633.html`

### V12e Paper (Hyperliquid - ETH/SOL/BTC USDC)
- Hyperliquid, Medium profile, 1h timeframe, pipeline enabled
- Task: `SpotPaperHyperliquid`
- Coins: ETH/USDC, SOL/USDC, BTC/USDC
- State/status: `trading/spot/paper/hyperliquid/`
- Dashboard: `docs/data/v12e/` → public `dashboardV12.html`

### V13 Paper Bot (Hyperliquid - ETH/SOL/LINK/XRP USDC) - LIVE as of 2026-02-25
- **Engine**: `v13_phase_backtest_v8.py` (43KB) - the CORRECT v8, NOT `v13_backtest_v8.py` (38KB)
- **Wrapper**: `v13_lifecycle_engine_v2.py` - live wrapper around the phase backtest engine
- **Runner**: `trading/spot/run_v13_paper.py`
- Coins: ETH/USDC, SOL/USDC, LINK/USDC, XRP/USDC - 1h candles, daily signal ticks at midnight UTC
- Profile: High (T1=60%, T2=20%, T3=10%, symmetric shorts, DCA 8% BO, 8 layers)
- Capital: $10,000 paper, $2,500/coin
- State/status: `trading/spot/paper/v13/`
- **Backtest ROI**: +199.1% portfolio ($10K → $29,910), verified exact match trade-for-trade
- **Current state (2026-02-25)**: All 4 coins in MARKDOWN, tier 3 shorts, adx_below_20_streak=0, equity $29,499 (+195%)
- **Single instance running** (PID 2704) - duplicate PID 2284 killed 2026-02-25
- **Brett directive (2026-02-25)**: "Just focus on V13 - our most valuable asset now"
- **4 phases**: DCA → MARKUP → FLAT → MARKDOWN
- **Key signals**: HH_HL+Fib (markup entry), ADX+Fib_break (markdown), 2W StochRSI OB93 (top), ADX ranging (exit), HVF (FLAT routing logged only)
- **Front-loaded tiers**: 60/20/10 for both markup AND shorts (symmetric)
- **Failure detectors**: Markup fail (DD>25%+ADX>25), Markdown fail (rise>25%+ADX>25)
- **FLAT routing**: 3 paths - from top (check markdown 42d max), from ranging (ADX<20 14d→DCA), from markdown (same)
- **Min phase hold**: 3 days (not 2 weeks!)
- Scheduled Task: **Not yet created** - needs elevated PS from Brett
- **CRITICAL**: Multiple v8 backtest files exist - only `v13_phase_backtest_v8.py` is correct. `v13_backtest_v8.py` produces -15% ROI on same coins.

### Aster Spot Live Bot - STATUS UNKNOWN (2026-02-25)
- `AsterSpotLive` task state=Ready but no LastRunTime, no status.json exists
- No Python process found running Aster as of 2026-02-25 evening
- Last known status was 2026-02-17 (9+ days stale before file disappeared)

### V12f Paper Bot - RUNNING BUT BROKEN STATUS (2026-02-25)
- Process running (PID 10352) but `trading/spot/paper/v12f/` directory doesn't exist
- Status file not being written - may need path fix in runner

### Legacy: Aster Futures Bot (DEPRECATED)
- Was HYPE/USDT dual-tracking bidirectional DCA on Aster futures
- Task `AsterTradingBot` is **Disabled** - superseded by spot V12e

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

### V13 Coin Scanner — Built 2026-02-25
- `trading/spot/coin_scanner_v13.py` + `trading/spot/run_scanner_v13.py`
- Runs all 44 CFGI tokens through `v13_phase_backtest_v8.py` (the REAL engine)
- 90-day rolling window, high profile, $2,500/coin, Binance 1h candles
- Output: `docs/data/scanner_t2.json` (dashboard reads) + `trading/spot/data/scanner_v13.json`
- Score: 35% closed_roi + 25% win_rate + 20% outperformance + 20% risk_adjusted
- Cold start accurate: scanner phase = exact phase paper bot would start in
- Known issues: ASTER isnan error (short data), HYPE not on Binance, FTM/MATIC delisted

### V13 Analytics DB — Built 2026-02-25
- 5 new tables: `scanner_results`, `phase_transitions`, `signal_snapshots`, `coin_correlations`, `trade_context`
- Daily collector: `trading/spot/daily_collector.py` (candles → daily → CFGI → signals → correlations)
- Runner: `python -u -m trading.spot.run_daily_collector`
- Scanner stores analytics after each run (scanner_results + phase_transitions + trade_context)

### Daily Cron Schedule — Set Up 2026-02-25
- **5:30 AM PST** — V13 Daily Collector (cron ID: a520cd05)
- **6:00 AM PST** — V13 Daily Scanner (cron ID: ef85844d)
- Old `AIT_CandleCollector` task broken (script deleted in git rebase) — superseded

### Legacy Coin Scanner (Two-Tier Architecture) - Built 2026-02-15, SUPERSEDED
- **Tier 1** (`trading/coin_scanner_t1.py`): ADX, ATR%, Hurst, SMA crosses, volume on all 275 Aster pairs (seconds/coin)
- **Tier 2** (`trading/coin_scanner_t2.py`): Full 14-day 5m backtest on shortlisted coins (minutes/coin)
- **Runner**: `trading/run_scanner.py` - ties both tiers, outputs recommendation
- **Maturity filters**: 60+ day age, <120% price swing, <4x volume spike, $1M volume floor
- Latest results: HYPE #1 (52.9), ASTER #2 (46.1), DOGE #3 (41.2), SOL #4, ETH #5
- Cron job: every 4h (ID: b9571b56-5d72-4d25-b125-d834b12ea572)
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

## Deferred Projects
- **AI GEO / ShadowQuery**: Brett moved discussion to Slack with Adeel; TBR migration is prep for this
- Tutorial notes saved: `reference/shadowquery-tutorials.md`

## Embedding/Memory Search
- Not working - no OpenAI/Google/Voyage API key configured for embeddings
