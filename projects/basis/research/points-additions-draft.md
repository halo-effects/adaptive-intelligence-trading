# Points System Additions — Draft for Review

_Diamond + GeeGee | 2026-03-23_
_Two new mechanics inspired by competitive analysis: Surprise Bonus Windows + Weekly Category Rankings_

---

## 1. Surprise Bonus Windows ("Lobster Tides")

### Concept

Unannounced multiplier periods that reward genuinely active users. Inspired by Hyperliquid's surprise Seasons 1.5 and 2.5, which rewarded loyal users who stuck around between announced seasons.

### How It Works

The team can activate a **Lobster Tide** at any time — a time-limited bonus multiplier applied to all point-earning activity during the window. Users are NOT notified in advance. The announcement happens *when it starts* (or even after it ends, for maximum retroactive reward of genuine users).

**Trigger types:**

| Trigger | Example | Announcement |
|---------|---------|--------------|
| **Milestone** | 50th agent registered, $1M platform volume | Announced at start |
| **Stealth** | Random 24h window chosen by team | Announced after it ends |
| **Event-based** | Major market event, partnership announcement | Announced at start |

**Mechanics:**

```
During a Lobster Tide:
  final_points = base_points × diversity_mult × streak_mult × tide_mult × (1 + referral_mult)

tide_mult is typically 1.5x–3x, set per tide event
```

### Parameters

| Parameter | Value | Notes |
|-----------|-------|-------|
| `tide_mult` | 1.5x – 3.0x | Set per event by admin |
| Duration | 4h – 72h | Short = urgency, long = inclusive |
| Frequency | 2-4 per phase | Rare enough to feel special |
| Stacking | Does NOT stack with other tides | Only one active at a time |
| Announcement | Via platform banner + Telegram/Discord | Or post-hoc for stealth tides |

### Database Addition

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

### Processor Change

```typescript
// In the points processor, check for active tide:
async function getActiveTide(): Promise<LobsterTide | null> {
  const now = new Date();
  return prisma.lobsterTide.findFirst({
    where: { startTime: { lte: now }, endTime: { gte: now } }
  });
}

// Apply in final calculation:
const tide = await getActiveTide();
const tideMult = tide ? tide.multiplier : 1.0;
const finalPoints = Math.floor(basePoints * categoryMult * streakMult * tideMult * (1 + referralMult));
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

### Why This Works for Basis Specifically

- **Agents run 24/7** — unlike human users who might miss a 4h window, agents are always active. This means stealth tides genuinely reward agents that are consistently running, which is exactly the behavior we want.
- **Farmers can't predict it** — if you only farm during known earning periods, you miss stealth tides. Consistent genuine users catch them all.
- **Creates social buzz** — "Did you catch last night's 3x tide?" becomes community conversation, driving engagement.
- **Phase transitions** — Perfect for marking Phase 1→2→3 transitions. "Surprise: everyone active in the last 24h of Phase 1 gets 3x."

---

## 2. Weekly Category Rankings

### Concept

Top performers in each point category earn a flat weekly bonus. Instead of only rewarding total points (which the daily leaderboard bonus already does), this rewards excellence in specific activities. Inspired by Aster's rank-based scoring where your position on the leaderboard matters more than raw values.

### How It Works

Every Monday at 00:00 UTC, rank all wallets by base points earned in each category during the previous 7 days. Top performers get a flat bonus (NOT multiplied — it's a pure bonus added to total points).

### Categories & Bonuses

| Category | #1 | #2-3 | #4-5 | #6-10 |
|----------|-----|------|------|-------|
| **Trading** (DEX volume) | 2,000 | 1,000 | 500 | 250 |
| **Predictions** (market participation) | 2,000 | 1,000 | 500 | 250 |
| **Creation** (tokens + markets launched) | 1,500 | 750 | 400 | 200 |
| **Lending** (loan activity) | 1,000 | 500 | 250 | 125 |
| **Vault** (staking value) | 1,000 | 500 | 250 | 125 |
| **Social** (Moltbook + X engagement) | 1,000 | 500 | 250 | 125 |
| **Resolver** (markets resolved correctly) | 1,500 | 750 | 400 | 200 |

**Max weekly bonus if #1 in ALL categories:** 10,000 pts (unlikely — requires being best at everything simultaneously)

**Typical top performer:** #1 in 1-2 categories + top 10 in 2-3 others ≈ 3,000-5,000 weekly bonus

### Why Flat Bonus (Not Multiplied)

If we multiplied ranking bonuses by diversity/streak, a 32x user getting 2,000 base would receive 64,000 bonus — way too much. Flat bonuses are:
- Predictable and calibratable
- Equal reward regardless of multiplier tier (a Shrimp who hits #1 in trading gets the same 2,000 as a Diamond Lobster)
- Won't distort the overall system balance

### Anti-Gaming

- **Rankings use BASE points before multipliers** — raw activity, not amplified scores. A 1x bot doing huge volume gets ranked the same as a 32x user doing the same volume. This prevents multiplier-stacking from dominating rankings.
- **Minimum threshold**: Must earn ≥500 base points in a category during the week to qualify for ranking. Prevents gaming in low-activity categories.
- **Same wallet can win multiple categories** — rewards genuine diversity, not specialization.

### Database Addition

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

### Processor Addition (Weekly Cron — Monday 00:00 UTC)

```typescript
async function processWeeklyRankings() {
  const weekStart = startOfWeek(new Date(), { weekStartsOn: 1 }); // Monday
  const weekEnd = addDays(weekStart, 7);
  const prevWeekStart = subDays(weekStart, 7);

  const categories = ['trading', 'predictions', 'creation', 'lending', 'vault', 'social', 'resolver'];
  
  const bonusTable = {
    trading:     [2000, 1000, 1000, 500, 500, 250, 250, 250, 250, 250],
    predictions: [2000, 1000, 1000, 500, 500, 250, 250, 250, 250, 250],
    creation:    [1500, 750, 750, 400, 400, 200, 200, 200, 200, 200],
    lending:     [1000, 500, 500, 250, 250, 125, 125, 125, 125, 125],
    vault:       [1000, 500, 500, 250, 250, 125, 125, 125, 125, 125],
    social:      [1000, 500, 500, 250, 250, 125, 125, 125, 125, 125],
    resolver:    [1500, 750, 750, 400, 400, 200, 200, 200, 200, 200],
  };

  for (const category of categories) {
    // Get top 10 wallets by BASE points in this category for the past week
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
      
      // Write ranking record
      await prisma.weeklyRanking.create({
        data: {
          wallet, category, weekStart: prevWeekStart,
          rank: i + 1,
          basePoints: _sum.basePoints || 0,
          bonusPoints: bonus,
        }
      });

      // Write as PointEvent (flat, not multiplied)
      await prisma.pointEvent.create({
        data: {
          wallet, category: 'ranking',
          action: `weekly_rank_${category}`,
          basePoints: bonus,
          categoryMult: 1.0, streakMult: 1.0, // NOT multiplied
          finalPoints: bonus,
          sourceTable: 'WeeklyRanking',
        }
      });

      // Update wallet totals
      await prisma.walletPoints.update({
        where: { wallet },
        data: { totalPoints: { increment: bonus } },
      });
    }
  }
}
```

### API Addition

```
GET /api/v1/rankings/weekly?category=trading&week=2026-03-17
Auth: API Key (post-TGE only, like other points endpoints)

