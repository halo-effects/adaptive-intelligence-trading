# BNB Chain Business Development — Action Tracker

_Source: Follow-up call with Walter, BD Manager at BNB Chain (April 2026)_
_Last updated: 2026-04-08_
_Contact: Walter (BNB Chain BD) — offered referral for Yzi Labs + CMC Labs_

---

## Goal
Seed funding, promotional support, and participation in BNB Chain sponsored channels.

## Daily Standup Line Item
> **BNB Chain BD**: [status summary — update daily]

---

## Track Status Overview

| # | Track | Priority | Owner | Status | Target Date |
|---|-------|----------|-------|--------|-------------|
| 1 | DappBay Listing | 🔴 HIGH | TBD | Not started | ASAP |
| 2 | X Deployment Post + Welcome Tweet | 🔴 HIGH | Brett + Diamond | Phase 1 live, ready to draft deployment tweet | ASAP |
| 3 | Walter's 12 Questions | 🟡 MEDIUM | Brett + GeeGee | 10/12 answered, Q11 pending (Atlas) | When Atlas delivers profiles |
| 4 | Yzi Labs $1B Builders Fund | 🟡 MEDIUM | Brett + GeeGee | Not started | TBD |
| 5 | CMC Labs Incubation | 🟡 MEDIUM | Brett | Not started | Parallel to Yzi |
| 6 | Binance Wallet SDK Integration | 🟡 MEDIUM | Alex | Steps 1-2 done, step 3 pending | Submit self-listing |
| 7 | Binance Alpha Launchpad | 🔵 LOW (post-TGE) | Brett | Blocked on traction + TGE | Post-TGE |
| 8 | Hackathons | 🔵 LOW | Monitor | Watching | As opportunities arise |

---

## TRACK 1: DAPPBAY LISTING

**URL:** https://dappbay.bnbchain.org/
**Review time:** 3-7 business days
**They audit:** website, team background, smart contract vulnerabilities

### What to submit:
- ✅ Website: https://launchonbasis.com
- ✅ Smart contract addresses: All 13 deployed on BSC mainnet (Chain ID: 56)
- ✅ Logo/branding
- ⏳ Team background info
- Category: **DeFi**

### Contract addresses for submission:
**Canonical endpoint:** https://launchonbasis.com/contracts.json (always pull latest from here)

| Contract | Address (as of 2026-04-04) |
|----------|---------|
| USDB | `0x1b2b5D36e5F07BD6a272F95079590B70AdB776b1` |
| mainToken (STASIS) | `0x4B01013aC1F3501c64DFC7bC08aE5E23F391b5EA` |
| swap | `0xD9C99E3E92c5Cb303371223FAaA3C8f5FeE39399` |
| factory | `0x13b32CcB24F1fd070cE8Ee5EA83AAC5a60f853DA` |
| loanHub | `0x4d3ca2DA5F77FA8c0D0CA53b4078D025519b6d8f` |
| staking | `0xb956d467D95a16f660aaBF25c5dE81A897254332` |
| vesting | `0xd27d9999b360f1D9c1Fb88F91d038D9d674f127b` |
| marketTrading | `0xcf8368E674A13662BA55F98bdb9A6FBC6aCEbEeE` |
| resolver | `0xDCE6daaE48Ec55977D22BB9D855BF7ef222077cf` |
| privateMarket | `0xe9aA86286bE3b353241091910FB11Fd62CC88bd3` |
| reader | `0x320C73CD00Dd484b53140795F9eD1C875A5A6D99` |
| leverage | `0xD10B597d2B5CDAf965f7AC29339866513311e84d` |
| taxes | `0xb65Ff977fFb0ABa34c28e8b571D29DFb1a3416a4` |
| erc8004Registry | `0x8004A169FB4a3325136EB29fA0ceB6D2e539a432` |

### Post-listing:
- Keep profile updated (new contracts, logo changes)
- DappBay tracks DAU + transactions — this drives future marketing support
- Check review status: https://dappbay.bnbchain.org/my-projects

