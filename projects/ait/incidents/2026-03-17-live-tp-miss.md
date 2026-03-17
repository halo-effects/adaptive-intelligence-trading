# Incident Report: Live Bot TP Miss & State Corruption
**Date:** 2026-03-17 (Tuesday)
**Severity:** Medium (real money affected, no capital loss)
**Status:** Resolved

---

## Timeline (all times PDT / UTC)

| Time (PDT) | Time (UTC) | Event |
|------------|-----------|-------|
| ~Sun 3/16 | | ASTER/USDT price wicks above TP ($0.7481) on multiple 1h candles but closes below — bot misses TP |
| 05:35 | 12:35 | Live bot restarts (gateway restart). Processes 12:00 UTC candle: close $0.7465 (MISS by $0.0017), high $0.7521 (would have HIT) |
| 05:47 | 12:47 | Brett reports Telegram unresponsive, restarts gateway |
| 06:23 | 13:23 | Brett reports JUP/USDT on V14PM paper bot also missed TP — same root cause |
| 06:28 | 13:28 | TP fill model fix applied to shared engine code (v14_dca_engine.py, v14_lifecycle_engine.py) |
| 06:36 | 13:36 | Paper bots restarted with new code |
| 06:42 | 13:42 | Brett reports ASTER live bot still has open position despite price at $0.77+ |
| 06:50 | 13:50 | Investigation: live bot running old code (in-memory), no new completed candles to process |
| 06:55 | 13:55 | Scheduled task auto-restarts live bot (Instance A — picks up new code) |
| 06:59 | 13:59 | Manual restart of live bot (Instance B — duplicate) |
| 07:00:28 | 14:00:28 | **Instance A** detects TP on completed 13:00 UTC candle, executes market sell: 223.20 ASTER @ $0.7757 ✅ |
| 07:00:58 | 14:00:58 | **Instance B** tries to sell, fails ("Insufficient ASTER: need 223.29, have 0.009"), rolls back engine state |
| 07:01 | 14:01 | Instance B writes rolled-back state to status.json — dashboard shows stale data |
| 07:05 | 14:05 | Cleanup: kill duplicates, reconcile engine state with exchange, restart single instance |
| 07:09 | 14:09 | Brett deposits $40 USDT. Capital updated $300 → $340 |
| 07:12 | 14:12 | Bot restarted, reconciliation picks up deposit (+$40.00 drift → adjusted) |
| 07:17 | 14:17 | Dashboard sync attempted — GitHub PAT expired |
| 07:27 | 14:27 | New PAT set, dashboard synced successfully |

---

## Root Cause Analysis

### Primary: TP checked candle close instead of candle high
- **File:** `trading/spot/engine/v14_dca_engine.py` → `_long_dca_tick()` / `_short_dca_tick()`
- **Bug:** `if price >= self.long_tp` where `price = candle['close']`
- **Impact:** TP only triggered when the candle *closed* above the target. Intraday wicks above TP were ignored.
- **Real-world mismatch:** In live trading, a limit sell order on the book fills instantly when price touches the level — even on a wick. The engine's close-only check was less realistic than actual exchange behavior.
- **Specific miss:** ASTER 12:00 UTC candle — close $0.7465 (below TP $0.7481), high $0.7521 (above TP). Gap: $0.0017.

### Secondary: No resting limit orders on exchange
- The live bot uses a **poll-then-react** pattern: fetch candles every 65 seconds → engine decides → market sell.
- There is no limit sell order placed on the exchange at the TP price when a position opens.
- This means TP execution depends on:
  - The bot process being alive
  - The exchange API returning candles successfully (multiple Aster API 502s observed)
  - A completed candle existing with close (now high) above TP
- **Architectural gap:** A limit sell order on the book would fill automatically, regardless of bot health.

### Tertiary: Duplicate bot instances
- The scheduled task `V14LiveAster` and a manual launch created two instances.
- Both processed the same candle. Instance A sold successfully; Instance B failed and corrupted engine state.
- The scheduled task has `MultipleInstances: IgnoreNew` but this only prevents the *task scheduler* from launching a second instance — it doesn't prevent manual launches.

---

## Fixes Applied

### 1. TP Fill Model (engine-level) ✅
**Files changed:**
- `trading/spot/engine/v14_dca_engine.py`
  - `_long_dca_tick(self, date, price, high=None)` — TP checks candle high, fills at TP price
  - `_short_dca_tick(self, date, price, low=None)` — TP checks candle low, fills at TP price
  - `run()` backtest loop — passes `row['high']`/`row['low']` from daily data
