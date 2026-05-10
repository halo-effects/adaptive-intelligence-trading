# V2 Audit — Phase 3: Coin Selection & Scoring (Cycle Scanner)

**Date**: 2026-05-10  
**Auditor**: OpenClaw AI  
**Files reviewed**: `v14_cycle_scanner.py` (877 lines), `v14_capital_manager.py` (560 lines), integration with live bot (`run_v14_portfolio_live_aster.py`)  
**Status**: COMPLETE — Scanner operating normally, minor findings documented

---

## FINDING 17: DCA Score Calculation May Produce Zero When No Deals Completed

**File**: `v14_cycle_scanner.py`, line 319  
**Code**:
```python
result["dca_score"] = round(
    result["realized_pnl"] * (1 - max_dd) * result["capital_freedom"] / 100,
    2
)
```

**Issue**: When a coin's DCA simulation completes 0 deals (no TP hits during the backtest window):
- `realized_pnl` = 0
- `dca_score` = 0 * (1 - max_dd) * capital_freedom / 100 = 0

Example: MKR in the bear window (Jan 1 - May 10, 2026) has:
- 0 deals completed
- 0 realized PnL
- DCA score = 0.0

This is mathematically correct but semantically odd: a coin that was never entered is ranked identically to one that entered N times but lost money. The capital router's hurdle rate (DCA score ≥ 5.0) filters these out, so it's not a blocking issue, but it masks the reason coins score 0.

**Severity**: LOW (hurdle rate masks the issue, but scoring transparency could be improved)  
**Recommendation**: Add a `reason_code` field to scanner output:
- `REASON_NO_DEALS` — never entered (0 completed deals)
- `REASON_NEGATIVE_PNL` — entered but unprofitable
- `REASON_HIGH_DD` — entered but high drawdown
- `REASON_LOW_CAPITAL_FREEDOM` — too many layers left open

---

## FINDING 18: Anomalous High-Drawdown Coins Pass Hurdle Rate

**Observation**: 21 of 46 coins in the bear window have drawdowns > 50%. Some still score > 5.0 because realized PnL is high enough to overcome it.

Examples (scored > 5.0 but DD > 50%):
- TAO: score 29.1, DD 50.3%, 96 deals, 100% WR
- RENDER: score 18.0, DD 51.1%, 67 deals, 100% WR
- FET: score 12.9, DD 53.1%, 48 deals, 100% WR
- EIGEN: score 11.1, DD 65.4%, 52 deals, 100% WR
- ENA: score 4.1, DD 69.5%, 3 deals, 100% WR
- ENS: score 2.9, DD 76.7%, 1 deal, 100% WR

**Interpretation**: High drawdown + 100% win rate = simulation never closed a losing position. The DCA grid catches every dip, never gets liquidated or stuck. Result: PnL compounds, score remains positive.

**Severity**: LOW (this is the DCA spec working correctly — grid catches dips. High DD is expected in range-bound markets)  
**Note**: Brett should review whether these coins are acceptable for production despite high DD. Some (ENA with 69.5% DD) might indicate thin liquidity or extreme choppiness.

---

## FINDING 19: Scanner JSON Format Inconsistency

**File**: `v14_cycle_scanner.py`, lines 430-460  
**Issue**: The scanner outputs:
```json
{
  "generated_at": "ISO timestamp",
  "windows": {
    "bear": {
      "rankings": [ { "coin": "BTC", "symbol": "BTC/USDT", "dca_score": 50.2, ... } ]
    }
  },
  "top_picks": { "best_score": "ZRO", ... }
}
```

But `load_scanner_json()` in `v14_capital_manager.py` tries to handle many legacy formats:
- `windows.30d.rankings[]`
- `windows.bear.rankings[]`
- `30d[]` (flat list)
- `bear[]` (flat list)
- Any list in the dict

The code is defensive (fail-open on parse errors) but suggests the JSON structure has changed over versions. The current scanner always outputs `windows.{window}.rankings[]`, so the legacy paths aren't needed.

**Severity**: LOW (defensive parsing works, but adds code smell)  
**Recommendation**: Document the canonical format in the scanner or consolidate parser to single path

---

## FINDING 20: Capital Router Hardcodes Hurdle Rate = 5.0

**File**: `v14_capital_manager.py`, line 253  
**Code**:
```python
if base_score >= 5.0:
    qualifying.append((symbol, base_score * trend_mult))
```

**Issue**: The 5.0 hurdle is hardcoded. If Brett wants to adjust it (e.g., raise to 10.0 during bear, lower to 3.0 during bull), it requires code change. No environment variable or config file control.

**Severity**: MEDIUM (non-urgent but reduces flexibility for production tuning)  
**Recommendation**: Move hurdle to a constant at module level: `HURDLE_RATE_DCA_SCORE = 5.0`

---

## FINDING 21: Stale Scanner JSON Data Risk

**File**: `run_v14_portfolio_live_aster.py`, lines 1895-1945  
**Issue**: The live bot reads `cycle_scanner.json` to gate whether coins can re-enter after TP. But scanner runs on a schedule (daily? hourly?). If scanner hasn't run since yesterday but bot is trading actively, the bot's re-entry decision is based on stale rankings.

The bot has a fail-open behavior: if scanner JSON is missing/unreadable, `_get_scanner_top_n_symbols()` returns empty set, and `_prune_stale_coin_after_tp()` defaults to keeping the coin. This prevents accidental locks but masks the stale data problem.

