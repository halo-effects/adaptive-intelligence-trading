# V13 DCA Strategy Baseline & Historical Review

> Generated: 2026-02-26 | Source: v13_phase_backtest_v8.py, run_new_coins_profiles.py, v13_lifecycle_engine_v2.py, lifecycle_trader.py, backtest_engine.py

---

## Part 1: Current V13 DCA Baseline

### Architecture Overview

V13 DCA operates as one of four phases in a **phase-riding state machine**: `DCA → MARKUP → FLAT → MARKDOWN → (repeat)`. DCA is the **accumulation phase** — it runs when no directional trend is confirmed. It's spot-only (long side), using a traditional safety-order grid with fixed parameters per risk profile.

The DCA engine is embedded directly in `V13BacktestV8._dca_tick()` and runs on **daily candles** in backtest, but **hourly candles** in live mode (via the lifecycle engine wrapper).

### DCA Parameters by Risk Profile

#### Default (V13Config in v13_phase_backtest_v8.py)

| Parameter | Value |
|-----------|-------|
| Base Order | 8% of available capital (90% of cash) |
| SO Deviation | 2.5% between layers (cumulative: L2=2.5%, L3=5%, L4=7.5%...) |
| SO Volume Multiplier | 1.5× per layer (capped at layer 4 for multiplier) |
| Take Profit | 1.5% above average entry |
| Max Layers | 8 |

#### Risk Profile Variants (from run_new_coins_profiles.py)

| Parameter | Low | Medium | High |
|-----------|-----|--------|------|
| Base Order % | 3% | 4% | 5% |
| SO Deviation | 3.0% | 2.5% | 2.0% |
| SO Volume Multiplier | 2.0× | 2.0× | 2.0× |
| Take Profit | 1.5% | 1.5% | 1.0% |
| Max Layers | 5 | 8 | 12 |
| Max Coins | 2 | 3 | 5 |

#### Live Engine Profile Variants (from v13_lifecycle_engine_v2.py)

The live wrapper uses slightly different profile presets (focused on markup tier sizing, DCA params overlap):

| Parameter | Low | Medium | High |
|-----------|-----|--------|------|
| DCA Base Order | 5% | 6% | 8% |
| DCA Max Layers | 5 | 6 | 8 |
| Markup T1/T2/T3 | 40/15/5% | 50/20/10% | 60/20/10% |

**Note:** There's a discrepancy between backtest profiles (`run_new_coins_profiles.py`) and live profiles (`v13_lifecycle_engine_v2.py`). The backtest uses more aggressive DCA (2.0× multiplier), while the live engine inherits the v8 default 1.5× multiplier unless overridden.

### DCA Execution Logic

**Order sizing:**
```
Layer 0 (base):  available_capital × 0.90 × DCA_BO_PCT
Layer N (safety): base_order × (SO_MULTIPLIER ^ min(N, 4))
Each order capped at: min(order, capital × 0.30)
```

**Entry triggers:**
- Layer 0: Always enters immediately when in DCA phase
- Layer N: Enters when `(avg_entry - current_price) / avg_entry >= SO_DEVIATION × N`
- Minimum 1 day between orders

**Take profit:**
- TP price = `average_entry × (1 + DCA_TP_PCT)`
- Closes entire DCA position (all layers) on TP hit

### DCA + Phase Transition Interactions

This is the critical design area:

| Transition | What Happens to DCA Position |
|------------|------------------------------|
| **DCA → MARKUP** (HH_HL + Fib_support) | DCA position **rides along** — noted as "DCA riding NL" in logs. Position is NOT closed. |
| **MARKUP phase** (while DCA open) | DCA TP still checked each tick — **graceful exit** via `_dca_tick()`. DCA can TP naturally during markup. |
| **MARKUP → FLAT** (top signal) | **HARD EXIT** — `_dca_close(date, 'TOP_EXIT')` forces close regardless of P&L |
| **DCA → MARKDOWN** (LH_LL + ADX + Fib_break) | **HARD EXIT** — `_dca_close(date, 'HARD_EXIT_MARKDOWN')` forces close |
| **Markup failure** (25% DD + ADX>25) | **HARD EXIT** — `_dca_close(date, 'MARKUP_FAIL')` |
| **Ranging exit** (ADX<20 for 21d) | **HARD EXIT** — `_dca_close(date, 'RANGING_EXIT')` |

