# V14PM Live Bot — Upgrade Scope

> **Updated 2026-03-23** — Added Upgrade 0 (Adaptive Tiers & Pool Split). Reordered implementation sequence. Exchange-as-truth architecture is live since 2026-03-21.

**Date:** 2026-03-23
**Status:** Upgrade 0 scoped from paper bot performance data (220 trades, 18 days)

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

**Problems at $3K:**
- 1 coin = zero rotation, stuck in single trades for days
- 75/25 split wastes capital in reserve that smaller accounts need for active grid depth

### What Needs to Change

#### 0A. New Equity Tier Table

```python
EQUITY_TIER_CAPS = [
    (100_000, 10),  # $100K+     -> 10 coins (full diversification)
    ( 50_000,  5),  # $50K-$100K ->  5 coins (proven on paper)
    ( 10_000,  5),  # $10K-$50K  ->  5 coins (same proven setup)
    (  5_000,  4),  # $5K-$10K   ->  4 coins (growing toward paper profile)
    (  3_000,  3),  # $3K-$5K    ->  3 coins (demo phase: turnover + depth)
    (  1_000,  3),  # $1K-$3K    ->  3 coins (max turnover, thin reserve OK)
    (    100,  1),  # $100-$1K   ->  1 coin  (too small to split)
]
```

**Rationale for 3 coins at $1K-$5K:**
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
    (50_000, 0.75, 0.25),  # $50K+    -> 75/25 (proven, deep safety buffer)
    (10_000, 0.75, 0.25),  # $10K-$50K -> 75/25 (same as paper)
    ( 5_000, 0.80, 0.20),  # $5K-$10K  -> 80/20 (slightly more active)
    ( 3_000, 0.85, 0.15),  # $3K-$5K   -> 85/15 (demo phase, depth > safety)
    ( 1_000, 0.90, 0.10),  # $1K-$3K   -> 90/10 (max grid depth, bounded risk)
    (   100, 0.90, 0.10),  # $100-$1K  -> 90/10 (single coin needs max depth)
]
```

**Why adaptive splits work:**

| Capital | Coins | Split | Per-Coin | Viable Layers | Smallest Layer | Reserve |
|---------|-------|-------|----------|---------------|---------------|---------|
| $1,000 | 3 | 90/10 | $300 | 9/12 | $5.19 | $100 |
| $2,500 | 3 | 85/15 | $708 | 11/12 | $6.01 | $375 |
| $3,000 | 3 | 85/15 | $850 | 11/12 | $7.21 | $450 |
| $5,000 | 4 | 80/20 | $1,000 | 12/12 | $5.93 | $1,000 |
| $10,000 | 5 | 75/25 | $1,500 | 12/12 | $8.90 | $2,500 |
| $50,000 | 5 | 75/25 | $7,500 | 12/12 | $44.49 | $12,500 |

**Reserve rationale at small accounts:**
- Reserve serves layers 6+ (code: `pool = "reserve" if layer >= 6 else "active"`)
- At 3 coins, simultaneous deep DCA across all 3 is rare (paper data: only 3 trades ever went to 5-6 layers)
- $450 reserve at $3K is enough for 1-2 coins hitting layer 6-7
- The risk of thin reserve is bounded: $3K total exposure, outside capital demo phase

#### 0C. Code Changes — `v14_capital_manager.py`

```python
# New: Equity-tiered pool splits
EQUITY_TIER_SPLITS = [
    (50_000, 0.75, 0.25),
    (10_000, 0.75, 0.25),
    ( 5_000, 0.80, 0.20),
    ( 3_000, 0.85, 0.15),
    ( 1_000, 0.90, 0.10),
    (   100, 0.90, 0.10),
]

@staticmethod
def get_tier_split(equity: float) -> tuple:
    """Return (active_pct, reserve_pct) for the given equity level."""
    for threshold, active, reserve in EQUITY_TIER_SPLITS:
        if equity >= threshold:
            return (active, reserve)
    return (0.90, 0.10)  # Default for tiny accounts
```

Update `__init__()`:
```python
def __init__(self, initial_capital: float):
    self.total_equity = initial_capital
    
    # Tier-aware pool split
    active_pct, reserve_pct = self.get_tier_split(self.total_equity)
    self.active_pool_total = self.total_equity * active_pct
    self.reserve_pool_total = self.total_equity * reserve_pct
    
    # ... rest unchanged
    logger.info(f"Pool split: {active_pct*100:.0f}/{reserve_pct*100:.0f} "
                f"(Active: ${self.active_pool_total:.2f} / Reserve: ${self.reserve_pool_total:.2f})")
