"""Quick bidirectional vs long-only backtest comparison for HYPE/USDT."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from trading.data_fetcher import fetch_multiple_symbols
from trading.regime_detector import classify_regime_v2, is_martingale_friendly_v2
from trading.martingale_engine import MartingaleBot, BacktestResult
from trading.config import MartingaleConfig

def main():
    print("=" * 60)
    print("HYPE/USDT 5m — Bidirectional vs Long-Only Backtest")
    print("=" * 60)

    # Fetch data
    print("\nFetching data (cached)...")
    data = fetch_multiple_symbols(["HYPE/USDT"], "5m", days_back=30)
    df = data["HYPE/USDT"]
    df = df.tail(8640).reset_index(drop=True)
    print(f"Candles: {len(df)} | {df['timestamp'].iloc[0]} → {df['timestamp'].iloc[-1]}")

    # Classify regimes
    print("Classifying regimes (may take a few minutes)...")
    regimes = classify_regime_v2(df, "5m")
    print(f"Regime distribution:\n{regimes.value_counts().to_string()}\n")

    cfg = MartingaleConfig(
        base_order_size=200, safety_order_size=200, safety_order_multiplier=2.0,
        take_profit_pct=4.0, max_safety_orders=8, price_deviation_pct=1.5,
        deviation_multiplier=1.0, max_active_deals=3, fee_pct=0.05,
        slippage_pct=0.05, initial_capital=10000,
    )

    # Long-only
    print("Running LONG-ONLY...")
    bot_long = MartingaleBot(cfg, bidirectional=False)
    res_long = bot_long.run(df, "HYPE/USDT", "5m", precomputed_regimes=regimes, friendly_fn=is_martingale_friendly_v2)

    # Bidirectional
    print("Running BIDIRECTIONAL...")
    bot_bidir = MartingaleBot(cfg, bidirectional=True)
    res_bidir = bot_bidir.run(df, "HYPE/USDT", "5m", precomputed_regimes=regimes, friendly_fn=is_martingale_friendly_v2)

    # Results
    print("\n" + "=" * 60)
    print("RESULTS")
    print("=" * 60)

    for label, res in [("LONG-ONLY", res_long), ("BIDIRECTIONAL", res_bidir)]:
        trades = res.closed_deals
        longs = [d for d in trades if d.direction == "LONG"]
        shorts = [d for d in trades if d.direction == "SHORT"]
        long_pnl = sum(d.pnl for d in longs)
        short_pnl = sum(d.pnl for d in shorts)
        total_pnl = sum(d.pnl for d in trades)
        pct = (total_pnl / cfg.initial_capital) * 100

        print(f"\n{'─'*40}")
        print(f"  {label}")
        print(f"{'─'*40}")
        print(f"  Total trades: {len(trades)}  |  PnL: ${total_pnl:,.2f} ({pct:+.1f}%)")
        print(f"  Longs:  {len(longs):3d}  |  PnL: ${long_pnl:,.2f}")
        print(f"  Shorts: {len(shorts):3d}  |  PnL: ${short_pnl:,.2f}")
        if res.win_rate is not None:
            print(f"  Win rate: {res.win_rate:.1f}%  |  Max DD: {res.max_drawdown:.1f}%")

    print(f"\n{'='*60}")

if __name__ == "__main__":
    main()
