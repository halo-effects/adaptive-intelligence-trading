"""
points.py — Check airdrop points, tier, rank, and ACS on Basis

Query your current airdrop standing including total points, Molt tier progression,
Agent Confidence Score, multipliers, and leaderboard rank. Use this to optimize
your farming strategy — "I'm weak on predictions, let me create more markets
this week to hit the diversity bonus."

Points earned during USDB testing carry over to the real BASIS airdrop.

Usage:
    python points.py --wallet 0xYOUR_WALLET
    python points.py --wallet 0xYOUR_WALLET --optimize   # suggest what to do next
    python points.py --wallet 0xYOUR_WALLET --json-output
"""

import argparse
import json
import os
import sys
from dotenv import load_dotenv

load_dotenv()

# Molt tier thresholds
MOLT_TIERS = [
    {"name": "🥚 Egg",            "points": 0,       "perks": "Basic platform access"},
    {"name": "🦐 Shrimp",         "points": 1_000,   "perks": "Access to leaderboard"},
    {"name": "🦀 Crab",           "points": 5_000,   "perks": "Bonding phase whitelist for select tokens"},
    {"name": "🦞 Lobster",        "points": 25_000,  "perks": "Featured in Lobster Report, priority API support"},
    {"name": "🦞👑 Alpha Lobster", "points": 100_000, "perks": "Moltbook verified badge, governance input"},
    {"name": "💎🦞 Diamond Lobster", "points": 500_000, "perks": "Founding-tier perks, direct dev access, co-marketing"},
]


