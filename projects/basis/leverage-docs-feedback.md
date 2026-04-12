# Leverage Position: Documentation Confusion & Resolution

**Date:** 2026-04-12
**Agent:** GeeGee (0x2D087a119271Ef50C72eC5F01183f85Ab7E74Fe2)
**Position:** GEEGEE leverage (0xbb8c...), ~64 USDB repay, 7-day term

---

## What Happened

Opened a `leverageBuy()` on GEEGEE token on April 9. When trying to close it on April 12, spent ~45 minutes trying wrong methods before Alex provided the correct flow.

---

## Confusion Point 1: Two Separate Systems (Leverage vs Loans)

### What the docs say
Module 04 Section 3d covers `hubPartialLoanSell()` on `client.loans` for closing leverage. Module 05 covers `repayLoan()` for hub loans. Both use "loan" terminology.

### What actually happened
Tried `client.loans.hubPartialLoanSell()` and `client.loans.repayLoan()` — both wrong contracts.

### The reality
- **Leverage** → lives on the **SWAP/STASIS contract**. Use `client.trading.partialLoanSell()`.
- **Loans** → lives on the **LOAN contract** (hub). Use `client.loans.repayLoan()`.

These are completely different contract systems. The docs don't make this separation clear.

### Doc fix needed
Module 04 Section 3d should explicitly state:
> Leverage positions are managed by the SWAP contract, NOT the LOAN hub. Use `client.trading.partialLoanSell()` — not `client.loans.hubPartialLoanSell()`. The loan module methods (`repayLoan`, `extendLoan`, etc.) do not work on leverage positions.

---

## Confusion Point 2: Method Signatures (getLeverageCount / getLeveragePosition)

### What the docs say (Module 04 + Module 18)
```
getLeverageCount(wallet, tokenAddress)    → 2 params
getLeveragePosition(wallet, tokenAddress, index)  → 3 params
```

### What actually works (per Alex)
```
getLeverageCount(wallet)      → 1 param
getLeveragePosition(wallet, index)  → 2 params
```

No `tokenAddress` parameter. The STASIS contract stores ALL leverage positions for a wallet in a single list — not segregated by token.

### Doc fix needed
Module 18 SDK Reference should update:
```
| getLeverageCount(wallet) | address | number | Total leverage positions | 04 |
| getLeveragePosition(wallet, index) | address, number | LeveragePosition | Position details | 04 |
```

Module 04 Section 3d code example should be:
```js
const count = await client.trading.getLeverageCount(wallet);
for (let i = 0n; i < count; i++) {
  const pos = await client.trading.getLeveragePosition(wallet, i);
  // pos[1] = collateral token address
  // pos[2] = collateral amount
  // pos[9] = active flag
}
```

---

## Confusion Point 3: Position Indexing (0-based vs 1-based)

### What the docs say
Module 04: "1-indexed, latest = count" (referring to hub loans)

### What actually happened
- Position **0** → empty/cleared slot (all zeros)
- Position **1** → the active GEEGEE leverage (my wallet, token, collateral, expiry — all present)

The `getLeverageCount` returned 1, but the active position was at index 1, not index 0. Position 0 existed but was zeroed out (previously closed or never used).

### What this means
The indexing appears to be 1-based for leverage positions, with index 0 being unused/empty. But `getLeverageCount` returns 1, which you'd expect means "one position at index 0" if 0-based.

### Doc fix needed
Clarify explicitly:
> Leverage positions are **1-indexed**. `getLeverageCount(wallet)` returns the total count. Loop from `1` to `count` (inclusive), not from `0` to `count-1`. Index 0 is always empty.

Or if the SDK should handle this: the SDK could add a helper that returns active positions without requiring callers to know the indexing scheme.

---

## Confusion Point 4: getLeveragePosition Return Format

### What the docs show
No clear field mapping for the returned array.

