"""Definitive 60-day bidirectional vs long-only backtest comparison."""
import sys, os, json, time
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
import numpy as np
from trading.data_fetcher import fetch_multiple_symbols
from trading.config import MartingaleConfig
from trading.martingale_engine import MartingaleBot, BacktestResult
from trading.regime_detector import classify_regime_v2, is_martingale_friendly_v2

RESULTS_DIR = Path(__file__).parent / "results"
RESULTS_DIR.mkdir(exist_ok=True)


def sweet_spot_config():
    return MartingaleConfig(
        base_order_size=200,
        safety_order_size=200,
        safety_order_multiplier=2.0,
        take_profit_pct=4.0,
        max_safety_orders=8,
        price_deviation_pct=1.5,
        deviation_multiplier=1.0,
        max_active_deals=3,
        fee_pct=0.05,
        slippage_pct=0.05,
        initial_capital=10000,
    )


def direction_breakdown(result: BacktestResult) -> dict:
    long_deals = [d for d in result.closed_deals if d.direction == "LONG"]
    short_deals = [d for d in result.closed_deals if d.direction == "SHORT"]

    def avg_duration(deals):
        durations = []
        for d in deals:
            if d.close_time and d.entry_time:
                dt = (d.close_time - d.entry_time).total_seconds() / 3600
                durations.append(dt)
        return np.mean(durations) if durations else 0

    def avg_sos(deals):
        return np.mean([d.so_count for d in deals]) if deals else 0

    return {
        "long_count": len(long_deals),
        "short_count": len(short_deals),
        "long_pnl": round(sum(d.pnl for d in long_deals), 2),
        "short_pnl": round(sum(d.pnl for d in short_deals), 2),
        "long_wr": round((sum(1 for d in long_deals if d.pnl > 0) / len(long_deals) * 100) if long_deals else 0, 1),
        "short_wr": round((sum(1 for d in short_deals if d.pnl > 0) / len(short_deals) * 100) if short_deals else 0, 1),
        "long_avg_duration_h": round(avg_duration(long_deals), 1),
        "short_avg_duration_h": round(avg_duration(short_deals), 1),
        "long_avg_sos": round(avg_sos(long_deals), 1),
        "short_avg_sos": round(avg_sos(short_deals), 1),
    }


def print_result(label: str, r: BacktestResult, breakdown: dict = None):
    print(f"\n{'='*60}")
    print(f"  {label}")
    print(f"{'='*60}")
    print(f"  Total trades:     {r.total_trades}")
    print(f"  Win rate:         {r.win_rate:.1f}%")
    print(f"  Total PnL:        ${r.total_profit:.2f}")
    print(f"  Total PnL %:      {r.total_profit_pct:.2f}%")
    print(f"  Max Drawdown:     {r.max_drawdown:.2f}%")
    print(f"  Profit Factor:    {r.profit_factor:.2f}")
    print(f"  Sharpe Ratio:     {r.sharpe_ratio:.2f}")
    s = r.summary_dict()
    print(f"  Avg SOs/deal:     {s['avg_so_per_deal']}")
    print(f"  Max Capital Used: ${s['max_concurrent_capital']:.0f}")
    if breakdown:
        print(f"\n  --- Direction Breakdown ---")
        print(f"  Long trades:      {breakdown['long_count']}  |  Short trades: {breakdown['short_count']}")
        print(f"  Long PnL:         ${breakdown['long_pnl']:.2f}  |  Short PnL: ${breakdown['short_pnl']:.2f}")
        print(f"  Long WR:          {breakdown['long_wr']:.1f}%  |  Short WR: {breakdown['short_wr']:.1f}%")
        print(f"  Long avg dur:     {breakdown['long_avg_duration_h']:.1f}h  |  Short avg dur: {breakdown['short_avg_duration_h']:.1f}h")
        print(f"  Long avg SOs:     {breakdown['long_avg_sos']:.1f}  |  Short avg SOs: {breakdown['short_avg_sos']:.1f}")


