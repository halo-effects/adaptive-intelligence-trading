#!/usr/bin/env python3
"""Test Optimal V11 Configuration - Based on Dec 2024 Analysis."""

import sys, json, logging, time
from pathlib import Path
from datetime import datetime

import pandas as pd

if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from trading.spot.run_v11_chained import run_chained, PRESETS, DEFAULT_V11_PARAMS
from trading.spot.macro_indicators import load_historical_fear_greed

logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)

def test_optimal_v11_configs():
    """Test the most promising V11 configurations based on analysis."""
    
    preset = PRESETS["eth"]
    fg = load_historical_fear_greed()
    
    # Based on analysis: death cross Dec 10, peak Dec 16, major distribution
    test_configs = [
        {
            "name": "structural_15_no_mcap",
            "desc": "Structural Exit, threshold=15, NO mcap gating",
            "params": {
                **DEFAULT_V11_PARAMS,
                "structural_exit": True,
                "dist_exit_threshold_1h": 15.0,
                "use_mcap_gating": False,  # Disable to test pure structural
            }
        },
        {
            "name": "structural_20_no_mcap", 
            "desc": "Structural Exit, threshold=20, NO mcap gating",
            "params": {
                **DEFAULT_V11_PARAMS,
                "structural_exit": True,
                "dist_exit_threshold_1h": 20.0,
                "use_mcap_gating": False,
            }
        },
        {
            "name": "dist_score_15",
            "desc": "Pure Distribution Score, threshold=15",
            "params": {
                **DEFAULT_V11_PARAMS,
                "structural_exit": False,
                "dist_exit_threshold": 15.0,
                "use_mcap_gating": False,
            }
        }
    ]
    
    results_dir = Path(__file__).resolve().parent / "backtest_results" / "v11_hybrid"
    results_dir.mkdir(parents=True, exist_ok=True)
    
    print("=" * 100)
    print("V11 OPTIMAL CONFIGURATION TEST")
    print(f"Symbol: {preset['symbol']} | Timeframe: 1h")
    print(f"Target: Short entries during Dec 2024 ETH top ($4087 peak on Dec 16)")
    print(f"Configurations: {len(test_configs)} focused tests")
    print("=" * 100)
    
    results = []
    
    for i, config in enumerate(test_configs):
        print(f"\n[{i+1}/{len(test_configs)}] {config['desc']}")
        print("-" * 80)
        
        try:
            start_time = time.time()
            
            result, chunk_info = run_chained(
                preset["symbol"], "1h", preset["start"], preset["end"],
                preset["capital"], fg, config["params"], profile="medium", exchange="aster"
            )
            
            elapsed = time.time() - start_time
            
            if result:
                extra = result.extra or {}
                
                # Analyze trade log for short entries
                short_entries = []
                for log_entry in result.trade_log:
                    action = getattr(log_entry, 'action', None) or log_entry.get('action')
                    if action == "SHORT_OPEN":
                        timestamp = getattr(log_entry, 'timestamp', None) or log_entry.get('timestamp')
                        price = getattr(log_entry, 'price', None) or log_entry.get('price')
                        short_entries.append({
                            'timestamp': timestamp,
                            'price': price,
                            'date': pd.Timestamp(timestamp).strftime('%Y-%m-%d %H:%M')
                        })
                
                # Count December 2024 shorts
                dec_2024_shorts = []
                for entry in short_entries:
                    entry_date = pd.Timestamp(entry['timestamp'])
                    if entry_date >= pd.Timestamp('2024-12-01') and entry_date <= pd.Timestamp('2024-12-31'):
                        dec_2024_shorts.append(entry)
                
                # Count mid-2023 shorts (should be none)
                mid_2023_shorts = []
                for entry in short_entries:
                    entry_date = pd.Timestamp(entry['timestamp'])
                    if entry_date >= pd.Timestamp('2023-06-01') and entry_date <= pd.Timestamp('2023-09-01'):
                        mid_2023_shorts.append(entry)
                
                entry = {
                    "config_name": config["name"],
                    "config_desc": config["desc"],
                    "params": config["params"],
                    "pnl_pct": round(result.total_return_pct, 2),
                    "max_dd_pct": round(result.max_drawdown_pct, 2),
                    "final_equity": round(result.final_equity, 2),
                    "total_deals": result.total_deals_completed,
                    "win_rate": round(result.win_rate, 1),
                    "short_deals_total": extra.get("v11_short_deals_completed", 0),
                    "short_pnl": round(extra.get("v11_short_pnl", 0.0), 2),
                    "short_funding": round(extra.get("v11_short_funding", 0.0), 2),
                    "force_exits": extra.get("v9_force_exits", 0),
                    "fast_invalidations": extra.get("v11_fast_invalidations", 0),
                    "total_short_entries": len(short_entries),
                    "dec_2024_shorts": len(dec_2024_shorts),
                    "mid_2023_shorts": len(mid_2023_shorts),
                    "dec_2024_short_details": dec_2024_shorts,
                    "elapsed_sec": round(elapsed, 1),
                }
                results.append(entry)
                
                # Save individual result
                result_file = results_dir / f"optimal_test_{config['name']}.json"
                with open(result_file, "w") as f:
                    json.dump(entry, f, indent=2, default=str)
                
                print(f"✓ RESULT: PnL={result.total_return_pct:+6.2f}% | "
                      f"Short_Entries={len(short_entries):2} | Dec_2024={len(dec_2024_shorts):2} | Mid_2023={len(mid_2023_shorts):2}")
                
                if dec_2024_shorts:
                    print("  Dec 2024 SHORT ENTRIES:")
                    for short in dec_2024_shorts:
                        print(f"    {short['date']} | ${short['price']:.2f}")
                else:
                    print("  ❌ NO Dec 2024 shorts!")
                
                if mid_2023_shorts:
                    print("  ⚠️ WARNING: Mid-2023 shorts detected:")
                    for short in mid_2023_shorts[:3]:
                        print(f"    {short['date']} | ${short['price']:.2f}")
                
                print(f"  Short_PnL=${extra.get('v11_short_pnl', 0.0):+7.2f} | "
                      f"Force_Exits={extra.get('v9_force_exits', 0):2} | Time={elapsed:.1f}s")
                      
            else:
                print("✗ ERROR: No result returned")
                results.append({"config_name": config["name"], "error": "no result"})
                
        except Exception as e:
            import traceback
            traceback.print_exc()
            print(f"✗ ERROR: {e}")
            results.append({"config_name": config["name"], "error": str(e)})
    
    # Print summary
    print(f"\n" + "=" * 100)
    print("OPTIMAL CONFIGURATION TEST SUMMARY")
    print("=" * 100)
    
    valid_results = [r for r in results if "error" not in r]
    if valid_results:
        print(f"{'Config':<25} {'PnL%':<8} {'Dec_Shorts':<11} {'Mid_Shorts':<11} {'ShortPnL$':<10} {'Result':<10}")
        print("-" * 25 + " " + "-" * 8 + " " + "-" * 11 + " " + "-" * 11 + " " + "-" * 10 + " " + "-" * 10)
        
        for r in sorted(valid_results, key=lambda x: x.get("dec_2024_shorts", 0), reverse=True):
            config = r["config_name"].replace("_", " ")[:24]
            pnl = r.get("pnl_pct", 0)
            dec_shorts = r.get("dec_2024_shorts", 0)
            mid_shorts = r.get("mid_2023_shorts", 0)
            short_pnl = r.get("short_pnl", 0)
            
            if dec_shorts > 0 and mid_shorts == 0:
                result = "✓ SUCCESS"
            elif dec_shorts > 0:
                result = "⚠️ SHORTS"
            else:
                result = "❌ NO_DEC"
                
            print(f"{config:<25} {pnl:>+7.2f} {dec_shorts:>10} {mid_shorts:>10} {short_pnl:>+9.2f} {result:<10}")
        
        # Find the best config
        best_config = None
        for r in valid_results:
            if r.get("dec_2024_shorts", 0) > 0 and r.get("mid_2023_shorts", 0) == 0:
                if best_config is None or r.get("pnl_pct", 0) > best_config.get("pnl_pct", 0):
                    best_config = r
        
        if best_config:
            print(f"\n🎯 BEST CONFIGURATION: {best_config['config_name']}")
            print(f"   Description: {best_config['config_desc']}")
            print(f"   PnL: {best_config['pnl_pct']:+.2f}%")
            print(f"   Dec 2024 shorts: {best_config['dec_2024_shorts']}")
            print(f"   Short PnL: ${best_config['short_pnl']:+.2f}")
            
            if best_config['dec_2024_short_details']:
                print(f"   Short entry dates:")
                for short in best_config['dec_2024_short_details']:
                    print(f"     {short['date']} @ ${short['price']:.2f}")
        else:
            print("\n❌ No optimal configuration found!")
            print("   Recommend further threshold reduction or different approach")
    
    else:
        print("❌ No valid results!")
    
    # Save combined results
    combined_file = results_dir / "optimal_config_test_results.json"
    with open(combined_file, "w") as f:
        json.dump(results, f, indent=2, default=str)
    
    print(f"\n✓ Results saved to: {combined_file}")
    print("=" * 100)

if __name__ == "__main__":
    test_optimal_v11_configs()