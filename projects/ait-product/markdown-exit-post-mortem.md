# Markdown Exit Engine — Post-Mortem & Future Development Guide

**Date:** 2026-02-23  
**Status:** Scrapped for V12f. Insights preserved for future iterations.  
**Data source:** V12f A/B/C backtest, ETH/USDT Oct 2020 → Feb 2025, Medium profile, $10K start

---

## 1. What Happened

Mode C (V12f gates + markdown exit engine) was tested against Mode A (V12e baseline) and Mode B (gates only). Results:

| Mode | Final Equity | P&L % | Trades | Max DD |
|------|-------------|-------|--------|--------|
| A (V12e baseline) | $71,687 | +617% | 84 | 52.5% |
| B (Gates only) ✅ | $107,606 | +976% | 110 | 52.5% |
| C (Gates + MD exit) ❌ | $63,922 | +539% | 91 | 47.9% |

**Mode C lost $43,684 vs Mode B** (-$7,766 vs even the baseline).

---

## 2. Root Cause: Gate Evaluation Explosion

The fundamental problem is that the markdown exit engine creates a **feedback loop** with the gate system:

| Metric | Mode B (gates only) | Mode C (gates + MD exit) | Ratio |
|--------|-------------------|------------------------|-------|
| EXIT gate evaluations | 23 | **258** | 11.2× |
| EXIT blocks | 20 | **152** | 7.6× |
| EXIT passes | 3 | **106** | 35.3× |
| MARKDOWN evaluations | 3 | **106** | 35.3× |
| MARKDOWN blocks | 0 | **11** | — |
| MARKDOWN passes | 0 | **95** | — |
| **Total gate decisions** | **29** | **366** | **12.6×** |

### Why This Happens

1. The markdown exit engine aggressively tries to transition to EXIT phase during distribution signals
2. The EXIT gate (correctly) blocks many of these because sentiment is still positive
3. But each time the gate blocks, the engine retries on the next candle (hourly)
4. When EXIT finally passes, the MARKDOWN gate gets evaluated repeatedly too
5. When MARKDOWN is blocked (11 times), the engine falls back to DCA instead of holding the MARKUP position
6. This creates a **rapid cycling pattern**: MARKUP → blocked EXIT → DCA → re-enter MARKUP → blocked EXIT → ...

### The Destructive Cycle

```
MARKUP phase (profitable, should hold)
  ↓ markdown exit engine detects distribution signal
  ↓ tries EXIT transition
  ↓ EXIT gate BLOCKS (sentiment still rising)
  ↓ engine falls back to DCA
  ↓ loses markup position
  ↓ re-enters on next signal
  ↓ tries EXIT again...
  ↓ repeat 152 times
```

Each cycle incurs:
- Lost position (sells markup, re-buys at DCA)
- Transaction fees on unnecessary trades
- Missed compounding from being out of position during micro-recoveries

---

## 3. Specific Failure Patterns (from gate decision data)

### Pattern A: March 2024 Rally Destruction
- **Period:** Mar 6-11, 2024 (ETH $3,769 → $4,067)
- Mode B: 20 EXIT blocks held position through entire rally → captured $36K
- Mode C: 152 EXIT blocks + 106 passes → churned in and out, net result worse than baseline
- The markdown engine saw distribution signals during what was actually a healthy markup consolidation

### Pattern B: MARKDOWN Gate False Starts (June 2024)
- **Period:** Jun 3-5, 2024 (ETH $3,769 → $3,820)
- 11 MARKDOWN blocks with `rsi_roc_3d` ranging 2.2-5.4
- The markdown engine wanted to short, but sentiment was mixed
- Gate correctly blocked, but engine had already exited markup position
- Damage: lost markup position for sideways movement

### Pattern C: High-Frequency Evaluation Cascades
- When both EXIT and MARKDOWN pass, the engine evaluates **every single candle** (hourly)
- Mar 7-8, 2024: 24 consecutive EXIT passes + 24 MARKDOWN passes = 48 evaluations in 24 hours
- Compare Mode B: 0 evaluations in same period (held markup, no transition attempted)

---

## 4. Key Insights for Future Development

### Insight 1: The markdown engine and DCA engine have fundamentally different time horizons
- **DCA engine:** Patient, accumulates over days/weeks, profits from scale-out on recovery
- **Markdown exit engine:** Aggressive, tries to time distribution on hourly candles
- These fight each other. When the exit engine sells, DCA wants to buy back.

