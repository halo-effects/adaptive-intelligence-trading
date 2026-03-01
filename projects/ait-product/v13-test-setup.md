# V13 Test Setup — Complete Reference

> Last validated: 2026-02-26. Backtest engine output matches live paper bot within ±1 day phase transitions and 10-15% PnL (daily vs 1h candle granularity).

## Architecture Overview

```
candles.db (SQLite)          <- 1h candle data (Binance)
    |
build_daily_candles.py       <- Aggregates 1h -> daily OHLCV
    |
v13_signals.py               <- V13SignalPack: computes all indicators from daily candles
    |                            (SMA50/200, ADX, Fib, StochRSI 2W/1W, HH_HL, LH_LL, CFGI, HVF)
    |
v13_phase_backtest_v8.py     <- V13BacktestV8 engine: phase state machine + DCA + tiered entry/exit
    |
run_new_coins_profiles.py    <- Runner: iterates coins × profiles, outputs results
```

## File Locations

All paths relative to workspace root (`C:\Users\Never\.openclaw\workspace\`):

| Component | Path |
|-----------|------|
| **Candle DB** | `trading/spot/data/candles.db` |
| **Signal Pack** | `trading/spot/backtest_results/v13/v13_signals.py` |
| **Engine** | `trading/spot/backtest_results/v13/v13_phase_backtest_v8.py` (43KB, class `V13BacktestV8`) |
| **Live Wrapper** | `trading/spot/v13_lifecycle_engine_v2.py` |
| **Paper Runner** | `trading/spot/run_v13_paper.py` |
| **Profile Runner** | `trading/spot/backtest_results/v13/run_new_coins_profiles.py` |
| **Results JSON** | `trading/spot/backtest_results/v13/wyckoff_v13_results.json` |
| **Daily Candle Builder** | `trading/spot/backtest_results/v13/build_daily_candles.py` |
| **Deep Backfill Script** | `trading/spot/backtest_results/v13/backfill_deep.py` |
| **SOL Warmup Backfill** | `trading/spot/backtest_results/v13/backfill_warmup.py` |
| **Indicator Recomputer** | `trading/spot/backtest_results/v13/recompute_indicators.py` |

⚠️ **CRITICAL**: There are TWO v8 files with the same class name:
- `v13_phase_backtest_v8.py` (43KB) ← **CORRECT** (phase engine)
- `v13_backtest_v8.py` (38KB) ← **WRONG** (produces -15% ROI)
Always verify file size. The correct engine is the larger one.

## Database Schema

### candles.db — Tables

**`candles_1h`**: Raw 1-hour OHLCV candles from Binance
- Columns: `symbol`, `timestamp`, `open`, `high`, `low`, `close`, `volume`
- Symbols: `BTC/USDC`, `ETH/USDC`, `SOL/USDC` (also USDT variants for some)
- Data range: Jan 2019+ for BTC/ETH, Aug 2020+ for SOL

**`daily_candles`**: Aggregated daily OHLCV (built from 1h)
- Same columns as `candles_1h`
- Built by `build_daily_candles.py`

**`daily_indicators`**: Pre-computed technical indicators
- Columns: `symbol`, `date`, `sma_50`, `sma_200`, `adx`, `atr`, `atr_pct`, `rsi_14`, `stoch_rsi_k`, `stoch_rsi_d`, `price_vs_sma200`, `sma50_slope`, `hh_hl_streak`, `ll_lh_streak`, `bullish_engulfing`, `bearish_engulfing`, `obv`, `vwap`
- Built by `recompute_indicators.py` or daily collector cron

**`cfgi_daily`**: Crypto Fear & Greed Index
- Columns: `date`, `value`
- Range: July 2022+ (NaN before that, engine handles gracefully)

## Data Requirements

### Warmup Periods
| Indicator | Minimum History Needed |
|-----------|----------------------|
| SMA200 | 200 daily candles |
| ADX(14) | ~28 daily candles |
| 2W StochRSI | **~784 daily candles** (14-period RSI on 14-day windows, then 14-period stochastic on that) |
| 1W StochRSI | ~392 daily candles |
| HH_HL / LH_LL | 60 daily candles (lookback default) |

**For Oct 2020 backtest start**: Need data from at least **Jan 2019** for BTC/ETH to ensure valid 2W StochRSI.

**SOL exception**: SOL trading started Aug 2020. Only ~450 days of history by Nov 2021 top — insufficient for 2W StochRSI. This is a known limitation (SOL bootstrap problem).

### Data Backfill Procedures

**1. Deep 1h backfill (BTC/ETH from Jan 2019):**
```bash
python -u trading/spot/backtest_results/v13/backfill_deep.py
```

**2. SOL warmup backfill (Aug 2020 → Jun 2021, from USDT merged into USDC):**
```bash
python -u trading/spot/backtest_results/v13/backfill_warmup.py
```

**3. Rebuild daily candles from 1h:**
```bash
python -u trading/spot/backtest_results/v13/build_daily_candles.py
```

**4. Recompute indicators on daily candles:**
```bash
python -u trading/spot/backtest_results/v13/recompute_indicators.py
```

⚠️ The daily collector cron (`trading/spot/daily_collector.py`) does DELETE+rebuild of daily candles from 1h. It will **wipe backfilled USDT data**. Use USDC pairs only for backtesting.

## Signal Pack (v13_signals.py)

`V13SignalPack(coin)` loads all data for a coin and provides:

| Signal Group | Class | Key Methods |
|-------------|-------|-------------|
| Structure | `StructureSignals` | `hh_hl_streak(date, lookback)`, `lh_ll_streak(date, lookback)` |
| Fibonacci | `FibSignals` | `above_support(date)`, `below_break(date)` |
| Indicators | `IndicatorSignals` | `adx(date)`, `sma200_distance(date)`, `sma50_slope(date)` |
| StochRSI | `StochRSISignals` | `two_week_k(date)`, `one_week_k(date)` |
| CFGI | `CFGISignals` | `value(date)` |
| Price | `PriceSignals` | `price(date)`, `daily_df` |

Signal pack is **read-only** and can be shared across profile runs for the same coin.

## Engine Configuration (V13Config)

### Risk Profile Settings
| Parameter | Low | Medium | High |
|-----------|-----|--------|------|
| `DCA_BO_PCT` | 3% | 4% | 5% |
| `DCA_SO_DEVIATION` | 3.0% | 2.5% | 2.0% |
| `DCA_SO_MULTIPLIER` | 2.0× | 2.0× | 2.0× |
| `DCA_TP_PCT` | 1.5% | 1.5% | 1.0% |
| `DCA_MAX_LAYERS` | 5 | 8 | 12 |

### Phase/Tier Settings (same across all profiles)
| Parameter | Value | Purpose |
|-----------|-------|---------|
| `TIER1_PCT` | 60% | T1 markup buy (front-loaded) |
| `TIER2_PCT` | 20% | T2 markup buy |
| `TIER3_PCT` | 10% | T3 markup buy |
| `SHORT_TIER1_PCT` | 60% | T1 short (symmetric) |
| `SHORT_TIER2_PCT` | 20% | T2 short |
| `SHORT_TIER3_PCT` | 10% | T3 short |
| `OB_THRESHOLD_2W` | 93 | 2W StochRSI overbought (primary top signal) |
| `OB_FALLBACK_1W` | 85 | 1W StochRSI fallback (if 2W never hits 93) |
| `FAILSAFE_1W` | 50 | 1W K<50 failsafe exit |
| `ADX_THRESHOLD` | 20 | Minimum ADX for MARKDOWN entry |
| `HH_HL_LOOKBACK` | 60 | Days to look back for structure streaks |
| `SMA200_OVEREXTENSION` | 20 | Threshold in **percentage** (not decimal!) |

### Phase State Machine
```
START → DCA → MARKUP → FLAT → MARKDOWN → FLAT → DCA → (repeat)
                                    ↓
                              DCA (if no markdown signal after 42d)
```

### Entry/Exit Gates (Current Engine State — Run 4)
| Transition | Gates Required |
|-----------|---------------|
| DCA → MARKUP | HH_HL ≥ 2 + Fib_support + CFGI (advisory) |
| DCA → MARKDOWN | **LH_LL ≥ 2** + ADX > 20 + Fib_break |
| FLAT → MARKDOWN | **LH_LL ≥ 2** + ADX > 20 + Fib_break |
| MARKUP → FLAT | 2W OB93 (primary) / 1W OB85 (fallback) / 1W K<50 (failsafe) |
| MARKDOWN → FLAT | ADX < 20 for 21+ consecutive days |
| FLAT → DCA | ADX < 20 for 14+ days (ranging confirmed) |

### Safety Nets
| Detector | Trigger | Action |
|----------|---------|--------|
| MARKUP_FAIL | DD > 25% + ADX > 25 | `_sell_all()` — liquidates entire position |
| MARKDOWN_FAIL | Rise > 25% + ADX > 25 | Closes short position |

## Running Backtests

### Single Coin, Single Profile
```python
import sys
sys.path.insert(0, 'trading/spot/backtest_results/v13')
from v13_phase_backtest_v8 import V13BacktestV8, V13Config, print_results
from v13_signals import V13SignalPack

cfg = V13Config()
cfg.CAPITAL = 10000
cfg.START_DATE = '2020-10-01'
cfg.END_DATE = '2026-02-26'
# Set profile params (DCA_BO_PCT, DCA_MAX_LAYERS, etc.)

pack = V13SignalPack('ETH')
bt = V13BacktestV8(pack, cfg)
result = bt.run()
print_results(result)
```

### Full 9-Combo Run (3 coins × 3 profiles)
```bash
python -u trading/spot/backtest_results/v13/run_new_coins_profiles.py
```
Edit the script to change coins list and date range.

### Paper Bot Comparison (Oct 2024 → present)
```bash
python -u trading/spot/backtest_results/v13/compare_paper.py
```

## Validation Checklist

Before trusting backtest results, verify:

1. **Data depth**: Check daily candle count per symbol
   ```sql
   SELECT symbol, COUNT(*), MIN(date), MAX(date) FROM daily_candles GROUP BY symbol;
   ```
   Need: BTC/ETH 2600+, SOL 2000+ rows

2. **Indicator completeness**: Check for NULL indicators near backtest start
   ```sql
   SELECT * FROM daily_indicators WHERE symbol='BTC/USDC' AND date >= '2020-10-01' LIMIT 5;
   ```

3. **2W StochRSI validity**: Verify known reference points
   - BTC Oct 2020: K ≈ 71.6
   - BTC Jan 2021: K ≈ 97.0
   - BTC Nov 2021: K ≈ 67 (structural — double top compressed it)

4. **Engine file verification**: Correct file is 43KB
   ```bash
   (Get-Item trading/spot/backtest_results/v13/v13_phase_backtest_v8.py).Length
   ```

5. **Paper bot comparison**: Run `compare_paper.py` — phase transitions should align ±1 day

## Known Limitations

- **SOL bootstrap**: Insufficient history for 2W StochRSI before ~mid-2022. Top detection unreliable for SOL's first cycle.
- **CFGI gaps**: Returns NaN before July 2022. Engine handles gracefully (CFGI is advisory, not a gate).
- **Daily vs 1h granularity**: Backtest uses daily closes; live bot trades on 1h candles. Expect 10-15% PnL variance.
- **HVF is dead code**: Logged only, not used for routing. Doesn't discriminate good vs bad entries on SOL/ETH.
- **SOL MARKUP_FAIL in 2022 bear**: 3 failed longs (-$5.2K total) have valid bullish structure at entry. No signal tested cleanly filters them without killing good entries on other coins.

## Diagnostic Tools

| Script | Purpose |
|--------|---------|
| `check_signals.py` | Verify signal values at specific dates |
| `verify_signals.py` | Cross-check signal pack vs raw DB values |
| `audit_signals.py` | Full pipeline audit (HH_HL streaks, Fib levels, data quality) |
| `debug_markup_entry.py` | Day-by-day trace of MARKUP entry logic |
| `check_shorts.py` | Analyze MARKDOWN entry decisions |
| `pnl_attribution.py` | Break down ROI by Markup/DCA/Short for all 9 combos |
| `test_signal_candidates.py` | Evaluate any signal as a gate (recall, precision, latency) |
| `build_weekly_signals.py` | Aggregate daily → weekly candles + weekly structure signals |
| `test_markup_weekly_gate.py` | Test weekly HH_HL variants as MARKUP gate |
| `test_bias_gate.py` | Test SMA200/Golden Cross as bias triggers |
| `test_bias_system.py` | Test engine top signals as bias triggers |
| `test_bias_hybrid.py` | Test asymmetric bias system with multiple triggers |
| `compare_paper.py` | Compare backtest vs live paper bot (Oct 2024+) |

## Validated Results (Run 4 — Current Engine)

Oct 2020 → Feb 2026, $10,000 capital:

| Coin | Low | Med | High | B&H |
|------|-----|-----|------|-----|
| ETH | +269% | +280% | +284% | +465% |
| BTC | +186% | +211% | +167% | +538% |
| SOL | +106% | +69% | +54% | +155% |

Paper bot validation (Oct 2024 → Feb 2026, $2,500/coin, High):
| Coin | Paper Bot | Backtest |
|------|-----------|----------|
| ETH | +75.8% | +65.3% |
| SOL | +193% | +176% |

## Test History

| Run | Change | Key Result |
|-----|--------|------------|
| Run 1 | Initial (broken SMA200 gate) | ETH +5%, BTC +20% (MARKUP never fires) |
| Run 2 | SMA200 threshold fix (0.20→20) | ETH +130%, BTC +121%, SOL +454% |
| Run 3 | SMA200 gate removed from MARKUP | ETH +161%, BTC +211%, SOL +142% |
| **Run 4** | **LH_LL ≥ 2 gate on MARKDOWN** | **ETH +284%, BTC +211%, SOL +54%** |

## Cron Jobs (Automated Pipeline)

| Job | Cron ID | Schedule | Purpose |
|-----|---------|----------|---------|
| V13 Daily Collector | a520cd05 | 5:30 AM PST | Fetch candles → daily → CFGI → signals → correlations |
| V13 Daily Scanner | ef85844d | 6:00 AM PST | Run all 44 CFGI tokens through engine, output scores |
| Dashboard Sync | Windows Task `AIT_DashboardSync` | Every 10 min | Push status.json/trades.csv to GitHub Pages |
