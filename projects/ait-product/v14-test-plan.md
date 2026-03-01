# V14 DCA Engine — Test Plan & Results

## Engine Architecture
- **Brain**: ROUTER v2 signal stack (top/bottom detection, phase routing)
- **Execution**: DCA grid cycling (buy layers → TP → restart grid)
- **Direction**: Full capital in one direction at a time (LONG_DCA or SHORT_DCA)
- **Transitions**: Early signals unwind, conviction-level signals flip direction

## Locked Decisions

### OB85 Fallback: REMOVED
- **Decision date**: 2026-02-28
- **Rationale**: OB85 is the only top trigger for coins whose 2W StochRSI never reaches 93 (e.g., SOL). It misfires — fires during bull runs, causing premature shorts that get crushed.
- **Data**: SOL jumped from +3.2% → +88.7% without OB85. ETH dropped +129.6% → +50.9% (Dec 19 OB85 was correct but K<50 failsafe catches it 3 weeks later). Portfolio net +$171.
- **Alternative**: K<50 failsafe is sufficient for top detection when OB93 doesn't arm.
- **Config**: `OB_FALLBACK_1W = 99` (effectively disabled)

### Conviction: KEEP AT 3/4
- **Rationale**: Disabling conviction loses $2,327 vs baseline. ETH drops to +18% without it. The problem was OB85, not conviction.
- **SOL conviction at $106 was the main loser** (-26% further drawdown), but with OB85 removed, SOL stays in LONG_DCA through the pump and only flips short on K<50 Oct 9 — much better timing.

### Grid Mode: CYCLING (Fixed TP)
- **Decision date**: 2026-02-28
- **Rationale**: Cycling beats accumulate on both coin sets. Rapid compounding > holding for big moves.
- **Trailing TP tested and rejected**: -3.1% worse on current coins, -34% worse on best coins. Gives back gains on reversals.
- **Geometric spacing tested and rejected**: -8.7% worse. Wider gaps mean fewer layers fill.
- **Optimal TP**: 1.5% for best coins (HBAR/ADA/LINK/ATOM), 2.5% for current coins (ETH/SOL/LINK/XRP)

## Coin Selection

### Evaluation: 14 Coins Tested (Oct 2024 start, $2,500/coin, no OB85)

| Rank | Coin | ROI | Max DD | Notes |
|------|------|-----|--------|-------|
| 1 | **HBAR/USDT** | +715.5% | -27.2% | Monster. 1 phase change. Full pump+dump captured. |
| 2 | **ADA/USDT** | +159.6% | -41.3% | Clean OB93 timeout top. |
| 3 | **LINK/USDC** | +157.8% | -34.2% | Current portfolio. Consistent. |
| 4 | **ATOM/USDT** | +118.4% | -20.8% | Best risk-adjusted (lowest DD). |
| 5 | NEAR/USDT | +91.5% | -28.9% | Good but 4 phase changes. |
| 6 | SOL/USDC | +88.7% | -42.8% | Current. OB85 removal fixed it. |
| 7 | LTC/USDT | +71.4% | -39.6% | Solid but unexciting. |
| 8 | ETH/USDC | +50.9% | -31.6% | Current. Underperforms without OB85. |
| 9 | XRP/USDC | +38.6% | -73.2% | Current. Terrible DD. OB93 timeout misfire. |
| 10 | BNB/USDT | +27.2% | -69.4% | Bad risk-reward. |
| 11 | AAVE/USDT | +24.2% | -118.8% | Disqualified. Extreme DD. |
| 12 | UNI/USDT | +21.7% | -63.2% | Poor. |
| 13 | AVAX/USDT | -13.1% | -64.3% | Negative ROI. |
| 14 | DOT/USDT | -22.1% | -72.6% | Worst performer. |

### Selected Portfolio: HBAR, ADA, LINK, ATOM
- **Best 4-coin combo**: +287.8% accumulate, +297.2% cycling
- **vs Current portfolio (ETH/SOL/LINK/XRP)**: +84.0% accumulate, +101.3% cycling
- **3× improvement** from coin selection alone

