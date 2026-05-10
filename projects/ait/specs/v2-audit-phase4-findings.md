# V2 Audit — Phase 4: Trade Execution & Portfolio Management

**Date**: 2026-05-10  
**Auditor**: OpenClaw AI  
**Files reviewed**: `run_v14_portfolio_live_aster.py` (3,730 lines), `v14_lifecycle_engine.py` (866 lines), `v14_capital_manager.py` (560 lines)  
**Status**: COMPLETE

---

## FINDING 26: MEDIUM — Capital Pool Drift Over Multiple Trades

**Files**: `v14_capital_manager.py` (return_capital, line 421), `run_v14_portfolio_live_aster.py` (_handle_tp_fill, line 1744)

**Issue**: When a deal closes (TP fill), two things happen:
1. `router.return_capital(sym, actual_proceeds)` — adds actual sale proceeds to active_pool_cash
2. `eng.capital = cs.allocated_capital` — resets engine capital to the full allocation

The proceeds returned to the pool include the original cost PLUS profit. Over time, the active pool accumulates more cash than was originally allocated (because profits are returned but never extracted). This means:
- After 10 winning trades at 1.5% TP, the pool has ~15% more cash than it started with
- `rebalance_daily()` then recalculates allocations based on equity (which includes this extra cash)
- This is actually correct behavior for compounding — profits stay in the pool

However, `return_capital()` zeros the coin's allocation tracking (`active_allocations[coin] = 0.0`). This means:
- Between the TP fill and the next rebalance, the T1 gate might block re-entry because `active_allocations` is zeroed
- BUT `_prune_stale_coin_after_tp()` runs right after, which checks scanner top-N independently

**Severity**: MEDIUM (could cause brief re-entry delay between TP and next rebalance)  
**Recommendation**: After return_capital, immediately re-seed active_allocations if coin is still in scanner top-N

---

## FINDING 27: LOW — CSV Trade Log Read on Every Status Write

**File**: `run_v14_portfolio_live_aster.py`, lines 3135-3145

**Code**:
```python
# Per-coin realized PnL from CSV (survives restarts)
csv_path = OUTPUT_DIR / "trades.csv"
if csv_path.exists():
    import csv as csv_mod
    with open(csv_path) as cf:
        reader = csv_mod.DictReader(cf)
        coin_pnl = sum(float(t.get("pnl", 0) or 0) for t in reader if t.get("symbol") == sym)
    coin_data["realized_pnl"] = round(coin_pnl, 4)
```

**Issue**: Status writes happen every 60 seconds. Each one opens and reads the entire trades.csv file for EACH coin to compute per-coin realized PnL. With 3 active coins and a growing CSV, this is O(coins × trades) disk IO per minute.

**Severity**: LOW (file is small, but will grow over months of trading)  
**Recommendation**: Cache per-coin PnL in memory, update only on new trade. Reset cache on restart from CSV.

---

## FINDING 28: LOW — `_detect_capital_change()` Is Dead Code

**File**: `run_v14_portfolio_live_aster.py`, lines 1120-1175

**Observation**: The function has an early `return` on line 1133 that makes everything below it dead code. This was intentionally disabled on 2026-05-08 (comment explains why: heuristic formula created phantom deposits). The dead code is preserved for reference.

**Severity**: LOW (intentionally disabled, documented)  
**Recommendation**: Remove dead code during migration cleanup, or move to a `_deprecated/` section

---

## FINDING 29: POSITIVE — Exchange-as-Truth Architecture Is Sound

**Observation**: The bot's exchange-as-truth pattern is well-implemented:
1. `_sync_positions_from_exchange()` runs every cycle, overwrites engine position state
2. If exchange has no position, ALL position fields (long AND short) are zeroed
3. TP orders are placed on exchange with actual exchange entry price, not engine TP
4. Fill prices come from exchange API, not engine simulation
5. Capital reads from DEX wallet on startup (DEX-as-truth)

This eliminates the entire class of phantom trade bugs that plagued earlier versions. The engine is used only for signal generation (phase transitions, top/bottom detection). All quantities come from the exchange.

