# V14PM Live Bot — Change Control Log
_Created: 2026-03-20 | Renamed from V14PM_UNIFIED_AUDIT.md: 2026-03-24_
_Source: Initial audit of `run_v14_portfolio_live_aster.py` against `run_v14_live_aster.py`_

---

## Summary

Production change control for V14PM Live Bot. Tracks all code changes, bug fixes,
and architectural decisions applied to the live trading system. Originally a 20-path
audit comparing the PM bot against the battle-tested single-coin bot.

**Initial audit: 17 of 20 items resolved. 3 remaining (all P2 — operational, not trade-blocking).**
**Post-audit changes: 4 production fixes applied (2026-03-21 through 2026-03-24).**

---

## ✅ Resolved Items

### 1. Fill Price Retrieval — FIXED
- Added `fetch_my_trades()` fallback when Aster doesn't return fill price on market orders
- Spread logging on every fill (bps), Telegram alert if >50bps

### 2. TP Price Calculation — FIXED (updated 2026-03-24)
- TP recalculated from actual **exchange entry price** after every market buy (not candle close)
- `cs.tp_limit_price` stored separately in CoinState for correction math
- **2026-03-24 fix:** `_place_tp_order()` now fetches exchange position entry price and computes TP from that, replacing the engine's candle-based TP. Previously, the engine would compute TP from the historical candle close price (e.g., $38.35), but the actual fill could be $40.31 due to spread/slippage. The old TP ($38.93) would be below entry, causing exchange rejection ("Limit price can't be lower than mark price"). Now: `TP = exchange_entry × (1 + DCA_TP_PCT)`, always above the actual entry.

### 3. LIVE GUARD (Engine TP Block) — FIXED
- Full `_snapshot_engine()` taken before every tick
- `_rollback_engine()` restores ALL fields: coins, avg_entry, layers, cost, tp, capital, trades list
- Phantom trades trimmed on rollback

### 4. TP Order Fill Handling — FIXED
- `_handle_tp_fill()` adds full `actual_proceeds` to engine capital
- ALL position fields zeroed (coins, avg_entry, layers, last_buy, tp, cost)
- Trade counters updated (long_trades, long_wins, long_pnl)
- Engine capital reset to `cs.allocated_capital` after every TP fill (prevents paper-capital depletion)

### 5. Pre-Flight Checks — FIXED
- Min cost $5 check before every order
- USDT balance check with 1% fee buffer
- Telegram alert on order skip

### 6. Reconciliation — FIXED (startup + periodic)
- **Startup**: `_reconcile_with_exchange()` fetches USDT balance + open perp positions, additive correction
- **Periodic**: `_periodic_reconcile()` runs every 5 minutes, resets idle engine capital to allocation
- Both use `fetch_open_positions()` for position-aware drift calculation

### 7. Engine Capital Management — FIXED
- Reset on startup when no position open (in `_load_state`)
- Reset after every TP fill (`eng.capital = cs.allocated_capital`)
- Reset by periodic reconciliation when engine idle
- `live_mode` flag disables paper-trading 30% order cap in inner DCA engine

### 8. Candle Handling — FIXED
- Fetches 50 candles (crash recovery for up to 50 hours of downtime)
- Incomplete candle check: `candle_end > now_ms` → break
- All missed candles processed sequentially

### 9. TP Order Recovery — FIXED
- `_recover_tp_orders()` on startup: checks saved order IDs + scans exchange for orphaned orders
- Phase 1: Validates saved TP orders (filled? cancelled? still open?)
- Phase 2: Scans ALL open sell orders on exchange, adopts matching ones, cancels strays

### 10. TP Order Quantity — FIXED
- `_place_tp_order()` fetches exchange position size via `fetch_open_positions()`
- Falls back to engine qty only if position fetch fails
- Logs when exchange qty differs from engine qty

### 11. Phase Change Handling — FIXED
- After candle processing loop, compares `current_phase` vs `prev_phase`
- If changed: cancels stale TP order, clears `cs.tp_order_id` and `cs.tp_limit_price`

