"""V10 Distribution/Markdown Threshold Sweep on 1h candles.

Tests lowered dist_threshold and markdown_dist_threshold to trigger
DISTRIBUTION→MARKDOWN→SHORT rotation that was missing in run 6.
"""
import json
import sys
import os
import logging
from pathlib import Path
from datetime import datetime, timedelta
from itertools import product

# Add parent to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from trading.spot.run_v10_chained import (
    run_chained, load_historical_fear_greed, PRESETS, DEFAULT_V10_PARAMS, RESULTS_DIR
)

logger = logging.getLogger("v10_dist_sweep")

# Sweep configs — lower thresholds to trigger dist/markdown
DIST_THRESHOLDS = [20, 30, 40]       # was 40
MARKDOWN_DIST_THRESHOLDS = [30, 40, 50]  # was 60
# Only combos where markdown >= dist
COMBOS = [(d, m) for d, m in product(DIST_THRESHOLDS, MARKDOWN_DIST_THRESHOLDS) if m >= d]


def main():
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    
    preset = PRESETS["eth"]
    symbol = preset["symbol"]
    start = preset["start"]
    end = preset["end"]
    capital = preset["capital"]
    timeframe = "1h"
    
    fg = load_historical_fear_greed()
    print(f"Loaded {len(fg)} F&G entries")
    
    out_file = RESULTS_DIR / "v10_dist_sweep.json"
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    
    # Load existing results
    results = []
    if out_file.exists():
        results = json.loads(out_file.read_text())
        print(f"Loaded {len(results)} existing results")
    
    done_keys = {(r["dist_threshold"], r["markdown_dist_threshold"]) for r in results}
    
    print(f"\n{'='*80}")
    print(f"  V10 DIST/MARKDOWN THRESHOLD SWEEP — 1h candles")
    print(f"  {symbol} | {start} → {end} | ${capital:,.0f}")
    print(f"  {len(COMBOS)} combos, {len(COMBOS) - len(done_keys)} remaining")
    print(f"{'='*80}\n")
    
    for di, (dist_t, md_t) in enumerate(COMBOS):
        if (dist_t, md_t) in done_keys:
            print(f"  [{di+1}/{len(COMBOS)}] dist={dist_t}, md={md_t} — SKIPPED (done)")
            continue
        
        print(f"\n  [{di+1}/{len(COMBOS)}] dist_threshold={dist_t}, markdown_dist={md_t}")
        
        params = dict(DEFAULT_V10_PARAMS)
        params["v10_dist_threshold"] = float(dist_t)
        params["v10_markdown_dist_threshold"] = float(md_t)
        
        try:
            result, equity, chunks = run_chained(
                symbol, timeframe, start, end, capital, fg, params,
                profile="medium",
            )
            
            extra = result.extra or {}
            transitions = extra.get("v10_phase_transitions", [])
            entry = {
                "dist_threshold": dist_t,
                "markdown_dist_threshold": md_t,
                "pnl_pct": round(result.total_return_pct, 2),
                "max_dd": round(result.max_drawdown_pct, 2),
                "final_equity": round(result.final_equity, 2),
                "deals": result.total_deals_completed,
                "win_rate": round(result.win_rate, 1),
                "phase_transitions": len(transitions),
                "short_deals": extra.get("v10_short_deals_completed", 0),
                "short_pnl": round(extra.get("v10_short_pnl", 0), 2),
                "short_funding": round(extra.get("v10_short_funding", 0), 2),
                "interim_sells": extra.get("v10_interim_sells", 0),
                "interim_buys": extra.get("v10_interim_buys", 0),
                "realized_pnl": round(extra.get("v10_realized_pnl", 0), 2),
                "transitions_detail": [{"ts": t.get("ts",""), "from": t.get("from",""), "to": t.get("to","")} for t in transitions[:10]],
            }
            
            results.append(entry)
            out_file.write_text(json.dumps(results, indent=2))
            
            print(f"    → PnL: {entry['pnl_pct']:+.2f}%, DD: {entry['max_dd']:.1f}%, "
                  f"Deals: {entry['deals']}, Shorts: {entry['short_deals']}, "
                  f"ShortPnL: ${entry['short_pnl']}, Trans: {entry['phase_transitions']}")
            if transitions:
                for t in transitions[:5]:
                    print(f"       {t.get('ts','')} {t.get('from','')} → {t.get('to','')}")
            
        except Exception as e:
            print(f"    → ERROR: {e}")
            import traceback
            traceback.print_exc()
    
    # Summary
    print(f"\n{'='*80}")
    print(f"  SWEEP COMPLETE — {len(results)} results")
    print(f"{'='*80}")
    results_sorted = sorted(results, key=lambda r: r["pnl_pct"], reverse=True)
    print(f"\n  {'dist':>5} {'md':>5} {'PnL%':>8} {'DD%':>6} {'Deals':>6} {'Shorts':>7} {'Trans':>6}")
    print(f"  {'-'*5} {'-'*5} {'-'*8} {'-'*6} {'-'*6} {'-'*7} {'-'*6}")
    for r in results_sorted:
        print(f"  {r['dist_threshold']:>5} {r['markdown_dist_threshold']:>5} "
              f"{r['pnl_pct']:>+7.2f}% {r['max_dd']:>5.1f}% {r['deals']:>6} "
              f"{r['short_deals']:>7} {r['phase_transitions']:>6}")


if __name__ == "__main__":
    main()
