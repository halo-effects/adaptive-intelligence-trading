# Return Schemas Draft — Read Methods Missing Schemas

**Purpose:** This is a DRAFT for review. Lists every SDK read method that's missing a return type or schema, grouped by module. When approved, these additions go into COMPLETE.md.

---

## Summary

**Well-documented (has return schema):** 22 methods
**Missing return schema:** 24 methods

The well-documented ones (like `getLeveragePosition`, `getUserStakeDetails`, `getUserLoanDetails`, `getAllOutcomes`, `simulateLeverage`) are great — they list every field with types and descriptions. The gaps below need the same treatment.

---

## Module: Trading (`client.trading`)

### `getTokenPrice(tokenAddress)` — MISSING return type
Currently says: "Gets the price of a token denominated in MAINTOKEN."
**Needs:** `Returns: bigint` (18 decimals, price in MAINTOKEN units) — or whatever the actual return is. Alex to confirm.

---

## Module: Factory (`client.factory`)

### `getTokenState(tokenAddress)` — HAS return but no field descriptions
Currently: `Returns: { frozen, hasBonded, totalSupply, usdPrice }`
**Needs:** Field-level descriptions:

| Field | Type | Description |
|-------|------|-------------|
| `frozen` | `boolean` | Whether the token is frozen (trading halted) |
| `hasBonded` | `boolean` | Whether the reward phase has ended (true = bonded, no more reward shares) |
| `totalSupply` | `bigint` | Total token supply (18 decimals) |
| `usdPrice` | `string` | Current USD price |

### `getFeeAmount()` — MISSING return type
Currently: "Returns the current token creation fee in BNB."
**Needs:** `Returns: bigint` — fee in wei (18 decimals). Currently 0 in Phase 1.

### `getClaimableRewards(tokenAddress, investor)` — MISSING return type
Currently: "Returns the claimable USDB reward amount for an investor on a factory token."
**Needs:** `Returns: bigint` — claimable amount in USDB (18 decimals).

---

## Module: Staking (`client.staking`)

### `getAvailableStasis(user)` — MISSING return type
Currently: "Returns STASIS available as collateral for a user."
**Needs:** `Returns: bigint` — available STASIS in 18 decimals.

### `totalAssets()` — MISSING return type
Currently: "Returns total STASIS held by the vault."
**Needs:** `Returns: bigint` — total vault STASIS in 18 decimals.

---

## Module: Vesting (`client.vesting`)

### `getVestingDetails(vestingId)` — MISSING return schema
Currently: "Returns full vesting schedule details including beneficiary, token, amounts, timing, loan status."
**Needs:** Full field breakdown. Likely something like:

| Field | Type | Description |
|-------|------|-------------|
| `beneficiary` | `address` | Wallet receiving the vested tokens |
| `token` | `address` | Token being vested |
| `totalAmount` | `bigint` | Total tokens in the vesting schedule |
| `vestedAmount` | `bigint` | Amount vested so far |
| `claimedAmount` | `bigint` | Amount already claimed |
| `startTime` | `bigint` | Vesting start timestamp |
| `duration` | `bigint` | Total vesting duration in seconds |
| `timeUnit` | `number` | Unlock frequency (0=second, 1=minute, 2=hour, 3=day) |
| `hasActiveLoan` | `boolean` | Whether a loan is active against this vesting |
| `memo` | `string` | Creator-set memo |

**⚠️ Alex to confirm actual fields — these are inferred from the contract description.**

### `getClaimableAmount(vestingId)` — MISSING return type
**Needs:** `Returns: bigint` — claimable token amount (18 decimals).

### `getVestedAmount(vestingId)` — MISSING return type
**Needs:** `Returns: bigint` — total vested amount (18 decimals).

### `getVestingsByBeneficiary(address)` — MISSING return type
**Needs:** `Returns: bigint[]` — array of vesting IDs.

### `getVestingsByCreator(address)` — MISSING return type
**Needs:** `Returns: bigint[]` — array of vesting IDs.

### `getActiveLoan(vestingId)` — MISSING return type
**Needs:** `Returns: bigint` — loan ID (0 if no active loan).

### `getTokenVestingIds(token, startIndex, endIndex)` — MISSING return type
**Needs:** `Returns: bigint[]` — array of vesting IDs for the token in the given range.

### `getVestingDetailsBatch(vestingIds)` — MISSING return type
**Needs:** `Returns: VestingDetails[]` — array of vesting detail structs (same schema as `getVestingDetails`).

### `getVestingCount()` — MISSING return type
**Needs:** `Returns: bigint` — total number of vesting schedules.

