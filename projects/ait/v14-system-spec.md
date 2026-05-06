# V14 System Specification — Adaptive Intelligence Trading (AIT)

**Version:** 1.0  
**Date:** 2026-03-05  
**Author:** Gee Gee (AI Agent) + Brett (Principal)  
**Status:** Live (Paper + Live)  
**Engine:** V14 DCA-only with ROUTER v2 signal stack  
**Production Exchange:** Hyperliquid (perps), Aster (spot)

---

## 1. Overview

V14 is the current production trading engine for AIT. It is a **DCA-only (long) strategy** that uses the ROUTER v2 signal stack to time entries and exits. The system is designed for bear/ranging markets where coins cycle through predictable drawdown-and-recovery patterns.

The architecture has four operational layers:

1. **Data Pipeline** — Candle collection and storage
2. **Intelligence Layer** — DCA Cycle Scanner and scoring
3. **Execution Layer** — Live and paper trading bots
4. **Presentation Layer** — Dashboards and GitHub Pages sync

### Design Philosophy

> "It's about finding the right coin at the right time and running the strategy and getting out with your shirt." — Brett

V14 prioritizes **capital velocity** over raw profit. The system scores coins by how quickly they complete profitable DCA cycles, how much capital gets trapped in safety orders, and how deep the drawdowns go. Capital is deployed where the DCA Score is highest.

---

## 2. System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        DATA PIPELINE                            │
│                                                                 │
│  Hyperliquid API ──→ collect_scanner_candles.py ──→ candles.db  │
│  (1h perp candles)    (hourly, incremental)         (SQLite)    │
│                                                                 │
│  Aster API ──→ live bot self-collects                           │
└──────────────────────────┬──────────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────────┐
│                    INTELLIGENCE LAYER                            │
│                                                                 │
│  candles.db ──→ v14_cycle_scanner.py ──→ cycle_scanner.json     │
│                 (hourly, after candle collection)                │
│                                                                 │
│  Outputs:                                                       │
│    - DCA Score per coin (4 time windows)                        │
│    - Rankings, top picks, capital deployment signals             │
│    - Immature coin tracking (< 6mo history)                     │
└──────────────────────────┬──────────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────────┐
│                     EXECUTION LAYER                             │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ V14 Live Bot (ASTER/USDT)         $300 real capital      │   │
│  │ Exchange: Aster (spot)            Profile: High          │   │
│  │ Runner: run_v14_live_aster.py     Task: V14LiveAster     │   │
│  │ State: trading/spot/live/v14/                            │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ V14 Paper Bot (HBAR/ATOM/LINK/NEAR)   $10K paper        │   │
│  │ Exchange: Hyperliquid (perps)         Profile: Medium    │   │
│  │ Runner: run_v14_paper.py              Task: V14PaperBot  │   │
│  │ State: trading/spot/paper/v14/                           │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ V14-ETF Paper Bot (SOL/XRP/LTC/HBAR/ADA)  $10K paper    │   │
│  │ Exchange: Hyperliquid (perps)         Profile: High      │   │
│  │ Runner: run_v14etf_paper.py           Task: V14ETFPaperBot│  │
│  │ State: trading/spot/paper/v14etf/                        │   │
│  └──────────────────────────────────────────────────────────┘   │
└──────────────────────────┬──────────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────────┐
│                   PRESENTATION LAYER                            │
│                                                                 │
│  status.json + trades.csv ──→ sync_dashboard.ps1 ──→ GitHub     │
│  cycle_scanner.json          (every 10 min)          Pages      │
│  daily_equity.json                                              │
│                                                                 │
│  Dashboards:                                                    │
│    - V14 Live:  d-984ae0d4ab9dc1a5.html                        │
│    - V14 Paper: dashboardV14.html                               │
│    - V14-ETF:   dashboardV14ETF.html                            │
│                                                                 │
│  GitHub: halo-effects.github.io/adaptive-intelligence-trading/  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 3. Data Pipeline

### 3.1 Candle Database

**File:** `trading/spot/data/candles.db` (SQLite, ~212 MB)

**Schema:**
```sql
CREATE TABLE candles (
    symbol TEXT,
    timeframe TEXT,
    timestamp INTEGER,    -- Unix ms
    open REAL, high REAL, low REAL, close REAL, volume REAL,
    PRIMARY KEY (symbol, timeframe, timestamp)
);

CREATE TABLE candles_daily (
    symbol TEXT,
    timestamp INTEGER,
    open REAL, high REAL, low REAL, close REAL, volume REAL,
    PRIMARY KEY (symbol, timestamp)
);
```

**Coverage:** 48 coins, 1h candles. Most coins have 6-86 months of history. The scanner requires a minimum of 6 months to be included in published rankings.

### 3.2 Candle Collector

