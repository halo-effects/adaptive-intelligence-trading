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

## AIT — Current State (2026-04-15)
- **V14PM Live (Aster)**: ~$375 equity, 3 coins (TAO, HYPE, JTO), trailing stop TP with **0.2% callback** (optimized from 0.5% via 365-day backtest)
- **V14PM Paper**: $75K+ equity, 4 active positions, running on fixed TP (Phase 2 trailing deferred)
- **V14 Paper**: Running | **V14-ETF Paper**: Running
- **All 4 bots running** on Windows. Cloud migration pending.
- **Trailing stop optimization (2026-04-15)**: Callback 0.5%→0.2%. Aster only accepts 0.1% increments. Backtest: 0.2% = $93K (187% ROI) vs fixed TP = $25K (50% ROI).
- **Git stability fix (2026-04-15)**: Root cause found — two git processes fighting. Source files now protected in .gitignore, never in git.
- **Architecture docs v2.0**: Implementation plan, change control, design doc all updated.

## Active Projects
- **AIT**: Primary. V14PM is the MVP. Next: cloud migration to Hyperliquid mainnet.
- **TrustedBusinessReviews.com**: WordPress â†’ static HTML. Malware cleanup.
- **ShadowQuery**: Deferred.

## LLM Config
- Primary: Claude Opus 4.6 (main sessions)
- Default: Claude Sonnet 4.6 (sub-agents, lighter tasks)
- Cron: Claude Haiku 4.5 (cheapest for routine checks)
- Heartbeat: Haiku

