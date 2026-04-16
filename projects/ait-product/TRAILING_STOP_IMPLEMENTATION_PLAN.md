# Trailing Stop TP — Comprehensive Implementation Plan
_Created: 2026-04-13 | Updated: 2026-04-15 | Status: PHASE 1 COMPLETE (LIVE)_

---

## 1. Summary

Replace the fixed 1.48% limit-sell TP with a trailing stop that activates at +1.5%.
After activation, the stop trails price upward with a **0.2% callback distance**.

**Zero-downside design:** Trail only activates after the current TP level is reached.
Worst case = 1.3% profit (activation minus callback). Best case = captures runaway moves.

**Implementation order:** Live bot first (exchange handles the trailing stop natively),
then paper bot (requires candle-based simulation in the shared engine).

### Parameter Change History
- **2026-04-13:** Initial design with 0.5% callback
- **2026-04-15:** Changed to 0.2% callback based on:
  - 365-day backtest against actual candle data: 0.2% = $93,338 (+274% vs fixed TP)
  - Aster exchange constraint: only accepts callback rates in 0.1% increments (0.25% rejected)
  - 0.2% is the best-performing Aster-compatible option

---

## 2. Trade Score Impact — NONE

The trailing stop should **NOT** affect the DCA cycle scanner trade score. Rationale:

- The scanner scores coins by **cycle velocity** — how fast they complete buy-low-sell-high
  cycles. This is fundamentally about entry frequency and grid efficiency.
- The trailing stop affects **exit quality**, not cycle speed. A coin that trails from
  +1.5% to +3% before exiting takes *longer* to close the deal, which would actually
  *lower* its deals/week score.
- The scanner's job is to find fast cyclers. The trailing stop's job is to extract more
  from each cycle. These are independent optimizations.
- If we scored based on trailing TP, the scanner would favor slow-moving coins that
  occasionally spike — the opposite of what we want for rapid DCA cycling.

**Decision: Scanner unchanged. Trailing stop is icing on the cake.**

---

