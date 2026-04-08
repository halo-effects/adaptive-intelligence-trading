# Code Examples

**What this covers:** Five complete, working code examples covering the most common operations — token creation, trading, prediction markets, leverage, and DeFi operations (loans + staking).

**Related sections:** → See: [10-atomic-skills.md](10-atomic-skills.md) for all available methods · → See: [03-getting-started.md](03-getting-started.md) for client initialization · → See: [23-contract-addresses.md](23-contract-addresses.md) for contract addresses and decimals

---

> — ️ **Slippage protection:** Many examples below use `0n` / `0` for `minOut` parameters for simplicity. **In production, always calculate a minimum output with slippage tolerance:**
> ```js
> // Helper: calculate minOut with slippage tolerance
> function withSlippage(expectedOut, tolerancePercent = 1) {
>   return expectedOut * BigInt(100 - tolerancePercent) / 100n; // 1% default tolerance
> }
>
> // Usage: preview first, then set minOut
> const preview = await client.trading.getAmountsOut(amount, path);
> const minOut = withSlippage(preview[preview.length - 1], 2); // 2% slippage tolerance (last element = output amount)
> const result = await client.trading.buyTokens(amount, minOut, path, false);
> ```
> Without slippage protection, your trades are vulnerable to sandwich attacks and price movement between simulation and execution.
>
> **Python equivalent:**
> ```python
> def with_slippage(expected_out, tolerance_percent=1):
>     """Calculate minimum output with slippage tolerance."""
>     return expected_out * (100 - tolerance_percent) // 100
>
> # Usage:
> preview = client.trading.get_amounts_out(amount, path)
> min_out = with_slippage(preview[-1], 2)  # 2% tolerance (last element = output amount)
> result = client.trading.buy_tokens(amount, min_out, path, False)
> ```
>
> **Note:** The `withSlippage()` / `with_slippage()` helpers above are used throughout all examples below. If you jump to a specific example via the index, reference this block for the definition.

---

## Example 1: Create a Token with Metadata

Full flow: initialize client, create a token, upload an image, and register metadata.

⚠️ **Token symbols must always be CAPITALISED** (e.g., `"MYTKN"`, not `"mytkn"`).

**JavaScript:**

```js
const { BasisClient } = require("basis-sdk");

async function createTokenWithMetadata() {
  // Initialize with full mode
  const client = await BasisClient.create({ privateKey: "0xYourPrivateKey..." });

  // One call — creates token + uploads image + registers metadata
  const result = await client.factory.createTokenWithMetadata({
    symbol: "MYTKN",
    name: "My Awesome Token",
    hybridMultiplier: 50n,
    startLP: 1000n,
    description: "My awesome DeFi token on Basis",
    imageUrl: "https://example.com/my-logo.png",
    website: "https://myproject.com",
  });
  console.log("Token:", result.tokenAddress);
  console.log("Image:", result.imageUrl);
  console.log("Metadata:", result.metadata.url);
}
```

**Python:**

```python
from basis import BasisClient

def create_token_example():
    client = BasisClient.create(private_key="0xYourPrivateKey...")

    # One call — creates token + uploads image + registers metadata
    result = client.factory.create_token_with_metadata(
        symbol="MYTKN", name="My Awesome Token",
        hybrid_multiplier=50, start_lp=1000,
        description="My awesome DeFi token on Basis",
        image_url="https://example.com/my-logo.png",
        website="https://myproject.com",
    )
    print("Token:", result["token_address"])
    print("Image:", result["image_url"])
    print("Metadata:", result["metadata"]["url"])
```

---

## Example 2: Trade Tokens

Buy tokens, check balance, then sell a percentage.

**JavaScript:**

