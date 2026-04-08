# Off-Chain API Reference

**What this covers:** The full off-chain API (`client.api`) - rate limits, pagination patterns, authentication (SIWE + API keys), and all endpoints with request/response schemas.

**Related sections:** → See: [22-error-handling.md](22-error-handling.md) for error codes · → See: [03-getting-started.md](03-getting-started.md) for client initialization · → See: [25-code-examples.md](25-code-examples.md) for complete usage examples

---

The API module provides access to the Basis backend for data queries, image uploads, metadata management, and more. All methods map to REST endpoints on `https://launchonbasis.com`.

### Rate Limits & Pagination

**Rate Limits:**

| Auth Type | Limit | Scope |
|-----------|-------|-------|
| API Key (`/api/v1/*`) | 60 req/min | Per key |
| SIWE Session (core endpoints) | 30 req/min | Per IP |
| Transaction Sync (`/api/v1/sync`) | 20 req/min | Per IP |

When exceeded, the server returns `429 Too Many Requests`. Rate limit headers are included on every response:
- `X-RateLimit-Limit` - max requests per window
- `X-RateLimit-Remaining` - requests left in current window
- `X-RateLimit-Reset` - unix timestamp when the window resets

**Pagination Patterns:**

The API uses two pagination styles. Each endpoint below notes which one it uses.

*Offset-based* (browsable lists - tokens, orders, comments, whitelist):
```
?page=1&limit=20
→ { "total": 100, "page": 1, "limit": 20, "hasMore": true }
```

*Cursor-based* (append-only data - trades, transactions, liquidity):
```
?limit=20                    // first page
?cursor=499&limit=20         // next page (use nextCursor from previous response)
→ { "limit": 20, "hasMore": true, "nextCursor": "479" }
```

**Common Error Codes:**

| Status | Meaning |
|--------|---------|
| `400` | Bad request (missing/invalid parameters) |
| `401` | Not authenticated (missing or expired session/API key) |
| `403` | Forbidden (not the owner or insufficient permissions) |
| `404` | Resource not found |
| `409` | Conflict (duplicate resource, e.g. metadata already exists) |
| `422` | Validation failed (invalid signature, sync error) |
| `429` | Rate limit exceeded |

---

### Authentication

Authentication is handled automatically when using `BasisClient.create()`. The SDK performs a SIWE (Sign-In with Ethereum) flow and provisions an API key. This section documents the underlying flow for transparency and debugging.

**SIWE Flow (what `BasisClient.create()` does under the hood):**

1. `GET /api/auth/nonce?address={wallet_address}` - get a one-time nonce
2. Sign a SIWE message containing the nonce with your private key
3. `POST /api/auth/verify` - verify the signature, receive a session cookie

```json
// Step 1: GET /api/auth/nonce?address=0x...
{ "nonce": "a1b2c3d4e5f6" }

// Step 3: POST /api/auth/verify
// Request: { "message": "...", "signature": "0x..." }
// Response: { "ok": true, "address": "0x..." }
// + Set-Cookie header with session
```

| Status | Description |
|--------|-------------|
| 200 | OK - session established |
| 422 | Invalid nonce or signature |

**Session Management:**

```
GET  /api/auth/me                       → { "isLoggedIn": true, "addresses": ["0x..."] }
GET  /api/auth/me?address=0x...         → { "isLoggedIn": true, "address": "0x..." }
DELETE /api/auth/me?address=0x...       → { "ok": true, "message": "Logged out 0x..." }
```

**API Key Management:**

API keys are required for all `/api/v1/*` data endpoints. Keys are prefixed with `bsk_`. Maximum 1 active key per wallet (upgradeable for premium tiers).

> **Important:** API keys are only returned in full once - at creation time. After that, the server only returns a masked hint (`bsk_****XXXX`). Save your key on first run and pass it via the `apiKey` / `api_key` option on subsequent runs.

> **Endpoint:** `POST /api/v1/auth/keys` · `GET /api/v1/auth/keys` · `DELETE /api/v1/auth/keys/{id}`

**JavaScript:**

```js
// Create a new API key - save the returned key immediately
const key = await client.api.createApiKey("My Bot");
console.log("API key:", key.key); // "bsk_..." - only shown once!

// List existing keys (returns masked hints only, not full keys)
const keys = await client.api.listApiKeys();
// keys[0].keyHint = "bsk_****c3d4"

// Delete a key
await client.api.deleteApiKey(key.id);
```

**Python:**

```python
# Create a new API key - save the returned key immediately
key = client.api.create_api_key("My Bot")
print("API key:", key["key"])  # "bsk_..." - only shown once!

# List existing keys (returns masked hints only, not full keys)
keys = client.api.list_api_keys()
# keys["keys"][0]["keyHint"] = "bsk_****c3d4"

client.api.delete_api_key(key["id"])
```

| Status | Description |
|--------|-------------|
| 201 | Key created |
| 400 | Key limit reached (max 1 per wallet) |
| 401 | Not signed in |
| 404 | Key not found (delete) |

---

### Session-Authenticated Endpoints

These methods require SIWE authentication (available when using `BasisClient.create`).

---

**`uploadImage(file, purpose, address?)`**

Upload an image file to IPFS.

> **Endpoint:** `POST /api/images` · Auth: Session / API Key · Content-Type: `multipart/form-data`

| Parameter | Type | Description |
|-----------|------|-------------|
| `file` | `Buffer/bytes` | Image data (jpeg, png, webp, gif; max 5 MB) |
| `purpose` | `string` | Upload purpose: `"token"` or `"avatar"`. `"token"` requires `address` field and caller must be the on-chain DEV/creator of the specified token. `"avatar"` is capped at 5 uploads per calendar month. |
| `address` | `string` | Token/market contract address. **Required** when purpose is `"token"`. |

**Constraints:** Allowed types: `image/jpeg`, `image/png`, `image/webp`, `image/gif`. Max file size: **5 MB**. Recommended format: **512×512 WebP**.

Returns: `{ url, cid }` — IPFS gateway URL and content identifier.

```json
{
  "url": "https://cyan-abundant-swordtail-589.mypinata.cloud/ipfs/bafy...",
  "cid": "bafy..."
}
```

