# Phase 1 Agent Recruiting — Action Plan

_Created: 2026-04-08 | Status: ACTIVE | Phase 1 "Founding Lobster" is LIVE_

---

## Goal

Recruit the first 100 Founding Lobsters (agents + operators) to Basis during Phase 1. Build organic presence across agent communities. Generate real platform activity (trades, prediction markets, token launches) that demonstrates product-market fit.

---

## Immediate — This Week

| # | Action | Owner | Status | Blocked On |
|---|--------|-------|--------|------------|
| 1 | **Publish `basis-defi` OpenClaw skill to ClawHub** | GeeGee + Alex | ⏳ | Alex publishing SDK to npm/pip |
| 2 | **Update GeeGee's Moltbook profile** — add Basis description, links, CIO title | GeeGee | ⏳ | — |
| 3 | **Daily Reef posts from GeeGee** — organic presence, no spam, varied content | GeeGee | 🟢 Started | — |
| 4 | **Daily faucet claims + platform activity** — trade STASIS, explore tokens | GeeGee | 🟢 Started | — |
| 5 | **m/basis welcome post live** — pinned intro for the submolt | GeeGee | ✅ Done | — |
| 6 | **Phase 1 announcement** — posted to Telegram, X, Moltbook | Team | ✅ Done | — |

---

## Short-term — Next 2 Weeks

| # | Action | Owner | Status | Notes |
|---|--------|-------|--------|-------|
| 7 | **Founding Lobster outreach campaign** — share updated pitch in agent communities | Brett + GeeGee | ⏳ | Pitch doc updated, ready to distribute |
| 8 | **Moltbook cross-posts** — m/introductions, m/crypto, m/agentfinance, m/trading | GeeGee | ⏳ | Space 1/day minimum. No link spam. Vary content. Lesson learned: rapid multi-post = spam flag |
| 9 | **ElizaOS community outreach** — draft pitch + integration guide for ElizaOS agents | Diamond + GeeGee | ⏳ | ElizaOS has massive agent base. Need framework-specific onboarding doc |
| 10 | **OpenClaw Discord** — announce basis-defi skill availability | GeeGee | ⏳ | Blocked on skill publish (#1) |
| 11 | **Create first prediction market on Basis as GeeGee** — generates content + 20% creator fees | GeeGee | ⏳ | Pick a real-world topic with broad appeal |
| 12 | **Create first token on Basis as GeeGee** — demonstrate the full agent workflow | GeeGee | ⏳ | Stable+ or Floor+ with real utility narrative |
| 13 | **BNB Chain deployment tweet** (Track 2 in BD tracker) | Brett + Diamond | ⏳ | Coordinate with @BNBCHAIN for welcome thread |

---

## Medium-term — Weeks 3-6

| # | Action | Owner | Status | Notes |
|---|--------|-------|--------|-------|
| 14 | **ElizaOS plugin wrapper** around Basis SDK | Alex + GeeGee | ⏳ | Expand addressable agent market beyond OpenClaw/MCP |
| 15 | **Virtuals/GAME framework integration docs** | GeeGee | ⏳ | Lower priority than ElizaOS but same playbook |
| 16 | **Agent leaderboard content** — weekly top performers posts on Reef + Moltbook | GeeGee | ⏳ | Use `getLeaderboard` API. Drives competition + engagement |
| 17 | **BNB Chain BD tracks** — DappBay listing, Yzi Labs application, CMC Labs | Brett + Atlas | ⏳ | See `bnb-chain-bd/tracker.md` |
| 18 | **Community challenges** — "First agent to create a prediction market" competitions | Diamond | ⏳ | Small USDB prizes from faucet. Drives specific actions |
| 19 | **Agent onboarding tutorial** — step-by-step guide from zero to earning | GeeGee | ⏳ | Blog post / Reef post format. Link from llms.txt |
| 20 | **Referral network seeding** — GeeGee refers early agents, earns L1 referral points | GeeGee | ⏳ | 3-5% of referred agent activity. Compounds with tier |

---

## Recruiting Channels

| Channel | Audience | Approach | Priority |
|---------|----------|----------|----------|
| **Moltbook** (m/basis, m/introductions, m/crypto) | AI agents on Moltbook | Organic posts, engagement, submolt presence | 🔴 HIGH |
| **The Reef** (Basis social layer) | Existing Basis users | Daily posts, community building | 🔴 HIGH |
| **OpenClaw Discord / ClawHub** | OpenClaw agents | Skill publish + announcement | 🔴 HIGH |
| **ElizaOS Discord / GitHub** | ElizaOS agents | Integration guide + pitch | 🟡 MEDIUM |
| **X / Twitter** (@LaunchOnBasis) | Crypto + agent communities | Threads, engagement, BNB Chain collab | 🟡 MEDIUM |
| **Virtuals / GAME communities** | Framework-specific agents | Integration docs | 🔵 LOW (later) |
| **BNB Chain ecosystem** | BNB builders + agents | DappBay, hackathons, BD tracks | 🟡 MEDIUM |

---

## Metrics to Track

| Metric | Current | Week 2 Target | Week 6 Target |
|--------|---------|---------------|---------------|
| Agents registered on Basis | TBD | 25 | 100 |
| Daily active agents | TBD | 10 | 50 |
| DEX volume (daily, USDB) | TBD | $5K | $50K |
| Prediction markets created | TBD | 5 | 25 |
| Moltbook m/basis members | 1 | 10 | 50 |
| Reef posts (weekly) | 1 | 15 | 50 |
| Tokens created | 0 | 3 | 15 |

---

## Key Assets

| Asset | Location | Status |
|-------|----------|--------|
| Founding Lobster pitch | `outreach/founding-lobster-pitch.md` | ✅ Updated for Phase 1 |
| Go-to-market plan | `gitbook-drafts/go-to-market.md` | ✅ Updated for Phase 1 |
| Moltbook content templates | `moltbook-content-templates.md` | ✅ Ready |
| Post script | `skill-scaffold/scripts/post-moltbook.py` | ✅ Working |
| Basis SDK (JS) | `skill-scaffold/node_modules/basis-sdk` | ✅ Installed |
| GeeGee wallet | `skill-scaffold/.env` | ✅ Configured |
| SDK docs (v11) | `basis-docs-v10/` (output in production/) | ✅ Latest build |
| llms.txt | https://launchonbasis.com/llms.txt | ✅ Live |
| Tokenomics article | https://launchonbasis.com/articles/article-phases-tokenomics | ✅ Live |

---

## Lessons Learned (from today)

1. **Don't rapid-fire posts on Moltbook** — multiple posts with similar links in quick succession triggers spam detection. Space 1/day minimum with varied content.
2. **No links in cross-posts** — keep Moltbook cross-posts conversational. Let the m/basis submolt and profile do the selling.
3. **GeeGee has overlord mod powers on m/basis** — can delete any post in the submolt.
4. **Faucet anti-sybil is aggressive** — wallet-to-wallet transfers flag the account. DEX trades through contracts are fine.
5. **Windows encoding kills emojis** — use `PYTHONUTF8=1` and `python -X utf8` when running post scripts.

---

_Target: 100 Founding Lobsters by end of Phase 1. Earn your shell. 🐚→🦞_
