# AIT Roadmap — Q1 2026 (Late Feb → Mid March)

**Created:** 2026-02-26
**Last reviewed:** 2026-02-26
**Review cadence:** Daily

---

## Project 1: LLM Engine Configuration

**Goal:** Configure optimal model routing for different task types.
**Owner:** Brett (API key) + Gee Gee (config)
**Status:** 🟡 Blocked — waiting on Gemini API key

| Task | Owner | Status | Notes |
|------|-------|--------|-------|
| 1.1 Brett generates Gemini 2.5 Pro API key | Brett | ⬜ TODO | Google AI Studio account ready |
| 1.2 Configure Gemini 2.5 Pro as primary model | Gee Gee | ⬜ TODO | Research, coordination, reasoning |
| 1.3 Configure Claude Opus 4.6 for analytics/coding | Gee Gee | ✅ Done | Already connected and in use |
| 1.4 Configure Claude Sonnet 4.6 as lighter coding option | Gee Gee | ⬜ TODO | For sub-agent tasks where Opus is overkill |
| 1.5 Set up model routing rules | Gee Gee | ⬜ TODO | Default=Gemini, coding/analytics=Claude, sub-agents=Sonnet |
| 1.6 Test and validate model switching | Gee Gee | ⬜ TODO | Verify quality across task types |

**Dependencies:** 1.1 blocks all others.

---

## Project 2: AIT V13 Trading Bot Development

### 2A: Website Content Update for V13

**Goal:** Update product, pricing, and Wyckoff pages to reflect V13 (currently based on older versions).
**Owner:** Brett + Gee Gee (collaborative, step by step)
**Status:** ⬜ Not started

| Task | Owner | Status | Notes |
|------|-------|--------|-------|
| 2A.1 Audit product page (`docs/index.html`) | Together | ⬜ TODO | Identify outdated V12/V11 references |
| 2A.2 Audit pricing page | Together | ⬜ TODO | Verify tier structure matches V13 profiles |
| 2A.3 Audit Wyckoff page | Together | ⬜ TODO | Replace V12f results with V13 Run 4 data |
| 2A.4 Update Wyckoff backtest tables | Gee Gee | ⬜ TODO | HTML tables with ETH/BTC/SOL Run 4 results (already computed) |
| 2A.5 Review and update feature descriptions | Together | ⬜ TODO | Phase model, signals, scanner descriptions |
| 2A.6 Ensure CSS/design unchanged | Gee Gee | ⬜ TODO | Content only — no style changes |

**Note:** Wyckoff table data already computed (Run 4). Just needs HTML update.

---

### 2B: DCA Strategy Optimization for V13

**Goal:** Evolve DCA from spot-only single-direction to dual-track (long + short) with dynamic parameters and risk-profiled tiers.
**Owner:** Gee Gee (research/build) + Brett (review/approve)
**Status:** 🟡 Research phase complete — dual-track invalidated, long-only grinder tested
**Last updated:** 2026-02-27

| Task | Owner | Status | Notes |
|------|-------|--------|-------|
| **Baseline** | | | |
| 2B.1 Document current DCA settings per profile | Gee Gee | ✅ Done | `dca-optimization-baseline.md` — all profiles documented |
| 2B.2 Analyze current DCA P&L contribution | Gee Gee | ✅ Done | DCA contributes <1% of portfolio returns. Markup/shorts dominate. |
| 2B.3 Review V11/V12 dynamic DCA logic | Gee Gee | ✅ Done | ATR-based adaptive TP/deviation documented in baseline |
| **Dual-Track Design** | | | |
| 2B.4 Design dual-track DCA architecture | Gee Gee | ❌ Invalidated | Testing showed shorts LOSE during DCA — 79% of windows exit to MARKUP |
| 2B.5 Define transition behavior | Gee Gee | ❌ Invalidated | Dual-track unnecessary — DCA phases are structurally long-biased |
| 2B.6 Capital allocation model | Gee Gee | ✅ Done | **10% isolated capital pool** — only viable model (shared capital starves markup) |
| 2B.7 Risk offset analysis | Gee Gee | ✅ Done | Shorts during DCA phases provide negative value, not hedging benefit |
| **Dynamic Parameters** | | | |
| 2B.8 Design BB-based step size adjustment | Gee Gee | ⬜ TODO | Deprioritized — fixed params beat adaptive for 4/5 coins |
| 2B.9 Design volume/lot scaling by regime | Gee Gee | ⬜ TODO | Deprioritized — marginal impact vs phase classification |
| 2B.10 Risk-profile tier calibration | Gee Gee | ✅ Done | Per-coin optimal configs identified (see baseline doc) |
| **Testing** | | | |
| 2B.11 Build DCA backtest harness | Gee Gee | ✅ Done | `dca_phase_test.py`, `dca_long_sweep.py`, `dca_tf_compare.py`, `dca_clean_sweep.py` |
| 2B.12 Backtest single vs dual-track | Gee Gee | ✅ Done | Single (long-only) wins decisively |
| 2B.13 Parameter sweep (step size, TP, layers) | Gee Gee | ✅ Done | 12+ combos × 5 coins × 2 timeframes |
| 2B.14 Full lifecycle integration test | Gee Gee | ✅ Done | 3 approaches tested: force-close, shared capital, isolated capital |

