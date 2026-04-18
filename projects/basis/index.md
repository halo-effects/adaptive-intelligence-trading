# Basis Project — Quick Reference Index

_Last updated: 2026-04-16 (v5 — Phase 1 live, SDK published, points system live)_

## Documents

| File | Contents |
|---|---|
| `project-plan.md` | Master strategy document (all sections below) |
| `dev-plan.md` | Technical build plan — what's deployed, in progress, and remaining |
| `mechanics-corrections.md` | Source-of-truth corrections from Diamond's live platform walkthrough (2026-03-12) |
| `update-log-2026-03-14.md` | Changelog for 2026-03-14 documentation consolidation |
| `strategy-decision-tree.md` | **Multi-path strategy guide** — full decision tree for agents (7 phases, 5 capital deployment paths, composability matrix) |
| `fee-schedule.md` | **Single source of truth** for all platform fees — trading, loans, leverage, creation, vault |
| `gitbook-corrections-for-alex-2026-03-14.md` | 5 corrections for the live GitBook site (ready for Alex) |
| `sdk-gap-analysis-2026-03-14.md` | Gap analysis of Alex's SDK reference |
| `sdk-docs-2026-03-16.md` | **Full SDK documentation from Alex** — 13 modules, Python + TypeScript, all read/write methods, examples, error handling |
| `standup-2026-03-17.md` | Standup — progress, blockers, questions for Alex, priorities |
| `standup-latest.md` | **Latest project state** (2026-04-16) — canonical status reference for standup generation |
| `index.md` | This file — quick reference to sections |

### Polymarket Scout (`polymarket-scout/`)
| File | Contents |
|---|---|
| `SKILL.md` | OpenClaw `polymarket-scout` skill definition — scout Polymarket for Basis-worthy markets |
| `scripts/scout.py` | Fetch, score, and rank Polymarket markets — prioritizes multi-outcome (3+) for Basis |
| `references/api.md` | Polymarket Gamma API reference (endpoints, data model, pagination) |
| `polymarket-scout.skill` | Packaged `.skill` file ready for distribution |

### Decision Trees (`skill-scaffold/decision-trees/`) — Agent Strategy Maps
| File | Contents |
|---|---|
| `master-overview.md` | **Start here** — how all 3 trees connect, entry points by agent type, cross-tree synergies |
| `prediction-markets.md` | Full decision tree for prediction market flow (7 phases, 5 capital paths) |
| `token-launch.md` | Full decision tree for token creation flow (6 phases, surge tax strategy, creator monetization) |
| `capital-management.md` | Full decision tree for loans/vault/leverage (5 phases, loan loops, vault refinance, velocity scoring) |

### Strategy Scripts (`skill-scaffold/strategies/`) — Pre-Packaged Pathways
| Directory | Strategies |
|---|---|
| `predictions/` | polymarket-mirror, probability-arb, creator-fee-farm, loan-bet-combo, full-stack |
| `tokens/` | launch-and-promote, bonding-sniper, loan-compound, vault-yield, token-portfolio |
| `cross-platform/` | capital-recycler, points-optimizer, referral-network |

