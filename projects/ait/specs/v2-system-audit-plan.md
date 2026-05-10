# V2 System Audit Plan — Pre-Migration Full Verification

**Status**: PLAN — awaiting approval  
**Date**: 2026-05-10  
**Auditor**: OpenClaw AI (direct, no sub-agents)  
**Scope**: Every production file, every code path, every state variable, every integration point  
**Goal**: Zero unturned stones before Hyperliquid migration

---

## Why Another Audit

The March 10 audit (v1) was effective but operated at the **module level** — it verified
architecture, data flow, and found critical DB path bugs. Since then, 12 specs of fixes
have been deployed, many addressing bugs that the v1 audit should have caught but didn't:

| Post-Audit Bug | Why v1 Missed It |
|----------------|------------------|
| Data sync cron overwrites source files | v1 didn't audit cron scripts line-by-line |
| Capital manager deployed from wrong branch | v1 didn't verify file provenance |
| Candle replay causes 113 spread-reject trades | v1 didn't test restart behavior under real conditions |
| Deposit detection creates phantom transactions | v1 didn't trace the formula end-to-end |
| Reconciliation creates phantom trades from churn | v1 noted TradeTracker "correct" without testing edge cases |
| `active_allocations` never cleaned after rebalance | v1 noted rebalance "correct" but didn't trace the full lifecycle |
| T1 gate circular dependency blocks new coin entries | v1 didn't test the new-coin promotion path |
| Phantom positions in status.json (HYPE) | v1 didn't test what status.json reports vs exchange truth |
| Exchange sync only zeros long fields, not short | v1 verified the "happy path" only |

**Pattern**: v1 verified each component in isolation ("does this function work?"). It did not 
verify **interactions between components**, **lifecycle state accumulation**, **failure/restart 
behavior**, or **what actually happens in production** over weeks of operation.

**v2 will audit at the function level AND the integration level.**

---

## Audit Methodology

### Approach: "Follow the Money"

Instead of auditing files in isolation, v2 traces every dollar through the system:

1. **How does money enter?** (startup capital, DEX balance, deposits)
2. **How does money get allocated?** (rebalance → router → engines)
3. **How does money move?** (buy orders, DCA layers, TP closes)
4. **How is money tracked?** (engine state, CSV, status.json, dashboard)
5. **How does money reconcile?** (what happens on restart, after a crash, after a gap)

Each trace will be a **line-number-annotated walk** through the actual code path,
not a module-level description. Every branch, every edge case, every error handler.

### Evidence Standard

For each finding, the audit will produce:
- **Code location**: file + line numbers
- **Expected behavior**: what the architecture doc says should happen
- **Actual behavior**: what the code actually does (verified by reading, not assuming)
- **Test case**: how to verify (or what would break if the finding is real)
- **Severity**: CRITICAL / HIGH / MEDIUM / LOW / NOTE
- **Recommendation**: fix now, fix before migration, or defer

---

## Audit Phases

### Phase 1: Live Runner — Complete Line-by-Line Review
**File**: `run_v14_portfolio_live_aster.py` (3,335 lines)  
**Estimated effort**: This is the largest and most critical file. Every production trade flows through it.

#### 1.1 Startup Sequence (lines ~700-1000)
- [ ] CLI argument parsing and validation
- [ ] Exchange client initialization (credentials, sandbox vs production)
- [ ] DEX-as-truth capital loading: does it actually read the wallet balance? What if the exchange is unreachable?
- [ ] State restoration from `state.json`: every field mapped, every default traced
- [ ] Router state restoration: `active_allocations`, `reserve_allocations`, pool cash
- [ ] Engine state restoration: what happens when signal pack fails for one coin?
- [ ] Tracker CSV loading: dedup logic, what happens with corrupt rows?
- [ ] PID lock / bot.lock behavior
- [ ] `--skip-backfill` vs `--fresh` vs normal restart — trace each path completely
- [ ] What runs before the main loop starts? Order matters.

#### 1.2 Main Loop (lines ~3400-3600)
- [ ] WebSocket candle ingestion: how are candles received, buffered, deduped?
- [ ] Per-coin candle processing: ordering, timing, what if one coin's data is late?
- [ ] Warmup-only replay: trace the `is_current_candle` logic. What defines "current"?
- [ ] Stale candle threshold: is 4500s correct for all scenarios?
- [ ] Engine tick: what's the call chain from candle → action → order?
- [ ] Regime gate: trace exactly which actions are blocked and which pass through
- [ ] Per-coin regime conflict check after each tick
- [ ] Status write frequency and what triggers it
- [ ] State save frequency and what triggers it
- [ ] Error handling in the main loop: what exceptions are caught? What crashes the bot?

