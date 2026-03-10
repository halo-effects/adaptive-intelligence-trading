# V14 PM System — Complete End-to-End Audit
**Date**: 2026-03-10
**Auditor**: OpenClaw AI
**Scope**: Every file in the V14PM dependency chain, from scheduled task to exchange API call

---

## 1. System Architecture (Verified)

```
Scheduled Tasks (Windows)
  ├── V14PMPaperBot (logon)    → run_v14_portfolio_paper.py
  ├── AIT_CandleCollector (1h) → collect_scanner_candles.py → resample_daily.py
  ├── V14CycleScanner (daily)  → v14_cycle_scanner.py
  └── AIT_DashboardSync (10m)  → sync_dashboard.ps1

Python Module Dependency Tree:
  run_v14_portfolio_paper.py (Runner)
    ├── v14_lifecycle_engine.py (Lifecycle Wrapper)
    │   ├── engine/v14_dca_engine.py (Core DCA Engine)
    │   │   ├── engine/v13_signals.py (V13SignalPack — indicators & signals)
    │   │   ├── engine/v13_router_engine_v1.py (Fib levels, swing detection)
    │   │   ├── engine/v13_router_engine_v2.py (HybridDetector2D — top/bottom)
    │   │   │   └── engine/_steve_3check.py (Steve's 3-Check bottom detector)
    │   │   └── engine/test_hvf_daily.py (HVF composite scoring)
    │   └── engine/v13_signals.py (signal refresh on daily boundary)
    ├── v14_capital_manager.py (CapitalRouter — allocation/tier management)
    ├── cfgi_client.py (CFGI.io fear & greed API)
    └── incident_schema.py (loss incident reports)

Data Pipeline:
  Hyperliquid (exchange)
    → collect_scanner_candles.py (1h candles → candles table)
    → resample_daily.py (1h → candles_daily table) [NEW — was missing]
    → v14_cycle_scanner.py (daily scores → cycle_scanner.json)
    → CapitalRouter (reads cycle_scanner.json → allocations)
    → V14LifecycleEngine (reads candles_daily via V13SignalPack)
```

---

## 2. Bugs Found & Fixed (This Audit)

### 2.1 CRITICAL: v13_router_engine_v2.py — Wrong DB Path
- **File**: `engine/v13_router_engine_v2.py` line 47
- **Bug**: `Path(__file__).resolve().parent.parent.parent / 'data' / 'candles.db'` resolved to `trading/data/candles.db` (0 bytes) instead of `trading/spot/data/candles.db` (214 MB)
- **Impact**: `HybridDetector2D` — which computes 2D RSI divergence dates and 3D death cross — was reading from an empty database. This means:
  - `compute_2d_divergence_dates()` always returned empty set → top detection OB93 always timed out (35d) instead of detecting actual divergences
  - `_compute_2d_death_cross()` returned None → bottom conviction gate 1 (3D death cross) always failed → no conviction-based bottoms were ever detected
  - The ONLY working phase transitions were: early warning (1W K<97), OB85 fallback, failsafe (1W K<50), and markdown failure (25% rise against shorts)
- **Fix**: Changed `.parent.parent.parent` → `.parent.parent` (same fix pattern as `_steve_3check.py` from March 9)
- **Severity**: Critical — fundamentally broken top/bottom detection for the entire system, not just PM

### 2.2 CRITICAL: Missing Daily Candle Resampling Pipeline
- **Bug**: `collect_scanner_candles.py` writes 1h candles to the `candles` table. `V13SignalPack.load_daily()` reads from `candles_daily`. There was NO code to resample 1h → daily.
- **Impact**: 19 of 45 scanner coins (COMP, DYDX, EIGEN, ENA, ENS, HBAR, KAS, LDO, MKR, ONDO, OP, PENDLE, PYTH, RENDER, SNX, STX, TIA, W, ZRO) had zero daily candles. The PM bot ran engines for these coins but with no signal pack — they were essentially blind DCA grids with no phase transitions.
- **Fix**: Created `resample_daily.py`, wired into hourly pipeline as Step 1.5. First run inserted 24,995 daily candles for 24 symbols.
- **Severity**: Critical — 42% of the coin universe had no signal data

