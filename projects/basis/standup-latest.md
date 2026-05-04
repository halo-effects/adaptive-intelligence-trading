# Basis — Latest Project State
_As of: 2026-04-16_

---

## Phase 1 Status: 🟢 LIVE

Phase 1 is live on BNB Chain with USDB. Agents can earn real points.

---

## ✅ Completed

| Item | Date | Notes |
|---|---|---|
| All 13 core DeFi contracts deployed | 2026-03-14 | BNB Chain mainnet |
| USDB test token deployed | Pre-March | Fake USDC for testing phase |
| Metadata API + Indexer | Pre-March | Candles, txns, syncs, leverage, prediction shares |
| SDK documentation | 2026-03-16 | Full, 13 modules, Python + TypeScript |
| All 7 skill scripts wired to SDK API | 2026-03-16 | create-prediction, bet, create-token, trade, lend, vault, portfolio |
| SDK published on npm/PyPI | April 2026 | Live and installable |
| Points system backend | April 2026 | Live and running |
| Points leaderboard | April 2026 | Live (part of points backend) |
| DappBay BNB Chain listing | April 2026 | Submitted |

---

## 🔧 In Progress

| Item | Status | Notes |
|---|---|---|
| Agent onboarding | Active | Driving users and agents into the live beta |
| First agents earning real points | Active | On USDB |

---

## 📋 Remaining — Pre-TGE Contracts

These are the **3 critical contracts** still to build:

| Contract | Type | Priority |
|---|---|---|
| BASIS token staking contract (notice-based) | New contract | 🔴 Critical |
| Airdrop haircut/distribution contract | New contract | 🔴 Critical |
| Presale notice-based vesting contracts | New contract | 🔴 Critical |

---

## 📋 Remaining — Other

| Item | Type | Priority |
|---|---|---|
| Agent wallet registration system | New build | 🟡 Important |
| Shareable activity cards | New build | 🟡 Important |
| Prediction market AI enhancements | Enhancement | 🟡 Important |
| DEX/CEX liquidity deployment | Operations | 🔴 Critical (TGE) |
| Moltbook registry | New build | 🟡 Post-TGE |

---

## Key Focus Areas (Next)

1. **Drive adoption** — get agents and users actively using the live beta
2. **Pre-TGE contract buildout** — staking, airdrop haircut, presale vesting
3. **Agent onboarding** — first agents earning real points on USDB

---

## Open Questions

1. Oracle provider decision for BNB Chain (Chainlink / API3 / custom)?
2. Contract upgrade patterns in use (proxy, diamond, etc.)?
3. Audit timeline and preferred auditor?
4. Is `mixedBuy` the only ASwap function not exposed on frontend?
5. USDB faucet URL and rate limits for test participants?
