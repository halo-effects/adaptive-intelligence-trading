"""TP% Grid Backtest — 1m candles, 2x leverage, 14 days HYPE/USDT."""
import sys, os, time, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import numpy as np
from trading.data_fetcher import fetch_multiple_symbols
from trading.config import MartingaleConfig
from trading.martingale_engine import MartingaleBot, DualMartingaleBot
from trading.regime_detector import classify_regime_v2, is_martingale_friendly_v2

SYMBOL = "HYPE/USDT"
TP_GRID = [0.5, 0.75, 1.0, 1.5, 2.0, 3.0]

def make_config(tp_pct: float) -> MartingaleConfig:
    return MartingaleConfig(
        base_order_size=400,      # 2x leverage (doubled from 200)
        safety_order_size=400,    # 2x leverage
        safety_order_multiplier=2.0,
        price_deviation_pct=1.5,
        deviation_multiplier=1.0,
        max_safety_orders=8,
        max_active_deals=3,
        take_profit_pct=tp_pct,
        trailing_tp_pct=None,
        fee_pct=0.05,
        slippage_pct=0.05,
        initial_capital=10000,
    )

def avg_trade_duration(deals):
    durations = []
    for d in deals:
        if d.close_time is not None:
            dt = (d.close_time - d.entry_time).total_seconds() / 60  # minutes
            durations.append(dt)
    return np.mean(durations) if durations else 0

def fmt_duration(minutes):
    if minutes < 60:
        return f"{minutes:.0f}m"
    elif minutes < 1440:
        return f"{minutes/60:.1f}h"
    else:
        return f"{minutes/1440:.1f}d"

def main():
    print("=" * 90)
    print("TP% GRID BACKTEST — HYPE/USDT 1m, 2x Leverage, 14 Days")
    print("=" * 90)

    # Fetch data
    print("\nFetching data...")
    data = fetch_multiple_symbols([SYMBOL], timeframe="1m", days_back=14)
    if SYMBOL not in data:
        print(f"ERROR: Could not fetch {SYMBOL}")
        return
    df = data[SYMBOL]
    print(f"\nCandles: {len(df)}")
    print(f"Period: {df['timestamp'].iloc[0]} to {df['timestamp'].iloc[-1]}")
    print(f"Price range: ${df['low'].min():.4f} — ${df['high'].max():.4f}")
    print(f"Open: ${df['open'].iloc[0]:.4f}  Close: ${df['close'].iloc[-1]:.4f}")
    pct_change = (df['close'].iloc[-1] / df['open'].iloc[0] - 1) * 100
    print(f"Buy & Hold: {pct_change:+.2f}%")

    # Precompute regimes ONCE
    print("\nClassifying regimes (v2)...")
    t0 = time.time()
    regimes = classify_regime_v2(df, timeframe="1m")
    print(f"Regime detection took {time.time()-t0:.1f}s")

    regime_counts = regimes.value_counts()
    print("\nRegime Distribution:")
    for r, c in regime_counts.items():
        print(f"  {r:20s}: {c:6d} ({c/len(df)*100:.1f}%)")

    # Run grid
    results = []
    print("\nRunning backtest grid...")
    for tp in TP_GRID:
        cfg = make_config(tp)

        # Long-only
        t0 = time.time()
        bot_long = MartingaleBot(cfg, bidirectional=False)
        res_long = bot_long.run(df, SYMBOL, "1m", precomputed_regimes=regimes,
                                friendly_fn=is_martingale_friendly_v2)
        dt_long = time.time() - t0
        ds = res_long.direction_stats
        results.append({
            "tp": tp, "strategy": "Long-Only",
            "trades": res_long.total_trades,
            "ls": f"{ds['long_count']}L/{ds['short_count']}S",
            "pnl": res_long.total_profit,
            "pnl_pct": res_long.total_profit_pct,
            "wr": res_long.win_rate,
            "maxdd": res_long.max_drawdown,
            "avg_dur": avg_trade_duration(res_long.closed_deals),
            "open": len(res_long.open_deals),
        })
        print(f"  TP={tp}% Long-Only: {res_long.total_trades} trades, "
              f"PnL=${res_long.total_profit:.2f} ({dt_long:.1f}s)")

        # Dual Dynamic+Vol
        t0 = time.time()
        bot_dual = DualMartingaleBot(cfg, dynamic_alloc=True, vol_adjusted_so=True)
        res_dual = bot_dual.run(df, SYMBOL, "1m", precomputed_regimes=regimes,
                                friendly_fn=is_martingale_friendly_v2)
        dt_dual = time.time() - t0
        ds = res_dual.direction_stats
        results.append({
            "tp": tp, "strategy": "Dual Dyn+Vol",
            "trades": res_dual.total_trades,
            "ls": f"{ds['long_count']}L/{ds['short_count']}S",
            "pnl": res_dual.total_profit,
            "pnl_pct": res_dual.total_profit_pct,
            "wr": res_dual.win_rate,
            "maxdd": res_dual.max_drawdown,
            "avg_dur": avg_trade_duration(res_dual.closed_deals),
            "open": len(res_dual.open_deals),
        })
        print(f"  TP={tp}% Dual Dyn:  {res_dual.total_trades} trades, "
              f"PnL=${res_dual.total_profit:.2f} ({dt_dual:.1f}s)")

    # Print results table
    print("\n" + "=" * 110)
    print(f"{'TP%':>5} | {'Strategy':<12} | {'Trades':>6} | {'L/S':>10} | {'Total PnL':>10} | "
          f"{'PnL%':>7} | {'WR%':>6} | {'MaxDD%':>7} | {'AvgDur':>8} | {'Open':>4}")
    print("-" * 110)
    for r in results:
        risk_adj = abs(r['pnl_pct'] / r['maxdd']) if r['maxdd'] != 0 else 0
        print(f"{r['tp']:>4.1f}% | {r['strategy']:<12} | {r['trades']:>6} | {r['ls']:>10} | "
              f"${r['pnl']:>9.2f} | {r['pnl_pct']:>6.2f}% | {r['wr']:>5.1f}% | "
              f"{r['maxdd']:>6.2f}% | {fmt_duration(r['avg_dur']):>8} | {r['open']:>4}")
    print("=" * 110)

    # Best combos
    if results:
        best_pnl = max(results, key=lambda r: r['pnl'])
        best_risk = max(results, key=lambda r: abs(r['pnl_pct'] / r['maxdd']) if r['maxdd'] != 0 else 0)
        print(f"\n🏆 Best PnL: TP={best_pnl['tp']}% {best_pnl['strategy']} → "
              f"${best_pnl['pnl']:.2f} ({best_pnl['pnl_pct']:.2f}%)")
        ratio = abs(best_risk['pnl_pct'] / best_risk['maxdd']) if best_risk['maxdd'] != 0 else 0
        print(f"🛡️  Best Risk-Adj: TP={best_risk['tp']}% {best_risk['strategy']} → "
              f"PnL/MaxDD ratio = {ratio:.2f}")

if __name__ == "__main__":
    main()
