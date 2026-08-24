# AIT V14PM — Comprehensive Code Audit & Performance Analysis
_Date: 2026-07-03 (rev. 2 — adds finding H4, overflow entry) | Auditor: Claude (Fable) | Scope: Live production system, Aster DEX Perps, real money_
_Reference baseline: V14PM_SYSTEM_ARCHITECTURE.md v1.10, hard-rules.md (36 rules), 119 live trades_

> **✅ POST-REMEDIATION STATUS (2026-07-04):** All P0 fixes from this audit independently verified delivered by Fable post-remediation audit. C1 (GridModel — three-grids gap) officially CLOSED. C2 (prune method), H1 (liquidity filter), H2 (1000-prefix), M1 (dead regime evaluator), M3 (trade IDs), startup self-test, bare-except removal, overflow v2, spread-reject pnl_adjustment, trend multiplier regression, CLOSE/CLOSEALL/MIGRATE commands, grid-freeze + daily digest, D-RESERVE fold — all confirmed implemented. See `fable-post-remediation-audit-2026-07-04.md` for full verification report.

---

## 1. Executive Summary

**Overall system health: GOOD, with three integrity gaps that need closing before scaling.**

The system's operational hardening is genuinely impressive — the hard-rules discipline, exchange-as-truth architecture, state persistence, atomic writes, orphan-TP mode, layer reconciliation, and capital top-up all trace to real incidents and all check out in code. The trade data validates the core thesis: after the May grid optimization and the no-force-close rule, the system runs 18 deals with a 94% win rate and zero catastrophic losses, and strategy-native deep-layer deals (L4) are 11-for-11 profitable. The DCA cycle engine works as designed when it is allowed to ride.

The problems this audit found are not in the trading logic — they are in the **connective tissue**: three components (scanner simulation, live engine, capital top-up) each believe in a *different* DCA grid; several risk controls and features are silently dead due to attribute errors that fail-open excepts have been swallowing; and the trade ledger has minor identity hygiene issues. None of these has cost money yet in an obvious way, but all of them widen the gap between what the system is documented to do and what it actually does — and Hard Rule #18 says the architecture doc is the single source of truth.

### Top 3 strengths
1. **Incident-driven hardening that actually works.** Post-5/17 data (orphan-TP era): 18 deals, +$29.14, 94% WR, worst loss -$0.20. The three catastrophic losses in the ledger (-$103.83) were all *manual* force-closes during codebase upgrades — the strategy itself has never produced a large loss. Hard Rule #34 now structurally prevents recurrence.
2. **Exchange-as-truth architecture.** Position sync every cycle, TP prices computed from actual exchange entry, DEX-as-truth capital on startup, immutable seed capital. This eliminates entire classes of drift bugs that plagued earlier versions (and that the changelog documents honestly).
3. **The intelligence layer has real signal.** The scanner's top-ranked coin (TAO) was also the live book's best performer (+$72.40, 17/17 wins, 6.25% avg return). Correlation between current 30d score and realized PnL-per-deal across traded coins is +0.39 — imperfect, but directionally validated with real money.

### Top 3 risks
1. **Three different grids in production (CRITICAL-1).** The documented Martingale (40/60/90/135% of allocation) is not what trades. A never-read `live_mode` flag leaves a 30%-of-remaining-capital cap active, producing a *decreasing* layer grid (~30/21/15/10%). The scanner scores coins under yet a third grid. Capital top-up sizes grants for the documented grid that nothing uses.
2. **Silently dead risk controls and features (CRITICAL-2, HIGH-1, HIGH-4).** An undefined method crashes the non-TP sell path mid-cycle; the liquidity filter has never executed (two attribute errors, both swallowed by fail-open handlers); the daily `_evaluate_regime` reads JSON fields that don't exist; and the overflow-entry feature — the mechanism meant to deploy weekly deposit capital when all grids are maxed — is logically unreachable (H4), stranding deposits until a TP frees a slot. Fail-open exception handling and silent no-ops have been hiding all of this.
3. **Long-only live runner vs. the coming down-leg.** SHORT_OPEN is explicitly rejected on live. Your own cycle model (~3 years up, ~1 year down) means that when the regime is confirmed SHORT at the top, the live bot as written goes **fully idle** — longs gated, shorts rejected — for the duration of the bear leg. This is a known scope decision, not a bug, but it needs a plan before the Hyperliquid migration and certainly before the cycle top.

---

## 2. Bug & Code Quality Findings

### 🔴 CRITICAL

#### C1 — `engine.live_mode` is write-only; deployed grid ≠ documented grid ≠ scanner grid
**Files:** `run_v14_portfolio_live_aster.py` (lines 950–952, 994, 2311, 2844), `v14_dca_engine.py` (lines 394, 499), `v14_cycle_scanner.py` (lines 30–38, 186–246)

