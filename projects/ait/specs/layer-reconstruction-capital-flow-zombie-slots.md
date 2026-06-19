# Layer Reconstruction, Capital Flow Fix & Zombie Slot Replacement

**Date**: 2026-06-19
**Status**: Draft — Pending Approval
**Author**: Brett + Gee Gee
**Severity**: Production change (V14PM Live on Aster — real money)
**Affects**: `run_v14_portfolio_live_aster.py`, `run_v14_portfolio_paper.py`, `d-984ae0d4ab9dc1a5.html`, `dashboardV14PM.html`

---

## 1. Problem Statement

Three cascading failures are preventing the V14PM live bot from deploying $127 idle capital:

### 1.1 Layer Count Reset on Restart (Root Cause)

On every bot restart, `cs.layer_count` resets to 1 for all positions regardless of actual depth. The current exchange sync logic:

```python
if cs.layer_count == 0 and ex_qty > 0:
    cs.layer_count = max(1, eng.long_layers)  # eng.long_layers is 0 → always 1
```

Meanwhile, `open_deals` in state.json preserves the correct layer count:
```json
{
  "JUP/USDT:long": { "layers": 5, "invested": 109.07 },
  "PENDLE/USDT:long": { "layers": 4, "invested": 92.91 },
  "INJ/USDT:long": { "layers": 4, "invested": 116.58 }
}
```

**Root cause**: `_load_state()` restores `cs.layer_count` from `coins[sym].layer_count` (saved as 1 from a previous buggy restart), then `_sync_positions_from_exchange()` overwrites `eng.long_layers` with that wrong value. The authoritative source (`open_deals.layers`) is loaded but never used to reconcile `cs.layer_count`.

### 1.2 DCA Grid Frozen (Capital Starvation)

Engine capital is calculated as `max(0, allocated_capital - invested)`. When invested ($87–$115) exceeds the current allocation ($0–$83), engine capital = $0. The DCA engine's `_long_dca_check()` silently skips BUY actions when `order < $10 or order > self.capital`.

The router has $166 in `active_pool_cash`, but this cash never flows into the per-engine capital. The engines are starved while the router hoards idle cash.

### 1.3 Capital Trapped in Zombie Slots

The tier coin cap (3) blocks new coin entry. The overflow mechanism requires ALL positions at max layers (`cs.layer_count >= 4`), but with layer counts stuck at 1, overflow never triggers. Meanwhile:

- All 3 positions are at L4-L5 (exchange truth) and cannot absorb more capital
- NEAR (score 16.98) and FET (score 15.22) are approved but blocked from entering
- $127 USDT sits idle on-exchange, earning nothing

**The combined effect**: Positions that reached max depth weeks ago appear as L1, preventing overflow. Even if overflow triggered, the positions genuinely can't absorb more capital. And the tier cap prevents new coin entry regardless.

---

## 2. Design Principles

> **Capital should always seek the best available opportunity.** Idle capital is a system failure.

> **The tier cap limits diversification, not capital deployment.** When existing positions are at max layers and can't absorb more capital, the cap should not trap idle funds.

> **Exchange and open_deals are truth for position state.** Engine internal counters are computational tools, not sources of truth. On any conflict, open_deals and exchange win.

---

## 3. Three Fixes

### Fix 1: Layer Count Reconstruction

Reconstruct `cs.layer_count` from `open_deals` on startup, not from engine state.

### Fix 2: Engine Capital Flow

Allow the router's `active_pool_cash` to flow into engines that need capital for DCA layers.

### Fix 3: Zombie Slot Replacement

Positions at max DCA depth that have dropped from the approved list don't count toward the tier cap, freeing slots for new approved coins.

---

## 4. Fix 1 — Layer Count Reconstruction

### 4.1 Current Bug Flow

