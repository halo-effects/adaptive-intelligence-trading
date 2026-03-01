# Price Discovery Mode for Exit Logic

## Problem

When a coin's price exceeds its **KNOWN_ATH** (historical all-time high), the ATH proximity gate becomes useless for exit detection. The gate checks "is price within 25% of ATH?" — but during price discovery, the rolling ATH updates to the current price, so any small dip trivially passes.

**Result**: ZEC thrashed DCA↔MARKDOWN every 1-3 hours during its $74→$724 parabolic run. BTC had similar issues during $73K→$109K.

## Solution

When `current_price > KNOWN_ATH`, replace the ATH proximity gate with **weekly candle structure confirmation**. The daily TA scorer still fires the EXIT signal, but instead of checking ATH distance, we require bearish weekly structure to confirm distribution.

## Implementation

### New Method: `DailyScorerConductor.weekly_confirms_exit_price_discovery()`

Located in `backtest_engine_v12.py` (shared by both backtest and live engine).

Confirms EXIT in price discovery if **ANY** of:
1. **Bearish engulfing**: Weekly close < weekly open AND close < prior week's low
2. **>10% drop from peak**: Current price dropped >10% from the rolling high during price discovery
3. **Two consecutive weekly lower closes**: After the peak week, two weeks of declining closes

If none match → **VETO** the EXIT (conservative — stay in DCA/MARKUP during parabolic runs).

### Live Engine Changes (`lifecycle_engine.py`)

- Added `price_discovery_mode: bool` and `price_discovery_peak: float` to `LifecycleState`
- Both fields persist in `state.json` (backward compatible — default `False`/`0.0`)
- In `_process_dca()`: when commitment window completes AND conductor is in price discovery:
  - Activates price discovery mode, tracks rolling peak
  - Calls `weekly_confirms_exit_price_discovery()` instead of allowing direct transition
  - Logs VETO when weekly doesn't confirm
  - Exits price discovery mode when price drops back below KNOWN_ATH

### Backtest Engine Changes (`backtest_engine_v12.py`)

- Updated all 3 price discovery gate locations to use `weekly_confirms_exit_price_discovery()`:
  1. `step()` method — DCA→EXIT (line ~1022)
  2. `_run_main_loop()` — DCA→EXIT (line ~1220)
  3. MARKUP→EXIT transition (line ~2238)
- Previously used generic `weekly_confirms_exit("distribution")` which only checked RSI>60 + momentum<5%

## Behavior Trace

### ZEC $74→$724 Scenario
- Price starts climbing past KNOWN_ATH (~$320)
- Conductor fires EXIT signal (daily score ≥ threshold)
- `_in_price_discovery = True` since price > $320
- `weekly_confirms_exit_price_discovery()` checks weekly candles
- During parabolic rise: weekly closes are HIGHER each week → no bearish engulfing, no lower closes, no 10% drop → **VETO**
- ZEC stays in DCA, continues accumulating during the parabola
- When distribution starts (weekly bearish engulfing or 10% drop from $724 peak) → EXIT confirmed
- Clean single transition instead of thrashing

### BTC $73K→$109K Scenario
- Same logic — price > KNOWN_ATH ($73,750 in backtest, $109K in live)
- Weekly structure stays bullish during run → VETO
- On actual top/distribution → weekly confirms → clean EXIT

## Files Modified

| File | Change |
|------|--------|
| `trading/spot/backtest_engine_v12.py` | Added `weekly_confirms_exit_price_discovery()` method to `DailyScorerConductor`; updated 3 price discovery gate sites |
| `trading/spot/lifecycle_engine.py` | Added `price_discovery_mode`/`price_discovery_peak` to `LifecycleState`; gated DCA→EXIT on weekly confirmation in price discovery |

## Constraints Met
- ✅ Normal behavior when price < KNOWN_ATH unchanged (ATH gate still applies)
- ✅ Backward compatible (new state fields default to False/0.0)
- ✅ No bot restarts required
- ✅ Conservative in price discovery (veto on insufficient data or errors)
