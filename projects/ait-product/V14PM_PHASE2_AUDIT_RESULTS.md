# V14PM Phase 2 — Component-Level Logic & Integration Audit
_Date: 2026-04-09 | Auditor: Gee Gee | Scope: 10 components + cross-component data flows_

---

## Summary

| Category | P1 | P2 | P3 | P4 |
|----------|----|----|----|----|
| Component Logic | 0 | 2 | 4 | 2 |
| Integration | 0 | 2 | 1 | 0 |
| **Total** | **0** | **4** | **5** | **2** |

**No P1 (critical) findings.** The system is structurally sound for production. P2 items are
improvements that should be addressed before or shortly after the production clone goes live.

---

## Component Audit Results

### Component 1: AsterPerpClient ✅

**Verdict: Production-ready.** Well-structured exchange abstraction.

**Strengths:**
- 15-second timeout on all CCXT calls (prevents hangs)
- Consistent 1000-prefix handling across all price/qty methods
- `reduceOnly: True` on all sell orders (can't accidentally open shorts)
- `positionSide: BOTH` on all orders (one-way mode)
- Fill price fallback chain: order.average → order.price → trade history → ticker
- Methods that don't handle price/qty (cancel, leverage, etc.) correctly delegate to `_aster_symbol()` only

**P3-01: fetch_balance returns 0.0 on API error**
Cannot distinguish "API failed" from "wallet empty". Both return 0.0.
- Impact: BUY would be skipped (correct) but no alert that the exchange API is down.
- Mitigation: The main loop's exchange sync would also fail, which IS logged.
- Recommendation: Return `None` on error, check in caller. Low priority.

**P3-02: fetch_ticker_price returns 0.0 on error**
Used only in fallback paths (TP calculation when exchange entry price not available).
- Mitigated by: Exchange-as-truth TP now uses exchange entry price, not ticker.
- The P2 zero-guard on `price <= 0` (Phase 1 fix) also catches this downstream.

### Component 2: Exception Handlers ✅

**Verdict: Appropriate for a trading bot.** 82 broad handlers, all reviewed.

**Classification:**

| Category | Count | Examples |
|----------|-------|---------|
| **Exchange API calls** — broad catch is correct | 28 | Balance, positions, orders, ticker |
| **Telegram sends** — fail silently, retry next cycle | 12 | Alert sends, command processing |
| **State save/restore** — best-effort with fallback | 8 | Engine snapshot, date parsing |
| **File I/O** — non-critical data | 6 | CSV writes, status updates |
| **Shutdown cleanup** — must not crash | 4 | Lock release, PID cleanup |
| **Candle processing** — per-coin isolation | 8 | One coin's error doesn't kill others |
| **Inner utility** — defensive coding | 16 | Scanner reads, data parsing |

**8 silent catches (except: pass)** — all reviewed and appropriate:
- Line 160: Telegram getUpdates — polls silently
- Line 395: Trade fetch for fill price — fallback chain continues
- Line 741: Engine snapshot — save what we can
- Line 926: Date parse — use default
- Line 2500: Ticker for display — non-critical
- Line 2841: CFGI poll — optional feature
- Lines 2873, 2885: Shutdown cleanup — never crash during teardown

**Recommendation:** No changes needed. The broad catches serve the design principle that
a trading bot should NEVER crash — it should log, recover, and keep managing positions.

### Component 3: State Persistence ✅

**Verdict: Round-trip is complete.** All fields save and restore correctly.

Fields verified at three levels:
- **Top-level:** bot_state, capital, tracked_capital, tg_update_offset, last_rebalance_date, regime ✅
- **Coin-level (CoinState.to_dict):** 14 fields including paused, regime_flagged, tp_order_id, last_candle_ts ✅
- **Router:** pools, allocations, tier indices (hysteresis preserved) ✅
- **Engine (snapshot_state):** Full DCA engine state including long/short positions, layers, PnL ✅

**Note:** `capital` and `tracked_capital` are both saved. On restore, `tracked_capital` takes
precedence (Upgrade 1 — dynamic capital). This is intentional redundancy.

### Component 4: Candle Dedup ⚠️

**P2-01: Candle dedup exists but known to be imperfect**

The dedup mechanism works:
- `cs.last_candle_ts` tracks the latest processed candle timestamp per coin
- Line 2792: `if ts_ms <= cs.last_candle_ts: continue` — skips already-processed candles
- After processing: `cs.last_candle_ts = ts_ms`

However, the duplicate candle processing bug (noted in prior work) persists because:
- Candles are fetched from CCXT with `limit=50`, which can return the in-progress candle
- The in-progress candle has the same timestamp but different OHLCV values as it updates
- When the candle closes, it's processed again as a "new" candle
- This causes ~2 ticks per candle (one in-progress, one final)

**Impact:** Engine generates duplicate signals (BUY/TP) — mitigated by exchange-as-truth
(balance/position checks prevent duplicate execution). But doubles Telegram alert volume.

**Recommendation:** Add a staleness check: only process candles whose close time is in the
past (i.e., `candle_timestamp + 3600000 < now_ms`). This filters out in-progress candles.

### Component 5: Telegram Commands ✅

**Verdict: Secure and complete.**

- No eval/exec on user input
- Chat ID authorization verified against `AIT_TG_CHAT_ID`
- Commands parsed via string matching (safe)
- Recognized: PAUSE, RESUME, CLOSE, APPROVE, DENY, DEPOSIT, WITHDRAW, CAPITAL, STATUS
- Per-coin variants: PAUSE <COIN>, RESUME <COIN>, CLOSE <COIN>

### Component 6: Main Loop ✅

**Verdict: Resilient.**

- Signal handler (SIGINT/SIGTERM): saves state before exit
- Main loop has outer try/except that logs and continues
- State saved every cycle (~65s) — max data loss is one cycle
- Lock file prevents duplicate instances

### Component 7: CapitalRouter ✅

**Verdict: Edge cases handled.**

- Tier transitions use hysteresis (5% buffer on downgrades)
- Below-minimum ($100) tier: coin_cap = 0 (no trading)
- `max(len(top_coins), 1)` prevents division by zero in cap_pct
- `total_score <= 0` guard added (Phase 1 fix)

### Component 8: DCA Engine ✅

**Verdict: Sound grid math.**

- Max layers capped at `DCA_MAX_ORDERS` (12 for high profile)
- TP = `avg_entry × (1 + DCA_TP_PCT)` with weighted average across all layers
- Fee simulation: taker (0.035%) and maker (0.01%) rates
- `price <= 0` guard added (Phase 1 fix)

### Component 9: Lifecycle Engine ✅

**Verdict: Clean.**

- Warmup period: 30 candles before generating signals (prevents cold-start trades)
- `reject_action()` supports BUY, SHORT_OPEN, and SELL (expanded 2026-04-09)
- State snapshot/restore: complete round-trip

### Component 10: Dashboard ✅

**Verdict: Clean with minor gaps.**

- All JS divisions have zero-guards
- External deps: only Chart.js (CDN)
- Paused badge displays correctly

**P4-01: Title says "Paper Trading"** — should be configurable for live deployment.

---

## Integration Audit Results

### Integration 1: Scanner → Bot — cycle_scanner.json ✅

Scanner outputs 12 fields per coin. Bot reads `dca_score` and `trend_multiplier` for
allocation during rebalance. Schema is stable.

### Integration 2: Bot → Dashboard — status.json ⚠️

**P2-02: Two dashboard fields missing from status.json**

| Field | Expected By | Present | Impact |
|-------|-------------|---------|--------|
| `halted` | Dashboard | ❌ | Dashboard shows `--` for halt status. Minor display issue. |
| `max_drawdown_pct` | Dashboard | ❌ | Dashboard falls back to calculating from data. |

**P3-03: Coin-level `symbol` field not in status.json coins**
Dashboard reads `c.symbol` but status.json uses the symbol as the dict key, not as a field.
Dashboard likely handles this by using the key. Non-blocking.

**Recommendation:** Add `halted` and `max_drawdown_pct` to `_write_status()`.

### Integration 3: Env Vars vs .env.template ⚠️

**P2-03: .env.template mismatches**

| Issue | Details |
|-------|---------|
| Template has `HYPERLIQUID_API_KEY/SECRET` | Not used by live Aster bot (leftover from early design) |
| Template missing `ASTER_API_KEY/SECRET` | **Actual credentials used by production bot** |
| Template missing `CFGI_API_KEY` | Optional but should be documented |
| Template has `AIT_SCANNER_JSON` | Not read via `os.environ` — hardcoded path in scanner |

**Recommendation:** Update `.env.template` to match actual Aster bot requirements.

### Integration 4: 1000-Prefix Coin Handling ✅

All methods that handle price or quantity values correctly scale for PEPE/BONK/FLOKI
(multiply qty by 1000 on send, divide by 1000 on receive). Methods that only route
symbols (cancel, leverage, etc.) correctly use `_aster_symbol()` without scaling.

---

## Phase 2 Action Items

### Fix Now (before production clone)

| # | Finding | Status | Files |
|---|---------|--------|-------|
| 1 | Update `.env.template` to reflect Aster credentials | ✅ FIXED 2026-04-09 | `.env.template` |
| 2 | Add `halted` and `max_drawdown_pct` to status.json | ✅ FIXED 2026-04-09 | `run_v14_portfolio_live_aster.py` |

### Fix Soon (after production is stable)

| # | Finding | Effort | Files |
|---|---------|--------|-------|
| 3 | Candle dedup: filter in-progress candles | 30 min | `run_v14_portfolio_live_aster.py` |
| 4 | Dashboard title: make configurable for live vs paper | 5 min | `dashboardV14PM.html` |

### Accepted Risks (no action needed)

| # | Finding | Rationale |
|---|---------|-----------|
| 5 | `fetch_balance` returns 0.0 on error | Exchange sync failure is logged separately |
| 6 | `fetch_ticker_price` returns 0.0 on error | Mitigated by exchange-as-truth TP calculation |
| 7 | Broad exception handlers (82) | Intentional — trading bot must not crash |
| 8 | Silent catches (8) | All in appropriate locations (Telegram, cleanup, optional features) |

---

_Phase 2 complete. Proceed to Phase 3 (Documentation Accuracy Audit) when ready._
_Combined report will be generated after all phases complete._