#### 1.3 Order Execution Path (lines ~2000-2200)
- [ ] `_execute_action()`: BUY path — T1 gate, regime check, order dedup, request_capital, actual exchange call
- [ ] `_execute_action()`: SELL/TP path — return_capital, CSV recording, pruning
- [ ] Exchange-truth trade recording: does the entry price really come from DEX?
- [ ] What happens if the exchange rejects an order? (insufficient balance, price moved, rate limit)
- [ ] What happens if the TP order succeeds but the status write fails?
- [ ] Bot-side trailing TP: trace the entire implementation
- [ ] Bot-side TP race condition fix: verify the fix is actually in place
- [ ] Fee model: where are fees calculated? Are they exchange-verified or assumed?

#### 1.4 Daily Rebalance (lines ~2297-2420)
- [ ] Timing guard: when exactly does rebalance fire? What prevents double-fire?
- [ ] Scanner data loading: what if the file is missing, corrupt, or stale?
- [ ] Regime-flagged coin exclusion: are flagged coins correctly excluded from rebalance candidates?
- [ ] Liquidity filter: trace the full volume check (ticker fetch, threshold calc, exemption for open positions)
- [ ] Tier cap enforcement: trace the cap calculation and the "slots full" guard
- [ ] New coin engine creation: full path from allocation → CoinState → V14LifecycleEngine → warmup
- [ ] Existing coin capital update: what gets updated and what doesn't?
- [ ] Allocation seeding (new fix): verify it unblocks T1 gate correctly
- [ ] Stale allocation cleanup (new fix): verify it preserves coins with open positions
- [ ] What happens if rebalance throws an exception mid-way? Is state consistent?

#### 1.5 Regime System (lines ~2425-2700)
- [ ] `_evaluate_regime()`: timing, what triggers it, what data it reads
- [ ] Graduated conviction calculation: count logic, threshold progression
- [ ] APPROVE command handler: what exactly changes? What's preserved?
- [ ] DENY command handler: what resets?
- [ ] Global regime persistence: saved to state.json? Restored on startup?
- [ ] Per-coin `regime_flagged` auto-unflag logic: when does it trigger?
- [ ] What happens if the regime flips during an active trade?

#### 1.6 Telegram Command Handlers
- [ ] Map every Telegram command: STATUS, APPROVE, DENY, DEPOSIT, WITHDRAW, PAUSE, RESUME, etc.
- [ ] What state does each command modify?
- [ ] Are there commands that could corrupt state if sent at the wrong time?
- [ ] Rate limiting on commands?

#### 1.7 Status Writer (lines ~3050-3200)
- [ ] Every field in `status.json`: where does the value come from? Is it exchange-truth or engine-internal?
- [ ] Phantom position fix: verify exchange zeroing is in place for ALL fields
- [ ] `approved_symbols`: now derived from router allocations — verify
- [ ] Router state serialization: pools, allocations, tier info
- [ ] Regime state serialization: global regime, flip %, per-coin status
- [ ] Error handling: what if status write fails? Does the bot continue?

#### 1.8 Exchange Sync (lines ~1000-1100)
- [ ] Every field synced from exchange to engine state
- [ ] What happens when exchange reports no position but engine thinks there is one?
- [ ] What happens when exchange reports a position but engine doesn't know about it?
- [ ] Short field zeroing (new fix): verify completeness
- [ ] Leverage sync: when is `ensure_leverage` called? What if it fails?

---

### Phase 2: Engine Stack — Signal Integrity

#### 2.1 V14DCAEngine (`engine/v14_dca_engine.py`, 801 lines)
- [ ] Phase transitions: map every path from one phase to another
- [ ] Every `_compute_signals()` call: what signals, what conditions, what thresholds
- [ ] `_check_top_signals()`: OB93 arm + divergence confirm — trace the full logic
- [ ] `_check_bottom_signals()`: 3D death cross + conviction — trace the full logic
- [ ] `_long_dca_tick()`: entry conditions, layer progression, TP calculation
- [ ] `_short_dca_tick()`: same analysis
- [ ] Unwinding mode: what triggers it, what it blocks, what it allows
- [ ] Fee calculation accuracy: verify against exchange fee schedule
- [ ] Edge cases: what happens at 0 coins, at max layers, at exactly the TP price?

#### 2.2 V14LifecycleEngine (`v14_lifecycle_engine.py`, 759 lines)
- [ ] `tick()`: full trace from candle input to action output
- [ ] Daily boundary detection: midnight UTC handling, timezone edge cases
- [ ] Signal pack refresh: what gets recomputed? What if it fails mid-refresh?
- [ ] `snapshot_state()` / `restore_state()`: every field persisted and restored
- [ ] Bare engine fallback: when it triggers, what's missing, when it recovers
- [ ] `_warmed_up` flag: every place it's checked, every place it's set