**Key findings (2026-02-27):**
- **Dual-track invalidated** — shorts lose money during DCA phases (structural long bias)
- **1h candles >> 15m** — 1.4-3.1× better across all coins
- **Fixed params >> adaptive** — simpler and better for 4/5 coins
- **BTC is a DCA dead zone** — skip entirely
- **Isolated 10% capital** — only clean integration model (+1.3% additive, zero interference)
- **DCA grinder adds ~$79 on $10K over 5 months** — marginal value at current allocation
- **Phase classification is the bigger lever** — FLAT routing speed matters more than DCA param tuning
- **Test engine now 100% accurate** (CFGI bug fixed 2026-02-27) — all results above are post-fix

**Decision point:** Is DCA grinder integration worth the complexity for ~$79/5mo? Options:
1. Integrate with per-coin enable/disable (skip BTC) — low risk, low reward
2. Increase allocation beyond 10% — higher reward but risks markup engine
3. Defer until FLAT routing improves — more DCA windows = more grinder value
4. Skip DCA grinder entirely — focus on gate optimization (2C) for bigger ROI

---

### 2C: Gate Optimization & Coin Qualification

**Goal:** Validate transition gate accuracy across a qualified coin universe, optimize signal stack for broader coverage.
**Owner:** Gee Gee (research/build) + Brett (coin qualification review)
**Status:** ⬜ Not started

