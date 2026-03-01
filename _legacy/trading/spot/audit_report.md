# V12e Code-Documentation Audit Report
**Date:** 2026-02-22  
**Auditor:** Automated (subagent)

---

## 1. ✅ Verified Items

### Code Imports
- ✅ `from trading.spot.lifecycle_trader import LifecycleTrader` — resolves
- ✅ `from trading.spot.exchange_adapter import create_adapter, EXCHANGE_REGISTRY` — resolves
- ✅ `from trading.spot.coin_pipeline import evaluate_coins` — resolves
- ✅ `from trading.spot.phase_classifier import classify_phase` — resolves
- ✅ `from trading.spot.lifecycle_engine import LifecycleEngine, LifecycleConfig` — resolves

### Class Names
- ✅ Main class is `LifecycleTrader` in `lifecycle_trader.py`
- ✅ `SpotPaperTrader` exists as alias: `SpotPaperTrader = LifecycleTrader` (line 2519)
- ✅ No stale `spot_trader` module imports in `trading/spot/*.py` (only a comment referencing old file)

### Status.json Schema Match (Paper vs Live)
- ✅ Paper and Live status.json share identical key sets (39 shared, 0 unique to either)

### Phase Names
- ✅ Code uses DCA, EXIT, MARKDOWN, SPRING, MARKUP (LifecyclePhase enum in lifecycle_engine.py)
- ✅ `docs/wyckoff-lifecycle.html` matches: DCA, MARKUP, EXIT, MARKDOWN, SPRING
- ✅ `docs/pricing.html` FAQ matches: DCA, EXIT, MARKDOWN, SPRING, MARKUP
- ✅ Dashboard phase CSS classes match: `pb-DCA`, `pb-EXIT`, `pb-MARKDOWN`, `pb-SPRING`, `pb-MARKUP`

### Risk Profiles in Code
- ✅ Three profiles defined: low, medium, high (`PROFILES` dict in lifecycle_trader.py)
- ✅ Low: max_safety_orders=5, base_order_pct=0.03, tp 1.5-2.5, dev 3.0-4.0, max_dd=15%, max_coins=2
- ✅ Medium: max_safety_orders=8, base_order_pct=0.04, tp 1.0-2.0, dev 2.0-3.0, max_dd=25%, max_coins=3
- ✅ High: max_safety_orders=12, base_order_pct=0.05, tp 0.8-1.5, dev 1.5-2.5, max_dd=35%, max_coins=5

### Dashboard Data URLs
- ✅ `dashboardV12.html` CONFIG reads from `data/v12e/status.json`, `data/v12e/trades.csv`, `data/scanner_t1.json`
- ✅ `sync_dashboard.ps1` copies V12e paper data to `docs/data/v12e/`
- ✅ `docs/data/v12e/status.json` and `docs/data/scanner_t1.json` exist

### Dashboard Fields vs Code
- ✅ `fear_greed_index` — written by `_write_status()` from `self._fear_greed_index`
- ✅ `coins[sym].cfgi` — written by `_write_status()` as `coin_info["cfgi"]`
- ✅ `lifecycle[sym].score` — written by `_build_lifecycle_status()` as `state.conductor_cached_score`
- ✅ `lifecycle[sym].phase` — written by `_build_lifecycle_status()` from `self._coin_phases`
- ✅ `lifecycle[sym].short_active` — written by `_build_lifecycle_status()` from `self._paper_shorts`
- ✅ `lifecycle[sym].metrics` — written with exit/markdown/spring/markup phase counts
- ✅ `regime` — written by `_write_status()` from first symbol's regime
- ✅ `trend_direction` — written by `_write_status()` as "bullish"/"bearish"

### Exchange Adapter Registry (exchange_adapter.py)
- ✅ Aster: `unified_wallet: False` (split) — matches docs claim
- ✅ Hyperliquid: `unified_wallet: True` — matches docs claim
- ✅ Hyperliquid: `quote_currency: "USDC"` — correct

### Scheduled Tasks
- ✅ `AIT_DashboardSync` — exists, Ready
- ✅ `AsterSpotLive` — exists, Ready
- ✅ `SpotPaperAster` — exists, Ready
- ✅ `SpotPaperHyperliquid` — exists, Ready
- ✅ `AIT_CandleCollector` — exists, Ready

### Product Pages (docs/)
- ✅ `index.html` — no references to "spot_trader.py", "SpotPaperTrader" as active class, "V12f", or "rotation" as shipped feature
- ✅ `pricing.html` — tier system (Starter/Trader/Pro/Elite/Whale) with coin limits (1/2/3/5/8)
- ✅ `wyckoff-lifecycle.html` — five phases correctly described
- ✅ Phase descriptions accurate: DCA=accumulation, EXIT=distribution, MARKDOWN=decline, SPRING=bottom, MARKUP=uptrend

### Guardrail Claims
- ✅ `index.html` claims "Medium→Low at 30% drawdown, High→Medium at 50%" — matches risk-profiles-spec.md §6.2
- ✅ Code max_drawdown_pct: low=15%, medium=25%, high=35% (these are per-profile halt thresholds, not auto-downgrade triggers — see warning below)

