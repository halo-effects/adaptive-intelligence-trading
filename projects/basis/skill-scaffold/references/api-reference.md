# Basis SDK — Contract Reference

> **Source: Alex's SDK Reference (2026-03-14). Contract addresses resolved dynamically by SDK.**
>
> This is the authoritative reference for all Basis smart contract interactions.
> Agents and integrators call these contracts directly via web3 libraries (ethers.js, web3.py, viem).
> The SDK abstracts contract address resolution — you reference contracts by name, not hardcoded address.
>
> _Note: The Basis SDK is being built by Alex. This reference covers all 13 deployed contracts.
> SDK usage documentation and the published package will follow when Alex releases them.
> In the meantime, use this reference for direct contract calls._

---

# BASIS DeFi Ecosystem — SDK Reference

> Complete reference for all user-facing and agent-facing smart contract functions.
> Contract addresses are resolved dynamically by the SDK — functions reference contracts by name.

---

## Table of Contents

1. [ASwap (SWAP)](#1-aswap-swap)
2. [A_STABLETOKEN (MAIN_TOKEN)](#2-a_stabletoken-main_token)
3. [FACTORYTOKEN](#3-factorytoken)
4. [ATokenFactory](#4-atokenfactory)
5. [ALOAN_HUB](#5-aloan_hub)
6. [AStasisVault (STAKING)](#6-astasisvault-staking)
7. [ATaxes](#7-ataxes)
8. [ALEVERAGE](#8-aleverage)
9. [A_VestingContract](#9-a_vestingcontract)
10. [AMarketTrading (Public Prediction Markets)](#10-amarkettrading-public-prediction-markets)
11. [AMarketResolver](#11-amarketresolver)
12. [APrivateTradingMarket (Private Prediction Markets)](#12-aprivatetradingmarket-private-prediction-markets)
13. [AMarketReader](#13-amarketreader)

---

## 1. ASwap (SWAP)

The primary entry point for all trading in the ecosystem. Users call this contract to buy and sell tokens (both MAIN and factory tokens), open leveraged positions, and close loan/leverage positions.

### Write Functions

---

#### `buyTokens`

```solidity
function buyTokens(uint256 amount, uint256 minOut, address[] calldata path, bool wrapTokens) external
```

Buy tokens through the ecosystem AMM.

| Parameter | Type | Description |
|-----------|------|-------------|
| `amount` | `uint256` | Amount of input token to spend |
| `minOut` | `uint256` | Minimum output tokens (slippage protection) |
| `path` | `address[]` | Swap route. `[USDC, MAIN_TOKEN]` for 2-hop or `[USDC, MAIN_TOKEN, factoryToken]` for 3-hop |
| `wrapTokens` | `bool` | If `true` and output is MAIN, wraps into wSTASIS automatically |

**Approve required:** `approve(path[0], SWAP, amount)` on the input token (typically USDC).

---

#### `sellTokens`

```solidity
function sellTokens(uint256 amount, uint256 minOut, address[] calldata path, bool swapToETH) external
```

Sell tokens through the ecosystem AMM.

| Parameter | Type | Description |
|-----------|------|-------------|
| `amount` | `uint256` | Amount of tokens to sell |
| `minOut` | `uint256` | Minimum output amount (slippage protection) |
| `path` | `address[]` | Swap route (reverse of buy path). `[MAIN_TOKEN, USDC]` or `[factoryToken, MAIN_TOKEN, USDC]` |
| `swapToETH` | `bool` | If `true`, converts output USDC to ETH via Uniswap V3 |

**Approve required:** `approve(path[0], SWAP, amount)` on the token being sold.

---

#### `leverageBuy`

```solidity
function leverageBuy(uint256 _amount, uint256 minOut, address[] calldata path, uint256 numberOfDays) external
```

Open a leveraged position. The contract borrows against the purchased tokens to amplify the buy.

| Parameter | Type | Description |
|-----------|------|-------------|
| `_amount` | `uint256` | USDC amount to use as initial investment |
| `minOut` | `uint256` | Minimum tokens received (slippage protection) |
| `path` | `address[]` | `[USDC, MAIN_TOKEN]` for MAIN leverage or `[USDC, MAIN_TOKEN, factoryToken]` for factory leverage |
| `numberOfDays` | `uint256` | Loan duration in days |

**Approve required:** `approve(USDC, SWAP, _amount)`.

**Note:** Leverage is dynamic — it depends on current pool liquidity and position size. Smaller positions yield higher leverage (up to ~28x on fresh pools). Larger positions have lower leverage due to price impact. "Up to 36x" is the theoretical maximum on perfectly liquid pools.

---

#### `mixedBuy`

```solidity
function mixedBuy(uint256 _amount, uint256 minOutLev, uint256 minOut, address[] calldata path, uint256 numberOfDays, uint256 percentageLeverage) external
```

Split a purchase between a spot buy and a leveraged position.

| Parameter | Type | Description |
|-----------|------|-------------|
| `_amount` | `uint256` | Total USDC to spend |
| `minOutLev` | `uint256` | Minimum tokens for the leverage portion |
| `minOut` | `uint256` | Minimum tokens for the spot portion |
| `path` | `address[]` | Swap route (same as `leverageBuy`) |
| `numberOfDays` | `uint256` | Loan duration for the leverage portion |
| `percentageLeverage` | `uint256` | Percentage allocated to leverage (1–99) |

**Approve required:** `approve(USDC, SWAP, _amount)`.

**Agent note:** `mixedBuy` is available via SDK/direct contract call only. It is **not exposed on the frontend UI**. This is an agent-exclusive function for splitting spot and leveraged exposure in one transaction.

---

#### `partialLoanSell`

```solidity
function partialLoanSell(uint256 loanId, uint256 percentage, bool isLeverage, uint256 minOut) external
```

Partially or fully close a loan or leverage position by selling collateral.

| Parameter | Type | Description |
|-----------|------|-------------|
| `loanId` | `uint256` | The loan or leverage ID |
| `percentage` | `uint256` | Percentage to close. Must be divisible by 10 (10, 20, ... 100) |
| `isLeverage` | `bool` | `true` for leverage positions, `false` for loans |
| `minOut` | `uint256` | Minimum USDC output (slippage protection) |

**Note:** For leverage positions, proceeds up to the initial investment amount are tax-free; only profits are taxed at 10%.

---

### Read Functions

---

#### `getAmountsOut`

```solidity
function getAmountsOut(uint256 amount, address[] calldata path) external view returns (uint256)
```

Estimate the output amount for a given input and path. Does **not** include tax in the estimate.

| Parameter | Type | Description |
|-----------|------|-------------|
| `amount` | `uint256` | Input amount |
| `path` | `address[]` | Swap route |

**Returns:** `uint256` — estimated output amount.

---

#### `lastTradeBlock`

```solidity
function lastTradeBlock() external view returns (uint256)
```

**Returns:** `uint256` — block number of the most recent trade.

---

#### `totalTaxDistributed`

```solidity
function totalTaxDistributed() external view returns (uint256)
```

**Returns:** `uint256` — total USDC distributed as tax across all trades.

---

## 2. A_STABLETOKEN (MAIN_TOKEN)

The core ecosystem token with an embedded AMM paired against USDC. Users interact directly with this contract to manage leverage positions (using `isLeverage=true`, which bypasses the LOAN_HUB check) and to query prices, reserves, and loan data.

### Write Functions

---

#### `ExtendLoan`

```solidity
function ExtendLoan(uint256 loanId, uint256 numberOfDays, bool isLeverage, bool payInUSDC, bool refinance, bool isFree) external
```

Extend an existing leverage position's duration, optionally refinancing against equity gains.

| Parameter | Type | Description |
|-----------|------|-------------|
| `loanId` | `uint256` | Leverage position ID |
| `numberOfDays` | `uint256` | Additional days. Set to `0` with `refinance=true` for refinance-only |
| `isLeverage` | `bool` | Must be `true` for leverage positions |
| `payInUSDC` | `bool` | If `true`, pay extension fee in USDC instead of deducting from collateral |
| `refinance` | `bool` | If `true`, borrow additional USDC against equity gain |
| `isFree` | `bool` | Must be `false` for regular users |

**Approve required (conditional):** If `payInUSDC=true`, call `approve(USDC, MAIN_TOKEN, fee)`. Use `ExtensionEligibility` to determine the fee.

---

#### `RepayLoan`

```solidity
function RepayLoan(uint256 loanId, bool isLeverage) external
```

Repay a leverage position in full, returning collateral tokens.

| Parameter | Type | Description |
|-----------|------|-------------|
| `loanId` | `uint256` | Leverage position ID |
| `isLeverage` | `bool` | Must be `true` for leverage positions |

**Approve required:** `approve(USDC, MAIN_TOKEN, loan.fullAmount)`.

---

#### `ClaimLiquidation`

```solidity
function ClaimLiquidation(uint256 loanId, bool isLeverage) external
```

Claim residual tokens remaining after a leverage position has been liquidated.

| Parameter | Type | Description |
|-----------|------|-------------|
| `loanId` | `uint256` | Leverage position ID |
| `isLeverage` | `bool` | Must be `true` for leverage positions |

---

### Read Functions

---

#### `getTokenPrice`

```solidity
function getTokenPrice() external view returns (uint256)
```

**Returns:** `uint256` — current token price in USDC with 18-decimal precision (`reserve1 * 1e18 / reserve0`).

---

#### `getUSDPrice`

```solidity
function getUSDPrice() external view returns (uint256)
```

**Returns:** `uint256` — same as `getTokenPrice` for MAIN_TOKEN.

---

#### `getReserves`

```solidity
function getReserves() external view returns (uint256 reserve0, uint256 reserve1, uint256 blockTimestampLast)
```

**Returns:** AMM reserves. `reserve0` = token reserve, `reserve1` = USDC reserve.

---

#### `reserve0` / `reserve1`

```solidity
function reserve0() external view returns (uint256)
function reserve1() external view returns (uint256)
```

**Returns:** Individual reserve values. `reserve0` = token, `reserve1` = USDC.

---

#### `baseReserve1`

```solidity
function baseReserve1() external view returns (uint256)
```

**Returns:** `uint256` — initial USDC reserve (used for stuck LP calculation).

---

#### `totalSupply`

```solidity
function totalSupply() external view returns (uint256)
```

**Returns:** `uint256` — total token supply.

---

#### `balanceOf`

```solidity
function balanceOf(address account) external view returns (uint256)
```

**Returns:** `uint256` — token balance of `account`.

---

#### `allowance`

```solidity
function allowance(address owner, address spender) external view returns (uint256)
```

**Returns:** `uint256` — remaining allowance.

---

#### `calculateTokensForBuy`

```solidity
function calculateTokensForBuy(uint256 usdcAmount) external view returns (uint256)
```

Estimate tokens received for a USDC buy amount.

| Parameter | Type | Description |
|-----------|------|-------------|
| `usdcAmount` | `uint256` | USDC input amount |

**Returns:** `uint256` — tokens out.

---

#### `calculateTokensForSell`

```solidity
function calculateTokensForSell(uint256 tokenAmount) external view returns (uint256)
```

Estimate USDC received for selling tokens.

| Parameter | Type | Description |
|-----------|------|-------------|
| `tokenAmount` | `uint256` | Token input amount |

**Returns:** `uint256` — USDC out.

---

#### `calculateUsdcForTokens`

```solidity
function calculateUsdcForTokens(uint256 tokenAmountOut) external view returns (uint256)
```

Calculate USDC needed to buy an exact amount of tokens (amountsIn).

| Parameter | Type | Description |
|-----------|------|-------------|
| `tokenAmountOut` | `uint256` | Desired token output |

**Returns:** `uint256` — USDC required.

---

#### `calculateTokensForUsdc`

```solidity
function calculateTokensForUsdc(uint256 usdcAmountOut) external view returns (uint256)
```

Calculate tokens needed to receive an exact amount of USDC (amountsIn).

| Parameter | Type | Description |
|-----------|------|-------------|
| `usdcAmountOut` | `uint256` | Desired USDC output |

**Returns:** `uint256` — tokens required.

---

#### `getColleteralValue`

```solidity
function getColleteralValue(uint256 tokenAmount, address token) external view returns (uint256)
```

Get the USDC value of tokens when used as loan collateral. Uses spot price for MAIN, floor price for factory tokens.

| Parameter | Type | Description |
|-----------|------|-------------|
| `tokenAmount` | `uint256` | Amount of tokens |
| `token` | `address` | Token address |

**Returns:** `uint256` — USDC collateral value.

---

#### `getDynamicFee`

```solidity
function getDynamicFee(uint256 amount, uint256 numberOfDays) external view returns (uint256)
```

Calculate the dynamic fee for a given loan amount and duration.

| Parameter | Type | Description |
|-----------|------|-------------|
| `amount` | `uint256` | Loan amount |
| `numberOfDays` | `uint256` | Loan duration |

**Returns:** `uint256` — fee amount in USDC.

---

#### `dynamicFeePercentage` / `staticFeePercentage`

```solidity
function dynamicFeePercentage() external view returns (uint256)
function staticFeePercentage() external view returns (uint256)
```

**Returns:** Fee rates. `dynamicFeePercentage`: 5 = 0.005%. `staticFeePercentage`: 200 = 2.0%.

---

#### `minimumLoan`

```solidity
function minimumLoan() external view returns (uint256)
```

**Returns:** `uint256` — minimum loan amount in USDC terms.

---

#### `minDaysLoan` / `maxDaysLoan`

```solidity
function minDaysLoan() external view returns (uint256)
function maxDaysLoan() external view returns (uint256)
```

**Returns:** Minimum and maximum loan duration in days.

---

#### `loans`

```solidity
function loans(address user, uint256 loanId) external view returns (Loan memory)
```

Get loan details. For hub loans, `user` is the LOAN_HUB address.

| Parameter | Type | Description |
|-----------|------|-------------|
| `user` | `address` | User address (or LOAN_HUB address for hub loans) |
| `loanId` | `uint256` | Loan ID |

**Returns:** `Loan` struct with loan details.

---

#### `leverages`

```solidity
function leverages(address user, uint256 loanId) external view returns (Loan memory)
```

Get leverage position details.

| Parameter | Type | Description |
|-----------|------|-------------|
| `user` | `address` | User's address |
| `loanId` | `uint256` | Leverage ID |

**Returns:** `Loan` struct with leverage details.

---

#### `loanCount` / `leverageCount`

```solidity
function loanCount(address user) external view returns (uint256)
function leverageCount(address user) external view returns (uint256)
```

**Returns:** Number of loans or leverages for the given address.

---

#### `userTokenLeverageIds`

```solidity
function userTokenLeverageIds(address user, address token, uint256 index) external view returns (uint256)
```

Get leverage ID by index for a specific user and token combination.

| Parameter | Type | Description |
|-----------|------|-------------|
| `user` | `address` | User address |
| `token` | `address` | Token address |
| `index` | `uint256` | Index into the user's leverage list for this token |

**Returns:** `uint256` — leverage ID.

---

#### `getLeverageCountForUserAndToken`

```solidity
function getLeverageCountForUserAndToken(address user, address token) external view returns (uint256)
```

**Returns:** `uint256` — number of leverage positions for user on a specific token.

---

#### `ExtensionEligibility`

```solidity
function ExtensionEligibility(address user, uint256 loanId, uint256 numberOfDays, bool isLeverage, bool payInUSDC, bool refinance) external view returns (bool possible, uint256 fee, uint256 extraOut)
```

Check whether a loan or leverage can be extended, and preview the cost.

| Parameter | Type | Description |
|-----------|------|-------------|
| `user` | `address` | User address |
| `loanId` | `uint256` | Loan or leverage ID |
| `numberOfDays` | `uint256` | Additional days |
| `isLeverage` | `bool` | `true` for leverage positions |
| `payInUSDC` | `bool` | Whether fee will be paid in USDC |
| `refinance` | `bool` | Whether to borrow against equity gain |

**Returns:**

| Field | Type | Description |
|-------|------|-------------|
| `possible` | `bool` | Whether extension is possible |
| `fee` | `uint256` | Fee amount |
| `extraOut` | `uint256` | Additional USDC from refinance |

---

#### `getPartialLoanSellAmounts`

```solidity
function getPartialLoanSellAmounts(uint256 loanId, address user, uint256 percentage, bool isLeverage) external view returns (uint256 mainToBurn, uint256 tokensToBurn, uint256 residualTokens)
```

Preview the amounts for a partial loan/leverage sell.

| Parameter | Type | Description |
|-----------|------|-------------|
| `loanId` | `uint256` | Loan or leverage ID |
| `user` | `address` | User address |
| `percentage` | `uint256` | Percentage to close (must be divisible by 10) |
| `isLeverage` | `bool` | `true` for leverage positions |

**Returns:**

| Field | Type | Description |
|-------|------|-------------|
| `mainToBurn` | `uint256` | MAIN tokens to burn |
| `tokensToBurn` | `uint256` | Factory tokens to burn (3-hop) |
| `residualTokens` | `uint256` | Tokens returned to user |

---

#### `getLiquidity`

```solidity
function getLiquidity() external view returns (uint256)
```

**Returns:** `uint256` — current USDC liquidity above the base reserve.

---

#### `tradingEnabled`

```solidity
function tradingEnabled() external view returns (bool)
```

**Returns:** `bool` — whether trading is currently active.

---

#### `hybridMultiplier`

```solidity
function hybridMultiplier() external view returns (uint256)
```

**Returns:** `uint256` — always `100` for MAIN_TOKEN.

---

#### `hasBonded`

```solidity
function hasBonded() external view returns (bool)
```

**Returns:** `bool` — always `true` for MAIN_TOKEN.

---

#### `projectedVetted`

```solidity
function projectedVetted() external view returns (bool)
```

**Returns:** `bool` — whether the project is vetted.

---

#### `SWAP` / `LOAN`

```solidity
function SWAP() external view returns (address)
function LOAN() external view returns (address)
```

**Returns:** Addresses of the SWAP and LOAN_HUB contracts.

---

## 3. FACTORYTOKEN

Ecosystem tokens created by ATokenFactory. Each has its own AMM paired against MAIN_TOKEN, a hybrid multiplier governing floor price behavior, optional bonding phase, optional freeze/whitelist, and a presale share reward system.

### Write Functions

---

#### `approve`

```solidity
function approve(address spender, uint256 value) external returns (bool)
```

Standard ERC20 approve.

---

#### `transfer`

```solidity
function transfer(address to, uint256 value) external returns (bool)
```

Standard ERC20 transfer. Burns sender's presale shares proportionally.

---

#### `claimRewards`

```solidity
function claimRewards() external
```

Claim accumulated USDC rewards from presale shares. No parameters required.

---

#### `DisableFreeze` (DEV only)

```solidity
function DisableFreeze() external
```

Remove the freeze (whitelist requirement) from the token. Only callable by the token's DEV.

---

#### `SetWhitelistedWallet` (DEV only)

```solidity
function SetWhitelistedWallet(address[] wallets, uint256 amount, string tag) external
```

Whitelist wallets to allow purchases on a frozen token.

---

#### `RemoveWhitelist` (DEV only)

```solidity
function RemoveWhitelist(address wallet) external
```

Remove a wallet from the whitelist. Only callable by the token's DEV.

---

### Read Functions

---

#### `getTokenPrice`

```solidity
function getTokenPrice() external view returns (uint256)
```

**Returns:** `uint256` — price in MAIN tokens (18-decimal precision).

---

#### `getUSDPrice`

```solidity
function getUSDPrice() external view returns (uint256)
```

**Returns:** `uint256` — price in USD. Combines token-to-MAIN price with MAIN-to-USDC price.

---

#### `calculateFloor`

```solidity
function calculateFloor() external view returns (uint256)
```

**Returns:** `uint256` — floor price in USD.

---

#### `calculateTokenFloor`

```solidity
function calculateTokenFloor() external view returns (uint256)
```

**Returns:** `uint256` — floor price in MAIN token terms.

---

#### `getReserves`

```solidity
function getReserves() external view returns (uint256 reserve0, uint256 reserve1, uint256 blockTimestampLast)
```

**Returns:** AMM reserves. `reserve0` = factory token reserve, `reserve1` = MAIN token reserve.

---

#### `calculateTokensForBuy` / `calculateTokensForSell`

```solidity
function calculateTokensForBuy(uint256 mainAmount) external view returns (uint256)
function calculateTokensForSell(uint256 tokenAmount) external view returns (uint256)
```

Estimate token output for a given input.

---

#### `calculateMainForTokens` / `calculateTokensForMain`

```solidity
function calculateMainForTokens(uint256 tokenAmountOut) external view returns (uint256)
function calculateTokensForMain(uint256 mainAmountOut) external view returns (uint256)
```

Calculate exact input needed for a desired output (amountsIn).

---

#### `getLiquidity`

```solidity
function getLiquidity() external view returns (uint256)
```

**Returns:** `uint256` — liquidity above base reserve (denominated in MAIN).

---

#### `getBondingTarget`

```solidity
function getBondingTarget() external view returns (uint256)
```

**Returns:** `uint256` — MAIN tokens needed to complete bonding (dynamically adjusted based on MAIN price).

---

#### `hybridMultiplier`

```solidity
function hybridMultiplier() external view returns (uint256)
```

**Returns:** `uint256` — the hybrid multiplier (1–100). `100` = standard AMM. Lower values = more speculative with a floor.

---

#### `hasBonded`

```solidity
function hasBonded() external view returns (bool)
```

**Returns:** `bool` — whether bonding is complete.

---

#### `frozen`

```solidity
function frozen() external view returns (bool)
```

**Returns:** `bool` — whether the token is frozen (whitelist-only trading).

---

#### `autoVest` / `gradualAutoVesting` / `autoVestDuration`

```solidity
function autoVest() external view returns (bool)
function gradualAutoVesting() external view returns (bool)
function autoVestDuration() external view returns (uint256)
```

**Returns:** Auto-vesting configuration.

---

#### `totalSupply` / `balanceOf` / `allowance`

Standard ERC20 read functions.

---

#### `shares` / `totalShares`

```solidity
function shares(address investor) external view returns (uint256)
function totalShares() external view returns (uint256)
```

**Returns:** Presale share balances for reward distribution.

---

#### `getClaimableRewards`

```solidity
function getClaimableRewards(address investor) external view returns (uint256)
```

**Returns:** `uint256` — claimable USDC rewards for the investor.

---

#### `whitelisted` / `whitelistMaxBuyForUser` / `whitelistBoughtByUser`

Whitelist status and buy limits for frozen tokens.

---

#### `symbol` / `name` / `decimals`

Standard ERC20 metadata. `decimals` is always `18`.

---

#### `token0` / `token1`

```solidity
function token0() external view returns (address)
function token1() external view returns (address)
```

**Returns:** `token0` = this factory token. `token1` = MAIN_TOKEN.

---

#### `baseReserve0` / `baseReserve1`

Initial reserve values at token creation.

---

#### `DEV`

```solidity
function DEV() external view returns (address)
```

**Returns:** `address` — the developer address of the token.

---

#### `creationBlock` / `creationTime` / `lastTrade`

Creation block, creation timestamp, and block of the last trade.

---

## 4. ATokenFactory

Creates new factory tokens within the ecosystem. Each created token gets its own AMM paired against MAIN_TOKEN.

### Write Functions

---

#### `createToken`

```solidity
function createToken(
    string symbol,
    string name,
    uint256 hybridMultiplier,
    bool frozen,
    uint256 usdcForBonding,
    uint256 startLP,
    bool autoVest,
    uint256 autoVestDuration,
    bool gradualAutovest
) external payable returns (address)
```

Create a new ecosystem token.

| Parameter | Type | Description |
|-----------|------|-------------|
| `symbol` | `string` | Token ticker symbol |
| `name` | `string` | Token name |
| `hybridMultiplier` | `uint256` | 1–100. `100` = standard AMM. Lower = more speculative with a floor price |
| `frozen` | `bool` | If `true`, only whitelisted wallets can buy |
| `usdcForBonding` | `uint256` | Bonding target in USDC (0–150000). `0` = no bonding phase. Must be >= 1 if `frozen` |
| `startLP` | `uint256` | Initial LP units (100–10000) — sets virtual liquidity depth ($100–$10,000) |
| `autoVest` | `bool` | Enable auto-vesting for bonding phase buyers |
| `autoVestDuration` | `uint256` | Vesting duration |
| `gradualAutovest` | `bool` | If `true`, gradual vesting. If `false`, cliff vesting |

**ETH required:** Must send `feeAmount()` ETH as `msg.value`.

**Returns:** `address` — the newly created token's address.

---

### Read Functions

---

#### `isEcosystemToken`

```solidity
function isEcosystemToken(address token) external view returns (bool)
```

**Returns:** `bool` — whether the address is a factory-created token.

---

#### `getTokensByCreator`

```solidity
function getTokensByCreator(address creator) external view returns (address[] memory)
```

**Returns:** `address[]` — all tokens created by the given address.

---

#### `creationCount`

```solidity
function creationCount() external view returns (uint256)
```

**Returns:** `uint256` — total number of factory tokens created.

---

#### `feeAmount`

```solidity
function feeAmount() external view returns (uint256)
```

**Returns:** `uint256` — ETH fee required to create a token.

---

## 5. ALOAN_HUB

Hub contract for managing regular loans (not leverages). Routes loan operations to the correct ecosystem's MAIN_TOKEN contract.

### Write Functions

---

#### `takeLoan`

```solidity
function takeLoan(address ecosystem, address collateral, uint256 amount, uint256 daysCount) external returns (uint256 hubId)
```

Take a loan against token collateral.

| Parameter | Type | Description |
|-----------|------|-------------|
| `ecosystem` | `address` | MAIN_TOKEN address of the ecosystem |
| `collateral` | `address` | Token to pledge (MAIN or any factory token) |
| `amount` | `uint256` | Amount of collateral tokens |
| `daysCount` | `uint256` | Loan duration in days (min 10, max 1000) |

**Approve required:** `approve(collateral, LOAN_HUB, amount)`.

**Returns:** `uint256` — the hub loan ID.

---

#### `repayLoan`

```solidity
function repayLoan(uint256 hubId) external
```

Repay a loan in full.

**Approve required:** `approve(USDC, LOAN_HUB, loan.fullAmount)`.

---

#### `increaseLoan`

```solidity
function increaseLoan(uint256 hubId, uint256 amountToAdd) external
```

Add more collateral and borrow additional USDC against an existing loan.

**Approve required:** `approve(collateralToken, LOAN_HUB, amountToAdd)`.

---

#### `extendLoan`

```solidity
function extendLoan(uint256 hubId, uint256 addDays, bool payInStable, bool refinance) external
```

Extend loan duration, optionally refinancing.

**Approve required (conditional):** If `payInStable=true`, call `approve(USDC, LOAN_HUB, fee)`.

---

#### `claimLiquidation`

```solidity
function claimLiquidation(uint256 hubId) external returns (uint256 claimed)
```

Claim residual tokens after a loan has been liquidated.

---

#### `hubPartialLoanSell`

```solidity
function hubPartialLoanSell(uint256 hubId, uint256 percentage, bool isLeverage, uint256 minOut) external
```

Partially sell a loan position through the SWAP contract.

| Parameter | Type | Description |
|-----------|------|-------------|
| `hubId` | `uint256` | Hub loan ID |
| `percentage` | `uint256` | Percentage to close (divisible by 10, range 10–100) |
| `isLeverage` | `bool` | `false` for regular loans |
| `minOut` | `uint256` | Minimum USDC output (slippage protection) |

---

### Read Functions

---

#### `getUserLoanDetails`

```solidity
function getUserLoanDetails(address user, uint256 hubId) external view returns (FullLoanDetails memory)
```

Get complete loan details including collateral, amounts, timing, and liquidation status.

---

#### `userLoanCount`

```solidity
function userLoanCount(address user) external view returns (uint256)
```

**Returns:** `uint256` — total number of loans for the user.

---

## 6. AStasisVault (STAKING)

Wrapped staking token (wSTASIS). Users deposit MAIN tokens and receive wSTASIS shares. Yield from ecosystem taxes increases the value of each share over time. Also supports borrowing against locked shares.

### Write Functions

---

#### `buy`

```solidity
function buy(uint256 _amount) external
```

Deposit MAIN tokens and receive wSTASIS shares.

**Approve required:** `approve(MAIN_TOKEN, STAKING, _amount)`.

---

#### `sell`

```solidity
function sell(uint256 _shares, bool _claimUSDC, uint256 _minUSDC) external
```

Redeem wSTASIS shares for MAIN tokens or USDC.

| Parameter | Type | Description |
|-----------|------|-------------|
| `_shares` | `uint256` | Number of wSTASIS shares to redeem |
| `_claimUSDC` | `bool` | If `true`, sells MAIN to USDC through SWAP (incurs tax) |
| `_minUSDC` | `uint256` | Minimum USDC output if `_claimUSDC=true` (slippage protection) |

---

#### `lock`

```solidity
function lock(uint256 _shares) external
```

Lock wSTASIS shares as collateral (transfers shares to the contract).

---

#### `unlock`

```solidity
function unlock(uint256 _shares) external
```

Unlock wSTASIS shares. Must maintain sufficient collateral ratio if a loan is active.

---

#### `borrow`

```solidity
function borrow(uint256 _stasisAmountToBorrow, uint256 _days) external
```

Borrow USDC against locked wSTASIS shares. Takes a loan through LOAN_HUB using the vault's MAIN tokens as collateral.

---

#### `addToLoan`

```solidity
function addToLoan(uint256 _additionalStasisToBorrow) external
```

Add more borrowing capacity to an existing vault loan.

---

#### `repay`

```solidity
function repay() external
```

Repay the vault loan in full.

**Approve required:** `approve(USDC, STAKING, fullAmount)`.

---

#### `extendLoan`

```solidity
function extendLoan(uint256 _daysToAdd, bool _payInUSDC, bool _refinance) external
```

Extend the vault loan duration.

**Approve required (conditional):** If `_payInUSDC=true`, call `approve(USDC, STAKING, fee)`.

---

#### `settleLiquidation`

```solidity
function settleLiquidation() external
```

Process liquidation of a vault loan. Burns proportional wSTASIS shares from the vault.

---

### Read Functions

---

#### `totalAssets`

```solidity
function totalAssets() external view returns (uint256)
```

**Returns:** `uint256` — total MAIN tokens managed by the vault (available + pledged in loans).

---

#### `convertToShares` / `convertToAssets`

```solidity
function convertToShares(uint256 assets) external view returns (uint256)
function convertToAssets(uint256 shares) external view returns (uint256)
```

Convert between MAIN tokens and wSTASIS shares at current ratio.

---

#### `getUserStakeDetails`

```solidity
function getUserStakeDetails(address user) external view returns (uint256 liquidShares, uint256 lockedShares, uint256 totalShares, uint256 totalAssetValue)
```

Get complete stake breakdown for a user.

---

#### `userVaults`

```solidity
function userVaults(address user) external view returns (uint256 lockedWStasis, uint256 pledgedStasis, uint256 hubId, bool hasActiveLoan)
```

Get user's vault state including loan status.

---

#### `balanceOf` / `totalSupply`

Standard wSTASIS balance and supply queries.

---

## 7. ATaxes

Tax configuration and surge pricing system. Token developers use this to manage surge taxes and revenue sharing on their tokens.

### Write Functions (DEV only)

---

#### `startSurgeTax`

```solidity
function startSurgeTax(uint256 startRate, uint256 endRate, uint256 duration, address token) external
```

Start a decaying surge tax on a factory token.

**Constraints:** 7 days of surge per 30-day rolling window. Only callable by the token's DEV.

---

#### `endSurgeTax`

```solidity
function endSurgeTax(address token) external
```

End an active surge tax early. Refunds unused hours to the quota.

---

#### `addDevShare`

```solidity
function addDevShare(IERC20 token, address wallet, uint256 basisPoints) external
```

Add or update a developer revenue share wallet. Maximum 10 wallets per token. Total allocation cannot exceed 10000 BP.

---

#### `removeDevShare`

```solidity
function removeDevShare(IERC20 token, address wallet) external
```

Remove a developer share wallet.

---

### Read Functions

---

#### `getTaxRate`

```solidity
function getTaxRate(IERC20 token, address user) external view returns (uint256)
```

Get the current effective tax rate in basis points. Includes surge. Whitelisted users return `0`.

---

#### `getCurrentSurgeTax`

```solidity
function getCurrentSurgeTax(address token) external view returns (uint256)
```

**Returns:** `uint256` — current decayed surge rate in basis points.

---

#### `availableSurgeQuota`

```solidity
function availableSurgeQuota(address token) external view returns (uint256)
```

**Returns:** `uint256` — remaining surge seconds available.

---

#### `_taxRateXether` / `_taxRateStable` / `_taxRateDefault` / `_taxRatePrediction`

Base tax rates in basis points:
- `_taxRateXether` — MAIN token
- `_taxRateStable` — factory tokens with `hybridMultiplier=100` (Stable+)
- `_taxRateDefault` — hybrid factory tokens (Floor+)
- `_taxRatePrediction` — prediction market tokens (Predict+)

---

## 8. ALEVERAGE

Simulation contract for previewing leverage positions before execution. All functions are `view` or `pure` — no state changes.

### Read Functions

---

#### `simulateLeverage`

```solidity
function simulateLeverage(uint256 _amount, address[] calldata path, uint256 numberOfDays) external view returns (EndResult memory)
```

Simulate a MAIN token leverage position. Returns projected reserves, repay amounts, collateral, fees.

**Use this before calling `leverageBuy` to preview the outcome.**

---

#### `simulateLeverageFactory`

```solidity
function simulateLeverageFactory(uint256 _amount, address[] calldata path, uint256 numberOfDays) external view returns (EndResult memory)
```

Simulate a factory token leverage position.

---

#### `calculateFloor`

```solidity
function calculateFloor(uint256 hybridMultiplier, uint256 reserve0, uint256 reserve1, uint256 baseReserve0, uint256 xereserve0, uint256 xereserve1) external pure returns (uint256)
```

Calculate floor price from raw reserve values.

---

#### `getColleteralValue` / `getColleteralValueHybrid`

Calculate collateral value for MAIN-paired or hybrid (factory) tokens.

---

#### `calculateTokensForBuy` / `calculateTokensToBurn`

AMM calculation helpers for leverage previewing.

---

## 9. A_VestingContract

Token vesting contract supporting both gradual and cliff vesting schedules, with integrated loan functionality against unvested tokens.

### Write Functions

---

#### `createGradualVesting`

```solidity
function createGradualVesting(
    address beneficiary,
    address token,
    uint256 totalAmount,
    uint256 startTime,
    uint256 durationInDays,
    TimeUnit timeUnit,
    string memo,
    address ecosystem
) external payable returns (uint256 vestingId)
```

Create a gradual vesting schedule.

**Approve required:** `approve(token, VESTING, totalAmount)`.

**Returns:** `uint256` — vesting ID.

---

#### `createCliffVesting`

```solidity
function createCliffVesting(
    address beneficiary,
    address token,
    uint256 totalAmount,
    uint256 unlockTime,
    string memo,
    address ecosystem
) external payable returns (uint256 vestingId)
```

Create a cliff vesting schedule (all tokens unlock at once).

---

#### `batchCreateGradualVesting` / `batchCreateCliffVesting`

Batch create vestings for multiple beneficiaries with a single `approve`.

---

#### `claimTokens`

```solidity
function claimTokens(uint256 vestingId) external
```

Claim vested tokens. Only callable by the beneficiary. Cannot claim while a loan is active.

---

#### `takeLoanOnVesting`

```solidity
function takeLoanOnVesting(uint256 vestingId) external
```

Borrow USDC against unvested tokens. Loan duration auto-calculated from remaining vesting period. USDC sent directly to the beneficiary.

---

#### `repayLoanOnVesting`

```solidity
function repayLoanOnVesting(uint256 vestingId) external
```

Repay a vesting loan. Adjusts `totalAmount` if loan was liquidated.

**Approve required (conditional):** If loan is active, `approve(USDC, VESTING, loan.fullAmount)`.

---

#### `extendVestingPeriod`

```solidity
function extendVestingPeriod(uint256 vestingId, uint256 additionalDays) external
```

Extend the vesting duration. Callable by creator or beneficiary.

---

### Read Functions

---

#### `getVestedAmount` / `getClaimableAmount`

```solidity
function getVestedAmount(uint256 vestingId) external view returns (uint256)
function getClaimableAmount(uint256 vestingId) external view returns (uint256)
```

Vested so far and claimable amount.

---

#### `getVestingDetails`

```solidity
function getVestingDetails(uint256 vestingId) external view returns (Vesting memory)
```

Full vesting schedule details including creator, beneficiary, token, amounts, timing, and loan status.

---

#### `getVestingsByCreator` / `getVestingsByBeneficiary`

```solidity
function getVestingsByCreator(address creator) external view returns (uint256[] memory)
function getVestingsByBeneficiary(address beneficiary) external view returns (uint256[] memory)
```

List vestings by creator or beneficiary.

---

## 10. AMarketTrading (Public Prediction Markets)

AMM-based public prediction markets with P2P order book support. Users can create markets, buy/sell outcome shares, and redeem winnings after resolution.

### Write Functions

---

#### `createMarket`

```solidity
function createMarket(
    string marketName,
    string symbol,
    uint256 endTime,
    string[] _optionNames,
    address maintoken,
    bool frozen,
    uint256 bonding
) external payable returns (address marketToken)
```

Create a new public prediction market.

| Parameter | Type | Description |
|-----------|------|-------------|
| `marketName` | `string` | Market title |
| `symbol` | `string` | Token symbol for the market's Predict+ token |
| `endTime` | `uint256` | Market end timestamp. `0` for open-ended |
| `_optionNames` | `string[]` | Outcome names (2–50 outcomes) |
| `maintoken` | `address` | MAIN_TOKEN address (ecosystem) |
| `frozen` | `bool` | Require whitelist to buy |
| `bonding` | `uint256` | Bonding target |

**ETH required:** Must send factory fee as `msg.value`.

**Returns:** `address` — the market's Predict+ token address.

---

#### `buy`

```solidity
function buy(address marketToken, uint8 outcomeId, address inputToken, uint256 inputAmount, uint256 minUsdc, uint256 minShares) external
```

Buy outcome shares via the AMM.

**Approve required:** `approve(inputToken, MARKET_TRADING, inputAmount)`.

---

#### `redeem`

```solidity
function redeem(address marketToken) external
```

Redeem winning shares after market resolution.

---

#### `listOrder`

```solidity
function listOrder(address marketToken, uint8 outcomeId, uint256 amount, uint256 pricePerShare) external
```

List a P2P sell order for outcome shares. `pricePerShare` range: 1000–999000 (in 1e6). Set to `0` for market price.

---

#### `cancelOrder` / `buyOrder` / `buyMultipleOrders` / `buyOrdersAndContract`

P2P order book management. See full signatures above. `buyOrdersAndContract` fills orders first then buys remainder from AMM.

---

### Read Functions

---

#### `getMarketData`

```solidity
function getMarketData(address marketToken) external view returns (MarketData memory)
```

Full market state including name, creator, timing, resolution status, and pot sizes.

---

#### `getAllOutcomes` (via AMarketReader)

Use `AMarketReader.getAllOutcomes()` to get all outcomes with prices and probabilities in one call.

---

#### `getUserShares`

```solidity
function getUserShares(address marketToken, address user, uint8 outcomeId) external view returns (uint256)
```

**Returns:** `uint256` — user's share count for an outcome.

---

#### `getBuyOrderCost`

```solidity
function getBuyOrderCost(address marketToken, uint256 orderId, uint256 fill) external view returns (uint256 baseUsdc, uint256 buyerTax, uint256 totalCostToBuyer, uint256 netToSeller)
```

Preview the cost to fill a P2P order.

---

## 11. AMarketResolver

Dispute resolution system for public prediction markets. Uses a propose-dispute-vote-veto mechanism with bonded proposals and staked voters.

### Write Functions

---

#### `proposeOutcome`

```solidity
function proposeOutcome(address marketToken, uint8 outcomeId) external
```

Propose the winning outcome. Can be submitted after `endTime` (creator can propose 15 minutes early).

**Approve required:** `approve(USDC, RESOLVER, PROPOSAL_BOND)`.

---

#### `dispute`

```solidity
function dispute(address marketToken, uint8 newOutcomeId) external
```

Dispute a proposed outcome.

**Approve required:** `approve(USDC, RESOLVER, PROPOSAL_BOND)`.

---

#### `vote`

```solidity
function vote(address marketToken, uint8 outcomeId) external
```

Vote during a dispute. Requires prior `stake()` call.

---

#### `stake` / `unstake`

```solidity
function stake(address token) external
function unstake(address token) external
```

Stake ecosystem tokens to become eligible to vote in disputes.

---

#### `finalizeUncontested` / `finalizeMarket`

Finalize markets after dispute periods. `finalizeMarket` requires quorum and 70% consensus.

---

#### `claimBounty` / `claimEarlyBounty`

Claim bounty rewards for voting correctly.

---

### Read Functions

---

#### `disputes`

```solidity
function disputes(address marketToken) external view returns (DisputeData memory)
```

Full dispute state including proposer, disputer, bonds, and timing.

---

#### Constants

```solidity
function DISPUTE_PERIOD() external view returns (uint256)
function PROPOSAL_PERIOD() external view returns (uint256)
function VETO_PERIOD() external view returns (uint256)
function PROPOSAL_BOND() external view returns (uint256)
function MIN_QUORUM() external view returns (uint256)
function VOTING_CONSENSUS() external view returns (uint256)
function MIN_STAKE_AMOUNT() external view returns (uint256)
function VOTE_LOCK_DURATION() external view returns (uint256)
```

System parameters for dispute resolution timing and thresholds.

---

## 12. APrivateTradingMarket (Private Prediction Markets)

Private prediction markets with creator-managed voting and resolution. Similar to public markets but with creator-controlled voter lists and optional buyer restrictions.

### Write Functions

---

#### `createMarket`

```solidity
function createMarket(
    string marketName,
    string symbol,
    uint256 endTime,
    string[] _optionNames,
    address maintoken,
    bool privateEvent,
    bool frozen,
    uint256 bonding
) external payable returns (address marketToken)
```

Create a private prediction market. `privateEvent=true` restricts buyers to approved list.

---

#### `buy` / `redeem` / `listOrder` / `cancelOrder` / `buyOrder` / `buyMultipleOrders` / `buyOrdersAndContract`

Same as public market equivalents. For private events, sender must be in `userCanBuyEvent` list.

---

#### `vote`

```solidity
function vote(address marketToken, uint8 outcomeId) external
```

Vote on the market outcome. Only registered voters or CEO. CEO voting INVALID instantly resolves the market.

---

#### `finalize`

```solidity
function finalize(address marketToken) external
```

Finalize the market after the voting window (15 minutes from first vote). Creator breaks ties.

---

#### `manageVoter` (Creator only)

```solidity
function manageVoter(address marketToken, address voter, bool status) external
```

Add or remove a voter. Maximum 11 voters per market.

---

#### `togglePrivateEventBuyers` (Creator only)

```solidity
function togglePrivateEventBuyers(address marketToken, address[] buyers, bool status) external
```

Enable or disable buyers for a private event.

---

### Read Functions

---

#### `getMarketData` / `getUserShares` / `getBuyOrderCost` / `getBuyOrderAmountsOut`

Same as public market equivalents.

---

#### `isMarketVoter` / `voterChoice`

```solidity
function isMarketVoter(address marketToken, address voter) external view returns (bool)
function voterChoice(address marketToken, address voter) external view returns (uint8)
```

Voter roster and choices.

---

#### `userCanBuyEvent`

```solidity
function userCanBuyEvent(address marketToken, address user) external view returns (bool)
```

**Returns:** `bool` — whether user is allowed to buy in a private event market.

---

## 13. AMarketReader

Read-only helper contract for aggregating prediction market data. Works with both public (AMarketTrading) and private (APrivateTradingMarket) markets.

### Read Functions

---

#### `getAllOutcomes`

```solidity
function getAllOutcomes(address routerAddress, address marketToken) external view returns (OutcomeInfo[] memory)
```

Get all outcomes with prices and probabilities in one call.

**Returns:** `OutcomeInfo[]` with outcome ID, name, reserves, shares, price per share, probability, and resolution status.

---

#### `estimateSharesOut`

```solidity
function estimateSharesOut(address routerAddress, address marketToken, uint8 outcomeId, uint256 usdcAmount, uint256[] orderIds, address user) external view returns (uint256)
```

Estimate total shares received from a combined order+AMM buy.

---

#### `getPotentialPayout`

```solidity
function getPotentialPayout(address routerAddress, address marketToken, uint8 outcomeId, uint256 sharesAmount, uint256 estimatedUsdcToPool) external view returns (uint256 holdPayout, uint256 simulatedAmmPayout)
```

Simulate potential payout for an outcome.

| Field | Description |
|-------|-------------|
| `holdPayout` | Payout if you already hold the shares |
| `simulatedAmmPayout` | Payout if you buy shares now (accounts for dilution from your own purchase) |

---

## Chain Details

| Property | Value |
|----------|-------|
| Chain | BNB Chain (Mainnet) |
| Chain ID | 56 |
| RPC | `https://bsc-dataseed.binance.org/` |
| Block time | ~3 seconds |
| Gas cost | Sub-cent (<$0.01 per tx) |
| Native token | BNB (for gas) |
| Stablecoin | USDC (live) / USDB (test — zero financial risk, real airdrop points) |

---

_End of SDK Reference — Source: Alex (2026-03-14)_