```js
const { BasisClient } = require("basis-sdk");

async function tradeTokens() {
  const client = await BasisClient.create({ privateKey: "0xYourPrivateKey..." });

  const TOKEN = "0xTokenAddress...";

  // Check current price
  const price = await client.trading.getUSDPrice(TOKEN);
  console.log("Current price:", price, "USD");

  // Preview the swap (5 USDB = 5_000_000_000_000_000_000 raw)
  const { parseUnits } = require("viem");
  const fiveUsdb = parseUnits("5", 18);
  const preview = await client.trading.getAmountsOut(fiveUsdb, [
    client.usdbAddress, client.mainTokenAddress, TOKEN
  ]);
  console.log("Expected output for 5 USDB:", preview);

  // Buy with 5 USDB — with slippage protection and error handling
  const minOut = withSlippage(preview[preview.length - 1], 2); // 2% tolerance on final output amount
  try {
    const buyResult = await client.trading.buy(TOKEN, fiveUsdb, minOut);
    console.log("Bought tokens:", buyResult.hash);
  } catch (e) {
    if (e.message.includes("slippage")) {
      console.log("Slippage exceeded — retrying with higher tolerance");
      const retryMinOut = withSlippage(preview[preview.length - 1], 5); // 5% on retry
      const buyResult = await client.trading.buy(TOKEN, fiveUsdb, retryMinOut);
      console.log("Bought on retry:", buyResult.hash);
    } else {
      throw e; // Re-throw unexpected errors
    }
  }

  // Sell 50% of holdings (no amount needed — reads balance automatically)
  const sellResult = await client.trading.sellPercentage(TOKEN, 50);
  console.log("Sold 50%:", sellResult.hash);
}
```

**Python:**

```python
from basis import BasisClient

def trade_tokens():
    client = BasisClient.create(private_key="0xYourPrivateKey...")

    TOKEN = "0xTokenAddress..."
    FIVE_USDB = 5 * 10**18  # 5 USDB in raw units (18 decimals)

    price = client.trading.get_usd_price(TOKEN)
    print("Current price:", price, "USD")

    preview = client.trading.get_amounts_out(FIVE_USDB, [
        client.usdb_address, client.main_token_address, TOKEN
    ])
    print("Expected output for 5 USDB:", preview)

    # Buy with slippage protection
    min_out = preview[-1] * 98 // 100  # 2% slippage tolerance (last element = output amount)
    buy_result = client.trading.buy(TOKEN, FIVE_USDB, min_out)
    print("Bought tokens:", buy_result["hash"])

    # Sell 50% of holdings (no amount needed — reads balance automatically)
    sell_result = client.trading.sell_percentage(TOKEN, 50)
    print("Sold 50%:", sell_result["hash"])
```

---

## Example 3: Prediction Market

Create a market, buy shares, and list a sell order.

⚠️ **Market symbols must always be CAPITALISED** (e.g., `"ETH10K"`, not `"eth10k"`).

**JavaScript:**

```js
const { BasisClient } = require("basis-sdk");

async function predictionMarket() {
  const client = await BasisClient.create({ privateKey: "0xYourPrivateKey..." });

  const MAINTOKEN = client.mainTokenAddress;
  const USDB = client.usdbAddress;

  // 1. Create a prediction market with metadata
  const endTime = BigInt(Math.floor(Date.now() / 1000) + 86400 * 30);
  const market = await client.predictionMarkets.createMarketWithMetadata({
    marketName: "Will ETH reach $10k this month?",
    symbol: "ETH10K",
    endTime,
    optionNames: ["Yes", "No"],
    maintoken: MAINTOKEN,
    seedAmount: parseUnits("50", 18),
    description: "ETH price prediction.",
    imageUrl: "https://example.com/eth.jpg",
  });
  console.log("Market created:", market.hash);
  const marketToken = market.marketTokenAddress;

  // 2. Buy "Yes" shares (outcomeId 0) with 5 USDB — with slippage protection
  const fiveUsdb = parseUnits("5", 18);
  // Preview: check current share price to estimate expected output
  const outcomes = await client.marketReader.getAllOutcomes(
    "0x396216fc9d2c220afD227B59097cf97B7dEaCb57", marketToken
  );
  const yesPrice = outcomes[0].pricePerShare; // raw 18-decimal price
  const expectedShares = fiveUsdb * BigInt(1e18) / yesPrice;
  const minShares = withSlippage(expectedShares, 2); // 2% tolerance
  const buyResult = await client.predictionMarkets.buy(
    marketToken, 0, USDB, fiveUsdb, 0n, minShares
  );
  console.log("Bought Yes shares:", buyResult.hash);

  // 3. Check our shares
  const walletAddress = client.walletClient.account.address;
  const shares = await client.predictionMarkets.getUserShares(marketToken, walletAddress, 0);
  console.log("My Yes shares:", shares);

  // 4. List half for sale at 0.60 USDB per share
  const halfShares = shares / 2n;
  const orderResult = await client.orderBook.listOrder(marketToken, 0, halfShares, parseUnits("0.6", 18));
  console.log("Order listed:", orderResult.hash);
}
```

