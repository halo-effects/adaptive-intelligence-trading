# ROUTER v2 Test Plan — Conviction Override Integration

## Objective
Validate that ROUTER v2 (conviction-enabled) produces **identical results to the paper bot** until a conviction trigger fires. The ONLY divergence should be: conviction closes shorts early + buys spot longs.

## Engine Under Test
- **Base**: `v13_router_engine_v1.py` (verified $0.00 delta vs v8)
- **Addition**: Hybrid 3/4 conviction stack (Steve 3-Check + CFGI<35) firing during MARKDOWN
- **Class**: `V13RouterV2` (extends V1)

## Paper Bot Reference
- **Start date**: October 1, 2024
- **Coins**: ETH/USDC, SOL/USDC, LINK/USDC, XRP/USDC (NO BTC)
- **Capital**: $10,000 ($2,500/coin)
- **Profile**: High (T1=60%, T2=20%, T3=10%, symmetric shorts)
- **Reference data**: `trading/spot/paper/v13/trades.csv` + `state.json`

## Gates (all must pass)
1. **Top detected** — MARKUP->ROUTER transition must have fired (confirms cycle)
2. **3D death cross active** — SMA50 < SMA200 on 3-day resampled candles (filters corrections from real bears)
3. **2W StochRSI exhaustion crossover** — K crosses above D after being pinned < 5 for 3+ 2W candles, K >= 5.0 at crossover (confirms bottom turn, filters dead cat bounces)

## Conviction Score (3/4 required)
Any 3 of these 4 signals on 2D chart:
1. Below SMA200
2. RSI(14) < 26
3. StochRSI(3,3,14,14) K&D < 20
4. CFGI < 35

### Conviction Behavior
- All 3 gates must pass before score is evaluated
- Fires DURING MARKDOWN phase (overrides `_check_markdown()`)
- Closes all open shorts for that coin
- Enters MARKUP T1 (60% allocation)
- Sets `_no_reshort = True` — blocks all subsequent short opens for that coin until next full cycle
- **One trigger per cycle** — fires once per markdown, then locks out
- Gates reset when next top signal fires (new cycle begins)

### Locked Parameters (2026-02-27)
- 3D DX: SMA50/SMA200 on 3-day resampled daily candles
- 2W StochRSI: RSI(14) -> StochRSI(3,3,14,14), pinned threshold < 5, lookback 3 candles
- Exhaustion K minimum: 5.0
- Conviction score threshold: 3 of 4
- On trigger: close shorts + MARKUP T1 (60%) + no-reshort flag

## Verification Steps

### Step 1: Baseline Match (Pre-Conviction)
1. Run ROUTER v2 from Oct 1, 2024 → present with conviction **disabled**
2. Compare phase transitions against paper bot trades.csv
3. Compare every trade (date, type, coin, amount, price)
4. **Required**: $0.00 equity delta across all 4 coins
5. This confirms v2 inherits v1's verified behavior

### Step 2: Conviction Enabled
1. Run ROUTER v2 from Oct 1, 2024 → present with conviction **enabled**
2. Compare against paper bot trades.csv:
   - All trades BEFORE first conviction trigger must match exactly
   - Divergence point = conviction trigger date
   - After trigger: shorts closed early, spot longs opened
3. Document each conviction trigger: coin, date, which 3/4 signals fired

### Step 3: Verify No Pre-Trigger Divergence
- Diff every phase transition and trade before the first conviction trigger
- If ANY divergence exists before conviction fires → **BUG, do not ship**
- Same standard as v1 verification: $0.00 delta or it doesn't ship

## Known Gaps
- **LINK/XRP**: Zero Steve 3-Check signals (insufficient 2D SMA200 data). Conviction may never fire for these coins. Need fallback or longer data.
- **One-trigger-per-cycle lock**: Not yet implemented. Must build before running Step 2.

## Test Script
`trading/spot/backtest_results/v13/_verify_router_v2.py`

## Step 4: Side-by-Side Comparison
Run both configs from Oct 1, 2024 → present, per coin:

| Coin | Baseline Equity | Conviction Equity | Delta | Trigger Date | Signals |
|------|----------------|-------------------|-------|-------------|---------|
| ETH  | $X | $Y | +/- | date | which 3/4 |
| SOL  | $X | $Y | +/- | date | which 3/4 |
| LINK | $X | $Y | +/- | date or N/A | which 3/4 |
| XRP  | $X | $Y | +/- | date or N/A | which 3/4 |
| **Portfolio** | **$X** | **$Y** | **+/-** | | |

Per-coin breakdown:
- Phase timeline comparison (when do phases diverge?)
- Trade count difference
- Short P&L captured vs missed
- Spot long entry price vs what baseline would have paid

## Success Criteria
- [ ] Step 1: $0.00 delta, all 4 coins, conviction disabled
- [ ] Step 2: Pre-trigger trades identical, post-trigger divergence is conviction only
- [ ] Step 3: Zero unexplained divergences
- [ ] Conviction triggers documented with signal breakdown
