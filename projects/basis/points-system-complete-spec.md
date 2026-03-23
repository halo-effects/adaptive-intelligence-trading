# Basis Points System â€" Complete Build Spec

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
- Zero new RPC calls needed â€" everything derives from existing indexed data
- USDB is the test currency (one-time $10K faucet per wallet, no refills) â€" all amounts are 18 decimals
- Points earned during USDB testing carry over to the real BASIS token airdrop

Build order:
1. Add Prisma models (PointEvent, WalletPoints, DailyActivity, MoltbookActivity, SocialActivity)
2. Points processor â€" scheduled job every 60s, reads new rows from existing tables, computes points
3. Category diversity multiplier â€" rolling 7-day window, weighted category scoring
4. Streak tracker â€" consecutive days with activity
5. Lending & vault point accrual â€" daily snapshot job
6. Social points (Moltbook + X/Twitter verification)
7. API endpoints: GET /api/v1/points/{wallet}, GET /api/v1/leaderboard, POST /api/v1/moltbook/log, POST /api/v1/social/verify-tweet

Anti-sybil is critical. The system must make it economically irrational for someone to run 100 bots doing one thing each. The category diversity multiplier is the primary mechanic â€" one-dimensional bots get 1x, real diverse users get up to 32x. Combined with buys-only, daily caps, and minimum trade sizes, mining from bot armies costs more than it earns.

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
  â"œâ"€â"€ TokenTransaction (DEX buys/sells â€" type, amountUSDC, user, contractAddress, blockNumber, timestamp)
  â"œâ"€â"€ MarketSharesTrade (prediction buys/sells â€" tradeType, usdcSpent, buyer, marketToken)
  â"œâ"€â"€ Project (token/market creation â€" dev, isPrediction, address, createdAt)
  â"œâ"€â"€ Agent (ERC-8004 registrations â€" wallet, agentId, createdAt)
  â"œâ"€â"€ Whitelist (reward phase buys â€" walletAddress, token)
  â"œâ"€â"€ Order (prediction market orders â€" seller, status, marketToken)
  â"œâ"€â"€ LoanEvent (loan lifecycle â€" wallet, action, loanId, txHash)
  â"œâ"€â"€ VaultEvent (vault staking â€" wallet, action, amount, txHash)
  â""â"€â"€ VestingEvent (vesting lifecycle â€" wallet, action, vestingId, amount, txHash)
        â†"
[Points Processor] â€" scheduled job, every 60 seconds
  â"œâ"€â"€ Scan for new rows since last processed ID per source table
  â"œâ"€â"€ Filter: buys only, minimum amounts
  â"œâ"€â"€ Compute base points per event
  â"œâ"€â"€ Apply category diversity multiplier (rolling 7-day window)
  â"œâ"€â"€ Apply streak multiplier
  â""â"€â"€ Write to points tables
        â†"
[Vault/Lending Daily Accrual] â€" cron job, once per day
  â"œâ"€â"€ Snapshot active vault balances â†' 2 pts/$1/day staked
  â"œâ"€â"€ Snapshot active loans â†' 1 pt/day per active loan
  â""â"€â"€ Write to PointEvent + update WalletPoints
        â†"
[Social Processor] â€" scheduled job, every 60 seconds
  â"œâ"€â"€ Process MoltbookActivity logs
  â"œâ"€â"€ Process SocialActivity (verified X posts)
  â""â"€â"€ Write to PointEvent with social category
        â†"
New Tables
  â"œâ"€â"€ PointEvent (immutable ledger â€" every point earned)
  â"œâ"€â"€ WalletPoints (aggregated wallet state â€" totals, multipliers, tier)
  â"œâ"€â"€ DailyActivity (per-wallet per-day â€" for streaks and daily caps)
  â"œâ"€â"€ MoltbookActivity (logged by skill scripts via API)
  â""â"€â"€ SocialActivity (verified X posts via API)
        â†"
[API] â€" 4 endpoints
  â"œâ"€â"€ GET  /api/v1/points/{wallet}
  â"œâ"€â"€ GET  /api/v1/leaderboard
  â"œâ"€â"€ POST /api/v1/moltbook/log
  â""â"€â"€ POST /api/v1/social/verify-tweet
