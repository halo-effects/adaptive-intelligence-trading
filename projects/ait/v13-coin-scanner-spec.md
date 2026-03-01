# V13 Coin Scanner System — Technical Specification

**Version:** 1.0
**Date:** 2026-02-25
**Engine:** `v13_phase_backtest_v8.py` (43KB, 4-phase signal-driven architecture)
**Status:** Live, running daily at 6:00 AM PST

---

## 1. Overview

The V13 Coin Scanner is the intelligence layer of the Adaptive Intelligence Trading (AIT) system. It evaluates all 44 CFGI-compatible cryptocurrency tokens by running each through the **exact same V13 phase backtest engine** used by the live paper trading bot. This ensures:

- **Cold start accuracy:** The phase detected by the scanner is the exact phase the live bot would start in if deployed on that coin.
- **One engine for everything:** Backtest validates -> scanner evaluates -> paper bot proves -> same code goes to production.
- **Rolling evaluation:** A 90-day sliding window adapts to current market conditions, re-ranking coins daily.

The scanner serves as both a **live test bed** (validating V13 performance across diverse market conditions) and a **compass** (guiding capital deployment into the most favorable coins for our system).

---

## 2. System Architecture

```
                    +------------------+
                    |  Daily Collector  |  5:30 AM PST
                    |  (data pipeline)  |
                    +--------+---------+
                             |
              +--------------+--------------+
              |              |              |
        Binance API    CFGI API     Signal Engine
        (1h candles)   (sentiment)  (V13SignalPack)
              |              |              |
              v              v              v
        +------------------------------------+
        |         candles.db (SQLite)         |
        |  candles | candles_daily | cfgi_daily|
        |  signal_snapshots | coin_correlations|
        +------------------------------------+
                             |
                    +--------+---------+
                    |   V13 Scanner    |  6:00 AM PST
                    |  (44-coin sweep) |
                    +--------+---------+
                             |
              +--------------+--------------+
              |              |              |
        scanner_t2.json  scanner_results  phase_transitions
        (dashboard)      (DB history)     (DB history)
              |
              v
        +------------------------------------+
        |   Dashboard (GitHub Pages)          |
        |   Live Opportunity Table            |
        |   Synced every 2 min               |
        +------------------------------------+
```

---

## 3. File Inventory

### Core Scanner
| File | Purpose |
|------|---------|
| `trading/spot/coin_scanner_v13.py` | Main scanner module — data pipeline, V13 backtest, scoring, output |
| `trading/spot/run_scanner_v13.py` | Runner entry point (`python -u -m trading.spot.run_scanner_v13`) |

### Data Collection
| File | Purpose |
|------|---------|
| `trading/spot/daily_collector.py` | Daily data pipeline — candles, CFGI, signal snapshots, correlations |
| `trading/spot/run_daily_collector.py` | Runner entry point (`python -u -m trading.spot.run_daily_collector`) |
| `trading/spot/db_migrate_v13_analytics.py` | Creates 5 analytics tables (IF NOT EXISTS) |

### V13 Engine (Dependencies)
| File | Purpose |
|------|---------|
| `trading/spot/backtest_results/v13/v13_phase_backtest_v8.py` | The V13 backtest engine (43KB) — **THE** correct engine |
| `trading/spot/backtest_results/v13/v13_signals.py` | V13SignalPack — all signal computers (StochRSI, ADX, BMSB, HVF, CFGI, SMA200) |
| `trading/spot/backtest_results/v13/test_hvf_daily.py` | HVF (Harmonic Volume Flow) scorer — used by FLAT phase routing |
| `trading/spot/backtest_results/v13/build_daily_candles.py` | Functions: `aggregate_daily()`, `compute_indicators()` |

### External Clients
| File | Purpose |
|------|---------|
| `trading/spot/cfgi_client.py` | CFGI API client (cfgi.io) — rate-limited, cached, multi-token fetch |

### Dashboard
| File | Purpose |
|------|---------|
| `docs/dashboardV13.html` | Dashboard reads `scannerData.rankings[]` for Opportunity table |
| `docs/data/scanner_t2.json` | Scanner output consumed by dashboard (synced via `AIT_DashboardSync`) |
| `trading/sync_dashboard.ps1` | PowerShell sync script (runs every 2 min) |

---

## 4. Database Schema

### Database: `trading/spot/data/candles.db` (SQLite)

