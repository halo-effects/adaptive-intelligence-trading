# AIT V14PM — Post-Remediation Audit (Independent Verification)
_Date: 2026-07-04 | Auditor: Claude (Fable) — this document written by me in this session, from scratch_
_Package: fable-resync-v3-2026-07-04.zip (78 files) | Fingerprints verified: capital manager 601 lines (reconcile @495), runner 4,768 lines (prune @2248), zero `self.client.exchange`, arch doc v1.11_
_Method: full diff of pre-remediation snapshot (project mount, 2026-06-19 era) against the package, followed by deep-read of every changed hunk and all three new modules. Blast radius confirmed: 4 changed files (runner ±829 lines, scanner ±119, capital manager ±39, DCA engine ±29), 3 new files (grid_model, gate_model, _gate_backtest_1h), everything else byte-identical._

---

## Part 1 — Remediation verification

Every claim checked against the code itself, not against reports.

| Task | Verified | Evidence |
|------|----------|----------|
| 0.1 (C2) `_prune_stale_coin_after_tp` | ✅ implemented, ⚠ semantics deviate (see M-3) | def at runner:2248; call at ~2636 now resolves |
| 0.2 (H1) liquidity filter attributes | ✅ | 0 × `self.client.exchange.`, 6 × `self.client._exchange`; alerts in except blocks |
| 0.3 (H2) 1000-prefix double-descale | ✅ | `price_from_exchange` flag; ticker fallback sets False; descale gated on flag (runner ~455–470) |
| 0.4 (M3) trade CSV identity | ✅ | deal_ids 1–119, zero gaps, zero duplicates (pre-fix copy had gaps at 117–118) |
| 0.5 (M1) `_evaluate_regime` deleted | ✅ | def gone; deletion comments at 102/~838/~3282/~4456; `_check_coin_regime_conflict` intact |
| 0.6 (P7) startup attribute self-test | ✅ | getattr sweep present |
| 0.7 (L2) bare `except: pass` | ✅ | zero remaining in live runner |
| 1.1 GridModel | ✅ | leaf module, zero engine imports; **self-test executed in my sandbox — passes**, reproduces D-GRID table incl. the 99.43/98.84 corrections of the handoff's display rounding |
| 1.2 call-site migration | ✅ | engine long+short ticks use `gm_layer_cost(layers, allocated_capital)` with legacy fallback; funds gate retained; 0.3 cap removed from GridModel path (retained only in legacy fallback, correct); scanner sim fully unified (geometric ladder removed, linear trigger from avg entry); top-up uses `remaining_grid_cost` |
| 1.3 arch doc v1.11 | ✅ | §5.2 table (lines 422–426) matches GridModel self-test output **exactly** |
| 2 (H4) overflow v2 | ✅ | soft ceiling from next tier; fail-closed on missing scanner (2392) and >24h stale (2395); candidate walk from rankings |
| 3.1 (M2) spread-reject `pnl_adjustment` | ✅ present |
| 3.3 (M5) trend multiplier | ✅ | least-squares regression over all snapshot points (scanner:667–685), normalized by mean score |
| 3.4 CLOSE/CLOSEALL CONFIRM + MIGRATE | ✅ | typed confirmation; MIGRATE → WIND_DOWN |
| 3.5 grid-freeze + daily digest | ✅ implemented, ⚠ freeze condition narrow (M-4) | `_check_grid_freeze` (~3290), `_daily_health_digest` |
| 3.6 (M7) D-RESERVE fold | ✅ | tier row <$10K now (100, 1.00, 0.00) |
| — `reconcile_pools_from_exchange` | ✅ implemented, ⚠ two findings (H-1, M-2) | capital_manager:495; called at startup (runner:4319, after position sync, before top-up) and **every** main-loop cycle (4449, immediately after `_sync_positions_from_exchange`, before rebalance); `_exchange_usdt_free` fresh at both sites |
| — `allocated_capital` lifecycle | ✅ | set on restore (1013), bare-engine path (1056), rotation (2497/2658), rebalance (3193/3213) |
| — TP consistency | ✅ no live fork | High profile `DCA_TP_PCT = 0.030` = GridModel `TP_PCT` (see L-1) |
| 4.6 GateModel + harness | ✅ built, correctly **not** wired into scanner/engine/runner (per plan) | gate_model self-test executed — passes; harness read in full (see companion go/no-go doc) |

**Verdict: the 2026-07-03 remediation is real and delivered as specified**, with the new findings below — none of which is a regression of a completed task; they are properties of the new code and of the system at current capital scale.

---

## Part 2 — New findings

### 🔴 HIGH

