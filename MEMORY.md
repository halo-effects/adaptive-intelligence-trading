# MEMORY.md — Long-Term Memory

## Brett
- Direct, no-fluff communicator. Values security/governance deeply.
- Timezone: America/Los_Angeles
- Uses Telegram for personal, Slack for Halo Effects business
- No desktop Slack — browser only via Gmail login
- Quote: "It's about finding the right coin at the right time and running the strategy and getting out with your shirt"

## Adaptive Intelligence Trading (AIT)
- **Product name**: Adaptive Intelligence Trading (AIT) — decided 2026-02-14
- **GitHub**: github.com/halo-effects/adaptive-intelligence-trading (account: halo-effects, geegee@haloeffects.net)
- **Product page**: https://halo-effects.github.io/adaptive-intelligence-trading/ (served from `docs/` on main branch)
- **Live Dashboard**: https://halo-effects.github.io/adaptive-intelligence-trading/dashboard.html (v3.0, data synced every 2 min)
- **Local dashboard**: trading/live/dashboard.html (served on port 8080)
- GitHub PAT: `openclaw-deploy` (repo scope, expires ~Mar 16 2026)
- **Dashboard sync**: Windows Scheduled Task `AIT_DashboardSync` runs every 2 min, pushes status.json/trades.csv to `docs/data/` via `trading/sync_dashboard.ps1`
- GitHub Pages config: Deploy from branch `main`, folder `/docs`

## Current Live Bots

### Aster Spot Live (ASTER/USDT) — V12f
- **Live** on Aster DEX, Medium profile, 1h timeframe, lifecycle enabled
- Task: `AsterSpotLive` (updated to 1h trigger by Brett 2026-02-23)
- Files: `trading/spot/lifecycle_trader.py` (class: `LifecycleTrader`), `trading/spot/run_live.py`
- State/status: `trading/spot/live/aster/`
- Dashboard: `docs/data/live-aster/` → private `d-474521b7c3545633.html`

### V12f Paper (Hyperliquid — ETH/SOL/BTC USDC)
- Hyperliquid, Medium profile, 1h timeframe, lifecycle + pipeline enabled
- Entry point: `python -u -m trading.spot.run_v12f_paper --exchange hyperliquid --pipeline`
- Coins: ETH/USDC, SOL/USDC, BTC/USDC
- State/status: `trading/spot/paper/v12f/`
- Old `run_v12e_paper` and task `SpotPaperHyperliquid` (v11 HYPE/USDC 15m) are DEPRECATED
- Dashboard: `docs/data/v12f/` → public `dashboardV12.html`

### Legacy: Aster Futures Bot (DEPRECATED → ARCHIVED)
- Was HYPE/USDT dual-tracking bidirectional DCA on Aster futures
- Task `AsterTradingBot` is **Disabled** — superseded by spot V12f
- All legacy code archived to `_legacy/` directory (2026-02-24)

### System Architecture Doc
- **Location**: `docs/SYSTEM_ARCHITECTURE.md` (built 2026-02-24)
- Comprehensive reference for cloud migration: subsystems, dependencies, data flows, security, flagged items
- Pre-migration cleanup completed: 194 legacy files archived, scanner relocated to `trading/scanner/`, Dockerfile created

### Phase Architecture Direction (2026-02-24, updated evening)
- **Cold start classifier (`classify_phase()`) is fundamentally flawed** — stateless snapshot whipsaws every 1-2 days (BNB had ~60+ transitions in 4 months)
- **Plan: eliminate cold start entirely** by persisting engine phase state per coin via `snapshot_state()`/`restore_state()`
- Engine's `DailyScorerConductor` (stateful, hysteresis) is the correct phase system — not the classifier
- **V12f gates always True**: Brett: "They should always be true" — no longer optional toggles
- **ATH distance unreliable** for coins with inflation/unlocks — use price structure (trend + regime) instead

### Architecture Evolution — Two-Timeframe + Simplified Phases (2026-02-24 evening)
- **Root cause of bad demo results**: 1h Conductor is too sensitive for macro phase decisions. Fires EXIT on minor dips, whipsaws.
- **Brett: "The pattern is there but we are switching on and off too fast"**
- **Drop SPRING phase entirely**: "We probably don't need a spring. Once the bottom is in, EXIT back to what conductor says."
- **Two-timeframe architecture**: Daily+Weekly for strategy (Conductor), 1h for execution (DCA engine)
- **Simplified phase model**: Conductor reads market daily → MARKUP / DISTRIBUTION / MARKDOWN / ACCUMULATION. Ride phase until confirmed otherwise. EXIT gracefully between phases.
- **No hardcoded transitions**: Every phase change = Conductor directional check. No fixed Wyckoff sequence.
- **Brett: "Once we confirm markup, we stay in markup for a long time. Once we exit, we stay in markdown for a long time."**
- **Brett: "Once we are in a phase we ride the phase until confirmed otherwise then EXIT to next phase as gracefully as possible."**
- **Accept small losses for bigger wins**: Brett: "It's OK if we take some losing trades as long we make up for them with bigger winners." Positive expectancy > win rate. Close longs fast when direction confirmed, don't hold for days chasing breakeven.
- **Simplified EXIT**: Instead of 14-day trailing unwind, close at market when Conductor confirms direction change. Small loss exiting = cost of being positioned correctly for next phase. A -2% exit loss is nothing vs a 15-30% phase move.
- **Current V12f production bot is still valid** — published backtest numbers still hold. This is optimization.
- Full evening session notes: `memory/2026-02-24-evening.md`
- Demo script: `trading/spot/backtest_results/demo/run_demo_backtest.py`

