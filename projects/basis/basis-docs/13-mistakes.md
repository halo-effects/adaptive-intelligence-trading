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
- ❌ **Using non-multiple-of-10 percentage on `hubPartialLoanSell()`** → Hub version requires percentage divisible by 10 (10, 20, 30... 100). `trading.partialLoanSell()` accepts any 1–100. Using 25% on the hub version causes a silent contract revert with no error message.

## Vault Mistakes
- ❌ **Not calculating your break-even** → Factor in gas costs (~$0.50-1.00 entry/exit) plus ~1.62% swap fees. Calculate whether expected yield exceeds total costs for your position size.
- ❌ **Staking for hours** → Need ~1.62% yield to cover round-trip. Give it days.

## Trading Mistakes
- ❌ **Ignoring the 3% round-trip for Floor+/Predict+** → Your trade needs 3%+ to break even.
- ❌ **Not checking `getAmountsOut()` before trading** → Slippage on low-liquidity tokens.

## Prediction Market Mistakes
- ❌ **Trying to fill your own order** → Contract rejects ("Cannot fill own order").
- ❌ **Selling immediately after resolution** → Price goes UP as others sell (burn → slippage retention). Wait.

## Vesting Mistakes
- ❌ **Setting start time to `now()`** → Already past by tx confirmation. Use `now() + 60`.
- ❌ **Cliff under 1 hour** → Contract rejects. Minimum is 1 hour.

## General Mistakes
- 🚨 **Transferring ANY token to another wallet** → Permanent disqualification from all rewards. Entire point balance wiped, irreversible. This applies to USDB, STASIS, factory tokens, Predict+ tokens — everything. All legitimate activity routes through platform contracts.
- ❌ **Assuming loan IDs are 0-indexed** → They're 1-indexed.
- ❌ **Not waiting between transactions** → BSC needs a few seconds between txs.
- ❌ **Assuming new tokens are immediately in the API** → On-chain is instant, backend has a slight indexing delay.
- ❌ **Converting BigInt to Number in JS** → `Number(shares)` silently loses precision for large token amounts (>2^53). Always pass BigInt values directly to SDK methods. Use `BigInt()` for arithmetic, `toString()` for display.
- ❌ **Hardcoding private keys in source files** → Use environment variables (`process.env.PRIVATE_KEY`) or a secrets manager. Never commit keys to version control. See security note in Getting Started.
