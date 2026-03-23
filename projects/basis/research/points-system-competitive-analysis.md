# Points System Competitive Analysis

_Diamond requested 2026-03-22 | Compiled 2026-03-23_

How Monad, Hyperliquid, Aster, and Plasma structured their points/airdrop systems — and what Basis can learn.

---

## 1. Hyperliquid — The Gold Standard

**The most successful airdrop in crypto history.** ~$2B distributed. Set the template everyone else is now copying.

### Structure
- **Fixed weekly pool**: 1M points/week (Season 1), 700K/week (Season 2). Total supply of points was limited — this prevented inflation and created real competition.
- **Duration**: ~12 months total. Closed alpha (pre-Oct 2023) → Season 1 (Nov 2023–May 2024) → Season 1.5 (May, 2x multiplier bridge) → Season 2 (May–Sep 2024) → Season 2.5 (Sep–Nov 2024)
- **Weekly cycles**: Points calculated and distributed weekly (snapshot Wed 00:00 UTC, distribution Thurs)
- **Referrals**: Affiliates earned 1 point per 4 points their referred users earned (25% rate)
- **Conversion**: 31% of HYPE supply airdropped to users based on points

### What Earned Points
- Trading volume (perps initially, spot added in S2)
- Deposits / TVL contribution
- Position holding time
- Season 2 broadened: spot trading + asset holding (leveled the field for retail)

### Anti-Gaming
- Wash trading penalized (not just ignored — actively punished)
- Linked wallet detection → sybil label
- Withdrawals penalized
- **Criteria kept deliberately opaque** — users knew the general behaviors that earned points but not exact formulas. This prevented reverse-engineering.

### Key Insight for Basis
> **Limited points + opaque formula + genuine product utility = the winning formula.** Hyperliquid's points worked because the product was actually good. The points drove real usage, not fake activity. They also used "surprise seasons" (1.5, 2.5) to reward real users who stuck around vs. farmers who left after announced seasons.

---

## 2. Monad — Community-First, Not Points-First

**Radically different approach.** No points system at all. Airdrop based on community contribution, not farming.

### Structure
- **3.3% of MON supply** airdropped (4.73B tokens across 289K eligible accounts)
- **Five tracks** (not a single points leaderboard):
  1. **Monad Community** (largest): 5,935 accounts → 1.67B tokens. Intensive manual + community input assessment of impact and commitment.
  2. **Onchain Users**: 229K accounts → 1.7B tokens. Power DeFi users, NFT holders.
  3. **Crypto Community**: 46K accounts → 897M tokens. Monad Cards holders, event participants.
  4. **Monad Builders**: 2,860 accounts → 288M tokens. Project teams, hackathon devs.
  5. **Crypto Contributors**: 4,431 accounts → 172M tokens. Auditors, educators, Protocol Guild.

### How Community Was Assessed
- Social data from Discord, Telegram, X
- Built a **"Recognizer App"** — community members nominated other community members
- Manual review by Monad team over months
- Post-launch vouching system to catch missed contributors
- **No formula, no leaderboard, no farming.** Pure human assessment of genuine contribution.

### Anti-Gaming
- No formula to game — everything was retrospective human judgment
- Sanctions screening (Chainalysis)
- Geo-blocking restricted jurisdictions
- Team members explicitly excluded

### Key Insight for Basis
> **Community recognition > automated points for building genuine loyalty.** Monad's 99.7% claim rate on community tokens (vs 41% on onchain user tokens) proves that people who feel personally recognized are far more engaged. However, this doesn't scale to 1000+ agents — it worked for Monad because they had 5,935 core community members. Basis is more automated by nature, so the diversity multiplier serves a similar "reward genuine engagement" function.

---

## 3. Aster (formerly ApolloX → DEX) — Volume-Heavy, Multi-Stage

**Perp DEX competitor to Hyperliquid.** Heavily volume-focused points with weekly resets.

### Structure
- **53.5% of total supply** (4.28B ASTER) allocated to community rewards — massive allocation
- **Multi-stage rollout**: Stage 0 (pre-TGE) → Stage 1 (TGE launch) → Stage 2 Genesis (ongoing) → Stage 3+ 
- **"Rh Points"** — reset weekly (Monday 00:00 UTC), convert to future token drops
- **Epoch structure**: 0.5% supply per epoch initially, declining over time
- **Referrals**: 10% first-level, 5% second-level

### What Earned Points (Rh Points)
- **Trading volume** (taker orders earn 2x vs maker)
- **Average position holding time** (caps at 2x weekly volume score)
- **Realized P&L** (both profits AND losses count — rewards active trading)
- **Collateral size** (using yield-bearing collateral like asBNB/USDF gets a multiplier)
- **Rank-based, not raw value**: Only your rank on each leaderboard matters — this prevents gaming by raw volume

### Anti-Gaming
- Rank-based scoring (not raw values) prevents whales from simply dumping volume
- Weekly resets prevent early accumulation advantage
- Multiple scoring dimensions make single-metric gaming inefficient