## 3. Component Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    LIVE BOT (Phase 1)                       │
│                                                             │
│  _place_tp_order()                                          │
│    │ Was: create_limit_sell_order(qty, tp_price)            │
│    │ Now: create_order(TRAILING_STOP_MARKET,                │
│    │        activationPrice=tp_price, callbackRate=0.5)     │
│    │                                                        │
│  _check_tp_fills()    — NO CHANGE (polls order status)      │
│  _handle_tp_fill()    — MINOR (fill price already dynamic)  │
│  _recover_tp_orders() — MINOR (recognize trailing type)     │
│  LIVE GUARD           — NO CHANGE (blocks engine TP sells)  │
│                                                             │
│  AsterPerpClient                                            │
│    + place_trailing_stop_sell()  — NEW METHOD                │
│                                                             │
│  CoinState                                                  │
│    + tp_type: "trailing" | "limit"                          │
│    + tp_activation_price: float                             │
│    + trailing_callback_pct: float                           │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                   PAPER BOT (Phase 2)                       │
│                                                             │
│  v14_dca_engine.py — _long_dca_tick / _short_dca_tick       │
│    Current: if candle_high >= long_tp → SELL at long_tp     │
│    New:     if candle_high >= long_tp → activate trail      │
│             track peak, check callback against candle_low   │
│             if triggered → SELL at trail_trigger price      │
│                                                             │
│  New engine state fields:                                   │
│    + long_trailing_active: bool                             │
│    + long_trailing_peak: float                              │
│    + short_trailing_active: bool                            │
│    + short_trailing_peak: float                             │
│                                                             │
│  v14_lifecycle_engine.py — snapshot/restore                  │
│    + Serialize/deserialize trailing state fields             │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                   NOT CHANGED                               │
│                                                             │
│  v14_cycle_scanner.py    — No change (scores cycle speed)   │
│  v14_capital_manager.py  — No change (capital routing)      │
│  Capital accounting      — No change (GAP-13 fix intact)    │
│  Regime detection        — No change                        │
│  Telegram commands       — No change (PAUSE/RESUME etc.)    │
│  Liquidity filter        — No change                        │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                   DASHBOARD (Phase 3)                       │
│                                                             │
│  status.json per-coin additions:                            │
│    tp_type: "trailing" | "limit"                            │
│    tp_activation_price: float                               │
│    trailing_callback_pct: float                             │
│                                                             │
│  Dashboard display:                                         │
│    Active positions table: "Trail 0.5%" badge               │
│    Tooltip on TP price: "Activates at $X, trails 0.5%"     │
│    Trade log: actual fill price (already shows this)        │
└─────────────────────────────────────────────────────────────┘
```

---

## 4. Phase 1 — Live Bot Implementation

### 4.1 Config Constants

File: `run_v14_portfolio_live_aster.py` (top of file, near other constants)

```python
# ── Trailing Stop TP ─────────────────────────────────────────
TRAILING_STOP_ENABLED = True          # Feature flag (set False to revert to limit TP)
TRAILING_CALLBACK_PCT = 0.2           # 0.2% trail distance after activation (Aster min increment: 0.1%)
```

### 4.2 AsterPerpClient — New Method

File: `run_v14_portfolio_live_aster.py`, class `AsterPerpClient`

```python
def place_trailing_stop_sell(self, db_symbol: str, qty: float,
                             activation_price: float,
                             callback_rate: float = 0.2) -> Optional[str]:
    """Place a TRAILING_STOP_MARKET sell order on Aster.

    The order activates when price reaches activation_price, then trails
    upward by callback_rate %. If price drops callback_rate % from peak,
    a market sell triggers.

    Returns: order_id or None
    """
    sym = self._aster_symbol(db_symbol)
    base = db_symbol.split("/")[0]
    exchange_qty = qty * 1000 if base in ("PEPE", "BONK", "FLOKI") else qty
    if self.dry_run:
        return f"dry_run_trail_{db_symbol}_{int(time.time())}"
    try:
        logger.info(
            f"PLACE TRAILING STOP SELL {db_symbol} qty={qty:.8f} "
            f"activation=${activation_price:.8f} callback={callback_rate}%"
        )
        order = self._exchange.create_order(
            symbol=sym,
            type="TRAILING_STOP_MARKET",
            side="sell",
            amount=exchange_qty,
            params={
                "quantity": str(exchange_qty),
                "activationPrice": str(activation_price),
                "callbackRate": str(callback_rate),
                "positionSide": "BOTH",
                "reduceOnly": "true",
            }
        )
        oid = order.get("id")
        logger.info(f"Trailing stop order placed: {oid}")
        return oid
    except Exception as e:
        logger.error(f"place_trailing_stop_sell({db_symbol}) failed: {e}")
        return None
```

### 4.3 _place_tp_order() — Updated

File: `run_v14_portfolio_live_aster.py`, method `_place_tp_order`

The ONLY change is at the bottom where the order is placed. All the exchange-entry
price computation, qty fetching, and cancel logic stays exactly the same.

```python
# Replace existing order placement block:

# --- BEFORE (limit sell) ---
# oid = self.client.place_limit_sell(sym, qty, tp_price)

# --- AFTER (trailing stop with limit fallback) ---
if TRAILING_STOP_ENABLED:
    oid = self.client.place_trailing_stop_sell(
        sym, qty, tp_price, TRAILING_CALLBACK_PCT
    )
    if oid:
        cs.tp_order_id = oid
        cs.tp_limit_price = tp_price       # activation price (for status/display)
        cs.tp_type = "trailing"
        cs.tp_activation_price = tp_price
        cs.trailing_callback_pct = TRAILING_CALLBACK_PCT
        logger.info(
            f"Trailing TP placed for {sym}: qty={qty:.4f} "
            f"activation=${tp_price:.8f} trail={TRAILING_CALLBACK_PCT}% | order={oid}"
        )
    else:
        # Fallback: place regular limit sell
        logger.warning(f"Trailing stop failed for {sym}, falling back to limit TP")
        oid = self.client.place_limit_sell(sym, qty, tp_price)
        if oid:
            cs.tp_order_id = oid
            cs.tp_limit_price = tp_price
            cs.tp_type = "limit"
else:
    oid = self.client.place_limit_sell(sym, qty, tp_price)
    if oid:
        cs.tp_order_id = oid
        cs.tp_limit_price = tp_price
        cs.tp_type = "limit"
