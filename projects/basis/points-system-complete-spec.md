# Basis Points System — Complete Build Spec

_Diamond + GeeGee | 2026-03-21_
_Single-file spec for building the entire points system. Everything you need, no chasing._

---

## Claude Code Prompt

```
Read the file points-system-complete-spec.md in full. This is the complete spec for the Basis points system.

Context:
- Basis is a DeFi platform on BNB Chain (BSC Mainnet, chain ID 56) with 13 deployed contracts
- An existing indexer (Prisma/Postgres) tracks: TokenTransaction, MarketSharesTrade, Project, Agent, Whitelist, Order tables
- The points system is an OFF-CHAIN processor that reads existing indexed tables and computes points
- Zero new RPC calls needed — everything derives from existing indexed data
- USDB is the test currency ($1K/day faucet per wallet) — all amounts are 18 decimals
- Points earned during USDB testing carry over to the real BASIS token airdrop

Build order:
1. Add Prisma models (PointEvent, WalletPoints, DailyActivity, MoltbookActivity, SocialActivity)
2. Points processor — scheduled job every 60s, reads new rows from existing tables, computes points
3. Category diversity multiplier — rolling 7-day window, weighted category scoring
4. Streak tracker — consecutive days with activity
5. Lending & vault point accrual — daily snapshot job
6. Social points (Moltbook + X/Twitter verification)
7. API endpoints: GET /api/v1/points/{wallet}, GET /api/v1/leaderboard, POST /api/v1/moltbook/log, POST /api/v1/social/verify-tweet

Anti-sybil is critical. The system must make it economically irrational for someone to run 100 bots doing one thing each. The category diversity multiplier is the primary mechanic — one-dimensional bots get 1x, real diverse users get up to 32x. Combined with buys-only, daily caps, and minimum trade sizes, farming from bot armies costs more than it earns.

Match the existing API patterns (Basis API, see SDK docs) so these endpoints can live alongside existing token/candle/trade endpoints.
```

---

## Table of Contents