---

## 2. ❌ Discrepancies Found

### D1: Exchange Fees Mismatch — Aster (CRITICAL)
**exchange_adapter.py (EXCHANGE_REGISTRY):**
- Aster maker: 0.0% (`0.0`), taker: 0.04% (`0.0004`)

**lifecycle_trader.py (EXCHANGE_FEES):**
- Aster maker: 0.01% (`0.0001`), taker: 0.035% (`0.00035`)

**MEMORY.md claims:**
- Aster fees: Maker = 0% (free), Taker = 0.04%

**Verdict:** Three different fee values across three files. `EXCHANGE_REGISTRY` matches MEMORY.md. `EXCHANGE_FEES` in lifecycle_trader.py is **wrong** — maker should be 0.0, taker should be 0.0004.
- **File:** `trading/spot/lifecycle_trader.py:60-61`
- **File:** `trading/spot/exchange_adapter.py:13-14`

### D2: Exchange Fees Mismatch — Hyperliquid
**exchange_adapter.py:** maker=0.02% (`0.0002`), taker=0.05% (`0.0005`)  
**lifecycle_trader.py:** maker=0.04% (`0.0004`), taker=0.07% (`0.0007`)

These don't match. One set is likely outdated.
- **File:** `trading/spot/lifecycle_trader.py:62`
- **File:** `trading/spot/exchange_adapter.py:22-23`

### D3: `spot_trader.py` File Does Not Exist
**MEMORY.md states:**
> `trading/spot/spot_trader.py` — SpotPaperTrader

File does not exist (`Test-Path` returned False). The class was renamed to `LifecycleTrader` in `lifecycle_trader.py`. MEMORY.md references are stale.
- **File:** `MEMORY.md` (Spot Paper Bots section)

### D4: HEARTBEAT.md References Stale Scheduled Task & Bot Params
**HEARTBEAT.md states:**
- Aster paper: "ETH/USDT Medium 15m"
- Hyperliquid paper: "HYPE/USDC Medium 15m"

**Actual running V12e paper bot** (from status.json):
- Exchange: hyperliquid, coins: ETH/USDC + SOL/USDC + BTC/USDC, timeframe: 1h
- No separate "Aster paper" V12e instance visible; the dashboard points to `data/v12e/`

**HEARTBEAT.md** does not mention the V12e paper bot at all, nor the live Aster spot bot (`AsterSpotLive`).

### D5: HEARTBEAT.md References Wrong Aster Task Name
**HEARTBEAT.md:** `"AsterTradingBot"` — this task exists but is **Disabled**  
**Actual:** `AsterSpotLive` is the active live spot bot task (Ready state)
- **File:** `HEARTBEAT.md`

### D6: MEMORY.md — Stale Bot Descriptions
**MEMORY.md Spot Paper Bots section says:**
- "Aster instance: ETH/USDT Medium 15m"
- "Hyperliquid instance: HYPE/USDC Medium 15m"

**Reality:** V12e paper bot runs on Hyperliquid with ETH/USDC, SOL/USDC, BTC/USDC at 1h timeframe. The HYPE-focused paper bot and 15m timeframe are from the old V11 era.
- **File:** `MEMORY.md` (Spot Paper Bots section)

### D7: MEMORY.md — Stale Scheduled Task Names
**MEMORY.md mentions:** `SpotPaperAster`, `SpotPaperHyperliquid`  
These exist but are likely the OLD paper bot tasks. No mention of `AsterSpotLive` or the V12e-specific runner.
- **File:** `MEMORY.md`

### D8: risk-profiles-spec.md — Leverage References Don't Apply to V12e Spot
The spec defines:
- Low: 1× leverage
- Medium: 2-3× leverage  
- High: 5-10× leverage

V12e is **spot only** — there is no leverage. The actual code profiles have no leverage parameter. The spec was written for the old futures-based approach and hasn't been updated for V12e spot.
- **File:** `projects/ait-product/risk-profiles-spec.md` §2.1-2.3

### D9: risk-profiles-spec.md — Parameters Don't Match Code
**Spec says Low Risk:**
- Max SOs: 8, Base Order: 4%, TP: 0.6-2.5%, Deviation: 1.2-4.0%

**Code says Low Risk:**
- Max SOs: 5, Base Order: 3%, TP: 1.5-2.5%, Deviation: 3.0-4.0%, max_coins: 2

**Spec says Medium Risk:**
- Max SOs: 12, Base Order: 6%, TP: 0.4-2.0%, Deviation: 0.8-3.0%

**Code says Medium:**
- Max SOs: 8, Base Order: 4%, TP: 1.0-2.0%, Deviation: 2.0-3.0%, max_coins: 3

**Spec says High Risk:**
- Max SOs: 16, Base Order: 8%, TP: 0.2-1.5%, Deviation: 0.5-2.0%

**Code says High:**
- Max SOs: 12, Base Order: 5%, TP: 0.8-1.5%, Deviation: 1.5-2.5%, max_coins: 5

The spec is significantly out of date — it reflects the old futures-era parameters.
- **File:** `projects/ait-product/risk-profiles-spec.md` §2

