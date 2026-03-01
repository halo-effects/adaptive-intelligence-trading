# AIT Roadmap — Q1 2026 (Late Feb → Mid March)

**Created:** 2026-02-26
**Last reviewed:** 2026-02-28
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

## Project 2: AIT Trading System Development

### 2A: Website Content Update

**Goal:** Update product, pricing, and Wyckoff pages to reflect V13/V14 (currently based on older versions).
**Owner:** Brett + Gee Gee (collaborative)
**Status:** ⬜ Not started

| Task | Owner | Status | Notes |
|------|-------|--------|-------|
| 2A.1 Audit product page (`docs/index.html`) | Together | ⬜ TODO | Update for V14 DCA engine |
| 2A.2 Audit pricing page | Together | ⬜ TODO | Verify tier structure matches V14 profiles |
| 2A.3 Audit Wyckoff page | Together | ⬜ TODO | Replace old results with V14 data |
| 2A.4 Update Wyckoff backtest tables | Gee Gee | ⬜ TODO | V14 results across coin universe |
| 2A.5 Review and update feature descriptions | Together | ⬜ TODO | Phase model, ROUTER, DCA grids |
| 2A.6 Ensure CSS/design unchanged | Gee Gee | ⬜ TODO | Content only — no style changes |

---

### 2B: V13 Research & Testing (COMPLETE)

**Status:** ✅ Complete — research findings led to V14 pivot

**Summary of V13 research (Feb 25-28):**
- **ROUTER architecture designed and built** — centralized phase routing replacing ad-hoc transition logic
- **ROUTER v1**: 100% behavioral match with v8 baseline (verified $0 delta, all coins)
- **ROUTER v2**: Integrated top detection (OB93 arm → 2D divergence confirm, 35d timeout) + bottom conviction (3/4 score, 2W K≥5 gate, 3D death cross)
- **Combined backtest**: Only +2.6% improvement over baseline — lump-sum execution punishes timing errors
- **DCA dual-track invalidated** — shorts lose money during DCA phases (79% structural long bias)
- **Fixed params >> adaptive** — simpler and better for 4/5 coins
- **1h candles >> 15m** for DCA grinding
- **OB93 broken for tops** — 2W StochRSI never reaches 93 for ETH/BTC in this cycle
- **2D RSI bearish divergence** — 5/5 top coverage, 24% false rate, 0% effective false rate in MARKUP context
- **Bottom conviction stack locked** — 3/4 hybrid, 2W K≥5 gate, 3D death cross, close all shorts on fire
- **Bear-OFF signal**: Weekly CFGI RSI(7) < 40 (coin-specific)

**Key decision:** V13's lump-sum execution is fundamentally limited by signal timing uncertainty. Pivoted to V14 DCA-only execution with same ROUTER brain.

**V13 paper bot**: Still running. Equity $28,406 (+184%). All 4 coins in MARKDOWN tier 3 shorts. Serves as baseline comparison.

---

### 2C: V14 DCA Engine (COMPLETE — LIVE)

**Goal:** DCA-only execution engine using ROUTER v2 signal stack for direction.
**Owner:** Gee Gee (build) + Brett (review/approve)
**Status:** ✅ Live paper trading since 2026-02-28
**Spec:** `projects/ait-product/v14-test-plan.md`, `projects/ait-product/v14-dca-architecture.md`

