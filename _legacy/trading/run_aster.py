"""Entry point for the Aster DEX Martingale trader."""
import argparse
import os
import sys

# Add parent to path so trading package imports work
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from trading.aster_trader import AsterTrader


def main():
    parser = argparse.ArgumentParser(description="Aster DEX Martingale Trader")
    parser.add_argument("--symbol", default="HYPEUSDT", help="Trading pair (default: HYPEUSDT)")
    parser.add_argument("--timeframe", default="5m", help="Candle timeframe (default: 5m)")
    parser.add_argument("--capital", type=float, default=None, help="Trading capital in USDT (default: from account)")
    parser.add_argument("--max-drawdown", type=float, default=25.0, help="Max drawdown %% circuit breaker (default: 25)")
    parser.add_argument("--leverage", type=int, default=1, help="Leverage (default: 1)")
    parser.add_argument("--dry-run", action="store_true", help="Dry run — no real orders")
    args = parser.parse_args()

    # Validate API keys (env var or Windows registry)
    if not args.dry_run:
        key = os.environ.get("ASTER_API_KEY", "")
        if not key:
            try:
                import winreg
                with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r'Environment') as k:
                    key = winreg.QueryValueEx(k, 'ASTER_API_KEY')[0]
            except Exception:
                pass
        if not key:
            print("ASTER_API_KEY not set (env var or setx)")
            sys.exit(1)

    trader = AsterTrader(
        symbol=args.symbol,
        timeframe=args.timeframe,
        capital=args.capital,
        max_drawdown_pct=args.max_drawdown,
        leverage=args.leverage,
        dry_run=args.dry_run,
    )

    try:
        trader.start()
    except KeyboardInterrupt:
        trader.stop()


if __name__ == "__main__":
    main()