**File:** `trading/spot/collect_scanner_candles.py`  
**Schedule:** Hourly via `AIT_CandleCollector` Windows Scheduled Task  
**Source:** Hyperliquid perps API (all coins mapped as `COIN/USDC:USDC`)

**Behavior:**
- **Incremental:** Only fetches candles newer than the last stored timestamp (with 6-hour overlap buffer for gap recovery)
- **First run:** Pulls up to 2 years of history
- **Rate limiting:** 0.5s between API pages, 0.8s between coins, automatic retry with exponential backoff on HTTP 429
- **Deduplication:** Uses `INSERT OR IGNORE` on the primary key
- **ASTER exception:** ASTER candles are collected by the live bot itself (Aster exchange, not Hyperliquid)

**Coin Universe (48 coins):**

| Category | Coins |
|----------|-------|
| Established (pre-2024) | BTC, ETH, SOL, XRP, LINK, DOGE, ADA, LTC, AVAX, DOT, UNI, ATOM, NEAR, HBAR, INJ, FIL, RUNE, CRV, SNX, COMP, MKR, ENS, DYDX, LDO, ARB, OP, STX, SEI, RENDER |
| 2024 launches | SUI, FET, TAO, TON, JUP, KAS, PENDLE, PYTH, TIA, ONDO, ENA, EIGEN, W, ZRO |
| Mid-cycle 2025 | HYPE, ASTER |
| Standalone | AAVE |

### 3.3 Pipeline Wrapper

**File:** `trading/spot/run_candle_collector.ps1`  
**Scheduled Task:** `AIT_CandleCollector` (hourly)  
**Log:** `trading/spot/data/collector.log`

```
Step 1: Run collect_scanner_candles.py (pull candles)
Step 2: Run v14_cycle_scanner.py (refresh DCA Scores)
```

This wrapper is called by the scheduled task via:
```
powershell.exe -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden
    -File C:\Users\Never\.openclaw\workspace\trading\spot\run_candle_collector.ps1
```

---

## 4. Intelligence Layer — DCA Cycle Scanner

### 4.1 Purpose

The scanner is the **source of truth** for capital deployment decisions. It evaluates every coin in the universe by simulating DCA cycles on historical candle data and scoring them by capital efficiency.

**File:** `trading/spot/v14_cycle_scanner.py`  
**Output:** `docs/data/v14/cycle_scanner.json`

### 4.2 DCA Score Formula

```
DCA Score = Realized_PnL × (1 - MaxDD%) × Capital_Freedom / 100
```

| Component | What it measures | Why it matters |
|-----------|-----------------|----------------|
| **Realized_PnL** | Dollar profit from completed deals in the window | Raw earning power — coins that cycle fast and profitably score higher |
| **(1 - MaxDD%)** | Penalty for maximum drawdown depth | Protects against coins that profit but expose you to catastrophic underwater periods |
| **Capital_Freedom** | `1 - (open_layers / 24)` | Measures how often capital is free vs trapped in safety orders. A coin sitting at layer 10 permanently traps capital |

### 4.3 DCA Simulation Parameters (V14 High Profile)

| Parameter | Value | Description |
|-----------|-------|-------------|
| `BO_PCT` | 40% | Base order as percentage of DCA allocation |
| `SO_DEV` | 1.5% | Safety order price deviation |
| `SO_STEP_MULT` | 1.5x | Each SO placed further apart (geometric) |
| `SO_VOL_MULT` | 1.5x | Each SO is larger (geometric) |
| `MAX_LAYERS` | 12 | Maximum safety orders per deal |
| `TP_PCT` | 1.5% | Take profit from weighted average entry |
| `TAKER_FEE` | 0.025% | Hyperliquid taker fee |
| `CAPITAL` | $10,000 | Simulated capital per coin |
| `DCA_ALLOC` | 90% | Percentage of capital allocated to DCA grid |

### 4.4 Time Windows

| Window | Range | Use Case |
|--------|-------|----------|
| `7d` | Last 7 days | Short-term momentum, what's cycling right now |
| `14d` | Last 14 days | Medium-term trend, smooths out daily noise |
| `30d` | Last 30 days | Monthly view, captures full market cycles |
| `bear` | 2026-01-01 → now | Bear market performance since the current cycle began |

### 4.5 Scanner Output

The scanner produces a ranked list per window with:
- `rank`, `coin`, `symbol`
- `deals_completed`, `deals_per_week`, `avg_cycle_hours`
- `realized_pnl`, `avg_pnl_per_deal`
- `max_drawdown_pct`, `open_layers`, `unrealized_pnl`
- `capital_freedom`, `dca_score`, `win_rate`
- `mature` flag (coins with < 6 months history are tracked but excluded from published rankings)

**Top Picks** (derived from the bear window):
- `best_score` — Highest DCA Score overall
- `fastest_cycler` — Most deals per week
- `lowest_dd` — Lowest maximum drawdown
- `most_capital_free` — Highest capital freedom

