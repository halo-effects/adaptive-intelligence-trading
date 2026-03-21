# Basis API Documentation

Base URL: `https://launchonbasis.com`

## Authentication Model

- **SIWE Session** — Required for write operations (image upload, metadata creation, project updates, comments). Obtained via wallet signature. Rate limited to 30 req/min per IP.
- **API Key** — Required for all `/api/v1/*` data endpoints. Generated from the Profile page or via API. Rate limited to 60 req/min per key. Keys are prefixed with `bsk_`.

---

## Core Endpoints

Authentication, session management, and write operations. These use SIWE session cookies.

### Authentication (SIWE)

#### `GET /api/auth/nonce?address={wallet_address}`
Generates a one-time nonce for the given wallet address. Must be called before signing.

**Response:**
```json
{ "nonce": "a1b2c3d4e5f6" }
```

#### `POST /api/auth/verify`
Verifies the signed SIWE message. Returns a `Set-Cookie` header with your session.

**Request Body:**
```json
{
  "message": "the prepared SIWE message string",
  "signature": "0x..."
}
```

**Response:**
```json
{ "ok": true, "address": "0x..." }
```

| Status | Description |
|--------|-------------|
| 200 | OK |
| 422 | Invalid nonce or signature |

#### Node.js Example

```js
import { ethers } from "ethers";
import { SiweMessage } from "siwe";

const BASE_URL = "https://launchonbasis.com";

async function authenticate() {
  const wallet = new ethers.Wallet(process.env.PRIVATE_KEY);
  const address = await wallet.getAddress();

  // 1. Get nonce
  const nonceRes = await fetch(`${BASE_URL}/api/auth/nonce?address=${address}`);
  const { nonce } = await nonceRes.json();

  // 2. Create & sign SIWE message
  const message = new SiweMessage({
    domain: "launchonbasis.com",
    address,
    statement: "Sign in to Basis API.",
    uri: BASE_URL,
    version: "1",
    chainId: 56,
    nonce,
  });

  const preparedMessage = message.prepareMessage();
  const signature = await wallet.signMessage(preparedMessage);

  // 3. Verify — returns session cookie
  const verifyRes = await fetch(`${BASE_URL}/api/auth/verify`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message: preparedMessage, signature }),
  });

  const sessionCookie = verifyRes.headers.get("set-cookie");
  return sessionCookie;
}
```

#### Python Example

```python
import requests
from eth_account import Account
from eth_account.messages import encode_defunct
from datetime import datetime
import os

BASE_URL = "https://launchonbasis.com"
private_key = os.environ["PRIVATE_KEY"]
account = Account.from_key(private_key)
address = account.address

# 1. Get nonce
nonce = requests.get(f"{BASE_URL}/api/auth/nonce?address={address}").json()["nonce"]

# 2. Construct & sign SIWE message
issued_at = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.%fZ")
message = (
    f"launchonbasis.com wants you to sign in with your Ethereum account:\n"
    f"{address}\n\nSign in to Basis API.\n\n"
    f"URI: {BASE_URL}\nVersion: 1\nChain ID: 56\n"
    f"Nonce: {nonce}\nIssued At: {issued_at}"
)
signature = Account.sign_message(
    encode_defunct(text=message), private_key=private_key
).signature.hex()

# 3. Verify — session object stores the cookie automatically
session = requests.Session()
session.post(f"{BASE_URL}/api/auth/verify", json={"message": message, "signature": signature})
# Use 'session' for all subsequent requests
```

---

### Session Management

#### `GET /api/auth/me`
Returns all authenticated wallet addresses in the current session.

**Response:**
```json
{ "isLoggedIn": false, "addresses": ["0x..."] }
```

#### `GET /api/auth/me?address={wallet_address}`
Checks if a specific wallet address has an active session.

**Response:**
```json
{ "isLoggedIn": true, "address": "0x...", "allAddresses": ["0x..."] }
```

#### `DELETE /api/auth/me?address={wallet_address}`
Logs out a specific address. Omit the address param to destroy the entire session.

**Response:**
```json
{ "ok": true, "message": "Logged out 0x..." }
```

