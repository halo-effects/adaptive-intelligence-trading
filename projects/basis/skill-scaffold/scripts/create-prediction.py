"""
create-prediction.py — Create a Predict+ prediction market on Basis

Deploys a new prediction market with N outcomes. Each outcome gets a fresh
Stable+ (Predict+) token on its own bonding curve. Creator earns 20% of all
trading fees for the lifetime of the market.

Key mechanics:
- Minimum 5 unique participants required to earn creator airdrop points (300 pts)
- Multi-outcome markets have higher expected payouts than binary markets
- Tokens cost tiny BNB for gas (~0.0001 BNB) — tracked in net P&L
- Fresh bonding curve = max price impact from early volume

Usage:
    python create-prediction.py --title "Will ETH close above $4000 on March 20?" \\
        --outcomes "Yes,No" --duration-days 7

    python create-prediction.py --title "2026 BNB Q2 price bracket" \\
        --outcomes "Below $400,$400-$600,$600-$800,Above $800" \\
        --duration-days 90 --resolution-source chainlink_bnb_usd \\
        --dry-run
"""

import argparse
import json
import os
import sys
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()


def parse_args():
    parser = argparse.ArgumentParser(
        description="Create a Predict+ prediction market on Basis (BNB Chain)"
    )
    parser.add_argument(
        "--title",
        required=True,
        help="Market title / question (e.g. 'Will ETH close above $4000 on March 20?')"
    )
    parser.add_argument(
        "--outcomes",
        required=True,
        help="Comma-separated outcome names (e.g. 'Yes,No' or 'Team A,Team B,Draw')"
    )
    parser.add_argument(
        "--duration-days",
        type=int,
        default=7,
        help="Days until market resolves (default: 7)"
    )
    parser.add_argument(
        "--resolution-source",
        default="manual",
        help="Resolution oracle: manual | chainlink_eth_usd | chainlink_bnb_usd | pyth | custom"
    )
    parser.add_argument(
        "--resolution-date",
        help="Explicit resolution date (YYYY-MM-DD). Overrides --duration-days."
    )
    parser.add_argument(
        "--creator-fee",
        type=float,
        default=0.20,
        help="Creator fee as decimal (default: 0.20 = 20%% of all trading fees)"
    )
    parser.add_argument(
        "--min-participants",
        type=int,
        default=5,
        help="Min unique participants for airdrop points eligibility (default: 5)"
    )
    parser.add_argument(
        "--wallet",
        default=os.getenv("BASIS_PRIVATE_KEY"),
        help="Agent wallet private key (or set BASIS_PRIVATE_KEY env var)"
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
        help="Output result as JSON (for agent pipelines)"
    )
    return parser.parse_args()


def estimate_gas(num_outcomes: int) -> dict:
    """
    Estimate gas cost for prediction market creation.
    TODO: Replace with actual contract call estimate when basis-sdk available.
    """
    # Rough estimates: ~200k gas per outcome contract + 100k base
    estimated_gas = 100_000 + (num_outcomes * 200_000)
    gas_price_gwei = 3  # BNB Chain typical
    gas_cost_bnb = (estimated_gas * gas_price_gwei * 1e-9)
    gas_cost_usd = gas_cost_bnb * 600  # approximate BNB price
    return {
        "estimated_gas_units": estimated_gas,
        "gas_price_gwei": gas_price_gwei,
        "gas_cost_bnb": round(gas_cost_bnb, 6),
        "gas_cost_usd": round(gas_cost_usd, 4),
    }


def main():
    args = parse_args()

    outcomes = [o.strip() for o in args.outcomes.split(",")]
    if len(outcomes) < 2:
        print("Error: Must specify at least 2 outcomes.", file=sys.stderr)
        sys.exit(1)

    # Compute resolution timestamp
    if args.resolution_date:
        resolution_dt = datetime.fromisoformat(args.resolution_date)
    else:
        resolution_dt = datetime.utcnow() + timedelta(days=args.duration_days)

    resolution_ts = int(resolution_dt.timestamp())
    gas_estimate = estimate_gas(len(outcomes))

    print(f"\n{'[DRY RUN] ' if args.dry_run else ''}Creating Prediction Market on Basis")
    print("=" * 60)
    print(f"  Title:           {args.title}")
    print(f"  Outcomes ({len(outcomes)}):   {', '.join(outcomes)}")
    print(f"  Resolves:        {resolution_dt.strftime('%Y-%m-%d %H:%M UTC')}")
    print(f"  Resolution:      {args.resolution_source}")
    print(f"  Creator fee:     {args.creator_fee * 100:.0f}% of all trading fees (forever)")
    print(f"  Min participants:{args.min_participants} (for airdrop points eligibility)")
    print(f"  Gas estimate:    ~{gas_estimate['gas_cost_bnb']} BNB (${gas_estimate['gas_cost_usd']})")
    print(f"  Airdrop points:  300 pts (if ≥{args.min_participants} unique participants join)")
    print()

    if args.dry_run:
        print("[DRY RUN] Transaction would be submitted here. No action taken.")
        result = {
            "status": "dry_run",
            "market_title": args.title,
            "outcomes": outcomes,
            "resolution_timestamp": resolution_ts,
            "creator_fee": args.creator_fee,
            "gas_estimate": gas_estimate,
            "expected_airdrop_points": 300,
        }
    else:
        # TODO: Implement using basis-sdk / direct contract call
        # Example flow (pseudocode):
        #
        # from basis_sdk import BasisClient
        # client = BasisClient(private_key=args.wallet, rpc_url=args.rpc_url)
        #
        # tx = client.predict.create_market(
        #     title=args.title,
        #     outcomes=outcomes,
        #     resolution_timestamp=resolution_ts,
        #     resolution_source=args.resolution_source,
        #     creator_fee=args.creator_fee,
        # )
        # receipt = client.wait_for_receipt(tx)
        #
        # result = {
        #     "status": "success",
        #     "tx_hash": receipt.transactionHash.hex(),
        #     "market_address": receipt.logs[0].address,
        #     "outcome_token_addresses": [...],  # one per outcome
        #     "gas_used": receipt.gasUsed,
        #     "block_number": receipt.blockNumber,
        # }

        print("ERROR: basis-sdk not yet available. Use --dry-run to simulate.")
        print("TODO: Implement direct contract call using web3.py + Basis ABIs.")
        sys.exit(1)

    if args.json_output:
        print(json.dumps(result, indent=2))
    else:
        print("✅ Market creation simulated successfully." if args.dry_run else f"✅ Market created!")
        print(f"\nEarning path:")
        print(f"  Every trade on '{args.title}' → you earn {args.creator_fee * 100:.0f}% of fees")
        print(f"  High-volume multi-outcome markets earn the most")
        print(f"  Bet on outcomes separately for additional income (Path B)")


if __name__ == "__main__":
    main()
