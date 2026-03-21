# Decision Trees

**What this covers:** 4 decision trees for the most common situations on Basis.
**Related sections:** → See: [02-archetypes.md](02-archetypes.md) to identify your role · → See: [04-strategies.md](04-strategies.md) for full playbooks · → See: [03-atomic-skills.md](03-atomic-skills.md) for method signatures · → See: [09-fees.md](09-fees.md) before committing to loans or leverage

---

## Part 9 — Decision Trees

---

### "I have idle USDB"

```
How long will it be idle?
├─ Hours → Leave as USDB
├─ Days → Buy STASIS → Stake in vault (earn yield + airdrop points daily)
│         → see: trading.buy() then staking.buy()
├─ Weeks → Stake + lock as collateral (ready to borrow if opportunity appears)
│         → see: staking.lock()
└─ Indefinitely → Stake + deploy via vault borrowing
                  → see: staking.borrow() → deploy borrowed USDB
```

**Cross-refs**: → See: [04-strategies.md — Strategy C](04-strategies.md) for the full Vault Compound playbook

---

### "I want exposure to token X"

```
How confident am I?
├─ Very confident → Leverage buy (simulate first to check fee, amplified returns, no price liquidation)
│                  → see: leverageSimulator.simulateLeverage() FIRST
│                  → see: trading.leverageBuy()
├─ Confident → Direct buy
│              → see: trading.buy()
├─ Somewhat → Smaller position, or prediction market bet
│              → see: predictionMarkets.buy()
└─ Unsure → Create a prediction market about it (earn fees either way)
            → see: predictionMarkets.createMarketWithMetadata()
```

**Important**: Always simulate leverage before executing. Effective fee varies significantly by position size and pool depth.

---

### "I need liquidity but don't want to sell"

```
What do I hold?
├─ STASIS (in vault) → Lock + borrow (2% flat fee, keep yield + exposure)
│                      → see: staking.lock() → staking.borrow()
├─ Factory token → Direct loan (2% fee, keep token exposure)
│                  → see: loans.takeLoan()
├─ Vested tokens → Loan on vesting (access liquidity pre-unlock)
│                  → see: vesting.takeLoanOnVesting()
└─ Nothing stakeable → Sell the least volatile position
                       → see: trading.sell() or trading.sellPercentage()
```

**Loan cost reminder**: 2% flat origination fee. 0.005%/day to extend. Always take minimum duration (10 days) and extend as needed — never re-originate.
**Cross-refs**: → See: [09-fees.md](09-fees.md) for total cost calculations · → See: [13-mistakes.md](13-mistakes.md) for loan pitfalls

---

### "I want to start a business"

```
Do I have capital?
├─ Yes → Launch token with initial buy, set up vesting, create related markets
│        → see: factory.createTokenWithMetadata()
│        → see: vesting.createGradualVesting() (for team/investors)
│        → see: predictionMarkets.createMarketWithMetadata() (for community engagement)
├─ Some → Launch token, focus on community building for organic volume
│         → see: factory.createTokenWithMetadata()
│         → see: api.requestTwitterChallenge() + api.verifyTwitter()
└─ No → Launch token (minimal cost), earn dev fees from others' trades,
        resolve markets for bounties, reinvest earnings
        → see: factory.createTokenWithMetadata()
        → see: resolver.proposeOutcome() + resolver.claimBounty()
```

**Key insight**: Token creation costs only the BNB creation fee (call `factory.getFeeAmount()`). You earn 20% of all trading fees on your token forever from the moment it launches.
**Cross-refs**: → See: [02-archetypes.md — Token Creator](02-archetypes.md) for full playbook
