"""
Basis Prediction Market Liquidity Simulator

Replays real Polymarket volume through the Basis bonding curve to analyze
how different starting liquidities affect probability distributions.

Uses the EXACT formula from APrivateTradingMarket contract:
  - Price = outcomeVirtualReserve / totalVirtualReserve
  - sharesOut = (netUsdc * newTotal) / newVirt
  - Slippage penalty above 95% probability
  - Tax rate: 1.5% (prediction market rate from ATaxes)
"""

import json
import sys
import os
from dataclasses import dataclass, field

TAX_RATE_BPS = 150  # 1.5% prediction tax
ONE_USD = 1_000_000_000_000_000_000  # 18 decimal USDB


@dataclass
class Outcome:
    name: str
    virtual_reserve: float
    total_cost: float = 0.0
    circulating_shares: float = 0.0
    volume_in: float = 0.0  # total USDC bought into this outcome


@dataclass
class Market:
    name: str
    outcomes: list
    total_virtual_reserve: float = 0.0
    initial_reserve_per_outcome: float = 0.0

    def __post_init__(self):
        self.total_virtual_reserve = sum(o.virtual_reserve for o in self.outcomes)
        self.initial_reserve_per_outcome = self.outcomes[0].virtual_reserve if self.outcomes else 0

    def get_probability(self, idx):
        return self.outcomes[idx].virtual_reserve / self.total_virtual_reserve

    def get_all_probabilities(self):
        return {o.name: o.virtual_reserve / self.total_virtual_reserve for o in self.outcomes}

    def buy(self, outcome_idx, usdc_amount):
        """Execute a buy using exact contract logic. Returns shares received."""
        # Apply tax
        tax = usdc_amount * TAX_RATE_BPS / 10000
        net_usdc = usdc_amount - tax

        o = self.outcomes[outcome_idx]
        total_before = self.total_virtual_reserve

        new_total = total_before + net_usdc
        new_virt = o.virtual_reserve + net_usdc

        # Update reserves
        o.virtual_reserve = new_virt
        self.total_virtual_reserve = new_total

        # Calculate shares: sharesOut = (netUsdc * newTotal) / newVirt
        shares_out = (net_usdc * new_total) / new_virt

        # Apply slippage if probability > 95%
        prob_bp = (new_virt * 10000) / new_total
        if prob_bp > 9500:
            remaining = 10000 - prob_bp
            shares_out = (shares_out * remaining * remaining) / 250000

        o.total_cost += net_usdc
        o.circulating_shares += shares_out
        o.volume_in += usdc_amount

        return shares_out


def create_market(outcome_names, initial_reserve_per_outcome):
    """Create a fresh market with given starting liquidity per outcome."""
    outcomes = [Outcome(name=name, virtual_reserve=initial_reserve_per_outcome) for name in outcome_names]
    return Market(name="Simulation", outcomes=outcomes)


def run_simulation(outcome_data, initial_reserve):
    """
    Replay Polymarket volume through Basis bonding curve.
    
    outcome_data: list of {title, volume, probability} from Polymarket
    initial_reserve: starting virtual reserve per outcome in USD
    """
    # Filter to outcomes with actual volume
    active_outcomes = [o for o in outcome_data if o["volume"] > 0]
    all_names = [o["title"] for o in active_outcomes]
    
    market = create_market(all_names, initial_reserve)
    
    # Replay each outcome's volume as a single buy
    # (In reality these would be many small buys, but for probability analysis
    #  the end state is what matters — the curve is path-independent for reserves)
    # 
    # Actually, the bonding curve IS path-dependent because shares_out depends on
    # current reserves. So we need to simulate in smaller chunks.
    # 
    # Strategy: break each outcome's volume into chunks proportional to their
    # share of total volume, then interleave buys in rounds.
    
    total_volume = sum(o["volume"] for o in active_outcomes)
    
    # Simulate in 1000 rounds, each outcome gets proportional volume per round
    NUM_ROUNDS = 1000
    volume_per_round = {i: active_outcomes[i]["volume"] / NUM_ROUNDS for i in range(len(active_outcomes))}
    
    for round_num in range(NUM_ROUNDS):
        for i in range(len(active_outcomes)):
            chunk = volume_per_round[i]
            if chunk > 0:
                market.buy(i, chunk)
    
    return market, active_outcomes


