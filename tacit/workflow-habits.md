# Workflow Habits
_Patterns that work well. Not rules — just things that improve outcomes._

## Development
- **Read all code before patching** — auditing the full dependency chain prevents patch-on-patch. The V14PM audit found 3 critical bugs because it read every file instead of spot-fixing symptoms.
- **Test restarts, not just runs** — a bot that works on first start may generate phantom trades on restart. Test the kill-restart cycle explicitly.
- **Trace the full data path** — from API call to database table to consumer code. Draw it out if needed. Gaps in the middle are invisible until production.
- **Check DB path resolution with Python, not PowerShell** — PowerShell path manipulation doesn't match Python's `Path().resolve().parent` chains accurately.

## Code Change Procedure (Production Bots)
1. **Write spec** — describe what changes, why, and where
2. **Get approval** from Brett
3. **Make the code change** in the workspace
4. **Pre-flight import test** — `python -c "from module import Class; print('OK')"`
5. **Commit and push** — local-only changes get wiped by any `git pull`. The code on `origin/main` is the durable copy.
6. **Stop the bot** (kill PID)
7. **Restart and verify** — check first 2 poll cycles for correct behavior
8. **Never skip step 5** — the data sync cron, git operations, and even future you will `git pull` at some point. If the fix isn't pushed, it's not real.

## Memory & Documentation
- **Daily notes are raw logs** — write everything that happened, decisions made, bugs found
- **MEMORY.md is curated** — only the distilled essentials that every session needs
- **Project overviews summarize** — current state + key decisions + next steps
- **Tacit knowledge captures patterns** — lessons that apply across projects
- **Architecture docs are living** — update them when code changes, version them

## Trading Operations
- **Check bot health on every heartbeat** — status.json freshness, trade count, equity
- **Batch heartbeat checks** — email + calendar + bots in one pass, rotate other checks
- **Alert thresholds**: status stale > 65 min, drawdown > 15%, process not running
- **Don't react to every market move** — DCA handles ranging. Phase transitions are signal-gated.

## Communication with Brett
- **Be direct** — he values no-fluff communication
- **Data over narrative** — show the numbers, let him draw conclusions
- **Ask before external actions** — sending emails, tweets, anything public
- **Telegram for personal** — his primary channel
- **No desktop Slack** — browser only via Gmail login
