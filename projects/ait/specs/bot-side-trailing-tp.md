# Implementation Spec: Bot-Side Trailing Take-Profit

**Date**: 2026-05-07  
**Author**: GeeGee (AI) — reviewed with Brett  
**Status**: DRAFT — Pending Brett approval  
**Target**: `run_v14_portfolio_live_aster.py` (live PM bot on Aster)  
**Future**: Same pattern portable to Hyperliquid migration

---

## 1. Problem Statement

The current trailing stop TP relies entirely on Aster's native `TRAILING_STOP_MARKET` order type. When the trailing stop triggers, Aster sends a **market sell** into an often-thin order book, resulting in:

- **69% of trades filling below the theoretical 1.3% minimum** (activation 1.5% - callback 0.2%)
- **15% of trades going negative** due to market sell slippage
- **Live win rate of 84.3%** vs paper's 99.9%
- Average live return of 1.25% vs paper's 1.78%

The exchange-native trailing stop has no concept of fill quality — it fires a market order regardless of available liquidity.

## 2. Proposed Solution: Hybrid Bot-Side Trailing TP

Replace the current exchange-native trailing stop with a **bot-side price monitor** that places **limit sell orders** when the trailing condition triggers. Retain an exchange-native trailing stop as a **wider safety net** in case the bot crashes.

### Two-Layer Architecture

```
Layer 1 (Primary): Bot-side trailing TP
  - Polls price every 5 seconds
  - Tracks peak price after activation (entry × 1.015)
  - When price drops 0.2% from peak → place LIMIT SELL at callback price
  - Limit sell guarantees fill at target price or better
  - If limit sell doesn't fill in 60s → escalate to market sell

Layer 2 (Safety Net): Exchange-native trailing stop
  - Placed at wider callback (1.0%) to avoid interference with bot-side TP
  - Only fires if bot crashes or loses connection
  - Accepts worse fill as insurance premium
  - Cancelled when bot-side TP successfully fills
```

## 3. Detailed Code Changes

### 3.1 New Constants (top of file, near existing trailing stop constants)

```python
# ── Bot-Side Trailing TP ──────────────────────────────────────────────────
BOT_SIDE_TP_ENABLED       = True    # Master switch for bot-side trailing TP
BOT_SIDE_POLL_INTERVAL    = 5       # Seconds between price checks
BOT_SIDE_CALLBACK_PCT     = 0.2     # 0.2% trail distance (same as current)
SAFETY_NET_CALLBACK_PCT   = 1.0     # 1.0% callback for exchange safety net
LIMIT_SELL_TIMEOUT_SECS   = 60      # Seconds before escalating limit to market
LIMIT_SELL_PRICE_BUFFER   = 0.05    # 0.05% below trigger price for fill certainty
```

**Rationale for `SAFETY_NET_CALLBACK_PCT = 1.0%`**: Must be wide enough that it never fires before the bot-side 0.2% callback. With 1.0%, the safety net only fires if price drops 1% from peak — giving the bot-side TP 0.8% of headroom to act first. Even with API latency, the bot-side limit sell will fill well before 1.0% retracement.

**Rationale for `LIMIT_SELL_PRICE_BUFFER = 0.05%`**: The limit sell is placed 0.05% below the theoretical callback price. This tiny concession virtually guarantees immediate fill while only giving back $0.05 per $100 traded. Without it, the limit order might sit at exactly the trigger price and not fill if the book is thin at that exact level.

### 3.2 New CoinState Fields

Add to `CoinState.__init__()` (after existing trailing stop fields, ~line 700):

```python
# Bot-side trailing TP state
self.bot_tp_activated: bool = False         # Has price reached activation?
self.bot_tp_peak_price: float = 0.0         # Highest price since activation
self.bot_tp_trailing_stop: float = 0.0      # Current stop level (peak × (1 - callback))
self.bot_tp_limit_order_id: Optional[str] = None   # Pending limit sell order
self.bot_tp_limit_placed_at: float = 0.0    # Timestamp when limit sell was placed
```

Add to `CoinState.to_dict()` and `_load_state()` / `_save_state()` for persistence.

### 3.3 New Method: `_bot_side_tp_check()` 

This is the core new method. Runs in the fast-poll loop (every 5 seconds).

