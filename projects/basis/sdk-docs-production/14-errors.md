# Error Handling

**What this covers:** Contract revert reasons, API error codes, non-fatal warnings, transaction sync behavior, and recovery patterns for common multi-step failures.

**Related sections:** → See: [15-api-reference.md](15-api-reference.md) for full API error codes · → See: [20-examples.md](20-examples.md) for try/catch patterns in context · → See: [17-mistakes.md](17-mistakes.md) for strategic mistakes to avoid · → See: [23-production-ops.md](23-production-ops.md) for production error recovery

---

## Contract Reverts

Write methods throw an error when a transaction reverts on-chain. The error message includes the revert reason from the contract.

**JavaScript:**

```js
try {
  await client.trading.buy("0xToken...", parseUnits("5", 18));
} catch (error) {
  console.error("Transaction failed:", error.message);
  // e.g., "execution reverted: Insufficient balance"
}
```

**Python:**

```python
try:
    client.trading.buy("0xToken...", 5_000_000_000_000_000_000)
except Exception as e:
    print("Transaction failed:", str(e))
```

### Common Revert Reasons

| Revert Message | Meaning |
|----------------|---------|
| `Insufficient balance` | Wallet does not have enough tokens |
| `Slippage exceeded` | Output amount fell below `minOut` |
| `Token is frozen` | Token is in frozen state; only whitelisted wallets can trade |
| `Loan expired` | The loan has passed its deadline |
| `Not the creator` | Caller is not the token/vesting creator |
| `Market not resolved` | Cannot redeem before market resolution |
| `Already proposed` | An outcome has already been proposed |

### Loan & Staking Reverts

| Revert Message | When It Happens | What To Do |
|----------------|-----------------|------------|
| `Position active. Use increaseLoan` | Called `borrow()` when a staking loan already exists for this wallet | Use `addToLoan(stasisAmount)` instead. Each wallet can only have one active staking loan at a time. |
| `Duration too short` | Called `addToLoan()` when the existing loan's remaining duration is below the contract minimum | Call `extendLoan(days, payInUsdb, refinance)` first to add more time, then retry `addToLoan()`. The loan must have sufficient remaining duration before you can add collateral to it. |
| `ERC20: insufficient allowance` | Called `extendLoan()` with `payInUsdb=true` but USDB is not approved to the staking contract | Approve USDB to the staking contract address before calling `extendLoan()`. The extension fee is paid in USDB when `payInUsdb` is true. |

**Correct staking loan flow:**

```
First loan:   borrow(stasisAmount, days)
Add more:     addToLoan(stasisAmount)       ← only if loan has enough remaining duration
Extend time:  extendLoan(days, true, false) ← approve USDB to staking contract first
Repay:        repay() or repayWithStasis()
```

**If your loan is near expiry and you want to add collateral:**

```python
# 1. Approve USDB to staking contract (for extension fee)
usdb.functions.approve(staking_address, 500 * 10**18)  # approve enough for fees

# 2. Extend the loan
client.staking.extend_loan(30, True, False)  # 30 more days, pay in USDB

# 3. Now you can add collateral
client.staking.add_to_loan(stasis_amount)
```

### Token Creation Reverts

| Revert Message | When It Happens | What To Do |
|----------------|-----------------|------------|
| `invalid starting LP` | `startLP` parameter is outside the valid range | Use a valid `startLP` value. Do not pass `0` — the contract requires a minimum. Check `contracts.json` documentation or existing tokens for valid values. `startLP` controls the initial liquidity pool configuration and affects the token's starting price. |

> ⚠️ **startLP directly affects token pricing.** An incorrect `startLP` value can result in tokens launching at unexpected prices (e.g., $1.19 instead of $1.00) or with inflated market caps. Always verify the expected starting price after creation with `factory.getTokenState(address)`.

### Prediction Market Reverts

| Revert Message | When It Happens | What To Do |
|----------------|-----------------|------------|
| `Seed below minimum` | `seedAmount` is less than the contract's `minSeed()` | Query `contract.functions.minSeed()` to get the minimum (currently 50 USDB). The seed provides initial liquidity for the AMM. Markets cannot be created without meeting this minimum. |

**Check minimum seed before creating a market:**

```python
min_seed = client.prediction_markets.contract.functions.minSeed().call()
print(f"Minimum seed: {min_seed / 10**18} USDB")  # Currently 50 USDB
```

```js
const minSeed = await client.predictionMarkets.contract.read.minSeed();
console.log("Minimum seed:", formatUnits(minSeed, 18), "USDB");  // Currently 50 USDB
```

---

## API Errors

