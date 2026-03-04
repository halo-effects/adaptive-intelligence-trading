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

### Coin Scanner (Legacy — Superseded 2026-03-03)
- **`trading/spot/backtest_results/v13/_v14_scanner.py`** — Original V14 scanner (DEPRECATED)
  - 15 coins evaluated, weighted scoring: trade cycling (25%), short PnL (20%), max DD (20%), ROI (15%), phase count (10%), win rate (10%)
  - Top scores: ATOM 97/A+, HBAR 94/A+, LINK 82/A, NEAR 74/B+
  - Output: `docs/data/v14/scanner.json` — **no longer consumed by dashboards**

### DCA Cycle Scanner (2026-03-03 — Current)
- **`trading/spot/v14_cycle_scanner.py`** — Capital velocity optimizer
  - Scores coins by DCA cycle efficiency: how fast they complete profitable cycles, how much capital gets trapped, and how deep the drawdowns go
  - **44 mature coins** from full Hyperliquid perp universe + immature coin tracking (auto-promotes at 6-month mark)
  - Rolling time windows: 7d, 14d, 30d, full bear (Jan 2026+)
  - Output: `docs/data/v14/cycle_scanner.json` — feeds all 3 dashboard Opportunity sections

- **Scoring formula:**
  ```
  DCA Score = Realized_PnL × (1 - MaxDD%) × Capital_Freedom / 100
  Capital_Freedom = 1 - (open_layers / 24)
  ```

- **DCA simulation parameters (V14 High Profile):**
  - BO=40%, SO_DEV=1.5%, SO_STEP_MULT=1.5, SO_VOL_MULT=1.5, TP=1.5%, MAX_LAYERS=12
  - Capital: $10K per coin, 90% DCA allocation, Hyperliquid taker fee (0.025%)

- **Per-coin metrics produced:**
  - `deals_completed` — completed DCA cycles in window
  - `deals_per_week` — cycle velocity (primary ranking metric)
  - `avg_cycle_hours` — average time from entry to TP
  - `realized_pnl` — total banked profit from completed cycles
  - `avg_pnl_per_deal` — average profit per cycle
  - `max_drawdown_pct` — worst peak-to-trough during window
  - `open_layers` — layers open at window end (capital lock indicator)
  - `unrealized_pnl` — P&L on open position
  - `net_return_pct` — total return including unrealized
  - `capital_freedom` — 1 - (open_layers/24), higher = more deployable capital
  - `dca_score` — composite score (the ranking metric)
  - `win_rate` — % of completed deals that were profitable
  - `mature` — boolean, true if coin has ≥6 months candle history
  - `history_months` — months of available data

- **Maturity gating:**
  - Minimum 6 months of 1h candle history required for published rankings
  - Immature coins scanned and tracked in `immature` array per window
  - Auto-promotes to published rankings when history crosses threshold
  - Rolling date — not hardcoded, recalculated each scan

- **Coin universe:**
  - 45 quality Hyperliquid perps + ASTER (Aster exchange live bot)
  - Auto-resolves symbol quotes (tries USDT then USDC)
  - Data sources: Binance (primary), KuCoin (KAS), candles.db
  - MKR gap: Binance data stops Sep 2025 (possibly delisted)

- **CLI:**
  ```
  python -m trading.spot.v14_cycle_scanner              # Full scan, all windows
  python -m trading.spot.v14_cycle_scanner --window 7d   # Single window
  python -m trading.spot.v14_cycle_scanner --coin HYPE   # Single coin
  python -m trading.spot.v14_cycle_scanner --top 5       # Top 5 only
  python -m trading.spot.v14_cycle_scanner --no-telegram  # Skip TG notification
  ```

- **Bear market results (2026-03-03, Jan 1 – Mar 3, 44 coins):**
  | Rank | Coin | Score | Deals/Wk | Realized | DD% |
  |------|------|-------|----------|----------|-----|
  | 1 | ZRO | 68.7 | 17.5 | +$12,289 | 36% |
  | 2 | HYPE | 41.7 | 10.3 | +$7,031 | 25% |
  | 3 | RENDER | 18.0 | 7.6 | +$4,649 | 51% |
  | 4 | STX | 17.0 | 5.7 | +$3,516 | 39% |
  | 5 | FET | 13.3 | 5.5 | +$3,468 | 51% |
  | ... | ... | ... | ... | ... | ... |
  | 43 | UNI | 2.3 | 0.9 | +$544 | 50% |
  | 44 | LTC | 2.1 | 0.8 | +$425 | 40% |