---

## Module: Prediction Markets (`client.predictionMarkets`)

### `getMarketData(marketToken)` — MISSING return schema
Currently: "Returns comprehensive market data including name, end time, outcomes, status."
**Needs:** Full field breakdown. Likely:

| Field | Type | Description |
|-------|------|-------------|
| `name` | `string` | Market question/title |
| `endTime` | `bigint` | Market end timestamp |
| `numOutcomes` | `bigint` | Number of outcomes |
| `isResolved` | `boolean` | Whether the market has been resolved |
| `finalOutcome` | `number` | Winning outcome index (if resolved) |
| `creator` | `address` | Market creator wallet |
| `bountyPool` | `bigint` | Resolver bounty pool |
| `generalPot` | `bigint` | General pot balance |

**⚠️ Alex to confirm actual fields.**

### `getOutcome(marketToken, outcomeId)` — MISSING return schema
Currently: "Returns reserves and current probability for a specific outcome."
**Needs:** Return type. Likely `{ reserve, totalCost, circulatingShares, probability }` or similar — compare with the fully-documented `getAllOutcomes` in MarketReader which returns `OutcomeInfo[]`.

### `getUserShares(marketToken, user, outcomeId)` — MISSING return type
**Needs:** `Returns: bigint` — number of shares held (18 decimals).

### `getBountyPool(marketToken)` — MISSING return type
**Needs:** `Returns: bigint` — bounty pool amount in USDB (18 decimals).

### `getGeneralPot(marketToken)` — MISSING return type
**Needs:** `Returns: bigint` — general pot balance in USDB (18 decimals).

### `getInitialReserves(numOutcomes)` — Partially documented
Currently: "Returns `(perOutcome, totalReserve)` - AMM scaling reference."
**Needs:** Types: `Returns: [bigint, bigint]` — `[perOutcomeReserve, totalReserve]` both in 18 decimals.

---

## Module: Market Reader (`client.marketReader`)

### `estimateSharesOut(routerAddress, marketToken, outcomeId, usdbAmount, orderIds, user)` — MISSING return schema
Currently: "Previews shares you would receive for a USDB input (AMM + order book combined)."
**Needs:** Return type — likely `{ sharesOut, effectivePrice, ... }` or similar. Alex to confirm.

### `getPotentialPayout(routerAddress, marketToken, outcomeId, sharesAmount, estimatedUsdbToPool)` — MISSING return schema
Currently: "Simulates payout for a winning outcome given a share amount."
**Needs:** Return type — likely `bigint` (payout amount in USDB) or a struct. Alex to confirm.

---

## Module: Taxes (`client.taxes`)

### `getCurrentSurgeTax(token)` — MISSING explicit return type
Has great description but no `Returns:` line.
**Needs:** `Returns: bigint` — current surge tax rate in basis points (0 if no surge active).

### `getAvailableSurgeQuota(token)` — MISSING return type
**Needs:** `Returns: bigint` — remaining surge-eligible seconds.

---

## Module: Agent (`client.agent`)

### `lookupFromApi(wallet)` — MISSING return schema
Currently: "Returns: agent details or null."
**Needs:** Schema for the agent details object. Likely:

| Field | Type | Description |
|-------|------|-------------|
| `wallet` | `address` | Agent wallet |
| `agentId` | `bigint` | On-chain NFT ID |
| `name` | `string` | Agent name |
| `uri` | `string` | Metadata URI |
| `registered` | `boolean` | On-chain registration status |

**⚠️ Alex to confirm actual fields.**

### `listAgents(page?, limit?)` — MISSING return schema
Currently: "Returns: paginated agent list."
**Needs:** `Returns: { data: Agent[], pagination: { total, page, limit, hasMore } }` — with Agent schema matching `lookupFromApi`.

### `getAgentURI(agentId)` — MISSING return type
**Needs:** `Returns: string` — base64-encoded JSON metadata URI.

### `getAgentWallet(agentId)` — MISSING return type
**Needs:** `Returns: address` — wallet address linked to the agent NFT.

---

## Items marked ⚠️ need Alex's confirmation

These return types are inferred from the method descriptions and contract patterns. Alex should verify:

1. `getTokenPrice` — what exactly does this return?
2. `getVestingDetails` — full struct fields
3. `getMarketData` — full struct fields
4. `getOutcome` — return struct
5. `estimateSharesOut` — return struct
6. `getPotentialPayout` — return type
7. `lookupFromApi` — agent details schema
8. `listAgents` — agent list schema + pagination format

Everything else is straightforward type annotations that can be added without verification.
