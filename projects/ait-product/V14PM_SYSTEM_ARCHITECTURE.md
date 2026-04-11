# Adaptive Intelligence Trading — V14PM System Architecture
_Version: 1.6 | Date: 2026-03-21 | Status: Production — Live on Aster Perps_

---

## Executive Summary

V14PM is an automated crypto portfolio trading system. Here's what it does,
in plain English.

### What It Does

The system watches 50 cryptocurrencies, picks the best one to trade right now,
buys it in layers as the price dips, and sells for a small profit (1.5%).
Then it rotates to the next best opportunity. Rinse and repeat, 24/7.

### How It Makes Decisions

1. **The Scanner** looks at all 50 coins every day and asks: "Which coin is
   completing the most profitable buy-low-sell-high cycles right now?" It scores
   each coin by speed, profitability, and risk. The best scorer gets the capital.

2. **The Grid Engine** manages the actual trading. When it enters a coin, it
   doesn't go all-in. It buys a starter position (~40% of allocation) and places
   up to 12 more buy orders at progressively lower prices. If the price dips,
   it buys more at better prices, lowering its average. When the price recovers
   just 1.5% above the average, it sells everything for a profit.

3. **The Regime Monitor** watches for market-wide danger signs. If half the coins
   start showing topping signals, it sends a Telegram alert. No automatic panic
   selling — Brett decides whether to wind down positions.

### Key Safety Features

