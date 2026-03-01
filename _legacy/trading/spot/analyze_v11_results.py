#!/usr/bin/env python3
"""
Analyze V11 backtest results and compare to baselines.

Looks for phase transition logs to verify SHORT entries/exits.
"""
import json
import sys
from pathlib import Path

def analyze_v11_results(results_file: Path):
    """Analyze V11 results and print detailed breakdown."""
    if not results_file.exists():
        print(f"Results file not found: {results_file}")
        return
    
    with open(results_file) as f:
        data = json.load(f)
    
    if not data:
        print("No results found")
        return
    
    print("=" * 80)
    print(f"V11 BACKTEST ANALYSIS: {results_file.name}")
    print("=" * 80)
    
    # Baselines for comparison
    baselines = {
        "V8 baseline": 23.06,
        "V11 no-shorts": 36.18,
        "V9 baseline (15m)": 43.81,
    }
    
    print("\nBASELINES:")
    for name, pnl in baselines.items():
        print(f"  {name}: +{pnl:.2f}%")
    
    print(f"\nV11 MCAP ATH GATING + FAST INVALIDATION RESULTS:")
    print("-" * 60)
    
    valid_results = [r for r in data if "error" not in r]
    
    if not valid_results:
        print("No valid results found")
        return
    
    # Sort by PnL descending
    sorted_results = sorted(valid_results, key=lambda x: x.get("pnl_pct", 0), reverse=True)
    
    for i, result in enumerate(sorted_results):
        params = result.get("params", {})
        
        print(f"\n[{i+1}] CONFIG:")
        print(f"  Market Cap ATH Gating: {params.get('use_mcap_gating', 'N/A')}")
        print(f"  MCAP ATH %: {params.get('mcap_ath_pct', 0.2)*100:.0f}%")
        print(f"  Fast Invalidation: {params.get('enable_fast_invalidation', 'N/A')}")
        print(f"  Short Tight SL: {params.get('short_tight_sl_pct', 'N/A'):.1f}%")
        print(f"  Short Main SL: {params.get('short_sl_pct', 'N/A'):.1f}%")
        print(f"  Structural Exit: {params.get('structural_exit', False)}")
        
        print(f"\n  PERFORMANCE:")
        print(f"  PnL: {result.get('pnl_pct', 0):+.2f}%")
        print(f"  Max DD: {result.get('max_dd', 0):.1f}%")
        print(f"  Total Deals: {result.get('total_deals', 0)}")
        print(f"  Win Rate: {result.get('win_rate', 0):.1f}%")
        print(f"  Sharpe: {result.get('sharpe', 0):.2f}")
        
        print(f"\n  SHORT ACTIVITY:")
        print(f"  Short PnL: ${result.get('short_pnl', 0):+.2f}")
        print(f"  Short Deals: {result.get('short_deals', 0)}")
        print(f"  Shorts Gated by MCAP: {result.get('shorts_gated', 0)}")
        print(f"  Fast Invalidations: {result.get('fast_invalidations', 0)}")
        print(f"  MCAP Data Available: {result.get('mcap_data', False)}")
        
        print(f"\n  OTHER METRICS:")
        print(f"  Force Exits: {result.get('force_exits', 0)}")
        print(f"  Spring Buys: {result.get('spring_buys', 0)}")
        print(f"  Short Funding: ${result.get('short_funding', 0):.2f}")
        
        # Compare to baselines
        pnl = result.get('pnl_pct', 0)
        print(f"\n  BASELINE COMPARISON:")
        for name, baseline_pnl in baselines.items():
            diff = pnl - baseline_pnl
            status = "✅ BEAT" if diff > 0 else "❌ MISSED" if diff < -1 else "➖ CLOSE"
            print(f"    vs {name}: {diff:+.2f}% ({status})")
    
    # Summary
    best_result = sorted_results[0]
    print(f"\n" + "=" * 80)
    print(f"BEST V11 CONFIGURATION:")
    print(f"  PnL: {best_result.get('pnl_pct', 0):+.2f}%")
    print(f"  Short deals fired: {best_result.get('short_deals', 0)}")
    print(f"  Shorts gated by MCAP: {best_result.get('shorts_gated', 0)}")
    print(f"  Fast invalidations: {best_result.get('fast_invalidations', 0)}")
    
    # Check if shorts actually fired
    total_short_deals = sum(r.get('short_deals', 0) for r in sorted_results)
    total_mcap_gated = sum(r.get('shorts_gated', 0) for r in sorted_results)
    
    print(f"\nSHORT ACTIVITY SUMMARY (across all configs):")
    print(f"  Total short deals fired: {total_short_deals}")
    print(f"  Total shorts gated by MCAP: {total_mcap_gated}")
    
    if total_short_deals == 0:
        print("⚠️  WARNING: NO SHORTS FIRED! Check if:")
        print("  - Distribution exit thresholds are too high")
        print("  - MCAP ATH gating is too restrictive")  
        print("  - Market never reached distribution phase")
    
    if total_short_deals > 0:
        print("✅ SUCCESS: Shorts fired during backtest period")


if __name__ == "__main__":
    results_dir = Path("backtest_results/v11_hybrid")
    
    # Look for ETH 1h results
    eth_1h_file = results_dir / "eth_1h.json"
    
    if eth_1h_file.exists():
        analyze_v11_results(eth_1h_file)
    else:
        print(f"Waiting for results file: {eth_1h_file}")
        print("Available files:")
        if results_dir.exists():
            for f in results_dir.glob("*.json"):
                print(f"  {f.name}")
        else:
            print("  Results directory doesn't exist yet")