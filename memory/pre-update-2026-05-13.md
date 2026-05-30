# Pre-Update Snapshot — 2026-05-13 12:33 PDT

## OpenClaw Version
- Current: 2026.4.11 (769908e)
- Upgrading to: 2026.5.7

## Cron Jobs (6 total)
1. Nightly Memory Consolidation — 2am PT daily (last: error/timeout)
2. V13 Daily Collector — 1:30pm UTC daily (last: ok)
3. Morning Briefing — 7am PT daily (last: ok)
4. System Health Check — 2pm UTC daily (last: ok)
5. OpenClaw Full Backup — 3am PT Sundays (last: ok)
6. Weekly Memory Review — 6pm PT Sundays (last: ok)

## Trading Bots (all running, independent of OpenClaw)
- V14PM Live Aster: running, equity $388.72, drawdown 9.29%
- V14 Paper: running
- V14-ETF Paper: running
- V14PM Paper: running

## Scheduled Tasks: All 4 bot tasks running via Windows Task Scheduler

## Notes
- Bots are Python processes on Windows Scheduled Tasks — unaffected by OpenClaw update
- Cron jobs are persisted in OpenClaw's cron store — preserved across updates
- Workspace files untouched by updater
- Config (openclaw.yaml) preserved
