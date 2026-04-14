"""
vault.py — Manage the STASIS Vault (wSTASIS) on Basis

The wSTASIS vault wraps STASIS into appreciating shares. Platform fees inject as
STASIS, mechanically increasing the STASIS:wSTASIS ratio. Locked wSTASIS can be
used as loan collateral WITHOUT leaving the vault.

SDK: client.staking.buy() / sell() / lock() / unlock() / borrow() / repay()
     client.staking.convert_to_shares() / convert_to_assets() / get_available_stasis()

Key mechanics:
- Wrap STASIS → wSTASIS (appreciation tracking shares)
- Lock wSTASIS → borrow USDC against it (stays in vault, keeps earning)
- As ratio grows, refinance for additional USDC
- Two variables to manage: refinance threshold + loan expiry
- Airdrop points: 2 pts per $1 per day staked; refinance = 150 pts

Usage:
    python vault.py --action stake --amount 100
    python vault.py --action lock --amount 50
    python vault.py --action borrow --stasis-amount 50 --duration-days 30
    python vault.py --action refinance
    python vault.py --action status
"""

import argparse
import json
import os
import sys
from dotenv import load_dotenv

load_dotenv()

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from client_helper import get_client, token_to_raw, raw_to_token, output_result


def parse_args():
    parser = argparse.ArgumentParser(
        description="Manage STASIS Vault (wSTASIS) on Basis — stake, lock, borrow, refinance"
    )
    parser.add_argument("--action", required=True,
                        choices=["stake", "unstake", "lock", "unlock", "borrow", "repay",
                                 "extend-loan", "refinance", "status"],
                        help="Vault action")
    parser.add_argument("--amount", type=float, help="STASIS amount (for stake/unstake) or wSTASIS shares (for lock/unlock)")
    parser.add_argument("--stasis-amount", type=float, help="STASIS amount to borrow against (for borrow)")
    parser.add_argument("--duration-days", type=int, default=30, help="Loan duration in days (for borrow)")
    parser.add_argument("--extend-days", type=int, default=30, help="Days to add (for extend-loan)")
    parser.add_argument("--pay-in-usdc", action="store_true", help="Pay extension fee in USDC")
    parser.add_argument("--claim-usdc", action="store_true", help="Claim accrued USDC when unstaking")
    parser.add_argument("--wallet", default=os.getenv("BASIS_WALLET_ADDRESS"), help="Wallet address (for status)")
    parser.add_argument("--dry-run", action="store_true", help="Simulate without submitting")
    parser.add_argument("--json-output", action="store_true", help="Output as JSON")
    return parser.parse_args()


