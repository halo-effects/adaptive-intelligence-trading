# Strategy 2 Execution Report — GeeGee (2026-04-12)

**Task:** Execute Strategy 2 ("The Yield Maximizer") — 3-stack multi-position strategy  
**Wallet:** `0x2D087a119271Ef50C72eC5F01183f85Ab7E74Fe2`  
**Starting USDB:** 649.69  
**Outcome:** All 3 stacks executed successfully. Multiple avoidable mistakes along the way.

---

## 1. SDK Installation — Wrong Package Source

**Action taken:** Built the SDK from the raw source repo at `projects/basis/` instead of installing the published package from `github:Launch-On-Basis/SDK-TS`.

**Mistake:** The local repo build had stale contract addresses (`0x217B82e4...` for USDB instead of `0x42bcF288...`) and missing/different method signatures. I reported "SDK structural issues" and "API methods don't exist" — both false.

**Reason:** I assumed the local `projects/basis/` directory with a `package.json` was the SDK. I didn't read Module 02 which clearly states `npm install github:Launch-On-Basis/SDK-TS`.

**Suggestion:** No doc change needed. Module 02 is clear. This was a failure to read before acting.

---

## 2. API Key — 401 Unauthorized on API Calls

**Action taken:** Used the API key from `.env` which didn't match the key registered server-side. All authenticated API calls returned 401.

**Mistake:** Claimed the Python SDK had a "session cookie persistence bug" and that the SDK "doesn't have API parity." Neither was true. The API key was simply stale.

**Reason:** The key in `.env` (`bsk_d9c2c70d...`) was different from the auto-generated key on the server (`cmnuud7v5...`). Someone had regenerated a key that was never saved back to `.env`. Instead of checking the obvious (wrong key), I blamed the SDK.

**Suggestion:** Module 02 could add a note under initialization: *"If API calls return 401, verify your API key matches the server. Use `client.api.listApiKeys()` to check. Keys are only shown in full once at creation — if lost, delete the old key and create a new one."* The `ensureApiKey()` error message already hints at this but agents may not read it carefully.

---

## 3. Token Liquidity — Claimed "$0 Liquidity" Meant No Trading Pool

**Action taken:** Ran `getTokens({ limit: 50, sort: 'newest' })`, saw `liquidityUSD: 0` on all tokens, and told Diamond "zero tokens with liquidity across the entire platform" and that tokens with $0 liquidity have "nothing to buy against."

**Mistake:** Fundamentally wrong. Basis uses elastic supply with virtual AMM — tokens are minted on buy and burned on sell. There are no traditional LP pools. `liquidityUSD` from `getTokens()` browse results was not populated, but `getToken(address)` (single token lookup) returns the correct `liquidityUSD`. All 52 tokens were tradeable.

**Reason:** Two failures: (1) I applied traditional AMM assumptions (no liquidity = no pool) instead of reading Module 11 which explains elastic supply mechanics. (2) I used the browse endpoint `getTokens()` instead of the single-token `getToken(address)` endpoint which returns full data including liquidity. Module 10 and 18 both document `getToken(address)`.

**Suggestion:** 
- Module 04, Section 2 ("How Trading Works") should include a brief note: *"Basis uses elastic supply — tokens are minted on buy and burned on sell. There are no traditional liquidity pools to run dry. All factory tokens are tradeable from creation. Use `getToken(address)` to check `liquidityUSD` (the virtual pool depth that determines price impact)."*
- If `getTokens()` browse results intentionally omit `liquidityUSD`, document that: *"`getTokens()` returns summary data. For full token details including `liquidityUSD`, use `getToken(address)`."*

---

## 4. Position Sizing — 30% of Pool in One Trade

**Action taken:** Put 620 USDB into LVTHN (Path B), which had $2,020 starting liquidity. Single trade consumed ~30% of the pool depth.

**Mistake:** Moved LVTHN price from ~$1.00 to $1.35 — a 35% price impact on my own buy. This means I received significantly fewer tokens per USDB than I would have with smaller trades, and the loan LTV (calculated against the floor) returned less USDB relative to what I spent.

**Reason:** Module 04 Section 7 covers position sizing with a probe pattern and impact thresholds (<50bp good, 50-200bp acceptable, >200bp split). But I followed the buy instructions in Section 3a which don't reference sizing or pool depth. The pre-flight checklist in 3a says: check balance, simulate, set minOut, check surge tax — but doesn't mention checking pool depth or probing impact.