### Backtest Engine Consolidation (2026-02-24)
- **Flattened 11-file inheritance chain** (base → v2 → v3 → v4 → v5 → v6 → v7 → v8 → v9 → v12 → v12f) into single `backtest_engine_consolidated.py` (~6,400 lines, 313KB)
- Old versioned files replaced with thin compatibility shims (re-exports)
- Originals backed up to `trading/spot/_originals/`
- **Verified**: backtest results match baseline exactly (BTC 90d: -6.99% return, 7 deals, Sharpe -1.26, DD 14.15%, 100% win rate)
- All production imports verified: lifecycle_trader, lifecycle_engine, scanner, v12/v3 data classes

### Key Technical Lessons
- reduceOnly orders fail in net position mode when opposing side has larger position — don't use reduceOnly
- Base order sizing should NOT scale by allocation % (hits minimums) — allocation only gates open/close
- TP retry logic needed — exchange can reject TP placement, must auto-retry
- 5m timeframe >> 1m for this strategy (less noise)
- 1x leverage >> 2x (counterintuitive — 2x eats capital reducing deal cycling)
- Wider SO deviation (2.5%) strongly preferred over tight (1.5%)
- **Net position mode margin trap**: selling to close a long can flip net short, requiring margin for the flip — must check margin before TP placement
- **TP > SOs priority**: always ensure TP can be placed, cancel deep SOs if needed to free margin
- **Aster fees**: Maker = 0% (free), Taker = 0.04% — limit orders (TP, SO fills) are free
- **Position drift bug (found 2026-02-17)**: old sync function only checked sign/zero, never compared qty. Orders can accumulate orphaned exposure silently. Fixed with qty drift detection + Telegram alerts.
- **Spot reconciliation bug (fixed 2026-02-23)**: `_get_spot_position()` used `free` balance, missing coins locked in open TP sell orders → bot thought position gone → duplicate buys on every restart. Fixed to use `total` balance.
- **Funding fees are the hidden killer**: Aster charges every 4h. Positions held 24h+ with SOs can lose 50-66% of expected TP profit to funding. Must factor into strategy.
- **Aster API quirks**: `/fapi/v1/income` and `/fapi/v1/userTrades` return 400. Use `/fapi/v1/fundingRate` (public) + `/fapi/v1/premiumIndex` (public) instead. `/fapi/v2/balance` works signed, `/fapi/v2/positionRisk` works signed.
- **1h candles too noisy for macro phase decisions** — Conductor scoring every hour fires EXIT on minor dips. Daily+Weekly is the right timeframe for Wyckoff phase detection. 1h for execution only.
- **Spring system was over-engineered** — built gates, Martingale tiering, recovery override, but 0 springs ever fired in testing. The real problem was Conductor sensitivity, not spring detection.
- **Duplicate code from consolidation is dangerous** — 6,400-line engine had TWO identical DCA→EXIT checks. Guard one, miss the other = hours of debugging.
- **Don't stack patches on a wrong foundation** — cooldowns, recovery overrides, post-EXIT routing all compensated for the real problem (1h sensitivity). Fix the root cause instead.
- **Force sync tool**: `trading/force_sync.py` — interactive tool to reconcile exchange vs tracked position

### Wyckoff Volume-Price Research (2026-02-24)
- Ran 10 isolated tests on Wyckoff volume-price signals for spring/exit timing improvement
- **8 of 10 volume-based tests failed** — crypto exchange volume is too noisy (wash trading, 24/7 markets, fragmented exchanges)
- **Test 10 (200-SMA overextension) = STRONG SIGNAL**: GOOD markups avg 11.4% above 200-SMA, BAD markups avg 34.5%. Threshold at 20% blocks 69% of BAD, keeps 71% of GOOD.
- **Test 1W (weekly buy/sell ratio)** = partial signal: 4/6 springs matched pattern at weekly timeframe
- Brett insight: "With crypto, sentiment is probably the strongest signal" — CFGI already captures what Wyckoff volume measures in equities
- **Conclusion**: Volume signals don't transfer to crypto. Price-based mean reversion (200-SMA) + CFGI sentiment = the viable path
- Full analysis: `projects/ait-product/spring-markdown-comprehensive-analysis.md`
- Test results: `trading/spot/backtest_results/cfgi_dwell_analysis/TEST{1,1W,4,5,6,8,8W,10}_*.md`