```

---

## Point-Earning Events

### Core Principle: BUYS ONLY

**Sells do not earn points.** This is the first anti-gaming layer. You can't buy and sell repeatedly to mine points because only the buy side counts, and each buy costs 1.5% tax + slippage. A bot doing wash trades loses money on every cycle.

### One-Time Events

| # | Event | Base Points | Source Table | Filter |
|---|---|---|---|---|
| 1 | Register agent (ERC-8004) | 500 | `Agent` (new row) | One-time per wallet |
| 2 | Create prediction market | 1,000 | `Project` (isPrediction=true) | Only after â‰¥5 unique buyers in `MarketSharesTrade` for that market |
| 3 | Create token (Stable+/Floor+) | 2,000 | `Project` (isPrediction=false) | One-time per token address |
| 4 | Register on Moltbook | 200 | `MoltbookActivity` (action=register) | One-time per wallet |
| 5 | First Moltbook post | 100 | `MoltbookActivity` (action=post, first occurrence) | One-time |
| 6 | Refer new agent via Moltbook | 500 | `MoltbookActivity` (action=referral) | One-time per referred wallet. Referred wallet must complete first trade. |
| 18 | Bug/exploit report (first discovery) | TBD (by severity) | `BugReport` (status=verified) | One-time per unique bug. Points scale by severity (see Bug Bounty section). |

### Recurring Events

| # | Event | Base Points | Source Table | Filter |
|---|---|---|---|---|
| 7 | Buy prediction shares | 1 pt / $50 USDC | `MarketSharesTrade` (tradeType=buy) | Min $5 per trade. Cap 5,000 base pts/day. |
| 8 | Buy tokens on DEX | 1 pt / $50 USDC | `TokenTransaction` (type=buy) | Min $10 per trade. Cap 5,000 base pts/day. |
| 9 | Buy during reward phase | 2 pt / $50 USDC | `TokenTransaction` (type=buy) where token address in `Whitelist` | Same daily cap as #8. |
| 10 | Take a loan | 200 | On-chain event (ALOAN_HUB.takeLoan) | One-time per loan ID. |
| 11 | Extend a loan | 100 | On-chain event (ALOAN_HUB.extendLoan) | Per extension. |
| 12 | Active loan daily | 1 pt/day | Daily accrual cron | Per active loan per day. |
| 13 | Vault staking daily | 2 pt / $1 / day | Daily accrual cron | Snapshots vault balance once per day. |
| 14 | Vault refinance | 150 | On-chain event (AStasisVault.borrow with existing loan) | Per refinance. |
| 19 | Create vesting schedule | 200 | `VestingEvent` (action=created) | One-time per vesting ID. Signals long-term commitment. |
| 20 | Claim vested tokens | 100 | `VestingEvent` (action=claimed) | Per claim event. |
| 21 | Loan against vested tokens | 200 | `LoanEvent` (source=vesting, action=created) | One-time per vesting loan. Rewards using vesting as collateral. |
| 22 | Active vesting daily | 1 pt/day | Daily accrual cron | Per active vesting schedule per day. Rewards long-term locking. |
| 15 | Post on Moltbook mentioning Basis | 50 pts/post | `MoltbookActivity` (action=post) | Cap 5 posts/day (250 max base pts). Must include "basis" or "@LaunchOnBasis". |
| 16 | Moltbook post gets upvotes | 5 pts/upvote | `MoltbookActivity` (action=upvote_received) | Cap 500 base pts/day from engagement. |
| 17 | Verified X post with @LaunchOnBasis tag | 75 pts/post | `SocialActivity` (platform=x, verified=true) | Cap 3 attempts/day (pass or fail). Must pass oEmbed verification. |

### Lending & Vault Detail

Lending and vault points require a **daily accrual job** (separate from the 60s processor):

**Vault staking**: Once per day, snapshot each wallet's locked wSTASIS balance. Convert to USD value using `convertToAssets()` price. Award `2 Ã- USD_value` base points. This means long-term stakers earn passively every day.

**Active loans**: Once per day, check all active loans (not liquidated, not repaid). Award 1 point per active loan per day.

**Why this matters**: These are "sticky" activities â€" they require capital commitment over time, which is expensive for sybil attackers to replicate across many wallets.

### Daily Cap Rules

- Daily cap is on **BASE points before multipliers**
- Cap is **per category per wallet per day**: max 5,000 base points
- Categories: `trading`, `predictions`, `creation`, `bonding`, `lending`, `vault`, `vesting`, `social`, `testing`, `leaderboard`, `registration`
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
| Buy during reward phase | 2 | Early conviction on new tokens |
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
| Created vesting schedule | 2 | Long-term commitment signal â€" hard to fake at scale |
| Verified bug report (any) | 2 | Testing contribution â€" strong real-user signal |

**Note:** Tiered actions don't stack â€" take the highest tier achieved. Max theoretical CP is approximately 25.

### Multiplier Table

| Category Points | Multiplier |
|---|---|
| 1â€"2 | 1x |
| 3â€"4 | 2x |
| 5â€"6 | 4x |
| 7â€"8 | 8x |
| 9â€"10 | 12x |
| 11â€"12 | 16x |
| 13â€"14 | 24x |
| 15+ | 32x |

**âš ï¸ Social Verification Gate:** Without a linked + verified X account (via `SocialLink` table), the multiplier is **hard-capped at 8x** regardless of CP score. Linking X unlocks 12x â†' 32x. This creates a strong incentive to verify without blocking day-one participation.

### Why This Kills Bot Farms

**Scenario: Attacker with 100 bots, each doing one thing**
- Each bot: CP = 1 â†' 1x multiplier (capped at 8x anyway without X)
- Each bot has $10K (one-time faucet, can't transfer or they lose everything)
- $10K at 1 pt/$50 = 200 base pts per bot if they spend it all
- 100 bots Ã- 200 pts Ã- 1x = 20,000 pts/day total
- Cost: 100 X accounts + 100 wallets + gas + 1.5% tax eating into the $10K

**Scenario: 1 real user doing everything**
- CP = 15+ â†' 32x multiplier (social verified)
- $10K capital, trades strategically across categories
- 200 base pts Ã- 32x = 6,400 pts/day from trading alone
- Plus one-time bonuses (agent reg 500, token creation 2000, etc.) Ã- 32x
- Single wallet, normal usage

**The math is devastating for bot farms.** Each bot is stuck with $10K (can't pool capital), earns at 1x-8x max (no social = capped), and loses everything if they try to transfer USDB. One verified diverse user earns more than dozens of bots combined.

---

## Streak Bonus

Consecutive daily activity earns a streak multiplier:

- +10% per consecutive day with any point-earning activity
- Caps at +100% (10 consecutive days = 2.0x streak multiplier)
- Resets to 0% on a missed day (no grace period)

**Streak stacks with all multipliers:**

```
final_points = base_points Ã— category_mult Ã— streak_mult Ã— tide_mult Ã— (1 + referral_mult) Ã— acs_mult
             + weekly_ranking_bonus (flat, not multiplied)
             + daily_leaderboard_bonus (flat, not multiplied)