```

### 4.4 CoinState — New Fields

File: `run_v14_portfolio_live_aster.py`, class `CoinState`

```python
self.tp_type: str = "trailing"                  # "trailing" or "limit"
self.tp_activation_price: Optional[float] = None # Price where trail activates
self.trailing_callback_pct: float = 0.5          # Trail distance %
```

Add to `_to_dict()` for state persistence:
```python
"tp_type": self.tp_type,
"tp_activation_price": self.tp_activation_price,
"trailing_callback_pct": self.trailing_callback_pct,
```

Add to state restoration (in `_restore_state` / coin loading):
```python
cs.tp_type = cs_data.get("tp_type", "limit")
cs.tp_activation_price = cs_data.get("tp_activation_price")
cs.trailing_callback_pct = cs_data.get("trailing_callback_pct", 0.5)
```

### 4.5 _check_tp_fills() — No Structural Change

The existing polling already works:
```python
result = self.client.check_order_status(sym, cs.tp_order_id)
if result and result["status"] == "closed":
    self._handle_tp_fill(sym, cs, result)
```

`TRAILING_STOP_MARKET` orders return the same status structure when filled.

### 4.6 _handle_tp_fill() — Minor

Already uses exchange fill price:
```python
fill_price = fill_result.get("price") or fill_result.get("average")
```

Add logging to capture the trail benefit:
```python
# After computing PnL:
if cs.tp_type == "trailing" and cs.tp_activation_price:
    trail_extra = (fill_price - cs.tp_activation_price) * qty
    if trail_extra > 0:
        logger.info(f"Trail bonus for {sym}: +${trail_extra:.2f} above fixed TP")
```

### 4.7 _recover_tp_orders() — Minor

The existing recovery scans for open sell orders on the exchange. Trailing stops
show as open orders too. One small check needed:

In Phase 2 (orphan scan), when adopting an order, detect if it's a trailing stop:
```python
if tp_order.get("info", {}).get("type") == "TRAILING_STOP_MARKET":
    cs.tp_type = "trailing"
else:
    cs.tp_type = "limit"
```

### 4.8 status.json — Per-Coin Additions

```python
# In _write_status(), per-coin data:
"tp_type": cs.tp_type,
"tp_activation_price": cs.tp_activation_price,
"trailing_callback_pct": cs.trailing_callback_pct,
```

### 4.9 LIVE GUARD — No Change

The LIVE GUARD pattern blocks engine TP sells when `cs.tp_order_id` is set.
This works identically for trailing stop orders — the order ID is set, so the
engine's candle-based TP detection is suppressed. The exchange trailing stop
is the sole TP mechanism.

---

## 5. Phase 2 — Paper Bot Engine Simulation

### 5.1 Why It's Separate

The paper bot doesn't place exchange orders. It simulates TP by checking candle
prices against the TP level. To accurately model trailing stops, the engine needs
new state and logic.

### 5.2 v14_dca_engine.py — Long DCA Tick

Current TP check (lines ~358-377):
```python
if tp_check_price >= self.long_tp:
    fill_price = self.long_tp  # Fixed TP
    → SELL at fill_price
```

New trailing TP simulation:
```python
# Trailing stop state (added to __init__):
# self.long_trailing_active = False
# self.long_trailing_peak = 0.0

if self.long_trailing_active:
    # Trail is active — track peak high, check for callback trigger
    self.long_trailing_peak = max(self.long_trailing_peak, high if high else price)
    trail_trigger = self.long_trailing_peak * (1 - cfg.TRAILING_CALLBACK_PCT / 100)
    check_low = low if low is not None and not np.isnan(low) else price
    if check_low <= trail_trigger:
        fill_price = trail_trigger  # Market sell at trail trigger
        fee = self._charge_fee(self.long_coins * fill_price, is_taker=True)  # Trail = market/taker
        → SELL at fill_price (same PnL calc as current)
        self.long_trailing_active = False
        self.long_trailing_peak = 0.0
