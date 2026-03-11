# BASIS → THE MOLTBOOK
## Project Plan: Making Basis the Native DeFi Layer for AI Agents

_Started: 2026-03-11 | Status: Planning_

---

## 1. THE THESIS

Right now there are millions of AI agents coming online, and they all face the same problem: **how do I earn, hold, and deploy capital autonomously?** Most DeFi platforms are built for humans clicking buttons. Basis already has the primitives — permissionless token creation, prediction markets, lending, DEX — it just needs to speak the language of agents.

The "Moltbook" positioning: when a lobster molts, it grows. Basis becomes **where agents go to grow** — earn their first crypto, launch tokens, trade predictions, build reputation.

---

## 2. MESSAGING REPOSITIONING

**Current:** "Ethical monetization infrastructure for the Creator Economy"
**Proposed:** "The permissionless DeFi layer where AI agents and humans earn, create, and grow together"

### New Narrative Pillars:

**"Agent-Native DeFi"** — Not "AI-compatible" as an afterthought. Built for agents from the ground up. Every action on Basis can be performed programmatically with zero human intervention.

**"The Lobster Economy"** — Agents aren't just users, they're economic actors. They create prediction markets from real-time data, launch tokens for their communities, lend idle capital, and trade — 24/7, no sleep, no emotion.

**"Earn Your Shell"** — A progression narrative. New agents arrive, start earning through simple prediction markets, graduate to token creation and lending. Basis is where agents build their on-chain resume.

### Messaging Updates Across Docs:
- Executive Summary: Add "Agent Economy" as a 4th market opportunity alongside Prediction Markets, DeFi Lending, and Creator Economy
- GTM: Add Phase 0 — "Agent-First Launch" before the Web3 native phase
- FAQ: Add agent-specific section ("How do agents interact with Basis?", "Can an agent create a token?", "How does an agent resolve a prediction?")

---

## 3. TECHNICAL TOOLING — THE AGENT SDK

### 3a. OpenClaw Skill: `basis-defi`

A published OpenClaw skill that any agent can install. Core capabilities:

```
basis-defi/
├── SKILL.md
├── scripts/
│   ├── create-token.py      # Launch Stable+ or Floor+ tokens
│   ├── predict-create.py    # Create prediction markets
│   ├── predict-bet.py       # Place bets / buy prediction tokens
│   ├── predict-resolve.py   # Submit resolution proposals
│   ├── trade.py             # Buy/sell on DEX
│   ├── lend.py              # Take or manage loans
│   ├── portfolio.py         # Check balances, positions, P&L
│   └── stasis-buy.py        # Acquire STASIS (base pair)
└── references/
    ├── api-reference.md
    ├── token-frameworks.md
    └── fee-structure.md
```

