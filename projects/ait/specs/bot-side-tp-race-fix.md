# Mini Spec: Bot-Side TP Race Condition Fix

**Date**: 2026-05-08  
**Status**: DRAFT — Pending Brett approval  
**Severity**: Medium (lost $0.30 PnL tracking, position was profitable on exchange)  
**Parent**: `bot-side-trailing-tp.md`

---

## 1. Root Cause Analysis

### What happened (PENDLE 03:01 UTC May 8)

```
Timeline:
19:00 UTC May 7 — Deal 89 opens (2 layers, different deal)
22:30 UTC May 7 — Deal 89 closes via OLD inherited trailing stop (pre-deploy code). Recorded. +$2.29.
23:00 UTC May 7 — NEW L1 buy at $1.9494 (12 coins). Safety net placed: order 334582195 (1.0% callback)
02:29 UTC May 8 — Bot-side TP ACTIVATES at $1.996
02:33 UTC May 8 — Aster API errors (ticker + order status both fail)
03:00 UTC May 8 — Candle close at $2.005. Engine detects TP but skips (exchange TP order active). ✓ Correct.
~03:00 UTC       — Safety net FIRES on exchange (price dropped 1%+ from peak $2.005)
03:01 UTC        — Bot-side TP TRIGGERS (price $1.974 < stop $2.001)
03:01:16         — place_limit_sell() → ReduceOnly Order is rejected (position already closed!)
03:01:17         — cancel_tp_order(334582195) → Unknown order sent (already filled!)
03:01:17         — create_market_sell() → ReduceOnly Order is rejected (no position!)
03:01:17         — Bot resets state. Deal NEVER recorded in CSV.
04:00 UTC        — Engine opens fresh L1 buy (new deal 90). This is the "layer 2" Brett saw.
```

### Why the spec missed this

Section 4.4 of `bot-side-trailing-tp.md` addressed the race condition between safety net and bot-side TP. It correctly identified that one of two outcomes would occur:

> 1. Limit sell fills first → bot-side detects fill, cancels safety net
> 2. Safety net fills first → `_check_tp_fills()` detects fill, cancels pending limit sell

**The spec assumed `_check_tp_fills()` would always detect the safety net fill before the bot-side TP tried to act.** This assumption was wrong because:

- `_check_tp_fills()` runs on a **65-second timer**
- `_bot_side_tp_check()` runs on a **5-second timer**
- The safety net can fire between `_check_tp_fills()` polls
- The bot-side TP's 5s poll detects the price drop first and tries to place a limit sell
- By the time it tries, the exchange has already closed the position via the safety net

**The 13:1 timing ratio (65s vs 5s) means the bot-side TP will almost always act before `_check_tp_fills()` can detect a safety net fill.** This is the opposite of what the spec assumed.

### What was lost

- **On exchange**: Position closed profitably by safety net. Estimated ~$0.30 PnL (+1.26%).
- **In CSV**: Trade never recorded. Deal counter not incremented.
- **In dashboard**: Trade invisible. Equity accounting drifts by ~$0.30.
- **In engine state**: Engine thought position was still open, then got overwritten by position sync on next cycle. Went to zero coins → fresh L1 buy at 04:00.

---

## 2. The Actual Gap

The problem is in the **limit sell failure path** of `_bot_side_tp_check()` (line ~1520):

```python
# Current code when limit sell fails:
else:
    # Limit sell placement failed -- fall back to market immediately
    logger.error(f"Bot-side TP limit sell FAILED for {sym} -- market fallback")
    if cs.tp_order_id:
        try:
            self.client.cancel_tp_order(sym, cs.tp_order_id)   # ← Also fails (already filled)
        except Exception:
            pass
        cs.tp_order_id = None
        cs.tp_limit_price = None
    result = self.client.create_market_sell(sym, eng.long_coins)  # ← Also fails (no position)
    if result and result.get("status") in ("filled", "dry_run"):
        self._handle_tp_fill(sym, cs, result)
    # Both failed. State cleaned up. Trade LOST. ← THE BUG
    cs.bot_tp_activated = False
    cs.bot_tp_peak_price = 0.0
    cs.bot_tp_trailing_stop = 0.0
```