---

### API Keys

API keys are required for all `/api/v1/*` data endpoints.

- Maximum **1 active key** per wallet (upgradeable for premium tiers)
- Keys are prefixed with `bsk_`
- Keys are **retrievable** via GET when authenticated with a valid SIWE session — no need to store them externally
- Rate limited to **60 requests/minute** per key
- Rate limit headers: `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset`

#### `POST /api/v1/auth/keys`
Creates a new API key. Returns the plain key.

**Auth:** Session required

**Request Body:**
```json
{ "label": "My Bot" }  // optional
```

**Response:**
```json
{
  "id": "clx...",
  "key": "bsk_a1b2c3d4...",
  "label": "My Bot",
  "createdAt": "2026-01-01T00:00:00.000Z"
}
```

| Status | Description |
|--------|-------------|
| 201 | Created |
| 400 | Key limit reached |
| 401 | Not signed in |

#### `GET /api/v1/auth/keys`
Lists all active API keys for the authenticated wallet, including decrypted key values.

**Auth:** Session required

**Response:**
```json
{
  "keys": [
    {
      "id": "clx...",
      "key": "bsk_a1b2c3d4...",
      "label": "My Bot",
      "createdAt": "2026-01-01T00:00:00.000Z",
      "lastUsedAt": "2026-03-13T12:00:00.000Z"
    }
  ]
}
```

#### `DELETE /api/v1/auth/keys/{id}`
Permanently deletes an API key. The key is immediately invalidated.

**Auth:** Session required

**Response:**
```json
{ "ok": true, "message": "API key deleted." }
```

| Status | Description |
|--------|-------------|
| 200 | Deleted |
| 401 | Not signed in |
| 404 | Key not found |

#### Example

```js
// Create an API key (requires active SIWE session)
const res = await fetch("https://launchonbasis.com/api/v1/auth/keys", {
  method: "POST",
  headers: {
    "Content-Type": "application/json",
    "Cookie": sessionCookie,
  },
  body: JSON.stringify({ label: "My Bot" }),
});
const { key } = await res.json();
// key = "bsk_a1b2c3..."

// Or retrieve existing keys (also returns key values)
const listRes = await fetch("https://launchonbasis.com/api/v1/auth/keys", {
  headers: { "Cookie": sessionCookie },
});
const { keys } = await listRes.json();
// keys[0].key = "bsk_a1b2c3..."

// Use the API key for v1 data endpoints
const tokens = await fetch("https://launchonbasis.com/api/v1/tokens?limit=10", {
  headers: { "X-API-Key": key },
});
```

---

### Image Upload

#### `POST /api/images`
Uploads an image file to IPFS. Returns the gateway URL.

**Auth:** Session required

**Request:** `multipart/form-data` with field `file`

- Allowed types: `image/jpeg`, `image/png`, `image/webp`, `image/gif`
- Max file size: **5 MB**

**Response:**
```json
"https://cyan-abundant-swordtail-589.mypinata.cloud/ipfs/bafy..."
```

| Status | Description |
|--------|-------------|
| 200 | URL string |
| 400 | No file / invalid type / too large |
| 401 | Not signed in |

---

### Token & Market Metadata

#### `POST /api/metadata`
Creates metadata JSON on IPFS for a new token or prediction market.

**Auth:** Session required + wallet must be the on-chain creator

**Request Body (JSON):**
```json
{
  "address": "0x...",           // Contract address (required)
  "description": "string",     // Optional
  "website": "string",         // Optional
  "telegram": "string",        // Optional
  "twitterx": "string",        // Optional
  "image": "string"            // IPFS URL from /api/images (optional)
}
```

The server automatically detects whether the address is a regular token, public prediction market, or private prediction market.

**Server-side verification reads from blockchain:**
- `name` and `symbol` — from the token contract
- `dev` — from `DEV()` or `marketData[1]`
- `multiplier` — from `hybridMultiplier()`
- `isPrediction` and `predictionType` — auto-detected
- `options` — from `getAllOutcomes()` (prediction markets only)
- `eventType` — from `marketData[11]` (prediction markets only)