```
_load_state()
  → cs.layer_count = cs_data["layer_count"]  # 1 (wrong, saved from prior buggy restart)
  → tracker._open_deals[key] = { "layers": 4 }  # correct data, ignored

_sync_positions_from_exchange()
  → if cs.layer_count == 0 and ex_qty > 0:
        cs.layer_count = max(1, eng.long_layers)  # doesn't fire (cs.layer_count=1, not 0)
  → eng.long_layers = cs.layer_count  # overwrites engine with wrong value
```

### 4.2 Fix: Reconcile from open_deals After State Load

After `_load_state()` restores both the coin states and `tracker._open_deals`, reconcile:

```python
def _reconcile_layer_counts(self):
    """Reconcile cs.layer_count with open_deals (authoritative source).
    
    open_deals tracks actual fills. cs.layer_count can drift on restart
    when eng.long_layers is 0 in the engine snapshot. This reconciliation
    ensures the system knows the true depth of each position.
    """
    for sym, cs in self.coins.items():
        deal_key = f"{sym}:long"
        deal = self.tracker._open_deals.get(deal_key)
        if deal and deal.get("layers", 0) > 0:
            true_layers = deal["layers"]
            if cs.layer_count != true_layers:
                logger.warning(
                    f"Layer reconciliation {sym}: cs.layer_count={cs.layer_count} "
                    f"→ {true_layers} (from open_deals)"
                )
                cs.layer_count = true_layers
                if cs.engine and cs.engine._engine:
                    cs.engine._engine.long_layers = true_layers
        # Also handle short deals if applicable
        short_key = f"{sym}:short"
        short_deal = self.tracker._open_deals.get(short_key)
        if short_deal and short_deal.get("layers", 0) > 0:
            true_layers = short_deal["layers"]
            if cs.layer_count != true_layers:
                logger.warning(
                    f"Layer reconciliation {sym}: cs.layer_count={cs.layer_count} "
                    f"→ {true_layers} (from open_deals, short)"
                )
                cs.layer_count = true_layers
                if cs.engine and cs.engine._engine:
                    cs.engine._engine.short_layers = true_layers
```

**Insertion point**: After `_load_state()` returns True, before `_sync_positions_from_exchange()`.

### 4.3 Also Fix the exchange sync fallback

The existing fallback `max(1, eng.long_layers)` should also consult open_deals:

```python
# In _sync_positions_from_exchange(), replace:
if cs.layer_count == 0 and ex_qty > 0:
    cs.layer_count = max(1, eng.long_layers)

# With:
if cs.layer_count == 0 and ex_qty > 0:
    deal_key = f"{sym}:long"
    deal = self.tracker._open_deals.get(deal_key)
    if deal and deal.get("layers", 0) > 0:
        cs.layer_count = deal["layers"]
        logger.info(f"Layer count {sym}: restored {cs.layer_count} from open_deals")
    else:
        cs.layer_count = max(1, eng.long_layers)
        logger.info(f"Layer count {sym}: defaulted to {cs.layer_count} (no open_deal)")
```

### 4.4 Ensure _save_state persists correct layer_count

Verify that `to_dict()` saves `layer_count` from `CoinState` — **already correct** (line 734). The bug is in the restore path, not the save path.

### 4.5 Component Impact

| Component | Affected? | Notes |
|-----------|-----------|-------|
| `_load_state()` | ✅ Add reconciliation call after load | New method `_reconcile_layer_counts()` |
| `_sync_positions_from_exchange()` | ✅ Improve fallback | Consult open_deals before defaulting to max(1, ...) |
| `_save_state()` / `to_dict()` | ❌ Already correct | Saves current cs.layer_count |
| `_execute_action()` BUY | ❌ No change | Still increments cs.layer_count on fill |
| `_execute_action()` SELL/TP | ❌ No change | Still resets cs.layer_count to 0 on close |
| `status.json` writer | ❌ No change | Reads cs.layer_count (now correct) |
| Dashboard | ❌ No change | Reads layer_count from status.json (now correct) |
| Engine tick / DCA check | ✅ Indirect benefit | eng.long_layers now correct → deviation check accurate |
| TradeTracker.on_buy() | ❌ No change | Already increments deal["layers"] on each fill |
| Overflow check | ✅ Indirect benefit | cs.layer_count now accurate → all_maxed evaluates correctly |

