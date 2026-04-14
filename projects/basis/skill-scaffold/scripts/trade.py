"""
trade.py — Buy or sell tokens on the Basis DEX (BNB Chain)

All tokens trade through the Basis SWAP contract with STASIS (MAINTOKEN) as base pair.
Supports spot buys/sells, percentage sells, and leveraged positions.

SDK: client.trading.buy() / sell() / sell_percentage() / leverage_buy()
     client.leverage_simulator.simulate_leverage() for preview

Key mechanics:
- USDC → MAINTOKEN → FactoryToken (3-hop path, handled automatically by SDK)
- Leverage is per-position via leverage_buy, NOT a global toggle
- Leveraged tokens held in leverage contract — cannot be used as loan collateral
- No price liquidation on leverage — calculated against floor price
- Airdrop points: 1 pt per $1 volume (min $10 per trade)

Usage:
    python trade.py --token 0xTOKEN --direction buy --amount 200
    python trade.py --token 0xTOKEN --direction sell --percentage 50
    python trade.py --token 0xTOKEN --direction buy --amount 100 --leverage --leverage-days 7
    python trade.py --token 0xTOKEN --direction buy --amount 50 --dry-run
"""

import argparse
import json
import os
import sys
from dotenv import load_dotenv

load_dotenv()

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from client_helper import get_client, usdc_to_raw, token_to_raw, raw_to_token, output_result, USDC, MAINTOKEN


def parse_args():
    parser = argparse.ArgumentParser(description="Buy or sell tokens on the Basis DEX")
    parser.add_argument("--token", required=True, help="Token contract address (0x...)")
    parser.add_argument("--direction", required=True, choices=["buy", "sell"], help="Trade direction")

    amount_group = parser.add_mutually_exclusive_group(required=True)
    amount_group.add_argument("--amount", type=float, help="USDC amount to spend (buy) or receive target (sell)")
    amount_group.add_argument("--token-amount", type=float, help="Exact number of tokens to sell")
    amount_group.add_argument("--percentage", type=int, help="Percentage of balance to sell (1-100)")

    parser.add_argument("--min-out", type=int, default=0, help="Minimum output (slippage protection, raw units)")
    parser.add_argument("--to-usdc", action="store_true", help="Sell all the way to USDC (3-hop for factory tokens)")

    # Leverage options (buy only)
    parser.add_argument("--leverage", action="store_true", help="Open a leveraged position")
    parser.add_argument("--leverage-days", type=int, default=7, help="Leverage loan duration in days (default: 7)")

    parser.add_argument("--dry-run", action="store_true", help="Simulate without submitting")
    parser.add_argument("--json-output", action="store_true", help="Output as JSON")
    return parser.parse_args()


def main():
    args = parse_args()

    # Safety checks
    max_trade = float(os.getenv("MAX_TRADE_SIZE", "500"))
    if args.amount and args.amount > max_trade:
        print(f"Warning: Trade ${args.amount} exceeds MAX_TRADE_SIZE=${max_trade}")
        sys.exit(1)

    if args.amount and args.amount < 10:
        print(f"Note: Minimum $10 per trade for airdrop points.")

    if args.leverage and args.direction == "sell":
        print("Error: --leverage only works with buy direction.", file=sys.stderr)
        sys.exit(1)

    if args.percentage and args.direction == "buy":
        print("Error: --percentage only works with sell direction.", file=sys.stderr)
        sys.exit(1)

    print(f"\n{'[DRY RUN] ' if args.dry_run else ''}{args.direction.upper()} on Basis DEX")
    print("=" * 60)
    print(f"  Token:           {args.token}")
    print(f"  Direction:       {args.direction}")

    if args.amount:
        print(f"  USDC amount:     ${args.amount:.2f} ({usdc_to_raw(args.amount)} raw)")
    elif args.token_amount:
        print(f"  Token amount:    {args.token_amount} ({token_to_raw(args.token_amount)} raw)")
    elif args.percentage:
        print(f"  Sell percentage: {args.percentage}% of balance")

    if args.leverage:
        print(f"  Leverage:        YES — {args.leverage_days} day loan")
        print(f"  ⚠️  Leveraged tokens held in leverage contract — cannot be used as loan collateral")
        print(f"  ✅ No price liquidation — calculated against floor price")

    if args.dry_run:
        client = get_client(require_write=False)

        # Preview swap output
        if args.direction == "buy" and args.amount:
            try:
                usdc_raw = usdc_to_raw(args.amount)
                path = [USDC, MAINTOKEN, args.token]

                if args.leverage:
                    sim = client.leverage_simulator.simulate_leverage(usdc_raw, path, args.leverage_days)
                    print(f"\n  Leverage simulation: {sim}")
                else:
                    expected = client.trading.get_amounts_out(usdc_raw, path)
                    print(f"\n  Expected output: {expected} raw tokens ({raw_to_token(int(expected)):.4f} tokens)")
            except Exception as e:
                print(f"\n  ⚠️  Preview failed: {e}")

        # Check current price
        try:
            price = client.trading.get_usd_price(args.token)
            print(f"  Current USD price: ${price}")
        except Exception:
            pass

        print("\n[DRY RUN] No action taken.")
        result = {
            "status": "dry_run",
            "token": args.token,
            "direction": args.direction,
            "amount_usdc": args.amount,
            "leverage": args.leverage,
        }
    else:
        client = get_client(require_write=True)

        try:
            if args.direction == "buy":
                usdc_raw = usdc_to_raw(args.amount)

                if args.leverage:
                    # Leveraged buy: protocol lends additional capital
                    path = [USDC, MAINTOKEN, args.token]
                    tx_result = client.trading.leverage_buy(
                        usdc_raw, args.min_out, path, args.leverage_days
                    )
                    print(f"\n✅ Leveraged buy executed!")
                else:
                    # Spot buy
                    tx_result = client.trading.buy(args.token, usdc_raw, args.min_out)
                    print(f"\n✅ Buy executed!")

            elif args.direction == "sell":
                if args.percentage:
                    tx_result = client.trading.sell_percentage(
                        args.token, args.percentage, args.to_usdc
                    )
                    print(f"\n✅ Sold {args.percentage}% of holdings!")
                elif args.token_amount:
                    token_raw = token_to_raw(args.token_amount)
                    tx_result = client.trading.sell(
                        args.token, token_raw, args.to_usdc, args.min_out
                    )
                    print(f"\n✅ Sell executed!")
                else:
                    # Sell by USDC target — sell tokens until reaching target USDC
                    # SDK doesn't have a direct "sell for X USDC" — use sell with amount
                    print("Error: Use --token-amount or --percentage for sells.", file=sys.stderr)
                    sys.exit(1)

            print(f"  Tx hash: {tx_result['hash']}")

            result = {
                "status": "success",
                "tx_hash": tx_result["hash"],
                "token": args.token,
                "direction": args.direction,
            }

        except Exception as e:
            print(f"\n❌ Trade failed: {e}", file=sys.stderr)
            sys.exit(1)

    output_result(result, args.json_output)

    if not args.json_output and not args.dry_run:
        if args.direction == "buy" and not args.leverage:
            print(f"\nTip: Borrow USDC against these tokens (100% LTV): python lend.py --action borrow --token {args.token}")


if __name__ == "__main__":
    main()
