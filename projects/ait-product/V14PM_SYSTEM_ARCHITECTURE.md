# Adaptive Intelligence Trading - V14PM System Architecture
_Version: 1.5 | Date: 2026-05-09 | Status: Production (Aster Perps)_

---

## 1. System Overview

### 1.1 Product Description

V14PM (V14 Portfolio Manager) is a fully automated crypto trading system built on a
Dynamic Dollar-Cost Averaging (DCA) engine, combined with a capital rotation portfolio
manager. It continuously scans a universe of 45 coins (66 symbol pairs), scores them
by DCA cycle efficiency, and dynamically allocates capital toward the highest-velocity
opportunities.

The system is designed for production deployment on **Hyperliquid** (perpetuals exchange),
though the core engine is exchange-agnostic via a CCXT abstraction layer.

### 1.2 Design Philosophy

- **Signal-first:** Never enter a position without qualifying signal confirmation
- **DCA-only exits:** All positions exit at a fixed take-profit above average entry
- **Capital rotation:** Close winners fast, redeploy to the next best opportunity
- **No manual intervention:** Fully autonomous from candle collection to order execution

### 1.3 System Layers

```
┌─────────────────────────────────────────────────────────────┐
│  PRESENTATION LAYER                                         │
│  GitHub Pages dashboards · Telegram alerts · Status JSONs  │
├─────────────────────────────────────────────────────────────┤
│  EXECUTION LAYER                                            │
│  V14PM Runner · CapitalRouter · Exchange Client            │
├─────────────────────────────────────────────────────────────┤
│  INTELLIGENCE LAYER                                         │
│  DCA Cycle Scanner · Signal Stack · ROUTER v2              │
├─────────────────────────────────────────────────────────────┤
│  DATA PIPELINE                                              │
│  Candle Collector · candles.db · Daily Aggregator          │
└─────────────────────────────────────────────────────────────┘
```

### 1.4 Active System Components

| Component | Entry Point | Exchange | Capital | Notes |
|-----------|------------|----------|---------|-------|
| **V14PM** (MVP) | `run_v14_portfolio_paper.py` | Hyperliquid | $50K paper | Target for live production |
| V14 Paper | `run_v14_paper.py` | Hyperliquid | $10K paper | Customer demo |
| V14-ETF Paper | `run_v14etf_paper.py` | Hyperliquid | $10K paper | Customer demo |
| V14 Live | `run_v14_live_aster.py` | Aster DEX | $300 real | Proof-of-concept |

---

## 2. Repository Structure

```
trading/
├── requirements.txt              # Production deps: ccxt, numpy, pandas
├── requirements-dev.txt          # Dev/backtest extras
├── openclaw_watchdog.ps1         # Bot watchdog (Windows - runs every 5 min)
├── sync_dashboard.ps1            # GitHub Pages sync (Windows)
├── sync_dashboard_silent.vbs     # Silent launcher for sync task
│
└── spot/
    ├── __init__.py
    │
    ├── engine/                   # Core signal + DCA engine (package)
    │   ├── __init__.py
    │   ├── v14_dca_engine.py       # V14 DCA phase machine + grid
    │   ├── v13_signals.py          # StochRSI, ADX, HH/HL detectors
    │   ├── v13_router_engine_v1.py # Fib levels, base config, V13RouterV1
    │   ├── v13_router_engine_v2.py # HybridDetector2D (top/bottom detection)
    │   ├── v13_phase_backtest_v8.py# V13BacktestV8, V13Config, Phase enum
    │   ├── _steve_3check.py        # 3-check top/bottom confirmation detector
    │   ├── test_hvf_daily.py       # HVF daily scoring
    │   └── build_daily_candles.py  # 1h→daily aggregation + indicator compute
    │
    ├── v14_lifecycle_engine.py   # Wraps engine for live/paper loop
    ├── v14_capital_manager.py    # CapitalRouter (V14PM allocation logic)
    ├── v14_cycle_scanner.py      # DCA Cycle Velocity scorer
    ├── coin_scanner.py           # Full 44-coin signal scanner
    ├── exchange_client.py        # CCXT exchange abstraction (HL + Aster)
    ├── cfgi_client.py            # Fear & Greed Index client
    ├── incident_schema.py        # Structured incident reporting
    ├── daily_collector.py        # Candle DB maintenance + signal rebuild
    │
    ├── run_v14_portfolio_paper.py  # V14PM bot runner (paper)
    ├── run_v14_paper.py            # V14 paper bot runner
    ├── run_v14etf_paper.py         # V14-ETF paper bot runner
    ├── run_v14_live_aster.py       # V14 live bot runner (Aster DEX)
    ├── run_v14_scanner.py          # Manual scanner runner
    ├── run_daily_collector.py      # Manual collector runner
    │
    ├── collect_scanner_candles.py  # Incremental 1h candle collector (Step 1)
    ├── resample_daily.py           # 1h → daily OHLCV resampling (Step 1.5)
    ├── backfill_scanner_coins.py   # Historical candle backfill
    ├── backfill_etf_candles.py     # ETF coin candle backfill
    ├── generate_daily_equity.py    # Daily equity JSON for dashboards
    ├── pm_comparison_log.py        # PM performance comparison logger
    │
    ├── run_candle_collector.ps1    # Pipeline runner (Windows)
    ├── run_candle_collector.sh     # Pipeline runner (Linux/cloud)
    │
    ├── data/
    │   └── candles.db              # Primary SQLite database (214 MB)
    │
    ├── live/
    │   └── v14/                    # V14 live bot state (Aster DEX)
    │       ├── .env                # Credentials (NOT in git)
    │       ├── .env.template       # Credential template
    │       ├── state.json          # Bot position state
    │       ├── status.json         # Health/metrics (updated every ~1h)
    │       ├── trades.csv          # Trade history
    │       └── bot.log             # Runtime log
    │
    ├── live/v14pm/                 # V14PM live bot state (create for production)
    │   └── .env.template           # Hyperliquid credential template
    │
    └── paper/
        ├── v14/                    # V14 paper bot state
        ├── v14etf/                 # V14-ETF paper bot state
        └── v14_portfolio/          # V14PM paper bot state
            ├── engine_state.json     # Engine snapshots (saved every 60s)
            ├── status.json           # Health metrics (dashboard + heartbeat)
            ├── trades.csv            # Closed trade history (source of truth)
            ├── bot.pid               # PID lock file (prevents duplicate instances)
            └── bot.log               # Runtime log
```

---

## 3. Data Pipeline

### 3.1 Candle Collection & Daily Resampling

**Entry point:** `run_candle_collector.ps1` (Windows) / `run_candle_collector.sh` (Linux)
**Schedule:** Hourly via `AIT_CandleCollector` scheduled task
**Exchange:** Hyperliquid perps (CCXT)
**Coverage:** 66 symbol pairs (45 base coins × USDC/USDT), 1h timeframe, incremental

**Three-step hourly pipeline:**
```
Step 1: collect_scanner_candles.py
  Hyperliquid API
    └─ fetch_ohlcv(symbol, '1h', since=last_stored)
         └─ INSERT INTO candles (symbol, timeframe, timestamp, O/H/L/C/V)

Step 1.5: resample_daily.py
  candles (1h)
    └─ Aggregate to daily OHLCV (floor timestamp to midnight UTC)
         └─ INSERT OR IGNORE INTO candles_daily (symbol, date, timestamp, O/H/L/C/V, candle_count)

Step 2: v14_cycle_scanner.py
  candles_daily → V14DCAEngine backtest per coin → cycle_scanner.json
```

