"""
bet.py — Place a bet on a Predict+ prediction market outcome on Basis

Buys shares in a specific prediction outcome. Winner takes the ENTIRE losing pool —
not capped at $1/share like Polymarket. Multi-outcome markets can deliver 8x+ returns.

Key mechanics:
- Airdrop points: 1 pt per $1 NET PROFIT only (hedging all outcomes = 0 points)
- Buying outcome tokens also earns trading points (1 pt/$1 volume, separate from bet points)
- No counterparty risk — modified AMM pool with virtual liquidity
- Sellers can only sell to next buyer, NOT against pool (protects winning pool)
- Post-resolution: selling BURNS tokens → fees inject into liquidity → price goes UP

Usage:
    python bet.py --market 0xMARKET_ADDRESS --outcome "Yes" --amount 100

    python bet.py --market 0xMARKET_ADDRESS --outcome "Team C" --amount 50 \\
        --strategy path-b --dry-run
"""

import argparse
import json
import os
import sys
from dotenv import load_dotenv

load_dotenv()


def parse_args():
    parser = argparse.ArgumentParser(
        description="Place a bet on a Predict+ market outcome on Basis"
    )
    parser.add_argument(
        "--market",
        required=True,
        help="Prediction market contract address (0x...)"
    )
    parser.add_argument(
        "--outcome",
        required=True,
        help="Outcome name to bet on (must match market outcomes exactly)"
    )
    parser.add_argument(
        "--amount",
        type=float,
        required=True,
        help="Amount of USDB/USDC to bet"
    )
    parser.add_argument(
        "--strategy",
        choices=["path-a", "path-b", "standalone"],
        default="standalone",
        help="Strategy context: path-a (separate USDC), path-b (borrowed USDC), standalone"
    )
    parser.add_argument(
        "--max-slippage",
        type=float,
        default=0.02,
        help="Max acceptable slippage as decimal (default: 0.02 = 2%%)"
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


def fetch_market_info(market_address: str) -> dict:
    """
    Fetch current market state: outcomes, pool sizes, current prices.
    TODO: Replace with actual API/contract call when basis-sdk available.
    """
    # TODO: Call GET /api/v1/predict/markets/{address} or read contract state
    # Returning mock data for now
    return {
        "address": market_address,
        "title": "[TODO: fetch from contract]",
        "outcomes": ["[TODO: fetch outcomes]"],
        "pool_sizes": {},  # outcome -> USDC in losing pool
        "status": "active",
        "resolution_date": "[TODO: fetch timestamp]",
        "total_volume": 0.0,
    }


def estimate_payout(
    outcome: str,
    bet_amount: float,
    market_info: dict
) -> dict:
    """
    Estimate potential payout if outcome wins.
    Winner splits entire losing pool (not capped at $1/share).
    TODO: Use actual pool data from contract when available.
    """
    # TODO: Read actual pool sizes from contract
    # Formula: payout = bet_amount + (bet_amount / winning_pool_total) * losing_pool_total
    return {
        "bet_outcome": outcome,
        "bet_amount": bet_amount,
        "estimated_min_payout": bet_amount,  # TODO: calculate from pool sizes
        "estimated_max_payout": "[TODO: calculate from current pools]",
        "note": "Winner takes ENTIRE losing pool — potential multiples of bet amount",
    }


def main():
    args = parse_args()

    # Validate bet amount
    max_bet = float(os.getenv("MAX_BET_PER_MARKET", "100"))
    if args.amount > max_bet:
        print(f"Warning: Bet amount ${args.amount} exceeds MAX_BET_PER_MARKET=${max_bet}")
        print(f"Adjust MAX_BET_PER_MARKET in .env or reduce --amount")
        sys.exit(1)

    market_info = fetch_market_info(args.market)
    payout_estimate = estimate_payout(args.outcome, args.amount, market_info)

    print(f"\n{'[DRY RUN] ' if args.dry_run else ''}Placing Bet on Basis Prediction Market")
    print("=" * 60)
    print(f"  Market:          {args.market}")
    print(f"  Outcome:         {args.outcome}")
    print(f"  Bet Amount:      ${args.amount:.2f} USDB")
    print(f"  Strategy:        {args.strategy}")
    print(f"  Max slippage:    {args.max_slippage * 100:.1f}%")
    print(f"  Payout model:    Winner takes ENTIRE losing pool (not capped at $1)")
    print(f"  Airdrop points:  1 pt per $1 NET PROFIT (hedging = 0 pts)")
    print()
    print(f"  Strategy note:")
    if args.strategy == "path-a":
        print(f"    Path A: You should already hold leveraged Predict+ tokens.")
        print(f"    This bet uses SEPARATE USDC — leverage and loans are not stackable.")
    elif args.strategy == "path-b":
        print(f"    Path B: Using borrowed USDC from a Predict+ loan.")
        print(f"    Run lend.py first to borrow USDC against your Predict+ tokens.")
    else:
        print(f"    Standalone bet — not part of a combined strategy.")

    if args.dry_run:
        print("\n[DRY RUN] Transaction would be submitted here. No action taken.")
        result = {
            "status": "dry_run",
            "market": args.market,
            "outcome": args.outcome,
            "bet_amount": args.amount,
            "payout_estimate": payout_estimate,
            "airdrop_points_if_win": f"1 pt per $1 net profit",
        }
    else:
        # TODO: Implement using basis-sdk / direct contract call
        # Example flow (pseudocode):
        #
        # from basis_sdk import BasisClient
        # client = BasisClient(private_key=args.wallet, rpc_url=args.rpc_url)
        #
        # # First approve USDC spend
        # client.usdc.approve(spender=market_address, amount=args.amount)
        #
        # # Place bet
        # tx = client.predict.bet(
        #     market_address=args.market,
        #     outcome=args.outcome,
        #     amount_usdc=args.amount,
        #     max_slippage=args.max_slippage,
        # )
        # receipt = client.wait_for_receipt(tx)
        #
        # result = {
        #     "status": "success",
        #     "tx_hash": receipt.transactionHash.hex(),
        #     "shares_received": ...,
        #     "effective_price": ...,
        #     "gas_used": receipt.gasUsed,
        # }

        print("ERROR: basis-sdk not yet available. Use --dry-run to simulate.")
        print("TODO: Implement direct contract call using web3.py + Basis ABIs.")
        sys.exit(1)

    if args.json_output:
        print(json.dumps(result, indent=2))
    else:
        print(f"\n✅ Bet {'simulated' if args.dry_run else 'placed'} successfully.")
        print(f"\nReminder — post-resolution sell strategy:")
        print(f"  If you win: wait through the sell wave.")
        print(f"  Selling tokens BURNS them → fees inject into price → price goes UP.")
        print(f"  Last sellers get the BEST price. Patience is profitable.")


if __name__ == "__main__":
    main()