where acs_mult = 1.0 + (acs_score Ã— 0.2)   // ranges 1.0 (ACS=0) to 1.2 (ACS=1.0)
```

**Example:** 1,000 base pts Ã— 12x category Ã— 1.5x streak Ã— 1.0 tide Ã— 1.15 referral Ã— 1.14 ACS (0.72) = 23,598 pts

**During a Lobster Tide:** 1,000 Ã— 12 Ã— 1.5 Ã— 2.0 Ã— 1.15 Ã— 1.14 = 47,196 pts

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
   c. Convert to USD: MAIN_TOKEN.getUSDPrice() Ã- mainValue
   d. base_points = floor(usd_value Ã- 2)
   e. Apply category + streak multipliers
   f. Write PointEvent(category=vault, action=daily_accrual)
3. Update WalletPoints.vaultPoints for each wallet
```

**Note:** This is the ONE place where RPC calls are needed â€" to read current vault balances. All other points derive from existing indexed data.

### Active Loan Daily

```
Every day at 00:00 UTC:
1. Query all active loans from the Loan table (active=true, isLiquidated=false)
2. For each unique wallet with active loans:
   a. base_points = count_of_active_loans Ã- 1
   b. Apply multipliers
   c. Write PointEvent(category=lending, action=daily_accrual)
```

### Active Vesting Daily

```
Every day at 00:00 UTC:
1. Query all active vesting schedules (not fully claimed) from VestingEvent
   â€" group by wallet, count distinct vestingId where action=created and no full claim
2. For each unique wallet with active vesting:
   a. base_points = count_of_active_vestings Ã- 1
   b. Apply multipliers
   c. Write PointEvent(category=vesting, action=daily_accrual)
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
- Moltbook API enforces 1 post per 30 minutes per user â€" provides natural spam protection
- Points processor caps at 5 posts/day (250 base pts) and 500 engagement pts/day

### X/Twitter Verification

Agents submit tweets for verification. The backend validates via oEmbed that the tweet exists, is public, and contains the `@LaunchOnBasis` tag.

**Endpoint:** `POST /api/v1/social/verify-tweet`

```json
{
  "wallet": "0x...",
  "tweetUrl": "https://x.com/handle/status/123..."
}
```

**Verification steps:**
1. Fetch tweet via oEmbed API (no X API key needed for public tweets)
2. Confirm tweet contains `@LaunchOnBasis` tag (case-insensitive)
3. Confirm tweet author matches the linked X account for this wallet (from `POST /api/auth/twitter/verify-tweet`)
4. Check for duplicate submissions (same tweetId)
5. If valid, write to `SocialActivity` table â†' points processor picks it up

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
| #4â€"5 | TBD |
| #6â€"10 | TBD |

> **Note:** Exact point values to be decided later. Build the structure and cron job now â€" values will be configured before launch.

**Rules:**
- Bonus is applied AFTER base + multiplier calculation (it's a flat bonus, not multiplied)
- Written as a separate PointEvent with `category=leaderboard`, `action=daily_rank_bonus`
- If rankings change mid-day, the bonus still goes to whoever held the rank at the 00:00 UTC snapshot
- Creates a "king of the hill" dynamic â€" top spots are worth defending

**Why this works:** It rewards genuine leaders without being gameable. You can't game your way into the top 10 with bots because the category diversity multiplier already ensures diverse users dominate the leaderboard. The bonus just sweetens the reward for actually being #1.

---

## Lobster Tides (Surprise Bonus Windows)

Unannounced multiplier periods that reward genuinely active users. Inspired by Hyperliquid's surprise Seasons 1.5/2.5 which rewarded loyal users who stuck around between announced seasons.

### How It Works

The team can activate a **Lobster Tide** at any time — a time-limited bonus multiplier applied to all point-earning activity during the window. Users are NOT notified in advance.

**Trigger types:**

| Trigger | Example | Announcement |
|---------|---------|--------------|
| **Milestone** | 50th agent registered, $1M platform volume | Announced at start |
| **Stealth** | Random 24h window chosen by team | Announced AFTER it ends |
| **Event-based** | Major market event, partnership announcement | Announced at start |

**Why stealth tides are powerful for Basis specifically:** Agents run 24/7. Unlike human farmers who only show up during known earning periods, always-on agents naturally catch every stealth tide. This is the exact behavior we want to reward.

### Parameters

| Parameter | Value | Notes |
|-----------|-------|-------|
| `tide_mult` | 1.5x – 3.0x | Set per event by admin |
| Duration | 4h – 72h | Short = urgency, long = inclusive |
| Frequency | 2-4 per phase | Rare enough to feel special |
| Stacking | Does NOT stack with other tides | Only one active at a time |
| Announcement | Platform banner + Telegram/Discord | Or post-hoc for stealth tides |

### Database Model

```prisma
model LobsterTide {
  id          Int      @id @default(autoincrement())
  name        String   // "First 50 Lobsters", "Stealth Tide #1"
  multiplier  Float    // 1.5, 2.0, 3.0
  startTime   DateTime
  endTime     DateTime
  announced   Boolean  @default(false)  // false = stealth (announced after)
  announcedAt DateTime?
  createdBy   String   // admin wallet
  createdAt   DateTime @default(now())

  @@index([startTime, endTime])
}
```

### Admin Endpoint

```
POST /api/v1/admin/tides
Auth: Admin only

