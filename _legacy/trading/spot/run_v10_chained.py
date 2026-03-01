#!/usr/bin/env python3
"""V10 Chained Backtest — Conviction-Weighted Wyckoff full cycle test.

Splits long date ranges into ~4-month chunks, runs each sequentially,
carries positions/cash/state across chunk boundaries.
"""
import sys, json, logging, time, argparse
from pathlib import Path
from datetime import datetime, timezone, timedelta

import ccxt, pandas as pd, numpy as np

if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from trading.spot.backtest_engine_v10 import SpotBacktestEngineV10
from trading.spot.macro_indicators import load_historical_fear_greed

logging.basicConfig(level=logging.WARNING, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

CACHE_DIR = Path(__file__).resolve().parent / "data" / "dwell_cache"
RESULTS_DIR = Path(__file__).resolve().parent / "backtest_results" / "v10_chained"

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
    logger.info("  Fetching: %s %s %s→%s ...", symbol, tf, start, end)
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


def run_chained(symbol, timeframe, start, end, capital, fg, v10_params,
                profile="medium", max_chunks=None):
    """Run V10 across multiple chunks with state carry-forward."""
    chunks = split_into_chunks(start, end)
    if max_chunks:
        chunks = chunks[:max_chunks]
        if chunks:
            chunks[-1]["is_last"] = True
    logger.info("Split into %d chunks of ~%d days", len(chunks), CHUNK_DAYS)

    state = None
    all_equity = []
    chunk_summaries = []

    # V8 params to pass through
    v8_keys = {"spring_reserve_pct", "spring_score_threshold", "spring_tp_mult",
               "spring_size_mult", "spring_max_entries", "phase1_dd_max", "phase2_dd_max"}
    v8_params = {k: v for k, v in v10_params.items() if k in v8_keys}
    v10_only = {k: v for k, v in v10_params.items() if k not in v8_keys}

    for ci, chunk in enumerate(chunks):
        logger.info("\n── Chunk %d/%d: %s → %s ──", ci+1, len(chunks),
                     chunk["trade_start"], chunk["trade_end"])

        df = get_candles(symbol, timeframe, chunk["fetch_start"], chunk["fetch_end"])
        if len(df) < 150:
            logger.warning("  Skipping chunk (only %d candles)", len(df))
            continue

        engine = SpotBacktestEngineV10(
            dwell_profile="aggressive", profile=profile, capital=capital,
            exchange="binance", symbol=symbol, timeframe=timeframe,
            variant="regime_adaptive", compounding=True, conviction_mode=True,
            fear_greed_history=fg,
            dwell_conviction_floor=30,
            spring_bypass_conviction=True,
            trend_gate_adx=25,
            trend_gate_conviction=50,
            **v8_params,
            **v10_only,
        )

        if state is not None:
            engine.restore_state(state)
            logger.info("  Restored state: cash=$%.0f, %d open deals, %d completed, mode=%s",
                         engine.cash, len(engine.deals), len(engine.completed_deals),
                         engine._capital_mode.value)

        if chunk["is_last"]:
            result = engine.run(df)
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
            partial, state = engine.run_no_close(df)
            all_equity.extend(engine.equity_snapshots)
            chunk_summaries.append({
                "chunk": ci+1,
                "period": f"{chunk['trade_start']}→{chunk['trade_end']}",
                "candles": len(df),
                **partial,
            })
            logger.info("  Chunk done: eq=$%.0f, cash=$%.0f, %d open, %d completed",
                         partial["final_equity"], partial["cash"],
                         partial["open_deals"], partial["completed_deals"])

    logger.warning("Fell through without final chunk — forcing close")
    return None, all_equity, chunk_summaries


PRESETS = {
    "eth": {
        "label": "ETH Full Wyckoff Cycle",
        "symbol": "ETH/USDT",
        "start": "2022-06-01",
        "end": "2025-02-19",
        "capital": 10000,
    },
    "eth_full": {
        "label": "ETH Full Wyckoff Cycle",
        "symbol": "ETH/USDT",
        "start": "2022-06-01",
        "end": "2025-02-19",
        "capital": 10000,
    },
    "sol": {
        "label": "SOL Full Cycle",
        "symbol": "SOL/USDT",
        "start": "2022-06-01",
        "end": "2025-02-19",
        "capital": 10000,
    },
    "btc": {
        "label": "BTC Full Cycle",
        "symbol": "BTC/USDT",
        "start": "2022-06-01",
        "end": "2025-02-19",
        "capital": 10000,
    },
}

DEFAULT_V10_PARAMS = {
    # V8 base params
    "spring_reserve_pct": 0.25,
    "spring_score_threshold": 60,
    "spring_tp_mult": 5.0,
    "spring_size_mult": 3.0,
    "spring_max_entries": 5,
    "phase1_dd_max": 15.0,
    "phase2_dd_max": 30.0,
    # V10 params
    "v10_dist_threshold": 40.0,
    "v10_markdown_dist_threshold": 60.0,
    "v10_accum_spring_threshold": 50.0,
    "v10_short_tp_pct": 2.5,
    "v10_short_sl_pct": 15.0,
    "v10_short_max_entries": 8,
    "v10_funding_rate_daily": 0.0003,
    "v10_cash_timeout_candles": 48,
    "v10_compounding": True,
}


def main():
    parser = argparse.ArgumentParser(description="V10 Chained Backtest — Wyckoff Conviction")
    parser.add_argument("--preset", choices=list(PRESETS.keys()), default="eth",
                        help="Preset coin/period")
    parser.add_argument("--symbol", help="Override symbol")
    parser.add_argument("--start", help="Override start date")
    parser.add_argument("--end", help="Override end date")
    parser.add_argument("--capital", type=float, help="Override capital")
    parser.add_argument("--profile", default="medium", help="Risk profile")
    parser.add_argument("--chunks", type=int, default=None, help="Limit number of chunks")
    parser.add_argument("--timeframe", default="15m", help="Candle timeframe (default: 15m)")
    args = parser.parse_args()

    preset = PRESETS[args.preset]
    symbol = args.symbol or preset["symbol"]
    start = args.start or preset["start"]
    end = args.end or preset["end"]
    capital = args.capital or preset["capital"]

    fg = load_historical_fear_greed()
    print(f"Loaded {len(fg)} F&G entries")

    out_file = RESULTS_DIR / f"{args.preset}_v10.json"
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    print(f"\n{'='*80}")
    print(f"  V10 CHAINED BACKTEST: {preset['label']}")
    print(f"  {symbol} | {start} → {end} | ${capital:,.0f}")
    if args.chunks:
        print(f"  Limited to {args.chunks} chunks")
    print(f"  Output: {out_file}")
    print(f"{'='*80}\n")

    try:
        result, equity_curve, chunk_info = run_chained(
            symbol, args.timeframe, start, end, capital, fg, DEFAULT_V10_PARAMS,
            profile=args.profile, max_chunks=args.chunks,
        )

        if result:
            extra = result.extra or {}
            entry = {
                "profile": args.profile,
                "params": DEFAULT_V10_PARAMS,
                "pnl_pct": round(result.total_return_pct, 2),
                "max_dd": round(result.max_drawdown_pct, 2),
                "final_equity": round(result.final_equity, 2),
                "total_deals": result.total_deals_completed,
                "win_rate": round(result.win_rate, 1),
                "sharpe": round(result.sharpe_ratio, 2),
                "spring_buys": extra.get("v8_spring_buys", 0),
                "phase_transitions": extra.get("v10_phase_transitions", []),
                "short_pnl": extra.get("v10_short_pnl", 0),
                "short_funding": extra.get("v10_short_funding", 0),
                "realized_pnl": extra.get("v10_realized_pnl", 0),
                "interim_sells": extra.get("v10_interim_sells", 0),
                "interim_buys": extra.get("v10_interim_buys", 0),
                "short_deals": extra.get("v10_short_deals_completed", 0),
                "chunks": chunk_info,
            }

            with open(out_file, "w") as f:
                json.dump(entry, f, indent=2, default=str)

            print(f"\n{'='*80}")
            print(f"  V10 RESULT: {preset['label']}")
            print(f"{'='*80}")
            print(f"  PnL:           {result.total_return_pct:+.2f}%")
            print(f"  Final Equity:  ${result.final_equity:,.2f}")
            print(f"  Max Drawdown:  {result.max_drawdown_pct:.1f}%")
            print(f"  Deals:         {result.total_deals_completed}")
            print(f"  Win Rate:      {result.win_rate:.0f}%")
            print(f"  Sharpe:        {result.sharpe_ratio:.2f}")
            print(f"  Short PnL:     ${extra.get('v10_short_pnl', 0):,.2f}")
            print(f"  Short Funding: ${extra.get('v10_short_funding', 0):,.2f}")
            print(f"  Interim Sells: {extra.get('v10_interim_sells', 0)}")
            print(f"  Interim Buys:  {extra.get('v10_interim_buys', 0)}")
            print(f"  Phase Transitions: {len(extra.get('v10_phase_transitions', []))}")

            # Compare with V8 baseline
            print(f"\n  V8 Baseline: +23.06% ($12,306)")
            print(f"  V10 Result:  {result.total_return_pct:+.2f}% (${result.final_equity:,.2f})")
            improvement = result.total_return_pct - 23.06
            print(f"  Delta:       {improvement:+.2f}pp")
        else:
            print("  ❌ No result")

    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"\n  ❌ ERROR: {e}")

    print(f"\nDone. Results: {out_file}")


if __name__ == "__main__":
    main()
