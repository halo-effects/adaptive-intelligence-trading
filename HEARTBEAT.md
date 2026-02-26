# HEARTBEAT.md

## Priority Checks (every heartbeat)

### Aster Spot Live Bot (ASTER/USDT)
- Check `trading/spot/live/aster/status.json` for bot health
- Alert if: `running` is false, drawdown > 15%, or regime changes to EXTREME
- Check status.json `last_update` — stale if >65 min old (1h candle + 5min grace)
- **Capital: $300** (rebased 2026-02-23). Alert if status.json shows different capital value.
- Restart: kill Python PID first, then `Start-ScheduledTask -TaskName "AsterSpotLive"` (task alone won't kill running process)
- Real Python: `C:\Users\Never\AppData\Local\Programs\Python\Python312\python.exe`
- Config: ASTER/USDT, Medium profile, 1h timeframe, V12f lifecycle + CFGI gates enabled

### V12f Paper Bot (Hyperliquid — ETH/SOL/BTC USDC)
- Check `trading/spot/paper/v12f/status.json` for bot health
- Alert if: process not running or status.json stale (>65 min, same 1h candle + 5min grace)
- Coins: ETH/USDC, SOL/USDC, BTC/USDC — 1h timeframe, Medium profile
- Pipeline enabled (scanner → pipeline → trader)
- Entry point: `python -u -m trading.spot.run_v12f_paper --exchange hyperliquid --pipeline`

### V13 Paper Bot (Hyperliquid — ETH/SOL/LINK/XRP USDC) — LIVE as of 2026-02-25
- Check `trading/spot/paper/v13/status.json` for bot health
- Alert if: process not running or status.json stale (>65 min)
- **Engine**: `v13_phase_backtest_v8.py` (the correct one — 43KB, NOT v13_backtest_v8.py)
- Coins: ETH/USDC, SOL/USDC, LINK/USDC, XRP/USDC — 1h candles, daily signal ticks
- Profile: High (T1=60%, T2=20%, T3=10%, symmetric shorts)
- Backfill verified: exact trade-for-trade match with standalone backtest (+199% portfolio ROI)
- Entry point: `python -u -m trading.spot.run_v13_paper --capital 10000 --profile high --exchange hyperliquid --skip-backfill`
- Scheduled Task: **Not yet created** — needs elevated PS from Brett

### Dashboard Sync
- Task: `AIT_DashboardSync` (every 2 min)
- Verify `docs/data/v12f/status.json` and `docs/data/live-aster/status.json` are fresh on GitHub Pages

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
