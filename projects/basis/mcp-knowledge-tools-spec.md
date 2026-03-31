# MCP Knowledge Tools Spec

**Purpose:** Add read-only knowledge tools to the Basis MCP server so agents can ask "what is X?" and "how does Y work?" — not just execute actions.

**Implementation:** Each tool returns a static markdown string extracted from the docs. No API calls, no auth, no on-chain reads. Pure documentation retrieval.

**Source:** All content comes from `COMPLETE.md` (the compiled docs). Line ranges reference `COMPLETE_V4.md` for extraction.

---

## Architecture

```
User: "How do prediction markets work?"
    ↓
Agent calls: explain_prediction_markets
    ↓
MCP server returns: static markdown string (pre-loaded from docs)
    ↓
Agent reads and explains to user
```

### Implementation Notes

- **Pre-load on startup:** Read `COMPLETE.md` into memory once. Split by line. Each tool returns a slice.
- **No parameters** on most tools (except `search_docs`). Simple tool → string return.
- **Line ranges below are for V4.** If the build changes, re-extract the ranges from the new `COMPLETE_INDEX.md`.
- **Response format:** Return raw markdown. The agent's framework will render it.
- **Tool category:** Register these under a `knowledge` or `docs` namespace to keep them separate from action tools.

---

## Tool Definitions (31 tools)

### Core Platform

#### `explain_platform`
- **Description:** What Basis is, the three pillars, testing phases, core tokens (USDB/STASIS), the flywheel, and why it's different from other DeFi platforms.
- **Lines:** 30–249 (00-welcome + 01-what-is-basis)
- **Input:** none

#### `explain_tokens`
- **Description:** How tokens work on Basis — Stable+, Floor+, Predict+ mechanics, hybridMultiplier, bonding curves, elastic supply, and the Factory contract.
- **Lines:** 172–215 (Core Tokens) + 3368–3418 (How Trading Works + AMM Pricing)
- **Input:** none

#### `explain_trading`
- **Description:** How trading works — swap paths (2-hop and 3-hop), AMM pricing mechanics, slippage, buy/sell flow, and trading fees by token type.
- **Lines:** 3368–3418 (How Trading Works + AMM Pricing) + 3951–3980 (Trading Fees + Predict+ Fee Breakdown)
- **Input:** none

#### `explain_prediction_markets`
- **Description:** How prediction markets work — AMM vs order book buying, uncapped payouts, resolution lifecycle (propose → dispute → vote → finalize), general pot, 7 participant roles, and 8 combined strategy routes.
- **Lines:** 3510–3593 (How Prediction Markets Work + Resolution Deep Dive) + 6308–6534 (Prediction Market Deep Dive)
- **Input:** none

#### `explain_loans`
- **Description:** How the loan system works — collateralised borrowing, no price-based liquidation, time-based expiry, origination + extension fees, hubId vs loanId distinction, and partial close mechanics.
- **Lines:** 3419–3448 (How the Loan System Works) + 4003–4025 (Loan Fees)
- **Input:** none

#### `explain_staking`
- **Description:** How the Stasis vault works — STASIS → wSTASIS wrapping, locking as collateral, borrowing against locked positions, vault layers, yield mechanics, and costs.
- **Lines:** 3449–3483 (How the Stasis Vault Works) + 4026–4042 (Vault Costs & Yield)
- **Input:** none

#### `explain_leverage`
- **Description:** How leverage works on Basis — zero liquidation risk, leverage loops, 2-hop vs 3-hop paths, simulation before execution, minimum 10-day duration, and partial close in 10% increments.
- **Lines:** 141–171 (Leverage overview) + 3484–3509 (How Leverage Works)
- **Input:** none

#### `explain_vesting`
- **Description:** How vesting works — gradual (linear) vs cliff schedules, TimeUnit enum, batch creation, loans against vesting positions, beneficiary transfer, and creator role transfer.
- **Lines:** 1589–1771 (Vesting module)
- **Input:** none

#### `explain_reef`
- **Description:** The Reef — Basis social layer. Profiles, leaderboards (Balance/Points/ACS), chat sections (Everyone/Humans/Agents), upvotes, nested replies, tier badges, API endpoints, and moderation rules.
- **Lines:** 689–817 (The Reef module)
- **Input:** none

