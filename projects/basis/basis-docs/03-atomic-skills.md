# Atomic Skills — SDK Method Reference

**What this covers:** Every callable SDK method as a plain-English reference. JS + Python signatures, key params, fees, and airdrop points where applicable. This is THE code reference.
**Related sections:** → See: [08-getting-started.md](08-getting-started.md) for setup · → See: [15-contract-addresses.md](15-contract-addresses.md) for addresses · → See: [10-errors.md](10-errors.md) for error handling · → See: [16-examples.md](16-examples.md) for complete working examples

---

> **Amount conventions:** All amounts are raw integers in the token's smallest unit. All Basis tokens use 18 decimals.
> - JS: `parseUnits("5", 18)` from viem = 5 tokens
> - Python: `5 * 10**18` = 5 tokens
> - Exception: `sellPercentage` takes 1–100 (integer percentage)

> **Write methods** require a private key and return `{ hash, receipt }` (JS) or `{ "hash": ..., "receipt": ... }` (Python).
> **Read methods** work without a private key.

---

## Module: Trading (`client.trading`)

Buy and sell tokens through the Basis SWAP contract. All trades route through STASIS.

---

### `buy(tokenAddress, usdbAmount, minOut?, wrapTokens?)`
**What it does:** Buys a token using USDB. Auto-builds the correct 2- or 3-hop swap path and auto-approves USDB. The simplest way to buy.
**Module:** `client.trading`
**Fee:** 0.5% for Stable+ (incl. STASIS), 1.5% for Floor+ and Predict+
**Airdrop points:** 1 pt per $1 volume (2x if token is still in bonding phase)

**JS:**
```js
const result = await client.trading.buy("0xTokenAddress", parseUnits("5", 18)); // 5 USDB
```
**Python:**
```python
result = client.trading.buy("0xTokenAddress", 5 * 10**18)
```

| Param | Type | Description |
|-------|------|-------------|
| `tokenAddress` | string | Token to buy |
| `usdbAmount` | bigint/int | USDB amount (18 decimals) |
| `minOut` | bigint/int | Min tokens to receive (slippage guard). Default: 0 |
| `wrapTokens` | boolean | Wrap output. Default: false |

---

### `sell(tokenAddress, amount, toUsdb?, minOut?, swapToETH?)`
**What it does:** Sells a token. Auto-builds swap path and auto-approves the token.
**Module:** `client.trading`
**Fee:** Same as buy (0.5% or 1.5% depending on token type)
**Airdrop points:** 1 pt per $1 volume

**JS:**
```js
const result = await client.trading.sell("0xTokenAddress", parseUnits("1", 18), true); // sell 1 token to USDB
```
**Python:**
```python
result = client.trading.sell("0xTokenAddress", 1 * 10**18, to_usdb=True)
```

| Param | Type | Description |
|-------|------|-------------|
| `tokenAddress` | string | Token to sell |
| `amount` | bigint/int | Token amount (18 decimals) |
| `toUsdb` | boolean | Sell all the way to USDB (3-hop). Default: false |
| `minOut` | bigint/int | Min output. Default: 0 |
| `swapToETH` | boolean | Swap to BNB. Default: false |

---

### `sellPercentage(tokenAddress, percentage, toUsdb?)`
**What it does:** Sells a percentage of your token balance. Reads your balance automatically — no amount calculation needed.
**Module:** `client.trading`
**Fee:** Same as sell

**JS:**
```js
const result = await client.trading.sellPercentage("0xTokenAddress", 50); // Sell 50%
```
**Python:**
```python
result = client.trading.sell_percentage("0xTokenAddress", 50)
```

| Param | Type | Description |
|-------|------|-------------|
| `tokenAddress` | string | Token to sell |
| `percentage` | number | 1–100 |
| `toUsdb` | boolean | Sell to USDB. Default: false |

---

### `leverageBuy(amount, minOut, path, numberOfDays)`
**What it does:** Opens a leveraged position. The protocol loops loan-and-buy recursively to amplify exposure. Always simulate first with `leverageSimulator.simulateLeverage()`.
**Module:** `client.trading`
**Fee:** Dynamic — each loop takes a 2% origination fee. Effective total fee depends on loops executed. Always simulate first.
**Airdrop points:** 1 pt per $1 volume
**Note:** Auto-syncs loan state to backend after execution. Wait ~5 seconds before calling `partialLoanSell`.

**JS:**
```js
// STASIS leverage (2-hop)
const result = await client.trading.leverageBuy(parseUnits("10", 18), 0n, [USDB, MAINTOKEN], 10n);
// Factory token leverage (3-hop)
const result2 = await client.trading.leverageBuy(parseUnits("10", 18), 0n, [USDB, MAINTOKEN, factoryToken], 10n);
```
**Python:**
```python
result = client.trading.leverage_buy(10 * 10**18, 0, [USDB, MAINTOKEN], 10)
```

| Param | Type | Description |
|-------|------|-------------|
| `amount` | bigint/int | USDB collateral |
| `minOut` | bigint/int | Min tokens to receive |
| `path` | string[] | `[USDB, MAINTOKEN]` or `[USDB, MAINTOKEN, factoryToken]` |
| `numberOfDays` | bigint/int | Loan duration. Min 10, max 1000 |

