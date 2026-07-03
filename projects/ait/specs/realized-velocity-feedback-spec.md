# Realized-Velocity Allocation Feedback Spec
_Version: 1.0 | Date: 2026-07-03 | Status: SPEC — depends on TradeStore (Task 4.3)_
_References: Audit finding F2, trade performance analysis §3.4_

---

## 1. Problem Statement

The scanner ranks coins by **simulated** DCA cycle velocity on historical candles. The live
book now has its own ground truth: actual PnL per capital-hour by coin. From the audit:

| Coin | PnL per 1K capital-hours | Verdict |
|------|--------------------------|---------|
| TON  | 1.9 | Fast cycler |
| TAO  | 1.3 | Star — frequency AND magnitude |
| INJ  | 0.4 | Reliable workhorse |
| PYTH | 0.0 | Capital trap |
| HYPE | ~0.0 | Capital trap |

PYTH and HYPE are unranked in the current scanner (maturity/data gaps), meaning the system
can't currently learn to avoid them via scores. The scanner has real signal (+0.39 correlation)
but a hard ceiling because it simulates a different grid than the bot trades (now fixed via
GridModel, C1) and can't see coins it doesn't rank.

## 2. Design: Blended Score

```
final_score = sim_score × (α + (1-α) × normalized_realized_velocity)
```

Where:
- `sim_score` = DCA Score × Trend Multiplier (existing, from scanner)
- `normalized_realized_velocity` = coin's PnL-per-capital-hour / max across all traded coins
- `α = 0.5` (equal weight to simulation and reality)
- Only applies when a coin has ≥5 live deals (minimum data for signal)

**Effect:**
- Coins with high live velocity (TON, TAO) get boosted allocation
- Capital traps (PYTH, HYPE) get penalized even if scanner ranks them
- New/untested coins start at pure sim score (no penalty, no boost)

## 3. Data Requirements

- **Source**: TradeStore (Task 4.3) or a lightweight stats cache
- **Per-coin metrics needed**:
  - Total capital-hours (invested × duration for each deal)
  - Total realized PnL
  - PnL per capital-hour = total_pnl / total_capital_hours
  - Deal count (for minimum threshold)
- **Refresh**: Daily at rebalance time (after scanner runs)

## 4. Implementation Approach

### 4.1 With TradeStore (preferred)
```sql
SELECT symbol,
       SUM(pnl) as total_pnl,
       SUM(invested * duration_h / 1000) as capital_hours,
       COUNT(*) as deal_count,
       SUM(pnl) / NULLIF(SUM(invested * duration_h / 1000), 0) as velocity
FROM trades
WHERE account_id = 'live-aster-pm'
  AND close_time >= datetime('now', '-90 days')
GROUP BY symbol
HAVING deal_count >= 5
```

### 4.2 Without TradeStore (lightweight cache)
- `realized_velocity_cache.json` updated after each trade close
- Maintains running totals per coin: `{pnl, capital_hours, deals}`
- Read by `CapitalRouter.rebalance_daily()` alongside scanner scores

## 5. Integration with CapitalRouter

```python
def rebalance_daily(self, scanner_data, velocity_data=None, ...):
    for coin in qualifying:
        sim_score = coin.dca_score * coin.trend_multiplier  # existing
        if velocity_data and coin in velocity_data and velocity_data[coin].deals >= 5:
            norm_vel = velocity_data[coin].velocity / max_velocity
            final = sim_score * (0.5 + 0.5 * norm_vel)
        else:
            final = sim_score  # Pure simulation for untested coins
```

## 6. Risks & Mitigations

- **Overfitting to recent history**: Use 90-day window, not all-time
- **Small sample**: ≥5 deal minimum prevents single-trade outliers from dominating
- **Regime change**: Reset velocity cache on global regime flip (bull vs bear performance differs)
- **New coin penalty**: None — untested coins get pure sim score (α=0.5 means 50% of score comes from sim regardless)

## 7. Dependencies

- TradeStore (Task 4.3) or lightweight cache implementation
- CapitalRouter.rebalance_daily() integration
- Dashboard: display velocity metric per coin