### 12. PID / Instance Lock — FIXED
- `msvcrt.locking()` file-based advisory lock (Windows)
- Second instance immediately exits: "Another V14PM instance is already running"
- Lock released in `finally` block; auto-released on crash (OS reclaims file handle)

### 13. Exchange Client Timeout — FIXED
- ccxt config includes `"timeout": 15000`

### 14. Equity Computation — FIXED
- `usdt_total + unrealized_pnl` (matches old bot pattern)
- `cash` and `exchange_balance` fields in status.json

### 15. cash_available Parameter — FIXED
- Engine tick now receives `cash_available=cs.allocated_capital` (was 0)

### 16. Error Handling — OK
- Main loop `try/except` with 10s backoff (old bot used 30s)
- Pre-tick snapshot enables rollback on any failure in the action execution path

### 17. Sell Failure Rollback — OK
- Full `_rollback_engine()` on sell/TP failure
- Phantom trade trimming included

---

## ✅ Previously Remaining Items (all resolved)

### 18. Cash Tracking (Double-Entry) — SUPERSEDED by Exchange-as-Truth
**Original gap:** Independent `self.cash` tracker alongside `eng.capital` for sanity checking.

**Resolution:** The exchange-as-truth architecture (2026-03-21) + periodic reconciliation every 5 minutes against exchange balance makes double-entry redundant. The old bot needed it because it had no exchange-side reconciliation — the PM bot syncs positions and balances directly from Aster every cycle.

### 19. Capital Ledger — ✅ IMPLEMENTED (Upgrade 1: Dynamic Capital, 2026-03-24)
**Original gap:** Capital was CLI arg only, no deposit/withdrawal tracking.

**Resolution:** Full implementation in Upgrade 1:
- `capital_ledger.json` — persistent ledger tracking all capital changes with timestamps and notes
- `load_capital_ledger()` / `save_capital_ledger()` / `record_ledger_transaction()` — ledger API
- `--deposit` and `--withdraw` CLI flags at launch
- `DEPOSIT <amount>` and `WITHDRAW <amount>` Telegram commands (live, no restart needed)
- `CAPITAL` Telegram command — shows current capital, deposits, withdrawals, transaction history
- `_tracked_capital` — survives restarts via state.json
- Safety: withdrawal blocked if it would drop capital below total invested

### 20. Deposit/Withdrawal Detection — ✅ IMPLEMENTED (Upgrade 1: Dynamic Capital, 2026-03-24)
**Original gap:** No auto-detection of deposits/withdrawals; large deposits triggered reconciliation warnings.

**Resolution:** `_detect_capital_changes()` runs every cycle:
- Compares exchange balance to `_tracked_capital`
- Distinguishes drift (small, ignored) from deposits/withdrawals (exceed `CAPITAL_DRIFT_MIN_PCT` threshold)
- Auto-records transaction to `capital_ledger.json`
- Sends Telegram alert with old→new capital and drift percentage
- Safety: auto-detected withdrawals that would drop below invested are rejected with explanation
- `router.resize()` called automatically to reallocate across pools

---

## Architecture Improvements (PM-Only Features)

These are capabilities the new bot has that the old bot never had:

| Feature | Description |
|---------|-------------|
| **CapitalRouter** | Multi-coin allocation, equity-tiered scaling, 90/10 active/reserve split |
| **Portfolio Regime Monitor** | Global direction governance across all 50 coins |
| **Telegram Commands** | PAUSE/RESUME/CLOSE/APPROVE/DENY |
| **Wind-Down Phase** | Graceful direction change (freeze grids, keep TPs) |
| **Funding Rate Tracking** | Per-coin cumulative funding in PnL |
| **Daily Rebalance** | Scanner-driven coin rotation with trend multipliers |
| **Order Dedup Guard** | 30s window prevents duplicate buys per symbol |
| **Rebalance Timing Guard** | 60s minimum between rebalances |
| **File-Based Instance Lock** | OS-level advisory lock (not just PID file) |

---

## Audit Trail

