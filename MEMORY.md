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

## AIT — Current State (2026-05-08)
- **V14PM Live (Aster)**: $385 equity, 95 trades, 85.3% win rate, $96.74 realized PnL, 3 coin slots
  - DEX-as-truth startup: reads wallet balance directly from exchange
  - Reconciliation & auto deposit detection disabled (caused corruption)
  - Positions: PENDLE 7.0, TON 61.7 (oversized from churn, approved to hold)
- **V14 Live (Aster)**: ASTER/USDT single-coin, running
- **V14 Paper**: Running on Hyperliquid
- **V14-ETF Paper**: Running
- **Major incident 2026-05-08**: Data sync cron overwrote capital_manager.py → restart cascade → 113 spread-reject round trips → CSV/capital corruption. Fixed with DEX-as-truth startup, disabled reconciliation/deposit detection, fixed sync script Windows pathspec bug.
- **6 new hard rules** added (19-24) from incident. See `tacit/hard-rules.md`.

## Active Projects
- **AIT**: Primary. V14PM is the MVP. Next: cloud migration to Hyperliquid mainnet.
- **TrustedBusinessReviews.com**: WordPress â†’ static HTML. Malware cleanup.
- **ShadowQuery**: Deferred.

## LLM Config
- Primary: Claude Opus 4.6 (main sessions)
- Default: Claude Sonnet 4.6 (sub-agents, lighter tasks)
- Cron: Claude Haiku 4.5 (cheapest for routine checks)
- Heartbeat: Haiku

