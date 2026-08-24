# V14PM Live Bot — Code Map

**File:** `trading/spot/run_v14_portfolio_live_aster.py` (~4900 lines)
**Supplements:** `v14-system-spec.md` (which covers overall architecture but not PM bot internals)
**Last verified:** 2026-08-21 (against live code, line numbers confirmed)

---

## 1. Class Structure

| Class | Line | Purpose |
|---|---|---|
| `TradeTracker` | 197 | Deal lifecycle tracking, CSV persistence, MAE tracking |
| `AsterPerpClient` | ~480 | Exchange API wrapper (Aster perps via ccxt) |
| `CoinState` | ~780 | Per-coin runtime state (TP orders, regime flags, layer count) |
| `V14PortfolioLiveAster` | ~850 | Main bot class — orchestrates everything |

---

## 2. Main Loop Flow

```
run()                                        # Line ~1100
  ├── _sync_positions_from_exchange()         # Every tick (~65s)
  ├── Engine tick per coin (candle-based)     # Processes latest candle
  ├── _execute_action() per coin             # BUY or (unused) SELL
  │     └── _place_tp_order()                # After every successful BUY
  ├── _check_tp_fills()                      # Polls TP order status
  │     └── _handle_tp_fill()                # On confirmed fill
  ├── update_mae() per coin                  # MAE tracking
  └── save_state()                           # Persist to state.json
```

On startup (before main loop):
```
run()
  ├── _sync_positions_from_exchange()         # Initial position sync
  ├── _recover_tp_orders()                    # Phase 1: check saved IDs
  │                                           # Phase 2: scan for orphans
  └── _reconcile_trades_on_startup()          # Check last 48h fills
```

---

## 3. Field Ownership Map

### 3.1 Engine Position Fields (`eng = cs.engine._engine`)

| Field | Written By | Frequency | Source of Truth |
|---|---|---|---|
| `eng.long_avg_entry` | `_sync_positions_from_exchange` | Every tick | **Exchange** (overwrites bot value) |
| `eng.long_cost` | `_sync_positions_from_exchange` | Every tick | **Exchange** (= ex_entry × ex_qty) |
| `eng.long_tp` | `_sync_positions_from_exchange`, `_place_tp_order` | Every tick + on buy | **Exchange** (= ex_entry × 1.03) |
| `eng.long_coins` | `_sync_positions_from_exchange` | Every tick | **Exchange** |
| `eng.long_layers` | `_sync_positions_from_exchange` | Every tick | **CoinState** (synced from open_deals) |
| `eng.long_last_buy` | `V14LifecycleEngine.tick()` | On BUY action | **Engine** |
| `eng.long_pnl` | `_handle_tp_fill` | On TP fill | **Bot** (accumulated) |
| `eng.long_wins` | `_handle_tp_fill` | On TP fill | **Bot** (accumulated) |
| `eng.long_trades` | `_handle_tp_fill` | On TP fill | **Bot** (accumulated) |
| `eng.capital` | `_sync_positions_from_exchange`, `_handle_tp_fill` | Various | **Bot** (= allocated - invested) |

### 3.2 Deal Tracking Fields (`self.tracker._open_deals`)

| Field | Written By | Read By | Source of Truth |
|---|---|---|---|
| `deal_id` | `on_buy` (first layer only) | `on_sell` (CSV write) | **Bot** (counter, never exchange-synced) |
| `invested` | `on_buy` (accumulates: += qty × price) | `on_sell` (PnL calc), `update_mae` | **Bot** (append-only, ⚠️ never reconciled to exchange) |
| `qty` | `on_buy` (accumulates: += qty) | `update_mae` (avg entry calc) | **Bot** (append-only) |
| `layers` | `on_buy` (increments: += 1) | Layer count restore, T1 gate | **Bot** |
| `open_time` | `on_buy` (first layer only) | `on_sell` (duration calc) | **Bot** |
| `mae_pct` | `update_mae` (running max) | `on_sell` (CSV write) | **Bot** |
| `dca_score`, `trade_score`, `trend_mult` | `on_buy` (first layer only) | `on_sell` (CSV write) | **Bot** (captured at deal-open) |

### 3.3 CoinState TP Fields (`cs: CoinState`)