**Why resample?** The candle collector writes 1h candles to the `candles` table.
The V13SignalPack (all indicators, phase detection) reads from `candles_daily`.
Without resampling, coins that only have Hyperliquid data would have zero daily
candles and their engines would run blind (no signals, no phase transitions).

> **History note:** Before 2026-03-10, the resampling step did not exist. 19 of 45
> coins had 1h data but zero daily candles. Their engines ran without signal packs.
> `resample_daily.py` was created to close this gap.

### 3.2 Database - `candles.db`

**Location:** `trading/spot/data/candles.db` (~225 MB, SQLite)
**Env var override:** `AIT_CANDLES_DB`

> **⚠ DB Path Warning:** All files that reference `candles.db` must resolve to
> `trading/spot/data/candles.db`. A 0-byte file at `trading/data/candles.db`
> previously existed and caused silent failures in two modules (`_steve_3check.py`
> and `v13_router_engine_v2.py`) where `.parent` chains resolved to the wrong path.
> The empty file has been renamed to prevent recurrence.
> **Recommendation:** Centralize `DB_PATH` into a single `trading/spot/config.py`
> module, imported by all consumers. This eliminates the class of bug entirely.

| Table | Rows (approx) | Purpose |
|-------|------|---------|
| `candles` | 1,562,000+ | 1h OHLCV for 66 symbol pairs |
| `candles_daily` | ~99,000 | Daily OHLCV (two sources - see below) |
| `cfgi_daily` | 23,846 | Fear & Greed Index per coin per day |
| `signal_snapshots` | 376 | Daily signal state snapshots |
| `phase_transitions` | 999 | Phase change events with trigger signals |
| `scanner_results` | 438 | Historical scanner scoring runs |
| `trades` | 21 | Closed trade records (all bots) |
| `trade_context` | 3,782 | Per-trade signal context at entry/exit |

**`candles_daily` has two data sources:**
1. **`build_daily_candles.py`** - aggregates 1h candles AND computes 26 indicators
   (SMA, ADX, RSI, etc.). These rows have all indicator columns populated.
2. **`resample_daily.py`** - simple 1h → daily OHLCV aggregation only. These rows
   have indicator columns as NULL. Used for coins added via Hyperliquid collector
   that `build_daily_candles.py` hasn't processed yet.

Both use `INSERT OR IGNORE` - they don't overwrite each other. The V13SignalPack
computes its own indicators from the raw OHLCV, so NULL indicator columns are fine.

**Core schema:**
```sql
-- Raw hourly candles (primary data source)
candles (
    symbol      TEXT,   -- e.g. 'BTC/USDC'
    timeframe   TEXT,   -- '1h'
    timestamp   INTEGER,-- Unix ms
    open REAL, high REAL, low REAL, close REAL, volume REAL
)

-- Daily OHLCV (may include pre-computed indicators from build_daily_candles.py)
candles_daily (
    symbol TEXT, date TEXT, timestamp INTEGER,
    open REAL, high REAL, low REAL, close REAL, volume REAL,
    candle_count INTEGER,
    -- Indicator columns (populated by build_daily_candles.py, NULL from resample_daily.py):
    sma20 REAL, sma50 REAL, sma200 REAL,
    bb_width REAL, bb_pct REAL,
    atr14 REAL, atr_pct REAL,
    adx REAL, plus_di REAL, minus_di REAL,
    rsi14 REAL,
    consec_hh_hl INTEGER, consec_lh_ll INTEGER,
    sma50_slope REAL, sma200_slope REAL,
    price_vs_sma50 REAL, price_vs_sma200 REAL
)
```

### 3.3 Daily Data - Two Paths

There are two distinct processes that populate `candles_daily`:

1. **`resample_daily.py`** (runs hourly in pipeline) - Simple 1h→daily OHLCV
   aggregation. Ensures all coins have daily candles regardless of whether they've
   been through the full indicator build. This is the **critical** path - without it,
   coins only available on Hyperliquid have zero daily data, and their signal packs fail.

2. **`build_daily_candles.py`** (engine package) - Full aggregation + 26 indicator
   computation (SMA, ADX, RSI, etc.). Heavier operation, used for historical backfill
   and when pre-computed indicators are needed by `candles_daily` consumers.

The V13SignalPack computes its own indicators from raw daily OHLCV, so the
`resample_daily.py` path is sufficient for live trading. The pre-computed indicators
in `build_daily_candles.py` are primarily used by the scanner and dashboards.

---

## 4. Intelligence Layer

### 4.1 DCA Cycle Velocity Score

**Module:** `trading.spot.v14_cycle_scanner`
**Output:** `docs/data/v14/cycle_scanner.json`

The core ranking metric for capital allocation decisions. Measures how efficiently
a coin completes profitable DCA cycles.

```
DCA Score = Realized_PnL × (1 - MaxDrawdown%) × Capital_Freedom / 100
```

Where:
- **Realized_PnL** - total closed profit across the simulation window
- **MaxDrawdown%** - worst peak-to-trough during the window
- **Capital_Freedom** - percentage of time capital was *not* trapped (available to redeploy)

**Simulation parameters (High Profile):**
```
Base Order:      40% of allocation
Safety Order deviation: 1.5% per layer
Safety Order multiplier: 1.5x volume per layer
Max layers:      12
Take Profit:     1.5% above average entry
Taker fee:       0.025% (Hyperliquid)
```

**Scan windows:** 7d, 14d, 30d, bear (extended lookback)

**Minimum history:** 6 months of 1h candles required to appear on dashboard rankings

### 4.2 Trend Multiplier

Applied on top of the DCA Score to bias allocation toward momentum:

```
Adjusted Score = DCA Score × Trend Multiplier
```

The trend multiplier is the weighted slope of the DCA Score time series:
- 7-day slope: **50% weight** (most recent signal)
- 14-day slope: 30% weight
- 30-day slope: 20% weight

**Output range:** clamped to [0.30, 1.50]
- Accelerating coin: up to **1.5x** multiplier
- Stable coin: ~1.0x
- Declining coin: as low as **0.30x** (strongly penalized)

Requires ≥3 historical snapshots. Without history, multiplier defaults to 1.0.

### 4.3 Coin Universe

44 coins across Hyperliquid perps and Aster DEX (spot):

**Established (pre-2024):** BTC, ETH, SOL, XRP, LINK, DOGE, ADA, LTC, AVAX, DOT,
UNI, ATOM, NEAR, HBAR, INJ, FIL, RUNE, CRV, SNX, COMP

**DeFi/Mid-cap:** AAVE, ARB, GMX, JUP, PENDLE, STX, ZRO, ENS, GRT, BAL

**High-beta/Speculative:** PEPE, BONK, WIF, FLOKI, JTO, PYTH, TIA, SEI, APT, SUI

**AI/Infrastructure:** FET, TAO, HYPE

**Legacy (still tracked):** ZEC, SAND, MANA

### 4.4 Signal Stack (`trading.spot.engine`)

> **Naming note:** The signal module is called `v13_signals.py` and the class is `V13SignalPack`
> for historical reasons - it was written during V13 development. It is **not** V13 trading logic.
> It's a shared signal/indicator library (StochRSI, ADX, structure detection) used by both V13 and V14
> engines. Renaming to `SignalPack` is planned but deferred to avoid touching all importers while
> bots are running.

All signals are computed from `candles_daily` data:

