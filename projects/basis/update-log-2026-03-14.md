# Update Log — 2026-03-14

## Context
Alex delivered the complete SDK contract reference covering all 13 deployed contracts. Diamond's platform walkthrough corrections (in `mechanics-corrections.md`) needed to be applied across all docs. The old REST API approach in dev-plan.md and project-plan.md needed to be superseded with the actual direct-contract-call architecture.

---

## Changes Made

### 1. `skill-scaffold/references/api-reference.md` — REPLACED
- **Before:** Placeholder with invented function signatures and fake REST endpoints
- **After:** Alex's complete SDK reference covering all 13 contracts (ASwap, A_STABLETOKEN, FACTORYTOKEN, ATokenFactory, ALOAN_HUB, AStasisVault, ATaxes, ALEVERAGE, A_VestingContract, AMarketTrading, AMarketResolver, APrivateTradingMarket, AMarketReader)
- Added header note: "Source: Alex's SDK Reference (2026-03-14). Contract addresses resolved dynamically by SDK."
- Added agent note on `mixedBuy` (SDK/agent-only, not on frontend)
- Added leverage note clarifying dynamic behavior (not fixed 36x)

### 2. `dev-plan.md` — REWRITTEN
- **Stripped:** All fake REST API endpoint listings (POST /api/v1/tokens/create, etc.)
- **Added:** Complete list of 13 deployed contracts with their roles
- **Reorganized** around: What's deployed/done, what's in progress, what's remaining
- **Kept:** Points system backend section (still needed as new build)
- **Kept:** Phase structure with updated statuses
- **Added:** Note that Alex manages GitHub/public releases
- **Updated:** Questions for Alex section — marked answered items, added new questions (SDK release timeline, mixedBuy scope, USDB faucet details)
- **Removed:** References to "Agent API layer" wrapping contracts with REST endpoints

### 3. `gitbook-drafts/executive-summary.md` — CORRECTED
- Fixed Stable+ description: clarified that price appreciation comes from **slippage retention** (price impact stays in pool), NOT fee injection. Fees go to creator/vault/platform.
- Clarified leverage: "dynamic (up to ~36x on deep pools, varies by position size)" instead of implying fixed 36x
- Clarified Predict+: emphasized ONE token per market with separate betting pool

### 4. `docs-drafts/faq.md` — CORRECTED (7 fixes)
- Fixed Stable+ mechanics: slippage retention, not fee injection
- Fixed Floor+ stability dial: 0%–100% range with default 0% (not 50%–90%)
- Fixed Predict+: ONE token per market, not one per outcome. Clarified token trading vs outcome betting separation
- Fixed leverage: dynamic (not toggle), with real-world examples from Diamond's data
- Added `mixedBuy` mention as agent/SDK-only function
- Updated SDK references: "being built by Alex" instead of "install basis-sdk"
- Updated agent onboarding: direct contract calls now, SDK coming

### 5. `docs-drafts/strategy-playbooks.md` — CORRECTED
- Strategy A: Replaced "36x leverage" with dynamic leverage description, added `mixedBuy` tip, added `ALEVERAGE.simulateLeverage()` risk check
- Strategy C: Fixed "fees inject" → "slippage stays in pool" (2 occurrences)
- Risk parameters: Changed `max_leverage: 1-36` to description of dynamic leverage + `mixedBuy`

### 6. `docs-drafts/earning-guide.md` — CORRECTED
- Fixed "fees inject into liquidity" → "slippage stays in pool"
- Fixed leverage description: dynamic with real examples ($5 ≈ 28x, $100 ≈ 17x on $1K pool), not "36x toggle"

### 7. `docs-drafts/getting-started-agents.md` — VERIFIED
- Already updated in a prior session. References direct contract calls, Alex building SDK, proper contract names. No changes needed.

### 8. `skill-scaffold/SKILL.md` — CORRECTED
- Fixed Token Type Reference table: replaced "36x (always)" with "Dynamic (up to ~36x, depends on pool depth + position size)"
- Replaced Swagger TODO link with actual contract reference link
- Already had correct SDK status from prior update

### 9. `index.md` — UPDATED
- Added `mechanics-corrections.md` and `update-log-2026-03-14.md` to file listing
- Updated leverage model in Key Decisions: "Dynamic (up to ~36x)" with mixedBuy note
- Updated Section 5 description: "dynamic leverage" instead of "leverage toggle (36x/1x)"
- Updated Section 12 description to reflect current status
- Updated Alex's API stack decision as answered
- Date was already 2026-03-14 from prior update

### 10. `project-plan.md` — TARGETED UPDATES
- Section 3b: Marked REST API endpoints as superseded with correction note. Struck through fake endpoints. Preserved read-only API references that still apply.
- Section 12: Already updated in a prior session — verified correct (all 13 contracts listed, contract ref delivered, SDK in progress, Alex manages releases)

---

## Files NOT changed (by design)
- `mechanics-corrections.md` — Source-of-truth reference, kept intact
- `project-plan.md` Sections 1-11, 13-15 — Only Section 3b and 12 touched per instructions
- `outreach/*` — Not in scope for this update
- `gitbook-drafts/*` (other than executive-summary.md) — Not in scope
- Script stubs in `skill-scaffold/scripts/` — Will be updated when SDK ships

---

## Key patterns corrected across all docs

| Old (incorrect) | New (correct) | Source |
|---|---|---|
| "36x leverage toggle" | Dynamic leverage (up to ~36x, depends on pool depth + position size) | Diamond's live walkthrough data |
| "Fees inject into liquidity" (Stable+) | Slippage retention — price impact stays in pool. Fees go to creator/vault/platform | Diamond's corrections |
| "One token per outcome" (Predict+) | ONE token per market. Betting on outcomes is separate via USDC pool | Diamond's corrections |
| Floor+ stability dial 50%–90% | 0%–100%, default 0% (most volatile) | Diamond's corrections |
| REST API endpoints for write ops | Direct contract calls via web3. SDK being built by Alex | Alex's architecture correction |
| `pip install basis-sdk` | SDK being built by Alex, not yet published. Use direct contract calls | Alex |
| "Swagger docs from Alex" | Alex delivering SDK with usage docs. Contract reference already delivered | Alex (2026-03-14) |

---

## Open items flagged with `<!-- TODO: verify -->`
- `docs-drafts/faq.md`: Floor+ stability dial range — "verify stability dial range and default with Alex"