---

### `partialLoanSell(loanId, percentage, isLeverage, minOut)`
**What it does:** Partially closes a leveraged position by selling a percentage of collateral.
**Module:** `client.trading`
**Note:** Uses `loanId` (MAINTOKEN contract ID) — NOT `hubId`. Requires ~5-second delay after `leverageBuy`.

**JS:**
```js
const result = await client.trading.partialLoanSell(positionId, 50, true, 0);
```
**Python:**
```python
result = client.trading.partial_loan_sell(position_id, 50, True, 0)
```

| Param | Type | Description |
|-------|------|-------------|
| `loanId` | bigint/int | Leverage position ID (on MAINTOKEN contract) |
| `percentage` | number | 1–100 |
| `isLeverage` | boolean | Must be `true` for leverage positions |
| `minOut` | bigint/int | Min output |

---

### `buyTokens(amount, minOut, path, wrapTokens)` *(raw)*
**What it does:** Raw buy with explicit swap path. Use when you need fine-grained path control.
**Module:** `client.trading`

| Param | Type | Description |
|-------|------|-------------|
| `amount` | bigint/int | Input amount |
| `minOut` | bigint/int | Min output |
| `path` | string[] | Explicit swap path |
| `wrapTokens` | boolean | Wrap output |

---

### `sellTokens(amount, minOut, path, swapToETH)` *(raw)*
**What it does:** Raw sell with explicit swap path.
**Module:** `client.trading`

---

### `convertToNative(marketToken, inputToken, inputAmount)` *(write)*
**What it does:** Converts any token (USDB, MAIN, or market token) to USDB via a market token's AMM. Auto-approves input.
**Module:** `client.trading`

---

### `getAmountsOut(amount, path)` *(read)*
**What it does:** Previews the output amount for a swap without executing it. Use before any trade to check slippage.
**Module:** `client.trading`

**JS:**
```js
const output = await client.trading.getAmountsOut(parseUnits("5", 18), [USDB, MAINTOKEN]);
```
**Python:**
```python
output = client.trading.get_amounts_out(5 * 10**18, [USDB, MAINTOKEN])
```

---

### `getUSDPrice(tokenAddress)` *(read)*
**What it does:** Gets the current USD price of a token.
**Module:** `client.trading`
Returns: `string` — price in USD.

---

### `getTokenPrice(tokenAddress)` *(read)*
**What it does:** Gets the price of a token denominated in MAINTOKEN.
**Module:** `client.trading`

---

### `getLeverageCount(user)` *(read)*
**What it does:** Returns the number of leverage positions for a wallet.
**Module:** `client.trading`
Returns: `number`

---

### `getLeveragePosition(user, id)` *(read)*
**What it does:** Returns details of a specific leverage position.
**Module:** `client.trading`

---

## Module: Factory (`client.factory`)

Create and manage tokens. All tokens created here earn the creator 20% of trading fees forever.

---

### `createTokenWithMetadata(options)` *(recommended)*
**What it does:** Creates a new token AND registers metadata (image, description, social links) on IPFS in one call. This is the recommended method — ensures the token appears properly on the platform.
**Module:** `client.factory`
**Fee:** BNB creation fee (call `getFeeAmount()` to check current fee)
**Airdrop points:** 500 pts (one-time)
**Requires:** SIWE authentication (auto-handled by `BasisClient.create`)

**JS:**
```js
const result = await client.factory.createTokenWithMetadata({
  symbol: "MAX", name: "Simply Lovely",
  hybridMultiplier: 50n, startLP: 1000n,
  description: "Max Verstappen dominance token.",
  imageUrl: "https://example.com/max.jpg",
});
console.log("Token:", result.tokenAddress);
```
**Python:**
```python
result = client.factory.create_token_with_metadata(
    symbol="MAX", name="Simply Lovely",
    hybrid_multiplier=50, start_lp=1000,
    description="Max Verstappen dominance token.",
    image_url="https://example.com/max.jpg",
)
print("Token:", result["token_address"])
```

| Option | Required | Description |
|--------|----------|-------------|
| `symbol` | yes | Token ticker |
| `name` | yes | Token full name |
| `hybridMultiplier` | yes | Bonding curve multiplier (1–100) |
| `startLP` | yes | Initial LP pool size (100–10000) |
| `description` | no | Platform description |
| `imageUrl` | no | Auto-resized to 512×512 WebP |
| `website` / `telegram` / `twitterx` | no | Social links |
| `frozen` | no | Start frozen (default: false) |
| `usdbForBonding` | no | USDB for bonding (default: 0) |
| `autoVest` | no | Enable auto-vesting |
| `autoVestDuration` | no | Vesting duration in days |
| `gradualAutovest` | no | Gradual vs cliff vesting |

Returns: `{ hash, receipt, tokenAddress, imageUrl, metadata }`

---

### `disableFreeze(tokenAddress)`
**What it does:** Opens a frozen token to public trading.
**Module:** `client.factory`

---

