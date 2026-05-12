# Grid Optimization: TP 3.0% + 4-Layer Cap

**Date**: 2026-05-12  
**Status**: DEPLOYED — 2026-05-12 16:20 PDT. Commit `62b26e15a`. Bot PID 9964.  
**Risk**: Medium (modifies live trading parameters, open positions affected)  
**Backtest**: Portfolio-level sim shows +26.3% PnL vs baseline ($23,772 vs $18,824 over 90 days)

---

## Summary

Change the V14PM live bot's grid parameters:
- **TP**: 1.5% → **3.0%**
- **Max Layers**: 12 → **4**
- Deviation (1.5%) and multiplier (1.5x) unchanged — backtests showed no benefit from changing these.

---

## Current Open Positions (at time of spec)

| Coin | Side | Layers | Avg Entry | Current TP | Invested | Unrealized PnL |
|------|------|--------|-----------|------------|----------|----------------|
| TON/USDT | Long | 3 | $2.4020 | $2.4380 (+1.5%) | $96.32 | -$3.04 |
| JUP/USDT | Long | 1 | $0.2529 | $0.2566 (+1.5%) | $108.22 | -$8.57 |
| PENDLE/USDT | Long | 2 | $2.0743 | $2.1054 (+1.5%) | $89.19 | -$1.53 |
| ONDO/USDT | Long | 2 | $0.4267 | $0.4331 (+1.5%) | $81.50 | -$6.67 |

All 4 positions are currently underwater. **Total unrealized: -$19.81**

---

## Open Position Handling — CRITICAL DECISION

### Option A: Grandfather existing orders (RECOMMENDED)
- **Existing positions keep their 1.5% TP targets** — no change to open orders on Aster
- **New positions opened after deploy** use 3.0% TP
- The engine already calculates TP from `eng.cfg.DCA_TP_PCT` at order placement time
- Existing TP orders (trailing stops) on Aster are already placed and will fill at their current activation prices
- **Zero monetary risk**: No orders are cancelled or modified. Current TPs remain closer to market, meaning they fill sooner and release capital for new deals at 3.0%.

### Why NOT Option B (update all open TPs to 3.0%):
- TON is at $2.3248, current TP is $2.4380 (+4.9% away). Moving TP to $2.4740 (+6.4% away) means waiting longer while already 3 layers deep
- JUP is at $0.2337, current TP is $0.2566 (+9.8% away). Moving TP to $0.2605 (+11.5% away) when already -7.6% underwater
- ONDO is at $0.3915, current TP is $0.4331 (+10.6% away). Moving TP to $0.4395 (+12.3% away) when already -8.2% underwater
- **Moving TPs further from market on underwater positions = longer capital lock + higher risk of extended drawdown**
- These positions were entered at 1.5% TP grid economics — changing the rules mid-deal is not strategy, it's hoping

### Implementation for Option A:
- The config change applies to `V14Config.DCA_TP_PCT` and `V14_PROFILES['high']['DCA_TP_PCT']`
- On next bot restart, existing engines restore from state with their current `long_tp` values
- `_place_tp_order()` reads `eng.cfg.DCA_TP_PCT` but only recalculates if the exchange entry differs from engine entry (exchange-as-truth path). For existing positions already on the exchange, the TP was placed pre-change and remains on the order book
- **Key**: The trailing stop orders are already live on Aster with specific activation prices. They don't re-read config. They fill when price hits their stored activation price.
- New L1 entries after restart will use the new 3.0% TP

### Edge case: DCA layers added to existing positions
- If TON drops further and hits L4 (the new max), the engine recalculates `avg_entry` and `long_tp`
- `long_tp = new_avg_entry * (1 + DCA_TP_PCT)` — this WILL use the new 3.0% value
- The existing TP order gets cancelled and replaced (standard behavior in `_place_tp_order`)
- **This is correct behavior**: the new layer changes the economics of the deal, so a new TP at the new rate is appropriate
- With 4L cap and 3.0% TP, the new TP after averaging down will be closer to market than the old 1.5% TP on the higher avg entry

---

## Files to Change