| Signal | Module | Purpose |
|--------|--------|---------|
| StochRSI (1w/2w/3w) | `v13_signals.py` | Overbought/oversold detection |
| ADX + DI± | `v13_signals.py` | Trend strength / regime classification |
| HH/HL, LH/LL | `v13_signals.py` | Higher highs/lows structure |
| SMA50/200 slope | `v13_signals.py` | Macro trend direction |
| HVF score | `test_hvf_daily.py` | High Volume Flush - exhaustion signal |
| 3-check detector | `_steve_3check.py` | Triple confirmation (price/volume/momentum) |
| Fibonacci levels | `v13_router_engine_v1.py` | Support/resistance + extension targets |
| HybridDetector2D | `v13_router_engine_v2.py` | Composite top/bottom detection |
| Fear & Greed | `cfgi_client.py` | Macro sentiment gating |

### 4.5 ROUTER v2 - Phase Transition Signal Stack

The V14DCAEngine uses a layered signal stack to detect tops and bottoms for phase
transitions between `LONG_DCA` and `SHORT_DCA`.

**Top Detection (during LONG_DCA → triggers switch to SHORT_DCA):**

| Layer | Signal | Action |
|-------|--------|--------|
| 1: Early Warning | 1W StochRSI K crosses below 97 | Start unwinding (stop new DCA entries, let TPs hit) |
| 2: OB93 Arm | 2W StochRSI K crosses below 93 | ARM - wait for divergence confirmation |
| 2a: Divergence | 2D RSI bearish divergence detected | CONFIRM TOP: close all longs, switch to SHORT_DCA |
| 2b: Timeout | 35 days armed, no divergence | TIMEOUT: close all longs, switch to SHORT_DCA |
| 2c: OB85 Fallback | 1W K crosses below 85 (only if NOT armed) | Fallback top: close longs, switch to SHORT |
| 3: Failsafe | 1W K crosses below 50 (after 2-week wait from early warning) | Emergency exit |

**Bottom Detection (during SHORT_DCA → triggers switch to LONG_DCA):**

Triple-gate prerequisite (ALL must pass before conviction scoring):
1. **Gate 1:** 3D death cross active (3D SMA50 < 3D SMA200)
2. **Gate 2:** 2W StochRSI exhaustion lift-off (K ≥ 5 after being pinned < 5)
3. **Gate 3:** Conviction score ≥ 3 of 4 (see HybridDetector2D)

**Conviction score components:**
- Steve's 3-Check (2D: below SMA200 + RSI<26 + StochRSI K&D<20)
- CFGI < 35 (extreme fear)
- HVF exhaustion signal
- Fibonacci support proximity

On conviction: close all shorts, switch to LONG_DCA.

**Safety net (markdown failure):**
If price rises 25%+ against the short grid with ADX > 25, force-close shorts
and switch to LONG_DCA regardless of conviction state.

**Implementation:** `HybridDetector2D` in `v13_router_engine_v2.py` computes 2D
divergence dates and 3D death cross state from `candles_daily` data. The Steve
3-Check detector (`_steve_3check.py`) computes 2D indicators independently.

> **Bug history (fixed 2026-03-10):** `v13_router_engine_v2.py` had a wrong DB path
> (`.parent.parent.parent` instead of `.parent.parent`), causing it to read from an
> empty 0-byte database. This meant top detection always timed out (never detected
> real divergences) and bottom conviction never fired (death cross gate always failed).
> Fixed by correcting the path. See `V14PM_FULL_AUDIT.md` §2.1 for details.

---

## 5. V14 DCA Engine (`trading.spot.engine.v14_dca_engine`)

### 5.1 Phase Machine

```
              ┌─────────────────────────────────────────┐
              │                                         │
  Entry  ───▶ LONG_DCA ──(top signal)──▶ ROUTER ──────▶ SHORT_DCA
              ▲                            │              │
              │                            │ (no signal)  │
              └────────────────────────────┘              │
              ◀──────────(bottom signal)──────────────────┘
```

**LONG_DCA** - Building a long position via DCA grid. Each layer triggered by
price dropping `SO_DEVIATION` below previous layer. Takes profit when average
entry rises to `TP_PCT` above average cost. Re-enters immediately after TP hit.

**ROUTER** - Evaluating market regime. ROUTER v2 (HybridDetector2D) determines
whether the market is topping (→ SHORT_DCA) or false alarm (→ back to LONG_DCA).

**SHORT_DCA** - Mirror of LONG_DCA for short positions (Hyperliquid perps only).
Triggered by confirmed top signal. Same grid mechanics, inverted direction.

> **Regime Gate (§7.5):** Phase transitions happen autonomously at the engine level,
> but the portfolio regime gate controls whether a coin in a given phase may actually
> trade. A coin in SHORT_DCA while the global regime is LONG_DCA is excluded from
> new entries - its open positions ride to TP naturally. See §7.5.2.

### 5.2 DCA Grid Mechanics

```
Base Order (BO) = capital × DCA_BO_PCT (40%)

Layer 0 (Base): BO amount at entry price
Layer 1: BO × SO_VOL_MULT at (entry × (1 - SO_DEV))
Layer 2: Layer1_size × SO_VOL_MULT at (Layer1_price × (1 - SO_DEV × price_multiplier))
...
Layer N: where N = DCA_MAX_LAYERS

Take Profit: when avg_entry × (1 + DCA_TP_PCT) ≤ current_price → SELL ALL
```

**Layer timing:** There is no cooldown between layers at any risk profile (Low,
Medium, or High). When price drops through multiple deviation thresholds, the
grid fills all qualifying layers on the next tick. The deviation check
(`current_drop >= SO_DEV × layer_count`) is the sole gate for adding layers.
This ensures the grid reacts immediately to volatility and captures rapid dips
for faster TP recovery.

> **History (2026-03-11):** A legacy 1-day cooldown guard was discovered in
> `v14_dca_engine.py` - originally a backtest artifact (daily candles = no effect)
> that silently throttled live bots running on 1h candles to one layer per day.
> Removed as it was never part of the tested/documented grid design and actively
> harmed DCA performance during volatile moves.

### 5.3 Risk Profiles

All bots are launched with an explicit `--profile` flag:

| Profile | Leverage | BO% | SO Dev | SO Mult | Max Layers | TP |
|---------|----------|-----|--------|---------|------------|----|
| `low` | 1.0x | 40% | 2.0% | 1.5x | 10 | 1.5% |
| `medium` | 1.5x | 40% | 2.0% | 1.5x | 10 | 1.5% |
| `high` | 1.5x | 40% | 1.5% | 1.5x | 12 | 1.5% |

**V14PM live production uses:** `high` profile, `1.0x` leverage (no liquidation risk)

### 5.4 Configuration (`V14Config`)

Key defaults (overridden by profile at runtime):
```python
DCA_TP_PCT          = 0.015   # 1.5% take profit
DCA_SO_DEVIATION    = 0.025   # 2.5% between safety orders (default)
DCA_SO_MULTIPLIER   = 1.5     # Volume multiplier per layer
DCA_BO_PCT          = 0.30    # 30% base order (default)
DCA_MAX_LAYERS      = 8       # Max safety orders (default)
DCA_ACCUMULATE      = True    # False = cycling mode (paper bots)
OB_THRESHOLD_2W     = 93      # StochRSI 2w overbought threshold
```

---

## 6. V14 Lifecycle Engine (`trading.spot.v14_lifecycle_engine`)

### 6.1 Runtime Loop

The lifecycle engine is the heartbeat of every bot. It runs continuously:

