# BASIS Ecosystem — Master Function List

Complete list of all public/external functions across all deployed contracts.

---

## 1. bUSDC (USDB)

| Function | Visibility | Mutability | Access |
|----------|-----------|-----------|--------|
| `decimals()` | public | view | open |
| `faucet()` | external | nonpayable | open |
| `mint(address to, uint256 amount)` | external | nonpayable | onlyOwner |
| `rescueTokens(address token, uint256 amount)` | external | nonpayable | onlyOwner |
| `rescueETH()` | external | nonpayable | onlyOwner |
| `NORMAL_FAUCET_AMOUNT()` | public | view | open |
| `OWNER_FAUCET_AMOUNT()` | public | view | open |
| `FAUCET_COOLDOWN()` | public | view | open |
| `lastFaucetRequest(address)` | public | view | open |

*Inherited ERC20: `name`, `symbol`, `totalSupply`, `balanceOf`, `transfer`, `allowance`, `approve`, `transferFrom`, `increaseAllowance`, `decreaseAllowance`*
*Inherited Ownable: `owner`, `renounceOwnership`, `transferOwnership`*

---

## 2. A_STASISTOKEN (MAIN_TOKEN)

### Write Functions

| Function | Visibility | Mutability | Access |
|----------|-----------|-----------|--------|
| `transfer(address to, uint256 value)` | external | nonpayable | open |
| `approve(address spender, uint256 value)` | external | nonpayable | open |
| `transferFrom(address from, address to, uint256 amount)` | external | nonpayable | open |
| `buyTokens(uint256 amount, address buyer)` | external | nonpayable | onlySWAP |
| `sellTokens(uint256 amount, address seller)` | external | nonpayable | onlySWAP |
| `openLeverage(uint256 newTokens, uint256 newUSDC, uint256 usdcToLP, address token, uint256 newFactoryReserveTokens, uint256 newFactoryTokens, address user)` | external | nonpayable | onlySWAP |
| `TakeLeverageFor(uint256 collateralAmount, address token, uint256 numberOfDays, uint256 borrowedAmount, uint256 fullAmount, address user, uint256 priceBefore, uint256 initialBuy)` | external | nonpayable | onlySWAP |
| `addCashedOut(uint256 loanId, bool isLeverage, uint256 amount, address user)` | external | nonpayable | onlySWAP |
| `PartialLoanSellFor(uint256 loanId, address user, uint256 percentage, bool isLeverage)` | external | nonpayable | onlySWAP |
| `TakeLoan(uint256 tokenAmount, address token, uint256 numberOfDays)` | external | nonpayable | LOAN only |
| `IncreaseLoan(uint256 loanId, uint256 amountToAdd)` | external | nonpayable | LOAN only |
| `ExtendLoan(uint256 loanId, uint256 numberOfDays, bool isLeverage, bool payInUSDC, bool refinance, bool isFree)` | external | nonpayable | LOAN or isLeverage |
| `RepayLoan(uint256 loanId, bool isLeverage)` | external | nonpayable | LOAN or isLeverage |
| `ClaimLiquidation(uint256 loanId, bool isLeverage)` | external | nonpayable | LOAN or isLeverage |
| `LiquidateLoan(uint256 loanId, address user, bool isLeverage)` | external | nonpayable | onlyAdmin |
| `InjectUSDC(uint256 amount)` | external | nonpayable | onlyAdmin |
| `setAdminStatus(bool status, address wallet)` | external | nonpayable | onlyCEO |
| `EnableTrading()` | external | nonpayable | onlyCEO |
| `transferOwnership(address newCEO)` | external | nonpayable | onlyCEO |
| `SetSwapWallet(address newSwap)` | external | nonpayable | onlyCEO |
| `SetLoanWallet(address newLoan)` | external | nonpayable | onlyCEO |
| `SetProjectVetted(bool status)` | external | nonpayable | onlyCEO |
| `setFactoryCA(address newFactory)` | external | nonpayable | onlyCEO |
| `SetMinimumLoan(uint256 newMinimum)` | external | nonpayable | onlyCEO |
| `SetLoanVariables(uint256 minDays, uint256 maxDays, uint256 minLoan)` | external | nonpayable | onlyCEO |
| `SetLoanFees(uint256 staticFee, uint256 dynamicFee)` | external | nonpayable | onlyCEO |
| `SetTaxesContract(address newTaxes)` | external | nonpayable | onlyCEO |
| `rescueAnyToken(IERC20 tokenToRescue)` | external | nonpayable | onlyCEO |
| `rescueEth()` | external | nonpayable | onlyCEO |

### Read Functions

