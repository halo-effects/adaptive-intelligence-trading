# Trailing Stop TP — Architecture Design
_Created: 2026-04-13 | Updated: 2026-04-15 | Status: LIVE (Phase 1)_

---

## 1. Concept

Replace fixed 1.48% limit-sell TP with a **trailing stop that activates at +1.5%**.

**Mechanism:**
1. After BUY → place a **TRAILING_STOP_MARKET** order with:
   - `activationPrice` = avg_entry × 1.015 (same as current TP)
   - `callbackRate` = 0.2% (trail distance — Aster only accepts 0.1% increments)
2. Price rises past +1.5% → trail activates, follows price up
3. Price pulls back 0.5% from peak → market sell triggers
4. Price never reaches +1.5% → order never activates (position stays open, DCA continues)

**Worst-case guarantee:** Since the trail activates at +1.5%, worst case is 1.5% − 0.2% = **1.3% profit** (vs 1.5% fixed TP). Best case captures runaway moves (avg peak was 3.68% in backtest).

**Parameter history:** Originally designed with 0.5% callback. Changed to 0.2% on 2026-04-15 after 365-day backtest showed 0.2% = $93,338 vs 0.5% = $75,720. Aster rejects 0.25% (only 0.1% increments accepted).

---

## 2. Backtest Results (provided by Brett)

$50K, 103 trades (GRASS/HYPE excluded), 30d:

| Trail % | Extra Profit | Extra % | Notes |
|---------|-------------|---------|-------|
| **0.5%** | **+$6,500** | **+95%** | **Recommended** |
| 0.75% | +$5,746 | +84% | |
| 1.0% | +$5,095 | +74% | |
| 1.5% | +$4,172 | +61% | |
| 2.0% | +$3,479 | +51% | |
| 3.0% | +$3,040 | +44% | |

- 87% of trades (90/103) went past +1.5% — trail activates on almost every trade
- Average peak above entry: 3.68%
- ZEC peaked at 18.55% on one trade
- 13 trades never hit +1.5% — normal TP, no harm

---

## 3. Implementation Scope

### 3.1 Exchange Client (`AsterPerpClient`)

**New method:** `place_trailing_stop_sell()`

```python
def place_trailing_stop_sell(self, db_symbol: str, qty: float,
                             activation_price: float,
                             callback_rate: float = 0.5) -> Optional[str]:
    """Place a TRAILING_STOP_MARKET sell order on Aster.

    Args:
        db_symbol: e.g. "TAO/USDT"
        qty: Position size to sell
        activation_price: Price at which trail activates (entry × 1.015)
        callback_rate: Trail distance in % (0.5 = 0.5%)

    Returns: order_id or None
    """
    sym = self._aster_symbol(db_symbol)
    # Aster (Binance-fork) supports TRAILING_STOP_MARKET with:
    #   activationPrice + callbackRate params
    order = self._exchange.create_order(
        symbol=sym,
        type='TRAILING_STOP_MARKET',
        side='sell',
        amount=qty,
        params={
            'activationPrice': activation_price,
            'callbackRate': callback_rate,
            'positionSide': 'BOTH',
            'reduceOnly': True,
        }
    )
    return order.get('id')
```

**Verification needed:**
- [ ] Confirm Aster supports `TRAILING_STOP_MARKET` order type (Binance-fork, likely yes)
- [ ] Confirm `activationPrice` + `callbackRate` params work via ccxt
- [ ] Test with a small order on live exchange

### 3.2 Live Bot (`run_v14_portfolio_live_aster.py`)

**Changes to `_place_tp_order()`:**

Current flow:
```
BUY fill → cancel old TP → place limit sell @ entry × 1.015 → store tp_order_id
```

New flow:
```
BUY fill → cancel old TP → place TRAILING_STOP_MARKET
    activation = exchange_entry × (1 + TP_PCT)     # same as current TP price
    callback   = TRAILING_CALLBACK_PCT              # 0.5% default
    → store tp_order_id
```

The change is **minimal** — only the order type and params change. Everything else stays:
- `tp_order_id` still tracks the order (for cancel/fill check)
- `_check_tp_fills()` still polls for fill status
- `_recover_tp_orders()` still recovers on restart
- `_handle_tp_fill()` still processes the fill

