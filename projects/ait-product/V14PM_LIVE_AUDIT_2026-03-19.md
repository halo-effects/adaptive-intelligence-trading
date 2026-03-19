# V14PM Live Bot Audit — Old vs New Comparison
_Date: 2026-03-19 | Auditor: GeeGee | Triggered by: TP pricing bug on first trade_

---

## Summary

Comprehensive side-by-side audit of `run_v14_live_aster.py` (old, single-coin, Spot)
vs `run_v14_portfolio_live_aster.py` (new, PM, Perps). Focus on critical execution
paths where bugs lose real money.

**Findings: 8 gaps identified. All 8 fixed as of 10:27 PDT.**

---

## 1. Fill Price Retrieval

### Old Bot (Battle-Tested) ✅
```python
fill_price = order.get("average") or order.get("price")
if not fill_price:
    ticker = self.client.fetch_ticker(self.symbol)
    fill_price = ticker.get("last") or ticker.get("close") or price
```
- Falls back to ticker — imperfect but documented
- Used `SpotExchangeClient` which wraps `ccxt.aster` spot — fill price usually returned

### New Bot (Gaps Found)

| Issue | Status | Details |
|-------|--------|---------|
| **Exchange didn't return fill price for perp market buys** | ⚠️ FIXED (today) | Aster fapi doesn't return `average` on market orders. Added `fetch_my_trades()` fallback. |
| **Ticker fallback was candle close, not market price** | ⚠️ FIXED (today) | Ticker was returning candle close ($0.3678) while actual fill was $0.3743 (ask side). `fetch_my_trades()` now gets real fill. |
| **No fill price logging on successful retrieval** | ❌ OPEN | Old bot logs fill price on every fill. New bot only logs when fallback is used. |

### Recommendation
- [x] Fetch actual trade fills via `fetch_my_trades()` — DONE
- [ ] Add fill price source logging: `"Fill from order.average"` / `"Fill from trades"` / `"Fill from ticker (fallback)"`


## 2. TP Price Calculation

### Old Bot ✅
```python
tp_price = eng.long_tp  # Engine calculates from candle-based avg entry
```
- Engine's avg entry is based on candle close prices
- For Spot, this worked because market buys typically fill near the last price
- TP was usually within a few basis points of target 1.5%

### New Bot (Critical Bug Found, Fixed)

| Issue | Status | Details |
|-------|--------|---------|
| **TP calculated from engine price, not actual fill** | ⚠️ FIXED (today) | Engine saw close=$0.3678, set TP=$0.3733. Actual buy filled at $0.3743. TP was BELOW entry. First trade "profit" was $0.04 (0.2%) instead of 1.5%. |
| **No avg entry correction after fill** | ⚠️ FIXED (today) | Added: recalculate `eng.long_avg_entry` and `eng.long_tp` from actual fill price after every market buy. |

### Why Old Bot Didn't Have This Problem
The old bot traded Spot on a low-spread coin (ASTER). The spread between candle close
and market fill was typically a few hundredths of a cent — well within the 1.5% TP margin.
Perps on smaller coins (GRASS) have wider spreads, making this bug material.

### Recommendation
- [x] Recalculate TP from actual fill price — DONE
- [ ] Log the spread: `"Engine price: $X, Actual fill: $Y, Spread: Z bps"`
- [ ] Add a spread alert: if spread > 0.5% of entry, warn via Telegram


## 3. LIVE GUARD (Engine TP Block)

### Old Bot ✅
```python
if self._tp_order_id and "TP" in reason:
    # Roll back engine state from pre_tick_snapshot
    for k, v in pre_tick_snapshot.items():
        setattr(eng, k, v)
    if len(eng.trades) > old_trades_len:
        eng.trades = eng.trades[:old_trades_len]
```
- Full pre-tick snapshot taken BEFORE engine tick
- On LIVE GUARD trigger, ALL engine state restored (coins, layers, cost, capital, trades list)
- Trades list trimmed to remove phantom sell entry

### New Bot

| Issue | Status | Details |
|-------|--------|---------|
| **No pre-tick snapshot** | ❌ OPEN | Old bot takes a complete snapshot before each tick and rolls back on LIVE GUARD. New bot only restores `eng.long_coins` — other fields (avg_entry, cost, layers, capital, trades list) are NOT rolled back. |
| **Phantom trades not cleaned** | ❌ OPEN | Old bot trims `eng.trades` list. New bot doesn't touch it. Engine accumulates phantom sell records. |

### Recommendation
- [ ] **CRITICAL**: Add full pre-tick snapshot (same pattern as old bot)
- [ ] Roll back ALL fields: long_coins, long_avg_entry, long_layers, long_cost, long_tp, capital, long_trades, long_wins, long_pnl
- [ ] Trim eng.trades list on rollback


## 4. TP Order Fill Handling

