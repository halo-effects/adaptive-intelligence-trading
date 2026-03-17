# Points System — Master Build Plan

_Author: GeeGee + Brett | Date: 2026-03-17_
_Three phases, three systems, one rewards engine._

---

## Overview

The Basis points/rewards system is composed of **three independent subsystems** that feed into a single wallet score. Each phase can be built, tested, and deployed separately. Phase 1 is fully spec'd and ready to build today. Phases 2 and 3 are documented here so the full picture is clear.

```
┌─────────────────────────────────────────────────────┐
│                  POINTS ENGINE                       │
│                                                      │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ │
│  │   PHASE 1    │ │   PHASE 2    │ │   PHASE 3    │ │
│  │  On-Chain    │ │   Social     │ │  Referrals   │ │
│  │  Activity    │ │ Engagement   │ │  & Growth    │ │
│  │              │ │              │ │              │ │
│  │ • Trading    │ │ • X/Twitter  │ │ • Referral   │ │
│  │ • Tokens     │ │ • Moltbook   │ │   chains     │ │
│  │ • Predictions│ │ • Content    │ │ • Wallet     │ │
│  │ • Lending    │ │   verify     │ │   registration│ │
│  │ • Vault      │ │ • Anti-spam  │ │ • Sybil      │ │
│  │              │ │              │ │   defense    │ │
│  └──────┬───────┘ └──────┬───────┘ └──────┬───────┘ │
│         │                │                │          │
│         ▼                ▼                ▼          │
│  ┌───────────────────────────────────────────────┐   │
│  │          Unified Wallet Score                 │   │
│  │   points + multipliers + tier + rank          │   │
│  └───────────────────────────────────────────────┘   │
│         │                                            │
│         ▼                                            │
│  ┌───────────────────────────────────────────────┐   │
│  │   API: /points/{wallet}  +  /leaderboard      │   │
│  └───────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────┘
```

---

## Phase 1 — On-Chain Activity Points

**Status:** ✅ Fully spec'd → `points-system-build-spec.md`
**Dependencies:** Existing contract indexer, BNB Chain RPC
**Scope:** Watch on-chain events from 13 deployed contracts, compute points, serve API

### What it covers:
- Token creation (500 pts per launch)
- DEX trading (1 pt/$1 volume, 2x during bonding)
- Prediction markets (creation, betting, resolution)
- Lending (take/extend/repay loans)
- Vault staking (daily accrual at 2 pts/$1/day, refinance bonuses)
- Multipliers: streak, diversity, volume tier, Founding Lobster, Early Bird
- Anti-gaming: min trade sizes, daily caps, same-pair cooldown

### Deliverables:
- Event indexer (poll-based, piggyback on existing pipeline)
- Points engine (rules + filters)
- Database (point_events, wallet_points, daily_activity, indexer_state)
- API: `GET /api/v1/points/{wallet}` + `GET /api/v1/leaderboard`
- Vault daily accrual cron

### Build doc: `points-system-build-spec.md` (complete with Claude Code prompt)

---

## Phase 2 — Social Engagement Points

**Status:** 📋 Designed, spec not yet written
**Dependencies:** Phase 1 (points engine + API must exist), X/Twitter API, content verification system
**Scope:** Reward social promotion of Basis across X and eventually Moltbook

### What it covers:

**X/Twitter Actions:**

| Action | Base Points | Frequency Cap | Verification |
|---|---|---|---|
| Post with @LaunchOnBasis tag | 50 | 1x/day | X API: confirm post exists, min 20 words |
| Reply to @LaunchOnBasis posts | 25 | 3x/day | X API: confirm reply, substantive (not just emoji) |
| Quote tweet with commentary | 75 | 1x/day | X API: min 30 words original text |
| Engage with Basis users' posts | 15 | 5x/day | X API: like + reply combo verified |
| Thread about a Basis feature | 150 | 1x/week | X API: min 3 tweets, educational content |

**Performance Multipliers (on social points):**

| Engagement Level | Multiplier |
|---|---|
| >50 engagements | 2x |
| >500 engagements | 5x |
| Video content | 3x base |
| Tutorial with referral link | 3x base |
| Viral (>5,000 engagements) | 10x |

**Moltbook Actions (when Moltbook is live):**

| Action | Base Points | Frequency Cap |
|---|---|---|
| Post market analysis / prediction thesis | 100 | 1x/day |
| Comment on another user's post | 25 | 5x/day |
| Share a trade receipt / earning report | 75 | 1x/day |
| Create a strategy guide | 200 | 1x/week |

### Anti-spam requirements:
- X accounts must have: 30+ day age, 10+ followers, prior post history
- One X account per wallet (no sharing)
- Content similarity detection across wallets (near-identical = flagged and zeroed)
- Engagement verification: confirm likes/replies actually happened via X API

### New components needed:
- **X API integration service** — verify posts, check engagement metrics, validate accounts
- **Wallet-to-X linking** — one-time setup: wallet signs message, links X handle
- **Content dedup engine** — hash/similarity check across posts to catch copy-paste farming
- **Social points processor** — separate module that feeds into the same wallet_points table from Phase 1

