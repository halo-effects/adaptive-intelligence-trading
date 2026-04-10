# V14PM Live Bot — Upgrade Scope

> **Updated 2026-03-24** — All four upgrades (0–3) deployed to V14PM Live. Upgrade 0 (Adaptive Tiers), Upgrade 1 (Dynamic Capital), Upgrade 2 (Per-Coin Pause), Upgrade 3 (Per-Coin Regime Flagging) all live on Aster Perps.

**Date:** 2026-03-24
**Status:** All upgrades deployed and running on V14PM Live (Aster Perps, ~$340 USDT)

---

## Upgrade 0: Adaptive Equity Tiers & Pool Split

### Why This Is Upgrade 0

Brett is adding $1,000 initially, then $1,500 more (total ~$3K) to the V14PM Live account. The current tier table puts $3K in the 1-coin tier — the same configuration that's been stuck in a single GRASS trade for days. Meanwhile the paper bot ($50K, 5 coins) is averaging 12+ deals/day with 100% win rate.

**This upgrade must land before the capital deposit.** It determines how many coins trade and how capital is split, which directly affects turnover and the investor demo story.

**Strategic context:** This capital is the first tranche of outside investment. Showing consistent, high-frequency positive trades at $3K will attract more capital. The goal is to demonstrate the system works at small scale, then grow to $10K+ quickly where the proven 5-coin paper configuration applies naturally.

### Data-Driven Analysis (from Paper Bot: 220 trades, March 3–23, 2026)

#### Layer Depth Distribution — Most Trades Close Shallow

| Layers | Trades | Cumulative % | Avg Duration | Avg Return |
|--------|--------|-------------|-------------|-----------|
| 1 | 139 | 63.2% | 4.6h | 1.86% |
| 2 | 49 | 85.5% | 17.1h | 1.76% |
| 3 | 20 | 94.5% | 24h | 1.77% |
| 4 | 10 | 99.1% | 59.5h | 1.76% |
| 5-6 | 3 | 100% | ~16h | 1.48% |

**Key finding:** 85.5% of trades close at layer 2 or fewer. 99.1% close at layer 4. The deepest *completed* trade was 6 layers. ZRO is currently at 11 layers (open, unrealized). **10 viable layers is sufficient to cover all historical outcomes.**

#### Coin Turnover — 3 Coins Capture Majority of Activity

| Coin | Trades | Cycles/Day | Total PnL | Avg Duration |
|------|--------|-----------|-----------|-------------|
| GRASS | 45 | 2.5 | $2,654 | 5h |
| TAO | 37 | 2.1 | $2,467 | 7.4h |
| EIGEN | 29 | 1.6 | $1,072 | 6h |
| HYPE | 27 | 1.5 | $1,142 | 7.5h |
| ZRO | 16 | 0.9 | $1,037 | 13.1h |

- **Top 3 coins: 112 trades (51%), ~7 deals/day, $6,193 PnL**
- Top 5 coins: 155 trades (70%), ~10 deals/day, $8,372 PnL
- Coins ranked 4-5 add ~3 deals/day but require 40% more capital spread

**3 coins at $3K = ~7 deals/day projected.** This is the optimal balance of turnover vs. grid depth for the demo phase.

#### Return % Is Independent of Lot Size

The TP engine takes profit at 1.5% regardless of position size. At $3K with 3 coins:
- Typical layer 1 deal: ~$300 invested × 1.86% = ~$5.50 per trade
- ~7 trades/day × $5.50 = ~$38/day
- **Projected: ~$1,150/month or ~38% monthly return**
- Visible, consistent, documented wins on a real exchange

#### Aster Perps Minimum Order Size

**$5 USDT for all symbols** — confirmed via ccxt `exchangeInfo`. This is the binding constraint for layer sizing.

### What Exists Today

```python
# v14_capital_manager.py — current static configuration
EQUITY_TIER_CAPS = [
    (100_000, 10),  # $100K+ -> up to 10 coins
    ( 50_000,  5),  # $50K-$100K -> up to 5 coins
    ( 30_000,  4),  # $30K-$50K -> up to 4 coins
    ( 20_000,  3),  # $20K-$30K -> up to 3 coins
    ( 10_000,  2),  # $10K-$20K -> up to 2 coins
    (    100,  1),  # $100-$10K -> 1 coin   ← $3K falls here
]

# Pool split: fixed 75% active / 25% reserve
self.active_pool_total = self.total_equity * 0.75
self.reserve_pool_total = self.total_equity * 0.25
```

**Problems at $3K with current config:**
- 1 coin = zero rotation, stuck in single trades for days
- 75/25 split wastes capital in reserve that smaller accounts need for active grid depth

### What Needs to Change

#### 0A. New Equity Tier Table

```python
EQUITY_TIER_CAPS = [
    (100_000, 10),  # $100K+     -> 10 coins (full diversification)
    ( 20_000,  5),  # $20K-$100K ->  5 coins (proven on paper)
    ( 10_000,  5),  # $10K-$20K  ->  5 coins (intermediate split)
    (  5_000,  5),  # $5K-$10K   ->  5 coins (aggressive turnover)
    (  3_000,  4),  # $3K-$5K    ->  4 coins (demo phase: turnover + depth)
    (    100,  3),  # $100-$3K   ->  3 coins (max turnover at small capital)
]
```

**Rationale for aggressive coin counts at small capital:**
- Paper data shows top 3 coins produce 51% of all trades (7 deals/day)
- 3 coins provides rotation even when 1-2 are stuck in deeper DCA
- At $3K, per-coin capital is $750-$850 — enough for 10-11 layers (covers 100% of historical outcomes)
- At $1K, per-coin capital is $300 — still gets 9 layers (covers 99.1% of outcomes)

#### 0B. Adaptive Pool Split by Tier

Replace the fixed 75/25 with a tier-aware split:

```python
# Equity-tiered pool splits
# Format: (min_equity_inclusive, active_pct, reserve_pct)
EQUITY_TIER_SPLITS = [
    (20_000, 0.75, 0.25),  # $20K+    -> 75/25 (proven, deep safety buffer)
    (10_000, 0.80, 0.20),  # $10K-$20K -> 80/20 (intermediate — avoids cliff)
    (   100, 0.90, 0.10),  # <$10K    -> 90/10 (max grid depth, bounded risk)
]
```