**H-1 — L4 silently never fires below $62.50 allocation; L3 below $50. ACTIVE at current capital.**
`v14_dca_engine.py` retains `if order < 10 or order > self.capital: return` after GridModel sizing. Under fixed fractions, L4 = 16% of allocation → below the $10 minimum whenever allocation < $62.50 (L3 = 20% → below $10 under $50). At reconciled equity ≈ free ($34.99) + invested, the 3-coin tier (<$3K) yields per-coin allocations right in this band. Consequences: (a) the "fully self-funded 100% grid" is a 3-layer-84% grid (or worse) at current scale, silently; (b) capital reserved for the unfireable layer sits idle and invisible — the grid-freeze detector won't flag it (capital > $1); (c) **every backtest arm — including the gating backtest — assumes full deployability** ($10K sim allocation), so live small-capital behavior diverges from all tested arms; (d) the 11-for-11 L4 record cannot extend at this scale because L4 physically cannot fire.
_Fix options (pick one, spec first per Rule #21): (i) allocation floor at rebalance — never seed a slot below $62.50, reduce coin count instead (tier table already trends this way); (ii) explicit Telegram warning when any layer of a seeded grid is sub-minimum; (iii) both. Option (i) preserves grid integrity; at $185 equity it means 2 slots, not 3._

### 🟠 MEDIUM

**M-1 — `reconcile_pools_from_exchange` zeroes reserve at ALL tiers.**
The comment says "Reserve is always 0 below $10K (D-RESERVE)" but `self.reserve_pool_cash = 0.0` executes unconditionally. Above $10K the split tier is 80/20: every cycle, reserve accounting is wiped while `active_pool_total` is set to 80% of equity — reserve-pool grants (`request_capital(pool="reserve")`) permanently return $0, and `active_pool_cash` (= all free cash) exceeds `active_pool_total` by design. Harmless at $400; a behavioral landmine the day equity crosses $10K. _Fix: gate the zeroing on the split tier, or route reserve share explicitly._

**M-2 — Balance-fetch failure injects $0.00 as truth for one cycle.**
`fetch_full_balance` swallows exceptions and returns `{"usdt_free": 0.0, ...}` (runner:412–414), so `_sync_positions_from_exchange`'s keep-previous-values guard never triggers for API failures. Reconcile then sets `active_pool_cash = 0.0` and `total_equity = invested only`. Direction is fail-safe for spending, but if the failure coincides with the midnight cycle, `_do_rebalance` runs on wrong equity (tier hysteresis dampens, doesn't eliminate). _Fix: return None on failure; sync keeps previous values on None; reconcile skips that cycle with a WARNING._

**M-3 — Prune method prunes unconditionally; docstring and Task 0.1 spec say otherwise.**
`_prune_stale_coin_after_tp` (2248) deletes the coin's allocations whenever the position is flat — it never checks "current rebalance targets" despite the docstring claiming that semantics. A top-ranked coin closed via non-TP sell loses its slot until the next daily rebalance (≤24h dead slot). Self-healing, but it deviates from the specified semantics and the docstring misdocuments the code. _Fix: either implement the targets check (compare against `_get_scanner_rankings()` top-N) or amend docstring + handoff record to the simpler behavior — but decide, don't leave the fork._

**M-4 — Grid-freeze detector condition too narrow for the fixed-fraction world.**
`_check_grid_freeze` fires on `eng.capital < 1.0`. Under GridModel + GAP-13, the starvation state produced by a mid-position allocation reduction is `0 < capital < next_layer_cost` — e.g. $5 on hand, $12 needed — which never alerts. _Fix: compare `eng.capital` against `gm_layer_cost(cs.layer_count, eng.allocated_capital)` instead of $1._

**M-5 — GateModel A3 input is direction-agnostic.**
`entry_veto(..., has_fresh_divergence: bool)` — the spec requires *bearish* divergence for the long veto and *bullish* for the short veto. The module cannot enforce which the caller passes; a wiring mistake would let a bullish (bottoming) divergence veto long entries — inverting the feature at the exact moment it should admit. Not live today (gating unwired, correctly). _Fix at wiring time: pass side-resolved divergence flags; add a signed-input assertion to the module._

### 🟡 LOW

**L-1** — Engine TP still sourced from profile config (`cfg.DCA_TP_PCT`), not GridModel. Values agree today (0.030); single-source-of-truth is one config drift away from a fork. Import GridModel TP in the lifecycle profile constructor.
**L-2** — GateModel self-test lacks the NEAR fixture required by spec §6 (see go/no-go doc — this is load-bearing for deployment).
**L-3** — `VetoState.since`/`day_count` never populated by `entry_veto`; consumers displaying "day 3" badges must maintain it externally.
**L-4** — Harness `vetoed_entries` counts per-1h-candle while vetoed (inflated metric, cosmetic); harness uses taker fee both sides vs live maker on entries/TPs (slightly pessimistic — acceptable direction).
**L-5** — `veto_clear` C2 retrace check silently skipped when the extreme is on the wrong side of SMA50 (possible under A3-triggered vetoes) — clears easier than spec intends in that edge.
**L-6** — Inline `import` inside the engine tick hot path (style; Python caches, negligible).

---

## Part 3 — What's working well (verified, not assumed)

1. Reconcile ordering is exactly right: position sync → reconcile → top-up (startup) / rebalance (cycle), with fresh `_exchange_usdt_free` at both sites.
2. GridModel is a genuine leaf (zero trading imports) and the scanner now simulates the grid the bot actually trades — the C1 "three grids, three truths" gap is closed in code, not just in docs.
3. Old-grid positions are untouched by construction — sizing changes apply only at fill time to new layers; no resize/rebase paths exist. Rule #34 holds.
4. Overflow v2 fails closed on missing/stale scanner data; soft ceiling counts zombies.
5. Arch doc v1.11 §5.2 equals GridModel self-test output line for line — the doc is the single source of truth again.

## Part 4 — Recommended sequence

1. **H-1 decision** (allocation floor vs. alert) — this is a Brett decision because it trades slot count against grid integrity at test-capital scale. Spec → approve → one restart.
2. M-2 (balance-failure guard) — smallest diff, protects the daily rebalance. One restart.
3. M-3 (prune semantics) — decide and align code/doc. One restart.
4. M-4 (freeze detector threshold) — one restart, pairs naturally with 1.
5. M-1 can ride until equity approaches $10K but should be specced now while context is fresh.
6. Gating: per the companion go/no-go document — Part A path is short; Part B needs the harness↔spec fork resolved first.
