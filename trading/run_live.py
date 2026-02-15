"""Entry point for the live Martingale trader on Hyperliquid."""
import argparse
import os
import sys
import signal

# Allow running as script
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from trading.config import MartingaleConfig
from trading.live_trader import LiveTrader


def main():
    parser = argparse.ArgumentParser(description="Live Martingale DCA Trader — Hyperliquid Spot")
    parser.add_argument("--symbol", default="HYPE/USDC", help="Trading pair (default: HYPE/USDC)")
    parser.add_argument("--timeframe", default="5m", help="Candle timeframe (default: 5m)")
    parser.add_argument("--capital", type=float, default=10000.0, help="Starting capital in USDC")
    parser.add_argument("--max-drawdown", type=float, default=25.0, help="Max drawdown %% circuit breaker")
    parser.add_argument("--dry-run", action="store_true", help="Simulate without placing orders")
    args = parser.parse_args()

    # Validate env vars (skip for dry-run — still needed for fetching candles)
    pk = os.environ.get("HL_PRIVATE_KEY", "")
    wallet = os.environ.get("HL_WALLET_ADDRESS", "")
    if not pk:
        print("❌ HL_PRIVATE_KEY env var not set")
        sys.exit(1)
    if not wallet:
        print("❌ HL_WALLET_ADDRESS env var not set")
        sys.exit(1)

    # Config: sweet spot params
    # Base order = ~2% of capital, SO = ~4% of capital
    base_order = args.capital * 0.02
    safety_order = args.capital * 0.04

    cfg = MartingaleConfig(
        base_order_size=base_order,
        safety_order_size=safety_order,
        safety_order_multiplier=2.0,
        price_deviation_pct=1.5,
        deviation_multiplier=1.0,
        max_safety_orders=8,
        max_active_deals=1,
        take_profit_pct=4.0,
        fee_pct=0.1,
        slippage_pct=0.0,  # live orders, no simulated slippage
        initial_capital=args.capital,
    )

    trader = LiveTrader(
        config=cfg,
        symbol=args.symbol,
        timeframe=args.timeframe,
        max_drawdown_pct=args.max_drawdown,
        dry_run=args.dry_run,
    )

    # Graceful shutdown
    def shutdown(sig, frame):
        print("\n\n  ⏹ Shutting down gracefully...")
        trader.stop()

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    print(f"\n  {'='*50}")
    print(f"  Martingale Live Trader — Hyperliquid Spot")
    print(f"  {'='*50}")
    print(f"  Symbol:       {args.symbol}")
    print(f"  Timeframe:    {args.timeframe}")
    print(f"  Capital:      ${args.capital:,.0f}")
    print(f"  Base Order:   ${base_order:,.0f} ({base_order/args.capital*100:.0f}%)")
    print(f"  Safety Order: ${safety_order:,.0f} (x2.0 multiplier)")
    print(f"  Max SOs:      {cfg.max_safety_orders}")
    print(f"  TP:           {cfg.take_profit_pct}%")
    print(f"  Max Drawdown: {args.max_drawdown}%")
    print(f"  Mode:         {'DRY-RUN' if args.dry_run else 'LIVE'}")
    print(f"  Max deal cap: ${cfg.max_deal_capital():,.0f}")
    print(f"  {'='*50}\n")

    trader.start()


if __name__ == "__main__":
    main()