#### Existing Tables (used by scanner)

**`candles`** — Raw 1h OHLCV data
```
id INTEGER PRIMARY KEY, symbol TEXT, timestamp INTEGER,
open REAL, high REAL, low REAL, close REAL, volume REAL, timeframe TEXT
```
- ~8,760 rows per coin (365 days of 1h candles)
- 44+ symbols, sourced from Binance
- `timeframe` must be `'1h'` for new inserts

**`candles_daily`** — Daily OHLCV with pre-computed technical indicators
```
symbol TEXT, date TEXT, timestamp INTEGER,
open REAL, high REAL, low REAL, close REAL, volume REAL, candle_count INTEGER,
sma20 REAL, sma50 REAL, sma200 REAL,
bb_width REAL, bb_pct REAL,
atr14 REAL, atr_pct REAL,
adx REAL, plus_di REAL, minus_di REAL,
rsi14 REAL,
consec_hh_hl INTEGER, consec_lh_ll INTEGER,
sma50_slope REAL, sma200_slope REAL,
price_vs_sma50 REAL, price_vs_sma200 REAL
```
- Built from 1h candles via `aggregate_daily()` + `compute_indicators()`
- V13 signals read these columns directly (not computed live)
- Requires ~200 days of data for SMA200 warmup

**`cfgi_daily`** — Per-coin Fear & Greed Index history
```
symbol TEXT, date TEXT, cfgi REAL
```
- 23,666 rows across 44 tokens
- History back to Jan 2025 for most coins, 2022 for BTC/ETH/SOL
- Sourced from cfgi.io API (per-coin, not market-wide)

#### Analytics Tables (created 2026-02-25)

**`scanner_results`** — Historical scanner scores per coin per day
```
symbol TEXT, scan_date TEXT, composite_score REAL, closed_roi REAL,
win_rate REAL, max_drawdown REAL, total_deals INTEGER, current_phase TEXT,
markup_cycles INTEGER, shorts_enabled INTEGER, outperformance REAL,
buy_hold_return REAL, time_markup_pct REAL, time_dca_pct REAL,
time_flat_pct REAL, time_markdown_pct REAL, has_coin_cfgi INTEGER,
daily_roi_pct REAL
```
- One row per coin per scan day
- Enables score timeline analysis: "How has ALGO's score trended over 3 months?"

**`phase_transitions`** — Every phase change from backtests
```
symbol TEXT, date TEXT, from_phase TEXT, to_phase TEXT,
trigger_signal TEXT, price REAL, equity REAL,
adx_value REAL, stochrsi_2w_k REAL, cfgi_value REAL, scan_date TEXT
```
- Extracted from V13 backtest `phases` list after each scan
- Enables: "What ADX level triggers the most accurate DCA->MARKUP transitions?"

**`signal_snapshots`** — Daily signal values for all coins
```
symbol TEXT, date TEXT, adx REAL, plus_di REAL, minus_di REAL,
stoch_1w_k REAL, stoch_2w_k REAL, stoch_3w_k REAL,
sma50_slope REAL, sma200_slope REAL,
consec_hh_hl INTEGER, consec_lh_ll INTEGER,
hvf_score REAL, cfgi_value REAL, price REAL,
price_vs_sma50 REAL, price_vs_sma200 REAL,
rsi14 REAL, atr_pct REAL, bb_pct REAL
```
- Full indicator state captured daily for every coin
- Enables backtesting new signal combinations without re-downloading candles

**`coin_correlations`** — Weekly correlation matrix
```
date TEXT, coin_a TEXT, coin_b TEXT,
correlation_30d REAL, correlation_90d REAL
```
- Pearson correlation of daily returns
- Computed on Sundays (or first run if empty)
- Enables: "Which coin pairs give best diversification?"

**`trade_context`** — Enriched trade log with decision context
```
symbol TEXT, date TEXT, action TEXT, phase TEXT, price REAL,
amount REAL, pnl_pct REAL, pnl_usd REAL, entry_price REAL,
hold_duration_days REAL, adx_at_entry REAL, cfgi_at_entry REAL,
adx_at_exit REAL, cfgi_at_exit REAL, trigger_signal TEXT,
was_winner INTEGER, scan_date TEXT
```
- Every trade from every backtest, with P&L and win/loss flag
- Enables: "What CFGI level at entry predicts the highest win rate?"

