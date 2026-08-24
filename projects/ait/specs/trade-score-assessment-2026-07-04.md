# Trade Score — Assessment & Remediation Spec
_Date: 2026-07-04 | Author: Claude (Fable) | For: GeeGee (via Brett)_
_Scope: the coin-selection scoring methodology in `v14_cycle_scanner.py` (dca_score / trade_score). All changes are scanner-side only — zero live-order-path risk, no engine restarts._
_Sources: v14_cycle_scanner.py (post-GridModel unification), 119 live V14PM trades (data/live/v14pm/trades.csv), cycle_scanner.json snapshot 2026-07-03, grid_model.py_

---

## 1. The score as implemented today

```
dca_score       = sim_realized_pnl × (1 − max_dd) × capital_freedom / 100
capital_freedom = 1 − open_layers / 24
trade_score     = dca_score × trend_multiplier      # ∈ [0.3, 1.5], least-squares slope over score_history
```

The sim now runs the actual GridModel grid (fixed fractions, linear deviation, TP 3.0%) over 7d/30d windows at a fixed $9,000 allocation. The historical three-grids-three-truths criticism is resolved as of 2026-07-03 — the sim finally scores the grid the bot trades. The findings below are what remains.

## 2. Findings

### S-1 (BUG, one line) — the trapped-capital penalty is dead
`capital_freedom = 1 − open_layers/24`: the /24 denominator is a **12-layer-era constant**. Under the 4-layer grid, open_layers ≤ 4, so the term ranges **[0.833, 1.0]** — a factor designed to span [0,1] now varies ≤17%. The score's penalty for coins that trap capital at depth has been silently neutered since the 4-layer migration. This is also a textbook argument for GridModel-as-single-source: a grid parameter was hiding outside the grid module.

### S-2 — the risk term measures the wrong window
`(1 − max_dd)` uses max drawdown *within the 7-day sim window*. Snapshot evidence: the 2026-07-03 top-10 shows DDs of 2.7–13.6% — over 7 days nearly everything looks safe, including a coin one week from a 40% correction. NEAR ranked #5 (score 7.3, DD 5.9%) **after** the blow-off/correction cycle that motivated the entire veto spec. The term discriminates almost nothing. (Deliberate design position: entry-timing risk belongs to the Part A veto, not the score — see §3 P2 note — so the fix is not to bolt overheat penalties onto the score but to make its risk terms measure *deal* risk.)

### S-3 — live outcomes vs. the score (119 deals)

| coin | deals | PnL | win% | median dur | L3+ |
|---|---|---|---|---|---|
| TAO | 17 | +$72.40 | 100% | 5.2h | 2 |
| ASTER | 10 | +$23.75 | 100% | 14.0h | 3 |
| INJ | 23 | +$19.84 | 91% | 8.9h | 7 |
| JTO | 13 | +$6.82 | 85% | 18.0h | 2 |
| ONDO | 2 | −$12.29 | 50% | **94.0h** | 1 |
| HYPE | 16 | −$18.97 | 75% | 11.6h | 3 |
| ENA | 5 | −$70.31 | 80% | 12.0h | 1 |

Overall: 85.7% wins, +$41.63 net; gross wins ≈ $143 vs. three tail losses ≈ −$101. Two readings, both true: (1) the ENA/HYPE outliers match the documented **manual force-close incidents** — their −34%/−20% returns are shapes the grid cannot produce naturally (no stop-loss exists; natural closes are +3% TPs). Native record ex-incidents ≈ +$142 with worst natural loss under $5 — the mechanical grid is vindicated. (2) The ONDO 94-hour median duration is a *natural* trapped-capital cost, and per S-1/S-2 the score is currently blind to exactly that.

Selection-quality signal: the 2026-07-03 snapshot top-10 (FET, ADA, ARB, JUP, NEAR, SUI, AVAX, UNI, FIL, AAVE) contains **none** of the three biggest live earners (TAO, ASTER, INJ). One snapshot vs. months of trades is not a fair comparison — which is precisely the problem: **nothing measures whether the score predicts outcomes.** It was backtested once, early, under the old geometric sim grid, and has not been validated since. It is currently an unfalsifiable model.

