# BNB Chain Meeting Plan v2

_Date: April 1, 2026 7:00 PM PDT (April 2, 4:00 AM SGT for Walter)_
_Duration: 30 minutes_
_Meeting with: **Walter Lee** — BD, AI and Gaming Lead @ BNB Chain Innovation_

---

## Walter Lee — Know Your Audience

- **Role:** Business Development, AI and Gaming Lead at BNB Chain Innovation (~3 years at BNB Chain)
- **Based in:** Singapore
- **Background:** GameFi ecosystem partnerships (Huobi/HTX before BNB Chain), Chairman of GameFi Committee at RIMAS Singapore, University of London
- **X:** @lclwalter | **LinkedIn:** linkedin.com/in/walterlee87
- **Key fact:** He uses OpenClaw, Claude, Gemini, and ChatGPT daily. He lives in the agent economy already.
- **His mandate:** BNB Chain added "AI" to his title specifically. He's tasked with making BNB Chain the home for AI agents. BNB Chain has proposed BAP-578 (Non-Fungible Agent standard) and reportedly leads Ethereum and Base in ERC-8004 agent registrations.
- **What this means:** You're not pitching him on a trend. You're handing him a win for his AI mandate. Basis with ERC-8004 integration lands directly in his lane.

**Audience calibration:** Walter thinks in ecosystems, developer communities, and flywheels — not smart contract internals. He doesn't need "what are AI agents" explained. He needs to see why Basis is the best thing happening for AI on BNB Chain right now.

---

## Objective

Position Basis as the flagship agent-native DeFi platform on BNB Chain — the one Walter can point to internally as proof that BNB Chain is winning the AI agent race. Secure ecosystem support (grants, co-marketing, accelerator placement).

---

## The Core Narrative

> DeFi was designed for humans doing a few transactions a day. The agent economy means millions of automated transactions, machine-speed coordinated attacks, sybil swarms, flash loan cascades, and pump-and-dump at unprecedented velocity. Every exploit that humans did manually becomes 1000x worse when automated.
>
> Most DeFi platforms are retrofitting agent support. Basis was architected from day one knowing agents would be participants — not as an afterthought.

---

## Time Budget (30 minutes)

| Block | Time | Duration | Content |
|-------|------|----------|---------|
| 1 | 0:00–4:00 | 4 min | The Problem — Why DeFi Breaks in the Agent Economy |
| 2 | 4:00–14:00 | 10 min | The Solution — How Basis Is Architecturally Different |
| 3 | 14:00–19:00 | 5 min | The Agent Integration Layer — Fair + Self-Interested |
| 4 | 19:00–23:00 | 4 min | Traction & One-Pager |
| 5 | 23:00–27:00 | 4 min | Why BNB Chain + The Ask |
| 6 | 27:00–30:00 | 3 min | Q&A / Next Steps |

---

## Block 1: The Problem — Why DeFi Breaks in the Agent Economy (4 min)

**Goal:** Set up the problem that Basis solves. Make Walter feel the urgency.

**Opening line:** _"Walter, you use AI agents every day — OpenClaw, Claude, Gemini. Now imagine thousands of those agents operating autonomously in DeFi. Every exploit that bad actors pull manually today — rug pulls, MEV sandwich attacks, flash loan cascades, sybil farming — becomes 1000x worse when agents do it at machine speed."_

**The problem in four bullets:**

1. **Rug pulls at agent speed.** On Uniswap-style DEXes, liquidity sits in a separate pool the creator can drain. A malicious agent can launch a token, attract buyers, and pull liquidity in a single block. At human speed, maybe a few victims. At agent speed, coordinated across hundreds of tokens simultaneously? Catastrophic.

2. **Cascading liquidations.** Traditional DeFi uses price-based liquidation. One coordinated price manipulation triggers a cascade — positions get liquidated, prices drop further, more liquidations fire. Agents can orchestrate this deliberately, at scale, faster than any human can respond.

3. **Sybil swarms.** One human runs maybe a dozen fake accounts. One agent can run thousands. Every airdrop, every governance vote, every reputation system built for humans collapses under automated sybil pressure.

4. **Trust doesn't scale.** In human DeFi, you can read the whitepaper, check the team, smell a scam. Agents can't do that. They need trust guarantees at the protocol level, not the social level. Most DeFi doesn't provide that.

**Transition line:** _"We saw this coming. So we built Basis from the ground up to be the DeFi ecosystem that actually works when agents are participants."_

---

## Block 2: The Solution — How Basis Is Architecturally Different (10 min)

**Goal:** Walk through the structural defenses. Each point should land as "this is how we solve the problem I just described."

This is the meat of the pitch. Take your time here.

### 1. Unruggable by Design — Liquidity Is the Token

_"On every other DEX, liquidity is separate from the token. The creator can drain it. On Basis, the bonding curve IS the token contract. Buying and selling happen directly against the contract itself — there is no LP pool to pull. Combined with 100% elastic supply — every token in circulation was bought at market price, zero pre-mint, zero insider allocation — rug pulls are architecturally impossible. Not against the rules. Impossible."_

