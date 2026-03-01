# V13 Incident Reports — Losing Trade Analysis

Every losing trade gets a post-mortem. No exceptions.

## Report Template

Each report should cover:

1. **Trade Summary**: Coin, phase, entry/exit dates, entry/exit prices, PnL, hold duration
2. **What the engine did**: Which signals fired, phase transitions, tier levels
3. **Market context**: What was happening (trend, ADX, volatility, macro events)
4. **Root cause**: Why did the trade lose? Categories:
   - **Bad entry** — signal was wrong, shouldn't have entered
   - **Bad exit** — exit too late or too early
   - **Regime mismatch** — strategy doesn't fit this market condition
   - **Black swan** — unpredictable external event
   - **Mechanical** — bug, data issue, execution problem
5. **Could it have been avoided?**: With what rule change or additional signal?
6. **Proposed improvement**: Specific testable change (→ link to test backlog entry)
7. **Verdict**: Accept (cost of doing business) / Investigate (needs engine change) / Fix (clear bug)

## Reports

| # | Date | Coin | Phase | PnL | Root Cause | Verdict |
|---|------|------|-------|-----|------------|---------|
| IR-001 | 2025-04-08→05-13 | XRP/USDC | MARKDOWN | -$1,675 (-34%) | Bad exit timing | Investigate |
| IR-002 | 2025-02-16→02-22 | LINK/USDC | DCA | -$32 (-4.9%) | Normal DCA loss | Accept |

---
