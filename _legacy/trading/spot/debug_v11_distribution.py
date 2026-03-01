#!/usr/bin/env python3
"""Debug V11 Distribution Scoring - See what scores are generated during Dec 2024."""

import sys, json, logging
from pathlib import Path
from datetime import datetime, timezone

import pandas as pd

if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from trading.spot.run_v11_chained import run_chained, PRESETS, DEFAULT_V11_PARAMS
from trading.spot.macro_indicators import load_historical_fear_greed

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

def debug_distribution_scores():
    """Run V11 with debug logging to see distribution scores during Dec 2024."""
    
    preset = PRESETS["eth"]
    fg = load_historical_fear_greed()
    
    # Use a very low threshold to ensure we capture all distribution events
    debug_params = {
        **DEFAULT_V11_PARAMS,
        "dist_exit_threshold_1h": 5.0,  # Very low to catch all events
        "structural_exit": False,  # Use distribution scores, not structural
        "use_mcap_gating": False,  # Disable mcap gating for pure score analysis
    }
    
    print("=" * 80)
    print("DEBUG V11: Distribution Score Analysis")
    print("ETH/USDT 1h | 2022-06-01 -> 2025-02-19")
    print("Looking for distribution scores during Dec 2024 ETH top...")
    print("=" * 80)
    
    try:
        result, chunk_info = run_chained(
            preset["symbol"], "1h", preset["start"], preset["end"],
            preset["capital"], fg, debug_params, profile="medium", exchange="aster"
        )
        
        if result:
            extra = result.extra or {}
            print(f"\nDEBUG RESULTS:")
            print(f"  PnL: {result.total_return_pct:+.2f}%")
            print(f"  Short deals: {extra.get('v11_short_deals_completed', 0)}")
            print(f"  Force exits: {extra.get('v9_force_exits', 0)}")
            
            # Check trade log for distribution exits near Dec 2024
            dec_2024_start = int(datetime(2024, 12, 1, tzinfo=timezone.utc).timestamp() * 1000)
            dec_2024_end = int(datetime(2025, 1, 1, tzinfo=timezone.utc).timestamp() * 1000)
            
            relevant_logs = []
            for log_entry in result.trade_log:
                ts_ms = int(pd.Timestamp(log_entry.timestamp).timestamp() * 1000)
                if dec_2024_start <= ts_ms <= dec_2024_end:
                    if log_entry.action in ["SHORT_OPEN", "DEAL_CLOSE"]:
                        relevant_logs.append(log_entry)
            
            print(f"\nDEC 2024 TRADE ACTIVITY ({len(relevant_logs)} entries):")
            for log in relevant_logs:
                print(f"  {log.timestamp} | {log.action} | Price: ${log.price:.2f}")
                
        else:
            print("ERROR: No result returned")
            
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"ERROR: {e}")

if __name__ == "__main__":
    debug_distribution_scores()