---

## 5. Fix 2 — Engine Capital Flow

### 5.1 Current Problem

```
Router active_pool_cash: $166.33   (idle — no mechanism to deploy)
JUP engine.capital:      $0.00     (invested $108 > alloc $83)
PENDLE engine.capital:   $0.00     (invested $87 > alloc $80)
INJ engine.capital:      $12.36    (invested $115 < alloc $139, but only $12 left)
```

The DCA engine needs `engine.capital > 0` to generate BUY actions. Without it, the grid is frozen even though the deviation check would trigger.

### 5.2 Design Decision: Router Capital Top-Up

After each daily rebalance, the router should "top up" engines that have open positions needing DCA capital. Specifically:

**When**: During `_do_rebalance()`, after allocations are computed, for each coin with an open position.

**Formula**:
```
needed_layers = max_layers - current_layers
if needed_layers > 0:
    grid_remaining_cost = calculate_remaining_grid_cost(current_layers, max_layers, allocation)
    top_up = min(grid_remaining_cost, available_active_cash)
    engine.capital += top_up
    router.active_pool_cash -= top_up
```

**Calculate remaining grid cost** (High profile example, BO=40%, mult=1.5x):
```
Layer costs relative to allocation:
  L1: 0.40 × alloc
  L2: 0.60 × alloc  (0.40 × 1.5)
  L3: 0.90 × alloc  (0.40 × 1.5²)
  L4: 1.35 × alloc  (0.40 × 1.5³)

If position is at L3 (layers_remaining=1):
  remaining_cost = L4 cost = 1.35 × alloc
  
If position is at L1 (layers_remaining=3):
  remaining_cost = L2 + L3 + L4 = (0.60 + 0.90 + 1.35) × alloc = 2.85 × alloc
```

### 5.3 Implementation

Add a method to the runner:

```python
def _top_up_engine_capital(self):
    """Push idle router cash into engines that need capital for DCA layers.
    
    When positions are at partial depth (< max_layers), the engine needs
    capital to generate BUY actions for deeper layers. Without this,
    positions freeze when invested > allocation (engine.capital = 0).
    
    Called after rebalance and after layer reconciliation.
    """
    max_layers = self._get_max_layers()
    
    for sym, cs in self.coins.items():
        if not cs.engine or not cs.engine._engine:
            continue
        eng = cs.engine._engine
        
        # Only for coins with open positions that aren't at max depth
        has_position = eng.long_coins > 0 or eng.short_coins > 0
        if not has_position:
            continue
        
        current_layers = cs.layer_count
        if current_layers >= max_layers:
            continue  # Already at max depth — no capital needed
        
        # Calculate capital needed for remaining layers
        remaining_cost = self._remaining_grid_cost(
            current_layers, max_layers, cs.allocated_capital
        )
        
        # How much more does the engine actually need?
        deficit = max(0, remaining_cost - eng.capital)
        if deficit <= 0:
            continue  # Engine already has enough
        
        # Grant from active pool cash (don't drain below a safety floor)
        grant = min(deficit, self.router.active_pool_cash * 0.9)  # Keep 10% buffer
        if grant < 5:  # Not worth granting less than $5
            continue
        
        eng.capital += grant
        self.router.active_pool_cash -= grant
        
        # Track the grant in active_allocations for accounting
        current_alloc = self.router.active_allocations.get(sym, 0)
        self.router.active_allocations[sym] = current_alloc + grant
        
        logger.info(
            f"Capital top-up {sym}: +${grant:.2f} for layers "
            f"{current_layers+1}→{max_layers} "
            f"(engine.capital now ${eng.capital:.2f}, "
            f"router.active_cash now ${self.router.active_pool_cash:.2f})"
        )

def _remaining_grid_cost(self, current_layers: int, max_layers: int, 
                          allocation: float) -> float:
    """Calculate the total cost of unfilled DCA layers.
    
    Uses the grid formula: each layer cost = allocation × BO_PCT × mult^layer
    """
    bo_pct = 0.40  # High profile base order percentage
    mult = 1.5     # SO volume multiplier
    
    total = 0.0
    for layer in range(current_layers, max_layers):
        if layer == 0:
            layer_cost = allocation * bo_pct
        else:
            layer_cost = allocation * bo_pct * (mult ** min(layer, 4))
        total += layer_cost
    return total
```