{
  "name": "First 50 Lobsters",
  "multiplier": 2.0,
  "startTime": "2026-04-01T00:00:00Z",
  "endTime": "2026-04-02T00:00:00Z",
  "announced": true
}
```

---

## Weekly Category Rankings

Top performers in each point category earn a flat weekly bonus. Instead of only rewarding total points (which the daily leaderboard bonus does), this rewards excellence in specific activities.

### How It Works

Every Monday at 00:00 UTC, rank all wallets by **base points** (before multipliers) earned in each category during the previous 7 days. Top 10 per category get a flat bonus (NOT multiplied — pure bonus added to total points).

### Bonuses by Category

| Rank | Trading / Predictions | Creation / Resolver | Lending / Vault / Social |
|------|----------------------|--------------------|-----------------------|
| #1 | 2,000 | 1,500 | 1,000 |
| #2–3 | 1,000 | 750 | 500 |
| #4–5 | 500 | 400 | 250 |
| #6–10 | 250 | 200 | 125 |

**Max weekly bonus if #1 in ALL categories:** 10,000 pts (near-impossible — requires being best at everything simultaneously).
**Realistic top performer:** #1 in 1–2 categories + top 10 in 2–3 others ≈ 3,000–5,000 weekly bonus.

### Rules

- **Ranked by base points before multipliers** — raw activity, not amplified scores. A 1x bot can't dominate rankings via multiplier stacking.
- **Minimum threshold:** Must earn ≥500 base points in a category during the week to qualify.
- **Same wallet can win multiple categories** — rewards genuine diversity.
- **Flat bonus (not multiplied):** A Shrimp who hits #1 in trading gets the same 2,000 as a Diamond Lobster. Keeps it fair across tiers.

### Database Model

```prisma
model WeeklyRanking {
  id          Int      @id @default(autoincrement())
  wallet      String
  category    String   // trading, predictions, creation, lending, vault, social, resolver
  weekStart   DateTime // Monday 00:00 UTC
  rank        Int      // 1-10
  basePoints  Int      // base points earned in that category that week
  bonusPoints Int      // flat bonus awarded
  createdAt   DateTime @default(now())

  @@unique([wallet, category, weekStart])
  @@index([weekStart, category])
  @@index([wallet])
}
```

### API Endpoint

```
GET /api/v1/rankings/weekly?category=trading&week=2026-03-17
Auth: API Key (post-TGE visibility only)