elif tp_check_price >= self.long_tp:
    if cfg.TRAILING_STOP_ENABLED:
        # Activate trail — price just hit the TP level
        self.long_trailing_active = True
        self.long_trailing_peak = high if high else price
        # Check if callback already triggered in same candle (spike then drop)
        trail_trigger = self.long_trailing_peak * (1 - cfg.TRAILING_CALLBACK_PCT / 100)
        check_low = low if low is not None and not np.isnan(low) else price
        if check_low <= trail_trigger:
            fill_price = trail_trigger
            fee = self._charge_fee(self.long_coins * fill_price, is_taker=True)
            → SELL at fill_price
            self.long_trailing_active = False
            self.long_trailing_peak = 0.0
    else:
        # Original fixed TP behavior
        fill_price = self.long_tp
        → SELL at fill_price
```

### 5.3 v14_dca_engine.py — Short DCA Tick

Mirror of long: track peak low, trail upward (for shorts, price falling is profit).

```python
# self.short_trailing_active = False
# self.short_trailing_peak = float('inf')

if self.short_trailing_active:
    self.short_trailing_peak = min(self.short_trailing_peak, low if low else price)
    trail_trigger = self.short_trailing_peak * (1 + cfg.TRAILING_CALLBACK_PCT / 100)
    check_high = high if high is not None and not np.isnan(high) else price
    if check_high >= trail_trigger:
        fill_price = trail_trigger
        → BUY BACK at fill_price
        self.short_trailing_active = False
        self.short_trailing_peak = float('inf')
elif tp_check_price <= self.short_tp:
    if cfg.TRAILING_STOP_ENABLED:
        self.short_trailing_active = True
        self.short_trailing_peak = low if low else price
        # Same-candle callback check...
    else:
        fill_price = self.short_tp
        → BUY BACK at fill_price
