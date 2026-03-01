#!/usr/bin/env python3
"""Entry point for AIT Multi-Coin Paper Trading Bot with Risk Profiles."""

import argparse
import signal
import sys
import time
from pathlib import Path

# Add parent to path so trading package imports work
sys.path.insert(0, str(Path(__file__).parent.parent))

from trading.aster_trader_v3 import AsterTraderV3, PROFILES

def signal_handler(signum, frame):
    """Handle Ctrl+C gracefully."""
    print("\nReceived shutdown signal...")
    if 'bot' in globals():
        bot.stop()
    sys.exit(0)

def main():
    parser = argparse.ArgumentParser(description="AIT Multi-Coin Paper Trading Bot with Risk Profiles")
    
    parser.add_argument("--timeframe", default="5m",
                       help="Timeframe for analysis (default: 5m)")
    parser.add_argument("--capital", type=float, default=10000,
                       help="Starting capital in USD (default: 10000)")
    parser.add_argument("--profile", choices=list(PROFILES.keys()), default="medium",
                       help="Initial risk profile (default: medium)")
    parser.add_argument("--max-coins", type=int, default=3,
                       help="Maximum number of coins to trade (default: 3)")
    
    args = parser.parse_args()
    
    # Register signal handler for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    if hasattr(signal, 'SIGTERM'):
        signal.signal(signal.SIGTERM, signal_handler)
    
    print("AIT Multi-Coin Paper Trading Bot v3.0")
    print("=" * 50)
    print(f"Timeframe: {args.timeframe}")
    print(f"Capital: ${args.capital:,.2f}")
    print(f"Profile: {PROFILES[args.profile]['name']}")
    print(f"Max Coins: {args.max_coins}")
    print("=" * 50)
    
    # Create bot instance
    global bot
    bot = AsterTraderV3(
        timeframe=args.timeframe,
        capital=args.capital,
        profile=args.profile
    )
    
    try:
        # Start the bot
        bot.start()
    except KeyboardInterrupt:
        print("\nInterrupted by user")
        bot.stop()
    except Exception as e:
        print(f"Fatal error: {e}")
        bot.stop()
        sys.exit(1)

if __name__ == "__main__":
    main()