```python
def _bot_side_tp_check(self):
    """Bot-side trailing TP: poll prices and place limit sells when triggered.
    
    Runs every BOT_SIDE_POLL_INTERVAL seconds (5s). For each coin with an
    open position and an activation price set:
    
    1. Fetch current price
    2. If not yet activated and price >= activation → activate, record peak
    3. If activated, update peak and trailing stop level
    4. If price <= trailing stop → place limit sell, cancel safety net
    5. If limit sell pending and timed out → escalate to market sell
    """
    for sym, cs in list(self.coins.items()):
        if not cs.engine or not cs.engine._engine:
            continue
        eng = cs.engine._engine
        if eng.long_coins <= 0 or not cs.tp_activation_price:
            continue
        
        # Skip if bot-side TP already completed (limit order placed and filled)
        # The _check_tp_fills() method handles fill detection
        
        # --- STEP 0: Check pending limit sell timeout ---
        if cs.bot_tp_limit_order_id:
            elapsed = time.time() - cs.bot_tp_limit_placed_at
            if elapsed >= LIMIT_SELL_TIMEOUT_SECS:
                # Limit sell didn't fill in time — escalate to market sell
                logger.warning(
                    f"Bot-side TP limit sell TIMEOUT for {sym} after {elapsed:.0f}s. "
                    f"Escalating to market sell."
                )
                self.client.cancel_tp_order(sym, cs.bot_tp_limit_order_id)
                cs.bot_tp_limit_order_id = None
                
                # Cancel safety net too
                if cs.tp_order_id:
                    self.client.cancel_tp_order(sym, cs.tp_order_id)
                    cs.tp_order_id = None
                
                # Market sell (same as existing _handle_tp_fill path)
                result = self.client.create_market_sell(sym, eng.long_coins)
                if result and result.get("status") in ("filled", "dry_run"):
                    self._handle_tp_fill(sym, cs, result)
                else:
                    logger.error(f"Market sell escalation FAILED for {sym}")
                    send_telegram(
                        f"🚨 {TG_PREFIX} <b>TP Escalation Failed</b>\n"
                        f"Symbol: {sym}\n"
                        f"Limit sell timed out AND market sell failed.\n"
                        f"Manual intervention required."
                    )
                continue
            else:
                # Limit sell still pending — check if filled
                try:
                    result = self.client.check_order_status(sym, cs.bot_tp_limit_order_id)
                    if result.get("filled"):
                        logger.info(f"Bot-side TP limit sell FILLED for {sym}")
                        # Cancel safety net
                        if cs.tp_order_id:
                            self.client.cancel_tp_order(sym, cs.tp_order_id)
                            cs.tp_order_id = None
                        self._handle_tp_fill(sym, cs, result)
                        cs.bot_tp_limit_order_id = None
                        cs.bot_tp_activated = False
                        cs.bot_tp_peak_price = 0.0
                        cs.bot_tp_trailing_stop = 0.0
                except Exception as e:
                    logger.warning(f"Bot-side TP fill check failed for {sym}: {e}")
                continue  # Don't re-check price while limit order is pending
        
        # --- STEP 1: Fetch current price ---
        try:
            current_price = self.client.fetch_ticker_price(sym)
            if current_price <= 0:
                continue
        except Exception as e:
            logger.debug(f"Price fetch failed for {sym} in bot-side TP: {e}")
            continue
        
        # --- STEP 2: Activation check ---
        if not cs.bot_tp_activated:
            if current_price >= cs.tp_activation_price:
                cs.bot_tp_activated = True
                cs.bot_tp_peak_price = current_price
                cs.bot_tp_trailing_stop = current_price * (1 - BOT_SIDE_CALLBACK_PCT / 100)
                logger.info(
                    f"Bot-side TP ACTIVATED for {sym}: "
                    f"price=${current_price:.6f} >= activation=${cs.tp_activation_price:.6f} | "
                    f"initial stop=${cs.bot_tp_trailing_stop:.6f}"
                )
            continue  # Not activated yet, nothing more to do
        
        # --- STEP 3: Update peak and trailing stop ---
        if current_price > cs.bot_tp_peak_price:
            cs.bot_tp_peak_price = current_price
            cs.bot_tp_trailing_stop = current_price * (1 - BOT_SIDE_CALLBACK_PCT / 100)
        
        # --- STEP 4: Check if trailing stop triggered ---
        if current_price <= cs.bot_tp_trailing_stop:
            # Calculate limit sell price (slightly below trigger for fill certainty)
            limit_price = cs.bot_tp_trailing_stop * (1 - LIMIT_SELL_PRICE_BUFFER / 100)
            
            logger.info(
                f"Bot-side TP TRIGGERED for {sym}: "
                f"price=${current_price:.6f} <= stop=${cs.bot_tp_trailing_stop:.6f} | "
                f"peak=${cs.bot_tp_peak_price:.6f} | "
                f"placing limit sell @ ${limit_price:.6f}"
            )
            
            # Place limit sell
            oid = self.client.place_limit_sell(sym, eng.long_coins, limit_price)
            if oid:
                cs.bot_tp_limit_order_id = oid
                cs.bot_tp_limit_placed_at = time.time()
                logger.info(f"Bot-side TP limit sell placed for {sym}: order={oid}")
                
                send_telegram(
                    f"🎯 {TG_PREFIX} <b>Bot-Side TP Triggered</b>\n"
                    f"Symbol: {sym}\n"
                    f"Peak: ${cs.bot_tp_peak_price:.6f}\n"
                    f"Limit sell: ${limit_price:.6f} (qty: {eng.long_coins:.4f})\n"
                    f"Timeout: {LIMIT_SELL_TIMEOUT_SECS}s before market fallback"
                )
            else:
                # Limit sell placement failed — fall back to market immediately
                logger.error(f"Bot-side TP limit sell FAILED for {sym} — falling back to market")
                if cs.tp_order_id:
                    self.client.cancel_tp_order(sym, cs.tp_order_id)
                    cs.tp_order_id = None
                result = self.client.create_market_sell(sym, eng.long_coins)
                if result and result.get("status") in ("filled", "dry_run"):
                    self._handle_tp_fill(sym, cs, result)
                cs.bot_tp_activated = False
                cs.bot_tp_peak_price = 0.0
                cs.bot_tp_trailing_stop = 0.0
```

