# HEARTBEAT.md

## Priority Checks (every heartbeat)

### V14 Live Bot (Aster — ASTER/USDT) ⚠️ REAL MONEY
- Check `trading/spot/live/v14/status.json` for bot health
- Alert if: `running` is false, drawdown > 15%, or status.json stale (>65 min)
- **Capital: reads from DEX on startup** (was $300 seed, now ~$385 with PnL). Alert if status.json stale.
- Profile: High, 12 layers, 1.5% TP, 1.5x leverage
- Restart: kill Python PID first, then `Start-ScheduledTask -TaskName "V14LiveAster"`
- **PRE-FLIGHT REQUIRED**: `python -c "from trading.spot.run_v14_portfolio_live_aster import V14PortfolioLiveAster; print('OK')"` before every restart
- Scheduled Task: `V14LiveAster` (at boot) — confirmed exists as of 2026-03-09
- Manual restart: `python -u -m trading.spot.run_v14_live_aster --confirm --skip-backfill`
- Real Python: `C:\Users\Never\AppData\Local\Programs\Python\Python312\python.exe`
- Dashboard: https://halo-effects.github.io/adaptive-intelligence-trading/d-984ae0d4ab9dc1a5.html
- **CHANGES 2026-05-08**: DEX-as-truth startup, reconciliation disabled, auto deposit detection disabled

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

### V14 PM (Portfolio Manager) Live Bot — Aster Perps
- **Capital**: Reads from DEX on startup (~$385). 3 coin slots (equity-tiered at <$500).
- **Profile**: High, 12 layers, **1.0x leverage** (no leverage), Aster Perps
- **Positions**: PENDLE 7.0 qty, TON 61.7 qty (oversized, approved to hold)
- **TP Orders**: PENDLE limit @ $2.0645, TON market sell
- Check `trading/spot/live/v14pm/status.json` for bot health
- Alert if: process not running or status.json stale (>65 min)
- **PRE-FLIGHT REQUIRED before restart**: `python -c "from trading.spot.run_v14_portfolio_live_aster import V14PortfolioLiveAster; print('OK')"`
- Entry point: `python -u -m trading.spot.run_v14_portfolio_live_aster --capital 300 --confirm --skip-backfill`
- Dashboard: `docs/d-984ae0d4ab9dc1a5.html`
- **CHANGES 2026-05-08**: DEX-as-truth startup, reconciliation disabled, auto deposit detection disabled, candle replay guard (4500s)

### V14 PM Paper Bot (Hyperliquid)
- Check `trading/spot/paper/v14_portfolio/status.json` for bot health
- Alert if: process not running or status.json stale (>65 min)
- Scheduled Task: `V14PMPaperBot` (at login)
- Entry point: `python -u -m trading.spot.run_v14_portfolio_paper --capital 50000 --profile high --leverage 1.0 --fresh`
- Dashboard: `docs/dashboardV14PM.html`

### V14 DCA Cycle Scanner
- New tool: `trading/spot/v14_cycle_scanner.py` — scores coins by DCA cycle velocity
- Output: `docs/data/v14/cycle_scanner.json`
- Not yet scheduled — run manually or wire into periodic task
- Brett wants real-time capital rotation based on scanner rankings

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
