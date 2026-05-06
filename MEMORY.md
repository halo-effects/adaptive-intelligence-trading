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

## AIT — Current State (2026-05-06)
- **V14PM Paper (MVP)**: $50,440 equity, 30 trades, 100% win rate, $50K capital, 10 coin slots
- **V14 Live (Aster)**: $311 real, ASTER/USDT
- **V14 Paper**: $48K+ equity, 380 deals | **V14-ETF Paper**: $10.5K+ equity, fixed PID lock and equity sync issues.
- **All 4 bots running** on Windows. Cloud migration pending.
- **Full audit complete 2026-03-10**: Fixed critical DB path bug (blind top/bottom detection), added state persistence (no more phantom trades), added daily resampling (19 blind coins now have signal data).
- **Dashboard Fixes (2026-03-10)**: Corrected V14 dashboards to show "Trade Score" (Base Score × Trend Mult) and sort by it to accurately reflect bot logic.
- **CSV-as-truth fix applied** to all 4 runners. V14-ETF equity bug fixed to enforce capital + CSV logic strictly.
- **Architecture doc v1.2, Migration doc v1.2, Audit doc §11** all updated.
- **2026-05-05**: Trade reconciliation system built. Recovered missing PYTH +$0.91 trade. Fixed 5 bugs from sub-agent audit.
- **2026-05-06**: Restored v14_capital_manager.py (sync script had silently stripped critical code on April 15). Fixed T1 gate/rebalance desync, liquidity filter crash, dashboard sync deleting source files, dashboard pointing at paper data instead of live. Architecture doc v1.5.

## Active Projects
- **AIT**: Primary. V14PM is the MVP. Next: cloud migration to Hyperliquid mainnet.
- **TrustedBusinessReviews.com**: WordPress â†’ static HTML. Malware cleanup.
- **ShadowQuery**: Deferred.

## LLM Config
- Primary: Claude Opus 4.6 (main sessions)
- Default: Claude Sonnet 4.6 (sub-agents, lighter tasks)
- Cron: Claude Haiku 4.5 (cheapest for routine checks)
- Heartbeat: Haiku

