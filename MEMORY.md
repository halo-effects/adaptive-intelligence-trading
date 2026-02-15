# MEMORY.md — Long-Term Memory

## Brett
- Direct, no-fluff communicator. Values security/governance deeply.
- Timezone: America/Los_Angeles
- Uses Telegram for personal, Slack for Halo Effects business
- No desktop Slack — browser only via Gmail login
- Quote: "It's about finding the right coin at the right time and running the strategy and getting out with your shirt"

## Adaptive Intelligence Trading (AIT)
- **Product name**: Adaptive Intelligence Trading (AIT) — decided 2026-02-14
- **GitHub**: github.com/halo-effects/breathing-grid (account: halo-effects, geegee@haloeffects.net)
- **Product page**: https://halo-effects.github.io/breathing-grid/
- **Dashboard**: trading/live/dashboard.html (v2.0, served on port 8080)
- GitHub PAT: `openclaw-deploy` (repo scope, expires ~Mar 16 2026)

## Aster Trading Bot (HYPEUSDT)
- **Live since 2026-02-13** on Aster DEX (Binance-compatible futures API)
- Dual-tracking bidirectional DCA: simultaneous LONG + SHORT virtual deals
- Net position mode (Aster doesn't support hedge mode) — opposing positions offset on exchange
- Capital: ~$332 USDT (was $292, +$40 deposit 2026-02-14), no leverage (1x)
- Params: TP=1.5%, Deviation=2.5%, MaxSO=8, SO_mult=2.0, 5m timeframe, base_order=4%
- Regime-based allocation: TRENDING=75/25 long/short, CHOPPY/RANGING=50/50, etc.
- EXTREME regime = 0/0 (halt trading)
- Files: `trading/aster_trader.py` (live), `trading/martingale_engine.py` (backtest)
- Runs as Windows Scheduled Tasks: `AsterTradingBot`, `AsterDashboard`
- **Restart procedure**: Stop-Process by PID first, THEN Start-ScheduledTask (task restart alone won't kill python)
- Dashboard: `trading/live/dashboard.html` (auto-refresh, shows both sides)

### Key Technical Lessons
- reduceOnly orders fail in net position mode when opposing side has larger position — don't use reduceOnly
- Base order sizing should NOT scale by allocation % (hits minimums) — allocation only gates open/close
- TP retry logic needed — exchange can reject TP placement, must auto-retry
- 5m timeframe >> 1m for this strategy (less noise)
- 1x leverage >> 2x (counterintuitive — 2x eats capital reducing deal cycling)
- Wider SO deviation (2.5%) strongly preferred over tight (1.5%)
- **Net position mode margin trap**: selling to close a long can flip net short, requiring margin for the flip — must check margin before TP placement
- **TP > SOs priority**: always ensure TP can be placed, cancel deep SOs if needed to free margin
- **Aster fees**: Maker = 0% (free), Taker = 0.04% — limit orders (TP, SO fills) are free

### Adaptive TP/Deviation System (Live since 2026-02-14)
- Dynamic TP: 0.6–2.5% based on 14-period ATR + regime multipliers (baseline 1.5%, ATR_BASELINE=0.8%)
- Dynamic deviation: 1.2–4.0% (baseline 2.5%), floor = TP × 1.5
- Regime multipliers: RANGING=0.85×TP/0.80×DEV, TRENDING=1.20×TP/1.30×DEV, EXTREME=0.70×TP/1.50×DEV
- Margin-aware: 10% capital reserve, skips unaffordable SOs, cancels deep SOs to ensure TP placement
- TP-hit analysis logged with duration, adaptive params, ATR, regime insight

### WhiteHatFX History
- Brett previously traded MT4 Martingale (WhiteHatFX v2) on FTMO 100k prop firms: BTC, currencies, gold, US30
- Dual-engine bidirectional grid — same core concept as Aster
- Key diff: 4x lot multiplier (vs 2x now), fixed params, no equity protection
- Evolution: from static hardcoded → dynamic regime-adaptive ("Breathing Grid")

### Coin Screener
- HYPE ranked #1 (0.876 fitness) for dual-tracking: low trend (2.7%), good range
- Pipeline: screen → deploy → monitor → rotate (regime detector = exit signal)
- Script: `trading/coin_screener.py`

## Slack Integration
- Workspace: halo-effects.slack.com
- Channel: C092S0TVA0Z
- Full gateway restart needed for Slack socket (SIGUSR1 insufficient)
- Bot name: "Gee Gee"
- **Socket drops silently** — Brett sends messages I never receive. Recurring issue.
- Agent can't restart gateway directly (commands.restart=true not set) — Brett must run `openclaw gateway restart`
- Consider adding Slack health check to HEARTBEAT.md

## TrustedBusinessReviews.com Migration (Active Project)
- **Phase 1 (active):** WordPress → static HTML migration, review system, admin dashboard, Google schema
- Instructions: `projects/tbr/migration-instructions.md`
- FTP access working (Adeel fixed path 2026-02-14)
- **Malware cleanup in progress** — major compromise found, mostly cleaned, ~1,900 spam pages + 2 plugins still need finishing
- Password changes still recommended (credential exfil was active)
- Public crawl done — ~10 business listings across 5-6 categories, Phoenix AZ focused
- Google Doc trick: append `/mobilebasic` to extract text from Google Docs via browser

## Communication Channels
- **Slack** → Halo Effects business (TBR, ShadowQuery, Adeel)
- **Telegram** → Trading bot, personal projects, everything else
- Slack channel: C092DGXUZFW (#team-)
- Slack user IDs: Brett=U092S0TJK5X, Adeel=U092D6SA0JW

## Deferred Projects
- **AI GEO / ShadowQuery**: Brett moved discussion to Slack with Adeel; TBR migration is prep for this
- Tutorial notes saved: `reference/shadowquery-tutorials.md`

## Embedding/Memory Search
- Not working — no OpenAI/Google/Voyage API key configured for embeddings
