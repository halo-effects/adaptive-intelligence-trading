# AIT V14PM — Implementation Handoff (rev. 3.1 — same-day execution, D-GRID resolved)
_Date: 2026-07-03 | Prepared by: Claude (Fable) audit | For: implementing agent (via Brett)_
_Changes from rev. 2/3: **D-GRID resolved to option (d), the bull-phase grid**; rev. 3.1 adds the delivered Task 4.6 spec (`signal-aware-deployment.md`) — supersedes the audit report's P1 recommendation per operator's macro-regime decision (bottom is in; live capital designated as test capital). Paper-soak carve-out removed; grid change deploys live same-day with per-layer verification. Overflow spec updated to v1.1 (`L1_COST_FRACTION = 0.40`)._

---

## Part 1 — Package Contents

| # | Document | Role |
|---|----------|------|
| 1 | `AIT_V14PM_Audit_Report_2026-07-03.md` (rev. 2) | Findings of record: C1–C2, H1–H4, M1–M7, L1–L6; performance analysis; recommendations P0–P8; features F1–F6; cloud readiness. Note: the report's P1 grid recommendation is superseded by D-GRID (d) below. |
| 2 | `overflow-entry-v2-soft-ceiling.md` (v1.2) | Normative spec for finding H4; L1_COST_FRACTION = 0.40 per D-GRID (d); condition 8 defers overflow to same-rebalance normal (zombie-freed) entries |
| 3 | `implementation-handoff-prompt.md` (this file, rev. 3.1) | Inventory, resolved decisions, paste-ready agent prompt |
| 4 | `signal-aware-deployment.md` (v1.0) | Task 4.6 spec: overheat/oversold entry veto + signal-gated L3/L4 deployment, symmetric LONG/SHORT; backtest-gated before live |

Existing repo documents the agent must read: `V14PM_SYSTEM_ARCHITECTURE.md` (v1.10), `hard-rules.md`, `layer-reconstruction-capital-flow-zombie-slots.md`, `grid-optimization-tp3-4layer.md`.

## Part 2 — Decisions (RESOLVED by Brett, 2026-07-03)

