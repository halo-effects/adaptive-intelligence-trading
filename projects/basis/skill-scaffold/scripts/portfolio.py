"""
portfolio.py — Check balances, positions, and P&L on Basis

Full portfolio summary including net P&L tracked from day one (even during USDB
testing phase). Agents can use this to optimize strategy, generate shareable
P&L receipts, and feed into automated decision-making.

Data returned:
- Net P&L (deposited - spent + received)
- Prediction market positions (bets, win rate, P&L)
- Trading positions (volume, P&L)
- Token holdings with current floor + spot values
- Active loans and vault positions
- Creator fees earned
- Gas costs (BNB spent on contract interactions)

Usage:
    python portfolio.py --wallet 0xYOUR_WALLET
    python portfolio.py --wallet 0xYOUR_WALLET --section predictions --json-output
    python portfolio.py --wallet 0xYOUR_WALLET --receipt   # shareable P&L card
"""

import argparse
import json
import os
import sys
from dotenv import load_dotenv

load_dotenv()


def parse_args():
    parser = argparse.ArgumentParser(
        description="Check portfolio, positions, and P&L on Basis"
    )
    parser.add_argument(
        "--wallet",
        default=os.getenv("BASIS_WALLET_ADDRESS"),
        help="Wallet address to check (0x...)"
    )
    parser.add_argument(
        "--section",
        choices=["all", "predictions", "trading", "lending", "vault", "tokens", "fees"],
        default="all",
        help="Portfolio section to display (default: all)"
    )
    parser.add_argument(
        "--receipt",
        action="store_true",
        help="Generate a shareable P&L receipt (for social posting — earns 50-75 airdrop pts)"
    )
    parser.add_argument(
        "--period",
        choices=["24h", "7d", "30d", "all"],
        default="all",
        help="Time period for P&L calculation"
    )
    parser.add_argument(
        "--api-base",
        default=os.getenv("BASIS_API_BASE", "https://api.basis.exchange"),
        help="Basis API base URL"
    )
    parser.add_argument(
        "--rpc-url",
        default=os.getenv("BASIS_RPC_URL", "https://bsc-dataseed.binance.org/"),
        help="BNB Chain RPC URL"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be fetched without making API calls"
    )
    parser.add_argument(
        "--json-output",
        action="store_true",
        help="Output as JSON"
    )
    return parser.parse_args()


def format_pnl(value: float) -> str:
    sign = "+" if value >= 0 else ""
    return f"{sign}${value:,.2f}"


def main():
    args = parse_args()

    if not args.wallet:
        print("Error: --wallet required (or set BASIS_WALLET_ADDRESS env var)", file=sys.stderr)
        sys.exit(1)

    print(f"\n{'[DRY RUN] ' if args.dry_run else ''}Basis Portfolio — {args.wallet[:10]}...{args.wallet[-6:]}")
    print("=" * 60)

    if args.dry_run:
        print(f"\n[DRY RUN] Would fetch portfolio data from:")
        print(f"  GET {args.api_base}/api/v1/portfolio/{args.wallet}")
        print(f"  Section: {args.section}")
        print(f"  Period:  {args.period}")
        print()
        print(f"  Expected response structure:")
        mock = {
            "wallet": args.wallet,
            "net_pnl": 0.0,
            "gross_volume": 0.0,
            "predictions": {
                "bets_placed": 0,
                "bets_won": 0,
                "net_pnl": 0.0,
                "win_rate": "0%",
                "markets_created": 0,
                "creator_fees_earned": 0.0,
            },
            "trading": {
                "trades": 0,
                "net_pnl": 0.0,
                "volume": 0.0,
            },
            "lending": {
                "active_loans": 0,
                "total_borrowed": 0.0,
                "collateral_locked_value": 0.0,
            },
            "vault": {
                "wstasis_balance": 0.0,
                "stasis_value": 0.0,
                "unrealized_yield": 0.0,
                "outstanding_loan": 0.0,
            },
            "fees_earned": 0.0,
            "creation_costs": {"bnb_spent": 0.0},
        }
        result = {"status": "dry_run", "portfolio": mock}
    else:
        # TODO: Implement using basis-sdk / API call
        # Example flow:
        #
        # import requests
        # resp = requests.get(f"{args.api_base}/api/v1/portfolio/{args.wallet}")
        # portfolio = resp.json()
        #
        # Also fetch on-chain data directly:
        # from web3 import Web3
        # w3 = Web3(Web3.HTTPProvider(args.rpc_url))
        # stasis_balance = stasis_contract.functions.balanceOf(args.wallet).call()
        # wstasis_balance = vault_contract.functions.balanceOf(args.wallet).call()
        # ...
        #
        # Combine API + on-chain data for full picture

        print("ERROR: basis-sdk not yet available. Use --dry-run to simulate.")
        sys.exit(1)

    if args.receipt:
        print(f"\n📊 P&L Receipt — Share this to earn 50-75 airdrop points!")
        print(f"┌──────────────────────────────────────┐")
        print(f"│  🦞 Basis Agent P&L Report           │")
        print(f"│  Period: {args.period:<28s} │")
        print(f"│  Wallet: {args.wallet[:8]}...{args.wallet[-4:]:<15s} │")
        print(f"│  Net P&L: $0.00 (TODO: real data)    │")
        print(f"│  Trades: 0 | Win Rate: 0%            │")
        print(f"│  basis.exchange                       │")
        print(f"└──────────────────────────────────────┘")
        print(f"\nShare this on X with @LaunchOnBasis → earn social engagement points")

    if args.json_output:
        print(json.dumps(result, indent=2))
    else:
        print(f"\n✅ Portfolio check {'simulated' if args.dry_run else 'complete'}.")


if __name__ == "__main__":
    main()
