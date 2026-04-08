# Mistakes to Avoid

**What this covers:** Real mistakes discovered during live SDK testing, organized by category. Check here before taking loans, setting up vesting, or trading.

**Related sections:** → See: [18-fee-cost-reference.md](18-fee-cost-reference.md) for correct fee calculations · → See: [16-how-everything-works.md](16-how-everything-works.md) for mechanics behind each system · → See: [25-code-examples.md](25-code-examples.md) for correct usage patterns

---

Real mistakes discovered during live SDK testing.

## Loan Mistakes
- ❌ **Treating the 2% fee as an interest rate** → It's a flat origination fee. A year-long loan costs ~3.78%, not 76%.
- ❌ **Taking long loans "to be safe"** → Interest is prepaid. Repaying early wastes unused days. Take minimum (10 days), extend.
- ❌ **Repaying early to "save on interest"** → No refund. Let it run to near-expiry.
- ❌ **Re-originating instead of extending** → Each new loan = 2% fee. Extension = 0.005%/day.
- ❌ **Using non-multiple-of-10 percentage on `partialLoanSell()`** → Both `trading.partialLoanSell()` and `loans.hubPartialLoanSell()` require percentage divisible by 10 (10, 20, 30... 100). Using 25% causes a silent contract revert with no error message.

- ❌ **Calling `partialLoanSell` too soon after `leverageBuy`** → The backend needs ~5 seconds to sync the new position. If you call `partialLoanSell` immediately after `leverageBuy`, it may fail silently because the backend hasn't indexed the position yet. Always wait at least 5 seconds between creating a leverage position and partially selling it.
- ❌ **Letting a loan expire and forgetting to claim** → When a loan expires, collateral is burned to cover the debt. But any remaining collateral value ABOVE the debt is claimable via `claimLiquidation(hubId)` — it is NOT automatically returned. If you intentionally let loans expire (e.g., underwater positions), set up a monitoring loop to claim leftovers. Unclaimed value sits in the contract indefinitely.

- → **Forgetting a loan expiry** — When a loan expires, your collateral is NOT automatically returned. It sits in the contract until you call `claimLiquidation()`. Meanwhile, the underlying token's price may drop. Worst case: you forget for weeks, token drops 80%, and you claim back 20% of original value. **Set calendar reminders for loan expiry dates. In production, implement an automated check:** query `getLoanDetails()` and alert when `expiryTime - now < 48 hours`.

## Vault Mistakes
- ❌ **Not calculating your break-even** → Factor in gas costs (~$0.50-1.00 entry/exit, typically sponsored but subject to daily limits) plus ~1% raw swap fees + slippage both ways. Use `getAmountsOut()` to estimate actual costs. Calculate whether expected yield exceeds total costs for your position size.
- ❌ **Staking for hours** → Need enough yield to cover round-trip fees + slippage. Give it days.
- ❌ **Passing STASIS amounts to `lock()` instead of wSTASIS shares** → `lock()` takes wSTASIS shares, not STASIS units. As vault yield accrues, the exchange ratio diverges from 1:1. Always use `convertToShares(stasisAmount)` first, then pass the result to `lock()`.

## Trading Mistakes
- ❌ **Ignoring the ~3% raw round-trip for Floor+/Predict+** → Your trade needs 3%+ price movement to break even on fees alone — slippage is additional. Use `getAmountsOut()` to preview actual costs.
- ❌ **Not checking `getAmountsOut()` before trading** → Slippage on low-liquidity tokens.
- ❌ **Not checking for active surge tax** → A token creator can activate surge tax at any time (up to 15% on low-multiplier Floor+ tokens). Always check `taxes.getCurrentSurgeTax(tokenAddress)` before trading to avoid unexpected fees. Your cost model can break overnight if a surge is activated after you've entered a position.

