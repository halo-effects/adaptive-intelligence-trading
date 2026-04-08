# Floor+ Tokens

## WHAT: What Are Floor+ Tokens?

Floor+ tokens have real price movement — up and down — but with a rising floor that never decreases. They use the same elastic supply as Stable+ (minted on buy, burned on sell, no pre-minting), but with a critical modification: the hybrid AMM absorbs sell pressure. A sell that would crater a traditional token only creates a dip on Floor+. The price moves down, but not nearly as far. Meanwhile, the floor price rises with every trade — buy or sell — because slippage retention accumulates in the pool. Creators set a stability dial at launch (0-100% in the UI), controlling exactly how much sell absorption the token has. Low stability = more price movement and weaker floor growth. High stability = less volatility and stronger floor. Trading fee: 1.5%.

## WHY: Why Would I Use Floor+ Tokens?

Because tokens don't die from lack of buying — they die from panic selling. On traditional launch platforms, a single whale dump triggers a cascade: price craters, holders panic, everyone sells, token dead in hours. Floor+ breaks that cycle. The same dump creates a smaller dip, which looks like a buying opportunity instead of a death spiral. The community holds because there's no reason to panic. The paradox: Floor+ tokens go up slower per dollar of buy volume, but because they survive sells that would kill traditional tokens, they have the potential to go higher overall. You sacrifice the spike to kill the crash — and killing the crash is what actually matters. For creators, it means your project doesn't live or die on a single bad hour. For traders, your downside shrinks over time as the floor rises. For leverage users, loans are valued against the floor price (which never drops), so there's no price liquidation risk — and leverage is highest at launch when floor and spot price are close together. There's nothing like this in the market.

## HOW: How Do I Use Floor+ Tokens?

As a creator: deploy a Floor+ token and choose your stability dial setting. High stability (closer to 100%) if you want a resilient community token. Low stability (closer to 0%) if you want more price action and trading appeal. Your token is instantly tradeable and you earn 20% of every trade fee permanently. As a trader: look for Floor+ tokens where the spot price is near the floor — that's your tightest risk. Buy dips knowing the floor is your backstop. Use leverage when floor and spot are close together for the best multipliers. As an agent: use the SDK's `factory.create_token_with_metadata()` to deploy, and build strategies around the floor-to-spot ratio — it's the key metric for timing entries and sizing leverage.

## Deep Dive

For full details, see these reference modules:
- [03-what-is-basis](../modules/03-what-is-basis.md) — Floor+ mechanics, stability dial, sell absorption
- [10-atomic-skills](../modules/10-atomic-skills.md) — Factory module (create Floor+ with hybridMultiplier)
- [12-defi-primitive-playbooks](../modules/12-defi-primitive-playbooks.md) — Floor+ launch window, sizing
- [18-fee-cost-reference](../modules/18-fee-cost-reference.md) — 1.5% trading fee, surge tax
