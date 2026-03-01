#!/usr/bin/env python3
"""V11 TA hybrid test: TA scorer integrated with distribution scorer."""
import sys, json, logging
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from trading.spot.run_v11_chained import run_chained, PRESETS, RESULTS_DIR, DEFAULT_V11_PARAMS
from trading.spot.macro_indicators import load_historical_fear_greed

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

# Create v11_hybrid results directory
HYBRID_RESULTS_DIR = RESULTS_DIR / "v11_hybrid"
HYBRID_RESULTS_DIR.mkdir(parents=True, exist_ok=True)

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
            "total_return_pct": round(result.total_return_pct, 2),
            "max_drawdown_pct": round(result.max_drawdown_pct, 2),
            "final_equity": round(result.final_equity, 2),
            "total_deals_completed": result.total_deals_completed,
            "win_rate": round(result.win_rate, 1),
            "sharpe_ratio": round(result.sharpe_ratio, 2),
            "short_pnl": round(result.extra.get("v11_short_pnl", 0), 2),
            "short_funding": round(result.extra.get("v11_short_funding", 0), 2),
            "short_deals_completed": result.extra.get("v11_short_deals_completed", 0),
            "force_exits": result.extra.get("v9_force_exits", 0),
            "fast_invalidations": result.extra.get("v11_fast_invalidations", 0),
            "mcap_gated": result.extra.get("v11_shorts_gated_by_mcap", 0),
            "chunks": chunks,
        }
        
        outf = HYBRID_RESULTS_DIR / f"ta_{name}.json"
        json.dump(out, open(outf, "w"), indent=2)
        
        print(f"\n  RESULT: PnL={out['total_return_pct']}% DD={out['max_drawdown_pct']}% "
              f"shorts={out['short_deals_completed']} short_pnl=${out['short_pnl']} "
              f"force_exits={out['force_exits']} invalidations={out['fast_invalidations']} "
              f"mcap_gated={out['mcap_gated']}")
        return out
    return None

# TA Hybrid configs: TA scorer integrated (already done in _McapGatedScorer)
# TA scorer hits 72 at real tops, so we test thresholds of 50 and 60
configs = [
    ("ta50_mcap25", {
        "dist_exit_threshold_1h": 50,  # TA scorer hits 72 at tops
        "use_mcap_gating": True,
        "mcap_ath_pct": 0.25,  # within 25% of mcap ATH
        "structural_exit": False,
    }),
    ("ta60_mcap25", {
        "dist_exit_threshold_1h": 60,  # higher bar
        "use_mcap_gating": True, 
        "mcap_ath_pct": 0.25,  # within 25% of mcap ATH
        "structural_exit": False,
    }),
]

results = []
for name, overrides in configs:
    r = run_config(name, overrides)
    if r:
        results.append(r)

print(f"\n\n{'='*80}")
print("TA HYBRID COMPARISON TABLE")
print(f"{'='*80}")
print(f"{'Config':15s} {'PnL%':>8} {'MaxDD':>8} {'Short Deals':>12} {'Short PnL':>10} {'Force Exits':>12}")
print("-" * 80)
for r in results:
    print(f"{r['config']:15s} {r['total_return_pct']:>7.1f}% {r['max_drawdown_pct']:>7.1f}% {r['short_deals_completed']:>12} "
          f"${r['short_pnl']:>9.0f} {r['force_exits']:>12}")

print(f"\nBaselines: V8=+23.06%, V11 DCA-only=+41.57%")
print(f"TA scorer threshold: hits ~72 at real tops")