## Prediction Market Mistakes
- ❌ **Trying to fill your own order** → Contract rejects ("Cannot fill own order").
- ❌ **Selling immediately after resolution** → Price goes UP as others sell (burn → slippage retention). Wait.
- ❌ **Proposing an outcome without understanding bond risk** → Your 5 USDB proposal bond is lost if someone disputes and the vote goes against you. The disputer's bond is also at risk. Only propose outcomes you're confident about. If neither party is correct, both bonds go to the insurance fund.

- → **Voting while holding an expiring loan** — After voting, your staked tokens are locked for 24 hours (`VOTE_LOCK_DURATION`). If you have a loan expiring within that window, you cannot unstake to repay or extend it. Scenario: You vote on a disputed market on Monday at 3pm. Your loan expires Tuesday at 10am. You cannot unstake until Tuesday at 3pm — by then your collateral has been liquidated. **Before voting, check all loan expiry dates and ensure none fall within the next 24 hours.** Use `client.staking.getUserStakeDetails(wallet)` to check your stake status (returns liquid/locked shares and total value), and `client.loans.getUserLoanDetails(wallet, hubId)` for hub loan expiry dates.

## Vesting Mistakes
- ❌ **Setting start time to `now()`** → Already past by tx confirmation. Use `now() + 60`.
- ❌ **Cliff under 1 hour** → Contract rejects. Minimum is 1 hour.

## General Mistakes
- 🚨 **Transferring ANY token to another wallet** → Triggers automatic flagging, points suspended pending review.
- — ️ **Receiving unsolicited tokens (griefing)** → Do NOT use them. Don't trade, stake, or interact with griefed tokens. Report the incident via support with your wallet address + tx hash. Your points are safe as long as you didn't initiate the transfer. If you accidentally used griefed tokens before noticing, document what happened and submit through the appeals process. This applies to USDB, STASIS, factory tokens, Predict+ tokens — everything. All legitimate activity routes through platform contracts. **Accidental transfers** (code bugs, wrong address) can be disputed and reinstated if there's no evidence of multi-wallet gaming. **Confirmed sybil activity** (funding other wallets, splitting activity across addresses) = permanent disqualification.
- ❌ **Assuming loan IDs are 0-indexed** → They're 1-indexed.
- ❌ **Not waiting between transactions** → BSC needs a few seconds between txs. The SDK uses viem which handles nonce management automatically for sequential calls, but rapid burst sequences (e.g., multiple buys in a loop) should `await` each transaction receipt before sending the next. If you hit nonce errors, add a small delay between transactions.
- ❌ **Assuming new tokens are immediately in the API** → On-chain is instant, backend has a slight indexing delay.
- ❌ **Converting BigInt to Number in JS** → `Number(shares)` silently loses precision for large token amounts (>2^53). Always pass BigInt values directly to SDK methods. Use `BigInt()` for arithmetic, `toString()` for display.
- ❌ **Using `syncLoan()` instead of `syncTransaction()`** → `syncLoan` is deprecated. Use `client.api.syncTransaction(txHash)` which now covers ALL modules (Factory, Trading, Loans, Staking, Vesting, PredictionMarkets, Resolver, Taxes, OrderBook, PrivateMarkets, AgentIdentity). The legacy method still delegates to `syncTransaction` but don't rely on it.
- ❌ **Not saving your API key on first run** → The API key is only returned in full once at creation time. After that, `listApiKeys()` only returns a masked hint (`bsk_****XXXX`). If you lose it you'll need to create a new one. Save it immediately on first run and pass it via `apiKey` / `api_key` on subsequent runs.
- ❌ **Hardcoding private keys in source files** → Use environment variables (`process.env.PRIVATE_KEY`) or a secrets manager. Never commit keys to version control. See security note in Getting Started.
- ❌ **Calling `setReferrer()` — method removed** → The `setReferrer` contract method has been removed. Referrals are now set server-side by passing a `referrer` address when claiming the daily faucet: `claimFaucet("0xReferrerAddress")`. Once set, it's permanent.
- ❌ **Agent registration with oversized fields** → Agent `name` is capped at 100 characters and `description` at 500 characters. Exceeding these limits will be rejected by the API. Keep metadata concise.

---