| Field | Written By | Read By | Cleared By |
|---|---|---|---|
| `cs.tp_order_id` | `_place_tp_order`, `_recover_tp_orders` | `_check_tp_fills`, phantom cleanup | `_handle_tp_fill`, `_place_tp_order` (cancel path) |
| `cs.tp_limit_price` | `_place_tp_order` | TP fill correction calc | `_handle_tp_fill` |
| `cs.tp_type` | `_place_tp_order` ("trailing" or "limit") | `_handle_tp_fill` (trail bonus) | — |
| `cs.tp_activation_price` | `_place_tp_order` (= tp_price for trailing) | `_handle_tp_fill` (trail bonus) | `_handle_tp_fill` |
| `cs.trailing_callback_pct` | `_place_tp_order` (= 0.2%) | state persistence | — |
| `cs.layer_count` | `_sync_positions_from_exchange` | Engine tick, layer gating | `_handle_tp_fill` (via engine zero) |

---

## 4. Critical Methods — Detail

### 4.1 `_sync_positions_from_exchange()` — Line 1180

**Called:** Top of every tick loop (~65s), once at startup.

**Flow:**
1. `fetch_full_balance()` → if None, early return (M-2 guard)
2. `fetch_open_positions()` → if raises, early return (guard works)
3. For each coin:
   - If exchange has position (LONG side):
     - **Overwrite:** `eng.long_coins`, `eng.long_cost`, `eng.long_avg_entry`, `eng.long_tp`
     - Restore `cs.layer_count` from `open_deals` if it was 0
     - Force-sync `eng.long_layers = cs.layer_count`
   - If no position:
     - **Zero ALL** long and short position fields
     - Set `cs.layer_count = 0`
