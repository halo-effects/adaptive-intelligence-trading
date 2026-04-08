# Loans & Leverage — L1 What/Why/How

## WHAT: Loans & Leverage

Basis has a built-in lending system where you deposit tokens as collateral and borrow USDB against them. The defining feature: **there is no price-based liquidation**. Your loan expires by time, not by price movement. If a flash crash drops your collateral value by 90%, nothing happens to your loan — you still have the full duration to repay.

This works because of the token mechanics underneath. Stable+ tokens can't decrease in price, and Floor+ tokens have a floor that never drops — so collateral can't crater to zero the way it can in traditional DeFi.

Leverage takes this further. A `leverageBuy` recursively loops: buy tokens → loan against them → buy more tokens → loan again → repeat until the 2% origination fee per loop consumes the remaining capital. A $10 input can produce roughly a $200 position. Because there's no price liquidation, this leverage doesn't carry the usual liquidation risk — your only obligation is to repay before the loan expires.

Loans cost 2% origination (flat, one-time) plus 0.005% per day in interest. Duration ranges from 10 to 1,000 days. Extensions cost just the daily rate (0.005%/day), making them roughly 400x cheaper per day than originating a new loan.

## WHY: Why Would I Use Loans & Leverage?

Because capital sitting in one place is capital not working elsewhere. Loans let you hold a position while deploying the borrowed USDB into other opportunities — trade another token, bet on a prediction market, stake, or simply diversify.

**No liquidation fear**: In traditional DeFi, leverage is a liquidation countdown. One bad wick and your position is gone. On Basis, your collateral can't be liquidated by price. You control when to exit — repay early, extend the loan, or let it expire and claim whatever's left after debt is settled. This changes leverage from a high-wire act to a calculated strategy.

**Stable+ leverage is uniquely powerful**: Because the price literally cannot decrease, Stable+ tokens support 20-36x leverage. The only cost is the origination fees stacking on each loop. Your position value can only go up while your debt stays fixed — the spread between the two is your profit.

**Floor+ leverage uses the floor, not spot**: Loans against Floor+ tokens are valued at the floor price, which never drops. If spot price is $2 and floor is $1.50, you borrow against $1.50. The gap between floor and spot is your built-in safety margin. As the floor rises with trading activity, your collateral value only strengthens.

**Extensions are dirt cheap**: If your loan is approaching expiry but you want to hold the position, extend rather than close and re-open. At 0.005%/day vs 2% origination, extending for 100 days costs 0.5% — compared to 2% for a new loan. This makes longer-term strategies viable without punishing origination costs.

## HOW: How Do I Use Loans & Leverage?

**Simple loan**: Deposit any token as collateral and borrow USDB against it. Use the USDB however you want — trade, bet, stake, or hold. Repay the USDB debt before expiry to reclaim your collateral. If you can't repay in time, the collateral is sold to cover the debt and any remainder is claimable.

**Vault loan (for STASIS holders)**: Wrap your STASIS into wSTASIS first, then lock it as collateral, then borrow against it. The advantage: your collateral continues earning yield from platform fees while it's locked. You're earning on collateral that's simultaneously backing a loan.

**Leverage buy**: Specify the token, the amount of USDB to start with, and the loan duration. The system loops automatically — buy → loan → buy → loan — until fees eat the remaining capital. You end up with a leveraged position worth roughly 20x your input. To unwind, use partial sell in 10% increments, working backward through the loan stack.

**DIY leverage**: For more control, manually loop `takeLoan()` and `buy()` yourself. Fewer loops, more deliberate sizing, and you choose exactly when to stop stacking.

**Extending**: If your loan is nearing expiry, extend it rather than closing and re-opening. You pay just the daily rate for additional days, preserving your position at a fraction of the cost.

## Deep Dive

For full details, see these reference modules:
- [16-how-everything-works](../modules/16-how-everything-works.md) — loan LTV system, leverage recursion loops
- [10-atomic-skills](../modules/10-atomic-skills.md) — Loans module, Leverage Simulator
- [12-defi-primitive-playbooks](../modules/12-defi-primitive-playbooks.md) — loan cost framework, leverage sizing
- [18-fee-cost-reference](../modules/18-fee-cost-reference.md) — origination fees, daily interest, extension costs
- [22-mistakes-to-avoid](../modules/22-mistakes-to-avoid.md) — loan duration traps, expiry pitfalls
- [25-code-examples](../modules/25-code-examples.md) — leverage trading and loan examples