### 4.6 DCA Trend Score (Score Momentum)

**Added:** 2026-03-05  
**Purpose:** Track whether a coin's DCA Score is improving, stable, or deteriorating over time.

A coin scoring 85 today but declining from 95 last week is a worse allocation target than a coin scoring 70 and rising from 40. The Trend Score captures this momentum.

#### 4.6.1 Score History

**File:** `trading/spot/data/score_history.json`

Every scanner run appends a daily snapshot of all coin DCA scores to a rolling history file:
- Stores up to **180 days** (6 months) of daily snapshots
- De-duplicates same-day runs (last run of the day wins)
- Tracks: `dca_score`, `deals_per_week`, `max_drawdown_pct`, `realized_pnl`, `capital_freedom`, `mature` flag
- Uses the `bear` window scores (longest backtest) for trend analysis

#### 4.6.2 Trend Computation

After recording the snapshot, the scanner computes trend slopes over three windows:

| Window | Weight | What it captures |
|--------|--------|-----------------|
| 7d slope | 50% | Recent momentum (highest weight) |
| 14d slope | 30% | Medium-term trajectory |
| 30d slope | 20% | Longer-term structural trend |

**Slope calculation:** `(latest_score - earliest_score_in_window) / abs(earliest_score)`

**Composite Trend Multiplier:**
```
Weighted change = Σ(slope × weight) / Σ(weights)
Trend Multiplier = clamp(1.0 + weighted_change, 0.3, 1.5)
```

| Direction | Condition | Multiplier Range | Meaning |
|-----------|-----------|-----------------|---------|
| **Accelerating** | Change > +5% | 1.05x – 1.5x | Score improving, coin cycling better |
| **Stable** | Change ±5% | 0.95x – 1.05x | Consistent performance |
| **Declining** | Change < -5% | 0.3x – 0.95x | Score deteriorating, coin cycling worse |

#### 4.6.3 Dashboard Integration

All three dashboards (V14 Live, V14 Paper, V14-ETF) display a **TREND** column in the Live Opportunity table:

| Indicator | Color | Direction | Tooltip |
|-----------|-------|-----------|---------|
| ↗ | Green (profit color) | Accelerating | "Score accelerating (1.35x)" |
| → | Gray (text2 color) | Stable | "Score stable (1.02x)" |
| ↘ | Red (loss color) | Declining | "Score declining (0.65x)" |

Hovering over the arrow reveals the exact trend multiplier. Trend data requires ≥3 daily snapshots before arrows appear (shows `--` until then).

#### 4.6.4 Scanner Output

Trend scores are included in `cycle_scanner.json` under the `trend_scores` key:

```json
{
  "trend_scores": {
    "HBAR": {
      "trend_7d": 0.125,
      "trend_14d": 0.085,
      "trend_30d": -0.032,
      "trend_multiplier": 1.078,
      "direction": "accelerating"
    }
  }
}
```

The scanner also prints a trend table to the console after rankings:
```
======================================================================
  DCA Trend Scores (score momentum)
======================================================================
Coin     Direction          7d      14d      30d   Mult
----------------------------------------------------------------------
SOL      accelerating    +18.2%   +12.5%    +5.3%  1.35x
HBAR     stable           +3.1%    +1.8%    -0.5%  1.02x
LTC      declining       -12.4%    -8.2%    -3.1%  0.65x
```

#### 4.6.5 Future Use: Capital Allocation

The Trend Multiplier is designed to feed directly into the Portfolio Capital Management System (see `projects/ait-product/portfolio-capital-management.md`):

```
Allocation Weight = Base DCA Score × Trend Multiplier
```

This ensures coins with rising DCA efficiency receive more capital, while coins with falling efficiency are gradually starved of new capital — providing natural portfolio rotation without forced position closures.

### 4.7 Maturity Threshold

Coins with fewer than 6 months of 1h candle history are classified as **immature**. They are still scanned and tracked internally but are excluded from the published rankings to prevent misleading scores based on limited data. This threshold is configurable via `MIN_HISTORY_MONTHS`.

---

## 5. Execution Layer — Trading Bots

### 5.1 V14 Engine Core

All three bots share the same V14 engine:
- **Strategy:** DCA-only (long), no shorts in current configuration
- **Signal Stack:** ROUTER v2 (StochRSI, structure analysis, trend detection)
- **Lifecycle:** `IDLE → LONG_DCA (Layer 1..12) → TP Hit → IDLE`
- **Tick Interval:** 65 seconds (live), 1h candle-driven (paper)

### 5.2 Risk Profiles