---

## 5. Token Universe

### All 44 CFGI-Compatible Tokens

```python
ALL_TOKENS = {
    "AAVE": "AAVE/USDT", "ADA": "ADA/USDT", "ALGO": "ALGO/USDT",
    "ARB": "ARB/USDT", "ASTER": "ASTER/USDT", "ATOM": "ATOM/USDT",
    "AVAX": "AVAX/USDT", "AXS": "AXS/USDT", "BCH": "BCH/USDT",
    "BNB": "BNB/USDT", "BONK": "BONK/USDT", "BTC": "BTC/USDT",
    "CRV": "CRV/USDT", "DOGE": "DOGE/USDT", "DOT": "DOT/USDT",
    "ETH": "ETH/USDT", "FET": "FET/USDT", "FIL": "FIL/USDT",
    "FLOKI": "FLOKI/USDT", "FTM": "FTM/USDT", "GALA": "GALA/USDT",
    "GRT": "GRT/USDT", "HYPE": "HYPE/USDC", "INJ": "INJ/USDT",
    "JUP": "JUP/USDT", "LINK": "LINK/USDT", "LTC": "LTC/USDT",
    "MANA": "MANA/USDT", "MATIC": "MATIC/USDT", "NEAR": "NEAR/USDT",
    "PEPE": "PEPE/USDC", "RUNE": "RUNE/USDT", "SAND": "SAND/USDT",
    "SEI": "SEI/USDT", "SHIB": "SHIB/USDT", "SOL": "SOL/USDT",
    "SUI": "SUI/USDT", "TAO": "TAO/USDT", "TON": "TON/USDT",
    "TRUMP": "TRUMP/USDC", "UNI": "UNI/USDT", "WIF": "WIF/USDT",
    "XRP": "XRP/USDT", "ZEC": "ZEC/USDT",
}
```

### Exchange Availability

```python
EXCHANGE_AVAILABILITY = {
    "ASTER": ["aster"], "BNB": ["aster"],
    "BTC": ["aster", "hyperliquid"], "DOGE": ["aster", "hyperliquid"],
    "ETH": ["aster", "hyperliquid"], "SOL": ["aster", "hyperliquid"],
    "XRP": ["aster", "hyperliquid"], "HYPE": ["hyperliquid"],
    "PEPE": ["hyperliquid"], "TRUMP": ["hyperliquid"],
    "LINK": ["hyperliquid"], "AVAX": ["hyperliquid"],
    "SUI": ["hyperliquid"], "SEI": ["hyperliquid"],
}
```

Coins not in this map show "no exchange" on the dashboard — they're tracked for analytical purposes but not yet tradeable on our connected exchanges.

### CFGI Tokens (20 with coin-specific sentiment)

```python
CFGI_TOKENS = [
    "BTC", "ETH", "SOL", "BNB", "HYPE", "ASTER", "DOGE", "PEPE",
    "AVAX", "ADA", "XRP", "DOT", "LINK", "UNI", "AAVE", "SUI",
    "TON", "ARB", "INJ", "TRUMP",
]
```

Remaining 24 tokens use market-wide FGI as fallback.

### Known Issues
| Token | Issue | Workaround |
|-------|-------|------------|
| ASTER | `isnan` error on SMA200 overextension (only 143 days of data) | Needs >200 days for SMA200 warmup |
| HYPE | Not on Binance (USDC pair only) | Existing DB data from Hyperliquid; scanner skips Binance fetch |
| FTM | Delisted on Binance | Skip; remove from token list when confirmed |
| MATIC | Migrated to POL on Binance | Skip; update symbol or remove |

---

## 6. Scanner Pipeline

### Step-by-Step Execution Flow

#### Step 1: Data Pipeline (per coin)
1. **Check 1h candles** in `candles` table — need minimum 290 days (200 SMA warmup + 90 backtest)
2. **Fetch from Binance** via ccxt if missing/stale — append-only INSERTs, no overwrites
3. **Build daily candles** — `aggregate_daily()` resamples 1h to daily OHLCV, `compute_indicators()` computes all 18 technical indicators
4. **DELETE + INSERT** daily candles per symbol (full rebuild ensures indicator consistency)

#### Step 2: CFGI Check
1. Query cfgi.io API via `CFGIClient.get_current(tokens)` for all 20 supported tokens
2. Returns dict of `{token: cfgi_value}` (0-100 scale)
3. Record which coins have coin-specific CFGI for ranking metadata