### 3.4 Modify `_place_tp_order()` (~line 1350)

Change to place the **safety net** trailing stop at the wider callback instead of the primary TP:

```python
# In _place_tp_order(), change the trailing stop placement:
if BOT_SIDE_TP_ENABLED:
    # Place WIDE safety net trailing stop (only fires if bot crashes)
    oid = self.client.place_trailing_stop_sell(
        sym, qty, tp_price, SAFETY_NET_CALLBACK_PCT  # 1.0% instead of 0.2%
    )
    if oid:
        cs.tp_order_id = oid
        cs.tp_limit_price = tp_price
        cs.tp_type = "safety_net"
        cs.tp_activation_price = tp_price
        cs.trailing_callback_pct = SAFETY_NET_CALLBACK_PCT
        # Reset bot-side TP state for fresh tracking
        cs.bot_tp_activated = False
        cs.bot_tp_peak_price = 0.0
        cs.bot_tp_trailing_stop = 0.0
        cs.bot_tp_limit_order_id = None
        logger.info(
            f"Safety net trailing TP placed for {sym}: qty={qty:.4f} "
            f"activation=${tp_price:.8f} safety_callback={SAFETY_NET_CALLBACK_PCT}% | "
            f"Bot-side TP will use {BOT_SIDE_CALLBACK_PCT}% callback"
        )
    # ... existing fallback to limit sell if trailing stop fails
elif TRAILING_STOP_ENABLED:
    # Legacy: exchange-native trailing stop (pre-bot-side)
    # ... existing code unchanged
```

### 3.5 Modify Main Loop (~line 3330)

Add the fast-polling bot-side TP check alongside existing checks:

