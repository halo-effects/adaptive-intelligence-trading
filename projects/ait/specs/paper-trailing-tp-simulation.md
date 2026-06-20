# Paper Bot Trailing TP Simulation

**Date**: 2026-06-19
**Status**: Draft — Analysis Required Before Implementation
**Author**: Brett + Gee Gee
**Severity**: Paper simulation accuracy (no real money impact)
**Affects**: `engine/v14_dca_engine.py` (or paper runner only)

---

## 1. Current State

### 1.1 Live Bot (Aster)
The live bot uses **exchange-native trailing stops** (`TRAILING_STOP_MARKET` on Aster):
- **Activation price**: `avg_entry × (1 + TP_PCT)` — same as the fixed TP level (3.0% for high profile)
- **Callback rate**: 0.2% (from peak price after activation)
- **Behavior**: Once price reaches the activation level, Aster tracks the peak price. If price pulls back 0.2% from peak, a market sell triggers. This captures upside beyond the 3% TP.
- **Execution**: Aster handles all trailing logic natively. The bot places the order and waits for fill notification.

### 1.2 Paper Bot (Engine)
The paper bot uses the **DCA engine's internal TP check**:
```python
if price >= self.long_tp:  # long_tp = avg_entry × 1.03
    proceeds = self.long_coins * price  # candle CLOSE price
```
- **No trailing mechanism** — sells immediately when any candle close >= TP
- **Sells at candle close price**, which can be above or below what a real trailing stop would capture
- **No activation/callback logic** at all

### 1.3 How They Diverge

| Scenario | Live (Trailing) | Paper (Fixed) | Impact |
|----------|----------------|---------------|--------|
| Candle closes exactly at TP (3.0%) | Activated, trails higher | Sells at 3.0% | Paper understates |
| Candle gaps from 2% to 8% in one bar | Activates at 3%, trails to ~7.8% (8% - 0.2% callback) | Sells at 8% close | Paper overstates |
| Price drifts up 0.1% per hour for 5h past TP | Trails up, sells when pullback > 0.2% | Sells at first close >= 3% | Paper understates significantly |
| Sudden spike to 50%+ (HYPE scenario) | Activates at 3%, trails to ~49.8% | Sells at 50%+ close | Paper matches (both get the high price) |
| Price touches 3%, reverses, closes at 2.5% | Doesn't activate (candle high hit 3% but close didn't) | Doesn't sell (close < TP) | Both agree |

**Key insight**: The live trailing stop activates when price REACHES the TP level during the candle (intra-candle), then trails the HIGH. The paper bot only sees the CLOSE. These are fundamentally different price observations.

---

## 2. Proposed Simulation

### 2.1 Approach: Intra-Candle Trailing Simulation

Simulate the trailing stop using the candle's OHLC data:

```python
def _check_trailing_tp(self, candle, eng):
    """Simulate trailing stop TP using candle high/low/close.
    
    Logic:
    1. If candle HIGH >= activation_price: trailing stop activates
    2. Once activated, peak_price = candle HIGH
    3. Check if candle LOW pulls back >= callback from peak
       - If yes: fill at peak × (1 - callback)
       - If no: position stays open, peak carries to next candle
    4. On subsequent candles, update peak from HIGH if higher
    """
    activation_price = eng.long_avg_entry * (1 + eng.cfg.DCA_TP_PCT)
    callback_pct = 0.002  # 0.2%
    
    high = candle["high"]
    low = candle["low"]
    close = candle["close"]
    
    # Check activation
    if high >= activation_price:
        # Trailing stop activates this candle
        peak = high
        
        # Check if callback triggered within same candle
        callback_level = peak * (1 - callback_pct)
        if low <= callback_level:
            # Callback triggered: fill at callback level
            fill_price = callback_level
            return fill_price
        else:
            # Trailing active but no callback yet
            # Store peak for next candle check
            eng._trailing_peak = peak
            eng._trailing_active = True
            return None  # No fill yet
    
    # If trailing was already active from a previous candle
    if getattr(eng, '_trailing_active', False):
        peak = max(getattr(eng, '_trailing_peak', 0), high)
        eng._trailing_peak = peak
        
        callback_level = peak * (1 - callback_pct)
        if low <= callback_level:
            fill_price = callback_level
            eng._trailing_active = False
            eng._trailing_peak = 0
            return fill_price
    
    return None  # No TP triggered
```

### 2.2 Where to Implement

**Option A: In the DCA engine (`v14_dca_engine.py`)**
- Replace the `price >= self.long_tp` check with trailing simulation
- Pro: All bots (paper, backtest) get accurate TP
- Con: Changes the core engine used by backtests — could change all historical results
- Con: Backtests use daily candles (not hourly) — trailing on daily OHLC is less accurate

**Option B: In the paper runner only (`run_v14_portfolio_paper.py`)**  
- Intercept the engine's SELL action and adjust the fill price
- Pro: No impact on backtests or live bot
- Con: Paper runner becomes more complex, diverges from engine truth