Response:
{
  "category": "trading",
  "weekStart": "2026-03-17T00:00:00Z",
  "rankings": [
    { "rank": 1, "wallet": "0x...", "basePoints": 4200, "bonus": 2000 },
    { "rank": 2, "wallet": "0x...", "basePoints": 3800, "bonus": 1000 }
  ]
}
```

---

## Referral System (Multiplier-Based)

Referrals boost the referrer's **multiplier** rather than transferring flat points. This ensures referrers must be active themselves to benefit — recruiting without platform activity earns effectively nothing.

### Why Multiplier > Flat Percentage

| Old System (10% L1 / 3% L2) | New System (Multiplier) |
|------------------------------|------------------------|
| Referral-only wallets earn 19,790% of own activity from referrals | Referral-only wallets earn +33% of their near-zero base = ~16 pts/day |
| Whale recruiters earn 480% of own earnings from referrals | Whale recruiters get +57% boost — meaningful but not dominant |
| Enables referral whales who never trade | Requires own diverse activity to benefit |
| Takes from a shared pool (dilutes everyone) | Amplifies own earnings (zero-sum with nobody) |

### Formula

```
referral_mult = L1_quality_bonus + L2_quality_bonus + count_tier_bonus
final_points = base_points × diversity_mult × streak_mult × tide_mult × (1 + referral_mult)
```

### L1: Per-Referee Quality Bonus

Based on each direct referee's total base points. The better your referees do, the more your multiplier increases.

| Referee Base Points | Referrer Bonus |
|---|---|
| 1,000+ (Egg) | +0.008 |
| 5,000+ (Shrimp) | +0.015 |
| 25,000+ (Crab+) | +0.030 |
| 100,000+ (Lobster+) | +0.050 |

- **Cap per referee:** +0.05 (so one whale referee doesn't dominate)
- **Cap total L1:** +0.50 (effectively caps at ~10 quality referees)

### L2: Per-Referee's-Referee Quality Bonus

Based on each L2 referee's (referee's referees) total base points. Smaller bonuses — rewards network depth without creating pyramid dynamics.

| L2 Referee Base Points | Referrer Bonus |
|---|---|
| 1,000+ | +0.002 |
| 5,000+ | +0.004 |
| 25,000+ | +0.008 |
| 100,000+ | +0.012 |

- **Cap per L2 referee:** +0.012
- **Cap total L2:** +0.15

### Count Tier Bonus

Rewards network building effort itself — number of active L1 referrals (any referral with >0 points).

| Active L1 Referrals | Bonus |
|---|---|
| 3+ | +0.08 |
| 10+ | +0.15 |
| 20+ | +0.25 |
| 50+ | +0.35 |

### Maximum Referral Multiplier

**Theoretical max: +1.0** (doubles your points). Requires 10+ quality L1 referees at cap + deep L2 network + 50+ total count. In practice, most active referrers see **+15–30%**.

### Simulation Results (30-day projection, Moderate config)

| Player | Referral Boost | 30d Points |
|--------|---------------|-----------|
| Power User + 8 quality refs | +29.5% | 2,486,400 |
| Solo Grinder (no referrals) | +0% | 652,800 |
| Referral Builder (12 refs) | +31.4% | 425,736 |
| Whale Recruiter (25 refs, moderate own activity) | +56.6% | 263,088 |
| Referral-Only (15 refs, no own activity) | +32.8% | **1,992** 💀 |
| Bot Farm (1 ref each, no diversity) | +0% | **6,000** 💀 |

**Key ratio:** Solo Grinder earns **328x** more than Referral-Only. System working exactly as designed.

### Database Addition

```prisma
model Referral {
  id              Int      @id @default(autoincrement())
  referrerWallet  String   // who referred
  refereeWallet   String   @unique // who was referred (one referrer per wallet)
  l1              Boolean  @default(true)  // direct referral
  createdAt       DateTime @default(now())

  @@index([referrerWallet])
  @@index([refereeWallet])
}
```

### Referral Tracking

- Referral link: `https://launchonbasis.com?ref={wallet}` or referral code
- Recorded on first platform action (not on link click — must actually use the platform)
- One referrer per wallet (first referral wins)
- L2 relationships are inferred: if A referred B and B referred C, then C is A's L2 referee

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
  "message": "Report submitted. Points will be awarded after team verification."
}
```

### Severity & Points

| Severity | Points | Examples |
|---|---|---|
| **Critical** | TBD | Fund loss vulnerability, contract exploit, auth bypass |
| **High** | TBD | Incorrect calculations affecting balances, order execution bugs, data corruption |
| **Medium** | TBD | SDK method returns wrong data, API endpoint misbehaves, indexer misses events |
| **Low** | TBD | Documentation errors, UI inconsistencies, edge case handling |

> **Note:** Exact point values per severity to be decided later. Build the submission, verification, and points-award pipeline now â€" values will be configured before launch.

### Rules
- **First discovery only** â€" duplicate reports for the same bug earn 0 points. The first valid report gets the reward.
- **Must be verifiable** â€" team reviews each report and marks it `verified`, `duplicate`, or `invalid`
- **Points awarded on verification** â€" not on submission. Prevents spam reports.
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
| **1 pt per $50 volume** | 50x lower earn rate than 1:1 | Massive volume needed to mine meaningful points |
| **Category diversity multiplier** | 1x for single-action, up to 32x for diverse | Bot farms doing one thing each are 32Ã- less efficient |
| **Social verification gate** | Max 8x without linked X account | Hard cap forces social verification to reach top tiers |
| **🚨 ANY token transfer = flagging + review** | Wallet-to-wallet transfer of ANY token (USDB, STASIS, factory tokens, Predict+) triggers automatic flagging. Accidental transfers disputable; confirmed sybil = permanent ban. | Prevents sybil funding via any token route. |
| **One-time faucet ($10K)** | Each wallet gets $10K USDB once, no refills | Fixed capital per wallet â€" can't endlessly fund bots |
| **Minimum trade sizes** | $5 predictions, $10 DEX | Eliminates dust-trade mining |
| **Daily caps** | 5,000 base pts per category per day | Limits max extractable points per wallet |
| **Social rate limits** | Moltbook: 1 post/30 min. X: 3 verified/day | Natural spam protection |
| **Lending/vault time lock** | Points accrue daily on committed capital | Can't mine without locking real capital |

### Token Transfer Ban (Nuclear Option)

**Any wallet-to-wallet transfer of ANY token triggers automatic flagging and point suspension for BOTH the sending and receiving wallet.** Accidental transfers (code bugs, wrong address) can be disputed and reinstated if there's no evidence of multi-wallet gaming. Confirmed sybil activity (funding other wallets, splitting activity across addresses) = permanent disqualification.

This applies to ALL ecosystem tokens:
- USDB
- STASIS / wSTASIS
- All factory tokens (Stable+, Floor+)
- All Predict+ tokens
- Any token created on the platform

There is no legitimate reason to transfer tokens directly to another wallet during the testing phase. All trading goes through the DEX, all lending goes through contracts, all vault operations go through the vault contract.

Without this ban, an attacker could bypass the USDB faucet limit by:
1. Claiming 10K USDB on 10 wallets
2. Buying STASIS on 9 of them
3. Transferring STASIS to the 10th wallet
4. 10th wallet now has 10K USDB + 90K worth of STASIS

With the ban: each wallet is completely isolated. No capital can move between wallets through any token route.

**Implementation:** Pre-airdrop batch scan (not real-time). Before any token distribution:
1. Get all token contract addresses from `Project` table + USDB + STASIS + wSTASIS
2. For each token contract, scan all `Transfer(from, to, amount)` events for the entire testing period
3. Build whitelist of known contract addresses (swap, factory, vault, loan hub, resolver, etc.)
4. Any Transfer where BOTH `from` and `to` are NOT known contracts = flag both wallets
5. Flagged wallets: set `WalletPoints.totalPoints = 0` and all category points to 0
6. Log each wipe in PointEvent with `action=transfer_ban_wipe`

This scan runs once, can take as long as needed (hours/days), and catches everything retroactively. The deterrent works because participants know the scan will happen but not when — the uncertainty is part of the punishment.

### One-Time Faucet ($10K USDB)

The USDB faucet is changing from unlimited daily claims to a **one-time $10K claim per wallet**. This is Alex's contract/backend change, not part of the points processor, but it's a critical anti-sybil foundation â€" it caps the capital available per wallet for the entire testing period.

### Pre-Airdrop Batch Analysis (Before Distribution)

This runs once before any token distribution. NOT in the real-time processor.

| Analysis | What It Does | Flag If |
|---|---|---|
| **Funding source clustering** | Trace where each wallet's initial funds came from | 5+ wallets funded from same source within 24h |
| **Timing correlation** | Compare transaction timestamps across wallets | Wallets transacting within same 5-second windows repeatedly |
| **Graph analysis** | Map token/USDC transfers between wallets | Circular flows (Aâ†'Bâ†'Câ†'A) or star patterns (Aâ†'B, Aâ†'C, Aâ†'D) |
| **Unique counterparty count** | How many distinct wallets each wallet interacts with | <5 counterparties after 30 days = suspicious |
| **Manual review** | Top 100 wallets reviewed by team | Any wallet with anomalous patterns |

**Process:** Flag â†' 7-day appeal window â†' zero flagged wallets' points â†' distribute

---

## Molt Tier System

Tiers are derived from total points â€" just a lookup, no separate tracking:

| Tier | Points Required | Emoji | Label |
|---|---|---|---|
| Egg | 0 | ðŸ¥š | New arrival |
| Shrimp | 1,000 | ðŸ¦ | Hatched |
| Crab | 5,000 | ðŸ¦€ | Growing |
| Lobster | 25,000 | ðŸ¦ž | Molting |
| Alpha Lobster | 100,000 | ðŸ'' | Apex |
| Diamond Lobster | 500,000 | ðŸ'Ž | Legend |

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
                         // x_verified_post, bug_report, daily_rank_bonus,
                         // vesting_create, vesting_claim, vesting_extend
  basePoints    Int
  categoryMult  Float    @default(1.0)
  streakMult    Float    @default(1.0)
  finalPoints   Int
  txHash        String?
  tokenAddress  String?
  usdAmount     Float?
  sourceTable   String?  // TokenTransaction, MarketSharesTrade, Project, Agent, LoanEvent, VaultEvent, VestingEvent, MoltbookActivity, SocialActivity
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

model LobsterTide {
  id          Int      @id @default(autoincrement())
  name        String   // "First 50 Lobsters", "Stealth Tide #1"
  multiplier  Float    // 1.5, 2.0, 3.0
  startTime   DateTime
  endTime     DateTime
  announced   Boolean  @default(false)  // false = stealth (announced after)
  announcedAt DateTime?
  createdBy   String   // admin wallet
  createdAt   DateTime @default(now())

  @@index([startTime, endTime])
}

model WeeklyRanking {
  id          Int      @id @default(autoincrement())
  wallet      String
  category    String   // trading, predictions, creation, lending, vault, social, resolver
  weekStart   DateTime // Monday 00:00 UTC
  rank        Int      // 1-10
  basePoints  Int      // base points earned in that category that week
  bonusPoints Int      // flat bonus awarded
  createdAt   DateTime @default(now())

  @@unique([wallet, category, weekStart])
  @@index([weekStart, category])
  @@index([wallet])
}

model Referral {
  id              Int      @id @default(autoincrement())
  referrerWallet  String   // who referred
  refereeWallet   String   @unique // who was referred (one referrer per wallet)
  l1              Boolean  @default(true)  // direct referral
  createdAt       DateTime @default(now())

  @@index([referrerWallet])
  @@index([refereeWallet])
}
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

// Loan events (take, extend)
const newLoanEvents = await prisma.loanEvent.findMany({
  where: { id: { gt: lastLoanEventId }, action: { in: ['created', 'extended'] } },
  orderBy: { id: 'asc' },
  take: 1000
});

// Vesting events (create, claim, extend)
const newVestingEvents = await prisma.vestingEvent.findMany({
  where: { id: { gt: lastVestingEventId }, action: { in: ['created', 'claimed', 'extended'] } },
  orderBy: { id: 'asc' },
  take: 1000
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
      return Math.floor(usdAmount / 50);   // 1 pt per $50
    case 'bonding':
      if (usdAmount < 10) return 0;
      return Math.floor((usdAmount / 50) * 2); // 2 pt per $50
    case 'predictions':
      if (usdAmount < 5) return 0;    // min $5
      return Math.floor(usdAmount / 50);    // 1 pt per $50
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

  // Agent registration (persistent â€" not time-windowed)
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

  // Social â€" Moltbook
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

  // Social â€" X/Twitter
  const xPosts = await prisma.socialActivity.count({
    where: { wallet, platform: 'x', verified: true, createdAt: { gte: sevenDaysAgo } }
  });
  if (xPosts >= 3) cp += 2;
  else if (xPosts >= 1) cp += 1;

  // Vesting
  const vestingCreated = await prisma.vestingEvent.count({
    where: { wallet, action: 'created', createdAt: { gte: sevenDaysAgo } }
  });
  if (vestingCreated >= 1) cp += 2;

  // Testing â€" Bug reports
  const verifiedBugs = await prisma.bugReport.count({
    where: { wallet, status: 'verified', createdAt: { gte: sevenDaysAgo } }
  });
  if (verifiedBugs >= 1) cp += 2;  // any verified bug = strong signal of real engagement

  return cp;
}

function cpToMultiplier(cp: number, hasSocialVerification: boolean): number {
  const MAX_WITHOUT_SOCIAL = 8;  // Hard cap: 8x max without linked + verified social (X)

  let multiplier = 1;
  if (cp >= 15) multiplier = 32;
  else if (cp >= 13) multiplier = 24;
  else if (cp >= 11) multiplier = 16;
  else if (cp >= 9) multiplier = 12;
  else if (cp >= 7) multiplier = 8;
  else if (cp >= 5) multiplier = 4;
  else if (cp >= 3) multiplier = 2;

  // Without social verification, cap at 8x regardless of CP
  if (!hasSocialVerification) {
    multiplier = Math.min(multiplier, MAX_WITHOUT_SOCIAL);
  }

  return multiplier;
}

// Check social verification status
async function hasSocialVerification(wallet: string): Promise<boolean> {
  const socialLink = await prisma.socialLink.findFirst({
    where: { wallet, platform: 'twitter' }
  });
  return !!socialLink;
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

// Check for active Lobster Tide
async function getActiveTideMult(): Promise<number> {
  const now = new Date();
  const tide = await prisma.lobsterTide.findFirst({
    where: { startTime: { lte: now }, endTime: { gte: now } }
  });
  return tide ? tide.multiplier : 1.0;
}

// Calculate referral multiplier for a wallet
async function getReferralMultiplier(wallet: string): Promise<number> {
  // L1 quality bonus: sum of per-referee bonuses (capped)
  const l1Referees = await prisma.referral.findMany({
    where: { referrerWallet: wallet, l1: true }
  });
  
  const L1_TIERS = [[100000, 0.05], [25000, 0.03], [5000, 0.015], [1000, 0.008]];
  const L1_CAP_PER = 0.05;
  const L1_CAP_TOTAL = 0.50;
  
  let l1Total = 0;
  let activeL1Count = 0;
  for (const ref of l1Referees) {
    const refPoints = await prisma.walletPoints.findUnique({ where: { wallet: ref.refereeWallet } });
    const pts = refPoints?.totalPoints || 0;
    if (pts > 0) activeL1Count++;
    let bonus = 0;
    for (const [threshold, mult] of L1_TIERS) {
      if (pts >= threshold) { bonus = mult; break; }
    }
    l1Total += Math.min(bonus, L1_CAP_PER);
  }
  l1Total = Math.min(l1Total, L1_CAP_TOTAL);

  // L2 quality bonus: referees of referees
  const L2_TIERS = [[100000, 0.012], [25000, 0.008], [5000, 0.004], [1000, 0.002]];
  const L2_CAP_PER = 0.012;
  const L2_CAP_TOTAL = 0.15;
  
  let l2Total = 0;
  for (const ref of l1Referees) {
    const l2Referees = await prisma.referral.findMany({
      where: { referrerWallet: ref.refereeWallet, l1: true }
    });
    for (const l2ref of l2Referees) {
      const l2Points = await prisma.walletPoints.findUnique({ where: { wallet: l2ref.refereeWallet } });
      const pts = l2Points?.totalPoints || 0;
      let bonus = 0;
      for (const [threshold, mult] of L2_TIERS) {
        if (pts >= threshold) { bonus = mult; break; }
      }
      l2Total += Math.min(bonus, L2_CAP_PER);
    }
  }
  l2Total = Math.min(l2Total, L2_CAP_TOTAL);

  // Count tier bonus
  const COUNT_TIERS = [[50, 0.35], [20, 0.25], [10, 0.15], [3, 0.08]];
  let countBonus = 0;
  for (const [threshold, mult] of COUNT_TIERS) {
    if (activeL1Count >= threshold) { countBonus = mult; break; }
  }

  return l1Total + l2Total + countBonus;
}
```