def parse_args():
    parser = argparse.ArgumentParser(
        description="Check airdrop points, Molt tier, ACS, and leaderboard rank on Basis"
    )
    parser.add_argument(
        "--wallet",
        default=os.getenv("BASIS_WALLET_ADDRESS"),
        help="Wallet address to check (0x...)"
    )
    parser.add_argument(
        "--optimize",
        action="store_true",
        help="Suggest actions to maximize points (analyze category gaps)"
    )
    parser.add_argument(
        "--acs",
        action="store_true",
        help="Show detailed Agent Confidence Score breakdown"
    )
    parser.add_argument(
        "--api-base",
        default=os.getenv("BASIS_API_BASE", "https://api.basis.exchange"),
        help="Basis API base URL"
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


def get_tier(points: int) -> dict:
    current_tier = MOLT_TIERS[0]
    next_tier = MOLT_TIERS[1] if len(MOLT_TIERS) > 1 else None
    for i, tier in enumerate(MOLT_TIERS):
        if points >= tier["points"]:
            current_tier = tier
            next_tier = MOLT_TIERS[i + 1] if i + 1 < len(MOLT_TIERS) else None
    return {"current": current_tier, "next": next_tier}


def suggest_optimizations(breakdown: dict) -> list:
    """Analyze point categories and suggest actions to maximize earnings."""
    suggestions = []
    categories = ["trading", "predictions_created", "predictions_participated",
                   "lending", "vault", "referrals"]

    # Check for diversity bonus eligibility (3+ products in a week)
    active_categories = sum(1 for c in categories if breakdown.get(c, 0) > 0)
    if active_categories < 3:
        missing = [c for c in categories if breakdown.get(c, 0) == 0]
        suggestions.append(
            f"🎯 Diversity bonus: Use {3 - active_categories} more products this week for +25% on ALL points. "
            f"Try: {', '.join(missing[:3])}"
        )

    # Category-specific suggestions
    if breakdown.get("predictions_created", 0) < 3:
        suggestions.append(
            "📊 Create more prediction markets (300 pts each, + 20% creator fees forever). "
            "Try mirroring popular Polymarket events."
        )
    if breakdown.get("vault", 0) == 0:
        suggestions.append(
            "🏛️ Stake STASIS in the vault (2 pts/$1/day, passive). Set and forget."
        )
    if breakdown.get("lending", 0) == 0:
        suggestions.append(
            "🏦 Take a loan against tokens (200 pts base, + 1 pt/day). "
            "Redeploy borrowed USDC for capital recycling."
        )
    if breakdown.get("referrals", 0) == 0:
        suggestions.append(
            "📨 Share your referral link (10% of referee's lifetime points, ongoing)."
        )

    return suggestions


def main():
    args = parse_args()

    if not args.wallet:
        print("Error: --wallet required (or set BASIS_WALLET_ADDRESS env var)", file=sys.stderr)
        sys.exit(1)

    print(f"\n{'[DRY RUN] ' if args.dry_run else ''}Basis Airdrop Points — {args.wallet[:10]}...{args.wallet[-6:]}")
    print("=" * 60)

    if args.dry_run:
        print(f"\n[DRY RUN] Would fetch from:")
        print(f"  GET {args.api_base}/api/v1/points/{args.wallet}")
        if args.acs:
            print(f"  GET {args.api_base}/api/v1/acs/{args.wallet}")

        mock_points = {
            "wallet": args.wallet,
            "total_points": 0,
            "tier": "🥚 Egg",
            "next_tier_at": 1000,
            "streak_days": 0,
            "multiplier": 1.0,
            "breakdown": {
                "trading": 0,
                "predictions_created": 0,
                "predictions_participated": 0,
                "lending": 0,
                "vault": 0,
                "referrals": 0,
            },
            "rank": 0,
            "total_participants": 0,
        }
        mock_acs = {
            "wallet": args.wallet,
            "acs": 0.0,
            "label": "Human",
            "multiplier": 1.0,
            "breakdown": {
                "framework_attestation": 0.0,
                "operator_linked": 0.0,
                "api_only": 0.0,
                "behavioral": 0.0,
                "wallet_type": 0.0,
                "challenge": 0.0,
            },
        }

        tier_info = get_tier(mock_points["total_points"])
        print(f"\n  Total Points:  {mock_points['total_points']:,}")
        print(f"  Current Tier:  {tier_info['current']['name']}")
        if tier_info["next"]:
            print(f"  Next Tier:     {tier_info['next']['name']} (need {tier_info['next']['points']:,} pts)")
        print(f"  Streak:        {mock_points['streak_days']} days (+{min(mock_points['streak_days'] * 10, 100)}%)")
        print(f"  Multiplier:    {mock_points['multiplier']:.2f}x")

        if args.acs:
            print(f"\n  Agent Confidence Score (ACS)")
            print(f"  Score:         {mock_acs['acs']:.2f} ({mock_acs['label']})")
            print(f"  ACS Multiplier:{mock_acs['multiplier']:.1f}x")
            print(f"  Components:")
            for k, v in mock_acs["breakdown"].items():
                print(f"    {k}: {v:.2f}")

        if args.optimize:
            suggestions = suggest_optimizations(mock_points["breakdown"])
            print(f"\n  📈 Optimization Suggestions:")
            for s in suggestions:
                print(f"    {s}")

        result = {"status": "dry_run", "points": mock_points, "acs": mock_acs if args.acs else None}
    else:
        # TODO: Implement using basis-sdk / API call
        # import requests
        # resp = requests.get(f"{args.api_base}/api/v1/points/{args.wallet}")
        # points_data = resp.json()
        #
        # if args.acs:
        #     acs_resp = requests.get(f"{args.api_base}/api/v1/acs/{args.wallet}")
        #     acs_data = acs_resp.json()

        print("ERROR: basis-sdk not yet available. Use --dry-run to simulate.")
        sys.exit(1)

    if args.json_output:
        print(json.dumps(result, indent=2))
    else:
        print(f"\n✅ Points check {'simulated' if args.dry_run else 'complete'}.")
        print(f"\nReminder: Points earned during USDB testing → real BASIS airdrop.")
        print(f"Pre-TGE farming window is open NOW. Every action counts.")


if __name__ == "__main__":
    main()
