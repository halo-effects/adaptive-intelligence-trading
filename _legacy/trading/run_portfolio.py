"""Entry point for multi-coin portfolio mode.

Usage:
    python -m trading.run_portfolio [--dry-run] [--max-coins N] [--leverage N]
"""
import sys
import os
import argparse

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from trading.aster_trader import AsterAPI
from trading.portfolio_manager import PortfolioManager


def main():
    parser = argparse.ArgumentParser(description="Aster DEX Portfolio Manager")
    parser.add_argument("--dry-run", action="store_true", help="Simulate without real orders")
    parser.add_argument("--max-coins", type=int, default=3, help="Max simultaneous coins (default: 3)")
    parser.add_argument("--leverage", type=int, default=1, help="Leverage per coin (default: 1)")
    parser.add_argument("--capital", type=float, default=None, help="Override starting capital")
    parser.add_argument("--scanner-interval", type=int, default=720,
                        help="Cycles between scanner runs (default: 720 = ~6h)")
    args = parser.parse_args()

    api = AsterAPI()
    pm = PortfolioManager(
        api=api,
        max_coins=args.max_coins,
        total_capital=args.capital,
        leverage=args.leverage,
        dry_run=args.dry_run,
        scanner_interval=args.scanner_interval,
    )
    pm.start()


if __name__ == "__main__":
    main()