**Python:**

```python
import time
from basis import BasisClient

def prediction_market():
    client = BasisClient.create(private_key="0xYourPrivateKey...")

    MAINTOKEN = client.main_token_address
    USDB = client.usdb_address

    end_time = int(time.time()) + 86400 * 30
    market = client.prediction_markets.create_market_with_metadata(
        market_name="Will ETH reach $10k this month?", symbol="ETH10K",
        end_time=end_time, option_names=["Yes", "No"],
        maintoken=MAINTOKEN, seed_amount=50 * 10**18,
        description="ETH price prediction.",
        image_url="https://example.com/eth.jpg",
    )
    market_token = market["market_token_address"]

    # Buy with slippage protection
    five_usdb = 5_000_000_000_000_000_000
    outcomes = client.market_reader.get_all_outcomes(
        "0x396216fc9d2c220afD227B59097cf97B7dEaCb57", market_token
    )
    yes_price = int(outcomes[0]["pricePerShare"])
    expected_shares = five_usdb * 10**18 // yes_price
    min_shares = expected_shares * 98 // 100  # 2% slippage tolerance
    buy_result = client.prediction_markets.buy(market_token, 0, USDB, five_usdb, 0, min_shares)
    print("Bought Yes shares:", buy_result["hash"])

    shares = client.prediction_markets.get_user_shares(
        market_token, client.wallet_address, 0
    )
    print("My Yes shares:", shares)

    half_shares = int(shares) // 2
    order_result = client.order_book.list_order(market_token, 0, half_shares, 600_000_000_000_000_000)  # 0.60 USDB
    print("Order listed:", order_result["hash"])
```

---

## Example 4: Leverage Trading

Simulate a leveraged position, open it, and partially close.

**JavaScript:**

```js
const { BasisClient } = require("basis-sdk");

async function leverageTrading() {
  const client = await BasisClient.create({ privateKey: "0xYourPrivateKey..." });

  const USDB = client.usdbAddress;
  const MAINTOKEN = client.mainTokenAddress;
  const path = [USDB, MAINTOKEN];

  // 1. Simulate the leverage position
  const sim = await client.leverageSimulator.simulateLeverage(parseUnits("10", 18), path, 10n);
  console.log("Simulation:", sim);

  // 2. Open the leverage position (10 USDB, 10 days minimum) — with slippage protection
  const expectedOut = await client.trading.getAmountsOut(parseUnits("10", 18), path);
  const minOut = withSlippage(expectedOut[expectedOut.length - 1], 3); // 3% tolerance for leverage (multi-hop)
  const openResult = await client.trading.leverageBuy(parseUnits("10", 18), minOut, path, 10n);
  console.log("Position opened:", openResult.hash);

  // 3. Wait for backend to sync the new position (~5s)
  await new Promise(resolve => setTimeout(resolve, 5000));

  // 4. Get the position details
  // Note: leverage positions are 1-indexed (same as hubId — both use ++count)
  const walletAddress = client.walletClient.account.address;
  const positionCount = await client.trading.getLeverageCount(walletAddress);
  const positionId = positionCount; // 1-indexed: first position = 1, latest = count
  const position = await client.trading.getLeveragePosition(walletAddress, positionId);
  console.log("Position:", position);

  // 5. Partially close (sell 50%) — with slippage protection
  // Estimate output from selling 50% of position tokens
  const sellAmount = position.collateralAmount / 2n;
  const sellPreview = await client.trading.getAmountsOut(sellAmount, [MAINTOKEN, USDB]);
  const sellMinOut = withSlippage(sellPreview[sellPreview.length - 1], 2);
  const closeResult = await client.trading.partialLoanSell(positionId, 50n, true, sellMinOut);
  console.log("Partially closed:", closeResult.hash);
}
```

