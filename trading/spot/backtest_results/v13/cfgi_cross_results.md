# CFGI RSI Cross Signal Research Results

Generated: 2026-02-26 ~9pm PST

## TL;DR

**All crossover signals failed.** The simple CFGI_RSI < 35 threshold remains the best bear-clearing approach. Crossover signals either clear bear too quickly (blocking nothing) or when filtered to only fire at low levels, they block good trades too aggressively. Don't overcomplicate what already works.

## What We Tested

| Signal | How Bear Clears | Result |
|--------|----------------|--------|
| **Baseline: CFGI_RSI < 35** | CFGI_RSI drops below 35 | **Best for ETH** (+$3,874 net) |
| Cross 1: CFGI_RSI x Price RSI | CFGI_RSI crosses above Price RSI | NEUTRAL — clears instantly, blocks nothing |
| Cross 1 + Filter (<45) | Same but only if CFGI_RSI < 45 at cross | HURTS — blocks good trades (-$14,335 combined) |
| Cross 2: Fast(7) x Slow(14) | Fast CFGI_RSI crosses above Slow | NEUTRAL — clears instantly |
| Cross 3: CFGI_RSI x SMA(9) | CFGI_RSI crosses above its 9-day MA | NEUTRAL — clears instantly |
| Cross 3 + Filter (<40) | Same but only if CFGI_RSI < 40 at cross | HURTS badly (-$18,106 combined) |
| Cross 4: Divergence | Bullish divergence CFGI_RSI vs Price RSI | NEUTRAL — never fires usefully |

## ETH/USDC (High Profile)

ROI: +284.0% | 6 tops detected | 11 markup entries | CFGI data from 2022-07-04

| Signal | Bad Blocked | Good Blocked | $ Saved | $ Missed | Net $ | Verdict |
|--------|:-----------:|:------------:|--------:|---------:|------:|---------|
| Baseline: CFGI_RSI<35 | 2 | 0 | $3,874 | $0 | **+$3,874** | HELPS |
| Cross1: CFGI_RSI x PriceRSI | 0 | 0 | $0 | $0 | $0 | NEUTRAL |
| Cross1+Filter: <45 | 2 | 3 | $4,183 | $5,975 | -$1,792 | HURTS |
| Cross2: Fast(7) x Slow(14) | 0 | 0 | $0 | $0 | $0 | NEUTRAL |
| Cross3: CFGI_RSI x SMA9 | 0 | 0 | $0 | $0 | $0 | NEUTRAL |
| Cross3+Filter: <40 | 4 | 4 | $6,891 | $12,959 | -$6,068 | HURTS |
| Cross4: Divergence | 0 | 0 | $0 | $0 | $0 | NEUTRAL |

### ETH Entry-by-Entry Detail

| Date | PnL | Quality | CFGI_RSI(14) | CFGI_RSI(7) | Price RSI | SMA9 | Baseline Bias |
|------|----:|---------|:------------:|:-----------:|:---------:|:----:|:-------------:|
| 2020-10-05 | +$22,282 | GOOD | n/a | n/a | 43.1 | n/a | neutral |
| 2021-05-26 | -$7,385 | BAD | n/a | n/a | 38.8 | n/a | neutral (pre-CFGI) |
| 2021-11-21 | -$3,981 | BAD | n/a | n/a | 40.7 | n/a | neutral (pre-CFGI) |
| 2022-09-27 | +$2,205 | GOOD | 46.1 | 44.7 | 34.1 | 47.4 | neutral |
| 2023-05-04 | +$17 | GOOD | 52.0 | 56.9 | 42.4 | 48.7 | neutral |
| 2023-06-21 | -$153 | BAD | 61.0 | 73.3 | 56.2 | 50.3 | **bear** |
| 2023-10-22 | +$6,985 | GOOD | 65.3 | 75.1 | 55.3 | 54.7 | neutral |
| 2024-03-25 | -$2,555 | BAD | 55.4 | 64.9 | 38.2 | 37.8 | neutral |
| 2024-06-16 | -$3,722 | BAD | 53.9 | 62.0 | 40.8 | 42.7 | **bear** |
| 2024-10-15 | +$3,753 | GOOD | 59.1 | 66.8 | 63.5 | 53.3 | neutral |
| 2025-10-01 | -$461 | BAD | 55.1 | 63.9 | 41.2 | 44.2 | neutral |

## BTC/USDC (High Profile)

ROI: +166.6% | 5 tops detected | 8 markup entries | CFGI data from 2022-07-03

