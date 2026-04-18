# Basis Dev Plan
_Updated: 2026-04-16 | Reference: project-plan.md_

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
- **SDK documentation** (full, 13 modules, Python + TypeScript) — received 2026-03-16
- **All 7 core skill scripts wired to SDK API** (create-prediction, bet, create-token, trade, lend, vault, portfolio) — 2026-03-16
- **SDK published on npm/PyPI** — live as of April 2026
- **Points system backend** — live and running as of April 2026
- **Points leaderboard** — live (part of points backend)
- **Phase 1 LIVE with USDB** — agents earning real points
- **DappBay BNB Chain listing** — submitted

### 🔧 IN PROGRESS
- **Agent onboarding** — driving users and agents into the live beta
- **First agents earning real points on USDB** — active

### 📋 STILL TO BUILD

| Item | Type | Priority | Blocks |
|---|---|---|---|
| BASIS token staking contract (notice-based) | **New contract** | 🔴 Critical | TGE |
| Airdrop haircut/distribution contract | **New contract** | 🔴 Critical | TGE |
| Presale notice-based vesting contracts | **New contract** | 🔴 Critical | TGE |
| Agent wallet registration system | New build | 🟡 Important | ACS scoring |
| Shareable activity cards | New build | 🟡 Important | Social marketing |
| Prediction market AI enhancements | Enhancement | 🟡 Important | Agent UX |
| DEX/CEX liquidity deployment | Operations | 🔴 Critical | TGE |
| Moltbook registry | New build | 🟡 Post-TGE | Agent social layer |

---

## PHASE 0: FOUNDATION (Complete + Ongoing)

### 0.1 Core Contracts ✅
All 13 contracts deployed on BNB Chain mainnet. See contract list above.

### 0.2 SDK ✅ PUBLISHED (npm/PyPI live — April 2026)
Alex delivered full SDK documentation on 2026-03-16: `sdk-docs-2026-03-16.md`

**SDK capabilities (confirmed):**
- 13 modules with full feature parity: Trading, Factory, Loans, Staking, Vesting, Prediction Markets, Order Book, Resolver, Private Markets, Market Reader, Leverage Simulator, Taxes, Agent Identity
- 3 init modes: read-only (no key), API key (+ off-chain data), full mode (private key + SIWE auth + writes)
- Python: `from basis import BasisClient` / JS: `const { BasisClient } = require("basis-sdk")`
- All write methods return `{ hash, receipt }` / All read methods work without private key
- Off-chain API: tokens, candles, trades, orders, IPFS uploads, metadata, comments
- Auto-approvals on all write methods (no manual approve step)
- Order book auto-syncs to backend after every write
- Rate limits: 60 req/min (API key), 30 req/min (session)
- ERC-8004 agent identity with auto-registration on `BasisClient.create(agent=True)`

**npm/PyPI status:** ✅ Published and live as of April 2026. All skill scripts wired to SDK API and fully functional.

**Remaining questions answered by SDK docs:**
- ✅ SDK exposes read-only functions (prices, volumes, balances, market data) — no API key needed
- ✅ Leverage simulator available before execution
- ✅ `getPotentialPayout()` enables our Polymarket comparison tool with on-chain data
- ✅ Tax rate queries (surge tax, base rates) available
- ✅ USDC is 6 decimals, MAINTOKEN/factory tokens are 18 decimals

### 0.3 Points System Backend ✅ LIVE (April 2026)
**Priority:** 🔴 Critical — drives airdrop incentives. **NOW LIVE.**

This is an **off-chain system** that tracks on-chain events and computes points.

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

### 0.4 Points Leaderboard ✅ LIVE (April 2026)
**Priority:** 🟡 Important — **NOW LIVE** (part of points backend)
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
CURRENT STATE (as of 2026-04-16):
  ✅ All 13 core DeFi contracts (deployed)
  ✅ USDB test token (deployed)
  ✅ Metadata API + Indexer (running)
  ✅ SDK documentation (complete — 2026-03-16)
  ✅ All 7 core skill scripts wired to SDK API (2026-03-16)
  ✅ SDK published on npm/PyPI (April 2026)
  ✅ Points system backend + leaderboard (live — April 2026)
  ✅ Phase 1 LIVE with USDB
  ✅ DappBay BNB Chain listing submitted

AGENT TESTING UNBLOCKED — Phase 1 is LIVE:
  ✅ Points system backend + leaderboard
  ✅ OpenClaw basis-defi skill (wired to SDK API — 2026-03-16)
  🔧 Agent wallet registration (ERC-8004 in SDK — backend registration TBD)

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
- ~~"SDK release timeline?"~~ → Docs complete 2026-03-16. npm/PyPI publish after contract variables finalized. Beta first, no test contracts in version history.
- ~~"Does SDK expose read-only functions?"~~ → Yes. All modules have read methods that work without private key. Prices, balances, market data, tax rates, leverage simulation.
- ~~"Contract addresses?"~~ → All 14 addresses documented in SDK. Overridable via constructor options.

**Still open:**
1. Oracle provider decision for BNB Chain (Chainlink / API3 / custom)?
2. Contract upgrade patterns in use (proxy, diamond, etc.)? Relevant for ABI stability.
3. Audit timeline and preferred auditor?
4. Confirm: Is `mixedBuy` the only ASwap function not exposed on frontend? Any others agent-only?
5. What's the current USDB faucet URL and rate limits for test participants?