- `trading/spot/v14_lifecycle_engine.py`
  - `tick()` — extracts high/low from hourly candle dict, passes to DCA tick methods
  - `_run_daily_tick()` — reads high/low from signal pack daily data
  - All hourly and daily DCA tick call sites updated

**Design decisions:**
- TP **triggers** on wick (high/low), **fills at TP price** (limit order simulation)
- DCA layer entries still use close price (market decisions, not resting orders)
- `high=None`/`low=None` defaults = backward compatible
- Trade log `price` field now shows fill price (TP level)

**Scope:** Affects all paper bots (V14, V14-ETF, V14-PM) + backtest engine. Live bot uses real exchange fills for execution, but the TP *detection* trigger now also uses high/low.

### 2. Live Bot State Reconciliation ✅
- Killed duplicate instances
- Synced engine state with exchange reality (position closed, 0 ASTER, $329.55 USDT)
- Updated trades.csv with the successful sell (deal #4)
- Verified status.json matches exchange balance

### 3. Capital Update ✅
- `DEFAULT_CAPITAL` in `run_v14_live_aster.py`: $300 → $340
- `state.json` capital: $300 → $340
- `HEARTBEAT.md` capital reference: $300 → $340

### 4. GitHub PAT Renewal ✅
- Old `openclaw-deploy` token expired 2026-03-16
- New token set in `AIT_GITHUB_PAT` user environment variable
- Dashboard sync confirmed working

---

## Documentation Updated

| Document | Section | Change |
|----------|---------|--------|
| `projects/ait/v14-system-spec.md` | §5.1 V14 Engine Core | Added TP Fill Model description with changelog note |
| `projects/ait-product/v14-dca-architecture.md` | §DCA Grid Params | TP description updated; status checklist entry added |
| `projects/ait-product/CLOUD_MIGRATION_GUIDE.md` | §5.4 item 12 | New item: live runner must use exchange fill price, not engine TP price |
| `projects/ait/log.md` | 2026-03-17 | Full entry with root cause, files changed, impact |
| `HEARTBEAT.md` | V14 Live Bot | Capital updated to $340 |
| `trading/spot/run_v14_live_aster.py` | `DEFAULT_CAPITAL` | $300 → $340 |

---

## Documentation Still Needed

### 1. Limit Order Architecture (Priority: High — pre-live migration)
The live bot should place resting limit sell orders at the TP price when a position opens, rather than relying on poll-then-market-sell. This should be:
- Documented in `CLOUD_MIGRATION_GUIDE.md` as a requirement for `run_v14_portfolio_live.py`
- Added to `v14-dca-architecture.md` as an architectural decision
- Covers: order placement on entry, order updates on DCA layer adds (new avg entry → new TP), order cancellation on phase change

### 2. Deposit Handling (Priority: Medium)
No formal process exists for handling fresh deposits to the live account. Should document:
- How `capital` is tracked (seed + deposits)
- How reconciliation handles unexpected balance increases
- Whether PnL% should be time-weighted or simple (current: simple against total capital)

### 3. Duplicate Instance Prevention (Priority: Medium)
The scheduled task's `IgnoreNew` only prevents task-scheduler duplicates. Should document:
- PID lock file mechanism (exists in paper bots but not live)
- Warning in HEARTBEAT.md about not manually launching while task is running
- Or: add PID lock to live bot runner

---

## Financial Impact
- **Capital at risk:** $300 (now $340 with deposit)
- **Capital lost:** $0
- **Missed TP fill price:** $0.7481 (would have filled at TP level)
- **Actual fill price:** $0.7757 (market sell, 30 minutes after TP level was first breached)
- **Net effect:** +$2.76 more profit than TP would have given (lucky — price went up, not down)
- **Risk exposure:** If price had reversed after wicking above TP, the position would have remained open and potentially lost money. The miss was favorable this time but represents a real risk.

---

## Lessons Learned
1. **Candle close ≠ price touched.** Limit orders fill on touch, not on close. Paper simulation must match reality.
2. **Single-instance enforcement matters.** Duplicate bot instances cause state corruption. PID locks should be mandatory for all live runners.
3. **API reliability is a dependency.** Multiple Aster API 502 errors observed. The bot was blind during those periods. Limit orders on the exchange eliminate this dependency for TP fills.
4. **Dashboard lags engine state.** When state is corrupted, the dashboard shows wrong data until the next clean write cycle. There's no "force refresh" mechanism — it depends on the bot loop.
5. **PAT expiry is silent.** The dashboard sync fails silently when the GitHub PAT expires. Should add a cron check or expiry reminder.