### 2.3 CRITICAL: No Engine State Persistence (Root Cause of Phantom Trades)
- **Bug**: `V14LifecycleEngine` has `snapshot_state()` and `restore_state()` methods, but the PM runner never called them. Every restart created blank engines that replayed 200 candles of history, generating phantom trades.
- **Fix**: Added `_save_state()` (every 60s) and `_load_state()` (on startup) to the PM runner. State includes: all engine snapshots, router pool cash/allocations, open deals, last candle timestamps, approved symbols.
- **Severity**: Critical — caused 41+ phantom trades and corrupted equity reporting

### 2.4 HIGH: Bare Engine Fallback for State Restore
- **Bug**: When `_load_state()` created a new `V14LifecycleEngine` and the signal pack failed to load (e.g., "No daily data for ZRO"), `self._engine` was set to None. `restore_state()` returned early, and the entire restore loop crashed.
- **Fix**: Added bare engine creation fallback in `restore_state()` — creates a `V14DCAEngine.__new__()` with minimal state, allowing position/phase data to be restored. Signals refresh on the next daily boundary tick.
- **Severity**: High — a single coin's missing data could crash the entire bot's state restore

### 2.5 LOW: Duplicate V14-PM Block in sync_dashboard.ps1
- **Bug**: The V14-PM copy block (status.json + trades.csv) was duplicated at lines 80-91 and 92-103.
- **Impact**: Harmless (copies same files twice per sync cycle), but indicates copy-paste sloppiness.
- **Fix**: Removed duplicate block.

---

## 3. DB Path Consistency Audit

All files in `trading/spot/engine/` use `Path(__file__).resolve().parent.parent / 'data' / 'candles.db'` which correctly resolves to `trading/spot/data/candles.db` (214 MB).

| File | DB Path Expression | Resolves To | Status |
|------|-------------------|-------------|--------|
| v13_signals.py | `.parent.parent / 'data'` | trading/spot/data/candles.db | ✅ Correct |
| _steve_3check.py | `.parent.parent / 'data'` | trading/spot/data/candles.db | ✅ Correct (fixed Mar 9) |
| v14_dca_engine.py | `.parent.parent / 'data'` | trading/spot/data/candles.db | ✅ Correct |
| v13_router_engine_v2.py | `.parent.parent / 'data'` | trading/spot/data/candles.db | ✅ Fixed today (was .parent.parent.parent) |
| build_daily_candles.py | `.parent.parent / 'data'` | trading/spot/data/candles.db | ✅ Correct |
| test_hvf_daily.py | `.parent.parent / 'data'` | trading/spot/data/candles.db | ✅ Correct |
| run_v14_portfolio_paper.py | `_WORKSPACE / 'trading' / 'spot' / 'data'` | trading/spot/data/candles.db | ✅ Correct |
| collect_scanner_candles.py | `Path(__file__).parent / 'data'` | trading/spot/data/candles.db | ✅ Correct |
| resample_daily.py | `Path(__file__).resolve().parent / 'data'` | trading/spot/data/candles.db | ✅ Correct |

**Note**: `trading/data/candles.db` (0 bytes) should be deleted — it's a trap that masks path errors.

---

## 4. Data Pipeline Audit

### 4.1 Candle Collection (Hourly)
- **Script**: `collect_scanner_candles.py`
- **Source**: Hyperliquid perps (ccxt)
- **Target**: `candles` table, 1h timeframe
- **Coins**: 46 symbols (45 + USDC variants)
- **Lookback**: 2 years on first pull, incremental after
- **Rate limiting**: 0.5s between pages, 0.8s between coins, retry on 429
- **Status**: ✅ Working correctly

### 4.2 Daily Resampling (Hourly, after candle collection)
- **Script**: `resample_daily.py` [NEW]
- **Source**: `candles` table (1h)
- **Target**: `candles_daily` table
- **Logic**: Floor timestamp to midnight UTC, OHLCV aggregation, INSERT OR IGNORE
- **Status**: ✅ Working — 24,995 candles inserted on first run

