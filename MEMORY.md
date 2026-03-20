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

## AIT - Current State (2026-03-19)
- **V14PM Paper (MVP)**: $50K capital, 5 coin slots (concentration pivot)
- **V14PM Live (Aster)**: GRASS/USDT, LONG_DCA, PID 6040. Dashboard data crossover fixed. LIVE GUARD active.
- **V14 Paper**: +583.8% (~$68.4K equity)
- **V14-ETF**: RETIRED (2026-03-17)
- **3 bots running** on Windows (V14 Paper, V14PM Paper, V14PM Live). Cloud migration pending.
- **Full V14PM vs V14 Live audit (2026-03-19)**: 20 critical paths, 12 gaps. 3× P0 trade-blocking (capital depletion, TP capital return bug, no periodic reconciliation). Audit doc: `V14PM_VS_V14_LIVE_AUDIT.md`.
- **Order sizing issue**: CapitalRouter 20% per-coin cap too restrictive with few coins. Needs dynamic cap.
- **Resting limit orders LIVE**: Exchange-side limit sell at TP price. LIVE GUARD blocks engine TP when exchange order exists.
- **Exchange-as-truth architecture** decided (2026-03-18). V14PM = production target.

## Active Projects
- **AIT**: Primary. V14PM is the MVP. Full audit found 12 gaps (3 P0). Next: fix P0 items, order sizing, cloud migration.
- **Basis**: SDK testing milestone — Python 44/44 read + 8/8 write (live BSC), JS/TS 39/39. 18-decimal migration done. X/Twitter verification built. Social integration priority (X → Telegram → Moltbook).
- **TrustedBusinessReviews.com**: WordPress → static HTML. Malware cleanup.
- **ShadowQuery**: Deferred.

## LLM Config
- Primary: Claude Opus 4.6 (main sessions)
- Default: Claude Sonnet 4.6 (sub-agents, lighter tasks)
- Cron: Claude Haiku 4.5 (cheapest for routine checks)
- Heartbeat: Haiku