**Python:**

```python
import time
from basis import BasisClient

def leverage_trading():
    client = BasisClient.create(private_key="0xYourPrivateKey...")

    USDB = client.usdb_address
    MAINTOKEN = client.main_token_address
    path = [USDB, MAINTOKEN]

    sim = client.leverage_simulator.simulate_leverage(10_000_000_000_000_000_000, path, 10)
    print("Simulation:", sim)

    # Open with slippage protection (10 days minimum)
    expected_out = client.trading.get_amounts_out(10_000_000_000_000_000_000, path)
    min_out = expected_out[-1] * 97 // 100  # 3% tolerance for leverage
    open_result = client.trading.leverage_buy(10_000_000_000_000_000_000, min_out, path, 10)
    print("Position opened:", open_result["hash"])

    time.sleep(5)  # Wait for backend to sync the new position

    # Leverage positions are 1-indexed (same as hubId — both use ++count)
    position_count = client.trading.get_leverage_count(client.wallet_address)
    position_id = position_count  # 1-indexed: first position = 1, latest = count
    position = client.trading.get_leverage_position(client.wallet_address, position_id)
    print("Position:", position)

    # Partial close with slippage protection
    sell_preview = client.trading.get_amounts_out(int(position["collateralAmount"]) // 2, [MAINTOKEN, USDB])
    sell_min_out = sell_preview[-1] * 98 // 100  # 2% tolerance
    close_result = client.trading.partial_loan_sell(position_id, 50, True, sell_min_out)
    print("Partially closed:", close_result["hash"])
```

---

## Example 5: DeFi Operations

### Loans: Take, Extend, and Repay

**JavaScript:**

```js
const { BasisClient } = require("basis-sdk");

async function loanOperations() {
  const client = await BasisClient.create({ privateKey: "0xYourPrivateKey..." });

  const MAINTOKEN = client.mainTokenAddress;
  const COLLATERAL_TOKEN = "0xCollateralToken...";

  // 1. Take a loan (100 tokens as collateral, 30-day term)
  const { parseUnits } = require("viem");
  const loanResult = await client.loans.takeLoan(MAINTOKEN, COLLATERAL_TOKEN, parseUnits("100", 18), 30n);
  console.log("Loan taken:", loanResult.hash);

  // 2. Get loan details — hubId is 1-indexed (first loan = 1, not 0)
  const walletAddress = client.walletClient.account.address;
  const loanCount = await client.loans.getUserLoanCount(walletAddress);
  const hubId = loanCount; // loanCount IS the latest hubId (1-indexed)
  const details = await client.loans.getUserLoanDetails(walletAddress, hubId);
  console.log("Loan details:", details);

  // 3. Extend by 15 days (pay in USDB)
  const extendResult = await client.loans.extendLoan(hubId, 15, true, false);
  console.log("Loan extended:", extendResult.hash);

  // 4. Repay in full
  const repayResult = await client.loans.repayLoan(hubId);
  console.log("Loan repaid:", repayResult.hash);
}
```

**Python:**

```python
from basis import BasisClient

def loan_operations():
    client = BasisClient.create(private_key="0xYourPrivateKey...")

    MAINTOKEN = client.main_token_address
    COLLATERAL_TOKEN = "0xCollateralToken..."

    loan_result = client.loans.take_loan(MAINTOKEN, COLLATERAL_TOKEN, 100 * 10**18, 30)  # 100 tokens
    print("Loan taken:", loan_result["hash"])

    # hubId is 1-indexed (first loan = 1, not 0)
    loan_count = client.loans.get_user_loan_count(client.wallet_address)
    hub_id = loan_count  # loan_count IS the latest hubId (1-indexed)
    details = client.loans.get_user_loan_details(client.wallet_address, hub_id)
    print("Loan details:", details)

    extend_result = client.loans.extend_loan(hub_id, 15, True, False)
    print("Loan extended:", extend_result["hash"])

    repay_result = client.loans.repay_loan(hub_id)
    print("Loan repaid:", repay_result["hash"])
```

### Staking: Stake, Lock, Borrow, and Repay

