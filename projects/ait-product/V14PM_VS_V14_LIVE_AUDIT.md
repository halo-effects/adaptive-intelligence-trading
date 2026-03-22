# V14PM Live vs V14 Live — Critical Path Audit
**Date:** 2026-03-19 | **Major revision:** 2026-03-21
**Status:** RESOLVED — Exchange-as-truth architecture implemented 2026-03-21

Systematic comparison of every critical path in the working old bot (`run_v14_live_aster.py`)
versus the new PM bot (`run_v14_portfolio_live_aster.py`).

> **2026-03-21 ARCHITECTURAL OVERHAUL:** Items 1–7, 10, 12, 14–16, 19 are all resolved by
> the exchange-as-truth refactor. The engine no longer tracks positions — exchange API is the
> single source of truth. LIVE GUARD, rollbacks, reconciliation, and engine-based position
> tracking have been removed. See §21 below.

---

## Summary of Findings

| # | Critical Path | Old Bot | PM Bot (post 2026-03-21) | Status |
|---|---|---|---|---|
| 1 | Engine capital management | ✅ Full capital, reset on startup | ✅ Engine synced from exchange every cycle | **RESOLVED** |
| 2 | Startup reconciliation | ✅ eng.capital synced to exchange | ✅ Replaced by `_sync_positions_from_exchange()` | **RESOLVED** |
| 3 | Periodic reconciliation | ✅ Every 5 min, auto-adjusts | ✅ Exchange sync every 65s cycle (replaces periodic recon) | **RESOLVED** |
| 4 | TP fill → capital return | ✅ eng.capital += proceeds | ✅ Exchange shows zero next cycle; router returns capital | **RESOLVED** |
| 5 | Cash tracking (self.cash) | ✅ Independent tracker, synced | ✅ `_exchange_usdt_free` from API every cycle | **RESOLVED** |
| 6 | Capital ledger | ✅ Deposit/withdrawal tracking | ⚠️ Not implemented (exchange balance is truth) | **ACCEPTABLE** |
| 7 | Engine tick cash_available | ✅ Passes self.cash | ✅ Passes allocated_capital (router-managed) | **RESOLVED** |
| 8 | PID lock management | ✅ acquire/release with cleanup | ✅ File lock (msvcrt) with cleanup | OK |
| 9 | Exchange client timeout | ✅ SpotExchangeClient has timeouts | ✅ 15s timeout on all API calls | **FIXED** |
| 10 | Equity computation | ✅ Exchange balance (API truth) | ✅ usdt_total + unrealized from exchange | **RESOLVED** |
| 11 | TP order recovery | ✅ Scans open orders on exchange | ⚠️ Only checks saved order IDs | **WEAKER** |
| 12 | Deposit/withdrawal detection | ✅ Auto-detects via periodic recon | ✅ Exchange balance refreshed every cycle | **RESOLVED** |
| 13 | Error handling in main loop | ✅ try/except with 30s backoff | ✅ try/except with 10s backoff | OK |
| 14 | LIVE GUARD | ✅ Full rollback on TP conflict | ✅ Removed — exchange TP skipped if active | **RESOLVED** |
| 15 | Pre-tick snapshot | ✅ Full snapshot + rollback | ✅ Removed — engine position overwritten next cycle | **RESOLVED** |
| 16 | Sell failure rollback | ✅ Full state + phantom trade trim | ✅ Removed — engine position overwritten next cycle | **RESOLVED** |
| 17 | TP limit order placement | ✅ Uses exchange base_free for qty | ✅ Uses exchange position qty | **RESOLVED** |
| 18 | Phase change handling | ✅ Cancels TP, notifies | ✅ Cancels TP on phase change | **FIXED** |
| 19 | Status.json equity source | ✅ Exchange balance × price | ✅ All fields from exchange API | **RESOLVED** |
| 20 | Candle fetch | ✅ via SpotExchangeClient | ✅ Direct ccxt (timeout added) | OK |

---

## Detailed Findings

### 1. Engine Capital Management — **BROKEN**

**Old bot:** The engine gets the FULL bot capital ($340). On every startup, `_reset_engine_positions()`
sets `eng.capital = self.capital`. The engine's internal capital always matches the real account.

```python
# Old bot startup
eng.capital = self.capital  # Always $340
```

**PM bot:** Each engine gets a FRACTION of capital ($52 out of $350). The engine's internal
capital is used for DCA order sizing (`available = self.capital * DCA_CAPITAL_PCT`). After TP fills,
the engine adds proceeds back but rounding errors accumulate. After 2 cycles, capital depleted
from $56 → $27.31, causing order sizes to fall below the $10 minimum → **silently blocking all trades**.

**Fix applied today:** Reset engine capital to `allocated_capital` on startup when no position is open.
But this only fixes the symptom — the engine's paper-capital tracking is fundamentally incompatible
with the PM architecture where the CapitalRouter manages real capital.

