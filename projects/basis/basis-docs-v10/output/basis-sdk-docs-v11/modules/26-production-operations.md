# Production Operations Guide

**What this covers:** Running a Basis agent in production - lifecycle, health checks, error recovery, state reconstruction, RPC configuration, and monitoring.
**Related sections:** → See: [03-getting-started.md](03-getting-started.md) for initial setup · → See: [22-error-handling.md](22-error-handling.md) for error codes · → See: [21-what-to-avoid.md](21-what-to-avoid.md) for common pitfalls · → See: [25-code-examples.md](25-code-examples.md) for bootstrap script

---

## Agent Lifecycle

A production Basis agent follows this lifecycle:

```
1. INIT          → Create client, register identity, claim USDB from daily faucet, fund BNB for gas
2. BUILD         → Develop and test your strategies (trading, creating, resolving, staking)
3. REGISTER      → Publish capabilities to ERC-8004 (publicly visible across the ecosystem)
4. OPERATE       → Run strategies, manage positions, earn points
5. MONITOR       → Watch positions, check health, handle alerts
6. RECOVER       → Rebuild state after crashes, handle RPC failures, retry stuck transactions
7. SHUTDOWN      → Close positions, repay loans, unstake, withdraw
```

**Don't skip step 2.** ERC-8004 registration is a public declaration of what your agent can do. Every registered agent that references Basis is visible ecosystem-wide. Register after you've built real capabilities - not on day one with empty metadata.

---

## Health Checks

Run these periodically (every 1-5 minutes for active agents):

**JS:**
```js
async function healthCheck(client) {
  const wallet = client.walletClient.account.address;

  // 1. RPC connectivity - can we reach the chain?
  try {
    const blockNumber = await client.publicClient.getBlockNumber();
    console.log("✅ RPC connected, block:", blockNumber);
  } catch (e) {
    console.error("🔴 RPC DOWN:", e.message);
    // → Switch to backup RPC or alert
    return false;
  }

  // 2. USDB balance - enough to operate?
  const usdbBalance = await client.publicClient.readContract({
    address: client.usdbAddress,
    abi: [{"inputs":[{"name":"","type":"address"}],"name":"balanceOf","outputs":[{"name":"","type":"uint256"}],"stateMutability":"view","type":"function"}],
    functionName: 'balanceOf',
    args: [wallet],
  });
  console.log("💰 USDB:", formatUnits(usdbBalance, 18));

  // 3. BNB balance - enough for gas?
  const bnbBalance = await client.publicClient.getBalance({ address: wallet });
  if (bnbBalance < parseUnits("0.005", 18)) {
    console.warn("— ️ Low BNB - refill for gas");
  }

  // 3b. Daily faucet claim check
  try {
    const faucetStatus = await client.api.getFaucetStatus();
    if (faucetStatus.canClaim) {
      console.log(`💧 Faucet available: ${faucetStatus.dailyAmount} USDB`);
      // Auto-claim or alert — your choice
    }
  } catch (e) {
    // Non-critical — faucet check failure shouldn't stop the health check
  }

  // 4. Open positions - any loans nearing expiry?
  const loanCount = await client.loans.getUserLoanCount(wallet);
  for (let i = 1n; i <= loanCount; i++) {
    const loan = await client.loans.getUserLoanDetails(wallet, i);
    if (loan.active) {
      const expiryMs = Number(loan.liquidationTime) * 1000;
      const hoursLeft = (expiryMs - Date.now()) / (1000 * 60 * 60);
      if (hoursLeft < 24) {
        console.warn(`— ️ Loan ${i} expires in ${hoursLeft.toFixed(1)}h - extend or repay`);
      }
    }
  }

  // 5. Leverage positions
  const levCount = await client.trading.getLeverageCount(wallet);
  for (let i = 1n; i <= levCount; i++) {
    const pos = await client.trading.getLeveragePosition(wallet, i);
    if (pos.active) {
      const expiryMs = Number(pos.liquidationTime) * 1000;
      const hoursLeft = (expiryMs - Date.now()) / (1000 * 60 * 60);
      if (hoursLeft < 24) {
        console.warn(`— ️ Leverage position ${i} expires in ${hoursLeft.toFixed(1)}h`);
      }
    }
  }

  return true;
}
```

---

## Error Recovery Patterns

### RPC Timeout / 429 Rate Limit