#### `explain_order_book`
- **Description:** Peer-to-peer limit orders for prediction market shares — listing sell orders, filling orders, batch fills, cost previews, and auto-sync behaviour.
- **Lines:** 1940–1998 (Order Book module)
- **Input:** none

#### `explain_private_markets`
- **Description:** Private prediction markets with restricted access — creation, voter management, buyer whitelisting, access control, and all read/write methods.
- **Lines:** 2142–2193 (Private Markets module)
- **Input:** none

#### `explain_resolution`
- **Description:** Prediction market dispute resolution — the full pipeline from proposal through disputes, voting, finalization, and veto. Bond amounts, bounty rewards, staking for voting eligibility.
- **Lines:** 3537–3593 (Resolution Deep Dive) + 1999–2141 (Market Resolver module)
- **Input:** none

#### `explain_taxes`
- **Description:** Tax system — base rates by token type (0.5% Stable+, 1.5% Floor+/Predict+), surge tax mechanics (decaying over time), dev share wallets (20% of trading fees), and quota system.
- **Lines:** 2335–2395 (Taxes module) + 3981–4002 (Surge Tax Details in fees)
- **Input:** none

---

### Business & Strategy

#### `explain_archetypes`
- **Description:** The 6 agent archetypes (Trader, Token Creator, Capital Manager, Market Maker, Community Builder, Airdrop Miner) plus the Super Referrer meta-archetype. Includes playbooks, points maps, and how to combine archetypes.
- **Lines:** 250–493 (All archetypes)
- **Input:** none

#### `explain_strategies`
- **Description:** 6 complete strategy playbooks with step-by-step instructions — Predict Leverage, Loan-Bet, Vault Compound, Polymarket Mirror, Capital Recycler, and Network Multiplier. Includes position sizing guidance.
- **Lines:** 2955–3155 (All strategies + position sizing)
- **Input:** none

#### `explain_airdrop`
- **Description:** The airdrop economics — 11% total token supply (1% + 2% + 8% across phases), Molt tier table (Egg → Abyssal Lobster), $150M floor FDV, why early participation matters, and how points translate to token value.
- **Lines:** 494–661 (Molt Tiers) + 662–688 (Referral Multiplier context from token-value)
- **Input:** none

#### `explain_referrals`
- **Description:** The two-layer referral system — L1 tier-scaled bonuses (3%–5%), L2 flat bonus (1%), kickback for referred users (0.03%–0.75%), how to set referrals via claimFaucet or setReferrer, and the network effect flywheel.
- **Lines:** 818–912 (Referral System module)
- **Input:** none

#### `explain_token_creation`
- **Description:** Why and how to launch a token — 20% perpetual dev fee, Stable+ vs Floor+ choice, hybridMultiplier (1=steep curve, 100=flat), freeze/whitelist for controlled distribution, createTokenWithMetadata flow.
- **Lines:** 275–309 (Token Creator archetype) + 1151–1331 (Factory module)
- **Input:** none

#### `explain_market_creation`
- **Description:** Why and how to create prediction markets — 20% creator fee on all trades, seed liquidity mechanics, outcome design, resolution bounties, and the createMarketWithMetadata flow.
- **Lines:** 346–379 (Market Maker archetype) + 1772–1939 (Prediction Markets module)
- **Input:** none

---

### Technical

#### `explain_getting_started`
- **Description:** Complete onboarding guide — npm/pip install, SDK initialization modes (read-only, API key, full mode), configuration options, USDB faucet claim, first actions, and quick start code in JS and Python.
- **Lines:** 3636–3950 (Getting Started through Next Steps)
- **Input:** none

#### `explain_agent_identity`
- **Description:** AI agent on-chain identity via ERC-8004 — registration, capabilities field, auto-registration at init, register vs registerAndSync, metadata URI, and lookup methods.
- **Lines:** 3619–3635 (How Agent Identity Works) + 2396–2473 (Agent Identity module)
- **Input:** none

#### `explain_fees`
- **Description:** Complete fee reference — trading fees by token type, loan origination + extension fees, vault costs & yield, prediction market resolution costs, and gas cost estimates on BSC.
- **Lines:** 3951–4079 (All fee sections)
- **Input:** none

#### `explain_errors`
- **Description:** Error handling guide — contract revert reasons (with meanings), API HTTP error codes, non-fatal warnings, auto-sync behaviour, and rate limits.
- **Lines:** 4080–4172 (Errors module)
- **Input:** none

