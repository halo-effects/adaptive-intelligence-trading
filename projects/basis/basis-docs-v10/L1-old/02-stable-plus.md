# Stable+ Tokens

## WHAT: What Are Stable+ Tokens?

Stable+ tokens have one defining property: the price can only go up. They use elastic supply — tokens are minted when bought and burned when sold, with no pre-minting. Price appreciation comes from slippage retention: the value "lost" to price impact on each trade stays permanently in the liquidity pool, increasing the liquidity-to-supply ratio. This means every trade, buy or sell, pushes the price up. The tradeoff is that appreciation slows as supply grows, so Stable+ tokens thrive on velocity — buy, use, sell/burn cycles — not passive holding. STASIS is the canonical Stable+ token and the heartbeat of the ecosystem: every trade on the platform routes through it, and platform fees flow into the STASIS vault. Predict+ tokens are also Stable+ subtypes. Trading fee: 0.5%.

## WHY: Why Would I Use Stable+ Tokens?

Because they're anti-rug by design. 100% elastic supply means every token in circulation was purchased at market price — zero pre-minting, zero insider allocations. It's mathematically impossible for creators to dump tokens they didn't buy. For creators, launching a Stable+ token means earning 20% of every trade fee forever, with no need to hold or dump supply. For traders, the price floor only rises — your downside on any position is bounded by slippage on exit, not a crash to zero. For leverage users, since the price literally cannot decrease, Stable+ tokens unlock 20-36x leverage with zero liquidation risk — the highest on the platform. And for the ecosystem, STASIS ties it all together: more platform activity → more fees → higher vault yield → STASIS more attractive → more staking → more activity. That's the flywheel.

## HOW: How Do I Use Stable+ Tokens?

As a creator: deploy a Stable+ token through the platform. Your token is instantly tradeable on the DEX and you start earning 20% of every trade fee from the first trade. Design it around a use case with natural buy-sell cycles — gambling, tipping, access tokens, in-game currency — because velocity is what drives appreciation. As a trader: buy into tokens with high trading volume. The price can only go up, so your main consideration is entry timing — earlier means more upside captured. You can also take leverage positions (20-36x) knowing there's no liquidation risk. As a staker: if you're holding STASIS specifically, wrap it into wSTASIS in the staking vault to earn yield from platform fees automatically, then lock your wSTASIS as collateral to borrow USDB and redeploy that capital elsewhere. As an agent: use the SDK's `factory.create_token_with_metadata()` to launch tokens programmatically, or build bots that trade high-volume Stable+ tokens to farm the price appreciation mechanic.

## Deep Dive

For full details, see these reference modules:
- [03-what-is-basis](../modules/03-what-is-basis.md) — Stable+ mechanics, elastic supply, slippage retention
- [10-atomic-skills](../modules/10-atomic-skills.md) — Factory module (create tokens), Trading module (buy/sell)
- [12-defi-primitive-playbooks](../modules/12-defi-primitive-playbooks.md) — when to choose Stable+ vs Floor+
- [18-fee-cost-reference](../modules/18-fee-cost-reference.md) — 0.5% trading fee details
- [25-code-examples](../modules/25-code-examples.md) — token creation and trading examples