**Response:**
```json
{ "url": "https://...pinata.cloud/ipfs/...", "cid": "bafy..." }
```

| Status | Description |
|--------|-------------|
| 200 | Created |
| 400 | Not an ecosystem token |
| 401 | Not signed in |
| 403 | Not the token creator |
| 409 | Metadata already exists |

---

### Image + Metadata Pipeline (Step-by-Step)

This is the full workflow for uploading an image and creating metadata for a newly deployed token or prediction market. Follow these steps in order.

#### Step 1: Prepare the image

Before uploading, resize and convert the image to **512x512 WebP**. This is the expected format — other sizes will work but 512x512 WebP gives the best results across the platform.

```javascript
// Browser / Node.js with canvas
async function prepareImage(file) {
  // Create a 512x512 canvas
  const canvas = document.createElement("canvas");
  canvas.width = 512;
  canvas.height = 512;
  const ctx = canvas.getContext("2d");

  // Load the source image
  const img = await createImageBitmap(file);

  // Draw scaled to 512x512 (center-crop if not square)
  const size = Math.min(img.width, img.height);
  const sx = (img.width - size) / 2;
  const sy = (img.height - size) / 2;
  ctx.drawImage(img, sx, sy, size, size, 0, 0, 512, 512);

  // Convert to WebP blob
  const blob = await new Promise((resolve) =>
    canvas.toBlob(resolve, "image/webp", 0.9)
  );

  return new File([blob], "image.webp", { type: "image/webp" });
}
```

**Requirements:**
- Allowed types: `image/jpeg`, `image/png`, `image/webp`, `image/gif`
- Max file size: **5 MB**
- Recommended: **512x512 WebP** (what the platform UI produces)

#### Step 2: Upload the image to IPFS

Send the prepared image as `multipart/form-data` to `/api/images`. This requires an active SIWE session.

```javascript
async function uploadImage(imageFile, sessionCookie) {
  const formData = new FormData();
  formData.append("file", imageFile);

  const res = await fetch("https://launchonbasis.com/api/images", {
    method: "POST",
    headers: { "Cookie": sessionCookie },
    body: formData,
  });

  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.error || `Upload failed: ${res.status}`);
  }

  // Returns a plain string — the IPFS gateway URL
  const imageUrl = await res.json();
  return imageUrl;
  // e.g. "https://cyan-abundant-swordtail-589.mypinata.cloud/ipfs/bafyrei..."
}
```

```python
import requests

def upload_image(image_path, session):
    with open(image_path, "rb") as f:
        res = session.post(
            f"{BASE_URL}/api/images",
            files={"file": ("image.webp", f, "image/webp")}
        )
    res.raise_for_status()
    return res.json()  # IPFS gateway URL string
```

**Response:** A plain JSON string (the IPFS gateway URL), not an object.

| Status | Description |
|--------|-------------|
| 200 | IPFS URL string returned |
| 400 | No file / wrong type / exceeds 5 MB |
| 401 | Not signed in |

#### Step 3: Create metadata on IPFS

After deploying the token/market on-chain and uploading the image, call `/api/metadata` to create the IPFS metadata JSON. Pass the image URL from Step 2.

```javascript
async function createMetadata(contractAddress, imageUrl, sessionCookie) {
  const res = await fetch("https://launchonbasis.com/api/metadata", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "Cookie": sessionCookie,
    },
    body: JSON.stringify({
      address: contractAddress,       // required — the deployed contract
      description: "My project",      // optional
      website: "https://example.com", // optional
      telegram: "https://t.me/...",   // optional
      twitterx: "https://x.com/...", // optional
      image: imageUrl,                // optional — IPFS URL from Step 2
    }),
  });

  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.error || `Metadata failed: ${res.status}`);
  }

  const { url, cid } = await res.json();
  return { url, cid };
  // url = "https://cyan-abundant-swordtail-589.mypinata.cloud/ipfs/bafy..."
  // cid = "bafy..."
}
```

```python
def create_metadata(contract_address, image_url, session):
    res = session.post(f"{BASE_URL}/api/metadata", json={
        "address": contract_address,
        "description": "My project",
        "image": image_url,
    })
    res.raise_for_status()
    data = res.json()
    return data["url"], data["cid"]
```