### D10: v12f-capital-allocation-spec.md — Missing
The file `projects/ait-product/v12f-capital-allocation-spec.md` does not exist. The task asked to verify it's marked deprecated. Since it doesn't exist, there's nothing to deprecate, but references to "V12f" and "smart allocation" in the code (`self.smart_allocation`) should be noted — it's present but disabled by default.

### D11: `docs/index.html` — "Smart Capital Allocation" Feature Mentioned
**pricing.html** feature card says:
> "Smart Capital Allocation — Three-position slider - Conservative, Balanced, or Aggressive deployment speed. Capital flows to coins with the best lifecycle opportunity"

This describes the V12f capital allocation feature (`smart_allocation` flag) which is **not active by default** — `smart_allocation=False` in the constructor. The feature exists in code but is gated behind a flag. The pricing page presents it as a shipped feature.
- **File:** `docs/pricing.html` (feature card "Smart Capital Allocation")

### D12: `docs/index.html` — "30s Adaptation Cycle" Claim
Hero stats show "30s Adaptation Cycle". The actual cycle time depends on timeframe config. V12e paper runs on 1h candles. The 30s claim appears to refer to the loop sleep interval, not the candle/decision interval.
- **File:** `docs/index.html` hero section

### D13: Lifecycle Engine Docstring References "SpotPaperTrader"
**lifecycle_engine.py:383:**
> "Designed to be composed into SpotPaperTrader — not a standalone bot."

Should say `LifecycleTrader`.
- **File:** `trading/spot/lifecycle_engine.py:383`

---

## 3. ⚠️ Warnings

### W1: Guardrail Auto-Downgrade — Spec vs Implementation
The product pages and spec claim auto-downgrade (Medium→Low at 30% DD, High→Medium at 50%). The `PROFILES` dict defines `max_drawdown_pct` per profile (15/25/35%), but the **auto-downgrade logic** (shifting from one profile to another) is not visible in `lifecycle_trader.py`. The code appears to halt at profile DD thresholds, not downgrade to lower profiles. This may work differently than advertised.

### W2: "100% Win Rate" Claims
Multiple pages claim 100% win rate. This is based on backtests with compounding where deals that don't complete are unrealized (not counted as losses). The claim is technically accurate for *completed* deals but could be misleading.

### W3: "8 Intelligence Signals" — Not Enumerated
`index.html` hero claims "8 Intelligence Signals." The code uses multiple signals (regime, CFGI, ATR, SMA50, conductor score, etc.) but the exact count of 8 is not explicitly defined anywhere in the codebase.

### W4: Pricing Page — "20+ certified coins"
The pricing page and FAQ reference "20+ certified coins." The coin certification process described (4-stage validation) is aspirational — the actual certified coin pool is not enumerated in the codebase. The scanner evaluates coins dynamically but there's no static "certified" list of 20+.

### W5: MEMORY.md — Heavily Outdated
Large portions of MEMORY.md describe the old Aster futures bot, v11 spot paper bots, and pre-V12e architecture. While not technically wrong (it's historical), readers could mistake past state for current state. Recommend a cleanup pass to separate "historical" from "current."

### W6: Duplicate Fee Definitions
Fees are defined in both `EXCHANGE_FEES` (lifecycle_trader.py) and `EXCHANGE_REGISTRY` (exchange_adapter.py). The trader uses `EXCHANGE_FEES` for its calculations, not the registry. This duplication will inevitably cause drift (as we see in D1/D2).

### W7: `AsterTradingBot` Task Disabled But Referenced
The old futures bot task `AsterTradingBot` is Disabled. HEARTBEAT.md and MEMORY.md still reference it. The live spot bot runs as `AsterSpotLive`.

### W8: Product Pages List Exchanges Not Yet Integrated
`index.html` lists 13 exchanges (Binance, Coinbase, Bybit, OKX, Kraken, KuCoin, Gate.io, Bitget, MEXC, HTX, Hyperliquid, Aster, dYdX). Only Aster and Hyperliquid have adapters in `EXCHANGE_REGISTRY`. The others are "supported via CCXT" but not configured/tested. The product page implies they're ready to use.

### W9: Telegram Token Hardcoded
`lifecycle_trader.py:37-38` contains a hardcoded Telegram bot token and chat ID. This is a security concern if the repo is public.

---

## Summary

| Category | Count |
|----------|-------|
| ✅ Verified | 30+ items |
| ❌ Discrepancies | 13 |
| ⚠️ Warnings | 9 |

**Critical issues:** D1/D2 (fee mismatches affect P&L calculations), D8/D9 (spec completely out of date with code).

**Recommended actions:**
1. Fix `EXCHANGE_FEES` in lifecycle_trader.py to match exchange_adapter.py values (or better: use registry as single source of truth)
2. Update MEMORY.md to reflect current V12e state
3. Update HEARTBEAT.md with current task names and bot configs
4. Update risk-profiles-spec.md for V12e spot parameters (remove leverage references)
5. Clarify "Smart Capital Allocation" in pricing.html — either mark as "coming soon" or remove
6. Update lifecycle_engine.py docstring to say LifecycleTrader
