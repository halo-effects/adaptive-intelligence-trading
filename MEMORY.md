# MEMORY.md - Long-Term Memory

## Brett
- Direct, no-fluff communicator. Values security/governance deeply.
- Timezone: America/Los_Angeles
- Uses Telegram for personal, Slack for Halo Effects business
- No desktop Slack - browser only via Gmail login
- Quote: "It's about finding the right coin at the right time and running the strategy and getting out with your shirt"

## Adaptive Intelligence Trading (AIT)
- **Product name**: Adaptive Intelligence Trading (AIT)
- **GitHub**: github.com/halo-effects/adaptive-intelligence-trading
- **Dashboards**: V14 (dashboardV14.html), V14-ETF (dashboardV14ETF.html), V14 Live (d-984ae0d4ab9dc1a5.html)
- **Dashboard sync**: Windows Scheduled Task AIT_DashboardSync (every 10 min)
- **Production Exchange**: Hyperliquid (perps)

## Current Live Bots
### V14 Live Bot (Aster - ASTER/USDT) - LIVE 
- **Coin**: ASTER/USDT (Spot). $300 real capital.
- **Engine**: V14 DCA-only with ROUTER v2 signals. 
- **Profile**: High (1.5x leverage), BO=40%, Dev=1.5%, Mult=1.5x, 12 layers, TP=1.5%
- **Status/State**: 	rading/spot/live/v14/
- **Scheduled Task**: V14LiveAster

### V14 Paper Bot (Hyperliquid - HBAR/ATOM/LINK/NEAR) - LIVE
- **Profile**: Medium (1.5x leverage), 10 layers. $10K paper.
- **Status/State**: 	rading/spot/paper/v14/
- **Scheduled Task**: V14PaperBot

### V14-ETF Paper Bot (Hyperliquid - SOL/XRP/LTC/HBAR/ADA) - LIVE
- **Profile**: High (1.5x leverage), 12 layers. $10K paper.
- **Status/State**: 	rading/spot/paper/v14etf/
- **Scheduled Task**: V14ETFPaperBot

### V14 PM (Portfolio Manager) Paper Bot (Hyperliquid) - LIVE
- **Strategy**: Dynamic capital rotation with trend-adjusted scoring. $50K paper. 10 coin slots.
- **Allocation**: `Adjusted Score = Base DCA Score × Trend Multiplier` (1.5x for accelerating, 0.36x-0.8x for declining)
- **Profile**: High, 12 layers, 1.0x leverage (no liquidation risk)
- **Trend data**: 45 coins with 7-day backfilled score history. Scanner supports `--backfill-history N` and `--as-of YYYY-MM-DD`.
- **Dashboard**: dashboardV14PM.html
- **Scheduled Task**: V14PMPaperBot (uses `--fresh` flag — starts clean on reboot)

## Bear Market Coin Research & DCA Cycle Scanner
- **Scanner**: 	rading/spot/v14_cycle_scanner.py - rolling window analysis (7d/14d/30d/bear)
- **Metric**: DCA Cycle Velocity (Score = Realized_PnL * (1 - MaxDD%) * Capital_Freedom)
- **Goal**: Capital rotation - shift capital toward actively cycling coins in real-time

## AIT Product Direction
- **V14PM is the MVP** — the product Brett will sell to customers and integrate with Hyperliquid for live trading
- V14 Paper + V14-ETF Paper = demo accounts (show DCA engine performance to prospects)
- V14 Live (Aster) = live proof-of-concept with real capital ($300)
- Dashboards = customer-facing demo surface
- Migration target = V14PM on Hyperliquid mainnet, production Linux cloud server
- Paper bots must stay running throughout migration — they are the demo

## Active Projects
- **LLM Engine Config**: Gemini 2.5 Pro as primary, Claude Opus/Sonnet for specific coding/analytics tasks via sub-agents or session overrides.
- **TrustedBusinessReviews.com Migration**: WordPress -> static HTML. Malware cleanup in progress.
- **ShadowQuery**: Deferred.

## Note on Historical Data
- V13 backtesting, historical roadmaps, and deep technical lessons have been archived to reduce token load.
- See projects/ait-product/history/ for legacy notes.