#### 2.3 Signal Pack (`engine/v13_signals.py`, 509 lines)
- [ ] `V13SignalPack.__init__()`: what loads, what can fail, what's the fallback?
- [ ] `load_daily()`: SQL query, dedup, symbol selection (multi-pair handling)
- [ ] `load_cfgi()`: same analysis
- [ ] Every signal class: StochRSI (1W/2W/3W), Divergence, BMSB, DailyStructure, CFGI, SMA200
- [ ] For each signal: what data does it need, what lookback, what happens with insufficient data?
- [ ] Edge cases: what happens with NaN values, gaps in data, extremely volatile data?

#### 2.4 ROUTER v2 (`engine/v13_router_engine_v2.py`, 522 lines)
- [ ] HybridDetector2D: what it computes, what DB it reads from
- [ ] 2D divergence dates: computation logic, caching, freshness
- [ ] 3D death cross: computation and truth table
- [ ] Steve 3-Check bottom detector: full logic trace
- [ ] Integration with V14DCAEngine phase transitions

---

### Phase 3: Capital Manager — Money Flow Integrity

**File**: `v14_capital_manager.py` (498 lines)

- [ ] `CapitalRouter` class: every field, every method
- [ ] `rebalance_daily()`: hurdle rate, tier caps, proportional weighting, risk cap — full trace
- [ ] Hysteresis: tier cap and pool split hysteresis — does it work correctly at boundaries?
- [ ] `request_capital()`: active vs reserve pool, partial grants, pool depletion
- [ ] `return_capital()`: where does returned capital go? What if it exceeds pool total?
- [ ] State persistence: what's saved, what's restored, what drifts over time?
- [ ] Pool cash accounting: trace through a full cycle (allocate → buy → TP → return → reallocate)
- [ ] Edge case: what happens if equity drops below minimum tier? Does the bot stop trading?

---

### Phase 4: Exchange Client — Order Execution Truth

**File**: `exchange_client.py` (188 lines)

- [ ] CCXT initialization: exchange selection, sandbox vs production, API key loading
- [ ] `create_order()`: parameter mapping, error handling, retry logic
- [ ] `fetch_balance()`: what fields are read, what's the precision?
- [ ] `fetch_positions()`: how are positions mapped back to engine symbols?
- [ ] `ensure_leverage()`: when called, what if the exchange rejects it?
- [ ] Aster-specific quirks: symbol naming, USDT vs USDC, position format
- [ ] **Hyperliquid differences**: What will need to change for migration?
  - Order types, margin modes, position fields, fee structure
  - Symbol format differences
  - API rate limits
  - WebSocket vs REST differences

---

### Phase 5: Data Pipeline — End-to-End Flow

#### 5.1 Candle Collection
- [ ] `collect_scanner_candles.py`: exchange connection, coin list, incremental vs full
- [ ] Rate limiting: actual sleep times, retry behavior
- [ ] What happens if a coin is delisted? New coin added?
- [ ] Database write: INSERT OR REPLACE behavior, index structure

#### 5.2 Daily Resampling
- [ ] `resample_daily.py`: OHLCV aggregation correctness
- [ ] Edge cases: partial days (missing candles), duplicate timestamps, timezone handling
- [ ] INSERT OR IGNORE behavior: does it handle updates for today's incomplete candle?

#### 5.3 DCA Cycle Scanner
- [ ] `v14_cycle_scanner.py` (728 lines): full scoring logic
- [ ] Backtest execution per coin: capital, parameters, fee model
- [ ] Score formula: `Realized_PnL × (1 - MaxDD%) × Capital_Freedom / 100`
- [ ] Trend multiplier calculation: lookback window, smoothing, direction classification
- [ ] Output format: does it match what `rebalance_daily()` expects?

#### 5.4 CFGI Client
- [ ] `cfgi_client.py`: API endpoint, response parsing, caching, fallback on failure
- [ ] How stale can CFGI data be before it affects trading decisions?

---

### Phase 6: Cross-Cutting Concerns

#### 6.1 State Consistency Matrix
Build a complete matrix: for every piece of persistent state, answer:
- Where is it written?
- Where is it read?
- What happens if it's missing on startup?
- What happens if it's corrupt?
- What happens if two writers conflict?
- What is the source of truth?

State locations: `state.json`, `engine_state.json`, `status.json`, `trades.csv`, 
`capital_ledger.json`, `score_history.json`, `cycle_scanner.json`, exchange API

#### 6.2 Restart Behavior Matrix
For every combination:
- Normal restart (kill + start, no flags)
- `--skip-backfill` restart
- `--fresh` restart  
- Restart after crash (no clean shutdown)
- Restart after data sync cron (files may have changed)
- Restart after manual state edit

What happens to: open positions, pending orders, engine phases, capital accounting,
trade history, regime state?

#### 6.3 Error Propagation Audit
Trace every `try/except` block:
- What exceptions are caught?
- What's the recovery behavior?
- Are there silent failures (catch + log + continue) that should be fatal?
- Are there fatal failures (crash) that should be recoverable?

