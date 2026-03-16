"""
create-prediction.py — Create a Predict+ prediction market on Basis

Deploys a new prediction market with N outcomes via the MarketTrading contract.
Each outcome gets a token on its own bonding curve. Creator earns 20% of all
trading fees for the lifetime of the market.

SDK: client.prediction_markets.create_market()

Key mechanics:
- Multi-outcome markets have higher expected payouts than binary markets
- Winner takes the ENTIRE losing pool (not capped at $1/share like Polymarket)
- Fresh bonding curve = max price impact from early volume
- Min 5 unique participants for creator airdrop points (300 pts)
- Requires small BNB for gas + creation fee

Usage:
    python create-prediction.py --title "Will ETH close above $4000 on March 20?" \\
        --outcomes "Yes,No" --duration-days 7

    python create-prediction.py --title "2026 BNB Q2 price bracket" \\
        --outcomes "Below $400,$400-$600,$600-$800,Above $800" \\
        --duration-days 90 --dry-run
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

# Import shared helpers
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from client_helper import get_client, output_result, MAINTOKEN


def parse_args():
    parser = argparse.ArgumentParser(
        description="Create a Predict+ prediction market on Basis (BNB Chain)"
    )
    parser.add_argument("--title", required=True, help="Market title / question")
    parser.add_argument("--symbol", default=None, help="Market token symbol (auto-generated if omitted)")
    parser.add_argument("--outcomes", required=True, help="Comma-separated outcome names (e.g. 'Yes,No')")
    parser.add_argument("--duration-days", type=int, default=7, help="Days until market closes (default: 7)")
    parser.add_argument("--end-date", help="Explicit end date (YYYY-MM-DD). Overrides --duration-days.")
    parser.add_argument("--bonding", type=int, default=1000, help="Bonding curve amount (default: 1000)")
    parser.add_argument("--frozen", action="store_true", help="Start in frozen state (whitelist-only)")
    parser.add_argument("--private", action="store_true", help="Create as private market (creator-managed resolution)")
    parser.add_argument("--dry-run", action="store_true", help="Simulate without submitting transactions")
    parser.add_argument("--json-output", action="store_true", help="Output as JSON")
    return parser.parse_args()


def main():
    args = parse_args()

    outcomes = [o.strip() for o in args.outcomes.split(",")]
    if len(outcomes) < 2:
        print("Error: Must specify at least 2 outcomes.", file=sys.stderr)
        sys.exit(1)

    # Generate symbol if not provided
    symbol = args.symbol or "".join(w[0] for w in args.title.split()[:4]).upper()

    # Compute end timestamp
    if args.end_date:
        end_dt = datetime.fromisoformat(args.end_date)
    else:
        end_dt = datetime.utcnow() + timedelta(days=args.duration_days)
    end_ts = int(end_dt.timestamp())

    print(f"\n{'[DRY RUN] ' if args.dry_run else ''}Creating Prediction Market on Basis")
    print("=" * 60)
    print(f"  Title:           {args.title}")
    print(f"  Symbol:          {symbol}")
    print(f"  Outcomes ({len(outcomes)}):   {', '.join(outcomes)}")
    print(f"  Closes:          {end_dt.strftime('%Y-%m-%d %H:%M UTC')}")
    print(f"  Bonding:         {args.bonding}")
    print(f"  Frozen:          {'Yes' if args.frozen else 'No'}")
    print(f"  Type:            {'Private' if args.private else 'Public'}")
    print(f"  Creator fee:     20% of all trading fees (forever)")
    print(f"  Airdrop points:  300 pts (if ≥5 unique participants)")
    print()

    if args.dry_run:
        print("[DRY RUN] Transaction would be submitted here. No action taken.")
        result = {
            "status": "dry_run",
            "market_title": args.title,
            "symbol": symbol,
            "outcomes": outcomes,
            "end_timestamp": end_ts,
            "bonding": args.bonding,
            "frozen": args.frozen,
            "private": args.private,
        }
    else:
        client = get_client(require_write=True)

        try:
            if args.private:
                # Private market: creator-managed resolution
                tx_result = client.private_markets.create_market(
                    args.title, symbol, end_ts,
                    outcomes, MAINTOKEN, args.frozen, args.bonding
                )
            else:
                # Public market: community dispute resolution
                tx_result = client.prediction_markets.create_market(
                    args.title, symbol, end_ts,
                    outcomes, MAINTOKEN, args.frozen, args.bonding
                )

            print(f"\n✅ Market created!")
            print(f"  Tx hash: {tx_result['hash']}")

            result = {
                "status": "success",
                "tx_hash": tx_result["hash"],
                "market_title": args.title,
                "symbol": symbol,
                "outcomes": outcomes,
                "end_timestamp": end_ts,
            }

        except Exception as e:
            print(f"\n❌ Market creation failed: {e}", file=sys.stderr)
            sys.exit(1)

    output_result(result, args.json_output)

    if not args.json_output:
        if args.dry_run:
            print("\n✅ Market creation simulated successfully.")
        print(f"\nNext steps:")
        print(f"  1. Buy shares in your preferred outcome: python bet.py --market <address> --outcome 'Yes' --amount 50")
        print(f"  2. Share the market — every trade earns you 20% of fees")
        print(f"  3. High-volume multi-outcome markets earn the most creator fees")


if __name__ == "__main__":
    main()
