# AIT V14PM — Final Audit, End of Day 2026-07-04
_Author: Claude (Fable) | Package: fable-final-audit-2026-07-04 (110 files) | Method: claims verified in code/data, not summaries. Every number recomputed where possible._

## Verified deployed (all confirmed in the code itself)

- **GridModel v2.0** — `LAYER_FRACTIONS = [0.48, 0.32, 0.20]`, `MAX_LAYERS = 3`; engine sizes via `gm_layer_cost` at fill time only, so the migration is Rule-#34-clean by construction (open 4-layer deals unaffected; a would-be L4 request falls out of range → $0 → no order). With 3 layers, L3 = 20% clears the $10 minimum down to $50 allocations — the H-1 truncation hazard largely retires.
- **M-2** balance-fetch None guard; **M-4** GridModel-based freeze threshold; **P1b** average-layer capital freedom (consistent with MAX_LAYERS=3); **P3** score columns live in trades.csv (`dca_score, trade_score, trend_mult`, 119 rows, append-compatible).
- **D-1 closeout** — grid-decision JSON regenerated with true medians (ASTER G-A1: 92.1h relabeled mean → 17h median). Duration is now provably ~uniform across arms; the "faster grid" claim stays dead.
- **E-3a rerun is honest** — lookup failures now NULL (zero old-style (0, 50.0) defaults), real derivation set (n=2,395), held-out preserved. **My independent recompute confirms the verdict: H-ext fails.** Derivation top-vs-bottom quintile MAE gap +0.52 pts, held-out +0.25, versus the ≥2.0 bar. **E-4 parked is the correct pre-registered call**, and my registered prediction (moderate pass) was wrong. Coherent reading: the binary veto already truncates the extension tail at ~3 ATR, so within the admitted range the residual continuous signal is weak. Consequence worth stating plainly for Brett: **the "lower risk" half of the aggressive-tier goal currently has no active mechanism beyond the veto and grid geometry** — and G-SPLIT's DD is a hair above the old live grid's.

## Findings

**FA-1 ⛔ — V-4 is still not implemented. Third flag.**
`veto_clear` remains untouched — no trigger-condition inputs, no guard. The May-30 clear-gap bug (veto clears on a day the A2 condition is simultaneously true, opening a 1-day re-entry window at elevated prices — proven from GeeGee's own fixture numbers) has now survived: the R-blocker verdict (as V-4), the L4 review (as F-5, "the only remaining code action"), and this package. It is a one-guard-clause fix in the **live production veto**. It should be the first commit of tomorrow, and if there's a reason it keeps not shipping, that reason should be said out loud.

**FA-2 ⛔ — The architecture doc does not record the grid change. The single source of truth is behind production again.**
v1.12's changelog covers only the post-remediation fixes (M-2/M-4/H-1). It says nothing about: GridModel v2.0 / G-SPLIT replacing the 4-layer grid (the day's biggest production change), Part A veto deployment, Part B closure and its evidence, the grid-decision outcome, or E-4's parking. The doc still describes the 4-layer 40/24/20/16 grid in 9 places while production trades 48/32/20. This is precisely the C1-class "multiple truths" failure the whole discipline exists to prevent — recreated on the same day it was fixed elsewhere. Required: v1.13 pass recording all of today's decisions with their evidence links, §5.2 grid table rewritten from GridModel v2.0's self-test output, and the Brett-approval trail for the grid migration recorded (the deployment preceded any written approval in the record I have; if approval was given verbally, write it down).

**FA-3 — E-1 live columns never shipped (entry context + MAE).**
The runner has zero references to `ext_atr_at_entry` / `rsi_at_entry` / `max_adverse_pct`; trades.csv carries only the P3 score columns. With E-4 parked, the entry-context columns lose urgency — a defensible deferral **if made consciously; record it**. But `max_adverse_pct` has standing value independent of E-4 (it's the per-deal pain metric the score-validation loop and the F-4 selection lesson both need). Recommendation: ship the MAE column alone in the next migration window; defer the other two with a note.

**FA-4 ⚠ — The held-out NULL anomaly may touch the live veto. Diagnose before trusting Part A coverage.**
E-3a lookups failed 88% in the held-out window (Apr–Jul 2026) vs 29% in older derivation data — backwards, since recent daily candles should be the most complete. Most likely: recent `candles_daily` rows are missing or the join misses on recent timestamps. **The live veto reads daily RSI/SMA50/ATR from the same table.** If recent dailies are sparse, the production veto may be silently inert (fail-open) for some coins right now while appearing deployed. Check: for each active scanner coin, how many of the last 90 daily rows exist, and what fraction of live veto evaluations found valid inputs. One query; do it before assuming Part A's backtested coverage describes production.

**FA-5 — Prediction scorecard (mine), for the record.** Grid winner: wrong (picked FAT statics, SPLIT won). Chop ordering: half wrong (missed the bounce-monetization mechanism). H-ext: wrong (fails, not passes). Correctly called: the fat-L1 trap mechanism (hit TON), duration invariance across grids, and every instance where reported numbers violated arithmetic. The pattern is consistent: statics catch impossible claims and mechanisms; they don't pick winners. That division of labor is worth keeping.

## End-of-day state

| Component | State |
|---|---|
| Production grid | **G-SPLIT 48/32/20 (GridModel v2.0)** — verified in code; approval trail to be recorded (FA-2) |
| Part A veto | LIVE (A1+A2, ATR-normalized, side-resolved A3 available; A3 off in scanner) — coverage pending FA-4 check; V-4 bug outstanding (FA-1) |
| Part B layer gate | **Closed** — pivot gate tested, inert-by-construction bug found, redesigned, retested, retired on honest data |
| Trade score | P1, P1b, P2, P4, P5 + P3 logging deployed; validation loop begins accruing with score columns |
| E-4 dynamic sizing | **Parked** by pre-registered rule (H-ext failed both sets) |
| Docs | v1.12 partial — **v1.13 required** (FA-2) |
| Open items | FA-1 (V-4, one guard clause), FA-2 (v1.13), FA-3 (MAE column decision), FA-4 (daily-candle coverage check) |

Four open items, three of them small. The system ends the day on a better grid than it started with, chosen by a pre-registered rule on verified numbers, with the features that failed their tests retired instead of shipped. Hold that standard and the Hyperliquid track record will be built on ground that doesn't move.