**New config constants:**
```python
TRAILING_STOP_ENABLED = True          # Feature flag
TRAILING_CALLBACK_PCT = 0.5           # 0.5% trail
```

**CoinState additions:**
```python
self.tp_type: str = "trailing"        # "limit" or "trailing" (for status/dashboard)
self.tp_activation_price: float = 0   # Price where trail activates
```

### 3.3 Fill Price Handling

**Critical difference:** With a limit sell, fill price = limit price (exact).
With a trailing stop market, fill price = market price at trigger (varies).

Current `_handle_tp_fill()` already handles this correctly:
```python
fill_price = fill_result.get("price") or fill_result.get("average")
```
This works for both limit and market fills — the exchange returns the actual execution price.

**No change needed** to PnL calculation or trade recording.

### 3.4 Paper Bot (`run_v14_portfolio_paper.py` / `v14_lifecycle_engine.py`)

Paper bots don't place exchange orders. They simulate TP via candle data.

**Current paper TP logic (in `v14_dca_engine.py`):**
```python
if candle_high >= self.long_tp:  # Fixed TP hit
    → SELL at self.long_tp price
```

**New trailing stop simulation:**
```python
if self.trailing_active:
    # Trail is active — track peak and check for callback
    self.trailing_peak = max(self.trailing_peak, candle_high)
    trail_trigger = self.trailing_peak * (1 - TRAILING_CALLBACK_PCT / 100)
    if candle_low <= trail_trigger:
        → SELL at trail_trigger price
elif candle_high >= self.long_tp:
    # Price hit activation threshold — activate trail
    self.trailing_active = True
    self.trailing_peak = candle_high
    # Check if callback already triggered in same candle
    trail_trigger = self.trailing_peak * (1 - TRAILING_CALLBACK_PCT / 100)
    if candle_low <= trail_trigger:
        → SELL at trail_trigger price
```

**New engine state fields:**
```python
self.trailing_active: bool = False
self.trailing_peak: float = 0.0
```

These need to be added to `snapshot_state()` / `restore_state()` for persistence.

### 3.5 Scanner (`v14_cycle_scanner.py`)

The scanner runs its own DCA simulation. It needs the same trailing stop logic
as the paper bot to accurately score coins with the new exit mechanism.

**Impact:** Scores will change — coins with momentum (TAO, ZEC) will score higher
because the scanner will capture the extra profit from trails.

### 3.6 Dashboard (`dashboardV14PM.html`)

- Show "Trail" badge on active positions where trailing stop is enabled
- Show `tp_activation_price` and `trailing_peak` in coin detail
- Show `tp_type: "trailing"` vs `"limit"` in status

### 3.7 Status/State Files

`status.json` per-coin additions:
```json
{
    "tp_type": "trailing",
    "tp_activation_price": 281.67,
    "trailing_callback_pct": 0.5,
    "trailing_peak": null
}
```

`state.json` engine state additions:
```json
{
    "trailing_active": false,
    "trailing_peak": 0.0
}
```

---

## 4. Component Impact Matrix

| Component | Change | Risk | Effort |
|-----------|--------|------|--------|
| `AsterPerpClient` | New `place_trailing_stop_sell()` method | **Medium** — needs exchange validation | 1h |
| `_place_tp_order()` | Switch from limit sell to trailing stop | **Low** — same flow, different order type | 30min |
| `_check_tp_fills()` | No change — already checks order status generically | **None** | 0 |
| `_handle_tp_fill()` | Minor — fill price already uses exchange actual | **Low** | 15min |
| `_recover_tp_orders()` | Minor — needs to recognize trailing stop order type | **Low** | 15min |
| `CoinState` | Add `tp_type`, `tp_activation_price` | **Low** | 15min |
| `v14_dca_engine.py` | Add trailing stop simulation for paper | **Medium** — new logic | 1h |
| `v14_lifecycle_engine.py` | Pass trailing params through | **Low** | 15min |
| `v14_cycle_scanner.py` | Add trailing stop to DCA simulation | **Medium** — same as engine | 1h |
| `state.json` | Add trailing fields | **Low** — backward compatible | 15min |
| `status.json` | Add trailing fields | **Low** | 15min |
| Dashboard | Show trail status | **Low** | 30min |
| Architecture doc | Update §5.2, §6.8.2 | **Low** | 30min |