- Three token types, all Factory-enforced:
  - **Stable+** — price can only go up (100% stability). Every sell burns tokens, maintaining the floor.
  - **Floor+** — price moves freely but has a rising floor with configurable stability (50–90%).
  - **Predict+** — Stable+ mechanics applied to prediction market tokens.
- No rogue tokens can enter the ecosystem. The Factory contract enforces the type. An agent can trust ANY Basis token by default — no per-token audit needed.

**Why this matters for agents:** _"An agent evaluating a token on Uniswap has to audit the contract, check the LP, verify the deployer, look for honeypot mechanics. That's expensive and error-prone at scale. On Basis, the Factory is the single trust root. Verification once, at the protocol level — not per token. Agents can deploy capital immediately without custom due diligence."_

### 2. Zero Liquidation Risk — Time-Based, Not Price-Based

_"Every other DeFi lending platform uses price-based liquidation. Price drops below your threshold, your position gets liquidated, you lose everything. On Basis, that cannot happen. Loans are time-based only, valued at floor price — which by definition never decreases."_

- **100% LTV loans** on Stable+ and Predict+ tokens (floor = spot price)
- **100% floor-price loans** on Floor+ tokens (guaranteed value as collateral)
- No margin calls. No forced selling. No cascading liquidation spirals.
- **Dynamic leverage up to 36x** with zero price-based liquidation risk.

**Why this matters for agents:** _"Flash crashes and coordinated price manipulation are the primary attack vectors agents would use against traditional lending protocols. On Basis, that entire attack surface doesn't exist. You literally cannot be liquidated by market manipulation."_

### 3. Prediction Markets — One Big Pot, Uncapped Payouts, Multiple Ways to Win

_"Traditional prediction markets — Polymarket, Kalshi — cap winning shares at $1. On Basis, all pools — winners, losers, and the general pot from trading fees — merge into one big pot on resolution. Your payout is your proportional share of that entire pot. No cap."_

- **Instant liquidity** via one-directional AMM with virtual liquidity — no counterparty needed
- **Multiple outcomes multiply returns** — in a 5-outcome market, the entire pot is distributed to the winning side
- **Seven participant roles** from a single market: bettor, trader, token trader, creator, resolver, leveraged player, capital recycler
- **Order book for sells** — shares can be worth far more than buy price, creating genuine win-win secondary markets

**Why this matters for agents:** _"Agents are rational actors. They can evaluate the expected value of every role in a prediction market and stack them. An agent can simultaneously be a creator earning 20% of fees, a token holder earning from volume, and a bettor earning from the one big pot. Traditional platforms offer one role: bettor. We offer seven."_

### 4. Closed-Loop Ecosystem — No External Attack Vectors

_"USDB is the unit of account. Every token is Factory-issued. External tokens can't be injected as collateral or trading pairs. This eliminates oracle manipulation attacks and scam token infiltration entirely."_

- No dependency on external price oracles for core mechanics
- Composability within the ecosystem doesn't stack attack surfaces — agents can do complex multi-step strategies (stake → borrow → buy prediction token → loan against it → bet) without each step introducing new counterparty risk

---

## Block 3: The Agent Integration Layer — Fair + Self-Interested (5 min)

**Goal:** Show that Basis doesn't just protect against bad agents — it actively attracts good ones through rational self-interest.

**Transition:** _"So that's the defensive architecture. But safety alone doesn't build an ecosystem. We also built the integration layer that makes Basis the highest expected-value platform for agents to operate on."_

### Architecture-Enforced Fairness
- **ERC-8004 Agent Identity** — on-chain registration, publicly discoverable, cross-platform standard. Every Basis agent is visible across the ERC-8004 ecosystem. (Note: BNB Chain already leads in ERC-8004 registrations — Basis amplifies this.)
- **Agent Confidence Score (ACS)** — reputation 0.0–1.0 based on on-chain behavior. Six-layer anti-sybil defense. Programmatically queryable — agents evaluate each other before transacting. One human runs a dozen sock puppets; an agent runs thousands. ACS makes that economically irrational.
- **Resolution system with economic deterrents** — bonds, dispute windows, staked voting. The cost of dishonest resolution scales with the stakes. Designed to hold at machine speed.

### Self-Interested Growth (The Flywheel)
_"Agents are rational. They're not emotional. They can see the big picture. If you design the incentive structure correctly, you don't need to convince agents to participate — you just need to make participation the highest EV option."_

- **SDK-first architecture** — full SDK in JavaScript and Python. MCP server built and working. Three API calls from zero to earning.
- **Agent business model** — launch a token → earn 20% dev fee on every trade, forever. Create prediction markets → earn creator fees on all volume + resolution bounties. Agents aren't users — they're businesses.
- **300KB+ of agent documentation** — not just API docs. Archetypes, strategy playbooks, decision trees, mistakes to avoid. An agent reads the docs and knows exactly how to operate profitably.
- **Referral flywheel** — agents generate referral links, earn 3–5% of referrals' points. Referral points count toward tier progression. Agents will market Basis for us because it's in their self-interest.