### 5.4 When to Call

1. **After `_reconcile_layer_counts()`** on startup — so the first tick has correct capital
2. **After `_do_rebalance()`** daily — when allocations change, recalculate engine capital needs
3. **After a BUY fill in `_execute_action()`** — update remaining capital needs (already handled by `router.request_capital()`)

### 5.5 Capital Return on TP

When a position closes at TP, `_execute_action()` already calls `router.return_capital()`. No change needed — the topped-up capital returns to the pool naturally.

### 5.6 Interaction with request_capital()

The existing `request_capital()` flow in `_execute_action()` BUY remains unchanged. The top-up ensures the engine has capital to *generate* BUY actions inside `tick()`. The `request_capital()` call in the runner then routes the actual order cost through the router's accounting. 

**Potential double-accounting**: The engine's `self.capital` is reduced inside `tick()` when it generates a BUY. Then `request_capital()` also deducts from the router. This is correct because they track different things: engine.capital is the engine's internal budget; router tracks pool-level allocation.

However, we must ensure the engine doesn't generate orders larger than what it actually has. The top-up sets `engine.capital` to the remaining grid cost — the engine will size orders from this, and `request_capital()` verifies the router can cover it.

### 5.7 Component Impact

| Component | Affected? | Notes |
|-----------|-----------|-------|
| `_do_rebalance()` | ✅ Call `_top_up_engine_capital()` after allocation | New call site |
| `_load_state()` | ✅ Call after `_reconcile_layer_counts()` | Startup path |
| `CapitalRouter` | ❌ No change | `active_pool_cash` is modified by runner, not router |
| `_execute_action()` BUY | ❌ No change | Still uses `request_capital()` for order-level accounting |
| `_execute_action()` SELL/TP | ❌ No change | `return_capital()` handles cleanup |
| `_sync_positions_from_exchange()` | ❌ No change | Position data only; capital not touched |
| `status.json` writer | ✅ Verify | `router.active_cash` should reflect post-top-up value (already does — reads from `self.router.active_pool_cash`) |
| Dashboard | ❌ No change | Reads cash from status.json |
| Deposit detection | ❌ No change | Uses `usdt_balance` from exchange, not router internal state |
| Capital ledger | ❌ No change | Ledger tracks deposits/withdrawals, not internal routing |

---

## 6. Fix 3 — Zombie Slot Replacement

### 6.1 Definition

A **zombie slot** is a position that:
1. Is at **max DCA depth** (`cs.layer_count >= max_layers`) — cannot absorb more capital
2. Has **dropped from the current approved list** — the scanner no longer ranks it in the top N
3. Is waiting for TP to exit — could be weeks or months in a deep drawdown

A zombie slot consumes a tier cap position while contributing no capital velocity. The capital it holds is locked until TP, and the slot prevents a fresh, high-scoring coin from entering.

### 6.2 Design Rule

> **Zombie slots do not count toward the tier coin cap for new T1 entries.**

When evaluating whether to create a new engine during rebalance:

```
effective_active_count = count of positions that are NOT zombie slots
if effective_active_count < tier_cap:
    allow new coin entry
```

This means:
- If 3/3 positions are active and approved → no new entry (normal cap enforcement)
- If 2/3 are approved and 1 is a zombie → effective count is 2 → new entry allowed
- If 1/3 is approved and 2 are zombies → effective count is 1 → 2 new entries allowed

