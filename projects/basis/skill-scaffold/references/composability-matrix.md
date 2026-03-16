# Composability Matrix
_What connects to what on Basis. Every row is an input, every column is what it unlocks._

## Action → Unlocks

| After doing this... | Can then... | Via | Cost |
|---|---|---|---|
| **Buy Stable+ token** | Take 100% LTV loan | `lend.py` | 2.0% + 0.005%/day |
| **Buy Stable+ token** | Leverage buy more | `leverage.py` | 43–70% of amount |
| **Buy Stable+ token** | Sell for USDC | `trade.py` | 0.5% fee |
| **Buy Stable+ token** | Hold for appreciation | — | Free |
| **Buy Floor+ token** | Take loan at floor price | `lend.py` | 2.0% + 0.005%/day |
| **Buy Floor+ token** | Leverage buy more | `leverage.py` | 43–70% of amount |
| **Buy Floor+ token** | Sell for USDC | `trade.py` | 1.5% fee |
| **Buy STASIS** | Wrap to wSTASIS vault | `vault.py` | Free |
| **Buy STASIS** | Take loan | `lend.py` | 2.0% + 0.005%/day |
| **Wrap wSTASIS** | Borrow against appreciation | `vault.py` | Loan terms |
| **Wrap wSTASIS** | Earn vault yield | — | Free (automatic) |
| **Take loan** | Buy any token | `trade.py` | Trading fee |
| **Take loan** | Place bet | `bet.py` | Prediction fee |
| **Take loan** | Stake in vault | `vault.py` | Free to wrap |
| **Take loan** | Create new token/market | `create-*.py` | Gas only |
| **Take loan** | Hold as USDC reserve | — | Free |
| **Place bet** | Win → receive USDC | — | Free (automatic) |
| **Place bet** | Lose → $0 | — | — |
| **Create token** | Earn 20% trading fees | — | Automatic, forever |
| **Create prediction** | Earn 20% trading fees | — | Automatic, forever |
| **Create prediction** | Bet on outcomes | `bet.py` | Fee |
| **Earn creator fees** | Redeploy USDC anywhere | Any script | Varies |
| **Earn points** | Increase ACS multiplier | — | Free |
| **Leverage buy** | Hold for amplified upside | — | Free |
| **Leverage buy** | ❌ CANNOT take loan | — | Blocked |
| **Leverage buy** | ❌ CANNOT use as collateral | — | Blocked |

## Blocked Combinations

| Action | Cannot Do | Reason |
|---|---|---|
| Leverage buy tokens | Use as loan collateral | Held in leverage contract |
| Bet USDC | Loan against bet | Bets aren't tokenized collateral |
| Hold USDC | Earn anything | Must deploy to earn |

## Capital Flow Diagram

```
                    ┌──────────┐
                    │   USDC   │ ◄── External deposit
                    └────┬─────┘     Bet winnings
                         │           Creator fees
                         │           Loan proceeds
                         │           Token sells
                         │
         ┌───────────────┼───────────────┐
         ▼               ▼               ▼
    ┌─────────┐    ┌──────────┐    ┌──────────┐
    │ Buy      │    │ Place    │    │ Stake    │
    │ Tokens   │    │ Bets     │    │ Vault    │
    └────┬────┘    └──────────┘    └────┬─────┘
         │          (terminal)          │
         ▼                              ▼
    ┌─────────┐                   ┌──────────┐
    │ Take    │                   │ Refinance│
    │ Loan    │───► USDC ◄────────│ Vault    │
    └─────────┘                   └──────────┘
         │
         ▼
    USDC recycles back to top ♻️
```

## Points Earned Per Action

| Action | Points | Repeatable |
|---|---|---|
| Create prediction market | 300 | Per market |
| Launch token | 500 | Per token |
| Trade (per $1 volume) | 1 | Unlimited |
| Bet (per $1 net profit) | 1 | Unlimited |
| Take loan | 200 base + 1/day | Per loan |
| Vault stake | 2 per $1/day | Continuous |
| Social post | 50–150 | Per post |
| Referral | 10% of referee lifetime | Per referral |