```

Update `rebalance()` (the equity-refresh section):
```python
# Update equity and derive tier cap + split
self.total_equity = current_equity if current_equity else self.total_equity
active_pct, reserve_pct = self.get_tier_split(self.total_equity)
self.active_pool_total = self.total_equity * active_pct
self.reserve_pool_total = self.total_equity * reserve_pct
```

#### 0D. Code Changes — `run_v14_portfolio_live_aster.py`

No structural changes needed. The runner already reads `tier_coin_cap` from the router and uses it for coin selection. The pool split is consumed transparently.

The only change: update `status.json` to include the active split ratio:
```python
"pool_split": f"{active_pct*100:.0f}/{reserve_pct*100:.0f}",
```

#### 0E. Integration with Upgrade 1 (Dynamic Capital)

When Upgrade 1's `resize()` is implemented, it must also re-derive the pool split:
```python
def resize(self, new_equity: float):
    self.total_equity = new_equity
    active_pct, reserve_pct = self.get_tier_split(new_equity)
    self.active_pool_total = new_equity * active_pct
    self.reserve_pool_total = new_equity * reserve_pct
    # ... recalculate cash, tier cap, etc.
```

This means a deposit that crosses a tier boundary (e.g., $2.5K → $3.5K) automatically shifts from 90/10 to 85/15 **and** keeps 3 coins. The $5K boundary adds a 4th coin slot.

#### 0F. Dashboard Impact

- Show current tier info: `"3 coins | 85/15 split | $3K tier"`
- Pool allocation donut should reflect actual split (not hardcoded 75/25)
- Minor: update any hardcoded "75% / 25%" labels

### Layer Sizing Proof — $3K / 3 Coins / 85-15

```
Per-coin capital: $850 (from $2,550 active pool)
Reserve: $450

Layer  1: $255 (BO: 40% of $850)        ← covers 63.2% of trades
Layer  2: $178                            ← covers 85.5%
Layer  3: $125                            ← covers 94.5%
Layer  4:  $87                            ← covers 99.1%
Layer  5:  $61
Layer  6:  $43  ← switches to reserve pool
Layer  7:  $30
Layer  8:  $21
Layer  9:  $15
Layer 10:  $10
Layer 11:   $7  ← smallest viable ($7.21 > $5 min)
           ----
Total:    $832 deployed of $850 allocated
```

**11 layers viable.** Covers 100% of all historical completed trades (max was 6 layers). Leaves ~$18 per-coin headroom + $450 reserve pool.

### Files Modified
- `v14_capital_manager.py` — new `EQUITY_TIER_SPLITS`, `get_tier_split()`, updated `__init__()` and `rebalance()`
- `v14_capital_manager.py` — updated `EQUITY_TIER_CAPS` table
- `run_v14_portfolio_live_aster.py` — add `pool_split` to status.json output
- `d-984ae0d4ab9dc1a5.html` — update pool split display (minor)

### Complexity: Low
- Two new lookup tables and a static method
- Pool split calculation already exists, just parameterized instead of hardcoded
- No new data flows, no new state, no external dependencies
- Fully backward compatible (paper bot at $50K+ hits the same 75/25 / 5-coin tier)

### Test Plan: Upgrade 0 (Adaptive Tiers & Pool Split)

| # | Test | Steps | Expected Result |
|---|------|-------|-----------------|
| T0.1 | Tier lookup at $340 | Start bot with `--capital 340` | Tier: 1 coin, 90/10 split. Logs: "Pool split: 90/10" |
| T0.2 | Tier lookup at $1,000 | Start bot with `--capital 1000` | Tier: 3 coins, 90/10 split. Active: $900, Reserve: $100 |
| T0.3 | Tier lookup at $3,000 | Start bot with `--capital 3000` | Tier: 3 coins, 85/15 split. Active: $2,550, Reserve: $450 |
| T0.4 | Tier lookup at $5,000 | Start bot with `--capital 5000` | Tier: 4 coins, 80/20 split. Active: $4,000, Reserve: $1,000 |
| T0.5 | Tier lookup at $10,000 | Start bot with `--capital 10000` | Tier: 5 coins, 75/25 split. Active: $7,500, Reserve: $2,500 |
| T0.6 | Tier lookup at $50,000 | Start bot with `--capital 50000` | Tier: 5 coins, 75/25 split (paper bot reference) |
| T0.7 | Layer viability at $3K/3 coins | Check that smallest layer > $5 | All 11 viable layers above $5 min order |
| T0.8 | Layer viability at $1K/3 coins | Check layer sizing | 9 viable layers, smallest ~$5.19 |
| T0.9 | Rebalance at tier boundary | Equity grows from $4.9K to $5.1K | Tier changes: 3→4 coins, 85/15→80/20 split. Logged. |
| T0.10 | Paper bot unchanged | Run paper bot at $50K | Same behavior: 5 coins, 75/25, 12 layers |
| T0.11 | Status.json accuracy | Start at $3K, check status.json | `tier_coin_cap: 3`, `pool_split: "85/15"` |
| T0.12 | Reserve pool routing | At $3K, coin hits layer 6+ | Layer 6+ capital drawn from reserve ($450 pool) |

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
    - Update `self.router.total_equity` and recalculate pool splits (75/25)
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
The `CapitalRouter` needs a `resize(new_equity)` method. **Depends on Upgrade 0** — must use `get_tier_split()` for adaptive pool ratios:
```python
def resize(self, new_equity: float):
    """Dynamically resize pools after deposit/withdrawal."""
    self.total_equity = new_equity
    # Upgrade 0: tier-aware split (not hardcoded 75/25)
    active_pct, reserve_pct = self.get_tier_split(new_equity)
    self.active_pool_total = new_equity * active_pct
    self.reserve_pool_total = new_equity * reserve_pct
    # Recalculate cash = pool total - allocated
    allocated_active = sum(self.active_allocations.values())
    self.active_pool_cash = self.active_pool_total - allocated_active
    self.reserve_pool_cash = self.reserve_pool_total
    self.tier_coin_cap = self.get_tier_coin_cap(new_equity)
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