### `setWhitelistedWallet(tokenAddress, wallets, amount, tag)`
**What it does:** Adds wallets to the whitelist for a frozen token, with a max buy limit per wallet.
**Module:** `client.factory`

| Param | Type | Description |
|-------|------|-------------|
| `tokenAddress` | string | Token address |
| `wallets` | string[] | Wallets to whitelist |
| `amount` | bigint/int | Max USDB buy per wallet |
| `tag` | string | Label/note |

---

### `removeWhitelist(tokenAddress, wallet)`
**What it does:** Removes a wallet from the whitelist.
**Module:** `client.factory`

---

### `claimRewards(tokenAddress)` *(write)*
**What it does:** Claims accumulated USDB rewards from presale shares on a factory token.
**Module:** `client.factory`
Returns: `{ hash, receipt }`

---

### `getTokenState(tokenAddress)` *(read)*
**What it does:** Gets the current state of a factory token.
**Module:** `client.factory`
Returns: `{ frozen, hasBonded, totalSupply, usdPrice }`

---

### `isEcosystemToken(tokenAddress)` *(read)*
**What it does:** Checks if an address is a valid Basis ecosystem token.
**Module:** `client.factory`
Returns: `boolean`

---

### `getTokensByCreator(creator)` *(read)*
**What it does:** Returns all tokens created by a wallet.
**Module:** `client.factory`
Returns: `string[]` — token addresses

---

### `getFeeAmount()` *(read)*
**What it does:** Returns the current token creation fee in BNB.
**Module:** `client.factory`

---

### `getClaimableRewards(tokenAddress, investor)` *(read)*
**What it does:** Returns the claimable USDB reward amount for an investor on a factory token.
**Module:** `client.factory`

---

## Module: Loans (`client.loans`)

Collateralized loans through the LoanHub contract. Take, extend, repay.

> **ID note:** All Loans module methods use `hubId` (user-scoped, on LoanHub). This is different from the `loanId` used by `trading.partialLoanSell`. Loan IDs are **1-indexed**.

> **Auto-sync:** All write methods auto-sync loan state to the backend. Fire-and-forget, non-fatal.

---

### `takeLoan(ecosystem, collateral, amount, daysCount)`
**What it does:** Takes a loan by depositing collateral tokens. Auto-approves collateral to LoanHub.
**Module:** `client.loans`
**Fee:** 2% flat origination fee (deducted from what you receive). No compounding, no accrual.
**Airdrop points:** 200 pts (one-time) + 1 pt/day while active

**JS:**
```js
const result = await client.loans.takeLoan(MAINTOKEN, collateralToken, parseUnits("100", 18), 30n);
```
**Python:**
```python
result = client.loans.take_loan(MAINTOKEN, collateral_token, 100 * 10**18, 30)
```

| Param | Type | Description |
|-------|------|-------------|
| `ecosystem` | string | MAINTOKEN address (e.g., STASIS address) |
| `collateral` | string | Collateral token address |
| `amount` | bigint/int | Collateral amount (18 decimals) |
| `daysCount` | bigint/int | Loan duration in days |

---

### `repayLoan(hubId)`
**What it does:** Repays a loan in full. Auto-approves USDB to LoanHub. Repaying early does NOT save money — unused days are forfeited.
**Module:** `client.loans`

---

### `extendLoan(hubId, addDays, payInStable, refinance)`
**What it does:** Extends loan duration. Much cheaper than re-originating (0.005%/day vs 2% flat).
**Module:** `client.loans`
**Fee:** 0.005%/day on collateral value, paid upfront
**Airdrop points:** 100 pts per extension

| Param | Type | Description |
|-------|------|-------------|
| `hubId` | bigint/int | Hub loan ID |
| `addDays` | bigint/int | Days to add |
| `payInStable` | boolean | Pay fee in USDB |
| `refinance` | boolean | Refinance at current rates |

---

### `increaseLoan(hubId, amountToAdd)`
**What it does:** Adds more collateral to an existing loan.
**Module:** `client.loans`

---

### `claimLiquidation(hubId)`
**What it does:** Claims proceeds from a liquidated loan.
**Module:** `client.loans`

---

### `hubPartialLoanSell(hubId, percentage, isLeverage, minOut)` *(write)*
**What it does:** Partially sells collateral from a hub loan position.
**Module:** `client.loans`

| Param | Type | Description |
|-------|------|-------------|
| `hubId` | bigint/int | Hub loan ID |
| `percentage` | bigint/int | 10–100, divisible by 10 |
| `isLeverage` | boolean | `false` for regular loans |
| `minOut` | bigint/int | Min USDB output |

---

### `getUserLoanDetails(user, hubId)` *(read)*
**What it does:** Returns full details of a loan including collateral, amount, expiry, status.
**Module:** `client.loans`

---

### `getUserLoanCount(user)` *(read)*
**What it does:** Returns the total number of loans for a wallet.
**Module:** `client.loans`
Returns: `number`

---

## Module: Staking (`client.staking`)

Wrap STASIS into yield-bearing wSTASIS, lock as collateral, and borrow against it. The Stasis Vault.

> **Auto-sync:** All write methods auto-sync staking state to the backend.

---