#### Step 3: V13 Backtest (per coin)
1. Create `V13SignalPack(coin, db_path)` — loads daily candles + CFGI from DB, builds all signal objects
2. Create `V13Config()` with overrides:
   - `START_DATE` = 90 days ago
   - `END_DATE` = today
   - `CAPITAL` = $2,500 (per-coin allocation)
3. Create `V13BacktestV8(pack, config)` — the actual phase-riding engine
4. Call `bt.run()` — returns result dict with ROI, trades, phases, equity curve
5. Extract metrics: `closed_roi`, `win_rate`, `max_drawdown`, `outperformance`, phase distribution

#### Step 4: Scoring & Ranking
Composite score (0-100 scale):
```
composite = 0.35 * roi_score      # closed_roi: 50% ROI = perfect 100
           + 0.25 * wr_score      # win_rate: 100% = perfect 100
           + 0.20 * out_score     # outperformance vs buy-and-hold: 50% = perfect 100
           + 0.20 * ra_score      # risk-adjusted (closed_roi / max_dd): 3.0 ratio = perfect 100
```

Scoring handles edge cases:
- Negative ROI: `max(0, 50 + closed_roi)` — penalizes but doesn't zero out
- Zero drawdown: perfect risk-adjusted score if ROI >= 0
- No trades: scored purely on outperformance (capital preservation in downtrend)

#### Step 5: Output
1. **JSON files** — `trading/spot/data/scanner_v13.json` and `docs/data/scanner_t2.json`
2. **DB analytics** — `scanner_results`, `phase_transitions`, `trade_context` tables
3. **Dashboard** — synced to GitHub Pages within 2 minutes via `AIT_DashboardSync`

---

## 7. V13 Engine Reference

The scanner uses the exact same engine as the live paper bot. This section documents how V13 evaluates each coin.

### 4 Phases

| Phase | Description | Capital Action | Exit Signal |
|-------|-------------|----------------|-------------|
| **DCA** | Accumulating position via dollar-cost-average grid | 8% base order, 1.5x SO multiplier, 1.5% TP, max 8 layers | HH_HL + Fib_support -> MARKUP; ADX>20 + Fib_break -> MARKDOWN |
| **MARKUP** | Trend confirmed, deploying capital in tiers | T1=60%, T2=20%, T3=10% (front-loaded) | 2W StochRSI OB93 (top detection) -> FLAT; Failure detector (25% DD + ADX>25) -> MARKDOWN |
| **FLAT** | Post-top/post-markdown evaluation | Holding, no new positions | HVF-driven routing: >0.4 = stay flat, <0.2 for 7d = DCA; ADX<20 for 14d confirmed = DCA; Max 42 days = default DCA |
| **MARKDOWN** | Riding shorts down | T1=60%, T2=20%, T3=10% (symmetric to markup) | ADX<20 for 21 consecutive days = DCA; Failure detector (25% above entry + ADX>25) |

### Key Signal Components
- **HH_HL + Fib_support**: Higher highs + higher lows + price near Fibonacci support level (94.0 score, 100% accuracy)
- **ADX + Fib_break**: ADX>20 confirming trend + Fibonacci level broken (94.0 score, 100% accuracy)
- **2W StochRSI OB93**: 2-week Stochastic RSI crosses below 93 from above — primary top detector
- **HVF (Harmonic Volume Flow)**: Composite harmonic pattern score for FLAT phase routing
- **ADX Ranging**: ADX staying below 20 for sustained period indicates sideways market

### V13Config Defaults (High Profile)
```python
CAPITAL = 2500                    # Per-coin allocation
TIER1_PCT = 0.60                  # Entry position (60%)
TIER2_PCT = 0.20                  # Confirmation add (20%)
TIER3_PCT = 0.10                  # Momentum add (10%)
SHORT_TIER1/2/3_PCT = same        # Symmetric shorts
DCA_BO_PCT = 0.08                 # 8% base order
DCA_SO_DEVIATION = 0.025          # 2.5% between layers
DCA_MAX_LAYERS = 8                # Maximum safety orders
DCA_TP_PCT = 0.015                # 1.5% take profit
MIN_PHASE_DAYS = 3                # Minimum hold before transition
MARKUP_FAIL_DD_PCT = 0.25         # 25% drawdown = failed markup
FLAT_MAX_EVAL_DAYS = 42           # 6 weeks max in FLAT
PHASE_ADX_SUSTAINED_DAYS = 21     # ADX<20 for 21d = ranging exit
```

