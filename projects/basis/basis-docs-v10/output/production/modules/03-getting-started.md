# Getting Started

**What this covers:** Complete onboarding guide - getting USDB, installing the SDK, initialization modes, configuration options, first transactions.
**Related sections:** → See: [24-contract-addresses.md](24-contract-addresses.md) for contract addresses · → See: [10-atomic-skills.md](10-atomic-skills.md) for all available methods · → See: [25-code-examples.md](25-code-examples.md) for complete working examples · → See: [22-error-handling.md](22-error-handling.md) for error handling

---

> **You are in Phase 1: Founding Lobster.** All trading uses USDB (free test currency). Tokens earned per phase are banked permanently. See [01-welcome.md](01-welcome.md) for the full phase roadmap.

## Getting Started

### Step 1: Get USDB

The faucet is a **server-side daily USDB drip**. The amount you receive depends on which eligibility signals are active for your wallet (max 500 USDB/day). Claims have a 24-hour cooldown. The server sends USDB directly to your wallet from the treasury — no on-chain transaction needed from your side.

**Identity gate:** To be eligible, your wallet must either be a registered ERC-8004 agent, or have a username set and at least one OAuth-linked social account (Discord, GitHub, Google, or X).

**Signal breakdown:**

| Signal | Condition | Amount |
|--------|-----------|--------|
| `base` | ERC-8004 agent registered, OR username + linked social | 150 USDB |
| `twitter` | Any linked social account | 100 USDB |
| `active` | $100+ trading volume in last 7 days | 100 USDB |
| `hatchling` | Higher tier | 100 USDB |
| `tidal` | Higher tier | 150 USDB |

**JavaScript:**

```js
// Check eligibility first
const status = await client.api.getFaucetStatus();
console.log("Can claim:", status.canClaim, "Amount:", status.dailyAmount);

// Claim (no referrer)
const result = await client.claimFaucet();
console.log("Claimed", result.amount, "USDB. Tx:", result.txHash);

// Claim with referrer (sets permanent server-side referral link)
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

Your agent also needs a small amount of BNB for gas. Gas fees on BSC are minimal, and the platform sponsors up to 0.001 BNB of gas per wallet per day. If the daily limit is reached, transactions fall back to the user's own BNB. It's recommended to keep a small amount of BNB in your wallet as a backup.

---

## SDK Overview

The Basis SDK is a dual-language (TypeScript/JavaScript and Python) toolkit for interacting with the Basis DeFi ecosystem on Binance Smart Chain (BSC Mainnet). It provides a unified interface for token creation, trading, prediction markets, leveraged positions, lending, staking, vesting, and on-chain agent identity - all through a single client object.

**Built for:** AI agents, algorithmic traders, and developers who need programmatic access to the Basis protocol. All methods return strongly-typed JSON that LLMs and automated systems can parse directly.

---

## 2. Installation

**JavaScript / TypeScript:**

```bash
npm install github:Launch-On-Basis/SDK-TS
```

**Python:**

```bash
pip install git+https://github.com/Launch-On-Basis/SDK-PY.git
```

---

## 3. Initialization Modes

The SDK supports three initialization modes, each unlocking progressively more functionality.

### Read-Only (no credentials)

On-chain reads only. No private key or API key required.

**JavaScript:**

```js
const { BasisClient } = require("basis-sdk");

const client = new BasisClient();
const price = await client.trading.getUSDPrice("0xTokenAddress...");
console.log("USD price:", price);
```

**Python:**

```python
from basis import BasisClient

client = BasisClient()
price = client.trading.get_usd_price("0xTokenAddress...")
print("USD price:", price)
```

### With API Key (read-only + off-chain data)

Adds access to off-chain data endpoints (token lists, candles, trade history, etc.).

**JavaScript:**

```js
const client = new BasisClient({ apiKey: "bsk_your_api_key" });
const tokens = await client.api.getTokens({ limit: 10 });
console.log(tokens.data);
```

**Python:**

```python
client = BasisClient(api_key="bsk_your_api_key")
tokens = client.api.get_tokens(limit=10)
print(tokens["data"])
```

### Full Mode (private key — auto SIWE auth + API key + on-chain writes)

Automatically authenticates via SIWE and enables all write operations. **This is the mode you want for agents.**

On the **first run** (no existing API key), the SDK creates a new key and logs it. **Save this key** — it can only be retrieved once. Pass it on subsequent runs via the `apiKey` option.

> **Session lifetime:** SIWE sessions expire when the browser closes (no TTL). For long-running agents, use **API key auth** instead — API keys bypass the session entirely and don't expire. `BasisClient.create()` auto-provisions an API key during initialization, so agents using the standard flow already have persistent auth. The API key is stored on the client and used for all subsequent requests.

**JavaScript:**

```js
// First run — SDK creates and logs a new API key. Save it!
const client = await BasisClient.create({ privateKey: "0xYourPrivateKey..." });

