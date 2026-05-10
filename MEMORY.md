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

## AIT — Current State (2026-05-10)
- **V14PM Live (Aster)**: $378 capital, 86 trades, 82.8% win rate, $13.96 realized PnL (seed=$300)
  - DEX-as-truth startup, exchange-truth trade recording, warmup-only candle replay
  - Reconciliation & auto deposit detection disabled (caused corruption)
  - **Regime phase gate deployed**: Coins trade only when engine phase matches global regime
  - **seed_capital immutable** (Hard Rule #26): CLI --capital arg, never recalculated
  - **Trade history restored**: 86 trades merged from git recovery + current bot
  - **V2 System Audit complete**: 60 findings, 15 fixed, 1 HIGH remaining (auto-restart task needs admin)
  - **Dashboard sync fixed**: Root cause was `git reset --soft` in sparse checkout → fresh clone per cycle
  - Approved symbols: `[INJ, JUP, TON]` (scanner top 3)
- **V14PM Paper**: 750 trades, $50,415 PnL (restored from 171 trades after CSV truncation)
- **V14 Live (Aster)**: ASTER/USDT single-coin, running
- **V14 Paper**: Running on Hyperliquid
- **V14-ETF Paper**: Running
- **Major incident 2026-05-08**: Data sync cron overwrote capital_manager.py → restart cascade.
- **Key principle (2026-05-09)**: Engine phases are truth — never overwrite to match global regime.
- **Hard rules 26-29 added** (2026-05-10): Immutable seed, no derived constants, fresh clone sync, append-only CSV.

### Needs Admin PowerShell
1. Create V14PM auto-restart task (`V14PMLiveAster`)
2. Disable old stale task (`V14LiveAster`)

## Active Projects
- **AIT**: Primary. V14PM is the MVP. Next: cloud migration to Hyperliquid mainnet.
- **TrustedBusinessReviews.com**: WordPress â†’ static HTML. Malware cleanup.
- **ShadowQuery**: Deferred.

## LLM Config
- Primary: Claude Opus 4.6 (main sessions)
- Default: Claude Sonnet 4.6 (sub-agents, lighter tasks)
- Cron: Claude Haiku 4.5 (cheapest for routine checks)
- Heartbeat: Haiku

