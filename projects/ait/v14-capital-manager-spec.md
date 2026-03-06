# V14 Capital Manager Specification

## Overview
The `v14_capital_manager.py` introduces a robust capital routing mechanism for the V14 Engine. It manages the distribution of capital between active trading and reserve holdings, ensuring strict risk management and dynamic allocation based on the DCA Score.

## Core Rules

1. **Pool Split:**
   - 75% Active Pool (Allocated for standard trading layers 1-5).
   - 25% Reserve Pool (Saved for emergency/deep layers 6+).

2. **The Hurdle Rate:**
   - A coin MUST have a DCA Score >= 5.0 (calculated over a 30-day window) to qualify for any capital allocation.

3. **Proportional Weighting:**
   - Capital is distributed proportionally among qualifying coins based on their relative DCA Scores. Higher score = more capital.

4. **Risk Caps:**
   - Maximum allocation per coin: 20% of the *Active Pool*.
   - Maximum number of concurrent coins: 10.

5. **The "Sidelines" Default:**
   - If the risk caps are hit (e.g., highly concentrated high scores) and leftover capital exists in the Active Pool, that excess capital remains unallocated in cash (on the sidelines).

6. **Reserve Release:**
   - Capital from the Reserve Pool is released on a strictly linear, first-come, first-served basis for any active coin that requires capital for Layer 6 or deeper.

7. **Routing (Deal Close):**
   - When a deal closes (profit taken), the freed capital returns entirely to the Active Pool. It is then immediately re-routed based on the *current day's* scanner rankings and DCA scores.

---

## Class Architecture: `CapitalRouter`

The primary class handling these operations will be `CapitalRouter`.

### Properties
- `total_equity`: Total account balance.
- `active_pool`: Available cash in the 75% allocation.
- `reserve_pool`: Available cash in the 25% allocation.
- `active_allocations`: Dictionary tracking current locked capital per coin.

### Key Methods
- `__init__(self, initial_capital: float)`
- `daily_rebalance(self, scanner_rankings: list[dict]) -> dict`
  - Processes the daily scanner data, applies rules, and returns target allocations.
- `request_reserve_capital(self, coin: str, amount: float) -> float`
  - Handles Layer 6+ requests. Returns the granted amount (up to the requested amount, limited by available reserve).
- `register_deal_close(self, coin: str, returned_capital: float)`
  - Returns capital to the Active Pool for re-routing.
- `_calculate_weights(self, qualifying_coins: list[dict]) -> dict`
  - Internal math for proportional DCA score weighting.

---

## Interaction with `V14Engine`

1. **Initialization:** The `V14Engine` instantiates the `CapitalRouter` upon startup, feeding it the total account balance.
2. **Daily Cron/Tick:** Before placing new Layer 1 orders, the `V14Engine` passes the updated daily scanner rankings to `CapitalRouter.daily_rebalance()`.
3. **Execution:** The engine receives a dictionary of maximum permitted allocations per coin from the router and adjusts its active orders accordingly.
4. **Deep Layers (6+):** If the engine attempts to place a Layer 6+ order, it calls `request_reserve_capital()`. If the router returns > 0, the order is placed; otherwise, it is skipped.
5. **Profit Taking:** Upon a sell order filling, the `V14Engine` triggers `register_deal_close()`, allowing the router to update its internal pool state.

---

## Exact Mathematical Flow (Daily Rebalance)

Assume the `active_pool` has $10,000.

**Step 1: Filter and Sort**
- Filter all scanned coins where `dca_score >= 5.0`.
- Sort descending by `dca_score`.
- Keep only the top 10 coins (`max_coins = 10`).

**Step 2: Calculate Sum of Scores**
- `total_score = sum(coin.dca_score for coin in top_10_coins)`

**Step 3: Calculate Raw Proportions**
- For each coin: `raw_allocation = (coin.dca_score / total_score) * active_pool`

**Step 4: Apply Risk Caps**
- Cap limit per coin: `max_cap = 0.20 * active_pool`
- For each coin:
  - If `raw_allocation > max_cap`, set `final_allocation = max_cap`.
  - Else, `final_allocation = raw_allocation`.

**Step 5: Handle the Sidelines**
- `total_allocated = sum(final_allocation for all coins)`
- `sidelines_cash = active_pool - total_allocated`
- The `sidelines_cash` is explicitly left unallocated to act as a buffer/cash drag, ensuring risk rules are not violated just to deploy capital.


---

## Dashboard

**File:** docs/dashboardV14PM.html
**Live URL:** https://halo-effects.github.io/adaptive-intelligence-trading/dashboardV14PM.html

### Data Sources (served via GitHub Pages)
| Path | Content | Updated by |
|------|---------|------------|
| docs/data/v14-pm/status.json | Bot health, equity, per-coin state, router pool info | un_v14_portfolio_paper.py every tick |
| docs/data/v14-pm/trades.csv | Completed deal log | Same |
| docs/data/v14/cycle_scanner.json | Full 44-coin ranked opportunity table | 14_cycle_scanner.py (daily manual or cron) |

### Status JSON — Key Fields
`json
{
  "running": true,
  "leverage": 1.0,
  "equity": 10000.0,
  "cash": 9999.99,
  "coins": { "ZRO/USDT": { "layers": 0, "invested": 0, ... } },
  "router": {
    "active_cash": 7500.0,
    "reserve_cash": 2500.0,
    "total_active_allocated": 0,
    "total_reserve_allocated": 0
  }
}
`

### Dashboard Behaviour Notes
- **Leverage badge** reads S.leverage from status JSON dynamically — does not infer from profile name.
- **Opportunity table** pulls all rankings from cycle_scanner.json (all mature coins), not just active PM coins. Active PM coins are highlighted in the table.
- **HYPE coin card** uses label "HYPE" (not "Hyperliquid") to prevent LONG DCA badge overflow.

---

## Performance Comparison Log

**Script:** 	rading/spot/pm_comparison_log.py
**Output:** docs/data/v14/pm_comparison.json
**Schedule:** AIT_PMComparisonLog — Windows Scheduled Task, daily at 9:10 AM PST (after PM rebalance)

Captures a daily snapshot comparing V14 PM vs V14 Paper (same $10K starting capital):

`json
{
  "date": "2026-03-06",
  "v14_paper":  { "equity": 69220.00, "pnl_pct": 592.20, "deals": 374, "win_rate": 97.6 },
  "v14_pm":     { "equity": 9999.99,  "pnl_pct": 0.0,    "deals": 0,   "win_rate": 0.0 },
  "delta":      { "equity_usd": -59220.01, "pnl_pct": -592.20, "deals": -374 },
  "pm_allocation": {
    "active_pool": 7500.0,
    "reserve": 2500.0,
    "coins": [
      { "symbol": "ZRO/USDT", "rank": 1, "dca_score": 64.56, "invested": 0, "layers": 0 }
    ]
  }
}
`

**Interpretation:** Delta starts large (V14 Paper has weeks of head start). Track **rate of PnL growth** month-over-month. After 30 days the allocation rotation story becomes clear — daily coin rankings and capital shifts are logged so you can correlate PM performance with rotation decisions.