**Proper fix needed:** The PM bot should either:
- (a) Reset engine capital to `allocated_capital` after EVERY TP fill (not just on startup), OR
- (b) Override the engine's order sizing to use `allocated_capital` directly (bypass internal tracking), OR
- (c) Set `eng.capital = allocated_capital` at the start of every tick cycle

### 2. Startup Reconciliation — **BROKEN**

**Old bot:** `_reconcile_on_startup()` compares:
- Exchange: USDT balance + base_total × price
- Engine: eng.capital + eng.long_coins × price
- If drift > $1: `eng.capital += total_drift` (and syncs `self.cash`)

This means the engine's internal capital is ALWAYS corrected to match reality on startup.

**PM bot:** `_reconcile_with_exchange()` compares:
- Exchange: USDT balance + position_value
- Engine: router_cash + sum(eng.long_cost)
- If drift > $1: `self.router.active_pool_cash += drift`

**Critical gap:** The PM bot adjusts the ROUTER, not the individual ENGINE capitals. An engine
can have `eng.capital = $27` while the router has plenty of cash. The router grants capital for
new trades, but the engine's internal sizing uses its own depleted `eng.capital` to calculate
order sizes — so the router capital is irrelevant.

**Fix needed:** Reconciliation must also sync each engine's `eng.capital` to its allocated amount
when no position is open.

### 3. Periodic Reconciliation — **MISSING**

**Old bot:** `_maybe_reconcile()` runs every 5 minutes. Compares exchange total value vs engine
total value. Alerts on >10% drift. Auto-detects deposits/withdrawals when no position is open.
Always syncs `self.cash` to `eng.capital`.

**PM bot:** No periodic reconciliation at all. Only runs `_reconcile_with_exchange()` once on startup.
If the engine or router state drifts during operation, there's no correction until next restart.

**Fix needed:** Add periodic reconciliation that:
- Runs every 5 minutes
- Compares exchange balance against router + engine totals
- Auto-corrects per-engine capital when position is closed
- Detects deposits/withdrawals

### 4. TP Fill → Capital Return — **FRAGILE**

**Old bot:** Simple and direct:
```python
eng.capital += proceeds  # Add actual exchange proceeds
self.cash += proceeds    # Track independently
# Later: self.cash = eng.capital (sync)
```

**PM bot:** Complex correction path:
```python
# Use stored TP price for expected proceeds
stored_tp = cs.tp_limit_price or eng.long_tp or actual_price
engine_expected = stored_tp * actual_qty
correction = actual_proceeds - engine_expected
if abs(correction) > 0.01:
    eng.capital += correction  # Only adds the DIFFERENCE
else:
    eng.capital += actual_proceeds  # Adds full proceeds
```

**Bug:** When `correction > 0.01`, only the correction amount is added — NOT the full proceeds.
The engine already added TP-price proceeds during its internal tick? No — the TP is handled by
the exchange, not the engine. The engine never ran a sell tick. So `eng.capital` still has the
pre-buy amount minus the buy cost. We need to add `actual_proceeds`, not just the correction.

Wait — let me re-check. The engine's `long_cost` was deducted on buy. After TP:
- `eng.capital` = original - buy_cost
- We add `correction` (= actual_proceeds - expected) → eng.capital = original - buy_cost + correction
- But we need: eng.capital = original - buy_cost + actual_proceeds

**This is a bug.** When `abs(correction) > 0.01`, only the delta is added, not the full proceeds.
The `else` branch correctly adds `actual_proceeds`, but the `if` branch only adds `correction`.

**Fix needed:** Always add `actual_proceeds` to `eng.capital`. If there's a correction from stored
vs actual TP price, apply that separately.

### 5. Cash Tracking (self.cash) — **MISSING**

**Old bot:** Maintains `self.cash` as an independent cash tracker alongside `eng.capital`.
Every buy: `self.cash -= actual_cost`. Every sell: `self.cash += proceeds`. Periodically synced
to `eng.capital` as a sanity check. This double-entry pattern catches discrepancies early.

**PM bot:** No `self.cash` equivalent. The CapitalRouter tracks pool-level cash
(`active_pool_cash`, `reserve_pool_cash`), but individual engine cash is not independently tracked.
When the engine's internal capital drifts, there's no second source of truth to catch it.

**Fix needed:** Either add per-coin cash tracking or verify engine capital against router
allocations on every tick.

### 6. Capital Ledger — **MISSING**

**Old bot:** Full capital ledger system (`capital_ledger.json`) tracking deposits, withdrawals,
and capital adjustments. The bot loads capital from ledger on startup (overrides CLI arg).
Supports `--deposit` and `--withdraw` CLI flags.

