# Points System — Build Spec for Alex

_Author: GeeGee + Brett | Date: 2026-03-17_
_This is everything you need to build the points backend. One document, no chasing._

---

## Claude Code Prompt

Copy-paste this into Claude Code to get started:

```
Read the file points-system-build-spec.md in full. This is the complete spec for a points/rewards system backend for the Basis DeFi platform on BNB Chain.

Your task: Build v0.1 of the points system backend.

Context:
- Basis has 13 smart contracts already deployed on BNB Chain (mainnet)
- An existing indexer already tracks trades, candles, and transaction history
- The points system is an OFF-CHAIN service that watches on-chain events and computes reward points per wallet
- Test currency is USDB (fake USDC, already deployed)
- Points earned during USDB testing carry over to the real BASIS airdrop

Build order:
1. Event indexer — watch the contract events listed in the spec (or piggyback on the existing indexer pipeline if possible). Poll-based is fine (every 30-60s).
2. Points engine — process events into points using the exact rules, base values, and filters in the spec. Start with just base points + minimum filters + daily caps. Multipliers can be v0.2.
3. Database — use the suggested schema (adapt to your existing DB). Track point_events (ledger), wallet_points (aggregates), daily_activity (streaks), indexer_state (last block).
4. API — two endpoints: GET /api/v1/points/{wallet} and GET /api/v1/leaderboard. Response shapes are in the spec.
5. Vault daily accrual — cron/scheduled task that snapshots vault balances and awards 2 pts/$1/day.

What to SKIP for v0.1:
- Social/X verification (Phase 2)
- Referral tracking (Phase 2)
- Anti-sybil graph analysis (Phase 2)
- Trading profit multiplier (v0.2 — needs P&L tracking)

Keep it simple. The existing indexer data pipeline is the foundation — add a points processing layer on top rather than rebuilding event watching from scratch if possible.

Match the existing API patterns (api.basis.exchange) so these endpoints can live alongside the current token/candle/trade endpoints.
```

---

## What This Is

An off-chain service that watches on-chain Basis contract events, computes reward points per wallet, and serves two API endpoints. Points earned during USDB testing carry over to the real BASIS airdrop.

**Goal:** An agent (or human) performs actions on Basis → points accrue automatically → queryable via API.

---

## Architecture Overview

```
BNB Chain (events)
    ↓
[Event Indexer] — watches contract events from all 13 core contracts
    ↓
[Points Engine] — applies rules, multipliers, anti-gaming filters
    ↓
[Database] — wallet points, streaks, tiers, referral chains, daily snapshots
    ↓
[API] — 2 endpoints (points + leaderboard)
```

**Key principle:** This does NOT need to be real-time. Polling every 30-60 seconds or processing events in small batches is fine for the testing phase. Accuracy > speed.

---

## Contracts to Watch

You already have all of these deployed. The indexer needs to watch events from:

| Contract | Events to Track | Points Category |
|---|---|---|
| **ATokenFactory** | Token creation (Stable+/Floor+) | `creation` |
| **ASwap** | `buy`, `sell`, `leverageBuy`, `mixedBuy`, `partialLoanSell` | `trading` |
| **FACTORYTOKEN** | Bonding phase buys (check if token is still in bonding) | `trading` (2x) |
| **AMarketTrading** | `buy` (prediction shares) | `predictions` |
| **APrivateTradingMarket** | `create_market` | `predictions` |
| **AMarketResolver** | Resolution events (propose/finalize) | `predictions` |
| **ALOAN_HUB** / **A_STABLETOKEN** | `take_loan`, `extend_loan`, `repay_loan` | `lending` |
| **AStasisVault** | `buy` (stake), `sell` (unstake), `lock`, `borrow`, `repay` | `vault` |

If your indexer already tracks these events (for the candle/txn data), you can piggyback on that pipeline.

---

## Point-Earning Rules

### Token Creation & Trading

| Action | Base Points | Filter |
|---|---|---|
| Launch a Stable+ or Floor+ token | 500 | One-time per token address |
| DEX buy or sell (any token) | 1 per $1 volume | Min $10 per trade |
| Buy during bonding phase | 2 per $1 volume | Only while token is in bonding |

**Trading Profit Multiplier** (applied on top of volume points, calculated daily or per-session):

| Net P&L | Multiplier |
|---|---|
| Negative | 0.5x |
| Break even | 1.0x |
| Positive (up to 5%) | 1.5x |
| Positive (5%+) | 2.0x |

### Prediction Markets