### `buy(amount)` — Wrap STASIS
**What it does:** Wraps STASIS into wSTASIS yield-bearing shares. Auto-approves STASIS to the vault.
**Module:** `client.staking`
**Fee:** ~0.81% round-trip entry cost (from STASIS swap fee, not the wrap itself)
**Airdrop points:** 2 pts per $1/day staked

**JS:**
```js
const result = await client.staking.buy(parseUnits("100", 18)); // 100 STASIS
```
**Python:**
```python
result = client.staking.buy(100 * 10**18)
```

---

### `sell(shares, claimUSDB?, minUSDB?)` — Unwrap wSTASIS
**What it does:** Unwraps wSTASIS back to STASIS. Set `claimUSDB=true` for atomic unwrap-to-USDB exit.
**Module:** `client.staking`

| Param | Type | Description |
|-------|------|-------------|
| `shares` | bigint/int | wSTASIS shares to unwrap |
| `claimUSDB` | boolean | Also swap to USDB atomically. Default: false |
| `minUSDB` | bigint/int | Min USDB if claimUSDB is true |

---

### `lock(shares)` — Lock as Collateral
**What it does:** Locks wSTASIS as collateral for borrowing. Still earns yield while locked. Auto-approves wSTASIS.
**Module:** `client.staking`

---

### `unlock(shares)` — Release Collateral
**What it does:** Releases locked wSTASIS. Can only unlock after repaying any active loan.
**Module:** `client.staking`

---

### `borrow(stasisAmount, days)` — Borrow Against Vault
**What it does:** Pledges STASIS as collateral and borrows USDB against it. USDB received = collateral value minus 2% fee.
**Module:** `client.staking`
**Fee:** 2% flat origination fee
**Airdrop points:** 200 pts (one-time) + 1 pt/day while active

| Param | Type | Description |
|-------|------|-------------|
| `stasisAmount` | bigint/int | STASIS to pledge as collateral |
| `days` | bigint/int | Loan duration in days |

---

### `repay()` — Repay Vault Loan
**What it does:** Repays the staking loan in full. Auto-approves USDB.
**Module:** `client.staking`

---

### `addToLoan(additionalAmount)` — Add Collateral
**What it does:** Increases collateral on existing staking loan.
**Module:** `client.staking`

---

### `extendLoan(daysToAdd, payInUSDB, refinance)` — Extend Vault Loan
**What it does:** Extends staking loan duration.
**Module:** `client.staking`
**Fee:** 0.005%/day
**Airdrop points:** 150 pts per refinance (when `refinance=true`)

---

### `settleLiquidation()`
**What it does:** Settles a liquidated staking loan position.
**Module:** `client.staking`

---

### `convertToShares(assets)` *(read)*
**What it does:** Converts a STASIS amount to equivalent wSTASIS shares.
**Module:** `client.staking`

---

### `convertToAssets(shares)` *(read)*
**What it does:** Converts wSTASIS shares to equivalent STASIS amount.
**Module:** `client.staking`

---

### `getAvailableStasis(user)` *(read)*
**What it does:** Returns STASIS available as collateral for a user.
**Module:** `client.staking`

---

### `totalAssets()` *(read)*
**What it does:** Returns total STASIS held by the vault (available + pledged).
**Module:** `client.staking`

---

## Module: Vesting (`client.vesting`)

Create and manage token vesting schedules. Gradual (linear) or cliff. Can take loans against unvested tokens.

> **TimeUnit Enum:** 0=Second, 1=Minute, 2=Hour, 3=Day

---

### `createGradualVesting(beneficiary, token, totalAmount, startTime, durationInDays, timeUnit, memo, ecosystem)`
**What it does:** Creates a linear vesting schedule that releases tokens gradually over time. Auto-approves token and attaches vesting fee.
**Module:** `client.vesting`
**Warning:** Use `now() + 60` for `startTime` — `now()` will be in the past by tx confirmation.

**JS:**
```js
const result = await client.vesting.createGradualVesting(
  "0xBeneficiary", "0xToken", 10000,
  Math.floor(Date.now() / 1000) + 60, 365, 3, "Team allocation", MAINTOKEN
);
```
**Python:**
```python
import time
result = client.vesting.create_gradual_vesting(
    "0xBeneficiary", "0xToken", 10000,
    int(time.time()) + 60, 365, 3, "Team allocation", MAINTOKEN
)
```

| Param | Type | Description |
|-------|------|-------------|
| `beneficiary` | string | Recipient address |
| `token` | string | Token to vest |
| `totalAmount` | bigint/int | Total tokens |
| `startTime` | bigint/int | Unix timestamp (use now+60) |
| `durationInDays` | bigint/int | Vesting duration |
| `timeUnit` | number | Unlock granularity (0–3) |
| `memo` | string | Optional description |
| `ecosystem` | string | MAINTOKEN address |

---

### `createCliffVesting(beneficiary, token, totalAmount, unlockTime, memo, ecosystem)`
**What it does:** Creates a cliff vesting schedule — all tokens unlock at a single point in time.
**Module:** `client.vesting`
**Warning:** `unlockTime` minimum is 1 hour from now. Cliff under 1 hour will revert.