### HBAR Scrutiny
- +715% is from one massive trade cycle: long Oct→Dec (caught pump), short Dec→end (rode crash)
- Only 1 phase change = clean signal but limited sample size
- Risk: overfitting to a single pump-dump cycle
- Mitigation: HBAR has 2,345 daily candles of history — can test on longer periods

## Grid Improvement Tests

### Trailing TP (REJECTED)
| Config | Current Coins ROI | Best Coins ROI |
|--------|-------------------|----------------|
| Fixed TP=2.5% | +101.3% | +258.2% |
| Trail TP=2.5% CB=0.7% | +98.2% | +258.3% |
| Trail TP=2.5% CB=0.5% | +95.8% | +263.3% |
Trailing gives back gains on reversals. Fixed TP compounds faster.

### Geometric Grid Spacing (REJECTED)
| Config | Current Coins ROI | Best Coins ROI |
|--------|-------------------|----------------|
| Arithmetic (baseline) | +101.3% | +297.2% |
| Geo ratio=1.2 | +92.6% | +246.5% |
| Geo ratio=1.3 | +87.7% | +249.1% |
Wider gaps = fewer layers fill = less averaging down. Hurts DCA.

## Risk Profiles (LOCKED 2026-02-28)

| | Low | Medium | High |
|---|---|---|---|
| **Leverage** | 1x | 1.5x | 1.5x |
| **BO** | 40% | 40% | 40% |
| **Deviation** | 2.0% | 2.0% | 1.5% |
| **Layers** | 10 | 10 | 12 |
| **TP** | 1.5% | 1.5% | 1.5% |
| **Mult** | 1.5x | 1.5x | 1.5x |
| **ROI** | +347% | +521% | +556% |
| **Equity ($10K)** | $44,743 | $62,115 | $65,546 |
| **Worst DD** | -53% (ADA) | -79% (ADA) | -80% (ADA) |

- High uses tighter deviation (1.5%) + more layers (12) = deeper grid averaging
- BO and Mult insensitive above 40% / 1.5x (capital fully utilized)
- Leverage capped at 1.5x max (2x causes ADA liquidation)

## Parameter Sweep Results

### BO% (base order)
- 15%: +138%, 20%: +204%, 25%: +259%, **30%: +297%**, **40%: +320%**, 50%: +320%
- 40-50% identical (capital ceiling). **40% optimal** (less initial risk, same result).

### Deviation (SO gap)
- 1.5%: +299%, **2.0%: +321%**, 2.5%: +297%, 3.0%: +266%, 4.0%: +226%
- **2.0% optimal** for standard grid. 1.5% better with 1.5x leverage (High profile).

### Volume Multiplier
- 1.0x: +275%, 1.2-2.5x: **all +297%** (insensitive above 1.2x)
- Insensitive parameter. Keep at 1.5x.

### Max Layers
- 4: +216%, 6: +292%, **8: +297%**, 10: +291%, 12: +291%
- 8-10 optimal at 1x. 12 adds edge with tighter deviation at 1.5x leverage.

### TP (take profit)
- 1.0%: +279%, 1.2%: +278%, **1.5%: +297%**, **1.8%: +305%**, 2.0%: +296%, 2.5%: +258%
- 1.5-1.8% sweet spot. 1.5% selected for consistency.

### Capital Allocation
- Equal (25% each): +297%
- 40/20/20/20 (HBAR heavy): +312%
- 50/20/15/15 (HBAR heavier): +318%
- **Equal weight selected** (Brett: "keep it balanced so it's not misleading")

### Leverage
- 1.0x: +347%, 1.5x: +521%, 2.0x: +695% (ADA liquidation risk)
- **1.5x max** (Brett directive). High profile uses 1.5x + aggressive grid.

## Remaining Optimization Targets
1. **BO%** — base order size (currently 30%)
2. **SO Deviation** — gap between layers (currently 2.5%)
3. **Volume multiplier** — layer scaling (currently 1.5x)
4. **Max layers** — grid depth (currently 8)
5. **Capital allocation** — equal vs performance-weighted
6. **Per-coin TP** — different TP per coin based on volatility
7. **Divergence timeout** — currently 35d, only affects XRP in best coins