When both the limit sell AND market sell return `ReduceOnly Order is rejected`, it means:
**The position was already closed by someone else** — which can only be the safety net.

The code should check whether the safety net filled and record that fill.

---

## 3. Proposed Fix

### Approach: Check safety net fill on `ReduceOnly` rejection

When the limit sell fails with a `ReduceOnly` rejection, before falling through to market sell, **check if the safety net order filled**. If it did, process the fill through `_handle_tp_fill()`.

### Code change (single location in `_bot_side_tp_check`)

Replace the limit sell failure path (lines ~1520-1535):

```python
                else:
                    # Limit sell placement failed
                    # Check if safety net already closed the position
                    safety_net_filled = False
                    if cs.tp_order_id:
                        try:
                            sn_result = self.client.check_order_status(sym, cs.tp_order_id)
                            if sn_result.get("filled"):
                                logger.info(
                                    f"Safety net already filled for {sym} — "
                                    f"recording fill via safety net path"
                                )
                                send_telegram(
                                    f"\u26a0\ufe0f {TG_PREFIX} <b>Safety Net Caught TP</b>\n"
                                    f"Symbol: {sym}\n"
                                    f"Bot-side limit sell rejected (position already closed).\n"
                                    f"Safety net fill: ${sn_result.get('price', 0):.6f}"
                                )
                                cs.tp_order_id = None
                                cs.tp_limit_price = None
                                cs.bot_tp_activated = False
                                cs.bot_tp_peak_price = 0.0
                                cs.bot_tp_trailing_stop = 0.0
                                self._handle_tp_fill(sym, cs, sn_result)
                                safety_net_filled = True
                        except Exception as e:
                            logger.warning(f"Safety net check failed for {sym}: {e}")

                    if not safety_net_filled:
                        # Genuine failure — fall back to market sell
                        logger.error(f"Bot-side TP limit sell FAILED for {sym} -- market fallback")
                        if cs.tp_order_id:
                            try:
                                self.client.cancel_tp_order(sym, cs.tp_order_id)
                            except Exception:
                                pass
                            cs.tp_order_id = None
                            cs.tp_limit_price = None
                        result = self.client.create_market_sell(sym, eng.long_coins)
                        if result and result.get("status") in ("filled", "dry_run"):
                            self._handle_tp_fill(sym, cs, result)
                        cs.bot_tp_activated = False
                        cs.bot_tp_peak_price = 0.0
                        cs.bot_tp_trailing_stop = 0.0
```

### Same fix in the market sell fallback path

The timeout escalation path (lines ~1410-1435) has the same gap. When `create_market_sell()` also fails with `ReduceOnly`, add the same safety net check:

```python
                    # In STEP 0 timeout path, after market sell fails:
                    result = self.client.create_market_sell(sym, eng.long_coins)
                    if result and result.get("status") in ("filled", "dry_run"):
                        self._handle_tp_fill(sym, cs, result)
                    else:
                        # Market sell also failed — check if safety net caught it
                        if cs.tp_order_id:
                            try:
                                sn_result = self.client.check_order_status(sym, cs.tp_order_id)
                                if sn_result.get("filled"):
                                    logger.info(f"Safety net caught timeout for {sym}")
                                    cs.tp_order_id = None
                                    cs.tp_limit_price = None
                                    self._handle_tp_fill(sym, cs, sn_result)
                                    continue  # Skip the error telegram
                            except Exception:
                                pass
                        # If we get here, genuine failure
                        logger.error(f"Market sell escalation FAILED for {sym}")
                        send_telegram(...)  # existing error notification
```

---

## 4. Order of Operations (Updated)

```
Main loop (every 5 seconds):
  1. _bot_side_tp_check()          ← Fast poll, places limit sells
     ├── Limit sell succeeds       → wait for fill (checked next cycle)
     ├── Limit sell ReduceOnly     → NEW: check safety net fill → record if filled
     └── Limit sell other failure  → market sell fallback
  2. _process_telegram_commands()
  3. _do_rebalance()
  4. _evaluate_regime()
  5. _check_tp_fills()             ← Every 65s, catches safety net fills
  6. _sync_positions_from_exchange() ← Every 30s
  7. _detect_capital_change()
  8. Process candles → engine ticks → execute actions
  9. _write_status()
  10. _save_state()
```