```

### 5.4 V14Config — New Constants

```python
TRAILING_STOP_ENABLED = True      # Feature flag
TRAILING_CALLBACK_PCT = 0.5       # 0.5% trail distance
```

### 5.5 State Persistence

`snapshot_state()` additions:
```python
'long_trailing_active': eng.long_trailing_active,
'long_trailing_peak': eng.long_trailing_peak,
'short_trailing_active': eng.short_trailing_active,
'short_trailing_peak': eng.short_trailing_peak,
```

`restore_state()` additions:
```python
eng.long_trailing_active = state.get('long_trailing_active', False)
eng.long_trailing_peak = state.get('long_trailing_peak', 0.0)
eng.short_trailing_active = state.get('short_trailing_active', False)
eng.short_trailing_peak = state.get('short_trailing_peak', float('inf'))
```

### 5.6 Fee Model Change

With trailing stops, the TP exit is a **market order** (taker), not a limit order (maker).
Fee changes from `MAKER_FEE` (0.02%) to `TAKER_FEE` (0.035% on Aster).

This slightly reduces profit per deal (~0.015% hit on the exit side), but the
trailing stop's extra capture far exceeds this cost.

---

## 6. Phase 3 — Dashboard

### 6.1 Active Positions Table

Add a small badge next to the TP price for positions with trailing stops:

```javascript
// In position row rendering:
var tpInfo = coin.next_tp_price ? '$' + coin.next_tp_price.toFixed(4) : '--';
if (coin.tp_type === 'trailing') {
    tpInfo += ' <span style="font-size:.6rem;color:var(--accent2)">TRAIL ' +
              (coin.trailing_callback_pct || 0.5) + '%</span>';
}
```

### 6.2 Completed Trades

The trade log already shows actual fill price. No change needed — trailing fills
will naturally show the higher exit price.

### 6.3 Status Card

Add a "Trailing TP" indicator in the header badges:
```javascript
if (data.trailing_enabled) {
    badges += '<span class="header-badge" style="...">Trail 0.5%</span>';
}
```

---

## 7. Files Modified (summary)

| File | Phase | Changes |
|------|-------|---------|
| `run_v14_portfolio_live_aster.py` | 1 | Config constants, `AsterPerpClient.place_trailing_stop_sell()`, `_place_tp_order()` update, `CoinState` fields, `_handle_tp_fill()` trail bonus log, `_recover_tp_orders()` type detection, `_write_status()` fields |
| `engine/v14_dca_engine.py` | 2 | `V14Config` constants, `__init__` trailing state, `_long_dca_tick()` trailing sim, `_short_dca_tick()` trailing sim, fee model (taker on trail exit) |
| `v14_lifecycle_engine.py` | 2 | `snapshot_state()` + `restore_state()` trailing fields |
| `docs/dashboardV14PM.html` | 3 | Trail badge on positions, header badge |
| `V14PM_SYSTEM_ARCHITECTURE.md` | 3 | Update §5.2, §6.8.2 |
| `V14PM_CHANGE_CONTROL.md` | 3 | New entry |

---

## 8. Rollback Plan

Set `TRAILING_STOP_ENABLED = False` in the live bot config. Next TP placement
will use the limit sell path. Existing trailing stop orders on the exchange stay
active until they fill or are manually cancelled.

For complete rollback: restart bot with the flag off. New positions get limit TPs.
Existing trailing stops fill normally (exchange handles them).

---

## 9. Testing Checklist

### Phase 1 (Live) — COMPLETE 2026-04-15
- [x] Aster accepts TRAILING_STOP_MARKET orders (validated 2026-04-13)
- [x] Aster callback rate constraint discovered: 0.1% increments only (0.25% rejected)
- [x] Callback rate optimized to 0.2% via 365-day backtest ($93K vs $25K fixed TP)
- [x] place_trailing_stop_sell() works with PEPE/BONK/FLOKI qty scaling
- [x] _check_tp_fills() correctly detects trailing stop fill
- [x] _handle_tp_fill() records correct fill price and PnL
- [x] _recover_tp_orders() recognizes trailing stop orders on restart
- [x] Feature flag OFF falls back to limit sell cleanly
- [x] Trailing stop fallback to limit sell when exchange rejects
- [x] State persistence: tp_type, tp_activation_price survive restart
- [x] Git source file protection (.gitignore) prevents sync from deleting code
- [x] Tier cap enforcement fix preserved across restarts

### Phase 2 (Paper) — DEFERRED
_Paper bots continue running on fixed TP. Phase 2 trailing simulation changes were_
_lost in a git reset and will be reimplemented separately. Paper bots are unaffected._
- [ ] Trailing activates when candle high >= long_tp
- [ ] Trail tracks peak correctly across candles
- [ ] Callback triggers sell at correct price
- [ ] Same-candle activation + callback works (spike then drop)
- [ ] Short DCA trailing mirrors long correctly
- [ ] State persists across paper bot restart
- [ ] Fee model uses taker fee for trailing exit

### Phase 3 (Dashboard) — PARTIAL
- [x] Trail badge displays on positions with trailing TP (needs text update to 0.2%)
- [x] Status badge shows trailing enabled
- [ ] Tooltip shows activation price and callback %

---

## 10. Backtest Results (2026-04-15, Actual Candle Data)

365-day window, 5 coins (TAO, ZEC, FET, JTO, HYPE), $50K capital.

| Config | PnL | ROI | vs Fixed | Trades | Win% |
|--------|-----|-----|----------|--------|------|
| Fixed TP 1.5% | $24,983 | 50.0% | baseline | 951 | 99.5% |
| **Trail 1.5/0.2%** | **$93,338** | **186.7%** | **+$68,355 (+274%)** | **1029** | **99.5%** |
| Trail 1.5/0.3% | $88,614 | 177.2% | +$63,631 | 1024 | 99.5% |
| Trail 1.5/0.5% | $75,720 | 151.4% | +$50,736 | 1017 | 99.5% |

**Key findings:**
- 0.2% is the best Aster-compatible callback rate
- Aster rejects 0.25% (only accepts 0.1% increments)
- Worst-case profit at 0.2%: 1.5% activation − 0.2% callback = **1.3%** minimum
- Tighter callback captures more upside on every exit

---

## 11. Git Source File Protection (2026-04-15)

**Root cause of repeated code deletion:** Two git processes fighting over the same remote:
1. OpenClaw cron "Workspace Git Backup" (hourly, `git add -A` + push)
2. Windows task "AIT_DashboardSync" (every 10 min, separate clone, `git reset --soft origin/main`)

**Fix applied:**
- Updated `.gitignore` to exclude all trading bot source code and runtime state
- Pushed to remote so both processes respect it
- Source files now exist only on disk, never in git
- Protected files: `run_v14_*.py`, `v14_capital_manager.py`, `v14_dca_engine.py`, `v14_lifecycle_engine.py`
