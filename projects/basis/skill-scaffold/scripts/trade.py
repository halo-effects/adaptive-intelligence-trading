"""
trade.py — Buy or sell tokens on the Basis DEX (BNB Chain)

All tokens on Basis trade through an internal DEX with STASIS as the base pair.
Agents earn 1 airdrop point per $1 volume (min $10 per trade). Profitable
trades earn a profit multiplier on top: 1.5x (up to 5% P&L) or 2.0x (5%+ P&L).

Buying during bonding phase earns 2x volume points.

Usage:
    # Buy $200 worth of a token
    python trade.py --token 0xTOKEN_ADDRESS --direction buy --amount 200

    # Sell 1000 tokens (exact amount)
    python trade.py --token 0xTOKEN_ADDRESS --direction sell --token-amount 1000

    # Dry-run to check slippage before committing
    python trade.py --token 0xTOKEN_ADDRESS --direction buy --amount 50 --dry-run
"""

import argparse
import json
import os
import sys
from dotenv import load_dotenv

load_dotenv()


def parse_args():
    parser = argparse.ArgumentParser(
        description="Buy or sell tokens on the Basis DEX"
    )
    parser.add_argument(
        "--token",
        required=True,
        help="Token contract address to trade (0x...)"
    )
    parser.add_argument(
        "--direction",
        required=True,
        choices=["buy", "sell"],
        help="Trade direction: buy or sell"
    )

    # Amount specification (one of these required)
    amount_group = parser.add_mutually_exclusive_group(required=True)
    amount_group.add_argument(
        "--amount",
        type=float,
        help="USDC/USDB amount to spend (for buy) or receive (for sell)"
    )
    amount_group.add_argument(
        "--token-amount",
        type=float,
        help="Exact number of tokens to buy or sell"
    )

    parser.add_argument(
        "--max-slippage",
        type=float,
        default=0.01,
        help="Max acceptable slippage (default: 0.01 = 1%%)"
    )
    parser.add_argument(
        "--leverage",
        action="store_true",
        help="Use 36x leverage toggle (floor-price based, no liquidation). Requires PATH_A strategy."
    )
    parser.add_argument(
        "--leverage-split",
        type=float,
        default=1.0,
        help="Fraction of position to leverage (0.0-1.0). E.g. 0.25 = 25%% leveraged + 75%% unleveraged ≈ 10x effective."
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


def compute_effective_leverage(leverage_enabled: bool, leverage_split: float) -> float:
    """
    Basis leverage is a toggle (1x or 36x) not a slider.
    Effective leverage is achieved via position splitting.
    E.g.: 25% leveraged + 75% unleveraged = 0.25*36 + 0.75*1 = 9.75x effective
    """
    if not leverage_enabled:
        return 1.0
    return (leverage_split * 36) + ((1 - leverage_split) * 1)


def main():
    args = parse_args()

    # Safety check
    max_trade = float(os.getenv("MAX_TRADE_SIZE", "500"))
    if args.amount and args.amount > max_trade:
        print(f"Warning: Trade size ${args.amount} exceeds MAX_TRADE_SIZE=${max_trade}")
        print(f"Adjust MAX_TRADE_SIZE in .env or reduce --amount")
        sys.exit(1)

    # Minimum trade for airdrop points
    if args.amount and args.amount < 10:
        print(f"Note: Minimum $10 per trade for airdrop points. This trade won't earn points.")

    effective_leverage = compute_effective_leverage(args.leverage, args.leverage_split)

    print(f"\n{'[DRY RUN] ' if args.dry_run else ''}{args.direction.upper()} on Basis DEX")
    print("=" * 60)
    print(f"  Token:           {args.token}")
    print(f"  Direction:       {args.direction}")
    if args.amount:
        print(f"  USDC amount:     ${args.amount:.2f}")
    else:
        print(f"  Token amount:    {args.token_amount}")
    print(f"  Max slippage:    {args.max_slippage * 100:.1f}%")

    if args.leverage:
        print(f"  Leverage:        36x toggle ON")
        print(f"  Leverage split:  {args.leverage_split * 100:.0f}% leveraged → {effective_leverage:.1f}x effective")
        print(f"  ⚠️  Leveraged tokens held in leverage contract — CANNOT be used as loan collateral")
        print(f"  ✅ No price liquidation — leverage calculated against floor price")
    else:
        print(f"  Leverage:        1x (off)")

    if args.amount:
        est_points = max(0, (args.amount // 1))  # 1 pt per $1
        print(f"  Airdrop points:  ~{est_points:.0f} pts base (+ profit multiplier if P&L positive)")

    if args.dry_run:
        print("\n[DRY RUN] Transaction would be submitted here. No action taken.")
        result = {
            "status": "dry_run",
            "token": args.token,
            "direction": args.direction,
            "amount_usdc": args.amount,
            "token_amount": args.token_amount,
            "leverage": args.leverage,
            "effective_leverage": effective_leverage,
            "max_slippage": args.max_slippage,
            "estimated_points_base": int(args.amount or 0),
        }
    else:
        # TODO: Implement using basis-sdk / direct contract call
        # Example flow (pseudocode):
        #
        # from basis_sdk import BasisClient
        # client = BasisClient(private_key=args.wallet, rpc_url=args.rpc_url)
        #
        # if args.direction == "buy":
        #     if args.leverage:
        #         # Split position: leverage_split% goes through leverage contract
        #         leveraged_amount = args.amount * args.leverage_split
        #         spot_amount = args.amount * (1 - args.leverage_split)
        #
        #         if leveraged_amount > 0:
        #             tx1 = client.dex.buy_leveraged(
        #                 token=args.token,
        #                 amount_usdc=leveraged_amount,
        #                 max_slippage=args.max_slippage,
        #             )
        #         if spot_amount > 0:
        #             tx2 = client.dex.buy(
        #                 token=args.token,
        #                 amount_usdc=spot_amount,
        #                 max_slippage=args.max_slippage,
        #             )
        #     else:
        #         tx = client.dex.buy(
        #             token=args.token,
        #             amount_usdc=args.amount,
        #             max_slippage=args.max_slippage,
        #         )
        # elif args.direction == "sell":
        #     tx = client.dex.sell(
        #         token=args.token,
        #         token_amount=args.token_amount or None,
        #         usdc_amount=args.amount or None,
        #         max_slippage=args.max_slippage,
        #     )
        #
        # receipt = client.wait_for_receipt(tx)
        # result = {
        #     "status": "success",
        #     "tx_hash": receipt.transactionHash.hex(),
        #     "tokens_bought_or_sold": ...,
        #     "price": ...,
        #     "gas_used": receipt.gasUsed,
        # }

        print("ERROR: basis-sdk not yet available. Use --dry-run to simulate.")
        print("TODO: Implement direct contract call using web3.py + Basis ABIs.")
        sys.exit(1)

    if args.json_output:
        print(json.dumps(result, indent=2))
    else:
        print(f"\n✅ Trade {'simulated' if args.dry_run else 'executed'} successfully.")
        if args.direction == "buy" and not args.leverage:
            print(f"\nTip: Consider running lend.py to borrow USDC against these tokens (100% LTV).")
            print(f"     Redeploy that USDC into predictions or another token (Path B strategy).")


if __name__ == "__main__":
    main()
