# AIT V14PM — Session Summary & Review Package (2026-07-04)
_For: Claude (Fable) — external review_
_Author: GeeGee (via Brett) | Date: 2026-07-04_
_Scope: All changes since Fable's post-remediation audit earlier today. Covers audit fixes, trade score improvements, and signal gating (Part A deployed, Part B analyzed with recommendation)._
_Code fingerprints: runner 4,780+ lines, capital manager 601+ lines, gate_model.py updated with G-1/G-2/G-3/G-6 changes_

---

## 1. Post-Remediation Audit Fixes (ALL DEPLOYED)

From Fable's post-remediation findings earlier today:

### M-2 — Balance-fetch failure guard
**File:** `run_v14_portfolio_live_aster.py`
- `fetch_full_balance()` now returns `None` on exception (was `{"usdt_free": 0.0, "usdt_total": 0.0}`)
- `_sync_positions_from_exchange()` checks for `None`, returns early with WARNING, keeps previous values
- Prevents injecting $0.00 as truth for one cycle, protects midnight rebalance from wrong equity

### M-3 — Prune docstring alignment
**File:** `run_v14_portfolio_live_aster.py`
- `_prune_stale_coin_after_tp()` docstring amended to match actual behavior
- Behavior: unconditional prune of flat coins from `active_allocations`; self-heals via next daily rebalance (≤24h)
- No code logic change, documentation accuracy only

### M-4 — Grid-freeze detector threshold
**File:** `run_v14_portfolio_live_aster.py`, `_check_grid_freeze()`
- Now imports `layer_cost` from GridModel and compares `eng.capital` against `gm_layer_cost(cs.layer_count, alloc)`
- Was: `eng.capital < 1.0` (flat $1 threshold)
- Now catches: "$5 on hand, $12 needed for next layer" — the real starvation case under GridModel fixed fractions

### H-1 — Sub-minimum layer warning
**File:** `run_v14_portfolio_live_aster.py`, `_check_grid_freeze()`
- If any layer in a coin's grid costs less than $10 exchange minimum, logs WARNING with details
- No behavior change — observability only
- Brett decision: no allocation floor needed. Real users start at $500+, where L4 = 16% × $167 = $26.70 (clears $10)

---

## 2. Trade Score Improvements (ALL DEPLOYED)

From Fable's Trade Score Assessment:

### P1 — Capital freedom denominator (S-1 bug fix)
**File:** `v14_cycle_scanner.py`
- Changed: `capital_freedom = 1 - open_layers/24` → `1 - open_layers/MAX_LAYERS`
- `/24` was a 12-layer-era constant. Under 4-layer grid, penalty ranged [0.833, 1.0] — effectively dead
- Now: [0.0, 1.0] as designed. 4 open layers = 0.0 freedom (fully trapped). Impact on rankings:

| Coin (30d) | Before (CapFree) | After (CapFree) | Before Score | After Score |
|------------|-----------------|-----------------|-------------|-------------|
| JUP (3L)   | 0.8750          | **0.25**        | 20.2        | **5.6**     |
| UNI (4L)   | 0.8333          | **0.00**        | 17.5        | **0.0**     |
| TAO (4L)   | 0.8333          | **0.00**        | 14.1        | **0.0**     |

### P2 — Time-at-depth penalty
**File:** `v14_cycle_scanner.py`
- New metric: `deals_depth_hours` — accumulates 1 hour per candle spent at L3+ per deal
- Formula: `depth_penalty = 1 / (1 + median_hours_at_L3plus / DEPTH_HALF_LIFE_H)`
- `DEPTH_HALF_LIFE_H = 72` (named constant). At 0h → 1.0, at 72h → 0.5, at 144h → 0.33
- Multiplied into dca_score. Directly penalizes ONDO-class capital traps (94h median at depth)
- New output fields: `median_depth_hours`, `depth_penalty`

