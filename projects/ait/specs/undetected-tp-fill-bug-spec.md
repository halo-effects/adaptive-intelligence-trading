# Undetected TP Fill Bug — Architecture Spec & Fix Proposal

**Date:** 2026-08-21
**Status:** IMPLEMENTED — All 4 fixes deployed 2026-08-21. Audited (see `fix-audit-opus5-2026-08-21.md`).
**Severity:** P0 — Caused $47.03 realized loss on live capital (ASTER deal #118)
**Affected bot:** V14PM Live (Aster Perps)

---

## 1. Bug Summary

Two interacting defects caused a 4-layer ASTER position to close at -54.58% despite the TP system believing it executed a +3% win.

**Bug A — Undetected TP Fill ("Silent Close"):**
When a TP order fills on the exchange while the bot is between ticks (or during an API outage), `cancel_tp_order()` returns "Unknown order sent" and the bot silently ignores it. The bot never checks whether the order *filled* vs was *cancelled* vs simply *doesn't exist*. The position is gone on the exchange, but `open_deals` still tracks it as open with accumulated invested capital.

**Bug B — Exchange-as-Truth Overwrites Cost Basis Every Cycle:**
`_sync_positions_from_exchange()` runs every tick and sets:
```python
eng.long_avg_entry = ex_entry        # Aster's entryPrice for CURRENT position
eng.long_cost = ex_entry * ex_qty
eng.long_tp = ex_entry * (1 + 0.030)
```
After a silent close + new buys, the exchange's `entryPrice` reflects only the NEW position, but `open_deals.invested` has accumulated cost from BOTH the old (silently closed) and new position. The TP is set correctly for the exchange position (+3% above current entry), but when it fills, the bot computes PnL against the inflated `invested` — producing a massive phantom loss.

---

## 2. Incident Timeline (ASTER Deal #118)

| Time (UTC) | Event | Effect |
|---|---|---|
| 2026-06-19 23:00 | L1 BUY: 44.46 qty @ $0.6349 ($28.23) | `open_deals.invested = $28.23`, exchange entry = $0.6349 |
| 2026-06-20 03:00 | L2 BUY: 31.80 qty @ $0.6238 ($19.84) | `open_deals.invested = $48.07`, exchange entry = $0.6440 (weighted) |
| ~2026-06-20 06:00 | **TP fills on exchange at ~$0.663** | Exchange position = 0. **Bot does not detect this.** |
| 2026-06-20 07:00 | Bot tries to cancel old TP → "Unknown order sent" | **Silently ignored.** `open_deals` still shows 2 layers, $48 invested. |
| 2026-06-20 07:00 | L1 BUY: 21.16 qty @ $0.6552 ($13.86) | `open_deals.invested = $61.93` (3 layers). Exchange: NEW position, entry = $0.6552 |
| 2026-06-20 12:00 | L2 BUY: 37.88 qty @ $0.6375 ($24.15) | `open_deals.invested = $86.08` (4 layers). Exchange: 59.02 qty, entry = $0.6438 |
| 2026-06-20 → 2026-08-20 | 61-day zombie. Bot detects "Zombie slot" daily. | Exchange position: 59.02 qty @ $0.6438 entry. `open_deals.invested` = $86.18. **2.27x mismatch.** |
| 2026-08-20 06:52 UTC | TP fills: 59.02 @ $0.6635 = $39.16 | Exchange: correct +3% profit on $38 position. Bot records: $39.16 proceeds vs $86.18 invested = **-$47.03 loss** |

---

## 3. Code Path Analysis

### 3.1 Components Involved

```
┌─────────────────────────────────────────────────────────────┐
│                    Main Tick Loop                            │
│                                                             │
│  1. _sync_positions_from_exchange()  ← WRITES eng.long_*    │
│  2. Engine tick (candle-based)       ← READS eng.long_*     │
│  3. _execute_action() [BUY]         ← calls on_buy()       │
│  4. _place_tp_order()               ← READS exchange entry  │
│  5. _check_tp_fills()               ← polls order status    │
│                                                             │
│  On TP fill:                                                │
│    _handle_tp_fill()                ← calls on_sell()       │
│      → TradeTracker.on_sell()       ← pops open_deals       │
│      → records to trades.csv                                │
│                                                             │
│  On startup:                                                │
│    _recover_tp_orders()             ← checks saved order IDs│
│                                                             │
│  cancel_tp_order()                  ← Bug A lives here      │
└─────────────────────────────────────────────────────────────┘
```

### 3.2 Field Ownership Map

| Field | Written By | Read By | Source of Truth |
|---|---|---|---|
| `eng.long_avg_entry` | `_sync_positions_from_exchange` (every tick) | `_place_tp_order`, engine tick, MAE, status | **Exchange** (overwrites bot's value) |
| `eng.long_cost` | `_sync_positions_from_exchange` (every tick) | capital calc | **Exchange** (= ex_entry × ex_qty) |
| `eng.long_tp` | `_sync_positions_from_exchange`, `_place_tp_order` | TP placement | **Exchange** (= ex_entry × 1.03) |
| `eng.long_coins` | `_sync_positions_from_exchange` (every tick) | TP qty, engine tick | **Exchange** |
| `eng.long_layers` | `_sync_positions_from_exchange` (from open_deals) | engine DCA logic | **open_deals** (restored) |
| `open_deals.invested` | `TradeTracker.on_buy()` (accumulates) | `on_sell()` PnL calc | **Bot** (never reset by exchange sync) |
| `open_deals.qty` | `TradeTracker.on_buy()` (accumulates) | MAE calc | **Bot** (never synced to exchange) |
| `open_deals.layers` | `TradeTracker.on_buy()` (increments) | layer count restore | **Bot** |

**The critical mismatch:** `open_deals.invested` is append-only (accumulated from each `on_buy`) and is NEVER reconciled against the exchange position. Meanwhile, `eng.long_avg_entry` and `eng.long_tp` are overwritten by exchange data every tick. These two systems can silently diverge.

### 3.3 fetch_open_positions() — Silent Empty Return (Related Concern)

`fetch_open_positions()` (line 755) catches its own exceptions and returns `{}`:
```python
except Exception as e:
    logger.error(f"fetch_open_positions failed: {e}")
    return {}  # ← No exception raised to caller
```

The guard in `_sync_positions_from_exchange()` (line 1195) only fires on RAISED exceptions:
```python
try:
    positions = self.client.fetch_open_positions()
except Exception as e:
    return  # Don't overwrite engine with empty data
```

If `fetch_open_positions()` catches internally and returns `{}`, the guard doesn't fire. The code proceeds into the for loop and **zeroes all engine fields for all coins** (treats every position as closed). This is visible in the bot log as repeated `fetch_open_positions failed:` followed by `Layer count ASTER/USDT: restored 4 from open_deals`.

**Mitigating factor:** The phantom deal cleanup (Finding #43) checks `has_tp = cs.tp_order_id` before popping open_deals. If a TP order ID is stored, the deal survives the transient zero-out. But if the TP already silently filled and `cs.tp_order_id` points to a dead order, the deal may still survive (the ID is only cleared on explicit cancel or fill detection).

**This is NOT the primary cause of the ASTER incident** but is a related fragility. A transient API failure could cause the engine to re-buy (seeing no position) and inflate `open_deals.invested` further.

### 3.4 cancel_tp_order() — Bug A Location

```python
# Line 646
def cancel_tp_order(self, db_symbol: str, order_id: str) -> bool:
    try:
        self._exchange.cancel_order(order_id, sym)
        return True
    except Exception as e:
        logger.warning(f"cancel_tp_order({db_symbol}, {order_id}): {e}")
        return False  # ← SILENTLY RETURNS FALSE. Caller doesn't check WHY.
```

The caller in `_place_tp_order()` (line ~1631):
```python
if cs.tp_order_id:
    self.client.cancel_tp_order(sym, cs.tp_order_id)  # ← ignores return value
    cs.tp_order_id = None
    cs.tp_limit_price = None
```

**Problem:** When cancel fails because the order already filled, the code clears `tp_order_id` and `tp_limit_price` anyway, losing the evidence that a fill happened. No check is made to determine if the order filled vs was already cancelled vs never existed.

### 3.4 _handle_tp_fill() — Exchange-Truth Override of invested

```python
# Line 2019
deal_key = f"{sym}:long"
if deal_key in self.tracker._open_deals:
    ex_entry = float(ex_pos.get("entry_price", 0) or 0)
    if ex_entry > 0:
        new_invested = ex_entry * actual_qty    # ← replaces accumulated invested
        self.tracker._open_deals[deal_key]["invested"] = new_invested
```

**This was supposed to fix the accounting** by using exchange-truth for the final PnL calc. But after a silent close, the exchange has NO position (or a new, cheaper one). So `_last_exchange_positions` will either have no entry (skip the override) or have the new position's entry (which is lower than the accumulated invested). Either way, the PnL is wrong.

---

## 4. Impact on Current Open Trades

### 4.1 Zombie Mismatch Audit (from state.json, Aug 21)

| Coin | Deal | Layers | open_deals invested | Exchange cost | Mismatch | TP Gap |
|---|---|---|---|---|---|---|
| INJ/USDT | #117 | 4L | $116.58 | $115.05 | +$1.52 (+1.3%) | TP $0.09 too low |
| JUP/USDT | #89 | 5L | $109.07 | $108.22 | +$0.85 (+0.8%) | TP $0.002 too low |
| PENDLE/USDT | #99 | 4L | $92.91 | $86.95 | +$5.96 (+6.9%) | TP $0.14 too low |
| FET/USDT | #121 | 3L | $70.65 | $70.43 | +$0.22 (+0.3%) | ✅ aligned |
| **ASTER #118** | **(closed)** | **4L** | **$86.18** | **$38.00** | **+$48.18 (+127%)** | **catastrophic** |

**Assessment:** None of the 4 surviving zombies have the catastrophic 127% inflation that ASTER had. PENDLE at +6.9% is the worst — likely one silent fill cycle occurred. The others are within normal slippage/rounding range. **These positions are NOT in immediate danger of the same blow-up**, but they remain vulnerable if the TP fills and re-buys happen again.

### 4.2 Non-Zombie Positions

The current ASTER/USDT position (deal #118 reused, 1L opened today) is clean — opened fresh after the zombie closed. No accumulated mismatch.

---

## 5. Proposed Fixes

### Fix 1: Detect fills on cancel failure (Bug A — Critical)

**When:** `cancel_tp_order()` throws an exception containing "Unknown order" or returns false.

**Action:** Before clearing `tp_order_id`, call `check_order_status()` to determine what happened:
- If **filled** → call `_handle_tp_fill()` to properly record the trade
- If **cancelled/expired** → safe to clear, log warning
- If **network error** → retry or leave tp_order_id intact for next cycle

**Where the check goes:** A new method `_safe_cancel_tp()` wrapping the cancel + fill-check logic, called from:
1. `_place_tp_order()` (line 1631) — before placing a new TP
2. `_execute_action()` BUY path — when selling to rotate (if applicable)
3. Anywhere else `cancel_tp_order` is called followed by clearing `tp_order_id`

**Downstream impact:**
- `_handle_tp_fill()` will be called mid-tick, which triggers `on_sell()`, capital return, CSV write, Telegram notification, capital rotation. All of these are designed to be called during normal tick flow — no new side effects.
- The engine state will be zeroed (long_coins=0, etc.) which is correct — the position IS gone.
- `open_deals` will be popped and a trade recorded. The recorded PnL will still reflect the inflated invested if the mismatch already exists, but it prevents FUTURE inflation.
- If a fill is detected, the current BUY action that triggered the cancel should be re-evaluated as a fresh L1 entry (not a DCA add-on), since the old position is now gone.

**Risk to open trades:** LOW. This is additive detection logic. Existing positions are not modified — the fix only catches fills that are currently being silently ignored. The 4 surviving zombies won't be affected unless their current TP order has already silently filled (which the audit suggests hasn't happened — their exchange positions match).

### Fix 2: Cross-validate invested vs exchange on TP fill (Bug B — Defensive)

**When:** `_handle_tp_fill()` fires.

**Action:** Before computing PnL, compare `open_deals.invested` against `exchange_entry × qty`. If they diverge by more than a threshold (e.g., 10%), log a WARNING with both values and use the **exchange-truth value** for PnL calculation (since the exchange entry is authoritative for what was actually at risk).

**Implementation:** This is already partially implemented (lines 2019-2030) but only overwrites invested from `_last_exchange_positions`. The fix would:
1. Make this check mandatory (not conditional on `_last_exchange_positions` having data)
2. Add a fresh `fetch_open_positions()` call if `_last_exchange_positions` is stale
3. Log a clear WARNING when divergence exceeds threshold so it's auditable

**Downstream impact:**
- `on_sell()` uses `open_deals.invested` for PnL — so the corrected invested flows through to trades.csv and Telegram notifications
- `cumulative_realized_pnl` will be more accurate
- Dashboard data will reflect corrected PnL

**Risk to open trades:** NONE. This only fires at close time and only affects the PnL accounting of the closing trade.

### Fix 3: Periodic invested-vs-exchange audit (Preventive)

**When:** Once per daily tick (alongside zombie slot detection).

**Action:** For each `open_deals` entry, compare `invested` to `exchange_entry × exchange_qty`. If mismatch exceeds 10%, log WARNING and optionally correct `open_deals.invested` to match exchange truth.

**Downstream impact:**
- Corrects the invested tracker proactively, before the trade closes
- MAE tracking (which uses `open_deals.invested / qty` for avg entry) will also be corrected
- Trade score logging at deal-open is not affected (captured once at open)

**Risk to open trades:** LOW but requires care. Correcting `open_deals.invested` mid-trade changes the PnL that will be recorded at close. For the 4 zombies, this would:
- INJ: $116.58 → $115.05 (reduces recorded loss by $1.52 at close)
- JUP: $109.07 → $108.22 (reduces by $0.85)
- PENDLE: $92.91 → $86.95 (reduces by $5.96)
- FET: $70.65 → $70.43 (reduces by $0.22)

These corrections are arguably MORE accurate, but they retroactively change the cost basis. **Decision point: should we correct in-flight, or only log the discrepancy and let on_sell handle it?**

### Fix 4: Prevent deal_id re-use after silent close (Defensive)

**When:** `on_buy()` is called for a symbol that has an existing `open_deals` entry.

**Action:** Before incrementing layers, verify the exchange actually has a position matching the deal's qty. If the exchange has NO position or a significantly smaller position than `open_deals.qty`, the old deal should be force-closed (recorded as a loss from silent fill) before opening a new deal.

**Downstream impact:**
- This is the deepest fix — it prevents the invested accumulation across position lifecycles
- Requires a `fetch_open_positions()` call during the BUY path, which adds latency
- Could produce unexpected "phantom close" trades in the CSV if the exchange position is temporarily unavailable (API flake)

**Risk to open trades:** MEDIUM. Must handle API failures gracefully — if `fetch_open_positions()` fails, the buy should proceed normally (don't block trading on a failed check). The existing `_sync_positions_from_exchange()` failure handling (bail and keep previous values) is the right model.

---

## 6. Fix Priority & Dependencies

```
Fix 1 (Silent fill detection)     ← MUST DO. Prevents future damage.
  └── depends on: check_order_status() being reliable
  └── affected by: nothing upstream
  └── affects: _handle_tp_fill(), engine state, open_deals, trades.csv

Fix 2 (invested cross-validation)  ← SHOULD DO. Corrects PnL at close.
  └── depends on: _last_exchange_positions being populated
  └── affected by: _sync_positions_from_exchange() timing
  └── affects: on_sell() PnL, trades.csv, dashboard

Fix 3 (Periodic audit)            ← NICE TO HAVE. Early warning system.
  └── depends on: Fix 1 being deployed (otherwise keeps re-triggering)
  └── affected by: exchange API reliability
  └── affects: open_deals.invested (if correction enabled)

Fix 4 (Prevent deal accumulation)  ← NICE TO HAVE. Belt-and-suspenders.
  └── depends on: Fix 1 (which is the primary guard)
  └── affected by: exchange API reliability in BUY path
  └── affects: on_buy() flow, possible phantom close records
```

**Recommended deployment order:** Fix 1 → Fix 2 → Fix 3 → Fix 4

---

## 7. Impact on Other Bots

| Bot | Uses same code? | Affected? |
|---|---|---|
| V14 Live (Aster, ASTER/USDT single) | `run_v14_live_aster.py` — separate file | Likely same pattern but single coin, less exposure |
| V14PM Paper (Hyperliquid) | `run_v14_portfolio_paper.py` — paper mode | No real exchange, dry_run=True, no real TP orders |
| V14 Paper (Hyperliquid) | `run_v14_paper.py` | No real exchange |
| V14-ETF Paper | `run_v14etf_paper.py` | No real exchange |

**Only V14PM Live and V14 Live (both Aster) are affected by this bug.** Paper bots use dry_run mode where `cancel_tp_order` returns True and `fetch_open_positions` returns empty.

---

## 8. Immediate Remediation (No Code Changes)

For the 4 surviving zombie positions, the mismatch is small (max 6.9% for PENDLE). If any of these TP fills before the fix is deployed:

- **INJ** would record ~$1.52 extra loss (1.3%)
- **JUP** would record ~$0.85 extra loss (0.8%)
- **PENDLE** would record ~$5.96 extra loss (6.9%)
- **FET** would record ~$0.22 extra loss (0.3%)

Total worst case if ALL four TP at current levels: ~$8.55 in phantom loss. This is manageable and not urgent enough to justify manual intervention on live trades.

---

## 9. Open Questions

1. **Should Fix 3 auto-correct `open_deals.invested`, or just log?** Auto-correction is more accurate but changes cost basis mid-trade.

2. **Should Fix 4 add a `fetch_open_positions()` call in the BUY path?** This adds latency and an API failure point. Alternative: rely on the periodic sync from `_sync_positions_from_exchange()` which already runs every tick.

3. **Should we also fix `_handle_tp_fill()` line 2019-2030** to do a fresh `fetch_open_positions()` instead of relying on `_last_exchange_positions`? The cached positions could be stale if multiple fills happen in one tick.

4. **V14 Live (single coin):** Should we port Fix 1 to `run_v14_live_aster.py` as well? Same exchange, same API, same risk.

---

## 10. Files That Will Be Modified

| File | Changes | Risk |
|---|---|---|
| `trading/spot/run_v14_portfolio_live_aster.py` | Fixes 1-4 | HIGH — live bot, must be tested |
| `trading/spot/run_v14_live_aster.py` | Port Fix 1 (if Q4 = yes) | MEDIUM — live bot, simpler |

No other files need modification. The `v14_lifecycle_engine.py` and `exchange_client.py` are not changed — the fixes are entirely in the portfolio bot's TP management layer.