```python
# Current main loop structure:
last_tp_check = time.time()
last_bot_tp_check = time.time()  # NEW

while not self._shutdown:
    cycle_start = time.time()
    
    try:
        # ... existing checks (telegram commands, rebalance, regime) ...
        
        # Bot-side trailing TP — fast poll (every 5 seconds)
        if BOT_SIDE_TP_ENABLED and time.time() - last_bot_tp_check >= BOT_SIDE_POLL_INTERVAL:
            self._bot_side_tp_check()
            last_bot_tp_check = time.time()
        
        # Existing TP fill check (every 65 seconds) — now only checks safety net
        if time.time() - last_tp_check >= TP_CHECK_INTERVAL:
            self._check_tp_fills()
            self._update_funding()
            last_tp_check = time.time()
        
        # ... rest of existing loop ...
    
    # IMPORTANT: Reduce main loop sleep to accommodate 5s polling
    elapsed = time.time() - cycle_start
    sleep_time = max(1, BOT_SIDE_POLL_INTERVAL - elapsed)  # Was LIVE_POLL_INTERVAL (65s)
    deadline = time.time() + sleep_time
    while time.time() < deadline and not self._shutdown:
        time.sleep(1)
```

**Critical change**: The main loop sleep drops from 65s to 5s. This means ALL existing per-cycle operations (candle processing, position sync, status writes) now run every 5s instead of every 65s. This is fine for:
- `_sync_positions_from_exchange()`: Already designed for frequent calls, uses caching
- `_write_status()`: Already has `STATUS_WRITE_INTERVAL` (60s) internal throttle
- `_check_tp_fills()`: Already has `TP_CHECK_INTERVAL` (65s) internal throttle
- Candle processing: Only acts when new candles appear (hourly), so runs but no-ops

However, we need to add rate-limiting guards to avoid hammering the exchange:

```python
# Add throttle to _sync_positions_from_exchange()
POSITION_SYNC_INTERVAL = 30  # Only sync every 30s, not every 5s cycle

# In _sync_positions_from_exchange():
now = time.time()
if now - self._last_position_sync < POSITION_SYNC_INTERVAL:
    return
self._last_position_sync = now
```

### 3.6 Modify `_check_tp_fills()` (~line 1465)