| Function | Visibility | Mutability | Access |
|----------|-----------|-----------|--------|
| `balanceOf(address)` | external | view | open |
| `allowance(address, address)` | external | view | open |
| `getTokenPrice()` | public | view | open |
| `getUSDPrice()` | public | view | open |
| `getColleteralValue(uint256 tokenAmount, address token)` | public | view | open |
| `ExtensionEligibility(address user, uint256 loanId, uint256 numberOfDays, bool isLeverage, bool payInUSDC, bool refinance)` | external | view | open |
| `getLeverageCountForUserAndToken(address user, address token)` | external | view | open |
| `getDynamicFee(uint256 amount, uint256 numberOfDays)` | public | view | open |
| `getReserves()` | public | view | open |
| `calculateTokensForBuy(uint256 usdcAmount)` | public | view | open |
| `calculateTokensForSell(uint256 tokenAmount)` | public | view | open |
| `calculateUsdcForTokens(uint256 tokenAmountOut)` | public | view | open |
| `calculateTokensForUsdc(uint256 usdcAmountOut)` | public | view | open |
| `calculateTokensToBurn(uint256 amountIn, uint256 multiplier, uint256 inputreserve0, uint256 inputreserve1)` | public | pure | open |
| `getPartialLoanSellAmounts(uint256 loanId, address user, uint256 percentage, bool isLeverage)` | external | view | open |
| `getLiquidity()` | public | view | open |

### Public State Getters

`projectedVetted`, `hasBonded`, `autoVest`, `gradualAutoVesting`, `symbol`, `name`, `decimals`, `totalSupply`, `tradingEnabled`, `lastTrade`, `creationBlock`, `USDCMULTIPLIER`, `PRICEMULTIPLIER`, `hybridMultiplier`, `token0`, `token1`, `reserve0`, `reserve1`, `baseReserve1`, `minDaysLoan`, `maxDaysLoan`, `dynamicFeePercentage`, `staticFeePercentage`, `SWAP`, `LOAN`, `CEO`, `DEV`, `minimumLoan`, `loans(address,uint256)`, `leverages(address,uint256)`, `userTokenLeverageIds(address,address,uint256)`, `loanCount(address)`, `leverageCount(address)`, `isAdmin(address)`

---

## 3. FACTORYTOKEN

### Write Functions

| Function | Visibility | Mutability | Access |
|----------|-----------|-----------|--------|
| `transfer(address to, uint256 value)` | external | nonpayable | open |
| `approve(address spender, uint256 value)` | external | nonpayable | open |
| `transferFrom(address from, address to, uint256 amount)` | external | nonpayable | open |
| `buyBondingTokens(uint256 buyAmount, address buyer)` | external | nonpayable | onlySWAP |
| `sellBondingTokens(uint256 amount, address seller)` | external | nonpayable | onlySWAP |
| `buyTokens(uint256 amount, address buyer)` | external | nonpayable | onlySWAP |
| `sellTokens(uint256 amount, address seller)` | external | nonpayable | onlySWAP |
| `LiquidateLoan(uint256 tokensToBurn, uint256 mainToBurn, address user, bool isLeverage)` | external | nonpayable | onlyMAINTOKEN |
| `openLeverageFactory(uint256 newReserveTokens, uint256 newReserveStasis, uint256 newTokens, address user)` | external | nonpayable | onlyMAINTOKEN |
| `addToRewards(uint256 usdcAmount)` | external | nonpayable | open |
| `claimRewards()` | external | nonpayable | open |
| `DisableFreeze()` | external | nonpayable | onlyDEV |
| `SetWhitelistedWallet(address[] wallets, uint256 amount, string tag)` | external | nonpayable | onlyDEV |
| `RemoveWhitelist(address wallet)` | external | nonpayable | onlyDEV |
| `transferOwnership(address newCEO)` | external | nonpayable | onlyCEO |
| `SetSwapWallet(address newSwap)` | external | nonpayable | onlyCEO |
| `SetProjectVetted(bool status)` | external | nonpayable | onlyCEO |

### Read Functions

| Function | Visibility | Mutability | Access |
|----------|-----------|-----------|--------|
| `balanceOf(address)` | external | view | open |
| `allowance(address, address)` | external | view | open |
| `getTokenPrice()` | public | view | open |
| `getUSDPrice()` | public | view | open |
| `calculateFloor()` | public | view | open |
| `calculateTokenFloor()` | public | view | open |
| `calculateTokensForBuy(uint256)` | public | view | open |
| `calculateTokensForSell(uint256)` | public | view | open |
| `calculateMainForTokens(uint256)` | public | view | open |
| `calculateTokensForMain(uint256)` | public | view | open |
| `getClaimableRewards(address)` | public | view | open |
| `getReserves()` | public | view | open |
| `getBondingTarget()` | public | view | open |
| `getLiquidity()` | public | view | open |

### Public State Getters