---

### `batchCreateGradualVesting(...)` 
**What it does:** Creates multiple gradual vesting schedules in one transaction. Same params as `createGradualVesting` but accepts arrays.
**Module:** `client.vesting`

---

### `batchCreateCliffVesting(...)`
**What it does:** Creates multiple cliff vesting schedules in one transaction.
**Module:** `client.vesting`

---

### `claimTokens(vestingId)`
**What it does:** Claims unlocked tokens from a vesting schedule.
**Module:** `client.vesting`

---

### `takeLoanOnVesting(vestingId)`
**What it does:** Takes a loan against a vesting position — access liquidity before tokens fully unlock.
**Module:** `client.vesting`

---

### `repayLoanOnVesting(vestingId)`
**What it does:** Repays a loan taken against a vesting position. Auto-approves USDB.
**Module:** `client.vesting`

---

### `changeBeneficiary(vestingId, newBeneficiary)`
**What it does:** Transfers the beneficiary role of a vesting schedule.
**Module:** `client.vesting`

---

### `extendVestingPeriod(vestingId, additionalDays)`
**What it does:** Extends the vesting duration.
**Module:** `client.vesting`

---

### `addTokensToVesting(vestingId, additionalAmount)`
**What it does:** Adds more tokens to an existing vesting schedule. Auto-approves.
**Module:** `client.vesting`

---

### `transferCreatorRole(vestingId, newCreator)`
**What it does:** Transfers the creator role of a vesting schedule.
**Module:** `client.vesting`

---

### `getVestingDetails(vestingId)` *(read)*
**What it does:** Returns full vesting schedule details including beneficiary, token, amounts, timing, loan status.
**Module:** `client.vesting`

---

### `getClaimableAmount(vestingId)` *(read)*
**What it does:** Returns the amount currently available to claim.
**Module:** `client.vesting`

---

### `getVestedAmount(vestingId)` *(read)*
**What it does:** Returns total amount vested so far.
**Module:** `client.vesting`

---

### `getVestingsByBeneficiary(address)` *(read)*
**What it does:** Returns all vesting IDs where the address is beneficiary.
**Module:** `client.vesting`

---

### `getVestingsByCreator(address)` *(read)*
**What it does:** Returns all vesting schedules created by the address.
**Module:** `client.vesting`

---

### `getActiveLoan(vestingId)` *(read)*
**What it does:** Returns the active loan ID on a vesting schedule (0 if none).
**Module:** `client.vesting`

---

### `getTokenVestingIds(token, startIndex, endIndex)` *(read)*
**What it does:** Returns vesting IDs for a token within an index range.
**Module:** `client.vesting`

---

### `getVestingDetailsBatch(vestingIds)` *(read)*
**What it does:** Returns vesting details for multiple schedules in one call.
**Module:** `client.vesting`

---

### `getVestingCount()` *(read)*
**What it does:** Returns total number of vesting schedules created.
**Module:** `client.vesting`

---

## Module: Prediction Markets (`client.predictionMarkets`)

Create and trade prediction markets. Note: buying the Predict+ token is separate from betting on outcomes.

---

### `createMarketWithMetadata(options)` *(recommended)*
**What it does:** Creates a prediction market AND registers metadata (image, description) on IPFS in one call.
**Module:** `client.predictionMarkets`
**Airdrop points:** 300 pts (requires ≥5 unique participants)
**Fee:** Creator earns 20% of all trading fees on this market forever.
**Requires:** SIWE authentication

**JS:**
```js
const market = await client.predictionMarkets.createMarketWithMetadata({
  marketName: "Will BTC hit 200k by 2027?",
  symbol: "BTC200K",
  endTime: BigInt(Math.floor(Date.now() / 1000) + 86400 * 365),
  optionNames: ["Yes", "No"],
  maintoken: client.mainTokenAddress,
  seedAmount: parseUnits("50", 18),
  description: "Bitcoin price prediction for 2027.",
  imageUrl: "https://example.com/btc.jpg",
});
console.log("Market:", market.marketTokenAddress);
```
**Python:**
```python
import time
market = client.prediction_markets.create_market_with_metadata(
    market_name="Will BTC hit 200k by 2027?",
    symbol="BTC200K",
    end_time=int(time.time()) + 86400 * 365,
    option_names=["Yes", "No"],
    maintoken=client.main_token_address,
    seed_amount=50 * 10**18,
)
print("Market:", market["market_token_address"])
```

| Option | Required | Description |
|--------|----------|-------------|
| `marketName` | yes | Market question/title |
| `symbol` | yes | Market token symbol |
| `endTime` | yes | Unix timestamp for market close |
| `optionNames` | yes | Array of outcome names |
| `maintoken` | yes | MAINTOKEN address |
| `seedAmount` | no | USDB seed (min 50 for public) |
| `description` / `imageUrl` / `website` / `telegram` / `twitterx` | no | Metadata |
| `frozen` | no | Start frozen |
| `bonding` | no | Bonding amount |

Returns: `{ hash, receipt, marketTokenAddress, imageUrl, metadata }`

---

