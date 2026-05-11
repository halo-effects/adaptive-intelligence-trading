# Deposit/Withdrawal Auto-Detection — System Audit

**Date**: 2026-05-11
**Trigger**: Brett deposited $40 USDT, system had no auto-detection
**Scope**: Trace deposit flow through ALL system components

---

## 1. Component Inventory

Every component that touches capital, equity, or allocation:

| # | Component | File | Role |
|---|-----------|------|------|
| 1 | **Exchange Client** | `run_v14_portfolio_live_aster.py` (AsterPerpClient) | Reads DEX balance via `fetch_balance()` |
| 2 | **Exchange Sync** | `_sync_positions_from_exchange()` | Stores `_exchange_usdt_free/total` every 60s |
| 3 | **DEX-as-Truth Startup** | `run()` method, startup block | Sets `_tracked_capital`, `capital` from DEX on boot |
| 4 | **Deposit Detection** | `_detect_capital_change()` | NEW: cycle-to-cycle balance comparison |
| 5 | **Startup Reconciliation** | `run()` method, after DEX-as-truth | NEW: ledger vs DEX on boot |
| 6 | **Capital Ledger** | `v14_capital_manager.py` | Records seed/deposit/withdrawal/pnl_adjustment |
| 7 | **Capital Router** | `v14_capital_manager.py` (CapitalRouter) | Pool split, tier cap, per-coin allocation |
| 8 | **Trade Tracker** | `run_v14_portfolio_live_aster.py` (TradeTracker) | CSV append, realized PnL accumulation |
| 9 | **Status Writer** | `_write_status()` | Writes status.json every 60s for dashboard |
| 10 | **Dashboard (Live)** | `d-984ae0d4ab9dc1a5.html` | Reads status.json, computes growth/equity |
| 11 | **Dashboard (Paper)** | `dashboardV14PM.html` | Same logic, paper bot data |
| 12 | **Dashboard Sync** | `sync_dashboard.ps1` | Copies status.json + trades.csv to docs/data/ |
| 13 | **State Persistence** | `_save_state()` / `_load_state()` | Saves `_tracked_capital` to state.json |
| 14 | **Telegram Commands** | DEPOSIT/WITHDRAW handlers | Manual deposit/withdrawal recording |
| 15 | **HEARTBEAT/Cron** | HEARTBEAT.md checks | Monitors bot health via status.json |
| 16 | **Watchdog** | AIT_Watchdog task | Checks status.json staleness |

---

## 2. Data Flow: Deposit $40 USDT

### 2.1 Immediate (within 60 seconds)

```
Aster DEX Account
  └─ USDT balance: $378 → $418
      │
      ├─ Exchange Sync (every 60s)
      │   └─ _exchange_usdt_total = $418
      │   └─ _exchange_usdt_free += $40
      │
      ├─ Deposit Detection (_detect_capital_change)
      │   ├─ prev_balance = $378 (last cycle)
      │   ├─ pnl_delta = 0 (no trades between cycles)
      │   ├─ funding_delta = ~0
      │   ├─ expected = $378 + 0 + 0 = $378
      │   ├─ actual = $418
      │   ├─ drift = +$40 > threshold ($8.46)
      │   └─ ACTION: Record deposit $40
      │       ├─ Capital Ledger: record_ledger_transaction("deposit", 40)
      │       │   └─ current_capital += 40
      │       ├─ _tracked_capital += 40 → $418
      │       ├─ capital = $418
      │       ├─ Router.resize($418)
      │       │   └─ Recalculates pool split, tier cap
      │       ├─ Telegram alert sent
      │       └─ _save_state() → state.json updated
      │
      └─ Status Writer (every 60s)
          ├─ equity = usdt_total + unrealized = ~$418
          ├─ seed_capital = $300 (immutable)
          ├─ capital = $418
          ├─ tracked_capital = $418
          ├─ net_deposits = $40 (from ledger summary)
          └─ status.json written
```

### 2.2 Dashboard (next sync cycle, ~10 min)

```
Dashboard Sync (sync_dashboard.ps1)
  └─ Copies status.json → docs/data/v14-pm-live/status.json
      └─ GitHub Pages rebuilds (~2 min)
          └─ Dashboard reads:
              ├─ Growth = (equity - seed - net_deposits) / seed
              │         = ($418 - $300 - $40) / $300 = +26%
              ├─ Equity card: $418
              └─ Realized PnL: $18.46 (from CSV, unaffected)
```

