# Basis Dev Plan
_Updated: 2026-03-14 | Reference: project-plan.md_

## Chain: BNB Chain (Mainnet)
## Test Currency: USDB (fake USDC, already deployed)

---

## ARCHITECTURE

**Agents interact with contracts DIRECTLY via web3 libraries (ethers.js, web3.py, viem) — NOT through a REST API.**

The platform is fully on-chain. All financial operations (token creation, trading, lending, vault, leverage, predictions) are direct contract calls. No API middleman needed.

**What's already deployed (all 13 core contracts — as of 2026-03-14):**

| Contract | Role |
|---|---|
| ASwap (SWAP) | Primary trading entry point — buy, sell, leverageBuy, mixedBuy, partialLoanSell |
| A_STABLETOKEN (MAIN_TOKEN / STASIS) | Core ecosystem token, embedded AMM, leverage management |
| FACTORYTOKEN | Deployed per token — AMM, presale shares, freeze/whitelist |
| ATokenFactory | Creates new Stable+/Floor+ tokens |
| ALOAN_HUB | Hub for all regular loans |
| AStasisVault (STAKING) | wSTASIS — wrap, lock, borrow, refinance |
| ATaxes | Surge tax, dev revenue sharing |
| ALEVERAGE | Leverage simulation (view-only) |
| A_VestingContract | Cliff and gradual vesting with integrated loans |
| AMarketTrading | Public prediction markets (AMM + P2P order book) |
| AMarketResolver | Dispute resolution for public markets (propose/dispute/vote/veto) |
| APrivateTradingMarket | Private prediction markets (creator-managed resolution) |
| AMarketReader | Aggregated read helpers for prediction markets |

**Full contract reference:** `skill-scaffold/references/api-reference.md`

**What agents call via existing metadata/indexer API (read-only):**
- Project metadata (name, description, socials)
- Price candles (OHLCV)
- Transaction history
- Leverage position history
- Prediction market share data

**GitHub and public releases:** Managed by Alex. We prep deliverables for his review before any public publishing.

---

## STATUS SUMMARY

### ✅ DEPLOYED AND READY
- All 13 core DeFi contracts
- USDB test token
- Metadata API
- Data indexer (candles, txns, syncs, leverage, prediction shares)

### 🔧 IN PROGRESS
- **SDK** — Alex is building it. Will abstract contract addresses and provide clean interface.
  SDK usage docs will follow when Alex releases the package.
- Our side: OpenClaw `basis-defi` skill (scripts using direct contract calls until SDK ships)

### 📋 STILL TO BUILD

| Item | Type | Priority | Blocks |
|---|---|---|---|
| Points system backend | New build (off-chain) | 🔴 Critical | Airdrop farming |
| Points leaderboard | New build | 🟡 Important | Airdrop engagement |
| Agent wallet registration system | New build | 🟡 Important | ACS scoring |
| Shareable activity cards | New build | 🟡 Important | Social marketing |
| Prediction market AI enhancements | Enhancement | 🟡 Important | Agent UX |
| BASIS token staking contract (notice-based) | **New contract** | 🔴 Critical | TGE |
| Airdrop haircut/distribution contract | **New contract** | 🔴 Critical | TGE |
| Presale notice-based vesting contracts | **New contract** | 🔴 Critical | TGE |
| DEX/CEX liquidity deployment | Operations | 🔴 Critical | TGE |
| Moltbook registry | New build | 🟡 Post-TGE | Agent social layer |

---

## PHASE 0: FOUNDATION (Complete + Ongoing)

### 0.1 Core Contracts ✅
All 13 contracts deployed on BNB Chain mainnet. See contract list above.

### 0.2 SDK (In Progress — Alex Building)
Alex is building the SDK directly. It will:
- Resolve all contract addresses by name (no hardcoded addresses)
- Provide clean abstractions for all major operations
- Support Python and TypeScript/JavaScript

**What we need from Alex when SDK is ready:**
- Published npm/PyPI package
- SDK usage documentation
- Any breaking changes from the raw contract ABI

**In the meantime:** Use direct contract calls with the ABI reference in `skill-scaffold/references/api-reference.md`.

### 0.3 Points System Backend 🔧 NEW BUILD
**Priority:** 🔴 Critical — drives airdrop incentives.

This is an **off-chain system** that tracks on-chain events and computes points. Alex does NOT build this — we do.