| Parameter | Medium (Paper) | High (Live + ETF) |
|-----------|---------------|-------------------|
| Leverage | 1.5x | 1.5x (Live: 1.0x spot) |
| Base Order | 40% | 40% |
| SO Deviation | 2.0% | 1.5% |
| SO Step Mult | 1.5x | 1.5x |
| SO Vol Mult | 1.5x | 1.5x |
| Max Layers | 10 | 12 |
| Take Profit | 1.5% | 1.5% |

### 5.3 Bot Status Files

Each bot writes two files continuously:

**`status.json`** — Current state snapshot (read by dashboard sync):
- Running state, equity, cash, PnL
- Per-coin: state, layers, avg entry, current price, unrealized PnL, TP price, liquidation price
- Aggregate: total realized PnL, fees, deals completed, win rate, max drawdown
- Market context: regime, trend direction, fear/greed index

**`trades.csv`** — Complete trade history log

### 5.4 Exchange Interaction Safety (Live Bot)

The live bot (`run_v14_live_aster.py`) implements multiple layers of protection for exchange order execution:

#### 5.4.1 Sell Verification & Rollback

Before each engine tick, the bot captures a **pre-tick snapshot** of the engine state (positions, capital, cash, and trades list). If a SELL order fails on the exchange:

1. **Engine state is rolled back** to the pre-tick snapshot — positions, capital, and cash are restored
2. **Phantom trades are removed** — the engine's internal `trades` list is trimmed back to its pre-tick length, preventing failed sells from being counted as completed deals
3. **Failure is logged** with full context and a Telegram alert is sent
4. **The engine retries** on the next tick cycle (65 seconds later)

This prevents the critical bug where a failed sell could be counted as a completed deal, corrupting PnL accounting and the W/L record.

#### 5.4.2 Balance Reconciliation

The bot maintains two reconciliation mechanisms:

**Startup Reconciliation (`_reconcile_on_startup`):**
Runs every time the bot starts (after exchange connection + state restoration):
1. Queries actual exchange balances (USDT free + base asset total)
2. Computes total portfolio value for both exchange reality and engine state
3. If drift exceeds $1: adjusts `eng.capital` to absorb the difference
4. Syncs the bot's independent `self.cash` tracker to corrected engine capital
5. Saves corrected state and sends Telegram notification with adjustment details

**Periodic Reconciliation (`_maybe_reconcile`, every 5 minutes):**
- Compares engine state to exchange balances
- Syncs `self.cash` to `eng.capital` on every cycle to prevent tracker drift
- Alerts via Telegram if drift exceeds 10% of capital

#### 5.4.3 Order Execution Flow

```
Engine tick produces SELL action
    │
    ├─→ Capture pre-tick snapshot (positions, capital, trades)
    │
    ├─→ Submit MARKET SELL to exchange
    │       │
    │       ├─→ FILLED ✅
    │       │     └─→ Update engine state, log trade, save CSV
    │       │
    │       └─→ FAILED ❌ (InsufficientFunds, timeout, etc.)
    │             └─→ Rollback engine to pre-tick snapshot
    │             └─→ Trim phantom trades from engine.trades
    │             └─→ Log failure + Telegram alert
    │             └─→ Retry on next tick (65s)
    │
    └─→ Periodic reconciliation (every 5 min)
          └─→ Compare engine cash vs exchange USDT
          └─→ Correct drift if > $1
```

### 5.5 Bot Management

| Bot | Scheduled Task | Start Command |
|-----|---------------|---------------|
| V14 Live (ASTER) | `V14LiveAster` | `python -u -m trading.spot.run_v14_live_aster --confirm --skip-backfill` |
| V14 Paper | `V14PaperBot` | `python -u -m trading.spot.run_v14_paper --capital 10000 --profile medium --exchange hyperliquid --skip-backfill` |
| V14-ETF Paper | `V14ETFPaperBot` | `python -u -m trading.spot.run_v14etf_paper --capital 10000 --profile high --exchange hyperliquid --fresh` |

**Python Runtime:** `C:\Users\Never\AppData\Local\Programs\Python\Python312\python.exe`

**Restart procedure (Live Bot):**
1. Kill existing Python PID first
2. `Start-ScheduledTask -TaskName "V14LiveAster"`
3. Or manually: `python -u -m trading.spot.run_v14_live_aster --confirm --skip-backfill`

---

## 6. Presentation Layer — Dashboards

### 6.1 Dashboard Sync

**File:** `trading/sync_dashboard.ps1`  
**VBS Wrapper:** `trading/sync_dashboard_silent.vbs` (runs PowerShell hidden)  
**Scheduled Task:** `AIT_DashboardSync` (every 10 minutes)

**Process:**
1. Clone/pull the AIT GitHub repo to `$env:TEMP\ait-dashboard-sync`
2. Copy status files from bot state directories to `docs/data/` subdirectories
3. Copy scanner data (`cycle_scanner.json`, `scanner.json`)
4. Copy dashboard HTML files
5. Run `generate_daily_equity.py` to produce equity curve data
6. Ensure `.nojekyll` exists (prevents Jekyll processing)
7. `git add -A`, commit if changes exist, push to GitHub

