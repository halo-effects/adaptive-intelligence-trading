"""Compare Long-Only vs Bidirectional Martingale on HYPE/USDT."""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from trading.data_fetcher import fetch_multiple_symbols
from trading.config import MartingaleConfig
from trading.martingale_engine import MartingaleBot
from trading.regime_detector import classify_regime_v2, is_martingale_friendly_v2


def main():
    # Fetch data
    print("=" * 60)
    print("Fetching HYPE/USDT 5m data (60 days)...")
    print("=" * 60)
    data = fetch_multiple_symbols(["HYPE/USDT"], "5m", days_back=60)
    if "HYPE/USDT" not in data:
        print("ERROR: Could not fetch HYPE/USDT data")
        return
    df = data["HYPE/USDT"]
    print(f"Got {len(df)} candles from {df['timestamp'].iloc[0]} to {df['timestamp'].iloc[-1]}")

    # Sweet Spot config
    cfg = MartingaleConfig(
        base_order_size=200.0,
        safety_order_size=200.0,
        safety_order_multiplier=2.0,
        take_profit_pct=4.0,
        max_safety_orders=8,
        price_deviation_pct=1.5,
        deviation_multiplier=1.0,
        max_active_deals=3,
        fee_pct=0.05,
        slippage_pct=0.05,
        initial_capital=10000.0,
    )

    # Precompute regimes
    print("\nClassifying regimes (v2)...")
    regimes = classify_regime_v2(df, "5m")
    regime_counts = regimes.value_counts()
    print("Regime distribution:")
    for r, c in regime_counts.items():
        print(f"  {r}: {c} ({c/len(regimes)*100:.1f}%)")

    # Run Long-Only
    print("\n" + "=" * 60)
    print("Running LONG-ONLY backtest...")
    print("=" * 60)
    bot_long = MartingaleBot(cfg, bidirectional=False)
    result_long = bot_long.run(df, "HYPE/USDT", "5m",
                                precomputed_regimes=regimes,
                                friendly_fn=is_martingale_friendly_v2)

    # Run Bidirectional
    print("\n" + "=" * 60)
    print("Running BIDIRECTIONAL backtest...")
    print("=" * 60)
    bot_bidir = MartingaleBot(cfg, bidirectional=True)
    result_bidir = bot_bidir.run(df, "HYPE/USDT", "5m",
                                  precomputed_regimes=regimes,
                                  friendly_fn=is_martingale_friendly_v2)

    # Print comparison
    print("\n" + "=" * 60)
    print("COMPARISON: Long-Only vs Bidirectional")
    print("=" * 60)
    print(f"{'Metric':<25} {'Long-Only':>15} {'Bidirectional':>15}")
    print("-" * 55)

    metrics = [
        ("Total Trades", f"{result_long.total_trades}", f"{result_bidir.total_trades}"),
        ("Win Rate %", f"{result_long.win_rate:.1f}%", f"{result_bidir.win_rate:.1f}%"),
        ("Total PnL $", f"${result_long.total_profit:.2f}", f"${result_bidir.total_profit:.2f}"),
        ("Total PnL %", f"{result_long.total_profit_pct:.2f}%", f"{result_bidir.total_profit_pct:.2f}%"),
        ("Max Drawdown %", f"{result_long.max_drawdown:.2f}%", f"{result_bidir.max_drawdown:.2f}%"),
        ("Profit Factor", f"{result_long.profit_factor:.2f}", f"{result_bidir.profit_factor:.2f}"),
        ("Sharpe Ratio", f"{result_long.sharpe_ratio:.2f}", f"{result_bidir.sharpe_ratio:.2f}"),
        ("Max Capital Used", f"${result_long.max_concurrent_capital:.0f}", f"${result_bidir.max_concurrent_capital:.0f}"),
        ("Open Deals", f"{len(result_long.open_deals)}", f"{len(result_bidir.open_deals)}"),
    ]
    for name, v1, v2 in metrics:
        print(f"{name:<25} {v1:>15} {v2:>15}")

    # Direction breakdown for bidirectional
    print("\n" + "=" * 60)
    print("BIDIRECTIONAL - Direction Breakdown")
    print("=" * 60)
    ds = result_bidir.direction_stats
    print(f"{'Metric':<25} {'LONG':>15} {'SHORT':>15}")
    print("-" * 55)
    print(f"{'Deal Count':<25} {ds['long_count']:>15} {ds['short_count']:>15}")
    print(f"{'Total PnL $':<25} {'${:.2f}'.format(ds['long_pnl']):>15} {'${:.2f}'.format(ds['short_pnl']):>15}")
    print(f"{'Win Rate %':<25} {'{:.1f}%'.format(ds['long_win_rate']):>15} {'{:.1f}%'.format(ds['short_win_rate']):>15}")

    # Open deal directions
    open_long = sum(1 for d in result_bidir.open_deals if d.direction == "LONG")
    open_short = sum(1 for d in result_bidir.open_deals if d.direction == "SHORT")
    print(f"\nOpen deals: {open_long} LONG, {open_short} SHORT")

    print("\nDone!")


if __name__ == "__main__":
    main()
