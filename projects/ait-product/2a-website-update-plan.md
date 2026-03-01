# 2A: Website Content Update Plan — V13 → V14

**Generated:** 2026-03-01  
**Status:** DRAFT — Needs Brett review before any changes  
**Engine:** V14 DCA-Only (LONG_DCA / SHORT_DCA / ROUTER)  
**Coins:** HBAR/USDT, ATOM/USDT, LINK/USDC, NEAR/USDT  
**Period:** Oct 2024 → Feb 2026 (515 days)  
**Capital:** $10,000 ($2,500/coin)

---

## ⚠️ CRITICAL: V14 Backtest Results Are Problematic

Before detailing the change plan, Brett needs to be aware that the V14 numbers are **significantly worse** than V13 and may not be suitable for marketing:

### V14 Backtest Results Summary

| Coin | Low ROI | Med ROI | High ROI |
|------|---------|---------|----------|
| HBAR | +202.3% | +202.3% | +226.0% |
| ATOM | **-52.2%** | **-52.2%** | **-54.0%** |
| LINK | +173.5% | +173.5% | +182.3% |
| NEAR | **-53.1%** | **-53.1%** | **-54.5%** |
| **Portfolio** | **+67.6%** | **+67.6%** | **+74.9%** |

| Metric | Low | Medium | High |
|--------|-----|--------|------|
| Portfolio Equity | $16,763 | $16,763 | $17,494 |
| Win Rate | 67% | 67% | 67% |
| Daily ROI | 0.131% | 0.131% | 0.146% |
| Worst Max DD | -69.7% | -69.7% | -70.5% |
| Total Trades | 9 | 9 | 9 |

### Key Issues