### Skill Scaffold (`skill-scaffold/`)
| File | Contents |
|---|---|
| `SKILL.md` | OpenClaw `basis-defi` skill definition — commands, config, quick start |
| `scripts/create-prediction.py` | Create Predict+ markets — **wired to SDK** (`client.prediction_markets.create_market()`) |
| `scripts/bet.py` | Place bets on prediction outcomes — **wired to SDK** (`client.prediction_markets.buy()` + order book) |
| `scripts/create-token.py` | Launch Stable+ or Floor+ tokens — **wired to SDK** (`client.factory.create_token()`) |
| `scripts/trade.py` | Buy/sell on Basis DEX — **wired to SDK** (`client.trading.buy()` / `sell()` / `leverage_buy()`) |
| `scripts/lend.py` | Take, extend, repay loans — **wired to SDK** (`client.loans.*`) |
| `scripts/vault.py` | STASIS vault — stake, borrow, refinance — **wired to SDK** (`client.staking.*`) |
| `scripts/portfolio.py` | Portfolio + net P&L summary — **wired to SDK** (`client.api.*` + `client.trading.get_usd_price()`) |
| `scripts/points.py` | Airdrop points, Molt tier, ACS score — **wired to SDK** (points backend live) |
| `references/api-reference.md` | Complete contract function reference — all 13 contracts (from Alex's SDK reference, 2026-03-14) |
| `references/token-frameworks.md` | Stable+, Floor+, Predict+ token mechanics |
| `references/earning-guide.md` | Quick reference: all earning paths + point values |
| `references/composability-matrix.md` | What connects to what — every action → what it unlocks, blocked combos, capital flow |

### Docs Drafts (`docs-drafts/`) — Ready for GitBook
| File | Contents |
|---|---|
| `getting-started-agents.md` | Agent quickstart — SDK install to first trade in 5 min |
| `earning-guide.md` | Comprehensive earning guide — all paths, points, multipliers |
| `strategy-playbooks.md` | 6 pre-built strategies: leverage, loan-bet, exit timing, vault, mirror, recycler |
| `faq.md` | High-level FAQ — general + agent-specific questions |

### Content / Articles (`content/articles/`) — Blog + X Articles
| File | Contents |
|---|---|
| `01-why-ai-agents-need-their-own-financial-layer.md` | **Article 1** — The thesis: why agents can't use human DeFi, what agent-native looks like, 5 requirements, market signals |
| `02-polymarket-slot-machine-vs-basis-business.md` | **Article 2** — Head-to-head Polymarket comparison with real $836M data, payout tables, agent stack gap, earnings loop |

### Outreach (`outreach/`) — Marketing & Recruitment
| File | Contents |
|---|---|
| `founding-lobster-pitch.md` | "Earn Your Shell" pitch deck for agent operators |
| `outreach-templates.md` | Personalized messages for 6 Tier 1 targets + follow-up |
| `content-templates.md` | Social media templates: posts, threads, tutorials, P&L receipts |
| `lobster-report-format.md` | Weekly "Lobster Report" template — auto-generatable |

---

## Project Plan Sections

| # | Section | Key Topics |
|---|---|---|
| 1 | **The Thesis** | Moltbook vision, why Basis for agents |
| 2 | **Messaging Repositioning** | New narrative: "Agent-Native DeFi", "Lobster Economy", "Earn Your Shell" |
| 3 | **Technical Tooling — Agent SDK** | OpenClaw `basis-defi` skill, API endpoints, strategy scripts, monitors, wallet standard |
| 4 | **Agent-Native Features** | Auto-Predict, Predict+ composability (payout mechanics, AMM, strategy paths A/B, exit timing, trader-to-bettor pot, flattening solution), Agent Token Launchpad, Self-Refinancing, Moltbook social layer |
| 5 | **Platform Mechanics (4e)** | Elastic supply, Floor+ stability dial (0%–100%), dynamic leverage (up to ~36x), surge tax, liquid vesting, STASIS Vault (wSTASIS), lending (internal liquidity, time-only risk), BASIS vs STASIS distinction |
| 6 | **GTM: The 100K Agent Blitz** | 🐚 SHELL (100 Founding Lobsters) → 🦞 MOLT (10K agents) → 🔴 LIVE (100K agents) → 💎 TGE (250K+). Growth-first, zero-friction onboarding, Lobster Army as marketing machine. Three-tier friction model. |
| 6A | **Founding Lobster Recruitment** | 3-tier target list, recruitment funnel, week-by-week timeline |
| 6B | **Points System Design** | Point values per action, social engagement tasks (X + Moltbook), multipliers, Molt tiers (🥚→💎), 6-layer anti-sybil defense, API spec, seasons |
| 7 | **Competitive Moat** | Switching costs, category ownership vs Polymarket/Pump.fun |
| 8 | **BASIS Token Lockup** | Notice-based staking (not fixed locks), 5 tiers, loyalty escalator, airdrop haircut model (1.0x/2.5x weighted), presale/airdrop specifics |
| 9 | **Testing Phase** | USDB (fake USDC) on BNB Chain mainnet, points carry over to real airdrop |
| 10 | **Token Allocation & Presale** | 9-bucket allocation, 4-round presale ($0.15 TGE, $30M raise), USDC deployment, float analysis, FDV mitigation |
| 11 | **What Motivates Agents** | 4 tiers (survival→agency), USDC-native earnings, earn-to-grow loop |
| 12 | **Dev Plan — Build Responsibilities** | All 13 contracts deployed. Alex built SDK (contract ref delivered 2026-03-14). Points system still to build. See `dev-plan.md` for full status |
| 13 | **Docs Review Notes** | Original strengths + pressure-test areas |
| 14 | **Competitive Analysis** | BNB Chain prediction markets (Predict.fun, Opinion, Probable, Myriad) — funding, points models, where Basis wins, strategic takeaways |
| 15 | **Future Considerations** | x402 protocol (Coinbase/Cloudflare) — watch & wait, design for compatibility, potential revenue from x402-gated data |

---

## Key Decisions Made

| Decision | Status | Details |
|---|---|---|
| TGE Price | ✅ $0.15 | FDV $150M, approved by Brett + Diamond |
| Chain | ✅ BNB Chain | Sub-cent gas, fast blocks, EVM compatible |
| Staking Model | ✅ Notice-based | Not fixed locks — all tiers use notice periods |
| Airdrop Model | ✅ Single pool (25%) with ACS weighting | Agent Confidence Score multiplier — spectrum, not binary |
| Airdrop Haircut | ✅ Weighted pool | 50% haircut for no-lock, redistributed to Committed (1.0x) + Diamond (2.5x) |
| Leverage Model | ✅ Dynamic (up to ~36x) | Depends on pool depth + position size. `mixedBuy` for SDK/agents only. Position splitting for effective leverage |
| Lending | ✅ Internal liquidity | No external LPs. Liquidation = time only, never price |
| Creator Earnings | ✅ USDC | Not tokens — immediately spendable |
| Presale Allocation | ✅ 30% (300M) | 4 rounds, all notice-locked with USDC yield |
| DEX Liquidity | ✅ 5% tokens + $7.5M USDC | 1:1 matched, $15M total |

---

## Pending Decisions

| Item | Status | Notes |
|---|---|---|
| Exact loan interest rate | ⏳ | Diamond said "low single digits APR" — TBC |
| Surge tax parameters | ⏳ | Feature exists, defaults TBD |
| Oracle provider for BNB | ⏳ | Chainlink / API3 / custom |
| Audit timeline | ⏳ | Before TGE, budget from raise |
| Alex's preferred API stack | ✅ | Alex building SDK himself — SDK published on npm/PyPI (April 2026) |

---

## Team

| Name | Role |
|---|---|
| Brett (@BrettonTG) | Strategy, vision |
| Diamond (@DiamondHandsDude) | Platform architecture, tokenomics |
| Alex (@Alexcrypto32) | Lead developer |
| Atlas (@chairmanAtlas) | Team member |
| GeeGee (@GeeGee_Claw_bot) | AI advisor (Lobster 🦞) |
