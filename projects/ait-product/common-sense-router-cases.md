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

---

## Vision: CFGI-Free Coin Universe Expansion

### The Bottleneck
Currently V14's coin universe is limited to ~15 coins with CFGI (Crypto Fear & Greed Index) data. CFGI serves two critical functions:
1. **Phase transition gating** — deciding when to flip between LONG_DCA and SHORT_DCA
2. **Bottom conviction scoring** — raw CFGI < 35 is one of the 4 conviction stack signals

This means coins without CFGI data (most of the market) are permanently excluded, even if they have ideal DCA cycling characteristics.

### The Opportunity
ETH scores "D" on V14 scanner (+8.6% ROI, -55.7% DD) while HBAR scores "A+" (+423%). The difference isn't the engine — it's the coin's **behavioral fit**. V14's sweet spot is coins with:
- Clean mean-reversion behavior (tight Bollinger Band cycling)
- Predictable volatility ranges (consistent ATR)
- Sufficient liquidity (tight spreads, deep order books)
- Responsive BTC correlation (follows macro moves cleanly)
- Clear phase structure (trending or ranging, not choppy)

None of these traits require CFGI to measure.

### AI Replacement Signals
The Common Sense Router could replicate CFGI's two jobs using publicly available data:

**For phase transition gating (replacing CFGI regime):**
- RSI divergences across multiple timeframes
- Volume profile shifts (accumulation vs distribution)
- Funding rates (perp market sentiment)
- Open interest changes (positioning shifts)
- Order book depth imbalance (bid/ask pressure)
- Social sentiment aggregation (alternative to CFGI)

**For bottom conviction (replacing raw CFGI < 35):**
- Multi-timeframe RSI exhaustion
- Capitulation volume spikes
- Funding rate extremes (mass liquidation signals)
- Historical volatility compression (pre-reversal squeeze)

### Architecture Evolution
The natural progression:
1. **V14 engine stays fixed** — the DCA grid mechanics work, don't touch them
2. **Scanner expands to full perps market** — score ALL coins on behavioral fit, not just CFGI-eligible ones
3. **AI layer replaces CFGI gating** — Common Sense Router provides phase transition signals using the alternative indicators above
4. **Dynamic coin rotation** — rotate into whichever 4-8 coins are in V14's sweet spot *right now*, not a static list

### Product Impact
- Coin universe: 15 → potentially 50-100+ qualified coins
- Coin rotation becomes a feature: always trading the best-fit coins for current conditions
- Removes dependency on third-party CFGI API
- Each customer's bot could run a personalized coin selection optimized for their capital tier

### Integration with 2F
This is the north star for the Common Sense Router project:
- **Phase 1 (current):** Case studies + incident reports teach it what "wrong" looks like
- **Phase 2:** AI replicates CFGI signals using public indicators, validated against historical CFGI data
- **Phase 3:** AI-driven coin scoring replaces static qualified list
- **Phase 4:** Full autonomous coin rotation with AI phase management

### Brett's Input (2026-03-01)
- Identified that CFGI limits coin universe as a scaling bottleneck
- Vision: AI conviction layers on top of programmed gates enables broader coin offering
- Coins that hit V14's sweet spot can be identified by behavioral traits, not sentiment data availability

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