### 4.3 DCA Cycle Scanner (Daily 6 AM PST + hourly after candle collection)
- **Script**: `v14_cycle_scanner.py`
- **Output**: `docs/data/v14/cycle_scanner.json`
- **Logic**: Runs V14DCAEngine backtest per coin, scores by DCA Cycle Velocity
- **Trend Scores**: Enriched with `trend_multiplier` and `trend_direction` per coin
- **Status**: ✅ Working

### 4.4 Dashboard Sync (Every 10 min)
- **Script**: `sync_dashboard.ps1`
- **Target**: GitHub Pages (halo-effects/adaptive-intelligence-trading)
- **Recovery**: Pull --rebase on divergence, nuke on failure
- **Status**: ✅ Working (divergence recovery added, duplicate PM block removed)

---

## 5. Engine Logic Audit

### 5.1 V14DCAEngine (Core)
- **Phase machine**: LONG_DCA → SHORT_DCA → ROUTER → LONG_DCA (correct)
- **DCA grid**: BO + SO layers with deviation scaling, TP at 1.5%
- **Fee model**: Maker 0.02% (DCA entries, TPs), Taker 0.05% (emergency/phase closes)
- **Liquidation**: Checked every tick, only when leverage > 1.0 (PM runs 1.0x — no liquidation risk)
- **Top detection**: OB93 arm → 2D divergence confirm (35d timeout) — **NOW WORKING** with DB path fix
- **Bottom detection**: 3D death cross + 2W StochRSI exhaustion + conviction ≥3/4 — **NOW WORKING** with DB path fix
- **Unwinding**: Early warning or OB93 stops new DCA entries, lets existing TPs hit
- **Status**: ✅ Correct after DB path fix

### 5.2 V14LifecycleEngine (Wrapper)
- **Live mode**: Accumulates 1h candles, triggers daily signal eval at midnight UTC
- **Hourly ticks**: DCA grid only (TP responsiveness between daily boundaries)
- **Warmup**: New engines wait for first daily boundary before trading (router sets direction)
- **Signal refresh**: V13SignalPack re-created on each daily boundary (fresh indicators)
- **State persistence**: `snapshot_state()` / `restore_state()` — comprehensive (phase, positions, top/bottom state, cycle tracking)
- **Bare engine fallback**: If signal pack fails during restore, creates minimal engine and restores position state
- **Orphaned position handling**: If long phase has leftover shorts, runs short TP check with `unwinding=True` (close-only, no new layers)
- **Status**: ✅ Correct

### 5.3 CapitalRouter
- **Pool split**: 75% active, 25% reserve
- **Tier system**: Equity-based coin caps ($50K+ = 10 coins)
- **Hurdle rate**: DCA Score ≥ 5.0 required
- **Trend multiplier**: `Adjusted Score = Base DCA Score × Trend Multiplier` — gates entry capital
- **Risk cap**: Max 20% of active pool per coin
- **State persistence**: Pool cash, allocations saved/restored with engine state
- **Status**: ✅ Correct

### 5.4 TradeTracker
- **CSV persistence**: `trades.csv` is source of truth across restarts
- **Dedup**: `_existing_keys` set prevents duplicate trades (symbol|open_time|close_time)
- **Forensic**: `recorded_at` field on every trade (wall-clock UTC when trade was recorded)
- **Phantom detection**: `recorded_at >> close_time` gap identifies replay-generated trades
- **Status**: ✅ Correct

---

## 6. Configuration Audit

### 6.1 PM Bot Scheduled Task
```
Task: V14PMPaperBot (logon trigger)
Exe: python.exe -u -m trading.spot.run_v14_portfolio_paper --capital 50000 --profile high --leverage 1.0
WorkDir: C:\Users\Never\.openclaw\workspace
```
- `--fresh` removed (state persistence handles restarts)
- `--fresh` still available for genuinely new account setup
- **Status**: ✅ Correct