**Data Flow:**
```
Bot state dirs:
  trading/spot/live/v14/     → docs/data/v14-live/
  trading/spot/paper/v14/    → docs/data/v14/
  trading/spot/paper/v14etf/ → docs/data/v14etf/

Scanner data:
  docs/data/v14/cycle_scanner.json (from scanner)
  docs/data/v14/daily_equity.json  (from equity generator)
```

### 6.2 Dashboard URLs

| Dashboard | URL |
|-----------|-----|
| V14 Live (ASTER) | `https://halo-effects.github.io/adaptive-intelligence-trading/d-984ae0d4ab9dc1a5.html` |
| V14 Paper | `https://halo-effects.github.io/adaptive-intelligence-trading/dashboardV14.html` |
| V14-ETF Paper | `https://halo-effects.github.io/adaptive-intelligence-trading/dashboardV14ETF.html` |
| Main Index | `https://halo-effects.github.io/adaptive-intelligence-trading/` |

### 6.3 Dashboard Data Integrity

The dashboards consume two data sources per bot: `status.json` (engine state) and `trades.csv` (trade log). These can diverge if the bot is restarted or if trades fail to log.

**Win/Loss Counter Logic:**
The dashboard uses `status.json` as the authoritative source for deal counts when `trades.csv` has fewer entries than `deals_completed`. This prevents stale or incomplete CSV data from overriding the engine's accurate counter.

```javascript
// Dashboard falls back to status.json when CSV is incomplete
if (trades.length > 0 && trades.length >= deals_completed) {
    // Count W/L from trades.csv rows
} else {
    // Use status.json deals_completed + win_rate
    wins = Math.round(dc * wr / 100);
}
```

**Trade Log (`trades.csv`) Recovery:**
The `TradeTracker` class reloads from `trades.csv` on bot restart via `load_existing()`. If the CSV was empty or incomplete at a prior restart point, historical trades are lost from the log. Recovery options:
1. Reconstruct from `bot.log` (contains all BUY/SELL actions with timestamps and prices)
2. Reconstruct from Telegram notifications (all orders are logged to Telegram)
3. The engine's `deals_completed` counter in `state.json` is always authoritative

**Known Limitation:** The `TradeTracker._deal_counter` resets based on what's loaded from CSV, not from the engine's deal count. This means deal IDs in the CSV may not match the engine's internal numbering after a restart with missing data.

### 6.4 GitHub Pages Notes

- Repository: `halo-effects/adaptive-intelligence-trading`
- Rate limit: Max 10 builds/hour (sync interval set to 10 min to stay under)
- `.nojekyll` must exist in `docs/` — sync script ensures this
- Authentication: `AIT_GITHUB_PAT` environment variable (User scope)

---

## 7. Scheduled Tasks Summary

| Task Name | Frequency | Script | Purpose |
|-----------|-----------|--------|---------|
| `AIT_CandleCollector` | Every 1 hour | `run_candle_collector.ps1` | Pull candles + refresh DCA Scores |
| `AIT_DashboardSync` | Every 10 min | `sync_dashboard_silent.vbs` → `sync_dashboard.ps1` | Push data to GitHub Pages |
| `V14LiveAster` | On startup | `run_v14_live_aster.py` | Live bot (ASTER/USDT, $300 real) |
| `V14PaperBot` | On startup | `run_v14_paper.py` | Paper bot (4 coins, $10K) |
| `V14ETFPaperBot` | On startup | `run_v14etf_paper.py` | ETF paper bot (5 coins, $10K) |

---

## 8. File System Layout

