#!/usr/bin/env python3
"""Quick test of the optimized TA scorer on a single chunk."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import pandas as pd
import logging
from trading.spot.backtest_engine_v11 import SpotBacktestEngineV11
from trading.spot.macro_indicators import load_historical_fear_greed

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

def test_single_chunk():
    """Test the TA scorer on chunk 8 (the one with the Dec 2024 peak)."""
    
    # Load the chunk data
    data_file = "trading/spot/data/dwell_cache/ETH_USDT_1h_2024-09-10_2025-01-16.csv"
    print(f"Loading test data: {data_file}")
    
    df = pd.read_csv(data_file)
    print(f"Loaded {len(df)} candles")
    
    # Load F&G data
    fg = load_historical_fear_greed()
    
    # Configure the V11 engine with TA scorer
    params = {
        "symbol": "ETH/USDT",
        "timeframe": "1h",
        "initial_capital": 50000.0,
        "dist_exit_threshold_1h": 50.0,
        "use_mcap_gating": True,
        "mcap_ath_pct": 0.25,
        "structural_exit": False,
    }
    
    print("Initializing V11 engine with TA scorer...")
    engine = SpotBacktestEngineV11(**params)
    
    print("Running backtest on single chunk...")
    result = engine.run(df)
    
    if result:
        print(f"\nSINGLE CHUNK RESULTS:")
        print(f"  PnL: {result.total_return_pct:.2f}%")
        print(f"  Max DD: {result.max_drawdown_pct:.2f}%")
        print(f"  Final Equity: ${result.final_equity:.0f}")
        print(f"  Total Deals: {result.total_deals_completed}")
        print(f"  Short Deals: {result.extra.get('v11_short_deals_completed', 0) if result.extra else 0}")
        print(f"  Short PnL: ${result.extra.get('v11_short_pnl', 0) if result.extra else 0:.2f}")
        print(f"  Force Exits: {result.extra.get('v9_force_exits', 0) if result.extra else 0}")
        print(f"  MCap Gated: {result.extra.get('v11_shorts_gated_by_mcap', 0) if result.extra else 0}")
        return True
    else:
        print("❌ Single chunk test failed")
        return False

if __name__ == "__main__":
    success = test_single_chunk()
    print("✅ Single chunk test completed successfully!" if success else "❌ Single chunk test failed")