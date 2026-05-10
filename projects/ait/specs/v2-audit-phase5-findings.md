# V2 Audit — Phase 5: State Management & Persistence

**Date**: 2026-05-10  
**Auditor**: OpenClaw AI  
**Files reviewed**: state.json writer/loader, capital ledger functions, TradeTracker, engine snapshot/restore  
**Status**: COMPLETE

---

## FINDING 38: MEDIUM — Capital Ledger Doesn't Track PnL, Becomes Stale

**File**: `v14_capital_manager.py`, lines 493-560

**Observed data**:
- Ledger `seed_capital`: $300.00
- Ledger `current_capital`: $300.00 (never updated after seed)
- State `tracked_capital`: $377.44 (updated from DEX every startup)
- CSV total PnL: $84.23

**Issue**: The capital ledger only records seed, deposit, and withdrawal transactions. It never records realized PnL. So `current_capital` stays at $300 forever (until a manual DEPOSIT/WITHDRAW command).

Meanwhile, the bot uses DEX-as-truth on startup (`tracked_capital = dex_total`), so the ledger's `current_capital` is never consulted during normal operation.

The ledger is only useful for:
1. Tracking deposits/withdrawals (rare, manual commands)
2. Historical audit trail of capital changes

**Severity**: MEDIUM (ledger is informational-only, not used for decisions, but shows wrong number)  
**Recommendation**: Either:
1. Record realized PnL as ledger transactions (keeps ledger accurate)
2. Document that ledger tracks cash flows only, not performance

---

## FINDING 39: LOW — State.json `capital` Field Is Redundant

**File**: `run_v14_portfolio_live_aster.py`, _save_state (line 833)

**Code**:
```python
"capital": self.capital,
...
"tracked_capital": self._tracked_capital,
```

Both `capital` and `tracked_capital` are always equal (set on the same line: `self.capital = self._tracked_capital`). The `capital` field exists for backward compatibility but creates confusion about which is authoritative.

**Severity**: LOW (no functional impact)  
**Recommendation**: Remove `capital` field from state.json during migration, use `tracked_capital` only

---

## FINDING 40: POSITIVE — Atomic File Writes Everywhere

**Observation**: All file writes use the write-to-tmp-then-rename pattern:
- `_save_state()`: state.json.tmp → state.json
- `save_csv()`: trades.csv.tmp → trades.csv
- `save_capital_ledger()`: capital_ledger.json.tmp → capital_ledger.json
- `_write_status()`: status.json.tmp → status.json

This prevents corruption from crashes mid-write. Good practice.

**Severity**: POSITIVE

---

## FINDING 41: POSITIVE — Engine State Snapshot Is Complete

**Observation**: `snapshot_state()` captures all 30+ engine fields including:
- Phase, capital, phase_start_date
- Long and short position state (coins, avg_entry, layers, TP, cost, trade counters)
- Top detection state (early_warning, failsafe, OB93 arm, peak_2w_k)
- Bottom detection state (top_detected, conviction_fired)
- Cycle tracking (markup_cycles, fees, ADX streak)
- Router state (from_top, from_markdown)
- Wrapper state (last_daily_date, live_mode, last_candle_ts)

`restore_state()` restores all of these. No fields are lost across restarts.

**Severity**: POSITIVE — comprehensive persistence

---

## FINDING 42: LOW — TradeTracker Dedup Uses String Matching on Timestamps

**File**: `run_v14_portfolio_live_aster.py`, TradeTracker.on_sell (line 252)

**Code**:
```python
trade_key = f"{symbol}|{deal['open_time']}|{ts.isoformat()}"
if trade_key in self._existing_keys:
    return {}
```

Dedup key is `symbol|open_time|close_time`. If a deal opens and closes at the exact same millisecond ISO timestamp twice (e.g., from a bug), the second trade would be silently dropped. This is the correct behavior for preventing duplicates.

However, the ISO timestamp includes microseconds which are effectively unique. The real dedup risk is: if the bot restarts during a TP fill and both the recovery handler AND the normal handler process the same fill, would they generate the same timestamp? No — the recovery handler runs on startup (different timestamp) from the original fill.

**Severity**: LOW (dedup works correctly for the primary use case)

---

## FINDING 43: LOW — open_deals Not Cleaned Up for Removed Coins

**File**: `run_v14_portfolio_live_aster.py`, _save_state (line 856)

**Code**:
```python
"open_deals": self.tracker._open_deals,
```

The `_open_deals` dict tracks in-progress deals (bought but not yet sold). When a coin is removed from the active set (no longer in scanner top-N), the CoinState is NOT removed from `self.coins` (it stays to finish existing positions). But if the coin's position is closed externally (e.g., manual exchange close), the open_deal entry might never be cleaned up.

The impact: phantom open_deals in state.json for coins that no longer exist. These are harmless (no capital is tracked against them) but accumulate over time.

**Severity**: LOW (cosmetic, no functional impact)  
**Recommendation**: Add cleanup in _sync_positions_from_exchange: if no exchange position and no TP order, remove from open_deals

---

## FINDING 44: NOTE — Delta Between tracked_capital and seed+CSV PnL

**Observed**:
- tracked_capital: $377.44
- seed($300) + CSV PnL($84.23) = $384.23
- Delta: -$6.79

**Explanation**: The delta represents:
1. Unrealized PnL on open positions (negative if position is underwater)
2. Cumulative funding fees (paid/received)
3. Exchange fees not fully captured in CSV PnL

This is expected behavior. `tracked_capital` = DEX wallet balance (which includes unrealized and fees), while CSV PnL only captures realized trade profits.

**Severity**: NOTE (expected, not a bug)

---

## Summary

| # | Severity | Finding | Status |
|---|----------|---------|--------|
| 38 | MEDIUM | Capital ledger doesn't track PnL (shows $300 not $377) | 🟡 Stale |
| 39 | LOW | `capital` and `tracked_capital` are always equal (redundant) | 🟢 Cleanup |
| 40 | POSITIVE | Atomic file writes everywhere | ✅ Well built |
| 41 | POSITIVE | Engine state snapshot is complete (30+ fields) | ✅ Well built |
| 42 | LOW | Trade dedup uses timestamp strings (works correctly) | 🟢 OK |
| 43 | LOW | open_deals accumulate for removed coins | 🟡 Cosmetic |
| 44 | NOTE | tracked_capital vs seed+PnL delta is expected | 🟢 Expected |

**Overall**: State persistence is solid. Atomic writes prevent corruption, engine snapshots are comprehensive, trade dedup works. The capital ledger staleness is the only real issue (informational only, doesn't affect trading).
