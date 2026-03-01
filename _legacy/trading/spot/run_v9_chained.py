#!/usr/bin/env python3
"""V9 Chained Backtest — Distribution Exit + Short Profit Model.

Runs V9 (V8 + distribution exit overlay) across multi-chunk periods.
Compares against V8 baseline to measure improvement from top detection.
"""
import sys, json, logging, time, argparse
from pathlib import Path
from datetime import datetime, timezone, timedelta

import ccxt, pandas as pd, numpy as np

if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from trading.spot.backtest_engine_v9 import SpotBacktestEngineV9
from trading.spot.macro_indicators import load_historical_fear_greed

logging.basicConfig(level=logging.WARNING, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

CACHE_DIR = Path(__file__).resolve().parent / "data" / "dwell_cache"
RESULTS_DIR = Path(__file__).resolve().parent / "backtest_results" / "v9_distribution"

CHUNK_DAYS = 120
OVERLAP_DAYS = 8


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
        df = pd.read_csv(cp)
        logger.info("  Cached: %s (%d candles)", cp.name, len(df))
        return df
    logger.info("  Fetching: %s %s %s->%s ...", symbol, tf, start, end)
    df = fetch_ohlcv(symbol, tf, start, end)
    if not df.empty:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        df.to_csv(cp, index=False)
        logger.info("  Fetched %d candles", len(df))
    return df


def split_into_chunks(start_str, end_str):
    start = datetime.strptime(start_str, "%Y-%m-%d")
    end = datetime.strptime(end_str, "%Y-%m-%d")
    chunks = []
    cursor = start
    while cursor < end:
        chunk_end = min(cursor + timedelta(days=CHUNK_DAYS), end)
        fetch_start = cursor - timedelta(days=OVERLAP_DAYS) if cursor > start else cursor
        chunks.append({
            "fetch_start": fetch_start.strftime("%Y-%m-%d"),
            "fetch_end": chunk_end.strftime("%Y-%m-%d"),
            "trade_start": cursor.strftime("%Y-%m-%d"),
            "trade_end": chunk_end.strftime("%Y-%m-%d"),
            "is_first": cursor == start,
            "is_last": chunk_end >= end,
        })
        cursor = chunk_end
    return chunks


def run_chained(symbol, timeframe, start, end, capital, fg, v9_params, profile="medium"):
    chunks = split_into_chunks(start, end)
    logger.info("Split into %d chunks of ~%d days", len(chunks), CHUNK_DAYS)

    state = None
    chunk_summaries = []

    for ci, chunk in enumerate(chunks):
        logger.info("\n-- Chunk %d/%d: %s -> %s --", ci+1, len(chunks),
                     chunk["trade_start"], chunk["trade_end"])

        df = get_candles(symbol, timeframe, chunk["fetch_start"], chunk["fetch_end"])
        if len(df) < 150:
            logger.warning("  Skipping chunk (only %d candles)", len(df))
            continue

        engine = SpotBacktestEngineV9(
            dwell_profile="aggressive", profile=profile, capital=capital,
            exchange="binance", symbol=symbol, timeframe=timeframe,
            variant="regime_adaptive", compounding=True, conviction_mode=True,
            fear_greed_history=fg,
            # V7 defaults
            dwell_conviction_floor=30,
            spring_bypass_conviction=True,
            trend_gate_adx=25,
            trend_gate_conviction=50,
            # V8 defaults
            spring_reserve_pct=0.25,
            spring_score_threshold=60,
            spring_tp_mult=5.0,
            spring_size_mult=3.0,
            spring_max_entries=5,
            phase1_dd_max=15.0,
            phase2_dd_max=30.0,
            # V9 params
            **v9_params,
        )

        if state is not None:
            engine.restore_state(state)
            logger.info("  Restored state: cash=$%.0f, %d open deals, %d completed",
                         engine.cash, len(engine.deals), len(engine.completed_deals))

        if chunk["is_last"]:
            result = engine.run(df)
            chunk_summaries.append({
                "chunk": ci+1,
                "period": f"{chunk['trade_start']}->{chunk['trade_end']}",
                "candles": len(df),
                "final_equity": round(result.final_equity, 2),
                "deals_completed": result.total_deals_completed,
            })
            return result, chunk_summaries
        else:
            partial, state = engine.run_no_close(df)
            chunk_summaries.append({
                "chunk": ci+1,
                "period": f"{chunk['trade_start']}->{chunk['trade_end']}",
                "candles": len(df),
                **partial,
            })
            logger.info("  Chunk done: eq=$%.0f, cash=$%.0f, %d open, %d completed",
                         partial["final_equity"], partial["cash"],
                         partial["open_deals"], partial["completed_deals"])

    return None, chunk_summaries


PRESETS = {
    "eth_full": {
        "label": "ETH Full Wyckoff Cycle",
        "symbol": "ETH/USDT",
        "start": "2022-06-01",
        "end": "2025-02-19",
        "capital": 10000,
    },
    "near_full": {
        "label": "NEAR Extended",
        "symbol": "NEAR/USDT",
        "start": "2025-02-01",
        "end": "2026-02-19",
        "capital": 10000,
    },
}

# V9 params to sweep (distribution thresholds)
DEFAULT_V9_PARAMS = {
    "dist_tighten_threshold": 30,
    "dist_winddown_threshold": 45,
    "dist_exit_threshold": 60,
    "dist_reentry_threshold": 20,
    "dist_cooldown_candles": 96,
    "dist_short_profit_per_5pct": 0.02,
}

SWEEP_PARAMS = [
    # Aggressive exit (triggers earlier)
    {"dist_tighten_threshold": 25, "dist_winddown_threshold": 40, "dist_exit_threshold": 55,
     "dist_reentry_threshold": 15, "dist_cooldown_candles": 96, "dist_short_profit_per_5pct": 0.02},
    # Default (calibrated for 90pt max)
    {"dist_tighten_threshold": 30, "dist_winddown_threshold": 45, "dist_exit_threshold": 60,
     "dist_reentry_threshold": 20, "dist_cooldown_candles": 96, "dist_short_profit_per_5pct": 0.02},
    # Conservative
    {"dist_tighten_threshold": 35, "dist_winddown_threshold": 55, "dist_exit_threshold": 70,
     "dist_reentry_threshold": 25, "dist_cooldown_candles": 48, "dist_short_profit_per_5pct": 0.02},
    # Higher short profits (2× leverage equivalent)
    {"dist_tighten_threshold": 30, "dist_winddown_threshold": 45, "dist_exit_threshold": 60,
     "dist_reentry_threshold": 20, "dist_cooldown_candles": 96, "dist_short_profit_per_5pct": 0.03},
    # No short profits (pure capital preservation test)
    {"dist_tighten_threshold": 30, "dist_winddown_threshold": 45, "dist_exit_threshold": 60,
     "dist_reentry_threshold": 20, "dist_cooldown_candles": 96, "dist_short_profit_per_5pct": 0.0},
]


def main():
    parser = argparse.ArgumentParser(description="V9 Chained Backtest")
    parser.add_argument("--preset", choices=list(PRESETS.keys()), default="eth_full")
    parser.add_argument("--sweep", action="store_true")
    parser.add_argument("--profile", default="medium")
    parser.add_argument("--skip", type=int, default=0)
    args = parser.parse_args()

    preset = PRESETS[args.preset]
    fg = load_historical_fear_greed()
    print(f"Loaded {len(fg)} F&G entries")

    sweep = SWEEP_PARAMS if args.sweep else [DEFAULT_V9_PARAMS]
    out_file = RESULTS_DIR / f"{args.preset}{'_sweep' if args.sweep else ''}.json"
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    print(f"\n{'='*80}")
    print(f"  V9 DISTRIBUTION EXIT BACKTEST: {preset['label']}")
    print(f"  {preset['symbol']} | {preset['start']} -> {preset['end']} | ${preset['capital']:,.0f}")
    print(f"  {len(sweep)} param set(s) | profile={args.profile}")
    print(f"  Output: {out_file}")
    print(f"{'='*80}\n")

    all_results = []

    for si, v9_params in enumerate(sweep):
        if si < args.skip:
            continue

        ps = " ".join(f"{k.replace('dist_','')}={v}" for k, v in v9_params.items())
        print(f"\n[{si+1}/{len(sweep)}] {ps}")
        print("-" * 60)

        try:
            result, chunk_info = run_chained(
                preset["symbol"], "15m", preset["start"], preset["end"],
                preset["capital"], fg, v9_params, profile=args.profile
            )

            if result:
                extra = result.extra if hasattr(result, 'extra') and result.extra else {}
                entry = {
                    "profile": args.profile,
                    "params": v9_params,
                    "pnl_pct": round(result.total_return_pct, 2),
                    "max_dd": round(result.max_drawdown_pct, 2),
                    "final_equity": round(result.final_equity, 2),
                    "total_deals": result.total_deals_completed,
                    "win_rate": round(result.win_rate, 1),
                    "sharpe": round(result.sharpe_ratio, 2),
                    "spring_buys": extra.get("spring_buys", 0),
                    "chunks": chunk_info,
                }
                all_results.append(entry)

                print(f"\n  {'='*60}")
                print(f"  RESULT: PnL={result.total_return_pct:+.2f}% | DD={result.max_drawdown_pct:.1f}% | "
                      f"Deals={result.total_deals_completed} | Win={result.win_rate:.0f}% | "
                      f"Sharpe={result.sharpe_ratio:.2f}")
                print(f"  Final equity: ${result.final_equity:,.2f}")
                print(f"  {'='*60}")
            else:
                all_results.append({"params": v9_params, "error": "no result"})

        except Exception as e:
            import traceback
            traceback.print_exc()
            all_results.append({"params": v9_params, "error": str(e)})
            print(f"  ERROR: {e}")

        # Save after each run
        with open(out_file, "w") as f:
            json.dump(all_results, f, indent=2, default=str)

    # Summary
    valid = [r for r in all_results if "error" not in r]
    if valid:
        print(f"\n{'='*80}")
        print(f"  V9 SUMMARY: {preset['label']} ({len(valid)} runs)")
        print(f"  V8 baseline: +23.06%")
        print(f"{'='*80}")
        for r in sorted(valid, key=lambda x: -x["pnl_pct"]):
            p = r["params"]
            print(f"  exit={p['dist_exit_threshold']:>2} short={p['dist_short_profit_per_5pct']:.2f} | "
                  f"PnL={r['pnl_pct']:+8.2f}% DD={r['max_dd']:5.1f}% "
                  f"Deals={r['total_deals']:>3} Win={r['win_rate']:.0f}%")

    print(f"\nDone. Results: {out_file}")


if __name__ == "__main__":
    main()
