# L4 Decision Test — Spec v1.0
_Date: 2026-07-04 | Author: Claude (Fable) | For: GeeGee | Approver: Brett_
_Purpose: produce the corrected, decision-grade comparison that answers one question: **what should L4 be — mechanical layer, removed (cash reserve), or pivot-gated crash insurance?** Output is a decision table for Brett, not a deployment._
_Supersedes as evidence: all prior G-7/options/bear-window tables (per Fable Verdict 2026-07-04, V-1/V-2/V-3)._

---

## 0. Prerequisite — P-0: DD reconciliation (blocking; nothing runs before this)

1. Verify the code computes MaxDD exactly as published: `equity = cash + qty × close` marked every 1h candle; `dd = (peak_equity − equity)/peak_equity`; `max_dd = max over window`. If the code differs, fix the code to the formula (not the formula to the code) and say what it was doing.
2. Commit a **per-candle equity series CSV** for at least one coin per arm (TAO minimum) so DD is independently recomputable. This is now a standing requirement for any table Brett decides from.
3. Sanity assertion, hard-coded into the harness output: for any two arms differing only in L4, `|MaxDD_a − MaxDD_b| ≤ L4_fraction + 0.02`. If the assertion fires, the run aborts and reports — it means the arms diverged somewhere other than L4 or DD is miscomputed. (The +0.02 tolerance covers post-TP timeline divergence.)
4. Recompute and republish the frozen-window table under the verified formula before adding the new arms.

## 1. The pivot gate (Arm A3 mechanics) — fill-on-confirmation

Replaces the disjoint-zone higher-low (Verdict V-3). All constants named, all in GateModel.

**States per layer (L3 and L4 only; L1/L2 always mechanical):**
- **DORMANT** → price touches the layer trigger level (`avg_entry` linear deviation, unchanged) → **ARMED**.
- **ARMED**: track `episode_low` = running min of 1h lows since arming. A **pivot candidate** is set at each new `episode_low`.
- **Pivot confirmed** when `PIVOT_CONFIRM_N = 3` consecutive candles print lows strictly above the candidate. A new lower low during counting resets the candidate and the count.
- On confirmation → **FILL** at next candle open (market), *even though price is above the trigger level*. This is the deliberate design trade: a slightly worse entry price in exchange for never catching the knife. The fill price delta vs trigger is a first-class output metric (§4), so the cost of confirmation is measured, not assumed.
- **Slippage bound:** if the confirmation fill price would exceed `trigger × (1 + PIVOT_MAX_SLIP_PCT)`, with `PIVOT_MAX_SLIP_PCT = 0.015` (one grid deviation), skip the fill and return to ARMED. Rationale: if price has recovered a full deviation above the trigger, the rescue layer is no longer buying meaningful depth.
- **Disarm** (back to DORMANT, no fill) when price recovers above the previous layer's fill price, or the deal TPs.
- **Cooldown:** `GATED_FILL_COOLDOWN_H = 4` between a gated L3 fill and L4 arming (retained from spec v1.0).

**Optional variant A3b** (run only if cheap): confirmation additionally requires a StochRSI K↑D cross with K < `GATE_K_MAX = 40` within the confirmation window. One extra arm, zero new constants.

**Self-test additions to GateModel:** (a) synthetic waterfall — staircase decline never confirms a pivot, zero fills; (b) synthetic capitulation-and-base — pivot confirms on the 3rd higher low, fill admitted, price delta recorded; (c) synthetic V-bounce — price recovers past slippage bound before confirmation, layer skipped; (d) reset case — lower low during counting restarts confirmation.

**Companion one-liner (rides along, separate commit):** Verdict V-4 — `veto_clear` returns False while any trigger condition evaluates true on the same candle; G-1 fixture gains a no-clear-while-trigger-true assertion.

## 2. Arms

| Arm | Grid | L4 semantics | Veto |
|---|---|---|---|
| A0 (reference) | 4-layer mechanical | mechanical | OFF |
| A1 (current live) | 4-layer mechanical | mechanical | ON |
| A2 (reserve variant) | **3-layer 40/24/20 + 16% held as cash** — honestly labeled; no gate code involved | absent | ON |
| A3 (pivot gate) | 4-layer; L1–L3 mechanical | pivot-gated per §1 | ON |
| A3b (optional) | as A3 | pivot + K↑D confirmation | ON |

A0 exists only to isolate the veto's contribution. A1 vs A2 vs A3 is the Brett decision set; all three run the production veto because that's deployment reality.

## 3. Windows

1. **Frozen window** 2026-04-05 → 2026-07-03 (bull-to-correction; includes NEAR/INJ waterfalls). 8-coin set unchanged.
2. **2026 Q1 chop** (NEAR + INJ minimum) — in-envelope stress window; this replaces Luna as the DD stress case per Brett's direction (Luna-class death spirals are a coin-selection problem, excluded by decision — recorded here).
3. **Bear-leg window** — only if 1h candle provenance is committed alongside results (exchange, fetch date, symbol mapping). No provenance, no window; unverifiable data doesn't enter a decision table again.

Same frozen edges, single commit, single run, per R-5 discipline.

## 4. Metrics (per arm × window, per coin AND aggregate)

- Total PnL = realized + end-of-window unrealized (never realized-only), with the decomposition shown
- MaxDD per verified formula + **per-coin DD distribution** (min/median/max — no lone averages; the DYDX lesson)
- Deals completed, median duration, hours-at-L3+
- **L4 fills admitted**, and for each: fill price delta vs trigger level (the confirmation cost, in % and $)
- Vetoed-entry count, gated-candle count
- PnL per %DD (Brett's stated objective function: DD weighted equal to PnL)

**Run-validity assertions (abort + report on failure):** P-0.3 bound holds between A1/A2; A3 admits ≥1 L4 fill in the chop window (a gate that never opens anywhere is V-3 again); A2's cash reserve is verifiably idle (16% never deployed).

## 5. Deliverables

1. `l4-decision-results.json` — full per-coin, per-arm, per-window data
2. Equity-series CSVs (≥ TAO for every arm, frozen window)
3. One-page decision table for Brett: A1 vs A2 vs A3 on Total PnL, MaxDD (median + worst coin), median deal duration, L4 fills + avg confirmation cost, PnL/%DD — one row per arm per window, nothing else
4. Updated `gate_model.py` self-tests green

## 6. Decision framework (for Brett, not auto-pass)

No thresholds decide this; the table does. The live priors to weigh against it: L4 is 11-for-11 live (rescues work), and un-rescued depth is slow (ONDO 94h median) — so A2 buys the calmest curve at the cost of slower recycling on deep deals; A3 keeps the rescue layer but pays a measured entry-price premium and will skip V-bounces; A1 is the status quo with the deepest DD. Commercial lens per Brett: DD weighs equal to or greater than PnL — subscribers churn on drawdowns, not on 93% vs 100% of backtest PnL.

## 7. Rules

Spec-first (this document is the spec; changes come back here before code). Constants: `PIVOT_CONFIRM_N`, `PIVOT_MAX_SLIP_PCT`, `GATED_FILL_COOLDOWN_H`, `GATE_K_MAX` — tuning limited to these, **two rounds maximum**, then design questions return to Brett. No live deployment from this work; output is the decision table. All prior gate tables are cited nowhere going forward.