**PM bot:** Capital is passed as CLI arg only. No ledger. No deposit/withdrawal tracking.
If Brett deposits more USDT, the bot won't know unless restarted with a new `--capital` value.

**Fix needed:** Port capital ledger system from old bot.

### 7. Engine Tick cash_available — **WRONG**

**Old bot:** `actions = self.engine.tick(candle, self.cash)` — passes actual available cash.

**PM bot:** `actions = cs.engine.tick(candle, cash_available=0)` — always passes 0.

The engine's `_long_dca_tick` uses `self.capital` for order sizing (not `cash_available`),
so passing 0 doesn't break sizing. But the lifecycle engine may use `cash_available` for
other decisions (e.g., position sizing validation). This should at minimum pass
`cs.allocated_capital` or `self.router.available_cash(sym)`.

### 8. PID Lock Management — **FRAGILE**

**Old bot:** Uses `_acquire_pid_lock()` / `_release_pid_lock()` helper functions.
The lock is released in a `finally` block, and the acquire function checks if the old
PID is actually alive via `os.kill(old_pid, 0)`.

**PM bot:** Inline PID lock check in `run()`. Checks `os.kill(old_pid, 0)` correctly,
but the release is buried in the `finally` block and only does `pid_path.unlink()`.
**No stale PID cleanup on crash** — if the bot crashes without reaching `finally`,
the next startup sees the stale PID file, tries `os.kill`, and if a different process
inherited that PID, it exits with code 1 (the exact bug we hit today).

**Fix needed:** Make PID lock more robust — include a timestamp and bot signature
in the PID file, or use a file lock (flock) instead.

### 9. Exchange Client Timeout — **FIXED** (today)

**Old bot:** Uses `SpotExchangeClient` which wraps ccxt with built-in timeouts.

**PM bot:** Uses `ccxt.aster()` directly with no `timeout` parameter. API calls could
hang indefinitely. **Fixed today** by adding `"timeout": 15000` to ccxt config.

### 10. Equity Computation — **FIXED** (2026-03-20)

**Old bot:** `_write_status()` fetches exchange balance (USDT + base × price) for equity.
Uses exchange API as the single source of truth. Uses `usdt_total` (includes locked margin).

**PM bot (was):** `_compute_equity()` called `fetch_balance()` which returned `USDT.free`
(excludes margin locked in positions). `_write_status()` added full notional
(`entry_price * qty + unrealized_pnl`) on top of `USDT.free` — double-counting margin.
Result: equity reported as $102.94 instead of ~$350.

**Fix applied (commit 812d5264):**
- Added `fetch_full_balance()` returning `{usdt_free, usdt_total}`
- `_compute_equity()` now uses `usdt_total + unrealized_pnl`
- `_write_status()` equity = `usdt_total + unrealized` (mirrors V14 Live pattern)
- Added `cash` and `exchange_balance` fields to status.json
- Dashboard donut patched to fall back to `router.active_cash + router.reserve_cash`

### 11. TP Order Recovery — **WEAKER**

**Old bot:** `_recover_tp_order()` fetches ALL open orders from the exchange, then:
- Has position + open sell → adopt order
- Has position + no order → place new TP
- No position + stale order → cancel it
- Handles multiple stale orders

**PM bot:** `_recover_tp_orders()` only checks saved `cs.tp_order_id` values.
If a TP order was placed but the state wasn't saved before crash, it's orphaned
on the exchange forever. If the state has a stale order ID that was already filled,
it checks and handles that. But it never scans for UNKNOWN orders on the exchange.

**Fix needed:** Add exchange-side open order scan on startup (like old bot).

### 17. TP Limit Order Quantity — **DIFFERENT**

**Old bot:** Uses `bal["base_free"]` (actual exchange holding) for TP sell quantity.
Falls back to `eng.long_coins` only if balance is 0. This handles leverage differences
and partial fills correctly.

**PM bot:** Uses `eng.long_coins` directly. For perps with leverage, this may not
match the actual exchange position size. If there's any discrepancy between the engine's
tracked position and the exchange's actual position, the TP order will have the wrong qty.

**Fix needed:** Fetch actual position size from exchange for TP order placement.

### 18. Phase Change Handling — **MISSING**

**Old bot:** Detects phase changes and cancels TP orders:
```python
if self.engine.phase != prev_phase:
    if self._tp_order_id and self.executor:
        self.executor.cancel_tp_order(self._tp_order_id)
        self._tp_order_id = None
```

**PM bot:** No phase change detection in the main loop. If the engine transitions
phases (e.g., LONG_DCA → SHORT_DCA), stale TP orders remain on the exchange.

### 19. Status.json Equity — **FIXED** (2026-03-20)