---

## Upgrade 3: Per-Coin Regime Flagging

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

**Recommended sequence:**

1. **Upgrade 0 (Adaptive Tiers & Pool Split)** — **PREREQUISITE for capital deposit.** Lowest complexity (two lookup tables + parameterized split). Must land before $1K deposit so the bot runs 3 coins from the start.
2. **Upgrade 1 (Dynamic Capital)** — Needed immediately after Upgrade 0 so deposits are auto-detected and capital is adjusted without restart. The `resize()` method must call `get_tier_split()` to recalculate pools on deposit.
3. **Upgrade 2 (Per-Coin Pause)** — Useful once 3+ coins are trading. Establishes per-coin gating pattern for Upgrade 3.
4. **Upgrade 3 (Per-Coin Regime Flagging)** — Highest complexity, builds on the per-coin pause pattern.

**Estimated effort:**
- Upgrade 0: ~1 hour (two tables, one static method, parameterize existing split)
- Upgrade 1: ~2-3 hours (porting + Router resize with tier-aware split)
- Upgrade 2: ~2-3 hours
- Upgrade 3: ~4-5 hours (new detection logic + auto-flag/unflag + dashboard)

**Critical path for capital deployment:**
```
Upgrade 0 (tiers) → Upgrade 1 (deposits) → Deposit $1K → Bot runs 3 coins / 90-10
                                           → Deposit $1.5K → Bot auto-adjusts to 3 coins / 85-15
                                           → Grow to $5K+ → Auto-adjusts to 4 coins / 80-20
                                           → Grow to $10K+ → Auto-adjusts to 5 coins / 75-25 (paper parity)
```

---

## Open Questions

0. **Tier boundary hysteresis:** When equity fluctuates around a boundary (e.g., $2,950 ↔ $3,050), the tier could flip back and forth between 90/10 and 85/15. Should we add a hysteresis band (e.g., must be 5% above threshold to upgrade, 5% below to downgrade)?

   > **Recommendation:** Yes, add a 5% hysteresis. Upgrade tier at threshold; downgrade only when equity drops 5% below threshold. This prevents split-flapping from normal PnL fluctuation. The coin cap already has graceful handling (existing positions allowed to exit on tier drop) — the same logic applies to the pool split.

1. **Deposit threshold:** What amount should trigger auto-detection? The old bot used 10% drift. For PM bot with $340 capital, 10% = $34. Should we use a fixed dollar floor (e.g., $5) instead?

   > **Recommendation:** Use $5 OR 2% (whichever is larger). With exchange-as-truth, drift detection is trivial since exact balances are already cached in `_exchange_usdt_total` — no estimation needed.

2. **Withdrawal with open positions:** Should we allow partial withdrawals when positions are open (reduce reserve only), or require all positions closed first?

   > **Recommendation:** Allow partial withdrawal from free balance. Exchange already protects margin — `usdt_free` is separate from `usdt_used`, so withdrawing free cash cannot liquidate open positions.

3. **Per-coin pause capital:** When a coin is paused, should its allocated capital be redistributed to other coins, or held in reserve until unpaused?

   > **Recommendation:** Hold paused capital in reserve until unpaused. Redistributing adds complexity and churn. The 25% reserve pool already provides buffer for new opportunities.

4. **Regime flag persistence:** If a flagged coin's TP fills and it has no position, should it stay flagged (waiting for global flip) or auto-clear since there's nothing to protect?

   > **Recommendation:** Auto-clear the flag when the TP fills and no position remains. The flag exists to protect open positions — there's nothing to protect if the position is gone.

5. **Manual RESUME overriding regime flag:** If Brett manually resumes a regime-flagged coin, should it be immune to re-flagging for some cooldown period, or can it re-flag immediately on the next candle?

   > **Recommendation:** 24h cooldown after manual RESUME before the coin can be re-flagged. If Brett overrode the flag, there's a reason — respect that intent for at least a day.
