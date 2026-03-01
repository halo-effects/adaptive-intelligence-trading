import sys
import os

# Add paths
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

print("Python paths:")
for p in sys.path[:5]:
    print(f"  {p}")

try:
    from trading.regime_detector import classify_regime_v2
    print("SUCCESS: imported regime_detector")
except Exception as e:
    print(f"FAILED: regime_detector: {e}")

try:
    from trading.indicators import atr, atr_pct
    print("SUCCESS: imported indicators")
except Exception as e:
    print(f"FAILED: indicators: {e}")

try:
    from trading.spot.backtest_engine_v3 import SpotBacktestEngineV3
    print("SUCCESS: imported backtest_engine_v3")
except Exception as e:
    print(f"FAILED: backtest_engine_v3: {e}")

print("All imports working!")