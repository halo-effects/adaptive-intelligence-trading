"""Find the starting liquidity sweet spot for EACH outcome, not just the frontrunner."""
import json

TAX = 0.015

with open("polymarket_democratic_presidential_nominee_2028_outcomes.json") as f:
    data = json.load(f)

outcomes = []
for o in data["outcomes"]:
    if o["volume"] > 0 and o["probability"] > 0:
        outcomes.append({
            "title": o["title"],
            "volume": o["volume"],
            "prob": o["probability"],
            "yes_cap": o["volume"] * o["probability"],
        })
outcomes.sort(key=lambda x: x["prob"], reverse=True)

reserves = [1000, 10000, 50000, 100000, 200000]
n = len(outcomes)


def sim(init_r):
    res = [init_r] * n
    total = init_r * n
    rounds = 1000
    for _ in range(rounds):
        for i, o in enumerate(outcomes):
            chunk = o["yes_cap"] / rounds
            if chunk > 0:
                net = chunk * (1 - TAX)
                res[i] += net
                total += net
    probs = [r / total for r in res]
    return probs


# Run all sims
sim_results = {}
for r in reserves:
    sim_results[r] = sim(r)

# Print detailed comparison for ALL active outcomes
print(f"\n{'='*120}")
print(f"  SWEET SPOT ANALYSIS: All 44 outcomes — Basis prob vs Polymarket prob at each starting liquidity")
print(f"{'='*120}")
print(f"{'#':<3} {'Outcome':<28} {'Poly':>6} {'YES Cap':>11}", end="")
for r in reserves:
    print(f" {'$'+format(r,','):>9}", end="")
print(f" {'Best Fit':>10} {'Best Delta':>10}")
print("-" * 120)

sweet_spot_counts = {r: 0 for r in reserves}
total_abs_delta = {r: 0.0 for r in reserves}

for i, o in enumerate(outcomes):
    line = f"{i+1:<3} {o['title']:<28} {o['prob']:>5.1%} ${o['yes_cap']:>9,.0f}"
    
    best_r = None
    best_delta = 999
    
    for r in reserves:
        bp = sim_results[r][i]
        delta = bp - o["prob"]
        abs_d = abs(delta)
        total_abs_delta[r] += abs_d
        line += f" {bp:>8.2%}"
        
        if abs_d < best_delta:
            best_delta = abs_d
            best_r = r
    
    sweet_spot_counts[best_r] += 1
    line += f" {'$'+format(best_r,','):>10} {best_delta:>+9.1%}"
    print(line)

# Summary stats
print(f"\n{'='*80}")
print(f"  SUMMARY: Which starting liquidity fits the most outcomes?")
print(f"{'='*80}")
print(f"\n  Outcomes where each reserve is the closest match to Polymarket:")
for r in reserves:
    print(f"    ${r:>7,}/outcome: {sweet_spot_counts[r]:>3} outcomes ({sweet_spot_counts[r]/n*100:.0f}%)")

print(f"\n  Average absolute delta from Polymarket (lower = better):")
for r in reserves:
    avg = total_abs_delta[r] / n
    print(f"    ${r:>7,}/outcome: {avg:.2%} avg delta")

# Tier analysis
print(f"\n{'='*80}")
print(f"  BY PROBABILITY TIER: Which reserve fits best?")
print(f"{'='*80}")

tiers = [
    ("Frontrunners (>10%)", lambda o: o["prob"] > 0.10),
    ("Contenders (3-10%)", lambda o: 0.03 <= o["prob"] <= 0.10),
    ("Underdogs (1-3%)", lambda o: 0.01 <= o["prob"] < 0.03),
    ("Longshots (<1%)", lambda o: o["prob"] < 0.01),
]

for tier_name, tier_fn in tiers:
    tier_outcomes = [(i, o) for i, o in enumerate(outcomes) if tier_fn(o)]
    if not tier_outcomes:
        continue
    
    print(f"\n  {tier_name} ({len(tier_outcomes)} outcomes):")
    print(f"  {'Reserve':>12} {'Avg Delta':>10} {'Max Delta':>10}")
    
    for r in reserves:
        deltas = [abs(sim_results[r][i] - o["prob"]) for i, o in tier_outcomes]
        avg_d = sum(deltas) / len(deltas)
        max_d = max(deltas)
        marker = " <-- best" if avg_d == min(
            sum(abs(sim_results[rr][i] - o["prob"]) for i, o in tier_outcomes) / len(tier_outcomes)
            for rr in reserves
        ) else ""
        print(f"  ${r:>10,} {avg_d:>9.2%} {max_d:>9.2%}{marker}")

# The tradeoff
print(f"""
{'='*80}
  THE TRADEOFF
{'='*80}
  Lower starting liquidity ($1K-$10K):
    + Probabilities converge faster to "true" odds
    + Less capital needed to seed
    - First bets are wildly volatile
    - Manipulable with small amounts
    
  Higher starting liquidity ($100K-$200K):  
    + Stable early pricing
    + Harder to manipulate
    - Probabilities stay flatter longer (diluted by initial reserve)
    - Requires more capital to seed
    
  The right answer depends on the MARKET TYPE:
    - Public, high-expected-volume markets: $1K-$10K (volume will find the level)
    - Private, creator-managed markets: $10K-$50K (stability matters more)
    - Markets expecting slow buildup: $50K+ (protect early participants)
""")