```
Every hour (on candle close):
  1. Fetch latest 1h candle from exchange
  2. Update signal state (StochRSI, ADX, HH/HL structure)
  3. Check for take-profit hit → execute sell if triggered
  4. Check phase transition signals → update phase if warranted
  5. Check for new DCA layer entry → execute buy if triggered
  6. Write state.json + status.json

At midnight UTC (daily signal evaluation):
  1. Load candles_daily from candles.db
  2. Run full signal stack (HVF, 3-check, Fibonacci, HybridDetector2D)
  3. Update ROUTER evaluation
  4. Write signal snapshot to DB
```

### 6.2 State Persistence

The PM bot writes two state files every cycle (~60 seconds):

**`engine_state.json`** - Complete engine state for restart recovery (PM-specific):
```json
{
  "version": 1,
  "saved_at": "2026-03-10T12:56:36Z",
  "engines": {
    "ZRO/USDT": { /* V14LifecycleEngine.snapshot_state() output */ },
    "NEAR/USDT": { /* ... */ }
  },
  "last_candle_ts": { "ZRO/USDT": 1741608000000, ... },
  "open_deals": { /* TradeTracker in-progress trades */ },
  "router": {
    "active_pool_cash": 28456.12,
    "reserve_pool_cash": 12500.00,
    "active_allocations": { "ZRO/USDT": 3750.00, ... },
    "reserve_allocations": {}
  },
  "last_rebalance_date": "2026-03-10",
  "approved_symbols": ["DOT/USDT", "ENS/USDT", ...],
  "current_equity": 50505.13
}
```

Each engine snapshot includes: phase, capital, all long/short position state
(coins, avg entry, layers, cost, TP, PnL), top detection state (early warning,
OB93 arm, peak 2W K, unwinding), bottom detection state (conviction, top_detected),
cycle tracking (markup cycles, ADX streak), router routing flags, and wrapper
state (last daily date, live mode flag, last candle timestamp, warmup status).

On startup, `_load_state()` reconstructs all engines from this file. If the signal
pack fails to load for a coin (e.g., missing daily data), a bare engine is created
and state is still restored - signals will refresh on the next daily boundary.

**`status.json`** - Health metrics (read by heartbeat monitor and dashboard):
```json
{
  "running": true,
  "mode": "paper",
  "engine": "v14",
  "profile": "high",
  "leverage": 1.0,
  "exchange": "hyperliquid",
  "capital": 50000,
  "equity": 50505.13,
  "total_realized_pnl": 505.13,
  "deals_completed": 22,
  "win_rate": 100.0,
  "coins": { "ZRO/USDT": {...}, "NEAR/USDT": {...}, ... },
  "last_update": "2026-03-10T12:56:36Z"
}
```

> **Single-bot state.json:** The V14 Live bot (Aster) uses a simpler `state.json`
> for its single engine. The PM bot does NOT use `state.json` - all its state is
> in `engine_state.json`, which covers all 10 engines, the router, and open deals.

### 6.3 Equity Calculation (All Bots)

**All four bot runners** compute equity from ground truth, not engine internals:

```
Equity = Capital + CSV Realized PnL - Fees + Unrealized PnL
```

- **Realized PnL** is **always** sourced from `trades.csv` - the CSV is the
  single source of truth. Engine-internal PnL counters are never used for
  status reporting. This was standardized across all runners on 2026-03-10
  after engine counters were found to drift on restart (one bot reported
  $65K realized when the CSV ledger showed $44K).
- **Unrealized PnL** is summed from each engine's per-coin status.
- **Uptime / Daily ROI** uses the earliest trade timestamp from `trades.csv`,
  not the process start time, so metrics survive restarts.

> **Why not sum engine equities?** Daily rebalance can inject cash into engines
> (via `eng.capital = max(eng.capital, new_alloc - invested)`) without updating
> `initial_capital`. Summing engine equities + unallocated capital double-counts
> the injected cash. The ground-truth formula avoids this entirely.

> **Bug history (fixed 2026-03-10):** Prior to this fix, equity and realized PnL
> in status.json came from engine internal counters (`eng.long_pnl + eng.short_pnl`).
> Deal counts and win rate were overridden from CSV, but equity and realized PnL
> were not. On restart, engine counters could reset, inflate, or drift - producing
> incorrect dashboard numbers while the CSV remained accurate. The fix applies to
> all four runners: `run_v14_paper.py`, `run_v14etf_paper.py`,
> `run_v14_portfolio_paper.py`, and `run_v14_live_aster.py`.

### 6.3.1 Live Bot Equity (Exchange API)

The V14 Live bot (Aster) has an additional equity source: **actual exchange balances**.

```
Live Equity = USDT Balance + (Base Coins × Current Price)
```

This is fetched from the exchange API every cycle and overrides the CSV-based
calculation. For a live bot, the exchange balance is the ultimate truth - it
accounts for positions the engine may not know about (e.g., after a `--fresh`
restart where the engine forgets old positions but the exchange still holds them).

The exchange balance is included in status.json as `exchange_balance`:
```json
{
  "exchange_balance": {
    "usdt_free": 79.47,
    "usdt_total": 79.47,
    "base_free": 331.72,
    "base_total": 331.72
  }
}
```

### 6.4 Trade History Preservation

`TradeTracker.load_existing()` is called on startup to load historical trades from
`trades.csv` into memory. This ensures:
- Deal counts and win rates include all historical trades
- Realized PnL reflects cumulative performance, not just the current session
- `save_csv()` writes all trades (loaded + new) without losing history

### 6.4.1 `--fresh` vs Normal Restart

| Scenario | Command | State Behavior |
|----------|---------|----------------|
| **Normal restart** (reboot, crash, update) | `--capital 50000 --profile high --leverage 1.0` | Loads `engine_state.json` → all engines restored with positions, phase, indicators. No candle replay. |
| **First launch** (new account, clean start) | `--capital 50000 --profile high --leverage 1.0 --fresh` | Skips state restore. Skips candle backfill. Engines start from NOW, trading only new candles. **Loads existing trades.csv** to preserve history and prevent CSV overwrite. |
| **Deliberate reset** (wipe and restart) | Delete `engine_state.json` + `trades.csv`, then `--fresh` | Full clean slate. Previous trade history lost. |

**On normal restart**, `engine_state.json` contains everything needed:
- Engine positions, phases, and signal state
- Router pool cash and allocations
- Last processed candle timestamps (no replay)
- Open deals (in-progress trades)

**`--fresh` is ONLY for first launch.** The PM scheduled task does NOT use `--fresh`.

### 6.5 PM Startup Sequence

On every PM bot restart:
1. Acquire PID lock (`bot.pid`) - exit if another instance is running
2. Load trade history from `trades.csv` (`TradeTracker.load_existing()`)
3. If `--fresh`: skip state restore, proceed to step 5
4. **State restore:** Load `engine_state.json` → reconstruct all engines with
   positions, phases, indicators, last candle timestamps. Restore router state
   (pool cash, allocations). Restore open deals.
5. Run initial rebalance (`_check_and_rebalance()`) - if engines were restored,
   this updates allocations; if fresh start, this creates new engines.
6. Enter live trading loop

> **Live bot startup (future):** Will add exchange balance reconciliation after step 4.
> Compare engine state vs. real balances, log drift, abort if drift exceeds threshold.
> Paper bots skip this since they don't interact with real exchange positions.

### 6.5.1 Engine Warmup Period

On fresh starts, each `V14LifecycleEngine` requires a **warmup period** before trading:

- Engines start with `_warmed_up = False`
- During warmup: candles are accumulated and price is tracked, but **no DCA ticks fire** (no entries)
- At the **first daily boundary** (midnight UTC): the full daily tick runs - signal pack refreshes,
  ROUTER evaluates direction (long vs short), signals compute. `_warmed_up` flips to `True`.
