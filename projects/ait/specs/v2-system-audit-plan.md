# V2 System Audit Plan — Pre-Migration Full Verification

**Status**: PLAN — awaiting approval  
**Date**: 2026-05-10  
**Auditor**: OpenClaw AI (direct, no sub-agents)  
**Scope**: Complete system — 25,087 lines across 38 production files  
**Goal**: Complete system mapping before Hyperliquid migration. Zero gaps.

---

## Why Another Audit

The March 10 audit (v1) operated at the **module level** — it verified architecture and
data flow and found critical bugs. But since then, 12 specs of fixes have been deployed
for bugs that v1 should have caught:

| Post-Audit Bug | What v1 Missed |
|----------------|----------------|
| Stale allocations accumulate forever | Didn't trace allocation lifecycle end-to-end |
| T1 gate circular dependency | Didn't test new-coin promotion path |
| Phantom positions in status.json | Didn't verify status.json vs exchange truth |
| Deposit detection creates phantom transactions | Didn't trace the capital formula |
| Reconciliation creates phantom trades | Tested TradeTracker in isolation, not under churn |
| Candle replay causes 113 spread-reject trades | Didn't test restart behavior |
| Data sync cron overwrites source files | Didn't audit infrastructure scripts |
| Exchange sync only zeros long fields | Verified happy path only |

**Pattern**: v1 verified "does this component work?" It did not verify "do these
components work together over time, across restarts, under failure conditions?"

**v2 verifies the system as a system, not as a collection of parts.**

---

## Audit Methodology

### Approach: Full System Mapping

The system has 7 functional domains. v2 audits each domain end-to-end, then audits
the integrations between them. For each domain:

1. **Map every variable**: inputs, outputs, state, persistence
2. **Trace every path**: happy path, error path, restart path, edge cases
3. **Verify against production**: compare code to actual live behavior
4. **Tag migration impact**: what changes for Hyperliquid

### Evidence Standard

Every finding includes:
- **Code location** (file + line numbers)
- **Expected vs actual behavior**
- **Severity**: CRITICAL / HIGH / MEDIUM / LOW / NOTE
- **Migration impact**: none / must-fix / must-change

### Ground Rules

1. I read every line. No skimming.
2. Code is truth. If docs say X but code does Y, code wins.
3. Production evidence where possible — actual logs, actual status.json, actual exchange state.
4. No sub-agents. Full context maintained across all phases.
5. Critical findings flagged immediately between phases.
6. No fixes during audit (except active money-loss emergencies). Findings first, fixes with specs after.

---

## System Domains

```
┌──────────────────────────────────────────────────────────────────┐
│                    COMPLETE SYSTEM MAP                           │
│                                                                  │
│  ┌─────────────┐   ┌──────────────┐   ┌──────────────────┐     │
│  │ 1. DATA     │──▶│ 2. INTEL     │──▶│ 3. COIN          │     │
│  │ PIPELINE    │   │ LAYER        │   │ SELECTION &      │     │
│  │             │   │              │   │ SCORING          │     │
│  │ Candle      │   │ Signal Stack │   │                  │     │
│  │ collection, │   │ (StochRSI,   │   │ Cycle scanner,   │     │
│  │ resampling, │   │ BMSB, CFGI,  │   │ hurdle rate,     │     │
│  │ DB mgmt     │   │ Router v2,   │   │ trend multiplier │     │
│  │             │   │ Steve 3chk)  │   │ ranking          │     │
│  └─────────────┘   └──────┬───────┘   └────────┬─────────┘     │
│                           │                     │                │
│                           ▼                     ▼                │
│  ┌──────────────────────────────────────────────────────┐       │
│  │         4. PORTFOLIO MANAGEMENT                       │       │
│  │                                                       │       │
│  │  Capital allocation, tier system, pool split,         │       │
│  │  rebalance, coin promotion/demotion, T1 gate,         │       │
│  │  liquidity filter, regime system (global + per-coin)  │       │
│  └────────────────────────┬──────────────────────────────┘       │
│                           │                                      │
│                           ▼                                      │
│  ┌────────────────────────────────────────────────────┐         │
│  │           5. TRADE EXECUTION ENGINE                 │         │
│  │                                                     │         │
│  │  V14 DCA engine (phase machine, grid, TP),          │         │
│  │  lifecycle wrapper, order placement, exchange sync,  │         │
│  │  bot-side trailing TP, trade recording               │         │
│  └───────────────────────┬─────────────────────────────┘         │
│                          │                                       │
│             ┌────────────┼────────────┐                          │
│             ▼            ▼            ▼                          │
│  ┌──────────────┐ ┌──────────┐ ┌──────────────┐                │
│  │ 6. STATE &   │ │ 7. PRES- │ │ INFRA-       │                │
│  │ PERSISTENCE  │ │ ENTATION │ │ STRUCTURE    │                │
│  │              │ │          │ │              │                │
│  │ state.json,  │ │ 7 dash-  │ │ Scheduled    │                │
│  │ trades.csv,  │ │ boards,  │ │ tasks, cron, │                │
│  │ status.json, │ │ GitHub   │ │ sync scripts,│                │
│  │ engine_state │ │ Pages    │ │ Telegram,    │                │
│  │ score_history│ │ deploy   │ │ watchdog     │                │
│  └──────────────┘ └──────────┘ └──────────────┘                │
└──────────────────────────────────────────────────────────────────┘
```

