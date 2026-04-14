# Basis Platform Fee Schedule — Single Source of Truth
_Last updated: 2026-03-16 — loan fees + tax rates confirmed by Alex from contract source_
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

### Confirmed Values from ATaxes Contract (2026-03-16, from Alex)

| Variable | Value | Meaning |
|---|---|---|
| `_taxRateXether` (STASIS) | 50 | 0.50% trading fee |
| `_taxRateStable` (Stable+) | 50 | 0.50% base + surge |
| `_taxRateDefault` (Floor+) | 150 | 1.50% base + surge |
| `_taxRatePrediction` | 150 | 1.50% |
| `injectRate` | 16 | 16% of fee → wSTASIS Vault |
| `devRate` | 20 | 20% of fee → Creator |
| `presaleRate` | 4 | 4% of fee → Bonding phase buyers |
| Platform remainder | 60% | 100% - 20% - 16% - 4% = 60% → platform revenue |

**⚠️ These splits are provisional (2026-03-16).** Alex noted the distribution will likely change once the staking contract is built to fit the final staking model. Current values reflect deployed contract state, not final tokenomics.

### Remaining Questions

1. For Predict+: what % of the fee goes to the bounty pot vs the standard waterfall?
2. Does `presaleRate` only apply during bonding phase, or always?
3. Is the platform remainder (60%) split 90/10 (stakers/ops), or different?

**Notes:**
- Fees are set by the platform per token type — creators cannot change the rate
- Creators control the SPLIT of their 20% share via Dev Tax Sharing (up to 10 wallets, total ≤ 100%)
- The `devRate()`, `injectRate()`, and `presaleRate()` functions on ATaxes return the system-wide distribution percentages
- Surge tax (creator-controlled on Floor+) adds on top of the base fee and follows the same distribution waterfall

---

## Loan Fees

| Component | Rate | Notes |
|---|---|---|
| Static fee (origination) | `staticFeePercentage = 200` → **2.0%** flat | One-time, on every loan. Set on MAIN_TOKEN/STASIS contract. |
| Dynamic fee (interest) | `dynamicFeePercentage = 5` → **0.005% per day** | Scales linearly with loan duration. Set on MAIN_TOKEN/STASIS contract. |
| **Total fee (origination + interest)** | **2.0% + (0.005% × days)** | All prepaid upfront, deducted from loan proceeds |

**Example total fees:**
| Duration | Static | Dynamic | Total |
|---|---|---|---|
| 10 days | 2.0% | 0.05% | **~2.05%** |
| 30 days | 2.0% | 0.15% | **~2.15%** |
| 365 days | 2.0% | 1.825% | **~3.83%** |
| 1,000 days | 2.0% | 5.0% | **~7.0%** |

**⚠️ Important:** Loan fees are set on the **MAIN_TOKEN / STASIS** contract, NOT on ATaxes.

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

## Surge Tax (Creator-Controlled)

| Parameter | Value |
|---|---|
| Quota | 7 days per rolling window (pruned history) |
| Min duration | 1 hour |
| Rate | Creator-set `startRate` → `endRate` (decays linearly over duration) |
| Max rate (Stable+, multiplier=100) | 0.50% (maxRate=50) |
| Max rate (Floor+) | Depends on hybridMultiplier: `rawMax = 1500 - ((mult-1)*1400/89)`, snapped to 50-step, min 1.0% |
| Floor+ range | ~1.0% (multiplier=90) to 15.0% (multiplier=1) |
| Min start rate | 0.10% (startRate ≥ 10) |
| Who controls | Token DEV (`msg.sender == token.DEV()`) only |
| Applies to | Stable+ and Floor+ (added on top of base tax rate). NOT separately applied to STASIS or Prediction tokens. |

**Source:** `ATaxes.startSurgeTax()` — confirmed from contract code 2026-03-16.

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