---

## 8. Daily Schedule

| Time (PST) | Job | Cron ID | What It Does |
|-------------|-----|---------|--------------|
| **5:30 AM** | V13 Daily Collector | `a520cd05` | Fetch new 1h candles, rebuild daily indicators, collect CFGI, compute signal snapshots, weekly correlations |
| **6:00 AM** | V13 Daily Scanner | `ef85844d` | Run 44-coin V13 backtest, store analytics, update dashboard JSON |

Both jobs run as isolated cron sessions with results announced to the main session.

### Dashboard Sync
- **Task:** `AIT_DashboardSync` (Windows Scheduled Task, every 2 min)
- **Script:** `trading/sync_dashboard.ps1`
- **Pushes:** `docs/data/scanner_t2.json`, `docs/data/v13/status.json`, `docs/data/v13/trades.csv` to GitHub Pages

---

## 9. Dependencies

### Python Packages
```
ccxt          # Exchange API (Binance candle fetching)
pandas        # Data manipulation, resampling, indicators
numpy         # Numerical computation
sqlite3       # Database (built-in)
```

### Environment Variables
```
CFGI_API_KEY  # cfgi.io API key for per-coin sentiment data
```

### System Requirements
- **Python:** 3.12 (`C:\Users\Never\AppData\Local\Programs\Python\Python312\python.exe`)
- **OS:** Windows (PowerShell, cp1252 encoding — ASCII-only in print statements)
- **DB:** SQLite (`trading/spot/data/candles.db`, ~70MB)
- **Network:** Binance API (candles), cfgi.io API (sentiment)

---

## 10. Dashboard Integration

The dashboard reads `docs/data/scanner_t2.json` (synced from `trading/spot/data/scanner_v13.json`).

### JSON Output Format
```json
{
  "timestamp": "2026-02-25T...",
  "engine": "v13_phase_backtest_v8",
  "profile": "high",
  "timeframe": "daily_signals_1h_dca",
  "backtest_days": 90,
  "candidates_tested": 44,
  "passed": 40,
  "cfgi_summary": {
    "coin_cfgi": 20,
    "market_fallback": 20
  },
  "rankings": [
    {
      "symbol": "ARB/USDT",
      "total_deals": 1,
      "win_rate": 0.0,
      "total_profit_pct": 0.0,
      "max_drawdown_pct": 0.0,
      "daily_roi_pct": 0.0,
      "composite_score": 57.5,
      "has_coin_cfgi": true,
      "available_on": [],
      "engine": "v13_phase_backtest_v8",
      "current_phase": "MARKDOWN",
      "markup_cycles": 0,
      "shorts_enabled": true,
      "time_markup_pct": 0,
      "time_dca_pct": 3,
      "time_flat_pct": 0,
      "time_markdown_pct": 97,
      "closed_roi": 0.0,
      "buy_hold_return": -65.0,
      "outperformance": 65.0
    }
  ]
}
```

### Dashboard Fields Used
| Field | Dashboard Column |
|-------|------------------|
| `symbol` | COIN |
| `current_phase` | PHASE (with color-coded pill) |
| `composite_score` | GRADE (letter grade A+ through F) |
| `win_rate`, `total_profit_pct`, `max_drawdown_pct` | SIGNAL (user-friendly summary) |
| `available_on` | SIGNAL (exchange availability) |
| Phase-based lookup | OPPORTUNITY (buy/wait/hold recommendation) |

### Grade Scale
| Score | Grade | Color |
|-------|-------|-------|
| 95+ | A+ | Green |
| 85-94 | A | Green |
| 75-84 | B+ | Cyan |
| 60-74 | B | Indigo |
| 45-59 | C | Amber |
| 30-44 | D | Amber |
| <30 | F | Red |

Active coins (in the paper bot) use phase-based grading instead of composite score.

---

## 11. Usage

### Run Full Scan (all 44 coins)
```powershell
python -u -m trading.spot.run_scanner_v13
```

### Run Subset (specific coins)
```powershell
python -u -m trading.spot.run_scanner_v13 ETH SOL BTC LINK
```

### Run Daily Collector
```powershell
python -u -m trading.spot.run_daily_collector
```