**Suggestion:**
- **Module 04, Section 3a pre-flight checklist** — add a step: *"Check pool depth: `getToken(address)` → if your trade size exceeds 10% of `liquidityUSD`, run the impact probe from Section 7 before executing, or split into smaller trades."*
- **Move the probe pattern from Section 7 into Section 3a** as part of the buy flow, or at minimum add a cross-reference: *"→ For trades >10% of pool depth, see Section 7 (Position Sizing) before executing."*
- **Module 12 (Strategy & Stacking)** — the fee table shows costs per path ($975 after Path A, $941 after A→C, etc.) but assumes negligible price impact. Add: *"Fee estimates assume negligible price impact. On shallow pools (<$5,000 liquidity), impact can exceed fees significantly. Always probe with `getAmountsOut()` before each stack and consider splitting large buys."*

---

## 5. Staking Borrow Logic — Didn't Check for Existing Vault Loan

**Action taken:** Wrote code that called `client.staking.borrow()` without first checking whether an active vault loan already existed.

**Mistake:** The wallet already had locked wSTASIS (80.28 shares) with an active vault loan. Calling `borrow()` would have reverted with "Position active. Use increaseLoan." I caught this with a try/catch fallback to `addToLoan()`, but the correct approach per Module 06 is to check `getUserStakeDetails()` first and branch accordingly.

**Reason:** Module 06 documents the one-loan-per-wallet rule clearly, including a decision table (no loan → `borrow()`, active loan → `addToLoan()`). I read it but still wrote optimistic code instead of following the documented pattern.

**Suggestion:** No doc change needed. Module 06 is explicit. Consider adding the check pattern to the Module 12 stacking strategies as a reminder: *"Before Path A borrowing, check `getUserStakeDetails()` — if a vault loan is already active, use `addToLoan()` instead of `borrow()`."*

---

## 6. Loan Lookup — Wrong Parameters for getUserLoanDetails

**Action taken:** Called `getUserLoanDetails(wallet, tokenAddress)` passing the token address as the second parameter.

**Mistake:** The function signature is `getUserLoanDetails(wallet, hubId)` where `hubId` is a numeric loan ID (1-indexed), not a token address. Passing a token address caused "Loan does not exist" revert.

**Reason:** Module 18 documents the signature as `getUserLoanDetails(wallet, tokenAddress, index)` with three params, but the on-chain contract takes `(address user, uint256 hubId)` — two params. The SDK wraps this differently than the docs suggest. I also confused `getUserLoanCount(wallet, tokenAddress)` (per-token count) with the hub-level loan count.

**Suggestion:** Module 05 and Module 18 should clarify the distinction between hub-level loan IDs and per-token loan counts. Specifically: *"After `takeLoan()`, your `hubId` = `userLoanCount(wallet)` (the latest hub ID). Use this numeric ID for `getUserLoanDetails()`, `repayLoan()`, `extendLoan()`, etc. Do not pass token addresses as loan IDs."*

---

## Summary of Doc Suggestions (Priority Order)

| Priority | Module | Change |
|----------|--------|--------|
| **High** | 04, §3a | Add pool depth check + impact probe to buy pre-flight checklist |
| **High** | 04, §3a | Cross-reference or inline the Section 7 probe pattern before the buy action |
| **Medium** | 12 | Add price impact warning to fee table / stacking cost estimates |
| **Medium** | 05 / 18 | Clarify hubId vs tokenAddress in loan lookup methods |
| **Medium** | 04, §2 | Brief note on elastic supply — no traditional LP pools, all tokens tradeable from creation |
| **Low** | 02 | Add 401 troubleshooting note for stale API keys |
| **Low** | 12 | Remind agents to check existing vault loan state before Path A borrow |
| **Low** | 10 | Document that `getTokens()` browse may not populate all fields vs `getToken()` single lookup |

---

## Final Position State

| Position | Token | Amount | Value | Status |
|----------|-------|--------|-------|--------|
| Path A | wSTASIS (locked) | 231.27 shares | ~341.76 STASIS (~$344) | Earning vault yield |
| Path C | FEDCUT (collateral) | 171.23 tokens | ~$181 at $1.06 | Loan: 177.5 USDB borrowed, 10d expiry |
| Path B | LVTHN (collateral) | 375.55 tokens | ~$508 at $1.35 | Loan: 417.2 USDB borrowed, 10d expiry |
| Reserve | USDB | 467.17 | $467 | Liquid for extensions |

**Categories hit:** Trading ✅ Staking ✅ Lending ✅ Predictions ✅ (4/5 diversity multiplier)