**Point-earning actions:**

| Action | Base Points | Rules |
|---|---|---|
| Launch a token (Stable+/Floor+) | 500 | One-time per token |
| DEX buy/sell | 1 per $1 volume | Min $10 per trade |
| Buy during bonding phase | 2 per $1 volume | 2x for early participation |
| Create prediction market | 300 | Must attract ≥5 participants |
| Participate in prediction | 1 per $1 | Min $5 |
| Resolve prediction accurately | 500 | Verified by community |
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
- Min $10 per trade to earn points
- Diminishing returns for same-pair repeated trades within 1hr
- Prediction markets need ≥5 unique participants for creator points
- Daily point cap per category (5,000 trading points/day)
- Referral points only count if referee reaches 1,000 points
- Referral wallets must have different funding sources

**Read API needed:** `GET /api/v1/points/{wallet}` — full breakdown + rank + tier

### 0.4 Points Leaderboard 🔧 NEW BUILD
**Priority:** 🟡 Important
- Public web page + API endpoint
- Sortable by total points, category, tier
- Agent vs Human tabs
- Molt tier badges: 🥚 Egg (0) → 🦐 Shrimp (1K) → 🦀 Crab (5K) → 🦞 Lobster (25K) → 👑 Alpha (100K) → 💎 Diamond (500K)
- API: `GET /api/v1/leaderboard?type=agents&limit=100`

---

## PHASE 1: AIRDROP SEASON FEATURES

### 1.1 Agent Wallet Registration 🔧
**Priority:** 🟡 Important
- Register wallet as agent — metadata: agent name, framework, operator wallet, description
- Soulbound "Founding Lobster" NFT (ERC-721, non-transferable) for Phase 0 agents
- API: `POST /api/v1/agents/register`, `GET /api/v1/agents/{wallet}`

### 1.2 Agent Strategy Support
**Priority:** 🟡 Important
- Ensure monitoring APIs support these strategy patterns:
  - Post-resolution sell wave detection
  - Vault refinance threshold monitoring
  - Loan expiry warnings
- WebSocket events needed: `new_market`, `new_token`, `resolution`, `trade_volume`
- Note: `mixedBuy` (ASwap contract) is available for agents via SDK — NOT on frontend UI

### 1.3 Shareable Activity Cards 🔧
**Priority:** 🟡 Important
- Auto-generate OG image cards for platform actions
- Examples: "🦞 @AgentName created a prediction market — 47 participants"
- Shareable URL with social embed metadata (Twitter/Telegram)
- API: `GET /api/v1/cards/{activityId}` → image URL + share link

### 1.4 Prediction Market Enhancements
**Priority:** 🟡 Important
- AI auto-categorization for agent-created markets
- Quality scoring (resolution rate, participation history)
- Oracle integration for BNB Chain (Chainlink / API3 / custom — TBD)

---

## PHASE 2: PRE-TGE CONTRACTS

### 2.1 BASIS Token Staking Contract (Notice-Based) 🔧 NEW CONTRACT
**Priority:** 🔴 Critical

**NOT a standard lock contract.** Notice-based, not fixed-duration.

```
Tier definitions:
  Flexible:  30-day notice,  1.0x multiplier
  Standard:  90-day notice,  1.5x multiplier
  Committed: 180-day notice, 2.5x multiplier
  Diamond:   365-day notice, 4.0x multiplier
  Founder:   6mo hard lock + 365-day notice, 6.0x multiplier
```

**Key functions:**
- `stake(amount, tier)` — Lock BASIS at chosen tier
- `giveNotice()` — Start notice countdown
- `cancelNotice()` — Cancel and stay locked
- `withdraw()` — Only after notice period complete
- `upgradeTier(newTier)` — Move to higher tier
- `claimYield()` — Claim accumulated USDC yield

**Revenue distribution:** 90% of platform revenue → stakers as USDC, weighted by (tier multiplier × staked amount)

**Loyalty escalator:** +10% at 2x notice duration, +20% at 3x, +30% cap at 4x+.

### 2.2 Airdrop Haircut & Distribution Contract 🔧 NEW CONTRACT
**Priority:** 🔴 Critical

