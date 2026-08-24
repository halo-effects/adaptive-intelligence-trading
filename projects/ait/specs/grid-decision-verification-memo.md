# Final Grid Decision — Verification Memo
_Date: 2026-07-04 | Author: Claude (Fable) | For: Brett (decision) + GeeGee (three corrections)_
_Package: fable-grid-decision-package-2026-07-04. Every number below recomputed by me from the raw JSON and equity CSVs._

## Verification result: the win is real; one headline is not

**Verified clean:** window edges byte-match the L4-test reference; G-A1/G-A2 equity CSVs are byte-identical to the reference package (reuse legitimate); my independent MaxDD recompute from the raw equity series matches the JSON to 0.01% on all arms (G-SPLIT 41.73% vs 41.72 reported on TAO, G-FAT 41.54 exact); per-coin totals sum to the reported aggregates; Rule-1 arithmetic checks out — all arms survive, trivially, since both new arms lost *less* than G-A1 in the chop.

**Corrected decision table (frozen window, my aggregation, uniform statistics):**

| Arm | Total PnL | Median DD | PnL/%DD | Duration |
|---|---|---|---|---|
| G-A1 (live) | $18,510 | 18.5% | 1,002 | *(see D-1)* |
| G-A2 | $17,393 | 17.0% | 1,024 | — |
| **G-SPLIT 48/32/20** | **$20,096** | 19.1% | **1,053** | — |
| G-FAT 56/24/20 | $17,742 | 18.9% | 940 | — |

Q1 chop totals: G-A1 −$4,819 | G-A2 −$3,585 | G-SPLIT −$4,187 | G-FAT −$4,452.

**G-SPLIT wins under the pre-registered rules** — highest frozen PnL (+8.6% over live), highest PnL/%DD, survives Rule 1 with room. The magnitudes of the PnL/%DD column differ slightly from GeeGee's summary (likely a different DD aggregation — see D-3), but the ordering is identical under both, so the outcome is robust.

## D-1 — The "dramatically faster (17h vs 46h)" claim is an artifact. Withdraw it.

Proof from the package's own bytes: G-A1's `med_duration_h` values are **identical on all 8 coins** to the reference package's `avg_duration_h` — the reference rows were copied and the field renamed. So the table's duration column compares **means** (G-A1/G-A2) against **medians** (G-SPLIT/G-FAT). Medians sit far below means on long-tailed deal durations, so most of the 46h→17h collapse is a statistic mismatch, not speed. Mechanically, layer weights barely move duration: L1-only deals (55% of all deals) TP at an identical price under every arm. Some real per-deal differences exist (fatter L1 slightly shifts post-L2 TP levels and deal sequencing), but they cannot be assessed until the column uses one statistic. **Fix: recompute median-of-deal-durations freshly for all four arms and republish the row.** The decision doesn't hinge on it — but the corrected table shouldn't carry a false headline into the architecture doc.

## D-2 — Claimed deliverables missing from the package

The E-3a per-deal CSVs ("generated" per the summary) are not in the zip, and neither are the chop-window TAO equity series (spec §7). E-3a is not optional bookkeeping — it is the input from which E-4's dynamic-sizing anchors derive, and per the spec's train/test discipline I need the derivation/held-out decile tables before any `EXT_FULL`/`EXT_MIN` constants are proposed. Ship them.

## D-3 — Publish the aggregation behind the summary's PnL/%DD figures
Minor, for reproducibility: my median-DD-based ratios rank identically but differ in magnitude from the summary's. State which DD statistic fed the summary so the one-page table is recomputable.

## Fable's predictions, scored — mostly wrong, and instructively

1. "G-FAT wins frozen PnL and PnL/%DD" — **wrong.** G-SPLIT won both. G-FAT was wrecked by exactly the path effect I feared but assigned to the wrong window: TON, *frozen* window, 7 deals vs 16–17 elsewhere — one oversized L1 into a decline trapped the slot early and it never recovered. The static per-deal edge (2.13% vs 1.99%) was real and irrelevant; one trap erased it.
2. "G-SPLIT lands between A1 and G-FAT on every metric" — **wrong.** It beat both. The L2 weight preserved enough averaging power to avoid G-FAT's traps while keeping most of the L1 upsize. Brett's instinct here beat my static analysis, plainly.
3. "Both fat variants lose more than A2 in the chop, G-FAT worst" — **half right** (both true) — "and more than A1" — **wrong.** Both beat A1 in the chop. The mechanism my statics missed: in a chop, bounces TP the L1-heavy deals, and a fatter L1 monetizes every bounce harder on the realized side, more than offsetting the similar trapped end-positions. The statics modeled the trap and ignored the bounce.
4. "Rule 1 is where G-FAT dies" — **wrong.** All survived.

The honest lesson, recorded for the record: the static framework correctly ordered per-deal economics and correctly identified the fat-L1 trap *mechanism*, but path effects determined which grid actually wins — which is precisely why the run existed and why registered predictions are worth the embarrassment.

## Decision framing for Brett

G-SPLIT is a legitimate winner: **+8.6% PnL at essentially the incumbent's drawdown (19.1% vs 18.5% median; worst-coin ~identical), better chop behavior than live, with L4 retired.** Two things to accept knowingly: (a) the 11-for-11 rescue layer is gone from production — deep deals now wait at L3; (b) the "lower risk" half of your goal is **not** achieved by this geometry — G-SPLIT's DD is a hair *higher* than live. Risk reduction was always assigned to E-4's extension-conditioned L1 sizing, which is blocked on the missing E-3a data (D-2). My recommendation: approve G-SPLIT contingent on D-1/D-2 corrections, migrate Rule-#34-clean (new weights at deal-open only, one GridModel constant set, one restart), and hold E-4 as the next gate. Architecture doc v1.12 records the decision, the corrected table, and this memo as its evidence trail.
