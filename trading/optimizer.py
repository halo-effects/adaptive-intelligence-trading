"""Grid search parameter optimizer for Martingale strategy."""
import itertools
import pandas as pd
import numpy as np
from .config import MartingaleConfig
from .martingale_engine import MartingaleBot
from .regime_detector import classify_regime


# Parameter grid
PARAM_GRID = {
    "take_profit_pct": np.arange(0.5, 5.5, 0.5).tolist(),
    "max_safety_orders": [4, 5, 6, 7, 8],
    "price_deviation_pct": np.arange(0.5, 3.0, 0.5).tolist(),
    "deviation_multiplier": [1.0, 1.1, 1.2, 1.3, 1.4, 1.5],
    "safety_order_multiplier": [1.2, 1.4, 1.6, 1.8, 2.0],
}

TIMEFRAMES = ["5m", "15m", "1h", "4h"]


def optimize(data_by_tf: dict, symbol: str, base_config: MartingaleConfig = None,
             param_grid: dict = None, timeframes: list = None, top_n: int = 20,
             quick: bool = False) -> pd.DataFrame:
    """
    Run grid search optimization.

    Args:
        data_by_tf: {timeframe: DataFrame} with OHLCV data
        symbol: trading pair
        base_config: starting config (non-optimized params kept)
        param_grid: override default grid
        timeframes: which timeframes to test
        top_n: how many results to return
        quick: if True, use reduced grid for speed
    """
    if base_config is None:
        base_config = MartingaleConfig()
    if param_grid is None:
        param_grid = PARAM_GRID.copy()
    if timeframes is None:
        timeframes = [tf for tf in TIMEFRAMES if tf in data_by_tf]

    if quick:
        param_grid = {
            "take_profit_pct": [1.0, 2.0, 3.0, 4.0],
            "max_safety_orders": [4, 6, 8],
            "price_deviation_pct": [1.0, 1.5, 2.0],
            "deviation_multiplier": [1.0, 1.3],
            "safety_order_multiplier": [1.5, 2.0],
        }

    keys = list(param_grid.keys())
    values = list(param_grid.values())
    combos = list(itertools.product(*values))
    total = len(combos) * len(timeframes)
    print(f"Optimizer: {len(combos)} param combos × {len(timeframes)} timeframes = {total} runs")

    # Precompute regimes once per timeframe (Hurst is expensive)
    precomputed_regimes = {}
    for tf in timeframes:
        if tf in data_by_tf:
            print(f"  Precomputing regime for {tf}...")
            precomputed_regimes[tf] = classify_regime(data_by_tf[tf], tf)

    results = []
    count = 0
    for tf in timeframes:
        if tf not in data_by_tf:
            continue
        df = data_by_tf[tf]
        regimes = precomputed_regimes.get(tf)
        for combo in combos:
            params = dict(zip(keys, combo))
            cfg = MartingaleConfig(
                base_order_size=base_config.base_order_size,
                safety_order_size=base_config.safety_order_size,
                safety_order_multiplier=params["safety_order_multiplier"],
                price_deviation_pct=params["price_deviation_pct"],
                deviation_multiplier=params["deviation_multiplier"],
                max_safety_orders=int(params["max_safety_orders"]),
                take_profit_pct=params["take_profit_pct"],
                trailing_tp_pct=base_config.trailing_tp_pct,
                max_active_deals=base_config.max_active_deals,
                fee_pct=base_config.fee_pct,
                slippage_pct=base_config.slippage_pct,
                initial_capital=base_config.initial_capital,
            )
            bot = MartingaleBot(cfg)
            res = bot.run(df, symbol, tf, precomputed_regimes=regimes)
            s = res.summary_dict()
            s.update(params)
            s["timeframe"] = tf
            results.append(s)
            count += 1
            if count % 100 == 0:
                print(f"  ... {count}/{total}")

    results_df = pd.DataFrame(results)
    # Rank by profit factor (descending), then max drawdown (ascending = less negative is better)
    # Replace inf profit factor with 999 for sorting
    results_df["profit_factor"] = results_df["profit_factor"].replace(float("inf"), 999)
    
    # Risk-adjusted score: profit% / abs(drawdown%) — higher is better
    results_df["risk_adj_score"] = results_df["total_profit_pct"] / results_df["max_drawdown_pct"].abs().clip(lower=0.01)
    
    # Sort by total profit (primary), then risk-adjusted (secondary)
    results_df = results_df.sort_values(
        ["total_profit_pct", "risk_adj_score"],
        ascending=[False, False]
    ).reset_index(drop=True)

    return results_df.head(top_n)
