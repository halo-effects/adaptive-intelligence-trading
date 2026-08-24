# Grid Decision — Corrected Package Verification (Addendum)
_Date: 2026-07-04 | Author: Claude (Fable) | For: Brett + GeeGee_
_Verifying: fable-grid-corrected-2026-07-04.zip against memo items D-1/D-2/D-3._

## Status of the three corrections

**D-3 — resolved.** Mean-vs-median DD clarified; ordering unchanged under both; corrected table uses median. Closed.

**D-1 — half-resolved.** The summary table now shows a uniform 17h median across all four arms — which, note, fully kills the "faster" claim: durations are *identical* across arms, exactly as the mechanics predict (55% of deals TP at the same price under every geometry). But the **results JSON still carries the old relabeled means** in G-A1/G-A2's per-coin `med_duration_h` fields (all 8 coins unchanged: ASTER 92.1, JUP 97.2, …). The artifact of record now contradicts its own corrections doc. Fix: regenerate the JSON with the fresh per-coin medians, or the mislabel gets rediscovered by whoever reads the artifact next year. Small, but artifacts of record don't get to be wrong.

**D-2 — delivered but unusable: the E-3a dataset has a 50% instrumentation failure.**
156 of 313 deals carry `ext_atr_at_entry = 0.00` **and** `rsi_at_entry = 50.0` — the same 156 rows. Entries don't land exactly on SMA50 with RSI exactly 50.0 half the time; these are **fallback defaults written when the daily-candle lookup failed** (timestamp misalignment, missing daily rows, or SMA50/ATR warm-up gaps — GeeGee to diagnose). Any decile analysis on this file puts lookup failures, not low-extension entries, in the bottom bucket. Additionally, the E-3a run covers only the frozen + chop windows (313 deals, 8 coins) — **there is no derivation set** (spec: full history to 2026-04-04, all scanner coins), so the frozen window, which the spec reserved as held-out, is currently the only data. Even with clean values, anchors derived from it would be fit on the evaluation window.

## The peek (in-sample, valid rows only — directional, not decision-grade)

On the 157 valid deals: top-vs-bottom extension quintile median-MAE gap is **+1.08 pts** (bar: ≥2.0), non-monotone in the middle quintiles, though duration rises with extension (5h → 15h median) and the tail (P90 MAE) is ugly everywhere above Q1. Verdict: **weak and unstable support for H-ext at this sample size — genuinely undecided**, which is precisely what a proper E-3a run exists to settle. Nobody should read this peek as either pass or fail.

## Consequences

1. **G-SPLIT approval stands unaffected.** The grid decision never depended on E-3a; my verification of the decision table itself is unchanged (win real, duration row now honest). Brett can sign whenever ready, contingent only on the D-1 JSON regeneration.
2. **E-4 is blocked** — no anchors can be derived until E-3a is rerun properly: (a) fix the entry-context computation and diagnose the 50% failure; (b) run over full available history (derivation set) per spec, all scanner coins; (c) frozen window stays held-out; (d) the ≥2 pt bar applies in both sets.
3. **Critical for the live E-1 migration:** the same lookup logic presumably ships in the runner. If it silently defaults in the sim, it will silently corrupt the live columns too. Requirement: on lookup failure, write **empty/NULL — never (0, 50.0)** — and increment a logged warning counter. A sizing rule fed by silent defaults would size L1 on noise while looking healthy.

## Action items (GeeGee)

1. Regenerate `final-grid-decision-results.json` with fresh per-coin duration medians (D-1 closeout).
2. Diagnose and fix the entry-context lookup; failure mode = NULL + warning, never defaults.
3. Rerun E-3a per spec: full-history derivation set, held-out frozen window, both decile tables, per-deal CSVs.
4. Confirm the E-1 live columns inherit the NULL-on-failure behavior before the trades.csv migration ships.