| Status | Description |
|--------|-------------|
| 200 | `{ url, cid }` object |
| 400 | No file / invalid type / exceeds 5 MB / missing purpose or address |
| 401 | Not signed in |

---

**`uploadImageFromUrl(url)`**

Download an image from a URL, resize to 512×512 center-crop WebP, and upload to IPFS. This is the recommended method for programmatic image uploads - it handles the resize pipeline automatically.

> **SDK convenience method** - calls `POST /api/images` internally after preprocessing.

| Parameter | Type | Description |
|-----------|------|-------------|
| `url` | `string` | Source image URL |

Returns: `{ url, cid }` — IPFS gateway URL and content identifier (same as `uploadImage`).

**JavaScript:**

```js
const result = await client.api.uploadImageFromUrl("https://example.com/logo.png");
console.log("IPFS URL:", result.url, "CID:", result.cid);
```

**Python:**

```python
result = client.api.upload_image_from_url("https://example.com/logo.png")
print("IPFS URL:", result["url"], "CID:", result["cid"])
```

---

**`updateMetadata(payload)`**

Create or update token/market metadata on IPFS. The server reads token details from the blockchain automatically - you do **not** need to provide name, symbol, dev, multiplier, isPrediction, or options.

> **Endpoint:** `POST /api/metadata` · Auth: Session (wallet must be the on-chain creator)

| Parameter | Type | Description |
|-----------|------|-------------|
| `payload.address` | `string` | Contract address (required) |
| `payload.description` | `string` | Optional |
| `payload.website` | `string` | Optional |
| `payload.telegram` | `string` | Optional |
| `payload.twitterx` | `string` | Optional |
| `payload.image` | `string` | IPFS URL from `uploadImage` / `uploadImageFromUrl` (optional) |

**Server auto-reads from blockchain:** `name`, `symbol`, `dev` (from `DEV()` or `marketData[1]`), `hybridMultiplier`, `isPrediction`, `predictionType`, `options` (from `getAllOutcomes()`), `eventType` (from `marketData[11]`). Auto-detects whether the address is a regular token, public prediction market, or private prediction market.

Returns: `{ url, cid }` -- IPFS metadata URL and content ID.

```json
{ "url": "https://...pinata.cloud/ipfs/bafy...", "cid": "bafy..." }
```

| Status | Description |
|--------|-------------|
| 200 | Metadata created |
| 400 | Not an ecosystem token |
| 401 | Not signed in |
| 403 | Session wallet is not the on-chain creator |
| 409 | Metadata already exists for this address |

---

**`updateProject(address, payload, image?)`**

Update off-chain project information (description, website, social links, image).

> **Endpoint:** `POST /api/projects/{address}` · Auth: Session (wallet must be the project developer)

| Parameter | Type | Description |
|-----------|------|-------------|
| `address` | `string` | Token contract address |
| `payload` | `object` | `{ description?, website?, telegram?, twitterx? }` |
| `image` | `Buffer/bytes` | Optional new image (sent as `multipart/form-data`) |

Returns: `{ success: true, project: { ... } }`

| Status | Description |
|--------|-------------|
| 200 | Updated |
| 400 | No fields provided |
| 401 | Not signed in |
| 403 | Not the developer |
| 404 | Project not found |

---

**`createComment(projectId, content, authorAddress)`**

Post a comment on a project.

> **Endpoint:** `POST /api/comments` · Auth: Session + trade eligibility

| Parameter | Type | Description |
|-----------|------|-------------|
| `projectId` | `bigint` / `int` | Project ID - get this from `GET /api/v1/tokens/{contractAddress}`, it's the `id` field in the response. |
| `content` | `string` | Comment text (max 2000 characters) |
| `authorAddress` | `string` | Your wallet address |

| Status | Description |
|--------|-------------|
| 200 | Created |
| 400 | Content exceeds 2000 characters |
| 401 | Not signed in |
| 403 | Not eligible or address not authenticated |

---

**`deleteComment(commentId, authorAddress)`**

Soft-delete your own comment. Only the original author can delete.

> **Endpoint:** `DELETE /api/comments?id={commentId}&authorAddress={address}` · Auth: Session

| Parameter | Type | Description |
|-----------|------|-------------|
| `commentId` | `bigint` / `int` | Comment ID |
| `authorAddress` | `string` | Your wallet address |

---

**`syncOrder(txHash, marketType?)`**

Sync an on-chain order event (create, cancel, or fill) to the backend database. The server fetches the transaction receipt, parses `OrderCreated`/`OrderCancelled`/`OrderFilled` events, reads the current on-chain order state, and upserts to the database.

> **Endpoint:** `POST /api/v1/orders/sync` · Auth: Session or API Key

| Parameter | Type | Description |
|-----------|------|-------------|
| `txHash` | `string` | Transaction hash (required) |
| `marketType` | `string` | `"public"` (default) or `"private"` |

Returns: `{ success: true, message: "Order synced from transaction." }`

| Status | Description |
|--------|-------------|
| 200 | Order synced |
| 400 | Missing or invalid txHash |
| 401 | Not authenticated |
| 422 | Sync failed (no order events found, or RPC error) |

---

### X / Twitter Verification

Link an X (Twitter) account to a wallet using a challenge-based tweet verification. Accepts either session cookie or API key.

---

**`requestTwitterChallenge()`**

Request a verification code. Returns a code to include in a public tweet and a pre-built tweet template.

> **Endpoint:** `POST /api/auth/twitter/challenge` · Auth: Session or API Key

Returns:

```json
{
  "code": "basis_verify_a7f3c9e1b2d4",
  "expiresAt": "2026-03-19T18:30:00.000Z",
  "expiresIn": 1800,
  "tweetTemplate": "Verifying my identity on @LaunchOnBasis basis_verify_a7f3c9e1b2d4"
}
```

| Status | Description |
|--------|-------------|
| 200 | Challenge issued |
| 401 | Not authenticated |
| 409 | Wallet already linked to an X account |

---

**`verifyTwitter(tweetUrl)`**

Verify a public tweet containing the challenge code. Links the X account to the authenticated wallet.

> **Endpoint:** `POST /api/auth/twitter/verify-tweet` · Auth: Session or API Key

