# HEARTBEAT.md

## Priority Checks (every heartbeat)

### V14PM Live Bot (Aster Perps — 50 coins) ⚠️ REAL MONEY
- Check `trading/spot/live/v14pm/status.json` for bot health
- Alert if: `running` is false, drawdown > 15%, or status.json stale (>65 min)
- **Capital: ~$340** real USDT. Alert if balance drifts significantly.
- Profile: High grid, 1x leverage, 30d scanner, Aster Perps, 50-coin universe
- Telegram commands: PAUSE, RESUME, CLOSE <COIN>, CLOSE ALL, APPROVE, DENY
- Manual restart: `python -u -m trading.spot.run_v14_portfolio_live_aster --capital 340 --confirm --skip-backfill`
- Real Python: `C:\Users\Never\AppData\Local\Programs\Python\Python312\python.exe`
- Dashboard: `docs/dashboardV14PM.html` (reads from `docs/data/v14-pm/`)
- State file: `trading/spot/live/v14pm/state.json` (persists across restarts)

### V14 Live Bot (Aster Spot — LEGACY, being replaced by V14PM)
- Check `trading/spot/live/v14/status.json` — will be retired once V14PM Live is stable
- Capital: ~$351 real USDT. LIVE GUARD active. Single-coin ASTER/USDT only.
- Scheduled Task: `V14LiveAster` (at boot)
- Manual restart: `python -u -m trading.spot.run_v14_live_aster --confirm --skip-backfill`

### V14 Paper Bot (Hyperliquid — HBAR/ATOM/LINK/NEAR) — LIVE as of 2026-02-28
- Check `trading/spot/paper/v14/status.json` for bot health
- Alert if: process not running or status.json stale (>65 min)
- Coins: HBAR/USDT, ATOM/USDT, LINK/USDC, NEAR/USDT — 1h candles, daily signal ticks
- Profile: Medium (1.5x leverage), BO=40%, Dev=2%, Mult=1.5x, 10 layers, TP=1.5%
- Engine: V14 DCA-only with ROUTER v2 signals
- Entry point: `python -u -m trading.spot.run_v14_paper --capital 10000 --profile medium --exchange hyperliquid --skip-backfill`
- Scheduled Task: `V14PaperBot`
- Backfill verified: +552% on $10K, matches standalone backtest

### V14 PM (Portfolio Manager) Paper Bot — LIVE as of 2026-03-05
- **Capital**: $50K paper. 10 coin slots (equity-tiered). Dynamic allocation with trend multiplier.
- **Profile**: High, 12 layers, **1.0x leverage** (no leverage), Hyperliquid perps (longs + shorts)
- **Allocation**: `Adjusted Score = Base DCA Score × Trend Multiplier` — accelerating coins boosted up to 1.5x, declining penalized down to 0.36x
- **Coins**: Dynamically selected by cycle scanner daily (all 45 scanned coins eligible)
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