| ID | Resolution |
|----|-----------|
| **D-GRID** | **(d) Bull-phase grid.** Layer sizes as fixed fractions of the coin's **allocated capital**: **L1 = 40%, L2 = 24%, L3 = 20%, L4 = 16%** (sum = 100%, fully self-funded — no top-up dependency). Deviation 1.5% linear from average entry (unchanged). TP 3.0% (unchanged). Max 4 layers (unchanged). Leverage 1.0x (unchanged). Rationale: macro assumption is bull-off-the-bottom; live data shows 79% of native PnL from L1–L2 cycles, so front-loading maximizes the dominant deal type (+33% profit per L1 cycle vs. deployed grid) while eliminating the 24%-of-slot that can never deploy today. Depth recovery essentially unchanged (~6.0% bounce from L4 vs. ~6.1%). The paper-era `min(order, capital × 0.3)` cap is REMOVED in live via the GridModel path. Live capital (~$400) is designated test capital; deploys live same-day. |
| **D-TIER** | Pending confirm at Gate 0 (default: confirm code's tier table; doc updated to match) |
| **D-RESERVE** | Pending confirm at Gate 0 (default: fold 10% reserve into active below $10K) |

Reference table for verification (entry 100, fills at 100 / 98.5 / 97.0 / 95.5):

| Layer | Fraction of allocation | Cumulative | Avg entry after fill | TP price | Bounce to TP from fill |
|-------|------------------------|------------|----------------------|----------|------------------------|
| L1 | 40% | 40% | 100.00 | 103.00 | +3.0% |
| L2 | 24% | 64% | 99.44 | 102.42 | +4.0% |
| L3 | 20% | 84% | 98.85 | 101.82 | +5.0% |
| L4 | 16% | 100% | 98.29 | 101.24 | +6.0% |

Pre-assigned defaults (no round-trips): Task 0.1 → implement the method; Task 3.1 → ledger `pnl_adjustment`.

---

## Part 3 — Paste-Ready Agent Prompt

───

You are implementing the full remediation plan from the 2026-07-03 external code audit of AIT V14PM — a **live production trading system** on Aster DEX Perps. The ~$400 live capital is designated **test capital** by the operator. Target: complete all phases **today**, gated only by Brett's approval between phases.

## Required Reading (in order, before touching any code)

1. `docs/tacit/hard-rules.md` — all 36 rules, non-negotiable. Most exercised today: #14 (never silence errors), #19 (pre-flight import test before every restart), #20 (one fix per restart), #21 (spec → approval → pre-flight → careful restart), #29 (trades.csv append-only; stop bot first), #33 (read spec before writing fix code), #34 (no forced closes).
2. `AIT_V14PM_Audit_Report_2026-07-03.md` — every task cites a finding ID; read the finding before implementing. NOTE: the report's P1 recommendation ("canonize the deployed grid") is **superseded** by the operator's D-GRID (d) resolution in this handoff — implement grid (d).
3. `overflow-entry-v2-soft-ceiling.md` v1.1 — Phase 2 spec; §3 normative; `L1_COST_FRACTION = 0.40`.
4. `V14PM_SYSTEM_ARCHITECTURE.md` v1.10 — you update it in Phase 1.

## Operating Constraints (same-day mode)

- **One fix per restart** (Rule #20). Each numbered task = one commit, one restart, one verification. Back-to-back once verified; no soak periods.
- **Pre-flight before every restart:** `python -c "from trading.spot.run_v14_portfolio_live_aster import V14PortfolioLiveAster; print('OK')"` (Rule #19).
- **Same-day verification standard:** after every restart — (1) startup Telegram received, (2) status.json updates within one cycle, (3) the task's acceptance check passes, (4) grep the last full cycle's log for ERROR/Traceback. Then proceed.
- **Grid-change extra verification (Task 1.2 step 3 only):** the first live fill at **each** layer depth is manually checked against expected size (40/24/20/16% of that coin's allocation, within lot-size rounding). Report each as it occurs; do not wait for all four before continuing other phases.
- **Passive backstop:** Rule #6's 24h trade review is scheduled for tomorrow; it does not block today.
- **All changes committed and pushed as you go** (Rule #25).
- **Stop-and-ask triggers:** a diff touching capital math outside the task's scope, order sizing not matching the D-GRID table, or more files than listed → stop, report, wait. Report incidental discoveries; do not fix ad hoc.
- **No forced closes, ever,** including "cleanup" during restarts (Rule #34). Open positions ride through every restart; positions opened under the old grid keep their existing layers — the new sizing applies to **new layers and new deals only**. Never resize, close, or "rebase" an open position to the new grid.
- **Decisions are made (Part 2).** Do not re-litigate D-GRID; confirm D-TIER/D-RESERVE defaults with Brett at Gate 0.

---

## PHASE 0 — Correctness fixes (~7 small isolated diffs)

**Task 0.1 — Implement missing method (audit C2).**
`run_v14_portfolio_live_aster.py` line ~2636 calls `self._prune_stale_coin_after_tp(sym, cs)` — undefined. Implement it: remove the coin from `active_allocations`/`reserve_allocations` if not in current rebalance targets and no open position (same semantics as `_do_rebalance`'s stale-cleanup block).
*Acceptance:* method exists (getattr check); simulated non-TP SELL path executes end-to-end in a dry-run harness without `AttributeError`.

**Task 0.2 — Fix dead liquidity filter (audit H1).**
Four edits: `_rotate_after_tp` ~2250 `self.client.exchange` → `self.client._exchange`; ~2251 `self._aster_symbol(...)` → `self.client._aster_symbol(...)`; `_do_rebalance` ~2709 and ~2722, same two fixes. Add Telegram alerts inside both `except` blocks — fail-open stays, silence does not (Rule #14).
*Acceptance:* rebalance/rotation log shows the filter executing with real volume numbers, no exception.

**Task 0.3 — Fix 1000-prefix double-descale (audit H2).**
`AsterPerpClient.create_market_buy` (~437–465): descale by 1000 only when the price came from the order object or `fetch_my_trades` (exchange units), never after the `fetch_ticker_price` fallback (already descaled). Mirror `create_market_sell`'s structure.
*Acceptance:* unit test, mocked responses, all three price sources × prefix/non-prefix coins.

**Task 0.4 — Trade CSV identity repair (audit M3).**
Stop bot → timestamped backup → `python -m trading.spot.reconcile_trades --fix-ids` → verify row count unchanged, deal_ids sequential → restart (Rules #2, #29). Then in `TradeTracker.load_existing()`: `self._deal_counter = max(len(self.trades), max_existing_deal_id)`.
*Acceptance:* unique monotonic deal_ids; row count identical to backup; no other field modified.

**Task 0.5 — Delete dead regime evaluator (audit M1).**
Remove `_evaluate_regime()` and its main-loop call; remove `REGIME_EVAL_HOUR` / `_regime_last_eval_date` if unreferenced. Do NOT touch `_check_coin_regime_conflict()`.
*Acceptance:* import test passes; per-coin conviction alert path intact.

**Task 0.6 — Startup attribute self-test (audit P7).**
After `__init__`: getattr-sweep every method referenced by `_execute_action`, `_handle_command`, `_do_rebalance`, `_rotate_after_tp`. Missing attribute → CRITICAL log + Telegram + exit before trading.
*Acceptance:* scratch-branch misspelling → bot refuses to start with a clear message; restore.

**Task 0.7 — Log the silent fallbacks (audit L2/P7).**
Replace the bare `except: pass` in `create_market_buy`'s trades-lookup fallback with a logged warning; add WARNING logs to every remaining fail-open handler.
*Acceptance:* zero bare `except: pass` remaining in the live runner.

**⛔ GATE 0:** Report per-task acceptance evidence (one line each) + Brett confirms D-TIER/D-RESERVE defaults. **Proceed on approval.**

---

## PHASE 1 — Grid deployment: bull-phase grid (D-GRID d) + GridModel (audit C1/F1)

**Task 1.1 — `GridModel` module.**
New `trading/spot/engine/grid_model.py` — single source of truth for grid geometry:
- `LAYER_FRACTIONS = [0.40, 0.24, 0.20, 0.16]` (of allocated capital; sum 1.00)
- `L1_COST_FRACTION = 0.40`
- `SO_DEVIATION = 0.015` (linear, from average entry — unchanged)
- `TP_PCT = 0.030`, `MAX_LAYERS = 4` (unchanged)
- Methods: `layer_cost(layer_idx, allocation)`, `cumulative_cost(n_layers, allocation)`, `tp_price(avg_entry)`, trigger-price helper.
Include a self-test that reproduces the Part 2 reference table exactly (avg entries 100.00 / 99.44 / 98.85 / 98.29 for unit fills at 100/98.5/97.0/95.5).
*Acceptance:* self-test green; module has zero imports from engine/runner (leaf dependency).

**Task 1.2 — Migrate call sites to GridModel, one restart each, in this order:**
1. `_remaining_grid_cost` / `_top_up_engine_capital` in the live runner. NOTE: under grid (d) a fully-allocated coin needs no top-up by construction; top-up remains as a safety net for legacy positions opened under the old grid and for allocation reductions. Deficit math must use GridModel.
2. `v14_cycle_scanner.run_dca_sim` — replace the sim's own BO/SO sizing AND its geometric price-step ladder with GridModel sizing and the engine's linear-deviation-from-avg-entry trigger, so the scanner finally simulates what the bot trades (closes the C1 three-grids gap). Regenerate `cycle_scanner.json`; sanity-check the new top-10 vs. previous — reshuffling is expected, flag anything extreme to Brett.
3. `v14_dca_engine._long_dca_tick` (and `_short_dca_tick` for symmetry) — **this is the live order-sizing change:**
   - Layer size = `GridModel.layer_cost(layer_idx, allocated_capital)` — sized from **allocation**, not from remaining capital.
   - **Remove the `order = min(order, self.capital * 0.3)` cap** (both tick functions).
   - Keep `engine.capital` as the funds gate only (`if order > self.capital: return`) — GAP-13's `capital = allocation − invested` reset makes this exactly sufficient for the 100%-sum grid.
   - The engine needs `allocated_capital` visible: pass it through the existing `cash_available` tick argument or a config field — smallest clean diff; state your choice.
   - Delete or implement the `live_mode` flag consistently (it must not remain write-only).
*Acceptance (per site):* site 1 — top-up log shows GridModel-derived deficits; site 2 — scanner runs clean, JSON regenerated, diff summary delivered; site 3 — unit test asserting emitted order sizes equal the Part 2 table for a $117 allocation across a scripted price path, THEN live restart, THEN the per-layer live verification (first real fill at each depth checked against 40/24/20/16% ± lot rounding). Open positions from the old grid must be untouched — verify their layer counts and TP orders survive the restart unchanged.

**Task 1.3 — Documentation reconciliation.**
`V14PM_SYSTEM_ARCHITECTURE.md`: §5.2/§5.4/§7.6 grid tables → the Part 2 reference table; §5.3 High profile row updated (BO column becomes the L1 fraction, note the fixed-fraction ladder); §7.2 tier table → match `EQUITY_TIER_CAPS` (per D-TIER); note top-up's new safety-net-only role; remove `live_mode` references per 1.2; version bump + changelog entry (Rule #18 — doc is single source of truth again by end of day). Also update `grid-optimization-tp3-4layer.md` with a pointer note that layer sizing was re-specified 2026-07-03 (D-GRID d).
*Acceptance:* doc grid table = GridModel self-test output, line for line.

**⛔ GATE 1:** Report + approval. Include the scanner top-10 diff and any live per-layer verifications observed so far.

---

## PHASE 2 — Overflow Entry v2 (audit H4)

Implement `overflow-entry-v2-soft-ceiling.md` v1.2 exactly; §3 normative. Non-negotiables: candidates from `_get_scanner_rankings()` (never the allocations dict); evaluation after `_top_up_engine_capital()`; soft ceiling = next tier's coin cap over **total** positions including zombies; one admission per rebalance day; fail-closed on scanner data missing/older than 24h; `L1_COST_FRACTION` imported from GridModel (= 0.40); delete the old unreachable overflow block.

Same-day test sequence: (1) unit tests — port the audit's enumeration harness; admissions fire in the all-maxed/all-approved/deposit scenario; blocked at ceiling, stale scanner, PAUSED/WIND_DOWN, mid-grid position, regime-flagged candidate, and same-rebalance normal entry (condition 8 — zombie-freed slot admits first, overflow defers); (2) dry-run harness demonstration of an admission end-to-end (engine creation, allocation seed, T1 gate pass) — the paper bot is NOT being updated in this engagement, so the harness substitutes for the paper deployment step in spec §7; (3) live deploy with pre-flight; verify the new status.json fields (`overflow_active`, `soft_ceiling`, `book_size`) and that the gate evaluates (log line) on the next rebalance. A real admission occurs only when conditions are met.
*Acceptance:* unit suite green; harness admission demonstrated; live gate evaluates without error.

**⛔ GATE 2:** Report + approval.

---

## PHASE 3 — Hygiene and hardening

- **Task 3.1 (M2):** Record spread-reject round-trips as ledger `pnl_adjustment` transactions so realized cash effects are never invisible to the ledger or deposit-detection math.
- **Task 3.2 (M4):** Fee audit — reconcile recorded fees ($0.18 total) vs. exchange fills for a 2-week sample; if CCXT under-reports, capture fees from `fetch_my_trades` at fill time. Report before changing recording.
- **Task 3.3 (M5):** Trend multiplier — least-squares slope over all snapshot points per window (replace endpoint delta); verify `score_history.json` accumulates one snapshot per day; add multiplier distribution to the scanner Telegram summary. **Elevated priority per operator:** in the assumed bull regime, momentum rotation between coins is a first-order return driver; this fix ranks with the grid change in expected impact.
- **Task 3.4 (P3/F4):** Force-close guards + `MIGRATE` command. CLOSE/CLOSEALL require typed confirmation quoting current unrealized PnL ("This will realize -$X.XX. Reply `CLOSE ENA CONFIRM` within 5 min"). `MIGRATE`: enter WIND_DOWN, report open positions + distance-to-TP, notify when flat. Runbook: upgrades use MIGRATE or state-preserving restart, never liquidation.
- **Task 3.5 (P7/F6):** Grid-freeze detector (open position + `layer_count < max` + `engine.capital == 0` for >1 cycle → Telegram) and daily silent-failure digest (swallowed exceptions by site, fail-open activations, scanner age, snapshot count, trend spread, zombies, overflow status, idle-cash-blocked notice).
- **Task 3.6 (M7, per D-RESERVE):** Fold reserve into active below $10K; remove the dead `layer >= 6` branch in `_execute_action`.

**⛔ GATE 3:** Report + approval.

---

## PHASE 4 — Pre-migration items

- **Task 4.1 (H3, code):** `_sync_positions_from_exchange` branches on `pos["side"]`; shorts never written into `eng.long_*`. Smallest possible diff, its own restart.
- **Task 4.2 (F3, spec only):** Hyperliquid short-side spec — short deal keys, short TP mechanics given HL order-type support, full-flip validation plan.
- **Task 4.3 (P8, spec only):** SQLite `TradeStore` migration spec per architecture §16.
- **Task 4.4 (F2, spec only):** Realized-velocity allocation feedback spec (depends on 4.3).
- **Task 4.5 (new, spec only):** **Grid-profile-per-regime spec** — named grid geometries (`bull` = D-GRID d today; `defensive`/Martingale-normalized for late-cycle and short grids) selected by the global regime, applied to **new deals only** (existing positions always finish under the grid that opened them — Rule #34 corollary). This is the adaptive follow-on to today's grid decision.
- **Task 4.6 (spec DELIVERED — build the backtest, do not deploy):** **Signal-Aware Deployment** per `signal-aware-deployment.md` v1.0 — Part A (overheat/oversold entry veto at the selector) + Part B (signal-gated L3/L4 deployment), fully symmetric for LONG and SHORT regimes. Today's scope: implement `GateModel` + unit tests (including the NEAR calibration self-test) and build the §8 backtest harness; run the long-regime and simulated short-regime windows and deliver results to Brett. **Live deployment only after the §8 acceptance criteria pass and Brett approves** — this is the single feature exempted from same-day live because it changes the character of the strategy (the 11-for-11 native L4 record was produced by mechanical firing). Note the stated precedence dependency: Task 3.3's trend-multiplier fix must land with or before Part A, and the veto takes precedence over the multiplier. Short-side code paths are implemented and unit-tested now but exercise live only after F3 (Task 4.2's implementation) ships shorts.

**⛔ GATE 4 (final):** Consolidated end-of-day report: every task's finding ID, files touched, diff size, pre-flight result, restart timestamp, acceptance evidence, anomalies. Outstanding items to track: remaining per-layer live fill verifications (as depths are reached naturally), tomorrow's Rule #6 review, scanner top-10 drift over the next week under the new sim.

## Explicitly OUT OF SCOPE
- Re-litigating D-GRID; any grid geometry other than the Part 2 table.
- Any change to TP %, deviation, max layers, leverage, or coin universe.
- **Paper bots — no updates in this engagement** (operator decision); the dry-run harness substitutes where specs reference paper testing.
- Hyperliquid implementation (specs only).
- Resizing/closing/rebasing open positions to the new grid — old-grid positions ride to TP untouched.

───
