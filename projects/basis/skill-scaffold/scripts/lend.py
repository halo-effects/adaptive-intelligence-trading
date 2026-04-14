"""
lend.py — Take, manage, and repay loans on Basis (BNB Chain)

Borrow USDC at 100% LTV against any Basis token collateral via the LoanHub contract.
No price liquidation — only time-based expiry. Tokens held by loan contract during term.

SDK: client.loans.take_loan() / repay_loan() / extend_loan() / increase_loan()
     client.loans.get_user_loan_details() / get_user_loan_count()

Loan fees (confirmed from contract):
- Origination: 2.0% flat (staticFeePercentage=200)
- Daily interest: 0.005% per day (dynamicFeePercentage=5)
- Formula: total_fee = 2.0% + (0.005% × days)
- Min loan duration: 10 days

Usage:
    python lend.py --action borrow --token 0xTOKEN --token-amount 100 --duration-days 30
    python lend.py --action extend --loan-id 5 --extend-days 15
    python lend.py --action repay --loan-id 5
    python lend.py --action status --wallet 0xWALLET
"""

import argparse
import json
import os
import sys
from dotenv import load_dotenv

load_dotenv()

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from client_helper import get_client, token_to_raw, raw_to_usdc, output_result, MAINTOKEN


def parse_args():
    parser = argparse.ArgumentParser(
        description="Manage loans on Basis — 100% LTV, no price liquidation"
    )
    parser.add_argument("--action", required=True,
                        choices=["borrow", "extend", "repay", "increase", "status"],
                        help="Loan action")
    parser.add_argument("--token", help="Collateral token address (for borrow/increase)")
    parser.add_argument("--token-amount", type=float, help="Number of tokens to lock as collateral")
    parser.add_argument("--loan-id", type=int, help="Loan ID (for extend/repay/increase/status)")
    parser.add_argument("--duration-days", type=int, default=30,
                        help="Loan duration in days (default: 30, min: 10)")
    parser.add_argument("--extend-days", type=int, default=30,
                        help="Days to extend (for extend action)")
    parser.add_argument("--pay-in-usdc", action="store_true",
                        help="Pay extension fee in USDC (for extend)")
    parser.add_argument("--refinance", action="store_true",
                        help="Refinance at current rates (for extend)")
    parser.add_argument("--wallet", default=os.getenv("BASIS_WALLET_ADDRESS"),
                        help="Wallet address (for status)")
    parser.add_argument("--dry-run", action="store_true", help="Simulate without submitting")
    parser.add_argument("--json-output", action="store_true", help="Output as JSON")
    return parser.parse_args()


def estimate_fees(duration_days: int, token_amount: float = 0) -> dict:
    """Estimate loan fees based on confirmed contract parameters."""
    origination_pct = 2.0  # staticFeePercentage=200 (basis points)
    daily_pct = 0.005  # dynamicFeePercentage=5 (basis points per day)
    total_pct = origination_pct + (daily_pct * duration_days)
    return {
        "origination": f"{origination_pct}%",
        "daily_interest": f"{daily_pct}%/day",
        "total_fee_pct": f"{total_pct:.3f}%",
        "duration_days": duration_days,
    }


