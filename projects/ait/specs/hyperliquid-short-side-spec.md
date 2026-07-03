# Hyperliquid Short-Side Spec
_Version: 1.0 | Date: 2026-07-03 | Status: SPEC — pending Hyperliquid migration_
_References: V14PM_SYSTEM_ARCHITECTURE.md §5.1, audit finding H3 (fixed), signal-aware-deployment.md_

---

## 1. Problem Statement

The live runner (`run_v14_portfolio_live_aster.py`) explicitly rejects SHORT_OPEN actions:
```python
elif act_type in ("SHORT_OPEN", "SHORT_CLOSE"):
    logger.warning(f"SHORT action {act_type} for {sym} — not supported in live mode.")
    cs.engine.reject_action(action)
```

The V14 engine already supports SHORT_DCA phases with full grid mechanics (mirrored from long).
The regime system supports SHORT_DCA global direction. When the cycle top is confirmed and
regime flips to SHORT_DCA, the live bot goes fully idle — longs gated by regime, shorts rejected
by the runner. This is tolerable in the current bull phase but becomes a lost-revenue gap during
the ~1-year down-leg of the crypto cycle.

## 2. Prerequisites (all completed or in progress)

| # | Prerequisite | Status |
|---|-------------|--------|
| 1 | H3 fix: position sync branches on side | ✅ Done (2026-07-03) |
| 2 | GridModel for short layer sizing | ✅ Done (grid_model.py is side-agnostic) |
| 3 | Engine SHORT_DCA tick | ✅ Exists (v14_dca_engine._short_dca_tick) |
| 4 | Orphan-TP for shorts | ✅ Exists (v14_lifecycle_engine handles orphaned short TP) |
| 5 | Regime gate for shorts | ✅ Exists (blocks SHORT_OPEN when global is LONG_DCA) |
| 6 | Signal-aware deployment (Part B short side) | ⏳ Backtest pending (signal-aware-deployment.md) |

## 3. Scope

### 3.1 Short Deal Keys in TradeTracker

Current `TradeTracker` uses deal keys like `{sym}:long`. Short deals need `{sym}:short`.

```python
# on_sell for short = buy-back (close short)
# on_buy for short = sell-to-open (enter short)
```

The key scaffolding (`":short"` pattern) already exists in open_deals handling. Needed:
- `on_short_open(sym, qty, price, cost, fee, ts)` — records a short entry
- `on_short_close(sym, qty, price, proceeds, fee, ts)` — records short close (buy-back)
- PnL = `short_cost - buy_back_cost - fee` (sold high, bought low)
- CSV columns: add `side` column (default "long" for existing trades)

### 3.2 Short TP Mechanics on Hyperliquid

| Aspect | Aster (current) | Hyperliquid (target) |
|--------|-----------------|---------------------|
| Short TP type | N/A (shorts not supported) | `TRAILING_STOP_BUY` or `STOP_MARKET` (buy-back) |
| Trailing support | `TRAILING_STOP_MARKET` (sell) | TBD — check HL CCXT docs for trailing buy |
| Order params | `positionSide: BOTH` | `reduceOnly: True` (HL unified margin) |

**Key question**: Does Hyperliquid CCXT support trailing stop buy orders? If not, the short TP
falls back to a limit buy order at `avg_entry * (1 - TP_PCT)`, checked via polling (like the
paper bot's candle-close check, but on exchange).

### 3.3 Runner Changes

1. Remove the SHORT_OPEN/SHORT_CLOSE rejection block
2. Add short-specific order methods to the exchange client:
   - `create_market_sell_short(sym, qty)` — open short (sell to open)
   - `create_market_buy_short(sym, qty)` — close short (buy to close)
3. Add short TP placement: `place_trailing_stop_buy` or `place_limit_buy`
4. Position sync: H3 fix already handles side branching — extend to write `eng.short_*`
5. TP fill detection: check for buy-side fills on short TP orders

### 3.4 Validation Plan

1. **Paper validation (no real money)**:
   - Deploy shorts on V14PM paper bot (Hyperliquid) first
   - Simulate a full regime flip (LONG → SHORT) with at least 3 coins
   - Verify: short entries, DCA layers, TP hits, position sync, CSV recording
   - Run through at least one full LONG → SHORT → LONG cycle

2. **Live rollout sequence**:
   - Pre-flight import test
   - Deploy with `SHORT_ENABLED = False` flag initially
   - Flip flag to True after paper validation
   - First live short manually reviewed against scanner ranking

## 4. Out of Scope

- Grid-profile-per-regime (Task 4.5 — separate spec)
- Signal-aware deployment short-side live activation (rides with this spec's implementation)
- Aster DEX short support (migrating away from Aster)

## 5. Dependencies

- Hyperliquid exchange client port (CLOUD_MIGRATION_GUIDE.md Phase 5)
- CCXT trailing stop buy order support verification
- Paper bot short validation (minimum 30 days before live consideration)
