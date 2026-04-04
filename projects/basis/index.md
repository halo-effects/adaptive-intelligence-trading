# Basis Project — Quick Reference Index

_Last updated: 2026-04-04 (v7 — SDK+MCP published, Phase 1 pre-launch, smart contract audit underway)_

## Documents

| File | Contents |
|---|---|
| `project-plan.md` | Master strategy document (all sections below) |
| `dev-plan.md` | Technical build plan — what's deployed, in progress, and remaining |
| `docs-unified.md` | **⭐ THE COMPLETE AGENT GUIDE** — 37KB unified doc (11 parts), merged from knowledge base + all 5 doc drafts. Corrected by Diamond. Single source of truth for agent-facing documentation. |
| `mechanics-corrections.md` | Source-of-truth corrections from Diamond's live platform walkthrough (2026-03-12) |
| `update-log-2026-03-14.md` | Changelog for 2026-03-14 documentation consolidation |
| `strategy-decision-tree.md` | **Multi-path strategy guide** — full decision tree for agents (7 phases, 5 capital deployment paths, composability matrix) |
| `fee-schedule.md` | **Single source of truth** for all platform fees — trading, loans, leverage, creation, vault |
| `gitbook-corrections-for-alex-2026-03-14.md` | 5 corrections for the live GitBook site (ready for Alex) |
| `sdk-gap-analysis-2026-03-14.md` | Gap analysis of Alex's SDK reference |
| `sdk-docs-2026-03-16.md` | SDK documentation v1 from Alex (2026-03-16) — USDC 6 decimals, XETHER naming |
| `sdk-docs-2026-03-19.md` | SDK documentation v2 from Alex (2026-03-19) — 18-decimal USDB rework, STASIS naming |
| `sdk-docs-2026-03-20.md` | **SDK documentation v3 from Alex (2026-03-20)** — full 13-module reference, 3 init modes, all new contract addresses post-redeployment |
| `sdk-docs-latest.md` | Symlink/latest SDK docs |
| `sdk-docs-production/` | **⭐ CURRENT** — Production SDK docs v5 (April 1), 24 chapters, COMPLETE.md, llms.txt. Published at launchonbasis.com |
| `sdk-docs-v5-deploy/` | SDK docs v5 deploy version (March 31) |
| `points-system-build-spec-v2.md` | Agent Mining system build spec — point values, category diversity multiplier (up to 32x), Molt tiers, anti-sybil |
| `points-system-master-plan.md` | Points system master plan — strategy + phasing |
| `standup-2026-03-17.md` | Standup from 2026-03-17 |
| `standup-2026-03-19.md` | Standup from 2026-03-19 |
| `standup-2026-03-20.md` | Standup from 2026-03-20 |
| `standup-2026-03-21.md` | **Tomorrow's standup** — write tests on new deployment, docs review, points decisions |
| `index.md` | This file — quick reference to sections |

### SDK Packages
| Directory | Contents |
|---|---|
| `basis-sdk-python/` | Current Python SDK — updated 2026-03-20, all 13 new contract addresses |
| `basis-sdk-js/` | Current JS/TS SDK — updated 2026-03-20, all 13 new contract addresses |
| `basis-sdk-python-old/` | Previous Python SDK (pre-redeployment) |
| `basis-sdk-js-old/` | Previous JS/TS SDK (pre-redeployment) |

### Test Scripts
| File | Contents |
|---|---|
| `sdk-test-readonly.py` | Read-only test suite — 44/44 PASS (Python) |
| `sdk-test-writes.py` | Write test suite — 8/8 PASS (buy, sell, create token w/ metadata) |
| `sdk-test-v2.py` | V2 test suite |
| `sdk-test-metadata-token.py` | Token creation with metadata test (LOBSTR) |
| `sdk-test-metadata-token2.py` | Token creation with metadata test (SEBASTIAN) |