| Task | Owner | Status | Notes |
|------|-------|--------|-------|
| **Coin Qualification** | | | |
| 2C.1 Build 44-coin qualification matrix | Gee Gee | ⬜ TODO | Sector, market cap rank, utility, exchange depth, team/backing |
| 2C.2 Define qualification criteria | Together | ⬜ TODO | Not meme, 1+ full crypto cycle, real utility, deep liquidity, large cap, institutional backing |
| 2C.3 Classify by crypto sector | Gee Gee | ⬜ TODO | L1, L2, DeFi, Infrastructure, Exchange tokens, etc. |
| 2C.4 Score and rank coins | Gee Gee | ⬜ TODO | Composite qualification score |
| 2C.5 Select qualified universe (target: 15-25 coins) | Together | ⬜ TODO | Remove memes, low-cap, erratic coins |
| **Data Preparation** | | | |
| 2C.6 Backfill 1h candles for qualified coins | Gee Gee | ⬜ TODO | Minimum 2 years, ideally back to 2020 for deep warmup |
| 2C.7 Build daily candles + indicators | Gee Gee | ⬜ TODO | Full signal pipeline for each coin |
| 2C.8 Verify 2W StochRSI warmup adequacy | Gee Gee | ⬜ TODO | ~784 days needed — flag coins with insufficient history |
| **Gate Accuracy Testing** | | | |
| 2C.9 Run V13 phase backtest on all qualified coins | Gee Gee | ⬜ TODO | Oct 2020 → present (or max available) |
| 2C.10 Build gate accuracy matrix | Gee Gee | ⬜ TODO | Per coin: MARKUP gates (recall, precision, latency), MARKDOWN gates, TOP detection |
| 2C.11 Measure captured moves | Gee Gee | ⬜ TODO | % of major move up/down captured per successful gate |
| 2C.12 Catalog missed gates | Gee Gee | ⬜ TODO | Moves the system failed to enter — why? |
| 2C.13 Catalog failed gates | Gee Gee | ⬜ TODO | Entries that resulted in MARKUP_FAIL or MARKDOWN_FAIL — root cause analysis |
| **Optimization** | | | |
| 2C.14 Identify signal stack gaps | Gee Gee | ⬜ TODO | Common patterns in missed/failed gates |
| 2C.15 Test signal adjustments | Gee Gee | ⬜ TODO | Additional gates, threshold tuning, new indicators |
| 2C.16 Validate optimizations don't break existing coins | Gee Gee | ⬜ TODO | Regression test on ETH/BTC/SOL |
| **Leverage Assessment** | | | |
| **From V13 Gaps** | | | |
| 2C.17 Bias system trigger research (G1) | Gee Gee | ⬜ TODO | **3D candle death cross as bear trigger** — widely used by traders, sits between daily (chatters) and weekly (too slow). Build 3D candles, compute SMA50/200 cross + HH_HL/LH_LL streaks, test as bias flip signal. Also test across 17-coin universe. |
| 2C.18 Two-layer failure detector (G2) | Gee Gee | ⬜ TODO | Profit protection layer + loss limiter. Backtest all qualified coins |
| 2C.19 ROUTER refactor Phase 1 (G3) | Gee Gee | ✅ DONE | **v8→v1 refactor complete (2026-02-27).** FLAT→ROUTER rename, centralized `_router_evaluate()` + `_compute_router_signals()`. 100% verified identical to v8 (all 5 coins, $0 delta). Doc: `projects/ait-product/router-v1-refactor.md`. Next: Phase 2 (dynamic tier gates), Phase 3 (confidence scoring), Phase 4 (ROUTER→MARKUP direct path). |
| 2C.20 1W OB85 fallback timing (G7) | Gee Gee | ⬜ TODO | Test minimum 2W threshold before allowing fallback |
| 2C.21 DCA-to-phase transition smoothness (G8) | Gee Gee | ⬜ TODO | How DCA capital converts to markup/markdown tiers |
| **Leverage Assessment** | | | |
| **Leverage Assessment** | | | |
| 2C.22 Identify high-accuracy coin/gate combos | Gee Gee | ⬜ TODO | Candidates for light leverage (2-3x) |
| 2C.23 Backtest with light leverage | Gee Gee | ⬜ TODO | Risk/reward analysis |
| **Post-Testing Cleanup** | | | |
| 2C.24 Trim scanner to qualified coins only | Together | ⬜ TODO | Review Opportunity list on dashboard, minimize to tested universe |

**Key insight from Brett:** System works best on mature, consistent coins — not memes or hype-driven tokens. We want to capture large chunks of the middle of moves, not edge cases. High signal accuracy on qualified coins opens the door for light leverage.

---

### 2D: V13 Paper Bot Reset with Optimized Settings

**Goal:** Rerun live paper trading on ETH/SOL/LINK/XRP with optimized V13 settings from 2B and 2C.
**Owner:** Gee Gee + Brett
**Status:** 🔒 Blocked — depends on 2B + 2C completion

| Task | Owner | Status | Notes |
|------|-------|--------|-------|
| 2D.1 Finalize optimized V13 config | Together | ⬜ TODO | Merge DCA + gate optimizations |
| 2D.2 Run full backtest with new settings | Gee Gee | ⬜ TODO | All 4 coins, compare vs Run 4 baseline |
| 2D.3 Brett approves new settings | Brett | ⬜ TODO | Review backtest results |
| 2D.4 Reset paper bot state | Gee Gee | ⬜ TODO | Fresh start with new config |
| 2D.5 Deploy and monitor | Gee Gee | ⬜ TODO | First 48h close monitoring |
| 2D.6 Create V13 Scheduled Task | Brett | ⬜ TODO | Needs elevated PowerShell |

---

### 2E: V14 DCA-Only Engine (NEW — 2026-02-28)

**Goal:** Replace V13's lump-sum tier execution with continuous DCA grids, using the same ROUTER v2 signal stack for direction.
**Owner:** Gee Gee (build) + Brett (review/approve)
**Status:** 🟡 v0.1 built, structural issues identified
**Spec:** `projects/ait-product/v14-dca-architecture.md`