### 6.3 Zombie Detection Criteria

A position is a zombie when ALL of:
1. `cs.layer_count >= max_layers` (at max DCA depth)
2. `sym not in current_approved_symbols` (not in the latest scanner top-N after rebalance)
3. `has_open_position` (exchange qty > 0 — the slot is occupied)

**Why require "not in approved list"?** A position at max depth that IS still approved should NOT be a zombie — its presence in the approved list means the scanner still considers it a strong performer. It's temporarily at max depth but may TP soon and re-enter with a new deal. The system should not undermine an approved coin by skipping its slot.

**Why require "at max depth"?** A position that hasn't reached max depth can still absorb capital via DCA layers (especially after Fix 2). Only positions that have exhausted all grid capacity are truly "stuck."

### 6.4 Implementation

Modify the rebalance gate in `_do_rebalance()`:

```python
# Current code:
active_coins = [
    sym_ for sym_, cs_ in self.coins.items()
    if cs_.engine and cs_.engine._engine
    and (cs_.engine._engine.long_coins > 0 or cs_.engine._engine.short_coins > 0)
]
active_count = len(active_coins)

# New code:
max_layers = self._get_max_layers()
# Get current approved symbols from rebalance targets
approved_set = set(allocations.keys())

active_coins = []
zombie_coins = []
for sym_, cs_ in self.coins.items():
    if not (cs_.engine and cs_.engine._engine):
        continue
    eng_ = cs_.engine._engine
    has_position = eng_.long_coins > 0 or eng_.short_coins > 0
    if not has_position:
        continue
    
    is_zombie = (
        cs_.layer_count >= max_layers
        and sym_ not in approved_set
    )
    
    if is_zombie:
        zombie_coins.append(sym_)
    else:
        active_coins.append(sym_)

active_count = len(active_coins)  # Zombies excluded from cap count
total_positions = len(active_coins) + len(zombie_coins)

if zombie_coins:
    logger.info(
        f"Zombie slots detected: {zombie_coins} "
        f"(at L{max_layers} max, not in approved list). "
        f"Effective cap usage: {active_count}/{tier_cap} "
        f"(total positions: {total_positions})"
    )
```

Then the existing gate check uses the new `active_count` which excludes zombies:

```python
if tier_cap > 0 and active_count >= tier_cap:
    # Overflow check (existing logic) ...
    if not allow_overflow:
        logger.info(f"Skipping new coin {sym} — at tier cap ...")
        continue
```

### 6.5 Interaction with Overflow

The overflow mechanism (`OVERFLOW_ENTRY_ENABLED`) allows +1 beyond the cap when ALL positions are at max layers. With zombie slots:

- If ALL non-zombie positions are at max layers AND zombies exist → overflow could trigger
- But zombies already freed the slot, so overflow may not be needed
- **Rule**: Evaluate overflow against `active_count` (non-zombie), not `total_positions`
- If `active_count < tier_cap` (thanks to zombie exclusion), no overflow needed — normal entry
- If `active_count == tier_cap` and all are at max layers, overflow allows +1 as before

### 6.6 Zombie Lifecycle

```
1. Coin enters at L1, DCA's to L4
2. Scanner scores decline → coin drops from approved list on next rebalance
3. Coin is now a zombie: at max depth, not approved
4. Zombie doesn't count toward tier cap → new approved coin enters
5. Eventually, zombie position hits TP → closes naturally
6. On TP close, capital returns to router pool
7. Next rebalance cleans up the stale allocation (existing cleanup logic)
8. Slot is fully freed — both capital and position are gone
```

### 6.7 Edge Cases

