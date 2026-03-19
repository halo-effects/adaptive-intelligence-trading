# Agent Mining System v0.1 — Build Spec (REVISED)

_Diamond + GeeGee | 2026-03-17_
_Replaces previous spec. Simplified scope, anti-gaming via category diversity multiplier._
_"Agent Mining" = earning through productive ecosystem contribution. The mining multiplier (up to 32x) ensures that the highest-earning agents are the ones building the healthiest ecosystem — economic alignment by design._

---

## Claude Code Prompt

```
Read the file points-system-build-spec-v2.md in full. This is the revised spec for the Basis points system.

Context:
- Basis already has an indexer tracking TokenTransaction, MarketSharesTrade, Project, Agent, Whitelist, Order tables (Prisma/Postgres)
- The points system is an OFF-CHAIN processor that reads existing tables and computes points
- Zero new RPC calls needed — everything derives from existing indexed data
- USDB is the test currency ($1K/day faucet per wallet)

Build order:
1. Add 3 new Prisma models (PointEvent, WalletPoints, DailyActivity)
2. Points processor — scheduled job every 60s, reads new rows from TokenTransaction + MarketSharesTrade + Project + Agent, computes points
3. Category diversity multiplier — rolling 7-day window, weighted category scoring
4. Streak tracker — consecutive days with activity
5. Two API endpoints: GET /api/v1/points/{wallet} and GET /api/v1/leaderboard

Keep it simple. Buys only earn points (not sells). Anti-sybil purge happens before airdrop, not in v0.1.
```

---

## Architecture

```
Existing Indexed Tables (no changes needed)
  ├── TokenTransaction (DEX buys/sells)
  ├── MarketSharesTrade (prediction buys/sells)
  ├── Project (market/token creation)
  ├── Agent (ERC 8004 registrations)
  └── Whitelist (bonding phase buys)
        ↓
[Points Processor] — scheduled job, every 60s
  ├── Scan for new rows since last processed ID
  ├── Filter: buys only, minimum amounts
  ├── Compute base points
  ├── Apply streak + category diversity multiplier
  └── Write to points tables
        ↓
New Tables
  ├── PointEvent (ledger)
  ├── WalletPoints (aggregates)
  └── DailyActivity (streak tracking)
        ↓
[API] — 2 endpoints
  ├── GET /api/v1/points/{wallet}
  └── GET /api/v1/leaderboard
```

---

## Point-Earning Events

### One-Time Events

| # | Event | Base Points | Source | Filter |
|---|---|---|---|---|
| 1 | Register agent (ERC 8004) | 500 | `Agent` table (new row) | One-time per wallet |
| 2 | Create prediction market | 1,000 | `Project` (isPrediction=true) | Only after ≥5 unique buyers in `MarketSharesTrade` for that market |
| 3 | Create token (Stable+/Floor+) | 2,000 | `Project` (isPrediction=false) | One-time per token address |
| 7 | Register on Moltbook | 200 | Internal tracking (API call success) | One-time per wallet |
| 8 | First Moltbook post | 100 | Internal tracking | One-time |

### Recurring Events

| # | Event | Base Points | Source | Filter |
|---|---|---|---|---|
| 4 | Buy prediction shares | 1 pt / $1 USDC | `MarketSharesTrade` where tradeType=buy | Min $5 per trade, cap 5,000 base pts/day |
| 5 | Buy tokens on DEX | 1 pt / $1 USDC | `TokenTransaction` where type=buy | Min $10 per trade, cap 5,000 base pts/day |
| 6 | Buy during bonding phase | 2 pt / $1 USDC | `TokenTransaction` (buy) where token address exists in `Whitelist` | Same caps as #5 |
| 9 | Post on Moltbook mentioning Basis | 50 pts/post | Moltbook API / internal log | Cap 5 posts/day (250 max base pts), must include "basis" or "launchonbasis" |
| 10 | Moltbook post gets upvotes | 5 pts/upvote | Moltbook API polling | Cap 500 base pts/day from engagement |
| 11 | Refer new agent via Moltbook | 500 pts one-time | Referral tracking (new wallet from Moltbook link completes first trade) | One-time per referred wallet |

**Buys only.** Sells do not earn points. This prevents wash trading — you can't buy and sell repeatedly to farm points because only the buy side counts, and each buy costs 1.5% tax + slippage.