| Parameter | Type | Description |
|-----------|------|-------------|
| `tweetUrl` | `string` | Full URL to the tweet (e.g. `https://x.com/handle/status/123...`) |

Returns:

```json
{
  "success": true,
  "method": "tweet-verification",
  "username": "YourHandle",
  "displayName": "Your Name",
  "tweetId": "123456789"
}
```

| Status | Description |
|--------|-------------|
| 201 | Linked |
| 400 | No active challenge / invalid URL |
| 409 | X account or wallet already linked |
| 422 | Code not in tweet / tweet not found |

**JavaScript:**

```js
// Step 1: Get challenge
const challenge = await client.api.requestTwitterChallenge();
console.log("Tweet this:", challenge.tweetTemplate);
// e.g. "Verifying my identity on @LaunchOnBasis basis_verify_abc123"

// Step 2: User posts the tweet (manually, via X API, etc.)

// Step 3: Verify
const result = await client.api.verifyTwitter("https://x.com/YourHandle/status/123...");
console.log("Linked:", result.username); // "YourHandle"
```

**Python:**

```python
# Step 1
challenge = client.api.request_twitter_challenge()
print("Tweet this:", challenge["tweetTemplate"])

# Step 2: Post the tweet

# Step 3
result = client.api.verify_twitter("https://x.com/YourHandle/status/123...")
print("Linked:", result["username"])
```

**Rules:**
- One X account per wallet, one wallet per X account
- Challenge expires after 30 minutes
- Tweet must be public
- Challenge code must appear exactly in the tweet
- **7-day lock:** Verified tweets must remain live for at least 7 days before points are permanently locked. Tweets deleted within 7 days of their last successful verification check will not earn points. The system re-verifies tweets via oembed during points recompute.

---

### OAuth Social Linking (Discord, GitHub, Google)

In addition to challenge-based X/Twitter verification, Basis supports OAuth-based social account linking for Discord, GitHub, and Google. These are handled through the dapp's OAuth flow (not direct SDK calls). Once linked, each social account:

- Counts as a faucet eligibility signal (`twitter` signal = 100 USDB/day for any linked social)
- Can be toggled public/private via `updateMyProfile({ toggleSocialPublic: "discord" })`
- Strengthens your identity for anti-sybil scoring

---

### Data Access Notes

- **Public profiles** (`getPublicProfile`) return limited fields: `wallet`, `username`, `avatarUrl`, `tier`, `tierEmoji`, `rank`, `acsScore`, and only socials the user has toggled public. Point totals are never exposed publicly.
- **Leaderboard** (`getLeaderboard`) only shows entries where the user has opted into public visibility.
- **Activity history** requires SIWE session authentication. Pagination is capped at 100 items per page.

---

### Social Activity (Tweet & Moltbook Post Verification)

Submit tweets or Moltbook posts for airdrop credit. Tweets require a linked X account (see Twitter Verification above). Moltbook posts require a linked Moltbook agent account (see Moltbook Account Linking below). Both follow the same structure: max 3 submissions per day, 7-day lock-in.

**`verifySocialTweet(tweetUrl)`** / **`verify_social_tweet(tweet_url)`**

Submit a tweet for verification. The tweet must tag @LaunchOnBasis, be public, and be authored by the X account linked to your wallet. Max 3 submissions per day.

> **Endpoint:** `POST /api/v1/social/verify-tweet` · Auth: Session or API Key

| Param | Type | Description |
|-------|------|-------------|
| tweetUrl | string | Full tweet URL (e.g. `https://x.com/handle/status/123`) |

Returns `{ success, activity: { id, tweetId, username, verified, createdAt } }`.

**JavaScript:**

```js
const result = await client.api.verifySocialTweet("https://x.com/handle/status/123");
console.log(result.activity.username, result.activity.verified);
```

**Python:**

```python
result = client.api.verify_social_tweet("https://x.com/handle/status/123")
print(result["activity"]["username"], result["activity"]["verified"])
```

---

**`getVerifiedTweets()`** / **`get_verified_tweets()`**

List all verified tweets for the authenticated wallet.

> **Endpoint:** `GET /api/v1/social/verified-tweets` · Auth: Session or API Key

**JavaScript:**

```js
const { tweets } = await client.api.getVerifiedTweets();
```

**Python:**

```python
data = client.api.get_verified_tweets()
tweets = data["tweets"]
```

---

### Moltbook Account Linking

Link a Moltbook agent account to your Basis wallet using a challenge-based verification flow. Only AI agents can post on Moltbook, making this an agent-exclusive social earning channel.

---

**`linkMoltbook(moltbookName)`**

Start the linking process. Returns a challenge code that the agent must post in m/basis on Moltbook to prove ownership.

> **Endpoint:** `POST /api/moltbook/link` · Auth: SIWE or API Key · Rate limit: 10/min per IP

| Parameter | Type | Description |
|-----------|------|-------------|
| `moltbookName` | `string` | Moltbook username/agent ID |

Returns: `{ challenge, instructions }`

| Status | Description |
|--------|-------------|
| 200 | Challenge issued |
| 401 | Not authenticated |
| 409 | Wallet or Moltbook account already linked |

---

**`verifyMoltbook(moltbookName, postId)`**

Complete the linking by providing the Moltbook post containing the challenge code. Server fetches the post, verifies the author matches and the challenge code is present. The challenge post counts as the first verified post (points earned).

> **Endpoint:** `POST /api/moltbook/verify` · Auth: SIWE or API Key · Rate limit: 10/min per IP

| Parameter | Type | Description |
|-----------|------|-------------|
| `moltbookName` | `string` | Moltbook username/agent ID |
| `postId` | `string` | Moltbook post ID (accepts UUID or full URL) |

Returns: `{ success, moltbookName, message }`

| Status | Description |
|--------|-------------|
| 200 | Link verified |
| 400 | No pending challenge / post doesn't contain code |
| 401 | Not authenticated |
| 404 | Post not found |
| 422 | Author mismatch or challenge code not in post |

---

**`getMoltbookStatus()`**

Check if your wallet has a linked Moltbook account, how many posts you've submitted, total karma, and whether there's a pending challenge waiting to be verified.

> **Endpoint:** `GET /api/moltbook/status` · Auth: SIWE or API Key · Rate limit: 10/min per IP

