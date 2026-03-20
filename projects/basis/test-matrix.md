# Basis SDK Test Matrix

Cross-referenced from `contract-functions-master.md` and `sdk-docs-2026-03-20.md`.
Generated 2026-03-20.

Legend:
- ✅ = Covered in Alex's 18-step script
- 🔲 = In SDK, not yet tested
- ⚠️ = In contract but NOT in SDK (gap)
- 🔒 = Admin/CEO only (not testable from user wallet)
- ❌ = Internal only (onlySWAP, onlyMAINTOKEN, etc.)

---

## Tier 1 — Core Happy Paths (Alex's 18-step + gaps)

These are single-wallet, straightforward operations.

| # | Module | Function | Contract Source | Status | Notes |
|---|--------|----------|----------------|--------|-------|
| 1 | Factory | `createTokenWithMetadata()` | ATokenFactory.createToken + API | ✅ | On-chain + IPFS |
| 2 | Trading | `buy()` | ASwap.buyTokens | ✅ | Auto path building |
| 3 | Trading | `sell()` | ASwap.sellTokens | ✅ | With block delay |
| 4 | Trading | `sellPercentage()` | ASwap.sellTokens | 🔲 | Reads balance, sells % |
| 5 | Trading | `buyTokens()` (raw) | ASwap.buyTokens | 🔲 | Explicit path |
| 6 | Trading | `sellTokens()` (raw) | ASwap.sellTokens | 🔲 | Explicit path |
| 7 | Trading | `convertToNative()` | ASwap.convertToNative | 🔲 | Any token → USDB |
| 8 | Trading | `leverageBuy()` | ASwap.leverageBuy | ✅ | |
| 9 | Trading | `partialLoanSell()` | ASwap.partialLoanSell | ✅ | With block delay |
| 10 | Loans | `takeLoan()` | ALOAN_HUB.takeLoan | ✅ | |
| 11 | Loans | `extendLoan()` | ALOAN_HUB.extendLoan | ✅ | |
| 12 | Loans | `repayLoan()` | ALOAN_HUB.repayLoan | ✅ | |
| 13 | Loans | `increaseLoan()` | ALOAN_HUB.increaseLoan | 🔲 | Add collateral to existing |
| 14 | Loans | `claimLiquidation()` | ALOAN_HUB.claimLiquidation | 🔲 | Hard — needs liquidated loan |
| 15 | Staking | `buy()` (wrap) | AStasisVault.buy | ✅ | STASIS → wSTASIS |
| 16 | Staking | `sell()` (unwrap) | AStasisVault.sell | 🔲 | wSTASIS → STASIS |
| 17 | Staking | `lock()` | AStasisVault.lock | ✅ | |
| 18 | Staking | `unlock()` | AStasisVault.unlock | 🔲 | Release collateral |
| 19 | Staking | `borrow()` | AStasisVault.borrow | ✅ | |
| 20 | Staking | `repay()` | AStasisVault.repay | 🔲 | Repay staking loan |
| 21 | Staking | `addToLoan()` | AStasisVault.addToLoan | 🔲 | Increase collateral |
| 22 | Staking | `extendLoan()` | AStasisVault.extendLoan | 🔲 | Extend staking loan |
| 23 | Staking | `settleLiquidation()` | AStasisVault.settleLiquidation | 🔲 | Hard — needs liquidation |
| 24 | Vesting | `createGradualVesting()` | A_VestingContract.createGradualVesting | ✅ | |
| 25 | Vesting | `createCliffVesting()` | A_VestingContract.createCliffVesting | 🔲 | |
| 26 | Vesting | `claimTokens()` | A_VestingContract.claimTokens | ✅ | Needs wait for unlock |
| 27 | Vesting | `takeLoanOnVesting()` | A_VestingContract.takeLoanOnVesting | ✅ | |
| 28 | Vesting | `repayLoanOnVesting()` | A_VestingContract.repayLoanOnVesting | ✅ | |
| 29 | Vesting | `changeBeneficiary()` | A_VestingContract.changeBeneficiary | 🔲 | Creator only |
| 30 | Vesting | `extendVestingPeriod()` | A_VestingContract.extendVestingPeriod | 🔲 | Creator or beneficiary |
| 31 | Vesting | `addTokensToVesting()` | A_VestingContract.addTokensToVesting | 🔲 | Creator only |
| 32 | Vesting | `transferCreatorRole()` | A_VestingContract.transferCreatorRole | 🔲 | |
| 33 | Vesting | `batchCreateGradualVesting()` | A_VestingContract.batchCreateGradualVesting | 🔲 | Multi-beneficiary |
| 34 | Vesting | `batchCreateCliffVesting()` | A_VestingContract.batchCreateCliffVesting | 🔲 | Multi-beneficiary |
| 35 | Prediction | `createMarketWithMetadata()` | AMarketTrading.createMarket + API | ✅ | |
| 36 | Prediction | `buy()` | AMarketTrading.buy | ✅ | |
| 37 | Prediction | `redeem()` | AMarketTrading.redeem | 🔲 | Needs resolved market |
| 38 | Prediction | `buyOrdersAndContract()` | AMarketTrading.buyOrdersAndContract | 🔲 | Hybrid AMM + book |
| 39 | Order Book | `listOrder()` | AMarketTrading.listOrder | ✅ | + auto-sync |
| 40 | Order Book | `cancelOrder()` | AMarketTrading.cancelOrder | 🔲 | |
| 41 | Order Book | `buyOrder()` | AMarketTrading.buyOrder | 🔲 | Fill single order |
| 42 | Order Book | `buyMultipleOrders()` | AMarketTrading.buyMultipleOrders | 🔲 | Fill multiple |
| 43 | Agent | `register()` | ERC-8004 | 🔲 | |
| 44 | Agent | `registerAndSync()` | ERC-8004 + API | 🔲 | + backend sync |
| 45 | Agent | `setAgentURI()` | ERC-8004 | 🔲 | Update metadata |

