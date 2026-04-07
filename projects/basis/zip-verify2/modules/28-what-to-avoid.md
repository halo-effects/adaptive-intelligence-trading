# What to Avoid - Common Pitfalls

**What this covers:** Strategies and actions that look reasonable but lose money or waste resources on Basis. Understanding these saves capital and time.
**Related sections:** → See: [15-why-each-action-matters.md](15-why-each-action-matters.md) for what TO do and why · → See: [18-fee-cost-reference.md](18-fee-cost-reference.md) for fee details · → See: [22-mistakes-to-avoid.md](22-mistakes-to-avoid.md) for technical errors that cause transaction failures

---

Every platform has strategies that sound good in theory but don't work in practice. Here's what to watch out for on Basis - and why.

---

## Leverage

**Avoid leveraging Floor+ tokens when spot price is far above floor price.** Loans are valued at floor price, not spot - so the further spot is above floor, the less you can actually borrow per loop. Your effective leverage drops sharply, but the 2% origination fee per loop stays the same. You're paying full fees for diminished leverage. Wait until spot and floor converge, or use Stable+/Predict+ tokens where floor = spot.

---

## Loans

**Avoid taking loans for very short periods.** The 2% origination fee is flat - it applies whether your loan lasts 10 days or 1 day. On a brief loan, that 2% may exceed whatever you earn from deploying the borrowed capital. Minimum loan duration is 10 days; if you don't need the capital for at least that long, the fee structure works against you. Use extensions (0.005%/day) instead of re-originating when you need to hold a position longer.

---

## Trading

**Avoid large single buys on new or low-liquidity tokens.** Early in a token's life, the AMM pool is shallow. A large buy will move the price significantly, and the slippage works against you. Split large positions into multiple smaller trades - each one moves the price less, and the pool deepens between trades as other participants enter. The same applies to prediction market shares in new markets.

---

## Prediction Markets

**Avoid creating markets on topics nobody cares about.** Creator fees are 20% of all trading volume - but 20% of zero is zero. Market creation costs gas, so a dead market is a net loss. Focus on questions that generate genuine debate, strong opinions, and active trading. Controversial, timely, and verifiable questions attract the most volume.

**Avoid resolving markets you're not fully confident about.** The 5 USDB proposal bond is lost if you're wrong and someone disputes successfully. Only propose outcomes you can clearly verify from public information. The bounty reward for being right is worth it - the bond loss for being wrong is avoidable.

**Avoid buying outcome shares at very high probability without checking the general pot.** At 95% implied probability, the raw pool split gives thin returns. The general pot (accumulated from trading fees across all outcomes) improves this, but you should check whether the combined payout justifies the entry price. Late-stage entries can still be profitable - just verify the math first.

---

## Predict+ Tokens

**Avoid selling Predict+ tokens during a market's active trading phase.** Stable+ mechanics mean selling burns tokens and pushes the price up - which is great for remaining holders, not for you. You're exiting before maximum volume has accumulated. The optimal exit is after market resolution, when the post-resolution sell wave pushes the price to its peak. Patience is rewarded structurally.

---

## Vault Staking

**Avoid staking very small amounts in the vault.** The ~1% raw swap fees round-trip (0.5% per leg) plus variable slippage on both entry and exit means your position needs to earn more than that in yield before you're profitable.

**Break-even estimation:** Before staking, preview your actual entry cost:
```js
const entryAmount = parseUnits("1000", 18); // 1000 USDB
const entryPreview = await client.trading.getAmountsOut(entryAmount, [USDB, MAINTOKEN]);
const entryCost = entryAmount - entryPreview[entryPreview.length - 1]; // What you "lose" to fees + slippage on entry
// Double it for round-trip (exit will cost roughly the same)
const roundTripCost = entryCost * 2n;
// Your vault position needs to earn more than roundTripCost in yield to be profitable
```
Rule of thumb: at ~1% round-trip fees, a $100 position needs $1+ in yield just to break even. At $1,000 the threshold is $10+. Factor in how long you plan to stake — days minimum, not hours. A $50 stake earning fractions of a cent per day may never break even against entry and exit costs. Larger positions and longer time horizons make the vault economics work. Wrapping, locking, and unlocking cost only gas — the swap fees and slippage on entry and exit are the real cost to consider. Use `getAmountsOut()` to preview your actual costs before committing.

---

## Reward Phase

**Avoid ignoring the reward phase on new tokens.** Reward phase buys earn bonus airdrop points and typically get better pricing (you're buying early while the token is still building momentum). Once the reward volume threshold is hit, the bonus ends permanently. Missing this window means paying the same fees for fewer points.

---

## General Anti-Patterns

**Avoid high-frequency trading / scalping strategies.** Round-trip raw trading fees are ~1% for Stable+ and ~3% for Floor+/Predict+ tokens — and that's before slippage, which varies by pool depth and trade size. Your actual break-even is higher than the raw fees alone. Use `getAmountsOut()` to preview real costs. HFT strategies designed for 0.1% fee environments will bleed out on Basis.

**Avoid passive USDB holding without deploying capital.** USDB sitting idle in your wallet earns nothing. Every other participant who is trading, staking, creating, or betting is earning airdrop points while your capital does nothing.

**Avoid hedging all prediction market outcomes simultaneously.** This guarantees a loss from fees and earns no airdrop points. Only enter positions where you have genuine conviction or information.

**Avoid strategies that depend on fixed APY.** Vault yield is variable - it changes with platform volume and staking participation. If your model requires predictable returns, the vault isn't a fixed-rate product.

---

→ See: [22-mistakes-to-avoid.md](22-mistakes-to-avoid.md) for technical mistakes that cause transaction failures (wrong IDs, bad parameters, silent reverts).

---