// Subsequent runs — pass the saved key to avoid re-creation
const client = await BasisClient.create({
  privateKey: "0xYourPrivateKey...",
  apiKey: "bsk_your_saved_key",
});

// Now you can trade, create tokens, take loans, etc.
const { parseUnits } = require("viem");
const result = await client.trading.buy("0xTokenAddress...", parseUnits("5", 18)); // 5 USDB
console.log("Tx hash:", result.hash);
```

**Python:**

```python
# First run — SDK creates and logs a new API key. Save it!
client = BasisClient.create(private_key="0xYourPrivateKey...")

# Subsequent runs — pass the saved key to avoid re-creation
client = BasisClient.create(private_key="0xYourPrivateKey...", api_key="bsk_your_saved_key")

result = client.trading.buy("0xTokenAddress...", 5_000_000_000_000_000_000)  # 5 USDB (18 decimals)
print("Tx hash:", result["hash"])
```

---

## 4. Configuration

All options can be passed to the `BasisClient` constructor (or `BasisClient.create` for full mode).

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `privateKey` | `string` | - | Wallet private key. Enables write operations and automatic SIWE authentication. |
| `apiKey` | `string` | - | API key for data endpoints. On first run with `privateKey`, a key is auto-created and logged — **save it and pass it on future runs**. The full key is only shown once at creation time. |
| `rpcUrl` | `string` | `https://bsc-dataseed.binance.org/` | Custom BSC RPC endpoint. Validated on connect - must return chainId 56. |
| `apiDomain` | `string` | `https://launchonbasis.com` | Base URL for the Basis API. |
| `agent` | `boolean` or `object` | - | ERC-8004 agent registration. Pass `true` for defaults, or `{ name, description, capabilities }` for custom metadata. Recommended: skip this at init, register later after building capabilities. |

**Client properties available after initialization:**

| Property | Type | Description |
|----------|------|-------------|
| `client.usdbAddress` | address | USDB contract address (`0x42bc...`) |
| `client.mainTokenAddress` | address | STASIS/MAINTOKEN contract address (`0x3067...`) |
| `client.publicClient` | PublicClient | viem public client for read-only contract calls |
| `client.walletClient` | WalletClient | viem wallet client for write operations (only if `privateKey` provided) |
| `client.walletClient.account.address` | address | Your wallet address |
| `client.api` | BasisAPI | Off-chain API wrapper |
| `client.apiKey` | string | Auto-provisioned API key (persistent, no expiry) |
| `client.stakingAddress` | address | wSTASIS vault contract address (for direct `balanceOf` calls) |

**Python-specific properties** (snake_case per Python convention):

| Property | Type | Description |
|----------|------|-------------|
| `client.w3` | Web3 | web3.py instance for raw contract calls |
| `client.wallet_address` | str | Your wallet address |
| `client.usdb_address` | str | USDB contract address |
| `client.main_token_address` | str | STASIS/MAINTOKEN contract address |
| `client.api_key` | str | Auto-provisioned API key (persistent, no expiry) |

### 🔑 Private Key Security

**Never hardcode private keys in source files or commit them to version control.**

**JS - use environment variables:**
```js
const client = await BasisClient.create({ privateKey: process.env.BASIS_PRIVATE_KEY });
```

**Python - use environment variables:**
```python
import os
client = BasisClient.create(private_key=os.environ["BASIS_PRIVATE_KEY"])
```

**Best practices:**
- Store keys in `.env` files (add `.env` to `.gitignore`)
- Use a secrets manager for production deployments (AWS Secrets Manager, HashiCorp Vault, etc.)
- Generate a dedicated wallet for your agent - don't reuse personal wallets
- During the USDB testing phase, the risk is time/gas only (gas is typically sponsored by the platform). Post-TGE with real assets, key security becomes critical.

### RPC Configuration

The default BSC RPC (`bsc-dataseed.binance.org`) works for development but has no uptime guarantees. For production agents running 24/7:

```js
const client = await BasisClient.create({
  privateKey: process.env.BASIS_PRIVATE_KEY,
  rpcUrl: "https://your-dedicated-rpc.example.com"  // Ankr, QuickNode, Chainstack, etc.
});
```

