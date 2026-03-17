# Liquidity & Seed Guide for Basis Prediction Markets

_How starting liquidity affects probability accuracy, price impact, and whale protection._
_Derived from simulation analysis: 2026-03-17_

---

## Seed Formula

Every Basis prediction market starts with a **virtual reserve** (seed) that sets the initial equal probability across all outcomes. This seed is not real capital — it's a pricing parameter in the bonding curve.

```
Public markets:  seed = min($50,000, max($5,000, $500 × numOutcomes))
Private markets: seed = min($10,000, max($1,000, $100 × numOutcomes))
```

### Quick Reference Table

| Outcomes | Public Seed | $/Outcome | Private Seed | $/Outcome |
|----------|-------------|-----------|--------------|-----------|
| 2        | $5,000      | $2,500    | $1,000       | $500      |
| 5        | $5,000      | $1,000    | $1,000       | $200      |
| 10       | $5,000      | $500      | $1,000       | $100      |
| 20       | $10,000     | $500      | $2,000       | $100      |
| 50       | $25,000     | $500      | $5,000       | $100      |
| 100      | $50,000     | $500      | $10,000      | $100      |
| 150+     | $50,000 cap | $333      | $10,000 cap  | $67       |

---

## Market Maturity Model

The **seed-to-volume ratio** determines how much the initial equal-probability assumption distorts the displayed odds.

| Seed/Volume Ratio | Market State | Probability Accuracy |
|---|---|---|
| > 5x | VERY EARLY | All outcomes near 1/N. Only ordering is reliable. |
| 1x - 5x | EARLY | Frontrunner at ~60% of true probability. Mid-tier compressed. |
| 0.1x - 1x | DEVELOPING | Within ~5% of true odds. Top outcomes reliable. |
| < 0.1x | MATURE | Within ~1% of true odds. Seed is noise. |

**Convergence rule:** Once total YES volume exceeds 10x the seed, probabilities are accurate.

### Example: 20-outcome public market ($10K seed)

| Total Volume | Seed/Volume | Frontrunner (true 25%) shows as |
|---|---|---|
| $2,000 | 5.0x | ~8% |
| $10,000 | 1.0x | ~16% |
| $50,000 | 0.2x | ~23% |
| $100,000 | 0.1x | ~24.5% |

---

## Price Impact Per Bet

How much does a single bet move the probability?

### Public 2-outcome market ($5K seed, init prob 50%)

| Bet Size | New Probability | Absolute Move |
|---|---|---|
| $100 | 51.0% | +1.0% |
| $500 | 54.5% | +4.5% |
| $1,000 | 58.2% | +8.2% |
| $10,000 | 74.8% | +24.8% |

### Public 20-outcome market ($10K seed, init prob 5%)

| Bet Size | New Probability | Absolute Move |
|---|---|---|
| $100 | 5.9% | +0.9% |
| $500 | 9.4% | +4.4% |
| $1,000 | 13.5% | +8.5% |
| $10,000 | 52.1% | +47.1% |

### Private 10-outcome market ($1K seed, init prob 10%)

| Bet Size | New Probability | Absolute Move |
|---|---|---|
| $100 | 18.1% | +8.1% |
| $500 | 39.7% | +29.7% |
| $1,000 | 54.7% | +44.7% |

---

## Agent Strategy by Market Maturity

### VERY EARLY (< $1K volume on a $5K seed)
- ✅ Bet small to signal conviction — you're setting the narrative
- ✅ Great for airdrop points (early activity)
- ⚠️ Do NOT read displayed probabilities as meaningful
- ⚠️ Large bets create misleading probability spikes
- 💡 Consider splitting into 3-5 smaller bets over time

### EARLY ($1K-$25K volume)
- ✅ Frontrunner ranking is reliable
- ✅ Getting shares below true-value prices
- ⚠️ Mid-tier probabilities still compressed toward mean
- 💡 Good entry point for medium-conviction bets

### DEVELOPING ($25K-$250K volume)
- ✅ Probabilities are trustworthy for top 5 outcomes
- ✅ Compare to Polymarket for edge detection
- ✅ Full position sizing appropriate
- 💡 Best risk/reward zone for informed bettors

### MATURE ($250K+ volume)
- ✅ Full probability accuracy
- ✅ Minimal price impact from normal bets
- ⚠️ Less upside — markets are efficiently priced
- 💡 Look for mispricing vs external sources or breaking news

---

## Whale Protection Mechanics

The bonding curve has **built-in whale resistance**:

1. **Increasing cost per share**: Each dollar buys fewer shares as probability rises
2. **Slippage penalty above 95%**: Share output drops exponentially
   - 96% → shares reduced to 64% of raw output
   - 98% → shares reduced to 16%
   - 99% → shares reduced to 4%
3. **Effective price explosion**: A whale paying $50K into a $1K-seed market pays $25/share (vs $0.55 for early bettors)
4. **Cannot reach 100%**: Cost approaches infinity as probability approaches 1.0

### Whale Dilution Speed

A $10K whale on a 44-outcome market ($4.4K seed) grabs 69.8% probability, but:

| Organic Volume After Whale | Whale's Outcome Drops To |
|---|---|
| $10K (equal to whale) | 42% |
| $50K (5x whale) | 17% |
| $100K (10x whale) | 11% |

**Equal volume halves the whale's advantage. 10x volume makes them a footnote.**

---

## Asymmetric Risk of Seed Size

| Scenario | What Happens | Severity |
|---|---|---|
| Seed too LOW + high volume | Self-corrects in minutes. No problem. | ✅ Fine |
| Seed too LOW + low volume | Very responsive — first bet dominates. Can look volatile. | ⚠️ Minor |
| Seed too HIGH + high volume | Volume overwhelms seed eventually. Slow start. | ⚠️ Minor |
| Seed too HIGH + low volume | Market looks flat and dead. Probabilities barely move. | ❌ Bad UX |

**Always err toward lower seeds.** The bonding curve self-corrects upward with volume; it cannot self-correct downward from an oversized seed.

---

## Key Formulas

### Probability
```
probability = outcomeVirtualReserve / totalVirtualReserve
```

### At scale (volume >> seed)
```
probability ≈ outcomeVolume / totalVolume
```

### Price impact of a bet
```
net = betAmount × (1 - TAX)     # TAX = 1.5%
newVirtual = outcomeReserve + net
newTotal = totalReserve + net
newProbability = newVirtual / newTotal
```

### Slippage penalty (above 95%)
```
if (probability_bps > 9500):
    remaining = 10000 - probability_bps
    shares = shares × remaining² / 250000
```

---

_Source: Simulation analysis across 4 Polymarket markets (149 outcomes, $1.57B volume)._
_Full report: `prediction-market-liquidity-report.md`_
_Simulation scripts: `scripts/low_volume_sim.py`, `scripts/whale_protection.py`_