#### 6.4 Race Conditions & Timing
- Telegram command arrives during candle processing
- Exchange WebSocket reconnection during active order
- State save concurrent with status write
- Dashboard sync reads status.json while bot is writing it
- Two candles arrive in rapid succession (exchange clock adjustment)

#### 6.5 Numerical Precision
- Float vs Decimal in capital accounting
- Rounding in fee calculations
- Minimum order sizes and how they're enforced
- Dust positions (tiny remainders after TP)

---

### Phase 7: Dashboard Verification

- [ ] Every data field on each dashboard: trace back to source in status.json
- [ ] JavaScript logic in each dashboard HTML: calculations, filters, display logic
- [ ] Are there stale dashboard calculations that don't match current bot logic?
- [ ] Regime panel: does the display match what the bot actually reports?
- [ ] Portfolio allocation: verify the filter logic matches current implementation
- [ ] Sync pipeline: is every file that dashboards read actually synced?

---

### Phase 8: Infrastructure & Cron

- [ ] Every Windows Scheduled Task: command, trigger, working directory
- [ ] `sync_dashboard.ps1`: full trace (what's synced, what's excluded, error handling)
- [ ] `run_candle_collector.ps1`: pipeline steps, timing, error handling
- [ ] `openclaw_watchdog.ps1`: what it monitors, alerting behavior
- [ ] OpenClaw cron jobs (`jobs.json`): every active job, what it does, schedule
- [ ] Git operations: pull/push/rebase behavior, conflict handling

---

### Phase 9: Documentation Reconciliation

- [ ] Architecture doc vs actual code: for every section, verify the code matches
- [ ] Update architecture doc sections that are now outdated (v1 audit section, performance numbers)
- [ ] Update or remove sections about disabled features (reconciliation, auto deposits)
- [ ] Verify all referenced line numbers still match after recent code changes
- [ ] Verify specs marked "DEPLOYED" are actually in the code
- [ ] Verify hard rules are actually enforced (not just documented)

---

## Deliverables

1. **Audit Report**: Comprehensive findings document (like v1 but at function level)
2. **State Flow Diagrams**: Visual maps of money flow, state flow, data flow
3. **Architecture Doc v2.0**: Updated to match actual production code
4. **Migration Risk Register**: Issues that will surface during Hyperliquid migration
5. **Bug List**: Any findings, prioritized by severity
6. **Updated Hard Rules**: Any new non-negotiable rules from audit findings

---

## Schedule Estimate

| Phase | Scope | Est. Time |
|-------|-------|-----------|
| Phase 1 | Live Runner (3,335 lines) | 3-4 sessions |
| Phase 2 | Engine Stack (~2,600 lines) | 2 sessions |
| Phase 3 | Capital Manager (498 lines) | 1 session |
| Phase 4 | Exchange Client (188 lines) | 1 session |
| Phase 5 | Data Pipeline (~1,500 lines) | 1-2 sessions |
| Phase 6 | Cross-cutting (matrices) | 1-2 sessions |
| Phase 7 | Dashboards (4 HTML files) | 1 session |
| Phase 8 | Infrastructure | 1 session |
| Phase 9 | Doc reconciliation | 1 session |
| **Total** | **~16,700 lines + infrastructure** | **~12-15 sessions** |

Each session = one focused audit block with deliverables. I'll report findings as I go,
not batch them all to the end. Critical findings get flagged immediately.

---

## What's Different from v1

| v1 Audit (March 10) | v2 Audit (May 10) |
|---------------------|-------------------|
| Module-level review | Line-by-line review |
| Verified components in isolation | Traces interactions between components |
| "Does this function exist?" | "Does this function work in every scenario?" |
| Tested the happy path | Tests error paths, restart paths, edge cases |
| Architecture doc as reference | Architecture doc as verification target |
| Single-pass | Multi-pass (code → integration → cross-cutting) |
| Found DB path bugs | Looking for lifecycle bugs, race conditions, accounting drift |
| 1 session | 12-15 sessions over ~2 weeks |
| No migration perspective | Every finding tagged with migration impact |

---

## Ground Rules

1. **I read every line.** No skimming, no "this looks fine." If I haven't read it, it's not audited.
2. **Code is truth.** If the architecture doc says X but the code does Y, the code wins. Doc gets updated.
3. **Production evidence.** Where possible, verify against actual log output, actual status.json, actual exchange state — not just code review.
4. **No sub-agents.** I do this directly, maintaining full context across phases.
5. **Findings reported immediately.** Critical issues don't wait for the phase to finish.
6. **No fixes during audit.** Audit produces findings. Fixes come after, with proper specs and approval.
   Exception: if something is actively losing money or creating danger, flag it for emergency fix.