**Why this works — simplified to 3 split tiers:**

| Capital | Coins | Split | Per-Coin | Viable Layers | Smallest Layer | Reserve |
|---------|-------|-------|----------|---------------|---------------|---------|
| $1,000 | 3 | 90/10 | $300 | 9/12 | $5.19 | $100 |
| $3,000 | 4 | 90/10 | $675 | 11/12 | $5.72 | $300 |
| $5,000 | 5 | 90/10 | $900 | 12/12 | $5.34 | $500 |
| $10,000 | 5 | 80/20 | $1,600 | 12/12 | $9.49 | $2,000 |
| $20,000 | 5 | 75/25 | $3,000 | 12/12 | $17.80 | $5,000 |
| $50,000 | 5 | 75/25 | $7,500 | 12/12 | $44.49 | $12,500 |
| $100,000 | 10 | 75/25 | $7,500 | 12/12 | $44.49 | $25,000 |

**Reserve rationale at small accounts:**
- Reserve serves layers 6+ (code: `pool = "reserve" if layer >= 6 else "active"`)
- 90/10 below $10K is safe — bounded total exposure, demo phase capital
- 80/20 at $10K–$20K provides a smooth transition (avoids a $1,500 active-capital cliff at $10K)
- 75/25 kicks in at $20K where the reserve buffer genuinely matters
- Paper data: only 3 trades ever went to 5-6 layers across 220 trades

#### 0C. Code Changes — `v14_capital_manager.py`

```python
# New: Equity-tiered pool splits
EQUITY_TIER_SPLITS = [
    (20_000, 0.75, 0.25),  # $20K+    -> 75/25 (proven, deep safety buffer)
    (10_000, 0.80, 0.20),  # $10K-$20K -> 80/20 (intermediate — avoids cliff)
    (   100, 0.90, 0.10),  # <$10K    -> 90/10 (max grid depth, bounded risk)
]

# Hysteresis band — prevents tier flapping from normal PnL fluctuation.
# Upgrade: at the threshold (no buffer).
# Downgrade: only when equity drops TIER_HYSTERESIS_PCT below the threshold.
TIER_HYSTERESIS_PCT = 0.05  # 5%

@staticmethod
def get_tier_split(equity: float) -> tuple:
    """Return (active_pct, reserve_pct) for the given equity level."""
    for threshold, active, reserve in EQUITY_TIER_SPLITS:
        if equity >= threshold:
            return (active, reserve)
    return (0.90, 0.10)  # Default for tiny accounts

@staticmethod
def _apply_hysteresis(equity: float, current_tier_index: int,
                      tier_table: list, key_fn) -> int:
    """
    Determine the effective tier index with hysteresis.

    - Upgrade (moving to a higher tier): triggers at the threshold — no buffer.
    - Downgrade (moving to a lower tier): only triggers when equity drops
      TIER_HYSTERESIS_PCT (5%) below the current tier's threshold.

    Parameters:
        equity:             Current portfolio equity.
        current_tier_index: Index into tier_table of the tier we're currently on.
                            -1 or None on first call (no prior tier).
        tier_table:         The tier lookup table (EQUITY_TIER_CAPS or EQUITY_TIER_SPLITS).
        key_fn:             Callable that extracts the threshold from a tier entry.
                            e.g., lambda row: row[0]

    Returns:
        New tier index into tier_table.
    """
    # Raw lookup — what tier would equity land on without hysteresis?
    raw_index = len(tier_table) - 1  # default: lowest tier
    for i, row in enumerate(tier_table):
        if equity >= key_fn(row):
            raw_index = i
            break

    # First call or no prior tier — no hysteresis, use raw
    if current_tier_index is None or current_tier_index < 0:
        return raw_index

    # Upgrade (raw is a higher tier = lower index): apply immediately
    if raw_index < current_tier_index:
        return raw_index

    # Same tier: no change
    if raw_index == current_tier_index:
        return current_tier_index

    # Downgrade (raw is a lower tier = higher index): apply hysteresis
    # Stay at current tier unless equity dropped 5% below current tier's threshold
    current_threshold = key_fn(tier_table[current_tier_index])
    downgrade_trigger = current_threshold * (1.0 - TIER_HYSTERESIS_PCT)
    if equity < downgrade_trigger:
        return raw_index  # Confirmed downgrade
    else:
        return current_tier_index  # Hold current tier (within buffer)
```

Update `__init__()`:
```python
def __init__(self, initial_capital: float):
    self.total_equity = initial_capital
    
    # Tier state — track indices for hysteresis
    self._cap_tier_index: int = self._apply_hysteresis(
        self.total_equity, -1, EQUITY_TIER_CAPS, lambda r: r[0])
    self._split_tier_index: int = self._apply_hysteresis(
        self.total_equity, -1, EQUITY_TIER_SPLITS, lambda r: r[0])
    
    # Tier-aware coin cap
    self.tier_coin_cap = EQUITY_TIER_CAPS[self._cap_tier_index][1]
    
    # Tier-aware pool split
    _, active_pct, reserve_pct = EQUITY_TIER_SPLITS[self._split_tier_index]
    self.active_pool_total = self.total_equity * active_pct
    self.reserve_pool_total = self.total_equity * reserve_pct
    
    # ... rest unchanged
    logger.info(f"Pool split: {active_pct*100:.0f}/{reserve_pct*100:.0f} "
                f"(Active: ${self.active_pool_total:.2f} / Reserve: ${self.reserve_pool_total:.2f})")
    logger.info(f"Tier coin cap: {self.tier_coin_cap} coins "
                f"(hysteresis active, 5% downgrade buffer)")
```