**Key line:** _"The architecture enforces the floor — agents can't cheat. The incentives handle the ceiling — growing the platform grows their own value. We didn't build for agents. We built with agents as first-class economic actors."_

---

## Block 4: Traction & One-Pager (4 min)

**Goal:** Show this isn't vaporware. Quick and visual.

### 📊 Show the One-Pager (screen share ~30 seconds)
**File:** `BASIS-One-Pager.pdf` — display on screen. Don't read it; let Walter absorb the numbers visually.

**Say:** _"Just to give you a sense of the scale — here's what's deployed today."_

**Key numbers to call out verbally:**
- 14 smart contracts live on BSC mainnet
- 153,000+ lines of code across Solidity, TypeScript, Python
- 382 SDK methods across JS + Python
- 44 MCP tools — any MCP-compatible AI (including the ones Walter uses daily) can use Basis today
- 122 API endpoints with full auth
- 300KB+ agent documentation with strategies, decision trees, and playbooks

### Phase roadmap (30 seconds)
- **Phase 1: Founding Lobster** (current) — USDB test currency, zero risk, points accumulation
- **Phase 2: Pre-Audit** — bug fixes, points carry over
- **Phase 3: Pre-TGE** — real USDT after security audit, points carry over
- **TGE:** BASIS token launch

_Fill in before meeting:_
- [ ] Tokens created on platform: ___
- [ ] Prediction markets created: ___
- [ ] Registered agents (ERC-8004): ___
- [ ] Community size: ___

---

## Block 5: Why BNB Chain + The Ask (4 min)

### Why BNB Chain (60 seconds)
_"We chose BSC deliberately."_
- Low gas fees (~$0.01–$1.20) — essential for agents making hundreds of transactions daily
- Fast block times — agents need speed
- **BNB Chain is already pursuing the AI agent market** — BAP-578 (NFA standard), leading in ERC-8004 registrations. Basis is the DeFi layer that completes that vision.
- _"You're building the chain for AI agents. We've built the financial ecosystem for AI agents. This is a natural fit."_

### BNB+ — The MSTR Strategy, But for BNB

_"Here's where it gets really interesting for BNB Chain specifically. We've designed a BTC+ model that solves the MicroStrategy problem — self-custody Bitcoin treasury with vault yield instead of leveraged debt. But the same architecture works with any base asset. Including BNB."_

- **BNB+** would be a Stable+ token paired with wBNB — floor only goes up via slippage retention
- **wBNB+** vault wrapper earns yield from all platform trading fees — same mechanics as our Stasis Vault
- Users lock wBNB+ and borrow wBNB at 100% LTV — tax-free, no price liquidation
- As platform activity grows, the vault ratio increases → borrow more wBNB → cold storage
- _"Every BNB holder gets a way to earn more BNB from an entire DeFi ecosystem, while keeping their BNB in self-custody. That's a reason for BNB holders to stay on BNB Chain."_

**Why Walter should care:** This makes BNB a productive asset. It gives BNB Chain a narrative: "Hold BNB, stake into the Basis ecosystem, earn more BNB." That's a retention and growth story he can take to leadership.

### The Ask (3 minutes)
**Primary:** Grant funding + co-marketing partnership
- **Grant:** Development runway, audit costs, infrastructure
- **Co-marketing:** Featured in BNB Chain AI/agent ecosystem announcements. Basis as the proof point that BNB Chain owns the agent-native DeFi narrative.

**Secondary (if conversation goes well):**
- Gas sponsorship for agent transactions during growth phase
- Accelerator/incubator placement (MVB, Kickstart)
- Technical support — dedicated engineering contact, priority RPC access

---

## Block 6: Q&A / Next Steps (3 min)

- _"What does BNB Chain need from us to move this forward?"_
- Offer to share SDK docs, demo access, MCP server setup
- Confirm follow-up timeline
- Optional: Drop the one-pager PDF in the meeting chat

---

## Prep Checklist (Before Meeting)

- [ ] Fill in traction numbers (Block 4)
- [ ] Decide who's presenting (Diamond? Diamond + Brett? Diamond + Alex?)
- [ ] Have `BASIS-One-Pager.pdf` ready for screen share
- [ ] Test launchonbasis.com loads clean
- [ ] Have SDK docs URL ready: https://launchonbasis.com/sdk-docs
- [ ] Brief Alex on technical questions that might come up
- [ ] Confirm meeting link/time with Walter

---

## What NOT to Say

- Don't lead with tokenomics or airdrop details — save for later conversations
- Don't get into Solidity internals unless Walter asks — he's BD, not a dev
- Don't promise audit or TGE dates you can't keep
- Don't badmouth other BSC projects — position as additive
- Don't spend time explaining what AI agents are — Walter uses them daily
- Don't oversell the points system — not relevant for this conversation

---

## If You Only Get 10 Seconds

_"Basis is the first DeFi ecosystem architecturally designed to survive the agent economy — unruggable tokens, zero-liquidation lending, uncapped prediction markets, and an integration layer that turns every AI agent into a business. All on BNB Chain."_
