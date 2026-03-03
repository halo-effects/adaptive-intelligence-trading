# HEARTBEAT.md

## Priority Checks (every heartbeat)

### V14 Live Bot (Aster — ASTER/USDT) ⚠️ REAL MONEY
- Check `trading/spot/live/v14/status.json` for bot health
- Alert if: `running` is false, drawdown > 15%, or status.json stale (>65 min)
- **Capital: $300** real USDT. Alert if balance drifts significantly.
- Profile: High, 12 layers, 1.5% TP, 1.5x leverage
- Restart: kill Python PID first, then `Start-ScheduledTask -TaskName "V14LiveAster"` (task not yet created)
- Manual restart: `python -u -m trading.spot.run_v14_live_aster --confirm --skip-backfill`
- Real Python: `C:\Users\Never\AppData\Local\Programs\Python\Python312\python.exe`
- Dashboard: https://halo-effects.github.io/adaptive-intelligence-trading/d-984ae0d4ab9dc1a5.html

### V12f Paper Bot (Hyperliquid — ETH/SOL/BTC USDC)
- Check `trading/spot/paper/v12f/status.json` for bot health
- Alert if: process not running or status.json stale (>65 min, same 1h candle + 5min grace)
- Coins: ETH/USDC, SOL/USDC, BTC/USDC — 1h timeframe, Medium profile
- Pipeline enabled (scanner → pipeline → trader)
- Entry point: `python -u -m trading.spot.run_v12f_paper --exchange hyperliquid --pipeline`

### V13 Paper Bot — SUNSET (2026-03-02)
- **Stopped.** V14 is the go-forward engine. V13 kept for reference only.
- Final state: +184.5% equity ($28,449), all 4 coins in MARKDOWN tier 3 shorts

### V14 Paper Bot (Hyperliquid — HBAR/ATOM/LINK/NEAR) — LIVE as of 2026-02-28
- Check `trading/spot/paper/v14/status.json` for bot health
- Alert if: process not running or status.json stale (>65 min)
- Coins: HBAR/USDT, ATOM/USDT, LINK/USDC, NEAR/USDT — 1h candles, daily signal ticks
- Profile: Medium (1.5x leverage), BO=40%, Dev=2%, Mult=1.5x, 10 layers, TP=1.5%
- Engine: V14 DCA-only with ROUTER v2 signals
- Entry point: `python -u -m trading.spot.run_v14_paper --capital 10000 --profile medium --exchange hyperliquid --skip-backfill`
- Scheduled Task: `V14PaperBot`
- Backfill verified: +552% on $10K, matches standalone backtest

### V14-ETF Paper Bot (Hyperliquid — SOL/XRP/LTC/HBAR/ADA) — LIVE as of 2026-03-02
- Check `trading/spot/paper/v14etf/status.json` for bot health
- Alert if: process not running or status.json stale (>65 min)
- Coins: SOL/USDT, XRP/USDT, LTC/USDT, HBAR/USDT, ADA/USDT — 1h candles, daily signal ticks
- Profile: High (1.5x leverage), BO=40%, Dev=1.5%, Mult=1.5x, 12 layers, TP=1.5%
- Engine: V14 DCA-only with ROUTER v2 signals
- Fresh start (no backfill history) — started 2026-03-02 with $10K
- Entry point: `python -u -m trading.spot.run_v14etf_paper --capital 10000 --profile high --exchange hyperliquid --fresh`
- Telegram: All notifications prefixed with `[V14-ETF]`
- Scheduled Task: `V14ETFPaperBot` (created 2026-03-02)
- Dashboard: `docs/dashboardV14ETF.html`

### Dashboard Sync
- Task: `AIT_DashboardSync` (every 10 min — changed from 2 min to avoid GitHub Pages rate limit)
- Verify `docs/data/v13/status.json` is fresh on GitHub Pages
- `.nojekyll` must exist in `docs/` — sync script ensures this
- If builds fail, check: broken submodules, rate limiting (max 10 builds/hour), `.nojekyll` present

### Cron Job Health
- Quick check: have any cron jobs failed in the last cycle? Check `memory/consolidation.log` for nightly consolidation status.
- If morning briefing or weekly review failed, note it for Brett.

## Periodic Checks (rotate through, 2-3x per day)
- Are there active project deadlines approaching within 48 hours?
- Any blocked tasks waiting for input >24 hours?

## When to Alert Brett
- A trading bot stopped or is stale
- Drawdown exceeds thresholds
- A cron job failed and needs intervention
- A project deadline is <24 hours away with incomplete tasks

## When to Stay Silent (HEARTBEAT_OK)
- Nothing urgent
- All bots running normally
- No approaching deadlines
- Late evening (after 9 PM) unless truly urgent
- You just checked <30 minutes ago and nothing changed

## Governance Reminder
- Before any heartbeat action, verify it falls within Tier 0-1 permissions.
- Never initiate financial operations, external communications, or system changes from a heartbeat.
