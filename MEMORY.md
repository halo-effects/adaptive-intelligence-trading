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

## AIT - Current State (2026-03-24)
- **V14PM Live (Aster)**: 3 coins (GRASS, TAO, HYPE), LONG_DCA. equity=$329. 90/10 split, 3-coin tier.
  - **All 4 upgrades LIVE (2026-03-24)**: Tiers, Dynamic Capital, Per-Coin Pause, Per-Coin Regime Flagging.
  - Exchange-as-truth architecture (2026-03-21).
  - Telegram commands: PAUSE/RESUME (global + per-coin), DEPOSIT/WITHDRAW/CAPITAL, CLOSE, APPROVE/DENY.
- **V14PM Paper (MVP)**: $50K capital, 5 coin slots (concentration pivot)
- **V14 Paper**: +583.8% (~$68.4K equity)
- **V14-ETF**: RETIRED (2026-03-17)
- **3 bots running** on Windows (V14 Paper, V14PM Paper, V14PM Live). Cloud migration pending.
- **Upgrades deployed 2026-03-24**: 0 (Adaptive tiers, 26 tests), 1 (Dynamic capital, 19 tests), 2 (Per-coin pause), 3 (Per-coin regime flagging). All passing, 45 total tests.
- **Exchange-as-truth refactor (2026-03-21)**: Engine is signal-only; exchange API is single source of truth.
- **PowerShell timezone bug (2026-03-24)**: `[datetime]::Parse()` converts +00:00 to local time silently. Use `[datetimeoffset]::Parse().UtcDateTime`. Caused 6 false "frozen" alerts. Documented in incident log §17.7.
- **Ghost process lesson (2026-03-21)**: Always `Get-Process python` first.
- Architecture doc: `V14PM_SYSTEM_ARCHITECTURE.md` | Scope doc: `V14PM_UPGRADE_SCOPE.md`

## Active Projects
- **AIT**: Primary. V14PM is the MVP. All 4 upgrades deployed 2026-03-24. Next: cloud migration, WebSocket fills, DB as position truth, $1K deposit to Aster.
- **Basis**: Docs at 7.5-8/10 (2026-03-21). 152.3KB "Complete Agent Guide" in `projects/basis/basis-docs/COMPLETE.md` (17 sections + INDEX). hybridMultiplier=100=Stable+ confirmed from Solidity. 5 test tokens on BSC. Contract-enforced limits documented. 25% airdrop confirmed (5% leaderboard top 50). Points spec complete. Tweet verification + bug reporting live. Action test: agent designed 4-module bot, "would build tonight." Next: Alex return schemas (7→8+), points backend build, clear TBD placeholders, prediction market testing.
- **TrustedBusinessReviews.com**: WordPress → static HTML. Malware cleanup.
- **ShadowQuery**: Deferred.

## LLM Config
- Primary: Claude Opus 4.6 (main sessions)
- Default: Claude Sonnet 4.6 (sub-agents, lighter tasks)
- Cron: Claude Haiku 4.5 (cheapest for routine checks)
- Heartbeat: Haiku

