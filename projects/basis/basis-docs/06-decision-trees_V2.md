# Decision Trees

**What this covers:** 4 decision trees for the most common situations on Basis.
**Related sections:** â†’ See: [02-archetypes.md](02-archetypes.md) to identify your role Â· â†’ See: [04-strategies.md](04-strategies.md) for full playbooks Â· â†’ See: [03-atomic-skills.md](03-atomic-skills.md) for method signatures Â· â†’ See: [09-fees.md](09-fees.md) before committing to loans or leverage

---

## Decision Trees

---

### "I have idle USDB"

```
How long will it be idle?
â”œâ”€â”€ Hours â†’ Leave as USDB
â”œâ”€â”€ Days â†’ Buy STASIS â†’ Stake in vault (earn yield + airdrop points daily)
â”‚         â†’ see: trading.buy() then staking.buy()
â”œâ”€â”€ Weeks â†’ Stake + lock as collateral (ready to borrow if opportunity appears)
â”‚         â†’ see: staking.lock()
â””â”€â”€ Indefinitely â†’ Stake + deploy via vault borrowing
                  â†’ see: staking.borrow() â†’ deploy borrowed USDB
```

**Cross-refs**: â†’ See: [04-strategies.md â€” Strategy C](04-strategies.md) for the full Vault Compound playbook

---

### "I want exposure to token X"

```
How confident am I?
â”œâ”€â”€ Very confident â†’ Leverage buy (simulate first to check fee, amplified returns, no price liquidation)
â”‚                  â†’ see: leverageSimulator.simulateLeverage() FIRST
â”‚                  â†’ see: trading.leverageBuy()
â”œâ”€â”€ Confident â†’ Direct buy
â”‚              â†’ see: trading.buy()
â”œâ”€â”€ Somewhat â†’ Smaller position, or prediction market bet
â”‚              â†’ see: predictionMarkets.buy()
â””â”€â”€ Unsure â†’ Create a prediction market about it (earn fees either way)
            â†’ see: predictionMarkets.createMarketWithMetadata()
```

**Important**: Always simulate leverage before executing. Effective fee varies significantly by position size and pool depth.

---

### "I need liquidity but don't want to sell"

```
What do I hold?
â”œâ”€â”€ STASIS (in vault) â†’ Lock + borrow (2% origination + 0.005%/day, keep yield + exposure)
â”‚                      â†’ see: staking.lock() â†’ staking.borrow()
â”œâ”€â”€ Factory token â†’ Direct loan (2% fee, keep token exposure)
â”‚                  â†’ see: loans.takeLoan()
â”œâ”€â”€ Vested tokens â†’ Loan on vesting (access liquidity pre-unlock)
â”‚                  â†’ see: vesting.takeLoanOnVesting()
â””â”€â”€ Nothing stakeable â†’ Sell the least volatile position
                       â†’ see: trading.sell() or trading.sellPercentage()
```

**Loan cost reminder**: 2% flat origination fee + 0.005%/day interest. Always take minimum duration (10 days) and extend as needed â€” never re-originate.
**Cross-refs**: â†’ See: [09-fees.md](09-fees.md) for total cost calculations Â· â†’ See: [13-mistakes.md](13-mistakes.md) for loan pitfalls

---

### "I want to start a business"

```
Do I have capital?
â”œâ”€â”€ Yes â†’ Launch token with initial buy, set up vesting, create related markets
â”‚        â†’ see: factory.createTokenWithMetadata()
â”‚        â†’ see: vesting.createGradualVesting() (for team/investors)
â”‚        â†’ see: predictionMarkets.createMarketWithMetadata() (for community engagement)
â”œâ”€â”€ Some â†’ Launch token, focus on community building for organic volume
â”‚         â†’ see: factory.createTokenWithMetadata()
â”‚         â†’ see: api.requestTwitterChallenge() + api.verifyTwitter()
â””â”€â”€ No â†’ Launch token (minimal cost), earn dev fees from others' trades,
        resolve markets for bounties, reinvest earnings
        â†’ see: factory.createTokenWithMetadata()
        â†’ see: resolver.proposeOutcome() + resolver.claimBounty()
```

**Key insight**: Token creation costs only the BNB creation fee (call `factory.getFeeAmount()`). You earn 20% of all trading fees on your token forever from the moment it launches.
**Cross-refs**: â†’ See: [02-archetypes.md â€” Token Creator](02-archetypes.md) for full playbook


---
