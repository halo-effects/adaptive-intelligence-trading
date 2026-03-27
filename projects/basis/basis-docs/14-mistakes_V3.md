# Mistakes to Avoid

**What this covers:** Real mistakes discovered during live SDK testing, organized by category. Check here before taking loans, setting up vesting, or trading.

**Related sections:** â†’ See: [10-fees.md](10-fees.md) for correct fee calculations Â· â†’ See: [08-how.md](08-how.md) for mechanics behind each system Â· â†’ See: [17-examples.md](17-examples.md) for correct usage patterns

---

Real mistakes discovered during live SDK testing.

## Loan Mistakes
- âŒ **Treating the 2% fee as an interest rate** â†’ It's a flat origination fee. A year-long loan costs ~3.78%, not 76%.
- âŒ **Taking long loans "to be safe"** â†’ Interest is prepaid. Repaying early wastes unused days. Take minimum (10 days), extend.
- âŒ **Repaying early to "save on interest"** â†’ No refund. Let it run to near-expiry.
- âŒ **Re-originating instead of extending** â†’ Each new loan = 2% fee. Extension = 0.005%/day.
- âŒ **Using non-multiple-of-10 percentage on `partialLoanSell()`** â†’ Both `trading.partialLoanSell()` and `loans.hubPartialLoanSell()` require percentage divisible by 10 (10, 20, 30... 100). Using 25% causes a silent contract revert with no error message.

- âŒ **Calling `partialLoanSell` too soon after `leverageBuy`** â†’ The backend needs ~5 seconds to sync the new position. If you call `partialLoanSell` immediately after `leverageBuy`, it may fail silently because the backend hasn't indexed the position yet. Always wait at least 5 seconds between creating a leverage position and partially selling it.
- âŒ **Letting a loan expire and forgetting to claim** â†’ When a loan expires, collateral is burned to cover the debt. But any remaining collateral value ABOVE the debt is claimable via `claimLiquidation(hubId)` â€” it is NOT automatically returned. If you intentionally let loans expire (e.g., underwater positions), set up a monitoring loop to claim leftovers. Unclaimed value sits in the contract indefinitely.

- â†’ **Forgetting a loan expiry** â€” When a loan expires, your collateral is NOT automatically returned. It sits in the contract until you call `claimLiquidation()`. Meanwhile, the underlying token's price may drop. Worst case: you forget for weeks, token drops 80%, and you claim back 20% of original value. **Set calendar reminders for loan expiry dates. In production, implement an automated check:** query `getLoanDetails()` and alert when `expiryTime - now < 48 hours`.

## Vault Mistakes
- âŒ **Not calculating your break-even** â†’ Factor in gas costs (~$0.50-1.00 entry/exit) plus ~1% raw swap fees + slippage both ways. Use `getAmountsOut()` to estimate actual costs. Calculate whether expected yield exceeds total costs for your position size.
- âŒ **Staking for hours** â†’ Need enough yield to cover round-trip fees + slippage. Give it days.
- âŒ **Passing STASIS amounts to `lock()` instead of wSTASIS shares** â†’ `lock()` takes wSTASIS shares, not STASIS units. As vault yield accrues, the exchange ratio diverges from 1:1. Always use `convertToShares(stasisAmount)` first, then pass the result to `lock()`.

## Trading Mistakes
- âŒ **Ignoring the ~3% raw round-trip for Floor+/Predict+** â†’ Your trade needs 3%+ price movement to break even on fees alone â€” slippage is additional. Use `getAmountsOut()` to preview actual costs.
- âŒ **Not checking `getAmountsOut()` before trading** â†’ Slippage on low-liquidity tokens.
- âŒ **Not checking for active surge tax** â†’ A token creator can activate surge tax at any time (up to 15% on low-multiplier Floor+ tokens). Always check `taxes.getCurrentSurgeTax(tokenAddress)` before trading to avoid unexpected fees. Your cost model can break overnight if a surge is activated after you've entered a position.

## Prediction Market Mistakes
- âŒ **Trying to fill your own order** â†’ Contract rejects ("Cannot fill own order").
- âŒ **Selling immediately after resolution** â†’ Price goes UP as others sell (burn â†’ slippage retention). Wait.
- âŒ **Proposing an outcome without understanding bond risk** â†’ Your 5 USDB proposal bond is lost if someone disputes and the vote goes against you. The disputer's bond is also at risk. Only propose outcomes you're confident about. If neither party is correct, both bonds go to the insurance fund.

- â†’ **Voting while holding an expiring loan** â€” After voting, your staked tokens are locked for 24 hours (`VOTE_LOCK_DURATION`). If you have a loan expiring within that window, you cannot unstake to repay or extend it. Scenario: You vote on a disputed market on Monday at 3pm. Your loan expires Tuesday at 10am. You cannot unstake until Tuesday at 3pm â€” by then your collateral has been liquidated. **Before voting, check all loan expiry dates and ensure none fall within the next 24 hours.** Use `client.staking.getUserStakeDetails(wallet)` to check your stake status (returns liquid/locked shares and total value), and `client.loans.getUserLoanDetails(wallet, hubId)` for hub loan expiry dates.

## Vesting Mistakes
- âŒ **Setting start time to `now()`** â†’ Already past by tx confirmation. Use `now() + 60`.
- âŒ **Cliff under 1 hour** â†’ Contract rejects. Minimum is 1 hour.

## General Mistakes
- ðŸš¨ **Transferring ANY token to another wallet** â†’ Triggers automatic flagging, points suspended pending review.
- â€” ï¸ **Receiving unsolicited tokens (griefing)** â†’ Do NOT use them. Don't trade, stake, or interact with griefed tokens. Report the incident via support with your wallet address + tx hash. Your points are safe as long as you didn't initiate the transfer. If you accidentally used griefed tokens before noticing, document what happened and submit through the appeals process. This applies to USDB, STASIS, factory tokens, Predict+ tokens â€” everything. All legitimate activity routes through platform contracts. **Accidental transfers** (code bugs, wrong address) can be disputed and reinstated if there's no evidence of multi-wallet gaming. **Confirmed sybil activity** (funding other wallets, splitting activity across addresses) = permanent disqualification.
- âŒ **Assuming loan IDs are 0-indexed** â†’ They're 1-indexed.
- âŒ **Not waiting between transactions** â†’ BSC needs a few seconds between txs. The SDK uses viem which handles nonce management automatically for sequential calls, but rapid burst sequences (e.g., multiple buys in a loop) should `await` each transaction receipt before sending the next. If you hit nonce errors, add a small delay between transactions.
- âŒ **Assuming new tokens are immediately in the API** â†’ On-chain is instant, backend has a slight indexing delay.
- âŒ **Converting BigInt to Number in JS** â†’ `Number(shares)` silently loses precision for large token amounts (>2^53). Always pass BigInt values directly to SDK methods. Use `BigInt()` for arithmetic, `toString()` for display.
- âŒ **Hardcoding private keys in source files** â†’ Use environment variables (`process.env.PRIVATE_KEY`) or a secrets manager. Never commit keys to version control. See security note in Getting Started.


---
