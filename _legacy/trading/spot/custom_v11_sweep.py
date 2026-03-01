#!/usr/bin/env python3
"""Custom V11 sweep for the 3 requested configurations."""
import sys, json, logging, time
from pathlib import Path
from datetime import datetime, timezone, timedelta

import ccxt, pandas as pd, numpy as np

if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from trading.spot.backtest_engine_v11 import SpotBacktestEngineV11
from trading.spot.macro_indicators import load_historical_fear_greed

logging.basicConfig(level=logging.WARNING, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

CACHE_DIR = Path(__file__).resolve().parent / "data" / "dwell_cache"
RESULTS_DIR = Path(__file__).resolve().parent / "backtest_results" / "v11_hybrid"

# Import the necessary functions from the original script
exec(open(Path(__file__).resolve().parent / "run_v11_chained.py").read())

# Custom configurations for the 3 requested runs
CUSTOM_CONFIGS = [
    {
        "name": "sweep_dist15",
        "params": {**DEFAULT_V11_PARAMS, 
                  "structural_exit": False, 
                  "dist_exit_threshold_1h": 15, 
                  "use_mcap_gating": False},
        "output": "sweep_dist15.json"
    },
    {
        "name": "sweep_dist20", 
        "params": {**DEFAULT_V11_PARAMS,
                  "structural_exit": False,
                  "dist_exit_threshold_1h": 20,
                  "use_mcap_gating": False},
        "output": "sweep_dist20.json"
    },
    {
        "name": "sweep_struct20",
        "params": {**DEFAULT_V11_PARAMS,
                  "structural_exit": True,
                  "dist_exit_threshold_1h": 20,
                  "use_mcap_gating": False},
        "output": "sweep_struct20.json"
    }
]

def run_custom_config(config, preset_name="eth", timeframe="1h"):
    preset = PRESETS[preset_name]
    fg = load_historical_fear_greed()
    
    print(f"\n{'='*80}")
    print(f"  Running Config: {config['name']}")
    print(f"  {preset['symbol']} | {timeframe} | {preset['start']} -> {preset['end']} | ${preset['capital']:,.0f}")
    print(f"  structural_exit={config['params']['structural_exit']}")
    print(f"  dist_exit_threshold_1h={config['params']['dist_exit_threshold_1h']}")
    print(f"  use_mcap_gating={config['params']['use_mcap_gating']}")
    print(f"{'='*80}\n")
    
    try:
        result, chunk_info = run_chained(
            preset["symbol"], timeframe, preset["start"], preset["end"],
            preset["capital"], fg, config["params"], profile="medium", exchange="aster"
        )
        
        if result:
            extra = result.extra if hasattr(result, 'extra') and result.extra else {}
            entry = {
                "config_name": config["name"],
                "timeframe": timeframe,
                "profile": "medium",
                "params": config["params"],
                "pnl_pct": round(result.total_return_pct, 2),
                "max_dd": round(result.max_drawdown_pct, 2),
                "final_equity": round(result.final_equity, 2),
                "total_deals": result.total_deals_completed,
                "win_rate": round(result.win_rate, 1),
                "sharpe": round(result.sharpe_ratio, 2),
                "spring_buys": extra.get("v8_spring_buys", 0),
                "force_exits": extra.get("v9_force_exits", 0),
                "short_pnl": extra.get("v11_short_pnl", 0.0),
                "short_funding": extra.get("v11_short_funding", 0.0),
                "short_deals": extra.get("v11_short_deals_completed", 0),
                "shorts_gated": extra.get("v11_shorts_gated_by_mcap", 0),
                "fast_invalidations": extra.get("v11_fast_invalidations", 0),
                "mcap_data": extra.get("v11_mcap_data_available", False),
                "phase_transitions": extra.get("phase_transitions", []),
                "chunks": chunk_info,
                "timestamp": datetime.now().isoformat(),
            }
            
            # Save individual result
            out_file = RESULTS_DIR / config["output"]
            RESULTS_DIR.mkdir(parents=True, exist_ok=True)
            with open(out_file, "w") as f:
                json.dump(entry, f, indent=2, default=str)
            
            print(f"\n  {'='*60}")
            print(f"  RESULT: PnL={result.total_return_pct:+.2f}% | DD={result.max_drawdown_pct:.1f}% | "
                  f"Deals={result.total_deals_completed} | Win={result.win_rate:.0f}% | "
                  f"Sharpe={result.sharpe_ratio:.2f}")
            print(f"  Final equity: ${result.final_equity:,.2f}")
            print(f"  Short PnL: ${extra.get('v11_short_pnl', 0):+.2f} | "
                  f"Funding: ${extra.get('v11_short_funding', 0):.2f} | "
                  f"Short deals: {extra.get('v11_short_deals_completed', 0)}")
            print(f"  Force exits: {extra.get('v9_force_exits', 0)} | "
                  f"Spring buys: {extra.get('v8_spring_buys', 0)}")
            print(f"  Phase transitions: {len(extra.get('phase_transitions', []))}")
            print(f"  Saved to: {out_file}")
            print(f"  {'='*60}")
            
            return entry
        else:
            print(f"  ERROR: No result returned")
            return None
            
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"  ERROR: {e}")
        return None

def main():
    print("Running 3 Custom V11 Configurations on ETH 1h...")
    
    results = []
    for config in CUSTOM_CONFIGS:
        result = run_custom_config(config)
        if result:
            results.append(result)
            
    # Print summary table
    if results:
        print(f"\n{'='*100}")
        print(f"  FINAL SUMMARY - ETH/USDT 1h Full 2.7yr Cycle")
        print(f"  Baselines: V8=+23.06%, V11 baseline=+41.57%")
        print(f"{'='*100}")
        print(f"| {'Config':<15} | {'PnL%':<8} | {'MaxDD':<6} | {'Short Deals':<11} | {'Short PnL':<9} | {'Force Exits':<11} |")
        print(f"|{'-'*17}|{'-'*10}|{'-'*8}|{'-'*13}|{'-'*11}|{'-'*13}|")
        
        for r in results:
            print(f"| {r['config_name']:<15} | {r['pnl_pct']:>+7.2f}% | {r['max_dd']:>5.1f}% | {r['short_deals']:>11d} | {r['short_pnl']:>+8.2f}$ | {r['force_exits']:>11d} |")
        
        # Print phase transitions
        print(f"\n{'='*80}")
        print(f"  PHASE TRANSITIONS (Short Entry/Exit Events)")
        print(f"{'='*80}")
        for r in results:
            transitions = r.get('phase_transitions', [])
            print(f"\n{r['config_name']}:")
            if transitions:
                for i, t in enumerate(transitions):
                    print(f"  {i+1}: {t}")
            else:
                print("  No phase transitions recorded")
    
    print(f"\nAll configurations completed!")

if __name__ == "__main__":
    main()