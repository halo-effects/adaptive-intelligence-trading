"""
lend.py — Take or manage loans on Basis (BNB Chain)

Borrow USDC at 100% LTV against any Basis token collateral. No price liquidation —
only time-based expiry. Loans use the token's own internal liquidity (no external LPs).
Tokens are held by the loan contract and cannot be sold during the loan term.

Key mechanics:
- 100% LTV: borrow the full floor-price value of your tokens
- Liquidation = loan expiry ONLY (never from price drops)
- Interest: low single-digit APR (exact rate TBC)
- One variable to manage: loan expiry timer
- Airdrop points: 200 base + 1 pt/day active loan; extend = 100 pts

Usage:
    # Borrow USDC against Predict+ tokens
    python lend.py --action borrow --token 0xTOKEN --amount 500

    # Extend an existing loan before expiry
    python lend.py --action extend --loan-id 0xLOAN_ID --extend-days 30

    # Check loan status
    python lend.py --action status --loan-id 0xLOAN_ID --dry-run
"""

import argparse
import json
import os
import sys
from dotenv import load_dotenv

load_dotenv()


def parse_args():
    parser = argparse.ArgumentParser(
        description="Take or manage loans on Basis — 100% LTV, no price liquidation"
    )
    parser.add_argument(
        "--action",
        required=True,
        choices=["borrow", "extend", "repay", "status"],
        help="Loan action: borrow | extend | repay | status"
    )
    parser.add_argument(
        "--token",
        help="Token contract address to use as collateral (for borrow)"
    )
    parser.add_argument(
        "--amount",
        type=float,
        help="USDC amount to borrow (max = 100%% of token floor value)"
    )
    parser.add_argument(
        "--token-amount",
        type=float,
        help="Number of tokens to lock as collateral"
    )
    parser.add_argument(
        "--loan-id",
        help="Existing loan ID (for extend/repay/status)"
    )
    parser.add_argument(
        "--duration-days",
        type=int,
        default=30,
        help="Loan duration in days (default: 30)"
    )
    parser.add_argument(
        "--extend-days",
        type=int,
        default=30,
        help="Days to extend an existing loan (for extend action)"
    )
    parser.add_argument(
        "--auto-extend",
        action="store_true",
        default=os.getenv("AUTO_EXTEND_LOANS", "true").lower() == "true",
        help="Auto-extend loans before expiry (default from .env)"
    )
    parser.add_argument(
        "--wallet",
        default=os.getenv("BASIS_PRIVATE_KEY"),
        help="Agent wallet private key"
    )
    parser.add_argument(
        "--rpc-url",
        default=os.getenv("BASIS_RPC_URL", "https://bsc-dataseed.binance.org/"),
        help="BNB Chain RPC URL"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simulate without submitting any transactions"
    )
    parser.add_argument(
        "--json-output",
        action="store_true",
        help="Output result as JSON"
    )
    return parser.parse_args()


def main():
    args = parse_args()

    print(f"\n{'[DRY RUN] ' if args.dry_run else ''}Basis Lending — {args.action.upper()}")
    print("=" * 60)

    if args.action == "borrow":
        if not args.token:
            print("Error: --token required for borrow action", file=sys.stderr)
            sys.exit(1)

        print(f"  Collateral token: {args.token}")
        print(f"  Token amount:     {args.token_amount or 'all available'}")
        print(f"  Borrow amount:    ${args.amount or 'max (100% LTV)'} USDC")
        print(f"  Duration:         {args.duration_days} days")
        print(f"  Auto-extend:      {'Yes' if args.auto_extend else 'No'}")
        print(f"  LTV:              100% of floor price value")
        print(f"  Interest:         Low single-digit APR (near-negligible)")
        print(f"  Liquidation risk: TIME ONLY — loan expiry, never price")
        print(f"  Collateral note:  Tokens held by loan contract, cannot be sold during term")
        print(f"  Airdrop points:   200 base + 1 pt/day")
        print()
        print(f"  ⚠️  Leveraged tokens CANNOT be used as collateral (separate paths)")
        print(f"  ✅ Unleveraged tokens, Predict+ tokens, and wSTASIS are all eligible")

    elif args.action == "extend":
        if not args.loan_id:
            print("Error: --loan-id required for extend action", file=sys.stderr)
            sys.exit(1)
        print(f"  Loan ID:        {args.loan_id}")
        print(f"  Extend by:      {args.extend_days} days")
        print(f"  Airdrop points: 100 pts for extension")

    elif args.action == "repay":
        if not args.loan_id:
            print("Error: --loan-id required for repay action", file=sys.stderr)
            sys.exit(1)
        print(f"  Loan ID:        {args.loan_id}")
        print(f"  Action:         Repay loan, release collateral tokens")

    elif args.action == "status":
        print(f"  Loan ID:        {args.loan_id or 'all active loans'}")
        print(f"  Fetching loan status...")

    if args.dry_run:
        print(f"\n[DRY RUN] No transactions submitted.")
        result = {
            "status": "dry_run",
            "action": args.action,
            "token": args.token,
            "amount": args.amount,
            "duration_days": args.duration_days,
            "airdrop_points": 200 if args.action == "borrow" else 100 if args.action == "extend" else 0,
        }
    else:
        # TODO: Implement using basis-sdk / direct contract call
        # Example flow for borrow (pseudocode):
        #
        # from basis_sdk import BasisClient
        # client = BasisClient(private_key=args.wallet, rpc_url=args.rpc_url)
        #
        # # Check floor price to determine max borrow
        # floor_price = client.tokens.get_floor_price(args.token)
        # token_balance = client.tokens.balance_of(args.token, client.wallet_address)
        # max_borrow = floor_price * token_balance  # 100% LTV
        #
        # borrow_amount = args.amount or max_borrow
        # if borrow_amount > max_borrow:
        #     print(f"Error: requested ${borrow_amount} exceeds max borrow ${max_borrow}")
        #     sys.exit(1)
        #
        # # Approve token spend
        # client.tokens.approve(args.token, spender=LOAN_CONTRACT, amount=token_balance)
        #
        # # Create loan
        # tx = client.lending.borrow(
        #     token=args.token,
        #     token_amount=args.token_amount or token_balance,
        #     borrow_usdc=borrow_amount,
        #     duration_days=args.duration_days,
        # )
        # receipt = client.wait_for_receipt(tx)
        #
        # result = {
        #     "status": "success",
        #     "loan_id": receipt.logs[0].topics[1],
        #     "borrowed_usdc": borrow_amount,
        #     "collateral_locked": token_balance,
        #     "expiry_timestamp": ...,
        #     "tx_hash": receipt.transactionHash.hex(),
        # }

        print("ERROR: basis-sdk not yet available. Use --dry-run to simulate.")
        sys.exit(1)

    if args.json_output:
        print(json.dumps(result, indent=2))
    else:
        print(f"\n✅ Loan {args.action} {'simulated' if args.dry_run else 'complete'}.")
        if args.action == "borrow":
            print(f"\nCapital recycling tip:")
            print(f"  Redeploy borrowed USDC into predictions (bet.py) or new tokens (trade.py)")
            print(f"  As collateral appreciates, refinance for more USDC (Path B strategy)")
            print(f"  Set up loan-expiry-tracker monitor to auto-extend before expiry")


if __name__ == "__main__":
    main()