API calls throw errors with HTTP status codes and error messages from the server.

| Status | Meaning |
|--------|---------|
| `400` | Bad request (missing required fields — see specific errors below) |
| `401` | Not authenticated (missing or expired session/API key) |
| `403` | Forbidden (not the owner or insufficient permissions) |
| `404` | Resource not found |
| `409` | Conflict (resource already exists — see metadata errors below) |
| `429` | Rate limit exceeded (60 req/min for API key, 30 req/min for session) |

### Image Upload Errors (POST /api/images)

| Error Message | Cause | Fix |
|---------------|-------|-----|
| `Missing or invalid purpose` | The `purpose` field was not included in the upload | Include `purpose: "token"` (or `"avatar"`) as a form field alongside the file upload |
| `Missing or invalid token address` | The `address` field was not included | Include `address: "0xTokenAddress..."` as a form field — identifies which token/market the image belongs to |
| `No file provided` | File upload used wrong field name | Use `file` as the multipart form field name (not `image`) |

**Correct image upload (Python):**

```python
# Image upload requires THREE fields: file, purpose, and address
files = {"file": ("token.webp", image_buffer, "image/webp")}
data = {"purpose": "token", "address": "0xYourTokenAddress..."}
response = session.post("https://launchonbasis.com/api/images", files=files, data=data)
```

> **SDK note:** As of SDK v1.0.3, the Python SDK's `upload_image()` and `upload_image_from_url()` methods do not send the required `purpose` and `address` fields. This causes a 400 error. Use the manual upload pattern above until the SDK is updated, or pass images during `create_token_with_metadata()` / `create_market_with_metadata()` which handle the upload internally.

### Metadata Errors (POST /api/metadata)

| Error Message | Cause | Fix |
|---------------|-------|-----|
| `Token metadata already exists` (409) | Metadata was already set during token/market creation | Metadata cannot currently be updated after initial creation. Always include all metadata (description, image, links) during `create_token_with_metadata()` or `create_market_with_metadata()`. There is no PATCH/PUT endpoint for metadata updates. |

> ⚠️ **Always include images at creation time.** Since metadata cannot be updated after creation, tokens/markets created without images will permanently lack images. If the image upload fails during creation, the token will be created but appear without an image on the platform — and there is currently no way to add one afterward.

---

## Non-Fatal Warnings

Order sync failures after `orderBook` write operations are logged as warnings but do not throw. The on-chain transaction succeeds regardless. You can manually sync later via `client.api.syncOrder(txHash)`.

---

## Transaction Sync

The SDK automatically syncs transaction state to the backend database after write operations across **ALL modules**. This calls the public `POST /api/v1/sync` endpoint (renamed from the former `syncLoan`), which requires no authentication.

**Covered modules:** Factory, Trading, Loans, Staking, Vesting, PredictionMarkets, MarketResolver, Taxes, OrderBook, PrivateMarkets, AgentIdentity.

**How it works:**
- After each write transaction confirms, the SDK fires a non-blocking `POST /api/v1/sync` request with the transaction hash.
- The backend auto-detects the transaction source from the contract address and processes all relevant events.
- If the sync request fails, a warning is logged but the on-chain transaction is not affected. Users do not need to call this manually.
- Rate limit: 20 requests per minute.
- Idempotent — submitting the same txHash twice is safe.

**Manual sync (if needed):**

**JavaScript:**

```js
await client.api.syncTransaction(txHash);
```

**Python:**

```python
client.api.sync_transaction(tx_hash)
```

> **Note:** The legacy `syncLoan` / `sync_loan` method still works but is deprecated — it simply delegates to `syncTransaction`.

---

## Pre-Flight Checks

Before executing multi-step operations (stacking strategies, leverage plays, etc.), query contract state to avoid reverts:

**Before creating a token:**
```python
fee = client.factory.get_fee_amount()      # BNB required (may be 0)
# Verify startLP value produces expected pricing after creation
```

**Before creating a prediction market:**
```python
min_seed = client.prediction_markets.contract.functions.minSeed().call()
# Ensure you have >= min_seed USDB available and approved
```

**Before borrowing/adding to loan:**
```python
stake = client.staking.get_user_stake_details(wallet)
available = client.staking.get_available_stasis(wallet)
# Check if a loan already exists (stake[2] > 0 means STASIS is pledged)
# If active loan: use add_to_loan(), and check remaining duration first
```

**Before extending a loan:**
```python
# Approve USDB to staking contract if paying extension fee in USDB
usdb.functions.approve(staking_address, amount)
```

These pre-flight checks prevent the most common agent failures. Test each step in isolation before chaining them into a multi-step strategy.

---