**Option C: Engine flag (`DCA_TRAILING_TP = True/False`)**
- Add trailing logic inside the engine, gated by a config flag
- Pro: Clean — engine handles all TP logic, flag controls behavior
- Con: Still changes engine, but flag prevents backtest impact

### 2.3 Recommendation: Option C (Engine Flag)

```python
class V14Config:
    DCA_TRAILING_TP = False      # Default off (backtests use fixed TP)
    DCA_TRAILING_CALLBACK = 0.002  # 0.2% callback rate
```

Paper runner sets `DCA_TRAILING_TP = True` on engine creation. Backtests keep `False`.

---

## 3. Risks and Concerns

### 3.1 Intra-Candle Simulation is Approximate

Real trailing stops on an exchange operate on every tick (sub-second). We're simulating with 1-hour OHLC bars. Within a 1-hour candle:
- We know the HIGH (peak) and LOW (trough) but NOT the order
- Did price go high-then-low (trailing activates then callback triggers) or low-then-high (no activation)?
- **Assumption**: We assume high comes before low within the candle. This biases toward triggering callbacks within the same candle, which means slightly LOWER fill prices than reality.

This is a well-known limitation of OHLC-based backtesting. The only way to fix it is with tick-level data (not available).

### 3.2 Multi-Candle Trailing State

If the trailing stop activates on candle N but doesn't callback until candle N+5, we need persistent state across candles:
- `eng._trailing_active` (bool)
- `eng._trailing_peak` (float)

These must be:
- Saved/restored in `snapshot_state()` / `restore_state()` — otherwise restart resets the trailing state
- Reset to 0 on TP close
- Reset if position is closed by other means (force-close, regime change)

### 3.3 Impact on Paper Bot Performance Metrics

Adding trailing TP simulation will **change** the paper bot's reported PnL. Current PnL ($61K gain) includes:
- Inflated trades from candle replay (now fixed)
- Fixed TP fills at candle close (sometimes above 3%, sometimes exactly 3%)

With trailing TP simulation:
- Some trades will capture MORE than 3% (price trails up before callback)
- Some trades will capture LESS than candle close (callback triggers below close)
- Net effect is unknown — needs backtest comparison

### 3.4 Backtest Comparison Required

Before deploying, run a backtest comparison:
1. Same coins, same period, same profile
2. Run A: Fixed TP (current behavior)  
3. Run B: Trailing TP simulation
4. Compare: total PnL, avg return per trade, win rate, max drawdown

If trailing TP simulation produces WORSE results than fixed TP, it means the 0.2% callback is too tight for 1h candles (callbacks trigger on noise within candles). In that case, either:
- Increase callback for paper simulation (0.5%? 1.0%?)
- Or keep fixed TP for paper (accept the simulation gap)

### 3.5 Interaction with Orphan-TP Mode

Orphaned positions (engine phase flipped, position waiting for TP) still need TP checks. The trailing simulation must work for orphaned positions too — the trailing state must survive phase transitions.

### 3.6 Interaction with DCA Layers

When a DCA layer fills (L2, L3, L4), the `avg_entry` changes and `long_tp` is recalculated:
```python
self.long_avg_entry = self.long_cost / self.long_coins
self.long_tp = self.long_avg_entry * (1 + cfg.DCA_TP_PCT)
```

If a trailing stop was already active from the old TP level, the new DCA layer changes the activation price. The trailing stop should:
- **Reset**: Deactivate the trail, use the new TP level as the new activation price
- This matches exchange behavior — on Aster, a new DCA layer would cancel the old TP order and place a new one at the updated avg_entry × 1.03

---

## 4. Implementation Plan (If Approved)

1. Add `DCA_TRAILING_TP` and `DCA_TRAILING_CALLBACK` to `V14Config`
2. Add `_trailing_active` and `_trailing_peak` to engine state
3. Add to `snapshot_state()` / `restore_state()`
4. Modify `_long_dca_check()` to use trailing logic when `DCA_TRAILING_TP = True`
5. Reset trailing state on DCA layer fill (avg_entry changes)
6. Reset trailing state on position close
7. Set `DCA_TRAILING_TP = True` in paper runner engine creation
8. Run backtest comparison (fixed vs trailing, same data, 90 days)
9. Evaluate results before deploying to paper bot

---

## 5. Decision Required

| Question | Options |
|----------|---------|
| Implement trailing TP simulation? | Wait for backtest comparison results |
| Where to implement? | Option C recommended (engine flag) |
| What callback rate? | Start with 0.2% (matches live), evaluate in backtest |
| High/Low ordering assumption? | Assume high-before-low within candle (conservative) |
| Reset trail on DCA layer? | Yes — matches exchange behavior |

**Recommendation**: Run the backtest comparison first. If trailing simulation produces comparable or better results with realistic trade profiles, implement. If it produces significantly different results or artifacts from the OHLC limitation, keep fixed TP for paper and accept the simulation gap.
