"""
bet.py — Place a bet on a Predict+ prediction market outcome on Basis

Buys shares in a specific prediction outcome via the MarketTrading contract.
Winner takes the ENTIRE losing pool — not capped at $1/share like Polymarket.

SDK: client.prediction_markets.buy() + client.market_reader.get_all_outcomes()

Key mechanics:
- Multi-outcome markets can deliver up to 15x or more returns
- Sellers can only sell to next buyer, NOT against pool (protects winning pool)
- Post-resolution: selling BURNS tokens → fees inject → price goes UP
- Supports hybrid fills: AMM + order book in single transaction
- Airdrop points: 1 pt per $1 volume

Usage:
    python bet.py --market 0xMARKET_ADDRESS --outcome-id 0 --amount 100
    python bet.py --market 0xMARKET_ADDRESS --outcome-id 1 --amount 50 --dry-run
"""

import argparse
import json
import os
import sys
from dotenv import load_dotenv

load_dotenv()

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from client_helper import get_client, usdb_to_raw, raw_to_usdb, raw_to_token, output_result, USDB, MARKET_TRADING


def parse_args():
    parser = argparse.ArgumentParser(
        description="Place a bet on a Predict+ market outcome on Basis"
    )
    parser.add_argument("--market", required=True, help="Prediction market token address (0x...)")
    parser.add_argument("--outcome-id", type=int, required=True, help="Outcome index (0-based)")
    parser.add_argument("--amount", type=float, required=True, help="USDB amount to bet")
    parser.add_argument("--min-shares", type=int, default=0, help="Minimum shares to receive (slippage protection)")
    parser.add_argument("--order-ids", help="Comma-separated order IDs to fill from book (hybrid fill)")
    parser.add_argument("--show-odds", action="store_true", help="Show current market odds before betting")
    parser.add_argument("--dry-run", action="store_true", help="Simulate without submitting")
    parser.add_argument("--json-output", action="store_true", help="Output as JSON")
    return parser.parse_args()


def show_market_odds(client, market_address: str):
    """Display current outcome probabilities and pool sizes."""
    try:
        outcomes = client.market_reader.get_all_outcomes(MARKET_TRADING, market_address)
        print(f"\n  Current Market Odds:")
        for i, outcome in enumerate(outcomes):
            print(f"    [{i}] {outcome}")
        return outcomes
    except Exception as e:
        print(f"  ⚠️  Could not fetch market data: {e}")
        return None


def estimate_price_impact(client, market_address: str, outcome_id: int, amount_usdc: float):
    """
    Estimate how much a bet will move the probability — critical for new/low-liquidity markets.
    
    The bonding curve uses virtual reserves seeded at market creation:
      Public:  seed = min($50K, max($5K, $500 × numOutcomes))
      Private: seed = min($10K, max($1K, $100 × numOutcomes))
    
    When total volume is low relative to seed, probabilities barely move (seed gravity).
    When volume exceeds ~10x seed, probabilities reflect true conviction.
    When betting into a young market, early bets have outsized price impact.
    
    Returns dict with impact metrics, or None if data unavailable.
    """
    try:
        outcomes = client.market_reader.get_all_outcomes(MARKET_TRADING, market_address)
        if not outcomes:
            return None
        
        n = len(outcomes)
        # Try to read current virtual reserves and total pool
        # Note: exact method depends on SDK version — adapt as needed
        market_info = client.market_reader.get_market_info(MARKET_TRADING, market_address)
        total_pool = float(market_info.get("totalPool", 0)) / 1e18  # USDB decimals
        
        # Estimate seed from outcome count (public formula)
        estimated_seed = min(50000, max(5000, 500 * n))
        
        # Volume = total pool minus seed
        estimated_volume = max(0, total_pool - estimated_seed)
        seed_ratio = estimated_seed / max(estimated_volume, 1) if estimated_volume > 0 else 999
        
        # Market maturity assessment
        if seed_ratio > 5:
            maturity = "VERY_EARLY"
            warning = "⚠️  Market barely traded. Your bet will dominate the odds."
        elif seed_ratio > 1:
            maturity = "EARLY"
            warning = "⚠️  Low volume. Your bet will significantly move the probability."
        elif seed_ratio > 0.1:
            maturity = "DEVELOPING"
            warning = "Market developing. Moderate price impact expected."
        else:
            maturity = "MATURE"
            warning = "Market mature. Minimal price impact."
        
        return {
            "num_outcomes": n,
            "estimated_seed": estimated_seed,
            "total_pool": total_pool,
            "estimated_volume": estimated_volume,
            "seed_ratio": seed_ratio,
            "maturity": maturity,
            "warning": warning,
        }
    except Exception:
        return None