### Key Insight for Basis
> **Weekly resets are double-edged.** They prevent early movers from locking in permanent advantages, but they also reduce urgency and can feel like a treadmill. Basis's "points carry over across phases" approach is better for retention. **The rank-based scoring is interesting** — it means absolute volume doesn't matter, only relative position. Could inspire how Basis thinks about the diversity multiplier (relative engagement across categories, not absolute numbers).

> **Both profits AND losses counting toward points** is clever — it rewards active trading without penalizing losing traders. Basis doesn't need this since we don't track P&L for points, but it's worth noting as a "keep people trading even when they're losing" mechanic.

---

## 4. Plasma — The "$0.10 Airdrop Myth"

**Radically simple.** Equal distribution regardless of deposit size. Not really a "points system" — more of a participation reward.

### Structure
- **18% of 10B XPL** initially circulating at launch (Sep 25, 2025)
- **Pre-depositor airdrop**: 25M tokens split equally among ALL depositors — whether you deposited $0.10 or $10,000, you got the same amount
- **Result**: Every participant received ~$8,390 worth of XPL regardless of deposit size
- **Additional distribution**: 40% ecosystem development, 10% public sale (oversubscribed $300M+), 25% team/investors (multi-year vesting)

### What Qualified
- Simply depositing ANY amount during the pre-launch period
- Claiming within the window (half claimed within 3 hours)

### Anti-Gaming
- Equal distribution eliminates whale advantage entirely
- Deposit size literally doesn't matter — 1 account = 1 share
- US investors delayed to July 2026 (regulatory)

### Key Insight for Basis
> **Equal distribution creates massive viral buzz** ("$0.10 got me $8,390!") but is fundamentally different from what Basis needs. Plasma didn't need to incentivize specific behaviors — they just needed warm bodies to prove adoption for Tether. Basis needs agents doing diverse platform activities, which requires a more sophisticated scoring system. **However, the "everyone gets something meaningful" principle is worth preserving** — ensure the minimum viable participation on Basis still feels rewarding, not just dust.

---

## Comparative Summary

| | Hyperliquid | Monad | Aster | Plasma |
|---|---|---|---|---|
| **Supply to community** | 31% | 3.3% | 53.5% | ~18% |
| **Points system?** | Yes (fixed weekly pool) | No (manual assessment) | Yes (weekly reset) | No (equal split) |
| **Formula public?** | Partially (behaviors known, weights hidden) | N/A | Partially (rank-based) | N/A |
| **Duration** | ~12 months | Retrospective | Ongoing stages | One-time |
| **Anti-sybil** | Wash trade penalties, wallet linking detection | Human judgment | Rank-based scoring | Equal distribution |
| **Referral** | 25% of referred points | None | 10% L1 + 5% L2 | None |
| **Key innovation** | Limited supply of points + surprise seasons | Community recognition app | P&L counts + yield collateral bonus | Equal distribution regardless of amount |

---

## Lessons for Basis

### ✅ What Basis Already Does Right
1. **Opaque formula** (like Hyperliquid) — publishing exact values enables min-cost gaming
2. **Diversity multiplier** (better than all four) — none of these projects rewarded breadth of engagement this explicitly
3. **Multi-phase with carryover** (better than Aster resets) — early participants maintain advantage without weekly treadmill
4. **Transfer ban / anti-sybil** (stronger than all four) — Hyperliquid penalized wash trading; Basis goes further with total transfer flagging
5. **25% supply allocation** — in line with Hyperliquid (31%), much more generous than Monad (3.3%)

### 🤔 Worth Considering
1. **Limited points pool** (Hyperliquid): Consider whether a fixed weekly/monthly points budget (vs unlimited accrual) would create more competitive engagement. Currently Basis has daily caps per category, but total points are uncapped across wallets.
2. **Surprise bonus seasons** (Hyperliquid 1.5, 2.5): Consider unannounced bonus multiplier periods to reward consistent users vs. farmers who game known schedules.
3. **Rank-based scoring** (Aster): For certain categories, rank might matter more than raw volume. A trader doing $50K in a thin market deserves more recognition than $50K in a deep one.
4. **Community recognition element** (Monad): The Molt tier system partially addresses this, but a "community vouching" mechanism for the top tier (Diamond Lobster) could add a human signal that's hard to fake.
5. **Guaranteed minimum reward** (Plasma): Ensure the minimum viable Basis participation feels meaningful, not just dust — even an Egg-tier agent should feel their time was valued.

### ❌ What to Avoid
1. **Pure volume-based scoring** (Aster's primary metric) — rewards wash trading, benefits whales disproportionately
2. **No points system at all** (Monad) — doesn't scale for 1000+ agents, requires manual review
3. **Equal distribution** (Plasma) — removes all incentive for quality/depth of engagement
4. **Fully transparent formula** — every project that published exact mechanics got gamed

---

_Sources: Hyperliquid GitBook, PANews analysis, Monad official announcements, Boxmining Aster guide, MEXC/BingX Plasma coverage_
