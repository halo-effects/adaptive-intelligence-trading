#!/usr/bin/env python3
"""Quick V7 sweep — just NEAR catastrophic and AVAX, reduced combos."""
import sys, json, logging, time
from pathlib import Path
from datetime import datetime, timezone

import ccxt, pandas as pd, numpy as np

if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from trading.spot.backtest_engine_v7 import SpotBacktestEngineV7
from trading.spot.macro_indicators import load_historical_fear_greed

logging.basicConfig(level=logging.WARNING, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

CACHE_DIR = Path(__file__).resolve().parent / "data" / "dwell_cache"
RESULTS_DIR = Path(__file__).resolve().parent / "backtest_results" / "v7_sweep"


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


def run_one(coin, start, end, fg, params):
    df = get_candles(coin, "15m", start, end)
    if len(df) < 150: return None
    engine = SpotBacktestEngineV7(
        dwell_profile="aggressive", profile="medium", capital=10000,
        exchange="binance", symbol=coin, timeframe="15m",
        variant="regime_adaptive", compounding=True, conviction_mode=True,
        fear_greed_history=fg, **params)
    result = engine.run(df)
    tl = engine.get_candle_timeline()
    springs = int(tl["spring_bypass"].sum()) if not tl.empty and "spring_bypass" in tl.columns else 0
    return {
        "pnl_pct": round(result.total_return_pct, 2),
        "max_dd": round(result.max_drawdown_pct, 2),
        "total_deals": result.total_deals_completed,
        "sharpe": round(result.sharpe_ratio, 2),
        "win_rate": round(result.win_rate, 1),
        "spring_entries": springs,
        "final_equity": round(result.final_equity, 2),
    }


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--group", type=int, default=0, help="0=NEAR, 1=AVAX")
    args = parser.parse_args()

    fg = load_historical_fear_greed()
    print(f"Loaded {len(fg)} F&G entries")

    groups = [
        {
            "label": "NEAR catastrophic",
            "coin": "NEAR/USDT", "start": "2025-10-01", "end": "2026-02-19",
            "sweeps": [
                {"spring_score_threshold": t, "spring_bypass_conviction": b,
                 "trend_gate_adx": a, "trend_gate_conviction": c}
                for t in [30, 50, 70]
                for b in [True, False]
                for a in [20, 30]
                for c in [40, 60]
            ]
        },
        {
            "label": "AVAX spring+trend",
            "coin": "AVAX/USDT", "start": "2024-07-01", "end": "2025-04-30",
            "sweeps": [
                {"spring_score_threshold": t, "spring_bypass_conviction": b,
                 "trend_gate_adx": a, "trend_gate_conviction": c}
                for t in [30, 50, 70]
                for b in [True, False]
                for a in [20, 30]
                for c in [40, 60]
            ]
        },
    ]

    g = groups[args.group]
    print(f"\n{'='*80}")
    print(f"  {g['label']}: {g['coin']} {g['start']} -> {g['end']}")
    print(f"  {len(g['sweeps'])} combos")
    print(f"{'='*80}")

    results = []
    for i, params in enumerate(g["sweeps"], 1):
        ps = " ".join(f"{k}={v}" for k,v in params.items())
        print(f"  [{i}/{len(g['sweeps'])}] {ps} ... ", end="", flush=True)
        try:
            r = run_one(g["coin"], g["start"], g["end"], fg, params)
            if r:
                print(f"PnL={r['pnl_pct']:+.2f}% DD={r['max_dd']:.2f}% Deals={r['total_deals']} Springs={r['spring_entries']}")
                results.append({**params, **r})
            else:
                print("SKIP (insufficient data)")
        except Exception as e:
            print(f"ERROR: {e}")
            results.append({**params, "error": str(e)})

        # Incremental save every 4 runs
        if i % 4 == 0:
            RESULTS_DIR.mkdir(parents=True, exist_ok=True)
            with open(RESULTS_DIR / f"quick_{g['label'].replace(' ','_')}.json", "w") as f:
                json.dump(results, f, indent=2, default=str)

    # Final save
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    with open(RESULTS_DIR / f"quick_{g['label'].replace(' ','_')}.json", "w") as f:
        json.dump(results, f, indent=2, default=str)

    # Print summary
    valid = [r for r in results if "error" not in r]
    if valid:
        print(f"\n{'='*80}")
        print(f"RESULTS: {g['label']}")
        print(f"{'='*80}")
        best_pnl = max(valid, key=lambda x: x["pnl_pct"])
        worst_pnl = min(valid, key=lambda x: x["pnl_pct"])
        best_dd = min(valid, key=lambda x: x["max_dd"])
        print(f"Best PnL:  {best_pnl['pnl_pct']:+.2f}% | spr_thresh={best_pnl['spring_score_threshold']} bypass={best_pnl['spring_bypass_conviction']} adx={best_pnl['trend_gate_adx']} conv={best_pnl['trend_gate_conviction']}")
        print(f"Worst PnL: {worst_pnl['pnl_pct']:+.2f}% | spr_thresh={worst_pnl['spring_score_threshold']} bypass={worst_pnl['spring_bypass_conviction']} adx={worst_pnl['trend_gate_adx']} conv={worst_pnl['trend_gate_conviction']}")
        print(f"Best DD:   {best_dd['max_dd']:.2f}% | spr_thresh={best_dd['spring_score_threshold']} bypass={best_dd['spring_bypass_conviction']} adx={best_dd['trend_gate_adx']} conv={best_dd['trend_gate_conviction']}")
        print(f"\nAll results:")
        for r in sorted(valid, key=lambda x: -x["pnl_pct"]):
            print(f"  spr={r['spring_score_threshold']:>2} bypass={str(r['spring_bypass_conviction']):>5} adx={r['trend_gate_adx']:>2} conv={r['trend_gate_conviction']:>2} | PnL={r['pnl_pct']:+7.2f}% DD={r['max_dd']:6.2f}% Deals={r['total_deals']:>3} Springs={r['spring_entries']:>5}")


if __name__ == "__main__":
    main()