def main():
    args = parse_args()

    if args.duration_days < 10 and args.action == "borrow":
        print("Error: Minimum loan duration is 10 days.", file=sys.stderr)
        sys.exit(1)

    print(f"\n{'[DRY RUN] ' if args.dry_run else ''}Basis Lending — {args.action.upper()}")
    print("=" * 60)

    if args.action == "borrow":
        if not args.token or not args.token_amount:
            print("Error: --token and --token-amount required for borrow", file=sys.stderr)
            sys.exit(1)

        fees = estimate_fees(args.duration_days)
        print(f"  Collateral:      {args.token}")
        print(f"  Token amount:    {args.token_amount}")
        print(f"  Duration:        {args.duration_days} days")
        print(f"  LTV:             100% of floor price value")
        print(f"  Fees:            {fees['total_fee_pct']} total ({fees['origination']} + {fees['daily_interest']} × {args.duration_days}d)")
        print(f"  Liquidation:     TIME ONLY — never from price drops")
        print(f"  Airdrop points:  200 base + 1 pt/day")

    elif args.action == "extend":
        if args.loan_id is None:
            print("Error: --loan-id required for extend", file=sys.stderr)
            sys.exit(1)
        print(f"  Loan ID:         {args.loan_id}")
        print(f"  Extend by:       {args.extend_days} days")
        print(f"  Pay in USDC:     {'Yes' if args.pay_in_usdc else 'No'}")
        print(f"  Refinance:       {'Yes' if args.refinance else 'No'}")
        print(f"  Airdrop points:  100 pts")

    elif args.action == "repay":
        if args.loan_id is None:
            print("Error: --loan-id required for repay", file=sys.stderr)
            sys.exit(1)
        print(f"  Loan ID:         {args.loan_id}")
        print(f"  Action:          Repay in full, release collateral")

    elif args.action == "increase":
        if args.loan_id is None or not args.token_amount:
            print("Error: --loan-id and --token-amount required for increase", file=sys.stderr)
            sys.exit(1)
        print(f"  Loan ID:         {args.loan_id}")
        print(f"  Additional:      {args.token_amount} tokens")

    elif args.action == "status":
        pass

    if args.dry_run:
        print(f"\n[DRY RUN] No transactions submitted.")
        result = {"status": "dry_run", "action": args.action}
    else:
        client = get_client(require_write=(args.action != "status"))

        try:
            if args.action == "borrow":
                token_raw = token_to_raw(args.token_amount)
                tx_result = client.loans.take_loan(
                    MAINTOKEN, args.token, token_raw, args.duration_days
                )
                print(f"\n✅ Loan taken!")
                print(f"  Tx hash: {tx_result['hash']}")
                result = {"status": "success", "tx_hash": tx_result["hash"], "action": "borrow"}

            elif args.action == "extend":
                tx_result = client.loans.extend_loan(
                    args.loan_id, args.extend_days, args.pay_in_usdc, args.refinance
                )
                print(f"\n✅ Loan extended by {args.extend_days} days!")
                print(f"  Tx hash: {tx_result['hash']}")
                result = {"status": "success", "tx_hash": tx_result["hash"], "action": "extend"}

            elif args.action == "repay":
                tx_result = client.loans.repay_loan(args.loan_id)
                print(f"\n✅ Loan repaid! Collateral released.")
                print(f"  Tx hash: {tx_result['hash']}")
                result = {"status": "success", "tx_hash": tx_result["hash"], "action": "repay"}

            elif args.action == "increase":
                token_raw = token_to_raw(args.token_amount)
                tx_result = client.loans.increase_loan(args.loan_id, token_raw)
                print(f"\n✅ Collateral increased!")
                print(f"  Tx hash: {tx_result['hash']}")
                result = {"status": "success", "tx_hash": tx_result["hash"], "action": "increase"}

            elif args.action == "status":
                wallet = args.wallet
                if not wallet:
                    print("Error: --wallet required for status", file=sys.stderr)
                    sys.exit(1)
                loan_count = client.loans.get_user_loan_count(wallet)
                print(f"\n  Active loans: {loan_count}")
                loans = []
                for i in range(loan_count):
                    details = client.loans.get_user_loan_details(wallet, i)
                    print(f"\n  Loan #{i}: {details}")
                    loans.append(details)
                result = {"status": "success", "action": "status", "loan_count": loan_count, "loans": loans}

        except Exception as e:
            print(f"\n❌ Loan {args.action} failed: {e}", file=sys.stderr)
            sys.exit(1)

    output_result(result, args.json_output)

    if not args.json_output and not args.dry_run and args.action == "borrow":
        print(f"\nCapital recycling tip:")
        print(f"  Redeploy borrowed USDC → bet.py (predictions) or trade.py (more tokens)")
        print(f"  As collateral appreciates, extend + refinance for more USDC")


if __name__ == "__main__":
    main()