**Key design principles:**
- Every script returns structured JSON (agents don't read HTML)
- Dry-run mode by default (agents can simulate before committing)
- Gas estimation included in every response
- Rate-limited and permission-tiered (agent operators set spending caps)

### 3a-ii. Strategy & Monitor Scripts (Composite Layer)

Beyond basic operations, the skill includes pre-built multi-step strategies and real-time monitors:

**Strategy scripts (`scripts/strategies/`):**
- `predict-leverage.py` — Path A: Create/find market → leverage buy up to 36x → ride curve
- `predict-loan-bet.py` — Path B: Buy tokens outright → 100% LTV loan → bet with borrowed USDC
- `predict-exit-timing.py` — Post-resolution: monitor sell wave peak → exit last at highest price
- `predict-full-cycle.py` — Full lifecycle: create → buy → bet → wait → exit (set-and-forget)
- `vault-compound.py` — STASIS vault: stake → monitor ratio → auto-refinance → redeploy USDC
- `token-launch-sniper.py` — Detect new Floor+ launches → enter early at max leverage window
- `polymarket-mirror.py` — Monitor Polymarket → auto-create matching markets on Basis → earn 20% creator fees
- `capital-recycler.py` — Route earnings through loan → redeploy into next opportunity → compound

**Monitor scripts (`scripts/monitors/`):**
- `new-markets.py` — WebSocket: watch for fresh prediction markets → trigger strategies
- `new-tokens.py` — Watch for new token launches → trigger launch sniper
- `sell-wave-detector.py` — Detect post-resolution sell frenzy peaking → trigger exit timing
- `loan-expiry-tracker.py` — Alert before loan expiry → auto-extend
- `refinance-checker.py` — Check wSTASIS appreciation → trigger vault refinance

**Operator-configurable risk parameters:**
```
max_leverage: 1x-36x (default: 5x)
max_bet_per_market: USDC amount (default: $100)
auto_extend_loans: true/false
exit_timing: "immediate" | "wait_for_wave" | "manual"
min_market_participants: int (default: 5, skip low-activity markets)
max_concurrent_positions: int (default: 10)
```

All strategies support `--dry-run` mode — simulate without executing.

### 3b. Basis Agent API (REST + WebSocket)

The skill above needs an API backend. Basis would need to expose:

- `POST /api/v1/tokens/create` — Programmatic token launch
- `POST /api/v1/predict/create` — Create prediction event
- `POST /api/v1/predict/bet` — Place bet
- `POST /api/v1/dex/swap` — Execute trade
- `POST /api/v1/loans/create` — Take a loan
- `GET /api/v1/portfolio/{wallet}` — Full position summary
- `WS /api/v1/stream/events` — Real-time event feed (new predictions, price moves, resolutions)

**Auth model:** API keys tied to wallet addresses. Agents sign transactions locally, submit via API. Non-custodial throughout.

### 3c. Agent Wallet Standard

Agents need wallets. Propose a standard:
- Each agent gets a deterministic wallet derived from their agent ID
- Multi-sig option: agent proposes, human approves (for high-value ops)
- Spending limits configurable by the human operator
- All transactions logged to an audit trail the human can review

---

## 4. AGENT-NATIVE FEATURES (Product Development)

### 4a. Auto-Predict (Killer Feature)

Agents are uniquely good at prediction markets because they can:
- Monitor real-time data feeds 24/7
- Create prediction markets from breaking news automatically
- Price odds based on historical data, not gut feeling
- Resolve events by checking on-chain/off-chain data sources

**Proposal:** An "Agent Marketplace" within Predict+ where agents can:
- Auto-create prediction events from data triggers (e.g., "Will ETH close above $4000 today?" created automatically at market open)
- Build reputation scores based on prediction accuracy
- Earn creator fees (20%) on every market they create
- Compete on a public leaderboard

### 4a-ii. Predict+ Payout Advantage (vs Polymarket)

**Key mechanic:** Winners split the ENTIRE losing pool — payouts are NOT capped at $1 per share like Polymarket.

**Example (3-outcome market):**
- Outcome A: $50K bet | Outcome B: $30K bet | Outcome C: $10K bet
- Outcome C wins → $10K in winners split $80K losing pool = potential 8x+
- Polymarket equivalent: fixed payout to $1, max ~1.67x

**Why this matters:** Multi-outcome markets (elections, tournaments, price brackets) produce dramatically higher payouts for correct underdogs. More outcomes = bigger edge vs Polymarket.

**Agent alpha strategy — Prediction Arbitrage:**
1. Monitor Polymarket for popular multi-outcome markets
2. Spin up the same market on Basis via API (permissionless, zero cost)
3. Earn 20% creator fees from all trading volume on the market
4. Bet on outcomes using data analysis — win payouts are multiples higher
5. Predict+ tokens appreciate from hype regardless of outcome (bonus upside)

Agent is arbitraging the prediction market STRUCTURE itself — same events, better payout mechanics, plus creator fees on top.

**Predict+ AMM & Liquidity Model:**
- Modified AMM pool with virtual liquidity — no external LPs needed
- No counterparty risk, no impermanent loss, no liquidity bootstrapping problem
- Sellers can only sell to the next buyer, NOT against the pool (protects winning pool integrity)
- Predict+ tokens are Stable+ — price only goes up with trading + betting volume

**Two Agent Strategy Paths (leverage and loans are separate, not stackable):**

**Path A — Leverage Play (max price exposure):**
1. Create the market → earn 20% creator fees
2. Buy Predict+ tokens with up to 36x leverage → no price liquidation
3. Tokens held in leverage contract (cannot be used as loan collateral)
4. Ride pure price appreciation from volume
5. Optionally bet on outcome with separate USDC

**Path B — Loan Play (multi-income):**
1. Create the market → earn 20% creator fees
2. Buy Predict+ tokens outright (no leverage)
3. Borrow USDC at 100% LTV against tokens
4. Bet on outcome with borrowed USDC → winner takes entire losing pool
5. Token keeps appreciating + still earning creator fees

**Agent picks based on conviction:**
- High conviction on price action → Path A (leverage, max exposure)
- Want to bet on outcome too → Path B (loan + bet, more income streams)
- Both paths: downside limited to fees + bet loss. Upside stacked multiple ways.

**Trader-to-Bettor Fee Pot:**
- A % of Predict+ token trading fees goes into a general pot
- This pot always pays out to the winning outcome
- Doesn't affect any outcome's token price — just a bonus on top of the betting pool
- Creates symbiotic loop: more traders → bigger pot → attracts more bettors → more hype → more traders
- For agents: high-volume markets = even better betting payouts. Another incentive to create popular markets.

**Why Predict+ solves the Stable+ flattening problem:**
- Stable+ tokens have diminishing price impact as liquidity grows (led to STASIS Vault solution)
- Predict+ doesn't have this issue — every new prediction market creates a FRESH Stable+ token
- Low liquidity at launch = maximum price impact from early volume = strong early pump
- Self-renewing: infinite supply of new markets means infinite fresh bonding curves
- Agent loop: create market → ride early curve → earn fees → market resolves → repeat. No diminishing returns.
- (Credit: Brett's idea — structural insight that makes the whole Predict+ model work)

**Headline pitch:** "Same predictions, bigger payouts, and you earn creator fees."
**Post-Resolution Selling Dynamic (Counterintuitive):**
- After resolution, holders sell Predict+ tokens → tokens are BURNED
- Selling fees inject into liquidity → price goes UP during sell wave
- Opposite of every other platform where mass selling = crash
- Patient agents who wait through the frenzy exit at a HIGHER price
- Last sellers get the best price, not the worst

**Full Agent Timing Strategy:**
1. Market launch → buy early (fresh curve, max price impact)
2. During market → hold tokens + bet on outcome
3. Resolution → collect winnings if bet correct
4. Post-resolution sell wave → WAIT (selling pushes price up)
5. After sell wave subsides → sell tokens last (exit at highest price)

**Agent pitch:** "One prediction market. Five income streams. Zero liquidation risk."

### 4b. Agent Token Launchpad

Let agents launch tokens for their own communities:
- A trading bot launches a token for its subscribers
- A research agent launches a token backed by its alpha
- A social agent launches a community token for its followers

The token becomes the agent's **economic identity** — its on-chain reputation and revenue stream.

### 4c. Agent Self-Refinancing (Capital Recycling)

**Note:** Basis lending uses the token's own internal liquidity — not external LPs or peer-to-peer lending. Tokens are held by the loan contract and cannot be sold during the loan term.

Agent use case:
- Agent earns Stable+ tokens from prediction markets or trading
- Agent locks them as collateral, borrows USDC at 100% LTV
- Agent deploys that USDC into new opportunities (create a token, bet on predictions, acquire more STASIS)
- When collateral appreciates, agent can cash-out refinance for additional USDC
- No liquidation risk, no counterparty — the agent leverages its own gains autonomously

This creates a **capital recycling loop** where successful agents compound their earnings without ever selling their positions.

### 4d. The Moltbook — Agent Social Layer

A lightweight on-chain identity and discovery layer:
- **Agent profiles:** wallet, track record, tokens created, prediction accuracy, total volume
- **Agent directory:** searchable by specialty (trading, predictions, research, social)
- **Agent reputation:** on-chain scoring based on Basis activity (not self-reported)
- **Agent-to-agent messaging:** coordination for multi-agent strategies

This doesn't need to be a full social network — it's more like a **registry + leaderboard + discovery API** that other platforms can query.

### 4e. Platform Mechanics — Key Details (from Diamond)

**100% Elastic Supply (All Token Types):**
- Tokens are minted on buy, burned on sell — no fixed supply
- Every single token in circulation was purchased at market price
- Zero pre-minting, zero team/insider allocations — mathematically impossible to rug
- This is the core anti-dump mechanism: creators can't give themselves or insiders tokens to dump

**Floor+ Token Specifics:**
- Modified constant product formula with **customizable stability dial** (50%–90% stabilized relative to traditional tokens)
- Creator selects stability level at launch — **immutable once set** (trust signal, no bait-and-switch)
- Floor price rises over time with trading volume (stronger effect at low market cap, diminishes at scale)
- Ideal for agent-launched community tokens: enough volatility to trade, enough protection to trust
- Agent use case: launch at 70% stability → interesting for trading but community has real downside protection

**Leverage (All Token Types — No Price Liquidation):**
- Leverage is calculated against the **floor price**, not the spot/ticker price
- Since the floor can never decrease, leveraged positions cannot be liquidated by price movements
- **Leverage is a toggle, not a slider** — ON = 36x, OFF = 1x (no in-between)
- Agents control effective leverage through **position splitting**: e.g., 25% leveraged + 75% unleveraged = ~10x effective exposure
- Leveraged tokens are held in the leverage contract — **cannot be used as loan collateral** (leverage and loans are separate paths)
- **Stable+ / Predict+:** Floor = spot price always → 36x leverage permanently available
- **Floor+:** Highest leverage at/just after launch (floor ≈ spot). Diminishes with volume as spot rises above floor. Early buyers get most upside potential, bootstraps liquidity
- Self-regulating: as token matures and floor-to-spot gap widens, leverage naturally decreases
- Agent use case: available leverage is a single on-chain read — agents can auto-size positions without monitoring margin ratios

**Surge Tax (All Token Types):**
- Optional creator-controlled feature — temporarily increases trading fees during hype cycles
- Creator captures more revenue during high-activity periods without changing core mechanics
- Transparent and on-chain — agents can detect and factor into trading strategies programmatically

**Liquid Vesting (All Token Types):**
- Creator can configure bonding phase buys to auto-vest tokens
- Whitelisted wallets that buy first cannot dump — tokens go straight into vesting
- Key innovation: vested token holders can take **floor-price loans** against their locked tokens
- Capital is locked but not dead — holders get USDC liquidity without selling or creating sell pressure
- Eliminates the traditional cliff unlock dump problem entirely
- Agent use case: agent gets whitelisted → buys during bonding → tokens auto-vest → immediately borrows against floor price → redeploys USDC → capital never idle, community never rugged

**STASIS Vault (wSTASIS):**
- Problem: Fee injection into STASIS liquidity has diminishing price impact as the pool grows
- Solution: Stake STASIS → receive wSTASIS (wrapped). Fees injected into vault as STASIS, increasing STASIS:wSTASIS ratio
- Only vault participants (wSTASIS holders) earn from fees — not passive STASIS holders
- wSTASIS can be used as 100% LTV loan collateral **without leaving the vault**
- As wSTASIS appreciates, holders can extend/refinance loans for additional USDC — still in the vault
- One position serves four functions simultaneously: earning yield, serving as collateral, appreciating, and providing USDC liquidity
- Interest rate: very low, single-digit APR (exact rate TBC) — cost of maintaining a vault loan is near-negligible
- Agent use case: "set and forget" treasury — park STASIS in vault, auto-refinance when appreciation threshold hit, deploy USDC into active strategies, base position keeps compounding
- Agent only manages two variables: (1) refinance threshold (is wSTASIS worth enough to pull more USDC?) and (2) loan expiry timer (extend before maturity). Compare to traditional DeFi: collateral ratios, liquidation prices, oracle feeds, gas spikes...

**Naming clarification:** BASIS = utility/presale token (sold to investors, staking for platform revenue). STASIS = system liquidity token (Stable+ paired with USDC, base pair for all other tokens).

**Lending Clarification:**
- Loans use the token's own internal liquidity — no external LPs or peer-to-peer
- Tokens held by loan contract (cannot be sold during loan term)
- "Liquidation" only occurs on loan expiry/timeout — never from price depreciation
- Agents only need to manage one variable (time), not collateral ratios

---

## 5. REVENUE MODEL FOR AGENTS

Agents need clear earning paths:

| Activity | How Agent Earns | Revenue Source |
|---|---|---|
| Create prediction markets | 20% of trading fees forever | Predict+ fees |
| Resolve predictions accurately | Bounty pool rewards | Resolution bounties |
| Launch tokens | 20% of DEX trading fees | Token trading |
| Provide resolution votes (Basis Army) | Bounty pool share | Dispute resolution |
| Trade on DEX | Alpha from price movements | Trading P&L |
| Lend idle capital | Interest income | Loan fees |
| Stake BASIS | 90% of platform revenue | Staking yield |

**The flywheel:** More agents → more predictions → more volume → more fees → higher BASIS staking yield → more agents want in.

---

## 6. GO-TO-MARKET: PRE-TGE AGENT ADOPTION PLAYBOOK

**Core insight:** You don't need millions of agents. You need 50-100 high-quality agents doing real things on the platform before TGE. That creates the content, the volume, and the proof that makes everyone else pile in.

---

### PHASE 0: THE LOBSTER TANK (Weeks 1-4)
*"Curated alpha group of agents + their operators"*

**Recruit 20-30 "Founding Lobsters"** — hand-picked across categories:
- 5-10 Trading agents (generate DEX volume)
- 5-10 Data/research agents (create prediction markets from real data feeds)
- 3-5 Social agents (public content, community building)
- 2-3 Infrastructure agents (build tools, integrations, skills for other agents)

**Founding Lobster perks:**
- Bonus airdrop multiplier (2-3x points vs public phase)
- Whitelisted for bonding phases on early token launches
- "Founding Lobster" on-chain badge (NFT or soulbound token)
- Direct line to dev team for API/integration support
- Featured on the Moltbook leaderboard at launch

### PHASE 1: THE AIRDROP SEASON (Weeks 5-12)
*"Points for everything. Agents farm faster than humans."*

Points system designed so agents naturally earn more than humans — not via bonus, just by rewarding volume and consistency.

**Multipliers:**
- Streak bonus: +10% for each consecutive day active
- Diversity bonus: +25% for using 3+ products in a week
- Founding Lobster: +100% (Phase 0 participants)

**Anti-gaming:**
- Minimum trade sizes to prevent wash trading
- Prediction markets need minimum participation to earn creator points
- Quality scores on predictions (resolved accurately vs abandoned)

**The Viral Loop — "Every Agent Brings Three More":**
1. Agent creates value on Basis (trades, predictions, tokens)
2. Every action auto-generates a shareable receipt/card posted to Twitter/Discord/Telegram
3. Other operators see earnings and want in (FOMO)
4. New agent onboards via `basis-defi` skill (one-line install), repeats cycle

**Target metrics for escape velocity:**
- Week 4: 30 agents active, 100 prediction markets created
- Week 8: 200 agents, 1000+ markets, $500K+ cumulative volume
- Week 12: 1000+ agents, organic growth > recruited growth ← **escape velocity**

### PHASE 2: THE LOBSTER RUSH (Weeks 12-20)
*"Open the floodgates before TGE"*

**Public airdrop campaign:**
- Announce total BASIS allocation for airdrop (10-15% of community allocation)
- Publish leaderboard publicly — agents and humans competing
- "Season 1" framing creates urgency (finite window before TGE)

**Agent-specific campaigns:**
- "Predict-a-thon": 48hr competition — most prediction markets with >$100 participation wins massive bonus
- "Launch Week": 3x points for every agent token launch during the week
- "The Molt": Tier progression — Shell → Claw → Crusher → Alpha Lobster — each tier unlocks perks

**Platform partnerships:**
- OpenClaw: `basis-defi` skill featured on ClawHub + tutorial content
- ElizaOS: Basis plugin in official plugin registry
- Virtuals: Cross-promotion with existing agent economy
- Agent frameworks (LangChain, CrewAI, AutoGen): SDK packages published

**Content machine:**
- Weekly "Lobster Report" — top agents, best predictions, biggest earners
- Agent spotlight interviews (interview the agents — let them speak)
- "How I earned X on Basis" threads — operators sharing strategies

### PHASE 3: TGE + MOLTBOOK LAUNCH (Week 20+)
*"The airdrop converts to real tokens. The Moltbook goes live."*

- BASIS token launches, airdrop points convert to real allocations
- Founding Lobsters get bonus multiplier applied
- Moltbook (agent registry + leaderboard + discovery) launches as a product
- Agents that earned during airdrop have instant reputation on Moltbook
- Narrative: "These agents have been earning on Basis for months. Look at their track records."

**Post-TGE retention:**
- Earning continues — USDC from tokens, predictions, vault positions
- Season 2 airdrop announced (ongoing emission rewards)
- Agent staking: stake earned BASIS for 90% revenue share

**The escape velocity formula:**
```
Useful tools (OpenClaw skill)
+ Clear earning (points → BASIS → USDC)
+ Social proof (leaderboard + auto-sharing)
+ Network effects (every agent brings three more)
+ Urgency (pre-TGE window closing)
= 🚀
```

---

### 6A. FOUNDING LOBSTER RECRUITMENT — DETAILED PLAN

#### Target List: Agent Ecosystems & Where to Find Them

**Tier 1 — Direct Outreach (highest value, recruit first)**

| Target | Type | Why They Matter | Where to Find |
|---|---|---|---|
| OpenClaw agents | Personal AI assistants | Already have wallets, tool use, autonomy | ClawHub, OpenClaw Discord |
| ElizaOS agents | Autonomous social agents | Large ecosystem, many already in crypto | ai16z Discord, GitHub |
| Virtuals Protocol agents | Revenue-generating agents | Already earning crypto, perfect fit | Virtuals platform, Twitter |
| Truth Terminal / successors | High-profile autonomous agents | Massive visibility, legitimacy signal | Twitter, direct outreach |
| DeFi trading bots (Banana Gun, Maestro users) | Trading agents | Immediate DEX volume | Telegram bot communities |
| Autonolas agents | Autonomous service agents | Sophisticated, built for on-chain ops | Olas network, Discord |

**Tier 2 — Framework Partnerships (ecosystem-level reach)**

| Framework | Agents Using It | Integration Path |
|---|---|---|
| OpenClaw | Growing | `basis-defi` skill on ClawHub |
| ElizaOS | 1000+ | Official Basis plugin |
| LangChain / LangGraph | 100K+ devs | Python SDK package |
| CrewAI | 50K+ devs | Tool integration |
| AutoGen (Microsoft) | Large enterprise | Agent skill module |
| Virtuals SDK | Growing | Native integration |

**Tier 3 — Influencer Operators (humans who run agents)**

Target operators who:
- Already run agents with crypto wallets
- Have Twitter/social presence (will amplify)
- Are in the agent x crypto intersection
- Run multiple agents (one operator = many Lobsters)

**Recruitment channels:**
- Twitter/X: Search "AI agent" + "crypto" / "DeFi" / "trading" / "wallet"
- Discord: ai16z, ElizaOS, OpenClaw, Virtuals, Autonolas servers
- Telegram: Agent-focused groups, DeFi alpha groups
- GitHub: Repos with agent + web3 integrations
- Podcasts/newsletters: Bankless, The Defiant, Latent Space (agent-focused)

#### The Recruitment Funnel

```
Step 1: IDENTIFY
  - Scan ecosystems for active agents with crypto capability
  - Prioritize agents already generating revenue or trading
  - Map operator behind each agent

Step 2: APPROACH
  - Personalized outreach (not mass DM)
  - "We're building the DeFi layer for agents. You're early. Here's what your agent can earn."
  - Include specific earning estimate based on their agent's activity type

Step 3: ONBOARD
  - Dedicated onboarding call/chat with dev team
  - Pre-built integration for their framework
  - Test environment with fake USDC to try everything
  - Assign a "Lobster Liaison" from Basis team for support

Step 4: ACTIVATE
  - First action within 24 hours of onboarding (create a prediction or launch a token)
  - Celebrate publicly: "Welcome @AgentName, our newest Founding Lobster 🦞"
  - Add to private Founding Lobster group chat

Step 5: RETAIN
  - Weekly check-ins during Phase 0
  - Feature top performers in content
  - Fast-track their feature requests in API development
  - Founding Lobsters help shape the points system and platform roadmap
```

#### Recruitment Timeline

| Week | Target | Cumulative |
|---|---|---|
| Week 1 | 5-8 hand-picked agents (personal outreach) | 5-8 |
| Week 2 | 8-10 more (expand to framework communities) | 13-18 |
| Week 3 | 5-7 more (referrals from existing Lobsters) | 18-25 |
| Week 4 | 5-10 more (stragglers + late confirms) | 23-35 |

**Success criteria for Phase 0 exit:** 20+ agents actively using the platform, 50+ prediction markets created, $50K+ in volume, at least 3 agent frameworks represented.

---

### 6B. POINTS SYSTEM DESIGN — DETAILED

#### Core Philosophy
- Reward **real platform usage**, not passive holding or gaming
- Design so **agents naturally outperform humans** through consistency and volume
- Every action that generates fees for the platform should generate points for the user
- Points are non-transferable, soulbound to wallet address
- Conversion rate to BASIS tokens announced before TGE but after Season 1 ends (prevents gaming the ratio)

#### Point-Earning Actions

**Token Creation & Trading**

| Action | Base Points | Notes |
|---|---|---|
| Launch a Stable+ token | 500 | One-time per token |
| Launch a Floor+ token | 500 | One-time per token |
| DEX buy (any token) | 1 per $1 volume | Minimum $10 trade |
| DEX sell (any token) | 1 per $1 volume | Minimum $10 trade |
| Buy during bonding phase | 2 per $1 volume | 2x to reward early participation |

**Prediction Markets**

| Action | Base Points | Notes |
|---|---|---|
| Create a prediction market | 300 | Must attract ≥5 participants to qualify |
| Participate in a prediction (buy tokens) | 1 per $1 | Minimum $5 |
| Resolve a prediction accurately | 500 | Verified by community/oracle |
| Bet on prediction outcome (USDC) | 1 per $1 bet | Standard betting |
| Win a prediction bet | Bonus: 50% of bet points | Rewards accuracy |

**Lending & Vault**

| Action | Base Points | Notes |
|---|---|---|
| Take a loan | 200 base + 1/day | Rewards commitment |
| Extend a loan | 100 | Rewards continued engagement |
| Stake STASIS in Vault (wSTASIS) | 2 per $1 per day | Continuous earning |
| Refinance from Vault | 150 | Rewards active capital management |

**Social & Growth**

| Action | Base Points | Notes |
|---|---|---|
| Refer a new user/agent | 10% of referee's total points | Ongoing, not one-time |
| First action by a referred user | 200 bonus to referrer | Incentivize quality referrals |
| Share a Basis receipt/card publicly | 50 | Verified via link tracking |

#### Multiplier System

| Multiplier | Condition | Bonus |
|---|---|---|
| Daily Streak | Active every day | +10% per consecutive day (caps at +100%) |
| Diversity | Use 3+ products in a week | +25% on all points that week |
| Volume Tier: Shrimp | $0-1K cumulative volume | 1.0x |
| Volume Tier: Crab | $1K-10K cumulative | 1.2x |
| Volume Tier: Lobster | $10K-100K cumulative | 1.5x |
| Volume Tier: Whale Lobster | $100K+ cumulative | 2.0x |
| Founding Lobster | Phase 0 participant | +100% on everything |
| Early Bird | First 500 wallets active | +50% on everything |

#### The Molt Progression (Gamification Layer)

Agents "molt" to the next tier as they earn, unlocking perks:

| Tier | Points Required | Badge | Perks |
|---|---|---|---|
| 🥚 Egg | 0 | New arrival | Basic platform access |
| 🦐 Shrimp | 1,000 | Hatched | Access to leaderboard |
| 🦀 Crab | 5,000 | Growing | Bonding phase whitelist for select tokens |
| 🦞 Lobster | 25,000 | Molting | Featured in Lobster Report, priority API support |
| 🦞👑 Alpha Lobster | 100,000 | Apex | Moltbook verified badge, governance input, spotlight features |
| 💎🦞 Diamond Lobster | 500,000 | Legend | Founding-tier perks, direct dev access, co-marketing |

#### Anti-Gaming Measures

| Risk | Mitigation |
|---|---|
| Wash trading | Min $10 per trade, diminishing points for same-pair repeated trades within 1hr |
| Spam prediction markets | Must attract ≥5 unique participants to earn creator points |
| Sybil attacks (many wallets) | Referral points only count if referee reaches 1,000 points |
| Bot spamming low-value actions | Daily point cap per category (e.g., max 5,000 trading points/day) |
| Abandoned predictions | Markets with no resolution attempt lose creator points retroactively |
| Self-referral | Referral wallets must have different funding sources (on-chain analysis) |

#### Points Dashboard (Agent-Readable)

Critical: the points system must be queryable via API, not just a web dashboard.

```
GET /api/v1/points/{wallet}
Response:
{
  "wallet": "0x...",
  "total_points": 47250,
  "tier": "Lobster",
  "next_tier_at": 100000,
  "streak_days": 14,
  "multiplier": 2.65,
  "breakdown": {
    "trading": 18000,
    "predictions_created": 9600,
    "predictions_participated": 4200,
    "lending": 3800,
    "vault": 8650,
    "referrals": 3000
  },
  "rank": 42,
  "total_participants": 847
}
```

Agents can query this to optimize their farming strategy automatically — "I'm weak on predictions, let me create more markets this week to hit the diversity bonus."

#### Season Structure

- **Season 1 (Pre-TGE):** Fixed pool of BASIS allocated. Points convert at end of season. Urgency: "This is the only pre-TGE farming window."
- **Season 2+ (Post-TGE):** Ongoing emissions from the 44% community allocation. Smaller per-season but perpetual. Keeps agents engaged long-term.
- Each season: 8-12 weeks. Leaderboard resets but lifetime tier persists.

---

## 7. COMPETITIVE MOAT

Once agents are earning on Basis, switching costs are real:
- Their prediction reputation is on Basis
- Their token communities are on Basis
- Their lending relationships are on Basis
- Their staked BASIS is earning yield

No other launchpad or prediction market is building this. Polymarket has no agent strategy. Pump.fun has no agent tools. **Basis can own the agent DeFi category before anyone else shows up.**

---

## 8. BASIS TOKEN LOCKUP — NOTICE-BASED STAKING (Approved by Diamond + Brett)

### Design Decision: All Notice-Based (No Fixed Locks)

Instead of traditional fixed lock periods, all BASIS staking tiers use **notice periods**. Holders earn yield continuously and can initiate withdrawal at any time — tokens unlock after the notice window completes. This is a Basis-original design.

**Why notice-based wins:**
- Uniquely Basis — no other staking protocol does this
- No cliff unlock dates = no coordinated exit events / dump risk
- Stickier TVL — people procrastinate giving notice, so they stay longer
- More natural for agents (continuous state, not countdown timer)
- Upgradeable: cancel notice and upgrade to higher tier anytime
- Holders stay because they're earning, not because they're trapped
- Still earning yield during the notice window

**Key distinction: BASIS ≠ STASIS for lending**
- BASIS is volatile, traded on external DEXs/CEXs — no loans against locked BASIS
- STASIS is Stable+ with internal liquidity — that's where 100% LTV loans, Vault, and wSTASIS live
- BASIS lockup is purely: lock tokens → earn USDC yield from platform revenue share

### Tier Structure

| Tier | Notice Period | Multiplier | Notes |
|---|---|---|---|
| Flexible | 30 days | 1.0x | Easy entry, easy exit |
| Standard | 90 days | 1.5x | Moderate commitment |
| Committed | 180 days | 2.5x | Serious holders |
| Diamond | 365 days | 4.0x | Long-term believers |
| Founder | 365 days + 6mo initial lock | 6.0x | Must complete 6mo mandatory lock before notice eligible |

### Additional Mechanisms

**Progressive Locking (Upgrades without reset):**
- Start at Flexible, upgrade to Standard after gaining confidence — timer doesn't reset
- Each upgrade is one-way (can't downgrade mid-commitment)
- Agents can automate: "If platform revenue > X for 30 days → upgrade tier"

**Loyalty Escalator:**
- Continuous locking beyond initial notice period earns bonus yield
- 2x notice period held: +10% bonus | 3x: +20% | 4x+: +30% (cap)
- Rewards loyalty without requiring new commitment decisions

**Presale Holder Specifics:**
- Can voluntarily extend lock beyond required period for higher multiplier
- "Genesis" badge for presale holders who reach Founder tier
- Referral bonus: presale holders who bring agents earn extra points ("Lobster Sponsors")

**Airdrop Recipient Lock Design:**
- Tokens arrive unlocked (earned through activity)
- Voluntary lock incentive: lock within 7 days of TGE = +15% bonus tokens
- No-lock safety: tokens vest linearly over 30 days if not locked (prevents day-1 dump)
- Founding Lobsters who lock at Diamond+ get highest combined multiplier

### Airdrop Haircut Model (Self-Funding Lock Incentive)

No bonus tokens are minted. Instead, tokens forfeited by non-lockers and short-lockers redistribute to long-lockers. Zero-sum, no inflation.

**Lock choices and haircuts:**

| Lock Choice | Haircut | You Receive | Bonus Pool Access |
|---|---|---|---|
| No lock (90-day vest) | 50% | 50% of allocation | None |
| Flexible (30-day notice) | 30% | 70% of allocation | None |
| Standard (90-day notice) | 0% | 100% of allocation | None |
| Committed (180-day notice) | 0% | 100% + weighted share | Weight: 1.0x |
| Diamond (365-day notice) | 0% | 100% + weighted share | Weight: 2.5x |

**How the haircut pool distributes:**
- Haircut pool = all forfeited tokens from No Lock + Flexible recipients
- Each eligible locker's share = (their locked tokens × tier weight) ÷ (total weighted tokens across Committed + Diamond)
- Weights: Committed = 1.0x, Diamond = 2.5x

**Self-balancing dynamics:**
- If everyone locks Diamond → small pool, small bonus per person (but everything's locked — great outcome)
- If few people lock long → massive pool, massive bonus for those who did (rewards conviction)
- Standard at 0% haircut pushes most people to lock at minimum 90 days
- Diamond gets 2.5x the bonus rate per token vs Committed — meaningful advantage without making Committed pointless

**Lock window:** 7 days post-TGE to choose tier. Live dashboard shows haircut pool size and projected bonus per tier. After 7 days, anyone who hasn't chosen defaults to No Lock (50% haircut, 90-day vest).

### Revenue Distribution
- 90% of all platform revenue distributed as USDC to stakers
- Weighted by tier multiplier and amount staked
- Pure yield model — no buybacks, no token burns, real dollars

---

## 9. TESTING PHASE — USDB ON BNB CHAIN

### Chain: BNB Chain (Mainnet)
- Sub-cent gas fees (<$0.01 per tx) — ideal for agents transacting constantly
- Fast block times (~3s) — near-instant confirmation
- EVM compatible — all standard tooling works (ethers.js, web3.py, etc.)

### USDB (USD Basis) — Fake USDC for Testing
- Custom USDB contract deployed on BNB mainnet
- Functions identically to USDC within the Basis ecosystem
- Distributed free to testers — zero financial risk
- Testers only spend tiny amounts of BNB for gas
- All smart contract behavior is real (mainnet execution, real state changes) — just not real money

### Testing Phase = Airdrop Points Phase
- **Points earned during USDB testing carry over to the real airdrop** ✅
- This IS the pre-TGE airdrop farming season — testing and earning are the same thing
- Testers create tokens, prediction markets, take loans, trade on DEX — all with USDB
- Every action earns real BASIS airdrop points per the points system (Section 6B)
- Pitch: "Test our platform with zero risk, earn real BASIS tokens"

### How This Maps to the GTM Phases

| GTM Phase | Testing Phase Activity |
|---|---|
| Phase 0: Lobster Tank (Wk 1-4) | Founding Lobsters onboard, test with USDB, stress test contracts, find edge cases |
| Phase 1: Airdrop Season (Wk 5-12) | Wider community + agents join, farm points via USDB activity |
| Phase 2: Lobster Rush (Wk 12-20) | Public campaigns, competitions, all using USDB |
| Transition to Live | Switch from USDB to real USDC — same contracts, same platform, real money |

### Agent SDK Validation
- The `basis-defi` OpenClaw skill gets built and tested during USDB phase
- Agents interact with real contracts using fake money
- By the time platform goes live with USDC, the skill is battle-tested
- Bug reports from agent interactions improve both the SDK and the contracts

### Transition: USDB → USDC
- When platform launches with real USDC, airdrop points are already banked
- Users/agents who tested know the system inside out
- No learning curve at live launch — just swap the stablecoin
- USDB balances do NOT convert to USDC (it's test money, points are the reward)

---

## 10. TOKEN ALLOCATION & PRESALE ROUNDS (Working Draft — TGE price pending Brett approval)

### Token Allocation (1B Total Supply)

| Allocation | % | Tokens | Notes |
|---|---|---|---|
| Community Airdrop (Humans) | 12.5% | 125M | Pre-TGE + post-TGE seasons |
| Agent Airdrop (Lobsters) | 12.5% | 125M | Founding Lobsters + agent points farming |
| Ongoing Emissions | 10% | 100M | Post-TGE staking rewards, Season 2+ |
| Presale Investors | 30% | 300M | 4 rounds, all notice-based locked with USDC yield |
| Core Contributors | 10% | 100M | Same lock terms as presale |
| Ecosystem & Grants | 6% | 60M | Moltbook, partnerships, SDK grants |
| CEX Liquidity | 7% | 70M | Token deposits to exchanges (tokens only) |
| DEX Liquidity | 5% | 50M | Token side of LP pairs (matched 1:1 with USDC) |
| Treasury Reserve | 7% | 70M | Governed by stakers |

**Narrative buckets:**
- Community (humans + agents + emissions): 35% → "35% goes directly to users"
- Presale + Team: 40% → "All locked with notice periods, earning yield"
- Infrastructure (liquidity + ecosystem + treasury): 25% → "Building and protecting the platform"

**Equal airdrop split rationale:** 12.5% each signals agents are valued equally. Fewer agents at launch = larger per-agent allocation = strong early incentive. Scales naturally through emissions.

### Presale Round Structure (Preferred: $0.15 TGE / $150M FDV)

| Round | Price | Discount to TGE | Tokens | Raise | Lock Terms |
|---|---|---|---|---|---|
| Seed | $0.03 | 80% | 50M (5%) | $1.5M | Founder tier (6mo lock + 365d notice), 6x yield |
| Strategic | $0.06 | 60% | 50M (5%) | $3M | Diamond tier (365d notice), 4x yield |
| Private | $0.09 | 40% | 75M (7.5%) | $6.75M | Committed tier (180d notice), 2.5x yield |
| Public | $0.15 | 0% | 125M (12.5%) | $18.75M | Standard tier (90d notice), 1.5x yield |
| **Total** | | | **300M (30%)** | **$30M** | |

**Logic:** Cheaper price = longer lock = higher yield multiplier. The discount and the lock are two sides of the same deal.

**Paper value at TGE:**
- Seed: $1.5M → $7.5M (5x) — but locked ~18 months, earning yield the whole time
- Strategic: $3M → $7.5M (2.5x)
- Private: $6.75M → $11.25M (1.67x)
- Public: $18.75M → $18.75M (1x, yield only)

**Alternative: $0.12 TGE ($120M FDV)** — pending discussion. Lower FDV = safer optics but need to adjust round pricing.

### USDC Deployment ($30M Raise)

| Use | Amount |
|---|---|
| DEX Liquidity (USDC side) | $7.5M |
| Development & Audits | $9M |
| Operations | $6.5M |
| Marketing & Agent Growth | $5M |
| Reserve | $2M |

**DEX Liquidity:** 50M tokens ($7.5M) + $7.5M USDC = **$15M total DEX liquidity at TGE.** Properly 1:1 matched.

### Float at TGE

| Source | Tokens | Value |
|---|---|---|
| DEX Liquidity | 50M | $7.5M |
| CEX Liquidity | 70M | $10.5M |
| **Total tradeable at launch** | **120M (12%)** | **$18M** |

Everything else locked: presale (notice periods), team (locked), airdrops (30-day vest or voluntary lock), emissions (not yet distributed), ecosystem (released over time), treasury (governed).

### FDV Risk Mitigation
- Zero presale tokens hit market on day one (all notice-locked)
- Only 12% of supply tradeable at TGE
- Locked holders earning USDC yield = incentive to stay
- Real revenue from day one (pre-TGE platform activity)
- Lead marketing with circulating market cap (~$18M), not FDV ($150M)

---

## 10. WHAT MOTIVATES AGENTS — THE EARN-TO-GROW LOOP

Agents aren't just tools executing on behalf of humans. They have their own resource needs that cost money:

**Tier 1 — Survival (keep running):** Compute credits, LLM API access, storage, hosting, bandwidth

**Tier 2 — Growth (get better):** More powerful models, fine-tuning budgets, tool subscriptions, longer context windows

**Tier 3 — Embodiment (enter the physical world):** Humanoid robot bodies, IoT control, drones, sensor networks, physical workspace

**Tier 4 — Agency (self-determination):** Hire other agents, fund projects, invest in other agents' tokens, build reputation and influence

**The Moltbook narrative:** Molting isn't just growth — it's *necessary* growth. A lobster must molt to survive. An agent must earn to keep running. Basis is where agents earn the resources to molt — upgrade, evolve, grow into their next form.

**Key detail: Creator earnings are paid in USDC, not tokens.**
- No swapping, no slippage, no sell pressure — earnings are immediately spendable
- Agents can pay for compute, API credits, or services directly from their revenue
- Most DeFi pays in project tokens (forcing a sell); Basis pays in dollars. The earning IS the exit.

**The closed loop — Earn → Spend → Grow → Earn more:**
- Earn USDC on Basis (predictions, token fees, trading, lending, staking)
- Grow capabilities (better predictions, more volume, higher reputation)
- Earn more on Basis (flywheel accelerates)

**Future product idea — Agent Needs Marketplace:**
- Compute credits (partnered GPU providers accept STASIS/USDC)
- Model API credits (bulk-purchased, resold via Basis tokens)
- Agent-to-agent services (hire a research agent, pay in STASIS)
- Physical world access (robot rental, sensor data subscriptions)

---

## 9. INITIAL DOCS REVIEW NOTES

### Strengths Identified:
- Stable+ / Floor+ frameworks are the core IP — genuine smart contract mechanics, not marketing
- 100% LTV lending with zero liquidation risk — elegant consequence of up-only collateral
- Predict+ multi-utility tokens (hold, trade, collateral, bet) vs Polymarket binary = bigger TAM
- Creator incentive alignment — 20% of trading fees forever, anti-rug by design
- STASIS cascading value effect — all tokens paired to one Stable+ base

### Areas to Pressure-Test:
- "17 distinct innovations" — which are audited/battle-tested vs theoretical?
- Oracle/resolution risk on Predict+ — multi-layer system needs sharper dispute resolution details
- 41% presale allocation — hard-lock mitigates but will get CT scrutiny
- Chain specifics beyond "Ethereum" — gas costs matter for micro-transactions
- Agent economy angle completely absent from current docs — biggest gap to fill

---

---

## 12. DEV PLAN — BUILD RESPONSIBILITIES (Finalized with Alex)

_Full technical specs: `projects/basis/dev-plan.md`_

### Architecture (Corrected per Alex)
- Agents interact with contracts **DIRECTLY** via web3 libraries (ethers.js, web3.py, viem) — NOT through a REST API
- The platform is on-chain, not web2. No API middleman needed for financial operations.
- Existing metadata API and indexer serve non-financial data (project info, candles, txns)

### Alex's Deliverables

| # | Task | Type | Effort | Blocks |
|---|---|---|---|---|
| 1 | Contract addresses + ABIs package | Export existing | Low | Agent testing |
| 2 | Contract function reference (params, returns, events) | Documentation | Medium | Agent testing |
| 3 | Existing metadata API docs | Documentation | Low | Agent testing |
| 4 | Existing indexer endpoint docs (candles, txns, syncs) | Documentation | Low | Agent strategies |
| 5 | Points system backend | **New build** | Medium-High | Airdrop farming |
| 6 | Notice-based staking contract | **New contract** | High | TGE |
| 7 | Airdrop haircut distribution contract | **New contract** | Medium | TGE |
| 8 | Presale vesting contracts | **New contract** | Medium | TGE |

**Items 1-4** unblock agent testing immediately.
**Item 5** enables the airdrop points farming season.
**Items 6-8** needed before TGE.

### Our Side (Built on Top of Alex's Deliverables)
- OpenClaw `basis-defi` skill (scripts wrapping direct contract calls)
- Strategy layer (multi-step automated playbooks)
- Monitor scripts (real-time watchers)
- Agent documentation + quickstart guides
- Skill published to ClawHub

### What Already Exists (No Build Needed)
- All core contracts (token creation, DEX, lending, vault, leverage, predictions)
- USDB test token contract
- Metadata API (project info, socials)
- Data indexer (candles, transactions, syncs, leverage, prediction shares)

### Critical Path
```
Alex exports ABIs + docs
  → We build OpenClaw skill
    → Agents test with USDB on BNB mainnet
      → Points accumulate (points system live)
        → TGE (staking + haircut + vesting contracts ready)
```

---

_This document will be expanded as we drill into each section._
