# Adaptive Intelligence Trading — V14PM System Architecture
_Version: 1.0 | Date: 2026-03-09 | Status: Cloud-Ready_

---

## 1. System Overview

### 1.1 Product Description

V14PM (V14 Portfolio Manager) is a fully automated crypto trading system built on a
Dynamic Dollar-Cost Averaging (DCA) engine, combined with a capital rotation portfolio
manager. It continuously scans a universe of 44+ coins, scores them by DCA cycle
efficiency, and dynamically allocates capital toward the highest-velocity opportunities.

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
├── openclaw_watchdog.ps1         # Bot watchdog (Windows — runs every 5 min)
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
    ├── collect_scanner_candles.py  # Incremental 1h candle collector
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
```

---

## 3. Data Pipeline

### 3.1 Candle Collection

**Entry point:** `collect_scanner_candles.py`
**Schedule:** Hourly via `AIT_CandleCollector` scheduled task
**Exchange:** Hyperliquid perps (CCXT)
**Coverage:** 44 coins, 1h timeframe, incremental (last stored timestamp forward)

**Flow:**
```
Hyperliquid API
    └─ fetch_ohlcv(symbol, '1h', since=last_stored)
         └─ INSERT INTO candles (symbol, timeframe, timestamp, open, high, low, close, volume)
              └─ candles.db
```

After collection, `v14_cycle_scanner.py` runs automatically to refresh DCA scores.

### 3.2 Database — `candles.db`

**Location:** `trading/spot/data/candles.db` (214 MB, SQLite)
**Env var override:** `AIT_CANDLES_DB`

| Table | Rows | Purpose |
|-------|------|---------|
| `candles` | 1,562,313 | 1h OHLCV for 66 coins |
| `candles_daily` | 74,289 | Aggregated daily OHLCV + 26 indicators |
| `cfgi_daily` | 23,846 | Fear & Greed Index per coin per day |
| `signal_snapshots` | 376 | Daily signal state snapshots |
| `phase_transitions` | 999 | Phase change events with trigger signals |
| `scanner_results` | 438 | Historical scanner scoring runs |
| `trades` | 21 | Closed trade records (all bots) |
| `trade_context` | 3,782 | Per-trade signal context at entry/exit |

**Core schema:**
```sql
-- Raw hourly candles (primary data source)
candles (
    symbol      TEXT,   -- e.g. 'BTC/USDC'
    timeframe   TEXT,   -- '1h'
    timestamp   INTEGER,-- Unix ms
    open REAL, high REAL, low REAL, close REAL, volume REAL
)

