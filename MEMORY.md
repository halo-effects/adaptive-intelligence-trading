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

## AIT — Current State (2026-05-09)
- **V14PM Live (Aster)**: $376 capital, 9 engines, 85% win rate, $85.24 realized PnL
  - DEX-as-truth startup, exchange-truth trade recording, warmup-only candle replay
  - Reconciliation & auto deposit detection disabled (caused corruption)
  - **Regime phase gate deployed**: Coins trade only when engine phase matches global regime
  - **Graduated conviction alerts**: 7 thresholds (15/25/30/35/40/45/50%), APPROVE at any level
  - **Dashboard**: Regime panel with conviction bar, per-coin gate status, global direction
  - Positions: INJ 4.0 qty long (TP active). HYPE in SHORT_DCA (excluded, 11.1% flip)
  - Architecture doc v1.5 (§7.5 complete)
- **V14 Live (Aster)**: ASTER/USDT single-coin, running
- **V14 Paper**: Running on Hyperliquid
- **V14-ETF Paper**: Running
- **Major incident 2026-05-08**: Data sync cron overwrote capital_manager.py → restart cascade. Fixed with 7 code changes, 5 specs, 6 hard rules.
- **Key principle (2026-05-09)**: Engine phases are truth — never overwrite to match global regime. The signal data IS the conviction signal.

## Active Projects
- **AIT**: Primary. V14PM is the MVP. Next: cloud migration to Hyperliquid mainnet.
- **TrustedBusinessReviews.com**: WordPress â†’ static HTML. Malware cleanup.
- **ShadowQuery**: Deferred.

## LLM Config
- Primary: Claude Opus 4.6 (main sessions)
- Default: Claude Sonnet 4.6 (sub-agents, lighter tasks)
- Cron: Claude Haiku 4.5 (cheapest for routine checks)
- Heartbeat: Haiku

