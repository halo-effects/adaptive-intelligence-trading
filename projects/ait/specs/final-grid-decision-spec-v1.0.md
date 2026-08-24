# Final Grid Decision — Test Run Spec v1.0
_Date: 2026-07-04 | Author: Claude (Fable) | Approver: Brett | Implementer: GeeGee_
_Purpose: one run, one table, one decision — the production grid for the single-product offering (no subscriber/aggressive split; Brett 2026-07-04). This spec consolidates and supersedes the arm list in Aggressive-Tier v1.1 §E-2; the v1.1 pipeline (E-1 columns, E-3a/E-3b, E-4 dynamic sizing) is unchanged and referenced below._
_Standing discipline: P-0 carries over in full — verified DD formula, per-candle equity CSVs, run-validity assertions, frozen edges, single commit, single run._

---

## 1. The decision being made

Which static grid ships as the production grid on Hyperliquid: the incumbent 4-layer, or a 3-layer fat-L1 variant. The winner also becomes the anchor for E-4's dynamic L1 sizing. **This is the final static-geometry menu** — no further grid variants are tested against these windows after this run (multiple-comparisons guardrail, agreed with Brett). The dynamic E-4 curve interpolates from the winner; it does not reopen the menu.

## 2. Arms (fixed menu — final)

| Arm | Grid | Layers | Veto | Status |
|---|---|---|---|---|
| G-A1 | 40/24/20/16 (current live) | 4 | ON | **reference — numbers exist** (L4 test package); do not rerun |
| G-A2 | 40/24/20 + 16% reserve | 3 | ON | **reference — numbers exist**; do not rerun |
| G-SPLIT | 48/32/20 | 3 | ON | **new run** |
| G-FAT | 56/24/20 | 3 | ON | **new run** |

New compute: 2 arms × 2 windows. Reuse of reference numbers is valid only if the frozen edges and commit match the L4-test run exactly; if anything drifted, rerun all four and say so.

## 3. Windows

1. **Frozen:** 2026-04-05 → 2026-07-03, 8-coin set, identical edges to the L4 test.
2. **2026 Q1 chop:** NEAR + INJ, identical edges to the L4 test.

## 4. Metrics (per arm × window, per coin and aggregate)

Total PnL (realized + end-of-window unrealized, decomposition shown), MaxDD per verified formula with per-coin distribution (median + worst), median deal duration, hours-at-depth (L3), deals completed, end-of-window state table, PnL per %median-DD. Equity-series CSV committed for TAO under both new arms.

**Run-validity assertions (abort + report on failure):** frozen edges byte-match the reference runs; G-SPLIT and G-FAT layer weights sum to 1.00; no arm deploys a 4th layer; per-deal MAE recorded (feeds §6).

## 5. Pre-registered decision rule

Applied in order, no post-hoc additions:

1. **Regime-cycle disqualifier:** an arm is eliminated if its Q1-chop total loss exceeds G-A1's by more than its frozen-window total-PnL gain over G-A1. (An arm that gives back its bull edge in one bad quarter is net-negative across a cycle.)
2. **Primary metric among survivors:** highest frozen-window **total PnL per % median DD**.
3. **Brett override (recorded if used):** may prefer lower worst-coin DD at a sacrifice of ≤5% on the primary metric — the public-track-record consideration. Note for the decision: the chop number of the winning grid is a *product* number — it is what a bad quarter looks like on the Hyperliquid public curve.

**Fable's registered predictions:** G-FAT wins frozen PnL and frozen PnL/%DD; G-SPLIT lands between G-A1 and G-FAT on every static metric; the chop window is the live question — I predict both 3-layer fat variants lose more than G-A2 there, G-FAT worst, and rule 1 is where G-FAT is most likely to die. If G-FAT survives rule 1, it should win.

## 6. E-3a rider (same batch — per Aggressive-Tier v1.1)

Run the entry-quality study under **both** candidate geometries (G-SPLIT and G-FAT): per simulated deal, log `ext_atr_at_entry`, `rsi_at_entry`, `max_adverse_pct`, duration, return. Derivation set = history to 2026-04-04; held-out = frozen window; decile analysis and the ≥2-point MAE-separation bar per v1.1. If the decile *ordering* differs between the two geometries, flag it — it shouldn't, and a difference is informative. E-4's `EXT_FULL`/`EXT_MIN` anchors derive from the winning grid's derivation-set deciles only.

## 7. Deliverables

1. `final-grid-decision-results.json` (all arms, both windows, per-coin)
2. TAO equity CSVs (G-SPLIT, G-FAT, both windows)
3. E-3a per-deal CSV + decile tables (derivation and held-out, both geometries)
4. **One-page decision table:** four arms × two windows on the §4 metrics, rule-1 verdicts marked, primary metric ranked — nothing else on the page
5. Predictions from §5 scored against outcomes

## 8. Out of scope / standing constraints

No L4 in any new arm. No changes to TP (3.0%), deviation (1.5%), veto config, or coin set — this isolates geometry. No additional static grids now or later against these windows. Migration of the winner is Rule #34-clean: new weights at deal-open only, open positions untouched; one GridModel constant set, one restart, architecture doc v1.12 records the decision and this spec as its evidence. E-1 columns ship in parallel per v1.1 so the live validation loop starts accumulating from day one under the new grid.