```
trading/
├── README.md                           # Legacy backtester docs
├── sync_dashboard.ps1                  # Dashboard → GitHub sync
├── sync_dashboard_silent.vbs           # VBS wrapper for hidden execution
├── spot/
│   ├── collect_scanner_candles.py      # Incremental candle collector (48 coins)
│   ├── v14_cycle_scanner.py            # DCA Cycle Scanner + scoring
│   ├── run_candle_collector.ps1        # Pipeline wrapper (collect + scan)
│   ├── generate_daily_equity.py        # Equity curve JSON generator
│   ├── pull_candles.py                 # Legacy candle puller (CSV, limited coins)
│   ├── backfill_etf_candles.py         # One-time ETF coin backfill
│   ├── run_v14_live_aster.py           # Live bot runner
│   ├── run_v14_paper.py                # Paper bot runner
│   ├── run_v14etf_paper.py             # ETF paper bot runner
│   ├── exchange_client.py              # Exchange abstraction layer
│   ├── data/
│   │   ├── candles.db                  # SQLite candle database (~212 MB)
│   │   ├── score_history.json          # DCA Score history (180-day rolling, for trend calc)
│   │   └── collector.log               # Candle collector pipeline log
│   ├── live/
│   │   └── v14/                        # Live bot state (status.json, trades.csv, state.json)
│   └── paper/
│       ├── v14/                        # Paper bot state
│       └── v14etf/                     # ETF paper bot state
│
docs/
├── index.html                          # AIT landing page
├── dashboardV14.html                   # V14 Paper dashboard
├── dashboardV14ETF.html                # V14-ETF dashboard
├── d-984ae0d4ab9dc1a5.html             # V14 Live dashboard
├── pricing.html                        # Pricing page
├── risk-profiles.html                  # Risk profile documentation
├── adaptive-intelligence.html          # Product overview
├── qb-theme.css                        # Dashboard theme
├── .nojekyll                           # Prevents Jekyll processing
└── data/
    ├── v14-live/                       # Synced live bot data
    │   ├── status.json
    │   └── trades.csv
    ├── v14/                            # Synced paper bot data + scanner
    │   ├── status.json
    │   ├── trades.csv
    │   ├── cycle_scanner.json          # DCA Score rankings
    │   ├── daily_equity.json           # Equity curve for calculator
    │   └── scanner.json                # Legacy scanner output
    └── v14etf/                         # Synced ETF bot data
        ├── status.json
        └── trades.csv
```

---

## 9. Monitoring & Alerting

### 9.1 Heartbeat Monitoring

OpenClaw's heartbeat system (every 30 min) checks:
- Bot health: `status.json` staleness (alert if > 65 min)
- Live bot: `running` flag, drawdown threshold (> 15%), capital drift
- Paper bots: process running, status freshness
- Dashboard sync: task health, GitHub Pages freshness
- Cron job health: consolidation log for failures

### 9.2 Telegram Notifications

All bots send real-time notifications to Telegram:
- Order execution (buy/sell)
- Deal completion (TP hit)
- Position updates (new safety order layers)
- Error conditions
- Scanner summary (when run with Telegram enabled)

Prefixes: `[V14-LIVE]`, `[V14]`, `[V14-ETF]`, `[SCANNER]`

### 9.3 Alert Thresholds

| Condition | Severity | Action |
|-----------|----------|--------|
| Bot stopped / status stale > 65 min | High | Alert Brett immediately |
| Live bot drawdown > 15% | High | Alert Brett |
| Live bot capital drift > 10% | Medium | Alert Brett |
| Dashboard sync failure | Low | Note in heartbeat, auto-recovers |
| Candle collector failure | Medium | Alert — DCA Scores will go stale |

---

## 10. Cloud Migration Guide

### 10.1 Current Environment

- **Host:** Windows 11 laptop (`LAPTOP-CLKA4E8J`)
- **Python:** 3.12 (`C:\Users\Never\AppData\Local\Programs\Python\Python312\python.exe`)
- **Scheduling:** Windows Scheduled Tasks
- **Process Management:** Scheduled Tasks with manual restart
- **Database:** Local SQLite file
- **Dashboard Hosting:** GitHub Pages (free)

### 10.2 Cloud Target Architecture

For production deployment on a cloud server (Linux VPS or container):

**Compute:**
- 1 vCPU, 2GB RAM minimum (bots are lightweight)
- Persistent storage for `candles.db` (~250 MB, growing)

**Scheduling Replacement:**
| Windows | Linux/Cloud |
|---------|-------------|
| Windows Scheduled Tasks | `cron` or `systemd.timer` |
| VBS hidden wrappers | Not needed (cron runs headless) |
| PowerShell scripts | Bash scripts or direct Python calls |

**Process Management:**
| Current | Cloud |
|---------|-------|
| Scheduled Task (on startup) | `systemd` service units |
| Manual PID kill for restart | `systemctl restart v14-live` |
| No auto-restart on crash | `Restart=on-failure` in systemd |

**Example systemd unit (live bot):**
```ini
[Unit]
Description=V14 Live Trading Bot (ASTER/USDT)
After=network.target

[Service]
Type=simple
User=ait
WorkingDirectory=/opt/ait
ExecStart=/usr/bin/python3 -u -m trading.spot.run_v14_live_aster --confirm --skip-backfill
Restart=on-failure
RestartSec=30
Environment=AIT_TG_TOKEN=xxx
Environment=AIT_TG_CHAT_ID=xxx

[Install]
WantedBy=multi-user.target
```

**Example crontab:**
```cron
# Candle collector + scanner (hourly)
0 * * * * cd /opt/ait && python3 trading/spot/collect_scanner_candles.py && python3 -m trading.spot.v14_cycle_scanner --no-telegram >> /var/log/ait/collector.log 2>&1

# Dashboard sync (every 10 min)
*/10 * * * * cd /opt/ait && bash scripts/sync_dashboard.sh >> /var/log/ait/dashboard_sync.log 2>&1
```