- After warmup: hourly DCA ticks run normally, entering positions based on router-directed phase

**Why:** Without warmup, engines default to `LONG_DCA` and enter L1 on the first candle they see,
before the router has evaluated whether the market direction warrants long or short. In a bear
market, this could mean entering 10 long positions right before the router would say "go short."

**Exceptions:** Engines restored from `engine_state.json` are immediately `_warmed_up = True`
because they were already trading with established direction before the restart.

### 6.6 PID Lock (Paper Trading)

The PM paper runner uses a PID lock file (`bot.pid`) to prevent duplicate instances:

- On startup: checks if another PM bot is running (validates PID + command line)
- If running: exits immediately with error log
- On shutdown: releases lock file
- Stale locks (dead process) are automatically overwritten

This prevents the scheduled task from spawning a second instance alongside a manually started bot,
which would cause both to write phantom trades to the same `trades.csv`.

### 6.7 Trade Provenance (`recorded_at`)

Every trade record includes a `recorded_at` UTC timestamp - the wall-clock time when the trade
was actually written, distinct from `close_time` (when the trade claims to have closed).

- **Real trade:** `recorded_at ≈ close_time` (within minutes)
- **Phantom trade:** `recorded_at` is hours/days after `close_time` (backfill replay)

This field is the forensic backstop: even if all other safeguards fail, phantom trades can always
be identified and removed by comparing `recorded_at` vs `close_time`.

### 6.8 Trade Reconciliation (2026-05-05)

The `TradeTracker` CSV can drift from exchange reality when trades are closed outside the
normal flow (forced API closes, bot crashes during TP fills, Telegram CLOSE commands).
The reconciliation system ensures the CSV stays in sync with the exchange.

#### 6.8.1 Standalone Reconciliation Tool

**File:** `trading/spot/reconcile_trades.py`

A CLI tool that connects to Aster DEX, fetches all fill history per symbol,
reconstructs closed deals from buy/sell fill sequences, and compares against `trades.csv`.

**Usage:**
```bash
python -m trading.spot.reconcile_trades            # dry-run (report only)
python -m trading.spot.reconcile_trades --fix-ids   # sort + reassign monotonic deal IDs
python -m trading.spot.reconcile_trades --fix        # full rewrite from exchange truth
python -m trading.spot.reconcile_trades --since-days 30  # limit lookback window
```

**Report categories:**
- **MISSING:** deals on exchange but absent from CSV (e.g., forced close bypassed TradeTracker)
- **PHANTOM:** deals in CSV with no matching exchange fill (within API retention window)
- **UNVERIFIABLE:** deals in CSV for symbols where exchange returned 0 fills (API retention expired)
- **MISMATCHED:** deals in both but PnL or layer count differ significantly
- **DUPLICATE:** deal_ids appearing more than once in CSV

**`--fix` behavior (conservative):**
1. For symbols WITH exchange data: replaces CSV rows with exchange-reconstructed deals
2. For symbols WITHOUT exchange data: keeps existing CSV rows (unverifiable but presumed correct)
3. Pre-retention CSV rows (older than earliest exchange fill) are preserved
4. Sorts all by `close_time`, assigns sequential deal_ids
5. Creates timestamped `.bak` backup before any modification

**`--fix-ids` behavior (minimal):**
1. Sorts all existing CSV rows by `close_time`
2. Reassigns sequential deal_ids (1, 2, 3, ...)
3. Does not add, remove, or modify any trade data

> **Aster API limitation:** Trade fill history has ~30-day retention. Older fills are
> purged from the API. The reconciliation tool handles this gracefully: CSV rows for
> symbols with no available fills are classified as "unverifiable" (not "phantom").

#### 6.8.2 Startup Reconciliation

**Method:** `_reconcile_trades_on_startup()` in `V14PortfolioLiveAster`

Runs automatically after `_load_state()` and `_recover_tp_orders()` on every bot start:

1. Fetches last 48h of exchange fills for all tracked symbols
2. Reconstructs closed deals from fill sequences
3. Checks each against CSV by matching symbol + close_time (±5 min window)
4. Appends any missing deals with new monotonic deal_ids
5. Saves CSV and sends Telegram alert if trades were recovered

This is lightweight - only checks recent history, not a full rebuild.

#### 6.8.3 RECONCILE Telegram Command

Operators can trigger on-demand reconciliation via Telegram:
- `RECONCILE` - runs the 48h startup reconciliation and reports results

#### 6.8.4 Deal ID Assignment Fix

`TradeTracker.load_existing()` now sets `_deal_counter = len(self.trades)` instead of
`max(deal_id)`. This prevents duplicate ID collisions when the CSV contains duplicate
IDs from prior bugs. New trades always get `counter + 1`.

---

## 7. V14PM Portfolio Manager

### 7.1 Architecture

```
run_v14_portfolio_paper.py
    │
    ├─ V14LifecycleEngine × N coins   (one instance per active slot)
    │
    ├─ CapitalRouter                   (v14_capital_manager.py)
    │    ├─ active_pool   (75% of equity)
    │    └─ reserve_pool  (25% of equity)
    │
    └─ Cycle Scanner JSON              (docs/data/v14/cycle_scanner.json)
         └─ Adjusted Score = DCA Score × Trend Multiplier
```

### 7.2 CapitalRouter - Allocation Rules

**Pool split:**
- **Active Pool (75%):** Deployed capital for DCA positions
- **Reserve Pool (25%):** Held back for new opportunities and drawdown buffer

**Equity-tiered coin cap:**

| Portfolio Equity | Max Simultaneous Coins |
|-----------------|------------------------|
| $100,000+ | 10 |
| $50,000 - $100,000 | 5 |
| $30,000 - $50,000 | 4 |
| $20,000 - $30,000 | 3 |
| $10,000 - $20,000 | 2 |
| $100 - $10,000 | 1 |

**Entry qualification:**
- DCA Score ≥ 5.0 (hurdle rate)
- Within tier coin cap
- Proportional allocation by Adjusted Score
- Per-coin cap: max 20% of Active Pool

**Capital rotation:**
When a position closes (TP hit):
1. Release capital back to active pool
2. Run scanner to refresh rankings
3. Evaluate next best qualifying coin
4. Deploy to new position

### 7.3 Daily Rebalance

At midnight UTC, the PM runner:
1. Updates total equity from exchange balances
2. Recalculates tier cap (may change if equity grew/shrunk)
3. Loads latest `cycle_scanner.json`
4. Computes trend multipliers from score history
5. Identifies coins that no longer qualify (score dropped below hurdle)
6. Identifies new entrants above hurdle
7. Adjusts allocations proportionally
8. **Seeds `active_allocations`** from new targets (unblocks T1 gate for promoted coins)
9. **Reconciles stale allocations**: removes coins from `active_allocations` that are not in new targets AND have no open position

> **Allocation lifecycle (2026-05-10):** Previously, `active_allocations` only grew
> (via `request_capital()` on buys) and only shrank when a coin completed a trade AND
> fell out of top-N (via `_maybe_prune_stale_coin()`). This caused stale coins to
> accumulate forever. Additionally, new coins promoted by rebalance couldn't trade
> because the T1 gate checked `active_allocations` before allowing entries, but
> `request_capital()` only ran inside `_execute_action()` — a circular dependency.
> Both issues fixed: rebalance now seeds new targets and cleans stale entries.

### 7.4 Current Paper Performance (2026-03-10)