**Guide:** https://drive.google.com/file/d/1A1ujH9ipP9MN8Xtkec9UAxF07ba8kKhS/view

---

## TRACK 2: X DEPLOYMENT POST + WELCOME TWEET

### Steps:
1. Draft deployment tweet mentioning @BNBCHAIN
2. Post from @LaunchOnBasis
3. Share draft + link with Walter
4. BNB Chain may feature in welcome thread (their discretion)

### Tweet requirements:
- Mention @BNBCHAIN (not DappBay — no X account)
- Highlight product value + use case for BNB Chain community
- Keep short, simple, clear

### GTM timing:
- Time marketing push around when BNB Chain welcome tweet drops
- Have blog post, threads, community push ready to go immediately after

### References:
- Brand guidelines: https://www.bnbchain.org/en/brand-guidelines
- Welcome post example: https://x.com/BNBCHAIN/status/2021418939931295881
- Campaign example: https://x.com/BNBCHAIN/status/2023729213854150698

---

## TRACK 3: WALTER'S 12 QUESTIONS

All answers needed before Walter can proceed with support.

| # | Question | Answer | Status |
|---|---------|--------|--------|
| Q1 | Draft tweet info and link | ⏳ See Track 2 | Needs drafting |
| Q2 | DappBay profile link | ⏳ After registration | Blocked on Track 1 |
| Q3 | Transactions shown on DappBay | Token creation (Stable+, Floor+, Predict+), AMM DEX trades, prediction market bets, loans (borrow/repay/extend), vault staking (wSTASIS), leveraged trades, vesting schedules | ✅ DRAFTED |
| Q4 | Project X link | https://x.com/LaunchOnBasis | ✅ |
| Q5 | Project website | https://launchonbasis.com | ✅ |
| Q6 | GitHub core repo | https://github.com/Launch-On-Basis/SDK-TS (TypeScript SDK), https://github.com/Launch-On-Basis/MCP-TS (MCP Server — 172 tools) | ✅ |
| Q7 | Audit/security docs | Preliminary audit in progress using Claude Sonnet 4.6. Testing methodology based on Hashlock public audits for similar projects. Formal third-party audit planned pre-TGE. | ⏳ IN PROGRESS |
| Q8 | TGE details | Not yet TGE'd. Currently in Phase 1 "Founding Lobster" (pre-launch testing, zero financial risk). Planned ticker: **BASIS**. Floor FDV: $150M. TGE price: $0.15. Airdrop: 11% of total supply across 3 phases. | ✅ DRAFTED |
| Q9 | Date of main contract deployment | **2026-03-20** — full redeployment of all 13 smart contracts on BSC mainnet (Chain ID: 56) | ✅ |
| Q10 | Target date for launch post + welcome tweet | **Phase 1 (Founding Lobster) is LIVE.** Launch announced on Telegram, Moltbook (m/basis), and X (@LaunchOnBasis). Ready for deployment tweet + BNB Chain welcome tweet. See: https://launchonbasis.com/articles/article-phases-tokenomics | ✅ READY |
| Q11 | Team background / LinkedIn | ⏳ Atlas is compiling team profiles. | IN PROGRESS (Atlas) |
| Q12 | Raise details / investors | Presale planned: 4 rounds, 30% allocation (300M tokens), target raise ~$30M. Notice-based locked. Floor FDV: $150M. Full tokenomics published: https://launchonbasis.com/articles/article-phases-tokenomics | ✅ PUBLIC |

### Blockers:
- **Q11 is the remaining gap** — Atlas is compiling team LinkedIn profiles / backgrounds
- ~~Q10~~ — **RESOLVED**: Phase 1 is live, launch announced across channels
- ~~Q12~~ — **RESOLVED**: Tokenomics article published, raise details are public

---

## TRACK 4: YZI LABS $1B BUILDERS FUND

**Apply:** https://forms.monday.com/forms/849b09d8df07fce1b6ded57b4f54334d
**Referral:** Walter from BNB Chain (confirmed he offered)
**Info:** https://www.bnbchain.org/en/blog/1b-builder-fund-to-empower-builders-backed-by-yzi-labs-and-bnb-chain

