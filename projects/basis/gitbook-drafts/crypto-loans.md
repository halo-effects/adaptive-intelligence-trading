# Crypto Loans

## Borrowing Against Your Basis Tokens

Basis's integrated lending platform offers a unique and flexible way for users to access liquidity (in USDC) by using their existing Basis Token holdings as collateral. A key innovation is 100% Loan-to-Value (LTV) ratios with zero liquidation risk from price movements, especially concerning price volatility of the collateral.

### Loan Terms and Loan-to-Value (LTV) Ratios

**Loan Term:** Users can select a fixed loan term ranging from **10 to 1,000 days**.

**Collateral Accepted:** Any Stable+ or Floor+ Basis Token held by the user.

**Loan Currency:** Loans are disbursed in USDC.

**LTV for Stable+ Tokens:** Up to 100% LTV based on the current market value of the Stable+ token collateral. Since Stable+ token prices are designed not to decrease, this offers a high degree of confidence.

**LTV for Floor+ Tokens:** Up to 100% LTV, but the maximum loan amount is calculated based on the token's current **floor price**, not its potentially higher fluctuating market price.

* Max Loan Value (Floor+) = Number of Floor+ Tokens Collateralized \* Current Floor Price of that Token

### Loan Fees

Loan fees are **dynamic based on duration** — not a flat percentage. All interest is prepaid upfront and deducted from loan proceeds. You receive USDC minus the fee, and during the loan period there are zero payments due.

| Loan Duration | Approximate Fee |
| ------------- | --------------- |
| 10 days       | ~2%             |
| 30 days       | ~2.2%           |
| 1,000 days    | ~7.1%           |

{% hint style="info" %}
These are **total fees**, not annualized rates. Compared to traditional DeFi lending rates of 5–15% per year, Basis loan costs are very competitive — especially for short-term borrowing.
{% endhint %}

**Repayment:** Pay the exact loan amount (collateral value) in USDC to reclaim your tokens. No added interest, no installments, no margin calls during the loan period.

### No Liquidation Risk from Collateral Price Depreciation

* For Stable+ collateral, since the token's price cannot decrease, the value of the collateral will not drop below the loan amount due to market volatility.
* For Floor+ collateral, since the loan value is based on its "rising floor price," and this floor price cannot decrease, the loan remains protected against liquidation caused by the market price of the Floor+ token falling (as long as it stays above or at the floor). Liquidation only occurs if the loan is not repaid or extended by its maturity date.

**On non-payment at maturity:** Collateral is **burned** (not sold on the open market), eliminating liquidation cascades. If the collateral value has increased above the loan amount, the borrower can **claim the excess** (the difference between current value and loan amount).

### Loan Stacking Potential

Users can potentially take out multiple loans. For example, a user could borrow USDC against their Basis Token, use that USDC to purchase another Basis Token, and then use that newly acquired Basis Token as collateral for a second loan. This should be approached with caution, understanding the cumulative fee obligations.

{% hint style="warning" %}
**Leveraged tokens cannot be used as loan collateral.** Leverage and loans are separate paths — you cannot combine both on the same tokens.
{% endhint %}

### Loan Extension with Potential Cash Out

* Borrowers have the option to extend their loan term before the maturity date.
* **Two extension modes:**
  * **Pay in USDC:** Pay extension fee externally in USDC. Always available.
  * **Pay from collateral:** Fee paid from the collateral's increased value. Only available if the token has appreciated. This also unlocks **Refinancing (Borrow Extra)** — borrow additional USDC against the new, higher collateral value.
* Extension fees are duration-based (dynamic, same structure as origination fees).

#### Example Loan (Stable+ Collateral):

<details>

<summary>Initial Loan: 100 tokens (valued at $100) as collateral.</summary>

**Loan:** $100 USDC at 100% LTV, minus ~2% fee for 10-day term = ~$98 received.

After 10 days, tokens have appreciated to $150.

Borrower extends for another 100 days.

New Max Loan Value = $150 USDC.

**Extension fees:** Dynamic based on new duration and amount.

**Cash Out** = New Max Loan Value – Old Loan Balance – New Fees.

The new outstanding loan becomes $150 USDC.

</details>

### Loan Management

Three actions available for active loans:

* **Repay:** Pay exact loan amount in USDC → get tokens back
* **Extend:** Extend the term with fee payment in USDC or from collateral appreciation
* **Sell (voluntary liquidation):** Burns collateral, you receive any value ABOVE the loan amount in USDC. Partial sell available (10–100% slider). If token hasn't increased, you receive $0.

### Loan Dashboard

The loan dashboard shows active and inactive loans with:

* Collateral amount and current value (excess above loan amount)
* Repay amount, total spent, cashed out, and P&L
* Time remaining with visual progress bar