---

## Phase 1: Data Pipeline
**How raw market data enters the system and becomes usable intelligence.**

### Files
| File | Lines | Role |
|------|-------|------|
| `collect_scanner_candles.py` | 235 | 1h candle collection from exchange |
| `resample_daily.py` | 117 | 1h → daily aggregation |
| `daily_collector.py` | 301 | Alternative/legacy collector |
| `run_daily_collector.py` | 39 | Runner for daily collector |
| `run_candle_collector.ps1` | 59 | Pipeline orchestration script |
| `backfill_scanner_coins.py` | 203 | Historical backfill |
| `backfill_etf_candles.py` | 173 | ETF coin backfill |
| `engine/build_daily_candles.py` | 168 | Legacy daily builder |
| `cfgi_client.py` | 223 | Fear & Greed Index API client |
| `candles.db` | (515 MB) | Central candle database |

### Audit Checklist
- [ ] **Candle collection**: Exchange connection, coin universe (all 45+), incremental fetch logic, rate limiting, retry on failure
- [ ] **Data integrity**: Are 1h candles ever missing? Duplicated? Out of order? How would we know?
- [ ] **Resampling**: OHLCV aggregation correctness. Partial day handling (today's candle is incomplete until midnight). Timezone (UTC midnight vs other)
- [ ] **Database schema**: Table definitions, indexes, INSERT OR REPLACE vs INSERT OR IGNORE behavior. What happens with duplicate timestamps?
- [ ] **Coin universe management**: How are new coins added to the collection set? How are delisted coins handled? Is the DB list vs the scanner list vs the engine list consistent?
- [ ] **CFGI client**: API endpoint, response parsing, caching/freshness, fallback behavior when API is down. How stale can CFGI data be before it affects decisions?
- [ ] **Pipeline orchestration**: `run_candle_collector.ps1` step ordering (collect → resample → scan). Error propagation between steps. What happens if step 1 fails — do steps 2-3 still run on stale data?
- [ ] **Legacy files**: Are `daily_collector.py`, `run_daily_collector.py`, `build_daily_candles.py` still used? Dead code?
- [ ] **Backfill scripts**: When are they used? Do they produce data compatible with the live pipeline?
- [ ] **DB path consistency**: Re-verify all references resolve to the 515 MB file (v1 found 2 bugs here)

### Key Questions
- If a coin's candle data has a 24h gap, what happens downstream?
- If `resample_daily.py` crashes, does the scanner use stale daily data?
- Can we verify data freshness programmatically?

---

## Phase 2: Intelligence Layer (Signal Stack)
**How raw data becomes trading signals that drive phase transitions.**

### Files
| File | Lines | Role |
|------|-------|------|
| `engine/v13_signals.py` | 509 | V13SignalPack — all signal classes |
| `engine/v13_router_engine_v2.py` | 522 | ROUTER v2 — HybridDetector2D, phase transitions |
| `engine/v13_router_engine_v1.py` | 887 | ROUTER v1 — Fib levels, swing detection |
| `engine/_steve_3check.py` | 226 | Steve's 3-Check bottom detector |
| `engine/test_hvf_daily.py` | 275 | HVF composite scoring |
| `engine/v13_phase_backtest_v8.py` | 880 | Phase backtest harness |

### Audit Checklist

#### Signal Pack (`v13_signals.py`)
- [ ] `V13SignalPack.__init__()`: What loads, what can fail, graceful degradation
- [ ] `load_daily()`: SQL query correctness, multi-pair symbol resolution (e.g., HYPE/USDT vs HYPE/USDC), dedup strategy
- [ ] `load_cfgi()`: Same analysis, missing data handling
- [ ] **StochRSI (1W/2W/3W)**: Resampling logic, K/D/RSI computation, lookback windows, edge cases with < N weeks of data
- [ ] **StochRSI Divergence**: Bullish/bearish detection algorithm, lookback tuning, false positive rate
- [ ] **Bull Market Support Band (BMSB)**: SMA/EMA computation, crossover detection, "below band" test
- [ ] **DailyStructure**: SMA50 slope calculation, window parameter, what "positive" vs "negative" means precisely
- [ ] **CFGI Signal**: Threshold logic (greed→decline, fear→rise), lookback windows
- [ ] **SMA200 Overextension**: What constitutes overextended? Threshold values.
- [ ] For EVERY signal: What data does it need? How many days of history minimum? What happens with insufficient data? What's the output format?

#### ROUTER v2 — Phase Transitions (`v13_router_engine_v2.py`)
- [ ] `HybridDetector2D`: Full constructor logic, what DB it reads, what it precomputes
- [ ] **2D RSI divergence dates**: How computed, cached or live, freshness guarantee
- [ ] **3D death cross detection**: Algorithm, thresholds, what "3D" means precisely
- [ ] **Top detection pipeline**: OB93 arm → 2D divergence confirm (35d timeout) → phase transition. Every condition, every fallback.
- [ ] **Bottom detection pipeline**: 3D death cross + 2W StochRSI exhaustion + conviction ≥ 3/4. Complete truth table.
- [ ] **Early warning**: What triggers it, what it blocks (unwinding mode)
- [ ] **OB85 fallback**: When OB93 doesn't arm, what happens?
- [ ] **Failsafe**: 1W K < 50 override — when does it fire, what does it do?
- [ ] **Markdown failure**: 25% rise against shorts — recovery path
- [ ] DB path verification (v1 found the critical bug here)

#### Steve 3-Check (`_steve_3check.py`)
- [ ] Complete algorithm: what 3 checks, what thresholds, how they combine
- [ ] Data dependencies: what tables it reads, DB path resolution
- [ ] Integration point: how does it feed into bottom detection?

#### ROUTER v1 (`v13_router_engine_v1.py`)
- [ ] Is this still used in production? Or only v2?
- [ ] Fib level computation, swing detection logic
- [ ] If used: full audit. If not: document as legacy and verify no code paths reference it.

#### Phase Backtest (`v13_phase_backtest_v8.py`)
- [ ] Is this used in production or only for offline analysis?
- [ ] Does the backtest harness match the live engine's behavior? (Divergence = silent bug factory)

#### HVF Daily (`test_hvf_daily.py`)
- [ ] What is HVF? Is it active in production?
- [ ] Composite scoring logic and integration points

### Key Questions
- For each signal type, what's the minimum history required for a valid signal?
- Can any signal return NaN/None? If so, what happens downstream?
- Are the signal parameters (thresholds, windows) hardcoded or configurable?
- Does the signal stack produce different results for the same data on different runs? (Determinism)
- v1 found the DB path bug in router v2. Are there similar silent-failure modes in any signal class?

---

## Phase 3: Coin Selection & Scoring
**How the system decides which coins to trade and how much to allocate.**

### Files
| File | Lines | Role |
|------|-------|------|
| `v14_cycle_scanner.py` | 728 | DCA Cycle Velocity scoring |
| `coin_scanner.py` | 465 | Legacy/alternative scanner |
| `data/score_history.json` | (211 KB) | Historical score tracking |
| `docs/data/v14/cycle_scanner.json` | (output) | Current scanner rankings |

### Audit Checklist

#### DCA Cycle Scanner (`v14_cycle_scanner.py`)
- [ ] **Coin universe definition**: Where is the list of 45 coins defined? How does a coin get added/removed?
- [ ] **Per-coin backtest**: What parameters (capital, profile, fee model)? Are they identical to the live bot's parameters?
- [ ] **DCA Cycle Velocity Score formula**: `Realized_PnL × (1 - MaxDD%) × Capital_Freedom / 100` — verify implementation matches spec
- [ ] **Trend multiplier calculation**: Score history lookback window, smoothing, direction classification logic (`accelerating` / `decelerating` / `stable`). Range [0.30, 1.50].
- [ ] **Trend direction thresholds**: What slope = accelerating? What = decelerating? Is there hysteresis?
- [ ] **Score history management**: How `score_history.json` accumulates over time. Does it grow unbounded? Pruning?
- [ ] **30-day vs 60-day vs 90-day windows**: Which window does the scanner use? Is it configurable? Has it been validated?
- [ ] **Output format**: Does `cycle_scanner.json` contain every field that `rebalance_daily()` expects? Field name consistency.
- [ ] **Backtest fee model**: Does the scanner's internal backtest use the same fee rates as the live bot (maker 0.02%, taker 0.05%)?
- [ ] **Execution time**: How long does a full scan take? Could it affect data freshness?

#### Score History & Trend
- [ ] How does the trend multiplier interact with the base DCA score? (Multiplicative vs additive)
- [ ] Can the trend multiplier completely suppress a coin's allocation? (Yes, if mult → 0.30 and score is low)
- [ ] How quickly does the trend multiplier react to a coin's performance change?
- [ ] Is the trend multiplier symmetric? (Rewards acceleration and penalizes deceleration equally?)

#### Legacy Scanner (`coin_scanner.py`)
- [ ] Is this still used anywhere in production? If not, document as legacy.

### Key Questions
- If the scanner runs on stale data (old candles), does it produce misleading scores?
- Are the scanner's backtest parameters version-locked to match the live engine?
- Could a coin score #1 in the scanner but be terrible for live trading? (Backtest overfitting)
- What happens if `cycle_scanner.json` is empty or corrupt?

---

## Phase 4: Portfolio Management & Capital Allocation
**How money gets divided across coins and how the portfolio adapts over time.**

### Files
| File | Lines | Role |
|------|-------|------|
| `v14_capital_manager.py` | 498 | CapitalRouter — pools, tiers, allocation |
| Runner rebalance code (in live runner) | ~120 | `_rebalance_daily()` integration |
| Runner regime code (in live runner) | ~300 | `_evaluate_regime()`, APPROVE/DENY |

### Audit Checklist

#### CapitalRouter (`v14_capital_manager.py`)
- [ ] **Pool architecture**: Active pool (90%) + Reserve pool (10%) — verify split calculation
- [ ] **Equity tier system**: Every tier boundary, coin cap per tier, the full EQUITY_TIER_CAPS table
- [ ] **Hysteresis**: 5% downgrade buffer — trace the `_apply_hysteresis()` logic completely. Test at boundary: $99.99, $100.01, $95.01
- [ ] **`rebalance_daily()` full trace**:
  - Hurdle rate filter (≥ 5.0)
  - Trend multiplier application
  - Sort by adjusted score
  - Tier coin cap enforcement
  - Proportional weighting formula
  - Dynamic risk cap: `cap_pct = min(1.0, 0.20 + (0.80 / max(len(top_coins), 1)))`
  - Sidelines cash calculation
  - Return value format
- [ ] **`request_capital()`**: Active vs reserve pool priority, partial grants, pool depletion edge
- [ ] **`return_capital()`**: Where returned capital goes, no bounds check (v1 noted this), accounting drift over time
- [ ] **State persistence**: What fields are saved/restored? What drifts? Pool cash after multiple restarts?

#### Rebalance Integration (in live runner)
- [ ] **Timing**: When does rebalance fire? Midnight UTC? What prevents double-fire? What if bot restarts at 23:59 and again at 00:01?
- [ ] **Scanner data loading**: File path, missing file handling, stale data detection
- [ ] **Regime-flagged exclusion**: Are flagged coins excluded from rebalance candidates correctly? What if ALL coins are flagged?
- [ ] **Liquidity filter**: Ticker fetch from exchange, volume threshold formula, exemption for open positions. What if ticker fetch fails?
- [ ] **Tier cap enforcement**: Active position count vs cap. Race condition: position opens between count and cap check?
- [ ] **New coin creation**: Full path: scanner target → CoinState → V14LifecycleEngine → signal pack → warmup → ready to trade
- [ ] **Existing coin update**: `allocated_capital` update, engine capital sync (only when no position)
- [ ] **Allocation seeding** (new): verify it unblocks T1 gate for newly promoted coins
- [ ] **Stale cleanup** (new): verify it removes dead allocations but preserves coins with positions
- [ ] **Exception handling**: What if rebalance throws mid-way? Is state consistent? Partial allocation?

#### Regime System (in live runner)
- [ ] **`_evaluate_regime()`**: What data it reads (scanner coins, signal state), when it runs (daily at REGIME_EVAL_HOUR)
- [ ] **Global regime state machine**: LONG_DCA ↔ SHORT_DCA. What triggers transitions? Only manual APPROVE?
- [ ] **Per-coin regime detection**: How does each engine's phase contribute to conviction count?
- [ ] **Graduated conviction calculation**: 7 thresholds (15/25/30/35/40/45/50%). Count formula: `flipped / total`. Edge cases: 0 coins, 1 coin flipped, all coins flipped.
- [ ] **APPROVE handler**: What changes (global regime), what's preserved (engine phases, open positions). Are there any race conditions with concurrent candle processing?
- [ ] **DENY handler**: What resets (conviction tracker). Can DENY be sent when no alert is pending?
- [ ] **Regime gate in candle loop**: Exactly which actions are blocked? Can TPs still fire on excluded coins? What about DCA add-on layers for existing positions?
- [ ] **Per-coin `regime_flagged` auto-unflag**: Trigger condition, timing, state consistency
- [ ] **Persistence**: `_global_regime` in state.json — verified on startup restore?

#### Coin Promotion/Demotion Lifecycle
- [ ] **Full lifecycle trace**: Scanner promotes coin → rebalance allocates → engine created → seeded in allocations → T1 gate open → first BUY → DCA layers → TP → coin demoted → engine preserved or removed → allocation cleaned
- [ ] **Demotion with open position**: What happens? Capital defended? Can it still DCA add-on? Can it still TP?
- [ ] **Demotion without position**: Immediately cleaned from allocations? Engine destroyed or kept?
- [ ] **Re-promotion**: Coin drops out then comes back in next scan. Fresh engine or restored?
- [ ] **T1 gate complete trace**: Where checked, what data it reads, every path through

### Key Questions
- Can the portfolio ever be 100% allocated with no sidelines cash? What happens to DCA layer 5+ if all capital is deployed?
- What happens if equity drops 50%? Does the tier cap reduce? Do coins get force-removed?
- If the regime flips, how long until the portfolio is fully repositioned? (Answer should be: never forcefully, only as trades naturally close)
- Can capital accounting drift over months? What's the reconciliation mechanism?

---

## Phase 5: Trade Execution Engine
**How buy/sell decisions become exchange orders and how positions are tracked.**

### Files
| File | Lines | Role |
|------|-------|------|
| `engine/v14_dca_engine.py` | 801 | Core DCA engine — phase machine, grid, TP |
| `v14_lifecycle_engine.py` | 759 | Live wrapper — candle processing, state persistence |
| `exchange_client.py` | 188 | CCXT exchange abstraction |
| Runner execution code (in live runner) | ~200 | `_execute_action()`, order placement |
| Runner exchange sync (in live runner) | ~100 | Position reconciliation with exchange |

### Audit Checklist

#### V14 DCA Engine (`v14_dca_engine.py`)
- [ ] **Phase machine**: Map every transition: LONG_DCA → SHORT_DCA → ROUTER → LONG_DCA. What triggers each? Are there impossible/missing transitions?
- [ ] **`_compute_signals()`**: What signals, what conditions, what output format
- [ ] **`_check_top_signals()`**: OB93 arm + divergence confirm. Timeout (35d). Fallback (OB85). Early warning. Complete truth table.
- [ ] **`_check_bottom_signals()`**: 3D death cross + conviction ≥ 3/4 + 2W StochRSI. Complete truth table.
- [ ] **`_long_dca_tick()`**: Entry conditions, layer calculation (BO → SO deviation × multiplier), TP price calc, fee application
- [ ] **`_short_dca_tick()`**: Mirror analysis
- [ ] **Unwinding mode**: What triggers, what blocks, what allows through. Re-entry conditions after unwinding.
- [ ] **`_check_markdown_exit()`**: 25% rise against shorts — exact formula and behavior
- [ ] **`_check_router()`**: How router signals translate to phase changes
- [ ] **Fee model verification**: Maker 0.02% for entries/TPs, Taker 0.05% for emergency closes. Correct for Aster? Correct for Hyperliquid?
- [ ] **Edge cases**: 0 coins position, max layers (12), TP at exact price, multiple signals on same tick

#### Lifecycle Wrapper (`v14_lifecycle_engine.py`)
- [ ] **`tick()`**: Full trace from candle → engine actions
- [ ] **Daily boundary detection**: Midnight UTC, how `_last_daily_date` works, timezone handling
- [ ] **Signal pack refresh**: What gets recomputed on daily boundary? What if refresh fails?
- [ ] **Hourly ticks between dailies**: Only DCA grid (entry/TP), no signal evaluation
- [ ] **`snapshot_state()` / `restore_state()`**: Field-by-field — every field persisted, every field restored, any fields missing?
- [ ] **Bare engine fallback**: When triggered, what's lost, when it self-heals
- [ ] **`_warmed_up` flag**: Every code path that checks it, every path that sets it. When forced True.
- [ ] **Orphaned position handling**: Long phase with leftover shorts (or vice versa)

#### Exchange Client (`exchange_client.py`)
- [ ] **CCXT initialization**: Exchange selection, sandbox detection, credential loading
- [ ] **Order creation**: Parameters, error handling, retry logic, what exceptions are thrown
- [ ] **Balance fetch**: Fields read, precision, what "total" vs "free" means per exchange
- [ ] **Position fetch**: Symbol mapping, long vs short, entry price, qty, unrealized PnL
- [ ] **Leverage management**: `ensure_leverage()` — when called, what if rejected
- [ ] **Aster quirks**: Symbol naming, USDT vs USDC, any exchange-specific workarounds
- [ ] **Hyperliquid differences**: Symbol format, order types, margin modes, position reporting, fee structure, API rate limits, WebSocket vs REST

#### Order Execution (in live runner)
- [ ] **`_execute_action()` BUY path**: Regime check → T1 gate → dedup guard → `request_capital()` → exchange order → CSV record
- [ ] **`_execute_action()` SELL/TP path**: Exchange order → `return_capital()` → CSV record → stale coin prune
- [ ] **Exchange-truth trade recording**: Entry price from DEX, not engine. Verify implementation.
- [ ] **Bot-side trailing TP**: Implementation trace — how trailing is tracked, when TP executes, what happens if price reverses
- [ ] **Bot-side TP race fix**: The specific race condition and the fix. Verify fix is in place.
- [ ] **Order failure handling**: Insufficient balance, price moved, rate limit, exchange error. What recovers? What's lost?
- [ ] **Order dedup**: 30s window — is this sufficient? Too aggressive?

#### Exchange Sync (in live runner)
- [ ] **Position fields synced**: Every field from exchange → engine state
- [ ] **No-position handling**: Zeros all fields (long AND short) — verify completeness
- [ ] **Has-position but engine disagrees**: What happens? Which wins?
- [ ] **Position that exists on exchange but bot doesn't know about**: (e.g., manual trade, or after --fresh restart)
- [ ] **Leverage sync**: Timing, failure handling

### Key Questions
- If the exchange rejects an order, does the engine state still advance? (It shouldn't)
- Can a TP and a new DCA entry fire on the same candle? What's the ordering?
- What happens if the WebSocket drops mid-trade?
- Is there a maximum position size or order size enforced?
- What's the latency between signal and order placement?

---

## Phase 6: State & Persistence
**Every piece of persistent state, who writes it, who reads it, what can go wrong.**

### Files (state files, not code)
| File | Role | Writer | Reader |
|------|------|--------|--------|
| `live/v14pm/state.json` | Full bot state | Live runner (every 60s) | Live runner (startup) |
| `live/v14pm/status.json` | Dashboard data | Live runner (every tick) | Dashboard sync, health checks |
| `live/v14pm/trades.csv` | Trade ledger | Live runner (on trade) | Dashboard, equity calc |
| `live/v14pm/capital_ledger.json` | Deposit/withdrawal log | Manual commands | Capital calc |
| `data/score_history.json` | Scanner score tracking | Cycle scanner | Trend multiplier calc |
| `data/candles.db` | Candle database (515 MB) | Collector, resampler | Signal pack, scanner |
| `docs/data/v14/cycle_scanner.json` | Current scanner output | Cycle scanner | Rebalance |
| `docs/data/v14/daily_equity.json` | Equity timeseries | `generate_daily_equity.py` | Dashboard |

### Audit Checklist

#### State Consistency Matrix
For EVERY field in state.json, status.json, and trades.csv:
- [ ] What writes it?
- [ ] What reads it?
- [ ] What's the source of truth? (exchange, engine, CSV, computed?)
- [ ] What happens if the field is missing on startup?
- [ ] What happens if the value is corrupt (NaN, negative, wrong type)?
- [ ] Can two processes write simultaneously? (Dashboard sync + bot)

#### Restart Behavior Matrix
- [ ] **Normal restart** (kill → start, no flags): State loaded, positions preserved?
- [ ] **`--skip-backfill` restart**: Same, but skips historical candle catch-up?
- [ ] **`--fresh` restart**: Creates blank engines, loads existing CSV. What about open positions on exchange?
- [ ] **Crash restart** (no clean shutdown, no final state save): How much state is lost? (Up to 60s of unsaved state)
- [ ] **Restart after data sync cron**: Are any code files at risk of being overwritten?
- [ ] **Restart after manual state edit**: Bot reads edited state — any validation?
- [ ] **Double restart** (two instances): PID lock prevents this? Verify.

#### Numerical Precision
- [ ] Float vs Decimal: All capital accounting uses float. What's the cumulative drift over 1000 trades?
- [ ] Rounding: Where are values rounded? Fee calculations? Order sizing?
- [ ] Dust: After TP, is there ever a tiny position remainder? How is it handled?
- [ ] Minimum order sizes: Exchange-enforced? Bot-enforced? What happens below minimum?

### Key Questions
- After 6 months of operation, how much will capital accounting drift from reality?
- Can status.json be read in a partially-written state? (Dashboard sync reads while bot writes)
- Is trades.csv append-only in practice? Or can it be rewritten?

---

## Phase 7: Presentation Layer (Dashboards)
**Everything the user sees — accuracy of displayed data and correctness of dashboard logic.**

### Files
| File | Lines | Role |
|------|-------|------|
| `docs/dashboardV14PM.html` | 1,313 | PM dashboard (source) |
| `docs/d-984ae0d4ab9dc1a5.html` | 1,313 | PM dashboard (live/hashed) |
| `docs/dashboardV14.html` | 1,198 | V14 paper dashboard |
| `docs/index.html` | 847 | Landing page / overview |
| `docs/risk-profiles.html` | 2,097 | Risk profile documentation |
| `docs/pricing.html` | 764 | Pricing page |
| `docs/adaptive-intelligence.html` | 667 | Product page |
| `sync_dashboard.ps1` | 174 | GitHub Pages deployment |
| `generate_daily_equity.py` | 162 | Equity timeseries generator |
| `pm_comparison_log.py` | 137 | PM comparison data |

### Audit Checklist

#### PM Dashboard (`dashboardV14PM.html`)
- [ ] **Every data field**: Trace from display → JavaScript → status.json field. Verify accuracy.
- [ ] **Portfolio Allocation section**: Filter logic (invested > 0), allocation percentages, cash calculation
- [ ] **Performance metrics**: Equity, realized PnL, unrealized PnL, win rate, drawdown — calculation formulas in JS
- [ ] **Per-coin cards**: Phase, layers, invested, unrealized, TP price, entry price — all from status.json?
- [ ] **Regime panel**: Global direction badge, conviction bar, flip %, per-coin ACTIVE/EXCLUDED
- [ ] **Risk profile panel**: What it displays, where data comes from
- [ ] **Macro indicators**: Regime gate card, per-coin status tags
- [ ] **Time calculations**: "Avg Daily ROI", "Projected Annual" — are the formulas correct?
- [ ] **Refresh logic**: How often does the dashboard poll? Auto-refresh? Cache?

#### Other Dashboards
- [ ] **`dashboardV14.html`**: Same field audit for V14 paper bot. Are the JS calculations the same as PM?
- [ ] **`index.html`**: What data does the landing page show? Is it accurate?
- [ ] **`risk-profiles.html`**: Does it match the actual profiles in code?
- [ ] **`pricing.html`** and **`adaptive-intelligence.html`**: Content accuracy for commercial positioning

#### Dashboard Sync
- [ ] **`sync_dashboard.ps1`**: What files are synced? Are all required data files included?
- [ ] **GitHub Pages deployment**: .nojekyll presence, build rate limits, error recovery
- [ ] **`generate_daily_equity.py`**: Equity calculation formula, timezone handling, data source
- [ ] **`pm_comparison_log.py`**: What it generates, who consumes it

#### Sync as Live Dashboard
- [ ] **`d-984ae0d4ab9dc1a5.html`**: Is it always identical to `dashboardV14PM.html`? What keeps them in sync?
- [ ] If one is edited but not the other, how is this detected?

### Key Questions
- Does every number on the dashboard match what the bot actually reports?
- Are there any JavaScript calculations that differ from the Python calculations?
- Can the dashboard display stale data without the user knowing?
- Does the dashboard work correctly when the bot has 0 positions? 1 position? Max positions?

---

## Phase 8: Infrastructure & Operations
**Scheduled tasks, cron, monitoring, and the deployment pipeline.**

### Files
| File | Lines | Role |
|------|-------|------|
| `sync_dashboard.ps1` | 174 | Git-based dashboard deployment |
| `run_candle_collector.ps1` | 59 | Data pipeline orchestration |
| `openclaw_watchdog.ps1` | 88 | Process monitoring |
| OpenClaw cron jobs (`jobs.json`) | N/A | Scheduled automations |
| Windows Scheduled Tasks | N/A | System-level scheduling |

### Audit Checklist

#### Windows Scheduled Tasks
- [ ] **Enumerate every task**: Name, trigger, command, working directory, run-as user
- [ ] **V14PMPaperBot** task: still correct? Parameters match current requirements?
- [ ] **V14LiveAster** task: same audit
- [ ] **AIT_CandleCollector** task: hourly trigger, pipeline script, error handling
- [ ] **AIT_DashboardSync** task: 10-min trigger, what it syncs, rate limit compliance
- [ ] Any tasks that reference deleted/moved scripts?

#### Dashboard Sync Script (`sync_dashboard.ps1`)
- [ ] **Full trace**: What files are staged, committed, pushed
- [ ] **Exclusion logic**: Does it correctly exclude non-docs files? (v1 noted the data sync overwrote source files)
- [ ] **Error recovery**: Divergence handling, nuke-and-reclone path
- [ ] **Git operations**: Pull --rebase, conflict resolution, force-push scenarios
- [ ] **Rate limiting**: GitHub Pages build limit (10 builds/hour). Does the 10-min cron respect this?

#### Data Pipeline Script (`run_candle_collector.ps1`)
- [ ] **Step ordering**: Collect → resample → scan → score history. Dependencies between steps.
- [ ] **Error handling**: If one step fails, do subsequent steps run? Should they?
- [ ] **Timing**: Does the full pipeline complete within the scheduled window?

#### Watchdog (`openclaw_watchdog.ps1`)
- [ ] **What it monitors**: Which processes? What conditions trigger alerts?
- [ ] **Alert mechanism**: Telegram? Log file? Both?
- [ ] **False positive / false negative risk**: Could it miss a dead bot? Could it alert for a healthy one?

#### OpenClaw Cron Jobs
- [ ] **Read `jobs.json`**: List every active job, schedule, command
- [ ] **LLM health check** (ef85844d): What it checks, what it reports, regime gate included?
- [ ] **Disabled jobs**: Are any disabled jobs still referenced anywhere?
- [ ] **Nightly consolidation**: Does it run? Does it work? Where does output go?

#### Telegram Integration
- [ ] **Every Telegram command the bot accepts**: Map exhaustively from code
- [ ] **Command parsing**: What happens with malformed commands? Unrecognized commands?
- [ ] **Notification content**: What gets sent, when, what's the format
- [ ] **Rate limiting**: Can the bot spam Telegram? Is there any throttling?
- [ ] **APPROVE/DENY timing**: Can these arrive during a critical code section?

### Key Questions
- If the dashboard sync fails for 2 hours, is there any alerting?
- If the candle collector fails, how quickly does the system degrade?
- Is there a single monitoring surface that shows "system healthy" vs "degraded"?
- What's the blast radius of each infrastructure failure?

---

## Phase 9: Integration Testing & Cross-Cutting Concerns
**Testing how domains interact with each other.**

### Audit Checklist

#### End-to-End Lifecycle Traces
- [ ] **New coin trace**: Candle collected → daily resampled → scanner scores coin #1 → rebalance promotes → engine created → signal pack loaded → first candle tick → BUY signal → T1 gate pass → order placed → CSV recorded → status.json updated → dashboard shows position
- [ ] **TP close trace**: Engine detects TP condition → action generated → order placed → exchange confirms → trade recorded to CSV → capital returned → coin stays/leaves based on scanner → dashboard updates
- [ ] **Coin demotion trace**: Scanner drops coin below hurdle → rebalance excludes → allocation cleaned → but position stays → DCA layers still available → TP still works → eventually closes → coin removed from engines
- [ ] **Regime flip trace**: Coins flip to SHORT → conviction climbs → alerts fire → user APPROVEs → global regime changes → coins unflag → shorts now allowed → longs excluded → existing long TPs ride

#### Error Propagation
- [ ] For every `try/except` in the codebase: what's caught, what's the recovery, any silent failures
- [ ] Are there catch-all `except Exception` blocks that swallow important errors?
- [ ] What can crash the bot vs what's recoverable?
- [ ] After a crash, what state is inconsistent?

#### Race Conditions
- [ ] Telegram command during candle processing
- [ ] Status.json write during dashboard sync read
- [ ] State.json write during crash (partial write)
- [ ] Two candles arriving in rapid succession
- [ ] Rebalance firing while a TP is being processed

#### Accounting Integrity
- [ ] Trace $100 through the full lifecycle: allocation → buy (fee deducted) → hold → TP (fee deducted) → return. Does the math add up?
- [ ] After 100 trades, does `capital + realized_pnl - fees` equal `exchange_balance + unrealized_pnl`?
- [ ] Float precision: run the accounting formula 1000 times in simulation. How much drift?

---

## Phase 10: Migration Risk Register
**Everything that will change or break when moving to Hyperliquid mainnet.**

### Audit Checklist
- [ ] **Exchange client changes**: CCXT Hyperliquid adapter vs Aster adapter. API differences.
- [ ] **Symbol format**: Aster uses `XXX/USDT`, Hyperliquid uses...? What needs to change?
- [ ] **Order types**: Market, limit, stop. Which does each exchange support?
- [ ] **Margin modes**: Cross vs isolated. What does the bot assume?
- [ ] **Fee structure**: Aster fees vs Hyperliquid fees. Where are fees hardcoded?
- [ ] **Position format**: How positions are reported differently
- [ ] **WebSocket**: Candle streaming differences
- [ ] **Rate limits**: API call limits per exchange
- [ ] **Minimum order sizes**: Different per exchange
- [ ] **Leverage limits**: Different per coin per exchange
- [ ] **Funding rates**: Hyperliquid perps have funding. Is the bot aware?
- [ ] **Liquidation model**: Different per exchange. The bot checks liquidation price — does the formula match HL?

---

## Phase 11: Documentation Reconciliation
**Architecture doc vs code. Every section verified.**

### Audit Checklist
- [ ] **§1-2**: System overview, repo structure — still accurate?
- [ ] **§3**: Data pipeline — matches actual collection/resampling flow?
- [ ] **§4**: Intelligence layer — signal stack, scanner — matches code?
- [ ] **§5**: V14 DCA Engine — phase machine, grid, risk profiles — matches code?
- [ ] **§6**: Lifecycle engine — runtime loop, persistence, equity calc — matches code?
- [ ] **§7**: Portfolio manager — router, rebalance, regime system — matches code? (§7.3 updated today)
- [ ] **§8**: Exchange client — matches code?
- [ ] **§9**: Dashboards — matches actual dashboard HTML?
- [ ] **§10-11**: Scheduled tasks, monitoring — matches actual system?
- [ ] **§12-14**: Env vars, CLI, Python env — still accurate?
- [ ] **§15-16**: Design decisions, future architecture — still valid?
- [ ] **§6.8**: Reconciliation section — should note reconciliation is DISABLED
- [ ] **Performance numbers**: Outdated (March 10 numbers). Update or remove?
- [ ] **Line numbers**: Many references to specific line numbers. Verify or remove (code has changed).
- [ ] **Every spec marked DEPLOYED**: Verify the code actually implements it
- [ ] **Every hard rule**: Verify the system actually enforces it

---

## Deliverables

1. **Audit Report**: Comprehensive findings document with severity ratings and migration tags
2. **Complete System Variable Map**: Every state variable, its lifecycle, its truth source
3. **Integration Flow Diagrams**: Money flow, data flow, signal flow, state flow
4. **Architecture Doc v2.0**: Updated to match actual production code
5. **Migration Risk Register**: Prioritized list of Hyperliquid migration risks
6. **Bug/Gap List**: Every finding, prioritized, with fix recommendations
7. **Updated Hard Rules**: Any new rules from findings

---

## Schedule

| Phase | Domain | Est. Sessions |
|-------|--------|---------------|
| 1 | Data Pipeline (1,500 lines) | 1-2 |
| 2 | Intelligence / Signal Stack (3,400 lines) | 2-3 |
| 3 | Coin Selection & Scoring (1,200 lines) | 1-2 |
| 4 | Portfolio Management & Capital (600 lines + runner integration) | 2 |
| 5 | Trade Execution Engine (1,750 lines + runner integration) | 2 |
| 6 | State & Persistence (all state files) | 1-2 |
| 7 | Dashboards (8,200 lines) | 2 |
| 8 | Infrastructure (320 lines + tasks/cron) | 1 |
| 9 | Integration / Cross-Cutting | 1-2 |
| 10 | Migration Risk Register | 1 |
| 11 | Documentation Reconciliation | 1-2 |
| **Total** | **~25,000 lines + infra + state** | **~16-20 sessions** |

Findings reported continuously. Critical issues flagged immediately between phases.
Phases 1-3 first (data → intelligence → selection) because that's the foundation everything else builds on.
