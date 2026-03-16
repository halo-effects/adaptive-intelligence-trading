"""
bet.py — Place a bet on a Predict+ prediction market outcome on Basis

Buys shares in a specific prediction outcome via the MarketTrading contract.
Winner takes the ENTIRE losing pool — not capped at $1/share like Polymarket.

SDK: client.prediction_markets.buy() + client.market_reader.get_all_outcomes()

Key mechanics:
- Multi-outcome markets can deliver up to 15x or more returns
- Sellers can only sell to next buyer, NOT against pool (protects winning pool)
- Post-resolution: selling BURNS tokens → fees inject → price goes UP
- Supports hybrid fills: AMM + order book in single transaction
- Airdrop points: 1 pt per $1 volume

Usage:
    python bet.py --market 0xMARKET_ADDRESS --outcome-id 0 --amount 100
    python bet.py --market 0xMARKET_ADDRESS --outcome-id 1 --amount 50 --dry-run
"""

import argparse
import json
import os
import sys
from dotenv import load_dotenv

load_dotenv()

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from client_helper import get_client, usdc_to_raw, raw_to_usdc, raw_to_token, output_result, USDC, MARKET_TRADING


def parse_args():
    parser = argparse.ArgumentParser(
        description="Place a bet on a Predict+ market outcome on Basis"
    )
    parser.add_argument("--market", required=True, help="Prediction market token address (0x...)")
    parser.add_argument("--outcome-id", type=int, required=True, help="Outcome index (0-based)")
    parser.add_argument("--amount", type=float, required=True, help="USDC amount to bet")
    parser.add_argument("--min-shares", type=int, default=0, help="Minimum shares to receive (slippage protection)")
    parser.add_argument("--order-ids", help="Comma-separated order IDs to fill from book (hybrid fill)")
    parser.add_argument("--show-odds", action="store_true", help="Show current market odds before betting")
    parser.add_argument("--dry-run", action="store_true", help="Simulate without submitting")
    parser.add_argument("--json-output", action="store_true", help="Output as JSON")
    return parser.parse_args()


def show_market_odds(client, market_address: str):
    """Display current outcome probabilities and pool sizes."""
    try:
        outcomes = client.market_reader.get_all_outcomes(MARKET_TRADING, market_address)
        print(f"\n  Current Market Odds:")
        for i, outcome in enumerate(outcomes):
            print(f"    [{i}] {outcome}")
        return outcomes
    except Exception as e:
        print(f"  ⚠️  Could not fetch market data: {e}")
        return None


def main():
    args = parse_args()

    # Safety check
    max_bet = float(os.getenv("MAX_BET_PER_MARKET", "100"))
    if args.amount > max_bet:
        print(f"Warning: Bet ${args.amount} exceeds MAX_BET_PER_MARKET=${max_bet}")
        print(f"Adjust MAX_BET_PER_MARKET in .env or reduce --amount")
        sys.exit(1)

    usdc_raw = usdc_to_raw(args.amount)

    print(f"\n{'[DRY RUN] ' if args.dry_run else ''}Placing Bet on Basis Prediction Market")
    print("=" * 60)
    print(f"  Market:          {args.market}")
    print(f"  Outcome ID:      {args.outcome_id}")
    print(f"  Bet Amount:      ${args.amount:.2f} USDC ({usdc_raw} raw)")
    print(f"  Min Shares:      {args.min_shares}")
    print(f"  Payout model:    Winner takes ENTIRE losing pool (uncapped)")

    if args.show_odds or args.dry_run:
        client = get_client(require_write=False)
        show_market_odds(client, args.market)

    if args.dry_run:
        # Preview expected shares
        try:
            client = get_client(require_write=False)
            wallet = os.getenv("BASIS_WALLET_ADDRESS", "0x0000000000000000000000000000000000000000")
            order_ids = [int(x) for x in args.order_ids.split(",")] if args.order_ids else []
            estimated = client.market_reader.estimate_shares_out(
                MARKET_TRADING, args.market, args.outcome_id,
                usdc_raw, order_ids, wallet
            )
            print(f"\n  Estimated shares: {estimated}")
        except Exception:
            pass

        print("\n[DRY RUN] Transaction would be submitted here. No action taken.")
        result = {
            "status": "dry_run",
            "market": args.market,
            "outcome_id": args.outcome_id,
            "amount_usdc": args.amount,
        }
    else:
        client = get_client(require_write=True)

        try:
            if args.order_ids:
                # Hybrid fill: order book + AMM in single transaction
                order_ids = [int(x) for x in args.order_ids.split(",")]
                tx_result = client.prediction_markets.buy_orders_and_contract(
                    args.market, args.outcome_id, order_ids,
                    USDC, usdc_raw, args.min_shares
                )
            else:
                # Pure AMM buy
                tx_result = client.prediction_markets.buy(
                    args.market, args.outcome_id, USDC,
                    usdc_raw, 0, args.min_shares
                )

            print(f"\n✅ Bet placed!")
            print(f"  Tx hash: {tx_result['hash']}")

            result = {
                "status": "success",
                "tx_hash": tx_result["hash"],
                "market": args.market,
                "outcome_id": args.outcome_id,
                "amount_usdc": args.amount,
            }

        except Exception as e:
            print(f"\n❌ Bet failed: {e}", file=sys.stderr)
            sys.exit(1)

    output_result(result, args.json_output)

    if not args.json_output and not args.dry_run:
        print(f"\nPost-resolution strategy:")
        print(f"  If you win: WAIT through the sell wave. Last sellers get the BEST price.")
        print(f"  Selling burns tokens → fees inject → price goes UP.")


if __name__ == "__main__":
    main()