- **Key design insight:** Simple daily range / volatility ≠ DCA profitability. A coin can be very volatile but trend straight down (SOs fill, TP never hits). The simulation measures actual cycle completion with capital lock-up — what V14 actually experiences.

### Coin Discovery (Planned — 2D.6)
- **`trading/spot/v14_coin_discovery.py`** — not yet built
- Auto-detect new Hyperliquid perp listings (weekly)
- Backfill from Binance → KuCoin → Bybit (in order)
- Filters: no memecoins, no synthetic/leveraged, no sub-$1M volume, no <3mo launches
- Log to `memory/coin-discovery.log`

### Dashboard
- **`docs/dashboardV14.html`** (~1,050 lines) — Standalone V14 dashboard
  - Data: `data/v14/status.json`, `data/v14/trades.csv`, `data/v14/cycle_scanner.json`
  - Phases: LONG_DCA / SHORT_DCA / ROUTER (3 phases, replacing V13's 6 Wyckoff phases)
  - Coins: HBAR, ATOM, LINK, NEAR with custom icon gradients
  - Positions: Direction badge, grid layers (X/10) progress bar, leveraged equity, TP target
  - Capital: 3-segment utilization (Long DCA / Short DCA / Cash Reserve)
  - Phase flow: Linear 3-node diagram (LONG_DCA ↔ ROUTER ↔ SHORT_DCA)
  - AI panel: Per-coin grid depth meter, direction, CFGI, top/conviction status
  - Risk profile: V14 params (BO 40%, DEV 2.0%, LAYERS 10, TP 1.5%, MULT 1.5×, LEV 1.5×)
  - Responsive, Chart.js, auto-refresh, standalone HTML

### Incident Reports (added 2026-02-28)
- **`trading/spot/incident_schema.py`** — Incident report generator
  - `create_incident_report(trade, engine_state, peer_states, market_context, config)` → self-contained JSON
  - Auto-classification: `GRID_EXHAUSTION`, `PHASE_TRANSITION`, `EARLY_EXIT`, `SIGNAL_FAILURE`, `UNKNOWN`
  - Severity: LOW (<1% capital), MEDIUM (1-5%), HIGH (>5%)
  - Auto-generated recommendations per classification type
  - Multi-tenant ready: `account_id`, `strategy_id` fields, schema versioned (`1.0`)
  - Cloud-migration ready: stateless, self-contained, one file per event → S3/blob later
- **Runner integration** (`run_v14_paper.py`)
  - `_capture_incident()` on `V14PaperBot` — gathers engine + peer + market context, writes JSON, sends Telegram alert
  - `on_losing_trade` callback on `TradeTracker` — fires on SELL/SHORT_CLOSE when `pnl < 0`
  - Wrapped in try/except — never crashes the trading loop
  - Output: `trading/spot/paper/v14/incidents/{timestamp}_{coin}_{id}.json`
- **`trading/spot/incident_viewer.py`** — CLI incident browser
  - Summary table: date, coin, type, loss, severity, layers, hours
  - Filters: `--coin`, `--type`, `--severity`
  - Aggregate stats by type, by coin, total losses
  - `--json` flag for machine-readable output
- **Activation**: Next bot restart (pending — not yet active)

### Dashboard Sync
- **`trading/sync_dashboard.ps1`** — Updated for V14 data paths
  - Syncs `trading/spot/paper/v14/status.json` → `docs/data/v14/status.json`
  - Syncs `trading/spot/paper/v14/trades.csv` → `docs/data/v14/trades.csv`
  - Syncs scanner output → `docs/data/v14/scanner.json` (legacy, no longer consumed)
  - Cycle scanner writes directly to `docs/data/v14/cycle_scanner.json`
  - Windows Scheduled Task: `AIT_DashboardSync` (every 10 min)

### Realism Features (added 2026-02-28)
- **Liquidation tracking**: Per-position liquidation price (Hyperliquid isolated margin model), distance-to-liq %, liquidation event detection during backtest. At 1.5x, liq is ~60% from entry. Zero liquidation events in Oct 2024 → present.
- **Trading fees (realistic mode)**: Maker 0.02%, Taker 0.05%. Fees deducted from capital on every trade (compounding). Estimated all-time fees: ~$749 on $61,592 realized PnL (1.2%).
- **Dashboard**: Liquidation price (red) + distance-to-liq (amber <20%) on position cards. Fee display on Realized PnL card.

### Data Integrity Notes (2026-02-28)
- **Engine `pnl` field**: Added to all trade records (TP, CLOSE). Wrapper uses exact engine PnL instead of reverse-engineering from `amount * pnl_pct / (100 + pnl_pct)` — eliminates floating-point drift.
- **Dedup-at-source**: TradeTracker tracks `_existing_keys` (symbol+open_time+close_time) loaded from CSV. New trades checked against keys before recording. Prevents restart catch-up duplicates.
- **Clean backfill baseline (2026-02-28)**: $67,068 (+571%), 357 trades, $61,592 realized, $749 fees. Status↔CSV gap: $124.73 (0.2%, stable, from edge-case trades without `pnl` field).
- **PowerShell BOM hazard**: `Set-Content -Encoding UTF8` writes BOM (EF BB BF). Python's json.load() fails. Use `[System.Text.UTF8Encoding]::new($false)` for Python-consumed files.

### Live Order Execution Safety (2026-03-04) — CRITICAL for Hyperliquid Production

**Incident:** V14 Live bot on Aster attempted TP sell of 216.90 ASTER but exchange rejected with "insufficient balance." Engine had already mutated state (closed the deal, recorded a win), so it immediately opened a new L1 buy. Result: ~$155 of orphaned ASTER sitting on exchange untracked by the engine. Required manual intervention to recover.

**Root Cause:** Two-phase commit violation. `engine.tick()` mutates state (closes positions, updates PnL) and returns actions. The runner then tries to execute those actions on the exchange. If execution fails, the engine state is already wrong.

**Fixes Applied (must carry forward to Hyperliquid runner):**

1. **Qty cap on sell:** Always sell `min(tracked_qty, actual_exchange_balance)`. Fee/rounding drift means tracked qty will always be slightly more than actual balance over time. The `execute_sell()` pre-flight now has an `elif available < qty` branch that caps to actual balance and logs the drift.

2. **Pre-tick snapshot + rollback:** Before calling `engine.tick()`, snapshot all position-critical fields (long_coins, long_avg_entry, long_layers, long_tp, long_cost, long_trades, long_wins, long_pnl, capital). If the resulting sell fails on the exchange, restore the snapshot so the engine retries next tick instead of moving on.

3. **Sell failure notification:** On rollback, send Telegram alert with restored position details and "will retry on next candle."

**Production Requirements for Hyperliquid:**

- [ ] **Balance reconciliation loop:** Periodic (every N candles) comparison of engine state vs exchange balances. Alert on drift > 0.1%.
- [ ] **Atomic execution pattern:** Consider execute-first-then-update-engine instead of update-engine-then-execute. This inverts the current pattern — engine state only updates AFTER exchange confirms the fill.
- [ ] **Order receipt verification:** After `create_market_sell_order()`, verify the order ID exists and is filled via `fetch_order()` before proceeding.
- [ ] **Partial fill handling:** Market sells can partially fill. Engine must handle partial closes (reduce position by filled amount, keep remainder open).
- [ ] **Dead letter queue:** Failed actions should be queued and retried with backoff, not silently dropped.
- [ ] **Position sync on startup:** On every bot restart, compare engine state vs exchange positions and reconcile before entering live loop.
- [ ] **Idempotent trade recording:** Use exchange order IDs as dedup keys so the same fill can never be recorded twice.

**Exchange-Specific Notes:**
- **Aster:** Amount precision is a float step size (0.01), not decimal places. `round(amount, 0.01)` crashes Python — must convert to decimal places first.
- **Hyperliquid:** Test fee model (maker/taker), precision format, and partial fill behavior before going live. Perps have funding fees every 8h that affect PnL tracking.
- **General:** Never trust tracked qty for sells. Always query actual balance. The exchange is the source of truth, not the engine.
