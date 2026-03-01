#!/usr/bin/env python3
"""Quick test of V11 engine to verify basic functionality."""
import sys, logging
from pathlib import Path

if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import pandas as pd
import numpy as np
from trading.spot.backtest_engine_v11 import SpotBacktestEngineV11
from trading.spot.macro_indicators import load_historical_fear_greed

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_v11_basic():
    """Test basic V11 functionality with dummy data."""
    # Create dummy OHLCV data
    np.random.seed(42)
    n_candles = 1000
    base_price = 3000
    
    timestamps = pd.date_range('2024-01-01', periods=n_candles, freq='1h')
    prices = []
    price = base_price
    
    for i in range(n_candles):
        # Random walk with slight upward bias
        change = np.random.normal(0, 0.02) + 0.0001
        price = max(price * (1 + change), base_price * 0.5)  # Floor at 50% of base
        prices.append(price)
    
    df = pd.DataFrame({
        'timestamp': [int(ts.timestamp() * 1000) for ts in timestamps],
        'open': prices,
        'high': [p * (1 + abs(np.random.normal(0, 0.01))) for p in prices],
        'low': [p * (1 - abs(np.random.normal(0, 0.01))) for p in prices],
        'close': prices,
        'volume': [np.random.uniform(1000, 10000) for _ in range(n_candles)]
    })
    
    # Load F&G data
    fg = load_historical_fear_greed()
    
    # Test V11 engine
    engine = SpotBacktestEngineV11(
        capital=10000,
        exchange="binance",
        symbol="ETH/USDT", 
        timeframe="1h",
        fear_greed_history=fg,
        # V11 params
        short_sl_pct=5.0,
        mcap_ath_pct=0.20,
        use_mcap_gating=True,
        short_tight_sl_pct=3.0,
        enable_fast_invalidation=True,
        structural_exit=True,
        dist_exit_threshold_1h=30.0,
    )
    
    print(f"Testing V11 engine with {len(df)} candles...")
    result = engine.run(df)
    
    print(f"\nV11 Test Results:")
    print(f"  Total Return: {result.total_return_pct:+.2f}%")
    print(f"  Max Drawdown: {result.max_drawdown_pct:.1f}%")
    print(f"  Total Deals: {result.total_deals_completed}")
    print(f"  Win Rate: {result.win_rate:.1f}%")
    
    extra = getattr(result, 'extra', {})
    print(f"  Short PnL: ${extra.get('v11_short_pnl', 0):+.2f}")
    print(f"  Short Deals: {extra.get('v11_short_deals_completed', 0)}")
    print(f"  Shorts Gated: {extra.get('v11_shorts_gated_by_mcap', 0)}")
    print(f"  Fast Invalidations: {extra.get('v11_fast_invalidations', 0)}")
    print(f"  Mcap Data Available: {extra.get('v11_mcap_data_available', False)}")
    
    return result

if __name__ == "__main__":
    test_v11_basic()
    print("\nV11 test completed!")