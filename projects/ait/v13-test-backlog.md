# V13 Test Backlog

Track potential improvements, observed issues, and ideas to backtest against the V13 engine.
Foundation: `v13_phase_backtest_v8.py` — the validated engine (+199% portfolio ROI).

---

## #1 — Two-Layer Markdown Failure Detector (Profit Protector)

**Date raised:** 2026-02-25
**Origin:** Brett observed that the current failure detector (25% above short entry) guarantees a loss when it fires. Could we exit while still profitable?

**Current behavior:**
- Failure detector fires when price rises >25% above **short entry price** + ADX >25
- Always exits at a loss (you're 25%+ underwater on the short)
- Example: XRP trade #34, Apr–May 2025, -$1,675 (-34%)

**Proposed change — two layers:**
1. **Profit protector**: Once short is ≥20% in profit, track the local bottom. If price bounces 25% from that bottom, exit with profit locked in.
2. **Loss limiter**: Original rule unchanged — if short never gets deep enough, 25% above entry still catches bad trades.

**Key considerations:**
- Must ensure the "spring" is deep enough — a shallow 10% dip + 25% bounce is just noise, not a reversal signal
- Dead cat bounces in deep downtrends: ADX staying >20 should help distinguish real reversals from traps
- The 20% profit threshold prevents premature activation on shallow moves

**What to test:**
- Backtest all 4 coins (ETH/SOL/LINK/XRP) with two-layer detector vs current single-layer
- Vary the profit activation threshold (15%, 20%, 25%)
- Vary the bounce-from-bottom threshold (20%, 25%, 30%)
- Compare: total portfolio ROI, max drawdown, number of failed shorts, avg short hold time
- Specifically check: would it have saved XRP trade #34's -$1,675 loss?
- Check for false exits: does it shake you out of profitable deep trends too early?

**Priority:** Medium — current engine is solid, test after paper bot proves stable

---

## Template

### #N — [Title]

**Date raised:** YYYY-MM-DD
**Origin:** [How this came up — observation, loss, idea, etc.]

**Current behavior:**
[What the engine does now]

**Proposed change:**
[What we'd test]

**What to test:**
[Specific backtest parameters and metrics]

**Priority:** [High / Medium / Low]
