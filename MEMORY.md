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

## AIT — Current State (2026-07-05)
- **V14PM Live (Aster)**: $442.29 capital (seed=$300 + $40 deposit), 119 trades, ~86% win rate
  - **Grid: G-SPLIT (48/32/20) deployed 2026-07-04**. 3 layers, L4 removed. GridModel v2.0.
    - Decision: Final Grid Decision Test (Fable spec v1.0). G-SPLIT +8.6% PnL over incumbent, best PnL/%DD. Fable-verified.
    - E-4 dynamic L1 sizing tested and FAILED evidence bar (MAE gap fails >=2.0). Static grid is the answer.
  - **Part A Signal Gating LIVE**: Entry veto system active. HYPE currently vetoed (A2_EXTENSION).
    - GateModel: ATR-normalized extension (EXT_ATR_MULT=3.0), side-resolved divergence, NEAR fixture.
    - Veto filter in all 3 selector paths (rebalance, rotation, overflow).
    - V-4 guard: veto_clear blocked while trigger still true. May 30 gap closed.
    - Stale-daily fail-closed guard (MAX_DAILY_STALE_DAYS=7).
  - **Part B Signal Gating**: Analyzed but superseded — G-SPLIT removes L4, so layer gating is moot.
  - **Fable Audit (2026-07-03–04)**: All P0 remediation verified. C1 "three grids" gap CLOSED. Post-remediation audit: all fixes confirmed. New findings (H-1/M-1 through M-5) addressed. Final verification ALL GREEN — self-tests executed.
  - **Trade Score (P1-P5)**: Capital freedom fixed (/MAX_LAYERS, average-layer-fraction), depth penalty (DEPTH_HALF_LIFE_H=72), score logging at deal-open (dca_score, trade_score, trend_mult), sim at live scale (MIN_ORDER_NOTIONAL=$10), funding cost in sim (AVG_FUNDING_RATE_8H=0.0001).
  - **MAE tracking**: Per-deal max adverse excursion. Running max per tick at current avg entry. Legacy backfill. Persists via open_deals.
  - **Strategy-native performance**: 116 deals, +$145.46, 87.9% WR, worst loss -$3.80.
  - **Post-orphan-TP era** (after 5/17): 18 deals, 94% WR, +$29.14, ~$28/month run rate.
  - **Pool reconciliation**: `reconcile_pools_from_exchange()` syncs active_pool_cash to DEX every cycle.
  - DEX-as-truth startup, exchange-truth trade recording, warmup-only candle replay
  - **Orphan-TP mode**: FORCE_CLOSE_ON_SIGNAL=False. Positions exit via TP only.
  - **seed_capital immutable** (Hard Rule #26): CLI --capital arg, never recalculated
  - Approved symbols: `[INJ, JUP, TON]` (scanner top 3)
  - **Star coin**: TAO (+$72.40, 17/17 wins, 6.25% avg return). Capital traps: PYTH, HYPE.
  - **Cloud migration readiness**: 6/10 current, 4/10 for Hyperliquid target. No HL runner exists.
  - **Collector pipeline**: Two-tier structure deployed 2026-07-05.
    - ACTIVE_UNIVERSE: 44 pairs (45 scanner coins minus ASTER which is Aster-exchange-only).
    - WATCHLIST: 9 coins (APT, JTO, TRUMP, BERA, S, VIRTUAL, GRASS, INIT, MOVE) — collected for reinstatement continuity.
    - Dead excluded: MKR (delisted), IP (delisted), ORCA (not on HL), PEPE (kPEPE mismatch).
    - TON→GRAM handled. HYPE quote fix (USDT). ccxt 4.5.x null-market patch.
  - **Score history**: Old /24 snapshots cleared. NULL-on-failure for scanner score lookup.
  - **Architecture doc**: v1.14. §7.5.10 two phase machines, §7.5.11 regime persistence.
  - **Regime persistence (RH-1)**: Append-only `regime_events.db`. GLOBAL_FLIP/COIN_PHASE/ALERT events. Fail-open writes. Attested history seeded (March 2024 SHORT, Dec 2025 LONG).
  - **Per-coin funding (RH-3)**: Trailing-90d median replaces flat P5 constant. 94K rates imported. 20% deals earn carry.
  - **Regime-Ladder Final**: Production +43.5% vs B&H −43.8%. Earlier +90%/yr reconstruction withdrawn.
- **V14PM Paper**: 750+ trades, $50K+ PnL (restored from CSV truncation)
- **V14 Live (Aster)**: ASTER/USDT single-coin, running
- **V14 Paper**: Running on Hyperliquid
- **V14-ETF Paper**: Running
- **Hard rules 26-36 (unchanged)**: Immutable seed, no derived constants, fresh clone sync, append-only CSV, no unrealized in detection, idempotent restart, post-tick gates must rollback + separate entries/exits (#32), read arch spec before writing fix code (#33), no forced closes on 1.0x leverage (#34), open_deals is truth for layer count (#35), idle router cash must flow to engines (#36).

### Admin PowerShell tasks — ALL DONE
_(V14PMLiveAster auto-restart task confirmed 2026-08-21: LogonTrigger enabled, correct exe/module/args/workdir, bot running PID-verified. Legacy single-coin task cleanup done 2026-08-21: AsterSpotLive, V14LiveAster, AsterTradingBot, SpotPaperAster unregistered. 6 keepers remain.)_

## Active Projects
- **AIT**: Primary. V14PM is the MVP. G-SPLIT deployed. Next: cloud migration to Hyperliquid mainnet.

## LLM Config
- Primary/Default: Claude Opus 5 (main sessions; now the configured default)
- Sub-agents / lighter tasks: Claude Sonnet 4.6
- Cron: Claude Haiku 4.5 (cheapest for routine checks)
- Heartbeat: Haiku
## Silent Replies
When you have nothing to say, respond with ONLY: NO_REPLY
⚠️ Rules:
- It must be your ENTIRE message — nothing else
- Never append it to an actual response (never include "NO_REPLY" in real replies)
- Never wrap it in markdown or code blocks
❌ Wrong: "Here's help... NO_REPLY"
❌ Wrong: "NO_REPLY"
✅ Right: NO_REPLY
