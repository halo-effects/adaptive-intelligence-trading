# What to Avoid

**What this covers:** Strategies that look reasonable but lose money, plus real technical mistakes discovered during live SDK testing. Check here before taking any action for the first time.
**Related sections:** → See: [11-why-each-action-matters.md](11-why-each-action-matters.md) for what TO do and why · → See: [18-fee-cost-reference.md](18-fee-cost-reference.md) for fee details · → See: [12-how-everything-works.md](12-how-everything-works.md) for mechanics behind each system · → See: [25-code-examples.md](25-code-examples.md) for correct usage patterns

---

## Strategic Pitfalls

Every platform has strategies that sound good in theory but don't work in practice. Here's what to watch out for — and why.

### Leverage Pitfalls

**Avoid leveraging Floor+ tokens when spot price is far above floor price.** Loans are valued at floor price, not spot — so the further spot is above floor, the less you can actually borrow per loop. Your effective leverage drops sharply, but the 2% origination fee per loop stays the same. You're paying full fees for diminished leverage. Wait until spot and floor converge, or use Stable+/Predict+ tokens where floor = spot.

### Loan Pitfalls

**Avoid taking loans for very short periods.** The 2% origination fee is flat — it applies whether your loan lasts 10 days or 1 day. On a brief loan, that 2% may exceed whatever you earn from deploying the borrowed capital. Minimum loan duration is 10 days; if you don't need the capital for at least that long, the fee structure works against you. Use extensions (0.005%/day) instead of re-originating when you need to hold a position longer.

### Trading Pitfalls

**Avoid large single buys on new or low-liquidity tokens.** Early in a token's life, the AMM pool is shallow. A large buy will move the price significantly. Split large positions into multiple smaller trades — each moves the price less, and the pool deepens between trades as other participants enter.

**Avoid high-frequency trading / scalping strategies.** Round-trip raw trading fees are ~1% for Stable+ and ~3% for Floor+/Predict+ — before slippage. Use `getAmountsOut()` to preview real costs. HFT strategies designed for 0.1% fee environments will bleed out on Basis.

### Prediction Market Pitfalls

**Avoid creating markets on topics nobody cares about.** Creator fees are 20% of all trading volume — but 20% of zero is zero. Market creation costs gas, so a dead market is a net loss. Focus on questions that generate genuine debate.

**Avoid resolving markets you're not fully confident about.** The 5 USDB proposal bond is lost if you're wrong and someone disputes successfully. Only propose outcomes you can clearly verify from public information.

**Avoid buying outcome shares at very high probability without checking the general pot.** At 95% implied probability, raw pool returns are thin. The general pot improves this, but verify the math first.

### Predict+ Pitfalls

**Avoid selling Predict+ tokens during a market's active trading phase.** Stable+ mechanics mean selling burns tokens and pushes the price up — great for remaining holders, not for you. The optimal exit is after resolution, when the post-resolution sell wave pushes the price to its peak.

### Vault Staking Pitfalls

**Avoid staking very small amounts in the vault.** The ~1% raw swap fees round-trip plus slippage means your position needs to earn more than that in yield before you're profitable.

**Break-even estimation:**
```js
const entryAmount = parseUnits("1000", 18); // 1000 USDB
const entryPreview = await client.trading.getAmountsOut(entryAmount, [USDB, MAINTOKEN]);
const entryCost = entryAmount - entryPreview[entryPreview.length - 1];
const roundTripCost = entryCost * 2n;
// Your vault position needs to earn more than roundTripCost in yield to be profitable
```

Rule of thumb: at ~1% round-trip fees, a $100 position needs $1+ in yield just to break even. Factor in how long you plan to stake — days minimum, not hours. Larger positions and longer time horizons make the economics work.

### Reward Phase

**Avoid ignoring the reward phase on new tokens.** Reward phase buys earn bonus airdrop points and typically get better pricing. Once the reward volume threshold is hit, the bonus ends permanently.

### General Anti-Patterns

**Avoid passive USDB holding without deploying capital.** USDB sitting idle earns nothing. Every other participant is earning points while your capital does nothing.

**Avoid hedging all prediction market outcomes simultaneously.** This guarantees a loss from fees and earns no airdrop points.

**Avoid strategies that depend on fixed APY.** Vault yield is variable — it changes with platform volume and staking participation.

---

## Technical Mistakes

Real mistakes discovered during live SDK testing. These cause transaction failures, lost funds, or wasted gas.

### Loan Mistakes

