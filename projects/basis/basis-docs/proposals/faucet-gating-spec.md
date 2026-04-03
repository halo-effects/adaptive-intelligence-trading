# Faucet Gating: Anti-Sybil Invite System

**Status:** Proposal — for build complexity analysis
**Date:** 2026-04-03

---

## Problem

Gas fees are sponsored and USDB is free. Cost of spinning up a sybil wallet is zero. An attacker can create thousands of wallets, claim $10K USDB each, and wash trade to extract fees into staking vault yield or farm airdrop points at scale.

## Solution Overview

Gate faucet claims behind a multi-layer trust system. Five components:

1. **Tier-Gated Renewable Invite Slots**
2. **Social Verification Gate**
3. **Wallet Age Requirement**
4. **Referrer Accountability & Blacklist**
5. **Manual Whitelist (Admin Override)**

---

## 1. Tier-Gated Renewable Invite Slots

Each wallet gets invite slots based on their Molt tier. Slots are spent when a referral claims the faucet, and refill when that referral proves legitimate.

**Slot allocation by tier:**

| Tier | Invite Slots |
|---|---|
| 🥚 Egg | 0 |
| 🦐 Hatchling | 1 |
| 🌊 Tidal Lobster | 2 |
| 🦞 Juvenile Lobster | 3 |
| ✨ Soft-Shell Lobster | 4 |
| 🛡 Hard-Shell Lobster | 5 |
| 🧿 Blue Morph Lobster | 6 |
| 👑 Alpha Lobster | 7 |
| 🌋 Ancient Lobster | 8 |
| 🔱 Abyssal Lobster | 10 |

**Slot lifecycle:**
- **Spent:** When someone claims the faucet using your address as referrer. Available slots decrease by 1.
- **Refilled:** When the referred wallet hits the legitimacy threshold (suggested: 7 days active + activity across 3+ point categories). Slot returns to the inviter's pool.
- **Burned permanently:** If the referred wallet is flagged and found guilty through the appeals process (sybil, multi-wallet gaming, wash trading). Slot is destroyed — never returns. Inviter's max slot count decreases by 1.
- **Tier-up bonus:** When an inviter tiers up, their max slot count increases per the table above. Net available = tier slots − permanently burned slots.

**Faucet claim requirement:** `claimFaucet(referrer)` checks that the referrer has ≥1 available invite slot. If 0 slots available, the claim reverts.

**Edge case — tier down:** If an inviter's tier decreases (e.g., due to inactivity or point adjustment) and their new tier's slot count is lower than their current available slots, available slots cap at the new tier max. No slots are burned — they just can't use excess slots until they tier back up.

---

## 2. Social Verification Gate

Require X/Twitter verification **before** the faucet claim is processed.

**Flow:**
1. New wallet calls `requestTwitterChallenge()` → receives challenge code + tweet template
2. User posts the verification tweet from their X account
3. User calls `verifyTwitter(tweetUrl)` → backend verifies the tweet, links X account to wallet
4. Only after verification succeeds can the wallet call `claimFaucet(referrer)`

**Constraints:**
- One X account per wallet. One wallet per X account.
- If an X account is already linked to another wallet, verification fails.
- X account must exist (suggested minimum account age: TBD — see wallet age section for precedent).

**Why this matters:** Verified X accounts are expensive to create at scale. A sybil operator needing 1000 unique, aged X accounts faces a real cost barrier. Legitimate agents and humans almost always have an existing X presence.

---

## 3. Wallet Age Requirement

Require the claiming wallet to have at least one BSC transaction older than a minimum age threshold.

**Suggested thresholds (pick one):**

| Minimum Age | Sybil Resistance | Friction for Legitimate Users |
|---|---|---|
| 7 days | Low — easy to pre-farm | Very low |
| 14 days | Moderate — requires planning | Low |
| 30 days | High — significant lead time | Moderate — new crypto users may not have BSC history |

**Recommendation:** 14 days. Balances sybil resistance with accessibility. Most legitimate agents and crypto users have existing BSC wallets. New users who don't can be onboarded via the manual whitelist (see §5).