**Database Migration:**
- SQLite works fine at current scale (48 coins, 1h candles)
- If scaling beyond ~200 coins or adding 1m/5m candles: consider PostgreSQL or TimescaleDB
- Migration path: `sqlite3 candles.db .dump | psql ait_candles`

**Environment Variables (required):**
```
AIT_GITHUB_PAT=...          # GitHub push access
AIT_TG_TOKEN=...            # Telegram bot token
AIT_TG_CHAT_ID=...          # Telegram chat ID
# Exchange API keys stored in .env files per bot
```

**Dashboard Sync (Linux):**
Replace `sync_dashboard.ps1` with a bash equivalent:
```bash
#!/bin/bash
REPO_DIR="/tmp/ait-dashboard-sync"
# ... same logic: git pull, copy files, commit, push
```

### 10.3 Migration Checklist

- [ ] Provision cloud server (VPS or container)
- [ ] Install Python 3.12+, git, ccxt
- [ ] Copy workspace (`trading/`, `docs/`)
- [ ] Copy `candles.db` (or backfill fresh)
- [ ] Set environment variables
- [ ] Create systemd units for each bot
- [ ] Create cron jobs for collector + sync
- [ ] Set up log rotation (`/etc/logrotate.d/ait`)
- [ ] Verify Telegram notifications work
- [ ] Verify GitHub Pages sync works
- [ ] Set up monitoring (uptime check on bot status endpoints)
- [ ] DNS/firewall: no inbound ports needed (all outbound to exchanges + GitHub)

---

## 11. Capital Management System

**Design Document:** `projects/ait-product/portfolio-capital-management.md`

The `v14_capital_manager.py` introduces a robust capital routing mechanism for the V14 Engine. It manages the distribution of capital between active trading and reserve holdings, ensuring strict risk management and dynamic allocation based on the DCA Score. This allows the system to scale from single-coin bots to a multi-coin portfolio.

### 11.1 Core Rules

1. **Pool Split:**
   - 75% Active Pool (Allocated for standard trading layers 1-5).
   - 25% Reserve Pool (Saved for emergency/deep layers 6+).

2. **The Hurdle Rate:**
   - A coin MUST have a DCA Score >= 5.0 (calculated over a 30-day window) to qualify for any capital allocation.

3. **Proportional Weighting:**
   - Capital is distributed proportionally among qualifying coins based on their relative DCA Scores. Higher score = more capital.

4. **Risk Caps:**
   - Maximum allocation per coin: 20% of the *Active Pool*.
   - Maximum number of concurrent coins: 10.

5. **The "Sidelines" Default:**
   - If the risk caps are hit (e.g., highly concentrated high scores) and leftover capital exists in the Active Pool, that excess capital remains unallocated in cash (on the sidelines).

6. **Reserve Release:**
   - Capital from the Reserve Pool is released on a strictly linear, first-come, first-served basis for any active coin that requires capital for Layer 6 or deeper.

7. **Routing (Deal Close):**
   - When a deal closes (profit taken), the freed capital returns entirely to the Active Pool. It is then immediately re-routed based on the *current day's* scanner rankings and DCA scores.

### 11.2 Class Architecture: `CapitalRouter`

The primary class handling these operations is `CapitalRouter`.

**Properties:**
- `total_equity`: Total account balance.
- `active_pool`: Available cash in the 75% allocation.
- `reserve_pool`: Available cash in the 25% allocation.
- `active_allocations`: Dictionary tracking current locked capital per coin.

**Key Methods:**
- `__init__(self, initial_capital: float)`
- `daily_rebalance(self, scanner_rankings: list[dict]) -> dict`
  - Processes the daily scanner data, applies rules, and returns target allocations.
- `request_reserve_capital(self, coin: str, amount: float) -> float`
  - Handles Layer 6+ requests. Returns the granted amount (up to the requested amount, limited by available reserve).
- `register_deal_close(self, coin: str, returned_capital: float)`
  - Returns capital to the Active Pool for re-routing.
- `_calculate_weights(self, qualifying_coins: list[dict]) -> dict`
  - Internal math for proportional DCA score weighting.

### 11.3 Interaction with `V14Engine`

1. **Initialization:** The `V14Engine` instantiates the `CapitalRouter` upon startup, feeding it the total account balance.
2. **Daily Cron/Tick:** Before placing new Layer 1 orders, the `V14Engine` passes the updated daily scanner rankings to `CapitalRouter.daily_rebalance()`.
3. **Execution:** The engine receives a dictionary of maximum permitted allocations per coin from the router and adjusts its active orders accordingly.
4. **Deep Layers (6+):** If the engine attempts to place a Layer 6+ order, it calls `request_reserve_capital()`. If the router returns > 0, the order is placed; otherwise, it is skipped.
5. **Profit Taking:** Upon a sell order filling, the `V14Engine` triggers `register_deal_close()`, allowing the router to update its internal pool state.