`projectedVetted`, `symbol`, `name`, `decimals`, `totalSupply`, `lastTrade`, `hasBonded`, `frozen`, `autoVest`, `gradualAutoVesting`, `tokenClosed`, `token0`, `token1`, `baseReserve0`, `baseReserve1`, `creationBlock`, `creationTime`, `usdcForBondingNeeded`, `hybridMultiplier`, `SWAP`, `CEO`, `DEV`, `totalShares`, `totalRewardsPerShare`, `lastDistribution`, `autoVestDuration`, `totalWhitelisted`, `claimedRewards(address)`, `shares(address)`, `excluded(address)`, `whitelisted(address)`, `whitelistMaxBuyForUser(address)`, `whitelistBoughtByUser(address)`

---

## 4. ATokenFactory

### Write Functions

| Function | Visibility | Mutability | Access |
|----------|-----------|-----------|--------|
| `createToken(string symbol, string name, uint256 hybridMultiplier, bool frozen, uint256 usdcForBonding, uint256 startLP, bool autoVest, uint256 autoVestDuration, bool gradualAutovest)` | public | payable | open |
| `setEcosystemToken(bool status, address token)` | external | nonpayable | onlyCEO |
| `setFeeAmount(uint256 newFeeAmount)` | external | nonpayable | onlyCEO |
| `setFeeEnabled(bool enabled)` | external | nonpayable | onlyCEO |
| `setFeeWhitelist(address addr, bool whitelisted)` | external | nonpayable | onlyCEO |
| `togglePairToken(address token)` | external | nonpayable | onlyCEO |
| `setSWAP(address addr)` | external | nonpayable | onlyCEO |

### Read Functions

| Function | Visibility | Mutability | Access |
|----------|-----------|-----------|--------|
| `getTokensByCreator(address creator)` | public | view | open |
| `getTokenCountByCreator(address creator)` | public | view | open |

### Public State Getters

`creatorToTokens(address,uint256)`, `creatorOf(address)`, `isEcosystemToken(address)`, `creationCount`, `lastCreation`, `feeAmount`, `vestFeeEnabled`, `feeWhitelist(address)`, `isPairToken(address)`

---

## 5. ASwap (SWAP)

### Write Functions

| Function | Visibility | Mutability | Access |
|----------|-----------|-----------|--------|
| `buyTokens(uint256 amount, uint256 minOut, address[] path, bool wrapTokens)` | external | nonpayable | nonReentrant |
| `sellTokens(uint256 amount, uint256 minOut, address[] path, bool swapToETH)` | external | nonpayable | nonReentrant |
| `leverageBuy(uint256 _amount, uint256 minOut, address[] path, uint256 numberOfDays)` | external | nonpayable | nonReentrant |
| `mixedBuy(uint256 _amount, uint256 minOutLev, uint256 minOut, address[] path, uint256 numberOfDays, uint256 percentageLeverage)` | external | nonpayable | nonReentrant |
| `partialLoanSell(uint256 loanId, uint256 percentage, bool isLeverage, uint256 minOut)` | external | nonpayable | nonReentrant |
| `convertToNative(address marketToken, address inputToken, uint256 inputAmount)` | external | nonpayable | nonReentrant |
| `swapForStaking(uint256 amount)` | external | nonpayable | onlySTAKING |
| `sellAndDistributeStasis(uint256 amount, address originalToken)` | external | nonpayable | open |
| `setContracts(address newFactory, address newLeverage, address newVesting, address newMain, address newTaxes, address newStaking)` | external | nonpayable | onlyCEO |
| `rescueAnyToken(IERC20 tokenToRescue)` | external | nonpayable | onlyCEO |
| `rescueEth()` | external | nonpayable | onlyCEO |
| `receive()` | external | payable | open |

### Read Functions

| Function | Visibility | Mutability | Access |
|----------|-----------|-----------|--------|
| `getAmountsOut(uint256 amount, address[] path)` | public | view | open |

### Public State Getters

`lastTradeBlock`, `totalTaxDistributed`

---

## 6. ALOAN_HUB (LOANS)

### Write Functions

| Function | Visibility | Mutability | Access |
|----------|-----------|-----------|--------|
| `takeLoan(address ecosystem, address collateral, uint256 amount, uint256 daysCount)` | external | nonpayable | nonReentrant |
| `repayLoan(uint256 hubId)` | external | nonpayable | nonReentrant |
| `extendLoan(uint256 hubId, uint256 addDays, bool payInStable, bool refinance)` | external | nonpayable | nonReentrant |
| `increaseLoan(uint256 hubId, uint256 amountToAdd)` | external | nonpayable | nonReentrant |
| `claimLiquidation(uint256 hubId)` | external | nonpayable | nonReentrant |
| `hubPartialLoanSell(uint256 hubId, uint256 percentage, bool isLeverage, uint256 minOut)` | external | nonpayable | nonReentrant |
| `addEcosystem(address mainToken, address stable, address swapContract)` | external | nonpayable | onlyCEO |
| `setExtensionWhitelist(address wallet, bool status)` | external | nonpayable | onlyCEO |
| `toggleEcosystemStatus(address mainToken, bool status)` | external | nonpayable | onlyCEO |
| `rescueToken(IERC20 token)` | external | nonpayable | onlyCEO |

