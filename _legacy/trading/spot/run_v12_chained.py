#!/usr/bin/env python3
"""V12 Chained Backtest — Three-Engine Lifecycle Architecture.

Runs V12 (DCA + Exit + Spring engines with daily TA conductor) across
multi-chunk periods. Key improvement over V11: daily timeframe top detection
replaces 1h scorer (confirmed 61-65 score at actual tops vs max 46 on 1h).
"""
import sys, json, logging, time, argparse, os
from pathlib import Path
from datetime import datetime, timezone, timedelta

import ccxt, pandas as pd, numpy as np

if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from trading.spot.backtest_engine_v12 import SpotBacktestEngineV12
from trading.spot.macro_indicators import load_historical_fear_greed

logging.basicConfig(level=logging.WARNING, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

CACHE_DIR = Path(__file__).resolve().parent / "data" / "dwell_cache"
RESULTS_DIR = Path(__file__).resolve().parent / "backtest_results" / "v12_lifecycle"

CHUNK_DAYS = 120
OVERLAP_DAYS = 8


def cache_path(symbol, tf, start, end):
    return CACHE_DIR / f"{symbol.replace('/', '_')}_{tf}_{start}_{end}.csv"


def fetch_ohlcv(symbol, timeframe, start, end, exchange_name="binance"):
    if exchange_name == "aster":
        exchange_name = "binance"
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


def run_chained(symbol, timeframe, start, end, capital, fg, v12_params, profile="medium", exchange="aster"):
    # Apply V12 profile overrides
    overrides = V12_PROFILE_OVERRIDES.get(profile, {})
    if overrides:
        v12_params = {**v12_params, **overrides}
    
    chunks = split_into_chunks(start, end)
    logger.info("Split into %d chunks of ~%d days", len(chunks), CHUNK_DAYS)

    state = None
    chunk_summaries = []
    accumulated_1h = None

    for ci, chunk in enumerate(chunks):
        logger.info("\n-- Chunk %d/%d: %s -> %s --", ci+1, len(chunks),
                     chunk["trade_start"], chunk["trade_end"])

        df = get_candles(symbol, timeframe, chunk["fetch_start"], chunk["fetch_end"], exchange)
        if len(df) < 150:
            logger.warning("  Skipping chunk (only %d candles)", len(df))
            continue

        # Accumulate 1h data for daily conductor
        if accumulated_1h is None:
            accumulated_1h = df.copy()
        else:
            accumulated_1h = pd.concat([accumulated_1h, df], ignore_index=True)
            accumulated_1h = accumulated_1h.drop_duplicates(
                subset=["timestamp"]
            ).sort_values("timestamp").reset_index(drop=True)

        engine = SpotBacktestEngineV12(
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
            # V9 distribution (EXIT unreachable — V12 conductor handles exits)
            dist_tighten_threshold=30,
            dist_winddown_threshold=45,
            dist_exit_threshold=999,  # V12 conductor handles exit
            dist_reentry_threshold=20,
            dist_cooldown_candles=96,
            # V12 params
            **v12_params,
        )

        if state is not None:
            engine.restore_state(state)
            logger.info("  Restored state: cash=$%.0f, %d open deals, lifecycle=%s",
                         engine.cash, len(engine.deals), engine._lifecycle_phase.value)

        # Pre-load accumulated 1h data
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
            logger.info("  Chunk done: eq=$%.0f, cash=$%.0f, %d open, %d completed, lifecycle=%s",
                         partial["final_equity"], partial["cash"],
                         partial["open_deals"], partial["completed_deals"],
                         engine._lifecycle_phase.value)

    return None, chunk_summaries


PRESETS = {
    "eth": {
        "label": "ETH Full Wyckoff Cycle",
        "symbol": "ETH/USDT",
        "start": "2021-10-01",
        "end": "2025-02-20",
        "capital": 10000,
    },
    "btc": {
        "label": "BTC Full Cycle",
        "symbol": "BTC/USDT",
        "start": "2020-10-01",
        "end": "2025-02-20",
        "capital": 10000,
    },
    "sol": {
        "label": "SOL Full Cycle",
        "symbol": "SOL/USDT",
        "start": "2021-10-01",
        "end": "2025-02-20",
        "capital": 10000,
    },
}

DEFAULT_V12_PARAMS = {
    # Daily conductor
    "v12_exit_threshold": 50.0,
    "v12_mcap_ath_pct": 0.25,
    "v12_commitment_hours": 48,
    # Exit engine — patient, sell into rallies
    "v12_initial_trail_pct": 3.0,
    "v12_trail_floor_pct": 1.5,
    "v12_trail_tighten_per_day": 0.5,
    "v12_rally_sell_pct": 1.5,
    "v12_urgency_day_moderate": 4,
    "v12_urgency_day_aggressive": 7,
    "v12_urgency_day_force": 14,
    # Aggressive shorts — mirror of spring deployment at confirmed top
    "v12_short_enabled": True,
    "v12_short_tier1_deploy": 0.60,     # 60% immediately
    "v12_short_tier2_deploy": 0.80,     # 80% on bounce confirmation
    "v12_short_tier3_deploy": 0.90,     # 90% on retest (10% reserve)
    "v12_short_tier2_bounce_pct": 3.0,  # 3% bounce = add
    "v12_short_tier3_retest_pct": 2.0,  # Within 2% of entry = retest
    "v12_short_trail_pct": 10.0,        # Wide trailing stop
    "v12_short_sl_pct": 15.0,           # Hard stop loss
    "v12_funding_rate_daily": 0.0003,
    # Markup engine — ride the bull after confirmed spring
    # Markup engine — mirror of markdown: aggressive tiered deployment
    "v12_markup_deploy_pct": 0.60,       # Deploy 60% on confirmed breakout
    "v12_markup_trail_pct": 10.0,        # (unused — hold until EXIT fires)
    "v12_markup_trail_tighten_score": 30.0,
    "v12_markup_trail_tight_pct": 5.0,
    "v12_markup_pullback_pct": 5.0,      # Add on 5% pullback from high
    "v12_markup_pullback_deploy_pct": 0.15,  # 15% more per pullback add (→80%→90%)
    "v12_markup_max_adds": 2,            # 2 adds: 60→80→90, keep 10% reserve
    # Spring engine — AGGRESSIVE discount-based deployment
    # Deploy big at the bottom, add on confirmation, keep small reserve
    "v12_spring_tier1_discount": 25.0,   # 25% below exit → deploy 60% (confirmed bottom)
    "v12_spring_tier2_discount": 28.0,   # 28% below exit → deploy 80% (confirmation)
    "v12_spring_tier3_discount": 35.0,   # 35% below exit → deploy 90% (retest bottom)
    "v12_spring_tier1_deploy": 0.60,     # 60% — pile in
    "v12_spring_tier2_deploy": 0.80,     # 80% cumulative
    "v12_spring_tier3_deploy": 0.90,     # 90% cumulative (10% reserve)
    "v12_spring_tp_pct": 15.0,           # Wide TP — hold for markup engine to take over
    "v12_spring_false_drop_pct": 20.0,   # More tolerance (we're buying the bottom)
    "v12_spring_recovery_pct": 25.0,     # 25% recovery → strong confirmation before MARKUP
}


# Profile-specific V12 overrides
# Key insight: High risk = bigger bets at phase transitions, NOT more safety orders
# High profile runs a LIGHTER DCA grid to preserve cash for lifecycle plays
V12_PROFILE_OVERRIDES = {
    "low": {
        # Conservative lifecycle — smaller bets, more reserve
        "v12_markup_deploy_pct": 0.50,
        "v12_short_tier1_deploy": 0.50,
        "v12_short_tier2_deploy": 0.65,
        "v12_short_tier3_deploy": 0.75,
        "v12_spring_tier1_deploy": 0.40,
        "v12_spring_tier2_deploy": 0.60,
        "v12_spring_tier3_deploy": 0.75,
        "v12_markup_pullback_deploy_pct": 0.10,
        "v12_markup_max_adds": 2,
        "v12_spring_recovery_pct": 30.0,     # Need stronger confirmation
        "v12_exit_threshold": 55.0,           # Higher bar to exit
    },
    "medium": {
        # Standard — profile-scaled deployment
        "v12_markup_deploy_pct": 0.70,
        "v12_short_tier1_deploy": 0.70,
        "v12_short_tier2_deploy": 0.80,
        "v12_short_tier3_deploy": 0.90,
    },
    "high": {
        # Aggressive lifecycle — max conviction at transitions, lean DCA
        "v12_markup_deploy_pct": 0.90,
        "v12_short_tier1_deploy": 0.90,
        "v12_short_tier2_deploy": 0.95,
        "v12_short_tier3_deploy": 0.98,
        "v12_spring_tier1_deploy": 0.70,
        "v12_spring_tier2_deploy": 0.85,
        "v12_spring_tier3_deploy": 0.95,
        "v12_spring_tier1_discount": 20.0,    # Enter springs earlier
        "v12_spring_tier2_discount": 25.0,
        "v12_spring_tier3_discount": 30.0,
        "v12_markup_pullback_deploy_pct": 0.15,
        "v12_markup_max_adds": 3,
        "v12_spring_recovery_pct": 20.0,      # Enter markup faster
        "v12_exit_threshold": 45.0,            # Lower bar — exit earlier to preserve capital
    },
}


def main():
    parser = argparse.ArgumentParser(description="V12 Chained Backtest — 3-Engine Lifecycle")
    parser.add_argument("--preset", choices=list(PRESETS.keys()), default="eth")
    parser.add_argument("--timeframe", default="1h", help="Candle timeframe (must be 1h for daily conductor)")
    parser.add_argument("--profile", default="medium")
    parser.add_argument("--skip", type=int, default=0)
    # Override individual params
    parser.add_argument("--exit-threshold", type=float, default=None)
    parser.add_argument("--mcap-ath-pct", type=float, default=None)
    parser.add_argument("--trail-pct", type=float, default=None)
    parser.add_argument("--short-enabled", type=lambda x: x.lower() == 'true', default=None)
    parser.add_argument("--weekly-dist-veto", action="store_true", default=False,
                        help="Require weekly confirmation for distribution exits (SOL needs this)")
    parser.add_argument("--symbol", default=None, help="Override preset symbol")
    parser.add_argument("--start", default=None, help="Override preset start date")
    parser.add_argument("--capital", type=float, default=None, help="Override preset capital")
    parser.add_argument("--end", default=None, help="Override preset end date")
    args = parser.parse_args()

    if args.timeframe != "1h":
        print("WARNING: V12 conductor requires 1h candles for daily resampling. Other timeframes untested.")

    preset = PRESETS[args.preset]
    fg = load_historical_fear_greed()
    print(f"Loaded {len(fg)} F&G entries")

    v12_params = DEFAULT_V12_PARAMS.copy()
    if args.exit_threshold is not None:
        v12_params["v12_exit_threshold"] = args.exit_threshold
    if args.mcap_ath_pct is not None:
        v12_params["v12_mcap_ath_pct"] = args.mcap_ath_pct
    if args.trail_pct is not None:
        v12_params["v12_initial_trail_pct"] = args.trail_pct
    if args.short_enabled is not None:
        v12_params["v12_short_enabled"] = args.short_enabled
    if args.weekly_dist_veto:
        v12_params["v12_weekly_dist_veto"] = True

    # Allow overriding preset fields
    if args.symbol:
        preset = {**preset, "symbol": args.symbol}
    if args.start:
        preset = {**preset, "start": args.start}
    if args.capital:
        preset = {**preset, "capital": args.capital}
    if args.end:
        preset = {**preset, "end": args.end}
    elif os.environ.get("V12E_END_DATE"):
        preset = {**preset, "end": os.environ["V12E_END_DATE"]}

    out_file = RESULTS_DIR / f"{args.preset}_{args.timeframe}_v12d_{args.profile}.json"
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    print(f"\n{'='*80}")
    print(f"  V12 LIFECYCLE BACKTEST: {preset['label']}")
    print(f"  {preset['symbol']} | {args.timeframe} | {preset['start']} -> {preset['end']} | ${preset['capital']:,.0f}")
    print(f"  profile={args.profile}")
    print(f"  Baselines: V8=+23.06% | V9=+43.81% | V11 best=+46.10%")
    print(f"  V12 params: exit_thresh={v12_params['v12_exit_threshold']}, "
          f"mcap={v12_params['v12_mcap_ath_pct']*100:.0f}%, "
          f"trail={v12_params['v12_initial_trail_pct']}%->{ v12_params['v12_trail_floor_pct']}%, "
          f"short={'ON' if v12_params['v12_short_enabled'] else 'OFF'}")
    print(f"  Output: {out_file}")
    print(f"{'='*80}\n")

    try:
        result, chunk_info = run_chained(
            preset["symbol"], args.timeframe, preset["start"], preset["end"],
            preset["capital"], fg, v12_params, profile=args.profile, exchange="aster"
        )

        if result:
            extra = result.extra or {}
            entry = {
                "timeframe": args.timeframe,
                "profile": args.profile,
                "params": v12_params,
                "pnl_pct": round(result.total_return_pct, 2),
                "max_dd": round(result.max_drawdown_pct, 2),
                "final_equity": round(result.final_equity, 2),
                "total_deals": result.total_deals_completed,
                "win_rate": round(result.win_rate, 1),
                "sharpe": round(result.sharpe_ratio, 2),
                # V12 metrics
                "exit_phases": extra.get("v12_exit_phases", 0),
                "spring_phases": extra.get("v12_spring_phases", 0),
                "rally_sells": extra.get("v12_rally_sells", 0),
                "trail_stops": extra.get("v12_trail_stops", 0),
                "urgency_closes": extra.get("v12_urgency_closes", 0),
                "short_pnl": extra.get("v12_short_pnl", 0.0),
                "spring_pnl": extra.get("v12_spring_pnl", 0.0),
                "spring_deploys": extra.get("v12_spring_deploys", 0),
                "false_springs": extra.get("v12_false_springs", 0),
                "exit_pnl_preserved": extra.get("v12_exit_pnl_preserved", 0.0),
                "markup_phases": extra.get("v12_markup_phases", 0),
                "markup_pnl": extra.get("v12_markup_pnl", 0.0),
                "markup_adds": extra.get("v12_markup_adds", 0),
                "markup_trail_exits": extra.get("v12_markup_trail_exits", 0),
                "markup_conductor_exits": extra.get("v12_markup_conductor_exits", 0),
                "breakout_entries": extra.get("v12_breakout_entries", 0),
                "v8_spring_buys": extra.get("v8_spring_buys", 0),
                "force_exits": extra.get("v9_force_exits", 0),
                "chunks": chunk_info,
            }

            with open(out_file, "w") as f:
                json.dump([entry], f, indent=2, default=str)

            print(f"\n{'='*80}")
            print(f"  V12 RESULT: {preset['label']} {args.timeframe}")
            print(f"{'='*80}")
            print(f"  PnL:          {result.total_return_pct:+.2f}%")
            print(f"  Max DD:       {result.max_drawdown_pct:.1f}%")
            print(f"  Final equity: ${result.final_equity:,.2f}")
            print(f"  Deals:        {result.total_deals_completed} (Win {result.win_rate:.0f}%)")
            print(f"  Sharpe:       {result.sharpe_ratio:.2f}")
            print(f"  ─────────────────────────────────")
            print(f"  Exit phases:     {extra.get('v12_exit_phases', 0)}")
            print(f"  Rally sells:     {extra.get('v12_rally_sells', 0)}")
            print(f"  Trail stops:     {extra.get('v12_trail_stops', 0)}")
            print(f"  Urgency closes:  {extra.get('v12_urgency_closes', 0)}")
            print(f"  Short PnL:       ${extra.get('v12_short_pnl', 0):+.2f}")
            print(f"  ─────────────────────────────────")
            print(f"  Spring phases:   {extra.get('v12_spring_phases', 0)}")
            print(f"  Spring deploys:  {extra.get('v12_spring_deploys', 0)}")
            print(f"  Spring PnL:      ${extra.get('v12_spring_pnl', 0):+.2f}")
            print(f"  False springs:   {extra.get('v12_false_springs', 0)}")
            print(f"  Exit PnL saved:  ${extra.get('v12_exit_pnl_preserved', 0):+.2f}")
            print(f"  ─────────────────────────────────")
            print(f"  Markup phases:   {extra.get('v12_markup_phases', 0)}")
            print(f"  Markup PnL:      ${extra.get('v12_markup_pnl', 0):+.2f}")
            print(f"  Markup adds:     {extra.get('v12_markup_adds', 0)}")
            print(f"  Markup exits:    trail={extra.get('v12_markup_trail_exits', 0)} conductor={extra.get('v12_markup_conductor_exits', 0)}")
            print(f"  Breakout entries:{extra.get('v12_breakout_entries', 0)}")
            print(f"  ─────────────────────────────────")
            print(f"  vs V8:  {result.total_return_pct - 23.06:+.2f}pp")
            print(f"  vs V9:  {result.total_return_pct - 43.81:+.2f}pp")
            print(f"  vs V11: {result.total_return_pct - 46.10:+.2f}pp")
            print(f"{'='*80}")
        else:
            print("ERROR: No result returned")

    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"\nERROR: {e}")

    print(f"\nDone. Results: {out_file}")


if __name__ == "__main__":
    main()
