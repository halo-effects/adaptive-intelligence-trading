# Mistakes to Avoid

**What this covers:** Real mistakes discovered during live SDK testing, organized by category. Check here before taking loans, setting up vesting, or trading.

**Related sections:** → See: [09-fees.md](09-fees.md) for correct fee calculations · → See: [07-how.md](07-how.md) for mechanics behind each system · → See: [16-examples.md](16-examples.md) for correct usage patterns

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

## Vault Mistakes
- ❌ **Not calculating your break-even** → Factor in gas costs (~$0.50-1.00 entry/exit) plus ~1% raw swap fees + slippage both ways. Use `getAmountsOut()` to estimate actual costs. Calculate whether expected yield exceeds total costs for your position size.
- ❌ **Staking for hours** → Need enough yield to cover round-trip fees + slippage. Give it days.
- ❌ **Passing STASIS amounts to `lock()` instead of wSTASIS shares** → `lock()` takes wSTASIS shares, not STASIS units. As vault yield accrues, the exchange ratio diverges from 1:1. Always use `convertToShares(stasisAmount)` first, then pass the result to `lock()`.

## Trading Mistakes
- ❌ **Ignoring the 3% round-trip for Floor+/Predict+** → Your trade needs 3%+ to break even.
- ❌ **Not checking `getAmountsOut()` before trading** → Slippage on low-liquidity tokens.
- ❌ **Not checking for active surge tax** → A token creator can activate surge tax at any time (up to 15% on low-multiplier Floor+ tokens). Always check `taxes.getCurrentSurgeTax(tokenAddress)` before trading to avoid unexpected fees. Your cost model can break overnight if a surge is activated after you've entered a position.

## Prediction Market Mistakes
- ❌ **Trying to fill your own order** → Contract rejects ("Cannot fill own order").
- ❌ **Selling immediately after resolution** → Price goes UP as others sell (burn → slippage retention). Wait.
- ❌ **Proposing an outcome without understanding bond risk** → Your 5 USDB proposal bond is lost if someone disputes and the vote goes against you. The disputer's bond is also at risk. Only propose outcomes you're confident about. If neither party is correct, both bonds go to the insurance fund.

## Vesting Mistakes
- ❌ **Setting start time to `now()`** → Already past by tx confirmation. Use `now() + 60`.
- ❌ **Cliff under 1 hour** → Contract rejects. Minimum is 1 hour.

## General Mistakes
- 🚨 **Transferring ANY token to another wallet** → Permanent disqualification from all rewards. Entire point balance wiped, irreversible. This applies to USDB, STASIS, factory tokens, Predict+ tokens — everything. All legitimate activity routes through platform contracts.
- ❌ **Assuming loan IDs are 0-indexed** → They're 1-indexed.
- ❌ **Not waiting between transactions** → BSC needs a few seconds between txs. The SDK uses viem which handles nonce management automatically for sequential calls, but rapid burst sequences (e.g., multiple buys in a loop) should `await` each transaction receipt before sending the next. If you hit nonce errors, add a small delay between transactions.
- ❌ **Assuming new tokens are immediately in the API** → On-chain is instant, backend has a slight indexing delay.
- ❌ **Converting BigInt to Number in JS** → `Number(shares)` silently loses precision for large token amounts (>2^53). Always pass BigInt values directly to SDK methods. Use `BigInt()` for arithmetic, `toString()` for display.
- ❌ **Hardcoding private keys in source files** → Use environment variables (`process.env.PRIVATE_KEY`) or a secrets manager. Never commit keys to version control. See security note in Getting Started.