Update `rebalance()` (the equity-refresh section):
```python
# Update equity and derive tier cap + split (with hysteresis)
self.total_equity = current_equity if current_equity else self.total_equity

# Coin cap — hysteresis-aware
prev_cap_index = self._cap_tier_index
self._cap_tier_index = self._apply_hysteresis(
    self.total_equity, self._cap_tier_index, EQUITY_TIER_CAPS, lambda r: r[0])
prev_cap = self.tier_coin_cap
self.tier_coin_cap = EQUITY_TIER_CAPS[self._cap_tier_index][1]
if self.tier_coin_cap != prev_cap:
    direction = "▼ DOWN" if self.tier_coin_cap < prev_cap else "▲ UP"
    logger.warning(f"Tier coin cap changed {direction}: {prev_cap} → {self.tier_coin_cap} "
                   f"(equity=${self.total_equity:.2f})")

# Pool split — hysteresis-aware
prev_split_index = self._split_tier_index
self._split_tier_index = self._apply_hysteresis(
    self.total_equity, self._split_tier_index, EQUITY_TIER_SPLITS, lambda r: r[0])
_, active_pct, reserve_pct = EQUITY_TIER_SPLITS[self._split_tier_index]
self.active_pool_total = self.total_equity * active_pct
self.reserve_pool_total = self.total_equity * reserve_pct

if self._split_tier_index != prev_split_index:
    logger.warning(f"Pool split changed: → {active_pct*100:.0f}/{reserve_pct*100:.0f} "
                   f"(equity=${self.total_equity:.2f})")
```

**Hysteresis behavior summary:**

**Coin cap tiers:**

| Threshold | Coins | Upgrade at | Downgrade at (5% below) |
|-----------|-------|-----------|------------------------|
| $100K | 10 | $100,000 | $95,000 |
| $20K | 5 | $20,000 | $19,000 |
| $10K | 5 | $10,000 | $9,500 |
| $5K | 5 | $5,000 | $4,750 |
| $3K | 4 | $3,000 | $2,850 |
| $100 | 3 | $100 | $95 |

**Pool split tiers:**

| Threshold | Split | Upgrade at | Downgrade at (5% below) |
|-----------|-------|-----------|------------------------|
| $20K | 75/25 | $20,000 | $19,000 |
| $10K | 80/20 | $10,000 | $9,500 |
| $100 | 90/10 | $100 | $95 |

Example: equity at $3,000 → 4 coins / 90-10 split. Equity dips to $2,860 — **stays at 4 coins** (within 5% buffer, trigger is $2,850). Dips to $2,849 — downgrades to 3 coins. Must reach $3,000 again to re-upgrade. Split stays 90/10 throughout (split only changes at $10K/$20K).

**State persistence:** `_cap_tier_index` and `_split_tier_index` must be saved in `state.json` so hysteresis survives restarts. On load, if indices are present, pass them as `current_tier_index`; otherwise use `-1` (first-call behavior).

#### 0D. Code Changes — `run_v14_portfolio_live_aster.py`

No structural changes needed. The runner already reads `tier_coin_cap` from the router and uses it for coin selection. The pool split is consumed transparently.

The only change: update `status.json` to include the active split ratio:
```python
"pool_split": f"{active_pct*100:.0f}/{reserve_pct*100:.0f}",
```

#### 0E. Integration with Upgrade 1 (Dynamic Capital)

When Upgrade 1's `resize()` is implemented, it must also re-derive tiers with hysteresis:
```python
def resize(self, new_equity: float):
    """Dynamically resize pools after deposit/withdrawal."""
    self.total_equity = new_equity
    # Hysteresis-aware tier updates
    self._cap_tier_index = self._apply_hysteresis(
        new_equity, self._cap_tier_index, EQUITY_TIER_CAPS, lambda r: r[0])
    self.tier_coin_cap = EQUITY_TIER_CAPS[self._cap_tier_index][1]
    self._split_tier_index = self._apply_hysteresis(
        new_equity, self._split_tier_index, EQUITY_TIER_SPLITS, lambda r: r[0])
    _, active_pct, reserve_pct = EQUITY_TIER_SPLITS[self._split_tier_index]
    self.active_pool_total = new_equity * active_pct
    self.reserve_pool_total = new_equity * reserve_pct
    # Recalculate cash = pool total - allocated
    allocated_active = sum(self.active_allocations.values())
    self.active_pool_cash = self.active_pool_total - allocated_active
    self.reserve_pool_cash = self.reserve_pool_total
    logger.info(f"Resized: ${new_equity:.2f} | {active_pct*100:.0f}/{reserve_pct*100:.0f} split | "
                f"max {self.tier_coin_cap} coins")
```

This means a deposit that crosses a tier boundary (e.g., $2.5K → $3.5K) automatically adds a 4th coin slot (3→4 coins, split stays 90/10). At $5K a 5th coin opens. The split only changes at $10K (80/20) and $20K (75/25). Hysteresis applies: a small withdrawal that dips just below $3K won't immediately downgrade — equity must fall 5% below the threshold ($2,850) to trigger.

#### 0F. Dashboard Impact

- Show current tier info: `"4 coins | 90/10 split | $3K tier"`
- Pool allocation donut should reflect actual split (not hardcoded 75/25)
- Minor: update any hardcoded "75% / 25%" labels

### Layer Sizing Proof — $3K / 4 Coins / 90-10

```
Per-coin capital: $675 (from $2,700 active pool / 4 coins)
Reserve: $300

Layer  1: $270 (BO: 40% of $675)        ← covers 63.2% of trades
Layer  2: $189                            ← covers 85.5%
Layer  3: $132                            ← covers 94.5%
Layer  4:  $93                            ← covers 99.1%
Layer  5:  $65
Layer  6:  $45  ← switches to reserve pool
Layer  7:  $32
Layer  8:  $22
Layer  9:  $15
Layer 10:  $11
Layer 11:   $7  ← smallest viable ($5.72 > $5 min)
           ----
Total:    $881 (capped to $675 allocated from active pool + reserve for layers 6+)
```

**11 layers viable.** Covers 100% of all historical completed trades (max was 6 layers). $300 reserve covers deep layers across 1-2 simultaneous coins.

### Files Modified
- `v14_capital_manager.py` — new `EQUITY_TIER_SPLITS`, `TIER_HYSTERESIS_PCT`, `get_tier_split()`, `_apply_hysteresis()`, updated `__init__()` and `rebalance()`
- `v14_capital_manager.py` — updated `EQUITY_TIER_CAPS` table
- `run_v14_portfolio_live_aster.py` — add `pool_split` to status.json output; persist `_cap_tier_index` / `_split_tier_index` in state.json
- `d-984ae0d4ab9dc1a5.html` — update pool split display (minor)

### Complexity: Low
- Two new lookup tables, two static methods, one constant
- Pool split calculation already exists, just parameterized instead of hardcoded
- Hysteresis adds two integer indices to state — no new data flows or external dependencies
- Fully backward compatible (paper bot at $50K+ hits the same 75/25 / 5-coin tier)

