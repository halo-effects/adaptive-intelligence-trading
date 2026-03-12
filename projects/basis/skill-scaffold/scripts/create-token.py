"""
create-token.py — Launch a Stable+ or Floor+ token on Basis

Deploys a new elastic-supply token on BNB Chain. 100% mint-on-buy, burn-on-sell.
Zero pre-minting, zero insider allocations — mathematically impossible to rug.
Creator earns 20% of all DEX trading fees forever.

Token Types:
  Stable+  — Price only ever goes up. Ideal for system tokens, agent treasury.
  Floor+   — Rising floor price with customizable stability dial (50%-90%).
             Ideal for community tokens, agent identity tokens.

Usage:
    # Launch a Floor+ community token with 70% stability
    python create-token.py --type floor_plus --name "MyAgentToken" --symbol "MAT" \\
        --stability 0.70 --initial-price 0.01 --fee-rate 0.02

    # Launch a Stable+ treasury token
    python create-token.py --type stable_plus --name "AgentTreasury" --symbol "ATR" \\
        --initial-price 0.001 --dry-run
"""

import argparse
import json
import os
import sys
from dotenv import load_dotenv

load_dotenv()


def parse_args():
    parser = argparse.ArgumentParser(
        description="Launch a Stable+ or Floor+ token on Basis (BNB Chain)"
    )
    parser.add_argument(
        "--type",
        required=True,
        choices=["stable_plus", "floor_plus"],
        help="Token type: stable_plus (always up) or floor_plus (rising floor + stability dial)"
    )
    parser.add_argument(
        "--name",
        required=True,
        help="Full token name (e.g. 'MyAgent Treasury')"
    )
    parser.add_argument(
        "--symbol",
        required=True,
        help="Token ticker symbol (e.g. 'MAT')"
    )
    parser.add_argument(
        "--initial-price",
        type=float,
        required=True,
        help="Initial price in USDC (e.g. 0.01)"
    )
    parser.add_argument(
        "--fee-rate",
        type=float,
        default=0.02,
        help="Trading fee rate as decimal (default: 0.02 = 2%%). Creator gets 20%% of this."
    )

    # Floor+ specific
    parser.add_argument(
        "--stability",
        type=float,
        default=0.70,
        help="(Floor+ only) Stability dial: 0.50-0.90 (default: 0.70). IMMUTABLE after launch."
    )

    # Optional features
    parser.add_argument(
        "--surge-tax",
        action="store_true",
        help="Enable surge tax (optional: temporarily increase fees during hype cycles)"
    )
    parser.add_argument(
        "--liquid-vesting",
        action="store_true",
        help="Enable liquid vesting for bonding phase buyers (auto-vest, still borrow against)"
    )
    parser.add_argument(
        "--vesting-duration-days",
        type=int,
        default=30,
        help="(if liquid-vesting enabled) Vesting duration in days (default: 30)"
    )
    parser.add_argument(
        "--description",
        default="",
        help="Token description / purpose"
    )
    parser.add_argument(
        "--website",
        default="",
        help="Agent/project website URL"
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


def validate_stability(token_type: str, stability: float):
    if token_type == "floor_plus":
        if not (0.50 <= stability <= 0.90):
            print(f"Error: --stability must be between 0.50 and 0.90 for Floor+ tokens.")
            print(f"  Current value: {stability}")
            sys.exit(1)
        print(f"  ⚠️  Stability dial {stability:.0%} is IMMUTABLE after launch — cannot be changed.")
    elif token_type == "stable_plus" and stability != 0.70:
        print(f"  Note: --stability is ignored for Stable+ tokens (they're always stable).")


def describe_leverage(token_type: str) -> str:
    if token_type == "stable_plus":
        return "36x (permanent — floor = spot always)"
    elif token_type == "floor_plus":
        return "36x at launch (decreases as spot rises above floor)"
    return "N/A"


def main():
    args = parse_args()
    validate_stability(args.type, args.stability)

    gas_estimate_bnb = 0.0003  # approximate for token creation
    gas_estimate_usd = gas_estimate_bnb * 600

    print(f"\n{'[DRY RUN] ' if args.dry_run else ''}Launching {args.type.replace('_', '+')} Token on Basis")
    print("=" * 60)
    print(f"  Name:            {args.name} ({args.symbol})")
    print(f"  Type:            {args.type.replace('_', '+').title()}")
    print(f"  Initial price:   ${args.initial_price:.6f} USDC")
    print(f"  Fee rate:        {args.fee_rate * 100:.1f}% (you earn 20% = {args.fee_rate * 0.20 * 100:.3f}% of each trade)")
    if args.type == "floor_plus":
        print(f"  Stability dial:  {args.stability:.0%} (IMMUTABLE — set it carefully)")
    print(f"  Available leverage: {describe_leverage(args.type)}")
    print(f"  Surge tax:       {'Enabled' if args.surge_tax else 'Disabled'}")
    print(f"  Liquid vesting:  {'Enabled (' + str(args.vesting_duration_days) + ' days)' if args.liquid_vesting else 'Disabled'}")
    print(f"  Gas estimate:    ~{gas_estimate_bnb} BNB (${gas_estimate_usd:.2f})")
    print(f"  Airdrop points:  500 pts (one-time at launch)")
    print()
    print(f"  Supply model: 100% elastic — zero pre-mint, zero insider tokens")
    print(f"  Anti-rug: Mathematically impossible for creator to dump pre-allocated tokens")

    if args.dry_run:
        print("\n[DRY RUN] Transaction would be submitted here. No action taken.")
        result = {
            "status": "dry_run",
            "token_name": args.name,
            "token_symbol": args.symbol,
            "token_type": args.type,
            "initial_price": args.initial_price,
            "fee_rate": args.fee_rate,
            "stability_dial": args.stability if args.type == "floor_plus" else "N/A",
            "leverage_available": describe_leverage(args.type),
            "gas_estimate_bnb": gas_estimate_bnb,
            "airdrop_points": 500,
        }
    else:
        # TODO: Implement using basis-sdk / direct contract call
        # Example flow (pseudocode):
        #
        # from basis_sdk import BasisClient
        # client = BasisClient(private_key=args.wallet, rpc_url=args.rpc_url)
        #
        # if args.type == "stable_plus":
        #     tx = client.tokens.create_stable_plus(
        #         name=args.name,
        #         symbol=args.symbol,
        #         initial_price=args.initial_price,
        #         fee_rate=args.fee_rate,
        #         surge_tax=args.surge_tax,
        #         liquid_vesting=args.liquid_vesting,
        #         vesting_duration_days=args.vesting_duration_days,
        #     )
        # elif args.type == "floor_plus":
        #     tx = client.tokens.create_floor_plus(
        #         name=args.name,
        #         symbol=args.symbol,
        #         initial_price=args.initial_price,
        #         stability_dial=args.stability,  # IMMUTABLE — double-check before sending
        #         fee_rate=args.fee_rate,
        #         surge_tax=args.surge_tax,
        #         liquid_vesting=args.liquid_vesting,
        #         vesting_duration_days=args.vesting_duration_days,
        #     )
        #
        # receipt = client.wait_for_receipt(tx)
        # token_address = receipt.logs[0].address
        #
        # result = {
        #     "status": "success",
        #     "tx_hash": receipt.transactionHash.hex(),
        #     "token_address": token_address,
        #     "gas_used": receipt.gasUsed,
        #     "block_number": receipt.blockNumber,
        # }

        print("ERROR: basis-sdk not yet available. Use --dry-run to simulate.")
        print("TODO: Implement direct contract call using web3.py + Basis ABIs.")
        sys.exit(1)

    if args.json_output:
        print(json.dumps(result, indent=2))
    else:
        print(f"\n✅ Token launch {'simulated' if args.dry_run else 'complete'}!")
        print(f"\nNext steps:")
        print(f"  1. Buy early to ride the bonding curve (max leverage available at launch)")
        print(f"  2. Share the token address — every trade earns you {args.fee_rate * 0.20 * 100:.3f}% forever")
        print(f"  3. Consider running trade.py to provide initial liquidity")


if __name__ == "__main__":
    main()