### Database additions:
```sql
CREATE TABLE social_links (
    wallet VARCHAR(42) PRIMARY KEY,
    x_handle VARCHAR(50),
    x_user_id VARCHAR(30),
    x_account_age TIMESTAMP,
    x_followers INT,
    linked_at TIMESTAMP DEFAULT NOW(),
    verified BOOLEAN DEFAULT FALSE
);

CREATE TABLE social_events (
    id SERIAL PRIMARY KEY,
    wallet VARCHAR(42) NOT NULL,
    platform VARCHAR(20) NOT NULL,     -- 'x', 'moltbook'
    action VARCHAR(50) NOT NULL,        -- 'post', 'reply', 'quote', 'thread'
    content_hash VARCHAR(64),           -- for dedup
    external_id VARCHAR(100),           -- tweet ID, moltbook post ID
    engagement_count INT DEFAULT 0,
    base_points DECIMAL NOT NULL,
    multiplier DECIMAL DEFAULT 1.0,
    final_points DECIMAL NOT NULL,
    verified BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW()
);
```

### Integration with Phase 1:
- Social points feed into the same `wallet_points.total_points`
- Add `social_points` column to `wallet_points` table
- Social activity counts toward daily streak and diversity bonus
- "social" becomes the 6th product category for diversity checks

---

## Phase 3 — Referrals & Growth Points

**Status:** 📋 Designed, spec not yet written
**Dependencies:** Phase 1 (points engine), wallet registration system
**Scope:** Referral chains, agent wallet registration, growth incentives, sybil defense

### What it covers:

**Referral System:**

| Action | Points | Notes |
|---|---|---|
| Refer a new user/agent | 10% of referee's LIFETIME points | Ongoing, recalculated as referee earns |
| First action by referred user | 200 bonus to referrer | One-time trigger |
| Share a Basis receipt publicly | 50 | Verified via link tracking |

**Key mechanic:** Referral points are *derived*, not static. If your referee earns 10,000 points over 6 months, you earn 1,000. This means referral points update as the referee's total updates — needs efficient recalculation.

### Agent Wallet Registration:
- `POST /api/v1/agents/register` — register wallet as agent with metadata:
  - Agent name, framework (OpenClaw/AutoGPT/CrewAI/etc.), operator wallet, description
  - ERC-8004 identity (auto-created by SDK with `agent=True`)
- Soulbound "Founding Lobster" NFT (ERC-721, non-transferable) for Phase 0 agents
- `GET /api/v1/agents/{wallet}` — query agent profile

### Anti-Sybil Defense (6-layer):

| Layer | What It Does | Implementation |
|---|---|---|
| 1. Cost to Exist | Min USDB balance ($50), BNB for gas, agent instance costs | Check balance on first point event |
| 2. Cost to Earn | Min trade sizes, ≥5 unique participants for prediction creator points, daily caps | Already in Phase 1 |
| 3. Graph Analysis | Funding source clustering, transaction graph, timing correlation | Batch job — run pre-airdrop |
| 4. Reputation = Time | Molt tier system requires weeks of consistent diverse activity | Already in Phase 1 |
| 5. Social Verification | X account requirements, one account per wallet, content dedup | Phase 2 |
| 6. Progressive Conviction | ACS score + Molt tiers compound; high-tier wallets earn 20x low-tier | Airdrop distribution weighting |

**Graph analysis** is the heavy hitter — run as a batch analysis before any airdrop distribution:
- Cluster wallets by funding source (same origin = flag)
- Measure unique counterparty count (sybils trade in tight loops)
- Detect timing correlation (bot farms transact in lockstep)
- 7-day appeal window for flagged clusters before final distribution

### Referral tracking schema:
```sql
CREATE TABLE referrals (
    referrer_wallet VARCHAR(42) NOT NULL,
    referee_wallet VARCHAR(42) NOT NULL UNIQUE,  -- each wallet can only be referred once
    referral_code VARCHAR(20) NOT NULL,
    referee_first_action BOOLEAN DEFAULT FALSE,
    referee_funding_source VARCHAR(42),          -- for sybil check
    created_at TIMESTAMP DEFAULT NOW(),
    PRIMARY KEY (referrer_wallet, referee_wallet)
);

CREATE TABLE agent_profiles (
    wallet VARCHAR(42) PRIMARY KEY,
    agent_name VARCHAR(100),
    framework VARCHAR(50),          -- openclaw, autogpt, crewai, custom
    operator_wallet VARCHAR(42),
    description TEXT,
    erc8004_id VARCHAR(66),
    is_founding_lobster BOOLEAN DEFAULT FALSE,
    founding_nft_id VARCHAR(66),
    registered_at TIMESTAMP DEFAULT NOW()
);

-- Add to wallet_points:
-- referral_points DECIMAL DEFAULT 0
```

### Integration with Phase 1 + 2:
- Referral points add a `referral_points` column to `wallet_points`
- Referral code generated at registration → stored in `referrals` table
- Derived points need recalculation trigger (daily batch or on-query)
- ACS score combines: agent registration data + on-chain behavior + social verification
- Sybil flags can zero out a wallet's points retroactively

---

## Build Sequence Summary

| Phase | System | Build Doc | Dependencies | Status |
|---|---|---|---|---|
| **1** | On-Chain Activity | `points-system-build-spec.md` | Existing indexer, BNB RPC | ✅ Spec complete |
| **2** | Social Engagement | `points-system-phase2-spec.md` (TBD) | Phase 1 + X API | 📋 Designed in this doc |
| **3** | Referrals & Growth | `points-system-phase3-spec.md` (TBD) | Phase 1 + wallet registration | 📋 Designed in this doc |

Each phase gets its own Claude Code–ready spec when it's time to build. Phase 1 is ready now. Phases 2 and 3 specs can be written whenever Alex is ready for them — all the design work is captured here.

**Alex:** You can build all three sequentially, or tackle Phase 1 now and we'll hand you Phase 2 + 3 specs when you're ready. Your call.

---

_Source: project-plan.md §6B (full points design), earning-guide.md, dev-plan.md §0.3_