**Total estimated effort: ~6 hours**

---

## 5. Risk Analysis

### 5.1 What Could Go Wrong

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Aster doesn't support TRAILING_STOP_MARKET | Low (Binance-fork) | **Blocks implementation** | Test first with small order |
| Trailing stop fills at worse price than limit | Medium (market order) | **Slight slippage** | Trail activates at +1.5% so worst case ≈ +1.0% (still profitable) |
| Bot restart loses track of trailing state | Low | **Missed trail** | Exchange holds the order; `_recover_tp_orders()` handles it |
| Paper bot simulation inaccuracy (1h candles) | Medium | **Scores may differ from live** | 1h candles capture most intra-candle movement; known limitation |
| Trailing stop on exchange gets cancelled by exchange | Low | **Position orphaned** | Existing TP recovery already handles this (places new order if missing) |

### 5.2 Zero-Downside Proof

The trailing stop ONLY activates after price hits +1.5% (our current TP level).

- **If price never hits +1.5%:** Trail never activates. DCA continues as normal. Same as today.
- **If price hits +1.5% and immediately reverses 0.5%:** Trail sells at ~+1.0%. Slightly worse than the fixed 1.48% TP. This is the ONLY downside scenario.
- **If price hits +1.5% and continues up:** Trail follows, captures extra profit. This happened on 87% of trades.

**Net expected value is strongly positive.** The 87% that continue past +1.5% far outweigh the slim margin lost on the few that reverse immediately after activation.

### 5.3 The Slippage Consideration

Current: Limit sell at exact TP price → guaranteed fill at TP price (or better)
New: Trailing stop market sell → fill at market price when trail triggers

The market sell could have slight slippage, especially on thin Aster books (see liquidity filter work). For coins with >$100K daily volume, this is negligible. For low-liquidity coins, the liquidity filter already excludes them.

---

## 6. Rollout Plan

### Phase 1: Validate Exchange Support (1h)
- Place a test TRAILING_STOP_MARKET order on Aster (tiny size, test coin)
- Confirm `activationPrice` + `callbackRate` params work
- Confirm order shows up in `fetch_open_orders()` and `check_order_status()`

### Phase 2: Paper Bot Implementation (2h)
- Add trailing stop simulation to `v14_dca_engine.py`
- Update `v14_lifecycle_engine.py` pass-through
- Update state persistence
- Run parallel: compare trailing TP vs fixed TP on same candle data

### Phase 3: Live Bot Implementation (2h)
- Add `place_trailing_stop_sell()` to `AsterPerpClient`
- Update `_place_tp_order()` with feature flag
- Update CoinState, status.json, state.json
- Test on live with next BUY fill (feature flag ON)

### Phase 4: Scanner + Dashboard (1h)
- Update scanner DCA sim with trailing logic
- Update dashboard to show trail status
- Update architecture doc

### Phase 5: Monitor (ongoing)
- Compare actual trail fills vs theoretical fixed TP
- Track slippage on trailing stop market orders
- Adjust callback rate if needed (0.5% → 0.75% etc.)

---

## 7. Decision Points for Brett

1. **Confirm trail %:** 0.5% recommended. Should this be configurable per Telegram command?
2. **Activation threshold:** Currently same as TP (1.5%). Should this be separately configurable?
3. **Feature flag:** Start with `TRAILING_STOP_ENABLED = True` by default, or require explicit enable?
4. **Fallback on exchange error:** If trailing stop placement fails, fall back to limit sell (current behavior)?
5. **Confirm Aster support first?** I can place a tiny test order right now to validate.

---

## 8. Relationship to Existing Architecture

The trailing stop is a **drop-in replacement** for the resting limit sell. It:
- Uses the same `tp_order_id` tracking infrastructure
- Uses the same `_check_tp_fills()` polling loop
- Uses the same `_handle_tp_fill()` PnL calculation
- Uses the same `_recover_tp_orders()` crash recovery
- Uses the same exchange-as-truth principle (fill price from exchange, not engine)

The only net-new logic is the **paper bot simulation** of trailing behavior, which doesn't exist today because the paper bot can't place exchange orders.

This is architecturally clean — the existing TP pipeline was designed to be order-type-agnostic.
