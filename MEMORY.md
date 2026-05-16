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

## AIT � Current State (2026-05-16)
- **V14PM Live (Aster)**: $423 capital (seed=$300 + $40 deposit), 96 trades, ~84% win rate
  - **Grid optimization (2026-05-12)**: TP 3.0%, Max 4 layers (was 1.5%/12L). Backtest: +26.3% PnL.
  - **Scanner synced (2026-05-12)**: Params match production (3.0% TP, 4L). 30d window confirmed via walk-forward analysis. INJ now #1 (score 35.0).
  - DEX-as-truth startup, exchange-truth trade recording, warmup-only candle replay
  - **Auto deposit/withdrawal detection ENABLED** (2026-05-11): Consecutive balance comparison, no unrealized PnL. Full system audit: `specs/deposit-detection-audit.md`
  - Reconciliation disabled (caused corruption). TP recovery handles missed fills.
  - **Orphan-TP mode (2026-05-16)**: FORCE_CLOSE_ON_SIGNAL=False. No forced closes on phase transition or MARKDOWN_FAIL. Positions exit via TP only. Orphaned positions ride to TP naturally. MARKDOWN_FAIL deprecated (leverage-era relic). Backtest: 5/8 coins improved.
  - **Regime phase gate fixed (2026-05-15)**: Entries (BUY/SHORT_OPEN) blocked + rolled back via `reject_action()`; exits (SELL/SHORT_CLOSE/TP) always pass through. Initial gate (05-13) blocked everything including exits (trapping positions) and had no rollback (phantom state drift). Incident: NEAR opened short in LONG regime because gate didn't exist in running code when position opened.
  - **seed_capital immutable** (Hard Rule #26): CLI --capital arg, never recalculated
  - **Dashboard growth**: `(equity - seed - net_deposits) / seed` � isolates trading from capital flows
  - **Capital ledger baseline**: seed=$300, deposit=$40, pnl_adjustment=$64.59 (dark PnL gap)
  - **ccxt Aster patch**: Filters null baseAsset markets from API (intermittent crash fix)
  - Approved symbols: `[INJ, JUP, TON]` (scanner top 3)
- **V14PM Paper**: 750+ trades, $50K+ PnL (restored from CSV truncation)
- **V14 Live (Aster)**: ASTER/USDT single-coin, running
- **V14 Paper**: Running on Hyperliquid
- **V14-ETF Paper**: Running
- **V2 System Audit** (2026-05-10): 60 findings, 15 fixed. Deposit detection audit (2026-05-11): 7 findings, 2 critical fixed.
- **Hard rules 26-34**: Immutable seed, no derived constants, fresh clone sync, append-only CSV, no unrealized in detection, idempotent restart, post-tick gates must rollback + separate entries/exits (#32), read arch spec before writing fix code (#33), no forced closes on 1.0x leverage (#34).

### Needs Admin PowerShell
1. Create V14PM auto-restart task (`V14PMLiveAster`)
2. Disable old stale task (`V14LiveAster`)

## Active Projects
- **AIT**: Primary. V14PM is the MVP. Next: cloud migration to Hyperliquid mainnet.
- **TrustedBusinessReviews.com**: WordPress → static HTML. Malware cleanup.
- **ShadowQuery**: Deferred.

## LLM Config
- Primary: Claude Opus 4.6 (main sessions)
- Default: Claude Sonnet 4.6 (sub-agents, lighter tasks)
- Cron: Claude Haiku 4.5 (cheapest for routine checks)
- Heartbeat: Haiku