### 11.4 Exact Mathematical Flow (Daily Rebalance)

Assume the `active_pool` has $10,000.

**Step 1: Filter and Sort**
- Filter all scanned coins where `dca_score >= 5.0`.
- Sort descending by `dca_score`.
- Keep only the top 10 coins (`max_coins = 10`).

**Step 2: Calculate Sum of Scores**
- `total_score = sum(coin.dca_score for coin in top_10_coins)`

**Step 3: Calculate Raw Proportions**
- For each coin: `raw_allocation = (coin.dca_score / total_score) * active_pool`

**Step 4: Apply Risk Caps**
- Cap limit per coin: `max_cap = 0.20 * active_pool`
- For each coin:
  - If `raw_allocation > max_cap`, set `final_allocation = max_cap`.
  - Else, `final_allocation = raw_allocation`.

**Step 5: Handle the Sidelines**
- `total_allocated = sum(final_allocation for all coins)`
- `sidelines_cash = active_pool - total_allocated`
- The `sidelines_cash` is explicitly left unallocated to act as a buffer/cash drag, ensuring risk rules are not violated just to deploy capital.

---

## Appendix A: Backfill Scripts

These are one-time scripts used during initial setup, not part of the recurring pipeline:

| Script | Purpose |
|--------|---------|
| `pull_candles.py` | Legacy: pulls 5m candles to CSV for limited coins (Aster + HL spot) |
| `backfill_etf_candles.py` | One-time: backfills LTC, ADA, HBAR 1h candles + daily candles from Binance |

---

## Appendix B: Known Issues

| Issue | Impact | Status | Workaround |
|-------|--------|--------|------------|
| MKR candles stopped Sept 2025 | MKR excluded from scanner rankings | Open | Needs manual backfill or removal from universe |
| ASTER candles not in hourly pipeline | ASTER data may lag | Open | Live bot self-collects; scanner marks as immature (< 6mo) |
| Exit code 1 on stderr output | PowerShell treats Python stderr as error | Won't fix | Non-blocking; scripts complete successfully despite error code |
| Failed sell counted as completed deal | Engine/exchange cash divergence ($10.91) | **Fixed 2026-03-05** | Sell verification + rollback + startup reconciliation added |
| trades.csv incomplete after restarts | Dashboard showed 1W instead of 3W | **Fixed 2026-03-05** | Dashboard falls back to status.json; trades reconstructed from bot.log |
| `self.cash` tracker corruption (-$34.33) | Bot's independent cash tracker diverged from engine | **Fixed 2026-03-05** | Periodic reconciliation syncs self.cash to eng.capital every 5 min |
| trades.csv drift from exchange (dupes, missing) | 8 duplicate deal IDs, missing trades from forced closes | **Fixed 2026-05-05** | Trade reconciliation system: startup 48h check, RECONCILE command, `reconcile_trades.py` CLI |
| Aster DEX API fill retention ~30 days | Cannot fully rebuild trade history from exchange | Open | Reconciliation labels expired fills as "unverifiable"; CSV is kept as fallback |

---

## Appendix C: Revision History

| Date | Version | Changes |
|------|---------|---------|
| 2026-03-05 | 1.0 | Initial V14 system spec. Documents full pipeline from candle collection through DCA scoring to dashboard sync. Includes cloud migration guide. |
| 2026-03-05 | 1.1 | Added Section 5.4 (Exchange Interaction Safety): sell verification/rollback, startup + periodic balance reconciliation, order execution flow diagram. Added Section 6.3 (Dashboard Data Integrity): W/L counter fallback logic, trade log recovery procedures. Updated Appendix B with 3 resolved incidents from 2026-03-05. |
| 2026-03-05 | 1.2 | Added Section 4.6 (DCA Trend Score): score history tracking, 7d/14d/30d trend computation, dashboard trend arrows (↗→↘). Updated Section 11 to reference portfolio-capital-management.md design doc. Added score_history.json to file layout. |
| 2026-05-05 | 1.3 | Trade reconciliation system: standalone CLI tool (`reconcile_trades.py`), startup reconciliation (`_reconcile_trades_on_startup()`), RECONCILE Telegram command, deal ID assignment fix. Aster API has ~30-day fill retention; reconciliation handles gracefully. See V14PM_SYSTEM_ARCHITECTURE.md §6.8. |
| 2026-05-06 | 1.4 | Restored v14_capital_manager.py (sync script corruption April 15). Fixed T1 gate/rebalance desync: `active_allocations` now synced after `_do_rebalance()`. Fixed liquidity filter crash (`client.exchange` → `client._exchange`). Fixed dashboard sync deleting source files. Fixed dashboardV14PM.html loading paper data instead of live. |
