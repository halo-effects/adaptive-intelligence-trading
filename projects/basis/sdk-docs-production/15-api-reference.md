# Off-Chain API Reference

**What this covers:** The full off-chain API (`client.api`) — rate limits, pagination patterns, authentication (SIWE + API keys), and all endpoints with request/response schemas.

**Related sections:** → See: [14-errors.md](14-errors.md) for error codes · → See: [12-getting-started.md](12-getting-started.md) for client initialization · → See: [20-examples.md](20-examples.md) for complete usage examples

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
- `X-RateLimit-Limit` — max requests per window
- `X-RateLimit-Remaining` — requests left in current window
- `X-RateLimit-Reset` — unix timestamp when the window resets

**Pagination Patterns:**

The API uses two pagination styles. Each endpoint below notes which one it uses.

*Offset-based* (browsable lists — tokens, orders, comments, whitelist):
```
?page=1&limit=20
→ { "total": 100, "page": 1, "limit": 20, "hasMore": true }
```

*Cursor-based* (append-only data — trades, transactions, liquidity):
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

1. `GET /api/auth/nonce?address={wallet_address}` — get a one-time nonce
2. Sign a SIWE message containing the nonce with your private key
3. `POST /api/auth/verify` — verify the signature, receive a session cookie

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
| 200 | OK — session established |
| 422 | Invalid nonce or signature |

**Session Management:**

```
GET  /api/auth/me                       → { "isLoggedIn": true, "addresses": ["0x..."] }
GET  /api/auth/me?address=0x...         → { "isLoggedIn": true, "address": "0x..." }
DELETE /api/auth/me?address=0x...       → { "ok": true, "message": "Logged out 0x..." }
```

**API Key Management:**

API keys are required for all `/api/v1/*` data endpoints. Keys are prefixed with `bsk_`. Maximum 1 active key per wallet (upgradeable for premium tiers). Keys are **retrievable** via GET when authenticated — no need to store them externally.

> **Endpoint:** `POST /api/v1/auth/keys` · `GET /api/v1/auth/keys` · `DELETE /api/v1/auth/keys/{id}`

**JavaScript:**

```js
// Create a new API key
const key = await client.api.createApiKey("My Bot");
console.log("API key:", key.key); // "bsk_..."

// List existing keys (returns decrypted key values)
const keys = await client.api.listApiKeys();
// keys[0].key = "bsk_..."

// Delete a key
await client.api.deleteApiKey(key.id);
```

**Python:**

```python
key = client.api.create_api_key("My Bot")
print("API key:", key["key"])

keys = client.api.list_api_keys()

client.api.delete_api_key(key["id"])
```

**Response schema (`createApiKey` / each entry in `listApiKeys`):**

```json
{
  "id": "clx...",
  "key": "bsk_a1b2c3d4...",
  "label": "My Bot",
  "createdAt": "2026-01-01T00:00:00.000Z",
  "lastUsedAt": "2026-03-13T12:00:00.000Z"
}
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

**`uploadImage(file, filename)`**

Upload an image file to IPFS.

> **Endpoint:** `POST /api/images` · Auth: Session · Content-Type: `multipart/form-data`

| Parameter | Type | Description |
|-----------|------|-------------|
| `file` | `Buffer/bytes` | Image data |
| `filename` | `string` | Filename with extension |

**Constraints:** Allowed types: `image/jpeg`, `image/png`, `image/webp`, `image/gif`. Max file size: **5 MB**. Recommended format: **512×512 WebP**.

Returns: `string` -- IPFS gateway URL (e.g. `"https://cyan-abundant-swordtail-589.mypinata.cloud/ipfs/bafy..."`).

| Status | Description |
|--------|-------------|
| 200 | IPFS URL string |
| 400 | No file / invalid type / exceeds 5 MB |
| 401 | Not signed in |

---

**`uploadImageFromUrl(url)`**

Download an image from a URL, resize to 512×512 center-crop WebP, and upload to IPFS. This is the recommended method for programmatic image uploads — it handles the resize pipeline automatically.

> **SDK convenience method** — calls `POST /api/images` internally after preprocessing.

| Parameter | Type | Description |
|-----------|------|-------------|
| `url` | `string` | Source image URL |

Returns: `string` -- IPFS gateway URL.

**JavaScript:**

```js
const imageUrl = await client.api.uploadImageFromUrl("https://example.com/logo.png");
console.log("IPFS URL:", imageUrl);
```

**Python:**

```python
image_url = client.api.upload_image_from_url("https://example.com/logo.png")
print("IPFS URL:", image_url)
```

---

**`updateMetadata(payload)`**

Create or update token/market metadata on IPFS. The server reads token details from the blockchain automatically — you do **not** need to provide name, symbol, dev, multiplier, isPrediction, or options.

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
| `projectId` | `bigint` / `int` | Project ID — get this from `GET /api/v1/tokens/{contractAddress}`, it's the `id` field in the response. |
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

### Transaction & Loan Sync Endpoints

---

**`syncLoan(txHash)`**

Sync an on-chain transaction to the backend database. Auto-detects source (hub/vault/leverage/vesting) from the transaction target.

> **Endpoint:** `POST /api/v1/sync` · Auth: None (public) · Rate limit: 20 req/min per IP

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

> **Note:** The SDK automatically calls this after write operations in Trading (leverage), Loans, Staking, and Vesting modules. You only need to call it manually if auto-sync fails (logged as a warning).

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
  "createdAt": "2026-01-01T00:00:00.000Z",
  "lastActivityAt": "2026-03-13T00:00:00.000Z"
}
```

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

