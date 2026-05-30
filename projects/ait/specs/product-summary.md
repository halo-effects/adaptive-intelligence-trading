# AIT V14 Portfolio Manager — Product & Business Summary

**Date**: 2026-05-08
**Version**: 1.0
**Author**: Halo Effects

---

## The Product

AIT (Adaptive Intelligence Trading) is a signal-driven portfolio management platform for cryptocurrency perpetual futures. The platform uses proprietary algorithms to identify high-probability DCA (Dollar Cost Averaging) entry and exit opportunities across 45+ cryptocurrency pairs, distributing actionable signals to subscribers who execute trades on their own exchange accounts.

### How It Works

1. **Signal Generation (Mothership)**: Proprietary cycle scanner analyzes coin-level DCA velocity, macro regime indicators, and trend acceleration to produce ranked coin signals with entry/exit timing.

2. **Signal Distribution**: Subscribers receive real-time signals via secure API — which coins to trade, when to enter/exit, regime direction (long/short/neutral), and per-coin trend multipliers for capital weighting.

3. **Automated Execution (Client)**: A lightweight execution client runs on the subscriber's infrastructure, connected to their own exchange account with their own API keys. The client receives signals and executes DCA trades according to the subscriber's configured risk profile and capital allocation.

4. **Portfolio Management**: The client manages position sizing, trailing take-profit orders, capital rotation between coins, and safety mechanisms — all calibrated to the subscriber's equity and risk tolerance.

### Performance (Live Trading)

- **88 completed trades** on live exchange (Aster DEX perpetuals)
- **83% win rate** (73 wins, 15 losses)
- **$135.05 realized PnL** on ~$375 starting capital
- **1.0x leverage** (no leverage — spot-equivalent risk)
- **Average trade duration**: Hours to days (not HFT)
- **Active since**: March 2026

---

## Architecture

```
┌──────────────────────────────────────┐
│          MOTHERSHIP                  │
│      (Halo Effects Cloud)            │
│                                      │
│   ┌──────────────┐                   │
│   │ Cycle Scanner │──→ Coin Rankings │
│   └──────────────┘                   │
│   ┌──────────────┐                   │
│   │ Regime Detect │──→ Long/Short    │
│   └──────────────┘                   │
│   ┌──────────────┐                   │
│   │ Trend Mults  │──→ Weightings    │
│   └──────────────┘                   │
│           │                          │
│     Signal API (encrypted)           │
│           │                          │
│   Fleet Dashboard (admin only)       │
└───────────┼──────────────────────────┘
            │
   ┌────────┼────────┬────────────┐
   ▼        ▼        ▼            ▼
┌──────┐ ┌──────┐ ┌──────┐ ┌──────────┐
│User A│ │User B│ │User C│ │ User D   │
│$10K  │ │$50K  │ │$5K   │ │ $200K    │
│HL    │ │HL    │ │OKX   │ │ Binance  │
│      │ │      │ │      │ │          │
│Own   │ │Own   │ │Own   │ │ Own      │
│keys  │ │keys  │ │keys  │ │ keys     │
│Own   │ │Own   │ │Own   │ │ Own      │
│risk  │ │risk  │ │risk  │ │ risk     │
└──────┘ └──────┘ └──────┘ └──────────┘
```

**Key principle**: Halo Effects never holds, controls, or has access to customer funds or exchange credentials. Subscribers maintain full custody at all times.

---

## Business Model

### Revenue: Signal Subscription (SaaS)

| Tier | Coin Slots | Features | Monthly |
|------|-----------|----------|---------|
| Starter | 3 coins | Signals, email alerts, basic dashboard | $49 |
| Pro | 10 coins | Full signals, real-time dashboard, Telegram, API access | $149 |
| Enterprise | Unlimited | Custom parameters, priority support, SLA, fleet API | $499 |

### Unit Economics

- **Mothership infrastructure**: ~$200-500/mo (cloud compute, exchange data feeds, monitoring)
- **Per-subscriber marginal cost**: Near zero (signals are broadcast)
- **Break-even**: ~5 Pro subscribers ($745/mo)
- **At 50 subscribers** (mix): ~$5,000-7,000/mo revenue
- **At 200 subscribers** (mix): ~$20,000-30,000/mo revenue
- **Gross margin at scale**: >95%

### Alternative: Hybrid Performance Model
- Lower base ($29/mo) + 10% of realized profits
- Better alignment with high-capital subscribers
- Requires profit tracking infrastructure

---

## Regulatory & Liability Posture

### What This Model Is

AIT is a **Software-as-a-Service platform that provides market analysis signals**. It is:

- **A SaaS product** — subscribers pay for access to analytical signals delivered via API
- **Non-custodial** — Halo Effects never holds, manages, or has access to customer funds
- **Self-directed execution** — subscribers choose whether and how to act on signals using their own exchange accounts
- **API key isolation** — customer exchange credentials are stored locally on the customer's own infrastructure, never transmitted to or stored by Halo Effects

### Structural Liability Protections

**1. No Custody = No Custodial Liability**
Halo Effects never touches customer assets. There is no commingling of funds, no escrow, no pooled investment vehicle. Each subscriber maintains their own exchange account with their own deposit, withdrawal, and trading authority. This eliminates the entire class of custodial liability, fiduciary duty over assets, and insurance requirements that apply to fund managers and custodians.

**2. SaaS End User License Agreement (EULA)**
All subscribers agree to terms that include:
- Signals are informational and analytical in nature, not personalized investment advice
- Past performance does not guarantee future results
- Subscriber assumes full responsibility for their trading decisions and exchange account
- No guaranteed returns or representations of specific outcomes
- Limitation of liability capped at subscription fees paid
- Indemnification for losses arising from subscriber's use of signals
- Subscriber confirms they understand the risks of cryptocurrency trading