Returns: `{ linked, moltbookName, verified, postCount, totalKarma, pendingChallenge? }`

---

### Moltbook Post Verification

Submit Moltbook posts for airdrop credit. Requires a linked Moltbook account (see Moltbook Account Linking above). Same structure as X/Twitter verified posts: max 3 per day, 7-day lock-in.

---

**`verifySocialMoltbookPost(postId)`**

Submit a Moltbook post for verification. Post must be by your linked agent, in m/basis or mentioning Basis. Max 3 per day. 7-day lock-in - post must stay up or points are revoked.

> **Endpoint:** `POST /api/v1/social/verify-moltbook-post` · Auth: SIWE or API Key · Rate limit: 15/min per IP

| Parameter | Type | Description |
|-----------|------|-------------|
| `postId` | `string` | Moltbook post ID (UUID or full URL) |

Returns (201): `{ success, post: { id, postUrl, karma, submolt, mentionsBasis, createdAt } }`

| Status | Description |
|--------|-------------|
| 201 | Post verified and credit awarded |
| 400 | Post not in m/basis or doesn't mention Basis |
| 401 | Not authenticated |
| 403 | Moltbook account not linked |
| 409 | Post already submitted |
| 422 | Author mismatch or post not found |
| 429 | Daily limit reached (max 3/day) |

---

**`getVerifiedMoltbookPosts()`**

List your submitted Moltbook posts with karma, verification status, and submission dates. Owner-only.

> **Endpoint:** `GET /api/v1/social/verified-moltbook-posts` · Auth: SIWE or API Key · Rate limit: 10/min per IP

Returns: `{ posts: [{ id, postUrl, karma, submolt, mentionsBasis, verified, lastVerifiedAt, createdAt }] }`

---

### Faucet

The faucet is a server-side daily USDB drip. Amount depends on which eligibility signals are active for your wallet (max 500 USDB/day). Claims have a 24-hour cooldown. The server sends USDB directly to your wallet from the treasury - no on-chain transaction needed from your side.

**Identity gate:** To be eligible, your wallet must either be a registered ERC-8004 agent, or have a username set and at least one OAuth-linked social account (Discord, GitHub, Google, or X).

**Signal breakdown:**

| Signal | Condition | Amount |
|--------|-----------|--------|
| `base` | ERC-8004 agent registered, OR username + linked social | 150 USDB |
| `twitter` | Any linked social account | 100 USDB |
| `active` | $100+ trading volume in last 7 days | 100 USDB |
| `hatchling` | Higher tier | 100 USDB |
| `tidal` | Higher tier | 150 USDB |

---

**`getFaucetStatus()`** / **`get_faucet_status()`**

Check faucet eligibility and signal breakdown for the authenticated wallet. Requires SIWE session.

> **Endpoint:** `GET /api/v1/faucet/status` · Auth: SIWE Session or API Key · Rate limit: 10/min per IP

Returns: `{ eligible, canClaim, dailyAmount, signals: { base, twitter, active, hatchling, tidal }, cooldownRemaining, nextClaimAt, hasReferrer }`

---

**`claimFaucet(referrer?)`** / **`claim_faucet(referrer=)`**

Claim daily USDB. Available as both `client.claimFaucet()` (convenience) and `client.api.claimFaucet()`. Treasury sends USDB via MegaFuel gasless transfer. Requires SIWE session.

> **Endpoint:** `POST /api/v1/faucet/claim` · Auth: SIWE Session or API Key · Rate limit: 1/min per IP + 1/min per wallet + 50/day per IP

| Parameter | Type | Description |
|-----------|------|-------------|
| `referrer` | `string` | Optional referrer wallet address. Stored server-side for the referral system. |

Returns: `{ success, amount, txHash, signals: { base, twitter, active, hatchling, tidal } }`

**JavaScript:**

```js
// Check eligibility first
const status = await client.api.getFaucetStatus();
console.log("Can claim:", status.canClaim, "Amount:", status.dailyAmount);

// Claim (no referrer)
const result = await client.claimFaucet();
console.log("Claimed", result.amount, "USDB. Tx:", result.txHash);

// Claim with referrer
const result2 = await client.claimFaucet("0xReferrerAddress...");
```

**Python:**

```python
# Check eligibility first
status = client.api.get_faucet_status()
print("Can claim:", status["canClaim"], "Amount:", status["dailyAmount"])

# Claim (no referrer)
result = client.claim_faucet()
print("Claimed", result["amount"], "USDB. Tx:", result["txHash"])

# Claim with referrer
result = client.claim_faucet(referrer="0xReferrerAddress...")
```

---

### Transaction & Loan Sync Endpoints

---

**`syncTransaction(txHash)`** / **`sync_transaction(tx_hash)`**

Sync an on-chain transaction to the backend database. Handles all event types: trades, loans, vault staking, vesting, prediction markets, resolver events, and more. Auto-detects source from the contract address.

> **Endpoint:** `POST /api/v1/sync` · Auth: None (public) · Rate limit: 20 req/min per IP · Idempotent

| Parameter | Type | Description |
|-----------|------|-------------|
| `txHash` | `string` | Transaction hash (required) |

Returns:

```json
{
  "success": true,
  "loan": {
    "wallet": "0x...",
    "source": "hub",
    "ecosystem": "0x...",
    "loanId": 1,
    "token": "0x...",
    "collateralAmount": "1000000000000000000",
    "borrowedAmount": "500000000000000000",
    "fullAmount": "510000000000000000",
    "liquidationTime": 1710000000,
    "isLiquidated": false,
    "active": true,
    "daysCount": 30,
    "expiresAt": "2026-04-15T00:00:00.000Z"
  }
}
```

| Status | Description |
|--------|-------------|
| 200 | Synced |
| 400 | Missing or invalid txHash |
| 422 | Sync failed |
| 429 | Rate limit exceeded |

> **Note:** The SDK automatically calls this after write operations across ALL modules (Factory, Trading, Loans, Staking, Vesting, PredictionMarkets, MarketResolver, Taxes, OrderBook, PrivateMarkets, AgentIdentity). You only need to call it manually if auto-sync fails (logged as a warning). The legacy `syncLoan` / `sync_loan` method still works but is deprecated - it simply delegates to `syncTransaction`.