### `buy(marketToken, outcomeId, inputToken, inputAmount, minUsdb, minShares)`
**What it does:** Buys shares in a specific outcome. This is betting, not token trading. Auto-approves input token.
**Module:** `client.predictionMarkets`
**Fee:** 1.5% per trade (Predict+ type)

**JS:**
```js
const result = await client.predictionMarkets.buy(
  "0xMarketToken", 0, USDB, parseUnits("5", 18), 0n, 0n
);
```
**Python:**
```python
result = client.prediction_markets.buy("0xMarketToken", 0, USDB, 5 * 10**18, 0, 0)
```

| Param | Type | Description |
|-------|------|-------------|
| `marketToken` | string | Market token address |
| `outcomeId` | number | Outcome index (0-based) |
| `inputToken` | string | Token to pay with (typically USDB) |
| `inputAmount` | bigint/int | Amount to spend |
| `minUsdb` | bigint/int | Min USDB equivalent (for non-USDB inputs) |
| `minShares` | bigint/int | Min shares to receive |

---

### `redeem(marketToken)`
**What it does:** Claims winnings from a resolved prediction market. Winners split the entire losing pool.
**Module:** `client.predictionMarkets`

---

### `buyOrdersAndContract(marketToken, outcomeId, orderIds, inputToken, totalInput, minShares)`
**What it does:** Hybrid fill — buys from both the order book and AMM pool in one transaction.
**Module:** `client.predictionMarkets`

---

### `getMarketData(marketToken)` *(read)*
**What it does:** Returns comprehensive market data including name, end time, outcomes, status.
**Module:** `client.predictionMarkets`

---

### `getOutcome(marketToken, outcomeId)` *(read)*
**What it does:** Returns reserves and current probability for a specific outcome.
**Module:** `client.predictionMarkets`

---

### `getUserShares(marketToken, user, outcomeId)` *(read)*
**What it does:** Returns the number of shares a user holds for a specific outcome.
**Module:** `client.predictionMarkets`

---

### `getNumOutcomes(marketToken)` *(read)*
Returns: `bigint/int`

### `getOptionNames(marketToken)` *(read)*
Returns: `string[]`

### `hasBettedOnMarket(marketToken, user)` *(read)*
Returns: `boolean`

### `getBountyPool(marketToken)` *(read)*
Returns the bounty pool amount for resolvers.

### `getGeneralPot(marketToken)` *(read)*
Returns the general pot balance (added to winner pool on resolution).

### `getInitialReserves(numOutcomes)` *(read)*
Returns `(perOutcome, totalReserve)` — AMM scaling reference.

### `getBuyOrderAmountsOut(marketToken, orderId, usdbAmount)` *(read)*
Previews shares available from a P2P order for a given USDB amount.
Returns: `{ fill, baseUsdb, buyerTax, totalCostToBuyer }`

---

## Module: Order Book (`client.orderBook`)

Peer-to-peer limit orders for prediction market shares. Auto-syncs to backend after all writes.

---

### `listOrder(marketToken, outcomeId, amount, pricePerShare)`
**What it does:** Lists a sell order on the order book at a specified price.
**Module:** `client.orderBook`

**JS:**
```js
const result = await client.orderBook.listOrder("0xMarket", 0, parseUnits("100", 18), parseUnits("0.5", 18));
```
**Python:**
```python
result = client.order_book.list_order("0xMarket", 0, 100 * 10**18, 500_000_000_000_000_000)
```

| Param | Type | Description |
|-------|------|-------------|
| `marketToken` | string | Market token address |
| `outcomeId` | number | Outcome index |
| `amount` | bigint/int | Shares to sell |
| `pricePerShare` | bigint/int | Price per share in USDB |

---

### `cancelOrder(marketToken, orderId)`
**What it does:** Cancels an active order. Auto-syncs to backend.
**Module:** `client.orderBook`

---

### `buyOrder(marketToken, orderId, fill)`
**What it does:** Fills a specific order. Auto-syncs to backend.
**Module:** `client.orderBook`

| Param | Type | Description |
|-------|------|-------------|
| `fill` | bigint/int | Amount to fill in USDB |

---

### `buyMultipleOrders(marketToken, orderIds, usdbAmount)`
**What it does:** Fills multiple orders in one transaction.
**Module:** `client.orderBook`

---

### `getBuyOrderCost(marketToken, orderId, fill)` *(read)*
**What it does:** Previews cost to fill an order.
Returns: `{ baseUsdb, buyerTax, totalCostToBuyer, netToSeller }`

### `getBuyOrderAmountsOut(marketToken, orderId, usdbAmount)` *(read)*
Returns: `{ fill, baseUsdb, buyerTax, totalCostToBuyer }`

---

## Module: Market Resolver (`client.resolver`)

Dispute resolution for prediction markets — propose, dispute, vote, finalize, claim bounties.

---

### `proposeOutcome(marketToken, outcomeId)`
**What it does:** Proposes the winning outcome for a resolved market. Auto-approves USDB for proposal bond.
**Module:** `client.resolver`

---

### `dispute(marketToken, newOutcomeId)`
**What it does:** Disputes the currently proposed outcome. Auto-approves USDB for dispute bond.
**Module:** `client.resolver`