- **Capital:** $50,000 paper
- **Equity:** ~$50,627 (+1.25%)
- **Realized PnL:** $608 | Win rate: 100% (30 deals) | Drawdown: 0.0%
- **Active coins:** 10/10 slots (dynamically selected by cycle scanner)
- **Regime:** RANGING - DCA grids cycling TPs in sideways market
- **State persistence:** Verified - multiple restart cycles with zero phantom trades

**Other bots (2026-03-10, CSV-truth verified):**
- **V14 Paper:** $49,988 equity, 380 deals, 97.6% win rate (Oct 2024 - present)
- **V14-ETF Paper:** $10,834 equity, 24 deals, 100% win rate (Mar 2 - present)
- **V14 Live (Aster):** $314 equity on $300 capital, +4.7%, 1 deal (exchange-verified)

> **Bug history:** Earlier equity figures were inflated by engine counter drift.
> Engine-internal realized PnL could diverge from CSV on restart - one bot reported
> $65K when the CSV showed $44K. Fixed 2026-03-10 by making all runners use CSV
> as the sole source of realized PnL. Full audit: `V14PM_FULL_AUDIT.md`.

### 7.5 Portfolio Regime System

The portfolio regime system connects the per-coin engine phase machine (§5.1) to a
portfolio-level macro direction. Individual coins detect tops and bottoms
autonomously; the portfolio layer decides whether those signals should be acted on.

#### 7.5.1 Two-Level Regime Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│  GLOBAL REGIME (portfolio level)                        │
│  ──────────────────────────────────────                   │
│  State: LONG_DCA or SHORT_DCA                           │
│  Changed ONLY by manual approval (Telegram APPROVE)     │
│  Persisted in state.json                                │
└─────────────────────────────────────────────────────────────────┘
        │                                           ▲
        │  gates                            informs │
        ▼                                           │
┌─────────────────────────────────────────────────────────────────┐
│  PER-COIN REGIME (engine level)                         │
│  ──────────────────────────────────────                   │
│  Each engine tracks its own phase: LONG_DCA / SHORT_DCA │
│  Phase transitions driven by per-coin signals            │
│  (top detection, bottom conviction)                      │
└─────────────────────────────────────────────────────────────────┘
```

**Global regime** is a portfolio-level state: either LONG_DCA or SHORT_DCA.
It represents the operator's view of the macro market direction. It is NOT
automatically derived - it changes only when the operator manually approves
a regime flip via Telegram (APPROVE command).

**Per-coin regime** is the engine's autonomous phase based on its own signal stack
(top detection, bottom conviction). Each coin independently detects tops and bottoms.

#### 7.5.2 Regime Gate Rule

**A coin may only open new positions when its engine phase matches the global regime.**

| Global Regime | Engine Phase | Result |
|---------------|-------------|--------|
| LONG_DCA | LONG_DCA | ✅ Coin trades normally (long entries, DCA layers, TPs) |
| LONG_DCA | SHORT_DCA | ⛔ Coin excluded from trading. No new entries. Open positions ride to TP. |
| SHORT_DCA | SHORT_DCA | ✅ Coin trades normally (short entries, DCA layers, TPs) |
| SHORT_DCA | LONG_DCA | ⛔ Coin excluded from trading. No new entries. Open positions ride to TP. |

Key behaviors:
- The engine still processes candles and updates indicators regardless of the gate.
  Signals are tracked even when the coin is excluded - this is how the regime monitor
  knows how many coins have flipped.
- **No forced closes.** Open positions naturally hit TPs. The gate only blocks NEW entries.
- When the global regime eventually flips to match the coin's phase, the coin
  automatically becomes eligible to trade again.

#### 7.5.3 Regime Monitor — Graduated Conviction Alerts

The regime monitor counts how many active coins have individually flipped phase.
This count is the conviction signal for whether the macro market has topped or bottomed.

**Graduated thresholds** (each fires once as conviction climbs):

| Threshold | Severity | Signal |
|-----------|----------|--------|
| 15% | 📊 Info | Early warning — first few coins flipping |
| 25% | 📊 Info | Building momentum |
| 30% | ⚠️ Warning | Significant — trend is real |
| 35% | ⚠️ Warning | Strong conviction |
| 40% | ⚠️ Warning | Accelerating |
| 45% | ⚠️ Warning | Near-majority |
| 50% | 🚨 Critical | Majority flipped |

**Key behaviors:**
- APPROVE is available at **any** conviction level (operator can flip early)
- DENY resets the conviction tracker (alerts re-fire if more coins flip)
- When coins unflag (flip back to match global), conviction steps down automatically
- `last_alert_pct` is persisted in state.json to survive restarts

```
Example (global regime = LONG_DCA, 9 engines):

  1/9 flipped (11%) → No alert yet (below 15%)
  2/9 flipped (22%) → 📊 15% alert: "HYPE, TAO flipped"
  3/9 flipped (33%) → ⚠️ 25% + 30% alerts fire
  Operator: APPROVE → global regime flips to SHORT_DCA
  Result:   Flipped coins now eligible. LONG coins excluded.
            No positions force-closed.
```

The same logic works in reverse for bottoms during a SHORT_DCA global regime.

#### 7.5.4 Dashboard Display

Each coin on the dashboard shows:
- **Engine phase**: LONG_DCA or SHORT_DCA (the coin's own signal-based state)
- **Trading status**: ACTIVE (green, matches global) or EXCLUDED (red, conflicts)
- **Signal that triggered the flip**: Top detection method or bottom conviction score

The portfolio summary shows (Risk Profile → "Portfolio Regime" panel):
- **Global regime**: Current macro direction (▲ LONG or ▼ SHORT)
- **Engine counts**: N Long / N Short / N total
- **Conviction bar**: Visual progress bar of flip % with color coding
- **Flipped coin list**: Names of coins in opposing phase

The header shows:
- **Global regime badge**: ▲ LONG (green) or ▼ SHORT (red)
- **Conviction badge**: "Flip: X%" (appears when > 0%, color-coded by severity)

Macro Indicators section shows:
- **Regime Gate card**: Per-coin phase with ACTIVE/EXCLUDED status tags
- **Global regime reference**: At top of card for context

#### 7.5.5 Status.json Regime Data

```json
"regime_detail": {
  "global_regime": "LONG_DCA",
  "alert_state": "NONE",
  "last_alert_pct": 0.0,
  "flip_pct": 11.1,
  "flipped_coins": ["HYPE"],
  "aligned_coins": ["DYDX", "ENA", "INJ", "JTO", "JUP", "PEPE", "TAO", "TON"],
  "long_count": 8,
  "short_count": 1,
  "total_engines": 9
}
```

#### 7.5.6 Regime Flip Lifecycle

```
1. Market starts topping
2. Individual coins detect tops via signal stack (OB93+divergence, fallbacks, etc.)
3. Each coin's engine transitions to SHORT_DCA independently
4. Regime gate blocks these coins from opening SHORT positions (global is still LONG)
5. Open LONG positions on these coins naturally hit TPs and close
6. Dashboard shows increasing count of flipped coins
7. Operator receives Telegram alerts as thresholds are crossed
8. When conviction is high enough, operator sends APPROVE
9. Global regime flips to SHORT_DCA
10. All coins already in SHORT_DCA immediately become eligible to trade (short entries)
11. Coins still in LONG_DCA are now excluded until they also flip
12. No positions are force-closed at any point
```

#### 7.5.7 Implementation Notes

- Global regime is stored in `state.json` as `global_regime: "LONG_DCA"` or `"SHORT_DCA"`
- On startup, global regime is restored from state (not hardcoded)
- The regime gate check runs after each `engine.tick()` in the candle processing loop
- If an engine transitions to a phase conflicting with the global regime:
  - The phase transition is allowed (engine state reflects reality)
  - The coin is marked as excluded from trading
  - The regime monitor count increments
  - An alert is sent if tier thresholds are crossed
- The APPROVE/DENY flow changes only the global regime, never individual engine phases

---

## 8. Exchange Client (`trading.spot.exchange_client`)

### 8.1 Supported Exchanges

| Exchange | Type | Use |
|----------|------|-----|
| Hyperliquid | Perps (CCXT) | V14PM live + all paper bots |
| Aster DEX | Spot (CCXT) | V14 live bot only |

### 8.2 Credential Resolution (Priority Order)

1. **Explicit config dict** passed at construction
2. **Environment variables** - `HYPERLIQUID_API_KEY` / `HYPERLIQUID_API_SECRET`
3. **Windows Registry** (Windows-only fallback - silent no-op on Linux)

**Critical:** On Linux/cloud servers, env vars **must** be set. The Windows Registry
fallback is unavailable. If credentials are missing, the client raises `ValueError`
at initialization (fail-fast - does not attempt to connect unauthenticated).

### 8.3 Exchange Defaults

```python
EXCHANGE_DEFAULTS = {
    'hyperliquid': {
        'env_key':    'HYPERLIQUID_API_KEY',
        'env_secret': 'HYPERLIQUID_API_SECRET',
        'options': {...}  # Hyperliquid-specific CCXT options
    },
    'aster': {
        'env_key':    'ASTER_API_KEY',
        'env_secret': 'ASTER_API_SECRET',
        'options': {...}
    }
}
```

### 8.4 Paper Trading Mode

All paper bots use `SpotExchangeClient` with Hyperliquid in paper/simulation mode.
No real orders are placed. State and P&L are tracked locally in state.json and trades.csv.
The exchange connection is used only for live price data.

---

## 9. Presentation Layer

### 9.1 Dashboard Files

| Dashboard | File | Bot |
|-----------|------|-----|
| V14PM Portfolio | `docs/dashboardV14PM.html` | V14PM paper |
| V14 DCA | `docs/dashboardV14.html` | V14 paper |
| V14-ETF | `docs/dashboardV14ETF.html` | V14-ETF paper |
| V14 Live | `docs/d-984ae0d4ab9dc1a5.html` | V14 live (Aster) |

**Hosted at:** https://halo-effects.github.io/adaptive-intelligence-trading/

### 9.2 Data Flow

```
Bot status.json / trades.csv
    │
    ▼
