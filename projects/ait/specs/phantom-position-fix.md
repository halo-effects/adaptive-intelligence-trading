# Spec: Phantom Position Display Fix — Dashboard Shows Engine State, Not Exchange Truth

**Status**: DRAFT — needs approval
**Date**: 2026-05-10
**Priority**: HIGH
**Restart Required**: YES

## Problem

The dashboard shows HYPE as having a $74.60 SHORT position with 3/12 layers, but there is zero HYPE position on exchange. This is because the status.json writer pulls `invested`, `layers`, and `side` from the **engine's internal state** rather than the **exchange**.

## Root Cause Analysis

The data flow for per-coin display data in status.json has **three sources** that can disagree:

### Source 1: V14LifecycleEngine.get_status() (line 760, v14_lifecycle_engine.py)
Returns engine-internal values:
- `invested` = `eng.long_cost + eng.short_cost` (engine's tracking, NOT exchange)
- `layers` = `eng.long_layers` or `eng.short_layers` (engine's tracking)
- `side` = derived from `eng.long_coins > 0` or `eng.short_coins > 0`
- `avg_entry` = engine's tracked avg entry
- `unrealized_pnl` = calculated from engine's position data

### Source 2: Exchange positions (_sync_positions_from_exchange, line 1032)
The exchange sync runs each cycle and:
- Overwrites `eng.long_coins`, `eng.long_cost`, `eng.long_avg_entry`, `eng.long_tp`, `eng.long_layers` from exchange
- If exchange has NO position: zeros out `long_coins`, `long_cost`, `long_avg_entry`, `long_layers`, `long_tp`
- **DOES NOT touch short fields**: `eng.short_coins`, `eng.short_cost`, `eng.short_avg_entry` are NEVER synced from exchange

This is because Aster doesn't support shorts, so the exchange sync only handles longs. But the engine internally still tracks short_coins when it transitions to SHORT_DCA.

### Source 3: CoinState.layer_count (line 893)
A separate `layer_count` field on CoinState, synced FROM the engine during exchange sync (line 1067).
Only syncs long_layers — never short_layers.

### The Bug

When status.json is written (line 3025-3090):

1. `coin_data = st["coins"].get(sym, {})` — copies ALL fields from engine.get_status()
   This includes: invested=$74.60 (from eng.short_cost), layers=3 (from eng.short_layers),
   side="short", avg_entry=engine's short_avg_entry

2. Exchange overrides (line 3042-3048) only override:
   - `avg_entry` → from exchange (becomes 0 since no position)
   - `unrealized_pnl` → from exchange (becomes 0)
   - `position_size` → from exchange (becomes 0)

3. `invested` is NEVER overridden → stays at $74.60 (phantom)
4. `layers` is NEVER overridden → stays at 3 (phantom)
5. `side` is NEVER overridden → stays at "short" (phantom)

Additionally, `coin_data["layer_count"] = cs.layer_count` (line 3078) uses CoinState which
was zeroed by exchange sync. But the dashboard reads `layers` (from engine), not `layer_count`.

## The Fix

**Single principle: When exchange says no position, ALL position display fields must be zero.**

### Change 1: Status.json writer (run_v14_portfolio_live_aster.py, ~line 3042)

Currently:
```python
if ex_qty > 0:
    coin_data["avg_entry"]      = round(ex_entry, 8)
    coin_data["unrealized_pnl"] = round(ex_unrealized, 4)
    coin_data["position_size"]  = round(ex_qty, 8)
else:
    coin_data["avg_entry"]      = 0
    coin_data["unrealized_pnl"] = 0
    coin_data["position_size"]  = 0
```

Fix — also zero out `invested`, `layers`, `side` when exchange has no position:
```python
if ex_qty > 0:
    coin_data["avg_entry"]      = round(ex_entry, 8)
    coin_data["unrealized_pnl"] = round(ex_unrealized, 4)
    coin_data["position_size"]  = round(ex_qty, 8)
    # invested and layers come from engine — valid when exchange confirms position
else:
    coin_data["avg_entry"]      = 0
    coin_data["unrealized_pnl"] = 0
    coin_data["position_size"]  = 0
    coin_data["invested"]       = 0
    coin_data["layers"]         = 0
    coin_data["side"]           = "none"
```

### Change 2: Exchange sync — zero short fields too (line 1078-1084)

Currently the `else` branch (no exchange position) only zeros long fields:
```python
else:
    eng.long_coins = 0.0
    eng.long_cost = 0.0
    eng.long_avg_entry = 0.0
    eng.long_layers = 0
    eng.long_tp = 0.0
    cs.layer_count = 0
```

Fix — also zero short fields when exchange has no position:
```python
else:
    eng.long_coins = 0.0
    eng.long_cost = 0.0
    eng.long_avg_entry = 0.0
    eng.long_layers = 0
    eng.long_tp = 0.0
    eng.short_coins = 0.0
    eng.short_cost = 0.0
    eng.short_avg_entry = 0.0
    eng.short_layers = 0
    eng.short_tp = 0.0
    cs.layer_count = 0
```

**Important:** This does NOT touch `eng.phase`, `eng.top_detected`, or any signal state.
The engine's phase (SHORT_DCA) is preserved — only the phantom position quantities are
zeroed because the exchange confirms they don't exist.

### What this does NOT change
- Engine phase (LONG_DCA / SHORT_DCA) — preserved, reflects real signals
- Top/bottom detection state — preserved
- regime_flagged — preserved
- Any signal or indicator state — preserved

The only fields being zeroed are position tracking fields (coins, cost, avg_entry, layers)
that claim a position exists when the exchange says it doesn't.

## Dependencies

- Dashboard reads `invested`, `layers`, `side` from status.json coins — will now show correct values
- Regime gate reads `engine.phase` — NOT affected (phase preserved)
- Conviction system counts `regime_flagged` — NOT affected
- TP detection reads `eng.long_coins` / `eng.short_coins` — zeroing phantom shorts prevents false TP detection
- Trade recording reads engine position data — zeroing phantom shorts prevents recording phantom trades

## Testing

1. Pre-flight import test
2. Verify HYPE shows invested=0, layers=0 in status.json after restart
3. Verify HYPE still shows phase=SHORT_DCA, regime_flagged=True
4. Verify INJ position data matches exchange (9.0 qty, $4.18 entry)
5. Verify dashboard renders correctly (HYPE shows excluded but no position card)