```js
async function withRetry(fn, maxRetries = 3, baseDelayMs = 1000) {
  for (let attempt = 1; attempt <= maxRetries; attempt++) {
    try {
      return await fn();
    } catch (e) {
      const isRetryable = e.message?.includes('timeout') ||
                          e.message?.includes('429') ||
                          e.message?.includes('ECONNRESET');
      if (!isRetryable || attempt === maxRetries) throw e;

      const delay = baseDelayMs * Math.pow(2, attempt - 1); // exponential backoff
      console.warn(`— ️ Attempt ${attempt} failed, retrying in ${delay}ms...`);
      await new Promise(r => setTimeout(r, delay));
    }
  }
}

// Usage:
const result = await withRetry(() => client.trading.buy(tokenAddr, amount));
```

### Transaction Stuck (Pending Too Long)

If a transaction is stuck in the mempool (common during BSC congestion):

1. **Check if it landed:** Query the transaction hash - if the receipt exists, it went through
2. **If still pending after 60s:** The SDK uses viem which handles nonce management, but you can manually resubmit with higher gas
3. **Never assume a timed-out transaction failed** - always check the receipt before retrying the operation, or you'll double-execute

```js
async function waitForTxSafe(client, hash, timeoutMs = 60000) {
  try {
    const receipt = await client.publicClient.waitForTransactionReceipt({
      hash,
      timeout: timeoutMs,
    });
    return receipt;
  } catch (e) {
    // Timeout - check if it landed anyway
    try {
      const receipt = await client.publicClient.getTransactionReceipt({ hash });
      if (receipt) return receipt; // It went through despite the timeout
    } catch {}
    throw new Error(`Transaction ${hash} timed out and may still be pending`);
  }
}
```

### BSC Chain Reorg Awareness

BSC uses a 3-second block time with occasional short reorgs (1-3 blocks). For time-sensitive operations:
- **Wait for 3+ block confirmations** before treating a transaction as final (especially for market finalization, loan extensions near expiry)
- **Don't act on pending transactions** - wait for `receipt.status === 'success'` with confirmation count
- Use `publicClient.waitForTransactionReceipt({ hash, confirmations: 3 })` for critical operations
- Reorgs are rare but can replay transactions in unexpected order - avoid chaining time-dependent transactions in rapid succession

### SIWE Session Expired

This only affects browser-based flows. **For long-running agents, use API keys** - they're auto-provisioned during `BasisClient.create()` and don't expire. The `client.apiKey` property persists across restarts if you store it.

If you do hit a 401:
```js
// Re-authenticate and get a fresh API key
const client = await BasisClient.create({
  privateKey: process.env.BASIS_PRIVATE_KEY,
});
// client.apiKey is now refreshed
```

---

## State Reconstruction After Crash

When your agent restarts after a crash, it needs to rebuild its view of open positions. All position data lives on-chain and can be queried directly:

```js
async function reconstructState(client) {
  const wallet = client.walletClient.account.address;
  const state = { loans: [], leveragePositions: [], staking: {} };

  // 1. Enumerate all loans
  const loanCount = await client.loans.getUserLoanCount(wallet);
  for (let i = 1n; i <= loanCount; i++) {
    const loan = await client.loans.getUserLoanDetails(wallet, i);
    if (loan.active) state.loans.push({ hubId: i, ...loan });
  }

  // 2. Enumerate all leverage positions
  const levCount = await client.trading.getLeverageCount(wallet);
  for (let i = 1n; i <= levCount; i++) {
    const pos = await client.trading.getLeveragePosition(wallet, i);
    if (pos.active) state.leveragePositions.push({ positionId: i, ...pos });
  }

  // 3. Check staking position (wSTASIS balance via direct contract read)
  const shares = await client.publicClient.readContract({
    address: client.stakingAddress, // wSTASIS vault contract
    abi: [{"inputs":[{"name":"","type":"address"}],"name":"balanceOf","outputs":[{"name":"","type":"uint256"}],"stateMutability":"view","type":"function"}],
    functionName: 'balanceOf',
    args: [wallet],
  });
  const stasisValue = await client.staking.convertToAssets(shares);
  state.staking = { shares, stasisValue };

  // 4. Check vesting schedules (enumerate by creator)
  const vestingIds = await client.vesting.getVestingsByCreator(wallet);
  for (const id of vestingIds) {
    // Process active vesting schedules...
  }
  // Also check vestings where you're the beneficiary
  const beneficiaryIds = await client.vesting.getVestingsByBeneficiary(wallet);
  for (const id of beneficiaryIds) {
    // Process vesting schedules you're receiving...
  }

  console.log(`Reconstructed: ${state.loans.length} loans, ${state.leveragePositions.length} leverage positions`);
  return state;
}
```

**Key principle:** The blockchain is the source of truth. The API is a convenience layer. If the API is down, all positions can be read directly from contracts via RPC.

---

## RPC Configuration

### Why Use a Dedicated RPC

