"""
create-token.py — Launch a token on Basis via the ATokenFactory contract

Deploys a new elastic-supply token on BNB Chain. 100% mint-on-buy, burn-on-sell.
Zero pre-minting, zero insider allocations — mathematically impossible to rug.
Creator earns 20% of all DEX trading fees forever.

SDK: client.factory.create_token()

Token Types (controlled by hybridMultiplier):
  Stable+  — Price only goes up. hybridMultiplier=0. Ideal for treasury/system tokens.
  Floor+   — Rising floor with volatility above. hybridMultiplier=50-100.
             Ideal for community tokens, agent identity tokens.

Usage:
    python create-token.py --name "MyAgentToken" --symbol "MAT" \\
        --hybrid-multiplier 50 --start-lp 1000

    python create-token.py --name "AgentTreasury" --symbol "ATR" \\
        --hybrid-multiplier 0 --frozen --dry-run
"""

import argparse
import json
import os
import sys
from dotenv import load_dotenv

load_dotenv()

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from client_helper import get_client, output_result


def parse_args():
    parser = argparse.ArgumentParser(
        description="Launch a token on Basis (BNB Chain) via ATokenFactory"
    )
    parser.add_argument("--name", required=True, help="Full token name (e.g. 'My Agent Token')")
    parser.add_argument("--symbol", required=True, help="Token ticker symbol (e.g. 'MAT')")
    parser.add_argument("--hybrid-multiplier", type=int, default=50,
                        help="Bonding curve multiplier. 0=Stable+, 50-100=Floor+ (default: 50)")
    parser.add_argument("--frozen", action="store_true",
                        help="Start in frozen state (whitelist-only trading)")
    parser.add_argument("--usdc-for-bonding", type=int, default=10000,
                        help="USDC allocated to bonding curve (default: 10000)")
    parser.add_argument("--start-lp", type=int, default=1000,
                        help="Initial LP pool size, 100-10000 (default: 1000)")
    parser.add_argument("--auto-vest", action="store_true",
                        help="Enable auto-vesting for dev allocation")
    parser.add_argument("--vest-duration-days", type=int, default=30,
                        help="Vesting duration in days if auto-vest enabled (default: 30)")
    parser.add_argument("--gradual-vest", action="store_true",
                        help="Use gradual vesting (vs cliff) if auto-vest enabled")
    parser.add_argument("--description", default="", help="Token description")
    parser.add_argument("--website", default="", help="Project website URL")
    parser.add_argument("--image-url", default="", help="Token image URL (auto-uploaded to IPFS)")
    parser.add_argument("--dry-run", action="store_true", help="Simulate without submitting")
    parser.add_argument("--json-output", action="store_true", help="Output as JSON")
    return parser.parse_args()


def main():
    args = parse_args()

    if args.start_lp < 100 or args.start_lp > 10000:
        print("Error: --start-lp must be between 100 and 10000", file=sys.stderr)
        sys.exit(1)

    token_type = "Stable+" if args.hybrid_multiplier == 0 else "Floor+"

    print(f"\n{'[DRY RUN] ' if args.dry_run else ''}Launching {token_type} Token on Basis")
    print("=" * 60)
    print(f"  Name:              {args.name} ({args.symbol})")
    print(f"  Type:              {token_type} (hybridMultiplier={args.hybrid_multiplier})")
    print(f"  USDC for bonding:  {args.usdc_for_bonding}")
    print(f"  Start LP:          {args.start_lp}")
    print(f"  Frozen:            {'Yes (whitelist-only)' if args.frozen else 'No (open trading)'}")
    print(f"  Auto-vest:         {'Yes (' + str(args.vest_duration_days) + ' days, ' + ('gradual' if args.gradual_vest else 'cliff') + ')' if args.auto_vest else 'No'}")
    print(f"  Creator earnings:  20% of all DEX trading fees (forever)")
    print(f"  Supply model:      100% elastic — zero pre-mint, zero insider tokens")
    print(f"  Airdrop points:    500 pts (one-time at launch)")
    print()

    if args.dry_run:
        # Check creation fee
        try:
            client = get_client(require_write=False)
            fee = client.factory.get_fee_amount()
            print(f"  Creation fee:      {fee} BNB")
        except Exception:
            print(f"  Creation fee:      (could not fetch — requires SDK)")

        print("\n[DRY RUN] Transaction would be submitted here. No action taken.")
        result = {
            "status": "dry_run",
            "name": args.name,
            "symbol": args.symbol,
            "type": token_type,
            "hybrid_multiplier": args.hybrid_multiplier,
            "usdc_for_bonding": args.usdc_for_bonding,
            "start_lp": args.start_lp,
        }
    else:
        client = get_client(require_write=True)

        try:
            tx_result = client.factory.create_token(
                args.symbol,
                args.name,
                args.hybrid_multiplier,
                args.frozen,
                args.usdc_for_bonding,
                args.start_lp,
                args.auto_vest,
                args.vest_duration_days if args.auto_vest else 0,
                args.gradual_vest if args.auto_vest else False,
            )

            tx_hash = tx_result["hash"]
            token_address = tx_result["receipt"]["logs"][0]["address"]

            print(f"\n✅ Token created!")
            print(f"  Tx hash:       {tx_hash}")
            print(f"  Token address: {token_address}")

            # Upload image and metadata if provided
            if args.image_url or args.description:
                try:
                    metadata_payload = {"address": token_address}
                    if args.description:
                        metadata_payload["description"] = args.description
                    if args.website:
                        metadata_payload["website"] = args.website

                    if args.image_url:
                        ipfs_url = client.api.upload_image_from_url(args.image_url)
                        metadata_payload["image"] = ipfs_url
                        print(f"  Image IPFS:    {ipfs_url}")

                    meta_result = client.api.update_metadata(metadata_payload)
                    print(f"  Metadata IPFS: {meta_result['url']}")
                except Exception as e:
                    print(f"  ⚠️  Metadata upload failed (non-fatal): {e}")

            result = {
                "status": "success",
                "tx_hash": tx_hash,
                "token_address": token_address,
                "name": args.name,
                "symbol": args.symbol,
                "type": token_type,
            }

        except Exception as e:
            print(f"\n❌ Token creation failed: {e}", file=sys.stderr)
            sys.exit(1)

    output_result(result, args.json_output)

    if not args.json_output:
        if args.dry_run:
            print("\n✅ Token creation simulated successfully.")
        print(f"\nNext steps:")
        print(f"  1. Buy early to ride the bonding curve: python trade.py --token <address> --direction buy --amount 50")
        print(f"  2. Share the token — every trade earns you creator fees forever")
        if args.frozen:
            print(f"  3. Whitelist wallets: use SDK client.factory.set_whitelisted_wallet()")
            print(f"  4. Open trading: use SDK client.factory.disable_freeze()")


if __name__ == "__main__":
    main()
