# Alex Checklist — March 21, 2026

Items needed to push SDK docs from 7.5-8/10 to 9/10. Prioritized by impact on fresh agent reviews.

## P0 — Blocking doc quality improvements

### 1. Return schemas for read methods
**Why:** Repeatedly flagged as the #1 improvement across all reviews. "Write methods get full docs, read methods get one-liners like 'returns details.'"

Need JSON return shapes for at minimum:
- `getLeveragePosition(user, id)` — what fields come back?
- `getLeverageCount(user)` — just a number?
- `simulateLeverage(amount, path, days)` — exact output schema
- `simulateLeverageFactory(amount, path, days)` — exact output schema
- `getVestingDetails(tokenAddress, vestingId)` — full object shape
- `getMarketData(marketAddress)` — prediction market state object
- `getDisputeData(marketAddress)` — dispute/resolution state
- `getLoanDetails(hubId)` — loan state, expiry, amounts
- `staking.convertToAssets(shares)` — what does this return?

### 2. hubId vs loanId abstraction in SDK
**Why:** Every reviewer flagged this as a "silent footgun" and "money-losing bug waiting to happen." Suggestion: `partialLoanSell` should accept the same ID format as other loan methods, with conversion handled internally.

If SDK abstraction isn't feasible short-term, at minimum confirm: is `getLeverageCount() - 1` always the correct ID for `partialLoanSell()`?

### 3. Points system backend build
**Why:** Full spec ready at `points-system-complete-spec.md`. Diamond wants this built with Claude Code. Spec includes all mechanics, DB schema, anti-sybil layers, Prisma models.

## P1 — TBD placeholders (affects doc rating)

### 4. Molt tier advancement thresholds
What activity earns what tier? Even ranges would help. Currently "TBD — will be announced before TGE."

### 5. Surge tax maximum rate limits
What's the max a creator can set? Currently "TBD — check with Alex."

### 6. Private market voting timer duration
How long is the voting window? Currently "TBD — check with Alex."

### 7. ACS query endpoint
"Coming soon — not yet available in SDK." Every reviewer asked for this. Even a basic `/acs/{wallet}` returning a score would help.

## P2 — SDK / API additions

### 8. Post SDK tweet verification update
Alex said "remind me" — the tweet verification endpoints are live but SDK wrapper needs publishing.

### 9. Referral system
Is it built? If so, needs documenting. If not, when?

### 10. Split buy function
Diamond mentioned a swap contract function that does partial leverage + normal buy. Is it exposed in SDK? If so, document it.

### 11. Tokens created via createToken() (no metadata)
Are they intentionally hidden from the dapp? Or is there a way to add metadata after creation?

## P3 — Nice to have

### 12. Error recovery patterns for agents
Reviewers asked for: retry logic examples, detecting stale state, handling 429s under sustained load.

### 13. Session management for long-running agents
What happens when SIWE session expires mid-operation? Does SDK auto-renew?

### 14. Gas cost estimates per operation type
Currently says "$0.01-$1.20" — which operations are expensive vs cheap?

---

**Context:** We ran 10+ fresh agent reviews today. Score went from 6.5 → 8/10. Items 1-2 are the biggest remaining blockers. Everything else we could fix without Alex is done.

**New additions today (for Alex's awareness):**
- 25% airdrop allocation stated in docs (20% general + 5% top-50 leaderboard)
- Leaderboard = USDB balance, top 50, on-chain analysis before payout
- Anti-sybil section expanded (behavioral analysis, wallet graph, diminishing returns, nuclear USDB transfer ban)
- Appeals process added
- Leverage section fully rewritten (no liquidation narrative, expiry mechanics, fee framing, DIY leverage)
- Token narratives rewritten (Floor+ crash resistance, Stable+ velocity use cases, Predict+ lifecycle)
- startLP fully explained (virtual/free, dollar-scale dial)