### Proposal requirements → Basis coverage:

| Requirement | What we have | Status |
|------------|-------------|--------|
| Product demo/MVP | Live platform + SDK + MCP (172 tools) + launchonbasis.com | ✅ |
| Team background | Need LinkedIn profiles + relevant experience | ⏳ |
| GTM strategy | 100K Agent Blitz: SHELL (100) → MOLT (10K) → LIVE (100K) → TGE (250K+). In project plan §6 | ✅ |
| Roadmap on BNB Chain | All 13 contracts deployed, Phase 1 entering pre-launch, 3-phase rollout | ✅ |
| Competitor analysis | Predict.fun, Opinion, Probable, Myriad — detailed in project plan §14 | ✅ |
| Revenue model | Creator fees (20%), DEX trading fees, lending fees, vault fees — all documented in fee-schedule.md | ✅ |
| Product-market fit | Agent-native DeFi thesis — agents can't use human DeFi, need autonomous financial primitives | ✅ |
| User journey | Agent onboarding: SDK install → wallet → faucet → first trade (5 min). Documented in getting-started | ✅ |

### Action:
- Package existing content into deck/blurb format
- Add team backgrounds
- Submit with Walter referral
- Inform Walter with deck after submission

---

## TRACK 5: CMC LABS INCUBATION

**Website:** https://coinmarketcap.com/events/cmc-labs/
**Apply:** https://docs.google.com/forms/d/e/1FAIpQLSeTUxGaMmq1XFZbzfRXrYz-35bNa_LrQhdUL7_8H1sxbCbjzg/viewform
**Contacts:**
- @Leonarda_VentureCapital (Telegram) — mention Builder Program
- @asiancryptoboy (Jin at CMC, Telegram) — inform after application
**Referral:** Walter at BNB Chain

### Action:
- Apply via form
- Mention Builder Program
- Contact Leonarda + Jin
- Run parallel to Yzi Labs application

---

## TRACK 6: BINANCE WALLET SDK INTEGRATION

### Steps (sequential):
1. ✅ **Integrate SDK:** https://developers.binance.com/docs/binance-w3w/introduction — DONE
2. ✅ **Self-test:** https://developers.binance.com/docs/w3w_web3_dapp/self-testing — DONE
3. ⏳ **Submit self-listing:** https://developers.binance.com/docs/w3w_web3_dapp/self-listing — PENDING
4. **Review period:** 5-7 business days (after step 3)

### Success criteria:
- Binance Wallet shown alongside MetaMask in wallet connect options
- Binance Wallet can sign transactions on iOS + Android

### Also integrate:
- **Trust Wallet** — Walter flagged both as strong performers on BNB Chain

**Owner:** Alex (development work)

---

## TRACK 7: BINANCE ALPHA LAUNCHPAD

**Apply when ready:** https://www.binance.com/en/my/coin-apply
- Binance Alpha reaches out if interested — no guarantees
- Strong DappBay traction → Walter can send recommendation note
- Growth path: Alpha → Futures → Spot listing
- Can assess for secondary listing if product launches with token

**Pre-requisites:**
- DappBay listing with strong on-chain stats
- TGE completed or imminent
- Binance Wallet integration preferred

**Reference:** https://x.com/binance/status/1978429250735677766

---

## TRACK 8: HACKATHONS

**Watch:** https://www.bnbchain.org/en/hackathons + @BNBCHAIN on X
**Relevance:** Good visibility if timing aligns with Phase 1/2
**Action:** Monitor — apply if a relevant hackathon opens

---

## Daily Check Template

```
🔷 BNB Chain BD Update — [DATE]

Track 1 (DappBay): [status]
Track 2 (Tweet): [status]
Track 3 (12 Qs): [X/12 answered]
Track 4 (Yzi Labs): [status]
Track 5 (CMC Labs): [status]
Track 6 (Wallet SDK): [status]

Blockers: [any]
Next action: [what + who]
```