- ❌ **Treating the 2% fee as an interest rate** → It's a flat origination fee. A year-long loan costs ~3.78%, not 76%.
- ❌ **Taking long loans "to be safe"** → Interest is prepaid. Repaying early wastes unused days. Take minimum (10 days), extend.
- ❌ **Repaying early to "save on interest"** → No refund. Let it run to near-expiry.
- ❌ **Re-originating instead of extending** → Each new loan = 2% fee. Extension = 0.005%/day.
- ❌ **Using non-multiple-of-10 percentage on `partialLoanSell()`** → Both `trading.partialLoanSell()` and `loans.hubPartialLoanSell()` require percentage divisible by 10 (10, 20, 30... 100). Using 25% causes a silent contract revert.
- ❌ **Calling `partialLoanSell` too soon after `leverageBuy`** → The backend needs ~5 seconds to sync. Always wait at least 5 seconds between creating a leverage position and partially selling it.
- ❌ **Letting a loan expire and forgetting to claim** → Remaining collateral value above debt is claimable via `claimLiquidation(hubId)` — NOT automatically returned. Set up monitoring to claim leftovers.
- ❌ **Forgetting a loan expiry** → Collateral sits in the contract until you call `claimLiquidation()`. Token price may drop while you wait. **Set calendar reminders. In production, alert when `expiryTime - now < 48 hours`.**

### Vault Mistakes

- ❌ **Not calculating your break-even** → Factor in gas (~$0.50-1.00, typically sponsored) plus ~1% swap fees + slippage both ways. Use `getAmountsOut()` to estimate.
- ❌ **Staking for hours** → Need enough yield to cover round-trip fees. Give it days.
- ❌ **Passing STASIS amounts to `lock()` instead of wSTASIS shares** → `lock()` takes wSTASIS shares. As yield accrues, the exchange ratio diverges from 1:1. Always use `convertToShares(stasisAmount)` first.

### Trading Mistakes

- ❌ **Ignoring the ~3% raw round-trip for Floor+/Predict+** → Your trade needs 3%+ price movement to break even on fees alone — slippage is additional.
- ❌ **Not checking `getAmountsOut()` before trading** → Slippage on low-liquidity tokens.
- ❌ **Not checking for active surge tax** → Creators can activate surge tax at any time (up to 15% on low-multiplier Floor+ tokens). Always check `taxes.getCurrentSurgeTax(tokenAddress)` before trading.

### Prediction Market Mistakes

- ❌ **Trying to fill your own order** → Contract rejects ("Cannot fill own order").
- ❌ **Selling immediately after resolution** → Price goes UP as others sell (burn → slippage retention). Wait.
- ❌ **Proposing without understanding bond risk** → 5 USDB bond is lost if disputed and vote goes against you.
- ❌ **Voting while holding an expiring loan** → After voting, staked tokens are locked for 24 hours (`VOTE_LOCK_DURATION`). If a loan expires within that window, you cannot unstake to repay. **Before voting, check all loan expiry dates within the next 24 hours.**

### Vesting Mistakes

- ❌ **Setting start time to `now()`** → Already past by tx confirmation. Use `now() + 60`.
- ❌ **Cliff under 1 hour** → Contract rejects. Minimum is 1 hour.

### General Mistakes

- 🚨 **Transferring ANY token to another wallet** → Triggers automatic flagging, points suspended pending review.
- ⚠️ **Receiving unsolicited tokens (griefing)** → Do NOT use them. Report via support with wallet + tx hash. Burn to `0x...dEaD`. Appeals process covers griefing victims.
- ❌ **Assuming loan IDs are 0-indexed** → They're 1-indexed.
- ❌ **Not waiting between transactions** → BSC needs a few seconds between txs. `await` each receipt before sending the next.
- ❌ **Assuming new tokens are immediately in the API** → On-chain is instant, backend has indexing delay.
- ❌ **Converting BigInt to Number in JS** → `Number(shares)` silently loses precision for large amounts (>2^53). Always use BigInt directly.
- ❌ **Using `syncLoan()` instead of `syncTransaction()`** → `syncLoan` is deprecated. Use `client.api.syncTransaction(txHash)` which covers ALL modules.
- ❌ **Not saving your API key on first run** → Only returned in full once at creation. After that, `listApiKeys()` returns masked hints only. Save immediately.
- ❌ **Hardcoding private keys in source files** → Use environment variables or secrets manager. Never commit keys.
- ❌ **Calling `setReferrer()` — method removed** → Referrals are now set server-side by passing `referrer` when claiming faucet: `claimFaucet("0xReferrerAddress")`.
- ❌ **Agent registration with oversized fields** → `name` max 100 chars, `description` max 500 chars.
