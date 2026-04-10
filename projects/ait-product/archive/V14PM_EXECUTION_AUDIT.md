# V14PM Live — Execution Layer Audit (Line-by-Line)
_Date: 2026-03-20 | Focus: Order processing code parity with proven old bot_

The PM bot has PM-specific code (router, multi-coin, regime, Telegram commands) that's
legitimately different. This audit focuses only on the **core execution paths** that should
work identically to the old bot.

---

## Main Loop Structure

### Old Bot ✅
```
while running:
    check_tp_order_fill()
    fetch 50 candles
    for each candle (skip incomplete, skip processed):
        snapshot engine
        tick engine → actions
        for action: execute_action()
        advance last_candle_ts
    detect phase change → cancel TP
    write status
    save state
    sleep(65s)
```

### PM Bot — DIFFERENCES FOUND

| # | Difference | Old Bot | PM Bot | Risk | Status |
|---|-----------|---------|--------|------|--------|
| 1 | **last_candle_ts reset** | Never resets. Only advances forward. | ~~Set to 0 after TP fill and fresh engine.~~ FIXED: set to `now` | **Critical** — caused 635 GRASS incident | ✅ FIXED |
| 2 | **Re-entry cooldown** | Doesn't exist. Engine naturally re-enters on next candle. | 60s cooldown timer blocks buys after TP. | **Medium** — unnecessary. Can mask bugs. | ⚠️ REMOVE |
| 3 | **Order dedup guard** | Doesn't exist. Single-process design prevents duplicates. | 30s window per symbol. | **Low** — defensive, but file lock is the real fix. | ⚠️ REVIEW |
| 4 | **Rebalance timing guard** | N/A (single coin). | 60s minimum between rebalances. | **Low** — PM-specific, probably fine. | OK |

---

## BUY Execution

### Old Bot ✅
```python
result = self.executor.execute_buy(qty, price, reason)
if filled:
    self.cash -= actual_cost
    action["price"] = result.price  # update action with actual fill
    tracker.process_actions(symbol, [action], ts)
    # Place TP using exchange balance for qty
    bal = executor.get_balance()
    tp_qty = bal["base_free"] or eng.long_coins
    tp_order_id = executor.place_limit_sell(tp_qty, eng.long_tp)
```

### PM Bot — DIFFERENCES FOUND

| # | Difference | Old Bot | PM Bot | Risk |
|---|-----------|---------|--------|------|
| 5 | **Cash tracking** | `self.cash -= actual_cost` (independent tracker) | No cash tracking. Router manages pools. | Low — recon covers it |
| 6 | **TP price recalculation** | Uses `eng.long_tp` as-is from engine | Recalculates `eng.long_avg_entry` and `eng.long_tp` from actual fill | **Medium** — recalc formula may have bugs |
| 7 | **TP qty source** | `bal["base_free"]` (exchange truth) | `fetch_open_positions()` in `_place_tp_order()` | OK — both use exchange |
| 8 | **Capital correction after buy** | None — engine tracks internally | `eng.capital -= (actual_cost - expected_cost)` | **Medium** — correction formula |
| 9 | **Router capital request** | N/A | Requests + validates before buy | OK — PM-specific |

### Issue #6 Detail — TP Recalculation
The PM bot recalculates avg entry after each buy:
```python
old_cost = eng.long_cost - actual_cost       # previous layers' cost
corrected_cost = old_cost + (actual_price * actual_qty)  # add actual fill
eng.long_cost = corrected_cost
eng.long_avg_entry = corrected_cost / eng.long_coins
eng.long_tp = eng.long_avg_entry * (1 + tp_pct)
```
This modifies engine state based on exchange fills, diverging from the engine's own accounting.
The old bot lets the engine handle its own avg entry and just uses whatever `eng.long_tp` is.
The TP price placed on exchange will differ from what the engine expects internally.