-- Daily OHLCV with pre-computed indicators
candles_daily (
    symbol TEXT, date TEXT, timestamp INTEGER,
    open REAL, high REAL, low REAL, close REAL, volume REAL,
    candle_count INTEGER,
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

### 3.3 Daily Indicator Rebuild

`daily_collector.py` (or `build_daily_candles.py` in the engine package) aggregates
1h candles into daily OHLCV and computes all 26 indicators. Run after candle collection
or on demand before a scanner run.

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
- **Realized_PnL** — total closed profit across the simulation window
- **MaxDrawdown%** — worst peak-to-trough during the window
- **Capital_Freedom** — percentage of time capital was *not* trapped (available to redeploy)

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
> for historical reasons — it was written during V13 development. It is **not** V13 trading logic.
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
| HVF score | `test_hvf_daily.py` | High Volume Flush — exhaustion signal |
| 3-check detector | `_steve_3check.py` | Triple confirmation (price/volume/momentum) |
| Fibonacci levels | `v13_router_engine_v1.py` | Support/resistance + extension targets |
| HybridDetector2D | `v13_router_engine_v2.py` | Composite top/bottom detection |
| Fear & Greed | `cfgi_client.py` | Macro sentiment gating |

### 4.5 ROUTER v2 — HybridDetector2D

The top/bottom detection engine used to transition between `LONG_DCA` → `ROUTER` → 
`SHORT_DCA` phases. Combines:
- StochRSI overbought stack (2w K ≥ 93 threshold)
- 3-check confirmation
- HVF exhaustion signal
- Fibonacci extension proximity
- ADX trend confirmation

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

**LONG_DCA** — Building a long position via DCA grid. Each layer triggered by
price dropping `SO_DEVIATION` below previous layer. Takes profit when average
entry rises to `TP_PCT` above average cost. Re-enters immediately after TP hit.

**ROUTER** — Evaluating market regime. ROUTER v2 (HybridDetector2D) determines
whether the market is topping (→ SHORT_DCA) or false alarm (→ back to LONG_DCA).

**SHORT_DCA** — Mirror of LONG_DCA for short positions (Hyperliquid perps only).
Triggered by confirmed top signal. Same grid mechanics, inverted direction.

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

All state is written to JSON after every cycle:

**`state.json`** — Complete bot position state:
```json
{
  "phase": "LONG_DCA",
  "layers": [...],
  "avg_entry": 0.4821,
  "total_invested": 12340.00,
  "last_update": "2026-03-09T10:49:42Z"
}
```

**`status.json`** — Health metrics (read by heartbeat monitor):
```json
{
  "running": true,
  "symbol": "ASTER/USDT",
  "phase": "LONG_DCA",
  "layer_count": 4,
  "total_invested": 312.32,
  "unrealized_pnl_pct": -2.83,
  "max_drawdown_pct": 2.83,
  "last_update": "2026-03-09T10:49:42Z"
}
```

### 6.3 Equity Calculation (V14PM)

The PM runner computes equity from ground truth, not engine internals:

```
Equity = Capital + Realized PnL - Fees + Unrealized PnL
```

- **Realized PnL** is sourced from `trades.csv` (source of truth across restarts),
  falling back to engine-reported values for the current session.
- **Unrealized PnL** is summed from each engine's per-coin status.
- **Uptime / Daily ROI** uses the earliest trade timestamp from `trades.csv`,
  not the process start time, so metrics survive restarts.

> **Why not sum engine equities?** Daily rebalance can inject cash into engines
> (via `eng.capital = max(eng.capital, new_alloc - invested)`) without updating
> `initial_capital`. Summing engine equities + unallocated capital double-counts
> the injected cash. The ground-truth formula avoids this entirely.

### 6.4 Trade History Preservation

`TradeTracker.load_existing()` is called on startup to load historical trades from
`trades.csv` into memory. This ensures:
- Deal counts and win rates include all historical trades
- Realized PnL reflects cumulative performance, not just the current session
- `save_csv()` appends new trades without overwriting history

**Important:** Do not use `--fresh` on restarts — it skips candle backfill (correct)
but also creates fresh engines that lose position state. Use `--skip-backfill` instead
for the live bot. The PM scheduled task omits `--fresh`.

### 6.5 Startup Reconciliation

On every restart, the engine reconciles with the live exchange:
1. Load `state.json` (restored position state)
2. Fetch real balances from exchange
3. Compare engine state vs. exchange state
4. Log drift; abort if drift exceeds threshold ($5 default)
5. Enter trading loop

`--skip-backfill` flag skips historical candle replay (use for restarts — state.json
already has valid signal context).

### 6.5 Engine Warmup Period

On fresh starts, each `V14LifecycleEngine` requires a **warmup period** before trading:

- Engines start with `_warmed_up = False`
- During warmup: candles are accumulated and price is tracked, but **no DCA ticks fire** (no entries)
- At the **first daily boundary** (midnight UTC): the full daily tick runs — signal pack refreshes,
  ROUTER evaluates direction (long vs short), signals compute. `_warmed_up` flips to `True`.
- After warmup: hourly DCA ticks run normally, entering positions based on router-directed phase

**Why:** Without warmup, engines default to `LONG_DCA` and enter L1 on the first candle they see,
before the router has evaluated whether the market direction warrants long or short. In a bear
market, this could mean entering 10 long positions right before the router would say "go short."

**Exceptions:** Engines restored from saved state (`restore_state()`) are immediately `_warmed_up = True`
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

Every trade record includes a `recorded_at` UTC timestamp — the wall-clock time when the trade
was actually written, distinct from `close_time` (when the trade claims to have closed).

- **Real trade:** `recorded_at ≈ close_time` (within minutes)
- **Phantom trade:** `recorded_at` is hours/days after `close_time` (backfill replay)

This field is the forensic backstop: even if all other safeguards fail, phantom trades can always
be identified and removed by comparing `recorded_at` vs `close_time`.

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

### 7.2 CapitalRouter — Allocation Rules

**Pool split:**
- **Active Pool (75%):** Deployed capital for DCA positions
- **Reserve Pool (25%):** Held back for new opportunities and drawdown buffer

**Equity-tiered coin cap:**

| Portfolio Equity | Max Simultaneous Coins |
|-----------------|------------------------|
| $50,000+ | 10 |
| $25,000–$50,000 | 5 |
| $10,000–$25,000 | 4 |
| $5,000–$10,000 | 3 |
| $1,000–$5,000 | 2 |
| $100–$1,000 | 1 |

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

### 7.4 Current Paper Performance (2026-03-09, corrected)

- **Capital:** $50,000 paper
- **Equity:** ~$50,480 (+0.96%)
- **Realized PnL:** $479.65 | Win rate: 100% (20 deals) | Drawdown: 0.0%
- **Active coins:** ZRO, NEAR, DOT, PENDLE, INJ, ENS, TAO, HYPE, JUP, SNX (10/10 slots)
- **Regime:** RANGING — DCA grids cycling TPs in sideways market
- **Daily ROI:** ~0.39%

> **Note:** Earlier equity figures (~$54K) were inflated by a bug in `_write_status()` that
> double-counted capital when daily rebalance increased engine allocations. Fixed 2026-03-08.
> See CODE_AUDIT_FINDINGS.md §C2 for the related `_steve_3check.py` DB path bug.

---

## 8. Exchange Client (`trading.spot.exchange_client`)

### 8.1 Supported Exchanges

| Exchange | Type | Use |
|----------|------|-----|
| Hyperliquid | Perps (CCXT) | V14PM live + all paper bots |
| Aster DEX | Spot (CCXT) | V14 live bot only |

### 8.2 Credential Resolution (Priority Order)

1. **Explicit config dict** passed at construction
2. **Environment variables** — `HYPERLIQUID_API_KEY` / `HYPERLIQUID_API_SECRET`
3. **Windows Registry** (Windows-only fallback — silent no-op on Linux)

**Critical:** On Linux/cloud servers, env vars **must** be set. The Windows Registry
fallback is unavailable. If credentials are missing, the client raises `ValueError`
at initialization (fail-fast — does not attempt to connect unauthenticated).

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
    ├─ git add docs/   ← ONLY docs/ — never stages source files
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
| `V14PMPaperBot` | At logon | `run_v14_portfolio_paper.py` | V14PM paper bot (no `--fresh`) |
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
- `running: true` — bot has not errored out
- `last_update` timestamp — must be < 65 minutes old
- `max_drawdown_pct` — alert if > 15% (live bot only)

### 11.3 AIT_Watchdog

Runs every 5 minutes. Monitors:
1. **OpenClaw Gateway** — restarts if process not found
2. **V14PaperBot** — restarts scheduled task if not running or status stale > 2h
3. **V14ETFPaperBot** — same
4. **V14PMPaperBot** — same
5. **V14LiveAster** — same

Log: `~/.openclaw/watchdog.log`

---

## 12. Environment Variables — Complete Reference

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

## 13. CLI Reference — Launch Commands

### V14PM Paper Bot
```bash
python -u -m trading.spot.run_v14_portfolio_paper \
  --capital 50000 \
  --profile high \
  --leverage 1.0 \
  --exchange hyperliquid \
  # --fresh         # First launch ONLY — skips backfill. OMIT on restarts (preserves trade history)
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
> Note: `run_v14_portfolio_live.py` does not yet exist — must be created as part
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
| `--skip-backfill` on restart | State.json already warm; avoids unnecessary API calls on reconnect |
| Ground-truth equity calc | `Capital + Realized - Fees + Unrealized` from trades.csv; avoids engine internal drift |
| `load_existing()` on startup | Trade history survives restarts; CSV is source of truth for realized PnL |

---

_Document generated by Gee Gee — 2026-03-09_
_Next: Cloud Migration Guide (Phase 5)_
