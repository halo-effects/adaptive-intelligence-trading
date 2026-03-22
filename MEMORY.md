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

## AIT - Current State (2026-03-21)
- **V14PM Live (Aster)**: GRASS/USDT, LONG_DCA. **Exchange-as-truth architecture LIVE** (2026-03-21). equity=$341, pnl=+0.39%.
- **V14PM Paper (MVP)**: $50K capital, 5 coin slots (concentration pivot)
- **V14 Paper**: +583.8% (~$68.4K equity)
- **V14-ETF**: RETIRED (2026-03-17)
- **3 bots running** on Windows (V14 Paper, V14PM Paper, V14PM Live). Cloud migration pending.
- **Exchange-as-truth refactor (2026-03-21)**: Removed LIVE GUARD, rollbacks, reconciliation. Engine is signal-only; exchange API is single source of truth for positions. ~280 lines removed. Fixed -70% phantom drawdown (was $103 display, actually $341). Audit doc §21.
- **Resting limit orders LIVE**: Exchange-side limit sell at TP price. Engine skips TP when exchange order exists.
- Architecture doc v1.5: `V14PM_SYSTEM_ARCHITECTURE.md`

## Active Projects
- **AIT**: Primary. V14PM is the MVP. Exchange-as-truth architecture LIVE (2026-03-21). All P0/P1 audit items resolved by architecture refactor. Next: cloud migration, WebSocket fills, DB as position truth.
- **Basis**: Docs at 7/10 (2026-03-21). 144.6KB "Complete Agent Guide" in `projects/basis/basis-docs/COMPLETE.md` (17 sections + INDEX). hybridMultiplier/startLP empirically tested on-chain. Points spec complete (`points-system-complete-spec.md`). Tweet verification + bug reporting live. Action test: fresh agent designed 4-module bot unprompted. Next: Alex return schemas (7→8+), points backend build, clear TBD placeholders, prediction market testing.
- **TrustedBusinessReviews.com**: WordPress → static HTML. Malware cleanup.
- **ShadowQuery**: Deferred.

## LLM Config
- Primary: Claude Opus 4.6 (main sessions)
- Default: Claude Sonnet 4.6 (sub-agents, lighter tasks)
- Cron: Claude Haiku 4.5 (cheapest for routine checks)
- Heartbeat: Haiku

