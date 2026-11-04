# HEARTBEAT.md

## Priority Checks (every heartbeat)

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
- **Capital**: Reads from DEX on startup (~$442). 3 coin slots (equity-tiered at <$500).
- **Profile**: High, **3 layers (G-SPLIT 48/32/20)**, **1.0x leverage** (no leverage), Aster Perps
- **Grid**: G-SPLIT 48/32/20 (GridModel v2.0). 3 layers, L4 removed.
- **Part A veto**: LIVE. Stale-daily guard (7d). V-4 guard deployed.
- **Regime persistence (RH-1)**: regime_events.db, append-only, fail-open.
- **TON→GRAM**: Handled in scanner+collector. V14PM picks up GRAM at runtime.
- **CHANGES 2026-07-05**: Two-tier collector, TON→GRAM, HYPE quote fix, RH-1/RH-2/RH-3 (Fable regime handoff). Arch doc v1.14.
- Check `trading/spot/live/v14pm/status.json` for bot health
- Alert if: process not running or status.json stale (>65 min)
- **PRE-FLIGHT REQUIRED before restart**: `python -c "from trading.spot.run_v14_portfolio_live_aster import V14PortfolioLiveAster; print('OK')"`
- Entry point: `python -u -m trading.spot.run_v14_portfolio_live_aster --capital 300 --confirm --skip-backfill`
- Dashboard: `docs/d-984ae0d4ab9dc1a5.html`
- **CHANGES 2026-05-16**: Orphan-TP mode active (`FORCE_CLOSE_ON_SIGNAL=False`). No forced closes on phase transition or MARKDOWN_FAIL. Positions exit via TP only. Phase-change TP cancel guards orphans.
- **CHANGES 2026-05-12**: Grid G-SPLIT 48/32/20 deployed. 3 layers, L4 removed. GridModel v2.0. Part A veto live. V-4 guard deployed. MAE tracking active.

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

## Periodic Checks (silent — do NOT message Brett with results)
- Bot health checks — auto-restart if needed, only alert on failure
- Dashboard sync health
- Cron job health — alert only if broken >24h
- **OpenClaw update check**: Run `npm view openclaw version` — if newer than `2026.7.1-2`, alert Brett (Opus 5 support). Once updated, remove this check.

## When to Alert Brett
- **Bot crash or stale** (process dead / status.json stale >65 min) — silent auto-restart first, alert only if restart fails
- **Regime change** (GLOBAL_FLIP, coin phase transition)
- **Signal alerts** (new entries, TPs hit, veto changes)
- **Morning briefing** (once daily, AM only)
- ⛔ Do NOT alert for: drawdown, routine status, periodic check results, cron health (unless broken >24h)

## When to Stay Silent (HEARTBEAT_OK)
- **Default is silent.** Only break silence for the alert categories above.
- All bots running normally → HEARTBEAT_OK
- Drawdown at any level → HEARTBEAT_OK (Brett DCA's weekly, not concerned)
- Routine health checks pass → HEARTBEAT_OK
- Late evening (after 9 PM) unless bot crash → HEARTBEAT_OK

## Governance Reminder
- Before any heartbeat action, verify it falls within Tier 0-1 permissions.
- Never initiate financial operations, external communications, or system changes from a heartbeat.
