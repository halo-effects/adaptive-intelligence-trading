#!/usr/bin/env python3
"""V8 Chained Backtest — Full Wyckoff cycle test with state carry-forward.

Splits long date ranges into ~4-month chunks, runs each sequentially,
carries positions/cash/state across chunk boundaries (no force-close between).
Only force-closes at the very end.

This solves the OOM problem (30K candle limit) while giving accurate multi-year results.
"""
import sys, json, logging, time, argparse
from pathlib import Path
from datetime import datetime, timezone, timedelta

import ccxt, pandas as pd, numpy as np

if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from trading.spot.backtest_engine_v8 import SpotBacktestEngineV8
from trading.spot.macro_indicators import load_historical_fear_greed

logging.basicConfig(level=logging.WARNING, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

CACHE_DIR = Path(__file__).resolve().parent / "data" / "dwell_cache"
RESULTS_DIR = Path(__file__).resolve().parent / "backtest_results" / "v8_chained"

CHUNK_DAYS = 120  # ~4 months per chunk
OVERLAP_DAYS = 8  # Overlap for indicator warm-up (100 candles @ 15m ≈ 1 day)


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
    logger.info("  Fetching: %s %s %s→%s ...", symbol, tf, start, end)
    df = fetch_ohlcv(symbol, tf, start, end)
    if not df.empty:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        df.to_csv(cp, index=False)
        logger.info("  Fetched %d candles", len(df))
    return df


def split_into_chunks(start_str, end_str):
    """Split date range into overlapping chunks for indicator warm-up."""
    start = datetime.strptime(start_str, "%Y-%m-%d")
    end = datetime.strptime(end_str, "%Y-%m-%d")
    chunks = []
    cursor = start
    while cursor < end:
        chunk_end = min(cursor + timedelta(days=CHUNK_DAYS), end)
        # Data fetch start: pull extra days before for indicator warm-up
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


def run_chained(symbol, timeframe, start, end, capital, fg, v8_params, profile="medium"):
    """Run V8 across multiple chunks with state carry-forward."""
    chunks = split_into_chunks(start, end)
    logger.info("Split into %d chunks of ~%d days", len(chunks), CHUNK_DAYS)

    state = None
    all_equity = []
    chunk_summaries = []

    for ci, chunk in enumerate(chunks):
        logger.info("\n── Chunk %d/%d: %s → %s ──", ci+1, len(chunks),
                     chunk["trade_start"], chunk["trade_end"])

        df = get_candles(symbol, timeframe, chunk["fetch_start"], chunk["fetch_end"])
        if len(df) < 150:
            logger.warning("  Skipping chunk (only %d candles)", len(df))
            continue

        # Create fresh engine with same params
        engine = SpotBacktestEngineV8(
            dwell_profile="aggressive", profile=profile, capital=capital,
            exchange="binance", symbol=symbol, timeframe=timeframe,
            variant="regime_adaptive", compounding=True, conviction_mode=True,
            fear_greed_history=fg,
            dwell_conviction_floor=30,
            spring_bypass_conviction=True,
            trend_gate_adx=25,
            trend_gate_conviction=50,
            **v8_params,
        )

        # Restore state from previous chunk
        if state is not None:
            engine.restore_state(state)
            logger.info("  Restored state: cash=$%.0f, %d open deals, %d completed",
                         engine.cash, len(engine.deals), len(engine.completed_deals))

        if chunk["is_last"]:
            # Last chunk: run with force-close
            result = engine.run(df)
            # Collect equity snapshots
            all_equity.extend(engine.equity_snapshots)
            chunk_summaries.append({
                "chunk": ci+1,
                "period": f"{chunk['trade_start']}→{chunk['trade_end']}",
                "candles": len(df),
                "final_equity": round(result.final_equity, 2),
                "deals_completed": result.total_deals_completed,
            })
            return result, all_equity, chunk_summaries
        else:
            # Intermediate chunk: run without force-close, carry state
            partial, state = engine.run_no_close(df)
            all_equity.extend(engine.equity_snapshots)
            chunk_summaries.append({
                "chunk": ci+1,
                "period": f"{chunk['trade_start']}→{chunk['trade_end']}",
                "candles": len(df),
                **partial,
            })
            logger.info("  Chunk done: eq=$%.0f, cash=$%.0f, %d open deals, %d completed",
                         partial["final_equity"], partial["cash"],
                         partial["open_deals"], partial["completed_deals"])

    # If we somehow didn't hit the last chunk with is_last, force-close now
    logger.warning("Fell through without final chunk — forcing close")
    return None, all_equity, chunk_summaries


# ── Presets ───────────────────────────────────────────────────────────

PRESETS = {
    "eth_full": {
        "label": "ETH Full Wyckoff Cycle",
        "symbol": "ETH/USDT",
        "start": "2022-06-01",
        "end": "2025-02-19",
        "capital": 10000,
    },
    "sol_full": {
        "label": "SOL Full Cycle",
        "symbol": "SOL/USDT",
        "start": "2022-06-01",
        "end": "2025-02-19",
        "capital": 10000,
    },
    "btc_full": {
        "label": "BTC Full Cycle",
        "symbol": "BTC/USDT",
        "start": "2022-06-01",
        "end": "2025-02-19",
        "capital": 10000,
    },
    "near_full": {
        "label": "NEAR Extended",
        "symbol": "NEAR/USDT",
        "start": "2022-06-01",
        "end": "2026-02-19",
        "capital": 10000,
    },
}

# V8 params to test (can sweep later, start with best guess)
DEFAULT_V8_PARAMS = {
    "spring_reserve_pct": 0.25,
    "spring_score_threshold": 60,
    "spring_tp_mult": 5.0,
    "spring_size_mult": 3.0,
    "spring_max_entries": 5,
    "phase1_dd_max": 15.0,
    "phase2_dd_max": 30.0,
}

# Small sweep for chained runs (fewer combos since each takes longer)
CHAINED_SWEEP = [
    {"spring_reserve_pct": 0.20, "spring_score_threshold": 50, "spring_tp_mult": 5.0,
     "spring_size_mult": 3.0, "spring_max_entries": 5, "phase1_dd_max": 15.0, "phase2_dd_max": 30.0},
    {"spring_reserve_pct": 0.25, "spring_score_threshold": 60, "spring_tp_mult": 5.0,
     "spring_size_mult": 3.0, "spring_max_entries": 5, "phase1_dd_max": 15.0, "phase2_dd_max": 30.0},
    {"spring_reserve_pct": 0.30, "spring_score_threshold": 60, "spring_tp_mult": 8.0,
     "spring_size_mult": 3.0, "spring_max_entries": 5, "phase1_dd_max": 15.0, "phase2_dd_max": 30.0},
    {"spring_reserve_pct": 0.25, "spring_score_threshold": 60, "spring_tp_mult": 5.0,
     "spring_size_mult": 3.0, "spring_max_entries": 5, "phase1_dd_max": 10.0, "phase2_dd_max": 25.0},
    {"spring_reserve_pct": 0.25, "spring_score_threshold": 60, "spring_tp_mult": 5.0,
     "spring_size_mult": 3.0, "spring_max_entries": 5, "phase1_dd_max": 20.0, "phase2_dd_max": 40.0},
]


def main():
    parser = argparse.ArgumentParser(description="V8 Chained Backtest — Full Wyckoff Cycle")
    parser.add_argument("--preset", choices=list(PRESETS.keys()), default="eth_full",
                        help="Preset coin/period")
    parser.add_argument("--symbol", help="Override symbol (e.g. ETH/USDT)")
    parser.add_argument("--start", help="Override start date (YYYY-MM-DD)")
    parser.add_argument("--end", help="Override end date (YYYY-MM-DD)")
    parser.add_argument("--capital", type=float, help="Override capital")
    parser.add_argument("--sweep", action="store_true", help="Run param sweep instead of single")
    parser.add_argument("--profiles", action="store_true",
                        help="Run all 3 risk profiles (low/medium/high) with default V8 params")
    parser.add_argument("--profile", default="medium", help="Risk profile (low/medium/high)")
    parser.add_argument("--skip", type=int, default=0, help="Skip N sweep runs")
    args = parser.parse_args()

    preset = PRESETS[args.preset]
    symbol = args.symbol or preset["symbol"]
    start = args.start or preset["start"]
    end = args.end or preset["end"]
    capital = args.capital or preset["capital"]

    fg = load_historical_fear_greed()
    print(f"Loaded {len(fg)} F&G entries")

    if args.profiles:
        # Run all 3 profiles with default V8 params
        profile_list = ["low", "medium", "high"]
        sweep_params = [DEFAULT_V8_PARAMS] * len(profile_list)
    elif args.sweep:
        profile_list = [args.profile] * len(CHAINED_SWEEP)
        sweep_params = CHAINED_SWEEP
    else:
        profile_list = [args.profile]
        sweep_params = [DEFAULT_V8_PARAMS]

    suffix = "_profiles" if args.profiles else ("_sweep" if args.sweep else "")
    out_file = RESULTS_DIR / f"{args.preset}{suffix}.json"
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    print(f"\n{'='*80}")
    print(f"  V8 CHAINED BACKTEST: {preset['label']}")
    print(f"  {symbol} | {start} → {end} | ${capital:,.0f}")
    print(f"  {len(sweep_params)} param set(s)")
    print(f"  Output: {out_file}")
    print(f"{'='*80}\n")

    all_results = []

    for si, (v8_params, prof) in enumerate(zip(sweep_params, profile_list)):
        if si < args.skip:
            continue

        ps = " ".join(f"{k}={v}" for k, v in v8_params.items()
                      if k not in ("spring_max_entries", "spring_size_mult"))
        print(f"\n[{si+1}/{len(sweep_params)}] profile={prof} {ps}")
        print("-" * 60)

        try:
            result, equity_curve, chunk_info = run_chained(
                symbol, "15m", start, end, capital, fg, v8_params, profile=prof
            )

            if result:
                extra = result.extra if hasattr(result, 'extra') and result.extra else {}
                entry = {
                    "profile": prof,
                    "params": v8_params,
                    "pnl_pct": round(result.total_return_pct, 2),
                    "max_dd": round(result.max_drawdown_pct, 2),
                    "final_equity": round(result.final_equity, 2),
                    "total_deals": result.total_deals_completed,
                    "win_rate": round(result.win_rate, 1),
                    "sharpe": round(result.sharpe_ratio, 2),
                    "spring_buys": extra.get("spring_buys", 0),
                    "phase_candles": extra.get("phase_candles", {}),
                    "chunks": chunk_info,
                }
                all_results.append(entry)

                print(f"\n  ✅ RESULT: PnL={result.total_return_pct:+.2f}% | DD={result.max_drawdown_pct:.1f}% | "
                      f"Deals={result.total_deals_completed} | Win={result.win_rate:.0f}% | "
                      f"Springs={extra.get('spring_buys', 0)} | Sharpe={result.sharpe_ratio:.2f}")
                print(f"     Final equity: ${result.final_equity:,.2f} (started ${capital:,.0f})")
            else:
                all_results.append({"params": v8_params, "error": "no result"})
                print("  ❌ No result")

        except Exception as e:
            import traceback
            traceback.print_exc()
            all_results.append({"params": v8_params, "error": str(e)})
            print(f"  ❌ ERROR: {e}")

        # Save after each run
        with open(out_file, "w") as f:
            json.dump(all_results, f, indent=2, default=str)

    # Final summary
    valid = [r for r in all_results if "error" not in r]
    if valid:
        print(f"\n{'='*80}")
        print(f"  SUMMARY: {preset['label']} ({len(valid)} runs)")
        print(f"{'='*80}")
        for r in sorted(valid, key=lambda x: -x["pnl_pct"]):
            p = r["params"]
            prof_label = r.get("profile", "medium")
            print(f"  {prof_label:>6} rsv={p['spring_reserve_pct']:.2f} thresh={p['spring_score_threshold']:>2} "
                  f"tp={p['spring_tp_mult']:.0f}× p1={p['phase1_dd_max']:.0f} p2={p['phase2_dd_max']:.0f} | "
                  f"PnL={r['pnl_pct']:+8.2f}% DD={r['max_dd']:5.1f}% "
                  f"Deals={r['total_deals']:>3} Win={r['win_rate']:.0f}% Springs={r['spring_buys']}")

    print(f"\nDone. Results: {out_file}")


if __name__ == "__main__":
    main()