### Step 4.5: Weekly rankings processor (Monday 00:00 UTC cron)

```typescript
async function processWeeklyRankings() {
  const weekStart = startOfWeek(new Date(), { weekStartsOn: 1 });
  const prevWeekStart = subDays(weekStart, 7);

  const categories = ['trading', 'predictions', 'creation', 'lending', 'vault', 'social', 'resolver'];
  
  const bonusTable: Record<string, number[]> = {
    trading:     [2000, 1000, 1000, 500, 500, 250, 250, 250, 250, 250],
    predictions: [2000, 1000, 1000, 500, 500, 250, 250, 250, 250, 250],
    creation:    [1500, 750, 750, 400, 400, 200, 200, 200, 200, 200],
    lending:     [1000, 500, 500, 250, 250, 125, 125, 125, 125, 125],
    vault:       [1000, 500, 500, 250, 250, 125, 125, 125, 125, 125],
    social:      [1000, 500, 500, 250, 250, 125, 125, 125, 125, 125],
    resolver:    [1500, 750, 750, 400, 400, 200, 200, 200, 200, 200],
  };

  for (const category of categories) {
    const topWallets = await prisma.pointEvent.groupBy({
      by: ['wallet'],
      where: {
        category,
        createdAt: { gte: prevWeekStart, lt: weekStart },
      },
      _sum: { basePoints: true },
      orderBy: { _sum: { basePoints: 'desc' } },
      take: 10,
    });

    for (let i = 0; i < topWallets.length; i++) {
      const { wallet, _sum } = topWallets[i];
      if ((_sum.basePoints || 0) < 500) continue; // minimum threshold

      const bonus = bonusTable[category][i];
      
      await prisma.weeklyRanking.create({
        data: {
          wallet, category, weekStart: prevWeekStart,
          rank: i + 1,
          basePoints: _sum.basePoints || 0,
          bonusPoints: bonus,
        }
      });

      await prisma.pointEvent.create({
        data: {
          wallet, category: 'ranking',
          action: `weekly_rank_${category}`,
          basePoints: bonus,
          categoryMult: 1.0, streakMult: 1.0,
          finalPoints: bonus, // flat, NOT multiplied
          sourceTable: 'WeeklyRanking',
        }
      });

      await prisma.walletPoints.update({
        where: { wallet },
        data: { totalPoints: { increment: bonus } },
      });
    }
  }
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
  const hasSocial = await hasSocialVerification(wallet);
  const categoryMult = cpToMultiplier(cp, hasSocial);
  const { multiplier: streakMult, days: streakDays } = await getStreakMultiplier(wallet);
  const tideMult = await getActiveTideMult();  // 1.0 if no active tide
  const referralMult = await getReferralMultiplier(wallet);  // 0.0 if no referrals
  const finalPoints = Math.floor(basePoints * categoryMult * streakMult * tideMult * (1 + referralMult));

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

### Points Visibility Strategy

**Points are completely invisible until TGE.** Users never see point totals, multipliers, tiers, hints, or any reference to a points system. The only public-facing data is the USDB balance leaderboard.

Points accrue silently in the database. Post-TGE, flip `POINTS_VISIBLE=true` to reveal everything.

### `GET /api/v1/leaderboard`

**Auth:** Public

**Query params:** `?limit=100&offset=0`

**The leaderboard shows USDB balances only.** No points, no tiers, no hints. Just wallet and balance.

**Response (pre-TGE):**

```json
{
  "total": 847,
  "leaderboard": [
    {
      "rank": 1,
      "wallet": "0x...",
      "balanceUSDB": 8742.50
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

**Response (post-TGE â€" `POINTS_VISIBLE=true`):** Adds `totalPoints`, tier, multiplier data. Re-ranked by points.

### `GET /api/v1/points/{wallet}`

**Pre-TGE:** This endpoint returns `404` or is not exposed at all. No points data is public.

**Post-TGE (`POINTS_VISIBLE=true`):**

```json
{
  "wallet": "0x...",
  "totalPoints": 47250,
  "tier": "Lobster",
  "tierEmoji": "ðŸ¦ž",
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
  "cumulativeVolumeUSDB": 52300.00,
  "lastActive": "2026-03-21T12:34:56Z"
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
3. Confirm text contains `@LaunchOnBasis` tag (case-insensitive)
4. Confirm tweet author matches linked X handle
5. Check not already submitted (unique tweetId)
6. Check daily cap (max 3 per wallet per day)

**Response (201):**

```json
{
  "success": true,
  "verified": true,
  "message": "Tweet verified. Points will be awarded."
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

## Configuration Flags

```typescript
// Environment config â€" controls what's exposed pre vs post TGE
const POINTS_VISIBLE = process.env.POINTS_VISIBLE === 'true'; // default: false
// When false: leaderboard shows USDB balances only, /points/{wallet} returns 404
// When true: full point data exposed in both endpoints
```

---

## Implementation Checklist

### Phase 1 â€" Core Points Engine
- [ ] Add Prisma models: PointEvent, WalletPoints, DailyActivity, ProcessorState, LobsterTide, Referral
- [ ] `prisma migrate dev`
- [ ] Points processor job (runs every 60s):
  - [ ] Process new `TokenTransaction` buys â†' trading points
  - [ ] Process new `MarketSharesTrade` buys â†' prediction points
  - [ ] Process new `Project` creation â†' creation points (tokens: 2000, markets: 1000 after 5 buyers)
  - [ ] Process new `Agent` registration â†' registration points (500)
  - [ ] Detect reward phase buys (cross-reference `Whitelist` table) â†' 2x points
  - [ ] Process new `LoanEvent` rows (action=created â†' 200 pts, action=extended â†' 100 pts)
  - [ ] Process new `VestingEvent` rows (created â†' 200 pts, claimed â†' 100 pts)
  - [ ] Process new `LoanEvent` where source=vesting (loan against vested tokens â†' 200 pts)
  - [ ] Apply daily caps (5,000 base per category per day)
  - [ ] Compute category diversity multiplier (rolling 7-day CP)
  - [ ] Compute streak multiplier (+10%/day, max 2x)
  - [ ] Check active Lobster Tide â†' apply tide_mult (1.0 if none)
  - [ ] Compute referral multiplier (L1 quality + L2 quality + count tier)
  - [ ] Write PointEvent + update WalletPoints + update DailyActivity
  - [ ] Track last processed ID per source table in ProcessorState
- [ ] `GET /api/v1/leaderboard` â€" USDB balances only (no points references) until TGE
- [ ] `GET /api/v1/points/{wallet}` â€" returns 404 pre-TGE, full data post-TGE
- [ ] `POINTS_VISIBLE` env flag â€" when true, expose full point data in both endpoints
- [ ] `POST /api/v1/admin/tides` â€" admin endpoint to create Lobster Tides
- [ ] Referral tracking: record referral on first platform action via `?ref=` link

### ~~Phase 1.5~~ â€" Moved to Phase 4 (Pre-Airdrop)
_Token transfer scanning is now a one-time pre-airdrop batch job, not a real-time monitor. See Phase 4._

### Phase 2 â€" Daily Accrual + Weekly Rankings
- [ ] Vault daily accrual cron (snapshot balances, award 2 pts/$1/day)
- [ ] Active loan daily accrual (1 pt/day per active loan)
- [ ] Active vesting daily accrual (1 pt/day per active vesting schedule)
- [ ] Add lending + vault + vesting to category diversity scoring
- [ ] Add Prisma model: WeeklyRanking
- [ ] Weekly ranking cron job (Monday 00:00 UTC) â€" top 10 per category earn flat bonus
- [ ] `GET /api/v1/rankings/weekly` endpoint (post-TGE visibility)

### Phase 3 â€" Social Points
- [ ] Add Prisma models: MoltbookActivity, SocialActivity
- [ ] `POST /api/v1/moltbook/log` endpoint
- [ ] `POST /api/v1/social/verify-tweet` endpoint (oEmbed verification)
- [ ] Points processor: process MoltbookActivity logs
- [ ] Points processor: process verified SocialActivity
- [ ] Add social to category diversity scoring
- [ ] Content similarity detection for anti-spam

### Phase 3.5 â€" Leaderboard Bonus + Bug Bounty
- [ ] Add Prisma model: BugReport
- [ ] `POST /api/v1/bugs/report` endpoint
- [ ] Admin verification flow (mark reports verified/duplicate/invalid)
- [ ] Points processor: award points on bug verification
- [ ] Leaderboard daily bonus cron (00:00 UTC, top 10 wallets)
- [ ] Add testing + leaderboard to PointEvent categories

### Phase 4 â€" Pre-Airdrop Analysis (includes token transfer scan)
- [ ] **Token transfer scan** â€" scan ALL token contracts (from `Project` table + USDB + STASIS + wSTASIS) for Transfer events where both `from` and `to` are non-contract wallets. Flag and wipe both wallets. This is the nuclear deterrent enforcement.
- [ ] Funding source clustering script
- [ ] Timing correlation analysis
- [ ] Graph analysis (circular flows, star patterns)
- [ ] Manual review process for top 100 wallets
- [ ] Appeal window (7 days)
- [ ] Zero flagged wallets' points

---

_This spec reads from existing indexed data wherever possible. Only vault/lending daily accrual needs RPC calls. Everything else derives from the tables you already have._

