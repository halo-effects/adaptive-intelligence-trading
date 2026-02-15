"""Martingale strategy configuration."""
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class MartingaleConfig:
    # Order sizing
    base_order_size: float = 100.0          # USD for initial buy
    safety_order_size: float = 200.0        # USD for first safety order
    safety_order_multiplier: float = 1.5    # Each subsequent SO is multiplied by this

    # Price deviation
    price_deviation_pct: float = 1.0        # % drop from entry to trigger first SO
    deviation_multiplier: float = 1.2       # Scale gap between successive SOs

    # Limits
    max_safety_orders: int = 6
    max_active_deals: int = 3

    # Take profit (intentionally not anchored — optimizer finds best value)
    take_profit_pct: float = 1.5            # % above avg entry to close
    trailing_tp_pct: Optional[float] = None # Optional trailing TP (e.g. 0.5 means 0.5% trail)

    # Costs
    fee_pct: float = 0.1                    # Trading fee per side
    slippage_pct: float = 0.05              # Estimated slippage per fill

    # Backtesting
    timeframes: List[str] = field(default_factory=lambda: ['5m', '15m', '1h', '4h'])
    initial_capital: float = 10000.0

    def so_deviation(self, so_index: int) -> float:
        """Cumulative price deviation % to trigger the nth safety order (1-indexed)."""
        total = 0.0
        for i in range(1, so_index + 1):
            if i == 1:
                total += self.price_deviation_pct
            else:
                total += self.price_deviation_pct * (self.deviation_multiplier ** (i - 1))
        return total

    def so_size(self, so_index: int) -> float:
        """USD size for the nth safety order (1-indexed)."""
        return self.safety_order_size * (self.safety_order_multiplier ** (so_index - 1))

    def max_deal_capital(self) -> float:
        """Max capital a single deal can consume if all SOs fill."""
        total = self.base_order_size
        for i in range(1, self.max_safety_orders + 1):
            total += self.so_size(i)
        return total