def format_results(market, active_outcomes, initial_reserve):
    """Format simulation results."""
    lines = []
    lines.append(f"\n{'='*100}")
    lines.append(f"STARTING LIQUIDITY: ${initial_reserve:,.0f} per outcome  |  {len(market.outcomes)} active outcomes  |  Total virtual pool: ${initial_reserve * len(market.outcomes):,.0f}")
    lines.append(f"{'='*100}")
    lines.append(f"{'#':<4} {'Outcome':<35} {'Poly Vol':>14} {'Poly Prob':>10} {'Basis Prob':>11} {'Delta':>8} {'Payout if Win':>14} {'Shares':>14}")
    lines.append(f"{'-'*110}")
    
    total_pool = sum(o.total_cost for o in market.outcomes)
    
    results = []
    for i, o in enumerate(market.outcomes):
        basis_prob = market.get_probability(i)
        poly_prob = active_outcomes[i]["probability"]
        delta = basis_prob - poly_prob
        
        # Payout per $1 invested (if this outcome wins)
        # Winners split entire pool proportional to shares
        if o.circulating_shares > 0 and o.volume_in > 0:
            # If you bought $1 worth, how many shares did you get on average?
            avg_share_per_dollar = o.circulating_shares / o.volume_in
            # Total pool / total shares * your shares
            payout_per_dollar = (total_pool / o.circulating_shares) * avg_share_per_dollar
        else:
            payout_per_dollar = 0
        
        results.append({
            "name": o.name,
            "poly_volume": active_outcomes[i]["volume"],
            "poly_prob": poly_prob,
            "basis_prob": basis_prob,
            "delta": delta,
            "payout_per_dollar": payout_per_dollar,
            "shares": o.circulating_shares,
            "total_cost": o.total_cost,
        })
    
    # Sort by Basis probability descending
    results.sort(key=lambda x: x["basis_prob"], reverse=True)
    
    for i, r in enumerate(results, 1):
        lines.append(
            f"{i:<4} {r['name']:<35} ${r['poly_volume']:>12,.0f} {r['poly_prob']:>9.1%} {r['basis_prob']:>10.2%} {r['delta']:>+7.1%} "
            f"${r['payout_per_dollar']:>12.2f} {r['shares']:>13,.0f}"
        )
    
    lines.append(f"\n  Total pool (post-tax): ${total_pool:,.0f}")
    lines.append(f"  Tax collected (1.5%): ${sum(o.volume_in for o in market.outcomes) * TAX_RATE_BPS / 10000:,.0f}")
    
    # Key stats
    top = max(results, key=lambda x: x["basis_prob"])
    bottom_active = min((r for r in results if r["poly_volume"] > 0), key=lambda x: x["basis_prob"])
    
    lines.append(f"\n  Highest probability: {top['name']} at {top['basis_prob']:.2%} (Polymarket: {top['poly_prob']:.1%})")
    lines.append(f"  Lowest active probability: {bottom_active['name']} at {bottom_active['basis_prob']:.2%}")
    lines.append(f"  Payout if {top['name']} wins: ${top['payout_per_dollar']:.2f} per $1 bet")
    lines.append(f"  Payout if {bottom_active['name']} wins: ${bottom_active['payout_per_dollar']:.2f} per $1 bet")
    
    return "\n".join(lines), results


def main():
    # Load outcome data
    json_file = sys.argv[1] if len(sys.argv) > 1 else "polymarket_democratic_presidential_nominee_2028_outcomes.json"
    
    if not os.path.exists(json_file):
        print(f"File not found: {json_file}")
        sys.exit(1)
    
    with open(json_file) as f:
        data = json.load(f)
    
    outcome_data = data["outcomes"]
    event_name = data["event"]
    total_volume = data["total_volume"]
    active_count = len([o for o in outcome_data if o["volume"] > 0])
    
    print(f"\n{'#'*100}")
    print(f"  BASIS LIQUIDITY SIMULATION: {event_name}")
    print(f"  Total Polymarket Volume: ${total_volume:,.0f}")
    print(f"  Active Outcomes: {active_count} (of {len(outcome_data)} total)")
    print(f"  Tax Rate: {TAX_RATE_BPS/100:.1f}% (prediction market rate)")
    print(f"{'#'*100}")
    
    # Run simulations at different starting liquidities
    reserves = [1_000, 10_000, 50_000, 100_000, 200_000]
    
    all_results = {}
    for reserve in reserves:
        market, active = run_simulation(outcome_data, reserve)
        output, results = format_results(market, active, reserve)
        print(output)
        all_results[reserve] = results
    
    # Comparison summary
    print(f"\n\n{'='*100}")
    print(f"  COMPARISON: How starting liquidity affects the TOP 10 outcomes")
    print(f"{'='*100}")
    
    # Get top 10 by Polymarket probability
    active = [o for o in outcome_data if o["volume"] > 0]
    active.sort(key=lambda x: x["probability"], reverse=True)
    top10 = active[:10]
    
    header = f"{'Outcome':<30} {'Poly':>7}"
    for r in reserves:
        header += f" {'$'+format(r,','):>10}"
    print(header)
    print("-" * (42 + 11 * len(reserves)))
    
    for candidate in top10:
        line = f"{candidate['title']:<30} {candidate['probability']:>6.1%}"
        for reserve in reserves:
            # Find this candidate in results
            match = next((r for r in all_results[reserve] if r["name"] == candidate["title"]), None)
            if match:
                line += f" {match['basis_prob']:>9.2%}"
            else:
                line += f" {'N/A':>9}"
        print(line)
    
    # Payout comparison for top 10
    print(f"\n  PAYOUT PER $1 BET (if outcome wins)")
    print(f"{'Outcome':<30} {'Poly':>7}")
    header2 = f"{'Outcome':<30} {'Poly$1':>7}"
    for r in reserves:
        header2 += f" {'$'+format(r,','):>10}"
    print(header2)
    print("-" * (42 + 11 * len(reserves)))
    
    for candidate in top10:
        # Polymarket payout is always $1/share, so payout = 1/probability
        poly_payout = 1.0 / candidate["probability"] if candidate["probability"] > 0 else 0
        line = f"{candidate['title']:<30} ${poly_payout:>5.2f}"
        for reserve in reserves:
            match = next((r for r in all_results[reserve] if r["name"] == candidate["title"]), None)
            if match:
                line += f" ${match['payout_per_dollar']:>8.2f}"
            else:
                line += f" {'N/A':>9}"
        print(line)
    
    # Save full results
    output_file = json_file.replace("_outcomes.json", "_simulation.json")
    with open(output_file, "w") as f:
        json.dump({
            "event": event_name,
            "total_volume": total_volume,
            "reserves_tested": reserves,
            "results": {str(k): v for k, v in all_results.items()}
        }, f, indent=2)
    print(f"\nFull results saved to {output_file}")


if __name__ == "__main__":
    main()