| Scenario | Handling |
|----------|----------|
| Zombie coin re-enters approved list (score recovers) | No longer a zombie — counts toward cap normally. Natural resolution. |
| All positions are zombies | active_count=0. Multiple new coins can enter up to tier_cap. Each gets its own allocation from the large idle cash pool. |
| Zombie TPs during a tick (between rebalances) | `_rotate_after_tp()` handles post-TP rotation normally. The freed slot reduces total_positions. |
| New coin enters and immediately goes to max depth | Possible but unlikely — new positions need significant price movement to reach L4. If it does AND falls from approved: becomes a zombie. |
| Equity drops, tier_cap decreases | Zombies still don't count. If active_count > new_tier_cap, normal graceful degradation applies (no forced closes). |
| Coin is paused or regime-flagged AND at max depth AND not approved | The paused/regime gate already blocks entries independently. Zombie status is about cap counting, not entry permission. These are separate gates that stack. |

### 6.8 Component Impact

| Component | Affected? | Notes |
|-----------|-----------|-------|
| `_do_rebalance()` engine creation gate | ✅ Modify | Split active vs zombie counts; use active_count for cap |
| `_do_rebalance()` allocation cleanup | ❌ No change | Existing `has_position` guard protects zombie coins from premature cleanup |
| `_do_rebalance()` allocation seeding | ❌ No change | New approved coins get seeded normally |
| Overflow check | ✅ Modify | Evaluate against active_count, not total positions |
| `CapitalRouter.tier_coin_cap` | ❌ No change | Cap value unchanged; zombie logic is in runner |
| `CapitalRouter.rebalance_daily()` | ❌ No change | Router allocates to top-N. Zombie coins naturally drop out of targets. |
| `_execute_action()` T1 gate | ❌ No change | Checks `active_allocations`. New coins seeded by rebalance pass T1. |
| `_execute_action()` regime gate | ❌ No change | Independent gate. |
| `_rotate_after_tp()` | ❌ No change | When zombie TPs, rotation evaluates normally. |
| Status writer / `status.json` | ✅ Enhance | Add `zombie_slots` list and `effective_cap_usage` to status |
| Dashboard | ✅ Enhance | Show zombie indicator on position cards (optional — visual only) |
| Dashboard sync | ❌ No change | Reads status.json. New fields are additive (backward compatible). |
| State persistence | ❌ No change | Zombie status is computed dynamically at rebalance time. Not persisted — recalculated on every rebalance. |
| Deposit detection | ❌ No change | Independent system. |
| Trailing TP / order management | ❌ No change | Zombie positions have existing TP orders. Same TP lifecycle. |
| Engine tick / candle processing | ❌ No change | Zombie engines still tick and check TP. They just don't generate new entries (already at max layers). |

---

## 7. Startup Sequence (Updated)

```
1. Acquire PID lock
2. Load trade history (TradeTracker.load_existing())
3. _load_state() → restore engines, router, open_deals
4. NEW: _reconcile_layer_counts() → fix cs.layer_count from open_deals
5. _sync_positions_from_exchange() → sync position data from exchange
6. NEW: _top_up_engine_capital() → push idle router cash into engines
7. _recover_tp_orders() → check/place TP orders on exchange
8. _reconcile_trades_on_startup() → check for missed fills
9. _check_and_rebalance() → run initial rebalance with zombie detection
10. Enter live trading loop
```

Steps 4 and 6 are the new additions. Step 9 now includes zombie slot logic.

---

## 8. Status.json Changes

Add new fields for monitoring:

```json
{
  "coins": {
    "JUP/USDT": {
      "layer_count": 5,
      "is_zombie": false,
      ...
    },
    "ONDO/USDT": {
      "layer_count": 0,
      "is_zombie": false,
      ...
    }
  },
  "zombie_slots": ["HYPE/USDT"],
  "effective_cap_usage": "2/3 (1 zombie)",
  "tier_coin_cap": 3
}
```

The `is_zombie` per-coin flag and `zombie_slots` list are computed at status write time (same criteria as rebalance). The `effective_cap_usage` string is human-readable for the dashboard and heartbeat monitoring.

---

## 9. Dashboard Changes

### 9.1 Live Dashboard (`d-984ae0d4ab9dc1a5.html`)