| Task | Owner | Status | Notes |
|------|-------|--------|-------|
| 2C.1 Clone ROUTER v2 as V14 base | Gee Gee | ✅ Done | `v14_dca_engine.py` |
| 2C.2 Architecture spec | Gee Gee | ✅ Done | `v14-dca-architecture.md` |
| 2C.3 Fix phase stickiness (v0.1→v0.2) | Gee Gee | ✅ Done | Removed ranging exit, conviction-only switches |
| 2C.4 OB85 fallback analysis | Gee Gee | ✅ Done | Removed — causes SOL misfire. K<50 failsafe sufficient. |
| 2C.5 Conviction analysis | Gee Gee | ✅ Done | 3/4 kept. Problem was OB85, not conviction itself. |
| 2C.6 Grid mode: cycling vs accumulate | Gee Gee | ✅ Done | Cycling wins both coin sets. Trailing TP rejected. |
| 2C.7 Grid spacing: linear vs geometric | Gee Gee | ✅ Done | Linear wins (-8.7% worse for geometric) |
| 2C.8 Full parameter sweep | Gee Gee | ✅ Done | BO, Dev, Mult, Layers, TP, capital, leverage |
| 2C.9 Risk profiles defined | Brett+GG | ✅ Done | Low/Medium/High locked |
| 2C.10 15-coin universe evaluation | Gee Gee | ✅ Done | All coins ranked at 3 risk levels |
| 2C.11 Extended coin evaluation (30 Tier B/C) | Gee Gee | ✅ Done | All failed — strict filtering confirmed |
| 2C.12 Optimal portfolio selected | Brett+GG | ✅ Done | HBAR/ATOM/LINK/NEAR |
| 2C.13 Lifecycle wrapper built | Gee Gee | ✅ Done | `v14_lifecycle_engine.py` |
| 2C.14 Paper bot runner built | Gee Gee | ✅ Done | `run_v14_paper.py` |
| 2C.15 Backfill verified | Gee Gee | ✅ Done | $65,247 (+552%) matches standalone |
| 2C.16 Paper bot deployed | Brett+GG | ✅ Done | `V14PaperBot` scheduled task, live since 2026-02-28 |
| 2C.17 Dashboard built | Gee Gee | ✅ Done | `dashboardV14.html`, audited and fixed |
| 2C.18 Scanner built | Gee Gee | ✅ Done | 15 coins scored, ATOM 97/A+, HBAR 94/A+ |
| 2C.19 Sync script updated | Gee Gee | ✅ Done | V14 data + dashboard syncing to GitHub Pages |
| 2C.20 All files backed up to GitHub | Gee Gee | ✅ Done | 37 files, 18K lines committed |
| 2C.21 Add regime/trend to V14 runner | Gee Gee | ✅ Done | Dashboard header now shows market conditions |

**V14 Paper Bot Status (2026-02-28):**
- Equity: $70,767 (+608%) on $10K capital
- Profile: Medium (1.5x leverage)
- Coins: HBAR (SHORT_DCA), ATOM/LINK/NEAR (LONG_DCA)
- 363 deals, 97.5% win rate, 15.9% max drawdown

**V14 Locked Config:**
- BO=40%, Dev=2%, Mult=1.5x, Layers=10, TP=1.5%
- OB85 disabled, Conviction 3/4, Divergence timeout 35d
- Profiles: Low (1x), Medium (1.5x), High (1.5x + Dev=1.5% + L=12)

---

### 2D: Coin Scanner & Per-Coin Parameter Scoring

**Goal:** Build scoring model for V14 coin selection and per-coin parameter optimization.
**Owner:** Gee Gee (build) + Brett (review)
**Status:** ⬜ Not started

| Task | Owner | Status | Notes |
|------|-------|--------|-------|
| 2D.1 Define per-coin scoring metrics | Together | ⬜ TODO | Trade cycling rate, short PnL, DD, phase count, win rate |
| 2D.2 Per-coin parameter optimization | Gee Gee | ⬜ TODO | Different TP/deviation per coin based on volatility characteristics |
| 2D.3 Build automated scanner pipeline | Gee Gee | ⬜ TODO | Periodic re-scoring as new data arrives |
| 2D.4 Integrate scoring into dashboard | Gee Gee | ⬜ TODO | Live opportunity rankings with per-coin grades |

**Current scanner** (`_v14_scanner.py`) scores 15 coins on aggregate metrics. This project extends to per-coin parameter tuning.

---

### 2E: Losing Trade Incident Reports (NEXT)

**Goal:** Automated AI-powered analysis when a losing trade occurs. Classify, diagnose, recommend.
**Owner:** Gee Gee (build) + Brett (review)
**Status:** 🟡 In progress
**Design:** Cloud-migration-ready — JSON incident files, stateless analysis, works per-account.

