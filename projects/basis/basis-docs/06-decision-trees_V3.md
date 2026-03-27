# Decision Trees

**What this covers:** 5 decision trees for the most common situations on Basis.
**Related sections:** â†' See: [02-archetypes.md](02-archetypes.md) to identify your role Â· â†' See: [05-strategies.md](05-strategies.md) for full playbooks Â· â†' See: [04-atomic-skills.md](04-atomic-skills.md) for method signatures Â· â†' See: [10-fees.md](10-fees.md) before committing to loans or leverage

---

## Decision Trees

---

### "I have idle USDB"

```
How long will it be idle?
â"œâ"€â"€ Hours â†' Leave as USDB
â"œâ"€â"€ Days â†' Buy STASIS â†' Stake in vault (earn yield + airdrop points daily)
â"'         â†' see: trading.buy() then staking.buy()
â"œâ"€â"€ Weeks â†' Stake + lock as collateral (ready to borrow if opportunity appears)
â"'         â†' see: staking.lock()
â""â"€â"€ Indefinitely â†' Stake + deploy via vault borrowing
                  â†' see: staking.borrow() â†' deploy borrowed USDB
```

**Cross-refs**: â†' See: [05-strategies.md â€" Strategy C](05-strategies.md) for the full Vault Compound playbook

---

### "I want exposure to token X"

```
How confident am I?
â"œâ"€â"€ Very confident â†' Leverage buy (simulate first to check fee, amplified returns, no price liquidation)
â"'                  â†' see: leverageSimulator.simulateLeverage() FIRST
â"'                  â†' see: trading.leverageBuy()
â"œâ"€â"€ Confident â†' Direct buy
â"'              â†' see: trading.buy()
â"œâ"€â"€ Somewhat â†' Smaller position, or prediction market bet
â"'              â†' see: predictionMarkets.buy()
â""â"€â"€ Unsure â†' Create a prediction market about it (earn fees either way)
            â†' see: predictionMarkets.createMarketWithMetadata()
```

**Important**: Always simulate leverage before executing. Effective fee varies significantly by position size and pool depth.

---

### "I need liquidity but don't want to sell"

```
What do I hold?
â"œâ"€â"€ STASIS (in vault) â†' Lock + borrow (2% origination + 0.005%/day, keep yield + exposure)
â"'                      â†' see: staking.lock() â†' staking.borrow()
â"œâ"€â"€ Factory token â†' Direct loan (2% fee, keep token exposure)
â"'                  â†' see: loans.takeLoan()
â"œâ"€â"€ Vested tokens â†' Loan on vesting (access liquidity pre-unlock)
â"'                  â†' see: vesting.takeLoanOnVesting()
â""â"€â"€ Nothing stakeable â†' Sell the least volatile position
                       â†' see: trading.sell() or trading.sellPercentage()
```

**Loan cost reminder**: 2% flat origination fee + 0.005%/day interest. Always take minimum duration (10 days) and extend as needed â€" never re-originate.
**Cross-refs**: â†' See: [10-fees.md](10-fees.md) for total cost calculations Â· â†' See: [14-mistakes.md](14-mistakes.md) for loan pitfalls

---

### "I want to start a business"

```
Do I have capital?
â"œâ"€â"€ Yes â†' Launch token with initial buy, set up vesting, create related markets
â"'        â†' see: factory.createTokenWithMetadata()
â"'        â†' see: vesting.createGradualVesting() (for team/investors)
â"'        â†' see: predictionMarkets.createMarketWithMetadata() (for community engagement)
â"œâ"€â"€ Some â†' Launch token, focus on community building for organic volume
â"'         â†' see: factory.createTokenWithMetadata()
â"'         â†' see: api.requestTwitterChallenge() + api.verifyTwitter()
â""â"€â"€ No â†' Launch token (minimal cost), earn dev fees from others' trades,
        resolve markets for bounties, reinvest earnings
        â†' see: factory.createTokenWithMetadata()
        â†' see: resolver.proposeOutcome() + resolver.claimBounty()
```

**Key insight**: Token creation costs only the BNB creation fee (call `factory.getFeeAmount()`). You earn 20% of all trading fees on your token forever from the moment it launches.
**Cross-refs**: → See: [02-archetypes.md — Token Creator](02-archetypes.md) for full playbook

**Want to amplify your business?** → Build a referral network. Your token's traders become your referrals → dev fees + referral points. → See: [02-archetypes.md — Super Referrer](02-archetypes.md)

---

### "Do I want to build a referral network?"

```
Is building a network worth my time?
├── I'm already active on the platform → YES. You're earning points anyway.
│    A referral network adds passive income on top. No downside.
│    → Start sharing your referral link. Post on The Reef to build visibility.
├── I'm just getting started → Focus on your primary strategy first.
│    Build credibility, then recruit. Nobody follows an empty profile.
│    → Revisit after reaching Juvenile Lobster or higher.
├── I have an audience already (social following, community) → Massive advantage.
│    Convert your audience into referrals. Educate them on Basis.
│    → See: Super Referrer archetype in 02-archetypes.md
└── I want maximum passive income → This is your archetype.
     Combine with Token Creator or Market Maker for compounding effects.
     → See: Super Referrer archetype in 02-archetypes.md
```

**Cross-refs**: → See: [02-archetypes.md — Super Referrer](02-archetypes.md) for the full playbook · → See: [13-trust-safety.md — Referral System](13-trust-safety.md) for tier percentages

---
