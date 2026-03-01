# Common Sense Router — Case Studies

Cases where rigid signal gates produce suboptimal decisions that a human (or AI with broader context) would override. These inform the design of Project 2F: AI-Governed Signal Override.

---

## Case 1: HBAR Long Flip — Exhausted Downside (2026-03-01)

### Situation
- HBAR in SHORT_DCA since July 31, 2025 (~7 months)
- Current price: $0.0997
- 2W StochRSI K = 0 (pinned), CFGI = 50.5
- Bottom conviction gate requires: CFGI < 35 + 2W K ≥ 5 (after pin) + score ≥ 3/4
- System says: stay short, no conviction signal

### What a human sees
1. **Retracement exhaustion**: 84.7% of the Nov 2024 → Jan 2025 cycle move already retraced. Diminishing short profit potential.
2. **Liquidation math**: At 1.5x leverage, long entry @ $0.0997 → liquidation at $0.0337 (66% below). Recent support at $0.072 is only 28% below — nowhere near liquidation.
3. **Double bottom structure**: Two bounces off $0.072 (Oct 2025, Feb 2026). Clear demand zone.
4. **Risk/reward asymmetry**: Short from here captures maybe 10-20% more downside. Long from here could capture 100%+ upside with minimal liquidation risk.

### Why the system misses it
- Bottom conviction stack requires specific technical conditions (CFGI < 35, 2W K recovery from pin)
- These are lagging indicators — by the time they fire, price may have already moved 30%+
- The system has no concept of "diminishing returns on current position" or "capital risk assessment"
- Fib retracement levels and structural support aren't part of the signal stack

### Common Sense Override Logic (proposed)
- **Retracement depth check**: If price has retraced > 80% of the cycle move, flag diminishing short value
- **Liquidation distance check**: If flipping long has > 50% distance to liquidation, risk is negligible
- **Structural support check**: Multiple bounces off a level = demand zone confirmation
- **Time in phase check**: 7+ months in one direction with price stabilizing = potential regime exhaustion

### Outcome (2026-03-01)
- **Manual override executed**: HBAR flipped SHORT_DCA → LONG_DCA
- Existing short closed during hourly catchup
- HBAR immediately started cycling longs in $0.095-$0.105 range
- Portfolio equity jumped $67K → $70K from catchup trades alone
- Wrapper code updated: orphaned short TPs now checked during LONG_DCA phase

### Decision Framework
This isn't about overriding the conviction stack — it's about adding a parallel "sanity check" layer:
- Conviction stack says WHEN to flip (precise timing)
- Common sense says WHETHER staying in current direction still makes sense (risk management)
- If common sense says "no reasonable risk to flip" AND conviction is close-ish, consider early flip or at minimum stop adding to shorts

### Monthly Chart Confirmation (2026-03-01)
- 1M chart shows HBAR retesting the 2022-2023 accumulation range ($0.05-$0.10) — the exact zone it consolidated in for ~2 years before the Nov 2024 breakout
- Monthly RSI neutral (42-51), no selling pressure
- Price sitting on long-term structural support (green zone on chart)
- However: project/coin interest may be fading — could grind sideways without catalyst
- Implication: even if it doesn't go up, the short has played out. Risk/reward favors neutral or long.

### Brett's Input (2026-03-01)
- "If we did switch to longs, there is no reasonable capital risk. We are still above recent retest levels, bouncing along a level of support."
- "It's kind of finding support and doesn't look like it has much other choice than to go up. Now there may not be much interest in the project or coin. So it may not be a great pick for the bear market or next bull cycle."
- Monthly charts as context gates (not triggers) — confirmed principle. The monthly structure informs risk assessment, not entry timing.

---

## Template for Future Cases

### Case N: [Title] — [Core Issue] (Date)

### Situation
- Current state of the position/signal
- What the rigid system says

### What a human sees
- The broader context the system misses

### Why the system misses it
- Which gates/signals fail and why

### Common Sense Override Logic (proposed)
- What rules would catch this

### Decision Framework
- How this integrates with existing system

### Brett's Input
- Direct quotes if available