### S-4 — sim scale ≠ live scale
Sim allocation is $9,000; live 3-coin-tier allocations are ~$61, where the engine's $10 minimum notional truncates L4 entirely (audit H-1). Sim rankings therefore systematically overrate coins whose sim PnL depends on deep-layer rescue economics the live grid cannot currently execute.

## 3. Recommendations (ranked)

**P1 — Fix S-1.** `capital_freedom = 1 − open_layers / GM_MAX_LAYERS` (import `MAX_LAYERS` from GridModel; already imported in the scanner). Restores the designed [0,1] range.
*Acceptance: unit check — 4 open layers → freedom 0.0; 0 layers → 1.0. Regenerate cycle_scanner.json; deliver a top-10 before/after diff to Brett (reshuffling is expected and is the point; flag anything extreme).*

**P2 — Add a time-at-depth penalty.** The live pain is duration, not window-DD. Proposed: `dca_score ×= 1 / (1 + median_hours_at_L3plus / DEPTH_HALF_LIFE_H)` with `DEPTH_HALF_LIFE_H = 72` as a named constant; `median_hours_at_L3plus` computed from the sim's own deal records (data already produced). Scores the ONDO failure mode directly.
*Deliberate exclusion: no entry-risk term (distance-from-SMA50, RSI, etc.) inside the score — that is the veto's jurisdiction, and spec §4.4's veto>multiplier precedence exists to keep timing safety out of the scoring plane. Score = velocity quality; veto = timing safety.*
*Acceptance: unit test on a synthetic pair (same PnL, different depth-time) ranking the shallow-fast coin higher; constant named; two-round tuning cap per house rules.*

**P3 — Close the validation loop (highest long-term value).** (a) Log `trade_score` (and `dca_score`, `trend_mult`) at deal-open as new trades.csv columns — append-only compatible, stop-bot-first per Rule #29 for the header migration. (b) A monthly report script: score-decile at entry vs. realized outcome (PnL, duration, depth). This converts the score from folklore into a measurable model, and it is the measurement foundation the F2 realized-velocity-feedback spec needs anyway — P3 first, F2 second.
*Acceptance: columns present on new rows, old rows unaffected, row count preserved through migration; first report generated against the existing 119 trades using snapshot-nearest scores (imperfect, labeled as such) as the baseline.*

**P4 — Sim at live scale.** Parameterize `run_dca_sim`'s allocation to the current tier's per-coin allocation and model the $10 minimum notional (skip layers that can't clear it, as the live engine does). Coordinates with the H-1 allocation-floor decision — whichever way H-1 goes, sim and live must agree on which grid is being scored. At minimum, flag truncated grids in the JSON (`layers_executable: 3`).
*Acceptance: sim at a $61 allocation shows L4 never firing (matches live); at $9,000 results match current behavior within rounding.*

**P5 — Subtract funding from sim PnL** (audit finding #23, still open). Perp funding is a real carry cost the sim ignores; long-heavy coins with persistently positive funding are overstated. Funding history is already fetched for open positions; extend the fetch to scanner coins or apply a per-coin trailing-average rate.
*Acceptance: sim PnL for a high-positive-funding coin visibly reduced; report the score impact distribution.*

**Keep as-is:** hurdle rate (≥5.0), the least-squares trend multiplier (just fixed — let it accumulate history before touching it), the 20% per-coin cap, and the velocity-first philosophy. The live data genuinely vindicates fast-cycling selection (TAO: 17 deals, 100%, 5.2h median; INJ: 23 deals, 91%). The score's core idea is right; it needs its risk term un-broken (P1), one term it never had (P2), and a feedback loop so selection quality stops being a matter of opinion (P3).

## 4. Sequence & risk

All five items are scanner-side. P1 rides with the next scanner run (one line). P2+P4 are one spec touching `run_dca_sim` (one change, one regeneration, one diff report). P3 is one column migration (Rule #29 discipline) plus a report script. P5 rides with P3's data pass. No engine restarts anywhere; the only live-adjacent step is the trades.csv header migration in P3(a), done bot-stopped with a timestamped backup per Rules #2/#29.
