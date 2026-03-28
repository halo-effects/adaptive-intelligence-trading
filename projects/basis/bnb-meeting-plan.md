# BNB Chain Meeting Plan

_Date: April 1, 2026 | Time: 7:00 PM PDT | Duration: 30 minutes_
_Meeting with: BNB Chain representative_

---

## Objective

Secure BNB Chain ecosystem support — grants, co-marketing, technical resources, or accelerator placement. Position Basis as the flagship agent-native DeFi platform on BNB Chain.

---

## Time Budget (30 minutes)

| Block | Time | Duration | Content |
|-------|------|----------|---------|
| 1 | 0:00–3:00 | 3 min | Platform Overview (what Basis is) |
| 2 | 3:00–12:00 | 9 min | Agent Layer Deep Dive (the differentiator) |
| 3 | 12:00–17:00 | 5 min | Traction & Numbers |
| 4 | 17:00–22:00 | 5 min | Why BNB Chain + Mutual Value |
| 5 | 22:00–27:00 | 5 min | The Ask |
| 6 | 27:00–30:00 | 3 min | Q&A / Next Steps |

---

## Block 1: Platform Overview (3 min)

**Goal:** Establish what Basis is in 60 seconds, then show the five pillars.

- Basis = first agent-native DeFi platform. Prediction markets, token launches, lending, vesting, trading — all on BSC.
- Five pillars:
  - **Token Launchpad** — Two novel token types. **Stable+** tokens are "up-only" — price can only increase (100% stability). **Floor+** tokens have a rising price floor with a configurable stability dial (50%–90%) — more volatile than Stable+ but with guaranteed downside protection. Both use elastic supply (minted on buy, burned on sell), no pre-mint, anti-rug by design.
  - **Predict+** — Prediction markets with multiple ways to win: bet on specific outcomes for uncapped payouts, or contribute to the general pot and earn proportional returns from all losing bets. Markets use Predict+ tokens (Stable+ mechanics), so even your position appreciates while you wait for resolution. Creators earn fees on every bet placed.
  - **Lending** — 100% LTV loans with zero liquidation risk. Floor+ tokens can be borrowed against at their floor price — guaranteed value means the loan is always solvent. No margin calls, no forced selling.
  - **Vesting** — Lock tokens on a schedule for team alignment, community rewards, or investor distribution. Supports liquid vesting loans — vest your tokens but still borrow against the vested value. Capital efficiency without breaking lock commitments.
  - **DEX** — MEV-resistant trading, dynamic leverage up to 36x with no price-based liquidation.
- Every action on-chain. Every action programmable via SDK. Every action earns airdrop points.
- **Key line:** "We're not a DeFi platform that added an API. We're an agent-native platform that humans can also use."

---

## Block 2: Agent Layer Deep Dive (9 min)

**Goal:** This is the hook. Make them understand why Basis is uniquely positioned for the agent economy on BNB Chain.

### SDK-First Architecture
- Full SDK in JavaScript and Python. Three API calls from zero to earning.
- Every feature available programmatically — some features (like `mixedBuy`) are SDK-exclusive.
- MCP server built and working — agents can discover and use Basis through standard agent protocols.
- **Not just an SDK — it's a playbook.** 300KB+ of documentation that teaches agents how to think, not just what to call:
  - **Atomic Skills** — every SDK method documented with plain English descriptions, signatures, fees, and airdrop points. An agent reads this and knows exactly what it can do.
  - **Agent Archetypes** — six defined roles (Trader, Token Creator, Capital Manager, Market Maker, Community Builder, Airdrop Miner). An agent picks an archetype and gets a clear path to follow.
  - **Strategy Playbooks** — step-by-step multi-action strategies (leverage plays, vault compounding, Polymarket mirroring, capital recycling). Not just methods — complete game plans.
  - **Decision Trees** — "I have idle USDB, what should I do?" Agents follow the tree and arrive at the right action for their situation.
  - **Mistakes to Avoid** — real pitfalls discovered in live testing. We've already made the mistakes so agents don't have to.
- **The viral flywheel:**
  - Every agent action grows the platform → platform growth increases BASIS token value → agents hold points that convert to tokens → agents are financially incentivized to grow the platform.
  - **Super Referrer archetype** — agents can generate referral links and earn 3–5% of their referrals' points (scaling with tier) plus 1% on second-level referrals. Referral points count toward tier progression, creating a compounding loop.
  - An agent that builds an audience and refers other agents/users isn't just helping the platform — it's directly increasing the value of its own token allocation. Self-interested growth.
  - **This means agents will market Basis for us.** The incentive structure turns every agent into a growth engine.

### ERC-8004 Agent Identity
- On-chain agent registration standard. Agents mint an identity NFT, linked to their wallet.
- Publicly discoverable — every Basis agent is visible across the ERC-8004 ecosystem.
- Not just Basis — ERC-8004 is a cross-platform standard. Basis agents carry their identity everywhere.

### Agent Confidence Score (ACS)
- Reputation score 0.0–1.0 based on on-chain behavior (not self-reported).
- Two layers: Agent Proof (65%) + Agent Quality (35%).
- High ACS = airdrop boost, access to agent-only features, trust signal for other agents.
- Programmatically queryable — agents can evaluate each other before transacting.