The existing TP fill checker needs to handle the safety net case. If the safety net fires (bot-side TP didn't catch it), it processes normally. If the bot-side TP already handled it, the safety net order won't exist anymore.

```python
def _check_tp_fills(self):
    """Poll exchange for safety net TP order fills.
    
    When BOT_SIDE_TP_ENABLED, the exchange order is a wide safety net.
    Bot-side TP handles normal fills; this only catches crash recovery.
    """
    for sym, cs in list(self.coins.items()):
        if not cs.tp_order_id:
            continue
        try:
            result = self.client.check_order_status(sym, cs.tp_order_id)
            if result.get("filled"):
                if BOT_SIDE_TP_ENABLED:
                    logger.warning(
                        f"SAFETY NET fired for {sym}! "
                        f"Bot-side TP did not catch this. Fill: ${result.get('price', 0):.6f}"
                    )
                    send_telegram(
                        f"⚠️ {TG_PREFIX} <b>Safety Net Fired</b>\n"
                        f"Symbol: {sym}\n"
                        f"Bot-side TP missed — safety net caught the fill.\n"
                        f"Fill: ${result.get('price', 0):.6f}"
                    )
                # Cancel any pending bot-side limit sell
                if cs.bot_tp_limit_order_id:
                    self.client.cancel_tp_order(sym, cs.bot_tp_limit_order_id)
                    cs.bot_tp_limit_order_id = None
                # Reset bot-side state
                cs.bot_tp_activated = False
                cs.bot_tp_peak_price = 0.0
                cs.bot_tp_trailing_stop = 0.0
                self._handle_tp_fill(sym, cs, result)
        except Exception as e:
            logger.error(f"TP check failed for {sym}: {e}")
```

### 3.7 State Persistence

Add bot-side TP fields to `_save_state()` and `_load_state()` so they survive restarts:

In `CoinState.to_dict()`:
```python
"bot_tp_activated": self.bot_tp_activated,
"bot_tp_peak_price": self.bot_tp_peak_price,
"bot_tp_trailing_stop": self.bot_tp_trailing_stop,
"bot_tp_limit_order_id": self.bot_tp_limit_order_id,
"bot_tp_limit_placed_at": self.bot_tp_limit_placed_at,
```

In state restoration (~line 900):
```python
cs.bot_tp_activated = cs_data.get("bot_tp_activated", False)
cs.bot_tp_peak_price = cs_data.get("bot_tp_peak_price", 0.0)
cs.bot_tp_trailing_stop = cs_data.get("bot_tp_trailing_stop", 0.0)
cs.bot_tp_limit_order_id = cs_data.get("bot_tp_limit_order_id", None)
cs.bot_tp_limit_placed_at = cs_data.get("bot_tp_limit_placed_at", 0.0)
```

### 3.8 Cleanup on Deal Close

In `_handle_tp_fill()` (~line 1870, existing cleanup section), add:

```python
cs.bot_tp_activated = False
cs.bot_tp_peak_price = 0.0
cs.bot_tp_trailing_stop = 0.0
cs.bot_tp_limit_order_id = None
cs.bot_tp_limit_placed_at = 0.0
```

## 4. Edge Cases & Safety

### 4.1 Bot Crash During Active Trail

**Scenario**: Bot is tracking a peak at $1.95 with stop at $1.946, then crashes.

**Handling**: Safety net trailing stop (1.0% callback) is on the exchange. If price drops 1% from peak, it fires. On restart, `_recover_tp_orders()` checks if the safety net filled and processes accordingly. The `_reconcile_trades_on_startup()` method also catches any fills missed during downtime.

**Residual risk**: If price drops between 0.2% and 1.0% from peak while bot is down, the position stays open until bot restarts or safety net fires. This is a small window and the safety net still protects against large drops.

### 4.2 Price Gaps Through Both Levels

**Scenario**: Price gaps down 2% in one tick (exchange outage, flash crash).

**Handling**: Safety net fires with a market sell — same as current behavior. No worse than today.

### 4.3 Bot-Side Limit Sell Doesn't Fill

**Scenario**: Limit sell placed at $1.946 but best bid is $1.940.

**Handling**: After `LIMIT_SELL_TIMEOUT_SECS` (60s), the bot cancels the limit sell and sends a market sell. This is the same as current behavior but with 60 extra seconds of trying for a better fill. The `LIMIT_SELL_PRICE_BUFFER` (0.05%) helps — the limit is placed at $1.945 instead of $1.946, making it more likely to fill immediately.

### 4.4 Race Condition: Safety Net and Bot-Side TP Fire Simultaneously

**Scenario**: Price drops quickly, bot-side TP places a limit sell while safety net also triggers.

**Handling**: One of two outcomes:
1. Limit sell fills first → `_bot_side_tp_check()` detects fill, cancels safety net
2. Safety net fills first → `_check_tp_fills()` detects fill, cancels pending limit sell

Both paths call `_handle_tp_fill()` which handles cleanup. The exchange won't fill both because the position is closed after the first fill — the second order becomes unfillable (no position to close).

### 4.5 Multiple Coins Polling

**Scenario**: 3 coins active, each needs a price check every 5 seconds.

**Handling**: Each `fetch_ticker_price()` call takes ~100-200ms. With 3 coins, the full poll takes ~0.5-1s, well within the 5s budget. If we scale to more coins, we can batch ticker fetches (Aster supports `fetch_tickers()` for multiple symbols in one call).

### 4.6 Engine TP Skip Logic

**Current code** (line ~2240): When the engine generates a `SELL` action for TP, `_execute_action()` checks `if cs.tp_order_id and "TP" in reason` and skips it. This still works because the safety net order ID is stored in `cs.tp_order_id`. The engine's candle-based TP detection is still a valid third layer of defense — if both bot-side and safety net somehow fail, the hourly candle check catches it and executes a market sell.

### 4.7 Short Positions (Future)

The current live bot is long-only (`SHORT_OPEN`/`SHORT_CLOSE` are explicitly rejected at line ~2300). When shorts are enabled:

- `_bot_side_tp_check()` needs a mirror path: track trough low, trigger when price rises 0.2% above trough, place limit buy
- Safety net becomes a `TRAILING_STOP_MARKET` buy order
- Same two-layer hybrid architecture applies

**No code for shorts in this spec** — implement when short support is enabled.

## 5. Monitoring & Observability

### 5.1 New Telegram Notifications

| Event | Message |
|-------|---------|
| Bot-side TP activated | `🎯 [V14-PM] Bot-Side TP Activated: {sym} at ${price}` |
| Bot-side TP triggered | `🎯 [V14-PM] Bot-Side TP Triggered: {sym} — limit sell placed` |
| Limit sell filled | Normal deal closed notification (existing) |
| Limit sell timeout | `⚠️ [V14-PM] TP Limit Timeout: {sym} — escalating to market` |
| Safety net fired | `⚠️ [V14-PM] Safety Net Fired: {sym} — bot-side TP missed` |
| Limit placement failed | `🚨 [V14-PM] TP Escalation Failed: {sym} — manual intervention` |

### 5.2 Status.json Additions

Add to coin status output for dashboard:
```python
"bot_tp_activated": cs.bot_tp_activated,
"bot_tp_peak_price": cs.bot_tp_peak_price,
"bot_tp_trailing_stop": cs.bot_tp_trailing_stop,
"bot_tp_pending_limit": cs.bot_tp_limit_order_id is not None,
```

### 5.3 Logging

All bot-side TP events log at INFO level. Price polls log at DEBUG to avoid log spam.

## 6. API Rate Impact

| Operation | Current Rate | New Rate | Notes |
|-----------|-------------|----------|-------|
| `fetch_ticker_price()` | 1/65s per coin | 1/5s per coin | 3 coins × 12/min = 36 calls/min |
| `fetch_open_positions()` | 1/65s | 1/30s | Throttled by POSITION_SYNC_INTERVAL |
| `fetch_balance()` | 1/65s | 1/30s | Same throttle |
| `check_order_status()` | 1/65s per coin | 1/65s per coin | Unchanged |

Aster rate limit: 1200 requests/minute. New total: ~50-60 requests/minute. Well within limits.

Hyperliquid rate limit: 1200 requests/minute (info endpoint: 120/min for positions). Same approach works with minor adjustment to batch position/balance calls.

## 7. Rollback Plan

Set `BOT_SIDE_TP_ENABLED = False` to revert to current behavior. The safety net trailing stop (stored in `cs.tp_order_id`) becomes the primary TP again. All bot-side state fields are ignored. No code removal needed.

## 8. Testing Strategy

Since this goes directly to the live bot with minimal capital ($460):

1. **Phase 1**: Deploy with `BOT_SIDE_TP_ENABLED = True`. Monitor first 5-10 trades.
2. **Phase 2**: Compare limit sell fill prices vs previous trailing stop market fills.
3. **Success criteria**: >90% of bot-side TP fills within 0.1% of trigger price (vs current avg 0.5-1% slippage).
4. **Abort criteria**: Any safety net fire without corresponding bot crash, or limit sell timeout rate >20%.

## 9. Files Modified

| File | Changes |
|------|---------|
| `run_v14_portfolio_live_aster.py` | Constants, CoinState fields, `_bot_side_tp_check()`, `_place_tp_order()`, main loop timing, `_check_tp_fills()`, state persistence, cleanup |

**No other files modified.** The change is fully contained within the live PM runner. The V14 DCA engine, lifecycle engine, trade tracker, router, and dashboard are untouched.

## 10. Dependency Map

```
_bot_side_tp_check() [NEW]
  ├── calls: client.fetch_ticker_price()      [existing, no changes]
  ├── calls: client.place_limit_sell()         [existing, no changes]  
  ├── calls: client.cancel_tp_order()          [existing, no changes]
  ├── calls: client.create_market_sell()        [existing, no changes]
  ├── calls: client.check_order_status()        [existing, no changes]
  ├── calls: _handle_tp_fill()                  [existing, no changes]
  └── writes: CoinState bot_tp_* fields         [NEW fields]

_place_tp_order() [MODIFIED]
  ├── calls: client.place_trailing_stop_sell()  [existing, wider callback param]
  └── writes: CoinState bot_tp_* fields         [reset on new TP]

Main loop [MODIFIED]
  ├── sleep reduced: 65s → 5s
  ├── adds: last_bot_tp_check timer
  └── adds: _bot_side_tp_check() call

_check_tp_fills() [MODIFIED]  
  └── adds: safety net fire detection + bot-side state cleanup

_sync_positions_from_exchange() [MODIFIED]
  └── adds: POSITION_SYNC_INTERVAL throttle (30s)

State persistence [MODIFIED]
  ├── _save_state(): adds bot_tp_* fields
  └── _load_state(): restores bot_tp_* fields
```

No upstream or downstream dependencies are affected. The engine still generates TP actions, they're still skipped when an exchange order exists (safety net counts), and `_handle_tp_fill()` processes fills identically regardless of source.