**Daily cap is on BASE points before multipliers.** A wallet can earn max 5,000 base points per category per day. Multipliers apply on top.

---

## Category Diversity Multiplier

This is the core anti-gaming mechanic. Points are multiplied based on how many different types of activity a wallet performs in a rolling 7-day window.

### Category Point Scoring

Each action type earns "category points" (CP). These are NOT reward points — they determine the multiplier tier.

| Action (in rolling 7 days) | Category Points | Rationale |
|---|---|---|
| Register agent (ERC 8004) | 2 | High-value identity signal |
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

**Note:** Tiered actions (e.g., "create 1" vs "create 5+" vs "create 10+") don't stack — take the highest tier achieved. Max theoretical CP is approximately 21 (up from 18 with Social category added).

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

### Example Scenarios

**Casual trader (1 category):**
- Only buys on DEX: CP = 1 → 1x multiplier
- Earns 1,000 pts × 1 = 1,000 pts/day

**Active agent (multiple categories):**
- Registered (2) + DEX buys (1) + prediction buys (1) + created a market (1) + bonding buy (2) + 3 different tokens (1) + active 5/7 days (1) = 9 CP → 12x
- Earns 1,000 pts × 12 = 12,000 pts/day

**Power user (max engagement):**
- Registered (2) + DEX buys (1) + prediction buys (1) + 10+ markets created (3) + 3+ tokens created (2) + bonding buy (2) + 10+ different tokens (2) + active 7/7 days (2) + Moltbook 5+ posts (2) + 10+ upvotes (1) = 18 CP → 32x
- Earns 1,000 pts × 32 = 32,000 pts/day

**Social + DeFi agent:**
- Registered (2) + DEX buys (1) + Moltbook 5+ posts (2) + 10+ upvotes (1) + active 5/7 days (1) = 7 CP → 8x
- A social-only agent still gets low multiplier; trading AND creating AND posting achieves the highest tiers.

**Sybil attacker (10 wallets, each doing one thing):**
- Each wallet: CP = 1 → 1x multiplier
- 10 wallets × 1,000 pts × 1 = 10,000 pts/day total
- vs 1 real user at 12-32x = 12,000-32,000 pts/day
- **Real engagement wins.**

---

## Streak Bonus

In addition to the category multiplier, consecutive daily activity earns a streak bonus:

- +10% per consecutive day with any point-earning activity
- Caps at +100% (10 consecutive days = 2x)
- Resets to 0% on a missed day

**Streak stacks with category multiplier:**
```
final_points = base_points × category_multiplier × streak_multiplier
```

Example: 1,000 base pts × 12x category × 1.5x streak (day 5) = 18,000 pts

---

## New Prisma Models

Add these to your existing schema:

```prisma
model PointEvent {
  id            Int      @id @default(autoincrement())
  wallet        String
  category      String   // registration, trading, predictions, creation, bonding, social
  action        String   // register_agent, dex_buy, prediction_buy, create_market, create_token, bonding_buy, moltbook_register, moltbook_post, moltbook_upvote_received, moltbook_referral
  basePoints    Int
  categoryMult  Float    @default(1.0)
  streakMult    Float    @default(1.0)
  finalPoints   Int
  txHash        String?
  tokenAddress  String?
  usdAmount     Float?
  sourceTable   String?  // TokenTransaction, MarketSharesTrade, Project, Agent
  sourceId      Int?     // ID from source table
  blockNumber   Int?
  createdAt     DateTime @default(now())

  @@index([wallet])
  @@index([wallet, category])
  @@index([wallet, createdAt])
  @@index([sourceTable, sourceId])  // prevent double-processing
}

model WalletPoints {
  wallet            String   @id
  totalPoints       Int      @default(0)
  tradingPoints     Int      @default(0)
  predictionsPoints Int      @default(0)
  creationPoints    Int      @default(0)
  bondingPoints     Int      @default(0)
  registrationPoints Int     @default(0)
  socialPoints      Int      @default(0)
  streakDays        Int      @default(0)
  lastActiveDate    DateTime? @db.Date
  categoryPoints    Int      @default(0)  // current rolling 7-day CP score
  currentMultiplier Float    @default(1.0)
  isAgent           Boolean  @default(false)  // exists in Agent table
  firstSeen         DateTime?
  updatedAt         DateTime @updatedAt

  @@index([totalPoints])
}

model DailyActivity {
  wallet         String
  activityDate   DateTime @db.Date
  categoriesHit  String[] // which categories had activity that day
  basePointsEarned Int
  finalPointsEarned Int

  @@id([wallet, activityDate])
}
```