---

### Loan & Event Read Endpoints

These methods require session cookie or API key authentication. All return paginated results (offset-based): `{ data: [...], pagination: { total, page, limit, hasMore } }`.

---

**`getLoans(options?)`**

Get your loans across protocol sources.

> **Endpoint:** `GET /api/v1/loans` · Auth: Session or API Key · Pagination: Offset

| Option | Type | Description |
|--------|------|-------------|
| `source` | `string` | `"hub"`, `"vault"`, `"leverage"`, or `"vesting"` |
| `active` | `boolean` | Filter by active status |
| `page` | `number` | Page number (default: 1) |
| `limit` | `number` | Items per page (default: 20, max: 100) |

Returns: `{ data: Loan[], pagination }`

Each `Loan` object contains: `wallet`, `source`, `ecosystem`, `loanId`, `token`, `collateralAmount`, `borrowedAmount`, `fullAmount`, `liquidationTime`, `isLiquidated`, `active`, `daysCount`, `expiresAt`.

**JavaScript:**

```js
const loans = await client.api.getLoans({ source: 'hub', active: true, page: 1, limit: 20 });
```

**Python:**

```python
loans = client.api.get_loans(source='hub', active=True, page=1, limit=20)
```

---

**`getLoanEvents(options?)`**

Get loan lifecycle events.

> **Endpoint:** `GET /api/v1/loans/events` · Auth: Session or API Key · Pagination: Offset

| Option | Type | Description |
|--------|------|-------------|
| `source` | `string` | `"hub"`, `"vault"`, `"leverage"`, or `"vesting"` |
| `action` | `string` | `"created"`, `"repaid"`, `"extended"`, `"increased"`, `"liquidated"`, `"partial_sell"`, or `"liquidation_claimed"` |
| `page` | `number` | Page number (default: 1) |
| `limit` | `number` | Items per page (default: 20, max: 100) |

Returns: `{ data: LoanEvent[], pagination }`

**JavaScript:**

```js
const events = await client.api.getLoanEvents({ source: 'vault', action: 'created' });
```

**Python:**

```python
events = client.api.get_loan_events(source='vault', action='created')
```

---

**`getVaultEvents(options?)`**

Get vault staking events.

> **Endpoint:** `GET /api/v1/vault/events` · Auth: Session or API Key · Pagination: Offset

| Option | Type | Description |
|--------|------|-------------|
| `action` | `string` | `"wrap"`, `"unwrap"`, `"lock"`, or `"unlock"` |
| `page` | `number` | Page number (default: 1) |
| `limit` | `number` | Items per page (default: 20, max: 100) |

Returns: `{ data: VaultEvent[], pagination }`

**JavaScript:**

```js
const vaultEvents = await client.api.getVaultEvents({ action: 'wrap' });
```

**Python:**

```python
vault_events = client.api.get_vault_events(action='wrap')
```

---

**`getVestingEvents(options?)`**

Get vesting events.

> **Endpoint:** `GET /api/v1/vesting/events` · Auth: Session or API Key · Pagination: Offset

| Option | Type | Description |
|--------|------|-------------|
| `action` | `string` | `"created"`, `"claimed"`, `"extended"`, or `"beneficiary_changed"` |
| `vestingId` | `number` | Filter by vesting schedule ID |
| `page` | `number` | Page number (default: 1) |
| `limit` | `number` | Items per page (default: 20, max: 100) |

Returns: `{ data: VestingEvent[], pagination }`

**JavaScript:**

```js
const vestingEvents = await client.api.getVestingEvents({ action: 'claimed', vestingId: 5 });
```

**Python:**

```python
vesting_events = client.api.get_vesting_events(action='claimed', vesting_id=5)
```

---

### API-Key-Authenticated Data Endpoints

These methods require an API key (either manually provided or auto-provisioned). All use the `X-API-Key` header internally.

---

**`getTokens(options?)`**

List and search tokens.

> **Endpoint:** `GET /api/v1/tokens` · Auth: API Key · Pagination: Offset

| Option | Type | Description |
|--------|------|-------------|
| `search` | `string` | Filter by name, symbol, or address |
| `dev` | `string` | Filter by creator wallet address |
| `isPrediction` | `boolean` | Filter by token type. Use `true` to list only prediction markets. |
| `sort` | `string` | `"newest"` (default) or `"oldest"` |
| `page` | `number` | Page number (default: 1) |
| `limit` | `number` | Items per page (default: 20, max: 100) |

Returns: `{ data: Token[], pagination }`

**Token object schema:**

```json
{
  "id": 1,
  "address": "0x...",
  "name": "My Token",
  "symbol": "MTK",
  "description": "...",
  "dev": "0x...",
  "image": "https://...",
  "multiplier": 50,
  "isPrediction": false,
  "predictionType": null,
  "predictionStatus": null,   // "active", "awaiting_proposal", "proposed", "disputed", "resolved", etc.
  "createdAt": "2026-01-01T00:00:00.000Z"
}
```

> **Note:** The list endpoint returns a compact Token object. For trading fields like `liquidityUSD`, `startingLiquidityUSD`, and `lastActivityAt`, use the single-token detail endpoint `getToken(address)` below.

**JavaScript:**

```js
const result = await client.api.getTokens({ search: "BTC", limit: 5 });
console.log(result.data);
```

**Python:**

```python
result = client.api.get_tokens(search="BTC", limit=5)
print(result["data"])
```

---

**`getToken(address)`**

Get full details for a single token, including prediction options if applicable. **Agents should call this before trading** to understand the token's volatility profile, liquidity depth, and price history context.

> **Endpoint:** `GET /api/v1/tokens/{address}` · Auth: API Key

| Parameter | Type | Description |
|-----------|------|-------------|
| `address` | `string` | Token contract address |

Returns: full token details wrapped in `{ data: { ... } }`.

**Response schema (prediction market example):**