### Read Functions

| Function | Visibility | Mutability | Access |
|----------|-----------|-----------|--------|
| `getUserLoanDetails(address user, uint256 hubId)` | external | view | open |

### Public State Getters

`CEO`, `ecosystems(address)`, `isEcosystemRegistered(address)`, `userLoans(address,uint256)`, `userLoanCount(address)`, `extensionWhitelisted(address)`

---

## 7. AStasisVault (STAKING)

### Write Functions

| Function | Visibility | Mutability | Access |
|----------|-----------|-----------|--------|
| `buy(uint256 _amount)` | external | nonpayable | nonReentrant |
| `buyForUser(uint256 _amount, address user)` | external | nonpayable | nonReentrant, onlySWAP |
| `sell(uint256 _shares, bool _claimUSDC, uint256 _minUSDC)` | external | nonpayable | nonReentrant |
| `lock(uint256 _shares)` | external | nonpayable | nonReentrant |
| `unlock(uint256 _shares)` | external | nonpayable | nonReentrant |
| `borrow(uint256 _stasisAmountToBorrow, uint256 _days)` | external | nonpayable | nonReentrant |
| `repay()` | external | nonpayable | nonReentrant |
| `addToLoan(uint256 _additionalStasisToBorrow)` | external | nonpayable | nonReentrant |
| `extendLoan(uint256 _daysToAdd, bool _payInUSDC, bool _refinance)` | external | nonpayable | nonReentrant |
| `settleLiquidation()` | external | nonpayable | nonReentrant |
| `injectYield(uint256 _amount)` | external | nonpayable | onlyTAXES |
| `setMinBuy(uint256 _amount)` | external | nonpayable | onlyOwner |
| `setContracts(address newTaxes, address newSwap, address newLoan)` | external | nonpayable | onlyOwner |
| `rescueToken(IERC20 token)` | external | nonpayable | onlyOwner |

### Read Functions

| Function | Visibility | Mutability | Access |
|----------|-----------|-----------|--------|
| `totalAssets()` | public | view | open |
| `convertToShares(uint256 assets)` | public | view | open |
| `convertToAssets(uint256 shares)` | public | view | open |
| `getAvailableStasis(address user)` | public | view | open |
| `getUserStakeDetails(address user)` | external | view | open |

### Public State Getters

`stasisToken`, `loanHub`, `TAXES`, `SWAP`, `totalStasisAvailable`, `totalStasisPledged`, `minBuyAmount`, `userVaults(address)`

*Inherited ERC20: `name`, `symbol`, `decimals`, `totalSupply`, `balanceOf`, `transfer`, `allowance`, `approve`, `transferFrom`*

---

## 8. ATaxes (TAXES)

### Write Functions

| Function | Visibility | Mutability | Access |
|----------|-----------|-----------|--------|
| `distributeTax(uint256 usdcAmount, IERC20 originalToken)` | external | nonpayable | open |
| `startSurgeTax(uint256 startRate, uint256 endRate, uint256 duration, address token)` | external | nonpayable | token DEV only |
| `endSurgeTax(address token)` | external | nonpayable | token DEV only |
| `addDevShare(IERC20 token, address wallet, uint256 basisPoints)` | external | nonpayable | token DEV only |
| `removeDevShare(IERC20 token, address wallet)` | external | nonpayable | token DEV only |
| `setPrediction(address prediction)` | external | nonpayable | onlyCEO |
| `setWhitelistStatus(address user, bool value)` | external | nonpayable | onlyCEO |
| `setMain(address _mainToken)` | external | nonpayable | onlyCEO |
| `setStaking(address _staking)` | external | nonpayable | onlyCEO |
| `setTaxRates(uint256 buyback, uint256 presalers, uint256 dev)` | external | nonpayable | onlyCEO |
| `setTaxesStable(uint256 newTaxRate)` | external | nonpayable | onlyCEO |
| `setTaxesDefault(uint256 newTaxRate)` | external | nonpayable | onlyCEO |
| `setTaxesStasis(uint256 newTaxRate)` | external | nonpayable | onlyCEO |

### Read Functions

| Function | Visibility | Mutability | Access |
|----------|-----------|-----------|--------|
| `getTaxRate(IERC20 token, address user)` | public | view | open |
| `getCurrentSurgeTax(address token)` | public | view | open |
| `availableSurgeQuota(address token)` | public | view | open |

### Public State Getters

