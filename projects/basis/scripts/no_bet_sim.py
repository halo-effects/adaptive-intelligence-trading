"""
Simulate a betAgainst() mechanism.

When a user bets NO on outcome X, the USDC is distributed as YES buys
across all OTHER outcomes, weighted by their current probability.

We estimate NO volume per outcome as: volume × (1 - probability)
This is the complement of our YES proxy.
"""
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
            "no_cap": o["volume"] * (1 - o["probability"]),
        })
outcomes.sort(key=lambda x: x["prob"], reverse=True)

n = len(outcomes)
total_yes = sum(o["yes_cap"] for o in outcomes)
total_no = sum(o["no_cap"] for o in outcomes)
total_raw = sum(o["volume"] for o in outcomes)

POOL = 50_000
per_out = POOL / n


class Market:
    def __init__(self, nn, init_per):
        self.n = nn
        self.reserves = [float(init_per)] * nn
        self.total = float(init_per * nn)

    def buy(self, idx, usdc):
        net = usdc * (1 - TAX)
        self.reserves[idx] += net
        self.total += net

    def prob(self, idx):
        return self.reserves[idx] / self.total

    def probs(self):
        return [self.reserves[i] / self.total for i in range(self.n)]


def run_yes_only():
    """Original: only YES buys."""
    m = Market(n, per_out)
    rounds = 1000
    for _ in range(rounds):
        for i, o in enumerate(outcomes):
            chunk = o["yes_cap"] / rounds
            if chunk > 0:
                m.buy(i, chunk)
    return m.probs()


def run_yes_plus_no():
    """YES buys + NO buys distributed as weighted YES across other outcomes."""
    m = Market(n, per_out)
    rounds = 500  # fewer rounds since we're doing more work per round

    for _ in range(rounds):
        # Phase 1: YES buys
        for i, o in enumerate(outcomes):
            chunk = o["yes_cap"] / rounds
            if chunk > 0:
                m.buy(i, chunk)

        # Phase 2: NO buys — distribute to all OTHER outcomes by current prob
        for i, o in enumerate(outcomes):
            no_chunk = o["no_cap"] / rounds
            if no_chunk <= 0:
                continue

            # Get current probabilities of all OTHER outcomes
            other_probs = []
            for j in range(n):
                if j != i:
                    other_probs.append((j, m.prob(j)))

            # Normalize weights
            total_other_prob = sum(p for _, p in other_probs)
            if total_other_prob <= 0:
                continue

            # Distribute NO capital as weighted YES buys
            for j, p in other_probs:
                weight = p / total_other_prob
                m.buy(j, no_chunk * weight)

    return m.probs()


def run_no_equal_weight():
    """NO buys distributed EQUALLY across other outcomes (simpler)."""
    m = Market(n, per_out)
    rounds = 500

    for _ in range(rounds):
        for i, o in enumerate(outcomes):
            chunk = o["yes_cap"] / rounds
            if chunk > 0:
                m.buy(i, chunk)

        for i, o in enumerate(outcomes):
            no_chunk = o["no_cap"] / rounds
            if no_chunk <= 0:
                continue
            per_other = no_chunk / (n - 1)
            for j in range(n):
                if j != i:
                    m.buy(j, per_other)

    return m.probs()


print(f"\n{'#'*120}")
print(f"  BET AGAINST SIMULATION: Democratic Presidential Nominee 2028")
print(f"  Total YES capital: ${total_yes:,.0f} | Total NO capital: ${total_no:,.0f}")
print(f"  NO is {total_no/total_yes:.1f}x larger than YES (makes sense — most volume is betting against)")
print(f"  Starting pool: ${POOL:,.0f} total (${per_out:,.0f}/outcome)")
print(f"{'#'*120}")

print("\nRunning 3 scenarios...")
print("  1. YES only (current Basis)")
yes_probs = run_yes_only()
print("  2. YES + NO (weighted distribution)")
yes_no_probs = run_yes_plus_no()
print("  3. YES + NO (equal distribution)")
yes_no_equal = run_no_equal_weight()

print(f"\n{'='*130}")
print(f"  RESULTS: Top 20 by Polymarket probability")
print(f"{'='*130}")
print(f"{'#':<3} {'Outcome':<28} {'Poly':>6} {'YES only':>9} {'YES+NO wt':>10} {'YES+NO eq':>10} {'Best':>10} {'Best Delta':>11}")
print("-" * 92)

for rank, (i, o) in enumerate(sorted(enumerate(outcomes), key=lambda x: x[1]["prob"], reverse=True)[:20], 1):
    pp = o["prob"]
    yo = yes_probs[i]
    ynw = yes_no_probs[i]
    yne = yes_no_equal[i]

    deltas = {
        "YES only": abs(yo - pp),
        "YES+NO wt": abs(ynw - pp),
        "YES+NO eq": abs(yne - pp),
    }
    best = min(deltas, key=deltas.get)
    best_d = (ynw if best == "YES+NO wt" else yne if best == "YES+NO eq" else yo) - pp

    print(f"{rank:<3} {o['title']:<28} {pp:>5.1%} {yo:>8.2%} {ynw:>9.2%} {yne:>9.2%} {best:>10} {best_d:>+10.1%}")

# Summary stats
print(f"\n{'='*80}")
print(f"  ACCURACY SUMMARY (avg |delta| from Polymarket)")
print(f"{'='*80}")

for label, probs_list in [("YES only", yes_probs), ("YES+NO weighted", yes_no_probs), ("YES+NO equal", yes_no_equal)]:
    avg_d = sum(abs(probs_list[i] - outcomes[i]["prob"]) for i in range(n)) / n
    max_d = max(abs(probs_list[i] - outcomes[i]["prob"]) for i in range(n))

    # Correlation with Polymarket
    poly = [outcomes[i]["prob"] for i in range(n)]
    basis = [probs_list[i] for i in range(n)]
    mean_p = sum(poly) / n
    mean_b = sum(basis) / n
    cov = sum((p - mean_p) * (b - mean_b) for p, b in zip(poly, basis)) / n
    std_p = (sum((p - mean_p)**2 for p in poly) / n) ** 0.5
    std_b = (sum((b - mean_b)**2 for b in basis) / n) ** 0.5
    corr = cov / (std_p * std_b) if std_p > 0 and std_b > 0 else 0

    print(f"  {label:<20} avg delta: {avg_d:.2%}  max delta: {max_d:.2%}  correlation: {corr:.4f}")

# The verdict
print(f"""
{'='*80}
  VERDICT
{'='*80}
  Does adding a betAgainst() mechanism fix the probability accuracy?
  
  If YES+NO scenarios show significantly lower deltas and higher
  correlation with Polymarket, then a betAgainst() contract function
  would meaningfully improve prediction accuracy.
  
  If the deltas are similar, the issue is deeper than missing NO bets
  and lies in the fundamental difference between CLOB marginal pricing
  and bonding curve cumulative pricing.
""")