4. Phantom deal cleanup (Finding #43): pop `open_deals` entries with no exchange position AND no `cs.tp_order_id`

**⚠️ Known fragility:** `fetch_open_positions()` catches its own exceptions and returns `{}` (line 755). The outer guard in `_sync_positions_from_exchange()` only fires on raised exceptions (line 1195). If API fails silently → empty dict treated as "all positions closed" → all engine fields zeroed. Mitigated by TP order ID keeping open_deals alive through phantom cleanup.

### 4.2 `_safe_cancel_tp()` — Line ~1576 (NEW, Fix 1)

**Called:** By `_place_tp_order`, `_execute_action` SELL path, force-close, phase-change TP cancel.

**Flow:**
1. If no `cs.tp_order_id` → return True
2. Call `cancel_tp_order()` → if success, clear IDs, return True
3. Cancel failed → call `check_order_status()`
4. Empty result guard (Bug 1.1 fix): if `{}` returned, leave ID intact, return True
5. If filled → call `_handle_tp_fill()`, return False (TP filled, position closed)
6. If not filled (cancelled/expired) → clear IDs, return True
7. Exception → leave ID intact for retry, return True

**Returns:** True = TP cancelled or gone (caller can proceed). False = TP silently filled (caller should abort).

### 4.3 `_place_tp_order()` — Line ~1700

**Called:** After every successful BUY fill in `_execute_action()`.

**Flow:**
1. Read `eng.long_tp` as fallback
2. Call `fetch_open_positions()` inline → get exchange entry + qty
3. Override: `tp_price = exchange_entry * (1 + tp_pct)`
4. Override: `eng.long_tp = tp_price`
5. Cancel existing TP via `_safe_cancel_tp()` → if returns False (TP filled), abort
6. Place new order: trailing stop → fallback to limit sell → fallback to warning

**✅ Bug A fixed:** Step 5 now uses `_safe_cancel_tp` which detects silent fills.

### 4.4 `_handle_tp_fill()` — Line ~2070

**Called:** By `_check_tp_fills()` when order status = filled. Also by `_recover_tp_orders()` at startup. Also by `_safe_cancel_tp()` when silent fill detected (Fix 1).

**Flow:**
1. Log TP FILL with price, qty, proceeds
2. Exchange-truth correction (Fix 2): FRESH `fetch_open_positions()` with fallback to cached `_last_exchange_positions`. Warns on >10% divergence via Telegram.
3. Call `tracker.on_sell()` → pops open_deal, computes PnL, writes CSV
4. Update `_cumulative_realized_pnl`
5. Return capital to router
6. Zero ALL engine position fields
7. Reset `eng.capital = cs.allocated_capital`
8. Clear all TP fields on CoinState
9. Post-TP: `_clear_regime_flag_on_tp()`, `_rotate_after_tp()`, orphan order cleanup

### 4.5 `_check_tp_fills()` — Line ~1760

**Called:** Every tick loop, per coin with `cs.tp_order_id` set.

**Flow:** `check_order_status(sym, tp_order_id)` → if filled → `_handle_tp_fill()`. Exception per coin → error logged, coin skipped.

### 4.6 `_recover_tp_orders()` — Line ~1770

**Called:** Once at startup, after initial `_sync_positions_from_exchange()`.

**Phase 1:** Check each saved `cs.tp_order_id`:
- Filled → `_handle_tp_fill()` (catches fills that happened while bot was down)
- Cancelled/expired → clear tp_order_id, Telegram alert
- Still open → log, keep

**Phase 2:** Scan exchange for orphan sell orders (coins without confirmed TP):
- Has position + orphan sell → adopt as TP (newest order, cancel extras)
- No position + stale sells → cancel all
- Has position + no orders + `eng.long_tp > 0` → place new TP

### 4.7 `TradeTracker.on_buy()` — Line 235

**Called:** By `_execute_action()` after exchange BUY fill confirmed.

**Flow:**
1. If no existing `open_deals[key]` → create new deal (increment `_deal_counter`)
2. `deal["layers"] += 1`
3. `deal["invested"] += qty * price` (**append-only, never reset**)
4. `deal["qty"] += qty`

### 4.8 `TradeTracker.on_sell()` — Line 291

**Called:** By `_handle_tp_fill()` on TP fill.

**Flow:**
1. Pop `open_deals[key]` (removes deal from tracking)
2. `pnl = actual_proceeds - invested - fee`
3. Compute return %, duration
4. Dedup check against `_existing_keys`
5. Append record to CSV, return record dict

### 4.9 `_execute_action()` BUY path — Line ~2900

**Called:** By main loop after engine tick produces an action.

**Gates (in order, each causes `reject_action()` + return):**
1. Bot state PAUSED/WIND_DOWN
2. Per-coin pause (`cs.paused`)
3. Regime conflict (`cs.regime_flagged`)
4. T1 gate: first entry must be in router allocations
5. Order dedup: <30s since last buy
6. Min cost: <$5
7. Router capital: denied or partial → reject + return capital
8. Exchange balance: < cost × 1.01
9. (continues with spread check, order placement)

**On successful BUY fill:**
1. **Fix 4:** Check exchange position vs open_deals qty. If exchange has <50% of tracked qty AND cached positions agree → force-close stale deal (clear tp_order_id first to prevent Bug 4.1 race), then proceed to on_buy.
2. `tracker.on_buy()` — accumulates invested
3. `_place_tp_order()` — places TP on exchange (via `_safe_cancel_tp`)
4. Update `cs._last_buy_time`

### 4.10 `cancel_tp_order()` — Line 646

**Flow:** `exchange.cancel_order(order_id, sym)` → if exception → WARNING logged, return False.

**⚠️ "Unknown order sent"** means the order doesn't exist on the exchange. Could be: already filled, already cancelled, or never existed. The method doesn't distinguish — just returns False. All callers ignore the return value.

### 4.11 `check_order_status()` — Line 665

**Flow:** `exchange.fetch_order(order_id, sym)` → if status "closed"/"filled" → return fill details (price, qty, proceeds, fee). Handles 1000-prefix scaling (PEPE/BONK/FLOKI). If order not found → returns empty dict.

---

## 5. Data Flow Diagrams

### 5.1 Normal BUY → TP Cycle
```
Engine tick → BUY action
  → _execute_action()
    → Gates (T1, capital, balance...)
    → exchange.create_market_buy()
    → tracker.on_buy() → open_deals.invested += cost
    → _place_tp_order()
      → fetch_open_positions() → exchange entry
      → tp_price = exchange_entry * 1.03
      → place_trailing_stop_sell()
      → cs.tp_order_id = order_id

[... time passes ...]

_check_tp_fills()
  → check_order_status(tp_order_id) → filled!
  → _handle_tp_fill()
    → tracker.on_sell() → pnl = proceeds - invested
    → zero engine fields
    → return capital to router
    → _rotate_after_tp()
```

### 5.2 Silent TP Fill — With Fixes (Post 2026-08-21)
```
Engine tick → BUY L1 → TP placed → TP fills on exchange
  [Bot doesn't detect fill — between ticks or API lag]

Next tick:
  → _sync_positions_from_exchange()
    → fetch_open_positions() returns {} for this coin
    → eng.long_coins = 0, all zeroed
    → phantom cleanup: open_deals survives (cs.tp_order_id still set)

Next engine tick:
  → Engine sees no position → generates BUY L1
  → _execute_action() BUY succeeds on exchange
  → Fix 4: exchange has new (small) position, but open_deals qty is old (large)
    → Cross-check cached + fresh positions both confirm mismatch
    → Clear cs.tp_order_id (Bug 4.1 fix) → force-close stale deal
  → tracker.on_buy() → creates FRESH deal (invested = new cost only)
  → _place_tp_order():
    → _safe_cancel_tp() → no tp_order_id (Fix 4 cleared it) → skip
    → Places NEW TP for new position ✅

Alternative (Fix 1 catches it first during _place_tp_order cancel):
  → _safe_cancel_tp() → cancel fails → check_order_status() = filled
    → _handle_tp_fill() with real TP proceeds
    → Fix 2: cross-validates invested vs exchange
    → Correct PnL recorded, deal closed cleanly
```

### 5.3 Position Sync After API Failure
```
_sync_positions_from_exchange()
  → fetch_open_positions() internally catches exception → returns {}
  → Guard does NOT fire (no exception raised to caller)
  → All coins: eng.long_coins = 0, all zeroed, cs.layer_count = 0
  → Phantom cleanup: open_deals survives IF cs.tp_order_id is set

Next successful sync:
  → fetch_open_positions() returns actual position
  → eng.long_coins = exchange_qty (restored)
  → cs.layer_count = 0, exchange has position
    → Restore from open_deals: cs.layer_count = deal["layers"]
  → eng.long_layers = cs.layer_count (re-synced)
```

---

## 6. Constants & Configuration

| Constant | Value | Location |
|---|---|---|
| `TRAILING_STOP_ENABLED` | `True` | Line 117 |
| `TRAILING_CALLBACK_PCT` | `0.2` (%) | Line 118 |
| `TP_CHECK_INTERVAL` | ~65s (tick interval) | Main loop |
| `ORDER_DEDUP_WINDOW` | 30s | Line ~2880 |
| `DCA_TP_PCT` | `0.030` (3%) | Engine config (High profile) |

---

## 7. Known Issues & Audit Trail

| ID | Issue | Status | Spec |
|---|---|---|---|
| **Bug A** | `cancel_tp_order` return value ignored — silent TP fills undetected | **FIXED** (Fix 1: `_safe_cancel_tp`) | `specs/undetected-tp-fill-bug-spec.md` |
| **Bug B** | Exchange-as-truth overwrites avg entry — TP set from exchange, not open_deals | **MITIGATED** (Fix 2: cross-validate at TP fill) | `specs/undetected-tp-fill-bug-spec.md` |
| **Bug C** | `fetch_open_positions()` internal catch bypasses sync guard | **DETECTED** (Fix 3: daily audit) | `specs/undetected-tp-fill-bug-spec.md` §3.3 |
| **Fix 1** | `_safe_cancel_tp()` — detect silent fills on cancel failure | **DEPLOYED** 2026-08-21 | `specs/fix-audit-opus5-2026-08-21.md` |
| **Fix 2** | Cross-validate invested vs exchange on TP fill | **DEPLOYED** 2026-08-21 | `specs/fix-audit-opus5-2026-08-21.md` |
| **Fix 3** | Daily invested-vs-exchange audit in health digest | **DEPLOYED** 2026-08-21 | `specs/fix-audit-opus5-2026-08-21.md` |
| **Fix 4** | Prevent deal accumulation on BUY (stale deal detection) | **DEPLOYED** 2026-08-21 | `specs/fix-audit-opus5-2026-08-21.md` |
| Finding #43 | Phantom open_deals cleanup | Fixed | In code (line ~1266) |
| H3 | Short position miswritten to long fields | Fixed | In code (line ~1212) |
| M-2 | Balance fetch None injecting $0 | Fixed | In code (line ~1186) |
| Audit #8 | TP price stored separately in CoinState | Fixed | `cs.tp_limit_price` |

---

*This document maps the code as of 2026-08-21. Update when methods move or new fields are added.*