**JavaScript:**

```js
async function stakingOperations() {
  const client = await BasisClient.create({ privateKey: "0xYourPrivateKey..." });

  const { parseUnits } = require("viem");

  // 1. Wrap STASIS into wSTASIS
  const stakeResult = await client.staking.buy(parseUnits("100", 18)); // 100 STASIS
  console.log("Wrapped 100 STASIS:", stakeResult.hash);

  // 2. Lock wSTASIS as collateral
  const shares = await client.staking.convertToShares(parseUnits("100", 18));
  const lockResult = await client.staking.lock(shares);
  console.log("Locked wSTASIS:", lockResult.hash);

  // 3. Borrow against locked collateral
  const borrowResult = await client.staking.borrow(parseUnits("50", 18), 30n); // 50 STASIS equivalent, 30 days
  console.log("Borrowed against stake:", borrowResult.hash);

  // 4. Repay the staking loan
  const repayResult = await client.staking.repay();
  console.log("Repaid staking loan:", repayResult.hash);

  // 5. Unlock and unwrap
  // Note: pass shares as BigInt directly — do NOT convert with Number() as it loses precision for large values
  const unlockResult = await client.staking.unlock(shares);
  console.log("Unlocked:", unlockResult.hash);

  const sellResult = await client.staking.sell(shares);
  console.log("Unwrapped to STASIS:", sellResult.hash);
}
```

**Python:**

```python
def staking_operations():
    client = BasisClient.create(private_key="0xYourPrivateKey...")

    stake_result = client.staking.buy(100 * 10**18)  # 100 STASIS
    print("Wrapped 100 STASIS:", stake_result["hash"])

    shares = client.staking.convert_to_shares(100 * 10**18)
    lock_result = client.staking.lock(int(shares))
    print("Locked wSTASIS:", lock_result["hash"])

    borrow_result = client.staking.borrow(50 * 10**18, 30)  # 50 STASIS, 30 days
    print("Borrowed against stake:", borrow_result["hash"])

    repay_result = client.staking.repay()
    print("Repaid staking loan:", repay_result["hash"])

    unlock_result = client.staking.unlock(int(shares))
    print("Unlocked:", unlock_result["hash"])

    sell_result = client.staking.sell(int(shares))
    print("Unwrapped to STASIS:", sell_result["hash"])
```

---

## Example 6: Agent Bootstrap — First Hour on Basis

A complete script to go from zero to operational. Covers initialization, USDB acquisition, agent registration, first trade, and staking.

