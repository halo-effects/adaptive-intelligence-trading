# V14 Live Trading — Aster Exchange

## Status: SETUP (awaiting API keys)

**Symbol:** ASTER/USDT (spot)  
**Capital:** $300 USDT  
**Profile:** High (BO=40%, Dev=1.5%, Mult=1.5x, 12 layers, TP=1.5%)  
**Phase:** LONG_DCA (spot longs only; futures shorts available when needed)  
**Engine:** V14 DCA-only with ROUTER v2 signal stack  

## Files

- `run_v14_live_aster.py` — Main runner (in `trading/spot/`)
- `.env.template` — Copy to `.env` and add API keys
- `state.json` — Engine state (auto-generated)
- `status.json` — Dashboard status (auto-generated)
- `trades.csv` — Trade log (auto-generated)
- `bot.log` — Full log output

## Quick Start

```powershell
# 1. Copy .env template and add your keys
Copy-Item "trading\spot\live\v14\.env.template" "trading\spot\live\v14\.env"
# Edit .env with your Aster API key and secret

# 2. Test connectivity
python -m trading.spot.run_v14_live_aster --test

# 3. Dry run (logs orders, doesn't execute)
python -m trading.spot.run_v14_live_aster --dry-run

# 4. Go live
python -m trading.spot.run_v14_live_aster --confirm

# Resume from saved state (after restart)
python -m trading.spot.run_v14_live_aster --confirm --skip-backfill

# Fresh start (no historical backfill)
python -m trading.spot.run_v14_live_aster --confirm --fresh
```

## Architecture

1. **Signal Backfill**: Runs V14 engine on historical ASTER data (Oct 2025+) to build signal context (StochRSI, structure, etc.)
2. **Position Reset**: After backfill, positions are cleared — only real exchange orders create positions
3. **Live Loop**: Every 65s, fetches 1h candles from Aster, ticks V14 engine, executes resulting BUY/SELL as market orders
4. **Reconciliation**: Every 5 min, compares engine state vs actual Aster balances; alerts on >10% drift
5. **Telegram**: All orders and events prefixed `[V14-LIVE]`

## Safety Features

- `--confirm` flag required for real orders
- `--dry-run` mode logs everything without executing
- Balance check before every buy
- Min order size validation
- Balance reconciliation with drift alerts
- Graceful shutdown (SIGINT/SIGTERM)
- All orders logged to Telegram