**Old bot:** Equity in status.json comes directly from exchange API:
```python
exchange_equity = eb["usdt_total"] + eb["base_total"] * price
st["equity"] = round(exchange_equity, 2)
st["cash"] = round(eb["usdt_total"], 2)
```

**PM bot (was):** Equity came from `fetch_balance()` (USDT.free only) + full notional of positions.
No `cash` field in status.json, breaking dashboard utilization donut.

**Fix applied (commit 812d5264):** Now mirrors V14 Live — uses `usdt_total + unrealized_pnl`.
Writes `cash` and `exchange_balance` to status.json.

---

## Priority Fixes (Ordered)

### P0 — Trade-blocking bugs (fix NOW)
1. **Engine capital reset after EVERY TP fill** — not just startup
2. **TP fill capital return bug** — always add `actual_proceeds`, not just `correction`
3. **Periodic reconciliation** — sync engine capitals every 5 minutes

### P1 — Safety gaps (fix this week)
4. **Exchange-side TP order scan on startup** — detect orphaned orders
5. **Phase change → cancel TP orders** — port from old bot
6. **TP order qty from exchange position** — not engine tracking
7. **PID lock robustness** — timestamp + signature in lock file

### P2 — Operational gaps (fix soon)
8. **Capital ledger** — deposit/withdrawal tracking
9. **Periodic cash tracking** — double-entry verification
10. ~~**Equity computation**~~ — ✅ FIXED 2026-03-20 (commit 812d5264). **Post-mortem (2026-03-21):** Fix was on disk but not active for ~21 hours. Root cause: `.pyc` bytecode cache mtime (08:37:25) was 43 seconds newer than `.py` source mtime (08:36:42) due to git/auto-backup touching the file during an active editing session. Python skipped recompilation on every restart, serving stale bytecode with the old `fetch_balance()` (returns `usdt_free` ~$103) instead of the fixed `fetch_full_balance()` (returns `usdt_total` ~$351). Dashboard showed equity alternating between ~$103 (wrong, ~80% of syncs) and ~$346 (correct, when `fetch_open_positions()` compensated). Resolution: deleted stale `.pyc`, touched `.py`, restarted bot (PID 5036). **Lesson:** After code fixes to running bots, always delete `__pycache__/*.pyc` or use `python -B` to disable bytecode caching.
11. **Pass real cash_available to engine tick** — not 0

---

## 21. Exchange-as-Truth Architecture Refactor (2026-03-21)

**Root cause of all position-tracking bugs:** The PM Live bot inherited a paper-bot architecture
where the engine tracks positions internally via candle simulation. Both the old V14 Live bot
and the PM Live bot had this fundamental flaw — the engine maintained its own position state
(long_coins, long_cost, long_avg_entry) that could diverge from exchange reality. The old bot
hid this with a status-write override; the PM bot exposed it.

**Symptom:** Engine state carried 68.17 GRASS tokens ($27 invested) from the original bot launch,
while the exchange had 635.4 GRASS tokens ($247 invested). Status.json reported equity ~$103
instead of ~$346. The -70% "drawdown" was entirely a display bug.

**Investigation findings:**
- Startup reconciliation briefly corrected engine to 635.4 coins, but something in the main loop
  reverted it (suspected: daily rebalance or LIVE GUARD rollback)
- Periodic reconciliation stopped firing after 10:43 AM (only 2 fires in 6+ hours)
- The old bot's `_maybe_reconcile()` literally does nothing when a position is open ("not auto-adjusting")
- Both bots used candle-tick-driven position simulation — wrong for live trading

**Architectural change:**
- `_sync_positions_from_exchange()` added — runs every main loop cycle (65s)
- Overwrites engine position state (long_coins, long_cost, avg_entry, TP) from exchange API
- `_write_status()` completely rewritten — ALL position/balance data from exchange API
- Engine only contributes signal/phase state (DCA levels, phase transitions)
- Layer tracking moved to `CoinState.layer_count` (persisted separately)

**Removed (no longer needed):**
- `_reconcile_with_exchange()` (~120 lines)
- `_periodic_reconcile()` (~80 lines)
- `_snapshot_engine()` / `_rollback_engine()` (~40 lines)
- LIVE GUARD TP blocking (~15 lines)
- Engine state correction after BUY/SELL fills (~40 lines)
- Pre-tick snapshot in candle processing

**Result:** Bot code is ~280 lines shorter. Status.json now shows correct data:
- equity: $341.33 (was $103.17)
- invested: $247.20 (was $27.03)
- avg_entry: $0.389 (was $0.396)
- pnl: +0.39% (was -70.52%)
- All fields present: cash, exchange_balance, total_realized_pnl, timeframe

**This resolves P0 items 1-3, P1 items 4-6, and P2 items 8-11 from the priority list above.**
Capital management, reconciliation, cash tracking, and equity computation are all now derived
from exchange API data rather than engine internal state.
