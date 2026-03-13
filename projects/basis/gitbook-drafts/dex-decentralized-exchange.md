# DEX (Decentralized Exchange)

## Trade Native Assets

The DEX is the native decentralized exchange of the Basis platform, serving as the exclusive marketplace for buying and selling all Basis Tokens (Stable+, Floor+, Predict+, and STASIS).

**Core Functionality:** Seamless interface for swapping between Basis Tokens and their paired assets. All tokens pair against STASIS; STASIS itself pairs with USDC. The buy panel supports both USDC (auto-routes through STASIS) and direct STASIS purchases.

**Technical Architecture:** Built as a system of smart contracts on BNB Chain, ensuring transparency, censorship resistance, and non-custodial trading. All Basis Tokens are ERC-20 compatible.

### Liquidity Model

* Unlike traditional AMMs that rely on external liquidity providers depositing pairs of assets into pools, liquidity on the DEX is established through direct token purchases.
* The token's own smart contract manages its internal ledger and price determination based on its specific framework (Stable+ or Floor+) and the bonding curve during the initial phase.
* **Buys mint** new tokens, adding to supply at the current or new price. **Sells burn** tokens, removing them from circulation.
* No external LPs needed, no impermanent loss, no liquidity bootstrapping problem.

### Trading Fees

Fees are **platform-set by token type** — creators cannot change the rate:

| Token Type | Trading Fee | Applied On |
| ---------- | ----------- | ---------- |
| Stable+    | 0.5%        | Buy & Sell |
| Floor+     | 1.5%        | Buy & Sell |
| Predict+   | 0.5%        | Buy & Sell |

**Fee Distribution (Waterfall):**
Trading Fee → Creator (20%) → Bonding phase buyers (3.33%) → STASIS Vault (portion) → Platform Revenue (remainder) → 90% to BASIS Vault stakers as USDC + 10% platform operations.

### Buy Flow

Trading requires two contract calls:

1. **Approve** — ERC-20 approval for spend amount (can approve a higher amount to save gas on repeated trades)
2. **Buy** — Execute the trade

Quick allocation buttons (25%, 50%, 75%, Max) make it easy to size positions. Trade history and open positions are tracked per token per wallet.

### Price Impact

Price impact is visible before execution in the UI. For example, a $10 buy against $1,000 starting liquidity produces approximately 1.1% price impact. For Stable+ tokens, this retained slippage drives the up-only appreciation mechanism.

### MEV Mitigation

Internal liquidity mechanisms and architectural choices prevent sandwich attacks, front-running, and other value extraction tactics. Because liquidity is managed by the token's smart contract rather than external pools, common MEV strategies are economically non-viable.

## Leverage Trading

### Dynamic Leverage — Not Fixed 36x

Leverage on Basis is a **toggle** (on/off), not a slider. When enabled, effective leverage is **dynamic** — it depends on current pool liquidity and the size of the buy:

* Smaller buys = higher leverage (but smaller position sizes)
* Larger buys = lower leverage (price impact moves spot away from floor)
* **"Up to 36x" is the theoretical maximum** on well-established pools — not a guaranteed constant

### How Leverage Works

Leverage is calculated against the protected **floor price**:

* **Stable+ / Predict+:** Floor = spot price (always equal), so maximum leverage is permanently available
* **Floor+:** Highest leverage at/near launch (floor ≈ spot). Diminishes as spot price rises above floor

### The Leverage Fee

The leverage fee is **substantial and separate from the trading fee**:

| Buy Amount (Example: $1,000 starting liquidity) | Effective Leverage | Leverage Fee      | Price Impact |
| ------------------------------------------------ | ------------------ | ----------------- | ------------ |
| $5                                               | ~27.8x             | ~$3.53 (70.6%)    | 0.60%        |
| $20                                              | ~26.8x             | ~$13.66 (68.3%)   | 2.38%        |
| $100                                             | ~16.7x             | ~$43.79 (43.8%)   | 11.90%       |

{% hint style="info" %}
**Key insight:** The leverage fee percentage decreases with larger buys, but absolute cost increases significantly. On low-liquidity pools, even moderate buys create heavy price impact. Consider splitting large leveraged positions into smaller buys, or wait for liquidity to build.
{% endhint %}

### Zero Liquidation Risk

Leveraged positions **cannot be liquidated** due to price movements:
* Stable+ tokens can never decrease in price, so the floor is always at or above entry
* Floor+ tokens have a rising floor that provides the same protection

This eliminates the 90%+ liquidation rate seen in traditional leverage trading.

### Important Limitations

* Leveraged tokens are held in the leverage contract — they show as "Open Positions," not regular holdings
* **Leveraged tokens cannot be used as loan collateral** — leverage and loans are separate paths
* Agents/traders control effective exposure through position splitting: e.g., 25% leveraged + 75% unleveraged = ~10x effective exposure