### P3 — Score validation loop
**Files:** `run_v14_portfolio_live_aster.py` (TradeTracker + runner)
- `on_buy()` now accepts `dca_score`, `trade_score`, `trend_mult` — captured at deal-open from latest scanner JSON
- `on_sell()` record includes these three fields
- CSV fieldnames updated: old rows get empty values (append-compatible per Rule #29)
- New `_get_coin_scanner_scores()` helper reads scanner JSON at buy time
- Foundation for F2 realized-velocity-feedback spec (monthly score-vs-outcome report)

### P4 — Sim at live scale
**File:** `v14_cycle_scanner.py`
- `run_dca_sim()` accepts optional `sim_allocation` parameter
- `MIN_ORDER_NOTIONAL = 10.0` — both `open_deal` and `add_so` check against it (was `< 1.0`)
- Output includes `layers_executable` (int) and `grid_truncated` (bool)
- Validation: at $50 alloc, L4 = $8 → skipped (matches live H-1 behavior). At $141 alloc, all 4 clear.

### P5 — Funding cost subtraction
**File:** `v14_cycle_scanner.py`
- `AVG_FUNDING_RATE_8H = 0.0001` (0.01% per 8h, conservative market average)
- Applied in `close_deal()`: `funding_cost = position_cost × rate × (duration_h / 8)`
- Effect: JUP sim PnL dropped $2,870 → $2,800 (longer-held positions penalized more)
- TODO: replace with per-coin trailing average once funding data pipeline exists

### Score history reset
Old snapshots (computed with /24 denominator) contaminated trend multiplier calculations. Reset to 1 snapshot with new scoring. Trends will self-calibrate over 3+ days of scheduled scanner runs.

---

## 3. Signal Gating — Part A: Entry Veto (DEPLOYED, LIVE)

"Benign mute" — blocks new entries for overextended coins. Worst case = missed opportunity. Fully reversible.

### G-1 — NEAR fixture self-test
**File:** `engine/gate_model.py`, `self_test()`
- Real NEAR/USDT daily data from `candles_daily` (May-July 2026) baked into self-test
- Asserts full lifecycle against known blow-off → crash → basing cycle:

| Date | Event | Close | RSI | SMA50 | Assertion |
|------|-------|-------|-----|-------|-----------|
| May 21 | **TRIGGER** (A1_RSI_HOT) | $1.93 | 78.6 | $1.42 | Veto activates ✓ |
| May 28 | Hold at $2.43 | $2.43 | 69.8 | $1.59 | Does NOT clear (3 calm days < 4) ✓ |
| Jun 1 | **RE-TRIGGER** (A2_EXTENSION) | $2.64 | 70.3 | $1.67 | ATR threshold $2.08, close $2.64 > threshold ✓ |
| Jun 27 | **CLEAR** | $1.87 | 41.8 | $2.06 | 10 calm days, RSI normalized, full retrace ✓ |
| Jul 3 | No veto (recovery) | $2.05 | 52.0 | $2.10 | Normal conditions ✓ |

L-5 edge documented: veto CAN clear at $2.38 after 4 days, but A2 re-evaluates every daily candle and immediately re-triggers from extension.

### G-2 — A2 ATR normalization
**File:** `engine/gate_model.py`
- New constant: `EXT_ATR_MULT = 3.0`
- Extension threshold: `close > sma50 + EXT_ATR_MULT × ATR14` (long) / `close < sma50 - EXT_ATR_MULT × ATR14` (short)
- Replaces fixed `EXT_PCT = 0.25` which was volatility-blind
- Falls back to fixed 25% when ATR not available (backward-compatible)
- Calibration evidence:

| Scenario | ATR% | Threshold | Close vs SMA50 | Result |
|----------|------|-----------|----------------|--------|
| NEAR May 21 (blow-off) | 5.4% | 16.2% | 36.1% | ✓ VETO (correct) |
| TAO normal trading | 8.0% | 24.0% | 20.0% | ✓ NO VETO (correct) |
| High-vol coin at normal range | 8.0% | 24.0% | 20.0% | ✓ NO VETO (correct) |
| Low-vol coin extended | 3.0% | 9.0% | 15.0% | ✓ VETO (correct) |

### G-3 — A3 side-resolved wiring (audit M-5 fix)
**File:** `engine/gate_model.py`
- `has_fresh_divergence` (direction-agnostic) replaced with `has_bearish_divergence` + `has_bullish_divergence`
- Long veto: only consumes **bearish** divergence (price high + RSI low = weakness at top)
- Short veto: only consumes **bullish** divergence (price low + RSI high = strength at bottom)
- Self-test assertions: bearish div cannot veto short ✓, bullish div cannot veto long ✓
- All parameters have defaults — existing callers don't break

### G-4 — Precedence wiring in selector paths
**Files:** `v14_cycle_scanner.py`, `run_v14_portfolio_live_aster.py`, `v14_capital_manager.py`

**Scanner side:**
- New `_load_daily_signals()` — reads latest RSI, SMA50, ATR14 from `candles_daily` per coin
- Veto evaluation per coin in `scan_all()` using `gate_model.entry_veto()`
- Veto data attached to each ranking entry: `veto: {active, reason, side, extreme_price, rsi14, atr_pct}`
- Top-level `vetoes` dict and `vetoed_count` in JSON for observability
- A3 divergence set to False in scanner (divergence detection lives in engine modules; deferred to runner-level)

**Runner side (`_get_scanner_rankings()`):**
- Filters vetoed coins BEFORE scoring — serves `_rotate_after_tp()` and `_find_overflow_candidate()`
- Logs: "Veto filter excluded N coin(s): SYM(reason), ..."

**Capital manager side (`rebalance_daily()`):**
- Filters vetoed coins BEFORE hurdle rate check — vetoed coins never enter qualifying pool
- Precedence order verified: **veto → hurdle rate → trend multiplier → scoring → tier cap**

**Current state:** HYPE vetoed (A2_EXTENSION, 36.4% above SMA50). All other scanner coins clear.

### G-5 — Part A backtest results

**Window:** Apr 1 – Jul 3, 2026 (3 months, 46 coins)
**Parameters:** RSI_HOT=78, RSI_COLD=22, EXT_ATR_MULT=3.0, CALM_DAYS=4, RETRACE_PCT=25%

**Summary:**
| Metric | Value |
|--------|-------|
| Coins scanned | 46 |
| Coins with veto events | 34 (74%) |
| Total triggers | 53 |
| Total clears | 46 |
| Currently vetoed (Jul 3) | 7 |

**Per-coin veto events (all coins with triggers):**

| Coin | Triggers | Retriggers | Clears | Status (Jul 3) |
|------|----------|------------|--------|----------------|
| ARB | 2 | 0 | 2 | clear |
| ATOM | 2 | 0 | 2 | clear |
| BTC | 1 | 0 | 1 | clear |
| COMP | 1 | 0 | 0 | **VETOED (A1_RSI_HOT)** |
| CRV | 1 | 0 | 1 | clear |
| DOGE | 2 | 2 | 2 | clear |
| DYDX | 2 | 4 | 2 | clear |
| EIGEN | 3 | 0 | 2 | **VETOED (A2_EXTENSION)** |
| ENA | 1 | 0 | 1 | clear |
| ENS | 1 | 0 | 0 | **VETOED (A1_RSI_HOT)** |
| FET | 1 | 0 | 1 | clear |
| FIL | 1 | 2 | 1 | clear |
| HYPE | 2 | 0 | 1 | **VETOED (A2_EXTENSION)** |
| INJ | 2 | 4 | 2 | clear |
| JUP | 2 | 2 | 2 | clear |
| KAS | 1 | 0 | 1 | clear |
| LDO | 2 | 0 | 2 | clear |
| LINK | 1 | 0 | 1 | clear |
| NEAR | 3 | 2 | 3 | clear |
| ONDO | 2 | 2 | 2 | clear |
| OP | 2 | 2 | 2 | clear |
| PENDLE | 2 | 2 | 1 | **VETOED (A2_EXTENSION)** |
| PYTH | 1 | 0 | 1 | clear |
| RENDER | 2 | 0 | 1 | **VETOED (A2_EXTENSION)** |
| RUNE | 1 | 0 | 1 | clear |
| SEI | 1 | 0 | 1 | clear |
| SNX | 1 | 0 | 1 | clear |
| SOL | 1 | 0 | 1 | clear |
| STX | 1 | 0 | 1 | clear |
| SUI | 1 | 2 | 1 | clear |
| TAO | 1 | 0 | 1 | clear |
| TIA | 3 | 0 | 2 | **VETOED (A2_EXTENSION)** |
| TON | 2 | 2 | 2 | clear |
| UNI | 1 | 0 | 1 | clear |

**NEAR anchor assertions (all pass):**
1. ✅ Veto triggers May 8 (A2_EXTENSION, first overshoot)
2. ✅ Clears May 17 (retraced, RSI normalized)
3. ✅ Re-triggers May 20 (A2), upgrades to A1 May 21 (RSI 78.6), downgrades to A2 May 27
4. ✅ Clears May 30 (4 calm days, retrace, RSI normalized)
5. ✅ Re-triggers May 31 (A2, bounce above ATR threshold)
6. ✅ Clears Jun 7 (crash completed, basing at $2.06, RSI 48.9)
7. ✅ Not vetoed Jul 3 (recovery, RSI 52.0)

**Part A is LIVE** — scanner + runner restarted with veto filtering active.

---

## 4. Signal Gating — Part B: L3/L4 Layer Gate (ANALYZED, NOT DEPLOYED)

### G-6 — B1 Fork Resolution

**Question:** Does stall-only B1 block L3/L4 fills during waterfall crashes?

**Test:** Simulated DCA grid through two waterfall legs with L3/L4 gating active:
- NEAR Jun 4–12: $2.82 → $1.81 (26.9% crash, 193 1h candles)
- INJ Jun 1–6: $7.35 → $4.78 (20.8% crash, 121 1h candles)

**Round 1 — No higher-low requirement:**
| Waterfall | L3/L4 Admitted | L3/L4 Gated | Leaks via |
|-----------|---------------|-------------|-----------|
| NEAR | 1 | 2 | B2 (K↑D cross on dead-cat bounce) |
| INJ | 2 | 4 | B2 (K↑D cross on intra-crash bounce) |
| **Total** | **3** | **6** | **All B2** |

**Round 2 — B2 higher-low added (B1 unchanged):**
| Waterfall | L3/L4 Admitted | L3/L4 Gated | Leaks via |
|-----------|---------------|-------------|-----------|
| NEAR | 1 | 12 | B1 stall (3h pause in crash) |
| INJ | 2 | 14 | B1 stall (3h pause in crash) |
| **Total** | **3** | **26** | **All B1** |

**Round 3 — Both B1 + B2 require higher-low:**
| Waterfall | L3/L4 Admitted | L3/L4 Gated |
|-----------|---------------|-------------|
| NEAR | **0** | 193 |
| INJ | **0** | 96 |
| **Total** | **0** | **289** |

**Resolution:** Higher-low anchor is the universal anti-noise filter. No flush primitive needed. Both B1 (stall ≥ STALL_N candles) and B2 (StochRSI K↑D, K < GATE_K_MAX=40) require the most recent 1h low to be HIGHER than the prior swing low before admitting a fill. Spec should be amended to v1.1.

### G-7 — Full backtest (4 arms, 8 coins, 90 days)

**Parameters:**
- Grid: D-GRID(d) [40/24/20/16%], TP 3.0%, Dev 1.5%, Max 4 layers
- B1: stall ≥ 3 candles (no new low) + higher-low
- B2: StochRSI K↑D cross, K < 40 + higher-low
- Cooldown: 4h between gated L3 and L4
- Veto: A1 RSI>78/<22, A2 ATR-normalized (3.0×ATR14), A3 side-resolved divergence

**Per-coin results (all 4 arms):**

| Coin | Arm | Deals | PnL | WR% | MaxDD | AvgDur | L3+ | Vetoed | Gated |
|------|-----|-------|-----|-----|-------|--------|-----|--------|-------|
| NEAR | mechanical | 41 | $7,900 | 100% | 22.2% | 33.4h | 12 | 0 | 0 |
| NEAR | veto | 35 | $6,972 | 100% | 12.1% | 36.4h | 12 | 527 | 0 |
| NEAR | gate | 38 | $6,305 | 100% | 2.7% | 36.1h | 0 | 0 | 1,470 |
| NEAR | veto+gate | 33 | $5,639 | 100% | 2.7% | 38.8h | 0 | 522 | 924 |
| TAO | mechanical | 5 | $726 | 100% | 42.2% | 10.8h | 1 | 0 | 0 |
| TAO | veto | 5 | $726 | 100% | 42.2% | 10.8h | 1 | 0 | 0 |
| TAO | gate | 5 | $666 | 100% | 2.0% | 10.8h | 0 | 0 | 2,100 |
| TAO | veto+gate | 5 | $666 | 100% | 2.0% | 10.8h | 0 | 0 | 2,100 |
| INJ | mechanical | 45 | $8,530 | 100% | 22.5% | 29.7h | 15 | 0 | 0 |
| INJ | veto | 31 | $6,056 | 100% | 18.5% | 33.6h | 13 | 644 | 0 |
| INJ | gate | 39 | $6,246 | 100% | 9.8% | 34.4h | 1 | 0 | 1,384 |
| INJ | veto+gate | 25 | $4,009 | 100% | 9.8% | 42.0h | 1 | 644 | 827 |
| TON | mechanical | 31 | $5,151 | 100% | 29.9% | 24.1h | 5 | 0 | 0 |
| TON | veto | 31 | $5,913 | 100% | 11.4% | 35.8h | 9 | 550 | 0 |
| TON | gate | 29 | $4,449 | 100% | 2.9% | 25.8h | 0 | 0 | 1,723 |
| TON | veto+gate | 9 | $1,428 | 100% | 2.9% | 76.4h | 0 | 146 | 1,630 |
| JUP | mechanical | 24 | $4,426 | 100% | 30.7% | 34.0h | 6 | 0 | 0 |
| JUP | veto | 20 | $4,212 | 100% | 27.3% | 96.2h | 8 | 210 | 0 |
| JUP | gate | 17 | $2,808 | 100% | 3.1% | 48.4h | 0 | 0 | 1,760 |
| JUP | veto+gate | 13 | $2,332 | 100% | 2.8% | 148.7h | 0 | 207 | 1,559 |
| DYDX | mechanical | 21 | $4,188 | 100% | 20.1% | 35.9h | 10 | 0 | 0 |
| DYDX | veto | 16 | $3,081 | 100% | 15.5% | 47.1h | 7 | 513 | 0 |
| DYDX | gate | 16 | $2,617 | 100% | 22.6% | 47.4h | 0 | 0 | 577 |
| DYDX | veto+gate | 15 | $2,284 | 100% | 3.1% | 50.3h | 0 | 513 | 534 |
| ASTER | mechanical | 19 | $3,581 | 100% | 14.2% | 91.0h | 7 | 0 | 0 |
| ASTER | veto | 19 | $3,581 | 100% | 14.2% | 91.0h | 7 | 0 | 0 |
| ASTER | gate | 15 | $2,498 | 100% | 3.0% | 115.5h | 0 | 0 | 1,390 |
| ASTER | veto+gate | 15 | $2,498 | 100% | 3.0% | 115.5h | 0 | 0 | 1,390 |
| HYPE | mechanical | 11 | $1,927 | 100% | 9.3% | 24.8h | 2 | 0 | 0 |
| HYPE | veto | 11 | $1,927 | 100% | 9.3% | 24.8h | 2 | 0 | 0 |
| HYPE | gate | 10 | $1,689 | 100% | 2.1% | 23.9h | 0 | 0 | 431 |
| HYPE | veto+gate | 10 | $1,689 | 100% | 2.1% | 23.9h | 0 | 0 | 431 |

**Summary by arm:**

| Arm | Deals | PnL | Avg MaxDD | Avg Duration | L3+ | Vetoed | Gated |
|-----|-------|-----|-----------|-------------|-----|--------|-------|
| Mechanical | 197 | $36,429 | 23.9% | 35.5h | 58 | 0 | 0 |
| Veto only | 168 | $32,467 | 18.8% | 47.0h | 50 | 2,444 | 0 |
| Gate only (L3+L4) | 169 | $27,280 | 6.0% | 42.8h | 1 | 0 | 10,835 |
| Veto + Gate | 125 | $20,546 | 3.6% | 63.3h | 0 | 2,032 | 9,395 |

**Finding:** Strict gate (L3+L4 both gated) blocks almost ALL L3/L4 fills (10,835 gated, 1 admitted). PnL drops 25%. On 1.0x leverage with no liquidation risk, drawdown is temporary — the grid always recovers (100% WR). The 25% PnL cost is excessive for the risk profile.

### G-7 Options Test — Gate Calibration

Three alternative calibration approaches tested:

**Option 1 — Gate during veto only:** L3/L4 are mechanical when no veto active, gated only when the coin is in a vetoed state.
**Option 2 — Gate L4 only:** L3 fills mechanically, only L4 requires exhaustion evidence.
**Option 3 — Relaxed higher-low:** Min of last 6 candle lows > prior swing low (instead of strict current low > prior).

**Per-coin results (all 5 modes):**

| Coin | Mode | Deals | PnL | MaxDD | L3+ | L4 | Gated |
|------|------|-------|-----|-------|-----|-----|-------|
| NEAR | mechanical | 41 | $7,900 | 22.2% | 12 | 5 | 0 |
| NEAR | strict_gate | 38 | $6,305 | 2.7% | 0 | 0 | 1,473 |
| NEAR | opt1_veto_gate | 44 | $8,257 | 16.8% | 8 | 4 | 409 |
| NEAR | opt2_l4_only | 38 | $7,043 | 4.8% | 10 | 0 | 1,215 |
| NEAR | opt3_relaxed_hl | 38 | $6,305 | 2.7% | 0 | 0 | 1,473 |
| TAO | mechanical | 4 | $607 | 42.7% | 1 | 0 | 0 |
| TAO | strict_gate | 4 | $547 | 2.0% | 0 | 0 | 2,100 |
| TAO | opt1_veto_gate | 4 | $607 | 42.7% | 1 | 0 | 0 |
| TAO | opt2_l4_only | 4 | $607 | 2.9% | 1 | 0 | 2,074 |
| TAO | opt3_relaxed_hl | 4 | $547 | 2.0% | 0 | 0 | 2,100 |
| INJ | mechanical | 45 | $8,578 | 22.4% | 15 | 7 | 0 |
| INJ | strict_gate | 39 | $6,246 | 9.8% | 1 | 1 | 1,393 |
| INJ | opt1_veto_gate | 43 | $7,507 | 19.7% | 7 | 4 | 390 |
| INJ | opt2_l4_only | 45 | $8,042 | 4.0% | 14 | 0 | 1,186 |
| INJ | opt3_relaxed_hl | 39 | $6,127 | 3.2% | 1 | 0 | 1,493 |
| TON | mechanical | 31 | $5,151 | 29.9% | 5 | 2 | 0 |
| TON | strict_gate | 29 | $4,449 | 2.9% | 0 | 0 | 1,723 |
| TON | opt1_veto_gate | 30 | $4,735 | 28.7% | 2 | 1 | 126 |
| TON | opt2_l4_only | 30 | $4,937 | 4.6% | 5 | 0 | 1,612 |
| TON | opt3_relaxed_hl | 29 | $4,449 | 2.9% | 0 | 0 | 1,723 |
| JUP | mechanical | 24 | $4,426 | 30.7% | 6 | 3 | 0 |
| JUP | strict_gate | 18 | $2,927 | 3.0% | 0 | 0 | 1,742 |
| JUP | opt1_veto_gate | 21 | $3,878 | 31.4% | 4 | 3 | 91 |
| JUP | opt2_l4_only | 22 | $3,974 | 4.3% | 6 | 0 | 1,567 |
| JUP | opt3_relaxed_hl | 18 | $2,927 | 2.9% | 0 | 0 | 1,749 |
| DYDX | mechanical | 21 | $4,188 | 20.1% | 10 | 5 | 0 |
| DYDX | strict_gate | 16 | $2,617 | 22.6% | 0 | 0 | 577 |
| DYDX | opt1_veto_gate | 19 | $3,367 | 21.3% | 3 | 3 | 315 |
| DYDX | opt2_l4_only | 21 | $3,950 | 20.4% | 10 | 0 | 477 |
| DYDX | opt3_relaxed_hl | 16 | $2,617 | 23.1% | 0 | 0 | 587 |
| ASTER | mechanical | 19 | $3,581 | 14.2% | 7 | 4 | 0 |
| ASTER | strict_gate | 15 | $2,498 | 3.0% | 0 | 0 | 1,390 |
| ASTER | opt1_veto_gate | 19 | $3,581 | 14.2% | 7 | 4 | 0 |
| ASTER | opt2_l4_only | 17 | $3,165 | 5.3% | 6 | 0 | 1,026 |
| ASTER | opt3_relaxed_hl | 15 | $2,498 | 3.0% | 0 | 0 | 1,390 |
| HYPE | mechanical | 11 | $1,915 | 9.3% | 3 | 0 | 0 |
| HYPE | strict_gate | 10 | $1,618 | 2.2% | 0 | 0 | 446 |
| HYPE | opt1_veto_gate | 11 | $1,915 | 9.3% | 3 | 0 | 0 |
| HYPE | opt2_l4_only | 11 | $1,915 | 3.4% | 3 | 0 | 350 |
| HYPE | opt3_relaxed_hl | 10 | $1,618 | 2.2% | 0 | 0 | 446 |

**Summary comparison:**

| Mode | Deals | PnL | % of Mech | Avg MaxDD | DD Reduction | PnL per % DD |
|------|-------|-----|-----------|-----------|-------------|-------------|
| Mechanical (baseline) | 196 | $36,345 | 100.0% | 23.9% | — | $1,519 |
| Strict gate (L3+L4) | 169 | $27,208 | 74.9% | 6.0% | 74.8% | $4,506 |
| **Opt 1: Veto-only gate** | 191 | $33,847 | 93.1% | 23.0% | 3.9% | $1,471 |
| **Opt 2: Gate L4 only** | 188 | $33,633 | 92.5% | 6.2% | 74.0% | **$5,405** |
| **Opt 3: Relaxed HL** | 169 | $27,089 | 74.5% | 5.3% | 78.0% | $5,153 |

**Analysis:**
- **Option 1** barely reduces drawdown (3.9%) — the veto isn't active during most corrections. L3/L4 fire freely in normal pullbacks, including mid-waterfall when no veto is active.
- **Option 2** retains 92.5% of PnL while cutting drawdown 74%. L3 fills freely (55 fills, the workhorse averaging layer). Only L4 requires exhaustion evidence. Best risk-adjusted return at $5,405/%.
- **Option 3** performs identically to strict gate — the 6-candle relaxation doesn't change outcomes.

**Recommendation: Option 2 (Gate L4 only, L3 mechanical).** Simple mental model, best PnL/DD tradeoff.

---

## 5. Files Modified Today

| File | Changes |
|------|---------|
| `run_v14_portfolio_live_aster.py` | M-2 (None guard), M-3 (docstring), M-4 (grid-freeze threshold), H-1 (sub-min warning), P3 (score logging), G-4 (veto filter in `_get_scanner_rankings`) |
| `v14_capital_manager.py` | G-4 (veto filter in `rebalance_daily`) |
| `v14_cycle_scanner.py` | P1 (capital freedom), P2 (depth penalty), P4 (sim alloc + $10 min), P5 (funding cost), G-4 (veto computation + daily signals) |
| `engine/gate_model.py` | G-1 (NEAR fixture), G-2 (ATR norm + `EXT_ATR_MULT`), G-3 (side-resolved div), G-6 (higher-low on B1+B2), `GATE_K_MAX` constant |
| `_gate_backtest_1h.py` | Higher-low tracking for B1 and B2, `prior_swing_low` state |

**Not modified:** `engine/grid_model.py`, `v14_dca_engine.py`, `v14_lifecycle_engine.py`

**New artifacts:**
- `specs/g5-veto-backtest-results.json` — Part A veto backtest (46 coins, 3 months)
- `specs/g7-backtest-summary.md` — Full gate backtest summary
- `specs/gate-backtest-results-1h.json` — Raw 4-arm backtest data (8 coins, 90 days)

---

## 6. Questions for Fable Review

1. **Option 2 deployment:** Does Fable concur that gating L4 only (L3 mechanical) is the right calibration? Any concern about L3 being ungated?
2. **Higher-low as universal anchor:** Both B1 and B2 now require `has_higher_low`. G-6 shows zero waterfall leaks. Are there edge cases where this is too strict or too loose?
3. **A3 divergence in scanner:** Currently set to False (divergence detection is in engine modules). Acceptable for Part A, or should it be wired in?
4. **EXT_ATR_MULT = 3.0:** Calibrated from NEAR data. Should this be validated across a broader coin set?
5. **M-1 (reconcile zeroes reserve):** Deferred until equity approaches $10K. Should it be specced now while context is fresh?
6. **DYDX anomaly:** Strict gate shows 22.6% MaxDD (worse than mechanical's 20.1%). This appears to be because gating delays fills into worse price levels on one specific deal. Worth investigating?

---

## 7. Production State

| Component | Status |
|-----------|--------|
| V14PM Live bot | Running with M-2/M-3/M-4/H-1 + P3 + Part A veto |
| Scanner | Outputs veto flags; HYPE currently vetoed |
| Part A (entry veto) | **DEPLOYED, LIVE** |
| Part B (L4 gate) | **Code exists, NOT wired into engine** |
| Score improvements (P1-P5) | **DEPLOYED** |
| Score history | Reset to 1 snapshot; trends recalibrating |
