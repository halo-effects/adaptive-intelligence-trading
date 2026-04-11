# BASIS SDK Learnings (from official docs)
> Updated: 2026-04-11

## Critical: Always use official SDK from GitHub
- `pip install git+https://github.com/Launch-On-Basis/SDK-PY.git`
- SDK auto-fetches contract addresses from `https://launchonbasis.com/contracts.json`
- NEVER use hardcoded addresses from old local copies

## Correct Staking Flow
1. `client.trading.buy(client.main_token_address, amount)` — buy STASIS with USDB
2. `client.staking.buy(amount)` — wraps STASIS into wSTASIS (ERC4626 vault)
3. Lock wSTASIS as collateral
4. Borrow USDB against it
- wSTASIS earns yield at ALL stages, even while locked and backing a loan

## Token Types (hybridMultiplier)
- 100 = Stable+ (price only goes up, elastic supply)
- 1-90 = Floor+ (price moves freely, rising floor absorbs sells)
- Predict+ = Stable+ subtype created by prediction markets

## Token Creation
- MUST use `create_token_with_metadata()` for tokens to appear on site
- Raw `create_token()` creates invisible on-chain tokens — don't use
- Creator earns 20% of net trading fees forever

## Prediction Markets
- Each market creates TWO assets: Predict+ token + Outcome shares
- Predict+ token = volume play (appreciates from trading activity)
- Outcome shares = conviction play (bet on specific result)
- Payout is UNCAPPED (not $1/share like Polymarket)

## Trading
- All trades route through STASIS as hub token
- Buy: USDB → STASIS → Token (3-path)
- Fees: 0.5% Stable+, 1.5% Floor+/Predict+

## Loans
- No price liquidation — time-based expiry only
- 2% origination + 0.005%/day interest
- Extensions cost ~400x less than new loans
- Stable+ loans can't be liquidated because price only goes up
- Floor+ loans valued against floor (which never drops)

## Reading Token Info
- API: `client.api.get_tokens()` for lists, `client.api.get_token(addr)` for details
- On-chain: `client.factory.get_token_state(addr)` for state
- hybridMultiplier via view function on token contract
- Prediction: `client.prediction_markets.get_market_data(addr)`

## Faucet
- Up to 500 USDB/day
- Requires: ERC-8004 agent registered OR username + linked social
- 24h cooldown between claims