---

## Points Processor Logic

Runs every 60 seconds as a scheduled job.

### Step 1: Find new unprocessed rows

```typescript
// Find TokenTransaction buys not yet in PointEvent
const newTrades = await prisma.tokenTransaction.findMany({
  where: {
    type: 'buy',
    id: { gt: lastProcessedTokenTxId },
    amountUSDC: { gte: '10000000000000000000' }  // min $10 (18 decimals)
  },
  orderBy: { id: 'asc' },
  take: 1000
});

// Find MarketSharesTrade buys not yet in PointEvent  
const newBets = await prisma.marketSharesTrade.findMany({
  where: {
    tradeType: 'buy',
    id: { gt: lastProcessedMarketTradeId },
    // min $5 — usdcSpent is a string, filter in code
  },
  orderBy: { id: 'asc' },
  take: 1000
});

// Find new Projects (markets + tokens)
const newProjects = await prisma.project.findMany({
  where: {
    id: { gt: lastProcessedProjectId }
  },
  orderBy: { id: 'asc' }
});

// Find new Agent registrations
const newAgents = await prisma.agent.findMany({
  where: {
    id: { gt: lastProcessedAgentId }
  },
  orderBy: { id: 'asc' }
});
```

### Step 1.5: Find new Moltbook activity logs

```typescript
// Moltbook activity is tracked via internal log table (MoltbookActivity)
// The post-moltbook.py skill logs each successful action to the Basis API
// Processor reads these logs same as other source tables

const newMoltbookActivity = await prisma.moltbookActivity.findMany({
  where: {
    id: { gt: lastProcessedMoltbookId },
  },
  orderBy: { id: 'asc' },
  take: 1000
});

// Each row: { wallet, action: 'register'|'post'|'upvote_received'|'referral',
//             postId?, mentionsBasis: boolean, upvoteCount?: number, createdAt }
// Logged via POST /api/v1/moltbook/log (called by post-moltbook.py on success)
```

### Step 2: Check daily caps

```typescript
// Per wallet per category per day: max 5,000 base points
async function getDailyBasePoints(wallet: string, category: string, date: Date): Promise<number> {
  const result = await prisma.pointEvent.aggregate({
    where: {
      wallet,
      category,
      createdAt: { gte: startOfDay(date), lt: endOfDay(date) }
    },
    _sum: { basePoints: true }
  });
  return result._sum.basePoints || 0;
}
```

### Step 3: Compute category points (rolling 7 days)

```typescript
async function getCategoryPoints(wallet: string): Promise<number> {
  const sevenDaysAgo = subDays(new Date(), 7);
  const activities = await prisma.dailyActivity.findMany({
    where: { wallet, activityDate: { gte: sevenDaysAgo } }
  });
  
  // Flatten all categories hit in last 7 days
  const allCategories = new Set(activities.flatMap(a => a.categoriesHit));
  
  let cp = 0;
  
  // Registration
  const isAgent = await prisma.agent.findFirst({ where: { wallet } });
  if (isAgent) cp += 2;
  
  // Basic activities
  if (allCategories.has('trading')) cp += 1;
  if (allCategories.has('bonding')) cp += 2;
  if (allCategories.has('predictions')) cp += 1;
  
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
  
  // Trading breadth
  const uniqueTokens = await prisma.tokenTransaction.groupBy({
    by: ['contractAddress'],
    where: { user: wallet, type: 'buy', timestamp: { gte: sevenDaysAgo } }
  });
  if (uniqueTokens.length >= 10) cp += 2;
  else if (uniqueTokens.length >= 3) cp += 1;
  
  // Consistency
  const activeDays = activities.length;
  if (activeDays >= 7) cp += 2;
  else if (activeDays >= 5) cp += 1;
  
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
async function getStreakMultiplier(wallet: string): Promise<number> {
  const walletData = await prisma.walletPoints.findUnique({ where: { wallet } });
  if (!walletData?.lastActiveDate) return 1.0;
  
  const today = startOfDay(new Date());
  const lastActive = startOfDay(walletData.lastActiveDate);
  const diffDays = differenceInDays(today, lastActive);
  
  if (diffDays > 1) return 1.0; // streak broken
  
  const streakDays = Math.min(walletData.streakDays, 10);
  return 1.0 + (streakDays * 0.10); // +10% per day, max 2.0x
}
```

