# Mini Spec: Candle Replay Guard

**Date**: 2026-05-08
**Status**: APPROVED (verbal approval via Telegram)
**Severity**: High (causes real money loss on every restart with gap >5min)

---

## Problem

When the bot restarts after being down, it fetches all candles since `last_candle_ts` (saved in state.json). Each candle runs through the engine tick, which may generate BUY actions. These are executed as real market buys at CURRENT prices, but the engine calculated them against HISTORICAL candle prices. The spread between historical and current price causes immediate spread-reject → close, losing money on the round-trip.

Example: Bot down 45 min. 45 stale candles replayed. Each BUY executed at current market price ($2.03) vs engine price ($1.92) = 571bps spread → reject → sell back → lose ~$0.10 per trip. 113 trips = ~$11.30 lost.

## Root Cause

Line 3387: `_execute_action(sym, cs, action)` is called for ALL candles, including stale ones. The engine correctly processes the tick (updating indicators, state), but the resulting BUY/SELL actions should NOT be sent to the exchange when the candle is old.

Fresh engines (no saved state) already handle this correctly at line 974: `cs.last_candle_ts = int(time.time() * 1000)` — skipping all history.

## Fix

Add a staleness check before `_execute_action()`. If the candle timestamp is more than 5 minutes old, let the engine tick run (so indicators stay warm) but suppress the action execution.

### Location
`run_v14_portfolio_live_aster.py`, line ~3383 (inside the candle processing loop)

### Change
Before:
```python
                            if actions:
                                logger.info(f"Engine actions for {sym}: {actions}")
                                for action in actions:
                                    self._execute_action(sym, cs, action)
```

After:
```python
                            if actions:
                                candle_age_s = (time.time() * 1000 - ts_ms) / 1000
                                if candle_age_s > 300:  # 5 minutes
                                    logger.info(
                                        f"REPLAY SKIP {sym}: {len(actions)} action(s) suppressed "
                                        f"(candle age {candle_age_s:.0f}s)"
                                    )
                                else:
                                    logger.info(f"Engine actions for {sym}: {actions}")
                                    for action in actions:
                                        self._execute_action(sym, cs, action)
```

### Why 5 minutes
- Normal poll interval is 65s
- Candles are 1h
- A candle from 5+ minutes ago is definitely stale from a restart gap
- Current candles are always <65s old (fetched within the poll cycle)

### Upstream impact
None. Engine still processes all ticks. Indicators, phase, state all stay current.

### Downstream impact
- Suppressed actions mean no BUY/SELL during catch-up = no spread reject churn
- Once candles catch up to current time (<5 min old), normal execution resumes
- Open positions from before the restart keep their TP orders (already on exchange)
- No trades recorded during catch-up = CSV stays clean

### Files modified
`run_v14_portfolio_live_aster.py` — 1 location, 7 lines changed
