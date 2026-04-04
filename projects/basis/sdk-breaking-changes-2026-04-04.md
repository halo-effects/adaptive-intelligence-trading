# SDK / Integration Breaking Changes Summary
_Source: Alex (@Alexcrypto32), 2026-04-04 — from Claude audit-driven update_
_Status: DO NOT ACT — reference only until Diamond/Brett give the word_

---

## Faucet — Complete Redesign

**Old system (removed):**
- On-chain faucet() function on USDB contract — one-time 10,000 USDB claim
- On-chain setReferrer() and referrer mapping
- hasClaimed mapping, FaucetClaimed / ReferrerSet events
- Client called contract directly via wallet transaction

**New system:**
- Server-controlled daily drip via POST /api/v1/faucet/claim
- Requires SIWE session authentication (not a wallet transaction)
- Max 500 USDB/day based on stacked signals (base 150, social 100, active 100, hatchling 100, tidal 150)
- Identity gate: ERC-8004 agent OR (username + OAuth-linked social account)
- 24h cooldown between claims
- Optional referrer field in request body (web2 referral, not on-chain)
- Treasury wallet sends USDB via MegaFuel (zero gas for user)
- GET /api/v1/faucet/status returns eligibility, signals, cooldown (also requires SIWE)

**SDK impact:** Any code calling the old USDB contract faucet() function must be replaced with API calls. The USDB contract is now a simple ERC20 with owner-only mint.

---

## Referral System — Moved Off-Chain

**Old system:**
- On-chain setReferrer(address) on USDB contract
- referrer and hasReferrer mappings readable on-chain
- ReferrerSet event

**New system:**
- Referral set via optional referrer field on POST /api/v1/faucet/claim
- Server-side storage in Referral table (layer 1 direct + layer 2 indirect)
- Circular chain detection (visited-set, up to 50 hops)
- GET /api/v1/me/referrals returns referral data for authenticated wallet
- GET /api/v1/profile/{wallet}/referrals returns public counts (API key required)
- Legacy on-chain events still synced via POST /api/v1/sync/faucet

**SDK impact:** Remove any setReferrer() contract calls. Pass referrer address in the faucet claim API call instead.

---

## USDB Contract — Simplified

**Removed:** faucet(), setReferrer(), _setReferrer(), hasClaimed, referrer, hasReferrer mappings, FAUCET_AMOUNT, FaucetClaimed event, ReferrerSet event

**Retained:** Standard ERC20 (transfer, approve, balanceOf, etc.), mint (owner only), rescueTokens, rescueETH, decimals

**Changed:** Initial supply from 1_000_000 * USD_UNIT to 1_000_000_000_000 * USD_UNIT

---

## Authentication Changes

**API Keys:**
- GET /api/v1/auth/keys now returns keyHint (masked bsk_****XXXX) instead of the full decrypted key
- Full key is only shown once at creation time via POST /api/v1/auth/keys
- SDK/bots must save the key on creation — it cannot be retrieved later

**Faucet Status:**
- GET /api/v1/faucet/status now requires SIWE session (was unauthenticated with ?wallet= param)
- Wallet determined from session, not query param

**Multi-wallet:**
- /api/agents POST and /api/v1/auth/keys routes now respect x-wallet-address header for wallet switching

---

## OAuth Social Linking — New

**New endpoints:**
- GET /api/auth/discord?wallet=0x... — Discord OAuth
- GET /api/auth/github?wallet=0x... — GitHub OAuth
- GET /api/auth/google?wallet=0x... — Google OAuth

These are browser-only flows (redirect-based). Each OAuth account is permanently bound 1:1 to a wallet via DB unique constraints. Linking a social account is one of the faucet eligibility signals.

---

## Ingress/Streaming

- DELETE /api/ingress now requires wallet signature + on-chain DEV() ownership check (was unauthenticated)
- Streaming docs removed from public API documentation (internal feature)

---

## Points System

- PointsLedger unique constraint changed from [source, category] to [wallet, source, category] — fixes cross-wallet collision bug
- recomputeWalletPoints now requires owner or admin auth
- getPointsHistory now requires SIWE auth
- pendingWrites scoped to function (no more global module state)
- Pagination capped at 100 per page on getPointsHistory and getPointsLeaderboard

---

## Data Access Changes

- getSocials — requires auth (was public)
- getLinkedPlatforms — returns empty for non-owners (was public)
- getAvatarUploadCount — requires auth (was public)
- getSocialLink — respects isPublic flag for non-owners
- getLeaderboard — filters isPublic: true only, capped at 100
- getProfile — returns only { wallet, username, avatarUrl } (was returning all fields)

---

## Security Headers

New response headers on all routes:
- X-Frame-Options: DENY
- X-Content-Type-Options: nosniff
- Referrer-Policy: strict-origin-when-cross-origin
- Permissions-Policy: camera=(), microphone=(), geolocation=()
- Strict-Transport-Security: max-age=63072000; includeSubDomains; preload

---

## Image Proxy

- next/image remote patterns restricted from wildcard (**) to specific trusted domains (Pinata gateway, Discord CDN, Twitter CDN, Google, GitHub avatars)

---

## Input Validation — New

- Agent name max 100 chars, description max 500 chars
- Article slugs validated with /^[a-zA-Z0-9\-_]+$/
- Contract addresses validated with /^0x[a-fA-F0-9]{40}$/ on getTokenInfo, getTokenMetrics, getTradeHistory, getCandleData, getProject
- Discord username: alphanumeric + dots + underscores only
- Google email: proper email regex
- Pagination: NaN-safe with fallback defaults

---

## Removed

- src/app/actions/beta.ts — hardcoded beta password deleted
- src/app/actions/metadata-queue.ts — server-side pending metadata queue deleted (moved to client localStorage)
- syncReferral — no longer a server action (moved to src/lib/referral-sync.ts)
- syncOAuthToUserSocial — no longer a server action (moved to src/lib/oauth-sync.ts)
- LiveKit/streaming section removed from API docs

---

## Schema Changes (require npm run database)

- SocialLink: added @@unique([platform, platformId]), @@unique([platform, username])
- PointsLedger: changed @@unique([source, category]) to @@unique([wallet, source, category])
- TokenTransfer: added @@index([from, contractAddress, timestamp])
- FaucetClaim: new model (wallet, amount, amountWei, signals, ip, txHash, referrer)
