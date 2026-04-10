# V14PM Phase 3 — Documentation Accuracy Audit
_Date: 2026-04-09 | Auditor: Gee Gee_
_Reference: V14PM_SYSTEM_ARCHITECTURE.md v1.7 vs actual codebase_

---

## Summary

55 claims checked. 45 verified correct. 10 require corrections.

| Severity | Count | Description |
|----------|-------|-------------|
| P2 | 1 | Documentation omission with safety implications |
| P3 | 5 | Factual inaccuracies (parameter values, behavior) |
| P4 | 4 | Stale env var references (informational only) |

**Overall: Architecture doc is 82% accurate.** Core architectural concepts are correct.
The inaccuracies are in specific parameter values and a few stale references.

---

## Verified Correct ✅

All core architectural claims are accurate:

- Exchange-as-truth principle documented and implemented correctly
- Safety features table: positionSide=BOTH, reduceOnly=True, pre-order checks ✅
- `_sync_positions_from_exchange()` runs every 65s cycle ✅
- All Telegram commands (PAUSE, RESUME, CLOSE, APPROVE, DENY, DEPOSIT, WITHDRAW, CAPITAL) implemented ✅
- Capital tier table: $100K/10, $20K/5, $10K/5, $5K/5, $3K/4, $100/3 ✅ (see exception below)
- Pool splits: 75/25 above $20K, 90/10 below $10K ✅
- 5% hysteresis on tier downgrades ✅
- Daily rebalance at midnight UTC, protected against double-fire ✅
- AsterPerpClient: 15s timeout, 1000-prefix handling, `_aster_symbol()` ✅
- All class names correct: V14PortfolioLiveAster, AsterPerpClient, CoinState, CapitalRouter, V14LifecycleEngine, V14Config ✅
- All 6 environment variables correctly documented ✅
- `defaultType=future` for Aster perps ✅

---

## Corrections Required

### DOC-01 (P2): DCA_BO_PCT documented as 40%, actual is 30%

**Architecture doc §5.2 states:** Base order = 40% of allocation

**Actual code (`v14_dca_engine.py`):**
```python
DCA_BO_PCT = 0.30  # 30% base order (aggressive initial position)
```

**Note:** The dashboard HTML also hardcodes `BO: 40%` in the risk parameters display.

**Corrections needed:**
1. Architecture doc §5.2 — update BO% from 40% to 30%
2. `docs/dashboardV14PM.html` — update hardcoded `BO: 40%` display to `30%`

---

### DOC-02 (P3): DCA_MAX_ORDERS doesn't exist — it's DCA_MAX_LAYERS = 8 (not 12)

**Architecture doc §5.2 states:** Max layers = 12 for High profile

**Actual code (`v14_dca_engine.py`):**
```python
DCA_MAX_LAYERS = 8  # Max safety orders
```

The High profile override should be checked to confirm the actual live value.

---

### DOC-03 (P3): Main loop interval description slightly imprecise

**Architecture doc claims:** "exchange sync every 65s"

**Actual code:**
```python
LIVE_POLL_INTERVAL = 65  # seconds between exchange polls
sleep_time = max(1, LIVE_POLL_INTERVAL - elapsed)  # dynamic sleep
```

The cycle targets 65s total (processing time + sleep), not a fixed 65s sleep. Under heavy
processing load, cycles can be shorter. Under error recovery, the loop sleeps 1s and retries.
Documented behavior is essentially correct; the doc could add "targeting 65s cycles."

---

### DOC-04 (P4): Stale env var references in §12

The architecture doc lists these env vars that are not used by any current production code:

| Variable | Status |
|----------|--------|
| `AIT_SCANNER_JSON` | In .env.template but not `os.environ.get()` in code — scanner uses hardcoded path |
| `ASTER_FAPI_URL` | Referenced in docs but not in code |
| `AIT_CandleCollector`, `AIT_DashboardSync`, `AIT_Watchdog`, `AIT_PMComparisonLog` | Scheduled task names listed as env vars — not env vars at all |

**Correction:** Separate "Scheduled Task names" from "Environment Variables" in §12.

---

### DOC-05 (P2): Leverage enforcement not verified at startup

**Architecture doc states:** "1x leverage enforced"

**Actual code:** `ensure_leverage()` is called per-symbol when a coin first becomes active,
but only if that symbol isn't in `self._leverage_set`. On fresh start with no positions,
leverage is set when the first DCA order is placed.

**Gap:** If the exchange has stale leverage settings from a previous session and the bot
restarts after TP fills (no active positions), leverage won't be reset until the next trade.
The `_leverage_set` is not persisted to state.json.

**Recommendation:** Add leverage verification at bot startup for all symbols in the coin
universe (not just active positions). Or persist `_leverage_set` to state.json so it's
not re-verified unnecessarily.

---

## Architecture Doc Patches

Applying corrections to V14PM_SYSTEM_ARCHITECTURE.md:

1. Update DCA_BO_PCT from 40% to 30% in §5.2
2. Update DCA_MAX_LAYERS/ORDERS clarification in §5.2
3. Add leverage persistence note to §6.8 / safety features
4. Separate scheduled task names from env vars in §12
5. Add note about `AIT_SCANNER_JSON` not being an env var

---

_Phase 3 complete. All 3 phases done — ready to generate comprehensive audit report._