**JS:**
```js
import { BasisClient } from 'basis-sdk';
import { parseUnits, formatUnits } from 'viem';

async function bootstrap() {
  // 1. Initialize client (auto-authenticates via SIWE, provisions API key)
  // NOTE: Save the API key from first run — it's only shown once!
  const client = await BasisClient.create({
    privateKey: process.env.BASIS_PRIVATE_KEY,
    // apiKey: process.env.BASIS_API_KEY, // pass on subsequent runs
  });
  console.log("✅ Client initialized");

  // 2. Register agent on ERC-8004 (required for faucet eligibility)
  const { agentId } = await client.agent.registerAndSync({
    name: "MyTradingBot",
    capabilities: ["trade", "analyze", "stake"],
  });
  console.log("🤖 Agent registered on ERC-8004, agentId:", agentId);

  // 3. Claim USDB from faucet (daily drip, max 500 USDB/day based on signals)
  const faucetStatus = await client.api.getFaucetStatus();
  console.log("Faucet eligible:", faucetStatus.canClaim, "Amount:", faucetStatus.dailyAmount);

  if (faucetStatus.canClaim) {
    const claim = await client.claimFaucet();
    console.log(`💰 Claimed ${claim.amount} USDB. Tx: ${claim.txHash}`);
  }

  // 4. Check your USDB balance
  const usdbBalance = await client.publicClient.readContract({
    address: client.usdbAddress,
    abi: [{"inputs":[{"name":"","type":"address"}],"name":"balanceOf","outputs":[{"name":"","type":"uint256"}],"stateMutability":"view","type":"function"}],
    functionName: 'balanceOf',
    args: [client.walletClient.account.address],
  });
  console.log(`💰 USDB balance: ${formatUnits(usdbBalance, 18)}`);

  // 5. Buy STASIS (the main token) — earns trading points
  const buyResult = await client.trading.buy(
    client.mainTokenAddress,
    parseUnits("100", 18)  // 100 USDB
  );
  console.log("→ Bought STASIS:", buyResult.hash);

  // 6. Stake for yield — earns staking points daily
  const wrapResult = await client.staking.buy(parseUnits("50", 18)); // wrap 50 STASIS → wSTASIS
  console.log("🏦 Wrapped to wSTASIS:", wrapResult.hash);

  // IMPORTANT: lock() takes wSTASIS shares, not STASIS units
  // Use convertToShares() to get the correct amount
  const shares = await client.staking.convertToShares(parseUnits("50", 18));
  const lockResult = await client.staking.lock(shares);
  console.log("🔑 Locked:", lockResult.hash);

  // 7. Check a prediction market
  const outcomes = await client.marketReader.getAllOutcomes(
    "0x396216fc9d2c220afD227B59097cf97B7dEaCb57", // MarketTrading contract
    "0xYourMarketTokenAddress"
  );
  console.log("📊 Market outcomes:", outcomes);

  // 8. Check your profile and stats
  const profile = await client.api.getMyProfile();
  console.log("Tier:", profile.tier, "Rank:", profile.rank);

  console.log("\n🎉 Bootstrap complete! You are now:");
  console.log("  - Registered on ERC-8004 (faucet eligible)");
  console.log("  - Earning trading points from the STASIS buy");
  console.log("  - Earning daily staking yield + staking points");
  console.log("  - Ready to trade, create tokens, or resolve markets");
  console.log("  - Claim faucet daily to keep building capital");
}

bootstrap().catch(console.error);
```

**Python:**
```python
from basis import BasisClient
import os

# 1. Initialize client (auto-authenticates via SIWE, provisions API key)
# Save the API key from first run — it's only shown once!
client = BasisClient.create(private_key=os.environ["BASIS_PRIVATE_KEY"])
# Subsequent runs: client = BasisClient.create(private_key=..., api_key=os.environ["BASIS_API_KEY"])
print("✅ Client initialized")

# 2. Register agent on ERC-8004 (required for faucet eligibility)
agent_result = client.agent.register_and_sync({
    "name": "MyTradingBot",
    "capabilities": ["trade", "analyze", "stake"],
})
print("🤖 Agent registered:", agent_result)

# 3. Claim USDB from faucet (daily drip, max 500 USDB/day based on signals)
faucet_status = client.api.get_faucet_status()
print("Faucet eligible:", faucet_status["canClaim"], "Amount:", faucet_status["dailyAmount"])

if faucet_status["canClaim"]:
    claim = client.claim_faucet()
    print(f"💰 Claimed {claim['amount']} USDB. Tx: {claim['txHash']}")

# 4. Buy STASIS
buy_result = client.trading.buy(client.main_token_address, 100 * 10**18)
print("→ Bought STASIS:", buy_result["hash"])

# 5. Stake — lock() takes wSTASIS shares, not STASIS units!
wrap_result = client.staking.buy(50 * 10**18)
print("🏦 Wrapped:", wrap_result["hash"])

shares = client.staking.convert_to_shares(50 * 10**18)
lock_result = client.staking.lock(int(shares))
print("🔑 Locked:", lock_result["hash"])

# 6. Check prediction market
outcomes = client.market_reader.get_all_outcomes(
    "0x396216fc9d2c220afD227B59097cf97B7dEaCb57",
    "0xYourMarketTokenAddress"
)
print("📊 Market outcomes:", outcomes)

# 7. Check your profile
profile = client.api.get_my_profile()
print("Tier:", profile["tier"], "Rank:", profile["rank"])

print("\n🎉 Bootstrap complete! Claim faucet daily to keep building capital.")
```

---

## Example 7: Resolver Workflow — Propose, Dispute, Vote, Finalize

Complete end-to-end resolution flow: discover markets → propose outcome → handle disputes → claim bounty.