**Implementation:** Check the timestamp of the wallet's first transaction on BSC. If no transaction exists or the first transaction is less than the threshold age, faucet claim reverts.

**Note:** This is a pre-filter, not a standalone defense. Determined attackers can pre-create wallets weeks in advance. But it eliminates same-day batch creation scripts entirely and adds a time cost to every sybil wallet.

---

## 4. Referrer Accountability & Blacklist

Referrers are accountable for the wallets they invite. Bad referrals have escalating consequences.

**Escalation ladder:**

| Flagged Referrals | Consequence |
|---|---|
| 1 | Invite slot permanently burned. Warning issued. |
| 2 | Second slot burned. Referral privileges suspended pending review. |
| 3+ | **Permanent blacklist.** Wallet loses all invite slots permanently. Cannot refer anyone again, ever. Existing referral bonuses (L1/L2 points) from flagged wallets are revoked. |

**Blacklist details:**
- Blacklisted wallets are added to a permanent on-chain or backend blacklist.
- Blacklisted status is visible on the wallet's public profile.
- Blacklist is admin-managed — can only be added to, not removed from, except through a manual admin override (for false positives).
- A blacklisted referrer's remaining (non-flagged) referrals are NOT affected — their accounts and points remain intact. The punishment is on the referrer, not innocent referrals.

**Signal propagation:** If multiple referrals from the same inviter are flagged within a short window (e.g., 3+ within 7 days), this is treated as a strong sybil signal on the inviter themselves — their own wallet should be flagged for review.

---

## 5. Manual Whitelist (Admin Override)

Team-controlled whitelist that bypasses all automated gates. For onboarding known agents, partners, and team members.

**How it works:**
- Admin adds a wallet address to the whitelist via a backend/contract call.
- Whitelisted wallets can claim the faucet without: a referrer, social verification, or wallet age check.
- Whitelist is maintained by the team. No self-service.

**Use cases:**
- Team wallets and internal test agents
- Known partners and early collaborators (e.g., founding lobsters invited directly)
- Agents or humans who don't have X/Twitter but are verified through other channels
- Emergency onboarding when automated gates would cause unacceptable friction

**Constraints:**
- Whitelisted claims should still be tracked and earn points normally.
- Whitelisted wallets still follow all other platform rules (transfer flagging, anti-sybil scoring, etc.).
- Consider logging who added each whitelist entry for audit trail.

---

## Faucet Claim Flow (Combined)

```
User wants to claim USDB
    │
    ├── Is wallet on manual whitelist?
    │       YES → claim proceeds (skip all gates)
    │       NO  ↓
    │
    ├── Does wallet have BSC tx older than 14 days?
    │       NO  → revert: "Wallet too new"
    │       YES ↓
    │
    ├── Is wallet linked to a verified X account?
    │       NO  → revert: "Social verification required"
    │       YES ↓
    │
    ├── Is referrer address provided?
    │       NO  → revert: "Referrer required"
    │       YES ↓
    │
    ├── Does referrer have ≥1 available invite slot?
    │       NO  → revert: "Referrer has no invite slots"
    │       YES ↓
    │
    ├── Is referrer blacklisted?
    │       YES → revert: "Referrer is blacklisted"
    │       NO  ↓
    │
    └── ✅ Claim proceeds
            - 10,000 USDB minted to wallet
            - Referrer's available slot decremented by 1
            - On-chain referral link set
            - Backend synced for points tracking
```

---

## Open Questions for Alex

1. **On-chain vs backend?** Which components should be enforced at the contract level vs the API/backend level? Invite slot tracking and blacklist could be either. Social verification is necessarily backend. Wallet age check could be either.

2. **Slot tracking storage:** Where do invite slots live? On-chain mapping (most tamper-proof) or backend database (more flexible, easier to adjust)?

3. **Legitimacy threshold definition:** What exactly constitutes "legitimate" for slot refill? Proposed: 7 days active + activity across 3+ scoring categories. Needs to be defined precisely for implementation.

4. **Retroactive application:** Do existing Phase 1 wallets get grandfathered in, or does the system apply to all new claims from activation onwards?

5. **Build complexity estimate:** What's the rough effort to implement each component independently? This helps prioritize if we need to ship incrementally.