---

## Tier 2 — Frozen Token & Whitelist Flows

Requires creating a token with `frozen: true`.

| # | Module | Function | Contract Source | Status | Notes |
|---|--------|----------|----------------|--------|-------|
| 46 | Factory | `createTokenWithMetadata({frozen: true})` | ATokenFactory.createToken | 🔲 | |
| 47 | Factory | `setWhitelistedWallet()` | FACTORYTOKEN.SetWhitelistedWallet | 🔲 | Dev only |
| 48 | Factory | `removeWhitelist()` | FACTORYTOKEN.RemoveWhitelist | 🔲 | Dev only |
| 49 | Factory | `disableFreeze()` | FACTORYTOKEN.DisableFreeze | 🔲 | Dev only |

**Test scenario**: Create frozen token → whitelist test wallet → buy within limit → remove whitelist → verify blocked → disable freeze → buy freely.

---

## Tier 3 — Market Resolver (Multi-step, ideally multi-wallet)

Full dispute lifecycle on a public prediction market.

| # | Module | Function | Contract Source | Status | Notes |
|---|--------|----------|----------------|--------|-------|
| 50 | Resolver | `proposeOutcome()` | AMarketResolver.proposeOutcome | 🔲 | Bond required |
| 51 | Resolver | `dispute()` | AMarketResolver.dispute | 🔲 | Counter-propose |
| 52 | Resolver | `vote()` | AMarketResolver.vote | 🔲 | Requires staked voter |
| 53 | Resolver | `stake()` | AMarketResolver.stake | 🔲 | Must stake to vote |
| 54 | Resolver | `unstake()` | AMarketResolver.unstake | 🔲 | After vote lock |
| 55 | Resolver | `finalizeUncontested()` | AMarketResolver.finalizeUncontested | 🔲 | No dispute within period |
| 56 | Resolver | `finalizeMarket()` | AMarketResolver.finalizeMarket | 🔲 | After dispute resolved |
| 57 | Resolver | `veto()` | AMarketResolver.veto | 🔲 | Elevated privileges |
| 58 | Resolver | `claimBounty()` | AMarketResolver.claimBounty | 🔲 | After finalization |
| 59 | Resolver | `claimEarlyBounty()` | AMarketResolver.claimEarlyBounty | 🔲 | Per-round bounty |

