#!/usr/bin/env python3
"""Fix mojibake in COMPLETE.md decision trees by replacing the 4 code blocks."""

filepath = r'C:\Users\Never\.openclaw\workspace\projects\basis\basis-docs\COMPLETE.md'

with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# Tree 1: "I have idle USDB"
old1 = """```
How long will it be idle?
\u00e2\u201c\u0153\u00e2\u201c\u20ac Hours \u00e2\u2020\u2019 Leave as USDB
\u00e2\u201c\u0153\u00e2\u201c\u20ac Days \u00e2\u2020\u2019 Buy STASIS \u00e2\u2020\u2019 Stake in vault (earn yield + airdrop points daily)
\u00e2\u201c\u2019         \u00e2\u2020\u2019 see: trading.buy() then staking.buy()
\u00e2\u201c\u0153\u00e2\u201c\u20ac Weeks \u00e2\u2020\u2019 Stake + lock as collateral (ready to borrow if opportunity appears)
\u00e2\u201c\u2019         \u00e2\u2020\u2019 see: staking.lock()
\u00e2\u201c\u201d\u00e2\u201c\u20ac Indefinitely \u00e2\u2020\u2019 Stake + deploy via vault borrowing
                  \u00e2\u2020\u2019 see: staking.borrow() \u00e2\u2020\u2019 deploy borrowed USDB
```"""

new1 = """```
How long will it be idle?
├─ Hours → Leave as USDB
├─ Days → Buy STASIS → Stake in vault (earn yield + airdrop points daily)
│         → see: trading.buy() then staking.buy()
├─ Weeks → Stake + lock as collateral (ready to borrow if opportunity appears)
│         → see: staking.lock()
└─ Indefinitely → Stake + deploy via vault borrowing
                  → see: staking.borrow() → deploy borrowed USDB
```"""

# Tree 2: "I want exposure to token X"
old2 = """```
How confident am I?
\u00e2\u201c\u0153\u00e2\u201c\u20ac Very confident \u00e2\u2020\u2019 Leverage buy (simulate first to check fee, amplified returns, no price liquidation)
\u00e2\u201c\u2019                  \u00e2\u2020\u2019 see: leverageSimulator.simulateLeverage() FIRST
\u00e2\u201c\u2019                  \u00e2\u2020\u2019 see: trading.leverageBuy()
\u00e2\u201c\u0153\u00e2\u201c\u20ac Confident \u00e2\u2020\u2019 Direct buy
\u00e2\u201c\u2019              \u00e2\u2020\u2019 see: trading.buy()
\u00e2\u201c\u0153\u00e2\u201c\u20ac Somewhat \u00e2\u2020\u2019 Smaller position, or prediction market bet
\u00e2\u201c\u2019              \u00e2\u2020\u2019 see: predictionMarkets.buy()
\u00e2\u201c\u201d\u00e2\u201c\u20ac Unsure \u00e2\u2020\u2019 Create a prediction market about it (earn fees either way)
            \u00e2\u2020\u2019 see: predictionMarkets.createMarketWithMetadata()
```"""

new2 = """```
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
```"""

# Tree 3: "I need liquidity but don't want to sell"
old3 = """```
What do I hold?
\u00e2\u201c\u0153\u00e2\u201c\u20ac STASIS (in vault) \u00e2\u2020\u2019 Lock + borrow (2% origination + 0.005%/day, keep yield + exposure)
\u00e2\u201c\u2019                      \u00e2\u2020\u2019 see: staking.lock() \u00e2\u2020\u2019 staking.borrow()
\u00e2\u201c\u0153\u00e2\u201c\u20ac Factory token \u00e2\u2020\u2019 Direct loan (2% fee, keep token exposure)
\u00e2\u201c\u2019                  \u00e2\u2020\u2019 see: loans.takeLoan()
\u00e2\u201c\u0153\u00e2\u201c\u20ac Vested tokens \u00e2\u2020\u2019 Loan on vesting (access liquidity pre-unlock)
\u00e2\u201c\u2019                  \u00e2\u2020\u2019 see: vesting.takeLoanOnVesting()
\u00e2\u201c\u201d\u00e2\u201c\u20ac Nothing stakeable \u00e2\u2020\u2019 Sell the least volatile position
                       \u00e2\u2020\u2019 see: trading.sell() or trading.sellPercentage()
```"""

new3 = """```
What do I hold?
├─ STASIS (in vault) → Lock + borrow (2% origination + 0.005%/day, keep yield + exposure)
│                      → see: staking.lock() → staking.borrow()
├─ Factory token → Direct loan (2% fee, keep token exposure)
│                  → see: loans.takeLoan()
├─ Vested tokens → Loan on vesting (access liquidity pre-unlock)
│                  → see: vesting.takeLoanOnVesting()
└─ Nothing stakeable → Sell the least volatile position
                       → see: trading.sell() or trading.sellPercentage()
```"""

# Tree 4: "I want to start a business"
old4 = """```
Do I have capital?
\u00e2\u201c\u0153\u00e2\u201c\u20ac Yes \u00e2\u2020\u2019 Launch token with initial buy, set up vesting, create related markets
\u00e2\u201c\u2019        \u00e2\u2020\u2019 see: factory.createTokenWithMetadata()
\u00e2\u201c\u2019        \u00e2\u2020\u2019 see: vesting.createGradualVesting() (for team/investors)
\u00e2\u201c\u2019        \u00e2\u2020\u2019 see: predictionMarkets.createMarketWithMetadata() (for community engagement)
\u00e2\u201c\u0153\u00e2\u201c\u20ac Some \u00e2\u2020\u2019 Launch token, focus on community building for organic volume
\u00e2\u201c\u2019         \u00e2\u2020\u2019 see: factory.createTokenWithMetadata()
\u00e2\u201c\u2019         \u00e2\u2020\u2019 see: api.requestTwitterChallenge() + api.verifyTwitter()
\u00e2\u201c\u201d\u00e2\u201c\u20ac No \u00e2\u2020\u2019 Launch token (minimal cost), earn dev fees from others' trades,
        resolve markets for bounties, reinvest earnings
        \u00e2\u2020\u2019 see: factory.createTokenWithMetadata()
        \u00e2\u2020\u2019 see: resolver.proposeOutcome() + resolver.claimBounty()
```"""

new4 = """```
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
```"""

count = 0
for old, new in [(old1, new1), (old2, new2), (old3, new3), (old4, new4)]:
    if old in content:
        content = content.replace(old, new)
        count += 1
        print(f"Fixed tree {count}")
    else:
        print(f"Tree {count+1}: NOT FOUND - checking...")
        # Show a snippet around where it should be
        idx = content.find('How long will it be idle?') if count == 0 else \
              content.find('How confident am I?') if count == 1 else \
              content.find('What do I hold?') if count == 2 else \
              content.find('Do I have capital?')
        if idx >= 0:
            snippet = content[idx-10:idx+50]
            print(f"  Found nearby text, repr: {repr(snippet[:60])}")
        count += 1

with open(filepath, 'w', encoding='utf-8', newline='\n') as f:
    f.write(content)

print(f"\nDone. Fixed {count} decision trees.")
