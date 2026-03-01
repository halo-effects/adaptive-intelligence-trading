"""Simple conviction weighted test - minimal version."""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from v13_signals import V13SignalPack
from v13_phase_backtest_v8 import V13BacktestV8, V13Config

print("Conviction-Weighted Tier Deployment Backtest")
print("=" * 60)

# Test just one coin first
coin = 'BTC'
print(f"Testing {coin}...")

try:
    # Load signal pack
    pack = V13SignalPack(coin)
    if pack.daily is None:
        print(f"No data for {coin}")
        exit(1)
        
    print(f"Loaded {len(pack.daily)} daily candles")
    
    # Configure backtest
    config = V13Config()
    config.CAPITAL = 2500
    
    # Run baseline V13 backtest
    print("Running baseline V13 backtest...")
    bt = V13BacktestV8(pack, config)
    result = bt.run()
    
    if result:
        print(f"Final equity: ${result['final_equity']:,.0f}")
        print(f"ROI: {result['roi']:+.1f}%")
        print(f"Trades: {result['total_trades']}")
        print(f"Phase changes: {result['phase_changes']}")
    else:
        print("No results returned")
    
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
    
print("Done.")