`CEO`, `_taxRateStasis`, `_taxRateStable`, `_taxRateDefault`, `_taxRatePrediction`, `injectRate`, `devRate`, `presaleRate`, `devBasisPoints(address,address)`, `devWallets(address,uint256)`, `devTotalAllocated(address)`, `isWhitelisted(address)`, `isPrediction(address)`, `totalDevTaxCollected(address)`, `devTotalEarnings(address)`, `tokenDevEarnings(address,address)`, `surgeHistory(address,uint256)`, `surgeStartTime(address)`, `surgeDuration(address)`, `surgeStartRate(address)`, `surgeEndRate(address)`, `isSurgeActive(address)`

---

## 9. ALEVERAGE (LEVERAGE)

### Read Functions (all open, no write functions for users)

| Function | Visibility | Mutability | Access |
|----------|-----------|-----------|--------|
| `simulateLeverage(uint256 _amount, address[] path, uint256 numberOfDays)` | public | view | open |
| `simulateLeverageFactory(uint256 _amount, address[] path, uint256 numberOfDays)` | public | view | open |
| `calculateTokensForBuy(uint256 usdcAmount, uint256 reserve0, uint256 reserve1)` | public | pure | open |
| `calculateFloor(uint256 hybridMultiplier, uint256 reserve0, uint256 reserve1, uint256 baseReserve0, uint256 xereserve0, uint256 xereserve1)` | public | view | open |
| `calculateFloor2(uint256 hybridMultiplier, uint256 reserve0, uint256 reserve1, uint256 baseReserve0, uint256 xereserve0, uint256 xereserve1)` | public | view | open |
| `getTokenPrice(uint256 reserve0, uint256 reserve1)` | public | view | open |
| `getUSDPrice(uint256 reserve0, uint256 reserve1, uint256 xereserve0, uint256 xereserve1)` | public | view | open |
| `getColleteralValue(uint256 tokenAmount, uint256 reserve0, uint256 reserve1)` | public | view | open |
| `getColleteralValueHybrid(uint256 tokenAmount, uint256 reserve0, uint256 reserve1, uint256 xereserve0, uint256 xereserve1, uint256 multiplier, uint256 basereserve0)` | public | view | open |
| `simulateDex(uint256 amount, address[] path, uint256 reserve0, uint256 reserve1)` | public | view | open |
| `simulateDexFactory(uint256 amount, uint256 reserve0, uint256 reserve1, uint256 multiplier)` | public | pure | open |
| `simulateLoan(uint256 boughtTokens, uint256 reserve0, uint256 reserve1, uint256 numberOfDays)` | public | view | open |
| `simulateLoanHybrid(uint256 boughtTokens, uint256 reserve0, uint256 reserve1, uint256 xereserve0, uint256 xereserve1, uint256 multiplier, uint256 basereserve0, uint256 numberOfDays)` | public | view | open |
| `calculateTokensToBurn(uint256 amountIn, uint256 multiplier, uint256 inputreserve0, uint256 inputreserve1, uint256 splitter)` | public | pure | open |

### Admin Functions

| Function | Visibility | Mutability | Access |
|----------|-----------|-----------|--------|
| `SetTaxWallet(address newTaxes)` | external | nonpayable | onlyCEO |
| `setMainToken(address addr)` | external | nonpayable | onlyCEO |
| `rescueAnyToken(IERC20 tokenToRescue)` | external | nonpayable | onlyCEO |
| `rescueEth()` | external | nonpayable | onlyCEO |

### Public State Getters

`PRICEMULTIPLIER`, `USDCMULTIPLIER`

---

## 10. A_VestingContract (VESTING)

### Write Functions

| Function | Visibility | Mutability | Access |
|----------|-----------|-----------|--------|
| `createGradualVesting(address beneficiary, address token, uint256 totalAmount, uint256 startTime, uint256 durationInDays, TimeUnit timeUnit, string memo, address ecosystem)` | public | payable | open |
| `createCliffVesting(address beneficiary, address token, uint256 totalAmount, uint256 unlockTime, string memo, address ecosystem)` | public | payable | open |
| `batchCreateGradualVesting(address[] beneficiaries, address token, uint256[] totalAmounts, string[] userMemos, uint256 startTime, uint256 durationInDays, TimeUnit timeUnit, address ecosystem)` | external | payable | open |
| `batchCreateCliffVesting(address[] beneficiaries, address token, uint256[] totalAmounts, uint256 unlockTime, string[] userMemos, address ecosystem)` | external | payable | open |
| `claimTokens(uint256 vestingId)` | external | nonpayable | nonReentrant, beneficiary only |
| `takeLoanOnVesting(uint256 vestingId)` | external | nonpayable | beneficiary only |
| `repayLoanOnVesting(uint256 vestingId)` | external | nonpayable | beneficiary only |
| `changeBeneficiary(uint256 vestingId, address newBeneficiary)` | external | nonpayable | creator only |
| `extendVestingPeriod(uint256 vestingId, uint256 additionalDays)` | external | nonpayable | creator or beneficiary |
| `addTokensToVesting(uint256 vestingId, uint256 additionalAmount)` | external | nonpayable | creator only |
| `transferCreatorRole(uint256 vestingId, address newCreator)` | external | nonpayable | creator only |
| `addEcosystem(address maintoken, address factory)` | external | nonpayable | onlyCEO |
| `setEcosystem(address maintoken, address factory)` | external | nonpayable | onlyCEO |
| `setLoanBuffer(uint256 newBuffer)` | external | nonpayable | onlyCEO |
| `setFeeAmount(uint256 newFeeAmount)` | external | nonpayable | onlyCEO |
| `setFeeEnabled(bool enabled)` | external | nonpayable | onlyCEO |
| `setFeeWhitelist(address addr, bool whitelisted)` | external | nonpayable | onlyCEO |
| `setNewLoan(address newLoan)` | external | nonpayable | onlyCEO |
| `rescueAnyToken(IERC20 tokenToRescue)` | external | nonpayable | onlyCEO |
| `rescueEth()` | external | nonpayable | onlyCEO |

