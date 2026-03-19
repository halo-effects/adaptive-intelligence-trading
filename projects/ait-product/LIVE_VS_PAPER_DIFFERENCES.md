# Live vs Paper Trading: Architecture Differences
_Last updated: 2026-03-17_

This document captures the differences between live and paper trading bot configurations,
and the production requirements for any live trading deployment.

---

## Shared Engine (identical)

Both live and paper bots use the same core engine stack:
- **V14 Lifecycle Engine:** `trading/spot/v14_lifecycle_engine.py`
- **V14 DCA Engine:** `trading/spot/engine/v14_dca_engine.py`
- **V13 Signal Pack:** `trading/spot/engine/v13_signals.py`
- **TP Fill Model:** Checks candle high (long) / low (short), fills at TP price

The engine produces **actions** (BUY/SELL). What differs is how those actions are executed.

---

## Key Differences

### Order Execution

| Aspect | Paper | Live |
|--------|-------|------|
| BUY execution | Simulated (engine updates internal state) | Real market order via exchange API |
| SELL/TP execution | Simulated at TP price | Resting limit sell order on exchange; market sell fallback |
| Fill price | TP price (limit order simulation) | TP price (limit sell) or exchange fill price (fallback market sell) |
| Slippage | None (simulated) | None for limit sell (fills at TP); real for market sell fallback |
| Fees | Simulated (maker/taker rates) | Real exchange fees |

### Resting Limit Orders (IMPLEMENTED on Aster live bot — 2026-03-17)

| Aspect | Paper | Live (Aster) |
|--------|-------|--------------|
| TP order type | Engine-internal check | Resting limit sell on exchange (primary) + engine detection (fallback) |
| TP reliability | Depends on bot running | Exchange handles it automatically; bot syncs on next poll |
| DCA layer order | Engine-internal check | Engine detects → market buy |
| TP order recovery | N/A | `_tp_order_id` in `state.json`; recovered or replaced on startup |

**Dual approach:** Limit sell placed at TP price after every BUY fill. If the bot is
down or API is unavailable, the exchange fills the order independently. On bot recovery,
engine syncs to exchange order status. Candle-based detection remains as fallback.

**For `run_v14_portfolio_live.py`:** Follow the same pattern as `run_v14_live_aster.py`
(already proven). See `CLOUD_MIGRATION_GUIDE.md` item 13.

### Balance & Equity

| Aspect | Paper | Live |
|--------|-------|------|
| Equity source | Engine-computed (capital + position value) | Exchange API balance (USDT + base asset value) |
| Cash source | Engine `capital` field | Exchange USDT balance |
| Realized PnL | Engine counters (drift on restart) | CSV-as-truth (trades.csv is the ledger) |
| Reconciliation | None (engine is truth) | Periodic exchange balance check, startup reconciliation |

### Capital Management

| Aspect | Paper | Live |
|--------|-------|------|
| Initial capital | CLI `--capital` flag (fixed) | `capital_ledger.json` → `current_capital` |
| Deposits/withdrawals | N/A | Tracked in `capital_ledger.json` with auto-detection |
| PnL% calculation | `(equity - capital) / capital` | `(equity - current_capital) / current_capital` |

### Process Management

| Aspect | Paper | Live |
|--------|-------|------|
| PID lock | V14-ETF and V14-PM have it, V14 paper doesn't | ✅ Implemented (bot.pid) |
| Scheduled task | At boot/login | At boot (`V14LiveAster`) |
| Crash recovery | Task restarts, state.json restore | Task restarts, state.json restore + exchange reconciliation |
| Duplicate prevention | PID lock (where implemented) | PID lock + `MultipleInstances: IgnoreNew` on task |

### Data Sources

| Aspect | Paper | Live |
|--------|-------|------|
| 1h candles | Hyperliquid perp API | Aster spot API |
| Daily candles | Signal pack (candles.db) | Signal pack (candles.db) — same |
| CFGI | CFGI API (hourly poll) | CFGI API (hourly poll) — same |
| Trade history | Internal trades list + trades.csv | Exchange trade history + trades.csv |

### Safety Gates

| Aspect | Paper | Live |
|--------|-------|------|
| `--confirm` flag | Not required | **Required** (refuses to trade without it) |
| `--dry-run` mode | N/A | Available (logs orders without executing) |
| Sell failure rollback | N/A | Engine state rolled back if exchange sell fails |
| Max order cap | 30% of capital per order | 30% of capital per order — same |

---

## Production Checklist (for any live deployment)

Before deploying a live trading bot:

- [ ] `--confirm` flag required in scheduled task
- [ ] PID lock implemented and tested
- [ ] Capital ledger initialized with seed capital
- [ ] Startup reconciliation enabled (exchange balance vs engine state)
- [ ] Periodic reconciliation enabled (drift detection)
- [ ] CSV-as-truth for realized PnL
- [ ] Exchange balance used for equity (not engine-computed)
- [ ] Sell failure rollback implemented
- [ ] Telegram notifications for: trades, phase changes, errors, drift alerts, deposits
- [ ] State persistence (engine_state.json / state.json) with atomic writes
- [ ] `--dry-run` mode available for testing
- [ ] GitHub PAT valid for dashboard sync
- [x] Resting limit orders for TP *(implemented on Aster bot 2026-03-17 — see CLOUD_MIGRATION_GUIDE.md item 13)*

---

## Current Live Deployment

| Parameter | Value |
|-----------|-------|
| Exchange | Aster DEX (spot) |
| Symbol | ASTER/USDT |
| Capital | $340 (seed $300 + deposit $40) |
| Profile | High (12 layers, 1.5% TP, 1.5% deviation) |
| Leverage | 1.0x (spot, no leverage) |
| Runner | `trading/spot/run_v14_live_aster.py` |
| Scheduled Task | `V14LiveAster` (at boot) |
| Status file | `trading/spot/live/v14/status.json` |
| Capital ledger | `trading/spot/live/v14/capital_ledger.json` |
| Dashboard | https://halo-effects.github.io/adaptive-intelligence-trading/d-984ae0d4ab9dc1a5.html (V14-PM Live) |
| TP execution | Resting limit sell on exchange (primary) + candle-based detection (fallback) — implemented 2026-03-17 |
