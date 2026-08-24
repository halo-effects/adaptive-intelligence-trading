# Signal-Aware Deployment — Go/No-Go & Implementation Plan (rev. 2)
_Date: 2026-07-04 | Author: Claude (Fable) | For: GeeGee (via Brett)_
_Supersedes: Signal-Gating_Go-No-Go_2026-07-04 (rev. 1). Changes: folds in the signal-confidence review — B1 phantom-detector finding, B2 repairs, A2 ATR normalization — and converts everything into numbered tasks with acceptance criteria._
_References: signal-aware-deployment.md v1.0, gate_model.py, _gate_backtest_1h.py, test_hvf_daily.py, resample_daily.py, audit findings H-1/M-5/L-2/L-5_

---

## Decision summary

| Feature | Decision | Gate |
|---|---|---|
| **Part A — Entry Veto** (selector level) | **Conditional GO** | Tasks G-1…G-5 complete → Brett approval → 2 restarts (scanner, then runner) |
| **Part B — Layer Gate** (grid level, L3/L4) | **NO-GO on current evidence** | B1 fork resolved (G-6) → harness brought to §8 standard (G-7) → backtest passes with anchors asserted → Brett approval → 1 engine restart |

Part A matches Brett's "benign mute" framing exactly: it only blocks *new* T1/rotation/overflow entries; worst case is opportunity cost; fully reversible by removing the filter. Part B changes when L3/L4 fire on live positions (including currently open ones, per spec §5.4) and is the one feature the spec itself made backtest-gated. The current backtest cannot authorize it — see §3.

Precondition for both, sequenced with this work: the **H-1 allocation-floor decision** from the 2026-07-04 audit. Gating when L4 fires is meaningless at allocations where L4 cannot clear the $10 minimum notional at all.

---

## §1 — Finding: spec B1 cites a detector that does not exist

Spec §5.2 B1 requires "HVF **flush** signal (`test_hvf_daily`), then ≥ STALL_N 1h candles with no new low." `test_hvf_daily.py` actually computes: harmonic ABCD patterns (40%), volume *compression* (30%), price-range *compression* (30%) — a pre-breakout **squeeze** detector. A capitulation flush (volume expansion on a wide-range down-bar) is its near-opposite, and no flush primitive exists anywhere in the stack (verified by full-module grep). This is almost certainly why the harness tested stall-only B1: there was nothing to call.

Consequence: **B1 as spec'd is unimplementable without new code**, and the spec's "no new indicators" principle collides with its own citation. One of them must be amended explicitly — not worked around silently.

Resolution paths, in the order to try them:

1. **(b-test) Adversarial test of stall-only B1** — run the harness's stall-only gate against NEAR's June 6–12 waterfall leg and count L3/L4 fills admitted mid-leg. One afternoon. If zero-or-defensible → amend spec to v1.1 (B1 = stall-only) and skip new code entirely. If it admits fills inside the leg → (b) is dead, proceed to 2.
2. **(a) Build the flush primitive.** The spec already defines the short-side climax bar ("top-decile 1h volume × range within lookback"); mirror it long-side (climax down-bar), ~20 lines over raw 1h candles, lives in GateModel as a pure function. Amend the spec principle to acknowledge one new primitive, deliberately.
3. **(c) Drop B1, rely on B2 alone** — fallback only if (a)'s primitive proves noisy in backtest; the spec's documented-asymmetry clause blesses evidence-set reduction over invented detection.

## §2 — B2 and A2 repairs (spec v1.1 content)

- **B2 (StochRSI K↑D, 1h): restore the higher-low requirement** the harness dropped — it is the anti-noise anchor. **Adopt the harness's `K < 40` filter into the spec** as a named GateModel constant (`GATE_K_MAX = 40`): a cross at K=75 is not exhaustion evidence, and this condition should be spec, not harness folklore. Optional backtest arm: 4h StochRSI variant (existing indicator, new timeframe — permitted).
- **A2 (extension veto): normalize by ATR%, not a fixed 25%.** `candles_daily` already carries `atr_pct` (via `resample_daily`). Fixed 25% is volatility-blind — it over-vetoes high-vol coins (TAO trades 25% from SMA50 in healthy conditions) and under-vetoes low-vol ones. Replace with `close > SMA50 + EXT_ATR_MULT × ATR14` (long side; mirrored short), `EXT_ATR_MULT` a named constant calibrated in the same backtest. Zero new indicators; a re-parameterization of an existing condition using an existing column.
- **A3 (divergence): side-resolve the wiring** (audit M-5) — long veto consumes *bearish* divergence only, short veto *bullish* only, with an assertion at the GateModel boundary. The harness hardcoded `has_fresh_divergence=False`, so A3 has never been exercised in any arm; it must be live in the re-run.
- **Threshold honesty:** RSI 78/22, CALM 4d, RETRACE 25%, STALL 3, COOLDOWN 4h are all single-anchor (NEAR) calibrations. They earn confidence only through §8 run properly. Tuning discipline per spec: named constants only, two rounds maximum, then design questions return to Brett.
- **Parked for v1.2 (do not implement now): funding rate** as veto confirmation / exhaustion evidence. Positioning signal, orthogonal to the price-derived stack, data already fetched every 8h per open position — but it enters only after Part A has live data so its contribution is measurable. Out of scope for this engagement; recorded so it isn't reinvented.

