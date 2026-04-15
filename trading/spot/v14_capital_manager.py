import json
import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger("V14CapitalManager")
logger.setLevel(logging.INFO)
# Optional: Add a console handler if one isn't configured globally
if not logger.handlers:
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    ch.setFormatter(formatter)
    logger.addHandler(ch)


# ---------------------------------------------------------------------------
# Equity-tiered coin cap
# ---------------------------------------------------------------------------
# Format: (min_equity_inclusive, max_coins)
# Evaluated top-down; first match wins.
EQUITY_TIER_CAPS = [
    (100_000, 10),  # $100K+ -> up to 10 coins
    ( 50_000,  5),  # $50K-$100K -> up to 5 coins
    ( 30_000,  4),  # $30K-$50K -> up to 4 coins
    ( 20_000,  3),  # $20K-$30K -> up to 3 coins
    ( 10_000,  2),  # $10K-$20K -> up to 2 coins
    (    100,  1),  # $100-$10K -> 1 coin
]


class CapitalRouter:
    """
    Capital Router for V14 Engine.
    Manages the distribution of capital between active trading (75%) 
    and reserve holdings (25%), dynamic allocation based on DCA Score,
    and strict risk caps.

    Tier-aware: max coins allowed scales with current portfolio equity.
    On a tier drop the cap is enforced on new T1 entries only — existing
    positions are allowed to exit gracefully (handled by the runner).
    """
    def __init__(self, initial_capital: float):
        self.total_equity = initial_capital
        
        # 75/25 Pool Split
        self.active_pool_total = self.total_equity * 0.75
        self.reserve_pool_total = self.total_equity * 0.25
        
        # Track available cash
        self.active_pool_cash = self.active_pool_total
        self.reserve_pool_cash = self.reserve_pool_total
        
        # Track locked allocations
        self.active_allocations: Dict[str, float] = {}
        self.reserve_allocations: Dict[str, float] = {}

        # Tier state (updated on each rebalance)
        self.tier_coin_cap: int = self.get_tier_coin_cap(self.total_equity)

        logger.info(f"Initialized CapitalRouter with ${self.total_equity:.2f} total equity.")
        logger.info(f"Active Pool (75%): ${self.active_pool_total:.2f}")
        logger.info(f"Reserve Pool (25%): ${self.reserve_pool_total:.2f}")
        logger.info(f"Tier coin cap: {self.tier_coin_cap} coins")

    @staticmethod
    def get_tier_coin_cap(equity: float) -> int:
        """Return the max allowed simultaneous coin positions for the given equity level."""
        for threshold, cap in EQUITY_TIER_CAPS:
            if equity >= threshold:
                return cap
        return 0  # Below $100 — no new positions

    def load_scanner_json(self, filepath: str) -> List[Dict[str, Any]]:
        """
        Utility to read cycle_scanner.json and return the rankings.
        Also enriches each ranking entry with trend_multiplier if available.
        """
        try:
            with open(filepath, 'r') as f:
                data = json.load(f)
            
            rankings = []
            # Navigate the windows structure from cycle_scanner.json
            if "windows" in data:
                if "30d" in data["windows"]:
                    rankings = data["windows"]["30d"]["rankings"]
                elif "bear" in data["windows"]:
                    rankings = data["windows"]["bear"]["rankings"]
            elif "30d" in data:
                rankings = data["30d"]
            elif "bear" in data:
                rankings = data["bear"]
            elif isinstance(data, list):
                rankings = data
            else:
                for key, val in data.items():
                    if isinstance(val, list):
                        rankings = val
                        break

            # Enrich rankings with trend multipliers from trend_scores
            trend_scores = data.get("trend_scores", {})
            if trend_scores:
                for entry in rankings:
                    coin = entry.get("coin", entry.get("symbol", "").split("/")[0])
                    if coin in trend_scores:
                        td = trend_scores[coin]
                        entry["trend_multiplier"] = td.get("trend_multiplier", 1.0)
                        entry["trend_direction"] = td.get("direction", "stable")
                    # If no trend data, default multiplier is 1.0 (neutral)
                logger.info(f"Trend scores loaded for {len(trend_scores)} coins")

            return rankings
        except Exception as e:
            logger.error(f"Failed to load scanner JSON from {filepath}: {e}")
            return []

    def rebalance_daily(
        self,
        scanner_rankings: List[Dict[str, Any]],
        current_equity: Optional[float] = None,
    ) -> Dict[str, float]:
        """
        Processes the daily scanner data, applies rules, and returns target allocations.

        Rules:
        - Hurdle rate: DCA Score >= 5.0
        - Max coins: determined by equity tier (see EQUITY_TIER_CAPS)
        - Proportional weighting by DCA Score
        - Risk Cap: Max 20% of Active Pool per coin
        - Sidelines: Leftover active pool cash remains unallocated

        If current_equity is provided it overrides self.total_equity for tier
        calculation and updates pool totals accordingly.
        """
        logger.info("Starting daily rebalance...")

        # Update equity snapshot and derive tier cap
        if current_equity is not None and current_equity > 0:
            prev_equity = self.total_equity
            self.total_equity = current_equity
            self.active_pool_total = self.total_equity * 0.75
            self.reserve_pool_total = self.total_equity * 0.25
            if abs(current_equity - prev_equity) > 1.0:
                logger.info(f"Equity updated: ${prev_equity:.2f} → ${current_equity:.2f}")

        prev_cap = self.tier_coin_cap
        self.tier_coin_cap = self.get_tier_coin_cap(self.total_equity)
        if self.tier_coin_cap != prev_cap:
            direction = "▼ DOWN" if self.tier_coin_cap < prev_cap else "▲ UP"
            logger.warning(
                f"Tier coin cap changed {direction}: {prev_cap} → {self.tier_coin_cap} "
                f"(equity=${self.total_equity:.2f})"
            )

        logger.info(f"Equity tier: ${self.total_equity:.2f} → max {self.tier_coin_cap} coins")

        # 1. Filter: hurdle rate >= 5.0, apply trend multiplier
        qualifying_coins = []
        for coin_data in scanner_rankings:
            symbol = coin_data.get("symbol") or coin_data.get("coin")
            base_score = coin_data.get("dca_score", 0.0)
            trend_mult = coin_data.get("trend_multiplier", 1.0)
            trend_dir = coin_data.get("trend_direction", "stable")
            
            try:
                base_score_float = float(base_score)
                trend_mult_float = float(trend_mult)
            except (ValueError, TypeError):
                continue
            
            # Trend-adjusted score: Base DCA Score × Trend Multiplier
            # Collapsed scores (mult near 0) effectively gate entry
            adjusted_score = base_score_float * trend_mult_float
                
            if base_score_float >= 5.0:
                qualifying_coins.append({
                    "symbol": symbol,
                    "dca_score": base_score_float,
                    "trend_multiplier": trend_mult_float,
                    "trend_direction": trend_dir,
                    "adjusted_score": adjusted_score,
                })
        
        # 2. Sort descending by trend-adjusted score (not raw score)
        qualifying_coins.sort(key=lambda x: x["adjusted_score"], reverse=True)
        
        # 3. Apply tier coin cap (never exceeds cap regardless of how many qualify)
        max_coins = self.tier_coin_cap
        top_coins = qualifying_coins[:max_coins]
        
        if not top_coins:
            if max_coins == 0:
                logger.warning(f"Equity ${self.total_equity:.2f} is below $100 minimum. No positions allowed.")
            else:
                logger.warning("No coins met the >= 5.0 hurdle rate. All capital goes to sidelines.")
            return {}

        # 4. Calculate total adjusted score
        total_score = sum(c["adjusted_score"] for c in top_coins)
        
        # 5. Proportional weighting by adjusted score & 20% max cap per coin
        max_cap_per_coin = 0.20 * self.active_pool_total
        target_allocations = {}
        
        for c in top_coins:
            raw_allocation = (c["adjusted_score"] / total_score) * self.active_pool_total
            final_allocation = min(raw_allocation, max_cap_per_coin)
            target_allocations[c["symbol"]] = final_allocation
            logger.debug(
                f"{c['symbol']}: Base={c['dca_score']:.1f} × Trend={c['trend_multiplier']:.2f} "
                f"= Adj={c['adjusted_score']:.1f} → ${final_allocation:.2f}"
            )

        # 6. Sidelines cash routing
        total_allocated = sum(target_allocations.values())
        sidelines_cash = self.active_pool_total - total_allocated
        
        logger.info(f"Rebalance complete. {len(top_coins)}/{max_coins} coin slots filled.")
        for c in top_coins:
            logger.info(
                f"  {c['symbol']}: Base={c['dca_score']:.1f} × Trend={c['trend_multiplier']:.2f} "
                f"({c['trend_direction']}) = {c['adjusted_score']:.1f} → ${target_allocations[c['symbol']]:.2f}"
            )
        logger.info(f"Total Target Allocation: ${total_allocated:.2f} | Sidelines Cash (Buffer): ${sidelines_cash:.2f}")
        
        return target_allocations

    def request_capital(self, coin: str, amount: float, pool: str = "active") -> float:
        """
        Request capital from either 'active' or 'reserve' pool.
        Returns the granted amount (up to the requested amount, limited by available cash).
        """
        if amount <= 0:
            return 0.0

        if pool.lower() == "active":
            if amount <= self.active_pool_cash:
                self.active_pool_cash -= amount
                self.active_allocations[coin] = self.active_allocations.get(coin, 0.0) + amount
                logger.info(f"Granted ${amount:.2f} to {coin} (Active Pool). Active Cash: ${self.active_pool_cash:.2f}")
                return amount
            else:
                granted = self.active_pool_cash
                self.active_allocations[coin] = self.active_allocations.get(coin, 0.0) + granted
                self.active_pool_cash = 0.0
                if granted > 0:
                    logger.warning(f"Active Pool depleted! Granted partial ${granted:.2f} to {coin}.")
                else:
                    logger.warning(f"Active Pool empty! Request for ${amount:.2f} by {coin} denied.")
                return granted
                
        elif pool.lower() == "reserve":
            # Reserve Pool is strictly for Layer 6+ / emergency
            if amount <= self.reserve_pool_cash:
                self.reserve_pool_cash -= amount
                self.reserve_allocations[coin] = self.reserve_allocations.get(coin, 0.0) + amount
                logger.info(f"Granted ${amount:.2f} to {coin} (Reserve Pool). Reserve Cash: ${self.reserve_pool_cash:.2f}")
                return amount
            else:
                granted = self.reserve_pool_cash
                self.reserve_allocations[coin] = self.reserve_allocations.get(coin, 0.0) + granted
                self.reserve_pool_cash = 0.0
                if granted > 0:
                    logger.warning(f"Reserve Pool depleted! Granted partial ${granted:.2f} to {coin}.")
                else:
                    logger.warning(f"Reserve Pool empty! Request for ${amount:.2f} by {coin} denied.")
                return granted
        else:
            logger.error(f"Unknown pool type requested: {pool}")
            return 0.0

    def return_capital(self, coin: str, amount: float):
        """
        When a deal closes, the freed capital returns entirely to the Active Pool.
        It is then available for immediate re-routing based on current allocations.
        """
        if amount <= 0:
            return

        self.active_pool_cash += amount
        
        # Reset tracking for this coin since the deal closed
        if coin in self.active_allocations:
            self.active_allocations[coin] = 0.0
        if coin in self.reserve_allocations:
            self.reserve_allocations[coin] = 0.0
            
        logger.info(f"Deal close for {coin}: Returned ${amount:.2f} to Active Pool. Active Cash: ${self.active_pool_cash:.2f}")