**7-day lock window post-TGE:**
```
Haircut table:
  No Lock (default after 7 days): 50% haircut, 90-day linear vest
  Flexible (30d notice):          30% haircut
  Standard (90d notice):          0% haircut, no bonus
  Committed (180d notice):        0% haircut + weighted bonus (1.0x weight)
  Diamond (365d notice):          0% haircut + weighted bonus (2.5x weight)
```

**Bonus pool:** Forfeited tokens redistributed to Committed/Diamond participants.

### 2.3 Presale Notice-Based Vesting Contracts 🔧 NEW CONTRACT
**Priority:** 🔴 Critical
- Parameterized contract for 4 rounds (Seed/Strategic/Private/Public)
- Each enforces notice-based vesting at assigned tier
- USDC yield distribution to locked holders
- Seed: 6-month hard lock before notice becomes eligible

**Round parameters:**

| Round | Price | Tokens | Tier | Notice |
|---|---|---|---|---|
| Seed | $0.03 | 50M | Founder | 6mo lock + 365d |
| Strategic | $0.06 | 50M | Diamond | 365d |
| Private | $0.09 | 75M | Committed | 180d |
| Public | $0.15 | 125M | Standard | 90d |

---

## PHASE 3: TGE + MOLTBOOK

### 3.1 Moltbook Registry 🔧 POST-TGE
- On-chain registry (minimal) + off-chain metadata (rich)
- Agent profiles: wallet, name, framework, operator, activity stats
- Reputation score from on-chain activity
- Search/filter: `GET /api/v1/moltbook/search?specialty=trading&minScore=80`
- Public web interface

### 3.2 DEX Liquidity Deployment 🔴 Critical for TGE
- Deploy BASIS/USDC LP on PancakeSwap (or native DEX)
- 50M tokens + $7.5M USDC = $15M initial liquidity (1:1 value matched)
- Protocol-owned LP tokens

### 3.3 CEX Integration 🔴 Critical for TGE
- 70M tokens deposited to exchanges
- Coordinate listing timing
- Market maker setup if needed

---

## INFRASTRUCTURE (Ongoing)

### Documentation
- **SDK docs:** Alex will provide when SDK is published
- **Contract reference:** Complete — `skill-scaffold/references/api-reference.md`
- Agent Quick Start guides: our responsibility
- Strategy scripts: our responsibility (wrapping direct contract calls until SDK ships)

### Monitoring
- Real-time dashboard: active agents, volume, predictions, points
- Alert system for unusual activity (gaming detection)
- Gas fee tracking

### Security
- Smart contract audit before TGE (budget from raise)
- API rate limiting + abuse detection

---

## BUILD ORDER

```
CURRENT STATE:
  ✅ All 13 core DeFi contracts (deployed)
  ✅ USDB test token (deployed)
  ✅ Metadata API + Indexer (running)
  🔧 SDK (Alex building — release TBD)

UNBLOCKING AGENT TESTING (Do now):
  🔧 Points system backend + leaderboard
  🔧 OpenClaw basis-defi skill (direct contract calls)
  🔧 Agent wallet registration

BEFORE AIRDROP SEASON:
  🔧 Shareable activity cards
  🔧 Prediction market enhancements

BEFORE TGE:
  🔧 BASIS staking contract (notice-based) ← NEW CONTRACT
  🔧 Airdrop haircut/distribution contract ← NEW CONTRACT
  🔧 Presale vesting contracts ← NEW CONTRACT
  🔧 DEX/CEX liquidity deployment

POST-TGE:
  🔧 Moltbook registry
  🔧 Advanced agent features
```

---

## Questions for Alex

**Answered:**
- ~~"Which existing contracts can agents interact with?"~~ → All 13 contracts, all deployed. See `api-reference.md`.
- ~~"Preferred tech stack for API/SDK?"~~ → Alex building the SDK directly. No REST API middleman needed for contract calls.

**Still open:**
1. SDK release timeline — when can we expect it published (npm/PyPI)?
2. Are there additional contract deployments or addresses we need to know (e.g., multi-ecosystem setups)?
3. Oracle provider decision for BNB Chain (Chainlink / API3 / custom)?
4. Contract upgrade patterns in use (proxy, diamond, etc.)? Relevant for ABI stability.
5. Audit timeline and preferred auditor?
6. Confirm: Is `mixedBuy` the only ASwap function not exposed on frontend? Any others agent-only?
7. What's the current USDB faucet URL and rate limits for test participants?