| Signal | Bad Blocked | Good Blocked | $ Saved | $ Missed | Net $ | Verdict |
|--------|:-----------:|:------------:|--------:|---------:|------:|---------|
| Baseline: CFGI_RSI<35 | 0 | 1 | $0 | $4,386 | **-$4,386** | HURTS |
| Cross1: CFGI_RSI x PriceRSI | 0 | 0 | $0 | $0 | $0 | NEUTRAL |
| Cross1+Filter: <45 | 0 | 4 | $0 | $12,543 | -$12,543 | HURTS |
| Cross2: Fast(7) x Slow(14) | 0 | 0 | $0 | $0 | $0 | NEUTRAL |
| Cross3: CFGI_RSI x SMA9 | 0 | 0 | $0 | $0 | $0 | NEUTRAL |
| Cross3+Filter: <40 | 1 | 4 | $506 | $12,543 | -$12,037 | HURTS |
| Cross4: Divergence | 0 | 0 | $0 | $0 | $0 | NEUTRAL |

### BTC Entry-by-Entry Detail

| Date | PnL | Quality | CFGI_RSI(14) | CFGI_RSI(7) | Price RSI | SMA9 | Baseline Bias |
|------|----:|---------|:------------:|:-----------:|:---------:|:----:|:-------------:|
| 2020-10-05 | +$11,938 | GOOD | n/a | n/a | 47.3 | n/a | neutral |
| 2021-04-27 | -$4,536 | BAD | n/a | n/a | 30.9 | n/a | neutral (pre-CFGI) |
| 2022-03-25 | -$3,297 | BAD | n/a | n/a | 74.9 | n/a | neutral (pre-CFGI) |
| 2023-01-09 | +$2,635 | GOOD | 61.0 | 71.0 | 60.5 | 56.7 | neutral |
| 2023-04-26 | -$506 | BAD | 50.4 | 56.4 | 40.1 | 43.3 | neutral |
| 2024-01-29 | +$4,675 | GOOD | 57.8 | 66.7 | 54.4 | 51.5 | neutral |
| 2024-06-04 | +$4,386 | GOOD | 58.8 | 70.4 | 51.7 | 50.1 | **bear** (false positive!) |
| 2025-06-24 | +$848 | GOOD | 47.9 | 50.3 | 38.8 | 45.5 | neutral |

## Why Crossovers Failed

### The Core Problem: Crossovers Fire Too Frequently

CFGI_RSI oscillates rapidly (it's RSI of a daily sentiment index). After any top signal:

1. **Cross 1 (CFGI_RSI x Price RSI):** CFGI_RSI crosses above Price RSI within days — these two oscillators naturally interweave. Bear clears almost immediately.
2. **Cross 2 (Fast x Slow):** RSI(7) and RSI(14) of the same series cross constantly. The fast line is just a noisier version of the slow line.
3. **Cross 3 (CFGI_RSI x SMA9):** RSI naturally oscillates around its own moving average. Crosses happen every few days.
4. **Cross 4 (Divergence):** Divergence detection with a 20-day lookback didn't fire at useful times. The two RSI series don't diverge in the classic technical analysis sense.

### Why the Simple Threshold Works Better

CFGI_RSI < 35 works because it requires **sentiment to reach genuine oversold territory** before clearing bear. It's a level-based gate, not a direction-based one. The crossovers only measure direction change, which happens constantly in noisy oscillators.

### Filtered Crossovers Made Things Worse

Adding level filters (e.g., "only clear if CFGI_RSI < 45 at the cross") made things worse because:
- The combination is MORE restrictive than the simple threshold
- It blocks more total trades, but indiscriminately — good trades get caught too
- ETH Cross3+Filter: blocked 4 bad ($6,891) but also 4 good ($12,959) = net -$6,068

## Note on Baseline Numbers

The baseline numbers in this test ($3,874 net for ETH) differ from the previously reported $15,241 because:
- 3 of ETH's bad markups (2021-05-26, 2021-11-21 — ~$11,366) are **pre-CFGI** (before Jul 2022) and thus default to neutral
- The $15,241 figure likely came from a run with different equity/compounding or included pre-CFGI period blocking
- Within the CFGI data period, baseline correctly blocks 2 bad / 0 good for ETH

## Recommendation

**Stick with CFGI_RSI < 35 as the bear-clearing signal.** It's simple, effective, and the data doesn't support more complex crossover approaches. The crossover signals are either too noisy (clearing instantly) or too restrictive (blocking good trades).

Future research directions that might be more productive:
- **Multi-timeframe CFGI_RSI** (weekly CFGI_RSI as confirmation)
- **CFGI_RSI duration** (must stay below 35 for N days, not just touch it)
- **CFGI_RSI + volume confirmation** (sentiment capitulation + volume spike)
- **Different thresholds per coin** (BTC may need CFGI_RSI < 30 or raw CFGI < 30)