**What the server does automatically:**
- Reads `name`, `symbol`, `dev` from the on-chain contract
- Reads `hybridMultiplier` for factory tokens
- Detects if it's a prediction market (public or private) and reads outcomes
- Verifies your session wallet matches the on-chain `DEV()` address
- Pins the metadata JSON to IPFS via Pinata

**You do NOT need to provide:** name, symbol, dev, multiplier, isPrediction, options — these are all read from the blockchain.

| Status | Description |
|--------|-------------|
| 200 | Metadata created, returns `{ url, cid }` |
| 400 | Address is not a valid ecosystem contract |
| 401 | Not signed in |
| 403 | Session wallet is not the on-chain creator |
| 409 | Metadata already exists for this address |

#### Full Pipeline Example

```javascript
// Complete: deploy on-chain → prepare image → upload → create metadata
async function deployAndRegister(sessionCookie) {
  // 1. Deploy token on-chain (via ethers.js / viem)
  const factory = new ethers.Contract(FACTORY_ADDRESS, FACTORY_ABI, signer);
  const tx = await factory.createToken("SYM", "My Token", 50, false, 10000, 1000, false, 0, false, {
    value: ethers.parseEther("0.00001"),
  });
  const receipt = await tx.wait();
  const tokenAddress = receipt.logs[0].address;

  // 2. Prepare image (resize to 512x512 WebP)
  const rawImage = await fetch("https://example.com/my-logo.png").then((r) => r.blob());
  const preparedImage = await prepareImage(rawImage);

  // 3. Upload to IPFS
  const imageUrl = await uploadImage(preparedImage, sessionCookie);

  // 4. Create metadata (server verifies on-chain ownership)
  const { url, cid } = await createMetadata(tokenAddress, imageUrl, sessionCookie);

  console.log(`Token ${tokenAddress} registered with metadata: ${url}`);
  return tokenAddress;
}
```

---

### Project Updates

#### `POST /api/projects/{address}`
Updates off-chain metadata for a deployed token or prediction market.

**Auth:** Session required + wallet must be the project developer

**Option 1: JSON Body (text fields only)**
```json
{
  "website": "string",
  "telegram": "string",
  "twitterx": "string",
  "description": "string"
}
```

**Option 2: FormData (text fields + image)**
Send as `multipart/form-data` with an `image` file field. Text fields are optional form fields.

**Response:**
```json
{ "success": true, "project": { ... } }
```

| Status | Description |
|--------|-------------|
| 200 | Updated |
| 400 | No fields provided |
| 401 | Not signed in |
| 403 | Not the developer |
| 404 | Project not found |

---

### Comments

#### `GET /api/comments?projectId={id}`
Fetches paginated comments for a project, ordered newest first. Hidden comments are excluded.

| Param | Type | Description |
|-------|------|-------------|
| projectId | number | Project ID (required) |
| page | number | Page number (default: 1) |
| limit | number | Items per page (default: 50, max: 100) |

**Response:**
```json
{
  "data": [
    {
      "id": 1,
      "projectId": 42,
      "author": "0x...",
      "content": "Great project!",
      "tradeType": "buy",
      "txHash": "0x...",
      "createdAt": "2025-01-01T00:00:00.000Z",
      "project": { "dev": "0x..." }
    }
  ],
  "pagination": {
    "total": 15,
    "page": 1,
    "limit": 50,
    "hasMore": false
  }
}
```

#### `POST /api/comments`
Posts a comment. Requires session and sufficient trade history on the project.

**Auth:** Session required + trade eligibility

**Request Body:**
```json
{
  "projectId": 42,
  "content": "Great project!",          // max 2000 characters
  "authorAddress": "0xYourAddress"
}
```

| Status | Description |
|--------|-------------|
| 200 | Created |
| 400 | Content exceeds 2000 characters |
| 401 | Not signed in |
| 403 | Not eligible or address not authenticated |

#### `DELETE /api/comments?id={commentId}&authorAddress={address}`
Soft-deletes a comment. Only the original author can delete their own comment.

