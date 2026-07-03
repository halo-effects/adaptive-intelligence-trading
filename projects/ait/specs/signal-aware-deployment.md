# Signal-Aware Deployment — Overheat/Oversold Entry Veto + Signal-Gated Layer Deployment
_Version: 1.0 | Date: 2026-07-03 | Status: SPEC — pending backtest validation, then approval (Hard Rule #21)_
_Applies symmetrically to LONG_DCA and SHORT_DCA regimes._
_References: V14PM_SYSTEM_ARCHITECTURE.md §4.4/§4.5/§5, implementation-handoff-prompt.md rev. 3 (GridModel, D-GRID d),
overflow-entry-v2-soft-ceiling.md v1.1, AIT_V14PM_Audit_Report_2026-07-03.md (findings C1, M5)_

---

## 1. Problem Statement

### 1.1 The two failure points (NEAR, Dec 2025 – Jul 2026 — canonical case study)

NEAR ran ~1.45 → 3.00 (late May – early June 2026), printed daily RSI > 80 with a flagged
bearish divergence at the top, then corrected ~40% to a ~1.80 base. Nearly every coin in the
actively traded universe shows the same shape in this window. Two independent system failures
occur on this chart:

**Failure 1 — the selector buys the blow-off.** The DCA cycle scanner's 7d/30d windows scored
NEAR *highest* precisely at the top: a vertical run produces fast simulated cycles, high
realized PnL, and high capital freedom. The trend multiplier (once fixed per audit M5)
*amplifies* the score of an accelerating coin. The intelligence layer, working exactly as
designed, promotes the most vertical chart on the board at its most dangerous moment.
Momentum scoring has no overheat governor.

**Failure 2 — the grid fills its full depth into the first 6% of a 40% move.** Layer triggers
are pure price deviation (1.5% × layer count from average entry). All four layers fire within
roughly the first 5–6% of a correction; the position then rides the remaining 15–35% fully
committed. Entry at 100 → correction to 75: mechanical grid averages 98.3 and needs a **+35%
bounce** from the low to TP; layers placed at stabilization points instead (~100/90/80/76)
average ~88.7 and need **+20%**. The difference is weeks-to-months of trapped capital and the
corresponding unrealized-drawdown display on the public dashboard.

The deviation trigger carries zero information about whether a dip is a wiggle or a waterfall.
The overheat information needed to avoid both failures is **already computed** by the existing
signal stack (RSI, StochRSI + divergence flags, 2D detectors in `HybridDetector2D` and
`_steve_3check`) — but it is consumed only at the **macro/cycle scale** by the regime system.
No component consumes daily-scale per-coin exhaustion signals at the selection or layer level.

### 1.2 The three-scale architecture this spec completes

| Scale | Question | Mechanism | Status |
|-------|----------|-----------|--------|
| Macro (weeks) | Is the *cycle* topping/bottoming? | Regime gate + operator APPROVE (§7.5) | ✅ exists |
| **Meso (daily)** | **Is *this coin* vertical right now?** | **Part A — Entry Veto (selector level)** | this spec |
| **Micro (hourly)** | **Is *this move* still running?** | **Part B — Signal-Gated L3/L4 (grid level)** | this spec |

Part A stops new grids from opening into a blow-off (long) or a capitulation flush (short).
Part B protects grids that legitimately opened earlier in the move from mechanically filling
to max depth while the move is still running. They cover different failure points and are
specified together because they share signals, a module, and a backtest.

---

## 2. Design Principles

> **Symmetry by construction.** Every trigger, clear condition, and gate is defined once in
> side-neutral terms ("extension against the grid's profit direction") and parameterized per
> side. A SHORT_DCA grid shorts rallies and TPs on declines; its dangers are the mirror image
> — entering a short into a vertical capitulation (the bounce zone), and adding short layers
> into a sustained squeeze. Where the signal stack lacks a true mirror (e.g., HVF is a
> flush detector), the asymmetry is documented, not improvised.

> **Veto and gate delay; they never accelerate.** Deviation thresholds remain a hard floor —
> no layer ever fires earlier than today. A veto never force-closes, down-ranks, or removes a
> coin; it only declines *new* deployment. Strictly conservative relative to current behavior.

> **Wrong-side cost must be opportunity cost only.** Under the front-loaded grid (D-GRID d,
> 40% L1), a false-positive gate means TP-ing on a smaller position; a false-positive veto
> means the next-ranked coin got the capital. Neither can produce a realized loss.

> **One implementation.** All conditions live in a shared `GateModel` consumed by the engine,
> the scanner simulation, and the selector — or this spec recreates audit finding C1 (three
> grids, three truths) at the signal layer.

> **No new indicators.** Every input already exists in `v13_signals.py`, `test_hvf_daily.py`,
> `_steve_3check.py`, `v13_router_engine_v2.py`, or `cfgi_client.py`. This spec adds routing
> and thresholds, not detection capability.

---

## 3. Side-Neutral Vocabulary

Used throughout; resolves per regime:

| Term | LONG_DCA grid | SHORT_DCA grid |
|------|---------------|----------------|
| **Adverse direction** (grid adds layers) | price falling | price rising |
| **Profit direction** (grid TPs) | price rising | price falling |
| **Overextension** (dangerous entry state) | vertical rally: RSI high, price ≫ SMA50, bearish divergence | vertical selloff: RSI low, price ≪ SMA50, bullish divergence |
| **Exhaustion** (safe-to-deepen evidence) | downmove stalling: flush + stabilization, higher-low, StochRSI K turns **up** | upmove stalling: blow-off + stall, lower-high, StochRSI K turns **down** |
| **New extreme** | new local high | new local low |
| **Mean reversion** | retrace down toward SMA50 | bounce up toward SMA50 |

---

## 4. Part A — Overheat/Oversold Entry Veto (selector level)

### 4.1 What it gates

A vetoed coin is blocked from: **T1 entries** (first layer of a new deal), **rotation
candidacy** (`_rotate_after_tp`), and **overflow candidacy** (overflow-entry-v2 §3.6).
A vetoed coin is NOT: removed from rankings, score-penalized, force-closed, or blocked from
adding layers to an *existing* position (that is Part B's jurisdiction) or from TP-ing.

Display: coin remains ranked with a paused badge — e.g. `NEAR  #2  ⏸ OVERHEATED (day 3)` /
`⏸ OVERSOLD (day 3)` in status.json and dashboard.

### 4.2 Trigger (veto ON) — evaluated daily per coin, from `candles_daily`

Veto fires when **any** of the following holds *in the adverse-entry sense for the
prospective grid's side*:

| # | Condition | LONG entry veto (overheat) | SHORT entry veto (oversold) | Default |
|---|-----------|---------------------------|------------------------------|---------|
| A1 | Daily RSI(14) extreme | RSI ≥ `RSI_HOT` | RSI ≤ `RSI_COLD` | 78 / 22 |
| A2 | Extension vs. mean | close ≥ SMA50 × (1 + `EXT_PCT`) | close ≤ SMA50 × (1 − `EXT_PCT`) | 25% |
| A3 | Fresh 2D divergence (≤ `DIV_AGE` days old) | bearish divergence (`HybridDetector2D`) | bullish divergence | 5 days |

Rationale per side: a LONG entry into A1–A3 buys a blow-off top (NEAR at 2.80). A SHORT entry
into the mirrored A1–A3 shorts a capitulation flush — the highest-probability violent-bounce
zone on the chart, which for a short grid is the falling knife.

### 4.3 Clear (veto OFF) — the clear condition matters as much as the trigger

The extreme reading fades quickly once the reversal starts (RSI drops below 78 fast on the way
down), but the *move* is still running — NEAR at 2.40 on June 10 was past A1 yet still a
falling knife. The veto therefore persists until **consolidation evidence**, all of:

| # | Condition | Side-neutral definition | Default |
|---|-----------|--------------------------|---------|
| C1 | No new extreme | ≥ `CALM_DAYS` daily candles without a new local extreme in the overextended direction | 4 days |
| C2 | Mean reversion begun | close has retraced ≥ `RETRACE_PCT` of the distance from the extreme toward SMA50 | 25% |
| C3 | Momentum normalized | daily RSI back inside [`RSI_COLD`+8, `RSI_HOT`−8] (hysteresis band) | [30, 70] |

Calibration anchor (must hold in backtest): on NEAR daily, the long-entry veto triggers in
late May 2026 and clears during the late-June basing near ~1.80 — **not** at 2.40 on the first
RSI cooldown.

**Anti-starvation guard:** grids monetize volatility, and post-blow-off chop is volatile. The
clear condition errs toward re-admission once structure stabilizes — it must not wait for a
confirmed new trend. If a vetoed coin remains blocked > `VETO_MAX_REVIEW` (default 21) days,
emit a Telegram review notice (information only; no auto-clear).

### 4.4 Precedence

**Veto > trend multiplier.** A coin failing the veto is excluded from T1/rotation/overflow
regardless of adjusted score. This is mandatory: audit Task 3.3 repairs the trend multiplier,
and a working multiplier *amplifies* exactly the vertical charts the veto exists to decline.
Without stated precedence, 3.3 re-opens the door this spec closes.

### 4.5 Placement

Computed in the daily scanner run (side-resolved for the current global regime), written into
`cycle_scanner.json` per coin as `veto: {active, side, reason, since, day_count}`; consumed by
`rebalance_daily` filtering, `_rotate_after_tp` candidate walk, and overflow candidate
selection (one flag, three consumers, single source).

---

## 5. Part B — Signal-Gated Layer Deployment (grid level)

### 5.1 Scope: L3 and L4 only

L1/L2 remain purely mechanical. Live data (audit §3.3): L1–L2 = 94 deals, 79% of native PnL,
median durations 2.4–14.6h — fast wiggle-fills that must not be slowed. L3–L4 is where time
concentrates (median 44–73h); gate exactly where the problem lives. This also minimizes the
parameter/curve-fitting surface.

### 5.2 Gate definition

A gated layer fires only when **both**:

1. **Deviation floor met** (unchanged, hard floor): adverse move from average entry ≥
   `SO_DEVIATION × layer_count`. The gate can only *delay* past this point, never pre-empt it.
2. **Exhaustion evidence** (side-resolved), at least one of:

| # | Evidence | LONG grid (adding into a decline) | SHORT grid (adding into a rally) | Default params |
|---|----------|-----------------------------------|----------------------------------|----------------|
| B1 | Flush/blow-off + stall | HVF flush signal (`test_hvf_daily`) followed by ≥ `STALL_N` 1h candles with no new low | Volume/range climax up-bar* followed by ≥ `STALL_N` 1h candles with no new high | STALL_N = 3 |
| B2 | Structure + momentum turn | 1h higher-low formed AND 1h StochRSI K crosses **up** through D | 1h lower-high formed AND 1h StochRSI K crosses **down** through D | StochRSI 14/14/3/3 |

*Documented asymmetry: HVF is a long-side flush detector with no packaged short mirror. The
short-side B1 uses a generic climax bar (top-decile 1h volume × range within lookback) + stall;
if that proves noisy in backtest, short-side relies on B2 alone. Do not invent a new indicator
to force symmetry — record the asymmetry and move on.*

3. **Cooldown between gated layers:** ≥ `GATE_COOLDOWN_H` (default 4) hours between L3 and L4
   fills, preventing both from firing on a single stabilization pocket mid-waterfall.

### 5.3 No max-wait override

If exhaustion never confirms, the layer never fires and the capital stays reserved in
`engine.capital`. This is correct behavior, not a stall: a max-wait fallback reintroduces
mechanical piling-in through the back door during exactly the sustained trends the gate exists
for. (System-level compensation: capital an un-deepened grid doesn't spend remains visible to
top-up accounting and, at max-depth-book moments, to overflow — velocity routes elsewhere.)

### 5.4 Interaction with the grid

Layer **sizes** are unchanged — GridModel fractions (40/24/20/16% of allocation) apply when
the layer fires. TP math unchanged. `unwinding` and orphan-TP behavior unchanged. Existing
positions opened pre-deployment: the gate applies to their *future* L3/L4 fills naturally (it
is an additional condition on the same code path), which is the desired behavior for the
currently open corrected positions.

### 5.5 Placement

Gate check inserted in `V14DCAEngine._long_dca_tick` / `_short_dca_tick` at the
`should_buy` decision for `long_layers >= 2` (i.e., the fill that would create L3+), calling
`GateModel.layer_gate_open(side, layer_idx, signals_1h, signals_daily)`. The scanner sim calls
the identical function so simulated and live grids stay one grid (C1 discipline).

---

## 6. GateModel Module (shared, like GridModel)

`trading/spot/engine/gate_model.py` — leaf module, zero engine/runner imports:

- All Part A trigger/clear parameters and Part B evidence parameters as named constants
  (single tuning surface): `RSI_HOT=78, RSI_COLD=22, EXT_PCT=0.25, DIV_AGE=5, CALM_DAYS=4,
  RETRACE_PCT=0.25, STALL_N=3, GATE_COOLDOWN_H=4, VETO_MAX_REVIEW=21`
- `entry_veto(side, daily_signals) -> VetoState(active, reason, since)`
- `veto_clear(side, daily_signals, veto_state) -> bool`
- `layer_gate_open(side, layer_idx, signals_1h, signals_daily, last_gated_fill_ts) -> (bool, reason)`
- Self-test reproducing the NEAR calibration case from fixture data (§4.3 anchor).

Consumers: scanner (Part A flag + sim Part B), live engine (Part B), runner selector paths
(Part A flag read from scanner JSON). One implementation, three consumers.

---

## 7. Interactions with Existing Systems

| System | Interaction |
|--------|-------------|
| Regime gate (§7.5) | Orthogonal and unchanged. Regime gate answers "may this coin trade at all"; veto answers "should it trade *now*". Both must pass for T1. Side for all GateModel calls = the coin's engine phase (which the regime gate already requires to match global for entries). |
| Trend multiplier (Task 3.3) | Veto takes precedence (§4.4). |
| Overflow v2 | Veto added to candidate exclusions in §3.6's walk (alongside held/regime-flagged/liquidity). |
| Zombie slots (§7.7) | Unchanged. A vetoed coin with an open maxed position that drops from approval zombifies normally. |
| Capital top-up (§7.6) | Unchanged; note that under D-GRID d top-up is safety-net-only, and gated-but-unfilled layers keep their reserve in `engine.capital` (no top-up demand). |
| Hard Rule #34 | Nothing in this spec closes, resizes, or force-exits anything, ever. |
| F3 (short-side live) | Part A/B **long-side** ships independently. Short-side code paths are implemented and unit-tested now (the engine's short tick exists), but exercise live only after F3 deploys shorts on Hyperliquid. |

---

## 8. Backtest Validation (required before live — the one feature so gated)

Test capital or not, this changes the *character* of the strategy (the 11-for-11 native L4
record was produced by mechanical firing), so acceptance is empirical.

**Harness:** engine-level replay from `candles.db` 1h data using GridModel (d) sizing, four
arms per window: mechanical, veto-only, gate-only, veto+gate.

**Long-regime windows (real data):**
1. **NEAR May–Jul 2026** (and ≥5 universe coins over the same window — the operator confirms
   the shape is universal): veto+gate must win **decisively** (net PnL and avg time-at-depth).
2. **Spring chop (Mar–Apr 2026)**: veto+gate must be within tolerance of mechanical
   (≤ 10% PnL giveback) — proves the anti-starvation clear condition and untouched L1/L2.
3. **Continuation fakeout window** (select a coin whose vertical run *continued*): veto+gate
   may lose only opportunity cost — zero realized-loss divergence from mechanical.

**Short-regime windows (simulated grids on historical data — no live short history exists):**
Mirror the three cases on bear-leg segments from the candle DB (e.g., 2025 correction windows
across the universe): short grids gated vs. mechanical through (1) a capitulation flush the
veto must decline to short into, (2) a grinding decline the gate must not starve, (3) a
breakdown continuation. Same acceptance shape, mirrored.

**Calibration anchors (hard):** §4.3 NEAR anchor holds; no Part B L3/L4 fill occurs on NEAR's
June 6–12 waterfall leg before a B1/B2 stabilization prints.

**Failure handling:** if any acceptance case fails, tune only the named GateModel constants
and re-run — no structural additions (added conditions = curve-fitting). Two tuning rounds
maximum before escalating design questions to Brett.

---

## 9. Observability

- Telegram: veto ON/OFF per coin (with reason and day count); each gated layer *deferral*
  (first occurrence per position, then daily summary — not per tick); each gated layer *fill*
  with the evidence that opened it.
- status.json: per-coin `veto` block (§4.5) and per-position `gated_layers_waiting: [3]`.
- Daily digest (audit F6): count of active vetoes by side, positions with deferred layers,
  oldest deferral age, veto max-review notices.
- Dashboard: the ⏸ badge and the "layer waiting for stabilization" state — this is the
  intelligence layer visibly earning its subscription; surface it.

## 10. Dependencies & Sequencing

1. GridModel deployed (handoff Task 1.2) — gate reuses its sizing and the scanner unification.
2. Task 3.3 (trend multiplier) — precedence rule lands with or before Part A.
3. F3 (short-side live) — gates *live* short-side exercise only; all short code paths and
   tests land now.
4. Sequencing: GateModel + unit tests → backtest program (§8) → Brett reviews results →
   long-side live deploy (scanner Part A first restart, engine Part B second restart) →
   short-side live activation rides with F3.

## 11. Out of Scope

- New indicators or data sources (existing stack only).
- Any change to layer sizes, TP, deviation floors, max layers, leverage.
- Auto-clearing a veto by timer (review notice only).
- Score penalties or ranking changes for vetoed coins (veto is binary and visible).
- Gating L1/L2, or gating exits/TPs (never).
- Force-closing anything (Rule #34).
