# Basis Platform Fee Schedule — Single Source of Truth
_Last updated: 2026-03-14_
_Referenced by all project docs. Update HERE first, then propagate._

---

## Trading Fees (platform-set, not creator-configurable)

| Token Type | Trading Fee | Applied On |
|---|---|---|
| Stable+ (incl. STASIS) | 0.5% | Buy & Sell |
| Floor+ | 1.5% | Buy & Sell |
| Predict+ | 1.5% | Buy & Sell |

### Fee Distribution — Stable+ (0.5% total fee)

| Recipient | % of Fee | Effective Rate | Notes |
|---|---|---|---|
| Creator (Dev Tax) | 20% | 0.10% | Controllable via Dev Tax Sharing (up to 10 wallets) |
| Bonding phase buyers (Presale) | <!-- TODO: confirm % --> | <!-- TODO --> | Reward Shares — 3.33% cited in docs, verify against `presaleRate()` |
| wSTASIS Vault (Inject) | <!-- TODO: confirm % --> | <!-- TODO --> | Portion that feeds vault yield. Query `injectRate()` on ATaxes |
| Platform Revenue | <!-- TODO: remainder --> | <!-- TODO --> | After all other distributions |
| → 90% to BASIS stakers | | | As USDC yield |
| → 10% platform operations | | | |

### Fee Distribution — Floor+ (1.5% total fee)

| Recipient | % of Fee | Effective Rate | Notes |
|---|---|---|---|
| Creator (Dev Tax) | 20% | 0.30% | Controllable via Dev Tax Sharing (up to 10 wallets) |
| Bonding phase buyers (Presale) | <!-- TODO: confirm % --> | <!-- TODO --> | Same `presaleRate()` as Stable+? Or different? |
| wSTASIS Vault (Inject) | <!-- TODO: confirm % --> | <!-- TODO --> | Query `injectRate()` on ATaxes |
| Platform Revenue | <!-- TODO: remainder --> | <!-- TODO --> | After all other distributions |
| → 90% to BASIS stakers | | | As USDC yield |
| → 10% platform operations | | | |

### Fee Distribution — Predict+ (1.5% total fee)

| Recipient | % of Fee | Effective Rate | Notes |
|---|---|---|---|
| Creator (Dev Tax) | 20% | 0.30% | Controllable via Dev Tax Sharing (up to 10 wallets) |
| Bonding phase buyers (Presale) | <!-- TODO: confirm % --> | <!-- TODO --> | Same as other types? |
| Bounty Pot | <!-- TODO: confirm % --> | <!-- TODO --> | Flows to winning outcome shareholders. Unique to Predict+. |
| wSTASIS Vault (Inject) | <!-- TODO: confirm % --> | <!-- TODO --> | Query `injectRate()` on ATaxes |
| Platform Revenue | <!-- TODO: remainder --> | <!-- TODO --> | After all other distributions |
| → 90% to BASIS stakers | | | As USDC yield |
| → 10% platform operations | | | |

### Fee Distribution — Summary Waterfall

```
Trading Fee (0.5% or 1.5%)
  ├── Creator / Dev Tax (20% of fee) — `devRate()` on ATaxes
  │     └── Split across up to 10 wallets via Dev Tax Sharing
  ├── Bonding Phase Buyers / Presale — `presaleRate()` on ATaxes
  ├── [Predict+ only] Bounty Pot — portion to winning outcome pool
  ├── wSTASIS Vault / Inject — `injectRate()` on ATaxes
  └── Platform Revenue (remainder)
        ├── 90% → BASIS Vault (USDC yield to stakers)
        └── 10% → Platform operations
```

### Questions for Alex (to complete the distribution)

1. What are the current values of `injectRate()`, `devRate()`, and `presaleRate()` on ATaxes?
2. Are these rates the same across all token types (Stable+, Floor+, Predict+)?
3. For Predict+: what % of the fee goes to the bounty pot vs the standard waterfall?
4. Does the distribution change during vs after the bonding phase? (i.e., does presaleRate only apply during bonding?)
5. Is the "90% to BASIS stakers" calculated after ALL other distributions, or is there a specific `platformRate()`?

**Notes:**
- Fees are set by the platform per token type — creators cannot change the rate
- Creators control the SPLIT of their 20% share via Dev Tax Sharing (up to 10 wallets, total ≤ 100%)
- The `devRate()`, `injectRate()`, and `presaleRate()` functions on ATaxes return the system-wide distribution percentages
- Surge tax (creator-controlled on Floor+) adds on top of the base fee and follows the same distribution waterfall

---

## Loan Fees

| Component | Rate | Notes |
|---|---|---|
| Origination fee | ~2–2.5% flat | One-time, on every loan. <!-- TODO: confirm exact current rate with Alex --> |
| Interest | Dynamic, based on duration | Increases with longer loan terms |
| **Total fee (origination + interest)** | **~2% (10-day loan) to ~7% (1,000-day loan)** | All prepaid upfront, deducted from loan proceeds |

**Loan Terms:**
- Duration: 10 days minimum, 1,000 days maximum
- LTV: 100% of floor price (Stable+ floor = spot; Floor+ floor < spot)
- Repayment: Exact loan amount in USDC. No installments, no margin calls.
- Non-payment at maturity: Collateral is burned (not sold). Excess value above loan claimable by borrower.
- Extension fee: Duration-based, payable in USDC or from collateral appreciation
- Leveraged tokens CANNOT be used as loan collateral

---

## Leverage Fees

| Component | Rate | Notes |
|---|---|---|
| Leverage fee | 43–70% of collateral (small buys) | Decreases as percentage with larger positions, but absolute cost increases |

**Notes:**
- Separate from trading fee
- Substantial — agents should use `simulateLeverage()` to preview before executing
- Leverage is dynamic: up to 36x in optimal conditions, fluctuates with buy size and pool liquidity

---

## Token Creation Fees

| Fee | Amount | Notes |
|---|---|---|
| Gas cost | ~$0.14 BNB | Single contract call |
| Platform fee | $0 | No platform fee for token creation |
| ETH/BNB fee | `feeAmount()` on ATokenFactory | <!-- TODO: confirm if this is always 0 or variable --> |

---

## Prediction Market Creation Fees

| Fee | Amount | Notes |
|---|---|---|
| Gas cost | TBD | <!-- TODO: measure real-world gas cost --> |
| Platform fee | Factory fee (same as token creation) | <!-- TODO: confirm --> |

---

## Vault Fees

| Action | Fee | Notes |
|---|---|---|
| Wrap STASIS → wSTASIS | None | Free to wrap/unwrap |
| Vault loan fees | Same as standard loan fees | 100% LTV, no liquidation (wSTASIS only goes up) |

---

## Surge Tax (Creator-Controlled, Floor+ only)

| Parameter | Value |
|---|---|
| Quota | 7 days per 30-day rolling window |
| Rate | Creator-set start rate → end rate (decays linearly) |
| Max rate | Depends on hybridMultiplier |
| Who controls | Token DEV only |

---

## Platform Access Fees

| Fee | Amount |
|---|---|
| Account creation | Free |
| Platform access | Free |
| API access | Free (rate-limited: 60 req/min) |
| SIWE authentication | Free |
| Discussion comments | Free (requires ≥$5 trade on the project) |

---

_When updating fees: change this file first, then search all docs for the old value and update them._
