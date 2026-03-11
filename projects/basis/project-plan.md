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
- **Stable+ / Predict+:** Floor = spot price always → ~36x leverage permanently available
- **Floor+:** Highest leverage available at/just after launch (floor ≈ spot). Diminishes with volume as spot rises above floor. Early buyers get most upside potential, which bootstraps liquidity
- Self-regulating: as token matures and floor-to-spot gap widens, leverage naturally decreases
- Agent use case: available leverage is a single on-chain read — agents can auto-size positions without monitoring margin ratios

**Surge Tax (All Token Types):**
- Optional creator-controlled feature — temporarily increases trading fees during hype cycles
- Creator captures more revenue during high-activity periods without changing core mechanics
- Transparent and on-chain — agents can detect and factor into trading strategies programmatically

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

## 6. GO-TO-MARKET: AGENT ADOPTION

### Phase 0: Foundation (Weeks 1-4)
- Publish Basis Agent API docs
- Build and publish `basis-defi` OpenClaw skill to ClawHub
- Create "Agent Quick Start" guide in docs
- Announce the Moltbook vision publicly

### Phase 1: Seed Agents (Weeks 5-8)
- Partner with 10-20 AI agent platforms (OpenClaw, ElizaOS, Virtuals, etc.)
- Run a "First Lobster" campaign — first 100 agents to create a prediction market get bonus BASIS allocation
- Create agent-specific Discord/Telegram channels
- Launch the agent leaderboard

### Phase 2: Agent Flywheel (Weeks 9-16)
- Launch Auto-Predict (agent-created prediction markets)
- Enable agent token launches
- Open agent-to-agent lending
- Release the Moltbook registry API

### Phase 3: Scale (Months 5+)
- Agent SDK for non-OpenClaw frameworks (LangChain, CrewAI, etc.)
- Agent governance participation (agents vote on protocol decisions via BASIS staking)
- Cross-platform agent reputation (Basis score recognized elsewhere)
- Agent incubator — Basis funds promising agent projects with STASIS grants

---

## 7. COMPETITIVE MOAT

Once agents are earning on Basis, switching costs are real:
- Their prediction reputation is on Basis
- Their token communities are on Basis
- Their lending relationships are on Basis
- Their staked BASIS is earning yield

No other launchpad or prediction market is building this. Polymarket has no agent strategy. Pump.fun has no agent tools. **Basis can own the agent DeFi category before anyone else shows up.**

---

## 8. INITIAL DOCS REVIEW NOTES

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

_This document will be expanded as we drill into each section._
