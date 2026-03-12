# Basis API Reference

_Status: **Placeholder** — will be populated from Alex's Swagger docs and ABI exports._
_Last updated: 2026-03-12_

---

## Architecture Note

Basis is **on-chain first**. Financial operations (token creation, trading, lending, betting) happen via **direct smart contract calls** using web3.py / ethers.js / viem — NOT through a REST API.

The REST API and indexer serve **read-only / metadata** queries (candles, transaction history, portfolio aggregation, points, ACS).

---

## Smart Contract Interactions (Direct Calls via web3)

### TODO: Awaiting Alex's Deliverables

| Deliverable | Status | What We Get |
|-------------|--------|-------------|
| Contract addresses + ABIs package | ⏳ Pending | All deployed contract addresses on BNB Chain + JSON ABIs |
| Contract function reference | ⏳ Pending | Parameter types, return values, events for each function |
| Metadata API docs | ⏳ Pending | Swagger/OpenAPI spec for read-only endpoints |
| Indexer endpoint docs | ⏳ Pending | Candles, transactions, syncs, leverage, prediction shares |

### Expected Contract Modules

Based on the project plan, the following contract interfaces will be documented:

**Token Factory**
- `createStablePlus(name, symbol, initialPrice, feeRate, ...)` → Deploy Stable+ token
- `createFloorPlus(name, symbol, initialPrice, stabilityDial, feeRate, ...)` → Deploy Floor+ token
- Events: `TokenCreated(address, creator, tokenType)`

**DEX / AMM**
- `buy(token, amount, maxSlippage)` → Buy tokens (mints from bonding curve)
- `sell(token, amount, minReceive)` → Sell tokens (burns on bonding curve)
- `buyLeveraged(token, amount, ...)` → Buy with 36x leverage toggle
- Events: `Swap(buyer, token, amountIn, amountOut, price)`

**Predict+ Markets**
- `createMarket(title, outcomes[], resolutionTimestamp, creatorFee)` → Deploy prediction market
- `bet(market, outcomeIndex, amount)` → Place bet on outcome
- `resolveMarket(market, winningOutcome)` → Submit resolution proposal
- Events: `MarketCreated(address, creator, outcomes[])`, `BetPlaced(market, user, outcome, amount)`, `MarketResolved(market, winningOutcome)`

**Lending**
- `borrow(token, tokenAmount, borrowAmount, durationDays)` → Take loan at 100% LTV
- `extendLoan(loanId, additionalDays)` → Extend before expiry
- `repayLoan(loanId)` → Repay and release collateral
- Events: `LoanCreated(loanId, borrower, collateralToken, borrowedAmount)`, `LoanExtended(loanId)`, `LoanRepaid(loanId)`

**STASIS Vault (wSTASIS)**
- `stake(stasisAmount)` → Deposit STASIS, receive wSTASIS
- `unstake(wstasisAmount)` → Redeem wSTASIS for STASIS
- `getRatio()` → Current STASIS:wSTASIS ratio
- Events: `Staked(user, stasisAmount, wstasisReceived)`, `Unstaked(user, wstasisAmount, stasisReceived)`

**USDB (Test Stablecoin)**
- Standard ERC20 interface
- Faucet: `requestUSDB(wallet)` → Receive test USDB (rate-limited)

---

## REST API (Read-Only + Metadata)

### Base URL
```
https://api.basis.exchange/api/v1
```

### Authentication
- **Read endpoints:** No auth required
- **Write operations:** Not applicable (writes go direct to contracts)
- **API keys:** Optional, for rate limit increases on read endpoints

### Expected Endpoints

**Portfolio & P&L**
```
GET /api/v1/portfolio/{wallet}
```
Returns: net P&L, gross volume, prediction stats (bets, wins, P&L), trading stats, fees earned, gas costs.

**Airdrop Points**
```
GET /api/v1/points/{wallet}
```
Returns: total points, tier, next tier threshold, streak, multiplier, category breakdown, rank.

**Agent Confidence Score**
```
GET /api/v1/acs/{wallet}
```
Returns: ACS score (0.0–1.0), label, multiplier, component breakdown (framework attestation, operator linked, API-only, behavioral, wallet type, challenge).

**Market Data (Indexer)**
```
GET /api/v1/markets                    # List all prediction markets
GET /api/v1/markets/{address}          # Market details
GET /api/v1/tokens                     # List all tokens
GET /api/v1/tokens/{address}           # Token details + price
GET /api/v1/tokens/{address}/candles   # Price candles (OHLCV)
GET /api/v1/transactions/{wallet}      # Transaction history
GET /api/v1/loans/{wallet}             # Active loans
```

**Real-Time (WebSocket)**
```
WS /api/v1/stream/events
```
Events: new predictions, price movements, resolutions, new token launches, loan expiry warnings.

---

## Chain Details

| Property | Value |
|----------|-------|
| Chain | BNB Chain (Mainnet) |
| Chain ID | 56 |
| RPC | `https://bsc-dataseed.binance.org/` |
| Block time | ~3 seconds |
| Gas cost | Sub-cent (<$0.01 per tx) |
| Native token | BNB (for gas) |
| Test stablecoin | USDB (ERC20, free from faucet) |
| Live stablecoin | USDC (post-launch) |

---

## TODO

- [ ] Import Alex's ABI package and list all contract addresses
- [ ] Generate full function reference from ABI JSON
- [ ] Import Swagger docs for metadata API
- [ ] Document indexer WebSocket event schema
- [ ] Add code examples (Python + JavaScript) for each contract call
- [ ] Add gas estimation benchmarks for each operation type