**3. Subscriber Self-Determination**
The execution client is configurable by the subscriber:
- They choose their own exchange
- They set their own risk limits (max drawdown, position sizes, daily loss limit)
- They can pause, override, or ignore any signal
- They can close any position at any time via their exchange or the dashboard
- The bot operates on THEIR infrastructure with THEIR credentials

**4. No Personalized Advice**
Signals are generated algorithmically and distributed uniformly to all subscribers in a tier. There is no personalized recommendation based on an individual subscriber's financial situation, goals, or risk tolerance. This is a key distinction from investment advisory services.

### Regulatory Advantages of This Model

**Compared to a hedge fund or managed account:**
- No SEC/CFTC registration as an investment adviser or commodity trading advisor (subject to legal review — see below)
- No custody requirements or third-party audits of customer funds
- No Form ADV, Form D, or accredited investor requirements
- No performance fee regulations (if using flat subscription model)
- No commingling concerns

**Compared to a copy-trading platform:**
- No liability for execution quality (subscriber's exchange, subscriber's fills)
- No requirement to ensure best execution
- No exposure to subscriber's leverage decisions

**Compared to selling trading software outright:**
- IP stays protected (signal algorithms never leave mothership)
- Recurring revenue vs one-time sale
- Can revoke access for non-payment or ToS violation

### What Still Requires Legal Review

Despite the favorable structural position, several areas require formal legal counsel before launch:

**1. Investment Adviser Classification**
The SEC and state regulators define "investment adviser" broadly. Providing specific buy/sell signals for securities or commodities, even via SaaS, could potentially trigger registration requirements depending on:
- How signals are characterized in marketing materials
- Whether signals are considered "personalized" even if algorithmically generated
- Jurisdiction-specific definitions and exemptions
- Whether cryptocurrency perpetual futures are classified as commodities or securities in the relevant jurisdiction

**Recommendation**: Engage a securities attorney to review the signal distribution model and provide a formal opinion before accepting subscribers.

**2. CFTC Commodity Trading Advisor (CTA) Rules**
Cryptocurrency perpetual futures may fall under CFTC jurisdiction. Providing trading signals for futures contracts may require CTA registration or reliance on an exemption (e.g., fewer than 15 clients in prior 12 months, or signals are "impersonal" — published to a broad audience without tailoring).

**Recommendation**: Confirm applicability and available exemptions with counsel.

**3. State-Level Requirements**
Some US states have their own investment adviser registration requirements that may apply independently of federal thresholds.

**4. International Considerations**
If accepting subscribers outside the US:
- EU: MiFID II may apply to signal services depending on classification
- UK: FCA rules on investment research
- Australia: AFSL requirements

**5. Marketing Claims**
All marketing materials must avoid:
- Guarantees of returns or income
- Cherry-picked performance without full context
- Language that implies personalized advice
- Testimonials without proper disclaimers (SEC marketing rule)

### Recommended Legal Actions Before Launch

1. ☐ Retain securities attorney for product review and formal opinion letter
2. ☐ Draft EULA with proper risk disclosures, limitation of liability, arbitration clause
3. ☐ Draft Terms of Service covering signal accuracy disclaimers, uptime SLA, data handling
4. ☐ Review marketing materials for compliance
5. ☐ Determine CTA registration requirement or applicable exemption
6. ☐ Privacy policy (GDPR/CCPA compliant)
7. ☐ Evaluate LLC vs Corp structure for liability isolation
8. ☐ Consider E&O (errors and omissions) insurance

---

## Intellectual Property

| Asset | Location | Exposure |
|-------|----------|----------|
| Cycle scanner algorithm | Mothership only | Never distributed |
| Regime detection logic | Mothership only | Never distributed |
| Trend multiplier formulas | Mothership only | Never distributed |
| Coin ranking methodology | Mothership only | Scores shared, method hidden |
| DCA execution engine | Client bot | Distributed (commodity logic) |
| Signal protocol/format | Both | Documented for client integration |

The proprietary value — **what** to trade and **when** — remains exclusively on Halo Effects infrastructure. The execution client contains only the DCA mechanics (open-source equivalent logic available in many trading libraries). A subscriber who cancels loses access to signals; the execution client without signals has nothing to act on.

---

## Competitive Landscape

| Competitor | Model | AIT Advantage |
|------------|-------|---------------|
| 3Commas | Bot marketplace, user configures | AIT provides the signals + execution. Less user expertise needed. |
| Cornix | Signal following for Telegram groups | AIT's signals are algorithmically generated, not manual calls. Consistent, backtested. |
| Pionex | Exchange with built-in bots | AIT is exchange-agnostic. Not locked to one platform. |
| TradingView signals | Alert-based, user implements | AIT provides end-to-end: signal → execution → management. |
| Custom algo funds | Managed accounts | AIT is non-custodial. Lower regulatory burden. Subscriber keeps control. |

**AIT's moat**: Proprietary signal generation + turnkey execution + non-custodial model. The subscriber doesn't need to be a trader — they need a Hyperliquid account and a subscription.

---

## Summary

AIT is a signal-as-a-service platform with a proven DCA strategy (83% win rate, 88 live trades), a non-custodial architecture that keeps customer funds under their own control, and a SaaS business model with >95% gross margins at scale. The hub-and-spoke design protects intellectual property while creating defensible recurring revenue.

The structural advantages — no custody, no fund management, algorithmic signal distribution, subscriber self-execution — position the product favorably from a regulatory perspective compared to managed accounts or fund structures. Formal legal review is recommended before launch to confirm classification and available exemptions in target jurisdictions.

Phase 1 (5 beta users on Hyperliquid) is achievable in 6-10 weeks from the current codebase.
