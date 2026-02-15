"""Entry point for the paper trading bot."""
import sys
import os
import argparse
import json
import signal

# Add parent dir to path so trading package is importable
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from trading.config import MartingaleConfig
from trading.paper_trader import PaperTrader


def main():
    parser = argparse.ArgumentParser(description="Martingale Paper Trader")
    parser.add_argument("--symbols", nargs="+", default=["HYPE/USDT"], help="Trading pairs")
    parser.add_argument("--timeframe", default="15m", help="Candle timeframe")
    parser.add_argument("--config", type=str, default=None, help="JSON config override file")
    parser.add_argument("--capital", type=float, default=10000, help="Initial capital")
    parser.add_argument("--max-drawdown", type=float, default=25.0, help="Circuit breaker drawdown %")
    parser.add_argument("--v1-regime", action="store_true", help="Use v1 regime detector instead of v2")
    args = parser.parse_args()

    # Conservative defaults
    cfg = MartingaleConfig(
        take_profit_pct=4.0,
        max_safety_orders=8,
        price_deviation_pct=1.5,
        deviation_multiplier=1.0,
        safety_order_multiplier=1.5,
        initial_capital=args.capital,
        base_order_size=100.0,
        safety_order_size=200.0,
        max_active_deals=3,
        fee_pct=0.1,
        slippage_pct=0.05,
    )

    # Override from JSON if provided
    if args.config:
        with open(args.config) as f:
            overrides = json.load(f)
        for k, v in overrides.items():
            if hasattr(cfg, k):
                setattr(cfg, k, v)

    # Banner
    print("\n" + "=" * 70)
    print("  🤖 MARTINGALE PAPER TRADER")
    print("=" * 70)
    print(f"  Symbols:        {', '.join(args.symbols)}")
    print(f"  Timeframe:      {args.timeframe}")
    print(f"  Capital:        ${cfg.initial_capital:,.0f}")
    print(f"  Take Profit:    {cfg.take_profit_pct}%")
    print(f"  Safety Orders:  {cfg.max_safety_orders} (dev {cfg.price_deviation_pct}%, mult {cfg.deviation_multiplier}x)")
    print(f"  SO Size Mult:   {cfg.safety_order_multiplier}x")
    print(f"  Max Deals:      {cfg.max_active_deals}")
    print(f"  Max Deal Cap:   ${cfg.max_deal_capital():,.0f}")
    print(f"  Circuit Breaker: {args.max_drawdown}% drawdown")
    print(f"  Regime:         {'v2 (Wyckoff+HVF)' if not args.v1_regime else 'v1 (basic)'}")
    print("=" * 70)
    print("  Press Ctrl+C to stop gracefully\n")

    trader = PaperTrader(
        config=cfg,
        symbols=args.symbols,
        timeframe=args.timeframe,
        use_v2_regime=not args.v1_regime,
        max_drawdown_pct=args.max_drawdown,
    )

    def handle_signal(sig, frame):
        print("\n  ⏹️  Stopping paper trader...")
        trader.stop()

    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    trader.start()


if __name__ == "__main__":
    main()
