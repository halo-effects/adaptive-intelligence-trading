# V14 Dashboard Review — Field Audit & Issues

**Reviewed**: 2026-02-28 16:30 PST
**File**: `docs/dashboardV14.html` (~1,212 lines)
**Data sources**: `data/v14/status.json`, `data/v14/trades.csv`, `data/v14/scanner.json`

---

## Critical Issues (Broken / Wrong Data)

### 1. ❌ Equity Chart Won't Plot — Wrong Field Names
**Location**: `renderEquityChart()` (~line 1150)
**Problem**: Uses `t.timestamp || t.time` but trades.csv columns are `open_time` and `close_time`.
```js
// BROKEN:
var t0 = trades[0] ? trades[0].timestamp || trades[0].time : null;
// ...
var tm = t.timestamp || t.time;

// FIX:
var t0 = trades[0] ? trades[0].close_time || trades[0].open_time : null;
// ...
var tm = t.close_time || t.open_time;
```
**Impact**: Equity chart shows only the final S.equity point with no history. All 363 trades have no x-axis.

### 2. ❌ Trade Log Regime Badges Unstyled
**Location**: `renderTrades()` (~line 1120)
**Problem**: V14 trades.csv `regime` column contains phase names (`LONG_DCA`, `SHORT_DCA`) but CSS `REGIME_CLS` only maps market regimes (`ACCUMULATION`, `TRENDING`, `RANGING`, `EXTREME`). Phase names get no styling.
**Fix**: Add V14 phase mappings:
```js
var REGIME_CLS = {
  // existing...
  LONG_DCA: 'rb-ACC',     // green
  SHORT_DCA: 'rb-EXTREME', // red
  ROUTER: 'rb-RANGING'     // purple
};
```

### 3. ❌ Missing `regime` and `trend_direction` in status.json
**Location**: Header badges `hdrRegime`, `hdrTrend`
**Problem**: V14 runner (`run_v14_paper.py _write_status()`) doesn't write `regime` or `trend_direction` fields. Header shows "--" for both.
**Fix**: Either add these fields to the runner, or remove/repurpose the header badges for V14-specific info (e.g., "3 LONG / 1 SHORT" direction summary).

---

## Math Issues

### 4. ⚠️ Leveraged Equity Calculation Wrong
**Location**: `renderPositions()` — "Leveraged Equity" stat
**Current**: `fUsd(inv * 1.5)` — simply multiplies invested capital by leverage
**Problem**: This is misleading. ATOM has $15,400 invested with -$3,876 unrealized PnL. Dashboard shows "Leveraged Equity: $23,100" but the actual leveraged position value should factor in unrealized PnL.
**Correct formula**: `invested * leverage + unrealized_pnl` OR just show the raw invested (since leverage is already applied to equity/PnL by the engine).
**Recommendation**: Remove this field or show `invested + unrealized_pnl` (net position value). The top-level equity already includes leverage.

### 5. ⚠️ Unrealized PnL % Denominator
**Location**: `renderStats()` — Unrealized PnL sub-text
**Current**: `upnlPct = totalUpnl / totalInv * 100`
**Issue**: `totalInv` sums invested across ALL coins (both long and short). For HBAR (SHORT_DCA), invested=$4,425 with upnl=-$377; for ATOM (LONG_DCA), invested=$15,400 with upnl=-$3,876. The combined percentage conflates long and short positions. Not technically wrong but potentially confusing.
**Minor** — acceptable as aggregate.

---

## Data Gaps (Missing Signal State)

### 6. ⚠️ Top Detection / Conviction Status Are Guesses
**Location**: `renderAIPanel()`
**Current logic**:
```js
var topStatus = phase === 'SHORT_DCA' ? 'fired' : (phase === 'ROUTER' ? 'armed' : 'monitoring');
var convictionStatus = phase === 'LONG_DCA' ? 'fired' : (phase === 'ROUTER' ? 'pending' : 'monitoring');
```
**Problem**: Derives signal state from current phase. A coin in LONG_DCA could have OB93 armed (top arming detected but not confirmed) — dashboard would show "Monitoring" when it should show "Armed".
**Fix (long-term)**: Add signal state to status.json per-coin:
```json
"signals": {
  "ob93_armed": true,
  "divergence_detected": false,
  "conviction_score": 0,
  "death_cross_active": true
}
```
**Workaround (quick)**: Accept the approximation for now. Note it's inferred, not exact.