**Key insight:** DCA positions are only safe during DCA and early MARKUP. Any phase exit triggers a hard close, which can result in losses if the DCA is underwater.

### DCA P&L Contribution

The `pnl_attribution.py` script computes per-source P&L. While I can't run it right now, the attribution framework classifies:
- `DCA_TP` → DCA win (scalp profit)
- `DCA_CLOSE` → DCA exit (may be win or loss depending on timing)

The backtest tracks: `dca_trades`, `dca_wins`, `dca_pnl` as aggregate metrics per run.

From the V13Config defaults ($10k capital, Oct 2024 → Feb 2026):
- DCA runs during ~30-50% of time (varies by coin)
- DCA P&L is typically small relative to markup rides (scalping 1.5% vs riding 30-100%+ markup moves)
- Hard exits during markdown transitions are the main source of DCA losses

---

## Part 2: Historical Dynamic DCA Implementations

### Pre-V13: Adaptive TP and Deviation (backtest_engine.py + lifecycle_trader.py)

The **pre-V13 DCA system** (used in v12 and earlier) had a significantly more sophisticated adaptive parameter system:

#### ATR-Based Scaling

```python
def _adaptive_tp(self, regime, atr_pct):
    atr_ratio = atr_pct / profile.atr_baseline_pct  # baseline = 0.8%
    tp = profile.tp_baseline * atr_ratio
    tp *= REGIME_TP_MULT[regime]
    return clamp(tp, tp_min, tp_max)

def _adaptive_deviation(self, regime, atr_pct, current_tp):
    atr_ratio = atr_pct / profile.atr_baseline_pct
    dev = profile.deviation_baseline * atr_ratio
    dev *= REGIME_DEV_MULT[regime]
    dev = max(dev, current_tp * 1.5)  # deviation always ≥ 1.5× TP
    return clamp(dev, dev_min, dev_max)
```

#### Regime Multipliers

| Regime | TP Mult | Deviation Mult |
|--------|---------|----------------|
| ACCUMULATION | 0.85× | 0.85× |
| CHOPPY | 0.90× | 0.90× |
| RANGING | 0.85× | 0.80× |
| DISTRIBUTION | 0.90× | 0.90× |
| MILD_TREND | 1.05× | 1.10× |
| TRENDING | 1.20× | 1.30× |
| EXTREME | 0.70× | 1.50× |
| BREAKOUT_WARNING | 0.80× | 1.20× |

**Key behaviors:**
- In TRENDING: wider deviation (1.3×) + higher TP (1.2×) = wider grid, bigger profits per cycle
- In EXTREME: much wider deviation (1.5×) + tiny TP (0.7×) = defensive, just trying to survive
- In RANGING: tighter grid (0.8× dev) + lower TP (0.85×) = frequent small scalps
- **BEARISH_SPACING_MULT = 1.4** — additional 40% wider spacing when below SMA50

#### Profile Ranges (Pre-V13)

| Profile | TP Range | Dev Range | Baseline ATR |
|---------|----------|-----------|-------------|
| Low | 1.5–2.5% | 3.0–4.0% | 0.8% |
| Medium | 1.0–2.0% | 2.0–3.0% | 0.8% |
| High | 0.8–1.5% | 1.5–2.5% | 0.8% |

#### What Worked / Didn't

**What worked:**
- ATR-based scaling naturally adapted to volatility (wider grid in volatile markets)
- Regime multipliers prevented aggressive entries during EXTREME conditions
- The `dev ≥ 1.5 × TP` constraint prevented overlapping TP/SO triggers

**What was abandoned in V13:**
- V13 moved to **fixed DCA parameters** with phase-aware exits instead of adaptive grid
- The regime detection was replaced by the phase state machine (DCA/MARKUP/FLAT/MARKDOWN)
- Rationale: phase riding captures macro moves; DCA is just accumulation noise. Making DCA "smarter" added complexity for marginal gains vs. getting the phase transitions right.

### Other Patterns Found

- **No Bollinger Band-based step adjustment** found in the codebase
- **No "breathing grid"** implementation found
- The regime detector (`trading/regime_detector.py`) uses `classify_regime_v2()` with volatility, trend, and volume metrics — this was the input to the adaptive system
- **Blocked regimes:** EXTREME regime blocked new deal entries entirely

---

## Part 3: Dual-Track DCA Design Considerations

### Current: Spot-Only (Long Side)

V13 DCA is exclusively long-side spot accumulation:
- Buys into dips during accumulation phases
- Takes profit on 1.5% bounces
- Hard exits on phase transitions to MARKDOWN
- No short-side DCA exists