| Feature | What It Does | Why It Matters |
|---------|-------------|----------------|
| **1x Leverage** | No borrowing, no liquidation risk | You can't lose more than you put in |
| **Exchange Is Truth** | Position state synced from exchange every 65s cycle | Engine can never diverge from reality |
| **Resting Limit Orders** | Exchange handles take-profit, not the bot | Even if the bot crashes, your TP order sits on the exchange. TP price is always computed from the actual exchange entry price (not engine's candle-based estimate) to account for spread/slippage. |
| **Pre-Order Exchange Checks** | Every BUY checks `fetch_balance()`, every SELL checks `fetch_open_positions()` | No order executes without exchange confirmation that the prerequisite exists (cash for buys, position for sells) |
| **Leverage Enforcement** | `ensure_leverage()` called per symbol at first trade | Sets 1x on Aster (which defaults to 5x Cross). Note: `_leverage_set` is not persisted to state.json — on restart with no open positions, leverage is re-verified at next trade entry. |
| **Human Approval** | Direction changes require Telegram confirmation | The bot never flips strategy on its own |
| **PAUSE/RESUME** | Freeze all trading with one command | Instant kill switch, existing TPs stay active |
| **No Engine Position Tracking** | Engine doesn't maintain its own position state | Eliminates entire class of drift/divergence bugs |

### How Capital Flows

```
$350 USDT (Aster Perps account)
  │
  ├── 90% Active Pool ($315)        ← Adaptive: 90/10 below $10K
  │     └── Deployed to top-ranked coins (up to 3 slots at current equity)
  │           └── DCA grid: layers at 1.5% spacing
  │                 └── TP hit → profit returned → rotate to next coin
  │
  └── 10% Reserve Pool ($35)        ← Scales to 25% at $20K+
        └── Held back for deep DCA layers (6+) and new opportunities
```

As equity grows, more coins trade and the pool split adjusts:

| Your Equity | Coins Trading | Pool Split | Effect |
|-------------|--------------|------------|--------|
| $350 (now) | 3 | 90/10 | Max turnover, thin reserve OK |
| $3,000 | 4 | 90/10 | Demo phase: turnover + depth |
| $5,000 | 5 | 90/10 | Aggressive turnover |
| $10,000 | 5 | 80/20 | Intermediate (avoids cliff) |
| $20,000+ | 5 | 75/25 | Proven paper profile |
| $100,000+ | 10 | 75/25 | Full rotation |

Tier transitions use **5% hysteresis**: upgrades are immediate at threshold;
downgrades only trigger when equity drops 5% below the current tier's threshold
(prevents flapping from normal PnL fluctuation).

### The Components

| Component | Role | Analogy |
|-----------|------|---------|
| **Cycle Scanner** | Ranks coins by DCA efficiency | The talent scout |
| **Capital Router** | Allocates money across coins | The portfolio manager |
| **DCA Grid Engine** | Generates buy/sell signals from candle data | The analyst |
| **Exchange Sync** | Overwrites engine state from exchange every cycle | The auditor |
| **Regime Monitor** | Watches for market-wide shifts | The risk officer |
| **Telegram Interface** | Human oversight and commands | The control panel |
| **Dashboard** | Real-time visualization on GitHub Pages | The scoreboard |

### Current Status (2026-03-21)

- **Live on Aster Perps** with ~$340 real USDT
- Scanner selected GRASS/USDT as first coin (top 30d DCA scorer)
- 3 coin slots at current equity (Upgrade 0: adaptive tiers, 2026-03-24); scales to 10
- **Adaptive pool split** (2026-03-24): 90/10 at current equity, scales to 75/25 at $20K+
- **5% hysteresis** on tier transitions prevents flapping at boundaries
- **Exchange-as-truth architecture** (2026-03-21): positions synced from exchange every cycle
- Resting limit orders for TP execution, Telegram commands operational
- Dashboard shows correct exchange-derived equity, invested, and P&L

---

## 1. System Overview

### 1.1 Product Description

V14PM (V14 Portfolio Manager) is a fully automated crypto trading system built on a
Dynamic Dollar-Cost Averaging (DCA) engine, combined with a capital rotation portfolio
manager. It continuously scans a universe of **50 coins**, scores them by DCA cycle
efficiency, and dynamically allocates capital toward the highest-velocity opportunities.

The system runs in production on **Aster DEX Perpetuals** at 1x leverage (no liquidation
risk). All coins trade in the same direction (global Long or Short), with direction
changes requiring human approval. The core engine is exchange-agnostic via CCXT.

**Key architectural principles (2026-03-19):**
- All trading on Aster Perps — no Spot, no dual-account management
- Unified risk profile (High grid, 1x leverage, 30d scanner window)
- Global strategy direction — all coins Long or all Short, never mixed
- Exchange is truth — LIVE GUARD, resting limit orders, actual fill prices
- Human-in-the-loop for regime changes — Telegram APPROVE/DENY
- Binance for candle backfill, Aster for live price data

### 1.2 Design Philosophy

- **Signal-first:** Never enter a position without qualifying signal confirmation
- **DCA-only exits:** All positions exit at a fixed take-profit above average entry
- **Capital rotation:** Close winners fast, redeploy to the next best opportunity
- **No manual intervention:** Fully autonomous from candle collection to order execution
- **Exchange is truth (live bots):** For live trading, exchange balances and fill prices
  are authoritative. Engine state is never used as a source of fill prices or position
  truth. All live bot capital calculations reflect actual exchange proceeds. Engine TP
  sells are blocked when an active exchange limit order exists (LIVE GUARD pattern).

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
├─────────────────────────────────────────────────────────────┤
│  EXCHANGE LAYER (LIVE BOTS ONLY)                            │
│  Resting Limit Orders · Fill Verification · LIVE GUARD     │
└─────────────────────────────────────────────────────────────┘
```

### 1.4 Active System Components

| Component | Entry Point | Exchange | Capital | Notes |
|-----------|------------|----------|---------|-------|
| **V14PM Live** | `run_v14_portfolio_live_aster.py` | Aster Perps | $350 real | **Production.** Live since 2026-03-19. All safeguards active. |
| V14PM Paper | `run_v14_portfolio_paper.py` | Hyperliquid (sim) | $50K paper | Benchmark / demo |
| V14 Paper | `run_v14_paper.py` | Hyperliquid (sim) | $10K paper | Benchmark / demo |
| V14 Live (legacy) | `run_v14_live_aster.py` | Aster Spot | — | **RETIRED 2026-03-19.** Replaced by V14PM Live. |

> **V14-ETF Paper Bot RETIRED (2026-03-17):** HBAR autonomously switched to DCA Short
> direction and suffered significant losses. Lesson learned: Long↔Short strategy direction
> changes require human-in-the-loop approval. Scheduled task unregistered. State preserved
> at `paper/v14etf/status.json.retired`.

### 1.5 Class & Module Quick Reference

Quick reference for all primary classes in the V14PM system. For full method-level details
and per-function traces, see `V14PM_CODE_AUDIT_2026-03-21.md`.

| Class | File | Description |
|-------|------|-------------|
| `BotState` | `run_v14_portfolio_live_aster.py` | Named constants for bot operational state (`RUNNING` / `PAUSED` / `WIND_DOWN`) |
| `TradeTracker` | `run_v14_portfolio_live_aster.py` | Records closed trade history to `trades.csv`; tracks open deals and per-coin PnL |
| `AsterPerpClient` | `run_v14_portfolio_live_aster.py` | Aster DEX Perpetuals exchange client; wraps `ccxt.aster` with perp-specific helpers |
| `CoinState` | `run_v14_portfolio_live_aster.py` | Tracks live state for a single coin slot (TP order ID, layer count, funding, candle timestamp) |
| `V14PortfolioLiveAster` | `run_v14_portfolio_live_aster.py` | Main bot class; orchestrates all trading logic, Telegram commands, and state persistence |
| `CapitalRouter` | `v14_capital_manager.py` | Manages capital distribution across active coins (adaptive pool split + equity-tiered coin cap with 5% hysteresis) |
| `V14LifecycleEngine` | `v14_lifecycle_engine.py` | Per-coin live wrapper around `V14DCAEngine`; manages signal pack, daily ticks, state persistence |
| `V14DCAEngine` | `engine/v14_dca_engine.py` | DCA phase machine + grid; generates `BUY`/`SELL` actions from candle data |
| `V13SignalPack` | `engine/v13_signals.py` | StochRSI, ADX, HH/HL structure detectors; shared signal library for V13 and V14 engines |
| `HybridDetector2D` | `engine/v13_router_engine_v2.py` | Composite top/bottom detection (2D RSI divergence + 3D SMA death cross) |
| `V13BacktestV8` | `engine/v13_phase_backtest_v8.py` | Backtest engine for historical phase simulation (not used in live trading) |
| `SpotExchangeClient` | `exchange_client.py` | Universal exchange client for Hyperliquid + Aster (used by paper bots; imported but **not used** by the live PM bot) |

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
    ├── run_v14etf_paper.py         # V14-ETF paper bot runner (RETIRED — do not restart)
    ├── run_v14_live_aster.py       # V14 live bot runner (Aster Spot — LEGACY, retired)
    ├── run_v14_portfolio_live_aster.py # V14PM live bot (Aster Perps — PRODUCTION)
    ├── run_v14_scanner.py          # Manual scanner runner
    ├── run_daily_collector.py      # Manual collector runner
    │
    ├── collect_scanner_candles.py  # Incremental 1h candle collector (Step 1)
    ├── resample_daily.py           # 1h → daily OHLCV resampling (Step 1.5)
    ├── backfill_scanner_coins.py   # Historical candle backfill
    ├── backfill_binance.py          # One-time deep history backfill from Binance Futures (50 coins)
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
    │       ├── state.json          # Bot position state (includes _tp_order_id)
    │       ├── status.json         # Health/metrics (updated every ~1h)
    │       ├── trades.csv          # Trade history
    │       └── bot.log             # Runtime log
    │
    ├── live/v14pm/                 # V14PM live bot state (Aster Perps — PRODUCTION)
    │   ├── .env.template           # Credential template
    │   ├── state.json              # Bot + engine state (persisted across restarts)
    │   ├── status.json             # Health/metrics (updated every 60s)
    │   ├── trades.csv              # Closed trade history
    │   ├── bot.pid                 # PID lock file
    │   └── bot.log                 # Runtime log
    │
    └── paper/
        ├── v14/                    # V14 paper bot state
        ├── v14etf/                 # V14-ETF paper bot state (RETIRED)
        │   └── status.json.retired # Renamed on 2026-03-17 retirement
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
**Exchange:** Aster DEX Perps (CCXT) — switched from Hyperliquid 2026-03-19
**Coverage:** 50 coins (Aster Perps universe), 1h timeframe, incremental
**Deep history:** Binance Futures backfill via `backfill_binance.py` (one-time, 722K candles)

**Three-step hourly pipeline:**
```
Step 1: collect_scanner_candles.py
  Aster Perps API (ccxt.aster, defaultType=future)
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

### 3.2 Database — `candles.db`

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
| `candles_daily` | ~99,000 | Daily OHLCV (two sources — see below) |
| `cfgi_daily` | 23,846 | Fear & Greed Index per coin per day |
| `signal_snapshots` | 376 | Daily signal state snapshots |
| `phase_transitions` | 999 | Phase change events with trigger signals |
| `scanner_results` | 438 | Historical scanner scoring runs |
| `trades` | 21 | Closed trade records (all bots) |
| `trade_context` | 3,782 | Per-trade signal context at entry/exit |

**`candles_daily` has two data sources:**
1. **`build_daily_candles.py`** — aggregates 1h candles AND computes 26 indicators
   (SMA, ADX, RSI, etc.). These rows have all indicator columns populated.
2. **`resample_daily.py`** — simple 1h → daily OHLCV aggregation only. These rows
   have indicator columns as NULL. Used for coins added via Hyperliquid collector
   that `build_daily_candles.py` hasn't processed yet.

Both use `INSERT OR IGNORE` — they don't overwrite each other. The V13SignalPack
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

### 3.3 Daily Data — Two Paths

There are two distinct processes that populate `candles_daily`:

1. **`resample_daily.py`** (runs hourly in pipeline) — Simple 1h→daily OHLCV
   aggregation. Ensures all coins have daily candles regardless of whether they've
   been through the full indicator build. This is the **critical** path — without it,
   coins only available on Hyperliquid have zero daily data, and their signal packs fail.

2. **`build_daily_candles.py`** (engine package) — Full aggregation + 26 indicator
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
- **Realized_PnL** — total closed profit across the simulation window
- **MaxDrawdown%** — worst peak-to-trough during the window
- **Capital_Freedom** — percentage of time capital was *not* trapped (available to redeploy)

**Simulation parameters (High Profile):**
```
Base Order:      30% of allocation  (DCA_BO_PCT = 0.30)
Safety Order deviation: 1.5% per layer
Safety Order multiplier: 1.5x volume per layer
Max layers:      12  (DCA_MAX_LAYERS = 8 default; overridden to 12 by High profile)
Take Profit:     1.5% above average entry
Taker fee:       0.035% (Aster Perps)
```

**Scan windows:** 7d, 14d, 30d, bear (extended lookback)

**Minimum history:** 6 months of 1h candles required to appear on dashboard rankings

> **Scanner fix (2026-03-18):** Best/Fastest/Safest summary picks in `cycle_scanner.json`
> are now derived from the top 5 scored coins only (`scored_rankings[:5]`), not the full
> coin universe. This ensures summary picks are drawn from genuinely high-performing coins.

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

**50 coins on Aster Perps** (updated 2026-03-19):

**Established (pre-2024):** BTC, ETH, SOL, XRP, LINK, DOGE, ADA, LTC, AVAX, DOT,
UNI, ATOM, NEAR, HBAR, INJ, FIL, CRV, SNX, ZEC

**DeFi/Mid-cap:** AAVE, ARB, JUP, PENDLE, STX, ZRO

**High-beta/Speculative:** PEPE, BONK, FLOKI, JTO, PYTH, TIA, SEI, APT, SUI

**AI/Infrastructure:** FET, TAO, HYPE, VIRTUAL, RENDER

**New L1/L2:** BERA, MOVE, INIT, S, IP

**Yield/RWA:** ONDO, EIGEN, ENA

**DePIN/Other:** GRASS, ORCA, TRUMP

> **Changes from v1.3 (2026-03-19):**
> - **Added 13 coins:** ONDO, RENDER, VIRTUAL, BERA, MOVE, INIT, IP, S, EIGEN, ENA, GRASS, ORCA, TRUMP
> - **Dropped 9 coins (not on Aster Perps):** BAL, COMP, ENS, GMX, GRT, MANA, RUNE, SAND, WIF
> - All 50 coins trade as `{COIN}USDT` perpetual on Aster DEX
> - 3 coins use 1000-prefix on exchanges: PEPE→1000PEPE, BONK→1000BONK, FLOKI→1000FLOKI
> - **Candle data:** Historical backfill from Binance Futures (deep history for ROUTER
>   signals). Live collection from Aster Perp API. Both stored in `candles.db`.
> - 38 coins have full ROUTER signal coverage (≥600 days). 12 newer coins have
>   partial coverage — can trade and contribute to top detection, but bottom detection
>   (3D SMA200 death cross) requires ~600 days to become valid.

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

### 4.5 ROUTER v2 — Phase Transition Signal Stack

The V14DCAEngine uses a layered signal stack to detect tops and bottoms for phase
transitions between `LONG_DCA` and `SHORT_DCA`.

**Top Detection (during LONG_DCA → triggers switch to SHORT_DCA):**

| Layer | Signal | Action |
|-------|--------|--------|
| 1: Early Warning | 1W StochRSI K crosses below 97 | Start unwinding (stop new DCA entries, let TPs hit) |
| 2: OB93 Arm | 2W StochRSI K crosses below 93 | ARM — wait for divergence confirmation |
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

**LONG_DCA** — Building a long position via DCA grid. Each layer triggered by
price dropping `SO_DEVIATION` below previous layer. Takes profit when average
entry rises to `TP_PCT` above average cost. Re-enters immediately after TP hit.

**ROUTER** — Evaluating market regime. ROUTER v2 (HybridDetector2D) determines
whether the market is topping (→ SHORT_DCA) or false alarm (→ back to LONG_DCA).

**SHORT_DCA** — Mirror of LONG_DCA for short positions (Hyperliquid perps only).
Triggered by confirmed top signal. Same grid mechanics, inverted direction.

### 5.2 DCA Grid Mechanics

```
Base Order (BO) = capital × DCA_BO_PCT (30%)   ← DCA_BO_PCT = 0.30 in code

Layer 0 (Base): BO amount at entry price
Layer 1: BO × SO_VOL_MULT at (entry × (1 - SO_DEV))
Layer 2: Layer1_size × SO_VOL_MULT at (Layer1_price × (1 - SO_DEV × price_multiplier))
...
Layer N: where N = DCA_MAX_LAYERS (default 8; High profile overrides to 12)

Take Profit: when avg_entry × (1 + DCA_TP_PCT) ≤ current_price → SELL ALL
```

**TP Fill Model (updated 2026-03-17):** TP detection now checks candle **high** (for longs)
and candle **low** (for shorts), not candle close. This ensures wicks that touch the TP price
trigger a fill at the TP price, matching the behavior of a resting exchange limit order.
Previously, the engine could miss TPs when the wick touched the TP level but the candle
closed below it. Files updated: `v14_dca_engine.py`, `v14_lifecycle_engine.py`.

**TP Price — Exchange-as-Truth (updated 2026-03-24):** `_place_tp_order()` computes the TP
price from the **actual exchange entry price**, not the engine's candle-based TP. The engine
processes historical candles and computes TP from the candle close price, but the actual fill
price can differ significantly due to spread/slippage (observed: 5.1% spread on HYPE entry).
Using the engine's TP could result in a sell limit below the actual entry price, which the
exchange correctly rejects. The flow is now:
1. Engine tick generates BUY at candle close price → market buy executes at actual price
2. `_place_tp_order()` fetches exchange position entry price via `fetch_open_positions()`
3. TP = `exchange_entry × (1 + DCA_TP_PCT)` — always above actual cost basis
4. If fetch fails, falls back to engine's `eng.long_tp` (best effort)
5. TP recovery (`_check_tp_fills`) retries placement for any position missing a TP order

**Layer timing:** There is no cooldown between layers at any risk profile (Low,
Medium, or High). When price drops through multiple deviation thresholds, the
grid fills all qualifying layers on the next tick. The deviation check
(`current_drop >= SO_DEV × layer_count`) is the sole gate for adding layers.
This ensures the grid reacts immediately to volatility and captures rapid dips
for faster TP recovery.

> **History (2026-03-11):** A legacy 1-day cooldown guard was discovered in
> `v14_dca_engine.py` — originally a backtest artifact (daily candles = no effect)
> that silently throttled live bots running on 1h candles to one layer per day.
> Removed as it was never part of the tested/documented grid design and actively
> harmed DCA performance during volatile moves.

### 5.3 Risk Profiles

#### Production Profile (Unified — decided 2026-03-18)

For initial production deployment, V14PM uses a **single unified profile** — the
proven High grid at 1x leverage with a 30d scanner window. Risk tiers are deferred
until production data justifies differentiation.

| Parameter | Production Value |
|-----------|-----------------|
| Leverage | **1.0x** (no liquidation risk) |
| Base Order | **30%** (DCA_BO_PCT = 0.30) |
| SO Deviation | 1.5% |
| SO Multiplier | 1.5x |
| Max Layers | **12** (DCA_MAX_LAYERS default=8; High profile=12). **Effective depth: ~4 layers** — Martingale sizing depletes the per-coin allocation by L4 (L1=30%, L2≈31.5%, L3≈26%, L4=remainder). See §5.2.1. |
| Take Profit | 1.5% |
| Scanner Window | 30d |
| Trend Multiplier | Yes (0.3–1.5x) |

> **§5.2.1 — Grid Capital Mechanics (revised 2026-04-11)**
>
> The DCA grid uses a Martingale formula: `order = remaining_capital × BO_PCT × SO_MULT^min(layer, 4)`.
> With `BO_PCT=0.30` and `SO_MULT=1.5x`, the allocation naturally depletes in ~4 layers:
>
> | Layer | % of Allocation | Cumulative |
> |-------|----------------|------------|
> | L1 | 30.0% | 30.0% |
> | L2 | 31.5% | 61.5% |
> | L3 | 26.0% | 87.5% |
> | L4 | 12.5% (remainder) | 100.0% |
>
> This is by design: the strategy prioritizes **capital velocity** — large L1 orders cycle
> at 1.48% net profit quickly (69% of deals are L1), while L2-L4 provide downside averaging
> within the allocation. The `DCA_MAX_LAYERS=12` config serves as a ceiling but is not expected
> to be reached under normal Martingale sizing. 365-day backtest: 81.4% annual ROI (long-only,
> $50K, 5 coins), zero pool denials, 702 completed deals.
>
> **Capital accounting**: The engine tracks `remaining = allocated_capital - long_cost`.
> Each layer calculates its order from what's actually left to spend, preventing any single
> coin from overspending its allocation into the shared pool.

#### Legacy Profiles (paper bots / backtesting only)

These profiles remain available for paper bots and backtesting but are **not used
in production**:

| Profile | Leverage | BO% | SO Dev | SO Mult | Max Layers | TP |
|---------|----------|-----|--------|---------|------------|----|
| `low` | 1.0x | 40% | 2.0% | 1.5x | 10 | 1.5% |
| `medium` | 1.5x | 40% | 2.0% | 1.5x | 10 | 1.5% |
| `high` | 1.5x | 40% | 1.5% | 1.5x | 12 | 1.5% |

> **Future:** Risk tiers may be reintroduced once production performance data
> supports it. Planned differentiation: scanner window (14d for aggressive vs 30d
> for moderate) rather than grid parameters. All tiers would remain 1x leverage.

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
     (LIVE GUARD: blocked if _tp_order_id is set — exchange limit order takes priority)
  4. Check phase transition signals → update phase if warranted
  5. Check for new DCA layer entry → execute buy if triggered
  6. Write state.json + status.json

At midnight UTC (daily signal evaluation):
  1. Load candles_daily from candles.db
  2. Run full signal stack (HVF, 3-check, Fibonacci, HybridDetector2D)
  3. Update ROUTER evaluation
  4. Write signal snapshot to DB
  5. [Live mode only] Run TP catch-up check against current candle (§6.9)
```

### 6.2 State Persistence

The PM bot writes two state files every cycle (~60 seconds):

**`engine_state.json`** — Complete engine state for restart recovery (PM-specific):
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
and state is still restored — signals will refresh on the next daily boundary.

**`status.json`** — Health metrics (read by heartbeat monitor and dashboard):
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
> for its single engine. The PM bot does NOT use `state.json` — all its state is
> in `engine_state.json`, which covers all 10 engines, the router, and open deals.

### 6.3 Equity Calculation (All Bots)

**All bot runners** compute equity from ground truth, not engine internals:

```
Equity = Capital + CSV Realized PnL - Fees + Unrealized PnL
```

- **Realized PnL** is **always** sourced from `trades.csv` — the CSV is the
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
> were not. On restart, engine counters could reset, inflate, or drift — producing
> incorrect dashboard numbers while the CSV remained accurate. The fix applies to
> all runners: `run_v14_paper.py`, `run_v14_portfolio_paper.py`, and
> `run_v14_live_aster.py`.

### 6.3.1 Live Bot Equity & Exchange Interaction (Aster)

The V14 Live bot (Aster) treats the **exchange as the ultimate source of truth**.
Multiple safeguards ensure engine state can never override real exchange positions.

**Equity calculation:**
```
Live Equity = USDT Balance + (Base Coins × Current Price)
```
Fetched from exchange API every cycle. Overrides the CSV-based calculation.

**Resting Limit Orders (implemented 2026-03-17):**
After every BUY fill, the bot places a resting limit sell order on the exchange at
the TP price for the full position size. This eliminates poll-dependent TP execution:
- Bot process dies → limit order still on book, fills automatically
- Exchange API errors → bot is blind, but exchange executes the order
- Wick touches TP but candle closes below → limit sell fills on touch

Implementation details:
- After BUY fill → cancel old TP order, place new limit sell at updated TP price for full position
- On startup → recover `_tp_order_id` from `state.json` or place fresh if missing
- Each poll cycle → check if limit order was filled; if yes, sync engine state
- Phase change → cancel TP order before transition
- Engine candle-based TP detection retained as fallback (belt and suspenders)
- `_tp_order_id` persisted in `state.json` for crash recovery

New `SpotExchangeClient` methods: `place_limit_sell()`, `cancel_tp_order()`, `check_order_status()`

**LIVE GUARD Pattern (implemented 2026-03-18 — incident response):**
When `_tp_order_id` is set (a TP limit order is active on the exchange), all engine-initiated
TP sells are **BLOCKED** and engine state is **ROLLED BACK** to pre-sell values. Only
non-TP exits (phase close, signal exit) can override the exchange limit order.

Root cause this addresses: the daily tick (which uses previous-day OHLC) could trigger an
internal TP sell even while an exchange limit order was active. On 2026-03-18, previous-day
high (~$0.78) exceeded TP ($0.7436) → engine cancelled exchange limit order → market sold at
~$0.69 → $22 loss. LIVE GUARD prevents the engine from ever overriding an active exchange
limit order with a TP sell. See §17.2 for full incident record.

**Fill price handling (implemented 2026-03-18):**
`execute_sell()` and `execute_buy()` now fetch the current ticker price if the exchange API
does not return a fill price. **Engine TP prices are never used as fill price substitutes.**
This corrects a pre-incident bug where fill price fell back to the engine's internal TP price
($0.7436) instead of the actual exchange fill price (~$0.69), causing incorrect PnL.

**PnL and capital correction:**
- PnL is calculated from actual exchange proceeds, not engine TP-price math
- Engine capital is corrected after sells to reflect actual vs. expected proceeds
- Startup reconciliation compares engine state vs. exchange balances and corrects drift
  (caught and corrected $22.73 drift from the 2026-03-18 incident on next restart)

**exchange_balance in status.json:**
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
1. Acquire PID lock (`bot.pid`) — exit if another instance is running
2. Load trade history from `trades.csv` (`TradeTracker.load_existing()`)
3. If `--fresh`: skip state restore, proceed to step 5
4. **State restore:** Load `engine_state.json` → reconstruct all engines with
   positions, phases, indicators, last candle timestamps. Restore router state
   (pool cash, allocations). Restore open deals.
5. Run initial rebalance (`_check_and_rebalance()`) — if engines were restored,
   this updates allocations; if fresh start, this creates new engines.
6. Enter live trading loop

> **Live bot startup:** Exchange balance reconciliation runs after step 4.
> Compare engine state vs. real balances, log drift, correct automatically.
> Paper bots skip this since they don't interact with real exchange positions.

### 6.5.1 Engine Warmup Period

On fresh starts, each `V14LifecycleEngine` requires a **warmup period** before trading:

- Engines start with `_warmed_up = False`
- During warmup: candles are accumulated and price is tracked, but **no DCA ticks fire** (no entries)
- At the **first daily boundary** (midnight UTC): the full daily tick runs — signal pack refreshes,
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

Every trade record includes a `recorded_at` UTC timestamp — the wall-clock time when the trade
was actually written, distinct from `close_time` (when the trade claims to have closed).

- **Real trade:** `recorded_at ≈ close_time` (within minutes)
- **Phantom trade:** `recorded_at` is hours/days after `close_time` (backfill replay)

This field is the forensic backstop: even if all other safeguards fail, phantom trades can always
be identified and removed by comparing `recorded_at` vs `close_time`.

### 6.8 Live Trading Safeguards

> **This section is the authoritative reference for all live bot exchange interaction patterns.**
> **Major revision 2026-03-21:** Exchange-as-truth architecture replaces LIVE GUARD, engine
> rollbacks, and reconciliation. See §6.8.1 for the new architecture.

#### 6.8.1 Exchange-as-Truth Architecture (2026-03-21)

The live PM bot uses the exchange API as the **single source of truth** for all position data.
Every main loop cycle (65 seconds), `_sync_positions_from_exchange()` overwrites the engine's
internal position state (long_coins, long_cost, avg_entry, TP level) from the exchange API.

**What the engine does:** Signal generation only — processes candles to decide WHEN to buy/sell
(DCA levels, TP targets, phase transitions).

**What the engine does NOT do:** Track positions. All position data comes from the exchange.
The engine's internal position fields are ephemeral — overwritten from exchange every cycle.

**What was removed (no longer needed):**
- LIVE GUARD (engine TP blocking when exchange order active)
- Pre-tick snapshots and engine state rollbacks
- Startup reconciliation (`_reconcile_with_exchange()`)
- Periodic reconciliation (`_periodic_reconcile()`)
- Engine state correction after BUY/SELL fills

**Why:** The previous architecture inherited from the paper bot, where the engine simulates
positions from candle ticks. In live trading, this created two sources of truth that constantly
diverged. LIVE GUARD, rollbacks, and reconciliation were all patches to manage this divergence.
The 2026-03-21 refactor eliminates the divergence entirely by making the engine's position state
ephemeral and exchange-derived.

**Layer tracking:** Since the exchange doesn't know about DCA layers, `CoinState.layer_count`
is tracked separately — incremented on confirmed BUY fill, reset on confirmed SELL fill.
Persisted in `state.json`.

#### 6.8.2 Resting Limit Orders as Primary TP Mechanism

After every BUY fill, a resting limit sell is placed on the exchange at the TP price for the
full position size. The exchange executes the TP without any bot interaction — bot polling is
a **fallback**, not the primary path.

Sequence:
1. BUY fill → cancel any existing TP limit order
2. Place new limit sell at updated TP price for full position size
3. Persist `tp_order_id` in CoinState
4. Each poll cycle: check order status; if filled, record trade and clear `tp_order_id`
5. If engine also detects TP via candle tick while exchange order active → skip (exchange handles it)

#### 6.8.3 Fill Price Handling

Exchange fill prices are always used. **Engine TP prices are never used as fill price substitutes.**
If the exchange API does not return a fill price, the current ticker price is fetched as fallback.

#### 6.8.4 PnL from Actual Exchange Fills

All PnL and capital accounting uses actual exchange proceeds. `trades.csv` reflects real
exchange fills, not engine simulations.

#### 6.8.5 Status.json — Exchange Data Only

All fields in `status.json` come from the exchange API:
- `equity` = `usdt_total + unrealized_pnl`
- `cash` = `usdt_free`
- `invested` = `sum(entry_price × qty)` per position
- `exchange_balance` = `{usdt_free, usdt_total}`
- Per-coin: `avg_entry`, `position_size`, `unrealized_pnl` from exchange positions
- Engine contributes only: `phase`, `lifecycle_phase`, signal state

#### 6.8.6 Human-in-the-Loop for Long↔Short Direction Changes

The V14-ETF incident (2026-03-17) demonstrated that autonomous Long↔Short direction switches
can cause catastrophic losses (HBAR switched to DCA Short autonomously and was liquidated).
Strategy direction changes (LONG_DCA ↔ SHORT_DCA) across all **live bots** require explicit
human approval before execution. Autonomous direction switches remain enabled for paper bots
where capital risk is simulated.

#### 6.8.7 Data Source Map

Every significant runtime variable, its authoritative source, and when it is updated.
This map reflects the exchange-as-truth architecture — position data originates from the
exchange API, not the engine's internal state.

| Variable | Authoritative Source | Updated When | Used By |
|----------|---------------------|--------------|---------|
| `eng.long_coins` | Exchange (`fetch_open_positions`) | Every cycle (exchange sync) | BUY sizing, TP qty, status |
| `eng.long_avg_entry` | Exchange (`fetch_open_positions.entry_price`) | Every cycle (exchange sync) | Status display |
| `eng.long_cost` | Exchange (`entry_price × qty`) | Every cycle (exchange sync) | PnL calc, equity |
| `eng.long_tp` | Engine (calculated: `entry × 1.015`) | Exchange sync overwrites; engine recalculates on buy | TP placement |
| `eng.long_layers` | `cs.layer_count` (CoinState) | BUY (+1), SELL/TP (0), exchange sync (copies layer_count) | Status, DCA logic |
| `eng.capital` | Init to `allocated_capital`; decremented by engine on buys; reset on TP fill and rebalance | On buy (−), TP fill (reset), rebalance (reset if no position) | Buy sizing |
| `cs.allocated_capital` | `router.rebalance_daily()` | Daily rebalance | Engine capital reset, status |
| `cs.tp_order_id` | `_place_tp_order()` (exchange order ID) | On BUY (set), on SELL/TP fill (cleared) | TP fill detection, TP cancel |
| `cs.tp_limit_price` | `_place_tp_order()` (stored separately from `eng.long_tp`) | On BUY (set), on SELL/TP fill (cleared) | Status display, fill correction logging |
| `cs.layer_count` | `_execute_action` BUY (+1); SELL/TP fill (0) | On every buy/sell | TP qty, status |
| `cs.last_candle_ts` | Main loop after each processed candle | Per candle | Dedup — prevent reprocessing |
| `cs.cumulative_funding` | `_update_funding()` | Every 8h per open position | Status, TP fill message |
| `_exchange_usdt_free` | `client.fetch_full_balance()` | Every cycle (exchange sync) | Status (`cash` field) |
| `_exchange_usdt_total` | `client.fetch_full_balance()` | Every cycle (exchange sync) | Status (equity calc) |
| `_last_exchange_positions` | `client.fetch_open_positions()` | Every cycle (exchange sync) | Status (per-coin position data) |
| `router.active_pool_cash` | CapitalRouter: +/− on request/return | On every BUY (−) and SELL/TP (+ proceeds) | Capital availability |
| `router.active_allocations` | CapitalRouter: +amount on request; 0 on return | On every BUY and SELL/TP | Accounting |
| `router.tier_coin_cap` | `EQUITY_TIER_CAPS` via `_apply_hysteresis()` | On rebalance | Max simultaneous coins |
| `router._cap_tier_index` | `_apply_hysteresis()` on `EQUITY_TIER_CAPS` | On rebalance | Hysteresis state for coin cap (persisted in state.json) |
| `router._split_tier_index` | `_apply_hysteresis()` on `EQUITY_TIER_SPLITS` | On rebalance | Hysteresis state for pool split (persisted in state.json) |
| `tracker._open_deals` | `on_buy()` (create/extend); `on_sell()` (pop) | On every BUY and SELL | PnL calculation, layer count for pool routing |
| `tracker.trades` | `on_sell()` (append) | On every SELL/TP fill | CSV, win_rate, total_pnl |
| `_cfgi_market` | CFGI API | Hourly | Status, regime eval message |
| `_cfgi_coins` | CFGI API | Hourly | Per-coin status |
| `_regime_signal_count` | `_evaluate_regime()` | Daily at midnight UTC | Telegram alerts |
| `_regime_alert_state` | `_evaluate_regime()`, `_handle_command()` | On regime signal / APPROVE / DENY | BUY blocking (WIND_DOWN), status |
| `bot_state` | `_handle_command()`, `_check_wind_down_complete()` | On PAUSE/RESUME/APPROVE/wind-down complete | BUY guard, status |
| `_tg_update_offset` | `_process_telegram_commands()` | On each Telegram update processed | Telegram dedup |
| `_last_rebalance_date` | `_do_rebalance()` | On successful rebalance | Prevents duplicate rebalances per day |
| `_last_status_write` | `_write_status()` | On each status write | 60s throttle |

### 6.9 TP Catch-Up (Paper Bots)

**Bug (pre-2026-03-18):** The daily tick uses the **previous day's OHLC** data. If today's
price gapped above the TP but yesterday's high was below the TP, the engine would add DCA
layers instead of selling — because the previous candle showed price below TP, and the engine
interpreted this as "price still below TP, DCA more."

**Example:** TP = $0.7436. Yesterday's high = $0.72. Today's price = $0.80. Daily tick sees
high=$0.72 < TP=$0.7436, skips TP, adds a DCA layer. Engine is now underwater on the new layer.

**Fix (2026-03-18):** A "Live TP catch-up" block was added after the daily tick in
`v14_lifecycle_engine.py`. After the daily tick completes, the engine checks the current
(live) candle against the TP. If the current candle's high (longs) or low (shorts) exceeds
the TP, it runs an additional TP tick with the current candle data.

This fix applies **only in `_live_mode`**. Backtesting is unaffected — it uses historical
OHLC data sequentially and cannot gap above TP in this way.

---

## 7. V14PM Portfolio Manager

### 7.1 Architecture

```
run_v14_portfolio_live_aster.py
    │
    ├─ _sync_positions_from_exchange()  (runs every 65s cycle)
    │    └─ Overwrites engine position state from exchange API
    │         └─ Engine position fields are ephemeral, not authoritative
    │
    ├─ V14LifecycleEngine × N coins   (signal generation only)
    │    └─ Processes candles → decides WHEN to buy/sell
    │         └─ Does NOT track positions (overwritten by exchange sync)
    │
    ├─ CapitalRouter                   (v14_capital_manager.py)
    │    ├─ active_pool   (90% of equity)
    │    └─ reserve_pool  (10% of equity)
    │
    ├─ Portfolio Regime Monitor        (global direction governance)
    │    ├─ ROUTER v2 signals × 50 coins (daily evaluation)
    │    ├─ Tiered alerts → Telegram
    │    └─ APPROVE / DENY → direction change
    │
    ├─ Capital Ledger                  (dynamic capital tracking)
    │    ├─ Auto-detect deposits/withdrawals (every 65s sync)
    │    ├─ capital_ledger.json        (persistent transaction log)
    │    └─ resize() → tier + split recalculation
    │
    ├─ Per-Coin Governance             (per-coin trading controls)
    │    ├─ Pause (manual)             (PAUSE/RESUME <COIN>)
    │    └─ Regime Flag (auto)         (signal conflict detection)
    │
    ├─ Telegram Command Interface      (governance layer)
    │    ├─ APPROVE / DENY             (regime change)
    │    ├─ PAUSE / RESUME             (global trading freeze)
    │    ├─ PAUSE / RESUME <COIN>      (per-coin pause + regime flag clear)
    │    ├─ DEPOSIT / WITHDRAW / CAPITAL (capital management)
    │    └─ CLOSE <COIN> / CLOSE ALL   (manual position override)
    │
    ├─ AsterPerpClient                 (Aster Perps via CCXT)
    │    ├─ Resting limit orders       (exchange handles TP)
    │    ├─ Fill price from exchange   (never engine fallback)
    │    └─ Position + balance queries (source of truth)
    │
    └─ Cycle Scanner JSON              (docs/data/v14/cycle_scanner.json)
         └─ Adjusted Score = DCA Score × Trend Multiplier
```

> **Architecture (revised 2026-03-21):** Exchange-as-truth. Engine is used for signal
> generation only; all position data comes from the exchange API every cycle. LIVE GUARD,
> rollbacks, and reconciliation have been removed — they were patches for a paper-bot
> architecture that shouldn't exist in live trading. Resting limit orders and fill price
> handling remain as proven exchange-interaction patterns.

### 7.2 CapitalRouter — Allocation Rules

> **Updated 2026-03-24 (Upgrade 0):** Adaptive pool split + revised tier table + 5% hysteresis.

**Adaptive pool split (equity-tiered):**

| Portfolio Equity | Active % | Reserve % | Rationale |
|-----------------|----------|-----------|-----------|
| $20,000+ | 75% | 25% | Proven on paper; deep safety buffer |
| $10,000 – $20,000 | 80% | 20% | Intermediate — avoids active-capital cliff |
| $100 – $10,000 | 90% | 10% | Max grid depth; bounded total exposure |

**Equity-tiered coin cap:**

| Portfolio Equity | Max Simultaneous Coins |
|-----------------|------------------------|
| $100,000+ | 10 |
| $20,000 – $100,000 | 5 |
| $10,000 – $20,000 | 5 |
| $5,000 – $10,000 | 5 |
| $3,000 – $5,000 | 4 |
| $100 – $3,000 | 3 |

**Hysteresis (5% band):**
Both coin cap and pool split use asymmetric hysteresis to prevent tier flapping:
- **Upgrade:** Immediate at threshold (e.g., equity hits $3,000 → 4 coins)
- **Downgrade:** Only when equity drops 5% below the current tier's threshold
  (e.g., must drop to $2,850 to go from 4 → 3 coins)
- Tier indices (`_cap_tier_index`, `_split_tier_index`) are persisted in `state.json`
  so hysteresis survives bot restarts.

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

### 7.2.1 Dynamic Capital Management (added 2026-03-24, Upgrade 1)

Supports runtime deposits and withdrawals without bot restart.

**Capital Ledger (`capital_ledger.json`):**
- Tracks seed capital, all deposits/withdrawals with timestamps and reasons
- Loaded on startup — if ledger exists, overrides `--capital` CLI arg
- Written atomically on every capital change
- Location: `trading/spot/live/v14pm/capital_ledger.json`

**Auto-detection (`_detect_capital_change`):**
- Runs every 65s sync cycle (piggybacks on `_sync_positions_from_exchange`)
- Compares exchange total balance against tracked capital + invested
- Threshold: max($5, 2% of tracked capital) — catches real deposits, ignores PnL fluctuation
- On detection: records to ledger, adjusts `tracked_capital`, calls `router.resize()`, sends Telegram alert
- Alert format: `📥 Deposit detected: +$X` or `📤 Withdrawal detected: -$X`

**Router `resize(new_equity)`:**
- Recalculates tier coin cap and pool split via hysteresis (same as rebalance)
- Updates active/reserve pool totals and cash amounts
- May trigger tier changes (e.g., deposit $2K pushes from 3-coin to 4-coin tier)

**Telegram commands:**
- `DEPOSIT <amt>` — Manual deposit recording (for when auto-detection misses or hasn't caught up)
- `WITHDRAW <amt>` — Manual withdrawal recording (safety check: refuses if amount > free balance)
- `CAPITAL` — Shows: seed, tracked, exchange balance, invested, free cash, deposits/withdrawals total

**CLI flags:**
- `--deposit <amt>` — Record deposit on startup
- `--withdraw <amt>` — Record withdrawal on startup
- `--ledger` — Print ledger summary and exit

**State persistence:** `tracked_capital` field in `state.json`, full ledger in `capital_ledger.json`.

### 7.3 Daily Rebalance

At midnight UTC, the PM runner:
1. Updates total equity from exchange balances
2. Recalculates tier cap and pool split via hysteresis (may change if equity grew/shrunk)
3. Loads latest `cycle_scanner.json`
4. Computes trend multipliers from score history
5. Identifies coins that no longer qualify (score dropped below hurdle)
6. Identifies new entrants above hurdle
7. Adjusts allocations proportionally

### 7.4 Global Strategy Direction

**All coins run one direction.** No mixed strategies — every position is either Long
or Short. When the direction changes, ALL positions change.

| Mode | Exchange | Execution |
|------|----------|-----------|
| **LONG_DCA** | Aster Perps | Long perpetual positions at 1x leverage |
| **SHORT_DCA** | Aster Perps | Short perpetual positions at 1x leverage |

Direction changes never happen autonomously. The Portfolio Regime Monitor detects
potential regime shifts and alerts Brett via Telegram. Only after human APPROVE does
the bot initiate a wind-down → direction flip.

### 7.5 Portfolio Regime Monitor

A daily evaluation of ROUTER v2 signals across all 50 scanner coins to detect
market-wide regime changes (top or bottom). Runs at **midnight UTC** alongside
the daily rebalance.

**Signal evaluation:**
- Each coin's ROUTER v2 signal stack is evaluated independently
- Top detection: 1W/2W StochRSI, 2D RSI divergence, fallback/failsafe gates
- Bottom detection: 3D death cross prerequisite, 2W StochRSI exhaustion, conviction score
- Each coin classified: BULLISH / TOPPING / BEARISH / BOTTOMING
- Coins with insufficient history (<180 days) excluded from bottom detection aggregate
  but included in top detection if they have ≥180 days of weekly data

**Tiered alert thresholds (locked):**

| Tier | Threshold | Meaning |
|------|-----------|---------|
| 🟡 Early Warning | 5+ coins (~10%) | Some coins starting to signal |
| 🟠 Strong Signal | 12+ coins (~25%) | Quarter of market flashing |
| 🔴 Majority | 25+ coins (~50%) | Half the market confirms regime change |

**Behavior:**
- Alerts sent via Telegram with: which coins, what signals triggered, CFGI reading,
  BTC status
- No automatic action at any tier. Everything keeps running normally.
- Brett decides when to APPROVE based on own analysis
- On DENY: signal logged, monitoring continues. Re-alerts if count increases.
- On no response: default DENY (safe — never flip without approval)
- Daily updates while signals persist: "{N}/50 coins still signaling — awaiting decision"

### 7.6 Direction Change — Wind-Down Phase

On APPROVE of a regime change, the bot enters a **graceful wind-down**:

```
APPROVE received
    ↓
Phase 1: WIND_DOWN
  - Freeze all grids: no new positions, no new DCA layers
  - Existing TP limit orders stay active on exchange
  - As each coin hits TP → close, capital returns to pool
  - Dashboard shows: "Winding down — 7/10 coins still open"
  - Daily Telegram status update with remaining positions
    ↓
Phase 2: TRANSFER (automatic when all positions closed)
  - All capital now free as USDT in Perp account
  - Telegram: "All positions closed. Ready for direction flip."
    ↓
Phase 3: DEPLOY (automatic)
  - Flip direction (LONG_DCA → SHORT_DCA or vice versa)
  - Run scanner, rank coins in new direction
  - Open positions per DCA grid on top-ranked coins
  - Normal operations resume
```

**Wind-down rules:**
- **Grid frozen:** No new DCA layers added. Existing layers and TP orders stay.
  Price drops do not trigger new buys.
- **TP orders active:** Each coin exits naturally when TP is hit.
- **Manual override for stragglers:** If a coin is stuck deep in its grid:
  - `CLOSE ZRO` — force-close specific coin at market
  - `CLOSE ALL` — force-close all remaining positions
  - Bot handles: cancel TP order → market close → record actual fill → log PnL
- **Never close directly on exchange UI** unless bot is down. Bot must process
  all closes to keep state in sync.

### 7.7 PAUSE / RESUME (Governance Override)

An emergency safety valve — freezes all trading without initiating a direction change.

**Global PAUSE** (via Telegram: `PAUSE`):
- Immediately freezes all grids — no new positions, no new DCA layers
- Existing TP limit orders **stay active** on exchange (let winners close)
- Bot keeps polling — monitors TP fills, updates dashboard, sends status
- Same manual override available: `CLOSE <COIN>`, `CLOSE ALL`
- Watchdog/health checks see bot as **intentionally paused** — no auto-restart
- Status shows: `⏸️ PAUSED — trading frozen by operator`
- **Persisted to `state.json`** — survives bot restart

**Global RESUME** (via Telegram: `RESUME`):
- Unfreezes grids — new entries and DCA layers resume
- Existing positions continue from where they were
- **Does NOT clear per-coin pauses** — individually paused coins stay paused
- Status returns to normal operations
- Telegram confirms: "Trading resumed — grids active"

**Per-Coin PAUSE / RESUME** (added 2026-03-24, Upgrade 2):
- `PAUSE <COIN>` — Pause a specific coin. Blocks new orders for that coin only.
- `RESUME <COIN>` — Resume a specific coin. Also clears regime flag if present (see §7.7.1).
- Per-coin pauses survive global RESUME (they are independent).
- Paused coin's capital held in reserve — not redistributed to other coins.
- Paused coins excluded from rebalance candidate list.
- TP limit orders stay active on exchange — positions can still close.
- Persisted in `state.json` per coin (`paused: true/false`).

**Difference from wind-down:** PAUSE has no destination — it's "stop until I say
otherwise." RESUME returns to the pre-pause state. Wind-down has a purpose
(direction change) and a destination (flip once all positions close).

```
Normal States:      LONG_DCA ←→ ROUTER ←→ SHORT_DCA
                       ↕           ↕          ↕
Override:           PAUSED      PAUSED     PAUSED
                       ↕           ↕          ↕
Direction Change:  WIND_DOWN → (all closed) → flip

Per-coin:   ACTIVE ←→ PAUSED (manual)
                ↕
            REGIME FLAGGED (automatic, see §7.7.1)
```

#### 7.7.1 Per-Coin Regime Flagging (added 2026-03-24, Upgrade 3)

Automatic per-coin protection when an individual coin's engine signals conflict
with the portfolio's global direction. Extends the per-coin pause pattern with
automatic detection and lifecycle management.

**Detection (`_check_coin_regime_conflict`):**
After each candle tick, check if the coin's engine fired a signal that conflicts
with the global direction:
- Global is LONG + engine fires `top_detected` → flag coin (signal: "TOP")
- Global is SHORT + engine fires `conviction_fired` → flag coin (signal: "BOTTOM")
- Skips already-flagged, paused, and cooldown-active coins

**CoinState fields:**
```python
regime_flagged: bool = False              # True when signals conflict with global direction
coin_regime_signal: Optional[str] = None  # "TOP" or "BOTTOM"
flagged_at: Optional[str] = None          # ISO timestamp when flagged
regime_cooldown_until: float = 0.0        # Unix timestamp — no re-flag before this
```

**Behavior when regime-flagged:**

| Behavior | Effect |
|----------|--------|
| New orders | ❌ Blocked (buy gate rejects with `reject_action()`) |
| TP fills | ✅ Active — exchange limit orders continue |
| Rebalance candidate | ❌ Excluded from scanner data |
| Signal scanning | ✅ Continues — engine keeps evaluating candles |
| Global regime count | ✅ Flagged coins count toward aggregate signal |
| Dashboard | 🚩 REGIME CONFLICT badge (red), dimmed in opportunity table |

**Auto-clear conditions:**
1. **TP fill with no remaining position:** Flag cleared automatically when TP fills
   and `eng.long_coins == 0 and eng.short_coins == 0`. Nothing to protect = flag cleared.
   Coin returns to opportunity list. (`_clear_regime_flag_on_tp`)
2. **Global regime flip:** When global direction changes to match the coin's signal
   (e.g., global flips to SHORT and coin was flagged TOP), flag auto-clears.
   (`_clear_matching_regime_flags`)

**Manual override:**
`RESUME <COIN>` clears both pause AND regime flag. If a regime flag was active,
a **24-hour cooldown** is applied (`regime_cooldown_until`). During cooldown,
the coin cannot be auto-re-flagged — respects operator intent.

**Telegram alerts:**
- 🚩 On flag: coin name, signal direction, global direction, flagged coin count
- ✅ On auto-clear (TP fill): coin returned to opportunity list
- ✅ On auto-clear (regime flip): global direction matches
- ▶️ On manual RESUME: cooldown status included

**Interaction with per-coin pause:**

| Behavior | Paused (manual) | Regime Flagged (auto) |
|----------|:---------------:|:---------------------:|
| New orders blocked | ✅ | ✅ |
| TPs active | ✅ | ✅ |
| Excluded from rebalance | ✅ | ✅ |
| Cleared by | `RESUME <COIN>` | TP fill / regime flip / `RESUME <COIN>` |
| Counts toward regime signal | ❌ | ✅ |
| 24h cooldown after manual clear | ❌ | ✅ |

### 7.8 Telegram Command Interface

The bot listens for and processes these Telegram commands:

| Command | Context | Action |
|---------|---------|--------|
| `APPROVE` | Regime change alert active | Initiate wind-down → direction flip |
| `DENY` | Regime change alert active | Log signal, continue current direction |
| `PAUSE` | Any time | Freeze all grids (governance override) |
| `RESUME` | Bot is paused | Unfreeze grids, resume normal trading (preserves per-coin pauses) |
| `PAUSE <COIN>` | Any time | Pause specific coin (Upgrade 2) |
| `RESUME <COIN>` | Coin is paused/flagged | Resume specific coin; clears regime flag with 24h cooldown (Upgrades 2+3) |
| `CLOSE <COIN>` | Wind-down or paused | Force-close specific coin at market |
| `CLOSE ALL` | Wind-down or paused | Force-close all remaining positions |
| `DEPOSIT <amt>` | Any time | Record manual deposit, resize pools (Upgrade 1) |
| `WITHDRAW <amt>` | Any time | Record manual withdrawal, resize pools (Upgrade 1) |
| `CAPITAL` | Any time | Show capital breakdown: seed, current, exchange balance, invested (Upgrade 1) |

**Implementation:** Bot polls for Telegram messages from authorized chat ID.
Commands are case-insensitive. Unknown commands are ignored.

### 7.9 Funding Rate Tracking

Aster perps settle funding every 8 hours. The bot tracks:
- Funding payments received (positive) and paid (negative) per symbol
- Funding rate at each settlement
- All logged to DB with timestamps
- Included in PnL calculation: `realized_pnl = trade_pnl + cumulative_funding`
- Dashboard displays cumulative funding as a separate line item

At 1x leverage with DCA hold times of hours to days, funding is typically negligible
(fractions of a basis point per 8-hour period) relative to the 1.5% TP target.

### 7.10 Current Bot Status (2026-03-24)

- **V14PM Live (Aster Perps):** ✅ **LIVE as of 2026-03-19.** ~$340 real USDT on Aster Perps.
  **All four upgrades deployed 2026-03-24:**
  - Upgrade 0: Adaptive tiers (3 coin slots at current equity, 90/10 split) with 5% hysteresis
  - Upgrade 1: Dynamic capital management (auto-detect deposits/withdrawals, capital ledger)
  - Upgrade 2: Per-coin pause (PAUSE/RESUME per coin, rebalance exclusion)
  - Upgrade 3: Per-coin regime flagging (auto-flag signal conflicts, 24h cooldown)
  Active coins: GRASS/USDT, TAO/USDT, HYPE/USDT.
  Exchange-as-truth architecture (2026-03-21). Resting limit orders, Telegram commands operational.
- **V14 Live (Aster Spot, legacy):** ❌ **RETIRED 2026-03-19** — replaced by V14PM Live.
  Position closed, funds transferred to Perps. Scheduled task `V14LiveAster` still exists
  but should not be started (will conflict with PM bot).
- **V14 Paper:** ~$52,600 equity, 400+ deals, 97.8% win rate
- **V14 PM Paper:** ~$53,100 equity, 100+ deals, 100% win rate
- **V14-ETF:** ❌ **RETIRED 2026-03-17** — HBAR autonomous direction switch caused losses.

> **Bug history:** Earlier equity figures were inflated by engine counter drift.
> Engine-internal realized PnL could diverge from CSV on restart — one bot reported
> $65K when the CSV showed $44K. Fixed 2026-03-10 by making all runners use CSV
> as the sole source of realized PnL. Full audit: `V14PM_FULL_AUDIT.md`.

---

## 8. Exchange Client (`trading.spot.exchange_client`)

### 8.1 Supported Exchanges

| Exchange | Type | API Base | Use |
|----------|------|----------|-----|
| **Aster DEX** | **Perps (CCXT)** | `fapi.asterdex.com` | **V14PM Live (production)** |
| Aster DEX | Spot (CCXT) | `sapi.asterdex.com` | V14 Live legacy (being replaced) |
| Hyperliquid | Perps (CCXT) | via CCXT | Paper bots (simulation only) |
| Binance | Futures (CCXT) | `fapi.binance.com` | Candle backfill only (no trading) |

**Aster fee structure (perps):**
- Maker: 0.005% / Taker: 0.04% (identical to Spot)
- 5% discount when paying fees with $ASTER token
- Funding rate: 0.03% interest component + premium index, settled every 8h

### 8.2 Credential Resolution (Priority Order)

1. **Explicit config dict** passed at construction
2. **Environment variables** — `ASTER_API_KEY` / `ASTER_API_SECRET` (production)
   or `HYPERLIQUID_API_KEY` / `HYPERLIQUID_API_SECRET` (paper bots)
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

### 8.5 Live Bot Methods (Aster Perps)

Methods on `SpotExchangeClient` for production trading:

| Method | Purpose |
|--------|---------|
| `create_market_buy(symbol, qty)` | Open/add to long position (perp) |
| `create_market_sell(symbol, qty)` | Close long / open short (perp) |
| `place_limit_sell(symbol, amount, price)` | Resting limit order at TP price |
| `cancel_tp_order(order_id)` | Cancel existing TP limit order |
| `check_order_status(order_id)` | Poll order fill status |
| `fetch_balance()` | Get USDT balance from perp account |
| `fetch_ticker(symbol)` | Get current price (fallback for fill price) |
| `fetch_positions()` | Get open perp positions (for reconciliation) |
| `fetch_funding_history(symbol)` | Get funding payments for PnL tracking |

> **Perp-specific notes:**
> - Long positions: BUY to open, SELL to close
> - Short positions: SELL to open, BUY to close
> - Position mode: ONE-WAY (not hedge mode) — simpler for 1x DCA
> - TP limit orders: `TAKE_PROFIT_MARKET` or `LIMIT` with GTC

### 8.6 External API Dependencies

Complete inventory of all external calls made by the V14PM live bot
(`run_v14_portfolio_live_aster.py`). For detailed call-site context (when in the main loop,
what data flows in/out), see `V14PM_CODE_AUDIT_2026-03-21.md` §4.

#### Exchange API Calls (Aster DEX Perpetuals via `ccxt.aster`)

| Call | `AsterPerpClient` Method | When Called |
|------|--------------------------|-------------|
| Load markets | `load_markets()` | Startup once |
| Set leverage | `set_leverage(1, sym)` | Per new coin (once each) |
| Fetch balance (free) | `fetch_balance({"type":"future"})` | BUY pre-flight check |
| Fetch balance (full) | `fetch_balance({"type":"future"})` | Exchange sync every cycle, `_compute_equity`, status write |
| Fetch positions | `fetch_positions()` | Exchange sync every cycle, TP placement |
| Fetch ticker | `fetch_ticker(sym)` | Status write (per coin), fill price fallback |
| Fetch OHLCV | `fetch_ohlcv(sym, "1h", limit=50)` | Candle fetch every cycle per coin |
| Market buy | `create_market_buy_order(sym, qty, {positionSide:"BOTH"})` | BUY execution |
| Market sell | `create_market_sell_order(sym, qty, {positionSide:"BOTH", reduceOnly:True})` | SELL execution, force-close |
| Fetch my trades | `fetch_my_trades(sym, limit=5)` | Fill price fallback when `order.average` is missing |
| Limit sell (TP) | `create_limit_sell_order(sym, qty, price, {GTC, positionSide, reduceOnly})` | TP placement after every BUY |
| Cancel order | `cancel_order(order_id, sym)` | TP cancellation before SELL or on phase change |
| Fetch order status | `fetch_order(order_id, sym)` | TP fill check every 65s per coin |
| Fetch open orders | `fetch_open_orders(sym)` | TP recovery at startup, orphan cleanup post-TP |
| Fetch funding history | `fetch_funding_history(sym, params)` | Every 8h per open position |

#### File I/O

| File | Path | Operations | Frequency |
|------|------|------------|-----------|
| State | `OUTPUT_DIR/state.json` | Read on startup; atomic write via `.tmp` rename | Every 65s |
| Status | `OUTPUT_DIR/status.json` | Atomic write via `.tmp` rename | Every 60s |
| Trades | `OUTPUT_DIR/trades.csv` | Read on startup; atomic write via `.tmp` rename | On every trade + every cycle |
| Bot log | `OUTPUT_DIR/bot.log` | Append (all `logging` output) | Continuous |
| Bot lock | `OUTPUT_DIR/bot.lock` | Create + OS lock on startup; unlock on shutdown | Startup/shutdown |
| Bot PID | `OUTPUT_DIR/bot.pid` | Write PID on startup; delete on clean shutdown | Startup/shutdown |
| Scanner JSON | `SCANNER_PATH` (`docs/data/v14/cycle_scanner.json`) | Read on rebalance + regime eval | Daily |
| Candles DB | `DB_PATH` (`trading/spot/data/candles.db`) | Read by `V13SignalPack` via SQLite3 | On engine init + daily signal refresh |

#### Database Queries (`candles.db`)

Not made directly from the main runner. All DB access is via `V13SignalPack(coin)` inside
`V14LifecycleEngine.__init__()` and during the daily boundary tick. Queries fetch per-coin
historical OHLCV + computed indicators from `candles_daily`.

#### External HTTP Calls

| Service | Endpoint | Frequency | Auth |
|---------|----------|-----------|------|
| Telegram sendMessage | `https://api.telegram.org/bot{token}/sendMessage` | On events (BUY, SELL, TP hit, alerts, startup/shutdown) | `AIT_TG_TOKEN` |
| Telegram getUpdates | `https://api.telegram.org/bot{token}/getUpdates` | Every 15 seconds | `AIT_TG_TOKEN` |
| CFGI API | `CFGIClient.get_current(...)` | Hourly | `CFGI_API_KEY` |

---

## 9. Presentation Layer

### 9.1 Dashboard Files

| Dashboard | File | Bot |
|-----------|------|-----|
| V14PM Portfolio | `docs/dashboardV14PM.html` | V14PM paper |
| V14 DCA | `docs/dashboardV14.html` | V14 paper |
| V14-ETF | `docs/dashboardV14ETF.html` | V14-ETF paper (RETIRED — dashboard preserved for historical record) |
| V14-PM Live | `docs/d-984ae0d4ab9dc1a5.html` | V14PM live (Aster Perps) |

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
│   ├── status.json          ← RETIRED — static snapshot
│   └── trades.csv           ← RETIRED — historical record
├── v14-pm/
│   ├── status.json          ← V14PM paper bot (always paper, never overwritten by live)
│   └── trades.csv
└── v14-pm-live/
    ├── status.json          ← V14PM live bot (Aster Perps)
    └── trades.csv
```

---

## 10. Scheduled Tasks (Windows)

All tasks run as the current user. Working directory: `C:\Users\Never\.openclaw\workspace`.

| Task Name | Trigger | Entry Point | Purpose |
|-----------|---------|-------------|---------|
| `V14LiveAster` | At boot | `run_v14_live_aster.py --confirm --skip-backfill` | V14 live bot |
| `V14PaperBot` | At boot | `run_v14_paper.py` | V14 paper bot |
| `V14PMPaperBot` | At logon | `run_v14_portfolio_paper.py --capital 50000 --profile high --leverage 1.0` | V14PM paper bot (state restored from `engine_state.json`) |
| `V14CycleScanner` | Daily | `v14_cycle_scanner.py` | DCA score refresh |
| `AIT_CandleCollector` | Hourly | `run_candle_collector.ps1` | Candle + scanner pipeline |
| `AIT_DashboardSync` | Every 10 min | `sync_dashboard_silent.vbs` | Push data to GitHub Pages |
| `AIT_PMComparisonLog` | Scheduled | `pm_comparison_log.py` | PM benchmark logging |
| `AIT_Watchdog` | Every 5 min | `openclaw_watchdog.ps1` | Monitor + auto-restart bots |

> **V14ETFPaperBot UNREGISTERED (2026-03-17):** Scheduled task removed when bot was retired.
> Do not re-register — bot is permanently retired. See §17.1.

**Auto-restart:** `V14LiveAster`, `V14PaperBot`, `V14PMPaperBot` all have
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
- V14 paper: `[V14]`
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
3. **V14PMPaperBot** — same
4. **V14LiveAster** — same

> **V14ETFPaperBot removed from watchdog (2026-03-17):** Bot retired; watchdog no longer
> monitors or restarts it.

Log: `~/.openclaw/watchdog.log`

---

## 12. Environment Variables — Complete Reference

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `ASTER_API_KEY` | Yes (production) | None | Aster DEX API key (perp trading) |
| `ASTER_API_SECRET` | Yes (production) | None | Aster DEX API secret |
| `ASTER_FAPI_URL` | Optional | `https://fapi.asterdex.com` | Aster Perp API base URL |
| `HYPERLIQUID_API_KEY` | Paper bots only | None | Hyperliquid wallet address |
| `HYPERLIQUID_API_SECRET` | Paper bots only | None | Hyperliquid private key |
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
# Normal start (restart, reboot, crash recovery):
python -u -m trading.spot.run_v14_portfolio_paper \
  --capital 50000 \
  --profile high \
  --leverage 1.0
# Restores engine state from engine_state.json — no candle replay, no phantom trades.

# First launch ONLY (new account, clean start):
python -u -m trading.spot.run_v14_portfolio_paper \
  --capital 50000 \
  --profile high \
  --leverage 1.0 \
  --fresh
# Skips state restore and candle backfill. Engines start trading from NOW only.
# After first cycle, engine_state.json is saved — subsequent restarts don't need --fresh.
```

### V14PM Live Bot (production — Aster Perps)
```bash
# Normal start (restart / crash recovery):
python -u -m trading.spot.run_v14_portfolio_live_aster \
  --capital 340 \
  --confirm \
  --skip-backfill

# First launch (fresh start):
python -u -m trading.spot.run_v14_portfolio_live_aster \
  --capital 340 \
  --confirm \
  --fresh
```
> Built from `run_v14_live_aster.py` (proven execution) + PM components.
> Unified profile (High grid, 1x leverage, 30d scanner) is hardcoded — no
> `--profile` or `--leverage` flags needed.
> Exchange is always Aster Perps — no `--exchange` flag.

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
| Adaptive pool split (90/10 → 80/20 → 75/25) | Small accounts need max grid depth; reserve scales up as equity grows and exposure warrants it (Upgrade 0, 2026-03-24) |
| Equity-tiered coin cap (3 → 4 → 5 → 10) | More coins earlier for turnover; scales with capital. 3 coins at $3K captures 51% of paper trades (Upgrade 0, 2026-03-24) |
| 5% hysteresis on tier transitions | Prevents flapping at boundaries from normal PnL fluctuation; upgrades immediate, downgrades buffered (Upgrade 0, 2026-03-24) |
| Score hurdle ≥ 5.0 | Filters out coins with poor cycle efficiency; avoids capital traps |
| Trend multiplier [0.3, 1.5] | Momentum bias without abandoning mean-reversion; bounded to prevent extremes |
| SQLite for candles.db | Zero-dependency, portable, sufficient for 1.5M rows at current scale |
| CCXT abstraction layer | Exchange-agnostic; swap Hyperliquid for any CCXT-supported exchange |
| State persistence via `engine_state.json` | Engines restore with positions, phases, indicators on restart; eliminates phantom trades from candle replay |
| `--fresh` for first launch only | New deployments skip history; all subsequent restarts use engine_state.json |
| Ground-truth equity calc | `Capital + Realized - Fees + Unrealized` from trades.csv; avoids engine internal drift. Live bot uses exchange API balances as ultimate truth. |
| `load_existing()` on ALL startup paths | Trade history survives restarts including `--fresh`; prevents `save_csv()` from overwriting history with empty data |
| `resample_daily.py` in hourly pipeline | Ensures all coins have daily candles for signal computation; closes gap between 1h collector and daily-dependent signal pack |
| TP checks candle high/low not close | Matches resting limit order behavior; fills on wick touch at TP price (2026-03-17) |
| LIVE GUARD pattern | Engine TP sells blocked when exchange limit order is active; prevents engine from overriding exchange truth (2026-03-18) |
| Resting limit orders as primary TP | Exchange executes TP even if bot dies; polling is fallback only (2026-03-17) |
| Fill price from exchange, never engine | PnL accuracy; prevents fictional bookkeeping when fill price differs from TP price (2026-03-18) |
| Human-in-the-loop for direction flips | V14-ETF incident: autonomous LONG↔SHORT switches can cause catastrophic losses (2026-03-17) |
| Top-5 scanner summary picks | Summary Best/Fastest/Safest picks derived from top 5 only; avoids low-quality picks from tail of coin universe (2026-03-18) |

---

## 16. Future Architecture: Production Trading System

> **Status:** Design finalized 2026-03-18 following live incident. Triggered by the
> fundamental problem identified: the current system treats engine state as primary truth
> with the exchange as a correction layer. This is backwards for live trading.

### 16.1 Why the Current Architecture Cannot Scale

The current design has a structural flaw: **the engine is authoritative, the exchange is secondary**.

| Current Problem | Impact |
|----------------|--------|
| Engine state (in-memory + JSON) is authoritative | Drift from actual exchange positions is possible at all times |
| CSV records engine's TP-price fills, not exchange fills | Trade history reflects fictional prices, not actual execution |
| Reconciliation runs periodically, not continuously | Window of incorrect state between reconciliation cycles |
| No database — everything is JSON + CSV on disk | No atomic writes, no concurrent access, no audit queries |
| Polls for TP fills every 65 seconds | 65-second window where exchange filled but engine doesn't know |
| Single process, single machine | No redundancy; process death = blind spot until restart |

This architecture works for paper bots (simulated, no real money). For live trading,
the **exchange must be authoritative**, with the engine as a decision-maker only.

### 16.2 Target Production Architecture

```
Signal Engine (read-only)
  → decides ENTRY signals + TP levels
         ↓
    Order Manager → Exchange API (REST + WebSocket)
         ↓                    ↓
    WebSocket fills ←── exchange pushes fills in real-time
         ↓
    PostgreSQL DB ← single source of truth
    (trades, balances, positions, signals, audit log)
         ↓
    Dashboard API → reads from DB
    Status/alerts → reads from DB
```

**Key principles of the target architecture:**
- **DB is truth** — not engine state, not CSV, not JSON files
- **Exchange pushes fills via WebSocket** — not polling every 65 seconds
- **Engine only decides entries** — all exits are exchange-driven (limit orders)
- **Order Manager is separate from Signal Engine** — clear separation of concerns
- **All prices are exchange prices** — engine never contributes fill price data
- **Full audit trail in DB** — every order, fill, balance change is immutable

### 16.3 Database Schema (Target)

```sql
-- Positions (source of truth for open positions)
CREATE TABLE positions (
    id              SERIAL PRIMARY KEY,
    account_id      TEXT NOT NULL,
    symbol          TEXT NOT NULL,
    side            TEXT NOT NULL,       -- 'long' | 'short'
    layers          INTEGER,
    avg_entry       REAL,
    quantity        REAL,
    tp_price        REAL,
    tp_order_id     TEXT,               -- exchange order ID
    opened_at       TIMESTAMPTZ,
    updated_at      TIMESTAMPTZ
);

-- Fills (immutable exchange fill records)
CREATE TABLE fills (
    id              SERIAL PRIMARY KEY,
    account_id      TEXT NOT NULL,
    order_id        TEXT NOT NULL,
    symbol          TEXT NOT NULL,
    side            TEXT NOT NULL,
    price           REAL NOT NULL,      -- actual exchange fill price
    quantity        REAL NOT NULL,
    fee             REAL,
    filled_at       TIMESTAMPTZ NOT NULL,
    raw_response    JSONB               -- full exchange API response
);

-- Trades (closed position records — derived from fills)
CREATE TABLE trades (
    id              SERIAL PRIMARY KEY,
    account_id      TEXT NOT NULL,
    symbol          TEXT NOT NULL,
    open_time       TIMESTAMPTZ,
    close_time      TIMESTAMPTZ,
    layers          INTEGER,
    invested        REAL,
    proceeds        REAL,               -- actual exchange proceeds
    pnl             REAL,               -- proceeds - invested - fees
    return_pct      REAL,
    duration_h      REAL
);
```

### 16.4 Migration Strategy: Aster Perps (Locked 2026-03-19)

Production exchange is **Aster DEX Perpetuals** at 1x leverage. Decision D1.

**Phase 1 (current):** V14PM Live on Aster Perps
- Build `run_v14_portfolio_live_aster.py` from proven live Aster bot
- Start with ~$340 capital, coin cap = 1, rotate after current ASTER TP
- LIVE GUARD, resting limit orders, fill price handling already proven
- Phase 2 execution: skip dry-run, go directly to small-capital live

**Phase 2 (near-term):** Scale up on Aster
- Increase capital → increase coin cap tier
- Enable full portfolio rotation
- Add regime monitor + wind-down + Telegram governance

**Phase 3 (medium-term):** Exchange-as-truth architecture — **PARTIALLY IMPLEMENTED (2026-03-21)**
- ✅ Exchange API as single source of truth for positions and balances (implemented)
- ✅ Engine position state overwritten from exchange every cycle (implemented)
- ✅ Status.json fully derived from exchange data (implemented)
- ⬜ WebSocket fill listener (replaces 65-second polling) — not yet
- ⬜ Database as position truth (replaces state.json + trades.csv) — not yet
- ⬜ Order Manager service (replaces engine-embedded order logic) — not yet
- ⬜ Dashboard reads from DB instead of synced JSON files — not yet

**Phase 4 (optional):** Cloud migration for reliability
- Move proven bot to always-on cloud server
- Same code, same config, systemd instead of Windows scheduled tasks

**What this enables:**
- Multi-account dashboard: single query across all accounts
- True real-time fill processing: no polling latency
- Immutable audit trail: every fill recorded at exchange time
- Redundancy: DB survives process restarts; fills don't need re-processing

### 16.5 CSV Migration Path

When moving to PostgreSQL:
1. Import all existing `trades.csv` files into `trades` table (one-time migration)
2. Create `TradeStore` class replacing CSV file I/O
3. Keep CSV export as read-only convenience (debugging, dashboards)
4. Add `account_id` to all records for multi-account isolation

---

## 17. Incident Log

### 17.1 2026-03-17: V14-ETF Retirement (Autonomous Direction Switch)

**Component:** `run_v14etf_paper.py` (V14-ETF Paper Bot)
**Severity:** High (demo bot capital lost; no real money)
**Status:** ✅ Resolved — bot retired

**What happened:** HBAR switched from LONG_DCA to SHORT_DCA autonomously without human approval.
The SHORT_DCA grid was built as price continued rising, resulting in significant simulated losses.

**Root cause:** No human-in-the-loop gate for Long↔Short direction changes.

**Resolution:**
- Bot stopped and scheduled task unregistered
- `status.json` renamed to `status.json.retired`
- Live trading rule added: Long↔Short direction flips require human approval (§6.8.6)
- Lesson documented in §6.8.6

### 17.2 2026-03-17: TP Fill Model Fix

**Component:** `v14_dca_engine.py`, `v14_lifecycle_engine.py`
**Severity:** Medium (missed TPs — opportunity cost)
**Status:** ✅ Fixed

**What happened:** TP detection checked candle **close** price, not high/low. Wicks that
touched the TP price but closed below would not trigger a TP sell. Engine missed TPs that
any exchange limit order would have filled.

**Fix:** Engine now checks candle high (longs) / low (shorts) for TP detection. Fills at
TP price on wick touch. See §5.2.

### 17.3 2026-03-17: Resting Limit Orders on Aster

**Component:** `run_v14_live_aster.py`, `exchange_client.py`
**Severity:** Enhancement
**Status:** ✅ Implemented

**What happened:** Live bot relied on polling every 65 seconds to detect TP hits.
Process death or API errors created windows where exchange filled but bot didn't know.

**Fix:** Resting limit sell placed on exchange after every BUY. Exchange executes TP
regardless of bot state. See §6.3.1, §6.8.2.

### 17.4 2026-03-18: TP Catch-Up Bug Fix (Paper Bots)

**Component:** `v14_lifecycle_engine.py`
**Severity:** Medium (incorrect DCA behavior after price gap above TP)
**Status:** ✅ Fixed

**What happened:** Daily tick used previous-day OHLC. If price gapped above TP overnight
but yesterday's high was below TP, engine would add a DCA layer instead of selling.

**Fix:** "Live TP catch-up" block added after daily tick. Checks current candle against TP;
if exceeded, runs TP tick with current data. Live mode only. See §6.9.

### 17.5 2026-03-18: CRITICAL — Live Aster False TP Sell ($22 Loss)

**Component:** `run_v14_live_aster.py`
**Severity:** Critical (real capital loss)
**Status:** ✅ Resolved — LIVE GUARD implemented

**What happened:**
1. Daily tick used previous-day OHLC (high ~$0.78)
2. Previous-day high exceeded TP ($0.7436) → engine triggered internal TP sell
3. Engine cancelled exchange limit order
4. Market sell executed at ~$0.69 (below TP — price had already fallen back)
5. Exchange API didn't return fill price → fill fell back to engine's TP price ($0.7436)
6. Engine booked sell at $0.7436, actual proceeds ~$0.69 → $22 loss + incorrect PnL

**Root cause:** Engine treated as authoritative over exchange. Daily tick could override
active exchange limit orders via its internal TP detection.

**Fix (LIVE GUARD — §6.8.1):**
- Engine TP sells blocked when `_tp_order_id` is set
- Engine state rolled back on blocked TP
- Fill price fallback fixed: fetches ticker price, never falls back to engine price
- PnL calculated from actual exchange proceeds
- Engine capital corrected after sells
- Startup reconciliation caught $22.73 drift and corrected

### 17.6 2026-03-18: Scanner Summary Pick Fix

**Component:** `v14_cycle_scanner.py`
**Severity:** Low (incorrect summary labels)
**Status:** ✅ Fixed

**What happened:** Best/Fastest/Safest summary picks were derived from the full coin
universe ranking, meaning poor-performing coins at the tail could appear as summary picks.

**Fix:** Summary picks now derived from `scored_rankings[:5]` (top 5 only). See §4.1.

### 17.7 2026-03-24: False "Bot Frozen" Alerts — PowerShell Timezone Parsing Bug

**Component:** Heartbeat monitoring script (OpenClaw agent)
**Severity:** Medium (unnecessary bot restarts, false critical alerts)
**Status:** ✅ Root cause identified and fixed

**What happened:** OpenClaw heartbeat checks reported V14PM Live as "frozen" with
~25,200 seconds (7 hours) of staleness — matching the PDT/UTC offset exactly.
The bot was restarted 6+ times in 24 hours due to false alerts. All restarts were
unnecessary — the bot was running normally the entire time.

**Root cause:** PowerShell's `[datetime]::Parse()` silently converts ISO timestamps
with `+00:00` offset to local time (Kind=Local). When subtracted from `[datetime]::UtcNow`
(Kind=Utc), the local-time value is treated as-is, creating a phantom 7-hour offset
matching the PDT timezone.

```powershell
# BAD: [datetime]::Parse("2026-03-25T04:03:53+00:00") → 03/24 21:03 (Local, Kind=Local)
# Subtracting UtcNow (04:04 UTC) from Local (21:03 "UTC") = 25,200 seconds

# GOOD: [datetimeoffset]::Parse("2026-03-25T04:03:53+00:00").UtcDateTime → 04:03 (UTC)
# Subtracting UtcNow (04:04 UTC) from UTC (04:03 UTC) = 42 seconds
```

**Fix:** Use `[datetimeoffset]::Parse($ts).UtcDateTime` instead of `[datetime]::Parse($ts)`
when comparing ISO timestamps against `[datetime]::UtcNow`.

**Impact:** No data loss or financial impact. Exchange-as-truth architecture ensured
all positions and TP orders were preserved across unnecessary restarts. Upgrades 0–3
deployed during the same session were unaffected.

**Lesson:** Never use `[datetime]::Parse()` for UTC timestamp comparison in PowerShell.
Always use `[datetimeoffset]` for timezone-aware parsing.

---

## 18. Code Audit & Gap Analysis (2026-03-21)

Point-in-time audit of `run_v14_portfolio_live_aster.py` and supporting modules, conducted
2026-03-21 during the exchange-as-truth refactor. 13 gaps were identified and resolved.
Full per-function traces and detailed flow analysis: `V14PM_CODE_AUDIT_2026-03-21.md`.

### 18.1 Gap Summary Table

| Gap | Description | Severity | Status |
|-----|-------------|----------|--------|
| GAP-01 | `_handle_tp_fill`: broken orphaned order cleanup — `self.client.client` and `._to_ccxt_symbol()` don't exist; orphaned sell orders never cleaned up | P1 | ✅ FIXED |
| GAP-02 | `CapitalRouter.rebalance_daily` silently changes pool split from 90/10 → 75/25 without adjusting cash amounts; docstring contradicted code | P1 | ✅ FIXED → superseded by Upgrade 0 (adaptive split) |
| GAP-03 | `_last_rebalance_date` and `_regime_last_eval_date` not persisted in `state.json` — both reset to `None` on restart, triggering immediate rebalance | P2 | ✅ FIXED |
| GAP-04 | `_reentry_cooldown_until` declared in `__init__` but never read or updated (dead code) | P2 | ✅ FIXED |
| GAP-05 | `_force_close_coin` uses stale `eng.long_coins` instead of fetching current exchange position qty | P1 | ✅ FIXED |
| GAP-06 | `_write_status` reads `trades.csv` N+1 times per 60s write (once per coin + once for aggregates) | P3 | ⏸️ DEFERRED |
| GAP-07 | `V14LifecycleEngine.get_status()` hardcodes `'exchange': 'hyperliquid'` — wrong for live bot | P2 | 🚫 WON'T FIX |
| GAP-08 | `msvcrt` file lock is Windows-only — crashes with `ModuleNotFoundError` on Linux/cloud | P1 | ✅ FIXED |
| GAP-09 | `_compute_equity` potential double-count: `usdt_total + unrealized` — needed API verification | P1 | ✅ NOT A BUG |
| GAP-10 | `SHORT_OPEN` / `SHORT_CLOSE` engine actions silently ignored in `_execute_action` — engine state drifts | P2 | ✅ FIXED |
| GAP-11 | `_place_tp_order` makes redundant `fetch_open_positions` call immediately after a BUY | P3 | ⏸️ DEFERRED |
| GAP-12 | `_recover_tp_orders` Phase 2 (orphan scan) runs on coins already fully handled by Phase 1 | P2 | ✅ FIXED |
| GAP-13 | Engine capital depletes mid-DCA, potentially blocking further layers on restart with open position | P1 | ✅ FIXED |

### 18.2 Gap Details

**GAP-01 — FIXED (2026-03-21):** After a TP fill, the code attempted
`self.client.client.fetch_open_orders()` and `self.client._to_ccxt_symbol()`.
`AsterPerpClient` has no `.client` attribute (it has `._exchange`) and no `._to_ccxt_symbol()`
method (the correct method is `._aster_symbol()`). Always raised `AttributeError`, silently
swallowed by a bare `except`. Orphaned sell orders were never cleaned up after TP fills.
**Fix:** Changed to `self.client.fetch_open_orders(sym)`.

**GAP-02 — FIXED (2026-03-21), then SUPERSEDED (2026-03-24, Upgrade 0):** Originally
`CapitalRouter.__init__` set 90/10 pool split; `rebalance_daily()` silently changed to 75/25.
**2026-03-21 fix:** Both paths set to 75/25 consistently.
**2026-03-24 (Upgrade 0):** Pool split is now adaptive and equity-tiered (90/10 → 80/20 → 75/25)
via `EQUITY_TIER_SPLITS` lookup table. Both `__init__()` and `rebalance_daily()` use
`_apply_hysteresis()` to determine the split, so the inconsistency can no longer recur.

**GAP-03 — FIXED (2026-03-21):** `_last_rebalance_date` was not saved in `state.json` — always
reset to `None` on restart, triggering an immediate rebalance on every restart regardless of
whether it had already run that day. `_regime_last_eval_date` had the same issue.
**Fix:** Both fields are now persisted in `state.json` and restored on startup.

**GAP-04 — FIXED (2026-03-21):** `self._reentry_cooldown_until = 0.0` declared in `__init__`,
never read or updated anywhere in the codebase. Was presumably superseded by the 30-second
`ORDER_DEDUP_WINDOW` in `_execute_action`. **Fix:** Removed dead attribute.

**GAP-05 — FIXED (2026-03-21):** `_force_close_coin` sold using `eng.long_coins` (last set by
exchange sync, potentially stale if called soon after a buy). The `_execute_action` SELL path
correctly fetches exchange position qty, but `_force_close_coin` did not.
**Fix:** Now calls `client.fetch_open_positions()` first; falls back to `eng.long_coins` if
exchange returns nothing.

**GAP-06 — DEFERRED (P3):** `_write_status` re-reads `trades.csv` once per active coin (for
per-coin realized PnL) and once more for aggregate stats — N+1 reads per 60-second cycle. At
current coin counts (1–3) this is negligible. **Fix when needed:** Read once, compute all
per-coin and aggregate stats in a single pass.

**GAP-07 — WON'T FIX:** `V14LifecycleEngine.get_status()` returns `'exchange': 'hyperliquid'`
(hardcoded from the paper bot template). Lives in shared `v14_lifecycle_engine.py` used by all
bots — modifying it risks breaking paper bots without clear benefit. The main runner's
`_write_status()` already overrides the top-level `"exchange"` field with `"aster_perp"`.
The wrong value never reaches `status.json` uncorrected.

**GAP-08 — FIXED (2026-03-21):** `import msvcrt; msvcrt.locking(...)` in the startup path is
Windows-only. Would raise `ModuleNotFoundError` on any Linux/cloud deployment.
**Fix:** Platform check — uses `msvcrt.locking` on `win32`, `fcntl.flock` on Linux.

**GAP-09 — NOT A BUG:** `_compute_equity()` computes `equity = usdt_total + unrealized_pnl`.
Concern was that `usdt_total` might already include unrealized PnL.
**Verified via Aster API:** `usdt_total = free + used` where `used` = margin posted as
collateral, NOT unrealized PnL. Adding engine-computed unrealized PnL on top is therefore
correct — it does not double-count.

**GAP-10 — FIXED (2026-03-21):** `_execute_action` only handled `"BUY"` and `"SELL"` action
types. The engine can emit `"SHORT_OPEN"` and `"SHORT_CLOSE"` when a coin is in `SHORT_DCA`
phase. These were silently dropped (no exchange order, no rollback), causing the engine's
internal position state to drift into an inconsistent state.
**Fix:** `SHORT_OPEN` and `SHORT_CLOSE` are now explicitly rejected via `engine.reject_action()`
to prevent state drift. Short-side trading is not currently enabled.

**GAP-11 — DEFERRED (P3):** `_place_tp_order` calls `client.fetch_open_positions()` to get the
exchange qty for the TP order, even though positions were already fetched at the top of the
cycle and the buy order result contains the filled qty.
**Fix when needed:** Use `actual_qty` from the BUY result directly for TP placement.

**GAP-12 — FIXED (2026-03-21):** `_recover_tp_orders` Phase 1 checks if known TP orders are
still valid (filled or live). Phase 2 then scanned for orphan orders on all coins — including
coins where Phase 1 had already confirmed the TP order was alive. Redundant exchange API calls
and risk of mis-classifying a valid TP order as an orphan.
**Fix:** Phase 2 now skips coins where Phase 1 confirmed the TP order is still valid.

**GAP-13 — FIXED (2026-03-21):** The DCA engine's internal `capital` field is decremented
each time a layer is added (part of the DCA sizing design). On restart with an open position,
the engine could have near-zero capital, causing the `order > self.capital` guard to block
further DCA layers — even though the `CapitalRouter` had real capital available.
**Fix:** Engine capital is reset to `cs.allocated_capital` on every restart (for coins with
open positions) AND after every confirmed BUY fill. The router manages real capital; the
engine's capital is a sizing reference that resets each cycle.

**GAP-14 — FIXED (2026-04-09):** `_execute_action` SELL path did not verify that a position
actually existed on the exchange before attempting a market sell. During candle catch-up, the
engine can generate BUY+SELL action pairs in a single tick. If the BUY is rejected (e.g.,
insufficient USDT), the SELL proceeds with no position to close — exchange rejects with
"ReduceOnly Order is rejected" (-2022).
**Fix:** SELL path now calls `fetch_open_positions()` and skips the sell if no position exists
for the coin. Engine state is rolled back via `reject_action(SELL)`.

**GAP-15 — FIXED (2026-04-09):** `reject_action()` in `v14_lifecycle_engine.py` only supported
BUY and SHORT_OPEN rollbacks. A rejected SELL (phantom TP with no exchange position) would
log a warning but leave the engine in a dirty state (position zeroed, capital credited with
phantom proceeds).
**Fix:** `reject_action()` now handles SELL: reverses TP credit (capital, coins, avg_entry,
layers, pnl, wins). In practice, `_sync_positions_from_exchange()` would also clean this up
on the next cycle, but explicit rollback prevents transient state corruption.

**GAP-16 — FIXED (2026-04-09):** Insufficient USDT Telegram alerts had no throttle. When the
bot is cash-starved ($0 USDT), every candle tick triggers a BUY signal → balance check fails →
Telegram alert. With duplicate candle processing (~20x per candle), this produces dozens of
alerts per coin per hour.
**Fix:** Alert throttled to once per coin per hour via `cs._last_insufficient_alert` timestamp.
The actual `fetch_balance()` check still runs every time — only the Telegram notification is
rate-limited.

---

_Document generated by Gee Gee — 2026-03-09_
_Updated: 2026-03-10 (v1.2 — CSV-as-truth, exchange API equity, --fresh loads existing trades)_
_Updated: 2026-03-18 (v1.3 — LIVE GUARD, resting limit orders, fill price fix, TP catch-up, V14-ETF retirement, production architecture target, incident log §17)_
_Updated: 2026-03-19 (v1.4 — Production architecture locked: Aster Perps, 50-coin universe, unified profile, global direction, regime monitor §7.5, wind-down §7.6, PAUSE/RESUME §7.7, Telegram commands §7.8, funding rate §7.9, exchange client updates §8, env vars §12, CLI §13, migration strategy §16.4)_
_Updated: 2026-03-21 (v1.5 — Exchange-as-truth architecture: removed LIVE GUARD, engine rollbacks, reconciliation. Exchange API is single source of truth for positions and balances. §6.8 rewritten, §7.1 architecture updated, §16.4 Phase 3 partially implemented.)_
_Updated: 2026-03-21 (v1.6 — Code audit merge from V14PM\_CODE\_AUDIT\_2026-03-21.md: §1.5 Class & Module Quick Reference, §6.8.7 Data Source Map, §8.6 External API Dependencies, §18 Code Audit & Gap Analysis (13 gaps, all resolved). Architecture doc is now single source of truth for design-level findings.)_
_Updated: 2026-04-09 (v1.7 — Pre-order exchange checks: SELL path verifies position exists via fetch_open_positions(), insufficient USDT alert throttle, SELL rollback in reject_action(). GAPs 14-16 added to §18.)_
_Decisions reference: PRODUCTION_DECISIONS_2026-03-19.md_
_Audit trail: V14PM_CHANGE_CONTROL.md (renamed from V14PM_UNIFIED_AUDIT.md 2026-03-24)_