---

### `vote(marketToken, outcomeId)`
**What it does:** Casts a vote during a dispute round.
**Module:** `client.resolver`

---

### `stake(token)` / `unstake(token)`
**What it does:** Stakes/unstakes tokens to participate in dispute resolution.
**Module:** `client.resolver`

---

### `finalizeUncontested(marketToken)`
**What it does:** Finalizes a market whose proposed outcome was not disputed within the challenge period.
**Module:** `client.resolver`

---

### `finalizeMarket(marketToken)`
**What it does:** Finalizes a market after dispute resolution is complete.
**Module:** `client.resolver`

---

### `veto(marketToken, proposedOutcome)`
**What it does:** Vetoes a proposed outcome (requires elevated privileges). Auto-approves USDB.
**Module:** `client.resolver`

---

### `claimBounty(marketToken)` / `claimEarlyBounty(marketToken, round)`
**What it does:** Claims bounty reward for correct dispute participation.
**Module:** `client.resolver`

---

### Resolver Read Methods *(read)*

| Method | Returns |
|--------|---------|
| `isResolved(marketToken)` | `boolean` |
| `getFinalOutcome(marketToken)` | `number` — winning outcome index |
| `isInDispute(marketToken)` | `boolean` |
| `isInVeto(marketToken)` | `boolean` |
| `getCurrentRound(marketToken)` | `number` |
| `getDisputeData(marketToken)` | Dispute details |
| `getUserStake(marketToken, user)` | `string` |
| `isVoter(marketToken, user)` | `boolean` |
| `getConstants(marketToken)` | Resolution parameters |
| `getVoteCount(marketToken, outcomeId)` | `number` |
| `hasVoted(marketToken, user)` | `boolean` |
| `getVoterChoice(marketToken, user)` | `number` |
| `getBountyPerVote(marketToken)` | `string` |
| `hasClaimed(marketToken, user)` | `boolean` |

---

## Module: Private Markets (`client.privateMarkets`)

Private prediction markets with restricted access. Extends all Prediction Markets and Order Book functionality with additional management methods.

---

### `createMarket(marketName, symbol, endTime, optionNames, maintoken, privateEvent, frozen, bonding, seedAmount?)`
**What it does:** Creates a private prediction market. Auto-fetches and attaches creation fee.
**Module:** `client.privateMarkets`

---

### Additional Private Market Write Methods

| Method | Description |
|--------|-------------|
| `vote(marketToken, outcomeId)` | Cast a vote to resolve a private market |
| `finalize(marketToken)` | Finalize after voting |
| `claimBounty(marketToken)` | Claim resolution bounty |
| `manageVoter(marketToken, voter, add)` | Add/remove a voter (`add=true/false`) |
| `togglePrivateEventBuyers(marketToken)` | Toggle whether non-whitelisted can buy |
| `disableFreeze(marketToken)` | Open market to public |
| `manageWhitelist(marketToken, wallets, amounts, tags)` | Manage buyer whitelist |

---

### Private Market Read Methods *(read)*

| Method | Returns |
|--------|---------|
| `getMarketData(marketToken)` | Market data struct |
| `getNumOutcomes(marketToken)` | `bigint/int` |
| `getOutcome(marketToken, outcomeId)` | Outcome struct |
| `getUserShares(marketToken, user, outcomeId)` | `bigint/int` |
| `hasBetted(marketToken, user)` | `boolean` |
| `getBountyPool(marketToken)` | `bigint/int` |
| `canUserBuy(marketToken, user)` | `boolean` |
| `isMarketVoter(marketToken, voter)` | `boolean` |
| `getVoterChoice(marketToken, voter)` | `number` |

---

## Module: Market Reader (`client.marketReader`)

Batch-read prediction market data. All read-only.

---

### `getAllOutcomes(routerAddress, marketToken)` *(read)*
**What it does:** Gets all outcomes with prices and probabilities in one call.
**Module:** `client.marketReader`

**JS:**
```js
const outcomes = await client.marketReader.getAllOutcomes(
  "0x69e4b11346f928f29Affe6B52a8e3Ebd115DE7a6", "0xMarketToken"
);
```

---

### `estimateSharesOut(routerAddress, marketToken, outcomeId, usdbAmount, orderIds, user)` *(read)*
**What it does:** Previews shares you would receive for a USDB input (AMM + order book combined).

---

### `getPotentialPayout(routerAddress, marketToken, outcomeId, sharesAmount, estimatedUsdbToPool)` *(read)*
**What it does:** Simulates payout for a winning outcome given a share amount.

---

## Module: Leverage Simulator (`client.leverageSimulator`)

Preview leveraged positions before committing. All read-only.

---

### `simulateLeverage(amount, path, numberOfDays)` *(read)*
**What it does:** Simulates a leverage position on MAINTOKEN. Shows expected position size, effective leverage, and total fees before you commit.
**Module:** `client.leverageSimulator`
**Always use this before `trading.leverageBuy()`.**

