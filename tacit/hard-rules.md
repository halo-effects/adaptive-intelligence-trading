# Hard Rules
_Non-negotiable rules from production incidents. Violating these causes real damage._

## Trading Bots

1. **`recorded_at` field is mandatory** on every trade record. It's the forensic backstop. (2026-03-09)

2. **Kill the bot BEFORE writing trades.csv** — running bot overwrites the file on every cycle. (2026-03-09)

3. **Never use PowerShell `Export-Csv` for trades.csv** — it mangles format. Use direct `write()` with explicit content. (2026-03-09)

4. **PM scheduled task must NOT use `--fresh`** — state persistence handles restarts. `--fresh` is for first launch only. (2026-03-10)

5. **PID lock is mandatory on Windows** paper bots — prevents duplicate instances from scheduled task + manual overlap. (2026-03-09)

6. **24-hour post-launch audit** — after any bot change, review trades within 24h for phantom/anomalous trades. (2026-03-09)

7. **Confirm capital with Brett** before changing any bot's capital parameter. I mistakenly "fixed" PM from $50K to $10K. (2026-03-06)

8. **Validate allocation output** after any rebalance logic change — check that the numbers make sense before restarting. (2026-03-06)

## Data & Code

9. **All DB_PATH references must resolve to `trading/spot/data/candles.db`** — the 214 MB file. A 0-byte trap exists at `trading/data/candles.db`. (2026-03-10)

10. **Trace data flow end-to-end** before declaring a pipeline "working". Collector→daily→signals→engine is 4 hops, and a gap between any two = silent failure. (2026-03-10)

11. **State persistence is not optional** — if an engine has runtime state, it must be saved and restored across restarts. (2026-03-10)

## OpenClaw & Infrastructure

12. **Stop gateway BEFORE npm install** — file locking crash. Accept offline period. (2026-03-02, 2026-03-09)

13. **Cron jobs use cheapest model** — Haiku for routine checks, not Opus. (2026-03-04)

14. **Never silence error output** from git push, API calls, or critical operations. Log failures explicitly. (2026-03-09)

## Communication

15. **Don't build narratives from user prompts** — let data lead. If Brett asks about DeFi coins, check the data before recommending DeFi coins. (2026-03-03)

16. **Don't send half-baked replies** to messaging surfaces. Get it right first. (AGENTS.md)

17. **Verify before claiming something is broken.** Check actual processes, actual data, actual files. Do not speculate or hallucinate problems — that erodes trust and compounds issues. If you don't know, say "I don't know" instead of building a theory. (2026-03-10)

18. **Architecture doc is single source of truth.** `V14PM_SYSTEM_ARCHITECTURE.md` → `CLOUD_MIGRATION_GUIDE.md` → Dashboard. Dashboard is the real-world verification. If dashboard is wrong, trace back to a system bug — don't blame the data first. (2026-03-10)