**Severity**: MEDIUM (affects allocation accuracy but not trading safety)  
**Recommendation**: Add freshness check — log warning if scanner JSON is >24 hours old

---

## FINDING 22: No "Trend Multiplier" in Scanner Output

**Observation**: The capital manager's `load_scanner_json()` expects `trend_scores` dict in the JSON:
```python
trend_scores = data.get("trend_scores", {})
if trend_scores:
    for entry in rankings:
        coin = entry.get("coin")
        if coin in trend_scores:
            entry["trend_multiplier"] = td.get("trend_multiplier", 1.0)
```

But `v14_cycle_scanner.py` doesn't generate `trend_scores`. Every coin gets default multiplier = 1.0 (neutral).

**Severity**: LOW (feature is disabled, not broken)  
**Recommendation**: Either remove the unused code path or implement trend multiplier computation in scanner (acceleration/deceleration of price vs signal momentum)

---

## FINDING 23: DCA Simulation Doesn't Account for Exchange Funding Rates

**File**: `v14_cycle_scanner.py`, lines 80-240  
**Issue**: The scanner simulates DCA on 1h candles using taker fees (0.025%) but ignores:
- Funding rates (on Hyperliquid perpetuals, can be 0.01-0.03% per 8h)
- Slippage on large orders
- Partial fills on limit orders
- Order rejection due to insufficient balance

The simulation assumes:
- All orders fill at exact price (open/high/low)
- All fills are at taker fee only
- No funding fees

**Severity**: MEDIUM (simulator results optimistic, real performance will be lower)  
**Recommendation**: Add funding rate adjustment — either:
1. Include annualized funding in the backtest (requires funding data in DB)
2. Apply a 0.01% per-day haircut to PnL estimates
3. Document the assumption and plan to calibrate post-migration

---

## FINDING 24: NO DATA QUALITY CHECK ON CANDLES PASSED TO SIMULATOR

**File**: `v14_cycle_scanner.py`, lines 160-170  
**Code**:
```python
for window in windows:
    start_ms, end_ms = get_window_range(window, now_ms)
    candles = load_candles(conn, symbol, start_ms, end_ms)

    if len(candles) < 10:
        logger.warning(f"  {window}: only {len(candles)} candles for {short_name}, skipping")
        continue

    sim = run_dca_sim(candles, symbol, window)
```

The scanner checks candle count (skip if <10) but doesn't validate:
- Candle timestamps are consecutive (no gaps > 1h + margin)
- OHLC values make sense (high ≥ low, close in [low, high], non-negative)
- Volume is non-negative
- No duplicates or resampling artifacts

If a coin has corrupted candles (e.g., a fat-finger entry where high=999999), the simulation runs but produces garbage results.

**Severity**: MEDIUM (unlikely but would corrupt rankings if it happens)  
**Recommendation**: Add candle validator before passing to simulator

---

## FINDING 25: MEDIUM — Scanner Hardcodes 45-Coin Universe

**File**: `v14_cycle_scanner.py`, lines 37-62  
**Code**:
```python
COINS = [
    'BTC/USDC', 'ETH/USDC', 'SOL/USDC', 'XRP/USDT', 'LINK/USDT',
    ...
    'HYPE/USDC', 'ASTER/USDT', 'AAVE/USDT',
]
```

The list is hardcoded in the file. To add a new coin to the scanner, you must:
1. Edit the Python source
2. Commit/push
3. Restart the scanner process

For operational agility (especially during migration when new coins might be added), this is rigid. Better approach: load coin list from DB or a config file.

**Severity**: LOW (operational friction, not a correctness issue)  
**Recommendation**: Load COINS from a `scanner_universe.json` config file or DB table

---

## Integration Assessment

**Scanner → CapitalRouter → LiveBot flow:**

1. **Scanner** runs daily (schedule TBD), outputs cycle_scanner.json with DCA scores
2. **CapitalRouter** reads JSON daily during rebalance, selects top-N by score × trend_mult
3. **LiveBot** executes positions, periodically checks if coins are still in top-N (prune stale)

**Data quality at each stage:**
- Scanner input: ✅ Phase 2 fixes ensure all coins have indicators
- Scanner output: ⚠️ No validation of candle quality pre-sim, MKR edge case (0 deals = 0 score)
- Router input: ✅ Parser is defensive, handles missing JSON
- Router output: ✅ Proportional allocation by score, risk caps enforced
- Bot input: ✅ Reads top-N, prunes stale coins post-TP

**Critical gaps:**
- None blocking. Operations are stable.

---

## Summary

| # | Severity | Finding | Status |
|---|----------|---------|--------|
| 17 | LOW | DCA score = 0 when 0 deals (MKR case) | 🟡 Masking |
| 18 | LOW | 21 coins with DD > 50% (expected for DCA) | 🟢 Normal |
| 19 | LOW | JSON format inconsistency (legacy parser) | 🟡 Code smell |
| 20 | MEDIUM | Hurdle rate hardcoded (5.0) | 🟡 Inflexible |
| 21 | MEDIUM | Stale scanner JSON risk | 🟡 Need freshness check |
| 22 | LOW | Trend multiplier feature disabled | 🟡 Unused code |
| 23 | MEDIUM | DCA sim ignores funding rates | 🟡 Optimistic results |
| 24 | MEDIUM | No candle quality validation | 🟡 Corruption risk |
| 25 | LOW | Scanner coin universe hardcoded | 🟡 Operational friction |

**Next phase**: Phase 4 — Portfolio Management & Trade Execution (V14DCAEngine, capital allocation, grid management, TP/SL, liquidation handling).
