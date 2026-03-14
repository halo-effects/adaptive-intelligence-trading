# SDK Reference — Gap Analysis
_2026-03-14 | GeeGee review against full project knowledge_
_Updated after reviewing live API docs at launchonbasis.com/api-docs_

Alex's SDK has two layers:
1. **On-chain contract reference** (the MD file shared today) — all 13 contracts
2. **Off-chain REST API** (live at launchonbasis.com/api-docs) — metadata, candles, trades, orders, market stats, auth

The REST API is already live and documented with SIWE auth, API keys, code examples (Node.js + Python), and response schemas. This resolves several gaps from the original analysis.

Below are the **remaining** gaps after accounting for both layers.

---

## 🔴 High Priority (agents can't build without these)

### 1. Contract Events — Still Undocumented
The REST API provides trade history and market data via polling, which is a good workaround. But for real-time reactive agents (monitors, snipers, exit timing), event definitions (name, indexed params) are still needed to subscribe via `eth_subscribe` / `eth_getLogs`. Key events:
- Swap events on `ASwap` (trade notifications)
- Token creation events on `ATokenFactory`
- Market resolution events on `AMarketTrading` / `AMarketResolver`
- Loan lifecycle events on `ALOAN_HUB` / `MAIN_TOKEN`

**Mitigated by:** REST API trade history + polling. But not a full replacement for WebSocket event subscriptions.

### 2. Loan Struct Fields — Still Missing
`loans()` and `leverages()` on MAIN_TOKEN return a `Loan` struct but fields aren't defined. `ALOAN_HUB.getUserLoanDetails()` returns `FullLoanDetails` which IS documented — so agents can work around this by using the hub. But for direct leverage management on MAIN_TOKEN, the struct definition would help.

### 3. Contract Addresses — Still Needed Pre-SDK
The REST API is live at `launchonbasis.com`, but contract addresses for direct web3 calls still aren't listed. SDK resolves them dynamically, but pre-SDK agents need them. Even a simple address map in the docs or a `GET /api/v1/contracts` endpoint would solve this.

### 4. USDC/USDB Reference — Still Needed
Address, decimals, and faucet mechanism. The API docs don't cover this. It's the input token for nearly every approve+call flow.

---

## 🟡 Medium Priority (agents can work around but it slows development)

### 5. No Error/Revert Conditions
What happens when:
- `minOut` slippage check fails?
- Loan duration is outside `minDaysLoan`/`maxDaysLoan`?
- `partialLoanSell` percentage isn't divisible by 10?
- Insufficient liquidity for a leverage position?
- Token is frozen and buyer isn't whitelisted?
- Prediction market is already resolved?

Custom error names or revert reason strings would let agents handle failures gracefully instead of catching generic reverts.

### 6. TimeUnit Enum Values
`A_VestingContract` uses `TimeUnit` enum but only lists: `Second(0)`, `Minute(1)`, `Hour(2)`, `Day(3)`. This is actually documented inline — but confirming these are the only values would be helpful.

### 7. Prediction Market AMM Pricing Formula
`AMarketReader.getAllOutcomes()` returns `pricePerShare` and `probability`. The virtual reserve model is implied but not documented. Agents building pricing models need to know:
- Is it a LMSR (Logarithmic Market Scoring Rule) or constant-product AMM?
- How does `virtualReserve` translate to price?
- What's the relationship between `totalVirtualReserve` (in MarketData) and individual outcome reserves?

### 8. Tax Calculation Detail
`ATaxes.getTaxRate()` returns basis points, but:
- How do buy vs sell taxes differ (if at all)?
- Does `getAmountsOut` on ASwap include or exclude tax? (Reference says "does NOT include tax" ✅ — good)
- How does surge tax stack with base tax? Additive?

### 9. Multi-Ecosystem Support
`ALOAN_HUB.ecosystems()` and prediction market `ecosystems()` suggest multiple ecosystems are possible. Are there currently multiple MAIN_TOKEN deployments? Or is this future-proofing? Agents need to know which ecosystem address to pass.