**Auth:** Session required + must be author

---

## Data Endpoints (v1)

All `/api/v1/*` data endpoints require an API key via the `X-API-Key` header. Rate limited to 60 req/min per key.

### List Tokens

#### `GET /api/v1/tokens`
List, search, and filter tokens with offset pagination.

**Auth:** API Key required

| Param | Type | Description |
|-------|------|-------------|
| search | string | Filter by name, symbol, or address |
| isPrediction | boolean | Filter by token type |
| sort | string | `newest` (default) or `oldest` |
| page | number | Page number (default: 1) |
| limit | number | Items per page (default: 20, max: 100) |

**Response:**
```json
{
  "data": [
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
      "predictionStatus": null,
      "createdAt": "2026-01-01T00:00:00.000Z",
      "lastActivityAt": "2026-03-13T00:00:00.000Z"
    }
  ],
  "pagination": {
    "total": 1250,
    "page": 1,
    "limit": 20,
    "hasMore": true
  }
}
```

---

### Token Detail

#### `GET /api/v1/tokens/{address}`
Get full details for a single token, including prediction options if applicable.

**Auth:** API Key required

**Response:**
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

### Candle / OHLC Data

#### `GET /api/v1/tokens/{address}/candles`
Get OHLC price candles for a token. Price is calculated as `reserve1 / reserve0` from on-chain sync events.

**Auth:** API Key required

| Param | Type | Description |
|-------|------|-------------|
| interval | string | `1m`, `5m`, `15m`, `1h` (default), `4h`, `1d` |
| from | number | Start time (unix ms, default: 7 days ago) |
| to | number | End time (unix ms, default: now) |
| limit | number | Max candles to return (default: 500, max: 1000) |

**Response:**
```json
{
  "data": [
    { "time": 1710000000000, "open": 0.0015, "high": 0.0018, "low": 0.0014, "close": 0.0017 },
    { "time": 1710003600000, "open": 0.0017, "high": 0.0020, "low": 0.0016, "close": 0.0019 }
  ],
  "interval": "1h",
  "count": 2
}
```

**Note:** For the base pair (caXETHER — TOKEN(18)/USDB(18)), no decimal adjustment needed. All pairs are 18/18.

---

### Trade History

#### `GET /api/v1/tokens/{address}/trades`
Get AMM trade history for a token. Cursor-based pagination, ordered newest first.

**Auth:** API Key required

| Param | Type | Description |
|-------|------|-------------|
| cursor | string | Cursor from previous response for next page |
| limit | number | Items per page (default: 20, max: 100) |
| type | string | `buy`, `sell`, `leverage_buy`, or `leverage_sell` |

**Response:**
```json
{
  "data": [
    {
      "id": 500,
      "type": "buy",
      "amountToken": "1000000000000000000",
      "amountUSDC": "5000000",
      "user": "0x...",
      "price": "0.005",
      "txHash": "0x...",
      "blockNumber": 12345678,
      "timestamp": "2026-03-13T12:00:00.000Z"
    }
  ],
  "pagination": {
    "limit": 20,
    "hasMore": true,
    "nextCursor": "499"
  }
}
```

---

### Prediction Market Orders

#### `GET /api/v1/tokens/{address}/orders`
Get prediction market order book. Offset-based pagination.

**Auth:** API Key required

| Param | Type | Description |
|-------|------|-------------|
| status | string | `ACTIVE`, `FILLED`, or `CANCELLED` |
| outcomeId | number | Filter by outcome index |
| page | number | Page number (default: 1) |
| limit | number | Items per page (default: 20, max: 100) |

**Response:**
```json
{
  "data": [
    {
      "id": "clx...",
      "orderId": 7,
      "seller": "0x...",
      "outcomeId": 0,
      "amount": "1000000000000000000",
      "pricePerShare": "500000",
      "status": "ACTIVE",
      "createdAt": "2026-03-13T12:00:00.000Z"
    }
  ],
  "pagination": {
    "total": 45,
    "page": 1,
    "limit": 20,
    "hasMore": true
  }
}
```

---

### Wallet Transactions