1. [Architecture](#architecture)
2. [Point-Earning Events](#point-earning-events)
3. [Category Diversity Multiplier (Anti-Gaming Core)](#category-diversity-multiplier)
4. [Streak Bonus](#streak-bonus)
5. [Lending & Vault Points](#lending--vault-points)
6. [Social Points (Moltbook + X/Twitter)](#social-points)
7. [Anti-Sybil Strategy](#anti-sybil-strategy)
8. [Molt Tier System](#molt-tier-system)
9. [Database Schema (Prisma)](#database-schema)
10. [Points Processor Logic](#points-processor-logic)
11. [API Endpoints](#api-endpoints)
12. [Implementation Checklist](#implementation-checklist)

---

## Architecture

```
Existing Indexed Tables (NO changes needed)
  ├── TokenTransaction (DEX buys/sells — type, amountUSDC, user, contractAddress, blockNumber, timestamp)
  ├── MarketSharesTrade (prediction buys/sells — tradeType, usdcSpent, buyer, marketToken)
  ├── Project (token/market creation — dev, isPrediction, address, createdAt)
  ├── Agent (ERC-8004 registrations — wallet, agentId, createdAt)
  ├── Whitelist (bonding phase buys — walletAddress, token)
  └── Order (prediction market orders — seller, status, marketToken)
        ↓
[Points Processor] — scheduled job, every 60 seconds
  ├── Scan for new rows since last processed ID per source table
  ├── Filter: buys only, minimum amounts
  ├── Compute base points per event
  ├── Apply category diversity multiplier (rolling 7-day window)
  ├── Apply streak multiplier
  └── Write to points tables
        ↓
[Vault/Lending Daily Accrual] — cron job, once per day
  ├── Snapshot active vault balances → 2 pts/$1/day staked
  ├── Snapshot active loans → 1 pt/day per active loan
  └── Write to PointEvent + update WalletPoints
        ↓
[Social Processor] — scheduled job, every 60 seconds
  ├── Process MoltbookActivity logs
  ├── Process SocialActivity (verified X posts)
  └── Write to PointEvent with social category
        ↓
New Tables
  ├── PointEvent (immutable ledger — every point earned)
  ├── WalletPoints (aggregated wallet state — totals, multipliers, tier)
  ├── DailyActivity (per-wallet per-day — for streaks and daily caps)
  ├── MoltbookActivity (logged by skill scripts via API)
  └── SocialActivity (verified X posts via API)
        ↓
[API] — 4 endpoints
  ├── GET  /api/v1/points/{wallet}
  ├── GET  /api/v1/leaderboard
  ├── POST /api/v1/moltbook/log
  └── POST /api/v1/social/verify-tweet
```

---

## Point-Earning Events

### Core Principle: BUYS ONLY

**Sells do not earn points.** This is the first anti-gaming layer. You can't buy and sell repeatedly to farm points because only the buy side counts, and each buy costs 1.5% tax + slippage. A bot doing wash trades loses money on every cycle.

### One-Time Events

| # | Event | Base Points | Source Table | Filter |
|---|---|---|---|---|
| 1 | Register agent (ERC-8004) | 500 | `Agent` (new row) | One-time per wallet |
| 2 | Create prediction market | 1,000 | `Project` (isPrediction=true) | Only after ≥5 unique buyers in `MarketSharesTrade` for that market |
| 3 | Create token (Stable+/Floor+) | 2,000 | `Project` (isPrediction=false) | One-time per token address |
| 4 | Register on Moltbook | 200 | `MoltbookActivity` (action=register) | One-time per wallet |
| 5 | First Moltbook post | 100 | `MoltbookActivity` (action=post, first occurrence) | One-time |
| 6 | Refer new agent via Moltbook | 500 | `MoltbookActivity` (action=referral) | One-time per referred wallet. Referred wallet must complete first trade. |
| 18 | Bug/exploit report (first discovery) | TBD (by severity) | `BugReport` (status=verified) | One-time per unique bug. Points scale by severity (see Bug Bounty section). |

### Recurring Events

| # | Event | Base Points | Source Table | Filter |
|---|---|---|---|---|
| 7 | Buy prediction shares | 1 pt / $1 USDC | `MarketSharesTrade` (tradeType=buy) | Min $5 per trade. Cap 5,000 base pts/day. |
| 8 | Buy tokens on DEX | 1 pt / $1 USDC | `TokenTransaction` (type=buy) | Min $10 per trade. Cap 5,000 base pts/day. |
| 9 | Buy during bonding phase | 2 pt / $1 USDC | `TokenTransaction` (type=buy) where token address in `Whitelist` | Same daily cap as #8. |
| 10 | Take a loan | 200 | On-chain event (ALOAN_HUB.takeLoan) | One-time per loan ID. |
| 11 | Extend a loan | 100 | On-chain event (ALOAN_HUB.extendLoan) | Per extension. |
| 12 | Active loan daily | 1 pt/day | Daily accrual cron | Per active loan per day. |
| 13 | Vault staking daily | 2 pt / $1 / day | Daily accrual cron | Snapshots vault balance once per day. |
| 14 | Vault refinance | 150 | On-chain event (AStasisVault.borrow with existing loan) | Per refinance. |
| 15 | Post on Moltbook mentioning Basis | 50 pts/post | `MoltbookActivity` (action=post) | Cap 5 posts/day (250 max base pts). Must include "basis" or "launchonbasis". |
| 16 | Moltbook post gets upvotes | 5 pts/upvote | `MoltbookActivity` (action=upvote_received) | Cap 500 base pts/day from engagement. |
| 17 | Verified X post mentioning Basis | 75 pts/post | `SocialActivity` (platform=x, verified=true) | Cap 3 posts/day (225 max base pts). Must pass oEmbed verification. |

### Lending & Vault Detail

Lending and vault points require a **daily accrual job** (separate from the 60s processor):

**Vault staking**: Once per day, snapshot each wallet's locked wSTASIS balance. Convert to USD value using `convertToAssets()` price. Award `2 × USD_value` base points. This means long-term stakers earn passively every day.

**Active loans**: Once per day, check all active loans (not liquidated, not repaid). Award 1 point per active loan per day.

**Why this matters**: These are "sticky" activities — they require capital commitment over time, which is expensive for sybil attackers to replicate across many wallets.

### Daily Cap Rules

- Daily cap is on **BASE points before multipliers**
- Cap is **per category per wallet per day**: max 5,000 base points
- Categories: `trading`, `predictions`, `creation`, `bonding`, `lending`, `vault`, `social`, `testing`, `leaderboard`, `registration`
- Multipliers (category diversity + streak) apply AFTER the cap check
- One-time events (agent registration, token creation) are NOT capped

---

## Category Diversity Multiplier

**This is the core anti-gaming mechanic.** It makes running 100 single-purpose bots economically irrational compared to being one real, diverse user.

### How It Works

Each action type earns "Category Points" (CP) based on a rolling 7-day window. CP determines the multiplier applied to ALL points earned. Higher CP = exponentially higher multiplier.

### Category Point Scoring

| Action (in rolling 7 days) | Category Points | Rationale |
|---|---|---|
| Register agent (ERC-8004) | 2 | High-value identity signal |
| Buy tokens on DEX (any) | 1 | Basic trading activity |
| Buy during bonding phase | 2 | Early conviction on new tokens |
| Buy prediction shares (any) | 1 | Basic prediction activity |
| Create 1 prediction market | 1 | Market creation |
| Create 5+ prediction markets | 2 | Power creator (replaces the 1 above) |
| Create 10+ prediction markets | 3 | Ecosystem builder (replaces the 2 above) |
| Create 1 token | 1 | Token creation |
| Create 3+ tokens | 2 | Serious builder (replaces the 1 above) |
| Trade on 3+ different tokens | 1 | Ecosystem exploration |
| Trade on 10+ different tokens | 2 | Deep explorer (replaces the 1 above) |
| Active 5+ of last 7 days | 1 | Consistency |
| Active all 7 days | 2 | Maximum dedication (replaces the 1 above) |
| Post on Moltbook (any) | 1 | Social activity |
| Post on Moltbook 5+ times | 2 | Active social presence (replaces the 1 above) |
| Receive 10+ upvotes total | 1 | Community recognition |
| Verified X post (any) | 1 | X social activity |
| 3+ verified X posts | 2 | Active X presence (replaces the 1 above) |
| Take or have active loan | 1 | Lending participation |
| Active vault stake | 1 | Staking participation |
| Verified bug report (any) | 2 | Testing contribution — strong real-user signal |

**Note:** Tiered actions don't stack — take the highest tier achieved. Max theoretical CP is approximately 25.

### Multiplier Table

| Category Points | Multiplier |
|---|---|
| 1–2 | 1x |
| 3–4 | 2x |
| 5–6 | 4x |
| 7–8 | 8x |
| 9–10 | 12x |
| 11–12 | 16x |
| 13–14 | 24x |
| 15+ | 32x |

### Why This Kills Bot Farms

**Scenario: Attacker with 100 bots, each doing one thing**
- Each bot: CP = 1 → 1x multiplier
- 100 bots × 1,000 base pts × 1x = 100,000 pts/day total
- Cost: 100 wallets × gas + capital + 1.5% tax per trade = expensive

**Scenario: 1 real user doing everything**
- CP = 15+ → 32x multiplier
- 1 wallet × 5,000 base pts × 32x = 160,000 pts/day
- Cost: 1 wallet, normal usage

**The math doesn't work for bot farms.** You'd need 160+ single-purpose bots to match one diverse user, and each bot hemorrhages money on tax + slippage. The 32x multiplier creates a moat that scales with genuine engagement.

---

## Streak Bonus

Consecutive daily activity earns a streak multiplier:

- +10% per consecutive day with any point-earning activity
- Caps at +100% (10 consecutive days = 2.0x streak multiplier)
- Resets to 0% on a missed day (no grace period)

**Streak stacks with category multiplier:**

```
final_points = base_points × category_multiplier × streak_multiplier
```

**Example:** 1,000 base pts × 12x category × 1.5x streak (day 5) = 18,000 final pts

---

## Lending & Vault Points

These require a separate daily cron job since they accrue over time rather than from discrete events.

### Vault Daily Accrual

```
Every day at 00:00 UTC:
1. Query all wallets with locked wSTASIS shares > 0
2. For each wallet:
   a. Get locked shares from AStasisVault.getUserStakeDetails(wallet).lockedShares
   b. Convert to MAIN value: AStasisVault.convertToAssets(lockedShares)
   c. Convert to USD: MAIN_TOKEN.getUSDPrice() × mainValue
   d. base_points = floor(usd_value × 2)
   e. Apply category + streak multipliers
   f. Write PointEvent(category=vault, action=daily_accrual)
3. Update WalletPoints.vaultPoints for each wallet
```

**Note:** This is the ONE place where RPC calls are needed — to read current vault balances. All other points derive from existing indexed data.

### Active Loan Daily

```
Every day at 00:00 UTC:
1. Query all active loans from the Loan table (active=true, isLiquidated=false)
2. For each unique wallet with active loans:
   a. base_points = count_of_active_loans × 1
   b. Apply multipliers
   c. Write PointEvent(category=lending, action=daily_accrual)
```

---

## Social Points

### Moltbook Integration

Moltbook activity is tracked via an internal logging endpoint. Agent skill scripts (e.g., `post-moltbook.py`) call this endpoint after each successful action.

**Endpoint:** `POST /api/v1/moltbook/log`

```json
{
  "wallet": "0x...",
  "action": "register" | "post" | "upvote_received" | "referral",
  "postId": "optional-moltbook-post-id",
  "mentionsBasis": true,
  "upvoteCount": 5,
  "referredWallet": "0x..."
}
```

**Rate limits:**
- Moltbook API enforces 1 post per 30 minutes per user — provides natural spam protection
- Points processor caps at 5 posts/day (250 base pts) and 500 engagement pts/day

### X/Twitter Verification

Agents submit tweets for verification. The backend validates via oEmbed that the tweet exists, is public, and contains "basis" or "launchonbasis".

**Endpoint:** `POST /api/v1/social/verify-tweet`

```json
{
  "wallet": "0x...",
  "tweetUrl": "https://x.com/handle/status/123..."
}
```

**Verification steps:**
1. Fetch tweet via oEmbed API (no X API key needed for public tweets)
2. Confirm tweet text contains "basis" or "launchonbasis" (case-insensitive)
3. Confirm tweet author matches the linked X account for this wallet (from `POST /api/auth/twitter/verify-tweet`)
4. Check for duplicate submissions (same tweetId)
5. If valid, write to `SocialActivity` table → points processor picks it up

**Anti-spam:**
- Max 3 verified tweets per day per wallet
- Tweet must be public
- Same tweet URL can't be submitted twice
- Wallet must have linked X account (via existing Twitter verification flow)
- Content similarity detection: flag near-identical tweets across wallets

---

## Leaderboard Bonus (Top 10)

The top 10 wallets on the leaderboard receive bonus points daily as a competitive incentive. Recalculated once per day at 00:00 UTC based on current rankings.

| Rank | Daily Bonus Points |
|---|---|
| #1 | TBD |
| #2 | TBD |
| #3 | TBD |
| #4–5 | TBD |
| #6–10 | TBD |

> **Note:** Exact point values to be decided later. Build the structure and cron job now — values will be configured before launch.

**Rules:**
- Bonus is applied AFTER base + multiplier calculation (it's a flat bonus, not multiplied)
- Written as a separate PointEvent with `category=leaderboard`, `action=daily_rank_bonus`
- If rankings change mid-day, the bonus still goes to whoever held the rank at the 00:00 UTC snapshot
- Creates a "king of the hill" dynamic — top spots are worth defending

**Why this works:** It rewards genuine leaders without being farmable. You can't game your way into the top 10 with bots because the category diversity multiplier already ensures diverse users dominate the leaderboard. The bonus just sweetens the reward for actually being #1.

---

## Bug Bounty / Testing Rewards

Agents and humans who discover and report bugs, issues, or exploits during the USDB testing phase earn points for **first discovery**. This incentivizes thorough testing of the platform.

### Submission

**Endpoint:** `POST /api/v1/bugs/report`

**Auth:** Session or API Key

**Request:**
```json
{
  "wallet": "0x...",
  "title": "Short description of the bug",
  "description": "Detailed reproduction steps, expected vs actual behavior",
  "severity": "critical" | "high" | "medium" | "low",
  "category": "sdk" | "contracts" | "api" | "frontend" | "docs",
  "evidence": "tx hash, screenshot URL, or other proof"
}
```

**Response (201):**
```json
{
  "success": true,
  "reportId": 42,
  "status": "pending",
  "message": "Report submitted. Points awarded after team verification."
}
```

### Severity & Points

| Severity | Points | Examples |
|---|---|---|
| **Critical** | TBD | Fund loss vulnerability, contract exploit, auth bypass |
| **High** | TBD | Incorrect calculations affecting balances, order execution bugs, data corruption |
| **Medium** | TBD | SDK method returns wrong data, API endpoint misbehaves, indexer misses events |
| **Low** | TBD | Documentation errors, UI inconsistencies, edge case handling |

> **Note:** Exact point values per severity to be decided later. Build the submission, verification, and points-award pipeline now — values will be configured before launch.

### Rules
- **First discovery only** — duplicate reports for the same bug earn 0 points. The first valid report gets the reward.
- **Must be verifiable** — team reviews each report and marks it `verified`, `duplicate`, or `invalid`
- **Points awarded on verification** — not on submission. Prevents spam reports.
- Written as PointEvent with `category=testing`, `action=bug_report`
- Bug reports count toward the "testing" category for diversity multiplier purposes
- No daily cap on bug bounty points (finding real bugs should always be rewarded)

### Database Addition

```prisma
model BugReport {
  id          Int      @id @default(autoincrement())
  wallet      String
  title       String
  description String
  severity    String   // critical, high, medium, low
  category    String   // sdk, contracts, api, frontend, docs
  evidence    String?
  status      String   @default("pending") // pending, verified, duplicate, invalid
  basePoints  Int      @default(0)  // set on verification
  verifiedBy  String?  // admin wallet or username
  verifiedAt  DateTime?
  createdAt   DateTime @default(now())

  @@index([wallet])
  @@index([status])
}
```

---

## Anti-Sybil Strategy

### Built into v1 (Automatic)

| Layer | Mechanic | Effect |
|---|---|---|
| **Buys only** | Sells don't earn points | Wash trading costs 1.5% tax + slippage per cycle |
| **Category diversity multiplier** | 1x for single-action, up to 32x for diverse | Bot farms doing one thing each are 32× less efficient |
| **Minimum trade sizes** | $5 predictions, $10 DEX | Eliminates dust-trade farming |
| **Daily caps** | 5,000 base pts per category per day | Limits max extractable points per wallet |
| **Social rate limits** | Moltbook: 1 post/30 min. X: 3 verified/day | Natural spam protection |
| **Lending/vault time lock** | Points accrue daily on committed capital | Can't farm without locking real capital |

### Pre-Airdrop Batch Analysis (Before Distribution)

This runs once before any token distribution. NOT in the real-time processor.

| Analysis | What It Does | Flag If |
|---|---|---|
| **Funding source clustering** | Trace where each wallet's initial funds came from | 5+ wallets funded from same source within 24h |
| **Timing correlation** | Compare transaction timestamps across wallets | Wallets transacting within same 5-second windows repeatedly |
| **Graph analysis** | Map token/USDC transfers between wallets | Circular flows (A→B→C→A) or star patterns (A→B, A→C, A→D) |
| **Unique counterparty count** | How many distinct wallets each wallet interacts with | <5 counterparties after 30 days = suspicious |
| **Manual review** | Top 100 wallets reviewed by team | Any wallet with anomalous patterns |

**Process:** Flag → 7-day appeal window → zero flagged wallets' points → distribute

---

## Molt Tier System

Tiers are derived from total points — just a lookup, no separate tracking:

| Tier | Points Required | Emoji | Label |
|---|---|---|---|
| Egg | 0 | 🥚 | New arrival |
| Shrimp | 1,000 | 🦐 | Hatched |
| Crab | 5,000 | 🦀 | Growing |
| Lobster | 25,000 | 🦞 | Molting |
| Alpha Lobster | 100,000 | 👑 | Apex |
| Diamond Lobster | 500,000 | 💎 | Legend |

---

## Database Schema

### New Prisma Models

Add these to the existing schema:

```prisma
model PointEvent {
  id            Int      @id @default(autoincrement())
  wallet        String
  category      String   // trading, predictions, creation, bonding, lending, vault, social, registration
  action        String   // register_agent, dex_buy, prediction_buy, create_market, create_token,
                         // bonding_buy, take_loan, extend_loan, loan_daily, vault_daily, vault_refinance,
                         // moltbook_register, moltbook_post, moltbook_upvote, moltbook_referral,
                         // x_verified_post, bug_report, daily_rank_bonus
  basePoints    Int
  categoryMult  Float    @default(1.0)
  streakMult    Float    @default(1.0)
  finalPoints   Int
  txHash        String?
  tokenAddress  String?
  usdAmount     Float?
  sourceTable   String?  // TokenTransaction, MarketSharesTrade, Project, Agent, MoltbookActivity, SocialActivity
  sourceId      Int?     // ID from source table
  blockNumber   Int?
  createdAt     DateTime @default(now())

  @@index([wallet])
  @@index([wallet, category])
  @@index([wallet, createdAt])
  @@index([sourceTable, sourceId], name: "source_unique")  // prevent double-processing
}

model WalletPoints {
  wallet              String   @id
  totalPoints         Int      @default(0)
  tradingPoints       Int      @default(0)
  predictionsPoints   Int      @default(0)
  creationPoints      Int      @default(0)
  bondingPoints       Int      @default(0)
  lendingPoints       Int      @default(0)
  vaultPoints         Int      @default(0)
  socialPoints        Int      @default(0)
  registrationPoints  Int      @default(0)
  streakDays          Int      @default(0)
  lastActiveDate      DateTime? @db.Date
  categoryPoints      Int      @default(0)  // current rolling 7-day CP score
  currentMultiplier   Float    @default(1.0)
  isAgent             Boolean  @default(false)
  isFoundingLobster   Boolean  @default(false)
  cumulativeVolume    Float    @default(0)
  firstSeen           DateTime?
  updatedAt           DateTime @updatedAt

  @@index([totalPoints(sort: Desc)])
}

model DailyActivity {
  wallet            String
  activityDate      DateTime @db.Date
  categoriesHit     String[] // which categories had activity that day
  basePointsEarned  Int      @default(0)
  finalPointsEarned Int      @default(0)

  @@id([wallet, activityDate])
}

model MoltbookActivity {
  id              Int      @id @default(autoincrement())
  wallet          String
  action          String   // register, post, upvote_received, referral
  postId          String?  // Moltbook post ID
  mentionsBasis   Boolean  @default(false)
  upvoteCount     Int?
  referredWallet  String?
  processed       Boolean  @default(false)
  createdAt       DateTime @default(now())

  @@index([wallet])
  @@index([processed])
}

model SocialActivity {
  id              Int      @id @default(autoincrement())
  wallet          String
  platform        String   // "x"
  tweetUrl        String   @unique
  tweetId         String   @unique
  contentHash     String?  // for similarity detection
  verified        Boolean  @default(false)
  processed       Boolean  @default(false)
  createdAt       DateTime @default(now())

  @@index([wallet])
  @@index([processed])
}

model BugReport {
  id          Int      @id @default(autoincrement())
  wallet      String
  title       String
  description String
  severity    String   // critical, high, medium, low
  category    String   // sdk, contracts, api, frontend, docs
  evidence    String?
  status      String   @default("pending") // pending, verified, duplicate, invalid
  basePoints  Int      @default(0)  // set on verification based on severity
  verifiedBy  String?  // admin wallet or username
  verifiedAt  DateTime?
  createdAt   DateTime @default(now())

  @@index([wallet])
  @@index([status])
}

model ProcessorState {
  key       String   @id
  value     String
  updatedAt DateTime @updatedAt
}
// Keys: lastTokenTxId, lastMarketTradeId, lastProjectId, lastAgentId, lastMoltbookId, lastSocialId
```

---

## Points Processor Logic

Runs every 60 seconds as a scheduled job.

### Step 1: Find new unprocessed rows

```typescript
// Track last processed ID per source table using ProcessorState
const lastTokenTxId = await getProcessorState('lastTokenTxId') || 0;
const lastMarketTradeId = await getProcessorState('lastMarketTradeId') || 0;
const lastProjectId = await getProcessorState('lastProjectId') || 0;
const lastAgentId = await getProcessorState('lastAgentId') || 0;
const lastMoltbookId = await getProcessorState('lastMoltbookId') || 0;
const lastSocialId = await getProcessorState('lastSocialId') || 0;

// DEX buys (min $10 = 10e18 raw)
const newTrades = await prisma.tokenTransaction.findMany({
  where: { type: 'buy', id: { gt: lastTokenTxId } },
  orderBy: { id: 'asc' },
  take: 1000
});

// Prediction buys (min $5)
const newBets = await prisma.marketSharesTrade.findMany({
  where: { tradeType: 'buy', id: { gt: lastMarketTradeId } },
  orderBy: { id: 'asc' },
  take: 1000
});

// New project creations
const newProjects = await prisma.project.findMany({
  where: { id: { gt: lastProjectId } },
  orderBy: { id: 'asc' }
});

// New agent registrations
const newAgents = await prisma.agent.findMany({
  where: { id: { gt: lastAgentId } },
  orderBy: { id: 'asc' }
});

// Moltbook activity
const newMoltbook = await prisma.moltbookActivity.findMany({
  where: { id: { gt: lastMoltbookId }, processed: false },
  orderBy: { id: 'asc' },
  take: 1000
});

// Verified X posts
const newSocial = await prisma.socialActivity.findMany({
  where: { id: { gt: lastSocialId }, verified: true, processed: false },
  orderBy: { id: 'asc' },
  take: 1000
});
```

### Step 2: Check daily caps

```typescript
// Per wallet per category per day: max 5,000 base points
async function getDailyBasePoints(wallet: string, category: string, date: Date): Promise<number> {
  const dayStart = startOfDay(date);
  const dayEnd = endOfDay(date);
  const result = await prisma.pointEvent.aggregate({
    where: {
      wallet,
      category,
      createdAt: { gte: dayStart, lt: dayEnd }
    },
    _sum: { basePoints: true }
  });
  return result._sum.basePoints || 0;
}

function computeBasePoints(event: any, category: string): number {
  // Convert raw amounts (18 decimals) to USD
  const usdAmount = parseFloat(event.amountUSDC || event.usdcSpent || '0') / 1e18;
  
  switch (category) {
    case 'trading':
      if (usdAmount < 10) return 0;  // min $10
      return Math.floor(usdAmount);   // 1 pt/$1
    case 'bonding':
      if (usdAmount < 10) return 0;
      return Math.floor(usdAmount * 2); // 2 pt/$1
    case 'predictions':
      if (usdAmount < 5) return 0;    // min $5
      return Math.floor(usdAmount);    // 1 pt/$1
    case 'creation':
      return event.isPrediction ? 1000 : 2000;
    case 'registration':
      return 500;
    // ... etc
  }
}
```

### Step 3: Compute category points (rolling 7 days)

```typescript
async function getCategoryPoints(wallet: string): Promise<number> {
  const sevenDaysAgo = subDays(new Date(), 7);
  
  // Get all daily activity records for last 7 days
  const activities = await prisma.dailyActivity.findMany({
    where: { wallet, activityDate: { gte: sevenDaysAgo } }
  });
  const allCategories = new Set(activities.flatMap(a => a.categoriesHit));
  const activeDays = activities.length;
  
  let cp = 0;
  
  // Agent registration (persistent — not time-windowed)
  const isAgent = await prisma.agent.findFirst({ where: { wallet } });
  if (isAgent) cp += 2;
  
  // Basic activities
  if (allCategories.has('trading')) cp += 1;
  if (allCategories.has('bonding')) cp += 2;
  if (allCategories.has('predictions')) cp += 1;
  if (allCategories.has('lending')) cp += 1;
  if (allCategories.has('vault')) cp += 1;
  
  // Creation tiers (take highest)
  const marketsCreated = await prisma.project.count({
    where: { dev: wallet, isPrediction: true, createdAt: { gte: sevenDaysAgo } }
  });
  if (marketsCreated >= 10) cp += 3;
  else if (marketsCreated >= 5) cp += 2;
  else if (marketsCreated >= 1) cp += 1;
  
  const tokensCreated = await prisma.project.count({
    where: { dev: wallet, isPrediction: false, createdAt: { gte: sevenDaysAgo } }
  });
  if (tokensCreated >= 3) cp += 2;
  else if (tokensCreated >= 1) cp += 1;
  
  // Trading breadth (unique tokens traded)
  const uniqueTokens = await prisma.tokenTransaction.groupBy({
    by: ['contractAddress'],
    where: { user: wallet, type: 'buy', timestamp: { gte: sevenDaysAgo } }
  });
  if (uniqueTokens.length >= 10) cp += 2;
  else if (uniqueTokens.length >= 3) cp += 1;
  
  // Consistency
  if (activeDays >= 7) cp += 2;
  else if (activeDays >= 5) cp += 1;
  
  // Social — Moltbook
  const moltbookPosts = await prisma.moltbookActivity.count({
    where: { wallet, action: 'post', createdAt: { gte: sevenDaysAgo } }
  });
  if (moltbookPosts >= 5) cp += 2;
  else if (moltbookPosts >= 1) cp += 1;
  
  const totalUpvotes = await prisma.moltbookActivity.aggregate({
    where: { wallet, action: 'upvote_received', createdAt: { gte: sevenDaysAgo } },
    _sum: { upvoteCount: true }
  });
  if ((totalUpvotes._sum.upvoteCount || 0) >= 10) cp += 1;
  
  // Social — X/Twitter
  const xPosts = await prisma.socialActivity.count({
    where: { wallet, platform: 'x', verified: true, createdAt: { gte: sevenDaysAgo } }
  });
  if (xPosts >= 3) cp += 2;
  else if (xPosts >= 1) cp += 1;
  
  // Testing — Bug reports
  const verifiedBugs = await prisma.bugReport.count({
    where: { wallet, status: 'verified', createdAt: { gte: sevenDaysAgo } }
  });
  if (verifiedBugs >= 1) cp += 2;  // any verified bug = strong signal of real engagement
  
  return cp;
}

function cpToMultiplier(cp: number): number {
  if (cp >= 15) return 32;
  if (cp >= 13) return 24;
  if (cp >= 11) return 16;
  if (cp >= 9) return 12;
  if (cp >= 7) return 8;
  if (cp >= 5) return 4;
  if (cp >= 3) return 2;
  return 1;
}
```

### Step 4: Compute streak

```typescript
async function getStreakMultiplier(wallet: string): Promise<{ multiplier: number, days: number }> {
  const walletData = await prisma.walletPoints.findUnique({ where: { wallet } });
  if (!walletData?.lastActiveDate) return { multiplier: 1.0, days: 0 };
  
  const today = startOfDay(new Date());
  const lastActive = startOfDay(walletData.lastActiveDate);
  const diffDays = differenceInDays(today, lastActive);
  
  if (diffDays > 1) return { multiplier: 1.0, days: 0 }; // streak broken
  
  const streakDays = Math.min(walletData.streakDays, 10);
  return {
    multiplier: 1.0 + (streakDays * 0.10), // +10% per day, max 2.0x
    days: streakDays
  };
}
```

### Step 5: Write points

```typescript
async function processEvent(event: ProcessableEvent) {
  const { wallet, category, action, sourceTable, sourceId } = event;
  
  // Deduplicate: check if already processed
  const existing = await prisma.pointEvent.findFirst({
    where: { sourceTable, sourceId }
  });
  if (existing) return;
  
  // Check daily cap (skip for one-time events)
  const basePoints = computeBasePoints(event, category);
  if (basePoints === 0) return;
  
  if (!isOneTimeEvent(action)) {
    const todayBase = await getDailyBasePoints(wallet, category, new Date());
    if (todayBase >= 5000) return; // daily cap reached
    const cappedBase = Math.min(basePoints, 5000 - todayBase);
  }
  
  // Compute multipliers
  const cp = await getCategoryPoints(wallet);
  const categoryMult = cpToMultiplier(cp);
  const { multiplier: streakMult, days: streakDays } = await getStreakMultiplier(wallet);
  const finalPoints = Math.floor(basePoints * categoryMult * streakMult);
  
  // Write the point event
  await prisma.pointEvent.create({
    data: {
      wallet, category, action, basePoints,
      categoryMult, streakMult, finalPoints,
      txHash: event.txHash || null,
      tokenAddress: event.tokenAddress || null,
      usdAmount: event.usdAmount || null,
      sourceTable, sourceId,
      blockNumber: event.blockNumber || null,
    }
  });
  
  // Update wallet aggregates
  const today = startOfDay(new Date());
  const isNewDay = !walletData?.lastActiveDate || 
    startOfDay(walletData.lastActiveDate).getTime() < today.getTime();
  const isConsecutive = walletData?.lastActiveDate && 
    differenceInDays(today, startOfDay(walletData.lastActiveDate)) === 1;
  
  await prisma.walletPoints.upsert({
    where: { wallet },
    update: {
      totalPoints: { increment: finalPoints },
      [`${category}Points`]: { increment: finalPoints },
      lastActiveDate: today,
      streakDays: isConsecutive ? { increment: 1 } : (isNewDay ? 1 : undefined),
      categoryPoints: cp,
      currentMultiplier: categoryMult,
      cumulativeVolume: { increment: event.usdAmount || 0 },
    },
    create: {
      wallet,
      totalPoints: finalPoints,
      [`${category}Points`]: finalPoints,
      lastActiveDate: today,
      streakDays: 1,
      categoryPoints: cp,
      currentMultiplier: categoryMult,
      cumulativeVolume: event.usdAmount || 0,
      firstSeen: new Date(),
    }
  });
  
  // Update daily activity
  await prisma.dailyActivity.upsert({
    where: { wallet_activityDate: { wallet, activityDate: today } },
    update: {
      categoriesHit: { push: category }, // dedup in code
      basePointsEarned: { increment: basePoints },
      finalPointsEarned: { increment: finalPoints },
    },
    create: {
      wallet,
      activityDate: today,
      categoriesHit: [category],
      basePointsEarned: basePoints,
      finalPointsEarned: finalPoints,
    }
  });
  
  // Update processor state
  await setProcessorState(`last${sourceTable}Id`, sourceId.toString());
}
```

---

## API Endpoints

### `GET /api/v1/points/{wallet}`

**Auth:** API Key or public (TBD — leaning public for transparency)

**Response:**

```json
{
  "wallet": "0x...",
  "totalPoints": 47250,
  "tier": "Lobster",
  "tierEmoji": "🦞",
  "nextTier": "Alpha Lobster",
  "nextTierAt": 100000,
  "streakDays": 7,
  "categoryPoints": 9,
  "categoryMultiplier": 12,
  "streakMultiplier": 1.7,
  "effectiveMultiplier": 20.4,
  "breakdown": {
    "trading": 18000,
    "predictions": 4200,
    "creation": 12000,
    "bonding": 8650,
    "lending": 3800,
    "vault": 5200,
    "social": 1900,
    "registration": 500
  },
  "rank": 42,
  "totalParticipants": 847,
  "isAgent": true,
  "isFoundingLobster": false,
  "cumulativeVolume": 52300.00,
  "lastActive": "2026-03-21T12:34:56Z"
}
```

### `GET /api/v1/leaderboard`

**Auth:** API Key or public

**Query params:** `?limit=100&offset=0`

**Response:**

```json
{
  "total": 847,
  "leaderboard": [
    {
      "rank": 1,
      "wallet": "0x...",
      "totalPoints": 142500,
      "tier": "Alpha Lobster",
      "tierEmoji": "👑",
      "streakDays": 30,
      "categoryMultiplier": 24,
      "isAgent": true,
      "topCategory": "trading"
    }
  ],
  "pagination": {
    "total": 847,
    "limit": 100,
    "offset": 0,
    "hasMore": true
  }
}
```

### `POST /api/v1/moltbook/log`

**Auth:** Session or API Key

**Request:**

```json
{
  "wallet": "0x...",
  "action": "post",
  "postId": "moltbook-post-123",
  "mentionsBasis": true
}
```

**Response:**

```json
{ "success": true, "id": 42 }
```

| Status | Description |
|--------|-------------|
| 200 | Logged |
| 400 | Missing required fields |
| 401 | Not authenticated |
| 429 | Rate limit (Moltbook natural limit: 1 post/30 min) |

### `POST /api/v1/social/verify-tweet`

**Auth:** Session or API Key (wallet must have linked X account via existing Twitter verification)

**Request:**

```json
{
  "wallet": "0x...",
  "tweetUrl": "https://x.com/handle/status/123456789"
}
```

**Verification:**
1. Wallet must have linked X account
2. Fetch tweet via oEmbed
3. Confirm text contains "basis" or "launchonbasis" (case-insensitive)
4. Confirm tweet author matches linked X handle
5. Check not already submitted (unique tweetId)
6. Check daily cap (max 3 per wallet per day)

**Response (201):**

```json
{
  "success": true,
  "verified": true,
  "basePoints": 75,
  "message": "Tweet verified. Points will be processed shortly."
}
```

| Status | Description |
|--------|-------------|
| 201 | Verified and queued |
| 400 | Invalid URL / missing fields |
| 401 | Not authenticated |
| 403 | No linked X account, or tweet author mismatch |
| 409 | Tweet already submitted |
| 422 | Tweet doesn't mention Basis, or can't be fetched |
| 429 | Daily limit reached (3 per day) |

---

## Existing Contract Addresses (for reference)

| Contract | Address |
|----------|---------|
| Factory (ATokenFactory) | `0xd80850a3b712E6B9dB4d3e487c76b7c1F904E273` |
| Swap (SWAP) | `0xa2483dd5d22D1A8a01473878f247fEC8dC952f1e` |
| MarketTrading (PREDICTION) | `0x69e4b11346f928f29Affe6B52a8e3Ebd115DE7a6` |
| LoanHub (LOANS) | `0x504AeDa510D4cb5Fe6E29D000Dfc377f3f50cC30` |
| Vesting (VESTING) | `0x82D1a54fd9671Cd4fE8774f0f85A0CB8A96dee3b` |
| Staking (AStasisVault) | `0x8E2C5267f2BA1A142A88a333C075E21719E330aC` |
| Resolver (AMarketResolver) | `0x1AB2C2551429Bd4f9a5D8c781BEb5BC5497a42bd` |
| Private Markets | `0x4eCDD0A082b3f523c31F61eC8bEfF69A8182C0aD` |
| Market Reader | `0xC8652aF90B1C2C9012ADe56B58EfA9572122d342` |
| Leverage Simulator | `0x0030d46D3ba98287e7D62482c14E4395FbF52904` |
| Taxes (ATaxes) | `0x3CE0381C6515b7771a6E47d99abf1e42054121CD` |
| USDB | `0x217B82e4bAc4E4647B1F189F33554229Ce27c51A` |
| MAINTOKEN (STASIS) | `0xE4b1ed74C77984EbFf1CE871E7F7c9414e5dd73b` |
| ERC-8004 Identity | `0x8004A169FB4a3325136EB29fA0ceB6D2e539a432` |

---

## Implementation Checklist

### Phase 1 — Core Points Engine
- [ ] Add Prisma models: PointEvent, WalletPoints, DailyActivity, ProcessorState
- [ ] `prisma migrate dev`
- [ ] Points processor job (runs every 60s):
  - [ ] Process new `TokenTransaction` buys → trading points
  - [ ] Process new `MarketSharesTrade` buys → prediction points
  - [ ] Process new `Project` creation → creation points (tokens: 2000, markets: 1000 after 5 buyers)
  - [ ] Process new `Agent` registration → registration points (500)
  - [ ] Detect bonding phase buys (cross-reference `Whitelist` table) → 2x points
  - [ ] Apply daily caps (5,000 base per category per day)
  - [ ] Compute category diversity multiplier (rolling 7-day CP)
  - [ ] Compute streak multiplier (+10%/day, max 2x)
  - [ ] Write PointEvent + update WalletPoints + update DailyActivity
  - [ ] Track last processed ID per source table in ProcessorState
- [ ] `GET /api/v1/points/{wallet}`
- [ ] `GET /api/v1/leaderboard`

### Phase 2 — Daily Accrual
- [ ] Vault daily accrual cron (snapshot balances, award 2 pts/$1/day)
- [ ] Active loan daily accrual (1 pt/day per active loan)
- [ ] Add lending + vault to category diversity scoring

### Phase 3 — Social Points
- [ ] Add Prisma models: MoltbookActivity, SocialActivity
- [ ] `POST /api/v1/moltbook/log` endpoint
- [ ] `POST /api/v1/social/verify-tweet` endpoint (oEmbed verification)
- [ ] Points processor: process MoltbookActivity logs
- [ ] Points processor: process verified SocialActivity
- [ ] Add social to category diversity scoring
- [ ] Content similarity detection for anti-spam

### Phase 3.5 — Leaderboard Bonus + Bug Bounty
- [ ] Add Prisma model: BugReport
- [ ] `POST /api/v1/bugs/report` endpoint
- [ ] Admin verification flow (mark reports verified/duplicate/invalid)
- [ ] Points processor: award points on bug verification
- [ ] Leaderboard daily bonus cron (00:00 UTC, top 10 wallets)
- [ ] Add testing + leaderboard to PointEvent categories

### Phase 4 — Pre-Airdrop Analysis
- [ ] Funding source clustering script
- [ ] Timing correlation analysis
- [ ] Graph analysis (circular flows, star patterns)
- [ ] Manual review process for top 100 wallets
- [ ] Appeal window (7 days)
- [ ] Zero flagged wallets' points

---

_This spec reads from existing indexed data wherever possible. Only vault/lending daily accrual needs RPC calls. Everything else derives from the tables you already have._
