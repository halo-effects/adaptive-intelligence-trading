#!/usr/bin/env python3
"""V11 short test: mcap ATH gating controls when EXIT fires."""
import sys, json, logging
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from trading.spot.run_v11_chained import run_chained, PRESETS, RESULTS_DIR, DEFAULT_V11_PARAMS
from trading.spot.macro_indicators import load_historical_fear_greed

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

RESULTS_DIR.mkdir(parents=True, exist_ok=True)

def run_config(name, params_override):
    preset = PRESETS["eth"]
    fg = load_historical_fear_greed()
    params = {**DEFAULT_V11_PARAMS, **params_override}
    
    print(f"\n{'='*60}")
    print(f"  CONFIG: {name}")
    for k, v in params_override.items():
        print(f"  {k}={v}")
    print(f"{'='*60}")
    
    result, chunks = run_chained(
        preset["symbol"], "1h", preset["start"], preset["end"],
        preset["capital"], fg, params, profile="medium", exchange="aster"
    )
    
    if result:
        out = {
            "config": name,
            "params": params,
            "pnl_pct": round(result.total_return_pct, 2),
            "max_dd": round(result.max_drawdown_pct, 2),
            "final_equity": round(result.final_equity, 2),
            "total_deals": result.total_deals_completed,
            "win_rate": round(result.win_rate, 1),
            "sharpe": round(result.sharpe_ratio, 2),
            "short_pnl": round(result.extra.get("v11_short_pnl", 0), 2),
            "short_funding": round(result.extra.get("v11_short_funding", 0), 2),
            "short_deals": result.extra.get("v11_short_deals_completed", 0),
            "force_exits": result.extra.get("v9_force_exits", 0),
            "fast_invalidations": result.extra.get("v11_fast_invalidations", 0),
            "mcap_gated": result.extra.get("v11_shorts_gated_by_mcap", 0),
            "chunks": chunks,
        }
        
        outf = RESULTS_DIR / f"sweep_{name}.json"
        json.dump(out, open(outf, "w"), indent=2)
        
        print(f"\n  RESULT: PnL={out['pnl_pct']}% DD={out['max_dd']}% "
              f"shorts={out['short_deals']} short_pnl=${out['short_pnl']} "
              f"force_exits={out['force_exits']} invalidations={out['fast_invalidations']} "
              f"mcap_gated={out['mcap_gated']}")
        return out
    return None

# Key test: dist_exit_threshold_1h=20 with mcap gating
# V9's exit_threshold stays at 100 (unreachable). McapGatedScorer
# checks: score >= 20 AND near mcap ATH → override to EXIT
configs = [
    ("mcap20", {
        "dist_exit_threshold_1h": 20,
        "use_mcap_gating": True,
        "mcap_ath_pct": 0.20,  # within 20% of mcap ATH
        "structural_exit": False,
    }),
    ("mcap20_tight", {
        "dist_exit_threshold_1h": 20,
        "use_mcap_gating": True,
        "mcap_ath_pct": 0.15,  # within 15% — tighter
        "structural_exit": False,
    }),
    ("mcap25", {
        "dist_exit_threshold_1h": 25,
        "use_mcap_gating": True,
        "mcap_ath_pct": 0.20,
        "structural_exit": False,
    }),
]

results = []
for name, overrides in configs:
    r = run_config(name, overrides)
    if r:
        results.append(r)

print(f"\n\n{'='*80}")
print("COMPARISON TABLE")
print(f"{'='*80}")
print(f"{'Config':20s} {'PnL%':>8} {'MaxDD':>8} {'Shorts':>7} {'ShortPnL':>10} {'ForceEx':>8} {'Inval':>6} {'Gated':>6}")
print("-" * 80)
for r in results:
    print(f"{r['config']:20s} {r['pnl_pct']:>7.1f}% {r['max_dd']:>7.1f}% {r['short_deals']:>7} "
          f"${r['short_pnl']:>9.0f} {r['force_exits']:>8} {r['fast_invalidations']:>6} {r['mcap_gated']:>6}")
print(f"\nBaselines: V8=+23.06%, V11 no-shorts=+41.57%")