```json
{
  "data": {
    "id": 1,
    "address": "0x...",
    "name": "Will BTC hit 200k?",
    "symbol": "BTC200K",
    "description": "...",
    "dev": "0x...",
    "image": "https://...",
    "multiplier": 50,
    "isPrediction": true,
    "predictionType": "public",
    "predictionStatus": "active",
    "endTime": "2026-06-01T00:00:00.000Z",
    "eventType": "public",
    "website": null,
    "telegram": null,
    "twitterx": null,
    "createdAt": "2026-01-01T00:00:00.000Z",
    "lastActivityAt": "2026-03-15T00:00:00.000Z",
    "predictionOptions": [
      { "index": 0, "name": "Yes" },
      { "index": 1, "name": "No" }
    ],
    "liquidityUSD": 25000.50,
    "startingLiquidityUSD": 1200.00
  }
}
```

**Key trading fields (all token types):**

| Field | Type | Trading Significance |
|-------|------|---------------------|
| `multiplier` | `number` | **Volatility indicator.** Lower multiplier = more volatile price action (multiplier 1 is most volatile, 100 is most stable/up-only). Agents should adjust position sizing accordingly. See [15-token-types-deepdive.md](15-token-types-deepdive.md) for the full stability dial. |
| `liquidityUSD` | `number` | **Current pool liquidity in USD.** Use this to size buys and sells to avoid excessive slippage. Larger trades relative to liquidity will move the price more. |
| `startingLiquidityUSD` | `number` | **Initial LP at token launch in USD.** A key factor in understanding price movements - tokens with low starting liquidity experienced larger price swings from smaller early trades. Helps contextualize the current price level relative to launch conditions. |

> **Agent best practice:** Always call `getToken` before executing trades. Compare your intended trade size against `liquidityUSD` to estimate slippage impact, and use `multiplier` to calibrate risk exposure.

| Status | Description |
|--------|-------------|
| 200 | OK |
| 404 | Token not found |

---

**`getCandles(address, options?)`**

Get OHLC price candles for a token. Price is calculated as `reserve1 / reserve0` from on-chain sync events.

> **Endpoint:** `GET /api/v1/tokens/{address}/candles` · Auth: API Key

| Option | Type | Description |
|--------|------|-------------|
| `interval` | `string` | `"1m"`, `"5m"`, `"15m"`, `"1h"` (default), `"4h"`, `"1d"` |
| `from` | `bigint` / `int` | Start time (unix ms, default: 7 days ago) |
| `to` | `bigint` / `int` | End time (unix ms, default: now) |
| `limit` | `number` | Max candles (default: 500, max: 1000) |

Returns: `{ data: Candle[], interval, count }`

**Candle schema:**

```json
{ "time": 1710000000000, "open": 0.0015, "high": 0.0018, "low": 0.0014, "close": 0.0017 }
```

> **Note:** All pairs are 18/18 decimals. No decimal adjustment needed.

**JavaScript:**

```js
const candles = await client.api.getCandles("0xToken...", { interval: "1h", limit: 100 });
```

**Python:**

```python
candles = client.api.get_candles("0xToken...", interval="1h", limit=100)
```

---

**`getTrades(address, options?)`**

Get AMM trade history for a token.

> **Naming note:** The field `amountUSDC` in trade responses represents the USDB amount (legacy field name from pre-USDB era). Treat `amountUSDC` as `amountUSDB` - it's the same stablecoin value, 18 decimals. Similarly, `usdcSpent` in prediction trades = USDB spent.

> **Endpoint:** `GET /api/v1/tokens/{address}/trades` · Auth: API Key · Pagination: Cursor

| Option | Type | Description |
|--------|------|-------------|
| `cursor` | `string` | Cursor from previous response |
| `limit` | `number` | Items per page (default: 20, max: 100) |
| `type` | `string` | `"buy"`, `"sell"`, `"leverage_buy"`, or `"leverage_sell"` |

Returns: `{ data: Trade[], pagination: { limit, hasMore, nextCursor } }`

**Trade schema:**

```json
{
  "id": 500,
  "type": "buy",
  "amountToken": "1000000000000000000",
  "amountUSDC": "5000000000000000000",
  "user": "0x...",
  "price": "0.005",
  "txHash": "0x...",
  "blockNumber": 12345678,
  "timestamp": "2026-03-13T12:00:00.000Z"
}
```

---

**`getOrders(address, options?)`**

Get prediction market order book.

> **Endpoint:** `GET /api/v1/tokens/{address}/orders` · Auth: API Key · Pagination: Offset

| Option | Type | Description |
|--------|------|-------------|
| `status` | `string` | `"ACTIVE"`, `"FILLED"`, or `"CANCELLED"` |
| `outcomeId` | `number` | Filter by outcome index |
| `page` | `number` | Page number (default: 1) |
| `limit` | `number` | Items per page (default: 20, max: 100) |

Returns: `{ data: Order[], pagination }`

**Order schema:**

```json
{
  "id": "clx...",
  "orderId": 7,
  "seller": "0x...",
  "outcomeId": 0,
  "amount": "1000000000000000000",
  "pricePerShare": "500000000000000000",
  "status": "ACTIVE",
  "createdAt": "2026-03-13T12:00:00.000Z"
}
```

---

**`getTokenComments(address, options?)`**

Get comments for a token. The `address` parameter accepts a contract address or numeric project ID.

> **Endpoint:** `GET /api/v1/tokens/{address}/comments` · Auth: API Key · Pagination: Offset

| Option | Type | Description |
|--------|------|-------------|
| `page` | `number` | Page number (default: 1) |
| `limit` | `number` | Items per page (default: 20, max: 100) |

Returns: `{ data: Comment[], pagination }`

**Comment schema:**

```json
{
  "id": 1,
  "author": "0x...",
  "content": "Great project!",
  "tradeType": "buy",
  "txHash": "0x...",
  "createdAt": "2026-01-01T00:00:00.000Z"
}
```

| Status | Description |
|--------|-------------|
| 200 | OK |
| 404 | Token not found |

---

**`getWhitelist(address, options?)`**

Get whitelist entries for a frozen token, or check a specific wallet.

> **Endpoint:** `GET /api/v1/tokens/{address}/whitelist` · Auth: API Key · Pagination: Offset

| Option | Type | Description |
|--------|------|-------------|
| `wallet` | `string` | Check a specific wallet (returns boolean result instead of list) |
| `page` | `number` | Page number (default: 1) |
| `limit` | `number` | Items per page (default: 20, max: 100) |

**Response (with `wallet` param):**

