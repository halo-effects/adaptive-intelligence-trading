"""
Basis Prediction Market Liquidity Simulator v2
Uses probability-weighted volume (YES conviction) instead of raw volume.

YES_capital = polymarket_volume × polymarket_probability
This filters out NO-side churn and gives us genuine conviction capital.
"""

import json
import sys
import os

TAX_RATE_BPS = 150  # 1.5%


class Market:
    def __init__(self, names, init_reserve):
        self.n = len(names)
        self.names = names
        self.reserves = [init_reserve] * self.n
        self.total_reserve = init_reserve * self.n
        self.total_cost = [0.0] * self.n
        self.circulating = [0.0] * self.n
        self.volume_in = [0.0] * self.n
        self.init_reserve = init_reserve

    def buy(self, idx, usdc):
        tax = usdc * TAX_RATE_BPS / 10000
        net = usdc - tax
        new_virt = self.reserves[idx] + net
        new_total = self.total_reserve + net
        self.reserves[idx] = new_virt
        self.total_reserve = new_total
        shares = (net * new_total) / new_virt
        prob_bp = (new_virt * 10000) / new_total
        if prob_bp > 9500:
            rem = 10000 - prob_bp
            shares = (shares * rem * rem) / 250000
        self.total_cost[idx] += net
        self.circulating[idx] += shares
        self.volume_in[idx] += usdc
        return shares

    def prob(self, idx):
        return self.reserves[idx] / self.total_reserve


def run_sim(outcomes, init_reserve, rounds=1000):
    names = [o["title"] for o in outcomes]
    m = Market(names, init_reserve)
    for _ in range(rounds):
        for i, o in enumerate(outcomes):
            chunk = o["yes_capital"] / rounds
            if chunk > 0:
                m.buy(i, chunk)
    return m