### Insight 2: Gate blocking + fallback to DCA is the worst of both worlds
- Blocking a transition should mean "stay in current phase" not "fall back to DCA"
- When EXIT is blocked, the engine should remain in MARKUP (not drop to DCA)
- **Future fix:** Gate blocks should be "hold current phase" rather than "revert to default"

### Insight 3: Evaluation frequency must be throttled
- 258 EXIT evaluations vs 23 in Mode B = the engine is checking too often
- **Future fix:** After a gate block, implement a cooldown (e.g., 24h minimum before re-evaluation)
- Alternative: Only evaluate EXIT on phase change triggers, not every candle

### Insight 4: Distribution detection needs higher conviction before attempting transition
- The markdown engine triggered on weak signals that turned out to be consolidation, not distribution
- **Future fix:** Require minimum distribution score (e.g., 70+) before even attempting EXIT
- Current: tries EXIT on any distribution signal → floods gate with low-conviction attempts

### Insight 5: The 47.9% DD advantage is real but not worth the cost
- Mode C had lower drawdown (47.9%) vs Mode B (52.5%)
- This confirms the markdown engine does reduce risk during actual drawdowns
- **Future opportunity:** A more selective markdown engine that only fires during high-conviction events (not every consolidation) could capture the DD reduction without the return destruction

### Insight 6: MARKDOWN gate dual-indicator requirement works perfectly
- 11 blocks, 95 passes — the gate correctly filtered the few cases where sentiment didn't confirm
- The problem isn't the gate — it's the volume of attempts reaching the gate
- **The gates are good. The engine feeding them is too aggressive.**

---

## 5. Future Architecture Recommendations

### 5a: Conviction-Gated Markdown Exit (Recommended Next Approach)
Instead of the current "attempt EXIT on any distribution signal":
1. Accumulate a **markdown conviction score** over multiple candles (like how DCA accumulates layers)
2. Only attempt EXIT when conviction exceeds threshold (e.g., 3 consecutive declining CFGI readings + distribution score > 70)
3. Add minimum holding period per phase (e.g., 48h in MARKUP before EXIT is even considered)
4. On gate block: add cooldown, don't fall back to DCA

### 5b: Asymmetric Gate Response
- EXIT gate BLOCK → stay in current phase (MARKUP/SPRING/DCA), do NOT transition
- EXIT gate PASS → proceed normally
- This prevents the "block → fall to DCA → re-enter" cycle

### 5c: Phase Transition Debounce
- After any gate block, minimum 24-candle cooldown before same gate re-evaluates
- Prevents the 152-block cascade that killed Mode C

### 5d: Separate "Protective" vs "Offensive" Markdown
- **Protective:** Reduce position size during extreme distribution (scale out 25-50%), don't fully exit
- **Offensive:** Full markdown short only during confirmed bear phases (CFGI < 25 for 7+ days)
- This captures the DD benefit without destroying returns

---

## 6. Data Files for Future Reference

| File | Content |
|------|---------|
| `trading/spot/backtest_results/v12f/v12f_ETH_C_summary.json` | Full Mode C results with 258 gate decisions |
| `trading/spot/backtest_results/v12f/v12f_ETH_B_summary.json` | Mode B comparison (29 decisions) |
| `trading/spot/backtest_results/v12f/v12f_ETH_A_summary.json` | V12e baseline |
| `trading/spot/backtest_results/v12f/v12f_ETH_C_trades.csv` | All 91 Mode C trades |
| `trading/spot/backtest_results/v12f/v12f_ETH_B_trades.csv` | All 110 Mode B trades |
| `trading/spot/backtest_engine_v12f.py` | Engine with Mode C code (preserved, not deployed) |
| `projects/ait-product/markdown-exit-engine-spec.md` | Original spec (archived) |

---

## 7. Summary

The markdown exit engine's failure isn't about the concept — it's about the implementation aggressiveness. The idea of profiting from downtrends is sound. The problem is:

1. **Too many attempts** (366 vs 29 gate evaluations)
2. **Too low conviction** (fires on weak distribution signals)  
3. **Wrong fallback** (gate block → DCA instead of hold current phase)
4. **No cooldown** (retries every candle after block)

The V12f sentiment gates proved they work beautifully (+39% improvement). A future markdown engine should be built *on top of* the gate system with proper conviction accumulation and phase-hold semantics, not fighting against the DCA engine.

**Bottom line:** The gates are the right foundation. The markdown engine needs to be rebuilt as a patient, high-conviction overlay — not an aggressive hourly trader.