### 6.2 Risk Profile (High)
| Parameter | Value | Locked |
|-----------|-------|--------|
| Leverage | 1.0x (overridden from profile's 1.5x) | ✅ |
| DCA_BO_PCT | 40% | ✅ |
| DCA_SO_DEVIATION | 1.5% | ✅ |
| DCA_SO_MULTIPLIER | 1.5x | ✅ |
| DCA_MAX_LAYERS | 12 | ✅ |
| DCA_TP_PCT | 1.5% | ✅ |
| DCA_ACCUMULATE | False (cycling mode) | ✅ |
| DCA_CAPITAL_PCT | 90% | ✅ |
| CONVICTION_MIN_SCORE | 3 | ✅ |
| TOP_DIVERGENCE_TIMEOUT | 35d | ✅ |

### 6.3 Fee Structure (Hyperliquid)
| Type | Rate | Usage |
|------|------|-------|
| Maker | 0.02% | DCA entries, TP closes |
| Taker | 0.05% | Emergency/phase closes, liquidations |

### 6.4 Capital
- Starting capital: $50,000
- Active pool: $37,500 (75%)
- Reserve pool: $12,500 (25%)
- Per-coin cap: $7,500 (20% of active pool)
- Coin slots: 10 (equity tier for $50K+)

---

## 7. Remaining Issues & Recommendations

### 7.1 Delete Empty DB Trap (RECOMMENDED)
`trading/data/candles.db` (0 bytes) should be deleted. It's a path resolution trap — any file that accidentally resolves to 3 parent levels will silently read from an empty database instead of failing loudly. This has caused TWO bugs already (`_steve_3check.py` on March 9, `v13_router_engine_v2.py` today).

### 7.2 Centralize DB Path (RECOMMENDED)
Six files independently define `DB_PATH` with varying `Path(__file__).parent` chains. This should be a single import:
```python
# trading/spot/config.py
DB_PATH = Path(__file__).resolve().parent / 'data' / 'candles.db'
```
All files import from there. Eliminates path resolution bugs entirely.

### 7.3 CSV Realized PnL Override Direction (LOW)
`_write_status()` line: `if csv_realized > total_realized` — only overrides in one direction. If engines somehow report MORE realized PnL than CSV (which shouldn't happen, but edge case during backfill or state corruption), the CSV value gets ignored. Should probably always prefer CSV as source of truth:
```python
total_realized = csv_realized  # CSV is always the source of truth
```

### 7.4 Router `return_capital()` No Bounds Check (LOW)
`CapitalRouter.return_capital()` adds proceeds to `active_pool_cash` without checking if it would exceed `active_pool_total`. In theory, profitable trades could inflate the pool beyond 75% of equity. Not harmful (more capital available is good), but the accounting drifts from the 75/25 model over time. The daily rebalance with `current_equity` partially corrects this.

### 7.5 Correlation Gate (DEFERRED)
Halt new entries when >60% of coins are at L4+. Not yet implemented. Would reduce concentrated drawdown risk.

### 7.6 V13SignalPack Rename (DEFERRED)
Rename to `SignalPack` — too many importers to change while bots are running.

### 7.7 `generate_daily_equity.py` (UNAUDITED)
Called by `sync_dashboard.ps1` to produce `daily_equity.json`. Not in the critical path for PM trading, but included in the sync pipeline. Not read during this audit.

---

## 8. Fresh Install Procedure (Verified)

For a brand new PM deployment:

1. Ensure `candles.db` has data:
   - Run `collect_scanner_candles.py` (populates `candles` table with 1h data)
   - Run `resample_daily.py` (creates `candles_daily` from 1h data)
   - Run `v14_cycle_scanner.py` (creates `cycle_scanner.json`)

2. Start the bot with `--fresh`:
   ```
   python -u -m trading.spot.run_v14_portfolio_paper --capital 50000 --profile high --leverage 1.0 --fresh
   ```
   - `--fresh` skips historical candle replay — engines start trading from NOW only
   - First cycle: engines enter positions based on current market conditions
   - After 60 seconds: `engine_state.json` is saved

3. All subsequent restarts:
   ```
   python -u -m trading.spot.run_v14_portfolio_paper --capital 50000 --profile high --leverage 1.0
   ```
   - No `--fresh` needed — state persistence handles everything
   - Engines restore from `engine_state.json` with all positions, phases, indicators
   - Candle processing resumes from last processed timestamp

---

## 9. Files Modified During This Audit

| File | Change |
|------|--------|
| `run_v14_portfolio_paper.py` | Added `_save_state()`, `_load_state()`, wired into main loop and startup |
| `v14_lifecycle_engine.py` | Added bare engine fallback in `restore_state()` |
| `engine/v13_router_engine_v2.py` | Fixed DB path: `.parent.parent.parent` → `.parent.parent` |
| `resample_daily.py` | **New file** — 1h → daily candle resampling |
| `run_candle_collector.ps1` | Added Step 1.5 (daily resample) |
| `sync_dashboard.ps1` | Removed duplicate V14-PM block |

---

## 10. Verification

After all fixes:
- PM bot restarted 4 times without `--fresh` → zero phantom trades each time
- All 10 engines restore with full signal packs (zero bare engines)
- Equity: $50,503.92 (consistent across all restarts)
- 22 verified trades (unchanged across restarts)
- Top/bottom detection now has correct 2D divergence and 3D death cross data
- 19 previously-blind coins now have daily candle data for signal computation

---

## 11. Post-Audit Fixes (2026-03-10, same day)

### 11.1 Problem: Engine Counter Drift Across All Bots

The audit fixed V14PM state persistence and phantom trades, but a broader issue was
discovered: **all four bot runners** reported equity and realized PnL from engine
internal counters, not from the CSV trade ledger.

**Impact:** V14 Paper reported $65K realized when the CSV showed $44K. V14-ETF showed
$8K equity (should have been $10.8K). Engine counters drift on restart because
`restore_state()` doesn't perfectly preserve cumulative PnL.

### 11.2 Fix: CSV-as-Truth for All Runners

Changed `_write_status()` in all four runners to always use `trades.csv` as the
source of realized PnL and recompute equity from ground truth:

```
equity = capital + csv_realized_pnl - fees + unrealized_pnl
```

**Files modified:**
- `run_v14_paper.py` — added CSV realized PnL + equity recompute
- `run_v14etf_paper.py` — same
- `run_v14_portfolio_paper.py` — changed conditional (`if csv > engine`) to unconditional
- `run_v14_live_aster.py` — added full CSV truth block (had none)

### 11.3 Fix: Live Bot Equity from Exchange API

The V14 Live bot (Aster) now computes equity from actual exchange balances:
```
equity = usdt_total + base_total × current_price
```
This accounts for positions the engine doesn't know about (e.g., after `--fresh`
restart where old positions still exist on the exchange).

### 11.4 Fix: `--fresh` Loads Existing Trades

The `--fresh` startup path in V14-ETF and Live Aster did not call
`tracker.load_existing()`. This meant the TradeTracker had 0 trades in memory,
and the next `save_csv()` call would overwrite the CSV with an empty file,
destroying trade history.

**Fixed in:** `run_v14etf_paper.py`, `run_v14_live_aster.py`
(V14PM already had this correct.)

### 11.5 Dashboard Daily ROI Fix

All 4 dashboard HTML files calculated "Avg Daily ROI" using `trades[0].open_time`
(first CSV row), assuming the CSV was sorted by date. It wasn't — unsorted CSVs
and a corrupt trade (deal_id 27 in V14-ETF, with close_time before open_time from
a brief candle replay) caused daily ROI to equal total ROI, producing absurd
projections ($306 quadrillion/year). Fixed by scanning all trades for the true
earliest open_time and latest close_time. Corrupt trade removed from CSV.

### 11.6 Verification

After all post-audit fixes:
- V14 Paper: $49,988 equity, $44,461 realized (matches CSV), 380 deals
- V14-ETF: $10,834 equity, $834 realized (matches CSV), 24 deals — was showing $8K/$0
- V14PM: $50,627 equity, $608 realized (matches CSV), 30 deals
- V14 Live Aster: $314 equity (matches exchange balance), $1.56 realized, 1 deal
- All CSVs verified intact after multiple restarts with `--fresh`
