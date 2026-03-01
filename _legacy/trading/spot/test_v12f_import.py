#!/usr/bin/env python3
"""Quick V12f import test"""
import sys
from pathlib import Path

# Add paths
sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

try:
    from backtest_engine_v12f import SpotBacktestEngineV12f
    print("✅ Import successful")
    
    # Try to create an engine with minimal config
    config = {
        'symbol': 'ETH/USDT',
        'initial_capital': 10000,
        'maker_fee': 0.001,
        'taker_fee': 0.001,
        'v12f_gates': True,
        'v12f_markdown_exit': True,
    }
    
    engine = SpotBacktestEngineV12f(**config)
    print("✅ Engine creation successful")
    print(f"✅ V12f gates enabled: {engine._v12f_gates}")
    print(f"✅ V12f markdown exit enabled: {engine._v12f_markdown_exit}")
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()