def main():
    print("=" * 60)
    print("  DEFINITIVE 60-DAY BACKTEST: HYPE/USDT 5m")
    print("  Bidirectional vs Long-Only Comparison")
    print(f"  Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    # 1. Fetch data
    print("\n[1/4] Fetching 60 days of HYPE/USDT 5m data...")
    data = fetch_multiple_symbols(["HYPE/USDT"], "5m", days_back=60)
    df = data["HYPE/USDT"]
    print(f"  Total candles: {len(df)}")
    print(f"  Date range: {df['timestamp'].iloc[0]} → {df['timestamp'].iloc[-1]}")

    # 2. Regime classification
    print(f"\n[2/4] Classifying regimes (this takes 10-30 minutes)...")
    print(f"  Regime classification started: {datetime.now().strftime('%H:%M:%S')}")
    t0 = time.time()
    regimes = classify_regime_v2(df, "5m")
    t1 = time.time()
    print(f"  Regime classification finished: {datetime.now().strftime('%H:%M:%S')}")
    print(f"  Duration: {(t1-t0)/60:.1f} minutes")

    # Regime distribution
    dist = regimes.value_counts()
    print(f"\n  --- Regime Distribution ---")
    for regime, count in dist.items():
        pct = count / len(regimes) * 100
        print(f"  {regime:20s}: {count:6d} ({pct:5.1f}%)")

    # 3. Run backtests
    cfg = sweet_spot_config()

    print(f"\n[3/4] Running LONG-ONLY backtest...")
    bot_long = MartingaleBot(cfg, bidirectional=False)
    result_long = bot_long.run(df, "HYPE/USDT", "5m", precomputed_regimes=regimes, friendly_fn=is_martingale_friendly_v2)
    print(f"  Done — {result_long.total_trades} trades")

    print(f"\n[4/4] Running BIDIRECTIONAL backtest...")
    bot_bidir = MartingaleBot(cfg, bidirectional=True)
    result_bidir = bot_bidir.run(df, "HYPE/USDT", "5m", precomputed_regimes=regimes, friendly_fn=is_martingale_friendly_v2)
    print(f"  Done — {result_bidir.total_trades} trades")

    # 4. Print results
    print_result("LONG-ONLY", result_long)
    bidir_breakdown = direction_breakdown(result_bidir)
    print_result("BIDIRECTIONAL", result_bidir, bidir_breakdown)

    # Delta
    print(f"\n{'='*60}")
    print(f"  DELTA (Bidirectional - Long-Only)")
    print(f"{'='*60}")
    print(f"  Trades:       {result_bidir.total_trades - result_long.total_trades:+d}")
    print(f"  PnL:          ${result_bidir.total_profit - result_long.total_profit:+.2f}")
    print(f"  PnL %:        {result_bidir.total_profit_pct - result_long.total_profit_pct:+.2f}%")
    print(f"  Win Rate:     {result_bidir.win_rate - result_long.win_rate:+.1f}%")
    print(f"  Max DD:       {result_bidir.max_drawdown - result_long.max_drawdown:+.2f}%")

    # Save results
    output = {
        "timestamp": datetime.now().isoformat(),
        "symbol": "HYPE/USDT",
        "timeframe": "5m",
        "days": 60,
        "candles": len(df),
        "regime_classification_minutes": round((t1 - t0) / 60, 1),
        "regime_distribution": {k: int(v) for k, v in dist.items()},
        "long_only": result_long.summary_dict(),
        "bidirectional": result_bidir.summary_dict(),
        "bidirectional_breakdown": bidir_breakdown,
        "config": {
            "base_order_size": cfg.base_order_size,
            "safety_order_size": cfg.safety_order_size,
            "safety_order_multiplier": cfg.safety_order_multiplier,
            "take_profit_pct": cfg.take_profit_pct,
            "max_safety_orders": cfg.max_safety_orders,
            "price_deviation_pct": cfg.price_deviation_pct,
            "deviation_multiplier": cfg.deviation_multiplier,
            "max_active_deals": cfg.max_active_deals,
            "fee_pct": cfg.fee_pct,
            "slippage_pct": cfg.slippage_pct,
            "initial_capital": cfg.initial_capital,
        },
    }
    out_path = RESULTS_DIR / "definitive_comparison.json"
    with open(out_path, "w") as f:
        json.dump(output, f, indent=2)
    print(f"\n  Results saved to: {out_path}")
    print(f"\n  Finished: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


if __name__ == "__main__":
    main()