## §3 — Why the current backtest cannot authorize Part B

Verified against `_gate_backtest_1h.py` line by line:

| Gap | Spec §8 requirement | Harness reality |
|---|---|---|
| B1 | HVF flush → stall | stall only (see §1) |
| B2 | higher-low AND K↑D | K↑D + K<40, no higher-low |
| A3 | divergence trigger live | hardcoded False — never exercised |
| Anchors | NEAR clear at ~1.80 basing (not 2.40); zero gated fills June 6–12 pre-stabilization | neither asserted anywhere |
| Windows | blow-off / chop (≤10% giveback) / continuation-fakeout, plus mirrored short-regime set | one undifferentiated lookback per coin; side hardcoded "long" |
| Artifact | results of record | `gate-backtest-results-1h.json` not in package |
| Scale | grid as actually run | $10K sim allocation; live allocations truncate L4 (H-1) |

The tested gate is looser than the specified gate; whatever numbers it produced describe a different strategy than the spec ships. This is the audit-C1 failure class (one implementation, one truth) recreated at the signal layer, and it is the specific reason for the NO-GO — not the idea, the evidence.

---

## §4 — Task list

**Phase G-A (Part A path — this week):**

- **G-1 — NEAR fixture self-test in GateModel** (spec §6, audit L-2). Fixture from `candles_daily` NEAR May–Jul 2026. Asserts: veto triggers late May; does NOT clear at ~2.40 first-RSI-cooldown; clears during late-June ~1.80 basing. Include the L-5 edge (C2 retrace when extreme sits on the wrong side of SMA50 — currently skips silently; decide and encode intended behavior). *Acceptance: fixture test green in `gate_model.self_test()`.*
- **G-2 — A2 ATR normalization** per §2. *Acceptance: unit test with a high-vol and low-vol synthetic pair showing the fixed-25% misclassification resolved; constant named and documented.*
- **G-3 — A3 side-resolved wiring + boundary assertion** (audit M-5). *Acceptance: unit test proving a bullish divergence cannot veto a long entry.*
- **G-4 — Precedence order in selector code path** (spec §4.4): veto filter executes before trend-multiplier scoring in `rebalance_daily`, `_rotate_after_tp`, overflow candidacy — one flag, three consumers, single source (scanner JSON `veto:{...}`). *Acceptance: code-order inspection + a test where a vetoed coin with the highest adjusted score is excluded from all three paths.*
- **G-5 — Part A results artifact**: re-run veto-only arm post G-1/G-2/G-3, save JSON to specs/, one-page summary to Brett. *Acceptance: artifact committed; Brett approval recorded.*
- **⛔ GATE A:** Brett approval → scanner restart (writes veto blocks) → runner restart (consumes filters). Telegram veto ON/OFF observability per spec §9 verified on first live veto.

**Phase G-B (Part B path — next week, honestly reached):**

- **G-6 — B1 fork resolution** per §1: run the (b-test); report fills-admitted count on the NEAR June 6–12 leg to Brett with the chart; Brett picks (a)/(b)/(c). *Acceptance: decision recorded in spec v1.1 changelog.*
- **G-7 — Harness to §8 standard**: chosen B1 + restored-higher-low B2 + live A3; window segmentation (three long-regime cases + mirrored short-regime set on 2025 bear legs); both NEAR anchors asserted in code; four arms; results JSON committed. Sim allocation parameterized to the live tier with $10 min notional modeled (coordinates with H-1 resolution). *Acceptance: §8 criteria computable from the output; anchors green.*
- **G-8 — Part B deploy** on §8 pass + Brett approval: engine restart; first gated deferral and first gated fill manually verified with evidence logged; per-deferral Telegram per spec §9. Short-side code paths remain built-but-dormant until F3.
- **⛔ GATE B:** consolidated report.

**Out of scope:** funding-rate input (v1.2, parked); any new indicator beyond the §1(a) flush primitive if selected; gating L1/L2 or any exit; any change to layer sizes/TP/deviation/max-layers; force-closes (Rule #34).

---

_Provenance note, unchanged from rev. 1: every claim here derives from files read directly in this session; the conclusions were rebuilt from code after two pre-written documents of unknown provenance were found and deleted. Where this document overlaps anything previously drafted elsewhere, the code is the common source._
