"""Test just the BottomStackDetector."""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import BottomStackDetector from our main script
from _conviction_weighted_test import BottomStackDetector

print("Testing BottomStackDetector...")

coin = 'BTC'
detector = BottomStackDetector(coin)

if detector.daily is not None:
    print(f"SUCCESS: Loaded {len(detector.daily)} daily candles")
    print(f"Date range: {detector.daily.index.min()} to {detector.daily.index.max()}")
    
    # Test a specific date
    test_date = detector.daily.index[-100]  # 100 days ago
    conviction, signals = detector.get_conviction_score(test_date)
    
    print(f"Test date: {test_date}")
    print(f"Conviction score: {conviction}/5")
    print(f"Signals: {signals}")
else:
    print("ERROR: Failed to load daily data")

if detector.cfgi is not None:
    print(f"SUCCESS: Loaded {len(detector.cfgi)} CFGI records")
    print(f"CFGI date range: {detector.cfgi.index.min()} to {detector.cfgi.index.max()}")
else:
    print("ERROR: Failed to load CFGI data")

print("Done.")