| Date | Action | Items |
|------|--------|-------|
| 2026-03-19 AM | Initial 8-gap audit | Fill price, TP calc, LIVE GUARD, TP cleanup, pre-flight, reconciliation, candles, TP recovery |
| 2026-03-19 AM | All 8 gaps fixed | Applied to `run_v14_portfolio_live_aster.py` |
| 2026-03-19 PM | 20-path comparison audit | Cross-referenced every critical path against old bot |
| 2026-03-19 PM | 3 dedup/sizing guards added | Order dedup (30s), rebalance timing (60s), engine capital sync |
| 2026-03-19 PM | File lock added | `msvcrt.locking()` replaces PID-only lock |
| 2026-03-19 PM | 30% cap removed for live mode | `live_mode` flag on inner DCA engine |
| 2026-03-19 PM | Phase change handling added | Cancels stale TP on phase transition |
| 2026-03-19 PM | cash_available fixed | Passes `cs.allocated_capital` instead of 0 |
| 2026-03-20 AM | Unified audit created | Consolidated both docs, verified all fixes in code |
| 2026-03-20 AM | **Candle replay bug fixed** | `last_candle_ts` set to `now` (not 0) after TP fill and fresh engine creation. Prevents historical candle replay generating real orders. |
| 2026-03-21 AM | **State persistence bug fixed** | BUY rejections now use pre-tick snapshot rollback instead of trade-history-dependent `reject_action()`. Trade history is empty after restore, causing silent rollback failures and engine state corruption. |
| 2026-03-21 AM | **Startup rebalance guard** | Skip initial `_do_rebalance()` when restoring from saved state. Prevents overwriting restored engine values before reconciliation runs. |
| 2026-03-24 PM | **TP price exchange-as-truth** | `_place_tp_order()` now computes TP from actual exchange entry price instead of engine's candle-based TP. Fixes exchange rejection when spread causes candle price ≠ fill price. Affected HYPE/USDT ($38.93 TP rejected, actual entry $40.31) and TAO/USDT ($265.98 TP rejected, actual entry $336.76). |
| 2026-03-24 PM | **Multi-coin scaling live** | Scanner automatically picked HYPE and TAO at midnight UTC rebalance. Tier system confirmed: 3 coins at $340 equity, 90/10 split. TP recovery successfully placed orders for both new coins after fix. |
| 2026-04-09 PM | **Insufficient USDT alert throttle** | `_execute_action()` BUY path: Telegram alert for insufficient balance now throttled to once per coin per hour (was every tick). Prevents alert spam when bot is cash-starved. Balance check itself still runs every time (exchange-as-truth). |
| 2026-04-09 PM | **Sell guard — no exchange position** | `_execute_action()` SELL path: Before executing any sell, fetches `fetch_open_positions()` and skips if no position exists on exchange. Prevents "ReduceOnly Order is rejected" errors when engine generates phantom BUY+SELL pairs during candle catch-up but the BUY was rejected (no cash). Engine state rolled back via `reject_action()`. |
| 2026-04-09 PM | **SELL rollback in reject_action()** | `v14_lifecycle_engine.py`: `reject_action()` now supports SELL action type. Reverses the engine's TP credit (capital, coins, avg_entry, layers, pnl, wins) when a sell is rejected due to no exchange position. Previously only BUY and SHORT_OPEN were supported. |
| 2026-04-09 PM | **Zero-guard: capital manager total_score** | `v14_capital_manager.py`: Added `if total_score <= 0: return {}` before proportional allocation loop. Prevents ZeroDivisionError if all scanner coins have 0 adjusted score. Found in Phase 1 static analysis audit. |
| 2026-04-09 PM | **Zero-guard: DCA engine price** | `v14_dca_engine.py`: Added `if price <= 0: return` before `coins = order / price` in both long and short DCA entry paths. Prevents ZeroDivisionError from bad candle data (price=0). Found in Phase 1 audit. |
| 2026-04-09 PM | **Atomic write: cycle_scanner.json** | `v14_cycle_scanner.py`: Scanner output now writes to `.tmp` then renames, matching the atomic write pattern used by state.json and status.json. Prevents bot reading half-written JSON during rebalance. Found in Phase 1 audit. |
| 2026-04-09 PM | **status.json: added halted + max_drawdown_pct** | `_write_status()`: Added `halted` (true when PAUSED or WIND_DOWN) and `max_drawdown_pct` (current equity drawdown from capital). Both fields expected by dashboard but missing. Found in Phase 2 integration audit. |
| 2026-04-09 PM | **.env.template corrected** | Updated `.env.template` to reflect actual Aster bot credentials (`ASTER_API_KEY`/`ASTER_API_SECRET`). Removed stale Hyperliquid keys. Corrected CLI launch command to match current bot. Found in Phase 2 integration audit. |
| 2026-04-09 PM | **Arch doc: DCA_BO_PCT corrected 40%→30%** | Architecture doc §5.2 and production config table incorrectly stated base order = 40%. Actual `DCA_BO_PCT = 0.30`. Dashboard HTML BO display also corrected. Found in Phase 3 accuracy audit. |
| 2026-04-09 PM | **Arch doc: DCA_MAX_LAYERS clarified** | Architecture doc §5.2 clarified: default `DCA_MAX_LAYERS = 8`, High profile overrides to 12. Removed incorrect `DCA_MAX_ORDERS` reference. Found in Phase 3 accuracy audit. |
| 2026-04-09 PM | **Arch doc: leverage persistence gap documented** | Added note to safety features table: `_leverage_set` is not persisted to state.json. On restart with no open positions, leverage re-verified at next trade entry. Found in Phase 3 accuracy audit. |
| 2026-04-10 PM | **CRITICAL: False TP bug fixed in lifecycle engine** | `v14_lifecycle_engine.py`: (1) Removed daily high/low from `_run_daily_tick()`'s DCA tick calls — daily tick now handles signals/phase transitions only. (2) Removed "Live TP catch-up" block entirely. (3) Moved hourly DCA grid tick to run on ALL candles (including daily boundary). Previously, the daily tick used the previous day's aggregate high against the current TP target, causing false TP fills on underwater positions. **106 of 467 TP deals (22.7%) were false, totaling $9,423 phantom PnL.** Live bot unaffected (uses exchange limit orders). See §17.8. |
| 2026-04-11 AM | **30% capital cap removed from DCA engine** | `v14_dca_engine.py`: Removed `min(order, self.capital * 0.3)` paper-only cap on both long and short sides. This cap inverted the Martingale — deeper layers got smaller instead of larger (L12=$50 vs L1=$6,000 on ZRO). Paper bot results were non-representative of live behavior. |
| 2026-04-11 AM | **Hard order block → soft cap** | `v14_dca_engine.py`: Changed `if order > self.capital: return` to `order = min(order, self.capital)` on both long and short sides. Layers now deploy remaining capital instead of refusing entirely when the Martingale formula exceeds available capital. Enables L4 to deploy the remainder of the allocation. |
| 2026-04-11 AM | **GAP-13 capital accounting fix** | `run_v14_portfolio_live_aster.py`: GAP-13 reset changed from `eng.capital = cs.allocated_capital` to `eng.capital = max(0, cs.allocated_capital - eng.long_cost)`. Previously, resetting to full allocation after each BUY let the Martingale overshoot — L1+L2+L3 could total 142% of allocation ($28.5K on a $20K alloc). Now the engine sees only what's actually left to spend. Applied to both post-BUY reset and startup state restoration. |
| 2026-04-11 AM | **Scanner parameter corrections** | `v14_cycle_scanner.py`: (1) `BO_PCT` corrected 0.40→0.30 to match engine's `DCA_BO_PCT`. (2) `TAKER_FEE` corrected 0.00025→0.00035 (Aster, not Hyperliquid). (3) SO sizing formula changed from `bo_size * 0.5 * mult^i` to `alloc * BO_PCT * mult^min(i,4)` to match engine. Scanner scores were inflated due to all three mismatches. |
| 2026-04-11 AM | **Grid architecture confirmed: 4-layer effective depth** | With honest capital accounting (alloc - invested), the DCA grid naturally fills 4 layers per coin (L1=30%, L2=31.5%, L3=26%, L4=remainder). 12-layer config was never reachable without the 30% cap's inverted sizing. Backtested over 365 days: 81.4% annual ROI on $50K (long-only), zero denied buys, 69% L1 quick cycles. Strategy validated as velocity-optimized DCA — large L1 orders cycle fast, deep layers deploy remaining capital. |
| 2026-04-11 AM | **Liquidity filter added to scanner** | `v14_cycle_scanner.py`: Added `--capital` and `--active-coins` args. Fetches 24h volume from Aster, tags coins as `TRADEABLE` or `LOW_LIQUIDITY` based on L1 order size vs 2% of daily volume. At $20K capital: 21 tradeable, 29 low-liquidity (GRASS at 28.5% of daily volume). Dashboard updated with 24h VOL column and LOW_LIQUIDITY phase pill. Scanner still scores all coins — filter only affects eligibility label. |
| 2026-04-13 PM | **Trailing stop TP — Phase 1 (Live bot)** | `run_v14_portfolio_live_aster.py`: Replaced fixed limit-sell TP with `TRAILING_STOP_MARKET` order on Aster. Trail activates at +1.5% (same as old TP level), then follows price with 0.5% callback distance. Aster handles all trailing logic natively — zero additional API calls. Feature flag `TRAILING_STOP_ENABLED` (default True) with automatic fallback to limit sell if trailing stop placement fails. New `place_trailing_stop_sell()` method on `AsterPerpClient`. CoinState extended with `tp_type`, `tp_activation_price`, `trailing_callback_pct`. `_handle_tp_fill()` logs trail bonus (extra profit above activation price). `_recover_tp_orders()` detects trailing stop type from exchange order info. status.json includes trailing fields per coin. Validated on Aster: TRAILING_STOP_MARKET with activationPrice + callbackRate confirmed working (test order 225878709). Backtest showed +95% extra profit ($6,500 on 103 trades). |
| 2026-04-13 PM | **Trailing stop TP — Phase 2 (Paper bot engine)** | `v14_dca_engine.py`: Added trailing stop simulation for paper bots. When candle high reaches TP level, trail activates and tracks peak across candles. When candle low drops 0.5% from peak, engine sells at trail trigger price. New state fields: `long_trailing_active`, `long_trailing_peak`, `short_trailing_active`, `short_trailing_peak`. Short DCA tick signature extended with `high` param for callback detection. Fee model uses taker fee for trailing exits (market order). All position reset paths (`_long_dca_close`, `_short_dca_close`, liquidation) clear trailing state. `v14_lifecycle_engine.py`: snapshot/restore updated with all 4 trailing fields. `V14Config`: `TRAILING_STOP_ENABLED=True`, `TRAILING_CALLBACK_PCT=0.5`. Live mode (`self.live_mode=True`) skips paper simulation since exchange handles the trail. |
| 2026-04-13 PM | **Trailing stop TP — Phase 3 (Dashboard + docs)** | `dashboardV14PM.html`: Position cards show "TP Activation" label with "TRAIL 0.5%" badge when `tp_type=trailing`. Header shows "🎯 Trail 0.5%" badge when any coin has trailing TP active. `V14PM_SYSTEM_ARCHITECTURE.md`: §6.8.2 rewritten for trailing stop mechanism (activation, callback, paper simulation, feature flag). Safety features table updated. |
| 2026-04-13 PM | **Tier cap enforcement bug fix** | `run_v14_portfolio_live_aster.py`: Fixed rebalance overshoot where new engines were added without checking existing active position count against tier coin cap. Added `active_count` guard in daily rebalance loop — counts coins with `long_coins > 0 or short_coins > 0`, skips new engine creation when `active_count >= tier_cap`. Increments count as each new engine is added. Bug caused 5 positions to be opened at $310 equity (3-coin tier). Existing positions drain naturally via TP; cap prevents further additions. `V14PM_SYSTEM_ARCHITECTURE.md`: Added §7.2 "Tier cap enforcement" paragraph documenting the gate logic. |

---

## Superseded Documents
- `V14PM_LIVE_AUDIT_2026-03-19.md` — merged into this doc
- `V14PM_VS_V14_LIVE_AUDIT.md` — merged into this doc

Both originals preserved for reference but this document is the canonical audit status.