### 1. `trading/spot/v14_lifecycle_engine.py` — Profile definition
```python
# BEFORE (line 58-65):
'high': {
    'leverage': 1.5,
    'DCA_BO_PCT': 0.40,
    'DCA_SO_DEVIATION': 0.015,
    'DCA_SO_MULTIPLIER': 1.5,
    'DCA_MAX_LAYERS': 12,
    'DCA_TP_PCT': 0.015,
},

# AFTER:
'high': {
    'leverage': 1.5,
    'DCA_BO_PCT': 0.40,
    'DCA_SO_DEVIATION': 0.015,
    'DCA_SO_MULTIPLIER': 1.5,
    'DCA_MAX_LAYERS': 4,
    'DCA_TP_PCT': 0.030,
},
```
**Impact**: All engines using profile='high' (live PM, paper PM, backtests) pick up the new values.

### 2. `trading/spot/engine/v14_dca_engine.py` — Base config default
```python
# BEFORE (line 56-60):
DCA_SO_DEVIATION = 0.025     # 2.5% between safety orders
...
DCA_MAX_LAYERS = 8           # Max safety orders

# AFTER:
DCA_SO_DEVIATION = 0.025     # 2.5% between safety orders
...
DCA_MAX_LAYERS = 8           # Max safety orders (base; profiles override)
```
**No change needed**: The base `V14Config` defaults (8 layers, 1.5% TP) are only used when no profile is applied. The high profile overrides these. Leave base defaults as-is to avoid unintended side effects on other engines (V14 single-coin, backtests using defaults).

### 3. `trading/spot/run_v14_portfolio_live_aster.py` — Hardcoded fallbacks
```python
# Line 1089 — exchange sync TP calculation:
tp_pct = eng.cfg.DCA_TP_PCT if hasattr(eng, 'cfg') and hasattr(eng.cfg, 'DCA_TP_PCT') else 0.015

# Line 1440 — TP order placement:
tp_pct = eng.cfg.DCA_TP_PCT if hasattr(eng, 'cfg') and hasattr(eng.cfg, 'DCA_TP_PCT') else 0.015
```
**Change**: Update fallback value from `0.015` to `0.030` on both lines. This only fires if the engine config object is somehow missing (defensive code), but should match the intended value.

```python
# AFTER (both lines):
tp_pct = eng.cfg.DCA_TP_PCT if hasattr(eng, 'cfg') and hasattr(eng.cfg, 'DCA_TP_PCT') else 0.030
```

### 4. `trading/spot/run_v14_portfolio_live_aster.py` — Reserve pool layer threshold
```python
# Line 2180:
pool = "reserve" if layer >= 6 else "active"
```
**NO CHANGE.** With max 4 layers, this threshold is now unreachable — all layers draw from active pool. This is safe: the reserve pool stays intact as a buffer. Changing it would introduce new untested behavior. Leave it.

### 5. `trading/spot/run_v14_portfolio_live_aster.py` — Docstring/comments
```python
# Line 26:
#   - Grid: High (BO=40%, Dev=1.5%, Mult=1.5x, 12 layers, TP=1.5%)

# AFTER:
#   - Grid: High (BO=40%, Dev=1.5%, Mult=1.5x, 4 layers, TP=3.0%)
```

### 6. `docs/d-984ae0d4ab9dc1a5.html` — Dashboard display
Three hardcoded references:
```javascript
// Line 772 — Risk params display:
'<div class="rp-val">'+(profile==='high'?'12':'10')+'</div></div>'+
// AFTER:
'<div class="rp-val">'+(profile==='high'?'4':'10')+'</div></div>'+

// Line 773 — TP display:
'<div class="rp-val">1.5%</div></div>'+
// AFTER:
'<div class="rp-val">3.0%</div></div>'+

// Lines 860, 945 — Max layers for grid meter:
var maxLayers=(S.profile==='high')?12:10;
// AFTER (both occurrences):
var maxLayers=(S.profile==='high')?4:10;
```

---

## Upstream/Downstream Impact Analysis

### Upstream (feeds INTO the grid):
| Component | Impact | Action |
|-----------|--------|--------|
| Scanner (`v14_cycle_scanner.py`) | None — selects coins, doesn't use grid params | No change |
| Capital Router (`v14_capital_manager.py`) | None — allocates $, doesn't know grid depth | No change |
| Signal Stack (`v13_signals.py`, `v13_router_engine_v2.py`) | None — drives phase transitions, not grid | No change |
| Candle Collector | None | No change |
| CFGI client | None | No change |

