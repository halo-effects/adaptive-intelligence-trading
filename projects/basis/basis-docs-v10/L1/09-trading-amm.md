# Trading & AMM Infrastructure — L1 What/Why/How

## WHAT: Trading & AMM Infrastructure

All trading on Basis routes through a single central SWAP contract using STASIS as the hub token. There are no direct token-to-token swaps. If you're buying a factory token with USDB, it goes: USDB → STASIS → Token (3-path). If you're buying STASIS itself, it's USDB → STASIS (2-path). Selling reverses the path.

This hub-and-spoke design means all liquidity is unified through STASIS. Every trade on the platform — regardless of which token — flows through STASIS and generates fees that feed into the staking vault. There's no liquidity fragmentation across hundreds of isolated pairs.

The AMM uses a modified constant-product formula. Buys work like standard Uniswap-style AMMs. Sells are where it gets different — the hybrid multiplier controls how much sell value stays in the pool versus returning to the seller. Stable+ tokens retain 100% (price only goes up). Floor+ tokens retain a percentage based on their stability setting (higher stability = more retention = stronger floor).

Trading fees vary by token type: 0.5% for Stable+ (STASIS), 1.5% for Floor+ and Predict+. Fees are distributed across staking yield, creator revenue, reward phase buyers, and platform treasury. Creators earn 20% of the net fee on every trade of their token, forever.

Gas is sponsored by the platform up to 0.01 BNB per wallet per day, so most users trade for free on gas.

## WHY: Why Would I Trade on Basis?

**Unified liquidity**: Because everything routes through STASIS, there's no scattered liquidity across dozens of thin pools. The deeper the STASIS pool gets (from platform-wide volume), the less slippage on every trade. Growing the platform benefits every token, not just popular ones.

**Built-in protections**: The token mechanics themselves protect traders. Stable+ tokens can't go down. Floor+ tokens absorb sell pressure instead of cratering. You're not trading against rugs and death spirals — the AMM design structurally prevents them.

**Creator alignment**: Creators earn from trading fees, not from dumping pre-minted tokens. 100% elastic supply means every token in circulation was bought at market price. There's no insider allocation to dump. The creator's incentive is to drive trading volume, which aligns with your interest as a trader.

**Zero gas cost**: With up to 0.01 BNB per day in sponsored gas, most traders never pay gas fees. This removes the friction that makes small trades uneconomical on other platforms. You can execute frequent, small trades without gas eating your profits.

**Every trade earns points**: Every swap contributes to your airdrop allocation. Trading isn't just a means to an end — it's directly rewarded. Combined with the fact that exploring multiple token types and features increases your earning potential, active trading across the platform is one of the most effective strategies.

## HOW: How Do I Trade on Basis?

**Buy a token**: Select any token on the DEX, enter the amount of USDB you want to spend, and execute the swap. The platform automatically builds the correct routing path (2-hop or 3-hop via STASIS). You receive tokens in your wallet instantly.

**Sell a token**: Select the token you hold, choose the amount (or a percentage of your balance), and sell. The path reverses through STASIS back to USDB. For Stable+ tokens, selling burns your tokens and the price stays the same or goes up. For Floor+ tokens, the price dips but the floor holds.

**Preview trades**: Before executing, check the expected output to see exactly how many tokens you'll receive (or USDB on sells) accounting for current pool state and any active surge taxes. This helps avoid unexpected slippage on larger trades.

**Leverage trade**: For amplified exposure, use leverage buy — specify the token, amount, and loan duration. The system automatically loops buy → loan → buy → loan to build a leveraged position. Unwind in 10% increments when ready.

**Understand surge taxes**: Token creators can temporarily activate a decaying extra fee on trades (surge tax). This is time-limited and rolls down from start rate to end rate over the duration. Check the current tax rate before trading if a surge is active — or wait for it to decay.

## Deep Dive

For full details, see these reference modules:
- [16-how-everything-works](../modules/16-how-everything-works.md) — swap routing, 2-path/3-path, slippage retention
- [10-atomic-skills](../modules/10-atomic-skills.md) — Trading module, Taxes module (surge tax)
- [18-fee-cost-reference](../modules/18-fee-cost-reference.md) — trading fees by token type, fee distribution
- [22-mistakes-to-avoid](../modules/22-mistakes-to-avoid.md) — trading slippage, hub ID indexing
- [25-code-examples](../modules/25-code-examples.md) — trading examples
