# Code Examples

**What this covers:** Five complete, working code examples covering the most common operations — token creation, trading, prediction markets, leverage, and DeFi operations (loans + staking).

**Related sections:** → See: [03-atomic-skills.md](03-atomic-skills.md) for all available methods · → See: [08-getting-started.md](08-getting-started.md) for client initialization · → See: [15-contract-addresses.md](15-contract-addresses.md) for contract addresses and decimals

---

## Example 1: Create a Token with Metadata

Full flow: initialize client, create a token, upload an image, and register metadata.

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

  // Buy with 5 USDB
  const buyResult = await client.trading.buy(TOKEN, fiveUsdb);
  console.log("Bought tokens:", buyResult.hash);

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

    buy_result = client.trading.buy(TOKEN, FIVE_USDB)
    print("Bought tokens:", buy_result["hash"])

    # Sell 50% of holdings (no amount needed — reads balance automatically)
    sell_result = client.trading.sell_percentage(TOKEN, 50)
    print("Sold 50%:", sell_result["hash"])
```

---

## Example 3: Prediction Market

Create a market, buy shares, and list a sell order.

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

  // 2. Buy "Yes" shares (outcomeId 0) with 5 USDB
  const buyResult = await client.predictionMarkets.buy(
    marketToken, 0, USDB, parseUnits("5", 18), 0n, 0n
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

    buy_result = client.prediction_markets.buy(market_token, 0, USDB, 5_000_000_000_000_000_000, 0, 0)  # 5 USDB
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
  const sim = await client.leverageSimulator.simulateLeverage(parseUnits("10", 18), path, 7n);
  console.log("Simulation:", sim);

  // 2. Open the leverage position (10 USDB, 7 days)
  const openResult = await client.trading.leverageBuy(parseUnits("10", 18), 0n, path, 7n);
  console.log("Position opened:", openResult.hash);

  // 3. Wait for the next block (required to avoid same-block revert)
  await new Promise(resolve => setTimeout(resolve, 5000));

  // 4. Get the position details
  // Note: leverage positions are 0-indexed (unlike loans which are 1-indexed via hubId)
  const walletAddress = client.walletClient.account.address;
  const positionCount = await client.trading.getLeverageCount(walletAddress);
  const positionId = positionCount - 1; // 0-indexed: first position = 0
  const position = await client.trading.getLeveragePosition(walletAddress, positionId);
  console.log("Position:", position);

  // 5. Partially close (sell 50%)
  // partialLoanSell uses the same 0-indexed positionId from getLeverageCount
  const closeResult = await client.trading.partialLoanSell(positionId, 50, true, 0);
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

    sim = client.leverage_simulator.simulate_leverage(10_000_000_000_000_000_000, path, 7)
    print("Simulation:", sim)

    open_result = client.trading.leverage_buy(10_000_000_000_000_000_000, 0, path, 7)  # 10 USDB
    print("Position opened:", open_result["hash"])

    time.sleep(5)

    # Leverage positions are 0-indexed (unlike loans which are 1-indexed via hubId)
    position_count = client.trading.get_leverage_count(client.wallet_address)
    position_id = position_count - 1  # 0-indexed: first position = 0
    position = client.trading.get_leverage_position(client.wallet_address, position_id)
    print("Position:", position)

    # partialLoanSell uses the same 0-indexed positionId
    close_result = client.trading.partial_loan_sell(position_id, 50, True, 0)
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
  const unlockResult = await client.staking.unlock(Number(shares));
  console.log("Unlocked:", unlockResult.hash);

  const sellResult = await client.staking.sell(Number(shares));
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
