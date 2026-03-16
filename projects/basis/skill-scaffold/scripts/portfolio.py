"""
portfolio.py — Check balances, positions, and P&L on Basis

Full portfolio summary using the SDK's off-chain API (trades, balances) combined
with on-chain reads (prices, loan details, vault positions).

SDK: client.api.get_wallet_transactions() / get_tokens()
     client.trading.get_usd_price()
     client.loans.get_user_loan_count() / get_user_loan_details()
     client.staking.get_available_stasis() / convert_to_assets()
     client.trading.get_leverage_count() / get_leverage_position()

Usage:
    python portfolio.py --wallet 0xYOUR_WALLET
    python portfolio.py --wallet 0xYOUR_WALLET --section predictions --json-output
"""

import argparse
import json
import os
import sys
from dotenv import load_dotenv

load_dotenv()

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from client_helper import get_client, raw_to_usdc, raw_to_token, output_result


def parse_args():
    parser = argparse.ArgumentParser(
        description="Check portfolio, positions, and P&L on Basis"
    )
    parser.add_argument("--wallet", default=os.getenv("BASIS_WALLET_ADDRESS"),
                        help="Wallet address (0x...)")
    parser.add_argument("--section",
                        choices=["all", "trades", "loans", "leverage", "vault"],
                        default="all", help="Portfolio section (default: all)")
    parser.add_argument("--trade-limit", type=int, default=20,
                        help="Max trades to fetch (default: 20)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Show what would be fetched without API calls")
    parser.add_argument("--json-output", action="store_true", help="Output as JSON")
    return parser.parse_args()


def fetch_trades(client, wallet: str, limit: int = 20) -> list:
    """Fetch recent wallet transactions."""
    try:
        result = client.api.get_wallet_transactions(wallet, limit=limit)
        return result.get("data", [])
    except Exception as e:
        print(f"  ⚠️  Could not fetch trades: {e}")
        return []


def fetch_loans(client, wallet: str) -> list:
    """Fetch all loan positions."""
    try:
        count = client.loans.get_user_loan_count(wallet)
        loans = []
        for i in range(count):
            details = client.loans.get_user_loan_details(wallet, i)
            loans.append({"id": i, "details": details})
        return loans
    except Exception as e:
        print(f"  ⚠️  Could not fetch loans: {e}")
        return []


def fetch_leverage(client, wallet: str) -> list:
    """Fetch all leverage positions."""
    try:
        count = client.trading.get_leverage_count(wallet)
        positions = []
        for i in range(count):
            pos = client.trading.get_leverage_position(wallet, i)
            positions.append({"id": i, "position": pos})
        return positions
    except Exception as e:
        print(f"  ⚠️  Could not fetch leverage positions: {e}")
        return []


def fetch_vault(client, wallet: str) -> dict:
    """Fetch vault (wSTASIS) position."""
    try:
        available = client.staking.get_available_stasis(wallet)
        return {"available_stasis": str(available)}
    except Exception as e:
        print(f"  ⚠️  Could not fetch vault data: {e}")
        return {}


def main():
    args = parse_args()

    if not args.wallet:
        print("Error: --wallet required (or set BASIS_WALLET_ADDRESS env var)", file=sys.stderr)
        sys.exit(1)

    wallet_short = f"{args.wallet[:10]}...{args.wallet[-6:]}"
    print(f"\n{'[DRY RUN] ' if args.dry_run else ''}Basis Portfolio — {wallet_short}")
    print("=" * 60)

    if args.dry_run:
        print(f"\n[DRY RUN] Would fetch:")
        print(f"  Wallet transactions (limit {args.trade_limit})")
        print(f"  Loan positions")
        print(f"  Leverage positions")
        print(f"  Vault (wSTASIS) balance")
        print(f"  Token prices for all held assets")
        result = {"status": "dry_run", "wallet": args.wallet, "section": args.section}
    else:
        client = get_client(require_write=False)
        portfolio = {"wallet": args.wallet}

        if args.section in ("all", "trades"):
            print(f"\n📊 Recent Trades")
            print("-" * 40)
            trades = fetch_trades(client, args.wallet, args.trade_limit)
            portfolio["trades"] = trades
            if trades:
                for t in trades[:10]:  # Show first 10
                    print(f"  {t}")
            else:
                print("  No trades found.")

        if args.section in ("all", "loans"):
            print(f"\n🏦 Loans")
            print("-" * 40)
            loans = fetch_loans(client, args.wallet)
            portfolio["loans"] = loans
            if loans:
                for loan in loans:
                    print(f"  Loan #{loan['id']}: {loan['details']}")
            else:
                print("  No active loans.")

        if args.section in ("all", "leverage"):
            print(f"\n⚡ Leverage Positions")
            print("-" * 40)
            leverage = fetch_leverage(client, args.wallet)
            portfolio["leverage"] = leverage
            if leverage:
                for pos in leverage:
                    print(f"  Position #{pos['id']}: {pos['position']}")
            else:
                print("  No leverage positions.")

        if args.section in ("all", "vault"):
            print(f"\n🏛️ STASIS Vault (wSTASIS)")
            print("-" * 40)
            vault = fetch_vault(client, args.wallet)
            portfolio["vault"] = vault
            if vault:
                for k, v in vault.items():
                    print(f"  {k}: {v}")
            else:
                print("  No vault position.")

        result = {"status": "success", "portfolio": portfolio}

    output_result(result, args.json_output)

    if not args.json_output:
        print(f"\n✅ Portfolio check {'simulated' if args.dry_run else 'complete'}.")


if __name__ == "__main__":
    main()