| Task | Owner | Status | Notes |
|------|-------|--------|-------|
| 2E.1 Design incident report schema | Gee Gee | ⬜ TODO | JSON format: trade context, signals at entry/exit, classification, recommendation |
| 2E.2 Build incident trigger in runner | Gee Gee | ⬜ TODO | Fire on `pnl < 0` at trade close |
| 2E.3 Context snapshot capture | Gee Gee | ⬜ TODO | Signals, CFGI, phase, layers, max DD during trade, peer coin states |
| 2E.4 Loss classification taxonomy | Together | ⬜ TODO | Grid exhaustion, phase transition, conviction failure, etc. |
| 2E.5 AI analysis integration | Gee Gee | ⬜ TODO | LLM classifies and recommends (async, doesn't block trading) |
| 2E.6 Incident dashboard or report viewer | Gee Gee | ⬜ TODO | View incidents, patterns, aggregate stats |
| 2E.7 Pattern detection across incidents | Gee Gee | ⬜ TODO | Cluster by market conditions, coin, phase type |

**Architecture notes (cloud-ready):**
- Incident files are self-contained JSON — one file per event, no shared state
- Analysis is stateless — any LLM can process an incident file independently
- Works per-account in multi-tenant: incident includes account_id, strategy_id, coin
- Storage: local files now → S3/blob storage later
- Analysis: inline LLM call now → queue/worker pattern later

---

### 2F: AI-Governed Signal Override ("Common Sense Router")

**Goal:** AI layer that detects when rigid signal gates miss obvious market regime changes, using cross-coin consensus and opportunity cost tracking.
**Owner:** Brett + Gee Gee (design) → Gee Gee (build)
**Status:** ⬜ Not started — design phase, informed by 2E incident data

| Task | Owner | Status | Notes |
|------|-------|--------|-------|
| 2F.1 Define override conditions | Together | ⬜ TODO | Cross-coin consensus, opportunity cost threshold, time-in-phase |
| 2F.2 Opportunity cost tracking | Gee Gee | ⬜ TODO | Measure "left on table" when stuck in wrong direction |
| 2F.3 Cross-coin consensus scoring | Gee Gee | ⬜ TODO | If N-1 coins agree, flag the holdout |
| 2F.4 Confidence-based gate relaxation | Gee Gee | ⬜ TODO | Soften gates when multiple weak signals align |
| 2F.5 Human-in-the-loop vs auto modes | Together | ⬜ TODO | Define which overrides need approval vs auto-execute |
| 2F.6 Backtest override impact | Gee Gee | ⬜ TODO | Would HBAR have benefited? Measure false override rate |

**Design principles:**
- Conservative: override is a last resort, not a routine event
- Evidence-based: must have quantifiable metrics, not vibes
- Auditable: every override logged with full context and rationale
- Cloud-ready: override decisions are per-account, stateless evaluation

**Dependency:** Incident data from 2E informs which override conditions matter most.

---

### 2G: Dynamic Fib Extension Top Targets

**Goal:** Build dynamic Fibonacci extension-based price targets for top detection.
**Owner:** Gee Gee
**Status:** ⬜ Not started (Brett request msg #7912)

---

## Open Blockers

| Item | Owner | Blocking |
|------|-------|----------|
| Gemini API key | Brett | Project 1 |
| V13 Scheduled Task (elevated PS) | Brett | V13 bot resilience |
| Dashboard sync GitHub auth intermittent | Investigation | Dashboard freshness |

---

## Completed Milestones

| Date | Milestone |
|------|-----------|
| 2026-02-25 | V13 paper bot live (ETH/SOL/LINK/XRP) |
| 2026-02-26 | 100% test accuracy achieved (standalone = wrapper = paper bot) |
| 2026-02-26 | LH_LL gate for MARKDOWN, CFGI coin-specific normalization bug fixed |
| 2026-02-27 | ROUTER v1 built and verified (100% match to v8) |
| 2026-02-27 | Bear-OFF signal finalized: Weekly CFGI RSI(7) < 40 |
| 2026-02-27 | Bottom conviction stack locked (3/4 + 2W K≥5 + 3D DX) |
| 2026-02-27 | DCA dual-track invalidated, long-only grinder tested |
| 2026-02-27 | FLAT→ROUTER rename approved |
| 2026-02-28 | ROUTER v2 built (top detection + bottom conviction) |
| 2026-02-28 | OB93 broken for tops → 2D divergence as replacement |
| 2026-02-28 | V14 pivot: DCA-only execution with ROUTER brain |
| 2026-02-28 | V14 full parameter optimization complete |
| 2026-02-28 | 15-coin universe evaluated, HBAR/ATOM/LINK/NEAR selected |
| 2026-02-28 | V14 paper bot LIVE (+608% on backfill) |
| 2026-02-28 | V14 dashboard, scanner, sync deployed |
| 2026-02-28 | All V14 files backed up to GitHub (37 files, 18K lines) |
