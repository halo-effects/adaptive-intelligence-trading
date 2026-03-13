# Token Frameworks

## Token Factory

Creators utilizing the Basis Token Factory can choose between two distinct token contract types for their projects: **Stable+** and **Floor+**. A third type, **Predict+**, is used specifically for prediction market events. These frameworks address critical market needs by offering novel solutions for stability, growth, and fair participation.

### Token Supply and Distribution

**All Basis Tokens** (Stable+, Floor+, and Predict+) have **100% elastic supply**:

* **Minting:** New tokens are minted when users purchase them on the DEX using the paired asset (STASIS for most tokens, USDC for STASIS itself).
* **Burning:** Tokens are burned (permanently removed from circulation) when users sell them on the DEX.
* **There is no pre-minting or fixed total supply.** Supply adjusts entirely based on demand and trading activity.
* **All tokens start at $1.00** with creator-configured starting liquidity ($100–$10,000).

{% hint style="info" %}
Every single token in circulation was purchased at market price. Zero pre-minting, zero team/insider allocations — this makes rug pulls structurally impossible.
{% endhint %}

### STASIS (Liquidity Pair Token)

**STASIS** is the native liquidity pair token of the Basis platform. It is itself a Stable+ token, paired with USDC.

* All other Basis Tokens (Stable+, Floor+, Predict+) pair against STASIS. For example, a new "MyBrandToken" (Stable+) would be traded as MyBrandToken/STASIS.
* Its supply is also dynamic — minted on purchase with USDC, burned on sale.
* STASIS appreciates slowly through the slippage retention mechanism driven by the circulation volume of the entire ecosystem.

**Cascading Growth Effect:** Because every Basis Token is paired with STASIS, any price increase in STASIS (due to its own Stable+ mechanics and ecosystem demand) positively influences the value of all other Basis Tokens paired against it.

### Stable+ — "Up-Only" Tokens

Stable+ tokens are designed so the price can only increase or remain flat — never decrease. The appreciation mechanism is **slippage retention**: when someone buys or sells, the price impact (slippage) stays in the liquidity pool, increasing the liquidity-to-supply ratio. This creates a ratcheting effect where each new high becomes the permanent minimum.

**Key details:**
* **Not a moonshot token** — it's a branded stablecoin with slow appreciation
* Appreciation is strongest at low supply and diminishes as supply grows
* Needs active circulation (buy → use → sell → buy cycles) for meaningful price movement
* Trading fee: **0.5%** (platform-set)
* Fees do **not** inject into Stable+ liquidity — fees go to Creator (20%), bonding phase buyers, platform revenue, and wSTASIS vault

**Best for:** Utility tokens, branded stablecoins, access passes, services, loyalty programs — anything with recurring circulation.

### Floor+ — "Rising Floor" Tokens

Floor+ tokens combine price discovery with downside protection. The price **goes up on buys and down on sells**, but can never fall below a rising floor price.

**Key details:**
* **Stability dial:** 0% to 100% (set at creation, immutable). 0% = most volatile, 100% = most stable
* The more volatile the setting, the more price moves per trade
* Floor price rises over time with trading volume
* 100% liquidity backing at floor price — every dollar of market cap at floor is backed by real liquidity
* Trading fee: **1.5%** (platform-set)

**Best for:** Community tokens, speculative assets with safety nets, creator tokens where trading action is desired alongside downside protection.

### Predict+ — Prediction Market Tokens

Predict+ tokens are Stable+ tokens created specifically for prediction markets. Each prediction market has **one Predict+ token** that represents the market itself — not individual outcomes.

**Key details:**
* Uses Stable+ mechanics (up-only price)
* Betting on outcomes is **separate** from buying the token
* Trading fee: **0.5%** (platform-set)
* A portion of trading fees flows into a trader-to-bettor pot that supplements the winning pool

**Best for:** Prediction market events — sports, politics, crypto prices, entertainment, any verifiable outcome.

### No Pre-Minting, Team, or Partner Allocations

A core principle of Basis is fairness. There are no pre-mined tokens, no tokens allocated to the development team, advisors, or partners. All participants, including token creators, must acquire their tokens through the public purchase mechanism on the DEX. This aligns incentives and prevents unfair advantages.

### Trading Fees by Token Type

| Token Type | Trading Fee | Creator Share (20% of fee) |
| ---------- | ----------- | -------------------------- |
| Stable+    | 0.5%        | 0.1% per trade             |
| Floor+     | 1.5%        | 0.3% per trade             |
| Predict+   | 0.5%        | 0.1% per trade             |

Trading fees are platform-set for transparency — creators cannot change the rate. Creators can control the split of their 20% share across up to 10 wallets via the Dev Tax Sharing feature.