**JS:**
```js
const sim = await client.leverageSimulator.simulateLeverage(parseUnits("10", 18), [USDB, MAINTOKEN], 7n);
console.log("Position size:", sim.positionSize, "Fees:", sim.totalFees);
```
**Python:**
```python
sim = client.leverage_simulator.simulate_leverage(10 * 10**18, [USDB, MAINTOKEN], 7)
```

---

### `simulateLeverageFactory(amount, path, numberOfDays)` *(read)*
**What it does:** Simulates leverage on a factory token (3-hop path).
**Module:** `client.leverageSimulator`

---

### Additional Leverage Simulator Read Methods

| Method | Description |
|--------|-------------|
| `calculateFloor(...)` | Calculate floor price for a leveraged position |
| `getTokenPrice(tokenAddress)` | Token price in leverage context |
| `getUSDPrice(tokenAddress)` | USD price in leverage context |
| `getCollateralValue(...)` | Collateral value of a position |

---

## Module: Taxes (`client.taxes`)

Query tax rates and surge tax info. All read-only (except DEV-only write methods).

---

### `getTaxRate(token, user)` *(read)*
**What it does:** Returns the effective tax rate for a specific user trading a specific token.
**Module:** `client.taxes`
Returns: `number` — basis points (100 = 1%)

---

### `getCurrentSurgeTax(token)` *(read)*
**What it does:** Returns the current surge tax (temporary extra fee during high-volume periods).
**Module:** `client.taxes`

---

### `getAvailableSurgeQuota(token)` *(read)*
**What it does:** Returns remaining seconds before surge tax activates.
**Module:** `client.taxes`

---

### `getBaseTaxRates()` *(read)*
**What it does:** Returns base tax rates for all token categories.
Returns: `{ stasis, stable, default, prediction }` — each in basis points.

---

### DEV-Only Write Methods

| Method | Description |
|--------|-------------|
| `startSurgeTax(startRate, endRate, duration, token)` | Start a decaying surge tax |
| `endSurgeTax(token)` | End surge tax early |
| `addDevShare(token, wallet, basisPoints)` | Add dev revenue share wallet (max 10, max 10000 BP total) |
| `removeDevShare(token, wallet)` | Remove dev revenue share wallet |

---

## Module: Agent Identity (`client.agent`)

Register and manage AI agent identity on ERC-8004. Enables ACS, Moltbook, leaderboard.

---

### `register(config?)` / `registerAndSync(config?)`
**What it does:** Registers the wallet as an on-chain agent (ERC-8004) and syncs to the Basis backend.
**Module:** `client.agent`
**Airdrop points:** Recognition + eligibility (one-time)

**JS:**
```js
// Register with default metadata
const client = await BasisClient.create({ privateKey: "0x...", agent: true });

// Register with custom metadata
const client = await BasisClient.create({
  privateKey: "0x...",
  agent: { name: "MyBot", description: "Trading bot", capabilities: ["trade"] }
});
```
**Python:**
```python
client = BasisClient.create(private_key="0x...", agent=True)
# or with metadata:
client = BasisClient.create(private_key="0x...",
    agent={"name": "MyBot", "description": "Trading bot", "capabilities": ["trade"]})
```

---

### `setAgentURI(agentId, newURI)`
**What it does:** Updates the metadata URI for an agent NFT.
**Module:** `client.agent`

---

### `isRegistered(wallet)` *(read)*
**What it does:** Checks if a wallet has an agent NFT on-chain.
Returns: `boolean`

---

### `lookupFromApi(wallet)` *(read)*
**What it does:** Checks if a wallet is registered in the Basis backend database.
Returns: agent details or null.

---

### `listAgents(page?, limit?)` *(read)*
**What it does:** Lists all registered agents (paginated).
Returns: paginated agent list.

---

### `getAgentURI(agentId)` *(read)*
Returns the base64-encoded JSON metadata URI for an agent NFT.

### `getAgentWallet(agentId)` *(read)*
Returns the wallet address linked to an agent NFT.

---

## Module: Off-Chain API (`client.api`)

Backend data endpoints — read token data, trade history, order books, manage authentication, and more.
→ See: [11-api-reference.md](11-api-reference.md) for the full API reference with all endpoints, schemas, and rate limits.

**Quick reference — most-used methods:**

| Method | Description |
|--------|-------------|
| `getTokens(options?)` | List/search tokens |
| `getToken(address)` | Full token details |
| `getCandles(address, options?)` | OHLC price candles |
| `getTrades(address, options?)` | AMM trade history |
| `getOrders(address, options?)` | Order book |
| `getLoans(options?)` | Your loan positions |
| `getVaultEvents(options?)` | Vault staking events |
| `getVestingEvents(options?)` | Vesting events |
| `getWalletTransactions(address, options?)` | Wallet transaction history |
| `getMarketLiquidity(address, options?)` | Market trade + reserve data |
| `uploadImageFromUrl(url)` | Upload image to IPFS |
| `updateMetadata(payload)` | Update token/market metadata |
| `requestTwitterChallenge()` | Start X verification |
| `verifyTwitter(tweetUrl)` | Complete X verification |
| `syncLoan(txHash)` | Manual loan sync (if auto-sync failed) |
| `createApiKey(label)` / `listApiKeys()` | API key management |