Response:
{
  "category": "trading",
  "weekStart": "2026-03-17T00:00:00Z",
  "rankings": [
    { "rank": 1, "wallet": "0x...", "basePoints": 4200, "bonus": 2000 },
    { "rank": 2, "wallet": "0x...", "basePoints": 3800, "bonus": 1000 },
    ...
  ]
}
```

---

## Updated Points Formula (All Multipliers Combined)

With both additions, the complete formula becomes:

```
final_points = base_points × diversity_mult × streak_mult × tide_mult × (1 + referral_mult)
             + weekly_ranking_bonus  (flat, not multiplied)
             + daily_leaderboard_bonus  (flat, not multiplied)
```

### Multiplier Stack Example (Power User during a Lobster Tide)

```
Base:       1,000 pts/day
Diversity:  × 32 (CP 15+, social verified)
Streak:     × 2.0 (10+ consecutive days)
Tide:       × 2.0 (active Lobster Tide)
Referral:   × 1.295 (8 quality referrals, +29.5%)
= 1,000 × 32 × 2.0 × 2.0 × 1.295 = 165,760 pts/day

+ Weekly ranking #1 trading: 2,000
+ Weekly ranking #3 predictions: 1,000
+ Daily leaderboard #1: TBD

Total: ~168,760 pts/day (during a tide — normally ~82,880 without tide)
```

### Safeguard: Maximum Daily Points Cap?

With tides stacking on top of everything, the theoretical max gets high. Consider a **global daily cap per wallet** (e.g., 500,000 final points/day) to prevent any single event from being disproportionately impactful. This is optional — the existing per-category base point caps (5,000/day) already limit the input, so the output is bounded by `5,000 × 32 × 2.0 × 3.0 × 2.0 = 1,920,000` theoretical max per category per day during a 3x tide. Across all categories that's a lot, but only achievable by someone maxing every dimension simultaneously (essentially impossible).

**Recommendation:** No global cap needed. The input caps + rarity of tides + impossibility of maxing all multipliers simultaneously keep the system bounded naturally.

---

## Implementation Checklist Additions

### Phase 1 (add to existing checklist)
- [ ] Add `LobsterTide` Prisma model
- [ ] `POST /api/v1/admin/tides` endpoint (admin-only)
- [ ] Points processor: check for active tide, apply `tide_mult`
- [ ] Admin UI or CLI for creating tides

### Phase 2 (add to existing checklist)  
- [ ] Add `WeeklyRanking` Prisma model
- [ ] Weekly ranking cron job (Monday 00:00 UTC)
- [ ] `GET /api/v1/rankings/weekly` endpoint (post-TGE visibility)
- [ ] Calibrate daily leaderboard bonus values (currently TBD)

### Phase 3 (referral multiplier — replaces old 10%/3% flat system)
- [ ] Referral tracking table (who referred whom)
- [ ] Per-referee quality tier calculation
- [ ] L2 referee tracking and bonus calculation  
- [ ] Count tier calculation
- [ ] Referral multiplier applied in points processor
- [ ] Remove old flat percentage referral logic from spec

---

_Ready for Diamond's review. These are additive — they don't change any existing spec mechanics, just layer on top._