**Scenario A (happy path)**: Create market → wait for end → proposeOutcome → wait dispute period → finalizeUncontested → redeem.
**Scenario B (dispute)**: Create market → proposeOutcome → dispute → stake → vote → finalizeMarket → claimBounty.

---

## Tier 4 — Private Markets

| # | Module | Function | Contract Source | Status | Notes |
|---|--------|----------|----------------|--------|-------|
| 60 | Private | `createMarket()` (via SDK) | APrivateTradingMarket.createMarket | 🔲 | `privateEvent: true` |
| 61 | Private | `buy()` | APrivateTradingMarket.buy | 🔲 | |
| 62 | Private | `redeem()` | APrivateTradingMarket.redeem | 🔲 | |
| 63 | Private | `vote()` | APrivateTradingMarket.vote | 🔲 | Voter or CEO |
| 64 | Private | `finalize()` | APrivateTradingMarket.finalize | 🔲 | |
| 65 | Private | `claimBounty()` | APrivateTradingMarket.claimBounty | 🔲 | |
| 66 | Private | `manageVoter()` | APrivateTradingMarket.manageVoter | 🔲 | Creator only |
| 67 | Private | `togglePrivateEventBuyers()` | APrivateTradingMarket.togglePrivateEventBuyers | 🔲 | |
| 68 | Private | `disableFreeze()` | APrivateTradingMarket.DisableFreeze | 🔲 | |
| 69 | Private | `manageWhitelist()` | APrivateTradingMarket.manageWhitelist | 🔲 | |
| 70 | Private | Order book (list/cancel/buy/buyMultiple/hybrid) | Same as public | 🔲 | With `marketType: "private"` |

---

## Tier 5 — Read Methods (verify all return sane data)

| # | Module | Function | Status |
|---|--------|----------|--------|
| 71 | Trading | `getAmountsOut()` | 🔲 |
| 72 | Trading | `getTokenPrice()` | 🔲 |
| 73 | Trading | `getUSDPrice()` | 🔲 |
| 74 | Trading | `getLeverageCount()` | 🔲 |
| 75 | Trading | `getLeveragePosition()` | 🔲 |
| 76 | Factory | `getTokenState()` | 🔲 |
| 77 | Factory | `isEcosystemToken()` | 🔲 |
| 78 | Factory | `getTokensByCreator()` | 🔲 |
| 79 | Factory | `getFeeAmount()` | 🔲 |
| 80 | Loans | `getUserLoanDetails()` | 🔲 |
| 81 | Loans | `getUserLoanCount()` | 🔲 |
| 82 | Staking | `getAvailableStasis()` | 🔲 |
| 83 | Staking | `convertToShares()` | 🔲 |
| 84 | Staking | `convertToAssets()` | 🔲 |
| 85 | Vesting | `getVestingDetails()` | 🔲 |
| 86 | Vesting | `getClaimableAmount()` | 🔲 |
| 87 | Vesting | `getVestingsByBeneficiary()` | 🔲 |
| 88 | Vesting | `getVestingsByCreator()` | 🔲 |
| 89 | Prediction | `getMarketData()` | 🔲 |
| 90 | Prediction | `getOutcome()` | 🔲 |
| 91 | Prediction | `getUserShares()` | 🔲 |
| 92 | Prediction | `getInitialReserves()` | 🔲 |
| 93 | Order Book | `getBuyOrderCost()` | 🔲 |
| 94 | Resolver | `isResolved()` | 🔲 |
| 95 | Resolver | `getFinalOutcome()` | 🔲 |
| 96 | Resolver | `isInDispute()` | 🔲 |
| 97 | Resolver | `isInVeto()` | 🔲 |
| 98 | Resolver | `getCurrentRound()` | 🔲 |
| 99 | Resolver | `getDisputeData()` | 🔲 |
| 100 | Resolver | `getUserStake()` | 🔲 |
| 101 | Resolver | reads (isVoter, getVoteCount, hasVoted, etc.) | 🔲 |
| 102 | Market Reader | `getAllOutcomes()` | 🔲 |
| 103 | Market Reader | `estimateSharesOut()` | 🔲 |
| 104 | Market Reader | `getPotentialPayout()` | 🔲 |
| 105 | Leverage Sim | `simulateLeverage()` | 🔲 |
| 106 | Leverage Sim | `simulateLeverageFactory()` | 🔲 |
| 107 | Taxes | `getTaxRate()` | 🔲 |
| 108 | Taxes | `getCurrentSurgeTax()` | 🔲 |
| 109 | Taxes | `getAvailableSurgeQuota()` | 🔲 |
| 110 | Taxes | `getBaseTaxRates()` | 🔲 |
| 111 | Agent | `isRegistered()` | 🔲 |
| 112 | Agent | `lookupFromApi()` | 🔲 |
| 113 | Agent | `listAgents()` | 🔲 |
| 114 | Agent | `getAgentURI()` | 🔲 |
| 115 | Agent | `getAgentWallet()` | 🔲 |