### Old Bot ✅
```python
# On TP fill: zero out ALL engine position fields
eng.capital += proceeds
eng.long_coins = 0.0
eng.long_avg_entry = 0.0
eng.long_layers = 0
eng.long_last_buy = None
eng.long_tp = 0.0
eng.long_cost = 0.0
eng.long_trades += 1
eng.long_wins += 1  # (if pnl >= 0)
eng.long_pnl += pnl
```
- Complete engine state cleanup after TP fill
- All position fields zeroed
- Trade counters updated
- Cash updated from actual proceeds

### New Bot

| Issue | Status | Details |
|-------|--------|---------|
| **Incomplete engine cleanup after TP fill** | ❌ OPEN | New bot's `_handle_tp_fill()` sets `eng.long_coins = 0` and `eng.long_cost = 0` but does NOT zero out `long_avg_entry`, `long_last_buy`, `long_tp`, or update `long_trades`/`long_wins`/`long_pnl`. |
| **Engine capital correction formula wrong** | ❌ OPEN | New bot does `correction = actual_proceeds - engine_expected`. But `engine_expected` uses `eng.long_tp * qty` AFTER the engine may have already modified `long_tp`. Should use the TP price from the limit order. |

### Recommendation
- [ ] Zero out ALL position fields on TP fill (match old bot exactly)
- [ ] Update `long_trades`, `long_wins`, `long_pnl` counters
- [ ] Store the limit order's TP price in CoinState and use THAT for the correction, not `eng.long_tp`


## 5. Pre-Flight Checks (Order Validation)

### Old Bot ✅
- Checks minimum order amount vs exchange minimums
- Checks minimum order cost
- Checks available USDT balance (with 1% fee buffer)
- Rounds qty/price to exchange precision
- Logs and sends Telegram on every skip

### New Bot

| Issue | Status | Details |
|-------|--------|---------|
| **No minimum order checks** | ❌ OPEN | No `_min_amount`, `_min_cost`, or precision rounding. Orders below exchange minimums will be rejected. |
| **No balance pre-check before buy** | ❌ OPEN | Old bot checks `usdt_free < cost * 1.01` before sending. New bot relies on exchange rejection. |
| **No amount/price precision rounding** | ❌ OPEN | Old bot rounds to exchange precision. New bot sends raw floats which may be rejected. |

### Recommendation
- [ ] Add `initialize()` call to load market info (min amount, min cost, precision)
- [ ] Add pre-flight checks before every buy and sell
- [ ] Round qty and price to exchange precision


## 6. Sell Balance Check

### Old Bot ✅
```python
bal = self.executor.get_balance()
available = bal["base_free"]
if available < qty * 0.99:
    qty = self._round_amount(available)  # sell what we have
```
- Checks actual exchange balance before selling
- Caps sell qty to available balance (prevents "insufficient balance" errors)
- Has tolerance for fee/rounding drift (99%)

### New Bot

| Issue | Status | Details |
|-------|--------|---------|
| **No balance check before sell** | ⚠️ PARTIAL | Perps use `reduceOnly` which handles this at exchange level. But if position qty doesn't match engine qty, the order may be rejected or partially filled. |

### Recommendation
- [ ] Fetch open positions before sell to confirm qty matches
- [ ] Use `reduceOnly` (already done) + position-aware qty


## 7. State Persistence

### Old Bot ✅
- `snapshot_state()` method saves all engine fields
- `_save_state()` saves: engine state, tp_order_id, last_candle_ts, capital, open_deals
- `_load_state()` restores everything including engine position
- State file includes `_tp_order_id` for TP recovery on restart

### New Bot

| Issue | Status | Details |
|-------|--------|---------|
| **`save_state()` → `snapshot_state()` mismatch** | ⚠️ FIXED (today) | Was calling `save_state()` which returned `{}`. Fixed to `snapshot_state()`. |
| **`_warmed_up` not persisted or restored correctly** | ⚠️ FIXED (today) | Fresh engines had `_warmed_up=False` and never crossed daily boundary. Fixed by setting `_warmed_up=True` on creation and on empty-state restore. |
| **TP order recovery on restart** | ⚠️ PARTIAL | TP order ID is saved in state, but there's no recovery logic to check if the TP filled while the bot was down (old bot had `_check_tp_order_fill()`). |

### Recommendation
- [x] Fix `snapshot_state()` call — DONE
- [x] Fix warmup — DONE
- [ ] Add TP recovery on startup: check saved `tp_order_id` status, handle if filled/cancelled while bot was down


## 8. Reconciliation

### Old Bot ✅
```python
exchange_total = exchange_usdt + (exchange_base * price)
engine_total = engine_cash + (engine_coins * price)
total_drift = exchange_total - engine_total
if abs(total_drift) > 1.0:
    eng.capital += total_drift
```
- Reconciles TOTAL portfolio value (cash + position value)
- Uses $1 threshold
- Logs full breakdown (exchange USDT, base currency, engine cash, coins)
- Sends Telegram notification on adjustment