1. **Win rate is 67%, not 100%** — ATOM and NEAR have open losing positions at backtest end
2. **Two coins are underwater** — ATOM (-52%) and NEAR (-53%) are significant losses
3. **Low and Medium profiles produce IDENTICAL results** — leverage parameter only affects liquidation math, not position sizing in the V14 engine
4. **Max drawdown is -70%** — much worse than implied by current site
5. **Daily ROI is 0.13%** — current site claims 0.35%
6. **Only 9 total trades** — very few data points for statistical confidence
7. **Short test period** (515 days vs V13's ~4.3 years) — less representative
8. **Portfolio ROI +68-75%** vs V13's headline numbers of +522% to +64,627%

### Decision Points for Brett

1. **Are these numbers ready for the website?** The V14 results are honest but not impressive for marketing
2. **Should ATOM and NEAR be replaced?** They're dragging the portfolio down
3. **Should we wait for better results** or a longer backtest period?
4. **Is the leverage bug intentional?** Low vs Medium showing identical results suggests leverage isn't wired into position sizing
5. **How to handle the win rate drop** from "100%" to "67%"?

---

## File-by-File Change Plan

### File 1: `docs/index.html`

#### 1.1 Hero Stats — Win Rate
**Line:** Hero stats section  
**Old:** `<div class="hero-stat-value">100%</div><div class="hero-stat-label">Win Rate (Backtest)</div>`  
**New:** TBD — depends on whether we keep "100%" (misleading) or show actual "67%" (less marketable)  
**Rationale:** V14 win rate is 67% across all profiles  
**⚠️ Ask Brett:** How to handle this — completed-cycle win rate vs overall?

#### 1.2 Risk Profiles — "100% win rate" claim
**Old:** `<strong>100% win rate across all profiles and coins.</strong>`  
**New:** Remove or rephrase  
**Rationale:** No longer accurate with V14

#### 1.3 Backtest Results Table
**Old:**
```
Oct 2020 → Feb 2025 · $10,000 starting capital · 1h candles
ETH  +522%    +976%     +1,284%
SOL  +22,034% +35,409%  +64,627%
BTC  +245%    +218%     +590%
Win Rate: 100%  100%  100%
```
**New:**
```
Oct 2024 → Feb 2026 · $10,000 starting capital · 1h candles
HBAR  +202%    +202%    +226%
ATOM  -52%     -52%     -54%
LINK  +174%    +174%    +182%
NEAR  -53%     -53%     -55%
Win Rate: 67%   67%     67%
```
**Rationale:** Replace V13 coins/numbers with V14 actuals  
**⚠️ Ask Brett:** ATOM and NEAR showing losses — do we really want to show these?

#### 1.4 Performance Comparison Section
**Old:** `<strong style="color:var(--ait-blue);font-size:20px;">BTC · ETH · SOL</strong><br><span style="font-size:14px;color:var(--text-body);">backtested Oct 2020 → Feb 2026</span>`  
**New:** `HBAR · ATOM · LINK · NEAR` and `Oct 2024 → Feb 2026`  
**Rationale:** New coins, new period

#### 1.5 "100% win rate · all risk levels" stat box
**Old:** `100% win rate · all risk levels`  
**New:** TBD  
**Rationale:** No longer accurate

#### 1.6 "100% on completed cycles" in comparison table
**Old:** `100% on completed cycles`  
**New:** TBD  
**⚠️ Ask Brett:** If we define "completed cycles" carefully, the completed DCA TPs might still be 100% — need to verify

#### 1.7 Layer 05 — "Spot DCA & Scale-Out" description
**Old:** `You own real coins. No leverage. No liquidation risk.`  
**New:** TBD — V14 uses leverage (1.5x on Medium/High) and perps, not spot  
**Rationale:** V14 is a fundamentally different architecture (perps with leverage, not spot)  
**⚠️ Ask Brett:** Major positioning change — "spot ownership" was a key selling point

#### 1.8 Layer 08 — Portfolio Management
**Old:** `Coins in Spring or Markup phases receive more capital.`  
**New:** Update phase names to LONG_DCA/SHORT_DCA/ROUTER  
**Rationale:** V14 doesn't have Spring/Markup phases

#### 1.9 "3 coins" references → "4 coins"
Multiple locations reference 3-coin portfolio, needs updating to 4

---

### File 2: `docs/pricing.html`

#### 2.1 "20+ certified coins" references
**Old:** `20+ certified coins available to every tier`  
**New:** TBD — V14 currently has 4 coins  
**⚠️ Ask Brett:** Is the coin universe still 20+? Or fewer for V14?

#### 2.2 Breakeven Calculator — "0.35% daily ROI"
**Old:** `At 0.35% average daily ROI with 100% profit compounding`  
**New:** `At 0.13% average daily ROI` (or 0.15% for High)  
**Rationale:** V14 daily ROI is much lower  
**Impact:** Breakeven changes from ~29 days to ~77 days (Starter $500 on $5K at 0.13%)

#### 2.3 Backtest Performance callout
**Old:** `ETH +976% · SOL +35,409% (Medium) | ETH +1,284% · BTC +590% (High) | 100% win rate`  
**New:** `HBAR +202% · LINK +174% (Medium) | HBAR +226% · LINK +182% (High) | 67% win rate`  
**Rationale:** Replace with V14 actuals

#### 2.4 FAQ — "Wyckoff Lifecycle Engine" description
**Old:** `5-phase Wyckoff lifecycle: DCA, EXIT, MARKDOWN, SPRING, MARKUP`  
**New:** `3-phase cycle: LONG_DCA, SHORT_DCA, ROUTER`  
**Rationale:** V14 architecture change

#### 2.5 FAQ — Risk profiles answer
**Old:** `Low: ETH +325%, SOL +15,145%, BTC +166%. Medium: ETH +539%...`  
**New:** Replace with V14 numbers per coin per profile  
**Rationale:** Old numbers are V13

#### 2.6 FAQ — Expected ROI
**Old:** `~0.35% daily ROI... ETH +1,116%, SOL +49,690%, BTC +299% (High profile) with 100% win rate`  
**New:** Replace with V14 actuals  
**Rationale:** Completely different performance profile

#### 2.7 FAQ — "Spot trading only - no leverage, no liquidation risk"
**Old:** (multiple places) Spot-only claims  
**New:** V14 uses perps with leverage (1.5x Medium/High)  
**⚠️ Ask Brett:** This is a fundamental product positioning change

#### 2.8 "Spot Ownership" feature card
**Old:** `Spot trading only - no leverage, no liquidation risk, no hidden funding fees`  
**New:** Needs complete rewrite for perps model  
**⚠️ Ask Brett:** How to position this

#### 2.9 Pricing tier descriptions — "1 coin", "2 coins", etc.
**Old:** Tier-based coin counts (1/2/3/5/8 coins)  
**New:** TBD — verify if tier structure changes for V14

#### 2.10 "$100M" capacity pool
May need updating if the V14 model changes capacity assumptions

---

### File 3: `docs/wyckoff-lifecycle.html`

#### 3.1 Hero subtitle
**Old:** `Five-phase market cycle engine — accumulate, ride, distribute, protect, spring, repeat.`  
**New:** `Three-phase DCA engine — long accumulation, short accumulation, intelligent routing.`  
**Rationale:** V14 has 3 phases, not 5

#### 3.2 Wyckoff Chart — 5 Phase Action Strips
**Old:** DCA → MARKUP → EXIT → MARKDOWN → SPRING  
**New:** LONG_DCA → ROUTER → SHORT_DCA (and back)  
**Rationale:** Completely different phase model  
**Note:** The entire chart canvas JS needs rewriting for 3 phases

#### 3.3 "Five Phases of the Wyckoff Lifecycle" section
**Old:** 5 phase cards (DCA, MARKUP, EXIT, MARKDOWN, SPRING) + cycle card  
**New:** 3 phase cards (LONG_DCA, SHORT_DCA, ROUTER) + cycle card  
**Rationale:** V14 architecture

#### 3.4 Backtest Results Tables (ETH, SOL, BTC)
**Old:**
```
ETH: +522% / +976% / +1,284%  (Low/Med/High)
SOL: +22,034% / +35,409% / +64,627%
BTC: +245% / +218% / +590%
All 100% win rate
```
**New:**
```
HBAR: +202% / +202% / +226%
ATOM: -52% / -52% / -54%
LINK: +174% / +174% / +182%
NEAR: -53% / -53% / -55%
Win rate: 67%
```
**Rationale:** V14 backtest actuals

#### 3.5 "V12f with CFGI Sentiment Gates" label
**Old:** `V12f with CFGI Sentiment Gates · Oct 2020 → Feb 2025`  
**New:** `V14 DCA Engine · Oct 2024 → Feb 2026`

#### 3.6 "+39% average improvement over V12e" subtitle
**Old:** `+39% average improvement over V12e across all configurations`  
**New:** Remove or replace with V14-relevant comparison

#### 3.7 Completed Trades table
**Old:** ETH 92/110/110, SOL 18/4/7, BTC 30/15/5  
**New:** V14 trade counts (very low — only 9 total per profile across 4 coins)

#### 3.8 Estimated Transactions table
**Old:** ETH ~850, SOL ~60, BTC ~160  
**New:** Much lower for V14

#### 3.9 CFGI Sentiment Gates section
**Old:** References V12e/V12f specific gate behavior  
**New:** TBD — V14 may use different signal stack  
**⚠️ Ask Brett:** Does V14 still use CFGI gates?

#### 3.10 Battle-Tested stats
**Old:** `196 backtests, 96 parameter combos, 45K+ candles, 2,200+ deals, 8,800+ trades, 5+ yrs data, 13 engine iterations`  
**New:** Update to V14 development stats  
**⚠️ Ask Brett:** What are the accurate V14 development stats?

#### 3.11 "3 risk profiles × 3 coins × multiple timeframes" note
**Old:** `3 risk profiles × 3 coins`  
**New:** `3 risk profiles × 4 coins`

#### 3.12 Mock Dashboard
**Old:** Shows SOL/BTC/ETH/HYPE with V13 phases  
**New:** Show HBAR/ATOM/LINK/NEAR with V14 phases

#### 3.13 Page title
**Old:** `Wyckoff Lifecycle Engine`  
**New:** TBD — V14 may not use "Wyckoff" framing since phases are different  
**⚠️ Ask Brett:** Keep the Wyckoff branding or rename?

---

## Cross-Cutting Issues

### Issue A: Spot → Perps Transition
The current website heavily sells **spot ownership** as a feature ("you own real coins", "no leverage", "no liquidation"). V14 uses **perpetual futures with leverage**. This is a fundamental product positioning change that affects:
- index.html: Layer 05, Risk Management section
- pricing.html: Multiple FAQ answers, feature cards
- wyckoff-lifecycle.html: Various descriptions

### Issue B: Win Rate Drop (100% → 67%)
The "100% win rate" was a major selling point throughout. With V14 showing 67%, this needs careful handling. Options:
1. Show actual 67% (honest but less marketable)
2. Only show "completed cycle" win rate (potentially misleading)
3. Wait for better results before updating

### Issue C: Low = Medium (Identical Results)
The Low and Medium profiles produce identical results because leverage doesn't affect position sizing in V14. This makes the 3-profile model look broken. Either:
1. Fix the engine so leverage actually changes behavior
2. Only show 2 profiles (Low and High)
3. Change what differentiates profiles (e.g., capital allocation %)

### Issue D: Losing Coins (ATOM, NEAR)
Two of four coins are showing -52% to -54% losses. Options:
1. Replace ATOM/NEAR with better-performing coins
2. Show them honestly (but hurts marketing)
3. Wait for positions to close before using the data

### Issue E: Test Period Length
V13 had ~4.3 years of data (Oct 2020 → Feb 2025). V14 has only ~1.4 years (Oct 2024 → Feb 2026). The shorter period and open positions make the data less conclusive.

---

## Recommended Next Steps

1. **Brett reviews this plan** and decides on Issues A-E above
2. **Fix the leverage bug** if Low ≠ Medium is intended
3. **Consider coin selection** — maybe replace ATOM/NEAR
4. **Decide on messaging strategy** for lower numbers
5. **Only then** proceed with HTML changes

---

## Raw Backtest Data

Full per-coin results saved to: `trading/spot/backtest_results/v13/v14_website_results.json`

### Per-Coin Detail (All Profiles)

**HBAR/USDT:**
- Low: $7,558 (+202.3%), 4 trades (3W), DD -65.9%, fees $16.71
- Medium: $7,558 (+202.3%), 4 trades (3W), DD -65.9%, fees $16.71  
- High: $8,150 (+226.0%), 4 trades (3W), DD -68.1%, fees $17.91

**ATOM/USDT:**
- Low: $1,195 (-52.2%), 1 trade (0W), DD -62.2%, fees $1.05
- Medium: $1,195 (-52.2%), 1 trade (0W), DD -62.2%, fees $1.05
- High: $1,150 (-54.0%), 1 trade (0W), DD -63.8%, fees $1.05

**LINK/USDC:**
- Low: $6,837 (+173.5%), 3 trades (3W), DD -34.2%, fees $6.39
- Medium: $6,837 (+173.5%), 3 trades (3W), DD -34.2%, fees $6.39
- High: $7,057 (+182.3%), 3 trades (3W), DD -34.3%, fees $7.09

**NEAR/USDT:**
- Low: $1,173 (-53.1%), 1 trade (0W), DD -69.7%, fees $1.04
- Medium: $1,173 (-53.1%), 1 trade (0W), DD -69.7%, fees $1.04
- High: $1,138 (-54.5%), 1 trade (0W), DD -70.5%, fees $1.04
