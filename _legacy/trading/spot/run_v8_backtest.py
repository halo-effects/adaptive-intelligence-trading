#!/usr/bin/env python3
"""V8 backtest runner — Spring-Only mode on catastrophic datasets.

Tests the key V8 hypothesis: freezing SOs in Phase 2 preserves capital
for Phase 3 spring buys, dramatically improving drawdown recovery.

Sweeps: spring_reserve_pct, spring_score_threshold, spring_tp_mult, phase2_dd_max
"""
import sys, json, logging, time
from pathlib import Path
from datetime import datetime, timezone

import ccxt, pandas as pd, numpy as np

if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from trading.spot.backtest_engine_v8 import SpotBacktestEngineV8
from trading.spot.macro_indicators import load_historical_fear_greed

logging.basicConfig(level=logging.WARNING, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

CACHE_DIR = Path(__file__).resolve().parent / "data" / "dwell_cache"
RESULTS_DIR = Path(__file__).resolve().parent / "backtest_results" / "v8_spring_only"


def cache_path(symbol, tf, start, end):
    return CACHE_DIR / f"{symbol.replace('/', '_')}_{tf}_{start}_{end}.csv"


def fetch_ohlcv(symbol, timeframe, start, end):
    exchange = ccxt.binance({"enableRateLimit": True})
    since_ms = int(datetime.strptime(start, "%Y-%m-%d").replace(tzinfo=timezone.utc).timestamp() * 1000)
    end_ms = int(datetime.strptime(end, "%Y-%m-%d").replace(tzinfo=timezone.utc).timestamp() * 1000)
    all_c = []
    cursor = since_ms
    while cursor < end_ms:
        try:
            candles = exchange.fetch_ohlcv(symbol, timeframe, since=cursor, limit=1000)
        except Exception:
            time.sleep(5); continue
        if not candles: break
        all_c.extend(candles)
        cursor = candles[-1][0] + 1
        time.sleep(0.3)
    if not all_c: return pd.DataFrame()
    df = pd.DataFrame(all_c, columns=["timestamp","open","high","low","close","volume"])
    return df[df["timestamp"] <= end_ms].drop_duplicates(subset=["timestamp"]).reset_index(drop=True)


def get_candles(symbol, tf, start, end):
    cp = cache_path(symbol, tf, start, end)
    if cp.exists():
        return pd.read_csv(cp)
    df = fetch_ohlcv(symbol, tf, start, end)
    if not df.empty:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        df.to_csv(cp, index=False)
    return df


def run_one(coin, start, end, fg, v8_params):
    df = get_candles(coin, "15m", start, end)
    if len(df) < 150:
        return None

    engine = SpotBacktestEngineV8(
        dwell_profile="aggressive", profile="medium", capital=10000,
        exchange="binance", symbol=coin, timeframe="15m",
        variant="regime_adaptive", compounding=True, conviction_mode=True,
        fear_greed_history=fg,
        # V7 defaults (keep consistent with prior runs)
        dwell_conviction_floor=30,
        spring_bypass_conviction=True,
        trend_gate_adx=25,
        trend_gate_conviction=50,
        # V8 params
        **v8_params,
    )
    result = engine.run(df)
    tl = engine.get_candle_timeline()

    # Extract spring metrics from timeline
    springs_placed = 0
    phase_candles = {1: 0, 2: 0, 3: 0}
    if not tl.empty:
        for _, r in tl.iterrows():
            p = int(r.get("dd_phase", 1))
            phase_candles[p] = phase_candles.get(p, 0) + 1
        if "spring_entries" in tl.columns:
            springs_placed = int(tl["spring_entries"].max())

    extra = result.extra if hasattr(result, 'extra') and result.extra else {}

    return {
        "pnl_pct": round(result.total_return_pct, 2),
        "max_dd": round(result.max_drawdown_pct, 2),
        "total_deals": result.total_deals_completed,
        "sharpe": round(result.sharpe_ratio, 2),
        "win_rate": round(result.win_rate, 1),
        "spring_buys": extra.get("spring_buys", springs_placed),
        "phase_candles": extra.get("phase_candles", phase_candles),
        "cash_at_phase2": round(extra.get("cash_at_phase2", 0), 2),
        "cash_at_phase3": round(extra.get("cash_at_phase3", 0), 2),
        "final_equity": round(result.final_equity, 2),
    }


# ── Datasets ──────────────────────────────────────────────────────────

DATASETS = [
    # Catastrophic (where V5-V7 all failed)
    {"label": "NEAR_catastrophic", "coin": "NEAR/USDT",
     "start": "2025-10-01", "end": "2026-02-19"},
    {"label": "AVAX_decline", "coin": "AVAX/USDT",
     "start": "2024-07-01", "end": "2025-02-28"},
    # Also test on winners to make sure V8 doesn't regress
    {"label": "AAVE_bull", "coin": "AAVE/USDT",
     "start": "2023-07-01", "end": "2024-11-30"},
    {"label": "SOL_recovery", "coin": "SOL/USDT",
     "start": "2023-01-01", "end": "2023-12-31"},
]

# Split long datasets to avoid OOM
def split_dataset(ds):
    """Split into sub-periods if > ~4 months."""
    start = datetime.strptime(ds["start"], "%Y-%m-%d")
    end = datetime.strptime(ds["end"], "%Y-%m-%d")
    days = (end - start).days
    if days <= 140:  # ~4.5 months, safe for 15m
        return [ds]
    # Split into 2
    mid = start + (end - start) / 2
    return [
        {**ds, "label": ds["label"] + "_p1", "end": mid.strftime("%Y-%m-%d")},
        {**ds, "label": ds["label"] + "_p2", "start": mid.strftime("%Y-%m-%d")},
    ]


# ── Parameter sweep ───────────────────────────────────────────────────

SWEEP_PARAMS = []
for reserve in [0.15, 0.25, 0.35]:
    for spring_thresh in [50, 65, 80]:
        for tp_mult in [3.0, 5.0, 8.0]:
            SWEEP_PARAMS.append({
                "spring_reserve_pct": reserve,
                "spring_score_threshold": spring_thresh,
                "spring_tp_mult": tp_mult,
                "spring_size_mult": 3.0,
                "spring_max_entries": 5,
                "phase1_dd_max": 15.0,
                "phase2_dd_max": 30.0,
            })

# Focused: also test varying phase thresholds on NEAR
PHASE_SWEEP = []
for p1 in [10.0, 15.0, 20.0]:
    for p2 in [25.0, 30.0, 40.0]:
        if p1 >= p2:
            continue
        PHASE_SWEEP.append({
            "phase1_dd_max": p1,
            "phase2_dd_max": p2,
            "spring_reserve_pct": 0.25,
            "spring_score_threshold": 60,
            "spring_tp_mult": 5.0,
            "spring_size_mult": 3.0,
            "spring_max_entries": 5,
        })


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", type=int, default=0,
                        help="0=NEAR, 1=AVAX, 2=AAVE, 3=SOL")
    parser.add_argument("--phase-sweep", action="store_true",
                        help="Run phase threshold sweep instead of main sweep")
    parser.add_argument("--skip", type=int, default=0, help="Skip N runs (resume)")
    args = parser.parse_args()

    fg = load_historical_fear_greed()
    print(f"Loaded {len(fg)} F&G entries")

    ds = DATASETS[args.dataset]
    sub_periods = split_dataset(ds)
    sweep = PHASE_SWEEP if args.phase_sweep else SWEEP_PARAMS

    suffix = "_phase" if args.phase_sweep else ""
    out_file = RESULTS_DIR / f"{ds['label']}{suffix}.json"

    print(f"\n{'='*80}")
    print(f"  V8 SPRING-ONLY BACKTEST: {ds['label']}")
    print(f"  {ds['coin']} | {len(sub_periods)} period(s) | {len(sweep)} param combos")
    print(f"  Output: {out_file}")
    print(f"{'='*80}\n")

    results = []
    run_idx = 0

    for params in sweep:
        for period in sub_periods:
            run_idx += 1
            if run_idx <= args.skip:
                continue

            ps = " ".join(f"{k}={v}" for k, v in params.items() if k != "spring_max_entries")
            print(f"  [{run_idx}/{len(sweep)*len(sub_periods)}] {period['label']} | {ps} ... ",
                  end="", flush=True)

            try:
                r = run_one(period["coin"], period["start"], period["end"], fg, params)
                if r:
                    print(f"PnL={r['pnl_pct']:+.2f}% DD={r['max_dd']:.1f}% Springs={r['spring_buys']} "
                          f"Cash@P2=${r['cash_at_phase2']:.0f} Cash@P3=${r['cash_at_phase3']:.0f}")
                    results.append({"period": period["label"], **params, **r})
                else:
                    print("SKIP (insufficient data)")
            except Exception as e:
                print(f"ERROR: {e}")
                import traceback; traceback.print_exc()
                results.append({"period": period["label"], **params, "error": str(e)})

            # Save every run (OOM crashes lose unsaved results)
            if True:
                RESULTS_DIR.mkdir(parents=True, exist_ok=True)
                with open(out_file, "w") as f:
                    json.dump(results, f, indent=2, default=str)

    # Final save
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    with open(out_file, "w") as f:
        json.dump(results, f, indent=2, default=str)

    # Summary
    valid = [r for r in results if "error" not in r]
    if valid:
        print(f"\n{'='*80}")
        print(f"  V8 RESULTS: {ds['label']} ({len(valid)} runs)")
        print(f"{'='*80}")
        best = max(valid, key=lambda x: x["pnl_pct"])
        worst = min(valid, key=lambda x: x["pnl_pct"])
        avg_pnl = sum(r["pnl_pct"] for r in valid) / len(valid)
        avg_springs = sum(r["spring_buys"] for r in valid) / len(valid)
        print(f"  Avg PnL: {avg_pnl:+.2f}%  Avg Springs: {avg_springs:.1f}")
        print(f"  Best:  {best['pnl_pct']:+.2f}% (reserve={best['spring_reserve_pct']}, "
              f"thresh={best['spring_score_threshold']}, tp_mult={best['spring_tp_mult']})")
        print(f"  Worst: {worst['pnl_pct']:+.2f}% (reserve={worst['spring_reserve_pct']}, "
              f"thresh={worst['spring_score_threshold']}, tp_mult={worst['spring_tp_mult']})")
        print(f"\n  Top 5:")
        for r in sorted(valid, key=lambda x: -x["pnl_pct"])[:5]:
            print(f"    {r['period']:>20s} rsv={r['spring_reserve_pct']:.2f} thresh={r['spring_score_threshold']:>2} "
                  f"tp={r['spring_tp_mult']:.0f}× | PnL={r['pnl_pct']:+7.2f}% DD={r['max_dd']:5.1f}% "
                  f"Springs={r['spring_buys']} Cash@P3=${r['cash_at_phase3']:.0f}")

    print(f"\nDone. Results saved to {out_file}")


if __name__ == "__main__":
    main()