**Pivot rationale:** V13 ROUTER v2 combined backtest showed only +2.6% improvement — lump-sum execution punishes timing errors that our signal stack can't avoid (20-50 day windows). Brett proposed DCA-only: same brain, gradual execution. "Roughly right" becomes strength, not weakness.

| Task | Owner | Status | Notes |
|------|-------|--------|-------|
| 2E.1 Clone V13 ROUTER v2 as V14 base | Gee Gee | ✅ Done | `v14_dca_engine.py` |
| 2E.2 Architecture spec | Gee Gee | ✅ Done | `v14-dca-architecture.md` |
| 2E.3 V14 v0.1 first run | Gee Gee | ✅ Done | -5.7% — structural issues (phase stickiness, capital utilization) |
| 2E.4 Fix phase stickiness | Gee Gee | ⬜ TODO | Remove ranging exit from DCA, conviction-only switches |
| 2E.5 Tune capital utilization | Gee Gee | ⬜ TODO | Larger base orders, more aggressive layers |
| 2E.6 DCA short grid optimization | Gee Gee | ⬜ TODO | Ensure shorts persist through bear phases |
| 2E.7 Backtest vs V13 baseline | Gee Gee | ⬜ TODO | Same coins, same period, head-to-head |
| 2E.8 Parameter sweep (if needed) | Gee Gee | ⬜ TODO | TP, deviation, layers, capital % |
| 2E.9 Brett review and approval | Brett | ⬜ TODO | Review backtest results |
| 2E.10 Paper bot deployment | Gee Gee | ⬜ TODO | Alongside or replacing V13 paper bot |

**Dependencies:** Builds on all V13 research (2B, 2C). V13 paper bot continues running as baseline.

---

## Execution Order & Dependencies

```
Project 1 (LLM Config) ──────────────────────── Independent, Brett-blocked
    │
Project 2A (Website) ────────────────────────── Independent, collaborative
    │
Project 2B (DCA Optimization) ───┐
                                 ├──→ Project 2D (Paper Bot Reset)
Project 2C (Gate Optimization) ──┘
```

**Recommended sequence:**
1. **Now:** Start 2C.1-2C.4 (coin qualification matrix) — research task, no code needed
2. **Now:** Start 2B.1-2B.3 (baseline documentation) — document what exists
3. **When Brett has time:** 2A (website review together)
4. **When Gemini key ready:** Project 1
5. **After 2B + 2C complete:** 2D (paper bot reset)

---

## V13 Gaps to Address (from 2026-02-26 testing)

These should be folded into 2B/2C workstreams or tracked separately:

| # | Gap | Priority | Relates To |
|---|-----|----------|-----------|
| G1 | Bias system trigger — **Weekly CFGI RSI(7) < 40 selected as bear-OFF** (2026-02-27). Bear-ON still uses engine top signals. | High | 2C |
| G2 | Two-layer failure detector (exit while profitable, not at -25%) | High | 2B |
| G3 | FLAT phase optimization — HVF fast-track tested, **breaks SOL universally**. No universal filter found. Wyckoff sequences needed. | Medium | 2C |
| G4 | Correlation-aware portfolio sizing (all coins same direction = concentrated risk) | Medium | Future project |
| G5 | Profit protection on markup/short positions (trailing or partial exits) | Medium | Future project |
| G6 | Paper bot Scheduled Task + auto-restart | ✅ Ready | Brett (elevated PS — now) |
| G7 | 1W OB85 fallback timing (sometimes fires early) | Low | 2C |
| G8 | DCA-to-phase transition smoothness | Low | 2B |

---

## Open Items & Blockers

| Item | Owner | Blocking |
|------|-------|----------|
| Gemini API key | Brett | Project 1 |
| V13 Scheduled Task (elevated PS) | Brett | Bot resilience |
| Aster live bot down (no status.json) | Brett | Monitoring |
| V12f paper bot down (no status.json) | Brett | Monitoring |
| Dashboard sync task intermittent | Brett | Dashboard freshness |

---

## Daily Review Template

```
Date: YYYY-MM-DD
Progress since last review:
- 

Blockers:
- 

Priority for today:
- 

Decisions needed:
- 
```