### Read Functions

| Function | Visibility | Mutability | Access |
|----------|-----------|-----------|--------|
| `getVestedAmount(uint256 vestingId)` | public | view | open |
| `getClaimableAmount(uint256 vestingId)` | public | view | open |
| `getTokenVestingIds(address token, uint256 startIndex, uint256 endIndex)` | external | view | open |
| `getVestingDetailsBatch(uint256[] vestingIds)` | external | view | open |
| `getActiveLoan(uint256 vestingId)` | external | view | open |
| `getVestingsByCreator(address creator)` | external | view | open |
| `getVestingsByBeneficiary(address beneficiary)` | external | view | open |
| `getVestingDetails(uint256 vestingId)` | external | view | open |

### Public State Getters

`vestingSchedules(uint256)`, `creatorVestings(address,uint256)`, `beneficiaryVestings(address,uint256)`, `tokenVestings(address,uint256)`, `creatorCount(address)`, `beneficiaryCount(address)`, `tokenVestingCount(address)`, `ecosystems(address)`, `vestingCount`, `LOAN`, `loanBuffer`, `MIN_VESTING_DURATION`, `MAX_VESTING_DURATION`, `feeAmount`, `feeEnabled`, `feeWhitelist(address)`

---

## 11. AMarketTrading (Public Prediction Markets)

### Write Functions

| Function | Visibility | Mutability | Access |
|----------|-----------|-----------|--------|
| `createMarket(string marketName, string symbol, uint256 endTime, string[] _optionNames, address maintoken, bool frozen, uint256 bonding, uint256 seedAmount)` | external | payable | open |
| `buy(address marketToken, uint8 outcomeId, address inputToken, uint256 inputAmount, uint256 minUsdc, uint256 minShares)` | public | nonpayable | nonReentrant |
| `redeem(address marketToken)` | external | nonpayable | nonReentrant |
| `listOrder(address marketToken, uint8 outcomeId, uint256 amount, uint256 pricePerShare)` | external | nonpayable | nonReentrant |
| `cancelOrder(address marketToken, uint256 orderId)` | external | nonpayable | open |
| `buyOrder(address marketToken, uint256 orderId, uint256 fill)` | public | nonpayable | nonReentrant |
| `buyMultipleOrders(address marketToken, uint256[] orderIds, uint256 usdcAmount)` | public | nonpayable | open |
| `buyOrdersAndContract(address marketToken, uint8 outcomeId, uint256[] orderIds, address inputToken, uint256 totalInput, uint256 minShares)` | external | nonpayable | open |
| `DisableFreeze(address marketToken)` | external | nonpayable | creator only |
| `SetWhitelistedWallet(address[] wallets, uint256 amount, string tag, address marketToken)` | external | nonpayable | creator only |
| `RemoveWhitelist(address wallet, address marketToken)` | external | nonpayable | creator only |
| `setResolved(address marketToken, uint8 outcome)` | external | nonpayable | onlyResolver |
| `drainBountyPool(address marketToken)` | external | nonpayable | onlyResolver |
| `donate(address marketToken, uint256 amount, bool isBounty)` | external | nonpayable | onlyTaxes |
| `setInsuranceWallet(address newWallet)` | external | nonpayable | onlyCEO |
| `setPredictionResolver(address _resolver)` | external | nonpayable | onlyCEO |
| `setMinSeed(uint256 _minSeed)` | external | nonpayable | onlyCEO |
| `setPoolConfig(uint256 minPool, uint256 maxPool, uint256 floor, uint256 maxOutcomes)` | external | nonpayable | onlyCEO |
| `addEcosystem(address maintoken, address factory, address swap, address usdc)` | external | nonpayable | onlyCEO |
| `rescueToken(IERC20 token)` | external | nonpayable | onlyCEO |
| `receive()` | external | payable | open |