### 7. ⚠️ Risk Profile Params Hardcoded
**Location**: `renderRiskProfile()`
**Problem**: Always shows Medium profile params (BO=40%, DEV=2.0%, LAYERS=10, TP=1.5%, MULT=1.5×, LEV=1.5×) regardless of actual profile from status.json.
**Fix**: Read from status.json `S.profile` and display profile-specific params:
```js
var PROFILES = {
  low:    { bo:'40%', dev:'2.0%', layers:10, tp:'1.5%', mult:'1.5×', lev:'1.0×' },
  medium: { bo:'40%', dev:'2.0%', layers:10, tp:'1.5%', mult:'1.5×', lev:'1.5×' },
  high:   { bo:'40%', dev:'1.5%', layers:12, tp:'1.5%', mult:'1.5×', lev:'1.5×' }
};
```

---

## Mobile CSS Issues

### 8. ⚠️ Coin Cards Min-Width Too Large
**Location**: `.coins-grid { grid-template-columns: repeat(auto-fit, minmax(400px, 1fr)) }`
**Problem**: On screens <400px (many phones in portrait), cards overflow horizontally.
**Fix**: Change to `minmax(300px, 1fr)` or `minmax(280px, 1fr)`.

### 9. ✅ Responsive Breakpoints — Generally Good
- 1024px: 3-col summary, single chart, stacked risk grid ✅
- 768px: 2-col summary, vertical header, single AI grid, table overflow ✅
- 480px: 1-col summary, vertical phase flow ✅
- Position stats → 2-col at 768px ✅

### 10. ⚠️ No `touch-action` or Tap Target Sizing
**Minor**: Pagination buttons and select dropdowns don't have explicit `min-height: 44px` (Apple HIG touch target). Works but not ideal for fat fingers.

---

## Minor Issues

### 11. ⚠️ Trade Side Detection in Opportunity Table
**Location**: `renderFlowDiagram()` — `coinTradeCounts`
**Problem**: Checks `t.side` and `t.action` but trades.csv has neither. Has `regime` (which contains the phase: `LONG_DCA` or `SHORT_DCA`).
**Fix**:
```js
// Instead of checking t.side/t.action:
var phase = (t.regime || '').toUpperCase();
if (phase === 'SHORT_DCA') coinTradeCounts[sym].short++;
else coinTradeCounts[sym].long++;
```

### 12. ℹ️ Compounding 2x Target May Be Passed
**Location**: `renderCompounding()` — progress bar capped at 100%
**Current**: Target is `cap * 2 = $20,000`. Equity is $70,767 (353% of target). Progress bar correctly caps at 100% but the visual is meaningless at this point.
**Suggestion**: Dynamic milestone targets ($25K → $50K → $100K → $250K) based on current equity.

### 13. ℹ️ `deals_won` Attribute on Engine
**Location**: Runner `_write_status()` uses `engine.deals_won`
**Status**: Confirmed this is set in the lifecycle wrapper. Not a dashboard issue — works correctly.

---

## Summary

| Severity | Count | Action |
|----------|-------|--------|
| ❌ Critical | 3 | Must fix — broken charts, unstyled badges, missing fields |
| ⚠️ Medium | 6 | Should fix — wrong math, hardcoded params, overflow |
| ℹ️ Minor | 2 | Nice to have — dynamic targets, touch sizing |

### Priority Fix Order
1. **Equity chart field names** (1 min fix — `timestamp`→`close_time`)
2. **Trade log regime class mapping** (add LONG_DCA/SHORT_DCA/ROUTER to REGIME_CLS)
3. **Coin cards min-width** (400px → 300px)
4. **Trade side detection** (use `t.regime` not `t.side`)
5. **Remove misleading Leveraged Equity** (or fix formula)
6. **Risk profile params from status.json** (not hardcoded)
7. **Add regime/trend to V14 runner** (or repurpose header badges)