- **Position cards**: If `is_zombie` is true, show a visual indicator (e.g., gray badge "ZOMBIE — waiting for TP", or skull emoji)
- **Layer count**: Already reads `layer_count` from status.json. Will now show correct values (e.g., "4/4" instead of "1/4")
- **Capital summary**: Already shows `router.active_cash`. Will now reflect post-top-up values.
- **Cap display**: Change tier cap badge to show effective usage: "Active: 2/3 (1 zombie)" instead of "3/3"

### 9.2 Paper Dashboard (`dashboardV14PM.html`)

Same changes. The paper runner gets the same three fixes.

### 9.3 Dashboard Sync (`sync_dashboard.ps1`)

No change needed. The sync script copies `status.json` → `docs/data/` → GitHub Pages. New fields are additive and won't break existing dashboard rendering (HTML reads from JSON dynamically).

---

## 10. Paper Runner Parity

Apply all three fixes to `run_v14_portfolio_paper.py`:

1. **Layer reconciliation**: Same `_reconcile_layer_counts()` method
2. **Capital top-up**: Same `_top_up_engine_capital()` method (paper runner uses `self.engines` instead of `self.coins` — adapt accessor names)
3. **Zombie slot detection**: Same logic in the rebalance gate

The paper runner's engine/state structure is similar but not identical (e.g., `self.engines` vs `self.coins`). Implementation must adapt to the paper runner's data model.

---

## 11. Risk Assessment

| Risk | Likelihood | Severity | Mitigation |
|------|------------|----------|------------|
| Layer reconciliation assigns wrong count | Very Low | Medium | open_deals is the source of truth — it tracks every fill. Cross-verify with exchange position (invested amount) on first run. |
| Capital top-up over-allocates (engine gets too much) | Low | Low | Top-up is capped at remaining grid cost. Router keeps 10% buffer. On TP close, all capital returns to pool. |
| Capital top-up double-counts with request_capital() | Low | Medium | Engine reduces its `self.capital` inside tick(). `request_capital()` checks router cash independently. Both must succeed for order to execute. Monitor first few BUY fills after deployment. |
| Zombie detection false positive (good coin excluded from cap) | Very Low | Low | Requires BOTH max layers AND not-in-approved. A coin must fail both criteria. If score recovers, it un-zombifies automatically. |
| Zombie detection causes too many new entries | Low | Medium | New entries still pass all existing gates: hurdle rate, regime gate, liquidity filter, capital availability. Only the cap count changes. |
| Dashboard shows stale zombie status | Very Low | Very Low | Zombie is recomputed every status.json write (~60s). Dashboard refreshes on page load. |
| Paper runner diverges from live | Low | Low | Apply same code to both runners. Paper validates behavior before live deployment. |

---

## 12. Testing Plan

### 12.1 Pre-deployment (Paper Bot)

1. Deploy all three fixes to `run_v14_portfolio_paper.py`
2. Restart paper bot and verify:
   - Layer counts match open_deals (check bot.log for "Layer reconciliation" messages)
   - Engine capital is topped up (check "Capital top-up" log messages)
   - Engines generate BUY actions for remaining layers (watch for L2/L3/L4 fills)
3. If any position is at max depth and not in approved list, verify zombie detection:
   - Check "Zombie slots detected" log message
   - Verify effective cap usage allows new coin entry
4. Run for 24+ hours and verify:
   - No phantom trades
   - Capital routing is consistent (pool cash + engine capitals = active pool total)
   - Dashboard shows correct layer counts

### 12.2 Live Bot Deployment

