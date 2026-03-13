# Crypto Loans

## Borrowing Against Your Basis Tokens

Basis's integrated lending platform lets users access USDC liquidity by using their Basis Token holdings as collateral. The key innovation: **100% Loan-to-Value (LTV) ratios** with zero liquidation risk from price movements — mathematically possible because Stable+ tokens cannot decrease in value and Floor+ loans are calculated against the rising floor price.

### Loan Terms

| Parameter | Details |
| --------- | ------- |
| **Collateral Accepted** | Any Stable+ or Floor+ Basis Token |
| **Loan Currency** | USDC |
| **LTV — Stable+** | Up to 100% of current market value |
| **LTV — Floor+** | Up to 100% of current **floor price** (not market price) |
| **Loan Term** | 10 days minimum, 1,000 days maximum |
| **Interest** | All prepaid upfront — deducted from loan proceeds |
| **Repayment** | Exact loan amount in USDC. No added interest, no installments, no margin calls. |

### Loan Fees

Loan fees are **dynamic based on duration** — not a flat percentage:

| Loan Duration | Approximate Fee |
| ------------- | --------------- |
| 10 days       | ~2%             |
| 30 days       | ~2.2%           |
| 1,000 days    | ~7.1%           |

{% hint style="info" %}
These are **total fees**, not annualized rates. Compared to traditional DeFi lending rates of 5–15% per year, Basis loan costs are very competitive — especially for short-term borrowing.
{% endhint %}

All interest is prepaid upfront. The fee is deducted from loan proceeds, so you receive USDC minus the fee. During the loan period, there are zero payments due.

### How It Works

1. **Select collateral** — choose which Basis Tokens to lock
2. **Set loan term** — 10 to 1,000 days
3. **Approve + Create** — two contract calls (ERC-20 approve, then loan creation)
4. **Receive USDC** — loan amount minus the prepaid fee
5. **Repay anytime** — pay exact loan amount in USDC to reclaim tokens

Collateral is valued at the **floor price** (conservative valuation that protects the lending system).

### No Liquidation from Price Movements

This is Basis's most powerful lending innovation:

* **Stable+ collateral:** The token's price cannot decrease, so collateral value can never drop below the loan amount.
* **Floor+ collateral:** The loan is based on the rising floor price, which also cannot decrease. The loan remains protected as long as the market price stays at or above the floor.
* **Liquidation only occurs** if the loan is not repaid or extended by its maturity date — never from price depreciation.

### What Happens at Loan Expiry

If a loan is not repaid or extended by its maturity date:

* Collateral is **burned** (not sold on the open market) — eliminating liquidation cascades
* If the collateral value has increased above the loan amount, the borrower can **claim the excess** (the difference between current value and loan amount)
* No market impact from forced selling

### Loan Extension & Refinancing

Before loan expiry, borrowers can:

**Extend the term:**
* **Pay in USDC** — pay extension fee externally (always available)
* **Pay from collateral** — fee paid from the collateral's increased value (only if token appreciated)

**Refinance (borrow more):**
* Available when paying from collateral and the token has appreciated
* Borrow additional USDC against the new, higher collateral value
* Access growing value without selling positions or creating sell pressure

### Loan Stacking

Users can chain multiple loans: borrow USDC → purchase additional tokens → use those tokens as collateral for another loan. This creates cascading leverage. Approach with caution, understanding the cumulative fee obligations.

{% hint style="warning" %}
**Leveraged tokens cannot be used as loan collateral.** Leverage and loans are separate paths — you cannot combine both on the same tokens.
{% endhint %}

### Loan Management Dashboard

The loan dashboard shows all active and inactive loans with:

* Collateral amount and current value (excess above loan amount)
* Repay amount, total spent, cashed out, and P&L
* Time remaining with visual progress bar
* Three actions: **Repay**, **Extend**, **Sell** (voluntary liquidation — burns collateral, you receive value above loan amount)

#### Example: Stable+ Loan

1. Lock 100 tokens (valued at $100) as collateral
2. Receive ~$98 USDC (100% LTV minus ~2% fee for a 10-day loan)
3. After 10 days, repay $100 USDC → reclaim 100 tokens
4. If tokens appreciated to $150 during the loan period, you can extend and refinance for additional USDC

### The wSTASIS Vault — Advanced Lending

For more sophisticated capital management, the **STASIS Vault** allows wrapping STASIS into wSTASIS (which only appreciates in value), then borrowing against it at 100% LTV. The vault position earns yield, serves as collateral, appreciates, and provides USDC liquidity — all simultaneously. See the [BASIS Utility Token](basis-utility-token.md) section for details on the vault.