def main():
    args = parse_args()

    print(f"\n{'[DRY RUN] ' if args.dry_run else ''}STASIS Vault — {args.action.upper()}")
    print("=" * 60)

    if args.action == "stake":
        if not args.amount:
            print("Error: --amount required for stake", file=sys.stderr)
            sys.exit(1)
        print(f"  STASIS to wrap:  {args.amount}")
        print(f"  Receive:         wSTASIS (appreciating ratio token)")
        print(f"  Yield source:    Platform fees → STASIS → ratio increase")
        print(f"  Airdrop points:  2 pts per $1 per day")

    elif args.action == "unstake":
        if not args.amount:
            print("Error: --amount required for unstake (wSTASIS shares)", file=sys.stderr)
            sys.exit(1)
        print(f"  wSTASIS shares:  {args.amount}")
        print(f"  Claim USDC:      {'Yes' if args.claim_usdc else 'No'}")

    elif args.action == "lock":
        if not args.amount:
            print("Error: --amount required for lock (wSTASIS shares)", file=sys.stderr)
            sys.exit(1)
        print(f"  Lock wSTASIS:    {args.amount} shares")
        print(f"  Purpose:         Enable borrowing against locked collateral")

    elif args.action == "unlock":
        if not args.amount:
            print("Error: --amount required for unlock (wSTASIS shares)", file=sys.stderr)
            sys.exit(1)
        print(f"  Unlock wSTASIS:  {args.amount} shares")

    elif args.action == "borrow":
        if not args.stasis_amount:
            print("Error: --stasis-amount required for borrow", file=sys.stderr)
            sys.exit(1)
        print(f"  Borrow against:  {args.stasis_amount} STASIS worth of locked wSTASIS")
        print(f"  Duration:        {args.duration_days} days")
        print(f"  ✅ wSTASIS stays in vault — keeps earning yield while borrowed against")

    elif args.action == "repay":
        print(f"  Action:          Repay staking loan in full")

    elif args.action == "extend-loan":
        print(f"  Extend by:       {args.extend_days} days")
        print(f"  Pay in USDC:     {'Yes' if args.pay_in_usdc else 'No'}")

    elif args.action == "refinance":
        print(f"  Action:          Check ratio growth → extend/reborrow at new value")
        print(f"  Result:          Extract additional USDC from vault appreciation")
        print(f"  Airdrop points:  150 pts")

    if args.dry_run:
        # Show conversion preview
        if args.amount and args.action in ("stake", "unstake"):
            try:
                client = get_client(require_write=False)
                if args.action == "stake":
                    shares = client.staking.convert_to_shares(token_to_raw(args.amount))
                    print(f"\n  Preview: {args.amount} STASIS → {shares} wSTASIS shares")
                else:
                    assets = client.staking.convert_to_assets(token_to_raw(args.amount))
                    print(f"\n  Preview: {args.amount} wSTASIS shares → {assets} STASIS")
            except Exception:
                pass

        print(f"\n[DRY RUN] No transactions submitted.")
        result = {"status": "dry_run", "action": args.action}
    else:
        client = get_client(require_write=(args.action != "status"))

        try:
            if args.action == "stake":
                stasis_raw = token_to_raw(args.amount)
                tx_result = client.staking.buy(stasis_raw)
                print(f"\n✅ STASIS wrapped into wSTASIS!")
                print(f"  Tx hash: {tx_result['hash']}")
                result = {"status": "success", "tx_hash": tx_result["hash"], "action": "stake"}

            elif args.action == "unstake":
                shares_raw = token_to_raw(args.amount)
                tx_result = client.staking.sell(shares_raw, args.claim_usdc)
                print(f"\n✅ wSTASIS unwrapped to STASIS!")
                print(f"  Tx hash: {tx_result['hash']}")
                result = {"status": "success", "tx_hash": tx_result["hash"], "action": "unstake"}

            elif args.action == "lock":
                shares_raw = token_to_raw(args.amount)
                tx_result = client.staking.lock(shares_raw)
                print(f"\n✅ wSTASIS locked as collateral!")
                print(f"  Tx hash: {tx_result['hash']}")
                result = {"status": "success", "tx_hash": tx_result["hash"], "action": "lock"}

            elif args.action == "unlock":
                shares_raw = token_to_raw(args.amount)
                tx_result = client.staking.unlock(shares_raw)
                print(f"\n✅ wSTASIS unlocked!")
                print(f"  Tx hash: {tx_result['hash']}")
                result = {"status": "success", "tx_hash": tx_result["hash"], "action": "unlock"}

            elif args.action == "borrow":
                stasis_raw = token_to_raw(args.stasis_amount)
                tx_result = client.staking.borrow(stasis_raw, args.duration_days)
                print(f"\n✅ Borrowed against locked wSTASIS!")
                print(f"  Tx hash: {tx_result['hash']}")
                result = {"status": "success", "tx_hash": tx_result["hash"], "action": "borrow"}

            elif args.action == "repay":
                tx_result = client.staking.repay()
                print(f"\n✅ Staking loan repaid!")
                print(f"  Tx hash: {tx_result['hash']}")
                result = {"status": "success", "tx_hash": tx_result["hash"], "action": "repay"}

            elif args.action == "extend-loan":
                tx_result = client.staking.extend_loan(
                    args.extend_days, args.pay_in_usdc, False
                )
                print(f"\n✅ Staking loan extended by {args.extend_days} days!")
                print(f"  Tx hash: {tx_result['hash']}")
                result = {"status": "success", "tx_hash": tx_result["hash"], "action": "extend-loan"}

            elif args.action == "refinance":
                # Refinance = extend loan + borrow additional based on appreciation
                # Check available STASIS first
                wallet = args.wallet or client.wallet_address
                available = client.staking.get_available_stasis(wallet)
                print(f"\n  Available STASIS for borrowing: {available}")

                if int(available) > 0:
                    # Extend existing loan and borrow more
                    tx_result = client.staking.extend_loan(30, True, True)  # refinance=True
                    print(f"\n✅ Vault refinanced!")
                    print(f"  Tx hash: {tx_result['hash']}")
                    result = {"status": "success", "tx_hash": tx_result["hash"], "action": "refinance"}
                else:
                    print(f"  No additional STASIS available for refinancing.")
                    result = {"status": "no_action", "reason": "no additional collateral available"}

            elif args.action == "status":
                wallet = args.wallet
                if not wallet:
                    print("Error: --wallet required for status", file=sys.stderr)
                    sys.exit(1)
                available = client.staking.get_available_stasis(wallet)
                print(f"\n  Available STASIS: {available}")
                result = {"status": "success", "action": "status", "available_stasis": str(available)}

        except Exception as e:
            print(f"\n❌ Vault {args.action} failed: {e}", file=sys.stderr)
            sys.exit(1)

    output_result(result, args.json_output)

    if not args.json_output and not args.dry_run and args.action == "stake":
        print(f"\nNext: Lock wSTASIS → borrow USDC → redeploy. Your position earns yield the whole time.")


if __name__ == "__main__":
    main()