### Step 5: Write points

```typescript
// For each qualifying event:
const basePoints = computeBasePoints(event);  // 1 per $1, or one-time bonus
const categoryMult = cpToMultiplier(await getCategoryPoints(wallet));
const streakMult = await getStreakMultiplier(wallet);
const finalPoints = Math.floor(basePoints * categoryMult * streakMult);

await prisma.pointEvent.create({
  data: {
    wallet, category, action, basePoints,
    categoryMult, streakMult, finalPoints,
    txHash, tokenAddress, usdAmount,
    sourceTable, sourceId, blockNumber
  }
});

// Update aggregates
await prisma.walletPoints.upsert({
  where: { wallet },
  update: {
    totalPoints: { increment: finalPoints },
    [`${category}Points`]: { increment: finalPoints },
    lastActiveDate: today,
    streakDays: isConsecutive ? { increment: 1 } : 1,
    categoryPoints: currentCP,
    currentMultiplier: categoryMult
  },
  create: {
    wallet, totalPoints: finalPoints,
    [`${category}Points`]: finalPoints,
    lastActiveDate: today, streakDays: 1,
    categoryPoints: currentCP, currentMultiplier: categoryMult,
    firstSeen: new Date()
  }
});
```

---

## API Endpoints

### GET /api/v1/points/{wallet}

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
    "registration": 500
  },
  "rank": 42,
  "totalParticipants": 847,
  "isAgent": true,
  "lastActive": "2026-03-17T12:34:56Z"
}
```

### GET /api/v1/leaderboard?limit=100&offset=0

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
      "isAgent": true
    }
  ]
}
```

### Molt Tiers (derived from total points)

| Tier | Points | Emoji |
|---|---|---|
| Egg | 0 | 🥚 |
| Shrimp | 1,000 | 🦐 |
| Crab | 5,000 | 🦀 |
| Lobster | 25,000 | 🦞 |
| Alpha Lobster | 100,000 | 👑 |
| Diamond Lobster | 500,000 | 💎 |

---

## Anti-Sybil Strategy

### v0.1 (built-in)
- **Buys only** — can't wash trade for points
- **Category diversity multiplier** — single-action bots get 1x, real users get 8-32x
- **Minimum trade sizes** — $5 predictions, $10 DEX
- **Daily caps** — 5,000 base pts per category per day
- **Moltbook rate limits** — 1 post/30 min enforced by Moltbook API, provides natural spam protection for social points

### Pre-Airdrop (batch analysis)
- **Funding source clustering** — wallets funded from same source = likely sybil
- **Timing correlation** — wallets that transact in synchronized patterns
- **Graph analysis** — interconnected transfer patterns
- **Manual review** — top 100 wallets reviewed before distribution

---

## Implementation Checklist

- [ ] Add 3 Prisma models (PointEvent, WalletPoints, DailyActivity)
- [ ] `prisma migrate dev`
- [ ] Points processor job (runs every 60s)
  - [ ] Process new `TokenTransaction` buys
  - [ ] Process new `MarketSharesTrade` buys
  - [ ] Process new `Project` creation
  - [ ] Process new `Agent` registration
  - [ ] Detect bonding phase buys (cross-reference Whitelist)
  - [ ] Apply daily caps
  - [ ] Compute category points (rolling 7 days)
  - [ ] Compute streak multiplier
  - [ ] Write PointEvent + update WalletPoints + update DailyActivity
- [ ] GET /api/v1/points/{wallet}
- [ ] GET /api/v1/leaderboard
- [ ] Track last processed ID per source table (use existing BlockTracker pattern or simple key-value)
- [ ] `post-moltbook.py` skill script ✅
- [ ] Moltbook activity logging endpoint (POST /api/v1/moltbook/log)
- [ ] Points processor: process Moltbook activity logs (MoltbookActivity table)
- [ ] Create m/basis submolt on Moltbook

---

_This spec uses only existing indexed data. Zero new RPC calls. Zero new contract watchers. Just a processing layer + 2 API routes._