The runner sets `engine._engine.live_mode = True` in four places with the comment *"disables paper-trading caps."* **`v14_dca_engine.py` never reads this attribute.** The paper-era cap `order = min(order, self.capital * 0.3)` is therefore active in live production.

Combined with the GAP-13 capital reset (`eng.capital = allocation − invested` after each buy), the actual live layer sizes are:

| Layer | Documented (§7.6 grid table) | Actually deployed | Scanner sim |
|-------|------------------------------|-------------------|-------------|
| L1 | 40% of allocation | **30.0%** | 40% |
| L2 | 60% | **21.0%** | 20% (BO×0.5) |
| L3 | 90% | **14.7%** | 30% (×1.5) |
| L4 | 135% | **10.3%** | 45% (×1.5) |
| Total | 325% (needs top-up) | **76%** | 135% |

Three consequences:

1. **The deployed grid is an inverted Martingale.** Deeper layers get *smaller*, so averaging-down barely moves the average entry, and TP recedes rather than approaches during drawdowns. This is the mechanical explanation for L3/L4 median durations of 64–73h vs. 2.4h at L1. It also means the live system is more conservative than believed — total deployment caps at ~76% of allocation, never exceeding it.
2. **`_remaining_grid_cost()` / `_top_up_engine_capital()` compute deficits using the documented formula** (`bo × mult^layer`), so top-ups grant capital sized for a grid the engine will never spend (the 30% cap re-throttles it anyway). Capital sits in `engine.capital` doing partial work.
3. **The scanner simulates a third grid** — BO 40%, first SO = 50% of BO scaling ×1.5, with *geometrically widening* price steps (`dev = 1.5% × 1.5^i`, compounding from the previous SO price), and up to 5 total fills (`layers <= MAX_LAYERS` with BO counted as layer 1). The live engine uses *linear* deviation from average entry (`1.5% × layer_count`) and 4 total layers. **The intelligence layer is ranking coins under grid mechanics the execution layer does not trade.** The +0.39 score-vs-outcome correlation is achieved *despite* this — aligning them should only improve it.

**Note:** the deviation *trigger geometry* also differs — sim measures from the previous SO price; engine measures from the volume-weighted average entry, which shifts upward-biased as layers fill, making live SOs fire *earlier* than the sim's.

