# V14PM Production Architecture — Decisions Log
_Date: 2026-03-19 | Status: All decisions locked_

---

## Decisions Made

### D1: Exchange — Aster DEX, Perp-Only
- **All trading on Aster Perpetuals** at 1x leverage
- No Spot trading. No Spot↔Perp capital transfers needed.
- Long DCA = long perp positions, Short DCA = short perp positions, same account
- Fees: Maker 0.005%, Taker 0.04% (identical to Spot; 5% discount with $ASTER)
- Funding rate exposure: negligible at DCA hold times (hours to days)
- Binance-compatible API: `fapi.asterdex.com` (REST + WebSocket)

### D2: Risk Profile — Unified (Single Profile)
- **One profile for production.** No multi-tier complexity.
- High grid, 1x leverage, 30d scanner window

| Parameter | Value |
|-----------|-------|
| Leverage | 1.0x |
| Base Order | 40% |
| SO Deviation | 1.5% |
| SO Multiplier | 1.5x |
| Max Layers | 12 |
| Take Profit | 1.5% |
| Scanner Window | 30d |
| Trend Multiplier | Yes (0.3–1.5x) |

- Risk tiers deferred until production data justifies differentiation.

### D3: Global Strategy Direction
- **All coins run one direction.** No mixed strategies (some long, some short).
- When regime flips: ALL coins flip together.
- Per-coin ROUTER replaced by **Portfolio Regime Monitor** (weighted composite).

### D4: Regime Detection — Weighted Composite (Full Universe)
- ROUTER v2 signals evaluated across **all 50 scanner coins** (not just active positions)
- Tiered alert system:
  - ~10% (5 coins) → 🟡 EARLY WARNING
  - ~25% (12-13 coins) → 🟠 STRONG SIGNAL
  - ~50% (25 coins) → 🔴 MAJORITY
- Tiered thresholds (locked):
  - 🟡 **5+ coins (~10%)** → Early Warning
  - 🟠 **12+ coins (~25%)** → Strong Signal
  - 🔴 **25+ coins (~50%)** → Majority
- Everything keeps running normally at all tiers. No automatic action.
- Brett decides when to APPROVE based on own analysis. Tiers control notification urgency.
- Top detection and bottom detection use different signal stacks (confirmed per ROUTER v2).
- 38 coins have full ROUTER signal coverage; 12 newer coins contribute to top detection only until they accumulate 600+ days of history.

### D5: Human-in-the-Loop Governance (Two-Gate)
- **Gate 1 (automatic):** Bot signals detect regime change → Telegram alert
- **Gate 2 (human):** Brett reviews → APPROVE or DENY via Telegram reply
- No timeout pressure — DENY is default if no response (safe)
- Re-alert when signal count increases or persists
- Log all signals and decisions to DB for audit trail

### D6: Graceful Direction Change (Wind-Down)
- On APPROVE: enter WIND_DOWN phase
  - **Freeze grids** — no new positions, no new DCA layers
  - **Keep TP limit orders active** — let existing trades close at profit
  - Dashboard shows wind-down status
  - Daily Telegram update with remaining positions
- On all positions closed → flip direction, deploy new grids
- **Manual override for stragglers** via Telegram command:
  - `CLOSE ZRO` — force-close specific coin at market
  - `CLOSE ALL` — force-close all remaining
  - Bot handles the exchange interaction (cancel TP, market close, record fill)
  - Never close directly on exchange UI unless bot is down

### D7: Coin Universe — 50 Coins on Aster Perps

**Carried from Hyperliquid scanner (37):**
BTC, ETH, SOL, XRP, LINK, DOGE, ADA, LTC, AVAX, DOT,
UNI, ATOM, NEAR, HBAR, INJ, FIL, CRV, SNX,
AAVE, ARB, JUP, PENDLE, STX, ZRO,
PEPE, BONK, FLOKI, JTO, PYTH, TIA, SEI, APT, SUI,
FET, TAO, HYPE,
ZEC

**New additions for Aster (13):**
ONDO, RENDER, VIRTUAL, BERA, MOVE, INIT, IP, S, EIGEN, ENA, GRASS, ORCA, TRUMP

**Dropped (not on Aster perps, 9):**
BAL, COMP, ENS, GMX, GRT, MANA, RUNE, SAND, WIF

**Notes:**
- New coins need 1h candle backfill (6 months ideal for reliable DCA scores)
- 30d scanner window naturally filters low-quality coins from active rotation
- All coins evaluated for regime signals regardless of active trading status

---

### D9: Candle Data Strategy — Binance Backfill + Aster Live
- **Historical backfill:** Binance Futures API (deep history — all 50 coins confirmed)
- **Live collection:** Aster Perp API (trade on the exchange you get prices from)
- Both stored in same `candles.db` — seamless for signal computation
- Paper bots use same unified candle data (no separate Hyperliquid feed)
- Handle 1000-prefix mapping: PEPE↔1000PEPE, BONK↔1000BONK, FLOKI↔1000FLOKI

### D10: PAUSE / RESUME Governance Override
- **PAUSE** (via Telegram): Freeze all grids immediately. No new positions, no new layers.
  - TP limit orders stay active on exchange
  - Bot keeps polling — monitors TP fills, updates dashboard
  - Same manual override: `CLOSE <COIN>`, `CLOSE ALL`
  - Watchdog sees bot as intentionally paused — no auto-restart
  - Persisted to `state.json` — survives bot restart
- **RESUME** (via Telegram): Unfreeze grids. Normal operations resume from current state.
- Different from wind-down: PAUSE has no destination. RESUME returns to pre-pause state.

### D11: Regime Alert Thresholds (locked)
- 🟡 5+ coins (~10%) → Early Warning
- 🟠 12+ coins (~25%) → Strong Signal
- 🔴 25+ coins (~50%) → Majority
- No automatic action at any tier. Human decides.

### D12: Build Approach — Add PM to Live Aster Bot (Option A)
- Start from `run_v14_live_aster.py` (proven execution layer with all live safeguards)
- Add PM components: CapitalRouter, multi-coin management, scanner integration
- Output: `run_v14_portfolio_live_aster.py`
- Retires single-coin `run_v14_live_aster.py` once PM version is proven

### D13: Testing Strategy — Phase 2 Direct (Small Capital Live)
- Skip dry-run phase — execution layer already proven on live Aster
- Launch with current capital (~$340), coin cap = 1
- Start with current ASTER position — rotate after natural TP close
- Scale up capital and coin cap once stable
- Current Aster account IS the production environment — no migration needed
- Cloud migration is reliability improvement only (later)

### D14: Regime Monitor Frequency — Daily at Midnight UTC
- Evaluate all 50 coins' ROUTER signals once per day at midnight UTC
- Matches daily candle close timing
- No hourly noise — ROUTER signals are daily/weekly by nature

---

## Still Open

| Item | Notes |
|------|-------|
| Scale-up capital for V14PM | When to increase from $340 → larger amount? Determines coin cap tier. |
| Cloud migration timing | Run on Windows initially; move to cloud server for reliability when ready. |
| Additional indicators for regime decision | Display in Telegram alert or manual check? |
| Aster Perp API key for V14PM | Current key works for spot — verify perp trading permissions. |

---

_Captured by Gee Gee — 2026-03-19_