Get full details for a single token, including prediction options if applicable.

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
    "predictionOptions": [
      { "index": 0, "name": "Yes" },
      { "index": 1, "name": "No" }
    ]
  }
}
```

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

> **Naming note:** The field `amountUSDC` in trade responses represents the USDB amount (legacy field name from pre-USDB era). Treat `amountUSDC` as `amountUSDB` — it's the same stablecoin value, 18 decimals. Similarly, `usdcSpent` in prediction trades = USDB spent.

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
| `payload.name` | `string` | Display name (default: "Basis Agent") |
| `payload.description` | `string` | Description (optional) |

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

Look up an agent by wallet address. Public — no auth required.

> **Endpoint:** `GET /api/agents/{address}`

Returns: `{ isAgent: true, agent: { ... } }` or `{ isAgent: false, agent: null }`.

---

**`listAgents(options?)`**

List all registered agents with pagination. Public — no auth required.

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

### Bug Reporting

Report bugs and track their status. Verified bugs earn points (amount set by admin). Rate limited to 5 reports per day per wallet.

**`POST /api/v1/bugs/reports`** · Auth: SIWE Session

Submit a bug report.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `title` | string | yes | Brief description of the bug |
| `description` | string | yes | Detailed reproduction steps |
| `severity` | string | yes | `low`, `medium`, `high`, or `critical` |
| `category` | string | yes | Area of the platform affected |
| `evidence` | string | no | Screenshots, tx hashes, or other proof |

Returns: `{ id, wallet, title, status: "pending", createdAt }`

**`GET /api/v1/bugs/reports`** · Auth: SIWE Session

View your submitted reports. Admins see all reports and can filter by wallet or status.

| Option | Type | Description |
|--------|------|-------------|
| `wallet` | string | Filter by wallet (admin only) |
| `status` | string | Filter: `pending`, `verified`, `duplicate`, `invalid` |

Returns: `{ data: BugReport[] }`

**`PATCH /api/v1/bugs/reports/{id}`** · Auth: Admin only

Update report status and award points.

| Field | Type | Description |
|-------|------|-------------|
| `status` | string | `verified`, `duplicate`, or `invalid` |
| `basePoints` | number | Points to award (verified reports only) |

**`POST /api/v1/admin/block`** · Auth: Admin only — Block a wallet from submitting reports.
**`DELETE /api/v1/admin/block`** · Auth: Admin only — Unblock a wallet.

> **Severity guide:** `low` = cosmetic/typo/UI glitch. `medium` = feature works but behaves unexpectedly. `high` = feature broken or produces wrong results. `critical` = funds at risk, data loss, or security vulnerability.

> **Admin wallets** are configured via the `ADMIN_WALLETS` environment variable (comma-separated addresses). The `/support` page on the dapp provides a form for submitting reports and viewing your submission history.

---
