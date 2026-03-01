#!/usr/bin/env python3
"""V11 Parameter Sweep - Distribution Threshold Optimization for Dec 2024 ETH Top."""

import sys, json, logging, time
from pathlib import Path
from datetime import datetime

import pandas as pd

if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from trading.spot.run_v11_chained import run_chained, PRESETS, DEFAULT_V11_PARAMS
from trading.spot.macro_indicators import load_historical_fear_greed

logging.basicConfig(level=logging.WARNING, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

def run_threshold_sweep():
    """Run parameter sweep on distribution thresholds to optimize short entries."""
    
    preset = PRESETS["eth"]
    fg = load_historical_fear_greed()
    
    # Define sweep configurations
    sweep_configs = [
        # structural_exit=True with dist_exit_threshold_1h values: [15, 20, 25]
        {
            "name": "struct_15", 
            "params": {**DEFAULT_V11_PARAMS, "structural_exit": True, "dist_exit_threshold_1h": 15.0},
            "desc": "Structural Exit, 1h threshold=15"
        },
        {
            "name": "struct_20", 
            "params": {**DEFAULT_V11_PARAMS, "structural_exit": True, "dist_exit_threshold_1h": 20.0},
            "desc": "Structural Exit, 1h threshold=20"
        },
        {
            "name": "struct_25", 
            "params": {**DEFAULT_V11_PARAMS, "structural_exit": True, "dist_exit_threshold_1h": 25.0},
            "desc": "Structural Exit, 1h threshold=25"
        },
        
        # structural_exit=False with regular dist_exit_threshold values: [20, 25, 30]
        {
            "name": "dist_20", 
            "params": {**DEFAULT_V11_PARAMS, "structural_exit": False, "dist_exit_threshold": 20.0},
            "desc": "Distribution Score, threshold=20"
        },
        {
            "name": "dist_25", 
            "params": {**DEFAULT_V11_PARAMS, "structural_exit": False, "dist_exit_threshold": 25.0},
            "desc": "Distribution Score, threshold=25"
        },
        {
            "name": "dist_30", 
            "params": {**DEFAULT_V11_PARAMS, "structural_exit": False, "dist_exit_threshold": 30.0},
            "desc": "Distribution Score, threshold=30"
        },
    ]
    
    results_dir = Path(__file__).resolve().parent / "backtest_results" / "v11_hybrid"
    results_dir.mkdir(parents=True, exist_ok=True)
    
    print("=" * 100)
    print("V11 PARAMETER SWEEP: Distribution Threshold Optimization")
    print(f"Symbol: {preset['symbol']} | Timeframe: 1h")
    print(f"Period: {preset['start']} -> {preset['end']}")
    print(f"Goal: Find threshold that triggers shorts near Dec 2024 ETH top (~$4000)")
    print(f"Configurations: {len(sweep_configs)} sweeps")
    print("=" * 100)
    
    all_results = []
    
    for i, config in enumerate(sweep_configs):
        config_name = config["name"]
        config_params = config["params"]
        config_desc = config["desc"]
        
        print(f"\n[{i+1}/{len(sweep_configs)}] {config_desc}")
        print("-" * 80)
        
        try:
            start_time = time.time()
            
            result, chunk_info = run_chained(
                preset["symbol"], "1h", preset["start"], preset["end"],
                preset["capital"], fg, config_params, profile="medium", exchange="aster"
            )
            
            elapsed = time.time() - start_time
            
            if result:
                extra = result.extra or {}
                
                # Count shorts fired during Dec 2024
                dec_2024_start = int(datetime(2024, 12, 1).timestamp() * 1000)
                dec_2024_end = int(datetime(2025, 1, 1).timestamp() * 1000)
                
                dec_shorts = 0
                for log_entry in result.trade_log:
                    action = log_entry.action if hasattr(log_entry, 'action') else log_entry.get('action')
                    timestamp = log_entry.timestamp if hasattr(log_entry, 'timestamp') else log_entry.get('timestamp')
                    if action == "SHORT_OPEN":
                        ts_ms = int(pd.Timestamp(timestamp).timestamp() * 1000)
                        if dec_2024_start <= ts_ms <= dec_2024_end:
                            dec_shorts += 1
                
                # Count shorts fired during mid-2023 (should be 0)
                mid_2023_start = int(datetime(2023, 6, 1).timestamp() * 1000)
                mid_2023_end = int(datetime(2023, 9, 1).timestamp() * 1000)
                
                mid_2023_shorts = 0
                for log_entry in result.trade_log:
                    action = log_entry.action if hasattr(log_entry, 'action') else log_entry.get('action')
                    timestamp = log_entry.timestamp if hasattr(log_entry, 'timestamp') else log_entry.get('timestamp')
                    if action == "SHORT_OPEN":
                        ts_ms = int(pd.Timestamp(timestamp).timestamp() * 1000)
                        if mid_2023_start <= ts_ms <= mid_2023_end:
                            mid_2023_shorts += 1
                
                entry = {
                    "config_name": config_name,
                    "config_desc": config_desc,
                    "params": config_params,
                    "pnl_pct": round(result.total_return_pct, 2),
                    "max_dd_pct": round(result.max_drawdown_pct, 2),
                    "final_equity": round(result.final_equity, 2),
                    "total_deals": result.total_deals_completed,
                    "win_rate": round(result.win_rate, 1),
                    "sharpe_ratio": round(result.sharpe_ratio, 2),
                    "short_deals_total": extra.get("v11_short_deals_completed", 0),
                    "short_pnl": round(extra.get("v11_short_pnl", 0.0), 2),
                    "short_funding": round(extra.get("v11_short_funding", 0.0), 2),
                    "shorts_gated_by_mcap": extra.get("v11_shorts_gated_by_mcap", 0),
                    "fast_invalidations": extra.get("v11_fast_invalidations", 0),
                    "force_exits": extra.get("v9_force_exits", 0),
                    "dec_2024_shorts": dec_shorts,
                    "mid_2023_shorts": mid_2023_shorts,
                    "elapsed_sec": round(elapsed, 1),
                    "chunks": chunk_info,
                }
                all_results.append(entry)
                
                # Save individual result
                result_file = results_dir / f"sweep_thresh_{config_name}.json"
                with open(result_file, "w") as f:
                    json.dump(entry, f, indent=2, default=str)
                
                print(f"✓ RESULT: PnL={result.total_return_pct:+6.2f}% | DD={result.max_drawdown_pct:5.1f}% | "
                      f"Total_Deals={result.total_deals_completed:3} | Win_Rate={result.win_rate:4.0f}%")
                print(f"  Short_Deals={extra.get('v11_short_deals_completed', 0):2} | "
                      f"Short_PnL=${extra.get('v11_short_pnl', 0.0):+7.2f} | "
                      f"Funding=${extra.get('v11_short_funding', 0.0):6.2f}")
                print(f"  Dec_2024_Shorts={dec_shorts:2} | Mid_2023_Shorts={mid_2023_shorts:2} | "
                      f"Force_Exits={extra.get('v9_force_exits', 0):2} | Time={elapsed:.1f}s")
                print(f"  Saved: {result_file}")
                
            else:
                entry = {"config_name": config_name, "error": "no result returned"}
                all_results.append(entry)
                print("✗ ERROR: No result returned")
                
        except Exception as e:
            import traceback
            traceback.print_exc()
            entry = {"config_name": config_name, "error": str(e)}
            all_results.append(entry)
            print(f"✗ ERROR: {e}")
    
    # Save combined results
    combined_file = results_dir / "sweep_threshold_summary.json"
    with open(combined_file, "w") as f:
        json.dump(all_results, f, indent=2, default=str)
    
    # Print comparison table
    print_comparison_table(all_results)
    
    print(f"\n{'='*100}")
    print(f"SWEEP COMPLETE: {len(all_results)} configurations tested")
    print(f"Combined results: {combined_file}")
    print(f"Individual results: {results_dir}/sweep_thresh_*.json")
    print(f"{'='*100}")

def print_comparison_table(results):
    """Print a comparison table of all sweep results."""
    valid_results = [r for r in results if "error" not in r]
    
    if not valid_results:
        print("\n❌ No valid results to compare!")
        return
    
    print(f"\n{'='*120}")
    print(f"COMPARISON TABLE: {len(valid_results)} Valid Configurations")
    print(f"{'='*120}")
    print(f"{'Config':<12} {'PnL%':<8} {'MaxDD%':<8} {'TotalDeals':<11} {'ShortDeals':<11} {'Dec2024':<8} {'Mid2023':<8} {'ShortPnL$':<10}")
    print(f"{'-'*12} {'-'*8} {'-'*8} {'-'*11} {'-'*11} {'-'*8} {'-'*8} {'-'*10}")
    
    # Sort by total PnL descending
    sorted_results = sorted(valid_results, key=lambda x: x.get("pnl_pct", -999), reverse=True)
    
    for r in sorted_results:
        config = r["config_name"]
        pnl = r.get("pnl_pct", 0)
        dd = r.get("max_dd_pct", 0)
        total_deals = r.get("total_deals", 0)
        short_deals = r.get("short_deals_total", 0)
        dec_shorts = r.get("dec_2024_shorts", 0)
        mid_shorts = r.get("mid_2023_shorts", 0)
        short_pnl = r.get("short_pnl", 0)
        
        # Highlight good configs
        marker = ""
        if dec_shorts > 0 and mid_shorts == 0:
            marker = " ✓"  # Good: shorts in Dec 2024, none in mid 2023
        elif dec_shorts == 0:
            marker = " ❌"  # Bad: no shorts in Dec 2024
        elif mid_shorts > 0:
            marker = " ⚠️"  # Warning: shorts in mid 2023
            
        print(f"{config:<12} {pnl:>+7.2f} {dd:>7.1f} {total_deals:>10} {short_deals:>10} "
              f"{dec_shorts:>7} {mid_shorts:>7} {short_pnl:>+9.2f}{marker}")
    
    print(f"{'-'*120}")
    print("Legend: ✓ = Good (Dec shorts, no mid-2023 shorts) | ❌ = No Dec shorts | ⚠️ = Mid-2023 shorts")
    print(f"{'='*120}")

if __name__ == "__main__":
    run_threshold_sweep()