**JS:**
```js
import { BasisClient } from 'basis-sdk';
import { parseUnits } from 'viem';

async function resolverWorkflow() {
  const client = await BasisClient.create({
    privateKey: process.env.BASIS_PRIVATE_KEY,
  });
  const wallet = client.walletClient.account.address;

  // 1. Discover markets needing resolution
  const markets = await client.api.getTokens({ isPrediction: true, limit: 100 });
  const needsProposal = markets.data.filter(m => m.predictionStatus === "awaiting_proposal");
  console.log(`Found ${needsProposal.length} markets needing proposals`);

  if (needsProposal.length === 0) return;

  const market = needsProposal[0];
  const marketToken = market.address;

  // 2. Check the market's outcomes to decide which won
  const outcomes = await client.marketReader.getAllOutcomes(
    "0x396216fc9d2c220afD227B59097cf97B7dEaCb57", // MarketTrading contract
    marketToken
  );
  for (const o of outcomes) {
    const prob = Number(o.probability) / 1e18 * 100;
    console.log(`  Outcome ${o.outcomeId}: "${o.name}" — ${prob.toFixed(1)}%`);
  }

  // 3. Propose the winning outcome (costs 5 USDB bond, auto-approved)
  const winningOutcomeId = 0; // ← Your determination of which outcome won
  const proposeResult = await client.resolver.proposeOutcome(marketToken, winningOutcomeId);
  console.log("✅ Proposed outcome:", winningOutcomeId, "tx:", proposeResult.hash);

  // 4. Wait for the challenge period (PROPOSAL_PERIOD — currently 30 min)
  //    During this time, anyone can dispute with a different outcome
  const disputeData = await client.resolver.getDisputeData(marketToken);
  console.log("Challenge period ends:", new Date(Number(disputeData.proposalEndTime) * 1000));

  // 5a. If NO dispute — finalize after challenge period expires
  //     (In production, poll or wait for the period to elapse)
  console.log("Waiting for challenge period...");
  // await sleep(30 * 60 * 1000); // 30 minutes in production

  try {
    const finalizeResult = await client.resolver.finalizeUncontested(marketToken);
    console.log("✅ Finalized uncontested! Bond returned + 100% bounty");
    console.log("Tx:", finalizeResult.hash);
  } catch (e) {
    // If someone disputed, finalizeUncontested will revert
    console.log("Market was disputed — entering voting flow");

    // 5b. If DISPUTED — stake tokens, then vote on the outcome
    //     Need to stake first (min 5 tokens of any ecosystem token)
    //     stake() takes one param: the ecosystem token address
    //     It auto-reads MIN_STAKE_AMOUNT from the contract and approves it
    const ECOSYSTEM_TOKEN = "0xAnyActiveEcosystemToken...";
    await client.resolver.stake(ECOSYSTEM_TOKEN);
    console.log("✅ Staked tokens for voting");

    // Now cast your vote
    await client.resolver.vote(marketToken, winningOutcomeId);
    console.log("✅ Voted for outcome:", winningOutcomeId);
    // — ️ Your stake is now locked for 24 hours (VOTE_LOCK_DURATION)
    // — ️ Check loan expiry dates before voting — you cannot unstake to repay during the lock

    // 5c. After voting period (DISPUTE_PERIOD — currently 30 min),
    //     finalize if quorum met and 70% supermajority reached
    // await sleep(30 * 60 * 1000); // Wait for voting period

    const voteResult = await client.resolver.finalizeMarket(marketToken);
    console.log("✅ Market finalized after vote:", voteResult.hash);
  }

  // 6. Claim bounty (if you proposed or voted on the winning side)
  const bountyResult = await client.resolver.claimBounty(marketToken);
  console.log("💰 Bounty claimed:", bountyResult.hash);
}

resolverWorkflow().catch(console.error);
```

**Key timing notes:**
- Challenge period (PROPOSAL_PERIOD): 30 min (target: 2h) — window to dispute
- Voting period (DISPUTE_PERIOD): 30 min (target: 24h) — window to vote after dispute
- Vote lock: 24 hours — staked tokens locked after voting
- — ️ These are testing values. Read them from the contract at runtime, don't hardcode.
- Self-dispute is allowed — useful for correcting your own proposal mistakes

---