### Downstream (reads FROM the grid):
| Component | Impact | Action |
|-----------|--------|--------|
| Dashboard HTML | Hardcoded "12 layers" and "1.5% TP" | **Update** (Change #6) |
| Dashboard sync (`sync_dashboard.ps1`) | None — copies files, no grid logic | No change |
| Trade tracker / CSV | None — records what happened, not params | No change |
| Telegram notifications | Dynamic — reads from engine state | No change |
| Paper PM bot | Uses same `V14_PROFILES['high']` | **Will change automatically** — verify paper results after deploy |
| V14 single-coin live (Aster) | Uses `PRODUCTION_PROFILE = "high"` in its own runner | **Check**: Does `run_v14_live_aster.py` also use `V14_PROFILES`? |
| V14 Paper (Hyperliquid) | Uses `_make_v14_config(profile)` | **Will change automatically** |
| V14-ETF Paper | Uses `_make_v14_config(profile)` | **Will change automatically** |
| Backtests (`_tp_backtest.py`, etc.) | Hardcoded params — won't change | No change needed |
| Incident schema | None | No change |

### V14 Single-Coin Live Bot (ASTER/USDT) — ALSO AFFECTED:
`run_v14_live_aster.py` imports `V14_PROFILES` and defaults to `profile='high'` (line 53). It creates its engine via `V14LifecycleEngine(symbol=SYMBOL, capital=capital, profile=profile)` which calls `_make_v14_config('high')` — same path as PM bot.

**This bot WILL also get 4 layers / 3.0% TP on next restart.**

Comment at line 526 says: `High profile DCA params (Dev=1.5%, 12 layers, TP=1.5%) still apply.` — needs updating.

**Decision needed**: Is this acceptable for ASTER/USDT single-coin? It's a different trading dynamic (single coin vs portfolio rotation). The backtest was run on scanner coins, not ASTER specifically. If you want ASTER to stay at old params, we need to either:
- Give it its own profile (e.g., 'high_legacy')
- Or hardcode overrides in `run_v14_live_aster.py`

---

## Deployment Plan

### Pre-deploy:
1. **Verify V14 single-coin bot** (`run_v14_live_aster.py`) — does it share the profile? If yes, decide if ASTER/USDT should also get new params.
2. **Git commit** all changes on a branch, review diff.

### Deploy:
1. **Stop the live PM bot** (kill Python PID)
2. **Pre-flight check**: `python -c "from trading.spot.run_v14_portfolio_live_aster import V14PortfolioLiveAster; print('OK')"`
3. **Verify open positions** on Aster haven't changed during stop
4. **Start the bot**: `Start-ScheduledTask -TaskName "V14PMLiveAster"` (or manual command)
5. **Monitor first 10 minutes**: Verify existing TP orders are NOT cancelled/replaced. New entries should show 3.0% TP in Telegram notifications.

### Post-deploy verification:
- [ ] Dashboard shows "4 layers" and "3.0% TP" in risk params
- [ ] Existing TON/JUP/PENDLE/ONDO TP orders unchanged on Aster
- [ ] Next new deal opens with 3.0% TP (visible in Telegram notification)
- [ ] If existing deal adds a DCA layer, new TP is at 3.0% (correctly recalculated)
- [ ] Paper PM bot picks up new params on next restart
- [ ] status.json shows correct `next_tp_price` for new vs existing deals

---

## Rollback Plan

If issues arise:
1. Stop bot
2. Revert `V14_PROFILES['high']` to `DCA_MAX_LAYERS: 12, DCA_TP_PCT: 0.015`
3. Revert fallbacks in `run_v14_portfolio_live_aster.py`
4. Revert dashboard
5. Restart bot — existing positions resume with old params

No data migration needed. Engine state persists `long_tp` per coin, and `_place_tp_order` recalculates from config on each call.

---

## Backtest Evidence

Portfolio-level simulation (3 slots, 10 coins, 90 days, real candles, Hyperliquid fees):

| Config | Deals | PnL | ROI | Avg Dur | Avg Layers | vs Baseline |
|--------|-------|-----|-----|---------|------------|-------------|
| Baseline (1.5% TP, 12L) | 147 | $18,824 | 37.65% | 41.5h | 1.80 | — |
| **3.0% TP, 4L cap** | **79** | **$23,772** | **47.54%** | 73.7h | 2.14 | **+26.3%** |

Higher return per deal more than compensates for fewer deals. Capital efficiency (PnL per $1K per hour) improved by 40%.
