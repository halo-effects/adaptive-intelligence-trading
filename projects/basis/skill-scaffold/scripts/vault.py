"""
vault.py — Stake STASIS in the wSTASIS Vault on Basis

The wSTASIS vault is the "set and forget" treasury for agents. Stake STASIS,
receive wSTASIS (wrapped ratio token). Platform fees inject into the vault as
STASIS, increasing the STASIS:wSTASIS ratio. Only vault participants earn fees.

Key mechanics:
- wSTASIS can be used as 100% LTV loan collateral WITHOUT leaving the vault
- As wSTASIS appreciates, refinance loans for additional USDC (still earning, still in vault)
- One position serves 4 functions: yield + collateral + appreciation + USDC liquidity
- Interest on vault loans: very low single-digit APR
- Agent manages 2 variables: (1) refinance threshold, (2) loan expiry timer
- Airdrop points: 2 pts per $1 per day staked; refinance = 150 pts

Usage:
    python vault.py --action stake --amount 1000
    python vault.py --action refinance --threshold 0.05
    python vault.py --action status
    python vault.py --action unstake --amount 500 --dry-run
"""

import argparse
import json
import os
import sys
from dotenv import load_dotenv

load_dotenv()


def parse_args():
    parser = argparse.ArgumentParser(
        description="Manage STASIS Vault (wSTASIS) on Basis — stake, refinance, earn"
    )
    parser.add_argument(
        "--action",
        required=True,
        choices=["stake", "unstake", "refinance", "status"],
        help="Vault action: stake | unstake | refinance | status"
    )
    parser.add_argument(
        "--amount",
        type=float,
        help="STASIS amount to stake/unstake (in USDC equivalent)"
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=float(os.getenv("VAULT_REFINANCE_THRESHOLD", "0.05")),
        help="Refinance when wSTASIS appreciation exceeds threshold (default: 5%%)"
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
        help="Simulate without submitting"
    )
    parser.add_argument(
        "--json-output",
        action="store_true",
        help="Output as JSON"
    )
    return parser.parse_args()


def main():
    args = parse_args()

    print(f"\n{'[DRY RUN] ' if args.dry_run else ''}STASIS Vault — {args.action.upper()}")
    print("=" * 60)

    if args.action == "stake":
        print(f"  Amount:            ${args.amount:.2f} worth of STASIS")
        print(f"  Receive:           wSTASIS (wrapped ratio token)")
        print(f"  Yield source:      Platform fees injected as STASIS → ratio increases")
        print(f"  Loan eligible:     Yes — 100% LTV against wSTASIS, stays in vault")
        print(f"  Airdrop points:    2 pts per $1 per day staked")
        print()
        print(f"  How it works:")
        print(f"    1. STASIS goes into vault → you receive wSTASIS")
        print(f"    2. Platform fees flow in as STASIS → STASIS:wSTASIS ratio increases")
        print(f"    3. Your wSTASIS is worth more STASIS over time")
        print(f"    4. Borrow USDC against wSTASIS without leaving vault")
        print(f"    5. When ratio grows enough, refinance for more USDC")

    elif args.action == "unstake":
        print(f"  Amount:            ${args.amount:.2f} worth of wSTASIS to redeem")
        print(f"  Receive:           STASIS (at current wSTASIS:STASIS ratio)")
        print(f"  ⚠️  Unstaking ends yield earning for this amount")

    elif args.action == "refinance":
        print(f"  Threshold:         {args.threshold:.0%} wSTASIS appreciation")
        print(f"  Action:            Extend or create loan at new, higher wSTASIS value")
        print(f"  Result:            Additional USDC extracted, still earning in vault")
        print(f"  Airdrop points:    150 pts per refinance")
        print()
        print(f"  Agent strategy:")
        print(f"    1. Check wSTASIS ratio → has it appreciated >{args.threshold:.0%}?")
        print(f"    2. If yes → refinance loan (borrow more USDC against increased value)")
        print(f"    3. Deploy new USDC into predictions, trades, or more STASIS")
        print(f"    4. Repeat when threshold hit again (compound loop)")

    elif args.action == "status":
        print(f"  Fetching vault position...")
        print(f"  Will show: wSTASIS balance, current ratio, outstanding loans,")
        print(f"  available USDC to borrow, unrealized appreciation, daily yield estimate")

    if args.dry_run:
        print(f"\n[DRY RUN] No transactions submitted.")
        result = {
            "status": "dry_run",
            "action": args.action,
            "amount": args.amount,
            "refinance_threshold": args.threshold,
            "airdrop_points": {
                "stake": "2 pts/$1/day",
                "refinance": "150 pts",
            }[args.action] if args.action in ["stake", "refinance"] else 0,
        }
    else:
        # TODO: Implement using basis-sdk / direct contract call
        # Example flow for stake (pseudocode):
        #
        # from basis_sdk import BasisClient
        # client = BasisClient(private_key=args.wallet, rpc_url=args.rpc_url)
        #
        # stasis_balance = client.tokens.balance_of(STASIS_ADDRESS, client.wallet_address)
        # stasis_amount = args.amount  # convert USDC amount to STASIS tokens
        #
        # # Approve STASIS spend
        # client.tokens.approve(STASIS_ADDRESS, spender=VAULT_CONTRACT, amount=stasis_amount)
        #
        # # Stake into vault
        # tx = client.vault.stake(amount=stasis_amount)
        # receipt = client.wait_for_receipt(tx)
        #
        # wstasis_received = receipt.logs[...]  # parse Transfer event
        # ratio = client.vault.get_ratio()
        #
        # result = {
        #     "status": "success",
        #     "stasis_staked": stasis_amount,
        #     "wstasis_received": wstasis_received,
        #     "current_ratio": ratio,
        #     "tx_hash": receipt.transactionHash.hex(),
        # }

        print("ERROR: basis-sdk not yet available. Use --dry-run to simulate.")
        sys.exit(1)

    if args.json_output:
        print(json.dumps(result, indent=2))
    else:
        print(f"\n✅ Vault {args.action} {'simulated' if args.dry_run else 'complete'}.")
        if args.action == "stake":
            print(f"\nNext: Set up refinance-checker monitor to auto-refinance at {args.threshold:.0%}")
            print(f"      and loan-expiry-tracker to auto-extend vault loans.")


if __name__ == "__main__":
    main()