The fix ensures that step 1 can detect safety net fills **immediately** when the `ReduceOnly` rejection tells us the position is gone. We no longer depend on step 5 (65s timer) to catch it.

---

## 5. Upstream / Downstream Impact

### Upstream (what feeds into this code)
- **`client.place_limit_sell()`**: No change. Still called the same way.
- **`client.check_order_status()`**: Already used in `_check_tp_fills()`. Adding one more call per failure event (rare).
- **`_place_tp_order()`**: No change. Safety net is still placed the same way.
- **Exchange API rate**: One extra `check_order_status` call only on failure events (not per-cycle). Negligible.

### Downstream (what this code feeds into)
- **`_handle_tp_fill()`**: Already handles safety net fills (from `_check_tp_fills` path). Same result object format. No change needed.
- **`TradeTracker.on_sell()`**: Called inside `_handle_tp_fill()`. Receives fill price and qty from exchange order status. No change.
- **`trades.csv`**: Trade will be recorded with the safety net's fill price (which is a market sell at 1.0% callback). Worse than bot-side limit sell, but the trade IS recorded.
- **Dashboard**: Trade appears. Equity accounting stays correct.
- **Engine state**: `_handle_tp_fill()` resets engine state → engine correctly starts fresh L1 on next candle. No phantom state.
- **Active Pool capital**: `_handle_tp_fill()` returns proceeds to active pool. Capital rotation works correctly.

### Reporting impact
- **Trail bonus calculation**: `_handle_tp_fill()` calculates trail bonus as `(fill_price - activation_price) × qty`. Safety net fills at 1.0% callback means the "trail bonus" will be lower (or negative if price dropped past activation). This is correct — the safety net fill IS worse, and the trail bonus should reflect that.
- **Deal counter**: Incremented correctly via `_handle_tp_fill()`.
- **Win rate**: Trade PnL depends on safety net fill price. If fill was above entry, it's a win. If below, it's a loss. Both correct.

### What does NOT change
- **`_check_tp_fills()` (step 5)**: Still runs on 65s timer. If the fix in step 1 catches the fill, `cs.tp_order_id` is cleared — step 5 sees no order to check. No double-processing.
- **`_sync_positions_from_exchange()` (step 6)**: Still runs on 30s timer. After fill is recorded, engine state is reset. Position sync sees zero coins for this symbol. Correct.
- **`_recover_tp_orders()` (startup)**: Unchanged. Handles fills that happened while bot was completely down.
- **Engine candle-based TP (layer 3)**: Unchanged. Still the final fallback.

---

## 6. Files Modified

| File | Change |
|------|--------|
| `run_v14_portfolio_live_aster.py` | `_bot_side_tp_check()`: Add safety net fill check on limit sell rejection (2 locations) |

**No other files.** Single method, single file.

---

## 7. Testing

The fix is defensive — it only activates when a `ReduceOnly` rejection occurs, which means the position is already closed. There is no scenario where this check creates a false positive because:

1. `check_order_status()` returns `filled=True` only when the exchange confirms the order filled
2. `_handle_tp_fill()` is idempotent for state cleanup (all fields set to None/False/0)
3. The safety net order ID is unique per deal — can't match a stale order

**Expected behavior after fix:**
- Safety net fires → bot-side TP gets `ReduceOnly` → checks safety net → finds fill → records trade → resets state
- Telegram notification changes from 🚨 (escalation failed) to ⚠️ (safety net caught it)

---

## 8. What About the Lost Trade?

Deal between 89 and 90 is unrecoverable from the bot's perspective — the fill data was on the exchange at the time but was never captured. Options:

1. **Manual CSV entry**: Look up the fill on Aster's trade history, add a row to trades.csv with the correct fill price/qty. Would require stopping the bot.
2. **Accept the $0.30 drift**: Small amount, doesn't affect strategy decisions.

Recommendation: Accept the drift. The fix prevents recurrence.