### Adaptive TP/Deviation System (Live since 2026-02-14)
- Dynamic TP: 0.6–2.5% based on 14-period ATR + regime multipliers (baseline 1.5%, ATR_BASELINE=0.8%)
- Dynamic deviation: 1.2–4.0% (baseline 2.5%), floor = TP × 1.5
- Regime multipliers: RANGING=0.85×TP/0.80×DEV, TRENDING=1.20×TP/1.30×DEV, EXTREME=0.70×TP/1.50×DEV
- Margin-aware: 10% capital reserve, skips unaffordable SOs, cancels deep SOs to ensure TP placement
- TP-hit analysis logged with duration, adaptive params, ATR, regime insight

### Spot DCA Scale-Out Strategy — Designed 2026-02-17
- Full spec: `projects/ait-product/spot-dca-strategy.md`
- Core idea: spot buy DCA in layers, sell in reverse order (largest lots first) on recovery
- Eliminates funding fees, simpler execution, ~5-8× more profit per cycle vs futures
- Long only — pair with futures short-only for bidirectional hybrid
- Coin selection: mature markets (BTC, ETH, SOL), screen out parabolic/meme coins
- Exchange candidates: Aster spot (no HYPE), Hyperliquid (has HYPE), Bybit/MEXC (KYC required)

### Spot Backtests — Completed 2026-02-17
- 47 combinations: 4 coins × 3 profiles × 3 timeframes × 2 exchanges
- Results: `trading/spot/backtest_results/SUMMARY.md`
- **Winners**: HYPE/USDC on Hyperliquid dominates (Medium 15m: +8.8%, Sharpe 11.35), ETH/USDT on Aster solid (Medium 15m: +6.5%)
- **Losers**: BTC and BNB negative across board (extended downtrend)
- **Best timeframe**: 15m (best Sharpe), 5m too noisy, 1h similar returns worse DD
- **100% win rate** on all profitable combos — scale-out exits work
- Parameter optimization sweeps in `trading/spot/backtest_results/optimization/`

### Spot Paper Bots — Evolution
- Originally launched 2026-02-17 as v11 (ETH/USDT 15m Aster, HYPE/USDC 15m Hyperliquid)
- **Current**: V12f paper on Hyperliquid (ETH/SOL/BTC USDC, 1h, pipeline enabled) — see "Current Live Bots" above
- Old tasks `SpotPaperAster` and `SpotPaperHyperliquid` still exist but are from v11 era

### WhiteHatFX History
- Brett previously traded MT4 Martingale (WhiteHatFX v2) on FTMO 100k prop firms: BTC, currencies, gold, US30
- Dual-engine bidirectional grid — same core concept as Aster
- Key diff: 4x lot multiplier (vs 2x now), fixed params, no equity protection
- Evolution: from static hardcoded → dynamic regime-adaptive ("Breathing Grid")

### Coin Scanner (Two-Tier Architecture) — Built 2026-02-15, V12f Rewrite 2026-02-24
- **Tier 1** (`trading/coin_scanner_t1.py`): CFGI-only mode (default) — scans 7 Aster CFGI pairs in seconds. Legacy full-scan (291 pairs) available via `cfgi_only=False`
- **Tier 2** (`trading/coin_scanner_t2_v12f.py`): ✅ V12f lifecycle backtest engine + coin CFGI + candle DB. Replaces legacy `coin_scanner_t2.py` (MartingaleBot).
- **Production scanner spec**: `~/life/projects/ait/production-scanner-spec.md`
- **Runner**: `trading/run_scanner.py` — imports V12f T2, current coin = ASTER/USDT
- **Candle DB**: `trading/spot/data/candles.db` (SQLite, 15 coins, up to 47K candles/coin). T2 reads from DB first, API fallback on miss.
- **Backtest window**: 90 days (lifecycle phases need 50+ daily bars)
- T1 results (2026-02-24): ASTER #1 (73.7), BNB #2 (52.2), XRP #3 (52.2), BTC #4 (49.6)
- T2 results (90d, V12f): BTC #1 (105, Sharpe 2.53), ASTER #2 (98, Sharpe 1.57), PEPE #3 (66), TRUMP #4 (51)
- Cron job: every 4h (ID: b9571b56-5d72-4d25-b125-d834b12ea572) — needs updating to use new pipeline
- Rotation threshold: 20% improvement required
- Output: `trading/live/scanner_t1.json`, `scanner_t2.json`, `scanner_recommendation.json`
- **Tradeable CFGI tokens (10)**: Aster: BTC, ETH, SOL, BNB, ASTER, DOGE, XRP. Hyperliquid: HYPE, PEPE, TRUMP.
- **Non-tradeable CFGI tokens**: AAVE, ADA, ARB, AVAX, DOT, INJ, LINK, SUI, TON, UNI (not on either exchange)
- **CFGI client**: `trading/spot/cfgi_client.py` — cfgi.io API, per-coin + market, cached. Bug fixed: `get_history()` no longer sends `values` with `start`+`end`.
- **Brett directive**: Only scan/trade coins with coin-specific CFGI. No scanning coins we can't trade. Paper bot = production beta with full pipeline.
- **Gap**: Hyperliquid-only coins (HYPE, PEPE, TRUMP) not in T1 — needs multi-exchange T1 or separate scan