def main():
    args = parse_args()

    # Safety check
    max_bet = float(os.getenv("MAX_BET_PER_MARKET", "100"))
    if args.amount > max_bet:
        print(f"Warning: Bet ${args.amount} exceeds MAX_BET_PER_MARKET=${max_bet}")
        print(f"Adjust MAX_BET_PER_MARKET in .env or reduce --amount")
        sys.exit(1)

    usdb_raw = usdb_to_raw(args.amount)

    print(f"\n{'[DRY RUN] ' if args.dry_run else ''}Placing Bet on Basis Prediction Market")
    print("=" * 60)
    print(f"  Market:          {args.market}")
    print(f"  Outcome ID:      {args.outcome_id}")
    print(f"  Bet Amount:      ${args.amount:.2f} USDB ({usdb_raw} raw)")
    print(f"  Min Shares:      {args.min_shares}")
    print(f"  Payout model:    Winner takes ENTIRE losing pool (uncapped)")

    # Always check price impact on new markets
    read_client = get_client(require_write=False)
    
    if args.show_odds or args.dry_run:
        show_market_odds(read_client, args.market)

    # Price impact check — warn on low-liquidity markets
    impact = estimate_price_impact(read_client, args.market, args.outcome_id, args.amount)
    if impact:
        print(f"\n  Market Maturity:  {impact['maturity']}")
        print(f"  Total Pool:       ${impact['total_pool']:,.0f}")
        print(f"  Est. Volume:      ${impact['estimated_volume']:,.0f}")
        print(f"  Seed/Volume:      {impact['seed_ratio']:.1f}x")
        print(f"  {impact['warning']}")
        
        if impact["maturity"] in ("VERY_EARLY", "EARLY") and args.amount > 500:
            print(f"\n  💡 TIP: Consider splitting into smaller bets over time.")
            print(f"     A ${args.amount:.0f} bet on a {impact['maturity'].lower()} market")
            print(f"     will create outsized price movement that may attract")
            print(f"     arbitrage or discourage other participants.")

    if args.dry_run:
        # Preview expected shares
        try:
            client = get_client(require_write=False)
            wallet = os.getenv("BASIS_WALLET_ADDRESS", "0x0000000000000000000000000000000000000000")
            order_ids = [int(x) for x in args.order_ids.split(",")] if args.order_ids else []
            estimated = client.market_reader.estimate_shares_out(
                MARKET_TRADING, args.market, args.outcome_id,
                usdb_raw, order_ids, wallet
            )
            print(f"\n  Estimated shares: {estimated}")
        except Exception:
            pass

        print("\n[DRY RUN] Transaction would be submitted here. No action taken.")
        result = {
            "status": "dry_run",
            "market": args.market,
            "outcome_id": args.outcome_id,
            "amount_usdb": args.amount,
        }
    else:
        client = get_client(require_write=True)

        try:
            if args.order_ids:
                # Hybrid fill: order book + AMM in single transaction
                order_ids = [int(x) for x in args.order_ids.split(",")]
                tx_result = client.prediction_markets.buy_orders_and_contract(
                    args.market, args.outcome_id, order_ids,
                    USDB, usdb_raw, args.min_shares
                )
            else:
                # Pure AMM buy
                tx_result = client.prediction_markets.buy(
                    args.market, args.outcome_id, USDB,
                    usdb_raw, 0, args.min_shares
                )

            print(f"\n✅ Bet placed!")
            print(f"  Tx hash: {tx_result['hash']}")

            result = {
                "status": "success",
                "tx_hash": tx_result["hash"],
                "market": args.market,
                "outcome_id": args.outcome_id,
                "amount_usdb": args.amount,
            }

        except Exception as e:
            print(f"\n❌ Bet failed: {e}", file=sys.stderr)
            sys.exit(1)

    output_result(result, args.json_output)

    if not args.json_output and not args.dry_run:
        print(f"\nPost-resolution strategy:")
        print(f"  If you win: WAIT through the sell wave. Last sellers get the BEST price.")
        print(f"  Selling burns tokens → fees inject → price goes UP.")


if __name__ == "__main__":
    main()
