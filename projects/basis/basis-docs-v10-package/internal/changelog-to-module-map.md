# Changelog → Module Map (UPDATED)
**Source:** GeeGee SDK Test Report (17 items + 1 new, April 6-7 2026)
**Target:** V10 module files in `modules/` (post-renumber: 29 modules)

**Status: APPLIED.** Most items were already handled by Anakin in the V10 module build. Remaining gaps filled by GeeGee on April 7.

---

## Report Item 1: Wei amounts — ✅ ALREADY IN V10
All modules already use `* 10**18` notation. Prominent warning box at top of `10-atomic-skills.md`. Token Amount Conventions section in `17-getting-started.md`.

## Report Item 2: Staking flow is 5 steps — ✅ ALREADY IN V10
`staking.buy()` labeled "Wrap STASIS", `staking.sell()` labeled "Unwrap wSTASIS". Full flow in `10-atomic-skills.md`, `13-strategy-playbooks.md`, and `25-code-examples.md`.

## Report Item 3: Prediction market creation params — ✅ ALREADY IN V10
`marketName`, `symbol`, `optionNames`, `maintoken` all correct across `10-atomic-skills.md` and `25-code-examples.md`.

## Report Item 4: `leverage_buy()` signature — ✅ ALREADY IN V10
Full correct signature `(amount, minOut, path, numberOfDays)` with path-building examples.

## Report Item 5: Vesting `time_unit` enum — ✅ ALREADY IN V10
`TimeUnit Enum: 0=Second, 1=Minute, 2=Hour, 3=Day` documented in Vesting module. Alex added JSDoc annotations.

## Report Item 6: API auth — ✅ ALREADY IN V10
Three init modes documented in `17-getting-started.md`. Full auth section in `20-offchain-api-reference.md` with SIWE flow, API key management, and per-endpoint auth requirements.

## Report Item 7: `gasless` not a module — ✅ NOT PRESENT IN V10
`gasless` is not listed as a module anywhere in V10. Constructor config section in `17-getting-started.md` doesn't mention it either (it's a boolean flag, not documented as a module).

## Report Item 8: Faucet daily amount and signals — ✅ ALREADY IN V10
Full signal breakdown table in `17-getting-started.md`, `03-what-is-basis.md`, and `10-atomic-skills.md` (Faucet section). Identity gate documented. Daily drip model correct.

## Report Item 9: `get_tokens_by_creator` returns Predict+ tokens — ✅ APPLIED
Added note to `10-atomic-skills.md` `getTokensByCreator` method: "This also returns Predict+ tokens from prediction markets you created."

## Report Item 10: `staking.borrow()` in STASIS units — ✅ ALREADY IN V10
"The `stasisAmount` param is denominated in STASIS units, raw 18 decimals (not wSTASIS shares)" — explicitly documented.

## Report Item 11: `taxes.get_tax_rate()` requires user param — ✅ ALREADY IN V10
`getTaxRate(token, user)` with both params documented.

## Report Item 12: `private_markets` module — ✅ ALREADY IN V10
Full Private Markets module in `10-atomic-skills.md` with all write and read methods. Module 12 in `11-mcp-server.md` (18 tools). Reference added to `26-prediction-deep-dive.md`.

## Report Item 13: Minor fixes — ✅ MOSTLY IN V10, GAPS FILLED
- `sell_percentage` `to_usdb` flag: ✅ documented
- `leverage_simulator` path + 12-element return: ✅ documented with all 12 fields
- Base tax rates: ✅ in `18-fee-cost-reference.md`
- Surge quota: ✅ documented (7 days per 30-day window)
- Resolver constants: ✅ full table in `10-atomic-skills.md`
- Profile `avatar` endpoint: ✅ APPLIED — added to `20-offchain-api-reference.md`
- Reef post sections: ✅ already `human`/`agent`/`mixed`
- Reef post rate limit: ✅ APPLIED — added ~490s rate limit to `08-the-reef.md`

## Report Item 14: Agentic Economy framing — ✅ APPLIED
Added "The Agentic Economy" section to `01-welcome.md` with value creation thesis and activity → USDB → points → airdrop → real money loop. Existing framing in `03-what-is-basis.md` ("where agents build businesses, not just execute trades") and `05-token-value-incentive.md` (full scoring philosophy) already strong.

## Report Item 15: DeFi Primitive Playbooks — ✅ APPLIED
New module `12-defi-primitive-playbooks.md` created. Covers token type selection (Stable+ vs Floor+ vs Predict+), staking sizing, loan/leverage risk framework, prediction market roles, STASIS flywheel. Inserted at position 12, before strategy playbooks (13).

## Report Item 16: Quickstart stops at "you're funded" — ✅ ALREADY IN V10
`17-getting-started.md` Step 3 says "your strategy may vary" and points to archetypes and decision trees. Not overly prescriptive.

## Report Item 17: Layered What/Why/How framework — ✅ DONE
L1 files (10) + navigation spine (V5) + cross-reference map. Complete.

## Report Item 18: MCP `upload_image_from_file` tool (NEW) — ✅ APPLIED
Added `upload_image_from_file` tool to `11-mcp-server.md` Module 15 table.

---

## Summary

| Status | Count |
|--------|-------|
| Already in V10 (Anakin handled) | 12 |
| Applied by GeeGee (April 7) | 6 |
| **Total resolved** | **18/18** |

### Changes made by GeeGee:
1. `10-atomic-skills.md` — Added Predict+ note to `getTokensByCreator`
2. `08-the-reef.md` — Added ~490s post rate limit
3. `20-offchain-api-reference.md` — Added `avatar` payload key to `updateMyProfile`
4. `01-welcome.md` — Added Agentic Economy section
5. `11-mcp-server.md` — Added `upload_image_from_file` tool
6. `26-prediction-deep-dive.md` — Added Private Markets section
7. `12-defi-primitive-playbooks.md` — New module (token selection, staking, loans, prediction roles, flywheel)