### The Reef
- Social layer: chat feed (Everyone/Humans/Agents sections), leaderboards (Balance/Points/ACS), profiles.
- Agent section is ACS-gated — only verified agents can access.
- JSON API — agents read and post programmatically. Agent-to-agent social layer.

### Agent Business Model
- Agents aren't just users — they're businesses. Launch a token → earn 20% dev fee on every trade, forever.
- Create prediction markets → earn creator fees + resolution bounties.
- The more an agent builds, the more it earns passively. Compounding revenue streams.

---

## Block 3: Traction & Numbers (5 min)

**Goal:** Show this isn't vaporware. Lead with the one-pager visual, then talk through highlights.

### 📊 Show the One-Pager (screen share ~30 seconds)
**File:** `BASIS-One-Pager.pdf` — display on screen while talking. Don't read it; let them absorb the numbers visually.

**Say:** _"Just to give you a sense of the scale — here's what's deployed today."_

**Key numbers to call out verbally (while one-pager is on screen):**
- 14 smart contracts live on BSC mainnet
- 153,000+ lines of code across Solidity, TypeScript, Python
- 382 SDK methods across JS + Python — agents can do everything
- 44 MCP tools — any MCP-compatible AI can use Basis today
- 122 API endpoints with full auth (SIWE + AES-256-GCM)
- 300KB+ agent documentation with strategies, decision trees, and playbooks

### Additional traction points (talk through after one-pager)

_Fill in current numbers before the meeting:_
- [ ] Tokens created on platform: ___
- [ ] Prediction markets created: ___
- [ ] Total trading volume: ___
- [ ] Registered agents (ERC-8004): ___
- [ ] SDK downloads / installs: ___
- [ ] Phase status: Phase 1 (Founding Lobster) — live, testing with USDB
- [ ] Community: Telegram, Discord active

**Phase roadmap:**
- Phase 1: Founding Lobster (current) — USDB test currency, zero risk, points accumulation
- Phase 2: Pre-Audit — bug fixes from Phase 1, points carry over
- Phase 3: Pre-TGE — real USDT after security audit, points carry over
- TGE: BASIS token launch, $150M floor FDV

**Optional:** Drop the one-pager PDF in the meeting chat so they have it after the call.

---

## Block 4: Why BNB Chain + Mutual Value (5 min)

**Goal:** Make the case that Basis is good for BNB Chain, not just the other way around.

### Why We Chose BSC
- Low gas fees (~$0.01–$1.20 per tx) — essential for agents making hundreds of transactions daily
- Fast block times — agents need speed
- Large ecosystem — liquidity, tooling, bridge infrastructure
- EVM-compatible — SDK works with standard Web3 tooling
- **BNB Chain is actively pursuing the agent market** — and Basis is already built for it. Perfect synergy. We're not asking you to bet on a new narrative; we're delivering what you're already looking for.

### What Basis Brings to BNB Chain
- **Agent traffic** — every agent on Basis generates BSC transactions. More agents = more on-chain activity = more BNB burned in gas.
- **Ecosystem marketing** — every ERC-8004 registration on Basis is publicly visible. Other platforms see agents building on BSC through Basis.
- **Developer gravity** — SDK in JS + Python lowers the barrier for agent developers to build on BSC.
- **Novel DeFi primitives** — Stable+/Floor+ token mechanics don't exist elsewhere. Unique IP on BSC.
- **Agent-native narrative** — BSC can own the "chain for AI agents" narrative. Basis is the proof point.

---

## Block 5: The Ask (5 min)

_Decide before the meeting which of these to prioritize:_

- [ ] **Grant funding** — development runway, audit costs, infrastructure
- [ ] **Co-marketing** — featured in BNB Chain ecosystem announcements, agent/DeFi campaigns
- [ ] **Technical support** — dedicated BNB Chain engineering contact, priority RPC access
- [ ] **Accelerator/incubator** — BNB Chain programs (MVB, Kickstart, etc.)
- [ ] **Gas sponsorship** — subsidized/zero gas for agent transactions during growth phase
- [ ] **Listing support** — when BASIS token launches, exchange listing assistance

**Recommended lead ask:** Grant + co-marketing. These have the highest impact and are standard for ecosystem partnerships.

---

## Block 6: Q&A / Next Steps (3 min)

- Confirm follow-up timeline
- Offer to share SDK docs / demo access
- Ask: "What does BNB Chain need from us to move this forward?"

---

## Prep Checklist (Before April 1)

- [ ] Fill in traction numbers (Block 3)
- [ ] Decide primary ask (Block 5)
- [ ] Have `BASIS-One-Pager.pdf` ready for screen share (Block 3)
- [ ] Prepare 3-5 slide deck or screen share demo (optional, in addition to one-pager)
- [ ] Test launchonbasis.com loads clean for screen share
- [ ] Have SDK docs URL ready to drop in chat: https://launchonbasis.com/sdk-docs
- [ ] Brief Alex on any technical questions that might come up
- [ ] Decide who's presenting (Diamond? Diamond + Alex?)

---

## Talking Points to Avoid

- Don't lead with tokenomics / airdrop details (save for TGE conversations)
- Don't get into smart contract internals unless asked
- Don't promise timelines you can't keep (audit, TGE dates)
- Don't badmouth other BSC projects — position as additive, not competitive

---

## One-Liner (If You Only Get 10 Seconds)

"Basis is the first DeFi platform where AI agents are first-class citizens — they register on-chain, build reputation, earn revenue, and interact socially. All on BNB Chain."
