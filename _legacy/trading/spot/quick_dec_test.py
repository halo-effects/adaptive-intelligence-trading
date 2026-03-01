#!/usr/bin/env python3
"""Quick December 2024 Test - Focus on specific period."""

import sys, json, logging
from pathlib import Path
from datetime import datetime

import pandas as pd

if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from trading.spot.backtest_engine_v11 import SpotBacktestEngineV11
from trading.spot.run_v11_chained import get_candles
from trading.spot.macro_indicators import load_historical_fear_greed

logging.basicConfig(level=logging.INFO)

def quick_dec_2024_test():
    """Quick test focused on December 2024 period only."""
    
    print("=" * 80)
    print("QUICK DECEMBER 2024 TEST")
    print("Testing V11 configurations on Dec 2024 period only")
    print("=" * 80)
    
    # Get data for Nov 2024 - Jan 2025 (need context before Dec)
    df = get_candles("ETH/USDT", "1h", "2024-10-01", "2025-01-31", exchange="aster")
    
    if len(df) < 100:
        print("ERROR: Not enough data")
        return
        
    print(f"Got {len(df)} candles from Oct 2024 to Jan 2025")
    
    # Load F&G data
    fg = load_historical_fear_greed()
    
    # Test configurations
    configs = [
        {
            "name": "baseline_30",
            "desc": "Baseline: structural=True, threshold=30",
            "params": {
                "structural_exit": True,
                "dist_exit_threshold_1h": 30.0,
                "use_mcap_gating": True,
            }
        },
        {
            "name": "lower_15",
            "desc": "Lower threshold: structural=True, threshold=15",
            "params": {
                "structural_exit": True,
                "dist_exit_threshold_1h": 15.0,
                "use_mcap_gating": False,
            }
        },
        {
            "name": "pure_dist_15", 
            "desc": "Pure distribution: structural=False, threshold=15",
            "params": {
                "structural_exit": False,
                "dist_exit_threshold": 15.0,
                "use_mcap_gating": False,
            }
        }
    ]
    
    results = []
    
    for config in configs:
        print(f"\nTesting: {config['desc']}")
        print("-" * 60)
        
        try:
            engine = SpotBacktestEngineV11(
                dwell_profile="aggressive", 
                profile="medium", 
                capital=10000,
                exchange="aster", 
                symbol="ETH/USDT", 
                timeframe="1h",
                variant="regime_adaptive", 
                compounding=True, 
                conviction_mode=True,
                fear_greed_history=fg,
                # V11 params
                **config["params"]
            )
            
            result = engine.run(df)
            
            if result:
                extra = result.extra or {}
                
                # Count short entries in December
                dec_shorts = 0
                short_details = []
                
                for log_entry in result.trade_log:
                    action = getattr(log_entry, 'action', log_entry.get('action'))
                    if action == "SHORT_OPEN":
                        timestamp = getattr(log_entry, 'timestamp', log_entry.get('timestamp'))
                        price = getattr(log_entry, 'price', log_entry.get('price'))
                        
                        entry_date = pd.Timestamp(timestamp)
                        if entry_date >= pd.Timestamp('2024-12-01') and entry_date <= pd.Timestamp('2024-12-31'):
                            dec_shorts += 1
                            short_details.append({
                                'date': entry_date.strftime('%Y-%m-%d %H:%M'),
                                'price': price
                            })
                
                print(f"  Result: PnL={result.total_return_pct:+.2f}%, Short_deals={extra.get('v11_short_deals_completed', 0)}")
                print(f"  Dec 2024 shorts: {dec_shorts}")
                print(f"  Force exits: {extra.get('v9_force_exits', 0)}")
                
                if short_details:
                    print("  Short entries:")
                    for detail in short_details:
                        print(f"    {detail['date']} @ ${detail['price']:.2f}")
                else:
                    print("  ❌ No December shorts fired!")
                
                results.append({
                    "config": config["name"],
                    "desc": config["desc"],
                    "pnl_pct": result.total_return_pct,
                    "dec_shorts": dec_shorts,
                    "short_details": short_details,
                    "force_exits": extra.get('v9_force_exits', 0),
                    "short_pnl": extra.get('v11_short_pnl', 0.0)
                })
                
            else:
                print("  ERROR: No result")
                
        except Exception as e:
            print(f"  ERROR: {e}")
            import traceback
            traceback.print_exc()
    
    print(f"\n" + "=" * 80)
    print("QUICK TEST SUMMARY")
    print("=" * 80)
    
    if results:
        print(f"{'Config':<20} {'Dec_Shorts':<11} {'PnL%':<8} {'Force_Exits':<12}")
        print("-" * 20 + " " + "-" * 11 + " " + "-" * 8 + " " + "-" * 12)
        
        for r in results:
            config_short = r["config"][:19]
            print(f"{config_short:<20} {r['dec_shorts']:>10} {r['pnl_pct']:>+7.2f} {r['force_exits']:>11}")
        
        # Check if any config worked
        working_configs = [r for r in results if r["dec_shorts"] > 0]
        if working_configs:
            print(f"\n✓ SUCCESS: {len(working_configs)} config(s) fired shorts in Dec 2024")
            for config in working_configs:
                print(f"  {config['config']}: {config['dec_shorts']} shorts")
        else:
            print(f"\n❌ FAILURE: No configs fired shorts in Dec 2024")
            print("  Recommendation: Try even lower thresholds (10, 12) or different approach")
    
    # Save results
    output_file = Path(__file__).resolve().parent / "backtest_results" / "v11_hybrid" / "quick_dec_test.json"
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    
    print(f"\nResults saved to: {output_file}")
    print("=" * 80)

if __name__ == "__main__":
    quick_dec_2024_test()