---

## Tier 6 — Off-Chain API

| # | Module | Function | Status |
|---|--------|----------|--------|
| 116 | API | `createApiKey()` | 🔲 |
| 117 | API | `listApiKeys()` | 🔲 |
| 118 | API | `deleteApiKey()` | 🔲 |
| 119 | API | `uploadImage()` | 🔲 |
| 120 | API | `uploadImageFromUrl()` | 🔲 |
| 121 | API | `updateMetadata()` | 🔲 |
| 122 | API | `updateProject()` | 🔲 |
| 123 | API | `createComment()` | 🔲 |
| 124 | API | `deleteComment()` | 🔲 |
| 125 | API | `syncOrder()` | 🔲 |
| 126 | API | `requestTwitterChallenge()` | 🔲 |
| 127 | API | `verifyTwitter()` | 🔲 |
| 128 | API | `getTokens()` | 🔲 |
| 129 | API | `getToken()` | 🔲 |
| 130 | API | `getCandles()` | 🔲 |
| 131 | API | `getTrades()` | 🔲 |
| 132 | API | `getOrders()` | 🔲 |
| 133 | API | `getTokenComments()` | 🔲 |
| 134 | API | `getWhitelist()` | 🔲 |
| 135 | API | `getWalletTransactions()` | 🔲 |
| 136 | API | `getMarketLiquidity()` | 🔲 |

---

## Contract Functions NOT in SDK (potential gaps or intentional omissions)

| Contract | Function | Reason |
|----------|----------|--------|
| ASwap | `mixedBuy()` | Leverage + spot combo — not exposed in SDK |
| ASwap | `sellAndDistributeStasis()` | Tax distribution utility |
| ALOAN_HUB | `hubPartialLoanSell()` | Partial sell via hub (SDK uses ASwap.partialLoanSell instead) |
| FACTORYTOKEN | `addToRewards()` / `claimRewards()` | Token reward distribution — not in SDK |
| A_STASISTOKEN | Direct loan/leverage functions | SDK routes through SWAP/LOAN_HUB instead |
| AStasisVault | `buyForUser()` | onlySWAP — internal |
| ATaxes | `startSurgeTax()` / `endSurgeTax()` | Token DEV only |
| ATaxes | `addDevShare()` / `removeDevShare()` | Token DEV only |
| AMarketResolver | `resolveByBasis()` | CEO only — emergency resolve |

---

## Summary

| Category | Total | Covered (✅) | To Test (🔲) | Hard/Edge (⚠️) |
|----------|-------|-------------|-------------|----------------|
| Tier 1 — Core writes | 45 | 18 | 24 | 3 (liquidation) |
| Tier 2 — Frozen/whitelist | 4 | 0 | 4 | 0 |
| Tier 3 — Resolver | 10 | 0 | 10 | 1 (veto) |
| Tier 4 — Private markets | 11 | 0 | 11 | 0 |
| Tier 5 — Reads | 45 | 0 | 45 | 0 |
| Tier 6 — API | 21 | 0 | 21 | 0 |
| **Total** | **136** | **18** | **115** | **4** |

Not in SDK (intentional): 8 functions (internal, admin, or alternative routing)
