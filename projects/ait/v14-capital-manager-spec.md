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