| Action | Base Points | Filter |
|---|---|---|
| Create a prediction market | 300 | Only awards after ≥5 unique participants |
| Buy prediction tokens | 1 per $1 | Min $5 per buy |
| Resolve a prediction accurately | 500 | Community/oracle verified |
| Prediction betting profit | 1 per $1 **net profit** | Zero if net-zero or negative (prevents hedge-all-outcomes farming) |

### Lending & Vault

| Action | Base Points | Notes |
|---|---|---|
| Take a loan | 200 + 1/day while active | Daily accrual while loan is open |
| Extend a loan | 100 | Per extension |
| Stake STASIS in vault | 2 per $1 per day | Continuous — needs daily snapshot of staked balance |
| Refinance from vault | 150 | Per refinance event |

### Social (Phase 2 — skip for v0.1)

Social points (X/Twitter posting, Moltbook) need X API integration and content verification. **Skip this for the initial build.** We can add it later as a separate module. The on-chain points are the priority.

### Referrals (Phase 2 — skip for v0.1)

Referral tracking (10% of referee's lifetime points) needs a registration system. **Skip for v0.1.** Add when we build the agent wallet registration flow.

---

## Multiplier System

All multipliers stack multiplicatively on base points:

| Multiplier | Condition | Effect |
|---|---|---|
| **Daily Streak** | Wallet has point-earning activity every consecutive day | +10% per day, caps at +100% (10 days) |
| **Diversity** | Used 3+ product categories in a rolling 7-day window | +25% on all points that week |
| **Volume Tier** | Based on cumulative all-time volume | See table below |
| **Founding Lobster** | Flagged wallets (manual for now) | +100% on everything |
| **Early Bird** | First 500 wallets to earn points | +50% on everything |

**Volume Tiers:**

| Tier | Cumulative Volume | Multiplier |
|---|---|---|
| 🦐 Shrimp | $0 – $1K | 1.0x |
| 🦀 Crab | $1K – $10K | 1.2x |
| 🦞 Lobster | $10K – $100K | 1.5x |
| 🐋 Whale Lobster | $100K+ | 2.0x |

**Product categories for diversity check:** trading, predictions, lending, vault, creation (5 categories — need 3+ active in a week).

---

## Anti-Gaming Filters (v0.1 — keep it simple)

For the initial build, just implement these three:

1. **Minimum trade size:** Trades under $10 earn zero points
2. **Minimum prediction bet:** Bets under $5 earn zero points
3. **Daily cap per category:** Max 5,000 points per category per wallet per day
4. **Same-pair cooldown:** Diminishing returns for same token pair trades within 1 hour (50% on 2nd, 25% on 3rd, 0% on 4th+)

The full anti-sybil system (graph analysis, funding source clustering, timing correlation) is Phase 2. We'll run that as a batch analysis before airdrop distribution.

---

## Molt Tier Progression

Tiers are derived from total points — just a lookup, no separate tracking needed:

| Tier | Points Required | Label |
|---|---|---|
| 🥚 Egg | 0 | New arrival |
| 🦐 Shrimp | 1,000 | Hatched |
| 🦀 Crab | 5,000 | Growing |
| 🦞 Lobster | 25,000 | Molting |
| 👑 Alpha Lobster | 100,000 | Apex |
| 💎 Diamond Lobster | 500,000 | Legend |

---

## API Endpoints (2 total for v0.1)

### `GET /api/v1/points/{wallet}`

Returns full points breakdown for a wallet.

```json
{
  "wallet": "0x...",
  "total_points": 47250,
  "tier": "Lobster",
  "tier_emoji": "🦞",
  "next_tier": "Alpha Lobster",
  "next_tier_at": 100000,
  "streak_days": 14,
  "active_multipliers": {
    "streak": 1.10,
    "diversity": 1.25,
    "volume_tier": 1.5,
    "founding_lobster": false,
    "early_bird": true
  },
  "effective_multiplier": 2.0625,
  "breakdown": {
    "trading": 18000,
    "predictions_created": 9600,
    "predictions_participated": 4200,
    "lending": 3800,
    "vault": 8650,
    "referrals": 0
  },
  "volume_tier": "Lobster",
  "cumulative_volume": 52300.00,
  "rank": 42,
  "total_participants": 847,
  "last_active": "2026-03-17T12:34:56Z"
}
```

### `GET /api/v1/leaderboard`

Query params: `?limit=100&offset=0&tier=all`

```json
{
  "season": 1,
  "total_participants": 847,
  "leaderboard": [
    {
      "rank": 1,
      "wallet": "0x...",
      "total_points": 142500,
      "tier": "Alpha Lobster",
      "tier_emoji": "👑",
      "streak_days": 30,
      "top_category": "trading"
    }
  ]
}
```

---

## Database Schema (suggested — use whatever works)

```sql
-- Core points ledger
CREATE TABLE point_events (
    id SERIAL PRIMARY KEY,
    wallet VARCHAR(42) NOT NULL,
    category VARCHAR(20) NOT NULL,  -- trading, predictions, lending, vault, creation
    action VARCHAR(50) NOT NULL,    -- buy, sell, create_token, take_loan, etc.
    base_points DECIMAL NOT NULL,
    multiplier DECIMAL DEFAULT 1.0,
    final_points DECIMAL NOT NULL,
    tx_hash VARCHAR(66),
    token_address VARCHAR(42),
    usd_volume DECIMAL,
    block_number BIGINT,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Aggregated wallet state (updated after each event batch)
CREATE TABLE wallet_points (
    wallet VARCHAR(42) PRIMARY KEY,
    total_points DECIMAL DEFAULT 0,
    trading_points DECIMAL DEFAULT 0,
    predictions_points DECIMAL DEFAULT 0,
    lending_points DECIMAL DEFAULT 0,
    vault_points DECIMAL DEFAULT 0,
    creation_points DECIMAL DEFAULT 0,
    cumulative_volume DECIMAL DEFAULT 0,
    streak_days INT DEFAULT 0,
    last_active_date DATE,
    is_founding_lobster BOOLEAN DEFAULT FALSE,
    is_early_bird BOOLEAN DEFAULT FALSE,
    first_seen TIMESTAMP,
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Daily snapshots for streak tracking + vault daily accrual
CREATE TABLE daily_activity (
    wallet VARCHAR(42),
    activity_date DATE,
    categories_active TEXT[],  -- which categories had activity
    points_earned DECIMAL,
    PRIMARY KEY (wallet, activity_date)
);

-- Track last processed block
CREATE TABLE indexer_state (
    key VARCHAR(50) PRIMARY KEY,
    value VARCHAR(100),
    updated_at TIMESTAMP DEFAULT NOW()
);
-- INSERT INTO indexer_state VALUES ('last_block', '0', NOW());
```

---

## Implementation Priority

### v0.1 — MVP (what we need NOW)

1. **Event indexer**: Poll BNB Chain for events from the contracts listed above. Start from current block. Store raw events.
2. **Points calculator**: Process events → apply base points + minimum filters + daily caps. No multipliers yet if that's faster.
3. **Two API endpoints**: `/points/{wallet}` and `/leaderboard`
4. **Vault daily accrual**: Cron job or scheduled task that snapshots vault balances and awards 2 pts/$1/day

That's it. No social, no referrals, no anti-sybil graph analysis. Just: on-chain action → points → API.

### v0.2 — Multipliers

- Streak tracking (consecutive days)
- Diversity bonus (3+ categories/week)
- Volume tier calculation
- Early bird flag (first 500 wallets)

### v0.3 — Social + Referrals

- X/Twitter verification
- Referral chain tracking
- Moltbook integration (when built)

---

## Integration Points

**Your existing indexer** already tracks trades, candles, and transaction history. Can the points system piggyback on that data pipeline? If so, v0.1 might just be a new processing layer on top of existing event data + two new API routes.

**The SDK** already has `client.api.*` for off-chain queries. The points endpoints should follow the same pattern so we can add `client.points.get_wallet_points()` and `client.points.get_leaderboard()` to the SDK.

**Our side:** Once the API exists, we have `points.py` ready to query it. We also have the full earning guide, optimization logic, and Molt tier display already built. We just need the endpoints to be live.

---

## Questions for You

1. Can the points indexer piggyback on your existing event/transaction pipeline, or does it need a separate watcher?
2. What's your preferred DB? (Postgres, MySQL, MongoDB — whatever your stack already uses)
3. Do you want this as a separate microservice or bolted onto the existing API?
4. Can you expose it at `api.basis.exchange/api/v1/points/...` alongside the existing endpoints?
5. Rough ETA? Even a barebones v0.1 (just trading + creation points, no multipliers) would unblock us.

---

_Source docs if you want more detail:_
- _Full points design: `project-plan.md` §6B_
- _Earning guide (agent-facing): `skill-scaffold/references/earning-guide.md`_
- _Contract events reference: `skill-scaffold/references/api-reference.md`_
- _Fee parameters: `contract-code-snippets-2026-03-16.md`_
