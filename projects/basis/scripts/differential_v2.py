"""
Corrected: Starting liquidity is TOTAL pool, not per-outcome.
$50K total / 44 outcomes = $1,136 per outcome.
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
        })
outcomes.sort(key=lambda x: x["prob"], reverse=True)

n = len(outcomes)
total_yes = sum(o["yes_cap"] for o in outcomes)

# CORRECTED: total pool amounts, divided by number of outcomes
total_pools = [1_000, 10_000, 50_000, 100_000, 200_000]


def sim(per_outcome_reserve):
    res = [float(per_outcome_reserve)] * n
    total = float(per_outcome_reserve * n)
    rounds = 1000
    costs = [0.0] * n
    circ = [0.0] * n
    for _ in range(rounds):
        for i, o in enumerate(outcomes):
            chunk = o["yes_cap"] / rounds
            if chunk > 0:
                net = chunk * (1 - TAX)
                new_v = res[i] + net
                new_t = total + net
                shares = (net * new_t) / new_v
                prob_bp = (new_v * 10000) / new_t
                if prob_bp > 9500:
                    rem = 10000 - prob_bp
                    shares = (shares * rem * rem) / 250000
                res[i] = new_v
                total = new_t
                costs[i] += net
                circ[i] += shares
    probs = [r / total for r in res]
    pool = sum(costs)
    return probs, costs, circ, pool


print(f"\n{'#'*120}")
print(f"  BASIS LIQUIDITY SIMULATION (CORRECTED)")
print(f"  Starting liquidity = TOTAL pool, split equally across {n} outcomes")
print(f"  YES Conviction Capital: ${total_yes:,.0f}")
print(f"{'#'*120}")

# Show the corrected reserves
print(f"\n  {'Total Pool':>12} {'Per Outcome':>14} {'% of YES Cap':>14}")
print(f"  {'-'*44}")
for tp in total_pools:
    per = tp / n
    pct = tp / total_yes * 100
    print(f"  ${tp:>10,} ${per:>12,.0f} {pct:>12.2f}%")

# Run $50K total sim in detail
POOL = 50_000
per_out = POOL / n
probs, costs, circ, pool = sim(per_out)

print(f"\n\n{'='*130}")
print(f"  DETAILED: $50K TOTAL ({n} outcomes x ${per_out:,.0f}/outcome)")
print(f"  Seed is {POOL/total_yes:.2%} of YES capital -- much less dilution")
print(f"{'='*130}")

print(f"\n{'#':<3} {'Outcome':<28} {'Poly':>6} {'Basis':>7} {'Delta':>7} {'YES Cap':>11} {'YES%':>6}")
print("-" * 75)

for i, o in enumerate(outcomes):
    bp = probs[i]
    pp = o["prob"]
    delta = bp - pp
    yes_pct = o["yes_cap"] / total_yes * 100
    print(f"{i+1:<3} {o['title']:<28} {pp:>5.1%} {bp:>6.2%} {delta:>+6.1%} ${o['yes_cap']:>9,.0f} {yes_pct:>5.1f}%")

# Run all total pool sizes
print(f"\n\n{'='*120}")
print(f"  COMPARISON: Top 15 outcomes across all starting liquidities (TOTAL pool)")
print(f"{'='*120}")

all_results = {}
for tp in total_pools:
    per = tp / n
    probs_r, _, _, _ = sim(per)
    all_results[tp] = probs_r

top15 = sorted(range(n), key=lambda i: outcomes[i]["prob"], reverse=True)[:15]

header = f"{'#':<3} {'Outcome':<28} {'Poly':>6}"
for tp in total_pools:
    header += f" {'$'+format(tp,',')+' tot':>12}"
print(header)
print("-" * (40 + 13 * len(total_pools)))

for rank, i in enumerate(top15, 1):
    o = outcomes[i]
    line = f"{rank:<3} {o['title']:<28} {o['prob']:>5.1%}"
    for tp in total_pools:
        bp = all_results[tp][i]
        line += f" {bp:>11.2%}"
    print(line)

# Delta table
print(f"\n  DELTA FROM POLYMARKET (negative = Basis underestimates, positive = overestimates)")
header2 = f"{'#':<3} {'Outcome':<28} {'Poly':>6}"
for tp in total_pools:
    header2 += f" {'$'+format(tp,',')+' tot':>12}"
print(header2)
print("-" * (40 + 13 * len(total_pools)))

for rank, i in enumerate(top15, 1):
    o = outcomes[i]
    line = f"{rank:<3} {o['title']:<28} {o['prob']:>5.1%}"
    for tp in total_pools:
        delta = all_results[tp][i] - o["prob"]
        line += f" {delta:>+11.1%}"
    print(line)

# Average delta
print(f"\n  Average |delta| across ALL {n} outcomes:")
for tp in total_pools:
    avg = sum(abs(all_results[tp][i] - outcomes[i]["prob"]) for i in range(n)) / n
    print(f"    ${tp:>7,} total (${tp/n:>6,.0f}/outcome): {avg:.2%} avg delta")

# Price impact
print(f"\n\n{'='*80}")
print(f"  EARLY PRICE IMPACT: First $100 bet at each total pool size")
print(f"{'='*80}")
bet = 100
net_bet = bet * (1 - TAX)
print(f"\n  {'Total Pool':>12} {'Per Outcome':>12} {'Init Prob':>10} {'After $100':>11} {'Rel Move':>10}")
print(f"  {'-'*60}")
for tp in total_pools:
    per = tp / n
    init_p = per / tp  # = 1/n
    new_per = per + net_bet
    new_total = tp + net_bet
    new_p = new_per / new_total
    rel = (new_p - init_p) / init_p
    print(f"  ${tp:>10,} ${per:>10,.0f} {init_p:>9.2%} {new_p:>10.2%} {rel:>+9.1%}")
