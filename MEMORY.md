# MEMORY.md - Long-Term Memory

_Curated essentials. For details, see the structured files below._

## Brett
- Direct, no-fluff communicator. Values security/governance deeply.
- Timezone: America/Los_Angeles
- Uses Telegram for personal, Slack for Halo Effects business (browser only, no desktop app)
- Quote: "It's about finding the right coin at the right time and running the strategy and getting out with your shirt"

## Quick Reference
- **AIT details**: `projects/ait/overview.md` (current state, key decisions, architecture docs)
- **AIT log**: `projects/ait/log.md` (reverse-chronological events)
- **All projects**: `projects/_index.md`
- **Lessons learned**: `tacit/lessons-learned.md`
- **Hard rules**: `tacit/hard-rules.md` (non-negotiable, from production incidents)
- **Workflow habits**: `tacit/workflow-habits.md`
- **Trading status**: `areas/finances/overview.md`
- **Daily notes**: `memory/YYYY-MM-DD.md` (raw session logs)

## AIT — Current State (2026-03-17)
- **V14PM Paper (MVP)**: $53,579 equity, $50K capital, 10 coin slots
- **V14 Live (Aster)**: $369.56 equity, $340 capital ($300 seed + $40 deposit), ASTER/USDT, 4 deals, 100% win rate
- **V14 Paper**: $53,120 equity | **V14-ETF Paper**: $11,335 equity
- **All 4 bots running** on Windows. Cloud migration pending.
- **Resting limit orders LIVE (2026-03-17)**: `run_v14_live_aster.py` places limit sell on exchange at TP price after every BUY fill. Dual approach: limit order (primary) + candle detection (fallback). Verified on exchange (order 485775318). `run_v14_portfolio_live.py` should follow same pattern when built.
- **TP fill model fix (2026-03-17)**: TP now checks candle high/low (not close). Simulates limit order fill on wick touch.
- **Full audit complete 2026-03-10**: Fixed critical DB path bug (blind top/bottom detection), added state persistence (no more phantom trades), added daily resampling (19 blind coins now have signal data).
- **CSV-as-truth fix applied** to all 4 runners. V14-ETF equity bug fixed to enforce capital + CSV logic strictly.

## Active Projects
- **AIT**: Primary. V14PM is the MVP. Next: cloud migration to Hyperliquid mainnet.
- **TrustedBusinessReviews.com**: WordPress â†’ static HTML. Malware cleanup.
- **ShadowQuery**: Deferred.

## LLM Config
- Primary: Claude Opus 4.6 (main sessions)
- Default: Claude Sonnet 4.6 (sub-agents, lighter tasks)
- Cron: Claude Haiku 4.5 (cheapest for routine checks)
- Heartbeat: Haiku

