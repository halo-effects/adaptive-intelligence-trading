# Incident Report: Bot Restart Cascade — 2026-05-08

**Severity**: Medium (real money lost, CSV corrupted, ~35 min downtime)  
**Root cause**: Untested restart surfaced corrupted dependency + candle replay generated real orders  
**Exchange loss**: ~$5.75 from 113 spread-reject round-trips  
**CSV damage**: 7 bad trades from startup reconciliation (need removal)

---

## Timeline (all times PDT)

| Time | Event |
|------|-------|
| 07:03 | Brett reports PENDLE showing 1 layer on dashboard |
| 07:08 | GeeGee identifies race condition bug + writes mini spec |
| 07:14 | GeeGee stops bot (PID 15608) to apply race condition fix + dashboard fix |
| 07:14 | Race condition fix applied (2 locations in `_bot_side_tp_check`) |
| 07:14 | Dashboard `seed_capital` fix applied and pushed to GitHub |
| 07:15 | First restart attempt → **CRASH**: `ImportError: cannot import name 'EQUITY_TIER_SPLITS'` |
| 07:16 | GeeGee adds local `EQUITY_TIER_SPLITS` definition |
| 07:17 | Second restart attempt → **CRASH**: `ImportError: cannot import name 'load_capital_ledger'` |
| 07:18 | GeeGee discovers `v14_capital_manager.py` was corrupted by data sync cron (commit `4c350c6ed`) |
| 07:22 | Capital manager restored from `afe65c43e`. Third restart attempt. |
| 07:22 | Bot starts successfully (PID 5696). Begins candle replay. |
| 07:22-07:28 | **113 spread-reject buy/sell round-trips** on live exchange. Each replay candle triggers a real buy at current market price, gets spread-rejected, immediately sells back. ~$5.75 lost in slippage. |
| 07:23 | Startup reconciliation records 7 trades, at least 2 bogus (ENA +638%, PENDLE -58%) |
| 07:28 | GeeGee stops bot. Damage assessment begins. |

## What Broke

### 1. Capital Manager Corruption (pre-existing)
- **Cause**: Data sync cron job (`sync_dashboard.ps1` or similar) committed a truncated version of `v14_capital_manager.py` on 2026-05-06
- **Impact**: Removed `EQUITY_TIER_SPLITS`, `load_capital_ledger`, `save_capital_ledger`, `record_ledger_transaction`, `get_ledger_summary`
- **Why it was hidden**: Bot was running in memory from before the corruption. Never restarted since.
- **Fix applied**: `git checkout afe65c43e -- trading/spot/v14_capital_manager.py`

### 2. Candle Replay Generating Real Orders
- **Cause**: `--skip-backfill` only skips historical candle fetching. When the bot restarts and catches up on missed 1h candles, it processes each one through the engine, which generates real BUY orders on the exchange.
- **Impact**: 113 spread-reject cycles. Each cycle: market buy → spread exceeds 100bps → immediate market sell. Round-trip slippage ~$0.05/trade.
- **Why this matters**: The bot was down ~35 minutes, missing ~0 candles in normal operation. But the engine replays ALL candles since the last processed timestamp, which can go back hours if candles were stale.

### 3. Bad Reconciliation Records
- **Cause**: Startup reconciliation matched exchange fills from the spread-reject churn against existing deal state
- **Impact**: 7 trades in CSV, including:
  - ENA/USDT deal 83: +$72.75 (+638.69%) — clearly wrong
  - PENDLE/USDT deal 88: -$22.65 (-58.45%) — phantom loss
- **Fix needed**: Remove all 7 trades recorded after 14:22 UTC from trades.csv

## Cleanup Required

### Step 1: Fix CSV
Remove all trades with `recorded_at > 2026-05-08T14:22:00`:
- Deal 83 ENA/USDT (+$72.75) — bogus reconciliation
- Deal 84 PENDLE/USDT (+$0.42) — may be legitimate or not
- Deal 85 PENDLE/USDT (-$0.13) — spread reject artifact  
- Deal 86 PENDLE/USDT (+$2.24) — may be legitimate or not
- Deal 87 PENDLE/USDT (+$0.28) — spread reject artifact
- Deal 88 PENDLE/USDT (-$22.65) — phantom loss
- Deal 89 TON/USDT (+$0.37) — may be legitimate or not

### Step 2: Verify Exchange State
- Check actual open positions on Aster
- Compare to bot's state expectations
- Reconcile any orphaned orders

### Step 3: Restart Bot
- Verify imports work: `python -c "from trading.spot.run_v14_portfolio_live_aster import V14PortfolioLiveAster; print('OK')"`
- Start bot
- Monitor first 5 minutes for normal behavior
- Verify no candle replay issues

### Step 4: Fix Data Sync
- Identify which cron job overwrites `v14_capital_manager.py`
- Add it to `.gitignore` for data sync, or exclude from the sync commit pattern

## Procedures to Add

1. **Pre-restart import test**: Before stopping a running bot, run `python -c "from trading.spot.run_v14_portfolio_live_aster import V14PortfolioLiveAster"` to verify the code loads.
2. **Never batch unrelated fixes**: Dashboard changes (HTML only, no restart needed) should be deployed separately from code changes (require restart).
3. **Wait for spec approval**: Don't implement fixes until the spec is explicitly approved.
4. **Candle replay guard**: Consider adding a guard that skips real order placement during candle catch-up (detect if candle timestamp is >N minutes old).

## Lessons Learned

- A "simple fix" that requires a restart is never simple if you haven't verified the full dependency chain
- Data sync cron jobs that commit Python source files are a ticking time bomb
- Candle replay after a restart generates real orders — this needs a guard
- The bot being "in memory" masked a broken dependency for 2+ days