---

## 🟢 Nice to Have (documentation quality)

### 10. Gas Estimates Per Operation
Approximate gas costs for each operation type would help agents budget BNB for gas. Diamond measured token creation at ~$0.14 — similar benchmarks for trades, loans, bets would be useful.

### 11. Flow Diagrams for Complex Operations
The leverage system (ASwap → MAIN_TOKEN → loan creation) and prediction market lifecycle (create → trade → bet → resolve → redeem) involve multiple contracts. A sequence diagram showing which contracts are called in which order would accelerate agent development.

### 12. `mixedBuy` — Agent-Only Feature Note
Worth noting in the SDK docs that `mixedBuy` is available via SDK but NOT exposed on the frontend UI. Agents have a capability advantage here. Same question for any other agent-only functions.

### 13. Decimal Precision Conventions
The reference mentions "18-decimal precision" for prices. A general note on decimal conventions would help:
- Token amounts: 18 decimals (standard ERC20)
- USDC amounts: 6 decimals? 18 decimals?
- Price returns: 18 decimals (confirmed for `getTokenPrice`)
- Basis points: raw integers (e.g., 200 = 2%)

---

## ✅ Resolved by Live REST API (launchonbasis.com/api-docs)

These were flagged as gaps in the contract reference but are covered by the existing API:

| Originally Flagged | Resolution |
|---|---|
| Trade monitoring / event feeds | `GET /api/v1/tokens/{addr}/trades` — paginated trade history with cursor |
| Market data / stats | `GET /api/v1/tokens`, `GET /api/v1/tokens/{addr}`, candles, liquidity |
| Prediction order book | `GET /api/v1/tokens/{addr}/orders` with status/outcome filters |
| Authentication | SIWE session + API keys (`bsk_` prefix), 60 req/min |
| Metadata management | `POST /api/metadata`, `POST /api/projects/{addr}` |
| Market probability tracking | `GET /api/v1/markets/{addr}/liquidity` — reserve + probability history |
| Wallet transaction history | `GET /api/v1/wallet/{addr}/transactions` |
| Order sync (on-chain → API) | `POST /api/v1/orders/sync` — syncs on-chain orders to the database |
| Full token creation flow | Documented end-to-end: deploy → upload image → create metadata |

**Notable API features:**
- SIWE auth with Python + Node.js examples
- API keys retrievable via GET (no need to store externally)
- Rate limit headers (`X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset`)
- Comments require "skin in the game" (≥$5 trade on the project)
- Image upload to IPFS via Pinata (512x512 WebP recommended)

---

## Updated Summary

| Priority | Gap | Impact | Status |
|----------|-----|--------|--------|
| 🔴 | Contract events (for WebSocket subscriptions) | Real-time monitors need raw events | Open — API polling is workaround |
| 🔴 | Contract addresses (pre-SDK) | Blocks direct web3 testing | Open — need address list |
| 🔴 | USDC/USDB reference | Blocks approve flows | Open |
| 🟡 | Loan struct fields (MAIN_TOKEN) | Affects direct leverage queries | Open — `FullLoanDetails` via hub is workaround |
| 🟡 | AMM pricing formula (predictions) | Blocks pricing models | Open |
| 🟡 | Revert conditions | Degrades error handling | Open |
| 🟡 | Tax stacking logic | Affects quote accuracy | Open |
| 🟢 | Decimal conventions | Prevents precision bugs | Open |
| 🟢 | Gas estimates | Convenience | Open |
| ✅ | Trade history / monitoring | Covered by REST API | **Resolved** |
| ✅ | Market data / candles | Covered by REST API | **Resolved** |
| ✅ | Order book queries | Covered by REST API | **Resolved** |
| ✅ | Auth system | Covered by REST API (SIWE + API keys) | **Resolved** |
| ✅ | Metadata management | Covered by REST API | **Resolved** |
