#!/usr/bin/env python3
"""V11 Chained Backtest — V9 Distribution Exit + V10 Short DCA Grid.

Runs V11 (V9 distribution exit + V10 real short DCA) across multi-chunk periods.
Combines V9's distribution scoring with V10's real short position management.
"""
import sys, json, logging, time, argparse
from pathlib import Path
from datetime import datetime, timezone, timedelta

import ccxt, pandas as pd, numpy as np

if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from trading.spot.backtest_engine_v11 import SpotBacktestEngineV11
from trading.spot.macro_indicators import load_historical_fear_greed

logging.basicConfig(level=logging.WARNING, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

CACHE_DIR = Path(__file__).resolve().parent / "data" / "dwell_cache"
RESULTS_DIR = Path(__file__).resolve().parent / "backtest_results" / "v11_hybrid"

CHUNK_DAYS = 120
OVERLAP_DAYS = 8


def cache_path(symbol, tf, start, end):
    return CACHE_DIR / f"{symbol.replace('/', '_')}_{tf}_{start}_{end}.csv"


def fetch_ohlcv(symbol, timeframe, start, end, exchange_name="binance"):
    # Support multiple exchanges
    if exchange_name == "aster":
        # Fallback to binance for now since aster might not be available in ccxt
        exchange_name = "binance"
        logger.warning(f"Using binance instead of aster for {symbol}")
    
    exchange = getattr(ccxt, exchange_name)({"enableRateLimit": True})
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


def get_candles(symbol, tf, start, end, exchange="binance"):
    cp = cache_path(symbol, tf, start, end)
    if cp.exists():
        df = pd.read_csv(cp)
        logger.info("  Cached: %s (%d candles)", cp.name, len(df))
        return df
    logger.info("  Fetching: %s %s %s->%s from %s...", symbol, tf, start, end, exchange)
    df = fetch_ohlcv(symbol, tf, start, end, exchange)
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


def run_chained(symbol, timeframe, start, end, capital, fg, v11_params, profile="medium", exchange="aster"):
    chunks = split_into_chunks(start, end)
    logger.info("Split into %d chunks of ~%d days", len(chunks), CHUNK_DAYS)

    state = None
    chunk_summaries = []
    accumulated_1h = None  # Accumulate all 1h data for MTF scoring

    for ci, chunk in enumerate(chunks):
        logger.info("\n-- Chunk %d/%d: %s -> %s --", ci+1, len(chunks),
                     chunk["trade_start"], chunk["trade_end"])

        df = get_candles(symbol, timeframe, chunk["fetch_start"], chunk["fetch_end"], exchange)
        if len(df) < 150:
            logger.warning("  Skipping chunk (only %d candles)", len(df))
            continue

        # Accumulate 1h data across chunks for MTF daily/4h scoring
        if accumulated_1h is None:
            accumulated_1h = df.copy()
        else:
            accumulated_1h = pd.concat([accumulated_1h, df], ignore_index=True)
            accumulated_1h = accumulated_1h.drop_duplicates(
                subset=["timestamp"]
            ).sort_values("timestamp").reset_index(drop=True)

        engine = SpotBacktestEngineV11(
            dwell_profile="aggressive", profile=profile, capital=capital,
            exchange=exchange, symbol=symbol, timeframe=timeframe,
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
            # V11 params (V9 distribution + V10 short)
            **v11_params,
        )

        if state is not None:
            engine.restore_state(state)
            logger.info("  Restored state: cash=$%.0f, %d open deals, %d completed, %d short deals",
                         engine.cash, len(engine.deals), len(engine.completed_deals), len(engine._short_deals))

        # Pre-load accumulated 1h data for MTF scoring (daily/4h need full history)
        engine._accumulated_1h = accumulated_1h

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
            logger.info("  Chunk done: eq=$%.0f, cash=$%.0f, %d open, %d completed, %d shorts",
                         partial["final_equity"], partial["cash"],
                         partial["open_deals"], partial["completed_deals"],
                         len(engine._short_deals) if hasattr(engine, '_short_deals') else 0)

    return None, chunk_summaries


PRESETS = {
    "eth": {
        "label": "ETH Full Wyckoff Cycle",
        "symbol": "ETH/USDT",
        "start": "2022-06-01",
        "end": "2025-02-19",
        "capital": 10000,
    },
    "near": {
        "label": "NEAR Extended",
        "symbol": "NEAR/USDT",
        "start": "2025-02-01",
        "end": "2026-02-19",
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

# V11 default params (V9 distribution + V10 short + mcap ATH gating + fast invalidation)
DEFAULT_V11_PARAMS = {
    # V9 distribution params (use winning values from V9)
    "dist_tighten_threshold": 30,
    "dist_winddown_threshold": 45,
    "dist_exit_threshold": 100,  # Keep V9's EXIT phase unreachable; V11's McapGatedScorer handles exit
    "dist_reentry_threshold": 20,
    "dist_cooldown_candles": 96,
    "dist_short_profit_per_5pct": 0.02,  # Unused in V11 (using real shorts)
    
    # V10 short params with TIGHTER STOP-LOSS
    "short_tp_pct": 2.5,
    "short_sl_pct": 10.0,  # Give shorts room to breathe at volatile tops
    "short_max_entries": 8,
    "short_deviation_pct": 2.5,
    "funding_rate_daily": 0.0003,
    
    # V11 market cap ATH gating
    "mcap_ath_pct": 0.25,  # 25% from mcap ATH
    "use_mcap_gating": True,
    
    # V11 fast invalidation
    "short_tight_sl_pct": 5.0,  # Fast exit at 5%
    "enable_fast_invalidation": False,  # Disabled — kills shorts too early at tops
    
    # V11 structural exit for 1h
    "structural_exit": False,  # Default off, enable for 1h
    "dist_exit_threshold_1h": 50.0,
}

# Parameter sweep configurations
SWEEP_PARAMS = [
    # Default V11 configuration with mcap gating
    {**DEFAULT_V11_PARAMS},
    
    # Tighter mcap ATH gating (10% instead of 20%)
    {**DEFAULT_V11_PARAMS, "mcap_ath_pct": 0.10},
    
    # Looser mcap ATH gating (30% instead of 20%)  
    {**DEFAULT_V11_PARAMS, "mcap_ath_pct": 0.30},
    
    # Disable mcap gating (price-based ATH only)
    {**DEFAULT_V11_PARAMS, "use_mcap_gating": False},
    
    # Tighter fast invalidation (2% instead of 3%)
    {**DEFAULT_V11_PARAMS, "short_tight_sl_pct": 2.0},
    
    # Looser fast invalidation (5% instead of 3%)
    {**DEFAULT_V11_PARAMS, "short_tight_sl_pct": 5.0},
    
    # Disable fast invalidation
    {**DEFAULT_V11_PARAMS, "enable_fast_invalidation": False},
    
    # Aggressive short config (higher TP, even tighter SL)
    {**DEFAULT_V11_PARAMS, "short_tp_pct": 3.5, "short_sl_pct": 3.0},
    
    # Conservative short config (lower TP, looser main SL)
    {**DEFAULT_V11_PARAMS, "short_tp_pct": 1.5, "short_sl_pct": 8.0},
    
    # Structural exit enabled (for 1h comparison)
    {**DEFAULT_V11_PARAMS, "structural_exit": True},
]


def detect_timeframe_params(timeframe: str, base_params: dict) -> dict:
    """Auto-detect and adjust parameters based on timeframe."""
    params = base_params.copy()
    # Don't force structural_exit — let the caller decide
    return params


def main():
    parser = argparse.ArgumentParser(description="V11 Chained Backtest")
    parser.add_argument("--preset", choices=list(PRESETS.keys()), default="eth")
    parser.add_argument("--timeframe", default="15m", help="Candle timeframe (15m, 1h)")
    parser.add_argument("--sweep", action="store_true", help="Run parameter sweep")
    parser.add_argument("--profile", default="medium")
    parser.add_argument("--skip", type=int, default=0)
    args = parser.parse_args()

    preset = PRESETS[args.preset]
    fg = load_historical_fear_greed()
    print(f"Loaded {len(fg)} F&G entries")

    # Adjust parameters based on timeframe
    if args.sweep:
        sweep = [detect_timeframe_params(args.timeframe, p) for p in SWEEP_PARAMS]
    else:
        sweep = [detect_timeframe_params(args.timeframe, DEFAULT_V11_PARAMS)]

    out_file = RESULTS_DIR / f"{args.preset}_{args.timeframe}{'_sweep' if args.sweep else ''}.json"
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    print(f"\n{'='*80}")
    print(f"  V11 HYBRID BACKTEST: {preset['label']}")
    print(f"  {preset['symbol']} | {args.timeframe} | {preset['start']} -> {preset['end']} | ${preset['capital']:,.0f}")
    print(f"  {len(sweep)} param set(s) | profile={args.profile}")
    print(f"  V9 baseline (15m, exit=60): +43.81%")
    print(f"  V8 baseline: +23.06%")
    print(f"  Output: {out_file}")
    print(f"{'='*80}\n")

    all_results = []

    for si, v11_params in enumerate(sweep):
        if si < args.skip:
            continue

        # Format param summary
        ps = f"exit={v11_params.get('dist_exit_threshold', 60)}"
        if v11_params.get('structural_exit'):
            ps += f" struct={v11_params.get('dist_exit_threshold_1h', 30)}"
        ps += f" short_tp={v11_params.get('short_tp_pct', 2.5)}"
        ps += f" short_sl={v11_params.get('short_sl_pct', 15)}"
        ps += f" funding={v11_params.get('funding_rate_daily', 0.0003):.4f}"

        print(f"\n[{si+1}/{len(sweep)}] {ps}")
        print("-" * 60)

        try:
            result, chunk_info = run_chained(
                preset["symbol"], args.timeframe, preset["start"], preset["end"],
                preset["capital"], fg, v11_params, profile=args.profile, exchange="aster"
            )

            if result:
                extra = result.extra if hasattr(result, 'extra') and result.extra else {}
                entry = {
                    "timeframe": args.timeframe,
                    "profile": args.profile,
                    "params": v11_params,
                    "pnl_pct": round(result.total_return_pct, 2),
                    "max_dd": round(result.max_drawdown_pct, 2),
                    "final_equity": round(result.final_equity, 2),
                    "total_deals": result.total_deals_completed,
                    "win_rate": round(result.win_rate, 1),
                    "sharpe": round(result.sharpe_ratio, 2),
                    "spring_buys": extra.get("v8_spring_buys", 0),
                    "force_exits": extra.get("v9_force_exits", 0),
                    "short_pnl": extra.get("v11_short_pnl", 0.0),
                    "short_funding": extra.get("v11_short_funding", 0.0),
                    "short_deals": extra.get("v11_short_deals_completed", 0),
                    "shorts_gated": extra.get("v11_shorts_gated_by_mcap", 0),
                    "fast_invalidations": extra.get("v11_fast_invalidations", 0),
                    "mcap_data": extra.get("v11_mcap_data_available", False),
                    "chunks": chunk_info,
                }
                all_results.append(entry)

                print(f"\n  {'='*60}")
                print(f"  RESULT: PnL={result.total_return_pct:+.2f}% | DD={result.max_drawdown_pct:.1f}% | "
                      f"Deals={result.total_deals_completed} | Win={result.win_rate:.0f}% | "
                      f"Sharpe={result.sharpe_ratio:.2f}")
                print(f"  Final equity: ${result.final_equity:,.2f}")
                print(f"  Short PnL: ${extra.get('v11_short_pnl', 0):+.2f} | "
                      f"Funding: ${extra.get('v11_short_funding', 0):.2f} | "
                      f"Short deals: {extra.get('v11_short_deals_completed', 0)}")
                print(f"  Force exits: {extra.get('v9_force_exits', 0)} | "
                      f"Spring buys: {extra.get('v8_spring_buys', 0)}")
                print(f"  Shorts gated by mcap: {extra.get('v11_shorts_gated_by_mcap', 0)} | "
                      f"Fast invalidations: {extra.get('v11_fast_invalidations', 0)} | "
                      f"Mcap data: {'Yes' if extra.get('v11_mcap_data_available', False) else 'No'}")
                print(f"  {'='*60}")
            else:
                all_results.append({"params": v11_params, "error": "no result"})

        except Exception as e:
            import traceback
            traceback.print_exc()
            all_results.append({"params": v11_params, "error": str(e)})
            print(f"  ERROR: {e}")

        # Save after each run
        with open(out_file, "w") as f:
            json.dump(all_results, f, indent=2, default=str)

    # Summary
    valid = [r for r in all_results if "error" not in r]
    if valid:
        print(f"\n{'='*80}")
        print(f"  V11 SUMMARY: {preset['label']} {args.timeframe} ({len(valid)} runs)")
        print(f"  V9 baseline (15m): +43.81% | V8 baseline: +23.06%")
        print(f"{'='*80}")
        for r in sorted(valid, key=lambda x: -x["pnl_pct"]):
            p = r["params"]
            structural = " [STRUCT]" if p.get('structural_exit') else ""
            mcap_gating = " [MCAP]" if p.get('use_mcap_gating', True) else ""
            fast_inv = " [FAST]" if p.get('enable_fast_invalidation', True) else ""
            print(f"  mcap={p.get('mcap_ath_pct', 0.2)*100:>2.0f}% sl={p.get('short_sl_pct', 5):>3.0f}% "
                  f"short_deals={r['short_deals']:>2} gated={r.get('shorts_gated', 0):>2}{mcap_gating}{fast_inv}{structural} | "
                  f"PnL={r['pnl_pct']:+8.2f}% DD={r['max_dd']:5.1f}% "
                  f"Deals={r['total_deals']:>3} Win={r['win_rate']:.0f}%")

    print(f"\nDone. Results: {out_file}")


if __name__ == "__main__":
    main()