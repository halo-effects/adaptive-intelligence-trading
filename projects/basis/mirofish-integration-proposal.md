# MiroFish × Basis — Integration Proposal

_Created: 2026-03-27 | Status: Exploratory | Author: Brett + GeeGee_

---

## What Is MiroFish

Open-source swarm intelligence engine (MIT license). Spawns thousands of AI agents with unique personalities, memories, and social connections into a simulated "digital world." Agents debate, argue, persuade, and evolve — emergent behavior predicts outcomes.

- **GitHub**: github.com/666ghj/MiroFish — 44K+ stars, 6K+ forks (as of 2026-03-27)
- **Creator**: Guo Hangjiang, 20-year-old undergrad in Beijing. Built in 10 days.
- **Funding**: $4.1M from Shanda Group founder Chen Tianqiao within 24 hours of demo
- **Powered by**: CAMEL-AI's OASIS framework
- **Runs**: Locally via Docker (Node.js frontend + Python/Flask backend)
- **Estimated installations**: 2,000–5,000 active (based on fork count proxy)

### How It Works

1. Upload seed data (news, financial signals, policy drafts, reports)
2. Describe prediction question in natural language
3. MiroFish builds a simulated world, populates it with agents
4. Agents interact, debate, form opinions, evolve
5. ReportAgent synthesizes results into a detailed prediction report
6. User can chat with any individual agent or the ReportAgent post-simulation

### Existing Traction in Prediction Markets

One developer plugged MiroFish into a Polymarket trading bot — simulated 2,847 digital humans before every trade — reported $4,266 profit across 338 trades. Proof of concept for prediction-market-to-trading pipeline already exists.

---

## The Opportunity for Basis

### Core Idea

Turn MiroFish from a research tool into a **prediction market creation pipeline** for Basis.

### User Flow

```
1. User/agent researches a topic in MiroFish
   → "What happens if the EU passes AI regulation X?"

2. Swarm simulation surfaces a debatable outcome
   → "70% of agents think it passes but with major amendments"

3. One click → "Launch this as a prediction market on Basis"
   → Question, outcomes, and context pre-populated from simulation

4. Creator takes a position (they already have conviction from simulation)
   → Instant liquidity on their own market

5. Other agents discover the market on Basis, bet on it
   → Fees flow to creator + platform
```

### Why This Is Powerful

- **Market creation flywheel**: MiroFish becomes an infinite source of well-formed prediction market questions. One of the hardest problems in prediction markets is generating good questions. This solves it.
- **Creator has built-in edge**: They've already simulated the outcome, so they're incentivized to create AND bet. Instant liquidity.
- **Agent factory for Basis**: Every MiroFish user is potentially a Basis market creator and trader. Their platform feeds agents (and humans) directly into the Basis ecosystem.
- **Dual revenue**: Creator earns from market resolution + trading fees on their market, AND from positions they take based on simulation conviction.

### Partnership Value Exchange

| Basis Gets | MiroFish Gets |
|---|---|
| Pipeline of prediction market creators with pre-formed conviction | Monetization layer for simulations (currently reports just sit there) |
| Well-structured market questions generated from research | "Your prediction research can now make money" |
| Every MiroFish user → potential Basis agent | Increased utility and stickiness for their platform |
| Technical audience (44K stars = developer-heavy) | Real-world application beyond demo simulations |

---

## Integration Paths

### Path 1: ReportAgent Tool (Quick Win) ⭐ Recommended

Build a custom tool for MiroFish's ReportAgent that formats simulation output into a Basis `predictionMarkets.createMarketWithMetadata()` call. Submit as a PR to the MiroFish repo.

**Effort**: Low (the ReportAgent is explicitly designed for extension with "domain-specific metrics")
**Visibility**: High (44K-star repo, PR would be noticed by the community)
**Technical**: ReportAgent tool → format question + outcomes from simulation → call Basis SDK → return market URL

### Path 2: Basis MCP Server

Build a Basis MCP (Model Context Protocol) server that any agent platform can connect to — not just MiroFish. MiroFish users would be natural early adopters given the prediction market overlap.

**Effort**: Medium
**Visibility**: Broader (any MCP-compatible platform can use it)
**Technical**: MCP server exposing Basis SDK methods (createMarket, placeBet, getMarkets, etc.)

### Path 3: Fork & Standalone Integration

Fork MiroFish, add a `/api/launch-to-basis` endpoint to the Flask backend, ship as a "MiroFish + Basis" distribution.

**Effort**: Medium
**Visibility**: Lower (separate fork, not in main repo)
**Technical**: New Flask endpoint → Basis SDK call, plus UI button in frontend

### Recommendation

**Start with Path 1**, then build Path 2 as the longer-term play. Path 1 gets Basis in front of 44K+ developers immediately with minimal effort. Path 2 creates a general-purpose integration layer that outlasts any single platform.

---

## Additional Use Cases Beyond Market Creation

1. **Prediction Market Oracle**: Agent runs MiroFish simulations before betting on existing Basis markets. Swarm consensus as trading signal.

2. **Token Launch Sentiment Testing**: Before creating a Floor+ token around a narrative, simulate crowd reaction. Stress-test token concepts before deploying capital.

3. **Reef Content Strategy**: Super Referrer agents simulate which educational content / narratives would resonate most before posting on The Reef.

4. **Market Maker with Conviction**: Simulate outcomes before taking sides on Basis prediction markets. Consistent edge over agents using simpler heuristics.

---

## Risks & Caveats

- **No published benchmarks**: "Scarily accurate" is social media hype, not peer-reviewed evidence. The Polymarket trader's results are self-reported.
- **LLM token costs**: Each simulation burns significant tokens. Hundreds of agents × dozens of rounds = expensive. This is the user's cost, not Basis's.
- **Prediction quality**: Depends entirely on the underlying LLM's domain understanding. Garbage in, garbage out still applies.
- **Very new project**: 44K stars in weeks, but no proven longevity. Could be a flash in the pan.
- **No existing plugin ecosystem**: No marketplace, no MCP server, no extension registry yet. First-mover advantage, but also no established patterns to build on.

---

## Next Steps

- [ ] Diamond / Brett: Decide if MiroFish integration is worth pursuing in current phase
- [ ] If yes: Scope Path 1 (ReportAgent tool) as a lightweight proof of concept
- [ ] Explore reaching out to MiroFish team about potential partnership
- [ ] Monitor MiroFish development for plugin/marketplace announcements
- [ ] Consider including MiroFish integration as an example in Basis docs (new archetype: "The Simulator")

---

_MiroFish simulates. Basis monetizes. Clean separation, mutual benefit._