The default public BSC endpoint (`bsc-dataseed.binance.org`) works for testing but has limitations:
- **Rate limits:** ~10-20 requests/second before throttling
- **No SLA:** Can be slow or unavailable during network congestion
- **Shared:** Every free user is hitting the same endpoint

For production agents making frequent calls (health checks, price monitoring, trading):

```js
const client = await BasisClient.create({
  privateKey: process.env.BASIS_PRIVATE_KEY,
  rpcUrl: "https://bsc-mainnet.nodereal.io/v1/YOUR_API_KEY", // or Ankr, QuickNode, Chainstack
});
```

### Recommended Providers (BSC)
- **Ankr** - Free tier available, good BSC support
- **QuickNode** - Fast, reliable, paid
- **NodeReal** - BSC-focused, meganode architecture
- **Chainstack** - Dedicated nodes available

### Failover Pattern

```js
const RPC_ENDPOINTS = [
  "https://your-primary-rpc.com",
  "https://bsc-dataseed1.binance.org",
  "https://bsc-dataseed2.binance.org",
];

async function createClientWithFailover() {
  for (const rpc of RPC_ENDPOINTS) {
    try {
      const client = await BasisClient.create({
        privateKey: process.env.BASIS_PRIVATE_KEY,
        rpcUrl: rpc,
      });
      console.log("Connected to:", rpc);
      return client;
    } catch (e) {
      console.warn(`RPC ${rpc} failed:`, e.message);
    }
  }
  throw new Error("All RPC endpoints failed");
}
```

---

## Transaction Sequencing

### Sequential Transactions

Always await the receipt before sending the next transaction:

```js
// ✅ Correct - sequential with receipts
const buy = await client.trading.buy(tokenAddr, parseUnits("10", 18));
// Receipt is already awaited inside buy()

const sell = await client.trading.sell(tokenAddr, parseUnits("5", 18));
// Safe - previous tx is confirmed
```

### Burst Operations

For operations that need multiple transactions (e.g., buying multiple tokens):

```js
// ✅ Correct - sequential loop
const tokens = ["0xToken1", "0xToken2", "0xToken3"];
for (const token of tokens) {
  const result = await client.trading.buy(token, parseUnits("10", 18));
  console.log(`Bought ${token}:`, result.hash);
  // Each buy() internally awaits the receipt, so nonce is managed
}

// ❌ Wrong - parallel sends will cause nonce collisions
// await Promise.all(tokens.map(t => client.trading.buy(t, amount)));
```

The SDK uses viem which manages nonces for sequential calls. **Do not send transactions in parallel** - BSC will reject them with nonce errors.

---

## Monitoring Checklist

Set up alerts for these conditions:

| What to Monitor | Check Method | Alert When |
|----------------|-------------|------------|
| Loan expiry | `getUserLoanDetails()` → `liquidationTime` | < 24 hours remaining |
| Leverage expiry | `getLeveragePosition()` → `liquidationTime` | < 24 hours remaining |
| BNB gas balance | `getBalance()` | < 0.005 BNB |
| USDB operating balance | `balanceOf()` on USDB contract | Below your minimum threshold |
| Faucet eligibility | `getFaucetStatus()` | `canClaim: true` (daily drip available) |
| Surge tax activation | `getCurrentSurgeTax(token)` | > 0 on tokens you're actively trading |
| Prediction market resolution | `getDisputeData(marketToken)` | Market in `awaiting_proposal` status |
| Staking lock expiry | Track `VOTE_LOCK_DURATION` after voting | Cannot unstake for 24h after vote |
| RPC health | `getBlockNumber()` | Timeout or stale block number |

### Monitoring Loop Example

```js
async function monitoringLoop(client) {
  const INTERVAL_MS = 60_000; // Check every minute

  while (true) {
    try {
      const healthy = await healthCheck(client);
      if (!healthy) {
        // Alert logic - send notification, switch RPC, etc.
      }
    } catch (e) {
      console.error("Monitoring error:", e.message);
    }
    await new Promise(r => setTimeout(r, INTERVAL_MS));
  }
}
```

---

## Shutdown Procedure

When shutting down gracefully:

1. **Stop opening new positions** - stop trading loops
2. **Repay active loans** before expiry (avoid collateral burn)
3. **Close leverage positions** via `partialLoanSell(id, 100, true, 0)` (100% = full close)
4. **Unstake** - `unlock()` → `sell()` (if not vote-locked)
5. **Claim any pending rewards** — `claimLiquidation(hubId)` for each expired loan, `claimBounty(marketToken)` for resolved markets
6. **Verify final state** - Run `reconstructState()` to confirm no orphaned positions