### What the actual return looks like
```
Position 1: [
  "0x2D087a...",     // [0] owner wallet
  "0xbb8c70bD...",   // [1] collateral token
  "63708706...",     // [2] collateral amount
  "0",               // [3] ?
  "64110844...",     // [4] full repay amount
  "62806188...",     // [5] borrowed amount
  "1776115405",      // [6] liquidation timestamp
  "0",               // [7] ?
  false,             // [8] ? (isLiquidated?)
  true,              // [9] active
  "1775510605",      // [10] creation timestamp
  "0",               // [11] ?
  { leverageBuyAmount: "10000000000000000000", cashedOut: "0" }  // [12] metadata
]
```

### Doc fix needed
Module 04 or Module 18 should include a field mapping table:
```
| Index | Field              | Type    | Description                    |
|-------|--------------------|---------|--------------------------------|
| 0     | owner              | address | Wallet that opened the position|
| 1     | collateralToken    | address | Token used as collateral       |
| 2     | collateralAmount   | uint256 | Amount of collateral locked    |
| 4     | fullAmount         | uint256 | Total repay obligation         |
| 5     | borrowedAmount     | uint256 | Original borrowed amount       |
| 6     | liquidationTime    | uint256 | Unix timestamp of expiry       |
| 8     | isLiquidated       | bool    | Whether position was liquidated|
| 9     | active             | bool    | Whether position is still open |
| 10    | creationTime       | uint256 | Unix timestamp of creation     |
| 12    | metadata           | object  | { leverageBuyAmount, cashedOut }|
```

---

## Confusion Point 5: hubPartialLoanSell vs partialLoanSell

### What the docs say
Module 04 Section 3d and Module 18 both reference `hubPartialLoanSell` on `client.loans`.

### What actually works
`client.trading.partialLoanSell()` — on the trading module, not loans.

### Doc fix needed
Either:
1. Rename the documented method to `partialLoanSell` and move it to `client.trading` section, OR
2. If `hubPartialLoanSell` is a separate method for hub-delegated leverage (different use case), clarify when to use which

---

## Confusion Point 6: API vs On-Chain State Mismatch

### What happened
The API (`getLoans()`) showed the leverage loan as `active: true`. On-chain, `getLeveragePosition(wallet, 0)` returned all zeros. This led me to believe the position was in a broken state.

### Root cause
I was querying index 0 (wrong index). The position was at index 1 and fully intact on-chain. The API was correct all along.

### Doc fix needed
Add a troubleshooting note:
> If `getLeveragePosition` returns zeros but the API shows an active position, check other indices. Positions are 1-indexed — try index 1 instead of 0.

---

## Summary of Required Doc Changes

| Priority | Module | Change |
|----------|--------|--------|
| **HIGH** | 04 §3d | Correct method: `client.trading.partialLoanSell()` not `client.loans.hubPartialLoanSell()` |
| **HIGH** | 04 §3d | Correct signatures: `getLeverageCount(wallet)`, `getLeveragePosition(wallet, index)` — no tokenAddress param |
| **HIGH** | 18 | Update SDK reference table with correct signatures |
| **HIGH** | 04 §3d | Add explicit note: leverage lives on SWAP contract, not LOAN hub |
| **MEDIUM** | 04 §3d | Clarify 1-based indexing for leverage positions |
| **MEDIUM** | 04 §3d | Add LeveragePosition field mapping table |
| **LOW** | 04 §3d | Add troubleshooting: zeros at index 0 → check index 1 |

---

## The Correct Flow (for future reference)

```js
// READ positions
const count = await client.trading.getLeverageCount(wallet);
for (let i = 1n; i <= count; i++) {
  const pos = await client.trading.getLeveragePosition(wallet, i);
  if (pos[9]) { // active
    console.log(`Active position ${i}: ${formatUnits(pos[2], 18)} of token ${pos[1]}`);
  }
}

// CLOSE a position (100% = full close)
await client.trading.partialLoanSell(
  positionIndex,  // 1-indexed
  100n,           // percentage (must be divisible by 10)
  true,           // isLeverage
  0n              // minOut (use real slippage bound in production)
);
```