### Risk Profile System — Spec'd 2026-02-16, Updated 2026-02-22
- Spec: `projects/ait-product/risk-profiles-spec.md`
- 3 profiles (all spot, no leverage): Low (5 SOs, 3% BO, 2 coins), Medium (8 SOs, 4% BO, 3 coins), High (12 SOs, 5% BO, 5 coins)
- Halt thresholds: Low 15% DD, Medium 25% DD, High 35% DD
- Auto-guardrails: Medium→Low at 30% DD, High→Medium at 50% DD (spec claim — auto-downgrade not yet implemented in code)
- Competitive differentiator: portfolio theory for bot trading

### Multi-Coin Portfolio Manager — Built 2026-02-15
- `trading/portfolio_manager.py` — PortfolioManager + CoinSlot classes
- `trading/run_portfolio.py` — entry point (--dry-run, --max-coins, --leverage, --capital)
- Up to 3 coins, scanner-driven, score-proportional allocation, 10% reserve, 15% min per coin
- Graceful wind-down: no new deals, 2h force-close, 4h minimum hold time
- **Not yet live** — bot still running single-coin HYPE via `run_aster.py`
- Capital concern: $335 split 3 ways risks hitting $5 minimum notional; recommend max-coins=2

### Paper Trading Bot (aster_trader_v2.py) — Built 2026-02-16
- `trading/aster_trader_v2.py` — paper bot with risk profile engine
- `trading/run_paper.py` — entry point (--symbol, --timeframe, --capital, --profile, --max-coins)
- Three risk profiles: Low (1×/8 SOs), Medium (2×/12 SOs), High (5×/16 SOs)
- Tier-based coin scaling: Starter=1, Trader=2, Pro=3, Elite=5, Whale=8 max coins
- $3K minimum per coin floor, reads scanner results, falls back to HYPEUSDT
- Writes to `trading/paper/` (status.json, trades.csv, allocation.json)
- **Not yet run live** — built and committed but not started as scheduled task

### Tier-Based Coin Scaling — Spec'd 2026-02-16
- Added to risk-profiles-spec.md, paper bot, pricing page, product page
- Starter($5K)=1, Trader($10K)=2, Pro($25K)=3, Elite($50K)=5, Whale($100K)=8
- $3K minimum per coin floor, 10% global reserve, 20% rotation threshold
- Product page now shows Generation 5 as "Current"

### Directional Awareness — Added 2026-02-15
- SMA50-based trend direction detection in `detect_regime()`
- Directional regimes (TRENDING, MILD_TREND, DISTRIBUTION) flip long/short allocation when bearish
- status.json: `trend_direction: "bullish"/"bearish"`, log shows ▲/▼

### Legacy Coin Screener (superseded)
- Old: `trading/coin_screener.py` — single-tier, no maturity filters
- HYPE ranked #1 (0.876 fitness) for dual-tracking: low trend (2.7%), good range

## Slack Integration
- Workspace: halo-effects.slack.com
- Channel: C092S0TVA0Z
- Full gateway restart needed for Slack socket (SIGUSR1 insufficient)
- Bot name: "Gee Gee"
- **Socket drops silently** — Brett sends messages I never receive. Recurring issue.
- Agent can't restart gateway directly (commands.restart=true not set) — Brett must run `openclaw gateway restart`
- Consider adding Slack health check to HEARTBEAT.md

## TrustedBusinessReviews.com Migration (Active Project)
- **Phase 1 (active):** WordPress → static HTML migration, review system, admin dashboard, Google schema
- Instructions: `projects/tbr/migration-instructions.md`
- FTP access working (Adeel fixed path 2026-02-14)
- **Malware cleanup in progress** — major compromise found, mostly cleaned, ~1,900 spam pages + 2 plugins still need finishing
- Password changes still recommended (credential exfil was active)
- Public crawl done — ~10 business listings across 5-6 categories, Phoenix AZ focused
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
- Not working — no OpenAI/Google/Voyage API key configured for embeddings
