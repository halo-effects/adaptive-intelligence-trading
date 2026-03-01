#!/usr/bin/env python3
"""V7 Parameter Sweep Runner.

Sweeps tunable V7 parameters across target coin/period combos.
Usage: python -m trading.spot.run_v7_sweep
"""
import sys, time, logging, json, itertools
from datetime import datetime, timezone
from pathlib import Path

import ccxt
import pandas as pd
import numpy as np

if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from trading.spot.backtest_engine_v7 import SpotBacktestEngineV7
from trading.spot.macro_indicators import load_historical_fear_greed

logging.basicConfig(level=logging.WARNING, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

TIMEFRAME = "15m"
PROFILE = "medium"
CAPITAL = 10_000.0
EXCHANGE = "binance"
VARIANT = "regime_adaptive"
DWELL_PROFILE = "aggressive"

RESULTS_DIR = Path(__file__).resolve().parent / "backtest_results" / "v7_sweep"
CACHE_DIR = Path(__file__).resolve().parent / "data" / "dwell_cache"

# ── Sweep definitions ─────────────────────────────────────────────────────

SWEEP_GROUPS = [
    {
        "label": "BTC dwell test",
        "coin": "BTC/USDT",
        "start": "2023-06-01",
        "end": "2023-11-30",
        "sweep_params": {
            "dwell_conviction_floor": [15, 20, 25, 30, 35, 40],
        },
    },
    {
        "label": "NEAR spring test",
        "coin": "NEAR/USDT",
        "start": "2025-02-01",
        "end": "2025-09-30",
        "sweep_params": {
            "spring_score_threshold": [30, 40, 50, 60, 70],
            "spring_bypass_conviction": [True, False],
        },
    },
    {
        "label": "NEAR catastrophic period",
        "coin": "NEAR/USDT",
        "start": "2025-10-01",
        "end": "2026-02-19",
        "sweep_params": {
            "spring_score_threshold": [30, 40, 50, 60, 70],
            "trend_gate_adx": [20, 25, 30],
            "trend_gate_conviction": [40, 50, 60],
        },
    },
    {
        "label": "AVAX spring+trend",
        "coin": "AVAX/USDT",
        "start": "2024-07-01",
        "end": "2025-04-30",
        "sweep_params": {
            "spring_score_threshold": [30, 40, 50, 60, 70],
            "trend_gate_adx": [20, 25, 30],
            "trend_gate_conviction": [40, 50, 60],
        },
    },
]

# ── Data fetching (copied from run_dwell_backtest.py) ──────────────────────


def fetch_ohlcv(symbol: str, timeframe: str, start: str, end: str) -> pd.DataFrame:
    exchange = ccxt.binance({"enableRateLimit": True})
    since_ms = int(datetime.strptime(start, "%Y-%m-%d").replace(tzinfo=timezone.utc).timestamp() * 1000)
    end_ms = int(datetime.strptime(end, "%Y-%m-%d").replace(tzinfo=timezone.utc).timestamp() * 1000)

    all_candles = []
    cursor = since_ms
    batch = 0

    while cursor < end_ms:
        try:
            candles = exchange.fetch_ohlcv(symbol, timeframe, since=cursor, limit=1000)
        except Exception as e:
            logger.warning("Fetch error %s at batch %d: %s, retrying in 5s", symbol, batch, e)
            time.sleep(5)
            continue
        if not candles:
            break
        all_candles.extend(candles)
        cursor = candles[-1][0] + 1
        batch += 1
        time.sleep(max(exchange.rateLimit / 1000, 0.3))
        if batch % 20 == 0:
            logger.info("  %s: fetched %d candles so far...", symbol, len(all_candles))

    if not all_candles:
        return pd.DataFrame()

    df = pd.DataFrame(all_candles, columns=["timestamp", "open", "high", "low", "close", "volume"])
    df = df[df["timestamp"] <= end_ms].drop_duplicates(subset=["timestamp"]).reset_index(drop=True)
    return df


def cache_path(symbol: str, timeframe: str, start: str, end: str) -> Path:
    safe = symbol.replace("/", "_")
    return CACHE_DIR / f"{safe}_{timeframe}_{start}_{end}.csv"


def get_candles(symbol: str, timeframe: str, start: str, end: str) -> pd.DataFrame:
    cp = cache_path(symbol, timeframe, start, end)
    if cp.exists():
        logger.info("  Loading cached: %s", cp.name)
        return pd.read_csv(cp)
    logger.info("  Fetching %s %s %s->%s from Binance...", symbol, timeframe, start, end)
    df = fetch_ohlcv(symbol, timeframe, start, end)
    if not df.empty:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        df.to_csv(cp, index=False)
        logger.info("  Cached %d candles to %s", len(df), cp.name)
    return df


# ── Run a single backtest ─────────────────────────────────────────────────


def run_single(coin, start, end, fg_history, extra_params) -> dict:
    df = get_candles(coin, TIMEFRAME, start, end)
    if len(df) < 150:
        return {"error": "insufficient_data", "candles": len(df)}

    engine = SpotBacktestEngineV7(
        dwell_profile=DWELL_PROFILE,
        profile=PROFILE,
        capital=CAPITAL,
        exchange=EXCHANGE,
        symbol=coin,
        timeframe=TIMEFRAME,
        variant=VARIANT,
        compounding=True,
        conviction_mode=True,
        fear_greed_history=fg_history,
        **extra_params,
    )

    result = engine.run(df)

    # Count spring bypass entries from timeline
    timeline = engine.get_candle_timeline()
    spring_entries = 0
    if not timeline.empty and "spring_bypass" in timeline.columns:
        spring_entries = int(timeline["spring_bypass"].sum())

    return {
        "pnl_pct": round(result.total_return_pct, 4),
        "max_dd": round(result.max_drawdown_pct, 4),
        "total_deals": result.total_deals_completed,
        "sharpe": round(result.sharpe_ratio, 4),
        "win_rate": round(result.win_rate, 2),
        "spring_entries": spring_entries,
        "final_equity": round(result.final_equity, 2),
    }


# ── Table printing ─────────────────────────────────────────────────────────


def print_table(rows, param_keys):
    """Print results as ASCII table."""
    metric_keys = ["pnl_pct", "max_dd", "total_deals", "sharpe", "win_rate", "spring_entries"]
    headers = param_keys + metric_keys

    # Compute column widths
    col_w = {h: len(h) for h in headers}
    str_rows = []
    for r in rows:
        sr = {}
        for k in param_keys:
            sr[k] = str(r.get(k, ""))
            col_w[k] = max(col_w[k], len(sr[k]))
        for k in metric_keys:
            val = r.get(k, "")
            if isinstance(val, float):
                sr[k] = f"{val:+.2f}" if k in ("pnl_pct", "sharpe") else f"{val:.2f}"
            else:
                sr[k] = str(val)
            col_w[k] = max(col_w[k], len(sr[k]))
        str_rows.append(sr)

    # Header
    hdr = " | ".join(h.rjust(col_w[h]) for h in headers)
    sep = "-+-".join("-" * col_w[h] for h in headers)
    print(hdr)
    print(sep)
    for sr in str_rows:
        print(" | ".join(sr[h].rjust(col_w[h]) for h in headers))


# ── Incremental save ──────────────────────────────────────────────────────


def save_results(all_results):
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    out_path = RESULTS_DIR / "sweep_results.json"
    with open(out_path, "w") as f:
        json.dump(all_results, f, indent=2, default=str)
    logger.info("Saved results to %s", out_path)


# ── Main ───────────────────────────────────────────────────────────────────


def main():
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    print("=" * 80)
    print("V7 PARAMETER SWEEP")
    print(f"TF={TIMEFRAME} | Profile={PROFILE} | Capital=${CAPITAL:,.0f} | Dwell={DWELL_PROFILE}")
    print("=" * 80)

    logger.info("Loading Fear & Greed history...")
    fg_history = load_historical_fear_greed()
    logger.info("Loaded %d F&G entries", len(fg_history))

    all_results = {}

    for group in SWEEP_GROUPS:
        label = group["label"]
        coin = group["coin"]
        start = group["start"]
        end = group["end"]
        sweep = group["sweep_params"]

        param_names = list(sweep.keys())
        param_values = list(sweep.values())
        combos = list(itertools.product(*param_values))
        total = len(combos)

        print(f"\n{'=' * 80}")
        print(f"  {label}: {coin} {start} -> {end}")
        print(f"  Sweeping: {', '.join(param_names)} ({total} combos)")
        print(f"{'=' * 80}")

        group_results = []

        for idx, combo in enumerate(combos, 1):
            params = dict(zip(param_names, combo))
            params_str = ", ".join(f"{k}={v}" for k, v in params.items())
            print(f"  [{idx}/{total}] {params_str} ... ", end="", flush=True)

            try:
                result = run_single(coin, start, end, fg_history, params)
                if "error" in result:
                    print(f"ERROR: {result['error']}")
                    row = {**params, **result}
                else:
                    print(f"PnL={result['pnl_pct']:+.2f}% DD={result['max_dd']:.2f}% "
                          f"Deals={result['total_deals']} Sharpe={result['sharpe']:.2f} "
                          f"Win={result['win_rate']:.1f}% Springs={result['spring_entries']}")
                    row = {**params, **result}
            except Exception as e:
                logger.error("FAILED: %s", e, exc_info=True)
                print(f"EXCEPTION: {e}")
                row = {**params, "error": str(e)}

            group_results.append(row)

        all_results[label] = group_results

        # Print table for this group
        valid = [r for r in group_results if "error" not in r]
        if valid:
            print(f"\n--- {label} Results ---")
            print_table(valid, param_names)

            # Best by PnL
            best = max(valid, key=lambda x: x.get("pnl_pct", -999))
            best_params = {k: best[k] for k in param_names}
            print(f"\n  Best PnL: {best['pnl_pct']:+.2f}% @ {best_params}")

            # Best by Sharpe
            best_s = max(valid, key=lambda x: x.get("sharpe", -999))
            best_s_params = {k: best_s[k] for k in param_names}
            print(f"  Best Sharpe: {best_s['sharpe']:.2f} @ {best_s_params}")

        # Incremental save
        save_results(all_results)

    print(f"\n{'=' * 80}")
    print(f"SWEEP COMPLETE. Results: {RESULTS_DIR / 'sweep_results.json'}")
    print(f"{'=' * 80}")


if __name__ == "__main__":
    main()
