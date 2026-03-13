# BASIS Utility Token

## Summary

The **BASIS** utility token has a pure yield tokenomics model where 90% of platform revenue flows directly to stakers as USDC. The token model provides clarity on how to earn tokens (Points System), how to maximize allocation (Lockdrop), and how to earn yield (Rev Share Vesting).

{% hint style="info" %}
**Important distinction:** BASIS is the platform's utility/governance token (sold to investors, staked for platform revenue share). STASIS is the system's liquidity token (a Stable+ token paired with USDC, serving as the base pair for all other tokens). They serve different roles.
{% endhint %}

### The Pure Yield Philosophy

> "BASIS does not rely on buybacks or token burns for price support. Instead, we deliver real value: 90% of every dollar the platform earns goes directly to stakers as USDC. Token value derives from yield, not speculation."

### Key Innovations

1. **Activity-Based Points System:** Tokens earned through genuine platform usage, not passive holding.
2. **Lockdrop Mechanism (50%–130%):** Pre-TGE commitment determines allocation. Founder tier receives 130%.
3. **Rev Share Vesting:** All presale tokens staked at TGE, earning USDC yield throughout lock.
4. **Hard-Locked Presales:** ALL presale participants (Seed through Public) locked with no early exit.
5. **90% Revenue to Stakers:** Industry-leading revenue share distributed as USDC.
6. **42% Community Allocation:** Creator Airdrop + User Airdrop + Founder Bonus + Emissions.
7. **Post-TGE Incentive Reserve:** Unused Founder Bonus redirected to incentivize ongoing staking.

### Capital Formation Summary

| Metric                   | Value               |
| ------------------------ | ------------------- |
| Total Presale Raise      | $30,000,000 USDC    |
| Protocol-Owned Liquidity | $5,000,000 USDC     |
| Operating Treasury       | $25,000,000 USDC    |
| Total Token Supply       | 1,000,000,000 BASIS |
| TGE Price                | $0.10               |
| Fully Diluted Valuation  | $100,000,000        |

## Notice-Based Staking

Unlike traditional fixed-lock staking, BASIS uses a **notice-based system**. Holders earn yield continuously and can initiate withdrawal at any time — tokens unlock after the notice window completes.

### Staking Tiers

| Tier       | Notice Period                  | Multiplier | Notes                                       |
| ---------- | ------------------------------ | ---------- | ------------------------------------------- |
| Flexible   | 30 days                        | 1.0x       | Easy entry, easy exit                        |
| Standard   | 90 days                        | 1.5x       | Moderate commitment                          |
| Committed  | 180 days                       | 2.5x       | Serious holders                              |
| Diamond    | 365 days                       | 4.0x       | Long-term believers                          |
| Founder    | 365 days + 6mo initial lock    | 6.0x       | Must complete 6mo mandatory lock first       |

**Why notice-based:**
* No cliff unlock dates = no coordinated exit events or dump risk
* Holders stay because they're earning, not because they're trapped
* Still earning yield during the notice window
* Can cancel notice and upgrade to a higher tier anytime

### Revenue Distribution

90% of ALL platform revenue is distributed as USDC to stakers, weighted by tier multiplier and amount staked.

**Revenue sources:**
* DEX trading fees (net of creator/bonding/vault shares)
* Lending fees
* Predict+ event fees

**APY Projections (Diamond Tier, 50% Supply Staked):**

| Scenario     | Annual Revenue | Diamond APY |
| ------------ | -------------- | ----------- |
| Conservative | $20M           | 28.1%       |
| Base Case    | $40M           | 56.2%       |
| Bullish      | $75M           | 105.3%      |

## The STASIS Vault (wSTASIS)

The STASIS Vault is separate from BASIS staking. It allows users to wrap STASIS into **wSTASIS**, which has a guaranteed only-up share price.

### How It Works

1. **Wrap:** Convert STASIS → wSTASIS at current share price
2. **Lock:** Deposit wSTASIS into collateral pool (reversible if no loan exists)
3. **Borrow:** Draw USDC at 100% LTV against locked wSTASIS (no liquidation risk — wSTASIS only goes up)
4. **Appreciate:** Ecosystem revenue flows into the vault → wSTASIS share price rises → collateral value increases
5. **Borrow more:** As collateral appreciates, draw additional USDC without depositing more wSTASIS

### Three wSTASIS States

| State | Description | Constraints |
| ----- | ----------- | ----------- |
| **Liquid wSTASIS** | Wrapped but free | Can unwrap to STASIS anytime |
| **Locked wSTASIS** | Deposited into collateral pool | Can unlock anytime unless loan exists |
| **Loan-locked wSTASIS** | Locked with active loan | Can't unlock until loan repaid |

### Revenue Source

A portion of trading fees (previously injected into STASIS liquidity) now feeds the vault, raising the wSTASIS share price perpetually. Current share price: **1 wSTASIS = 5.8654 STASIS** (significant appreciation already achieved).

## Two Vaults — Key Distinction

| Feature | STASIS Vault (wSTASIS) | BASIS Vault (Post-TGE) |
| ------- | ---------------------- | ---------------------- |
| Revenue source | Trading fee portion | 90% of net platform revenue |
| Token behavior | wSTASIS only goes up (guaranteed) | BASIS price fluctuates |
| Yield currency | Appreciation in STASIS terms | USDC distributions |
| Loans available | Yes (100% LTV, no liquidation) | No — can't safely lend against volatile collateral |
| Status | Live now | Post-TGE |

### Fee Waterfall

Trading Fee → Creator (20%) → Bonding phase buyers → STASIS Vault (portion) → Platform Revenue (remainder) → 90% to BASIS Vault stakers as USDC + 10% platform operations