The MARKDOWN phase uses **tiered position entry** (T1=60%, T2=20%, T3=10%), not DCA grid logic. Shorts are opened as directional bets, not scalped.

### What Dual-Track Would Require

**Simultaneous long + short DCA grids:**
- Long DCA grid: buys dips, TPs on bounces (current behavior)
- Short DCA grid: sells rallies, TPs on drops (mirror of current)
- Both running simultaneously during neutral/ranging phases

**New components needed:**
1. **Short DCA engine** — mirror of `_dca_tick()` with inverse logic (short on rallies, cover on dips)
2. **Short DCA state** — `short_dca_coins`, `short_dca_avg_entry`, `short_dca_layers`, etc.
3. **Exchange support** — requires margin/perps (spot can't short). Hyperliquid perps would work.
4. **Separate capital pools** — long DCA and short DCA need isolated capital to prevent double-leverage

### Phase Transition Behavior (Dual-Track)

| Transition | Long DCA | Short DCA |
|------------|----------|-----------|
| **Neutral/Ranging** | Active (accumulate) | Active (scalp) |
| **→ MARKUP** (HH_HL + Fib) | Ride position, stop adding | **Close all short DCA** (hard exit) |
| **→ MARKDOWN** (LH_LL + ADX + Fib) | **Close all long DCA** (hard exit) | Ride position, stop adding |
| **→ FLAT** (from top/ranging) | Close or let TP hit | Close or let TP hit |

### Capital Allocation Considerations

1. **Split ratio:** 50/50 is simplest but may not be optimal. Could weight toward the prevailing macro trend.
2. **Total exposure:** With both sides active, max exposure doubles. Need to reduce per-side allocation.
3. **Suggested approach:** 
   - DCA phase: 40% long capital, 40% short capital, 20% reserve
   - On MARKUP signal: redirect short capital to long (80% long, 20% reserve)
   - On MARKDOWN signal: redirect long capital to short (80% short, 20% reserve)
4. **Margin requirements:** Short DCA requires margin. Funding rates eat into short-side profitability in bull markets.

### Key Questions to Resolve

1. **Is short DCA profitable in ranging markets?** Need to backtest short-side DCA scalps. The 1.5% TP on shorts may be eaten by funding rates on perps.

2. **Capital efficiency:** Running two grids simultaneously requires 2× capital or half-sized positions. Does the diversification benefit outweigh the reduced size?

3. **Asymmetry:** Crypto trends bullish long-term. Should short DCA have wider deviation / fewer layers to reflect this asymmetry?

4. **Exchange mechanics:** Spot DCA has no funding cost. Short DCA on perps has ongoing funding costs (positive in bull, negative in bear). This fundamentally changes the math.

5. **Complexity vs. benefit:** V13 abandoned adaptive DCA in favor of simpler fixed params + smart phase transitions. Adding dual-track re-introduces complexity. Is the expected improvement worth it?

6. **Interaction with markup/markdown tiers:** If short DCA is running and a MARKUP signal fires, the short DCA hard-exit loss partially offsets the markup entry gain. Need to model this drag.

7. **Implementation priority:** Should dual-track be a V14 feature, or can it be bolted onto V13's existing architecture?

---

## Summary

| Aspect | Current V13 | Pre-V13 (Adaptive) | Proposed Dual-Track |
|--------|-------------|---------------------|---------------------|
| Side | Long only (spot) | Long only (spot) | Long + Short (perps) |
| Parameters | Fixed per profile | ATR + regime adaptive | TBD |
| TP | 1.0–1.5% fixed | 0.8–2.5% adaptive | TBD per side |
| Deviation | 2.0–3.0% fixed | 1.5–4.0% adaptive | TBD per side |
| Phase awareness | Hard exit on transition | Regime blocks entries | Directional switching |
| Complexity | Low | Medium | High |

---

## Part 4: DCA Parameter Optimization Campaign (Started 2026-02-27)

### Motivation

V12f Wyckoff page results vs V13 backtest over same period (Oct 2020 → Feb 2026, $10K):

| Coin | V12f (Wyckoff page) | V13 (phase backtest) | Gap |
|------|--------------------|-----------------------|-----|
| ETH High | +1,283% | +284% | **4.5× worse** |
| SOL High | +64,627% | +56% | **1,154× worse** |
| BTC High | +590% | +167% | **3.5× worse** |

**Root cause**: V13 gutted the DCA grinding engine. V12f ran adaptive DCA on 1h candles with 110+ ETH trades compounding at 100% win rate. V13 runs fixed DCA on daily candles with ~5-7 trades over 5 years. The lifecycle phase detection is better in V13, but the money-making engine between phases was removed.

**Goal**: Determine optimal DCA parameters for V13's ranging/accumulation phases, then integrate V12f-style adaptive DCA back into V13's phase framework.

### Approach — Isolated DCA Testing

Per Brett's directive: **measure DCA grinding parameters during ranging periods only, keep it isolated.**

1. Run V13 phase engine on daily candles → extract DCA phase windows (date ranges where V13 says "DCA")
2. Run V12f-style DCA engine within those windows on **15m candles**
3. Sweep DCA parameters in a matrix across multiple coins
4. Force-close any open position at window boundaries
5. Report per-coin, per-param results
6. Phase integration (running DCA during markup/markdown) is a LATER step

**NOT testing in this phase:**
- DCA during markup or markdown (later: phase optimization)
- Short-side DCA (later: dual-track integration)
- How DCA positions interact with phase transition exits

### Data Collection

#### 15m Candle Backfill (2026-02-27)

**Script**: `trading/spot/backtest_results/v13/backfill_15m.py`
**Database**: `trading/data/candles.db` (table: `candles`, keyed by `(symbol, timeframe, timestamp)`)
**Period**: January 1, 2023 → present (~Feb 27, 2026)
**Source**: Binance REST API (`/api/v3/klines`)

| Symbol (DB) | Binance Symbol | Timeframe | Candles (approx) | Status |
|-------------|----------------|-----------|-------------------|--------|
| ETH/USDC | ETHUSDC | 15m | ~104,000 | Collected |
| BTC/USDC | BTCUSDC | 15m | ~104,000 | Collecting |
| SOL/USDC | SOLUSDC | 15m | ~104,000 | Queued |
| LINK/USDC | LINKUSDC (→ LINKUSDT fallback) | 15m | ~104,000 | Queued |
| XRP/USDC | XRPUSDC (→ XRPUSDT fallback) | 15m | ~104,000 | Queued |
| ETH/USDC | ETHUSDC | 5m | ~300,000 | Queued (noise comparison) |

**Notes:**
- LINK and XRP may not have USDC pairs on Binance; script falls back to USDT but stores as `/USDC` symbol for consistency
- 5m ETH data collected for comparison to confirm 15m is the right timeframe (5m was noisy in V12f testing)
- Rate limit: 150ms between Binance requests
- Data stored alongside existing 1h candles in same table, distinguished by `timeframe` column

#### Pre-existing Candle Data (already in DB)

| Symbol | Timeframe | Candles | Period |
|--------|-----------|---------|--------|
| ETH/USDC | 1h | 62,434 | 2018-12-31 → 2026-02-17 |
| BTC/USDC | 1h | 62,434 | 2018-12-31 → 2026-02-17 |
| SOL/USDC | 1h | 40,622 | 2021-06-30 → 2026-02-17 |
| ETH/USDT | 1h | 13,332 | 2024-08-20 → 2026-02-27 |
| BTC/USDT | 1h | 13,332 | 2024-08-20 → 2026-02-27 |
| SOL/USDT | 1h | 21,066 | 2020-08-10 → 2026-02-27 |

### Test Engine Architecture

#### File: `trading/spot/backtest_results/v13/dca_phase_test.py`

**Components:**

1. **`DCAParams` dataclass** — Defines a parameter set:
   - `base_order_pct`: % of available capital for base order
   - `tp_baseline`, `tp_min`, `tp_max`: Take profit range
   - `deviation_baseline`, `deviation_min`, `deviation_max`: Safety order deviation range
   - `so_multiplier`: SO size multiplier per layer (capped at layer 4)
   - `max_layers`: Maximum safety order depth
   - `atr_baseline_pct`: ATR baseline for adaptive scaling
   - `adaptive`: bool — whether to use ATR/regime multipliers (V12f) or fixed params (V13)
   - `maker_fee`, `taker_fee`: Exchange fee structure

2. **`DCAEngine` class** — V12f-style execution engine:
   - Scale-out exits: each lot has individual TP based on its entry price
   - Adaptive TP/deviation: ATR ratio × regime multiplier (when `adaptive=True`)
   - Regime multipliers: same as V12f (RANGING=0.85/0.80, TRENDING=1.20/1.30, EXTREME=0.70/1.50)
   - Capital management: 90% available (10% reserve), SO capped at 30% of cash
   - Force-close method for window boundaries

3. **`get_dca_windows()`** — Runs V13 phase engine, extracts DCA phase start/end dates

4. **`compute_regime_and_atr()`** — Computes ATR% and simple regime classification on 15m candles:
   - ATR(14) as percentage of close
   - Regime based on ATR percentile over 7-day rolling window (672 candles at 15m)
   - ACCUMULATION (<30th pctile), RANGING (30-80th), TRENDING (80-95th), EXTREME (>95th)

5. **`build_param_matrix()`** — 8 parameter combos to test

#### DCA Parameter Matrix

| Name | Base Order | TP Baseline | TP Range | Dev Baseline | Dev Range | SO Mult | Layers | Adaptive |
|------|-----------|-------------|----------|-------------|-----------|---------|--------|----------|
| `V13_current` | 5% | 1.5% | fixed | 2.5% | fixed | 2.0× | 8 | No |
| `V12f_adaptive_med` | 4% | 1.5% | 1.0–2.0% | 2.5% | 2.0–3.0% | 2.0× | 8 | Yes |
| `V12f_aggressive` | 6% | 1.2% | 0.8–2.0% | 2.0% | 1.5–3.0% | 2.0× | 10 | Yes |
| `tight_grid` | 5% | 1.0% | 0.6–1.5% | 1.5% | 1.2–2.5% | 1.5× | 6 | Yes |
| `wide_grid` | 5% | 2.0% | 1.2–2.5% | 3.0% | 2.0–4.0% | 2.0× | 8 | Yes |
| `scalper` | 4% | 0.8% | 0.5–1.2% | 1.2% | 1.0–2.0% | 1.5× | 5 | Yes |
| `conservative` | 3% | 2.0% | 1.5–2.5% | 3.5% | 2.5–4.0% | 2.0× | 6 | Yes |
| `high_freq` | 3% | 1.0% | 0.6–1.5% | 2.0% | 1.5–3.0% | 1.5× | 12 | Yes |

**Logic**: Range from V13's current fixed params (baseline) through V12f adaptive (known good) to aggressive/tight variants. The scalper and tight_grid test whether more frequent cycling at lower TP outperforms wider grids.

#### Execution Flow

```
For each coin:
  1. V13 phase engine → DCA windows [(start, end), ...]
  2. For each DCA param set:
     a. Initialize DCAEngine with $2,500 capital (matches paper bot per-coin allocation)
     b. For each DCA window:
        - Load 15m candles for [start, end]
        - Compute ATR + regime per candle
        - Tick DCA engine on every 15m candle
        - Force-close at window end
     c. Record: ROI, total deals, win rate, PnL
  3. Output: per-coin × per-param matrix
```

#### Naming Convention

| File | Purpose | Version |
|------|---------|---------|
| `backfill_15m.py` | Data collection: 15m + 5m candles from Binance | v1 |
| `dca_phase_test.py` | DCA parameter matrix test, isolated to V13 DCA phases | v1 |
| `v13_phase_backtest_v8.py` | V13 lifecycle phase engine (43KB, the correct one) | v8 |
| `backtest_engine.py` (in `trading/spot/`) | V12f spot DCA engine with adaptive params | v12f |
| `lifecycle_engine.py` (in `trading/spot/`) | V12f full lifecycle engine (DCA + phases) | v12f |

**Convention going forward:**
- `dca_phase_test_v{N}.py` — DCA parameter testing (increment N for major changes)
- `v13_dca_engine_v{N}.py` — Integrated V13+DCA engine (when we build it)
- Results stored in `trading/spot/backtest_results/v13/dca_results/` directory

### Results — Completed Tests (2026-02-27)

All tests below use the **corrected test engine** (CFGI `load_cfgi()` fix applied 2026-02-27). Previous results using `COIN/USDC` format had missing CFGI data, silently disabling tier adds. All results below are post-fix.

#### Test 1: DCA Dual-Track (Long + Short) — `dca_phase_test.py`
- **Result: Long-only baseline wins.** Every dual-track config underperformed.
- Shorts lose money during DCA because 79% of DCA windows exit to MARKUP (structural long bias).
- **Decision: DCA phases are long-only grinding zones.**

#### Test 2: DCA Long-Only Parameter Sweep — `dca_long_sweep.py`
- Best found: TP=0.8%, DEV=1.2%, SO=2.5x, 5 layers — only +1.4% avg improvement.
- Pure DCA grinding within windows is modest: SOL profitable, ETH moderate, BTC consistently negative.
- **BTC is a DCA dead zone** — negative on every config tested (3/6 windows have 5-15% price drops from slow FLAT routing).

#### Test 3: Timeframe Comparison (15m vs 1h) — `dca_tf_compare.py`
- **1h candles dominate 15m across ALL 5 coins.** Validates V12f's original design.
- SOL: 1h is 3.1× better. LINK: 3.1×. ETH: 1.6×. XRP: 1.4×.
- **Fixed params beat adaptive for 4/5 coins** (XRP exception: adaptive slightly better).
- **Wider TP/deviation works better**: TP 1.5-2.0%, DEV 2.5-3.0%.
- Detailed results: `projects/ait-product/dca-timeframe-comparison.md`

#### Test 4: Full Lifecycle Integration — `v13_enhanced_dca_test.py`
Three approaches tested:
1. **Force-close at boundaries**: DCA hurts portfolio -3.6%. Force-closing kills profitable positions.
2. **Shared capital pool**: +12.6% lift BUT capital contamination — grinder steals from markup engine.
3. **Isolated capital (10% dedicated)**: +1.3% additive (+$166 on $10K). Clean, zero interference.

- **Decision: DCA grinder must be capital-isolated (10% dedicated pool).**
- **Graceful exits essential** — positions must be allowed to TP naturally into markup.

#### Test 5: Paper Bot Comparison — `_paperbot_compare.py`
- Oct 1, 2024 → Feb 27, 2026 (matches paper bot actual start)
- Baseline: +184.4% ($28,438). With grinder: +185.2% ($28,517).
- **DCA grinder adds only ~$79 on $10K portfolio over 5 months.**

#### Per-Coin Optimal DCA Configs (1h candles, MARKUP-exit windows)

| Coin | TP | DEV | SO Mult | Layers | Adaptive | ROI |
|------|-----|------|---------|--------|----------|-----|
| SOL | 0.8% | 1.2% | 2.5× | 10 | No | +294.9% |
| LINK | 1.5% | 2.5% | 2.0× | 8 | No | +10.1% |
| ETH | 2.0% | 3.0% | 2.0× | 8 | No | +6.7% |
| XRP | 1.5% | 2.5% | 2.0× | 8 | Yes | +4.2% |
| BTC | — | — | — | — | — | Skip (negative) |

### Resolved Questions

1. **15m vs 1h?** → 1h wins decisively. 15m has too much noise, worse fill quality.
2. **Adaptive vs fixed?** → Fixed wins for 4/5 coins. Adaptive adds complexity for no gain.
3. **Optimal TP range?** → 1.5-2.0% for most coins. SOL prefers tighter (0.8%) due to higher volatility.
4. **Force-close cost?** → Devastating (-3.6% portfolio). Graceful exits are non-negotiable.
5. **Scalper viable?** → No. Tight TP doesn't compensate for increased trade count.
6. **Per-coin params?** → Yes, strongly coin-dependent. BTC should skip DCA entirely.

### Critical Bug Fix (2026-02-27)

**`load_cfgi()` in `v13_signals.py`** was not extracting the base coin before DB query. When called with `XRP/USDC`, the query `LIKE 'XRP/USDC%'` matched nothing (cfgi_daily stores `XRP` or `XRP/USDT`). This silently disabled all CFGI-gated features (T2/T3 tier adds) for standalone backtests.

**Fix:** Extract base coin: `base = coin.split('/')[0]` (same as `load_daily()` already did).

**Impact:** All previous standalone backtest results using `COIN/USDC` format were wrong — missing tier adds. Portfolio with fix: $28,438 (was $27,005). The paper bot (which used stripped `COIN` format) was accidentally correct.

### Remaining Open Questions

1. **Is +$79 DCA lift worth integration complexity?** At current levels, probably not. But could improve if:
   - Phase classification speeds up (FLAT routing fixes)
   - More coins added with favorable DCA profiles (SOL-like volatility)
   - Capital allocation increased beyond 10%
2. **Wyckoff sequence detection** — could dramatically improve FLAT→DCA routing, increasing DCA window quality
3. **Per-coin DCA enable/disable** — should BTC skip DCA entirely? Currently wastes capital.