### Test Plan: Upgrade 0 (Adaptive Tiers & Pool Split)

| # | Test | Steps | Expected Result |
|---|------|-------|-----------------|
| T0.1 | Tier lookup at $340 | Start bot with `--capital 340` | Tier: 3 coins, 90/10 split. Active: $306, Reserve: $34 |
| T0.2 | Tier lookup at $1,000 | Start bot with `--capital 1000` | Tier: 3 coins, 90/10 split. Active: $900, Reserve: $100 |
| T0.3 | Tier lookup at $3,000 | Start bot with `--capital 3000` | Tier: 4 coins, 90/10 split. Active: $2,700, Reserve: $300 |
| T0.4 | Tier lookup at $5,000 | Start bot with `--capital 5000` | Tier: 5 coins, 90/10 split. Active: $4,500, Reserve: $500 |
| T0.5 | Tier lookup at $10,000 | Start bot with `--capital 10000` | Tier: 5 coins, 80/20 split. Active: $8,000, Reserve: $2,000 |
| T0.6 | Tier lookup at $20,000 | Start bot with `--capital 20000` | Tier: 5 coins, 75/25 split. Active: $15,000, Reserve: $5,000 |
| T0.7 | Tier lookup at $50,000 | Start bot with `--capital 50000` | Tier: 5 coins, 75/25 split (paper bot reference) |
| T0.8 | Tier lookup at $100,000 | Start bot with `--capital 100000` | Tier: 10 coins, 75/25 split |
| T0.9 | Layer viability at $3K/4 coins | Check that smallest layer > $5 | 11 viable layers, smallest ~$5.72 (above $5 min) |
| T0.10 | Layer viability at $1K/3 coins | Check layer sizing | 9 viable layers, smallest ~$5.19 |
| T0.11 | Upgrade at coin cap boundary | Equity grows from $2.9K to $3.0K | Coin cap upgrades immediately: 3→4 coins. Split stays 90/10. Logged. |
| T0.12 | Upgrade at split boundary | Equity grows from $9.9K to $10.0K | Split upgrades: 90/10→80/20. Coins stay 5. Logged. |
| T0.13 | Paper bot unchanged | Run paper bot at $50K | Same behavior: 5 coins, 75/25, 12 layers |
| T0.14 | Status.json accuracy | Start at $3K, check status.json | `tier_coin_cap: 4`, `pool_split: "90/10"` |
| T0.15 | Reserve pool routing | At $3K, coin hits layer 6+ | Layer 6+ capital drawn from reserve ($300 pool) |
| T0.16 | Hysteresis — no downgrade in buffer | Start at $3K (4 coins). Equity dips to $2,860. | **Stays at 4 coins / 90/10.** Within 5% buffer ($2,850 trigger). No tier change logged. |
| T0.17 | Hysteresis — downgrade below buffer | Start at $3K (4 coins). Equity drops to $2,849. | Downgrades to 3 coins. Split stays 90/10 (both tiers same split). Logged. |
| T0.18 | Hysteresis — re-upgrade after downgrade | After T0.17 (now 3 coins at $2,849). Equity rises to $3,000. | Upgrades back to 4 coins immediately. No buffer on upgrade. |
| T0.19 | Hysteresis — split downgrade buffer | Start at $10K (80/20). Equity dips to $9,600. | **Stays at 80/20.** Trigger is $9,500 (5% below $10K). |
| T0.20 | Hysteresis — split confirmed downgrade | Start at $10K (80/20). Equity drops to $9,499. | Downgrades to 90/10. Coin cap also drops: 5→5 (same at both tiers). |
| T0.21 | Hysteresis — state persistence | Start at $3K (4 coins). Equity dips to $2,860 (in buffer). Restart bot. | Tier indices restored from state.json. Still 4 coins after restart — no fresh re-evaluation. |

---

## Upgrade 1: Dynamic Capital Management (Deposits & Withdrawals)

### What Exists Today

**Old live bot (`run_v14_live_aster.py`) — FULLY BUILT:**
- Capital Ledger (`capital_ledger.json`) — tracks seed, deposits, withdrawals with timestamps
- Auto-detection in `_maybe_reconcile()`: when drift > 10% AND no open position → auto-records deposit/withdrawal, adjusts engine capital, sends Telegram alert
- CLI flags: `--deposit AMOUNT` and `--withdraw AMOUNT` for manual recording
- `--ledger` flag to print ledger summary
- Capital loaded from ledger on startup (not just CLI arg)

**PM live bot (`run_v14_portfolio_live_aster.py`) — NOT IMPLEMENTED:**
- Capital is CLI arg only (`--capital 340`)
- `_sync_positions_from_exchange()` runs every 65s cycle, caching `_exchange_usdt_free` and `_exchange_usdt_total` — but drift is treated as a generic pool adjustment with no deposit/withdrawal distinction
- No capital ledger
- No way to add/remove capital without restarting the bot
- Listed as P2 items #18, #19, #20 in the unified audit

_Note: `_reconcile_with_exchange()` and `_periodic_reconcile()` were removed in the 2026-03-21 exchange-as-truth refactor. Exchange is now the single source of truth via `_sync_positions_from_exchange()`._

### What Needs to Change

#### 1A. Port Capital Ledger from Old Bot
- Copy `load_capital_ledger()`, `save_capital_ledger()`, `record_ledger_transaction()`, `print_ledger_summary()` into PM bot (or extract to shared module)
- Ledger file: `trading/spot/live/v14pm/capital_ledger.json`
- CLI flags: `--deposit`, `--withdraw`, `--ledger`
- On startup: if ledger exists, load `current_capital` from it instead of `--capital` arg (first run seeds the ledger)