### Read Functions

| Function | Visibility | Mutability | Access |
|----------|-----------|-----------|--------|
| `getInitialReserves(uint256 n)` | public | view | open |
| `getBuyOrderCost(address marketToken, uint256 orderId, uint256 fill)` | public | view | open |
| `getBuyOrderAmountsOut(address marketToken, uint256 orderId, uint256 usdcAmount)` | public | view | open |
| `getMarketData(address marketToken)` | external | view | open |
| `getNumOutcomes(address marketToken)` | external | view | open |
| `getOutcome(address marketToken, uint8 outcomeId)` | external | view | open |
| `getOptionNames(address marketToken)` | external | view | open |
| `getUserShares(address marketToken, address user, uint8 outcomeId)` | external | view | open |
| `hasBettedOnMarket(address marketToken, address user)` | external | view | open |
| `getBountyPool(address marketToken)` | external | view | open |
| `getGeneralPot(address marketToken)` | external | view | open |

### Public State Getters

`CEO`, `TAXES`, `insuranceWallet`, `resolver`, `ONE_USD`, `minSeed`, `MIN_TOTAL_POOL`, `MAX_TOTAL_POOL`, `FLOOR_PER_OUTCOME`, `MAX_OUTCOMES`, `OUTCOME_EARLY`, `OUTCOME_INVALID`, `OUTCOME_UNRESOLVED`, `lastTrade`, `ecosystems(address)`, `marketData(address)`, `optionNames(address,uint256)`, `outcomes(address,uint256)`, `bountyPool(address)`, `hasBetted(address,address)`, `userShares(address,address,uint8)`, `nextOrderId(address)`, `marketOrders(address,uint256)`, `sharesLockedInOrders(address,address,uint8)`

---

## 12. AMarketResolver

### Write Functions

| Function | Visibility | Mutability | Access |
|----------|-----------|-----------|--------|
| `proposeOutcome(address marketToken, uint8 outcomeId)` | external | nonpayable | nonReentrant |
| `dispute(address marketToken, uint8 newOutcomeId)` | external | nonpayable | nonReentrant |
| `vote(address marketToken, uint8 outcomeId)` | external | nonpayable | nonReentrant |
| `finalizeUncontested(address marketToken)` | external | nonpayable | nonReentrant |
| `finalizeMarket(address marketToken)` | external | nonpayable | nonReentrant |
| `veto(address marketToken, uint8 proposedOutcome)` | external | nonpayable | nonReentrant |
| `stake(address token)` | external | nonpayable | nonReentrant |
| `unstake(address token)` | external | nonpayable | nonReentrant |
| `claimBounty(address marketToken)` | external | nonpayable | nonReentrant |
| `claimEarlyBounty(address marketToken, uint256 round)` | external | nonpayable | nonReentrant |
| `resolveByBasis(address marketToken, uint8 outcomeId)` | external | nonpayable | onlyCEO |
| `setPredictionTrader(address trader)` | external | nonpayable | onlyCEO |
| `toggleVoterWallet(address wallet)` | external | nonpayable | onlyCEO |
| `configResolver(uint256 dp, uint256 pp, uint256 vp, uint256 pb, uint256 mq, uint256 maxq, uint256 vc)` | external | nonpayable | onlyCEO |
| `rescueToken(IERC20 token)` | external | nonpayable | onlyCEO |

### Read Functions

| Function | Visibility | Mutability | Access |
|----------|-----------|-----------|--------|
| `resolved(address marketToken)` | external | view | open |
| `finalOutcome(address marketToken)` | external | view | open |

### Public State Getters

`CEO`, `trading`, `DISPUTE_PERIOD`, `PROPOSAL_PERIOD`, `VETO_PERIOD`, `PROPOSAL_BOND`, `MIN_QUORUM`, `MAX_QUORUM`, `VOTING_CONSENSUS`, `ONE_USD`, `OUTCOME_EARLY`, `OUTCOME_INVALID`, `OUTCOME_UNRESOLVED`, `disputes(address)`, `inDispute(address)`, `inVeto(address)`, `currentRound(address)`, `nftVoteCount(address,uint256,uint8)`, `nftHasVoted(address,uint256,address)`, `voterChoice(address,uint256,address)`, `bountyPerCorrectVote(address)`, `bountyPerCorrectEarlyVoteForRound(address,uint256)`, `bountyClaimed(address,address)`, `bountyEarlyClaimed(address,uint256,address)`, `userStakedAmount(address)`, `isVoter(address)`, `MIN_STAKE_AMOUNT`, `VOTE_LOCK_DURATION`, `lastVoteTime(address)`

---

## 13. APrivateTradingMarket (Private Prediction Markets)