**Fix path (requires spec + approval per Hard Rule #21):** Decide which grid is canonical. Either (a) honor the doc — implement the `live_mode` bypass and size layers from `allocated_capital` rather than remaining capital, or (b) accept the deployed conservative grid — update §5.2/§7.6, re-derive `_remaining_grid_cost`, and re-run the 2026-05-12 TP/layer backtest under the true grid. Then extract one shared `GridModel` (see §5, Feature F1) so engine, scanner, and top-up can never diverge again. Do not hot-patch: this changes live order sizing.

#### C2 — `self._prune_stale_coin_after_tp()` is called but never defined
**File:** `run_v14_portfolio_live_aster.py` line 2636 (call), no definition anywhere (AST-verified: 34 methods on the class, this is not one of them)

The non-TP SELL branch of `_execute_action()` calls this method after a market sell fills and the CSV is saved. It raises `AttributeError` every time an engine-initiated sell executes — i.e., precisely the candle-based TP fallback path that is the designed safety net when exchange TP orders fail. The exception unwinds to the main-loop handler, which logs "Main loop error," sleeps 10s, and continues — **skipping all remaining coins that cycle and skipping `cs.last_candle_ts` update**, so the candle replays next cycle (mostly benign because the deal was already popped, but state is inconsistent for a full cycle).

**Fix:** implement it (the paper runner's `_maybe_prune_stale_coin` logic, referenced in §7.3 history), or replace the call with the equivalent inline allocation cleanup, or delete the call. One-line fix; pre-flight import test won't catch it (it's a runtime attribute), so add a startup self-check (see R7).

### 🟠 HIGH

#### H1 — Liquidity filter has never executed (two attribute errors, both swallowed)
**File:** `run_v14_portfolio_live_aster.py` lines 2250–2251 (`_rotate_after_tp`) and 2709, 2722 (`_do_rebalance`)

Both call sites use `self.client.exchange` (the attribute is `_exchange`) and `self._aster_symbol(...)` (defined on `AsterPerpClient`, not on the runner — AST-verified). Both raise `AttributeError` on first touch; both are wrapped in `except Exception: logger.warning(...proceeding...)`. **Every rotation and every rebalance has proceeded without the 24h-volume check since this code shipped.** `MIN_VOLUME_FLOOR = $50K` and `MIN_VOLUME_MULTIPLIER = 100×` allocation have never gated anything.

At $423 capital on majors this hasn't hurt. At scaled capital on a 45-coin universe including microcaps, entering an illiquid coin means slippage on entry and a TP that can't fill at size. **Fix:** `self.client._exchange` and `self.client._aster_symbol(...)` (4 edits). Then downgrade the exception handler from fail-open to fail-open-with-Telegram-alert so a future regression is visible (Hard Rule #14: never silence errors from critical operations).

#### H2 — 1000-prefix double-descale in `create_market_buy` ticker fallback
**File:** `run_v14_portfolio_live_aster.py` lines ~437–460

When a buy order returns no fill price and the trades lookup also fails, the code falls back to `fetch_ticker_price()` — which **already divides by 1000** for PEPE/BONK/FLOKI — and then unconditionally divides by 1000 again. Result: recorded fill price wrong by 1000×, corrupting avg entry, invested, and the TP price for that deal. `create_market_sell` handles the same descale correctly (inside the else-branch only), confirming the buy path is an accident. Rare path, but when it fires on a prefix coin it poisons the deal.

**Fix:** mirror the sell path's structure — descale only when the price came from the order/trades (exchange units), never after the ticker fallback.

#### H3 — Short positions from exchange would be synced as longs
**File:** `run_v14_portfolio_live_aster.py`, `_sync_positions_from_exchange()` (lines ~1082–1120)

The sync checks only `ex_qty > 0` and writes into `eng.long_*`. `fetch_open_positions()` returns a `side` field that the sync ignores. Today the live runner is long-only (SHORT_OPEN explicitly rejected), so this is dormant — but it is a loaded landmine for the Hyperliquid migration where short support is planned. A short position (opened manually, by a future code path, or by residue) would be mirrored into the engine as a long, and `_place_tp_order` would place a *sell* TP against a short. **Fix before any short-capable deployment:** branch on `pos["side"]`.

#### H4 — Overflow entry (`OVERFLOW_ENTRY_ENABLED`) is unreachable; deposit capital strands when all grids are maxed *(added 2026-07-03, post-initial-report)*
**File:** `run_v14_portfolio_live_aster.py`, `_do_rebalance()` new-coin loop (lines ~2797–2835); root cause in `v14_capital_manager.py` `rebalance_daily()` (`top_coins = qualifying_coins[:max_coins]`)

The overflow branch — designed to admit a +1 coin when all positions are at max DCA depth and idle cash exists — can never fire. Mechanical verification across 7,680 enumerated scenarios: **zero admissions.** The logic is a closed loop: overflow candidates are drawn only from the cap-sliced `allocations` dict; `all_maxed` over non-zombie positions implies every counted position is maxed *and approved* (a maxed unapproved position is a zombie and is excluded); those maxed-and-approved incumbents therefore occupy every allocation slot, so no new symbol ever reaches the check. In the one case a new symbol *does* appear (an incumbent decayed out of the top-N), the maxed incumbent zombifies, the slot frees, and the normal entry path handles it before overflow is consulted — the zombie mechanism (shipped in the same 2026-06-19 release) cannibalized every case overflow could serve.

**Production impact:** the core deposit-driven use case is unhandled. When all held coins are at max layers *and still top-ranked*, a weekly/monthly deposit flows `_detect_capital_change → resize()` into `active_pool_cash` and then idles: the next rebalance re-allocates to the same maxed incumbents, `_top_up_engine_capital()` skips them all (`layer_count >= max_layers`), and the next-ranked coin never appears as a candidate. Capital waits for a TP — the exact "idle capital is a system failure" condition the layer-reconstruction spec's design principles prohibit. Secondary defects in the branch (relevant once reachable): `min_l1_capital = alloc × 0.4` uses the documented grid's BO rather than the deployed grid's 30% (same drift class as C1), and the hard `active_count == tier_cap` equality makes it one-shot — a second deposit into a maxed cap+1 book re-strands.

**Fix:** full remediation design in `overflow-entry-v2-soft-ceiling.md` — candidates drawn from the full scanner ranking (the proven `_rotate_after_tp` pattern), evaluated after top-up, soft ceiling bounded at the *next* equity tier's coin cap counted over total positions, one admission per rebalance day, fail-closed on stale scanner data, L1 cost from the canonical grid. Depends on P0 fix H1 (liquidity filter) and the C1 grid decision. Book shrinks via TP rotation only (Rule #34).

### 🟡 MEDIUM

#### M1 — `_evaluate_regime()` is dead code that shadows the real regime monitor
**File:** lines 2926–3046. It reads `scanner.get("rankings") or scanner.get("coins")` — neither key exists at the top level of `cycle_scanner.json` (the structure is `windows → {7d,14d,30d,bear} → rankings`), so `coins_data` is always `[]`. Even if it parsed, it looks for `lifecycle_phase` / `router_signal` fields the scanner never emits. It no-ops silently every midnight. The *actual* §7.5.3 graduated-conviction monitor lives in `_check_coin_regime_conflict()` and is correctly implemented (15–50% thresholds, APPROVE at any level, step-down on unflag). **Fix:** delete `_evaluate_regime` (and its call) or rewrite it as a scanner-universe-wide early-warning layer with fields the scanner actually produces. Two overlapping regime systems, one dead, is exactly the kind of ambiguity Hard Rule #33 warns about.

#### M2 — Spread-reject losses are invisible to the ledger
The spread-reject path (buy fills > 100bps from engine price → immediate market sell) happens *before* `tracker.on_buy()`, so the round-trip loss is never recorded in trades.csv and never added to `_cumulative_realized_pnl`. Two effects: (1) small unaccounted PnL leakage; (2) the deposit-detection drift formula sees an unexplained balance drop — below the $5/2% threshold individually, but a burst of rejects on a volatile day could register a phantom "withdrawal" in the capital ledger (the exact cascade class Hard Rule #30 exists to prevent). Also note this path *is* a forced close; it's defensible as an entry-error abort (the grid never started), but it should be recorded. **Fix:** record spread-rejects as zero-duration trades or as a `pnl_adjustment` ledger transaction.

#### M3 — Trade CSV identity hygiene: 6 duplicate deal_ids, 8 non-monotonic rows
deal_ids **74, 75, 97, 98, 113, 114** each appear twice; 8 rows are out of order. No phantom trades detected (recorded_at ≈ close_time on 105/109 rows carrying the field), but 4 trades were recorded 1–47h after close — consistent with the documented TP-recovery-while-down path; worth a one-time exchange-fill spot check. **Fix:** stop bot → backup → `reconcile_trades.py --fix-ids` → restart (per Hard Rules #2, #29). Root-cause: `_deal_counter = len(self.trades)` collides when startup reconciliation appends deals with their own IDs; consider `max(counter, max_existing_id)` on load.

#### M4 — Fee column is effectively empty ($0.18 total on ~$7,100 of buy volume)
Either Aster's fee promo is real, fees are netted invisibly into proceeds, or CCXT isn't surfacing `fee.cost` for these order types (trailing stops filled as market orders often report fees only via `fetch_my_trades`). If fees exist but aren't captured, live PnL is slightly overstated and — more importantly — the Hyperliquid migration (0.025% taker) will introduce a visible PnL step-down that should be anticipated, not discovered. **Fix:** one-time reconciliation of fills vs. recorded fees; if CCXT under-reports, pull fees from `fetch_my_trades` at fill time.

#### M5 — Trend multiplier has almost no discriminating power in production
Current `cycle_scanner.json`: 27 of 46 coins at exactly 1.0; the rest compressed into 0.90–1.00. Nothing near the designed [0.3, 1.5] range and nothing above 1.0 — the "momentum bias" is effectively off. Causes worth checking: (a) the "slope" is an endpoint delta `(latest − earliest)/|earliest|`, which a single flat scan day flattens; (b) same-day snapshot dedup replaces rather than appends, so intraday scanner reruns erase movement; (c) 0-score coins produce 0.0 slopes by the `abs(earliest) < 0.01` guard. **Fix:** switch to least-squares slope over all points in the window, verify `score_history.json` is accumulating one snapshot per day, and add the multiplier distribution to the scanner's Telegram summary so collapse is visible.

#### M6 — Architecture doc vs. code drift on equity tiers (Hard Rule #18 violation)
Doc §7.2: `$100–$10K → 1 coin`. Code `EQUITY_TIER_CAPS`: `$100–$3K → 3 coins`, `$3–5K → 4`, `$5–100K → 5`. The live bot at ~$423 runs 3 slots; the doc says it should run 1. Peak concurrency observed in the trade data was 8 open deals — evidence the caps have changed over time without the doc following. Same drift class as C1. The code tiers look *better* for turnover at small capital (and the data supports fast-cycling), but the doc must be updated — it is the canonical reference and the thing future fixes are verified against (Hard Rule #33).

#### M7 — Dead reserve-pool branch
`pool = "reserve" if layer >= 6 else "active"` in `_execute_action` — max layers is 4; layer can never reach 6. The reserve pool (10% at current tier) is pure idle drag with no code path that ever taps it. Either wire reserve to a real function (e.g., overflow entries, or L4 top-ups) or fold it into active at small equity.

### 🟢 LOW

- **L1 — `TradeTracker.on_sell` can silently drop a trade:** if the dedup key already exists, it returns `{}` *after* popping the open deal — the deal vanishes with no record and no log. Add a warning log and re-insert the deal or record with a suffix.
- **L2 — Bare `except: pass`** in the buy-fill trades-lookup fallback (line ~452) — Hard Rule #14 adjacent; log it.
- **L3 — Stale-lock recovery race:** between `unlink()` and re-lock, a concurrently starting instance can win; both then write `bot.pid`. Watchdog-restart plus manual start is the realistic collision. Low probability; acceptable.
- **L4 — `_handle_tp_fill` invested override uses cached `_last_exchange_positions`:** if layers filled after the last sync but before the TP fill, `ex_entry × actual_qty` uses a slightly stale entry. Bounded error; note only.
- **L5 — `fetch_open_orders` lacks a dry-run guard** (all other client methods have one). Cosmetic consistency.
- **L6 — `_compute_equity()` re-fetches tickers per coin** during rebalance while `_write_status` correctly uses cached exchange unrealized PnL. Minor API load; unify on the cached path.

### Verified-clean items (checked, no issue)
Atomic writes for state.json/trades.csv (`tmp → replace`); `save_csv()` refuses to write an empty trade list (truncation guard); Phase constants are plain strings so the orphan-detection string comparisons in the phase-change block are correct; regime gate correctly separates entries (rejected + rolled back) from exits (pass through) per §7.5.2 and Hard Rule #32; candle warmup guard rolls back non-current-candle actions; `--fresh` semantics and `load_existing()` on all startup paths match doc; deposit detection uses only stable balances (Rules #30/#31); seed capital is immutable (Rules #26/#27); file lock has a working fcntl path for Linux; `AIT_CANDLES_DB` / `AIT_SCANNER_JSON` env vars are respected in this runner (prior audit H1/H2 fixed here).

---

## 3. Trade Performance Report

**Dataset:** 119 closed deals, 2026-03-01 → 2026-06-22 (113 days), ~$300 seed growing to ~$423, 1.0x leverage, long-only.

### 3.1 The operational-vs-strategy split (the single most important framing)

Per operator confirmation, the three large losses were **manual force-closes during codebase upgrades** (system resets), not strategy outcomes. Splitting the ledger:

| | Deals | PnL | Win rate | Avg return/deal | Worst loss |
|---|---|---|---|---|---|
| **Strategy-native** | 116 | **+$145.46** | **87.9%** | +1.86% | -$3.80 |
| Operational (manual resets) | 3 | -$103.83 | — | — | -$71.95 (ENA) |
| **Ledger total** | 119 | +$41.63 | 85.7% | — | — |

Native losses are structurally tiny: 14 losing deals totaling **-$10.26** (avg -$0.73). The loss distribution is exactly what a DCA-cycle engine should produce — many small scratches, no blowups — *when nothing force-closes it*. The -$103.83 of reset damage equals 71% of native profits; Hard Rule #34 and orphan-TP mode are therefore worth roughly **2.5× the entire net ledger PnL** going forward, and the post-5/17 record (below) shows they're holding.

One native outlier worth a five-minute exchange-fill check: deal 85 (INJ, -11.36% at 2 layers, 118.8h). An -11% realized exit doesn't come from a TP; it's either another operational close or a recording artifact.

### 3.2 Regime eras — the Learning Loop, evidenced

| Era | Deals | PnL | WR | Avg ret/deal | Deals/day |
|---|---|---|---|---|---|
| Pre 5/12 (TP 1.5%, 12L config era) | 93 | +$18.93 | 84% | +0.18% | 1.30 |
| Post 5/12 (TP 3.0%, 4L) | 26 | +$22.70 | 92% | +1.86% | 0.62 |
| Post 5/17 (orphan-TP / no force-close) | 18 | +$29.14 | 94% | — | — |

The 5/12 grid change traded deal frequency (halved) for per-deal quality (10× avg return) and net PnL improved — the backtest-driven decision is confirmed in live data. The post-5/17 era annualizes to roughly **$28/month on ~$423 (~6.7%/month run rate)** with a worst loss of -$0.20 — small sample (18 deals), but the healthiest stretch in the dataset. *(Internal figure only, per the live-dashboard-is-the-only-proof policy.)*

### 3.3 Layer distribution — the grid works, and where time goes

| Layers | Deals | PnL | WR | Median duration | Median return/day |
|---|---|---|---|---|---|
| 1 | 66 | +$29.24 | 84.8% | 2.4h | 9.0%/day |
| 2 | 28 | +$62.76 | 89.3% | 14.6h | 2.4%/day |
| 3 | 12 | +$11.65 | 83.3% | 72.6h | 0.4%/day |
| 4 (native only) | 11 | **+$22.41** | **100%** | 44h | 0.2%/day |
| 6 (legacy config) | 1 | +$4.82 | 100% | 21h | — |

Native L4 deals are 11-for-11. Deep layers are not where losses live — they're where **time** lives. Capital velocity collapses ~45× from L1 to L4. That's the martingale bargain working as intended: depth buys certainty at the price of duration. The optimization frontier is therefore not "avoid depth" but "spend less calendar time at depth" — which is a coin-selection problem (§3.5) and a grid-geometry question (C1: the deployed shrinking layers make TP recovery *slower* than the documented grid would).

### 3.4 Per-coin performance

| Coin | Deals | WR | PnL | Avg ret | Avg dur | PnL per 1k capital-hours | Verdict |
|---|---|---|---|---|---|---|---|
| TAO | 17 | 100% | +$72.40 | 6.25% | 34h | 1.3 | ⭐ Star — frequency AND magnitude |
| ASTER | 10 | 100% | +$23.75 | 1.41% | 42h | 0.2 | Profitable but capital-hungry (30% of all capital-hours for 16% of native PnL) |
| INJ | 23 | 91% | +$19.84 | 1.24% | 33h | 0.4 | Reliable workhorse |
| TON | 9 | 89% | +$5.72 | 1.03% | 3.8h | 1.9 | Fast cycler — high velocity |
| NEAR | 3 | 100% | +$5.91 | 3.29% | 17h | 1.8 | Efficient |
| JTO | 13 | 85% | +$6.82 | 1.01% | 34h | 0.3 | Mediocre velocity |
| DYDX | 7 | 71% | +$5.36 | 1.99% | 52h | 0.2 | Slow |
| FET/JUP/GRASS | 6 | 100% | +$1.59 | ~1% | <4h | 2.3–10.5 | Tiny sample, excellent velocity |
| PYTH | 4 | 25% | +$0.04 | -0.06% | 52h | 0.0 | **Capital trap** — 5.5% of capital-hours for zero |
| HYPE (native) | 15 | 80% | +$0.44 | — | 55h | ~0.0 | Capital trap — high duration, churn |
| ENA (native) | 4 | 100% | +$1.64 | — | — | — | Native record fine; the -$72 was the reset |

**Capital traps (high duration, low PnL/capital-hour): PYTH, HYPE, ASTER (relative), DYDX. Fast cyclers: TON, FET, GRASS, JUP, TAO.** The pattern matches the scanner's own `capital_freedom` concept — the metric exists; it's whether allocation weights it hard enough.

### 3.5 Scanner cross-reference

- Current 30d rankings top-list: AAVE (15.98), JUP (12.39), **TAO (11.30)**, UNI, CRV. TAO — the live book's best coin — is top-3 ranked. JUP scored high and its 1 live deal cycled in 0.6h. Directional validation.
- Correlation of current 30d score vs. realized PnL/deal across traded coins: **+0.39** (weak-positive; caveat — today's score vs. historical trades is not a proper walk-forward).
- **Gap:** several traded coins (JTO, DYDX, PENDLE, GRASS, PYTH, ONDO, HYPE, ENA) are absent from current mature 30d rankings — the universe the bot traded and the universe the scanner now ranks have drifted (maturity gates, data coverage). Both biggest capital traps (PYTH, HYPE) are unranked, meaning the system can't currently *learn* to avoid them via scores.
- **Structural caveat (C1):** the sim grids a different strategy than live trades, so score fidelity has a hard ceiling until grids are unified.
- Trend multiplier: inert in practice (M5) — allocation is effectively raw-score-proportional today.

### 3.6 Capital efficiency

- **Time-weighted deployed capital: $131.7 (~37% of average equity).** Peak deployed: $555 across 8 concurrent deals (early-era tier caps).
- The deployed grid's own ceiling is ~76% of allocation (C1), and one-slot-one-deal means idle time between TP and next entry compounds. Roughly speaking, **the system earns its ~1.86%/deal on only about a third of the bankroll** — utilization, not win rate, is the dominant lever on portfolio-level returns.
- The 10% reserve pool is never tapped by any code path (M7) — pure drag at this equity tier.

---

## 4. Optimization Recommendations (prioritized)

**P0 — Correctness fixes (this week; small, isolated diffs; spec → approval → pre-flight → one fix per restart, per Rules #19–21):**
1. Define or remove `_prune_stale_coin_after_tp` (C2).
2. Fix `client.exchange → client._exchange` and `self._aster_symbol → self.client._aster_symbol` in both liquidity-filter sites (H1); add a Telegram alert to the except blocks.
3. Fix the 1000-prefix double-descale in `create_market_buy` (H2).
4. Bot stopped → backup → `reconcile_trades.py --fix-ids` (M3).
5. Delete or rewrite `_evaluate_regime` (M1).

**P1.5 — Overflow Entry v2 (H4):** implement `overflow-entry-v2-soft-ceiling.md` after the P0 fixes and the C1 grid decision (it depends on both — the working liquidity filter and the canonical L1 cost). This is the deposit-deployment feature the weekly-capital product model requires; today that capital strands whenever all grids are maxed and still top-ranked.

**P1 — One grid, one truth (highest-impact structural fix):** resolve C1 by decision, not by patch. Recommended direction: **(b) canonize the deployed conservative grid** — it has real-money evidence behind it (116 native deals, 87.9% WR, max native loss -$3.80), whereas the documented 325%-of-allocation grid has only backtest support and requires top-up plumbing that currently over-grants. Re-run the grid-optimization backtest under the true 30/21/15/10 geometry to confirm the TP 3.0%/4L conclusion still holds, update §5.2/§7.6 and `_remaining_grid_cost`, and rebuild the scanner sim on the same sizing function. Whatever is decided, extract `GridModel` (F1) so this class of drift is extinct.

**P2 — Capital utilization program (biggest return lever):** with 37% time-weighted deployment, target the idle two-thirds before adding capital. Ordered by risk: (i) fold the untouched reserve into active below $10K (config change); (ii) re-weight allocation toward realized velocity (F2) so slots spend less time in PYTH-class traps; (iii) only then consider BO% or slot-count increases — and model drawdown-defense headroom first, since idle cash is also the grid's ammunition.

**P3 — Codify "never force close" beyond Rule #34:** the -$103.83 was operator-initiated through commands that still exist (`_force_close_coin`, `_force_close_all`, CLOSE/CLOSEALL). Add a typed confirmation (e.g., `CLOSE ENA CONFIRM -LOSS`), a Telegram warning that quotes the current unrealized PnL before executing, and — the real fix — a **migration runbook**: upgrades use `WIND_DOWN` (already implemented: blocks new entries, positions exit via TP naturally) or a state-preserving restart, never liquidation. The system already contains the right tool; the incidents happened because the runbook didn't mandate it.

**P4 — Record spread-reject round-trips** (M2) as ledger `pnl_adjustment` entries or zero-duration trades.

**P5 — Fee audit** (M4) before Hyperliquid cutover, so the fee step-change is modeled, not discovered.

**P6 — Trend multiplier rebuild** (M5): least-squares slope, verify snapshot accumulation, surface the distribution in the daily Telegram summary.

**P7 — Make silent failures loud (monitoring gaps):**
- Startup self-test: after init, verify every method referenced by `_execute_action`/`_handle_command` exists (`getattr` sweep) — would have caught C2 and H1 on day one; complements the Rule #19 import test, which cannot catch attribute errors.
- Alert when an engine has an open position, `layer_count < max`, and `engine.capital == 0` for >1 cycle (grid-freeze detector — the Rule #36 incident class).
- Alert when any fail-open handler fires (liquidity filter, scanner load, rebalance) more than once per day.
- Deal-duration watchdog: Telegram notice when a position exceeds e.g. 7 days at max depth (information only — no action, per Rule #34).

**P8 — SQLite trade store** (§16 migration path) before any second account; CSV identity issues in M3 are the early warning that per-file ledgers are at their limit.

---

## 5. New Feature Proposals

**F1 — Shared `GridModel` module** *(complexity: medium, risk: low if introduced read-first)*
One class defining layer sizes, trigger prices, TP, and cumulative cost — imported by `v14_dca_engine`, `v14_cycle_scanner`, and `_remaining_grid_cost`/`_top_up_engine_capital`. Kills the C1 drift class permanently and makes future grid experiments (profile changes) single-point. Introduce by first asserting parity with the current engine in a shadow test, then swapping call sites one restart at a time.

**F2 — Realized-velocity feedback into allocation** *(complexity: medium, risk: medium — changes capital routing)*
The live book now contains its own ground truth: PnL per capital-hour by coin (TON 1.9, TAO 1.3 vs. PYTH 0.0). Blend the scanner's simulated score with a live realized-velocity term (e.g., `final = sim_score × (0.5 + 0.5 × normalized_realized_velocity)` once a coin has ≥5 live deals). This is the literal embodiment of the Automated Learning Loop — the system's own trades tuning its own coin selection — and it directly attacks the capital-trap pattern the scanner currently can't see (PYTH/HYPE are unranked). Requires the SQLite store (P8) or a small stats cache to be clean.

**F3 — Short-side readiness for Hyperliquid** *(complexity: high, risk: high — full spec required)*
Current reality: a confirmed SHORT regime idles the live bot entirely (longs gated, SHORT_OPEN rejected, H3 landmine in sync). Given the ~3-up/1-down cycle shape, this is tolerable *now* and wrong to rush — but the top-detection stack exists precisely to call that transition, and the platform's value proposition during the bear year depends on it. Sequence: fix H3 → short deal keys in TradeTracker (`:short` scaffolding already exists) → short TP orders (trailing-stop-buy) → paper-validate through a full simulated flip → live. Target: specced before Hyperliquid cutover, deployed well before top conviction climbs.

**F4 — Migration wind-down mode (`MIGRATE` command)** *(complexity: low, risk: low)*
A first-class Telegram command that: enters WIND_DOWN, reports open positions + distance-to-TP, and confirms when flat so the upgrade can proceed. Converts P3's runbook into a button. The three-figure reset losses never happen again by construction.

**F5 — Paper trailing-TP simulation** *(already specced: paper-trailing-tp-simulation.md)*
Endorsed, with priority raised: the scanner sim's optimistic TP fill (`high >= tp → filled at tp`) is a third TP model beyond paper (candle close) and live (0.2% trailing callback). Whatever unified GridModel emerges (F1) should own the TP fill model too.

**F6 — Daily "silent failure" digest** *(complexity: low)*
One Telegram message per day: count of swallowed exceptions by site, fail-open activations, scanner age, snapshot-history length, trend-multiplier spread, zombie slots. The theme of this audit is that everything that broke, broke *quietly* — this is the cheap immune system.

---

## 6. Architecture Readiness Score — Cloud Migration

### Score: **6 / 10** for the Linux lift of the current system; effectively **4 / 10** for the full Hyperliquid production target.

**What's genuinely ready (earns the 6):**
- Runner respects `AIT_CANDLES_DB` / `AIT_SCANNER_JSON` env vars; no hardcoded Windows paths in the audited Python (prior-audit H1/H2 resolved in this file).
- File lock has a working `fcntl` branch; PID handling is cross-platform; UTF-8 wrappers are win32-gated no-ops on Linux.
- `run_candle_collector.sh` exists; the migration guide's systemd/provisioning sections are concrete and correct.
- Exchange credentials fail fast when env vars are missing (winreg fallback is silent no-op, validated at init).
- State persistence + DEX-as-truth startup means the bot can be killed/moved/restarted with confidence — the hardest migration property is already proven.

**Blockers (why not higher):**
1. **`run_v14_portfolio_live.py` (Hyperliquid) does not exist.** `AsterPerpClient` is Aster-specific: `ccxt.aster` hardcoded, Binance-style `TRAILING_STOP_MARKET` params, `positionSide: BOTH`, the null-market monkey-patch, and 1000-prefix logic. Hyperliquid's CCXT surface (vault/wallet auth, order types, trailing-stop support or lack thereof) requires a genuine port, not a config swap. TP mechanics may need re-design if HL lacks native trailing stops. **This is the migration's critical path.**
2. **P0 bug list (C2, H1, H2)** — migrating known-broken silent paths to a new environment compounds diagnosis difficulty. Fix on Windows first, verify 24h (Rule #6), then move.
3. **C1 grid decision** should precede migration — re-basing the scanner and docs while also changing exchanges violates the one-change-per-restart discipline (Rule #20) at architecture scale.
4. **Watchdog and dashboard sync are PowerShell/VBS** — guide covers systemd equivalents but they're unwritten; the fresh-clone sync approach (Rule #28) needs a bash port.
5. **Windows↔cloud dual-candles.db** plan is sound but the scanner JSON handoff between machines (who produces `cycle_scanner.json` the cloud bot reads?) needs one explicit decision in the guide's D1–D6 list.
6. **Decisions D1–D6 all still pending** per the guide itself.

**Recommended sequence:** P0 fixes → 24h audit → C1 grid decision + doc update → HL exchange-client spec (with H3 short-sync fix folded in) → Linux port of Aster bot as dress rehearsal (it's the running system; moving it validates systemd/lock/env plumbing with zero exchange risk) → Hyperliquid runner → paper-parallel on HL → cutover.

---

## Appendix A — Data quality notes
- 4 zero-duration trades (deals 11, 64, 72, 78) — same-cycle open/close; small losses; consistent with immediate-TP or manual closes, benign.
- 4 trades with `recorded_at` 1–47h after `close_time` — matches TP-recovery-while-down; spot-check against exchange fills once.
- 10 oldest rows lack proceeds/fee/fill_price/recorded_at (pre-schema-extension era) — expected.
- Peak concurrent deployed ($555) briefly exceeds contemporaneous equity — likely an artifact of exchange-truth invested overrides on overlapping deals; resolves itself under the SQLite store with per-fill records.

## Appendix B — Hard-rules compliance spot-check
Rules #1 (recorded_at), #26/#27 (immutable seed), #29 (append-only CSV, atomic writes), #30/#31 (no unrealized PnL in detection; idempotent ledger), #32 (entry/exit gate separation + rollback), #34 (no force closes — in code via `FORCE_CLOSE_ON_SIGNAL=False` and orphan-TP; operationally still exposed via manual commands → P3), #35 (open_deals authoritative for layers), #36 (top-up implemented — but sized to the wrong grid, see C1). **Rule #14 (never silence errors) is the most-violated rule in spirit:** the fail-open handlers around the liquidity filter, scanner loads, and rebalance are where every silent failure in this report hid.