**Severity**: POSITIVE — well architected

---

## FINDING 30: POSITIVE — Candle Replay Guard Works Correctly

**Observation**: The warmup logic on lines 3489-3510 correctly identifies the most recent candle as the only one that can trigger real trades. All earlier candles update indicators only (warmup). This prevents the "635 GRASS incident" pattern where replayed historical candles executed real buys at stale prices.

**Severity**: POSITIVE — correct implementation

---

## FINDING 31: MEDIUM — Engine Capital Reset After TP May Cause Sizing Error

**File**: `run_v14_portfolio_live_aster.py`, _handle_tp_fill, line 1856

**Code**:
```python
# Reset engine capital to allocated amount
eng.capital = cs.allocated_capital
```

**Issue**: After a TP fill, engine capital is reset to `cs.allocated_capital`. But if the daily rebalance hasn't run yet, `cs.allocated_capital` might be stale (from yesterday's allocation). If equity changed significantly (e.g., big win or loss), the engine's next layer sizing will use the old allocation.

The fix is that `_do_rebalance()` updates `cs.allocated_capital` daily. Between rebalances, the allocation is static — which is actually correct (you don't want allocation to shift mid-deal). The only risk is if a TP fires right before rebalance, the next trade uses yesterday's allocation for a few seconds.

**Severity**: MEDIUM (edge case, but could cause slight oversizing)  
**Recommendation**: Acceptable as-is. Document that allocation is intentionally static between rebalances.

---

## FINDING 32: MEDIUM — Router Pool Cash Can Go Negative

**File**: `v14_capital_manager.py`, request_capital (line 377)

**Issue**: The `request_capital()` function caps grants at available cash (partial fill). But in `_execute_action()`, if `granted < cost`, the bot rejects the trade AND returns the granted amount. The return happens via `router.return_capital(sym, granted)`, which adds to `active_pool_cash`. This is correct.

However, there's no check that `active_pool_cash` or `reserve_pool_cash` can't go negative through rounding or concurrent access. In Python's single-threaded GIL, this is safe. But during migration to multi-threaded/async, this would need locks.

**Severity**: MEDIUM (not a bug now, but migration risk)  
**Recommendation**: Add assertion/guard: `if self.active_pool_cash < -0.01: logger.error(...)`

---

## FINDING 33: MEDIUM — Spread Reject Creates Net Loss

**File**: `run_v14_portfolio_live_aster.py`, lines 2143-2170

**Issue**: When a buy fills with spread > MAX_ENTRY_SPREAD_BPS (default 100bps = 1%), the bot immediately sells the position to limit damage. But:
1. Buy at market: pays taker fee + slippage
2. Immediate sell at market: pays taker fee + slippage again
3. Net result: double fees + spread loss ≈ 1-2% of the order

This is the correct behavior (limiting a bad fill) but creates a guaranteed small loss. The question is whether the spread threshold is too tight or too loose.

At 100bps (1%), for a $100 order, the spread reject triggers if fill is $1 away from expected. This seems reasonable for small-cap perps on Aster.

**Severity**: MEDIUM (correct behavior but worth monitoring)  
**Recommendation**: Log spread reject events and analyze frequency. If happening often, consider:
1. Using limit orders instead of market orders for entries
2. Pre-checking order book depth before market buy

---

## FINDING 34: LOW — No Graceful Degradation for Exchange API Failures

**File**: `run_v14_portfolio_live_aster.py`, main loop (lines 3444-3590)

**Issue**: If the exchange API fails (network error, rate limit), the bot:
1. `_sync_positions_from_exchange()` — keeps previous values (correct)
2. `_check_tp_fills()` — logs error, continues (correct)
3. `_fetch_candles()` — logs warning, skips coin (correct)
4. `_execute_action()` — BUY fails, rolls back router (correct)

Individual failure handling is good. But there's no circuit breaker — if the exchange is down for 30 minutes, the bot will:
- Try every 65-second cycle
- Accumulate candle backlog
- When exchange comes back, process all queued candles (warmup-only except last)

This is actually safe because of the warmup guard. The only risk is if the exchange comes back with partial data (e.g., position exists but balance API fails), which could cause engine/exchange state mismatch for one cycle.

**Severity**: LOW (existing guards handle this)  
**Recommendation**: Add consecutive failure counter; after 5+ failures, log ERROR-level alert

---

## FINDING 35: POSITIVE — TP Recovery Is Thorough

**File**: `run_v14_portfolio_live_aster.py`, _recover_tp_orders (lines 1452-1555)

**Observation**: On startup, the bot:
1. Checks saved TP order IDs (filled/cancelled while down)
2. Scans exchange for ALL open sell orders per coin
3. Adopts orphaned sell orders as TP orders
4. Cancels stale sell orders with no matching position
5. Places new TP orders for positions with no sell order

This handles all edge cases from crashes, restarts, and manual exchange interaction.

**Severity**: POSITIVE — battle-tested recovery logic

---

## FINDING 36: LOW — Lifecycle Engine Refreshes Signal Pack Every Day

**File**: `v14_lifecycle_engine.py`, tick() lines 227-237

**Code**: On each daily boundary, the engine reinitializes V13SignalPack from DB:
```python
self.pack = V13SignalPack(self.coin)
self._engine.pack = self.pack
self._engine.daily = self.pack.daily
self._engine._precompute_stoch()
self._engine.detector = HybridDetector2D(...)
self._engine.div_dates = self._engine.detector.compute_2d_divergence_dates()
```

This reads from candles.db, recomputes all indicators, and rebuilds the divergence dates. For 3 active coins, this runs 3× per day at midnight UTC. Each read loads the full daily history for the coin.

**Severity**: LOW (acceptable overhead for 3 coins, could become noticeable at 10+ coins)  
**Recommendation**: At scale, consider incremental signal updates instead of full reload

---

## FINDING 37: NOTE — Short Selling Is Explicitly Blocked

**File**: `run_v14_portfolio_live_aster.py`, _execute_action, lines 2282-2291

**Observation**: SHORT_OPEN and SHORT_CLOSE actions are explicitly rejected:
```python
elif act_type in ("SHORT_OPEN", "SHORT_CLOSE"):
    logger.warning(f"SHORT action {act_type} for {sym} — not supported in live mode.")
    if cs.engine: cs.engine.reject_action(action)
```

This means the bot is long-only in production. The engine can detect SHORT_DCA phase (and flags it via regime gate), but never opens short positions. This is intentional (Aster perps long-only mode) but worth documenting for migration when shorting becomes available.

---

## Summary

| # | Severity | Finding | Status |
|---|----------|---------|--------|
| 26 | MEDIUM | Capital pool drift between TP and rebalance | 🟡 Edge case |
| 27 | LOW | CSV read on every status write (60s) | 🟡 Performance |
| 28 | LOW | `_detect_capital_change()` is dead code | 🟢 Intentional |
| 29 | POSITIVE | Exchange-as-truth architecture is sound | ✅ Well built |
| 30 | POSITIVE | Candle replay guard works correctly | ✅ Well built |
| 31 | MEDIUM | Engine capital reset may use stale allocation | 🟡 Edge case |
| 32 | MEDIUM | Router pool cash has no negative guard | 🟡 Migration risk |
| 33 | MEDIUM | Spread reject creates guaranteed small loss | 🟡 By design |
| 34 | LOW | No circuit breaker for exchange API failures | 🟡 Low risk |
| 35 | POSITIVE | TP recovery is thorough | ✅ Battle-tested |
| 36 | LOW | Signal pack full reload every day per coin | 🟡 Scale concern |
| 37 | NOTE | Short selling explicitly blocked (long-only) | 🟢 Intentional |

**Overall assessment**: The trade execution layer is well-built. Exchange-as-truth eliminates phantom trade bugs. TP recovery handles all crash scenarios. The main areas for improvement are edge cases around capital pool timing and scalability concerns that only matter at 10+ coins.

---

## Next Phase: Phase 5 — State Management & Persistence (state.json, capital ledger, trade tracker)