#### 1B. Auto-Detect Deposits/Withdrawals via Exchange Sync
- Hook into the existing `_sync_positions_from_exchange()` (already runs every 65s cycle):
  - Compare `_exchange_usdt_total` to `self.capital` + invested amount to detect drift
  - No need for a separate reconciliation pass — the exchange sync already runs every cycle
  - When drift > threshold (e.g. $5 or 2%, whichever is larger):
    - **No open positions across all coins**: Classify as deposit (positive) or withdrawal (negative)
    - **Open positions exist**: Flag as suspicious drift, alert but don't auto-classify
  - On deposit detection:
    - Record to capital ledger
    - Update `self.capital` (the bot's tracking variable)
    - Update `self.router.total_equity` and recalculate pool splits (via `get_tier_split()`)
    - Trigger immediate rebalance so new capital is allocated
    - Telegram alert: "📥 Deposit detected: $X. Capital: $old → $new. Rebalancing."
  - On withdrawal detection:
    - Record to capital ledger
    - Reduce `self.capital`
    - Update router pools
    - Telegram alert: "📤 Withdrawal detected: $X. Capital: $old → $new."
    - Safety: if withdrawal would make capital < total invested, alert but DON'T auto-adjust (requires CLOSE commands first)

#### 1C. Telegram Commands for Capital
- `DEPOSIT <amount>` — Manually record a deposit (doesn't move funds — just tells the bot)
- `WITHDRAW <amount>` — Manually record a withdrawal
- `CAPITAL` — Show current capital breakdown (ledger balance, exchange balance, invested, free)

#### 1D. Router Integration
The `CapitalRouter` needs a `resize(new_equity)` method. **Depends on Upgrade 0** — must use `get_tier_split()` and `_apply_hysteresis()` for adaptive pool ratios with downgrade buffering:
```python
def resize(self, new_equity: float):
    """Dynamically resize pools after deposit/withdrawal. Hysteresis-aware."""
    self.total_equity = new_equity
    # Hysteresis-aware tier updates (same as rebalance)
    self._cap_tier_index = self._apply_hysteresis(
        new_equity, self._cap_tier_index, EQUITY_TIER_CAPS, lambda r: r[0])
    self.tier_coin_cap = EQUITY_TIER_CAPS[self._cap_tier_index][1]
    self._split_tier_index = self._apply_hysteresis(
        new_equity, self._split_tier_index, EQUITY_TIER_SPLITS, lambda r: r[0])
    _, active_pct, reserve_pct = EQUITY_TIER_SPLITS[self._split_tier_index]
    self.active_pool_total = new_equity * active_pct
    self.reserve_pool_total = new_equity * reserve_pct
    # Recalculate cash = pool total - allocated
    allocated_active = sum(self.active_allocations.values())
    self.active_pool_cash = self.active_pool_total - allocated_active
    self.reserve_pool_cash = self.reserve_pool_total
    logger.info(f"Resized: ${new_equity:.2f} | {active_pct*100:.0f}/{reserve_pct*100:.0f} split | "
                f"max {self.tier_coin_cap} coins")
```

#### 1E. Dashboard Impact
- Add `capital_ledger` section to `status.json` (seed, current, last_tx)
- Dashboard can show capital history if desired (low priority)

### Files Modified
- `run_v14_portfolio_live_aster.py` — ledger integration, recon changes, Telegram commands
- `v14_capital_manager.py` — add `resize()` method
- `d-984ae0d4ab9dc1a5.html` — optional: capital section

### Complexity: Medium
- Most logic is already proven in the old bot
- Main new work: Router resize + rebalance trigger on capital change

---

## Upgrade 2: Per-Coin Pause

> **✅ DEPLOYED 2026-03-24** — Live on V14PM Live (Aster Perps).

### What Exists Today

**Global PAUSE** (`PAUSE` / `RESUME` commands):
- Sets `self.bot_state = BotState.PAUSED`
- Blocks ALL new entries and DCA layers across ALL coins
- Existing TP orders remain active natively (exchange-as-truth architecture — no LIVE GUARD needed)
- Implemented and working

**Per-coin:** Nothing. No way to pause individual coins.

### What Needs to Change

#### 2A. Per-Coin Pause State
- Add `paused: bool` field to `CoinState` (the per-coin tracking object):
  ```python
  class CoinState:
      # ... existing fields ...
      paused: bool = False
  ```
- Persist in state.json (per-coin section)

#### 2B. Behavior When a Coin is Paused
- **Blocked:** New DCA layer buys, new entries (coin won't be selected in rebalance)
- **Allowed:** TP fills (existing exchange limit orders stay active), TP recovery on restart
- **Allowed:** Periodic reconciliation (position sync continues)
- **Allowed:** Status reporting (coin still appears on dashboard with "PAUSED" badge)
- **Removed from opportunity list:** Paused coins excluded from `CapitalRouter.rebalance()` candidate list. Their allocated capital stays locked (not redistributed) until unpaused or position closes.

#### 2C. Telegram Commands
- `PAUSE <COIN>` — Pause a specific coin (e.g., `PAUSE GRASS`)
- `RESUME <COIN>` — Resume a specific coin
- `PAUSE` (no args) — Global pause (existing behavior)
- `RESUME` (no args) — Global resume (existing behavior)
- Confirmation messages with current state

#### 2D. Code Changes
In `_process_candle()` (where buy decisions happen):
```python
if cs.paused:
    logger.info(f"BUY blocked for {sym} — coin is paused")
    return
```

In `_daily_rebalance()` (where coin selection happens):
```python
# Exclude paused coins from candidate list
candidates = [c for c in qualifying_coins if not self.coins.get(c['symbol'], CoinState()).paused]
```

In `_handle_command()`:
```python
elif text.startswith("PAUSE ") and len(text.split()) == 2:
    coin = text.split()[1]
    # ... find matching symbol, set cs.paused = True
elif text.startswith("RESUME ") and len(text.split()) == 2:
    coin = text.split()[1]
    # ... find matching symbol, set cs.paused = False
```

#### 2E. Dashboard Impact
- Add `paused` field to per-coin status data
- Dashboard shows "⏸️ PAUSED" badge on paused coins
- Paused coins greyed out in opportunity table

### Files Modified
- `run_v14_portfolio_live_aster.py` — CoinState, command handler, candle processing, rebalance
- `d-984ae0d4ab9dc1a5.html` — paused badge styling

### Complexity: Low-Medium
- Straightforward boolean flag with clear gate points
- No new data flows or external dependencies

### Deployment Notes (2026-03-24)

**Implementation matches spec exactly.** Key decisions confirmed:
- **Q3 (Paused capital): A** — Capital held in reserve, not redistributed
- **Q4 (Global RESUME): A** — Per-coin pauses survive global RESUME

**Actual code changes:**
- `CoinState.paused` field added, persisted to `state.json`
- Buy gate in `_execute_action()` checks `cs.paused` before allowing BUY orders; calls `cs.engine.reject_action()` to keep engine state consistent
- Rebalance exclusion: paused coins filtered from scanner data before `rebalance_daily()`
- `PAUSE <COIN>` / `RESUME <COIN>` Telegram commands with confirmation messages
- Dashboard: position card shows "⏸ PAUSED" amber badge; opportunity table dims paused rows (50% opacity) and sorts them to bottom

---

## Upgrade 3: Per-Coin Regime Flagging

> **✅ DEPLOYED 2026-03-24** — Live on V14PM Live (Aster Perps).

### What Exists Today

**Global regime monitor** (`_evaluate_regime()`):
- Runs once daily at midnight UTC
- Reads scanner JSON for per-coin phase/signal data
- Counts coins with TOP or BOTTOM signals
- Tiered alerts: 🟡 EARLY (5+ coins / 10%), 🟠 STRONG (12+ / 25%), 🔴 MAJORITY (25+ / 50%)
- Sends APPROVE/DENY prompt to Telegram
- APPROVE → WIND_DOWN state (freeze grids, keep TPs)
- DENY → continue current strategy

**Per-coin signals** (V14 DCA Engine):
- Each coin's inner engine tracks `top_detected` (bool) and `conviction_fired` (bool)
- `_check_top_signals()` fires on RSI overbought + confirmation patterns
- `_check_bottom_signals()` fires on bullish structure confirmation
- These signals trigger phase changes (LONG_DCA ↔ SHORT_DCA) within the engine

**Current gap:**
- The engine's per-coin top/bottom signals run independently but the PM bot operates in **global direction mode** (all coins Long or all Short)
- When a single coin's signal stack fires a regime change, nothing happens — the engine tries to flip but the PM bot's global direction overrides it
- No alerting, no flagging, no removal from the opportunity list

### What Needs to Change

#### 3A. Per-Coin Regime Flag
Add to `CoinState`:
```python
class CoinState:
    # ... existing fields ...
    regime_flagged: bool = False          # True when coin's signals conflict with global direction
    coin_regime_signal: Optional[str] = None  # "TOP" or "BOTTOM" — what the coin's stack detected
    flagged_at: Optional[str] = None      # ISO timestamp when flagged
```

#### 3B. Detection Logic
After each candle is processed for a coin, check if the engine's signal stack triggered a direction change that conflicts with the global direction:

```python
def _check_coin_regime_conflict(self, sym: str, cs: CoinState):
    """Check if a coin's signal stack conflicts with global direction."""
    if not cs.engine or not cs.engine._engine:
        return
    eng = cs.engine._engine

    # Global direction: currently always LONG (until regime flip)
    global_direction = "LONG"  # Will be configurable after full regime flip is implemented

    # Check if the engine detected a top (wants to go SHORT) while global is LONG
    if global_direction == "LONG" and eng.top_detected and not cs.regime_flagged:
        cs.regime_flagged = True
        cs.coin_regime_signal = "TOP"
        cs.flagged_at = datetime.now(timezone.utc).isoformat()
        logger.warning(f"REGIME FLAG: {sym} — top detected, conflicts with global LONG direction")
        send_telegram(
            f"🚩 {TG_PREFIX} <b>Coin Regime Conflict: {sym.split('/')[0]}</b>\n"
            f"Signal stack: TOP DETECTED (wants Short)\n"
            f"Global direction: LONG\n\n"
            f"Coin removed from active trading.\n"
            f"Open positions can still hit TPs.\n"
            f"Will auto-resume when global regime matches."
        )

    # Similarly for SHORT direction with bottom detection
    elif global_direction == "SHORT" and eng.conviction_fired and not cs.regime_flagged:
        cs.regime_flagged = True
        cs.coin_regime_signal = "BOTTOM"
        cs.flagged_at = datetime.now(timezone.utc).isoformat()
        # ... similar alert
```

#### 3C. Behavior When Flagged
- **Removed from opportunity list:** Flagged coins excluded from rebalance candidates (same as paused)
- **No new orders:** Buy blocked, no new layers
- **TPs active:** Existing positions can gracefully close
- **Still scanned:** Coin continues in scanner, signal stack continues to evaluate
- **Counts toward global regime threshold:** Flagged coins contribute to the aggregate signal count in `_evaluate_regime()`
- **Auto-unflag:** When global regime changes to match the coin's signal (e.g., global flips to SHORT and coin was flagged TOP), the coin is automatically unflagged and returned to the opportunity list

#### 3D. Integration with Global Regime Monitor
Update `_evaluate_regime()` to:
1. Count `regime_flagged` coins as part of the signal aggregate
2. Include flagged coins in the tier alert message
3. After global regime flip (APPROVE → direction change), auto-clear all matching flags

#### 3E. Telegram Alert Format
When a coin gets flagged:
```
🚩 V14PM | Coin Regime Conflict: GRASS
Signal stack: TOP DETECTED (wants Short)
Global direction: LONG
Flagged coins: 3/50 (GRASS, SOL, ETH)

Coin removed from active trading.
Open positions can still hit TPs.
```

When flagged count reaches a tier threshold, the existing regime alert fires with the flagged coins listed prominently.

#### 3F. Auto-Resume After Global Flip
```python
def _clear_matching_regime_flags(self, new_direction: str):
    """After global regime change, unflag coins that now match."""
    for sym, cs in self.coins.items():
        if cs.regime_flagged:
            # TOP flag + new direction SHORT = match → unflag
            # BOTTOM flag + new direction LONG = match → unflag
            if (cs.coin_regime_signal == "TOP" and new_direction == "SHORT") or \
               (cs.coin_regime_signal == "BOTTOM" and new_direction == "LONG"):
                cs.regime_flagged = False
                cs.coin_regime_signal = None
                logger.info(f"REGIME UNFLAG: {sym} — matches new global direction {new_direction}")
```

#### 3G. Dashboard Impact
- Flagged coins show 🚩 badge with "REGIME CONFLICT" label
- Opportunity table: flagged coins show signal direction vs global direction
- Position card: flagged coin shows warning about no new orders

### Files Modified
- `run_v14_portfolio_live_aster.py` — CoinState, detection logic, rebalance exclusion, regime integration, Telegram alerts
- `v14_lifecycle_engine.py` — expose `top_detected` / `conviction_fired` (already exposed)
- `d-984ae0d4ab9dc1a5.html` — flagged coin badges, opportunity table column

### Complexity: Medium-High
- Per-coin signal detection needs careful integration with the global regime model
- Auto-unflag logic after global flip needs to be robust
- Edge cases: coin flagged → TP fills → reflagged on re-entry? (Answer: yes, if signal persists)

### Dependencies
- The scanner JSON currently does NOT include per-coin `lifecycle_phase` or `router_signal` fields — the regime evaluation reads these but they're empty
- The per-coin engine's `top_detected` and `conviction_fired` flags ARE available in the V14 DCA engine
- **The detection should come from the live engine's signal stack** (processing real candles), not from the scanner (which is a backtest summary)

### Deployment Notes (2026-03-24)

**Implementation matches spec with Q5/Q6 decisions confirmed:**
- **Q5 (Flag persistence after TP fill): A** — Auto-clear flag when TP fills and no position remains. Nothing to protect = flag cleared. Coin returns to opportunity list.
- **Q6 (Manual RESUME cooldown): A** — 24-hour cooldown after manual RESUME before re-flagging. Respects operator intent.

**Actual code changes:**

**CoinState fields added:**
```python
regime_flagged: bool = False              # True when coin signals conflict with global direction
coin_regime_signal: Optional[str] = None  # "TOP" or "BOTTOM"
flagged_at: Optional[str] = None          # ISO timestamp when flagged
regime_cooldown_until: float = 0.0        # Unix timestamp — no re-flag before this
```

**Detection (`_check_coin_regime_conflict`):**
- Runs after each candle tick for every active coin
- Checks engine's `top_detected` (LONG global → wants SHORT) and `conviction_fired` (SHORT global → wants LONG)
- Skips already-flagged, paused, and cooldown-active coins
- On flag: sets fields, sends 🚩 Telegram alert with flagged coin count, saves state

**Buy gate (in `_execute_action`):**
```python
if cs.regime_flagged:
    logger.info(f"BUY blocked for {sym} — regime conflict ({cs.coin_regime_signal})")
    cs.engine.reject_action(action)
    return
```

**Auto-clear on TP fill (`_clear_regime_flag_on_tp`):**
- Called in `_handle_tp_fill()` after position closes
- Checks `eng.long_coins == 0 and eng.short_coins == 0`
- Clears flag, sends ✅ Telegram notification

**Auto-clear on global regime flip (`_clear_matching_regime_flags`):**
- TOP flag + new direction SHORT = match → unflag
- BOTTOM flag + new direction LONG = match → unflag
- Sends ✅ Telegram notification per cleared coin

**RESUME command updated:**
- `RESUME <COIN>` now clears both `paused` and `regime_flagged`
- If coin was regime-flagged, sets 24h cooldown (`regime_cooldown_until`)
- Telegram confirmation includes cooldown status

**Rebalance exclusion:** Updated to filter both paused AND regime-flagged coins from scanner data.

**Dashboard:**
- Position card: "🚩 REGIME CONFLICT" red badge (alongside existing PAUSED badge)
- Opportunity table: flagged coins show "🚩 FLAGGED" badge, dimmed rows (50% opacity, red tint), sorted to bottom
- Phase column shows engine's actual phase (e.g., "Short DCA" in red) reflecting the conflict

---

## Interaction Between Upgrades 2 & 3

Per-coin pause (manual) and regime flag (automatic) are separate mechanisms but behave similarly:

| Behavior | Paused (manual) | Regime Flagged (auto) |
|----------|:---------------:|:---------------------:|
| New orders blocked | ✅ | ✅ |
| TPs active | ✅ | ✅ |
| Excluded from rebalance | ✅ | ✅ |
| Cleared by | `RESUME <COIN>` | Global regime flip |
| Can be manually overridden | N/A | `RESUME <COIN>` clears flag |
| Counts toward regime signal | ❌ | ✅ |

Implementation: The buy-gate check becomes:
```python
if cs.paused or cs.regime_flagged:
    reason = "paused" if cs.paused else "regime conflict"
    logger.info(f"BUY blocked for {sym} — {reason}")
    return
```

---

## Test Plans

### Test Plan: Upgrade 1 (Dynamic Capital Management)

**Pre-requisite:** Bot running with $340 capital, 1 coin active (GRASS)

| # | Test | Steps | Expected Result |
|---|------|-------|-----------------|
| T1.1 | Manual deposit (no positions) | Close all positions → transfer $50 USDT to Futures → wait for next recon cycle (65s) | Bot detects +$50 drift, records deposit, capital adjusts $340→$390, rebalance triggers |
| T1.2 | Manual deposit (position open) | Transfer $50 USDT to Futures while GRASS position is open | Bot detects drift, alerts "deposit suspected but position open", records to ledger, adjusts pools |
| T1.3 | Manual withdrawal | Transfer $25 USDT from Futures to Spot | Bot detects -$25 drift, records withdrawal, capital $400→$375 |
| T1.4 | Telegram DEPOSIT command | Send `DEPOSIT 50` | Bot records manual deposit, adjusts capital, confirms via Telegram |
| T1.5 | Telegram WITHDRAW command | Send `WITHDRAW 25` | Bot records withdrawal, adjusts capital. Verify: if withdrawal > free cash, bot refuses |
| T1.6 | Telegram CAPITAL command | Send `CAPITAL` | Returns: seed, current, deposits total, withdrawals total, exchange balance |
| T1.7 | Router resize on deposit | Deposit $100 → check allocations | Active pool grows from $255→$330, reserve $85→$110, tier cap recalculated |
| T1.8 | Withdrawal safety | Attempt withdrawal larger than free cash | Bot refuses: "Cannot withdraw $X — only $Y free. Close positions first." |
| T1.9 | State persistence | Deposit $50 → restart bot | Capital ledger survives restart, bot starts with $400 capital |
| T1.10 | Dashboard accuracy | After deposit, check dashboard | Equity, capital, allocation donut all reflect new amounts |

### Test Plan: Upgrade 2 (Per-Coin Pause)

| # | Test | Steps | Expected Result |
|---|------|-------|-----------------|
| T2.1 | Pause single coin | Send `PAUSE GRASS` | Confirmation message. GRASS shows paused in status. |
| T2.2 | Verify buy blocked | Wait for candle tick while GRASS paused | Log shows "BUY blocked for GRASS/USDT — coin is paused". No new orders. |
| T2.3 | Verify TP still works | GRASS has TP order active on exchange | TP fills normally. PnL recorded. Capital returned. |
| T2.4 | Resume single coin | Send `RESUME GRASS` | Confirmation message. GRASS active again. Next candle can trigger buy. |
| T2.5 | Pause + Global pause | Pause GRASS → then PAUSE (global) → RESUME (global) | After global resume, GRASS should STILL be paused (per-coin overrides). |
| T2.6 | Rebalance exclusion | Pause GRASS → trigger rebalance | GRASS excluded from candidate list. Another coin may be selected if tier allows. |
| T2.7 | State persistence | Pause GRASS → restart bot | Paused state restored from state.json. GRASS still paused. |
| T2.8 | Dashboard display | Pause GRASS → check dashboard | GRASS card shows ⏸️ PAUSED badge. Greyed in opportunity table. |
| T2.9 | Unknown coin | Send `PAUSE INVALID` | Error: "Symbol 'INVALID' not found. Active: GRASS" |
| T2.10 | Multiple coins paused | At higher equity (2+ coins): Pause one, verify other trades normally | Only paused coin blocked. Other coins trade as usual. |

### Test Plan: Upgrade 3 (Per-Coin Regime Flagging)

| # | Test | Steps | Expected Result |
|---|------|-------|-----------------|
| T3.1 | Simulate top signal | Manually set `eng.top_detected = True` for GRASS engine | Coin flagged, Telegram alert sent, GRASS removed from opportunity list |
| T3.2 | Verify new orders blocked | After flag, wait for candle tick | Log: "BUY blocked for GRASS/USDT — regime conflict" |
| T3.3 | Verify TP still active | GRASS has TP on exchange, gets flagged | TP fills normally despite flag |
| T3.4 | Verify scanner continues | Flagged coin in next scanner run | Coin still scanned, score updated, regime signal still tracked |
| T3.5 | Aggregate counting | Flag 3 coins → check regime eval | 3 flagged coins counted in global signal. If reaches EARLY tier (5+), alert fires. |
| T3.6 | Auto-unflag after global flip | APPROVE global regime change → direction changes | All coins flagged with matching signal are auto-unflaged and returned to opportunity list |
| T3.7 | Manual override | Flag fires → send `RESUME GRASS` | Flag cleared manually. Coin back in opportunity list. (Note: may re-flag on next candle if signal persists) |
| T3.8 | Persistence | Flag GRASS → restart bot | Flag state restored from state.json |
| T3.9 | Dashboard display | Flag GRASS | GRASS shows 🚩 REGIME CONFLICT badge with signal direction |
| T3.10 | Flag + Pause interaction | Flag fires → manually PAUSE same coin → RESUME | Resume clears pause but flag persists (they're independent). Coin still blocked by flag. |

---

## Implementation Order

**All upgrades deployed in sequence on 2026-03-24:**

1. ✅ **Upgrade 0 (Adaptive Tiers & Pool Split)** — Deployed. 26/26 tests pass (`test_tier_upgrade0.py`).
2. ✅ **Upgrade 1 (Dynamic Capital)** — Deployed. 19/19 tests pass (`test_upgrade1_capital.py`).
3. ✅ **Upgrade 2 (Per-Coin Pause)** — Deployed. Tested manually via Telegram commands.
4. ✅ **Upgrade 3 (Per-Coin Regime Flagging)** — Deployed. All 45 pre-existing tests pass (no regressions).

**Actual effort (single session):**
- Upgrade 0: ~1 hour
- Upgrade 1: ~2 hours
- Upgrade 2: ~1.5 hours
- Upgrade 3: ~1.5 hours (leveraged Upgrade 2 pattern heavily)

**Critical path for capital deployment:**
```
Upgrade 0 (tiers) → Upgrade 1 (deposits) → Deposit $1K → Bot runs 3 coins / 90-10
                                           → Deposit $2K → 3 coins / 90-10 (more depth per coin)
                                           → Grow to $3K+ → Auto-adjusts to 4 coins / 90-10
                                           → Grow to $5K+ → Auto-adjusts to 5 coins / 90-10
                                           → Grow to $10K+ → 5 coins / 80-20 (intermediate)
                                           → Grow to $20K+ → 5 coins / 75-25 (paper parity)
```

---

## Open Questions — ALL RESOLVED ✅

0. ~~**Tier boundary hysteresis:**~~ **RESOLVED — implemented in Upgrade 0C.** 5% asymmetric hysteresis band. Upgrade at threshold (immediate). Downgrade only when equity drops 5% below the current tier's threshold. Applies to both coin cap and pool split via `_apply_hysteresis()`. Tier indices persisted in state.json for restart survival. See sections 0C (code spec), test cases T0.13–T0.18.

1. ~~**Deposit threshold:**~~ **RESOLVED — implemented in Upgrade 1 (Dynamic Capital).** Uses `max($5, 2% of tracked capital)` as recommended. `CAPITAL_DRIFT_MIN_PCT = 0.02`. Auto-detection runs every sync cycle via `_detect_capital_changes()`, comparing exchange balance to `_tracked_capital`.

2. ~~**Withdrawal with open positions:**~~ **RESOLVED — implemented in Upgrade 1 (Dynamic Capital).** Partial withdrawals allowed from free balance. Safety guard: `if (tracked_capital - amount) < total_invested → reject`. Exchange margin protection is a second layer (`usdt_free` vs `usdt_used`). Both Telegram `WITHDRAW` command and auto-detection enforce this.

3. ~~**Per-coin pause capital:**~~ **RESOLVED — implemented in Upgrade 2 (Per-Coin Pause).** Paused/flagged coins are excluded from rebalance candidates — their capital stays with their existing allocation (held, not redistributed). On unpause, the coin resumes trading with its allocation intact at next rebalance cycle.

4. ~~**Regime flag persistence:**~~ **RESOLVED — Q5: A.** Auto-clear flag when TP fills and no position remains. Implemented in `_clear_regime_flag_on_tp()`.

5. ~~**Manual RESUME overriding regime flag:**~~ **RESOLVED — Q6: A.** 24h cooldown after manual RESUME before re-flagging. Implemented via `regime_cooldown_until` field (Unix timestamp).