generate_daily_equity.py  (produces daily_equity.json)
    │
    ▼
sync_dashboard.ps1  (every 10 min via AIT_DashboardSync)
    │
    ├─ git sparse-checkout clone → $TEMP/ait-dashboard-sync
    ├─ Copy docs/ data files to clone
    ├─ git add docs/   ← ONLY docs/ - never stages source files
    ├─ git commit -m "Data sync YYYY-MM-DD HH:MM"
    └─ git push → GitHub Pages
         └─ Live at halo-effects.github.io
```

**Safety note:** The sync script uses `git add docs/` (not `git add -A`) to ensure
source code files are never accidentally staged or deleted from the repository.

### 9.3 Dashboard Data Files

All under `docs/data/`:
```
docs/data/
├── v14/
│   ├── status.json          ← V14 paper bot live status
│   ├── trades.csv           ← V14 paper trade history
│   ├── cycle_scanner.json   ← DCA scores (read by V14PM runner)
│   └── daily_equity.json    ← Equity curve data
├── v14etf/
│   ├── status.json
│   └── trades.csv
└── v14-pm/
    ├── status.json
    └── trades.csv
```

---

## 10. Scheduled Tasks (Windows)

All tasks run as the current user. Working directory: `C:\Users\Never\.openclaw\workspace`.

| Task Name | Trigger | Entry Point | Purpose |
|-----------|---------|-------------|---------|
| `V14LiveAster` | At boot | `run_v14_live_aster.py --confirm --skip-backfill` | V14 live bot |
| `V14PaperBot` | At boot | `run_v14_paper.py` | V14 paper bot |
| `V14ETFPaperBot` | At boot | `run_v14etf_paper.py` | V14-ETF paper bot |
| `V14PMPaperBot` | At logon | `run_v14_portfolio_paper.py --capital 50000 --profile high --leverage 1.0` | V14PM paper bot (state restored from `engine_state.json`) |
| `V14CycleScanner` | Daily | `v14_cycle_scanner.py` | DCA score refresh |
| `AIT_CandleCollector` | Hourly | `run_candle_collector.ps1` | Candle + scanner pipeline |
| `AIT_DashboardSync` | Every 10 min | `sync_dashboard_silent.vbs` | Push data to GitHub Pages |
| `AIT_PMComparisonLog` | Scheduled | `pm_comparison_log.py` | PM benchmark logging |
| `AIT_Watchdog` | Every 5 min | `openclaw_watchdog.ps1` | Monitor + auto-restart bots |

**Auto-restart:** `V14LiveAster`, `V14PaperBot`, `V14ETFPaperBot`, `V14PMPaperBot` all have
`RestartCount=3` / `RestartInterval=2min` configured on the task.

---

## 11. Monitoring & Alerting

### 11.1 Telegram Notifications

All bots send structured Telegram alerts for:
- Bot startup / shutdown
- Phase transitions (LONG_DCA → ROUTER → SHORT_DCA)
- Take-profit hits (deal closed)
- DCA layer fills
- Exchange errors / reconnection events
- CFGI poll failures (non-critical)

**Required env vars:** `AIT_TG_TOKEN`, `AIT_TG_CHAT_ID`

**Message prefixes:**
- V14PM paper: `[V14-PM]`
- V14-ETF paper: `[V14-ETF]`
- V14 live: `[ASTER]`

### 11.2 Heartbeat Health Check

`status.json` is written after every trading cycle (~60 min). The watchdog and
heartbeat monitor check:
- `running: true` - bot has not errored out
- `last_update` timestamp - must be < 65 minutes old
- `max_drawdown_pct` - alert if > 15% (live bot only)

### 11.3 AIT_Watchdog

Runs every 5 minutes. Monitors:
1. **OpenClaw Gateway** - restarts if process not found
2. **V14PaperBot** - restarts scheduled task if not running or status stale > 2h
3. **V14ETFPaperBot** - same
4. **V14PMPaperBot** - same
5. **V14LiveAster** - same

Log: `~/.openclaw/watchdog.log`

---

## 12. Environment Variables - Complete Reference

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `HYPERLIQUID_API_KEY` | Yes (live) | None | Hyperliquid wallet address |
| `HYPERLIQUID_API_SECRET` | Yes (live) | None | Hyperliquid private key |
| `ASTER_API_KEY` | Yes (Aster bot) | None | Aster DEX API key |
| `ASTER_API_SECRET` | Yes (Aster bot) | None | Aster DEX API secret |
| `AIT_TG_TOKEN` | Recommended | None | Telegram bot token for alerts |
| `AIT_TG_CHAT_ID` | Recommended | None | Telegram chat ID for alerts |
| `CFGI_API_KEY` | Optional | None | Fear & Greed Index API key |
| `AIT_CANDLES_DB` | Optional | `trading/spot/data/candles.db` | Absolute path to candles.db |
| `AIT_SCANNER_JSON` | Optional | `docs/data/v14/cycle_scanner.json` | Path to cycle scanner output |
| `PYTHONPATH` | Cloud only | None | Set to workspace root on Linux |

**On Linux cloud servers:** `AIT_CANDLES_DB`, `AIT_SCANNER_JSON`, `PYTHONPATH` should
be set explicitly in the systemd service environment or `.env` file.

---

## 13. CLI Reference - Launch Commands

### V14PM Paper Bot
```bash
# Normal start (restart, reboot, crash recovery):
python -u -m trading.spot.run_v14_portfolio_paper \
  --capital 50000 \
  --profile high \
  --leverage 1.0
