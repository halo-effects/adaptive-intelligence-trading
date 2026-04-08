# Error Handling

**What this covers:** Contract revert reasons, API error codes, non-fatal warnings, and transaction sync behavior.

**Related sections:** → See: [19-offchain-api-reference.md](19-offchain-api-reference.md) for full API error codes · → See: [25-code-examples.md](25-code-examples.md) for try/catch patterns in context

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

---

## API Errors

API calls throw errors with HTTP status codes and error messages from the server.

| Status | Meaning |
|--------|---------|
| `401` | Not authenticated (missing or expired session/API key) |
| `403` | Forbidden (not the owner or insufficient permissions) |
| `404` | Resource not found |
| `429` | Rate limit exceeded (60 req/min for API key, 30 req/min for session) |

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
