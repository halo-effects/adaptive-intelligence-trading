# Spec: DEX-as-Truth Startup Sequence

**Status**: IMPLEMENTED (2026-05-08) — deployed and verified
**Date**: 2026-05-08
**Priority**: CRITICAL (bot can't start with correct capital)

## Problem

The bot's startup sequence has multiple systems fighting over capital truth:

1. **CLI `--capital` arg**: Manual seed value
2. **Capital ledger** (`ledger.json`): Tracks deposits/withdrawals over time
3. **State file** (`state.json`): Saves `tracked_capital` from last session
4. **Reconciliation**: Pulls 48h of DEX fills, creates synthetic trades from heuristic grouping
5. **Deposit detection**: Compares exchange balance to tracked capital, auto-adjusts for drift

These interact badly:
- Reconciliation creates phantom trades from churn fills → inflates realized PnL → inflates capital
- Deposit detection sees capital/exchange mismatch → creates fake deposit/withdrawal
- State file carries forward corrupted capital from prior session
- Each restart compounds the errors

**Real-world result** (May 8, 2026):
- DEX wallet: **$385.09**
- Bot thinks: **$597.64** (wrong)
- After my fix attempts: **$288.32** (even more wrong)

## Root Cause

The bot treats `state.json`, `trades.csv`, and `ledger.json` as co-equal sources of truth alongside the DEX. When they disagree (which they always will after corruption), the bot has no way to resolve the conflict correctly.

## Solution: DEX Balance Is the Only Source of Truth for Capital

### Startup Sequence (new)

```
1. Connect to exchange
2. Fetch wallet balance → this IS the tracked capital
3. Fetch open positions → this IS the current position state
4. Fetch open orders → these ARE the active TP orders
5. Load state.json for engine state ONLY (indicators, warmup, last_candle_ts)
6. Load trades.csv as append-only history (for dashboard/reporting only)
7. Calculate: seed_capital = exchange_balance - sum(csv_pnl)
   This gives us the implied seed for growth% calculations
8. Skip reconciliation entirely (no need — the DEX state IS the state)
9. Disable deposit detection for first 2 poll cycles (let things stabilize)
10. Start main loop
```

### Capital Equation

```
exchange_balance = seed_capital + realized_pnl + unrealized_pnl
tracked_capital  = exchange_balance  (always, read from DEX)
seed_capital     = exchange_balance - csv_realized_pnl - current_unrealized_pnl
growth_pct       = csv_realized_pnl / seed_capital * 100
```

### What Changes

| Component | Before | After |
|-----------|--------|-------|
| `_tracked_capital` | Loaded from state.json | Read from DEX `fetch_balance()` |
| `_seed_capital` | CLI `--capital` arg | Calculated: `exchange_balance - realized_pnl - unrealized_pnl` |
| `_cumulative_realized_pnl` | State file | Sum of `trades.csv` PnL column |
| Reconciliation | 48h lookback on every restart | **Disabled** — replaced by TP order recovery |
| Deposit detection | Every sync cycle | Delayed 2 cycles on startup; uses DEX as baseline |
| `--capital` CLI | Required, sets seed | Optional, used only for `--fresh` starts |

### What Doesn't Change

- Engine state restoration (indicators, phases, warmup) — still from state.json
- TP order recovery — still checks if saved order IDs are open on exchange
- Trade recording — still writes to CSV on TP fill
- Main loop — unchanged

### Implementation

**File**: `run_v14_portfolio_live_aster.py`

**Location**: In `run()`, replace the block between "Initial exchange position sync" and "Announce startup"

**Code changes**:

1. After `_sync_positions_from_exchange()`, fetch balance and set capital:
```python
# DEX-as-truth: exchange balance IS the capital
dex_balance = self.client._exchange.fetch_balance()
dex_total = float(dex_balance.get("USDT", {}).get("total", 0))
if dex_total > 0:
    # Realized PnL from CSV (append-only history)
    csv_pnl = sum(float(t.get("pnl", 0)) for t in self.tracker.trades)
    
    # Unrealized PnL from current positions
    unrealized = sum(
        float(p.get("unrealizedPnl", 0))
        for p in self.client._exchange.fetch_positions()
        if float(p.get("contracts", 0)) > 0
    )
    
    # Set capital from DEX
    self._tracked_capital = dex_total
    self.capital = dex_total
    self._cumulative_realized_pnl = csv_pnl
    self._seed_capital = dex_total - csv_pnl - unrealized
    self.router.resize(dex_total)
    
    # Suppress deposit detection for 2 cycles
    self._deposit_detection_skip_until = time.time() + (LIVE_POLL_INTERVAL * 2)
    
    logger.info(
        f"DEX-as-truth: balance=${dex_total:.2f} "
        f"seed=${self._seed_capital:.2f} "
        f"realized=${csv_pnl:.2f} unrealized=${unrealized:.2f}"
    )
```

2. In `_detect_deposit_withdrawal()`, add early return:
```python
if hasattr(self, '_deposit_detection_skip_until') and time.time() < self._deposit_detection_skip_until:
    return
```

3. Remove `_reconcile_trades_on_startup()` call (or make it a no-op for now)

4. Make `--capital` optional (default to 0, meaning "read from DEX")

### Risks

- **If DEX API is down on startup**: Fall back to state.json (current behavior). Log a warning.
- **If CSV is corrupted**: `seed_capital` calculation will be wrong, but `tracked_capital` will still be correct from DEX. Only growth% would be off.
- **If a trade filled while bot was down**: TP recovery already handles this. The fill shows up in exchange fills, and the next TP check will record it.

### Testing

1. Start bot, verify capital matches `fetch_balance()` USDT total
2. Verify no "Deposit detected" or "Withdrawal detected" on startup
3. Verify engine processes candles normally
4. Verify TP fills are recorded correctly
5. Let it run for 2+ hours, verify no capital drift

## What This Doesn't Fix (Yet)

- **Data sync cron overwriting source files** — separate issue, needs sync script fix
- **CSV reconciliation corruption** — eliminated by removing reconciliation
- **Proper database migration** — long-term, replaces CSV entirely
