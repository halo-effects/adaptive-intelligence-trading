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

## AIT — Trust Chain
The V14PM system has a defined trust chain. Respect this hierarchy:
1. **V14PM_SYSTEM_ARCHITECTURE.md** — Single source of truth for how the system works (confirmed by audit)
2. **CLOUD_MIGRATION_GUIDE.md** — Depends on architecture doc being accurate
3. **V14PM Dashboard** — Real-world output. Verifies the architecture doc against reality.
4. **If dashboard ≠ architecture doc** → bug in the system, go find it and fix it
5. **Do NOT hallucinate problems.** Verify before claiming something is broken. Check actual processes, actual data. If you don't know, say so — don't speculate.

## AIT — Current State (2026-03-10)
- **V14PM Paper (MVP)**: $50,592 equity, 29 trades, 100% win rate, $50K capital, 10 coin slots, 10 open positions
- **V14 Live (Aster)**: $300 real, ASTER/USDT
- **V14 Paper**: $69K+ equity, 374+ deals | **V14-ETF Paper**: $10K+, running
- **All 4 bots running** on Windows. Cloud migration pending (decisions: provider, capital, API wallet).
- **Full audit complete 2026-03-10**: Fixed critical DB path bug (blind top/bottom detection), added state persistence (no more phantom trades), added daily resampling (19 blind coins now have signal data)
- **Dashboard verified accurate** as of 2026-03-10 09:18 PDT
- **CSV-as-truth fix applied** to all 4 runners (2026-03-10 10:14 PDT)
- **Live Aster equity** now from exchange API balances, not engine counters
- **Architecture doc v1.2, Migration doc v1.2, Audit doc §11** all updated

## Active Projects
- **AIT**: Primary. V14PM is the MVP. Next: cloud migration to Hyperliquid mainnet.
- **TrustedBusinessReviews.com**: WordPress → static HTML. Malware cleanup.
- **ShadowQuery**: Deferred.

## LLM Config
- Primary: Claude Opus 4.6 (main sessions)
- Default: Claude Sonnet 4.6 (sub-agents, lighter tasks)
- Cron: Claude Haiku 4.5 (cheapest for routine checks)
- Heartbeat: Haiku