## Parameter Sweep Results
*(To be filled after sweep completes)*

## Paper Bot Configuration

### Coins: HBAR/USDT, ATOM/USDT, LINK/USDC, NEAR/USDT
*(Updated from HBAR/ADA/LINK/ATOM after full universe sweep — NEAR replaced ADA as #4)*
Equal weight: $2,500/coin on $10K capital.

### Runner Command
```
python -u -m trading.spot.run_v14_paper --capital 10000 --profile medium --exchange hyperliquid
```
Default coins: HBAR/USDT, ATOM/USDT, LINK/USDC, NEAR/USDT

### Config (Medium Profile — Default)
```python
# DCA Grid
DCA_ACCUMULATE = False      # Cycling mode (fixed TP)
DCA_TP_PCT = 0.015          # 1.5% take profit
DCA_BO_PCT = 0.40           # 40% base order
DCA_SO_DEVIATION = 0.02     # 2.0% between layers
DCA_SO_MULTIPLIER = 1.5     # 1.5x volume scaling
DCA_MAX_LAYERS = 10         # 10 safety orders
DCA_CAPITAL_PCT = 0.90      # 90% capital utilization

# Signal Stack
OB_FALLBACK_1W = 99         # OB85 disabled
CONVICTION_MIN_SCORE = 3    # 3/4 bottom conviction
TOP_DIVERGENCE_TIMEOUT = 35 # Days to wait for divergence after OB93

# Leverage
LEVERAGE = 1.5              # Medium profile
```

### Profile Overrides
```python
# Low: LEVERAGE=1.0 (everything else same)
# High: LEVERAGE=1.5, DCA_SO_DEVIATION=0.015, DCA_MAX_LAYERS=12
```

## File Architecture

### Engine (Backtest)
- **`trading/spot/backtest_results/v13/v14_dca_engine.py`** — V14 DCA-only backtest engine
  - Class: `V14DCAEngine` — runs on daily candles from `V13SignalPack`
  - Three phases: `LONG_DCA`, `SHORT_DCA`, `ROUTER`
  - ROUTER v2 signal stack: OB93 arming → 2D divergence confirmation (top), 3D death cross + 2W K≥5 + conviction ≥3/4 (bottom)
  - DCA grid: cycling mode with fixed TP, configurable BO/Dev/Mult/Layers
  - Standalone runner: `run_v14()` for direct backtest execution

### Lifecycle Wrapper (Live)
- **`trading/spot/v14_lifecycle_engine.py`** — Live wrapper around V14DCAEngine
  - Class: `V14LifecycleEngine` — wraps engine for real-time candle feeds
  - `backfill_direct(start, end)` — calls engine.run() directly (100% backtest match guaranteed)
  - `tick(candle_1h, cash)` — processes 1h candles; daily boundary triggers full signal eval, hourly ticks run DCA grid for TP responsiveness
  - Signal pack refresh on daily boundary (including detector + divergence dates re-init)
  - `snapshot_state()` / `restore_state()` — persists all 25+ engine state fields
  - `get_status()` — dashboard-compatible output with leveraged equity/PnL
  - Risk profiles defined in `V14_PROFILES` dict (Low/Medium/High)
  - Leverage implemented as PnL multiplier: `pnl = (engine_equity - capital) * leverage`
  - Restores open positions after backfill OPEN_END cleanup

### Paper Bot Runner
- **`trading/spot/run_v14_paper.py`** — Paper trading runner for Hyperliquid
  - Class: `V14PaperBot` — manages engines, state, live loop
  - Coins: HBAR/USDT, ATOM/USDT, LINK/USDC, NEAR/USDT (equal weight $2,500 each)
  - Price feed: Hyperliquid perps via CCXT (`HBAR/USDC:USDC`, `ATOM/USDC:USDC`, `LINK/USDC:USDC`, `NEAR/USDC:USDC`) — no spot market exists for HBAR/ATOM/NEAR on Hyperliquid
  - CFGI polling: hourly per-coin + market sentiment
  - State persistence: `trading/spot/paper/v14/state.json`, `status.json`, `trades.csv`
  - Telegram notifications on trade completions and phase transitions
  - Graceful shutdown via signal handlers
  - Windows Scheduled Task: `V14PaperBot` (AtStartup trigger, auto-restart 3×)

### Entry Points
```bash
# Backfill only (verify backtest match)
python -u -m trading.spot.run_v14_paper --capital 10000 --profile medium --backfill-only

# Live (skip backfill, use existing state)
python -u -m trading.spot.run_v14_paper --capital 10000 --profile medium --exchange hyperliquid --skip-backfill

# Full (backfill then live)
python -u -m trading.spot.run_v14_paper --capital 10000 --profile medium --exchange hyperliquid
```

### Backtest Verification (2026-02-28)
- Backfill: **$65,247 (+552%)** on Medium profile — matches standalone backtest ✅
- Per-coin (1x engine): HBAR $13,428 (+437%), ATOM $12,658 (+406%), LINK $10,608 (+324%), NEAR $9,970 (+299%)
- 345 deals, 97.4% win rate
- Live hourly execution produces slightly higher equity ($68,806 / +588%) due to intraday TP fills

### Analysis Scripts (in `trading/spot/backtest_results/v13/`)
- `_conviction_analysis.py` — Conviction trigger outcome analysis
- `_conviction_fixes.py` — 8-way config sweep for conviction/OB85/timeout
- `_ob85_refinements.py` — OB85 threshold sweep (87-92)
- `_coin_eval.py` — 14-coin universe evaluation
- `_extended_coins.py` — 30 Tier B/C coin evaluation (all failed)
- `_cycling_vs_accumulate.py` — Cycling vs accumulate mode comparison
- `_grid_v2.py` — Grid improvement tests (trailing TP, geometric spacing)
- `_v14_param_sweep.py` — Full BO/Dev/Mult/Layers/TP sweep
- `_leverage_test.py` — Leverage 1x-3x analysis
- `_risk_profiles.py` — Risk profile definition and validation
- `_full_universe.py` — 15-coin × 3-profile universe sweep

### Coin Scanner
- **`trading/spot/backtest_results/v13/_v14_scanner.py`** — Scores coins on V14-specific metrics
  - 15 coins evaluated, weighted scoring: trade cycling (25%), short PnL (20%), max DD (20%), ROI (15%), phase count (10%), win rate (10%)
  - Top scores: ATOM 97/A+, HBAR 94/A+, LINK 82/A, NEAR 74/B+
  - Output: `docs/data/v14/scanner.json` — feeds dashboard Opportunity section

### Dashboard
- **`docs/dashboardV14.html`** (~1,050 lines) — Standalone V14 dashboard
  - Data: `data/v14/status.json`, `data/v14/trades.csv`, `data/v14/scanner.json`
  - Phases: LONG_DCA / SHORT_DCA / ROUTER (3 phases, replacing V13's 6 Wyckoff phases)
  - Coins: HBAR, ATOM, LINK, NEAR with custom icon gradients
  - Positions: Direction badge, grid layers (X/10) progress bar, leveraged equity, TP target
  - Capital: 3-segment utilization (Long DCA / Short DCA / Cash Reserve)
  - Phase flow: Linear 3-node diagram (LONG_DCA ↔ ROUTER ↔ SHORT_DCA)
  - AI panel: Per-coin grid depth meter, direction, CFGI, top/conviction status
  - Risk profile: V14 params (BO 40%, DEV 2.0%, LAYERS 10, TP 1.5%, MULT 1.5×, LEV 1.5×)
  - Responsive, Chart.js, auto-refresh, standalone HTML

### Dashboard Sync
- **`trading/sync_dashboard.ps1`** — Updated for V14 data paths
  - Syncs `trading/spot/paper/v14/status.json` → `docs/data/v14/status.json`
  - Syncs `trading/spot/paper/v14/trades.csv` → `docs/data/v14/trades.csv`
  - Syncs scanner output → `docs/data/v14/scanner.json`
  - Windows Scheduled Task: `AIT_DashboardSync` (every 10 min)