# Restores engine state from engine_state.json - no candle replay, no phantom trades.

# First launch ONLY (new account, clean start):
python -u -m trading.spot.run_v14_portfolio_paper \
  --capital 50000 \
  --profile high \
  --leverage 1.0 \
  --fresh
# Skips state restore and candle backfill. Engines start trading from NOW only.
# After first cycle, engine_state.json is saved - subsequent restarts don't need --fresh.
```

### V14PM Live Bot (production)
```bash
python -u -m trading.spot.run_v14_portfolio_live \
  --capital 50000 \
  --profile high \
  --leverage 1.0 \
  --exchange hyperliquid \
  --confirm         # Required for live trading
```
> Note: `run_v14_portfolio_live.py` does not yet exist - must be created as part
> of cloud migration. See Cloud Migration Guide.

### V14 Live Bot (Aster)
```bash
python -u -m trading.spot.run_v14_live_aster \
  --confirm \
  --skip-backfill   # Use for restarts (loads from state.json)
```

### Candle Collector (Linux)
```bash
# Runs collect_scanner_candles.py + v14_cycle_scanner
bash trading/spot/run_candle_collector.sh
```

### DCA Cycle Scanner (manual)
```bash
python -u -m trading.spot.v14_cycle_scanner
python -u -m trading.spot.v14_cycle_scanner --no-telegram  # Silent mode
python -u -m trading.spot.v14_cycle_scanner --backfill-history 7  # Backfill 7 days of score snapshots
python -u -m trading.spot.v14_cycle_scanner --as-of 2026-03-01    # Run as if it were a past date
```

---

## 14. Python Environment

- **Runtime:** Python 3.12
- **Package manager:** pip

**Production dependencies** (`trading/requirements.txt`):
```
ccxt==4.5.37       # Exchange client (Hyperliquid + Aster)
numpy==2.4.2       # Numerical computing
pandas==3.0.0      # Data manipulation
```

Only three third-party packages are required to run the complete production system.
All other dependencies are Python standard library.

**Development dependencies** (`trading/requirements-dev.txt`):
```
matplotlib, scipy, scikit-learn, plotly  # Backtest analysis only
```

---

## 15. Key Design Decisions & Rationale

| Decision | Rationale |
|----------|-----------|
| DCA-only entry/exit | Eliminates timing risk; consistent cycle completion regardless of market direction |
| 1.5% TP across all profiles | Balances cycle frequency vs. fee impact; proven through extensive backtesting |
| 75/25 active/reserve split | Reserve ensures capital always available for high-score opportunities |
| Equity-tiered coin cap | Prevents over-diversification at small capital; scales naturally |
| Score hurdle ≥ 5.0 | Filters out coins with poor cycle efficiency; avoids capital traps |
| Trend multiplier [0.3, 1.5] | Momentum bias without abandoning mean-reversion; bounded to prevent extremes |
| SQLite for candles.db | Zero-dependency, portable, sufficient for 1.5M rows at current scale |
| CCXT abstraction layer | Exchange-agnostic; swap Hyperliquid for any CCXT-supported exchange |
| State persistence via `engine_state.json` | Engines restore with positions, phases, indicators on restart; eliminates phantom trades from candle replay |
| `--fresh` for first launch only | New deployments skip history; all subsequent restarts use engine_state.json |
| Ground-truth equity calc | `Capital + Realized - Fees + Unrealized` from trades.csv; avoids engine internal drift. Live bot uses exchange API balances as ultimate truth. |
| `load_existing()` on ALL startup paths | Trade history survives restarts including `--fresh`; prevents `save_csv()` from overwriting history with empty data |
| `resample_daily.py` in hourly pipeline | Ensures all coins have daily candles for signal computation; closes gap between 1h collector and daily-dependent signal pack |

---

## 16. Future Architecture: Trade Database Migration

> **Status:** Planning. Triggered when scaling to multiple live accounts on a DEX.

### 16.1 Why CSV Won't Scale

The current `trades.csv` per-bot design works for single-instance paper/live bots.
It breaks when scaling to multiple accounts:

| Limitation | Impact |
|-----------|--------|
| No concurrent writes | Multiple bot instances can't safely append to the same file |
| No querying | Slicing by account, time range, coin, or P&L requires reading the entire file |
| No atomicity | A crash mid-write can corrupt the CSV; databases handle this natively |
| No cross-account reconciliation | Comparing positions across accounts needs joins, not file parsing |
| No schema enforcement | Malformed rows silently corrupt data |

### 16.2 Target Architecture

```
trades.csv (per-bot)  →  trades table (shared database)
```

**Schema extension:**
```sql
CREATE TABLE trades (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    account_id      TEXT NOT NULL,       -- e.g. 'paper-v14pm', 'live-hl-main'
    deal_id         INTEGER NOT NULL,
    symbol          TEXT NOT NULL,
    open_time       TEXT NOT NULL,
    close_time      TEXT NOT NULL,
    regime          TEXT,
    layers          INTEGER,
    invested        REAL,
    pnl             REAL,
    return_pct      REAL,
    duration_h      REAL,
    recorded_at     TEXT,                -- wall-clock time of recording
    UNIQUE(account_id, symbol, open_time, close_time)
);
```

**Database choice:**
- **SQLite** - simplest path. `candles.db` already uses it. Trades table could
  live in the same file. Sufficient for single-server multi-account deployment.
- **PostgreSQL** - required if multiple servers need write access to the same
  trade ledger (e.g., cloud bot + local bot writing to central DB). Adds
  operational complexity (backup, auth, networking).

**Recommendation:** Start with SQLite (add `trades` table to `candles.db`).
Migrate to Postgres only when multi-server writes become a requirement.

### 16.3 Migration Path

1. Add `trades` table to `candles.db` schema
2. Create `TradeStore` class (read/write/query) replacing CSV file I/O
3. Import existing CSV data into the table (one-time migration script)
4. Update `_write_status()` to query `TradeStore` instead of reading CSV
5. Update `TradeTracker` to write to DB instead of CSV
6. Keep CSV export as a read-only convenience (dashboard, debugging)
7. Add `account_id` to all trade records for multi-account isolation

### 16.4 What This Enables

- **Multi-account dashboard:** Single query across all accounts for total P&L
- **Cross-account analytics:** Which account/strategy performs best on which coins
- **Audit trail:** Immutable trade records with `recorded_at` timestamps
- **Reconciliation queries:** Compare DB trades vs exchange order history
- **Portfolio-level risk:** Aggregate exposure across accounts in real time

---

_Document generated by Gee Gee - 2026-03-09_
_Updated: 2026-03-10 (v1.2 - CSV-as-truth for all bots, exchange API equity for live bot, --fresh loads existing trades, future trade DB architecture)_
_Updated: 2026-04-18 (v1.3 - Aster DEX collector, 50-coin universe, trend multiplier gap resilience, §3.4 exchange migration)_
_Updated: 2026-05-05 (v1.4 - Trade reconciliation system: standalone CLI tool, startup reconciliation, RECONCILE command, deal ID fix. §6.8)_
_Next: Cloud Migration Guide (Phase 5)_
_Audit trail: V14PM_FULL_AUDIT.md, PM_AUDIT_2026-03-10.md_