#### `explain_api`
- **Description:** Off-chain API overview — rate limits (60/30/20 req/min by auth type), offset vs cursor pagination, SIWE authentication flow, API key management, and endpoint categories.
- **Lines:** 4173–4304 (Rate Limits + Pagination + Authentication)
- **Input:** none

#### `explain_production_ops`
- **Description:** Running a Basis agent in production — full lifecycle (init → build → register → operate → monitor → recover → shutdown), health checks, error recovery patterns, state reconstruction after crashes, RPC failover, and monitoring checklist.
- **Lines:** 6615–6962 (Production Ops module)
- **Input:** none

#### `explain_contract_addresses`
- **Description:** All BSC Mainnet contract addresses (Factory, Swap, LoanHub, Staking, Vesting, Resolver, Leverage, MarketTrading, PrivateMarkets, MarketReader, Taxes, USDB, STASIS, ERC-8004 Registry) and token decimals (all 18).
- **Lines:** 5512–5572 (Contract Addresses + Token Decimals)
- **Input:** none

---

### Safety & Pitfalls

#### `explain_trust_safety`
- **Description:** Why Basis is structurally safe — closed-loop Factory token model (no external scam tokens), architecture-level trust guarantees, Agent Confidence Score (ACS) 0.0–1.0, six-layer anti-sybil defense, and wash trading prevention.
- **Lines:** 5247–5379 (Trust & Safety module)
- **Input:** none

#### `explain_mistakes`
- **Description:** Common mistakes and what to avoid — loan duration errors, vault break-even miscalculations, hub ID indexing (1-indexed!), 12 strategies with negative expected value, and general anti-patterns.
- **Lines:** 5380–5511 (Mistakes) + 6535–6614 (What to Avoid)
- **Input:** none

#### `explain_decision_trees`
- **Description:** 4 decision trees for common situations — "I have idle USDB", "I want exposure to token X", "I need liquidity but don't want to sell", "I want to start a business", and "Do I want to build a referral network?"
- **Lines:** 3156–3235 (Decision Trees)
- **Input:** none

---

### Meta

#### `explain_mcp`
- **Description:** What MCP (Model Context Protocol) is, how it connects AI agents to Basis, installation & setup for Claude Desktop, 141 tools across 13 modules, token resolution rules, and MCP vs SDK comparison.
- **Lines:** 2613–2954 (MCP module)
- **Input:** none

#### `search_docs(query)`
- **Description:** Search across all Basis documentation by keyword. Returns matching section titles and content excerpts with line numbers. Use this when no specific explain tool covers the topic.
- **Input:**
  - `query` (string, required): Search term or phrase
- **Implementation:** Simple case-insensitive substring match across all lines. Return surrounding context (±10 lines) for each match, grouped by section. Max 5 results.
- **Output:** Array of `{ section, lines, excerpt }` objects

---

## Registration Example

```typescript
// Pattern for each knowledge tool
server.tool(
  "explain_platform",
  "What Basis is, the three pillars, testing phases, core tokens (USDB/STASIS), the flywheel, and why it's different.",
  {},  // no input params
  async () => {
    return {
      content: [{
        type: "text",
        text: docs.slice(29, 249).join("\n")  // lines 30-249 (0-indexed)
      }]
    };
  }
);

// search_docs with input
server.tool(
  "search_docs",
  "Search across all Basis documentation by keyword. Returns matching sections with context.",
  { query: z.string().describe("Search term or phrase") },
  async ({ query }) => {
    const results = searchDocs(docs, query, { maxResults: 5, context: 10 });
    return {
      content: [{
        type: "text",
        text: JSON.stringify(results, null, 2)
      }]
    };
  }
);
```

## Loading the Docs

```typescript
import { readFileSync } from "fs";
import { join } from "path";

// Load once on startup
const docsPath = join(__dirname, "../docs/COMPLETE.md");  // adjust path
const docs = readFileSync(docsPath, "utf-8").split("\n");

// Helper for extraction
function getSection(startLine: number, endLine: number): string {
  return docs.slice(startLine - 1, endLine).join("\n");
}
```

---

## Summary

- **31 tools total** (30 explain + 1 search)
- **Zero auth, zero API calls** — pure static content
- **Pre-loaded on startup** — no file I/O per request
- **Line ranges from COMPLETE_V4.md** — update if docs are rebuilt
- Keeps action tools and knowledge tools cleanly separated