### 2.3 Next Daily Rebalance

```
Router.rebalance_daily()
  ├─ Uses self.total_equity (= $418 from resize)
  ├─ Active pool = $418 × 90% = $376.20
  ├─ Reserve pool = $418 × 10% = $41.80
  ├─ Tier cap: 3 coins (equity $100-$500 tier)
  └─ Per-coin allocation proportional to DCA score
      └─ Each coin gets ~$125 max (3 coins × $376 active)
```

### 2.4 Next Bot Restart

```
_load_state()
  └─ tracked_capital = $418 (from state.json)

DEX-as-Truth
  ├─ dex_total = current DEX balance (may have changed from trading)
  ├─ _tracked_capital = dex_total
  ├─ capital = dex_total
  └─ Startup Reconciliation
      ├─ expected = ledger.current_capital + csv_pnl
      ├─ delta = dex_total - expected
      └─ If |delta| > threshold → record deposit/withdrawal
         (Only triggers for NEW deposits since last calibration)
```

---

## 3. Upstream Dependencies

| Dependency | What it provides | Failure mode |
|-----------|-----------------|-------------|
| Aster DEX API | `fetch_balance()` → usdt_total | Returns 0 or throws → detection skipped (safe) |
| ccxt library | Market data, balance parsing | Null baseAsset crash → patched with filter |
| trades.csv | `csv_pnl` for reconciliation | Incomplete → dark PnL gap → absorbed by pnl_adjustment |
| capital_ledger.json | `current_capital` baseline | Missing → uses seed_capital as fallback |
| state.json | `_tracked_capital` on restore | Stale → DEX-as-truth overwrites (safe) |

---

## 4. Downstream Effects

### 4.1 Capital Router (CRITICAL)
- **resize()** called on deposit detection → recalculates pools
- Active pool grows → more capital available for new positions
- Reserve pool grows → larger safety buffer
- Tier cap may change if equity crosses a tier boundary
- **Risk**: If false deposit detected, router gets wrong pool sizes
- **Mitigation**: Threshold max($5, 2%) + stable formula (no unrealized)

### 4.2 Engine Capital
- Engines receive capital via `_compute_capital_per_coin()`
- This reads from `router.active_allocations[sym]`
- Allocations are set during `rebalance_daily()`, which uses `total_equity`
- **Between rebalances**: existing allocations don't change on deposit
- **At next rebalance**: allocations recalculated with new equity
- **Risk**: Mid-cycle deposit means engines don't see extra capital until rebalance
- **Impact**: LOW — deposit sits in cash until rebalance allocates it

### 4.3 Trade Recording
- Deposit does NOT affect trade recording
- Trades are recorded from exchange fills (exchange-as-truth)
- csv_pnl is purely from closed trades
- **Risk**: None

### 4.4 Dashboard
- Growth formula: `(equity - seed - net_deposits) / seed`
- `net_deposits` from `get_ledger_summary()` → only counts type="deposit"
- `pnl_adjustment` type is NOT counted as deposit → correct
- **Risk**: If ledger has wrong deposit total, growth % is wrong
- **Mitigation**: Ledger transactions are append-only, auditable

### 4.5 Status.json
- New fields: `total_deposits`, `total_withdrawals`, `net_deposits`
- Written every 60s from `get_ledger_summary()`
- **Risk**: If ledger read fails, defaults to 0 → growth inflated
- **Mitigation**: try/except with 0 fallback, logged

### 4.6 State Persistence
- `_tracked_capital` saved in state.json via `_save_state()`
- On restore, `_load_state()` reads it back
- DEX-as-truth then overwrites with actual DEX balance
- **Risk**: None — DEX-as-truth is authoritative

### 4.7 Telegram Commands (DEPOSIT/WITHDRAW)
- Still functional as manual override
- Both call same `record_ledger_transaction()` + `router.resize()`
- **Risk**: Double-counting if manual DEPOSIT sent AND auto-detection fires
- **Mitigation**: Auto-detection runs every 60s. If manual command runs first,
  `_tracked_capital` and `_prev_usdt_balance` are both updated, so next cycle's
  delta is zero. If auto-detection fires first, manual command adds on top.
- **Recommendation**: Remove need for manual commands (auto handles it),
  but keep them as admin override for corrections.

---

## 5. Edge Cases