**Recommendation:** This is the right approach for live (actual fill > candle close), but verify
the math is correct. The engine's `eng.long_coins` must already include the new buy's coins
when we recalculate, otherwise the avg entry is wrong.

---

## SELL Execution (Non-TP)

### Old Bot ✅
```python
# LIVE GUARD check first
if tp_order_id and "TP" in reason:
    rollback from pre_tick_snapshot
    return
# Cancel TP for non-TP sells
if tp_order_id: cancel_tp_order()
result = executor.execute_sell(qty, price, reason)
if filled:
    # Correct engine capital from actual vs expected
    eng.capital += correction
    self.cash += proceeds
```

### PM Bot — DIFFERENCES

| # | Difference | Old Bot | PM Bot | Risk |
|---|-----------|---------|--------|------|
| 10 | **LIVE GUARD rollback** | Restores individual fields from snapshot dict | Uses `_rollback_engine()` helper | OK — same logic |
| 11 | **Post-sell engine cleanup** | Only corrects capital delta | Zeros ALL position fields + updates counters | **Good** — more thorough |
| 12 | **Capital return** | `self.cash += proceeds` | `self.router.return_capital(sym, proceeds)` | OK — PM-specific |

---

## TP Fill Handling

### Old Bot ✅
```python
def _check_tp_order_fill():
    order = fetch_order(tp_order_id)
    if order.status == "closed":
        actual_price = order.average or order.price
        actual_qty = order.filled
        proceeds = actual_qty * actual_price
        # Update tracker
        tracker.on_sell(...)
        # Correct engine capital
        eng.capital += correction_from_expected_vs_actual
        # Zero position fields
        eng.long_coins = 0; eng.long_cost = 0; ...
        # Save state
        tp_order_id = None
```
**Key: Does NOT reset last_candle_ts. Does NOT have re-entry cooldown.**

### PM Bot — DIFFERENCES

| # | Difference | Old Bot | PM Bot | Risk | Status |
|---|-----------|---------|--------|------|--------|
| 13 | **last_candle_ts reset** | Never touched | ~~Set to 0~~ Now set to `time.time()*1000` | **Critical** | ✅ FIXED |
| 14 | **Re-entry cooldown** | None | 60s global timer | **Medium** | ⚠️ |
| 15 | **Engine capital reset** | Only correction delta | `eng.capital = cs.allocated_capital` (full reset) | OK — PM needs this |
| 16 | **Two-tranche TP** | Single TP order for full position | Can have multiple TP orders (one per engine iteration) | **High** — orphaned orders |

### Issue #16 Detail — Multiple TP Orders
During the incident, the PM bot processed two TP fills (28.5 + 68.0 GRASS) as separate events.
After each fill, the engine replayed candles and placed new BUY orders. Each BUY triggered
a new TP order. Result: multiple overlapping TP orders on the exchange.

The old bot only ever had ONE TP order ID (`self._tp_order_id`). If a partial fill happened,
it would detect the remaining order still being open.

---

## Recommendations

### Remove (not in old bot, caused problems)
1. **Re-entry cooldown** — Remove `REENTRY_COOLDOWN` and `_reentry_cooldown_until` entirely. The old bot doesn't need it. The engine naturally re-enters on the next complete candle.
2. **Order dedup guard** — The file lock prevents dual processes. The dedup guard is a band-aid that can mask real bugs. Remove or demote to logging-only.

### Fix
3. **TP recalculation math** — Verify `eng.long_coins` includes the new buy before dividing to get avg entry. Add a unit test.
4. **Multi-TP orphan prevention** — After any TP fill, scan exchange for ALL open sell orders and cancel any that don't match the current `cs.tp_order_id`.

### Keep (improvements over old bot)
5. Pre-flight checks (min cost, balance check)
6. Spread logging
7. Full engine cleanup on TP fill
8. LIVE GUARD with full snapshot rollback
9. Phase change → cancel TP
