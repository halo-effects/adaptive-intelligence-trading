# AIT — Project Log
_Reverse chronological. Key events only._

## 2026-03-10
- **Full system audit complete**: Read every file in V14PM dependency chain
- **CRITICAL FIX**: `v13_router_engine_v2.py` wrong DB path (`.parent.parent.parent` → `.parent.parent`). HybridDetector2D was reading from 0-byte DB — top/bottom detection completely broken across ALL bots since deployment
- **CRITICAL FIX**: Created `resample_daily.py` — 19 of 45 coins had zero daily candles. Wired into hourly pipeline as Step 1.5
- **CRITICAL FIX**: Added engine state persistence (`engine_state.json`) — root cause of phantom trades. Saves every 60s, restores on startup. 4 restart tests with zero phantoms.
- Removed `--fresh` from PM scheduled task (state persistence handles restarts)
- Updated V14PM_SYSTEM_ARCHITECTURE.md (v1.1) and CLOUD_MIGRATION_GUIDE.md (v1.1)
- Rebuilt QMD structured memory system

## 2026-03-09
- **PM trade reconciliation**: 61 trades → 20 genuine, 41 phantoms removed ($943 fake PnL)
- Added `recorded_at` field to all trades (forensic provenance)
- Added `_fresh_floor_ms` candle replay guard
- Added PID lock (`bot.pid`) — prevented dual-instance bug
- Added engine warmup period (no trading until first daily boundary)
- Upgraded OpenClaw 2026.3.1 → 2026.3.8
- Fixed dashboard sync silent push failure (17 hours of silent failures)

## 2026-03-08
- Macro bottom conviction signals documented (6 index-level signals all active)
- Added to conviction-stack-spec.md, not wired into bot logic

## 2026-03-07
- Scanner run: 38/40 coins in MARKDOWN, ATOM sole MARKUP in top-10
- Fixed ASTER NaN `isnan` bug in `_check_dca`

## 2026-03-06
- **Trend multiplier wired into PM allocation**: `Adjusted Score = DCA Score × Trend Multiplier`
- Scanner backfill feature (`--backfill-history N`, `--as-of YYYY-MM-DD`)
- PM capital confirmed at $50K (was mistakenly set to $10K)
- Expanded COIN_BASE to all 45 scanner coins across all 4 dashboards
- Created V14CycleScanner scheduled task (daily 6 AM)

## 2026-03-05
- **V14 PM paper bot launched**: $10K initial (later corrected to $50K)
- Fixed dashboard JS syntax errors (V14ETF, Live, V14PM)
- Fixed `np.isnan(daily_close)` bug, `InvalidIndexError` in `load_daily()`
- V14 Live bot restarted after silent crash (stale 476 min)
- PM comparison log tool created
- Switched primary model to Claude Opus 4.6

## 2026-03-04
- API rate limit incident (Gemini 1M TPM + Anthropic credit exhaustion)
- V14 Live double-execution bug (two instances, duplicate trades)
- Model config: Gemini → Sonnet as primary
- Git backup switched from OpenClaw cron to Windows bat script

## 2026-03-03
- **V14 Live bot launched** on Aster DEX ($300 real, ASTER/USDT)
- Bear market coin research: DCA Cycle Velocity scoring created
- DCA Cycle Scanner built (`v14_cycle_scanner.py`)
- Full Hyperliquid universe backfill (18 coins from Binance/KuCoin)
- ZRO discovered as surprise champion via backfill data

## 2026-03-02
- **V13 SUNSET** (final: +184.5%, $28,449)
- **V14-ETF paper bot launched** (SOL/XRP/LTC/HBAR/ADA, $10K, High profile)
- OpenClaw security audit + update to 2026.3.1
- Created OpenClaw watchdog scheduled task