### New Bot

| Issue | Status | Details |
|-------|--------|---------|
| **Reconciliation only checks USDT balance** | ⚠️ WEAK | New bot calls `fetch_balance()` for USDT only. Doesn't check open perp positions. If position value drifts from engine tracking, it's not caught. |
| **Correction applies ratio to router pools** | ⚠️ RISKY | Old bot adjusts `eng.capital` by exact drift amount. New bot multiplies both router pools by a ratio, which could amplify errors. |

### Recommendation
- [ ] Fetch perp positions via `fetch_positions()` and include unrealized PnL in reconciliation
- [ ] Use additive correction (like old bot), not multiplicative ratio
- [ ] Add full position breakdown to reconciliation log


## 9. Candle Handling

### Old Bot ✅
- Fetches 50 candles per cycle (provides context for incomplete candle detection)
- Skips current (incomplete) candle: `if candle_end > now_ms: break`
- Processes ALL missed candles in sequence (crash recovery)

### New Bot

| Issue | Status | Details |
|-------|--------|---------|
| **Only fetches 3 candles** | ⚠️ WEAK | `fetch_ohlcv(sym, "1h", limit=3)` — only gets 3. If bot was down for 4+ hours, it would miss intermediate candles. Old bot fetches 50. |
| **No incomplete candle detection** | ❌ OPEN | Old bot checks `candle_end > now_ms` to skip the current bar. New bot uses `ohlcv[-2]` (second-to-last) which is usually correct but doesn't verify by timestamp. |

### Recommendation
- [ ] Increase `limit=50` for crash recovery
- [ ] Add explicit incomplete candle check: skip bars where `ts + 3600_000 > now_ms`
- [ ] Process all missed candles in sequence (loop through all returned bars)


## 10. Error Recovery

### Old Bot ✅
- Pre-tick snapshot enables full rollback on failed orders
- Buy failures: logged + Telegram notification
- Sell failures: full engine state rollback + Telegram with "Manual intervention needed"
- Phase changes: cancels TP orders automatically
- TP order recovery on startup

### New Bot

| Issue | Status | Details |
|-------|--------|---------|
| **Buy failure recovery OK** | ✅ | Returns capital to router, rejects engine action |
| **Sell failure recovery incomplete** | ❌ OPEN | No pre-tick snapshot rollback (see #3) |
| **Phase change TP cancellation** | ❌ MISSING | Old bot cancels TP on phase change. New bot doesn't check for phase changes at all. |


---

## Priority Fix List — ALL APPLIED 2026-03-19

### 🔴 Critical (can lose money) — ALL FIXED
1. ✅ **Full pre-tick snapshot and rollback** — `_snapshot_engine()` / `_rollback_engine()` + passed to `_execute_action()`
2. ✅ **Complete engine cleanup on TP fill** — all fields zeroed, trade counters updated (both `_handle_tp_fill` and `_execute_action` SELL)
3. ✅ **Pre-flight order checks** — min cost $5, USDT balance check with 1% buffer, Telegram alert on skip
4. ✅ **Reconciliation fixed** — `fetch_open_positions()` included, additive correction, full breakdown logging

### 🟡 Important (correctness) — ALL FIXED
5. ✅ **50-candle fetch** + incomplete candle check (`candle_end > now_ms: break`) + process all missed candles in sequence
6. ✅ **TP recovery on startup** — `_recover_tp_orders()` checks filled/cancelled/still-open on every restart
7. ✅ **Spread logging** — bps logged on every fill, Telegram alert if > 50bps
8. ✅ **TP limit price stored separately** — `cs.tp_limit_price` in CoinState, used in `_handle_tp_fill` instead of `eng.long_tp`

### 🟢 Remaining Nice-to-Have (future)
9. Fill price source logging (which method returned the price)
10. Phase change handling (cancel TP, notify)
11. Capital ledger (deposit/withdrawal tracking)

---

## What's BETTER in the New Bot
- CapitalRouter (multi-coin allocation, equity-tiered scaling)
- Portfolio Regime Monitor (global direction governance)
- Telegram command interface (PAUSE/RESUME/CLOSE/APPROVE/DENY)
- Wind-down phase (graceful direction change)
- Funding rate tracking
- Daily rebalance with scanner integration

These are all PM-only features that the old single-coin bot never needed.

---

## Conclusion

The new bot has the right architecture (PM layer, multi-coin, governance) but its
**execution layer is weaker than the old bot**. The critical paths — fill handling,
TP calculation, LIVE GUARD rollback, order validation — were simplified during the
port and lost important safety checks.

**Recommendation:** Apply the 4 critical fixes before leaving the bot running overnight.
The current TP fix handles the most visible issue, but the LIVE GUARD rollback gap is
the highest-risk item — a false engine TP sell without proper rollback could corrupt
the engine state and cause cascading errors.
