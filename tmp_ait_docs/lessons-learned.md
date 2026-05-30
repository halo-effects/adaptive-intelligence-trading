# Lessons Learned
_Hard-won knowledge from production incidents and development._

## Code & Architecture

### DB Path Resolution (2026-03-09, 2026-03-10)
- `Path(__file__).parent.parent.parent` is a landmine — one extra `.parent` silently points to a different (possibly empty) DB
- TWO separate bugs from the same pattern: `_steve_3check.py` and `v13_router_engine_v2.py`
- An empty 0-byte file at the wrong path masks the error completely (no FileNotFoundError, just empty results)
- **Rule**: Centralize DB_PATH into a single config module. Never define it independently in 6+ files.

### State Persistence Is Not Optional (2026-03-10)
- The PM runner had `snapshot_state()` / `restore_state()` methods on the engine — but never called them
- Every restart = blank engines = 200 candles of history replayed = phantom trades
- Band-aids (`--fresh`, fresh floor, PID lock, recorded_at) are not substitutes for actual state persistence
- **Rule**: If an engine has state, that state must be saved and restored. Period.

### Daily Data Pipeline Gaps (2026-03-10)
- The candle collector wrote 1h data. The signal pack read daily data. Nothing connected them.
- 19 coins ran blind for days — no signals, no phase transitions, no top/bottom detection
- **Rule**: Trace the entire data flow from source to consumer. If there's a gap, you'll find it in production.

### Phantom Trade Detection (2026-03-09)
- `recorded_at` field (wall-clock UTC when trade was written) is the forensic backstop
- Real trades: `recorded_at ≈ close_time` (within minutes)
- Phantom trades: `recorded_at` hours/days after `close_time`
- 24 phantom trades caught instantly by this field (all recorded within 9-second window)
- **Rule**: Always add forensic timestamps to critical records

### PID Lock on Windows (2026-03-09)
- Windows Scheduled Tasks + manual starts = duplicate bot instances
- Two instances writing to the same trades.csv and state files = corruption
- PID lock with command-line validation catches this at startup
- **Not needed on Linux** — systemd guarantees single instance

### Engine Warmup Before Trading (2026-03-09)
- New engines default to LONG_DCA and enter L1 on first candle
- Without warmup, router hasn't evaluated whether market warrants long or short
- In a bear market, this means 10 blind long entries before signals kick in
- **Rule**: New engines observe until first daily boundary (router sets direction)

### Never Use PowerShell Export-Csv for Trading Data (2026-03-09)
- `Export-Csv` adds BOM, mangles headers, changes delimiter behavior
- Direct `write()` with explicit content is the only safe approach for trades.csv

## Trading & Strategy

### Data-Driven Over Narrative (2026-03-03)
- Brett asked about bear market coins. I built a "DeFi revenue" thesis from his framing without data backing it.
- He called it: "Did you find that in your research or just from what I originally said?"
- The actual data showed ASTER (not DeFi) as the clear winner — it doesn't get trapped
- **Rule**: Let data lead. Don't build narratives from user prompts.

### Simple Cycle Counting Misleads (2026-03-03)
- First analysis ranked HYPE #1 at 76 cycles
- Full DCA sim with capital lock-up showed ASTER #1 because it doesn't trap capital
- The scoring metric that includes capital freedom changes rankings significantly
- **Rule**: Raw metrics without context (capital lock-up, drawdown) are misleading

### V14 Won't Whipsaw on Microcrashes (2026-03-03)
- All phase transitions require multi-layered structural signals (2W StochRSI, divergence, etc.)
- Ranging exit explicitly REMOVED in V14 (caused 4+ interruptions/coin in v0.1)
- DCA naturally handles ranging (grid buys dips, TPs on bounces)

### Data Sync Cron Can Overwrite Source Files (2026-05-08)
- The dashboard sync script uses a separate temp repo with sparse checkout
- It does `git add docs/` then `git reset HEAD -- ':!docs/'` to unstage non-docs files
- The `':!docs/'` pathspec negation **doesn't work on Windows PowerShell**
- Result: `v14_capital_manager.py` got committed in a "Data sync" commit and pushed to remote
- Every `git pull` in the workspace then restored the bad version
- **Fix**: Replaced pathspec negation with explicit per-file unstage loop
- **Rule**: Always verify pathspec behavior on Windows. PowerShell quotes interact badly with git pathspecs.

### DEX-as-Truth Eliminates Capital Corruption (2026-05-08)
- The bot had 5 systems fighting over capital: CLI arg, state.json, ledger.json, reconciliation, deposit detection
- Each restart compounded errors: reconciliation added phantom trades → deposit detection "corrected" by adding fake deposits → state file carried forward corrupted capital
- DEX wallet balance ($385) vs bot's calculation ($597 or $288) — neither internal number was real
- **Fix**: Read exchange balance on startup. Period. No other source of truth for capital.
- **Rule**: When you have a single authoritative source (the exchange), USE IT. Don't build complex math to approximate what you can just ask.

### Auto-Detection Heuristics Are Fragile (2026-05-08)
- Reconciliation: groups DEX fills into "deals" using time windows and qty matching. Churn fills break the grouping.
- Deposit detection: `exchange_total - unrealized - realized vs tracked_capital`. Works only when tracked_capital IS the seed. Breaks when tracked_capital is the exchange balance.
- Both systems failed silently by doing the wrong thing confidently.
- **Rule**: Heuristic systems need kill switches and manual overrides. "Auto" is not always better.

### In-Memory State Masks Code Corruption (2026-05-08)
- Bot ran fine in memory for hours after `v14_capital_manager.py` was overwritten on disk
- Only failed when manually restarted (fresh import required)
- A "running" process is not proof that code on disk is valid
- **Rule**: Pre-flight import test before every restart. `python -c "from module import Class; print('OK')"`

## Operations

### Stop Gateway Before OpenClaw npm Install (2026-03-02, 2026-03-09)
- Running node process locks files, npm fails silently or crashes mid-install
- Kill node gateway PID directly, then install, then restart
- Burned twice on this — once during 2026.3.1, once during 2026.3.8

### OpenClaw Cron Token Burn (2026-03-04)
- Every cron job was spinning up Claude Opus 4-6 agent turns
- Hourly git backup × Opus = ~400k tokens/day wasted on `git add && git commit`
- **Rule**: Cron jobs should use the cheapest model that can do the job (Haiku)

### Dashboard Sync Recovery (2026-03-09)
- `git push --quiet 2>$null` silently swallowed push failures for 17+ hours
- Dashboard data was stale but nobody noticed until heartbeat check
- **Rule**: Never silence error output from critical operations. Log failures explicitly.

### Genuine vs Synthetic Backfill (2026-03-06)
- Cloning/backdating snapshots creates synthetic data that looks real but isn't
- The `--backfill-history N` and `--as-of` flags generate genuine historical snapshots
- **Rule**: Always prefer genuine data generation over synthetic shortcuts
