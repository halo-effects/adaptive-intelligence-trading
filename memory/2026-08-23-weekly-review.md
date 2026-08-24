# Weekly Memory Review — 2026-08-23 (Sunday)

## Scope
Reviewed daily notes (Aug 9–21), `C:\Users\Never\life\` tree, and MEMORY.md.

## Findings / Proposed Changes (awaiting Brett approval)

### 1. MEMORY.md is lagging behind the structured files
- "AIT — Current State" header still dated **2026-07-05** (~7 weeks stale). The Aug 21 TP-fill fixes + Opus 5 note are already captured in `projects/ait/overview.md` and `log.md` but NOT distilled into MEMORY.md.
- **LLM Config** section says "Primary: Claude Opus 4.6" — outdated. Opus 5 is now default (Aug 9). Current run is Opus 4.8.
- **Proposed**: Refresh the AIT summary date/content and correct the LLM Config block.

### 2. projects/_index.md is incomplete
- Only lists **AIT** and **Basis**. But 4 project folders exist: `ait`, `basis`, `shadowquery`, `tbr`.
- **ShadowQuery** (last updated 2026-02-24, ~6 mo) — status "Deferred", moved to Slack w/ Adeel.
- **TBR migration** (last updated 2026-02-24, ~6 mo) — was mid-cleanup (~1,900 spam pages + 2 plugins left).
- **Proposed**: Add ShadowQuery + TBR to the index with current (likely dormant) status, OR confirm they're dead so I can archive. Need your call on whether either is still live.

### 3. Finances overview has a contradiction
- `areas/finances/overview.md` lists **V14-ETF** as active (+42% PnL) in one line AND as RETIRED (2026-03-17) two lines later.
- **Proposed**: Remove the stale "active" V14-ETF line; keep only the retirement record.

### 4. Basis project — confirm status
- `_index.md` marks Basis "Archive/Waiting" (out of active dev since 2026-05-17, SHELL phase).
- `projects/basis/overview.md` is a large, detailed doc last updated 2026-03-22 with a big "Still Pending" list (mostly Alex deliverables).
- **Proposed**: Leave the detailed doc intact (good reference), but no action needed unless the team reactivates. Confirm it's still dormant.

### 5. People index (resources/people/_index.md)
- Last updated 2026-03-12 (~5 mo). Lists Adeel (active) + 3 Basis team members (Diamond/Atlas/Alex).
- Basis members are effectively dormant while Basis waits. Adeel still active (ShadowQuery/TBR).
- **Proposed**: No deletions. Optionally annotate Basis members as "dormant (Basis paused)". Low priority.

### 6. MEMORY.md entries >30 days
- The bulk of MEMORY.md is the AIT current-state block, which is legitimately current (production bot). Not stale in the "remove" sense — just needs the date/summary refresh in #1.
- No entries recommended for outright removal. Lessons-learned and hard-rules are append-only historical records (correctly kept).

## No changes made yet — all pending your review.