### Write Functions

| Function | Visibility | Mutability | Access |
|----------|-----------|-----------|--------|
| `createMarket(string marketName, string symbol, uint256 endTime, string[] _optionNames, address maintoken, bool privateEvent, bool frozen, uint256 bonding, uint256 seedAmount)` | external | payable | open |
| `buy(address marketToken, uint8 outcomeId, address inputToken, uint256 inputAmount, uint256 minUsdc, uint256 minShares)` | public | nonpayable | nonReentrant |
| `redeem(address marketToken)` | external | nonpayable | nonReentrant |
| `listOrder(address marketToken, uint8 outcomeId, uint256 amount, uint256 pricePerShare)` | external | nonpayable | nonReentrant |
| `cancelOrder(address marketToken, uint256 orderId)` | external | nonpayable | open |
| `buyOrder(address marketToken, uint256 orderId, uint256 fill)` | public | nonpayable | nonReentrant |
| `buyMultipleOrders(address marketToken, uint256[] orderIds, uint256 usdcAmount)` | public | nonpayable | open |
| `buyOrdersAndContract(address marketToken, uint8 outcomeId, uint256[] orderIds, address inputToken, uint256 totalInput, uint256 minShares)` | external | nonpayable | open |
| `vote(address marketToken, uint8 outcomeId)` | external | nonpayable | nonReentrant, voter or CEO |
| `finalize(address marketToken)` | external | nonpayable | nonReentrant |
| `claimBounty(address marketToken)` | external | nonpayable | nonReentrant |
| `manageVoter(address marketToken, address voter, bool status)` | external | nonpayable | creator only |
| `togglePrivateEventBuyers(address marketToken, address[] buyers, bool status)` | external | nonpayable | creator only |
| `DisableFreeze(address marketToken)` | external | nonpayable | creator only |
| `manageWhitelist(address marketToken, address[] wallets, uint256 amount, string tag, bool status)` | external | nonpayable | creator only |
| `donate(address marketToken, uint256 amount, bool isBounty)` | external | nonpayable | onlyTaxes |
| `addEcosystem(address maintoken, address factory, address swap, address usdc)` | external | nonpayable | onlyCEO |
| `setMinSeed(uint256 _minSeedPublic, uint256 _minSeedPrivate)` | external | nonpayable | onlyCEO |
| `setPoolConfig(uint256 minPool, uint256 maxPool, uint256 floor, uint256 maxOutcomes)` | external | nonpayable | onlyCEO |
| `setInsuranceWallet(address newWallet)` | external | nonpayable | onlyCEO |
| `rescueToken(IERC20 token)` | external | nonpayable | onlyCEO |
| `receive()` | external | payable | open |

### Read Functions

| Function | Visibility | Mutability | Access |
|----------|-----------|-----------|--------|
| `getInitialReserves(uint256 n)` | public | view | open |
| `getBuyOrderCost(address marketToken, uint256 orderId, uint256 fill)` | public | view | open |
| `getBuyOrderAmountsOut(address marketToken, uint256 orderId, uint256 usdcAmount)` | public | view | open |
| `getMarketData(address marketToken)` | external | view | open |
| `getNumOutcomes(address marketToken)` | external | view | open |

### Public State Getters

`CEO`, `TAXES`, `insuranceWallet`, `ONE_USD`, `VOTING_WINDOW`, `minSeedPublic`, `minSeedPrivate`, `MIN_TOTAL_POOL`, `MAX_TOTAL_POOL`, `FLOOR_PER_OUTCOME`, `MAX_OUTCOMES`, `OUTCOME_INVALID`, `OUTCOME_UNRESOLVED`, `lastTrade`, `ecosystems(address)`, `marketData(address)`, `firstVoteTime(address)`, `optionNames(address,uint256)`, `outcomes(address,uint256)`, `bountyPool(address)`, `hasBetted(address,address)`, `userShares(address,address,uint8)`, `nextOrderId(address)`, `marketOrders(address,uint256)`, `sharesLockedInOrders(address,address,uint8)`, `marketVoters(address,uint256)`, `userCanBuyEvent(address,address)`, `isMarketVoter(address,address)`, `voterChoice(address,address)`, `bountyPerCorrectVote(address)`, `bountyClaimed(address,address)`

---

## 14. AMarketReader

| Function | Visibility | Mutability | Access |
|----------|-----------|-----------|--------|
| `getAllOutcomes(address routerAddress, address marketToken)` | external | view | open |
| `estimateSharesOut(address routerAddress, address marketToken, uint8 outcomeId, uint256 usdcAmount, uint256[] orderIds, address user)` | external | view | open |
| `getPotentialPayout(address routerAddress, address marketToken, uint8 outcomeId, uint256 sharesAmount, uint256 estimatedUsdcToPool)` | external | view | open |