### 5.1 Rapid successive deposits
- Two deposits within 60s: combined into one detection event
- Amount will be sum of both deposits
- **Impact**: Single ledger entry instead of two, but total correct

### 5.2 Deposit + trade in same cycle
- Deposit $40, then TP fills for +$5 PnL in same 60s window
- pnl_delta = $5, so expected = prev + 5 = $383
- actual = $378 + 40 + 5 = $423
- drift = $423 - $383 = $40 → correctly detects $40 deposit
- **Impact**: None — PnL delta cancels out

### 5.3 Bot crash during detection
- Detection writes to ledger BEFORE updating _tracked_capital
- If crash after ledger write but before _tracked_capital update:
  - On restart, DEX-as-truth sets correct _tracked_capital
  - Startup reconciliation checks ledger vs DEX → delta should be small
  - No double-count because ledger.current_capital already updated
- **Impact**: Safe

### 5.4 Exchange API returns 0 balance
- `_sync_positions_from_exchange()` returns early
- Detection skipped (checks `_exchange_usdt_total <= 0`)
- **Impact**: Detection paused until API recovers. No false triggers.

### 5.5 Funding payment between cycles
- Funding changes USDT balance without a trade
- `funding_delta` in detection formula accounts for this
- Tracks `sum(cs.cumulative_funding)` each cycle
- **Impact**: Correctly excluded from deposit detection

### 5.6 Position liquidation
- Would show as: usdt_total drops (position gone), unrealized PnL goes to 0
- But usdt_total reflects the liquidation loss
- Detection: `expected = prev + pnl_delta + funding_delta`
- If liquidation happened, pnl_delta is negative (loss recorded)
- drift should be ~0
- **Risk**: If liquidation isn't recorded as a trade (exchange-specific),
  detection would see a "withdrawal". Low probability given 1x leverage.
- **Mitigation**: 1x leverage makes liquidation near-impossible

### 5.7 Cascade on restart (ADDRESSED)
- Old formula used unrealized PnL → volatile, caused false triggers
- New formula: `expected = ledger_capital + csv_pnl` (stable values only)
- dex_total (usdt_total) also excludes unrealized
- Verified: 3 consecutive restarts, delta = $0.00

---

## 6. Findings

| # | Sev | Finding | Status |
|---|-----|---------|--------|
| D1 | CRITICAL | Old formula used unrealized PnL → cascade risk | ✅ Fixed (removed unrealized) |
| D2 | HIGH | Startup reconciliation lumped dark PnL with real deposit | ✅ Fixed (pnl_adjustment type) |
| D3 | MEDIUM | Manual DEPOSIT + auto-detection could double-count | 🟡 Low risk (timing window <60s, manual not needed) |
| D4 | LOW | Rapid deposits merged into one event | 🟢 By design (total correct) |
| D5 | LOW | Ledger balance_after field not set by record_ledger_transaction | 🟡 Cosmetic |
| D6 | NOTE | ccxt Aster null market crash | ✅ Fixed (endpoint filter) |
| D7 | NOTE | Equity curve on dashboard uses CSV PnL shape + scaling | 🟢 OK (existing behavior) |

---

## 7. Verification Checklist

- [x] Deposit detection fires within 60s of DEX balance change
- [x] Correct amount detected ($40, not $123 or $110)
- [x] Ledger records deposit with correct type and amount
- [x] Router resized with new capital
- [x] Telegram alert sent
- [x] status.json includes net_deposits field
- [x] Dashboard growth subtracts deposits
- [x] No cascade on restart (3x verified, delta=$0.00)
- [x] No false triggers from unrealized PnL swings
- [x] No false triggers from funding payments
- [x] Manual DEPOSIT command still works
- [x] Bot survives exchange API failure (graceful skip)
- [x] ccxt Aster null market patched

---

## 8. Files Modified

| File | Changes |
|------|---------|
| `run_v14_portfolio_live_aster.py` | New `_detect_capital_change()`, startup reconciliation, ccxt patch, net_deposits in status.json |
| `v14_capital_manager.py` | No changes (existing ledger functions work correctly) |
| `d-984ae0d4ab9dc1a5.html` | Growth formula: `(equity - seed - net_deposits) / seed` |
| `dashboardV14PM.html` | Same growth formula update |
| `sync_dashboard.ps1` | Already fixed (fresh clone, no cascade there) |
| `capital_ledger.json` | Baseline: seed=$300, deposit=$40, pnl_adjustment=$64.59 |