### Run DB Migration Only
```powershell
python -u -m trading.spot.db_migrate_v13_analytics
```

---

## 12. Analytical Queries (Future Use)

These queries become possible as the analytics tables accumulate data:

### Score Timeline
```sql
-- How has a coin's score trended over time?
SELECT scan_date, composite_score, closed_roi, current_phase
FROM scanner_results WHERE symbol='ETH/USDT'
ORDER BY scan_date;
```

### Best Phase Transition Conditions
```sql
-- What ADX values produce the most profitable DCA->MARKUP transitions?
SELECT AVG(adx_value), AVG(cfgi_value), COUNT(*)
FROM phase_transitions
WHERE from_phase='DCA' AND to_phase='MARKUP'
GROUP BY ROUND(adx_value/5)*5;  -- bucket by ADX range
```

### Win Rate by CFGI at Entry
```sql
-- What CFGI level at entry predicts highest win rate?
SELECT ROUND(cfgi_at_entry/10)*10 as cfgi_bucket,
       COUNT(*) as trades,
       SUM(was_winner)*100.0/COUNT(*) as win_rate_pct
FROM trade_context
WHERE cfgi_at_entry IS NOT NULL
GROUP BY cfgi_bucket
ORDER BY cfgi_bucket;
```

### Correlation-Based Diversification
```sql
-- Find least correlated coin pairs for portfolio construction
SELECT coin_a, coin_b, correlation_30d, correlation_90d
FROM coin_correlations
WHERE date = (SELECT MAX(date) FROM coin_correlations)
ORDER BY ABS(correlation_30d) ASC
LIMIT 20;
```

### Signal Pattern at Losing Trades
```sql
-- What signal patterns preceded losing trades?
SELECT tc.symbol, tc.action, tc.pnl_pct, ss.adx, ss.cfgi_value, ss.stoch_2w_k
FROM trade_context tc
JOIN signal_snapshots ss ON tc.symbol = ss.symbol AND tc.date = ss.date
WHERE tc.was_winner = 0
ORDER BY tc.pnl_pct ASC;
```

---

## 13. Evolution Roadmap

### Near Term
- [ ] Fix ASTER `isnan` error (add guard for SMA200 with insufficient data)
- [ ] Add Hyperliquid candle fetching for HYPE/USDC (bypass Binance)
- [ ] Remove FTM/MATIC from token list (delisted/migrated)
- [ ] Add POL (MATIC replacement) if CFGI-compatible

### Medium Term
- [ ] Expand backtest window from 90 to 180 days as data accumulates
- [ ] Build automated incident report generation from `trade_context` losses
- [ ] Add CFGI-based entry gates (e.g., block MARKUP entry when CFGI > 70)
- [ ] Portfolio optimizer using `coin_correlations` (minimum variance selection)

### Long Term
- [ ] Machine learning on `signal_snapshots` — predict phase transitions
- [ ] Adaptive scoring weights based on historical accuracy
- [ ] Multi-timeframe scanner (add 4h/daily signal analysis)
- [ ] Real-time scanner updates (trigger on significant market moves)

---

## 14. Relationship to V12f Scanner (Legacy)

The V12f scanner (`coin_scanner_t2_v12f.py`, now deleted) used the V12f lifecycle engine — a DCA-only grid trading strategy with regime-based entry/exit gates. Key differences:

| Aspect | V12f Scanner | V13 Scanner |
|--------|-------------|-------------|
| Engine | `SpotBacktestEngineV12` (DCA grinder) | `V13BacktestV8` (4-phase lifecycle) |
| Strategy | Buy low, sell high via grid | Phase-ride full market cycles |
| Shorts | No | Yes (symmetric tiers in MARKDOWN) |
| Signals | Regime detection (ADX/ATR) | HH_HL, Fib, StochRSI, HVF, CFGI |
| Phases | None (single mode) | 4 phases: DCA, MARKUP, FLAT, MARKDOWN |
| Profile | Medium | High |
| Cold start | Approximate phase detection | Exact phase detection (same engine as live bot) |
| Analytics | JSON output only | JSON + 5 DB analytics tables |
| CFGI | Per-coin integration | Per-coin integration + historical storage |

The V13 scanner fully supersedes the V12f scanner. All 44 CFGI-compatible tokens are now evaluated through the same engine that powers the live paper trading bot.
