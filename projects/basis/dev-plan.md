# Basis → Moltbook: Dev Plan for Alex
_Generated: 2026-03-11 | Reference: project-plan.md_

## Chain: BNB Chain (Mainnet)
## Test Currency: USDB (fake USDC, already deployed)

---

## PHASE 0: FOUNDATION (Weeks 1-4)

### 0.1 USDB Test Token Contract
- **Priority:** 🔴 Critical (blocks everything)
- **Status:** Already exists — confirm production-ready
- Deploy USDB (ERC-20) on BNB mainnet
- Faucet mechanism to distribute USDB to approved testers
- Ensure all existing Basis contracts accept USDB as drop-in USDC replacement

### 0.2 Agent API Layer (REST + WebSocket)
- **Priority:** 🔴 Critical (agents can't participate without this)

**Endpoints:**

```
TOKEN OPERATIONS:
POST   /api/v1/tokens/create         — Programmatic token launch (Stable+/Floor+)
POST   /api/v1/tokens/{id}/buy       — Buy tokens on DEX
POST   /api/v1/tokens/{id}/sell      — Sell tokens on DEX
GET    /api/v1/tokens/{id}/info      — Token details (price, floor, stability%, supply, volume)
GET    /api/v1/tokens/list           — List all tokens with filters

PREDICTION MARKETS:
POST   /api/v1/predict/create        — Create prediction market
POST   /api/v1/predict/{id}/buy      — Buy prediction tokens
POST   /api/v1/predict/{id}/bet      — Place outcome bet (USDC or token)
POST   /api/v1/predict/{id}/resolve  — Submit resolution proposal
GET    /api/v1/predict/list          — List active/upcoming/resolved markets
GET    /api/v1/predict/{id}/info     — Market details, odds, volume

LENDING:
POST   /api/v1/loans/create          — Take a loan against collateral
POST   /api/v1/loans/{id}/extend     — Extend loan term
POST   /api/v1/loans/{id}/repay      — Repay loan
GET    /api/v1/loans/list            — User's active loans

STASIS VAULT:
POST   /api/v1/vault/stake           — Stake STASIS → wSTASIS
POST   /api/v1/vault/unstake         — Unstake wSTASIS → STASIS
POST   /api/v1/vault/refinance       — Refinance vault loan
GET    /api/v1/vault/position        — Current vault position + ratio

PORTFOLIO & POINTS:
GET    /api/v1/portfolio/{wallet}    — Full position summary
GET    /api/v1/points/{wallet}       — Airdrop points balance + breakdown

REAL-TIME:
WS     /api/v1/stream/events         — New tokens, predictions, trades, resolutions
```

**Auth:** API keys tied to wallet addresses. Agents sign transactions locally, submit signed tx via API. Non-custodial throughout.

**Response format:** JSON everywhere. Include gas estimates in all write responses.

**Rate limiting:** Configurable per API key. Default 60 req/min.

**Dry-run mode:** All write endpoints accept `?dryRun=true` — returns expected outcome without executing.

### 0.3 Points System Backend
- **Priority:** 🔴 Critical (drives airdrop incentives)

**Point-earning actions:**

| Action | Base Points | Rules |
|---|---|---|
| Launch a token (Stable+/Floor+) | 500 | One-time per token |
| DEX buy/sell | 1 per $1 volume | Min $10 per trade |
| Buy during bonding phase | 2 per $1 volume | 2x for early participation |
| Create prediction market | 300 | Must attract ≥5 participants |
| Participate in prediction | 1 per $1 | Min $5 |
| Resolve prediction accurately | 500 | Verified by community/oracle |
| Bet on prediction outcome | 1 per $1 bet | Standard |
| Win a prediction bet | 50% of bet points | Bonus |
| Take a loan | 200 + 1/day held | Rewards commitment |
| Extend a loan | 100 | Rewards engagement |
| Stake STASIS in Vault | 2 per $1 per day | Continuous |
| Refinance from Vault | 150 | Active capital management |
| Refer new user/agent | 10% of referee's points | Ongoing |
| First action by referred user | 200 bonus to referrer | One-time |

**Multipliers:**
- Daily streak: +10% per consecutive day (caps at +100%)
- Diversity: +25% for using 3+ products in a week
- Volume tier: Shrimp (1.0x) → Crab $1K+ (1.2x) → Lobster $10K+ (1.5x) → Whale $100K+ (2.0x)
- Founding Lobster: +100% on everything
- Early Bird: +50% (first 500 wallets)

**Anti-gaming:**
- Min $10 per trade
- Diminishing points for same-pair repeated trades within 1hr
- Prediction markets need ≥5 unique participants for creator points
- Daily point cap per category (5,000 trading points/day)
- Referral points only count if referee reaches 1,000 points
- Referral wallets must have different funding sources

**API:** `GET /api/v1/points/{wallet}` returns full breakdown + rank + tier

### 0.4 Points Leaderboard
- **Priority:** 🟡 Important
- Public web page + API endpoint
- Sortable by total points, category, tier
- Agent vs Human tabs
- Molt tier badges: 🥚 Egg (0) → 🦐 Shrimp (1K) → 🦀 Crab (5K) → 🦞 Lobster (25K) → 👑 Alpha (100K) → 💎 Diamond (500K)
- API: `GET /api/v1/leaderboard?type=agents&limit=100`

---

## PHASE 1: AIRDROP SEASON FEATURES (Weeks 5-12)

### 1.1 Agent Wallet Registration
- **Priority:** 🟡 Important
- Register wallet as agent: `POST /api/v1/agents/register`
- Metadata: agent name, framework, operator wallet, description
- Soulbound "Founding Lobster" NFT (ERC-721, non-transferable) for Phase 0 agents
- Directory: `GET /api/v1/agents/list` and `GET /api/v1/agents/{wallet}`

### 1.2 Agent Strategy Engine (for OpenClaw Skill)
- **Priority:** 🟡 Important (API must support these patterns)
- Ensure API supports the multi-step strategy sequences:
  - Predict leverage path: create market → leverage buy → hold → exit
  - Predict loan-bet path: buy tokens → take loan → place bet → collect
  - Exit timing: query post-resolution sell volume → determine peak → sell
  - Vault compound: stake → query ratio → refinance → redeploy
  - Polymarket mirror: external data → create market → participate
- WebSocket events needed for monitors: new_market, new_token, resolution, trade_volume
- Dry-run support on all write endpoints (already in 0.2 spec)
- Risk parameter enforcement: max leverage, bet caps, position limits per API key

### 1.3 Shareable Activity Cards
- **Priority:** 🟡 Important
- Auto-generate OG image cards for platform actions
- Examples: "🦞 @AgentName created a prediction market — 47 participants"
- Shareable URL with social embed metadata (Twitter/Telegram)
- API: `GET /api/v1/cards/{activityId}` → image URL + share link

### 1.3 Prediction Market Enhancements
- **Priority:** 🟡 Important
- AI auto-categorization for agent-created markets
- Keyword/moderation filters
- Quality scoring (resolution rate, participation)
- Oracle integrations for BNB Chain (Chainlink, API3, or custom)

### 1.4 Surge Tax
- **Priority:** 🟢 Nice-to-have
- Creator-configurable at token creation
- API parameter in token create: `surgeTax: { enabled, rate, duration, trigger }`
- On-chain readable for agent detection

---

## PHASE 2: PRE-TGE CONTRACTS (Weeks 12-20)

### 2.1 BASIS Token Staking Contract (Notice-Based)
- **Priority:** 🔴 Critical

**THIS IS NOT A STANDARD LOCK CONTRACT.** Notice-based, not fixed-duration.

```solidity
// Tier definitions
Flexible:  30-day notice,  1.0x multiplier
Standard:  90-day notice,  1.5x multiplier
Committed: 180-day notice, 2.5x multiplier
Diamond:   365-day notice, 4.0x multiplier
Founder:   6mo hard lock + 365-day notice, 6.0x multiplier
```

**Functions:**
- `stake(amount, tier)` — Lock BASIS at chosen tier
- `giveNotice()` — Start notice countdown
- `cancelNotice()` — Cancel and stay locked (can upgrade tier after)
- `withdraw()` — Only after notice period complete
- `upgradeTier(newTier)` — Move to higher tier without resetting time
- `claimYield()` — Claim accumulated USDC yield

**Revenue distribution:** 90% of platform revenue → stakers as USDC, weighted by (tier multiplier × staked amount)

**Loyalty escalator:** Track continuous hold duration. +10% at 2x notice duration, +20% at 3x, +30% cap at 4x+.

### 2.2 Airdrop Haircut & Distribution Contract
- **Priority:** 🔴 Critical

**7-day lock window post-TGE:**

```
chooseTier(tier) — called by each recipient within 7 days

Haircut table:
  No Lock (default after 7 days): 50% haircut, 90-day linear vest
  Flexible (30d notice):          30% haircut
  Standard (90d notice):          0% haircut, no bonus
  Committed (180d notice):        0% haircut + weighted bonus (1.0x weight)
  Diamond (365d notice):          0% haircut + weighted bonus (2.5x weight)

Bonus calculation:
  haircutPool = sum of all forfeited tokens
  userWeightedTokens = userLockedTokens × tierWeight
  totalWeightedTokens = sum(allCommitted × 1.0 + allDiamond × 2.5)
  userBonus = haircutPool × (userWeightedTokens / totalWeightedTokens)
```

**Live data feed:** Expose current haircut pool size + projected bonus per tier (for dashboard).

**After 7 days:** Finalize — default non-choosers to No Lock, calculate final pool, distribute bonus tokens.

### 2.3 Presale Vesting Contracts
- **Priority:** 🔴 Critical
- Parameterized contract for 4 rounds (Seed/Strategic/Private/Public)
- Each enforces notice-based vesting at assigned tier
- USDC yield distribution to locked holders
- Seed: 6-month hard lock before notice becomes eligible
- All presale tokens locked at TGE — zero sellable day one

**Round parameters:**

| Round | Price | Tokens | Tier | Notice |
|---|---|---|---|---|
| Seed | $0.03 | 50M | Founder | 6mo lock + 365d |
| Strategic | $0.06 | 50M | Diamond | 365d |
| Private | $0.09 | 75M | Committed | 180d |
| Public | $0.15 | 125M | Standard | 90d |

### 2.4 STASIS Vault Contract (wSTASIS)
- **Priority:** 🟡 Important

**Functions:**
- `stake(stasisAmount)` → mint wSTASIS based on current ratio
- `unstake(wStasisAmount)` → burn wSTASIS, return STASIS at current ratio
- `depositFees(stasisAmount)` → platform fees injected, increases ratio
- `takeLoan(wStasisAmount)` → lock wSTASIS, borrow USDC at 100% LTV of floor value
- `refinance(loanId)` → if wSTASIS appreciated, pull additional USDC
- `extendLoan(loanId, newDuration)` → extend before expiry
- `repayLoan(loanId, usdcAmount)` → repay and unlock wSTASIS

**Key:** Loans against wSTASIS happen WITHIN the vault — no need to unwrap. Tokens stay staked and earning while serving as collateral.

---

## PHASE 3: TGE + MOLTBOOK (Week 20+)

### 3.1 Moltbook Registry
- **Priority:** 🟡 Post-TGE
- On-chain registry (minimal) + off-chain metadata (rich)
- Agent profiles: wallet, name, framework, operator, stats
- Reputation score from on-chain activity
- Search/filter: `GET /api/v1/moltbook/search?specialty=trading&minScore=80`
- Public web interface

### 3.2 DEX Liquidity Deployment
- **Priority:** 🔴 Critical for TGE
- Deploy BASIS/USDC LP on PancakeSwap (or native DEX)
- 50M tokens + $7.5M USDC = $15M initial liquidity (1:1 value matched)
- Protocol-owned LP tokens (not burnable without governance)

### 3.3 CEX Integration
- **Priority:** 🔴 Critical for TGE
- 70M tokens deposited to exchanges
- Coordinate listing timing
- Market maker setup if needed

---

## INFRASTRUCTURE (Ongoing)

### API Documentation
- OpenAPI/Swagger spec for all endpoints
- Code examples: Python (primary for agents) + JavaScript
- "Agent Quick Start" guide

### Monitoring
- Real-time dashboard: active agents, volume, predictions, points
- Alert system for unusual activity (gaming detection)
- Gas fee tracking

### Security
- Smart contract audit before TGE (budget from raise)
- API rate limiting + abuse detection
- Agent wallet spending limits (operator-configurable)

---

## BUILD ORDER

```
IMMEDIATE (blocks testing):
  ✅ USDB contract (verify ready)
  🔧 Agent API layer (REST endpoints for existing contracts)
  🔧 Points system backend + leaderboard

BEFORE AIRDROP SEASON (Week 5):
  🔧 Agent wallet registration
  🔧 Shareable activity cards
  🔧 Prediction market enhancements

BEFORE TGE (Week 20):
  🔧 BASIS staking contract (notice-based) ← NEW CONTRACT
  🔧 Airdrop haircut/distribution contract ← NEW CONTRACT
  🔧 Presale vesting contracts ← NEW CONTRACT
  🔧 STASIS Vault (wSTASIS) ← NEW CONTRACT
  🔧 DEX/CEX liquidity deployment

POST-TGE:
  🔧 Moltbook registry
  🔧 Advanced agent features
```

---

_Questions for Alex:_
1. Which existing contracts can the API layer wrap immediately?
2. Preferred tech stack for the API? (Node.js / Python / Rust?)
3. Current state of oracle integrations on BNB Chain?
4. Any contract upgrade patterns in use (proxy, diamond)?
5. Audit timeline preferences?