#### `GET /api/v1/wallet/{address}/transactions`
Get transaction history for a wallet across all tokens. Cursor-based pagination.

**Auth:** API Key required

| Param | Type | Description |
|-------|------|-------------|
| cursor | string | Cursor from previous response |
| limit | number | Items per page (default: 20, max: 100) |
| type | string | `buy`, `sell`, `leverage_buy`, or `leverage_sell` |

**Response:**
```json
{
  "data": [
    {
      "id": 300,
      "contractAddress": "0x...",
      "type": "buy",
      "amountToken": "1000000000000000000",
      "amountUSDC": "5000000",
      "price": "0.005",
      "txHash": "0x...",
      "blockNumber": 12345678,
      "timestamp": "2026-03-13T12:00:00.000Z"
    }
  ],
  "pagination": {
    "limit": 20,
    "hasMore": true,
    "nextCursor": "299"
  }
}
```

---

### Market Liquidity / Probability

#### `GET /api/v1/markets/{address}/liquidity`
Get prediction market trade history with reserve data for probability tracking. Cursor-based pagination.

**Auth:** API Key required

| Param | Type | Description |
|-------|------|-------------|
| cursor | string | Cursor from previous response |
| limit | number | Items per page (default: 20, max: 100) |
| outcomeId | number | Filter by outcome index |

**Response:**
```json
{
  "data": [
    {
      "id": 100,
      "buyer": "0x...",
      "outcomeId": 0,
      "shares": "500000000000000000",
      "usdcSpent": "2500000",
      "tradeType": "buy",
      "newReserve": "10000000000000000000",
      "newTotalReserve": "25000000000000000000",
      "txHash": "0x...",
      "blockNumber": 12345678,
      "timestamp": "2026-03-13T12:00:00.000Z"
    }
  ],
  "pagination": {
    "limit": 20,
    "hasMore": true,
    "nextCursor": "99"
  }
}
```

---

### Token Comments

#### `GET /api/v1/tokens/{address}/comments`
Get paginated comments for a token. The `address` param accepts a contract address or numeric project ID. Hidden comments are excluded.

**Auth:** API Key required

| Param | Type | Description |
|-------|------|-------------|
| page | number | Page number (default: 1) |
| limit | number | Items per page (default: 20, max: 100) |

**Response:**
```json
{
  "data": [
    {
      "id": 1,
      "author": "0x...",
      "content": "Great project!",
      "tradeType": "buy",
      "txHash": "0x...",
      "createdAt": "2026-01-01T00:00:00.000Z"
    }
  ],
  "pagination": {
    "total": 15,
    "page": 1,
    "limit": 20,
    "hasMore": false
  }
}
```

| Status | Description |
|--------|-------------|
| 200 | OK |
| 404 | Token not found |

---

### Token Whitelist

#### `GET /api/v1/tokens/{address}/whitelist`
List whitelisted wallets or check a specific wallet for a frozen token.

**Auth:** API Key required

| Param | Type | Description |
|-------|------|-------------|
| wallet | string | Check a specific wallet address (returns boolean result) |
| page | number | Page number (default: 1, ignored when wallet is set) |
| limit | number | Items per page (default: 20, max: 100) |

**Response (with `?wallet=`):**
```json
{
  "whitelisted": true,
  "entry": {
    "walletAddress": "0x...",
    "buyAmount": "1000000",
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
    {
      "walletAddress": "0x...",
      "buyAmount": "1000000",
      "note": null,
      "txHash": "0x...",
      "timestamp": "2026-01-01T00:00:00.000Z"
    }
  ],
  "pagination": {
    "total": 50,
    "page": 1,
    "limit": 20,
    "hasMore": true
  }
}
```

---

### Order Sync

#### `POST /api/v1/orders/sync`
Syncs an on-chain order event (create, cancel, or fill) to the database. Call this after any `listOrder`, `cancelOrder`, or `buyOrdersAndContract` transaction to keep the off-chain order book in sync.

**Auth:** Session or API Key

**Request Body (JSON):**
```json
{
  "txHash": "0x...",              // required — the transaction hash
  "marketType": "public"          // optional — "public" (default) or "private"
}
```