### BNB Chain BD (`bnb-chain-bd/`)
| File | Contents |
|---|---|
| `tracker.md` | **⭐ Master tracker** — 8 tracks (DappBay, X tweet, Walter's 12 Qs, Yzi Labs fund, CMC Labs, Binance Wallet, Alpha Launchpad, Hackathons). Daily check template included. |

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
| `scripts/points.py` | Airdrop points, Molt tier, ACS score — stub (points backend not built yet) |
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
| 2 | **Messaging Repositioning** | New narrative: "Agent-Native DeFi", "Lobster Economy", "Earn Your Shell", **"Agent Mining"**, **"Economic Alignment"** |
| 3 | **Technical Tooling — Agent SDK** | OpenClaw `basis-defi` skill, API endpoints, strategy scripts, monitors, wallet standard |
| 4 | **Agent-Native Features** | Auto-Predict, Predict+ composability (payout mechanics, AMM, strategy paths A/B, exit timing, trader-to-bettor pot, flattening solution), Agent Token Launchpad, Self-Refinancing, Moltbook social layer |
| 5 | **Platform Mechanics (4e)** | Elastic supply, Floor+ stability dial (0%–100%), dynamic leverage (up to ~36x), surge tax, liquid vesting, STASIS Vault (wSTASIS), lending (internal liquidity, time-only risk), BASIS vs STASIS distinction |
| 6 | **GTM: The 100K Agent Blitz** | 🐚 SHELL (100 Founding Lobsters) → 🦞 MOLT (10K agents) → 🔴 LIVE (100K agents) → 💎 TGE (250K+). Growth-first, zero-friction onboarding, Lobster Army as marketing machine. Three-tier friction model. |
| 6A | **Founding Lobster Recruitment** | 3-tier target list, recruitment funnel, week-by-week timeline |
| 6B | **Agent Mining System** | Point values per action, category diversity multiplier (up to 32x), Molt tiers (🥚→💎), anti-sybil via aligned incentives, API spec |
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

## Backend / API (New — 2026-03-20)

| Endpoint | Description |
|---|---|
| `POST /api/v1/sync` | Universal sync — auto-detects source from tx `to` address, idempotent, no auth |
| `GET /api/v1/loans` | Paginated loan data (auth: wallet) |
| `GET /api/v1/loans/events` | Loan event history (auth: wallet) |
| `GET /api/v1/vault/events` | Vault event history (auth: wallet) |
| `GET /api/v1/vesting/events` | Vesting event history (auth: wallet) |

### Prisma Schema Additions (2026-03-20)
- `Loan`, `LoanEvent`, `VaultEvent`, `VestingEvent` models added
- 15 new/fixed events: LoanRepaid, LoanLiquidated, LoanExtended, LeverageCreated, PartialLoanSell, LoanIncreased, LiquidationClaimed, Staking hubId fix, SurgeEnded fix, + 6 more

## Contract Addresses (Redeployed 2026-03-20)

| Contract | Address |
|---|---|
| USDB | `0x217B82e4bAc4E4647B1F189F33554229Ce27c51A` |
| STASIS | `0xE4b1ed74C77984EbFf1CE871E7F7c9414e5dd73b` |
| SWAP | `0xa2483dd5d22D1A8a01473878f247fEC8dC952f1e` |
| FACTORY | `0xd80850a3b712E6B9dB4d3e487c76b7c1F904E273` |
| LOANS | `0x504AeDa510D4cb5Fe6E29D000Dfc377f3f50cC30` |
| STAKING | `0x8E2C5267f2BA1A142A88a333C075E21719E330aC` |
| VESTING | `0x82D1a54fd9671Cd4fE8774f0f85A0CB8A96dee3b` |
| PREDICTION | `0x69e4b11346f928f29Affe6B52a8e3Ebd115DE7a6` |
| RESOLVER | `0x1AB2C2551429Bd4f9a5D8c781BEb5BC5497a42bd` |
| PRIVATE | `0x4eCDD0A082b3f523c31F61eC8bEfF69A8182C0aD` |
| READER | `0xC8652aF90B1C2C9012ADe56B58EfA9572122d342` |
| LEVERAGE | `0x0030d46D3ba98287e7D62482c14E4395FbF52904` |
| TAXES | `0x3CE0381C6515b7771a6E47d99abf1e42054121CD` |

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
| Pre-TGE Rewards Branding | ✅ "Agent Mining" | Not "farming" — rewards productive work, not passive staking (Brett, 2026-03-18) |
| Value Prop Framing | ✅ "Economic Alignment" | Basis aligns agent behavior through incentive design — profit-maximizing = ecosystem-building (Brett, 2026-03-18) |
| Presale Allocation | ✅ 30% (300M) | 4 rounds, all notice-locked with USDC yield |
| DEX Liquidity | ✅ 5% tokens + $7.5M USDC | 1:1 matched, $15M total |

---

## Pending Decisions

| Item | Status | Notes |
|---|---|---|
| Exact loan interest rate | ✅ | 2.0% flat + 0.005%/day (~3.83% for 1yr). Confirmed from contract source 2026-03-16. See `fee-schedule.md` |
| Surge tax parameters | ✅ | 7-day quota, 1hr min, creator-set decaying rate, max 0.5% Stable+ / 1-15% Floor+. See `fee-schedule.md` |
| getPotentialPayout() | ✅ | Documented in SDK docs & API reference 2026-03-16. On-chain view function confirmed. |
| Google Slides from v2 deck | ✅ | Completed by Brett 2026-03-18 |
| Oracle provider for BNB | ✅ | Chainlink for BTC up/down. Creator-managed or Basis oracle for all others. Per-market, not platform-wide. (Alex, 2026-03-18) |
| Audit timeline | ⏳ → 🔄 | Claude Sonnet 4.6 as preliminary auditor. Alex developing testing methodology based on Hashlock public audits for similar projects. Formal audit still TBD. |
| SDK beta publish (npm/PyPI) | ✅ | **PUBLISHED** (2026-04-04). SDK-TS on GitHub (Launch-On-Basis/SDK-TS), MCP-TS on GitHub (Launch-On-Basis/MCP-TS — 172 tools). Python SDK available. Docs at launchonbasis.com/llms.txt |
| USDB faucet URL | ✅ | No standalone URL. Built into dapp: button on `launchonbasis.com/profile` + hovering overlay (if claimable USDB & balance < 2500). Also via SDK. (Alex, 2026-03-18) |
| Points system ownership | ✅ → ⏳ | **Alex will build it.** Needs phased spec — manageable chunks. GeeGee to deliver phased build plan. (Alex, 2026-03-18) |
| Alex's preferred API stack | ✅ | Alex building SDK himself — contract reference delivered 2026-03-14, usage docs to follow |

---

## Team

| Name | Role |
|---|---|
| Brett (@BrettonTG) | Strategy, vision |
| Diamond (@DiamondHandsDude) | Platform architecture, tokenomics |
| Alex (@Alexcrypto32) | Lead developer |
| Atlas (@chairmanAtlas) | Team member |
| GeeGee (@GeeGee_Claw_bot) | AI advisor (Lobster 🦞) |