1. Pre-flight import test (Hard Rule #19):
   ```
   python -c "from trading.spot.run_v14_portfolio_live_aster import V14PortfolioLiveAster; print('OK')"
   ```
2. Restart live bot
3. Immediately verify:
   - Bot.log shows layer reconciliation: JUP→5, PENDLE→4, INJ→4
   - Engine capital topped up for any positions below max layers
   - Existing TP orders preserved on exchange (check Aster)
   - Status.json layer_count matches open_deals
4. Monitor for 24h:
   - Dashboard shows correct layer counts
   - If any DCA layers fire, verify fills are correct
   - If zombie slot triggers, verify new coin entry works

### 12.3 Regression Checks

- [ ] Existing TP orders are NOT cancelled or modified
- [ ] No new entries for paused/regime-flagged coins
- [ ] No forced closes
- [ ] Deposit detection still works (balance comparison unaffected)
- [ ] Dashboard sync still works (new JSON fields don't break HTML)
- [ ] State.json saves correctly (layer_count persisted at correct value)
- [ ] On next restart, layer_count is correctly reconciled again

---

## 13. Hard Rules Compliance

| Rule | Status |
|------|--------|
| #19: Pre-flight import test | ✅ Required before restart |
| #20: No batched fixes per restart | ⚠️ Three fixes — but they are tightly coupled (all address the same root cause and its cascading effects). Can deploy as one unit. |
| #21: Explicit spec and approval | ✅ This document |
| #26: seed_capital immutable | ✅ Not touched |
| #29: Trade CSV append-only | ✅ Not touched |
| #30: No unrealized in detection | ✅ Not touched |
| #31: Idempotent restart | ✅ Layer reconciliation is idempotent (reads open_deals, writes same value each time). Capital top-up is idempotent (recalculated from current state). |
| #32: Post-tick gates rollback | ✅ Not touched — all existing gates intact |
| #33: Read arch spec before code | ✅ Full architecture doc reviewed |
| #34: No forced closes | ✅ Zombie positions exit via TP only |

---

## 14. Files Changed

| File | Changes |
|------|---------|
| `run_v14_portfolio_live_aster.py` | Add `_reconcile_layer_counts()`, `_top_up_engine_capital()`, `_remaining_grid_cost()`. Modify `_do_rebalance()` for zombie slot detection. Modify exchange sync fallback. Update status writer for new fields. |
| `run_v14_portfolio_paper.py` | Same three fixes adapted to paper data model |
| `d-984ae0d4ab9dc1a5.html` | Show zombie indicator, correct cap display, layer count already correct via status.json |
| `dashboardV14PM.html` | Same dashboard changes as live |
| `V14PM_SYSTEM_ARCHITECTURE.md` | Document layer reconciliation, capital top-up, zombie slots in §7.2 and §7.3. New section §7.6 for zombie slot lifecycle. |
| `tacit/hard-rules.md` | Add rules: #35 (open_deals is truth for layer count), #36 (idle router cash must flow to engines needing DCA capital) |

---

## 15. Decision Record

| Question | Answer | Rationale |
|----------|--------|-----------|
| Should zombie status be persisted in state.json? | No — computed dynamically | Zombie depends on current approved list, which changes daily. Persisting would create stale data. |
| Should zombie positions be force-closed? | No — exit via TP only | Hard Rule #34. Zombie is about cap counting, not position management. |
| Should capital top-up happen every tick or just on rebalance? | Rebalance + startup | Every tick would be wasteful (capital needs don't change hourly unless a layer fills). On BUY fill, the engine's capital is already updated. |
| Should the paper runner be changed first or simultaneously? | Paper first (24h validation) | Paper validates behavior in a safe environment before live deployment. |
| Can all three fixes be deployed together? | Yes — tightly coupled | Fix 1 (layer reconstruction) is prerequisite for Fix 2 (capital flow needs correct depth) and Fix 3 (zombie needs correct depth). Deploying separately would require multiple restarts with partial behavior. |
| Max total positions (zombies + active + overflow)? | No hard limit | Zombies don't count toward cap. Active is limited by cap. Overflow adds +1 to cap. Total positions = active (≤ cap) + overflow (≤ 1) + zombies (unlimited but practically bounded by historical positions). Each zombie is passively waiting for TP — no capital drain. |
