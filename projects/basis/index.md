# Basis Project — Quick Reference Index

_Last updated: 2026-03-11_

## Documents

| File | Contents |
|---|---|
| `project-plan.md` | Master strategy document (all sections below) |
| `dev-plan.md` | Technical build requirements for Alex |
| `index.md` | This file — quick reference to sections |

---

## Project Plan Sections

| # | Section | Key Topics |
|---|---|---|
| 1 | **The Thesis** | Moltbook vision, why Basis for agents |
| 2 | **Messaging Repositioning** | New narrative: "Agent-Native DeFi", "Lobster Economy", "Earn Your Shell" |
| 3 | **Technical Tooling — Agent SDK** | OpenClaw `basis-defi` skill, API endpoints, strategy scripts, monitors, wallet standard |
| 4 | **Agent-Native Features** | Auto-Predict, Predict+ composability (payout mechanics, AMM, strategy paths A/B, exit timing, trader-to-bettor pot, flattening solution), Agent Token Launchpad, Self-Refinancing, Moltbook social layer |
| 5 | **Platform Mechanics (4e)** | Elastic supply, Floor+ stability dial, leverage toggle (36x/1x), surge tax, liquid vesting, STASIS Vault (wSTASIS), lending (internal liquidity, time-only risk), BASIS vs STASIS distinction |
| 6 | **GTM: Pre-TGE Playbook** | Phase 0: Lobster Tank → Phase 1: Airdrop Season → Phase 2: Lobster Rush → Phase 3: TGE + Moltbook |
| 6A | **Founding Lobster Recruitment** | 3-tier target list, recruitment funnel, week-by-week timeline |
| 6B | **Points System Design** | Point values per action, multipliers, Molt tiers (🥚→💎), anti-gaming, API spec, seasons |
| 7 | **Competitive Moat** | Switching costs, category ownership vs Polymarket/Pump.fun |
| 8 | **BASIS Token Lockup** | Notice-based staking (not fixed locks), 5 tiers, loyalty escalator, airdrop haircut model (1.0x/2.5x weighted), presale/airdrop specifics |
| 9 | **Testing Phase** | USDB (fake USDC) on BNB Chain mainnet, points carry over to real airdrop |
| 10 | **Token Allocation & Presale** | 9-bucket allocation, 4-round presale ($0.15 TGE, $30M raise), USDC deployment, float analysis, FDV mitigation |
| 11 | **What Motivates Agents** | 4 tiers (survival→agency), USDC-native earnings, earn-to-grow loop |
| 12 | **Dev Plan — Build Responsibilities** | Architecture correction (direct contract calls, not REST API), Alex's 8 deliverables, our deliverables, what already exists, critical path |
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
| Airdrop Split | ✅ 12.5% / 12.5% | Equal human + agent allocation |
| Airdrop Haircut | ✅ Weighted pool | 50% haircut for no-lock, redistributed to Committed (1.0x) + Diamond (2.5x) |
| Leverage Model | ✅ Toggle (36x/1x) | Binary, not slider. Position splitting for effective leverage |
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
| Alex's preferred API stack | ⏳ | Node.js / Python / Rust |

---

## Team

| Name | Role |
|---|---|
| Brett (@BrettonTG) | Strategy, vision |
| Diamond (@DiamondHandsDude) | Platform architecture, tokenomics |
| Alex (@Alexcrypto32) | Lead developer |
| Atlas (@chairmanAtlas) | Team member |
| GeeGee (@GeeGee_Claw_bot) | AI advisor (Lobster 🦞) |