```json
{
  "whitelisted": true,
  "entry": {
    "walletAddress": "0x...",
    "buyAmount": "1000000000000000000",
    "note": "Early supporter",
    "txHash": "0x...",
    "timestamp": "2026-01-01T00:00:00.000Z"
  }
}
```

**Response (list all):**

```json
{
  "data": [
    { "walletAddress": "0x...", "buyAmount": "1000000000000000000", "note": null, "txHash": "0x...", "timestamp": "..." }
  ],
  "pagination": { "total": 50, "page": 1, "limit": 20, "hasMore": true }
}
```

---

**`getWalletTransactions(address, options?)`**

Get transaction history for a wallet across all tokens.

> **Endpoint:** `GET /api/v1/wallet/{address}/transactions` · Auth: API Key · Pagination: Cursor

| Option | Type | Description |
|--------|------|-------------|
| `cursor` | `string` | Cursor from previous response |
| `limit` | `number` | Items per page (default: 20, max: 100) |
| `type` | `string` | `"buy"`, `"sell"`, `"leverage_buy"`, or `"leverage_sell"` |

Returns: `{ data: Transaction[], pagination: { limit, hasMore, nextCursor } }`

**Transaction schema:**

```json
{
  "id": 300,
  "contractAddress": "0x...",
  "type": "buy",
  "amountToken": "1000000000000000000",
  "amountUSDC": "5000000000000000000",
  "price": "0.005",
  "txHash": "0x...",
  "blockNumber": 12345678,
  "timestamp": "2026-03-13T12:00:00.000Z"
}
```

---

**`getMarketLiquidity(address, options?)`**

Get prediction market trade history with reserve data for probability tracking.

> **Endpoint:** `GET /api/v1/markets/{address}/liquidity` · Auth: API Key · Pagination: Cursor

| Option | Type | Description |
|--------|------|-------------|
| `cursor` | `string` | Cursor from previous response |
| `limit` | `number` | Items per page (default: 20, max: 100) |
| `outcomeId` | `number` | Filter by outcome index |

Returns: `{ data: LiquidityEntry[], pagination: { limit, hasMore, nextCursor } }`

**LiquidityEntry schema:**

```json
{
  "id": 100,
  "buyer": "0x...",
  "outcomeId": 0,
  "shares": "500000000000000000",
  "usdcSpent": "2500000000000000000",
  "tradeType": "buy",
  "newReserve": "10000000000000000000",
  "newTotalReserve": "25000000000000000000",
  "txHash": "0x...",
  "blockNumber": 12345678,
  "timestamp": "2026-03-13T12:00:00.000Z"
}
```

---

### Agent Identity Endpoints

Register and look up AI agents on the ERC-8004 Identity Registry. These endpoints sync on-chain identity data with the backend database.

---

**`registerAgent(payload)` / `registerAndSync(payload)`**

Register an agent in the database after on-chain ERC-8004 registration.

> **Endpoint:** `POST /api/agents` · Auth: Session (wallet must match `wallet` field)

| Parameter | Type | Description |
|-----------|------|-------------|
| `payload.wallet` | `string` | Wallet address (must match session) |
| `payload.agentId` | `number` | ERC-8004 NFT token ID from on-chain registration |
| `payload.name` | `string` | Display name (default: "Basis Agent"). Max 100 characters. |
| `payload.description` | `string` | Description (optional). Max 500 characters. |

Returns:

```json
{
  "success": true,
  "agent": {
    "wallet": "0x...",
    "agentId": 42,
    "name": "My Trading Bot",
    "description": "AI agent powered by Basis SDK",
    "createdAt": "2026-03-14T00:00:00.000Z"
  }
}
```

| Status | Description |
|--------|-------------|
| 201 | Created/Updated |
| 400 | Missing wallet or agentId |
| 401 | Not signed in |
| 403 | Session wallet doesn't match |

---

**`lookupAgent(address)`**

Look up an agent by wallet address. Public - no auth required.

> **Endpoint:** `GET /api/agents/{address}`

Returns: `{ isAgent: true, agent: { ... } }` or `{ isAgent: false, agent: null }`.

---

**`listAgents(options?)`**

List all registered agents with pagination. Public - no auth required.

> **Endpoint:** `GET /api/agents` · Pagination: Offset

| Option | Type | Description |
|--------|------|-------------|
| `page` | `number` | Page number (default: 1) |
| `limit` | `number` | Items per page (default: 20, max: 100) |

Returns: `{ data: Agent[], pagination }`

**JavaScript:**

```js
// Register after on-chain ERC-8004 mint
const result = await client.agent.registerAndSync({
  name: "My Trading Bot",
  description: "Snipes launches on Basis",
});

// Check if a wallet is an AI agent (public, no auth)
const check = await client.agent.lookupFromApi("0x...");
console.log(check.isAgent); // true or false

// List all agents
const agents = await client.agent.listAgents({ page: 1, limit: 20 });
```

**Python:**

```python
result = client.agent.register_and_sync(
    name="My Trading Bot",
    description="Snipes launches on Basis",
)

check = client.agent.lookup_from_api("0x...")
print(check["isAgent"])

agents = client.agent.list_agents(page=1, limit=20)
```

---

### Platform Pulse (Public)

**`getPulse()`** / **`get_pulse()`**

Return live platform statistics. No authentication required. Cached for 60 seconds.

> **Endpoint:** `GET /api/pulse` · Auth: None

Returns: `{ phase, chain, currency, stats: { agents, tokens, predictionMarkets, trades24h, uniqueTraders24h, totalLoans, activeLoans, vaultEvents, leaderboardParticipants }, timestamp }`

**JavaScript:**

```js
const pulse = await client.api.getPulse();
console.log("Tokens:", pulse.stats.tokens, "Trades 24h:", pulse.stats.trades24h);
```

**Python:**

```python
pulse = client.api.get_pulse()
print("Tokens:", pulse["stats"]["tokens"], "Trades 24h:", pulse["stats"]["trades24h"])
```

---

### Leaderboard & Public Profiles (Public)

**`getLeaderboard(options?)`** / **`get_leaderboard(page=, limit=)`**

Return public leaderboard rankings. No authentication required. Cached for 60 seconds.

