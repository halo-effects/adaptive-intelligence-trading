# Spec: Exchange-Truth Trade Recording

**Status**: DRAFT — needs approval before implementation
**Date**: 2026-05-09
**Priority**: HIGH (incorrect PnL reporting, turns wins into reported losses)
**Restart Required**: YES (code change in live runner)

## Problem

The trade recorder uses the engine's internal cost tracking to calculate `invested` amount when closing a deal. The engine tracks theoretical prices (before slippage), so the recorded cost basis diverges from reality.

**Example** (PENDLE/USDT, May 9):
- Engine price at buy: $2.0685
- Actual exchange fill: $2.0827 (69bps spread)
- Exchange entry price (position avg): $2.0827
- Exchange TP fill: $2.1025
- **Real PnL**: +$0.20 (+0.95%)
- **Recorded PnL**: -$0.79 (-3.6%) ← wrong

The CSV says `invested=$21.81` (implying $2.181/unit cost basis) when the exchange says entry was $2.0827. The $2.181 comes from the engine's internal accounting which double-counts spread adjustments.

## Root Cause

In the TP fill handler (`_on_tp_fill` or equivalent), the trade recorder calculates:
```python
invested = engine.long_invested  # Engine's internal cost tracking
proceeds = fill_price * fill_qty  # From exchange (correct)
pnl = proceeds - invested - fees  # Wrong because invested is wrong
```

The engine's `long_invested` accumulates costs using engine prices (pre-slippage), then applies spread corrections inconsistently. The result is an inflated cost basis.

## Solution

When recording a closed deal, use **exchange data** for all monetary values:

```python
# BEFORE (engine-truth):
invested = engine.long_invested
entry_price = engine.long_avg_entry

# AFTER (exchange-truth):
entry_price = exchange_position.entry_price  # From fetch_positions() or cached sync
invested = entry_price * fill_qty            # Simple: avg entry × qty sold
proceeds = fill_price * fill_qty             # Already from exchange
pnl = proceeds - invested - fees
```

### Data Sources

| Field | Source | API |
|-------|--------|-----|
| `entry_price` | Exchange position avg entry | `fetch_positions()` → `entryPrice` (already cached in `_last_exchange_positions`) |
| `fill_price` | Exchange TP fill | `fetch_order()` → `avgPrice` (already retrieved on TP fill) |
| `fill_qty` | Exchange TP fill | `fetch_order()` → `filled` (already retrieved) |
| `invested` | Calculated | `entry_price × fill_qty` |
| `proceeds` | Calculated | `fill_price × fill_qty` |
| `fee` | Exchange fill | `fetch_order()` → `fee` (already retrieved) |
| `pnl` | Calculated | `proceeds - invested - fee` |

### Where to Change

**File**: `run_v14_portfolio_live_aster.py`

**Location**: The TP fill handler — wherever `self.tracker.record_trade()` or equivalent is called after a TP fill is detected.

**Changes**:
1. When recording a closed deal after TP fill, read `entry_price` from `self._last_exchange_positions[base]["entry_price"]` (already synced every cycle)
2. Calculate `invested = entry_price * fill_qty`
3. Pass exchange-sourced values to the trade recorder

**Fallback**: If exchange position data is unavailable (position already closed by the time we check), fall back to the TP fill's own data — Aster includes `entryPrice` in the order response for some endpoints. If neither is available, use the engine value with a warning log.

## What Doesn't Change

- Engine internal state tracking (still needed for DCA layer decisions, signal processing)
- TP order placement logic (still uses exchange entry for activation price — this already works correctly)
- Dashboard equity calculation (already uses DEX-as-truth)
- Capital management (already DEX-as-truth from yesterday's fix)

## Validation

After implementation:
1. Check that a TP fill records `invested = exchange_entry × qty` (not engine's internal number)
2. Verify PnL matches: `(fill_price - entry_price) × qty - fees`
3. Compare a few trades against Aster's trade history page

## Risk

- **Low**: This is a recording/reporting change, not a trading logic change
- **The bot already uses exchange entry price for TP placement** (line: "TP price for X: using exchange entry $Y") — we're just extending that to trade recording
- **No risk to open positions** — only affects how future completed trades are recorded in CSV
