# IR-001: XRP/USDC Markdown Short Loss

## Trade Summary
- **Coin**: XRP/USDC
- **Phase**: MARKDOWN (short)
- **Entry**: 2025-04-08 | Tier 1 short
- **Exit**: 2025-05-13 | Failure detector triggered
- **Invested**: $4,930.14
- **PnL**: -$1,675.32 (-34.0%)
- **Hold duration**: 35 days

## What the engine did
- XRP transitioned from DCA → MARKDOWN on ~April 8
- Entered tier 1 short position at ~$2.10
- Price reversed and rallied instead of continuing down
- Failure detector fired: price >25% above short entry AND ADX >25
- Forced close, transitioned to FLAT

## Market context
- XRP had a brief markdown signal (ADX + Fib break) but the move didn't sustain
- Price quickly reversed — likely a false breakdown / bear trap
- ADX remained >25 during the rally confirming strong upward momentum
- This was the only markdown failure across all 4 coins in 17 months of data

## Root cause: **Bad exit timing**
The failure detector worked correctly (cut the loss at -34%), but the fundamental issue is:
- The markdown entry signal was arguably correct — there WAS a Fib break + ADX signal
- But the move was shallow and reversed quickly
- The exit rule (25% above entry) guarantees a significant loss before firing

## Could it have been avoided?
**Yes — with the two-layer failure detector (Test Backlog #1):**
- If measuring 25% bounce from local bottom instead of from entry, the exit would have fired earlier
- If the short had moved 20%+ in profit first, the profit protector would have locked gains
- In this case, the short likely never got deep enough to activate the profit protector, so the original loss limiter would still fire — but potentially earlier

**Alternative approaches to test:**
- Shorter min hold for markdown (currently 3 days) — would faster exit have helped?
- Additional entry confirmation (e.g., require 2 consecutive days of ADX + Fib break)
- Volume confirmation on markdown entry

## Proposed improvement
→ See [Test Backlog #1: Two-Layer Markdown Failure Detector](../v13-test-backlog.md)

## Verdict: **Investigate**
This is the only markdown loss in the entire backtest. The -$1,675 was recovered and then some on subsequent XRP cycles (+$1,658 markup, +$2,499 unrealized short). But if we can eliminate it or reduce it, that's free alpha.

## Net impact on XRP performance
- This loss: -$1,675
- XRP total realized: +$5,756
- XRP total (incl. unrealized): +$8,255
- Without this loss: would be +$9,930
- **Impact**: ~17% drag on XRP total returns