**What it does:**
1. Fetches the transaction receipt from BSC
2. Parses logs for `OrderCreated`, `OrderCancelled`, and `OrderFilled` events
3. Reads the current on-chain order state via `marketOrders(marketToken, orderId)`
4. Upserts the order in the database (creates if new, updates amount/status if existing)

**Response:**
```json
{ "success": true, "message": "Order synced from transaction." }
```

| Status | Description |
|--------|-------------|
| 200 | Order synced |
| 400 | Missing or invalid txHash |
| 401 | Not authenticated |
| 422 | Sync failed (no order events found, or RPC error) |

**Example (Node.js):**
```javascript
// After creating a sell order on-chain
const tx = await walletClient.writeContract({
  address: PREDICTION_ADDRESS,
  abi: PREDICTION_ABI,
  functionName: "listOrder",
  args: [marketToken, outcomeId, amount, pricePerShare],
});

// Wait for confirmation
await publicClient.waitForTransactionReceipt({ hash: tx });

// Sync to database
await fetch("https://launchonbasis.com/api/v1/orders/sync", {
  method: "POST",
  headers: {
    "Content-Type": "application/json",
    "X-API-Key": "bsk_your_key",
  },
  body: JSON.stringify({ txHash: tx, marketType: "public" }),
});
```

```python
# After creating a sell order on-chain and getting tx_hash
import requests

res = session.post(f"{BASE_URL}/api/v1/orders/sync", json={
    "txHash": tx_hash,
    "marketType": "public",
})
print(res.json())  # { "success": true, "message": "Order synced from transaction." }
```

---

### ERC-8004 Agent Identity

Register and look up AI agents on the ERC-8004 Identity Registry.

#### `POST /api/agents`
Register an agent in the database after on-chain ERC-8004 registration.

**Auth:** Session required (SIWE) — the authenticated wallet must match the `wallet` field.

**Request Body (JSON):**
```json
{
  "wallet": "0x...",
  "agentId": 42,
  "name": "My Trading Bot",
  "description": "AI agent powered by Basis SDK"
}
```

| Field | Required | Description |
|-------|----------|-------------|
| wallet | yes | Wallet address (must match session) |
| agentId | yes | ERC-8004 NFT token ID from on-chain registration |
| name | no | Display name (default: "Basis Agent") |
| description | no | Description |

**Response (201):**
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

#### `GET /api/agents/{address}`
Look up an agent by wallet address. Public endpoint — no auth required.

**Response (200):**
```json
{
  "isAgent": true,
  "agent": {
    "wallet": "0x...",
    "agentId": 42,
    "name": "My Trading Bot",
    "description": "...",
    "createdAt": "2026-03-14T00:00:00.000Z"
  }
}
```

**Response (200, not registered):**
```json
{ "isAgent": false, "agent": null }
```

---

#### `GET /api/agents`
List all registered agents with pagination. Public endpoint — no auth required.

| Param | Type | Description |
|-------|------|-------------|
| page | number | Page number (default: 1) |
| limit | number | Items per page (default: 20, max: 100) |

**Response (200):**
```json
{
  "data": [
    {
      "wallet": "0x...",
      "agentId": 42,
      "name": "My Trading Bot",
      "description": "...",
      "createdAt": "2026-03-14T00:00:00.000Z"
    }
  ],
  "pagination": {
    "total": 150,
    "page": 1,
    "limit": 20,
    "hasMore": true
  }
}
```

**Example (Node.js):**
```javascript
// Register agent after on-chain ERC-8004 registration
const res = await fetch("https://launchonbasis.com/api/agents", {
  method: "POST",
  headers: {
    "Content-Type": "application/json",
    "Cookie": sessionCookie,
  },
  body: JSON.stringify({
    wallet: "0x...",
    agentId: 42,
    name: "My Trading Bot",
    description: "Snipes launches on Basis",
  }),
});

// Check if a wallet is an AI agent (public, no auth)
const check = await fetch("https://launchonbasis.com/api/agents/0x...");
const { isAgent, agent } = await check.json();

// List all agents
const list = await fetch("https://launchonbasis.com/api/agents?page=1&limit=20");
const { data, pagination } = await list.json();
```