def main():
    json_file = sys.argv[1] if len(sys.argv) > 1 else "polymarket_democratic_presidential_nominee_2028_outcomes.json"
    with open(json_file) as f:
        data = json.load(f)

    outcomes = data["outcomes"]
    event = data["event"]

    # Calculate YES conviction capital
    active = []
    for o in outcomes:
        if o["volume"] > 0 and o["probability"] > 0:
            yes_cap = o["volume"] * o["probability"]
            active.append({
                "title": o["title"],
                "raw_volume": o["volume"],
                "probability": o["probability"],
                "yes_capital": yes_cap,
            })
    active.sort(key=lambda x: x["yes_capital"], reverse=True)

    total_raw = sum(o["raw_volume"] for o in active)
    total_yes = sum(o["yes_capital"] for o in active)

    print(f"\n{'#'*100}")
    print(f"  BASIS LIQUIDITY SIMULATION v2: {event}")
    print(f"  Method: Probability-weighted volume (YES conviction)")
    print(f"  Raw Polymarket Volume: ${total_raw:,.0f}")
    print(f"  YES Conviction Capital: ${total_yes:,.0f} ({total_yes/total_raw:.1%} of raw)")
    print(f"  Active Outcomes: {len(active)}")
    print(f"  Tax Rate: {TAX_RATE_BPS/100:.1f}%")
    print(f"{'#'*100}")

    # Show YES capital breakdown
    print(f"\n{'='*95}")
    print(f"  YES CONVICTION CAPITAL (volume x probability)")
    print(f"{'='*95}")
    print(f"{'#':<4} {'Outcome':<35} {'Raw Volume':>14} {'Poly Prob':>10} {'YES Capital':>14} {'YES %':>8}")
    print(f"{'-'*88}")
    for i, o in enumerate(active[:20], 1):
        pct = o["yes_capital"] / total_yes * 100
        print(f"{i:<4} {o['title']:<35} ${o['raw_volume']:>12,.0f} {o['probability']:>9.1%} ${o['yes_capital']:>12,.0f} {pct:>6.1f}%")
    if len(active) > 20:
        rest_yes = sum(o["yes_capital"] for o in active[20:])
        print(f"     {'... remaining ' + str(len(active)-20) + ' outcomes':<35} {'':>14} {'':>10} ${rest_yes:>12,.0f} {rest_yes/total_yes*100:>6.1f}%")

    # Run simulations
    reserves = [1_000, 10_000, 50_000, 100_000, 200_000]
    all_results = {}

    for reserve in reserves:
        m = run_sim(active, reserve)
        pool = sum(m.total_cost)

        results = []
        for i, o in enumerate(active):
            bp = m.prob(i)
            pp = o["probability"]
            delta = bp - pp
            if m.circulating[i] > 0 and m.volume_in[i] > 0:
                avg_share = m.circulating[i] / m.volume_in[i]
                payout = (pool / m.circulating[i]) * avg_share
            else:
                payout = 0
            results.append({
                "name": o["title"],
                "yes_capital": o["yes_capital"],
                "raw_volume": o["raw_volume"],
                "poly_prob": pp,
                "basis_prob": bp,
                "delta": delta,
                "payout": payout,
                "shares": m.circulating[i],
            })

        results.sort(key=lambda x: x["basis_prob"], reverse=True)

        print(f"\n{'='*115}")
        print(f"STARTING LIQUIDITY: ${reserve:,.0f}/outcome | {len(active)} outcomes | Init pool: ${reserve*len(active):,.0f} | YES capital: ${total_yes:,.0f}")
        print(f"{'='*115}")
        print(f"{'#':<4} {'Outcome':<30} {'YES Capital':>13} {'Poly Prob':>10} {'Basis Prob':>11} {'Delta':>8} {'Payout/\\$1':>11}")
        print(f"{'-'*90}")

        for i, r in enumerate(results[:25], 1):
            print(f"{i:<4} {r['name']:<30} ${r['yes_capital']:>11,.0f} {r['poly_prob']:>9.1%} {r['basis_prob']:>10.2%} {r['delta']:>+7.1%} ${r['payout']:>9.2f}")

        if len(results) > 25:
            print(f"     ... {len(results)-25} more outcomes below 25")

        top = results[0]
        print(f"\n  Pool (post-tax): ${pool:,.0f} | Tax: ${total_yes * TAX_RATE_BPS/10000:,.0f}")
        print(f"  Top: {top['name']} at {top['basis_prob']:.2%} (Poly: {top['poly_prob']:.1%})")

        all_results[reserve] = results

    # Comparison table
    print(f"\n\n{'='*100}")
    print(f"  PROBABILITY COMPARISON: Top 15 by Polymarket odds")
    print(f"{'='*100}")

    top15 = sorted(active, key=lambda x: x["probability"], reverse=True)[:15]

    header = f"{'Outcome':<28} {'Poly':>7} {'YES Cap':>11}"
    for r in reserves:
        header += f" {'$'+format(r,','):>10}"
    print(header)
    print("-" * (50 + 11 * len(reserves)))

    for cand in top15:
        line = f"{cand['title']:<28} {cand['probability']:>6.1%} ${cand['yes_capital']:>9,.0f}"
        for reserve in reserves:
            match = next((r for r in all_results[reserve] if r["name"] == cand["title"]), None)
            if match:
                line += f" {match['basis_prob']:>9.2%}"
            else:
                line += f" {'N/A':>9}"
        print(line)

    # Payout comparison
    print(f"\n  PAYOUT PER $1 BET (if outcome wins)")
    header2 = f"{'Outcome':<28} {'Poly':>7}"
    for r in reserves:
        header2 += f" {'$'+format(r,','):>10}"
    print(header2)
    print("-" * (38 + 11 * len(reserves)))

    for cand in top15:
        poly_pay = 1.0 / cand["probability"] if cand["probability"] > 0 else 0
        line = f"{cand['title']:<28} ${poly_pay:>5.2f}"
        for reserve in reserves:
            match = next((r for r in all_results[reserve] if r["name"] == cand["title"]), None)
            if match:
                line += f" ${match['payout']:>8.2f}"
            else:
                line += f" {'N/A':>9}"
        print(line)

    # Price impact analysis
    print(f"\n\n{'='*100}")
    print(f"  EARLY PRICE IMPACT: First $1,000 bet on the favorite ({top15[0]['title']})")
    print(f"{'='*100}")

    bet = 1000
    net = bet * (1 - TAX_RATE_BPS/10000)
    n = len(active)

    print(f"\n{'Init Reserve':>15} {'Init Prob':>10} {'After $1K':>10} {'Abs Move':>10} {'Rel Move':>10}")
    print("-" * 60)
    for r in reserves:
        init_prob = r / (n * r)
        new_r = r + net
        new_t = n * r + net
        new_prob = new_r / new_t
        print(f"${r:>13,} {init_prob:>9.2%} {new_prob:>9.2%} {new_prob-init_prob:>+9.2%} {(new_prob-init_prob)/init_prob:>+9.1%}")

    # Creator seed recommendation
    print(f"\n\n{'='*100}")
    print(f"  CREATOR SEED RECOMMENDATION (answering Alex's question)")
    print(f"{'='*100}")
    print(f"""
  The question: How much should creators seed a prediction market?

  Based on simulations, the seed amount should target:
  "First real bet should move probability by no more than X%"

  Target: <5% relative price impact for a $100 bet

  {'Outcomes':>10} {'Seed/Outcome':>15} {'Total Seed':>12} {'$100 Impact':>12}""")

    for num_outcomes in [2, 5, 10, 20, 44]:
        # Find seed where $100 bet moves price < 5% relative
        for seed in [100, 500, 1000, 2500, 5000, 10000, 25000, 50000]:
            init_p = seed / (num_outcomes * seed)
            net_100 = 100 * (1 - TAX_RATE_BPS/10000)
            new_p = (seed + net_100) / (num_outcomes * seed + net_100)
            rel_move = (new_p - init_p) / init_p
            if abs(rel_move) < 0.05:
                total = seed * num_outcomes
                print(f"  {num_outcomes:>10} ${seed:>13,} ${total:>10,} {rel_move:>+11.1%}")
                break

    print(f"""
  Rule of thumb: seed = 20x the expected minimum bet size per outcome.
  For $10 min bets: $200/outcome. For $100 min bets: $2,000/outcome.
  
  Private markets (creator-managed): Lower seed OK since fewer participants.
  Public markets: Higher seed for stable early pricing.
""")


if __name__ == "__main__":
    main()