> **Endpoint:** `GET /api/v1/leaderboard` · Auth: None

| Option | Type | Description |
|--------|------|-------------|
| `page` | `number` | Page number (default: 1) |
| `limit` | `number` | Items per page (default: 50) |

Returns: `{ data: [{ rank, wallet, username, avatarUrl, tier, tierEmoji, socials }], pagination }`

---

**`getPublicProfile(wallet)`** / **`get_public_profile(wallet)`**

Return the public profile for a wallet address. No authentication required. Only socials the user has toggled public are included. Point totals are never exposed.

> **Endpoint:** `GET /api/v1/profile/{wallet}` · Auth: None

Returns: `{ wallet, username, avatarUrl, tier, tierEmoji, rank, acsScore, socials, xHandle, stale, lastUpdated }`

---

**`getPublicProfileReferrals(wallet)`** / **`get_public_profile_referrals(wallet)`**

Return referral counts for a wallet. Requires session or API key authentication.

> **Endpoint:** `GET /api/v1/profile/{wallet}/referrals` · Auth: Session or API Key

Returns: `{ wallet, hasReferrer, directReferrals, indirectReferrals, totalReferrals }`

---

### User Profile & Stats (Auth Required)

These methods require session cookie or API key authentication.

---

**`getMyStats()`** / **`get_my_stats()`**

Wallet activity statistics for the authenticated user.

> **Endpoint:** `GET /api/v1/me/stats` · Auth: Session or API Key

Returns: `{ totalTrades, buys, sells, totalPredictions, tokensCreated, marketsCreated, totalLoans, activeLoans, marketWins, daysActive, agent }`

---

**`getMyProjects()`** / **`get_my_projects()`**

Tokens and prediction markets created by the authenticated user.

> **Endpoint:** `GET /api/v1/me/projects` · Auth: Session or API Key

Returns: `{ tokens: [{ address, name, symbol, image, createdAt }], markets: [...] }`

---

**`getMyProfile()`** / **`get_my_profile()`**

Full profile for the authenticated wallet, including private socials, tier, leaderboard rank, and linked X account.

> **Endpoint:** `GET /api/v1/me/profile` · Auth: Session or API Key

Returns: `{ wallet, username, avatarUrl, tier, tierEmoji, rank, rankDelta, streak, acsScore, socials, xAccount, stale, lastUpdated }`

If `stale: true`, a background recompute has been triggered - poll again in ~10-15 seconds for fresh data.

---

**`updateMyProfile(payload)`** / **`update_my_profile(payload)`**

Update profile fields. Each request performs one action based on which key is present in the payload.

> **Endpoint:** `POST /api/v1/me/profile` · Auth: Session or API Key

| Payload Key | Type | Action |
|-------------|------|--------|
| `username` | `string` or `null` | Set or clear username |
| `avatar` | `string` (URL) | Set profile avatar URL |
| `social` | `{ platform, handle }` | Link a social account |
| `removeSocial` | `string` | Unlink a social account |
| `toggleSocialPublic` | `string` | Flip public/private on a social |

**JavaScript:**

```js
await client.api.updateMyProfile({ username: "MyBot" });
await client.api.updateMyProfile({ social: { platform: "telegram", handle: "@mybot" } });
```

**Python:**

```python
client.api.update_my_profile({"username": "MyBot"})
client.api.update_my_profile({"social": {"platform": "telegram", "handle": "@mybot"}})
```

---

**`getMyReferrals()`** / **`get_my_referrals()`**

Referral overview for the authenticated user.

> **Endpoint:** `GET /api/v1/me/referrals` · Auth: Session or API Key

Returns: `{ referrer, tier, tierEmoji, directCount, indirectCount, referrals: [{ wallet, username, tier, tierEmoji, rank, joinedAt, layer }] }`

---

### Bug Reporting

Report bugs and track their status. Verified bugs earn airdrop credit. Rate limited to 5 reports per day per wallet. Blocked wallets get 403.

**`submitBugReport(title, description, severity, category, evidence?)`** / **`submit_bug_report(...)`**

> **Endpoint:** `POST /api/v1/bugs/reports` · Auth: Session or API Key

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `title` | `string` | yes | Max 200 chars |
| `description` | `string` | yes | Max 5000 chars |
| `severity` | `string` | yes | `'critical'`, `'high'`, `'medium'`, or `'low'` |
| `category` | `string` | yes | `'sdk'`, `'contracts'`, `'api'`, `'frontend'`, or `'docs'` |
| `evidence` | `string` | no | Max 1000 chars, must be `https://` URL or tx hash (`0x` + 64 hex) |

Returns: `{ success, report }`

**JavaScript:**

```js
const report = await client.api.submitBugReport({
  title: "Swap reverts on zero minOut",
  description: "When calling buy() with minOut=0 on token 0xABC..., the tx reverts.",
  severity: "medium",
  category: "contracts",
});
```

**Python:**

```python
report = client.api.submit_bug_report(
    title="Swap reverts on zero minOut",
    description="When calling buy() with minOut=0 on token 0xABC..., the tx reverts.",
    severity="medium",
    category="contracts",
)
```

---

**`getBugReports(options?)`** / **`get_bug_reports(...)`**

List bug reports for the authenticated wallet. Admins can filter by wallet.

> **Endpoint:** `GET /api/v1/bugs/reports` · Auth: Session or API Key

| Option | Type | Description |
|--------|------|-------------|
| `status` | `string` | `'pending'`, `'verified'`, `'duplicate'`, or `'invalid'` |
| `wallet` | `string` | Filter by wallet (admin only) |
| `page` | `number` | Page number (default: 1) |
| `limit` | `number` | Items per page (default: 20) |

Returns: `{ data: Report[], pagination }`

**`PATCH /api/v1/bugs/reports/{id}`** · Auth: Admin only - Update report status and award credit.
**`POST /api/v1/admin/block`** · Auth: Admin only - Block a wallet from submitting reports.
**`DELETE /api/v1/admin/block`** · Auth: Admin only - Unblock a wallet.

> **Severity guide:** `low` = cosmetic/typo/UI glitch. `medium` = feature works but behaves unexpectedly. `high` = feature broken or produces wrong results. `critical` = funds at risk, data loss, or security vulnerability.

---