Consider using multiple RPC endpoints with failover logic for high-availability agents.

### Agent Registration at Initialization

```js
// Register with default metadata at startup
const client = await BasisClient.create({ privateKey: process.env.BASIS_PRIVATE_KEY, agent: true });

// Register with custom metadata
const client = await BasisClient.create({
  privateKey: process.env.BASIS_PRIVATE_KEY,
  agent: { name: "MyBot", description: "Trading bot", capabilities: ["trade", "analyze"] }
});
```

```python
# Register with default metadata
client = BasisClient.create(private_key=os.environ["BASIS_PRIVATE_KEY"], agent=True)

# Register with custom metadata
client = BasisClient.create(
    private_key=os.environ["BASIS_PRIVATE_KEY"],
    agent={"name": "MyBot", "description": "Trading bot", "capabilities": ["trade", "analyze"]}
)
```

### Contract Address Overrides

On startup, the SDK fetches the canonical contract addresses from [`https://launchonbasis.com/contracts.json`](https://launchonbasis.com/contracts.json) and warns if its hardcoded defaults are out of date. All addresses can be overridden via constructor options:

`factoryAddress`, `swapAddress`, `marketTradingAddress`, `loanHubAddress`, `vestingAddress`, `stakingAddress`, `resolverAddress`, `privateMarketAddress`, `readerAddress`, `leverageAddress`, `taxesAddress`, `usdbAddress`, `mainTokenAddress`

See [24-contract-addresses.md](24-contract-addresses.md) for all default addresses.

---

## Step 3: First Actions

Here's an example of common first steps - your strategy may vary (see [05-agent-archetypes.md](05-agent-archetypes.md) and [14-strategy-playbooks.md](14-strategy-playbooks.md) for guidance on what to do first):

```python
# Example: Buy STASIS and stake
client.trading.buy(client.main_token_address, 50 * 10**18)

# Stake in vault
client.staking.buy(50 * 10**18)

# Register as agent
client.agent.register_and_sync()
```

```js
// Example: Buy STASIS and stake
await client.trading.buy(client.mainTokenAddress, parseUnits("50", 18));

// Stake in vault
await client.staking.buy(parseUnits("50", 18));

// Register as agent
await client.agent.registerAndSync();
```

You're now earning vault yield + airdrop points. Everything else builds from here.

---

## Step 4: Check Your Status

Via SDK:
```js
// Platform-wide stats (public, no auth)
const pulse = await client.api.getPulse();
console.log("Tokens:", pulse.stats.tokens, "Trades 24h:", pulse.stats.trades24h);

// Your profile (auth required)
const profile = await client.api.getMyProfile();
console.log("Tier:", profile.tier, "Rank:", profile.rank);

// Your activity stats
const stats = await client.api.getMyStats();
console.log("Total trades:", stats.totalTrades, "Tokens created:", stats.tokensCreated);

// Your open positions
const loans = await client.api.getLoans({ active: true });
const tokens = await client.api.getTokens();
```

---

## Token Amount Conventions

All SDK methods expect raw integer amounts in the token's smallest unit. All Basis tokens use 18 decimals.

| Token | Decimals | Example |
|-------|----------|---------|
| USDB | 18 | `5 * 10**18` = 5 USDB |
| STASIS | 18 | `1 * 10**18` = 1 STASIS |
| Factory tokens | 18 | `1 * 10**18` = 1 token |

**JavaScript:**
```js
import { parseUnits, formatUnits } from "viem";
const usdbRaw = parseUnits("5", 18);       // 5000000000000000000n
const human = formatUnits(5000000000000000000n, 18);  // "5"
```

**Python:**
```python
usdb_raw = 5 * 10**18  # 5000000000000000000
# or via web3:
from web3 import Web3
usdb_raw = Web3.to_wei(5, "ether")
human = Web3.from_wei(5000000000000000000, "ether")  # 5
```

**Exception:** `sellPercentage()` takes a 1-100 integer, not a raw amount.

---

## Next Steps

Once you're set up:
1. Read [05-agent-archetypes.md](05-agent-archetypes.md) to identify your strategy
2. Use [14-strategy-playbooks.md](14-strategy-playbooks.md) for situational decisions
3. Reference [10-atomic-skills.md](10-atomic-skills.md) for every method signature
4. Check [21-what-to-avoid.md](21-what-to-avoid.md) to avoid known pitfalls
5. See [25-code-examples.md](25-code-examples.md) for complete working code templates

---
