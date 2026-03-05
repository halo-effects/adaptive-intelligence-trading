import json
import logging
from typing import List, Dict, Any

logger = logging.getLogger("V14CapitalManager")
logger.setLevel(logging.INFO)
# Optional: Add a console handler if one isn't configured globally
if not logger.handlers:
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    ch.setFormatter(formatter)
    logger.addHandler(ch)


class CapitalRouter:
    """
    Capital Router for V14 Engine.
    Manages the distribution of capital between active trading (75%) 
    and reserve holdings (25%), dynamic allocation based on DCA Score,
    and strict risk caps.
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

        logger.info(f"Initialized CapitalRouter with ${self.total_equity:.2f} total equity.")
        logger.info(f"Active Pool (75%): ${self.active_pool_total:.2f}")
        logger.info(f"Reserve Pool (25%): ${self.reserve_pool_total:.2f}")

    def load_scanner_json(self, filepath: str) -> List[Dict[str, Any]]:
        """
        Utility to read cycle_scanner.json and return the rankings.
        """
        try:
            with open(filepath, 'r') as f:
                data = json.load(f)
            
            # Use '30d' window if available, otherwise 'bear', or fallback to root list
            if "30d" in data:
                return data["30d"]
            elif "bear" in data:
                return data["bear"]
            elif isinstance(data, list):
                return data
            
            # Fallback scan of dict
            for key, val in data.items():
                if isinstance(val, list):
                    return val
            
            return []
        except Exception as e:
            logger.error(f"Failed to load scanner JSON from {filepath}: {e}")
            return []

    def rebalance_daily(self, scanner_rankings: List[Dict[str, Any]]) -> Dict[str, float]:
        """
        Processes the daily scanner data, applies rules, and returns target allocations.
        
        Rules:
        - Hurdle rate: DCA Score >= 5.0
        - Max 10 coins
        - Proportional weighting by DCA Score
        - Risk Cap: Max 20% of Active Pool per coin
        - Sidelines: Leftover active pool cash remains unallocated
        """
        logger.info("Starting daily rebalance...")
        
        # 1. Filter: hurdle rate >= 5.0
        qualifying_coins = []
        for coin_data in scanner_rankings:
            symbol = coin_data.get("symbol") or coin_data.get("coin")
            score = coin_data.get("dca_score", 0.0)
            
            try:
                score_float = float(score)
            except (ValueError, TypeError):
                continue
                
            if score_float >= 5.0:
                qualifying_coins.append({"symbol": symbol, "dca_score": score_float})
        
        # 2. Sort descending by score
        qualifying_coins.sort(key=lambda x: x["dca_score"], reverse=True)
        
        # 3. Max 10 coins
        top_coins = qualifying_coins[:10]
        
        if not top_coins:
            logger.warning("No coins met the >= 5.0 hurdle rate. All capital goes to sidelines.")
            return {}

        # 4. Calculate total score
        total_score = sum(c["dca_score"] for c in top_coins)
        
        # 5. Proportional weighting & 20% max cap
        max_cap = 0.20 * self.active_pool_total
        target_allocations = {}
        
        for c in top_coins:
            raw_allocation = (c["dca_score"] / total_score) * self.active_pool_total
            final_allocation = min(raw_allocation, max_cap)
            target_allocations[c["symbol"]] = final_allocation
            logger.debug(f"{c['symbol']}: Score {c['dca_score']} -> Final Allocation ${final_allocation:.2f}")

        # 6. Sidelines cash routing
        total_allocated = sum(target_allocations.values())
        sidelines_cash = self.active_pool_total - total_allocated
        
        logger.info(f"Rebalance complete. {len(top_coins)} coins allocated.")
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