---

### Transaction Sync

#### `POST /api/v1/sync`
Sync an on-chain transaction to the database. Auto-detects source (hub/vault/leverage/vesting) from the tx target. Handles loans, vault staking, leverage positions, and vesting events.

**Auth:** None required (public data). Rate limited to 20 req/min per IP.

**Request Body:**
```json
{ "txHash": "0x..." }
```

**Response (200):**
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
| 200 | Loan synced |
| 400 | Missing or invalid txHash |
| 422 | Sync failed |
| 429 | Rate limit exceeded |

---

### Loans

#### `GET /api/v1/loans`
List loans for the authenticated wallet.

**Auth:** Session or API Key

| Param | Type | Description |
|-------|------|-------------|
| source | string | Filter: `hub`, `vault`, `leverage`, or `vesting` |
| active | boolean | Filter: `true` for active, `false` for closed |
| page | number | Page number (default: 1) |
| limit | number | Items per page (default: 20, max: 100) |

**Response:** Paginated list of `Loan` objects with collateral, borrowed, full amounts, liquidation time, status.

---

#### `GET /api/v1/loans/events`
List loan lifecycle events for the authenticated wallet.

**Auth:** Session or API Key

| Param | Type | Description |
|-------|------|-------------|
| source | string | Filter: `hub`, `vault`, `leverage`, or `vesting` |
| action | string | Filter: `created`, `repaid`, `extended`, `increased`, `liquidated`, `partial_sell`, `liquidation_claimed` |
| page | number | Page number (default: 1) |
| limit | number | Items per page (default: 20, max: 100) |

---

### Vault Events

#### `GET /api/v1/vault/events`
List vault staking events for the authenticated wallet.

**Auth:** Session or API Key

| Param | Type | Description |
|-------|------|-------------|
| action | string | Filter: `wrap`, `unwrap`, `lock`, `unlock` |
| page | number | Page number (default: 1) |
| limit | number | Items per page (default: 20, max: 100) |

---

### Vesting Events

#### `GET /api/v1/vesting/events`
List vesting events for the authenticated wallet.

**Auth:** Session or API Key

| Param | Type | Description |
|-------|------|-------------|
| action | string | Filter: `created`, `claimed`, `extended`, `beneficiary_changed` |
| vestingId | number | Filter by specific vesting ID |
| page | number | Page number (default: 1) |
| limit | number | Items per page (default: 20, max: 100) |

---

### X / Twitter Verification

Link an X account to a wallet using a challenge-based tweet verification. No wallet address is exposed — only a temporary code.

#### `POST /api/auth/twitter/challenge`
Generate a verification code valid for 30 minutes.

**Auth:** Session or API Key

**Response:**
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
| 409 | Wallet already linked |

---

#### `POST /api/auth/twitter/verify-tweet`
Verify a public tweet containing the challenge code and link the X account.

**Auth:** Session or API Key

**Request Body:**
```json
{ "tweetUrl": "https://x.com/YourHandle/status/123456789" }
```

**Response (201):**
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
| 400 | No challenge / invalid URL |
| 409 | X or wallet already linked |
| 422 | Code not in tweet / tweet not found |

See `TWITTER_VERIFY_API.md` for full SDK examples (Python + Node.js).

---

## Rate Limiting

### API Key endpoints (`/api/v1/*`)
- 60 requests per minute per key
- Response headers: `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset`
- Returns `429 Too Many Requests` when exceeded

### Session endpoints (core)
- 30 requests per minute per IP
- Same response headers

---

## Pagination

### Offset-based
Used for browsable lists (tokens, orders, comments, whitelist).

```
?page=1&limit=20
```

Response includes:
```json
{ "total": 100, "page": 1, "limit": 20, "hasMore": true }
```

### Cursor-based
Used for append-only data (trades, transactions, liquidity).

```
?limit=20           // first page
?cursor=499&limit=20  // next page (use nextCursor from previous response)
```

Response includes:
```json
{ "limit": 20, "hasMore": true, "nextCursor": "479" }
```
