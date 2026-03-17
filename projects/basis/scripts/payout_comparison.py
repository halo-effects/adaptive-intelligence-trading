"""
Payout comparison: Basis vs Polymarket for the favorite.
Show total shares for Newsom and total pool from all losers.
"""
import json

TAX = 0.015
POOL = 5000  # Using formula seed for 44 outcomes: min(50000, max(5000, 500*44)) = $22,000
# Actually let's use the correct seed
N_OUTCOMES = 44
POOL = min(50000, max(5000, 500 * N_OUTCOMES))  # = $22,000

with open("polymarket_democratic_presidential_nominee_2028_outcomes.json") as f:
    data = json.load(f)

outcomes = []
for o in data["outcomes"]:
    if o["volume"] > 0 and o["probability"] > 0:
        outcomes.append({
            "title": o["title"],
            "probability": o["probability"],
            "volume": o["volume"],
            "yes_capital": o["volume"] * o["probability"],
        })

outcomes.sort(key=lambda x: x["probability"], reverse=True)
n = len(outcomes)
per = POOL / n

# Simulate
reserves = [float(per)] * n
total = float(POOL)
costs = [0.0] * n
shares = [0.0] * n
rounds = 500

for _ in range(rounds):
    for i, o in enumerate(outcomes):
        chunk = o["yes_capital"] / rounds
        if chunk > 0:
            net = chunk * (1 - TAX)
            new_v = reserves[i] + net
            new_t = total + net
            s = (net * new_t) / new_v
            prob_bp = (new_v * 10000) / new_t
            if prob_bp > 9500:
                rem = 10000 - prob_bp
                s = (s * rem * rem) / 250000
            reserves[i] = new_v
            total = new_t
            costs[i] += net
            shares[i] += s

probs = [reserves[i] / total for i in range(n)]
total_pool_usdc = sum(costs)  # Total real money in the system (excluding seed)

print(f"{'='*100}")
print(f"  PAYOUT COMPARISON: Democratic Nominee 2028")
print(f"  {n} outcomes | Seed: ${POOL:,} | Total volume in pool: ${total_pool_usdc:,.0f}")
print(f"{'='*100}")

# Show all outcomes with shares and costs
print(f"\n{'#':<3} {'Outcome':<28} {'Poly':>6} {'Basis':>7} {'$ In':>12} {'Shares':>12} {'Cost/Share':>11}")
print(f"{'-'*82}")

for i in range(min(20, n)):
    o = outcomes[i]
    cs = costs[i] / shares[i] if shares[i] > 0 else 0
    print(f"{i+1:<3} {o['title']:<28} {o['probability']:>5.1%} {probs[i]:>6.2%} ${costs[i]:>10,.0f} {shares[i]:>11,.0f} ${cs:>9.4f}")

# Newsom wins scenario
newsom_idx = 0  # sorted by probability, Newsom is #1
newsom_shares = shares[newsom_idx]
newsom_cost = costs[newsom_idx]

# Total pool from ALL losers
loser_pool = sum(costs[i] for i in range(n) if i != newsom_idx)
# Plus seed from losers
loser_seed = per * (n - 1)

print(f"\n{'='*100}")
print(f"  IF NEWSOM WINS:")
print(f"{'='*100}")
print(f"  Newsom total shares outstanding:  {newsom_shares:>15,.0f}")
print(f"  Newsom total $ invested:          ${newsom_cost:>14,.0f}")
print(f"  Loser pools total $:              ${loser_pool:>14,.0f}")
print(f"  Loser seed (virtual):             ${loser_seed:>14,.0f}")
print(f"  TOTAL WINNING POOL:               ${loser_pool + newsom_cost:>14,.0f}")
print(f"  (pool = all money, winners + losers)")
print(f"")
print(f"  Payout per share = total pool / winner shares")
print(f"  = ${loser_pool + newsom_cost:,.0f} / {newsom_shares:,.0f}")
payout_per_share = (loser_pool + newsom_cost) / newsom_shares if newsom_shares > 0 else 0
print(f"  = ${payout_per_share:.4f} per share")
print(f"")
print(f"  Average cost per Newsom share:    ${newsom_cost/newsom_shares:.4f}")
print(f"  Return per $ invested in Newsom:  ${payout_per_share / (newsom_cost/newsom_shares):.2f}")
print(f"  ROI:                              {(payout_per_share / (newsom_cost/newsom_shares) - 1)*100:.0f}%")

# Polymarket comparison
poly_newsom = outcomes[newsom_idx]["probability"]
poly_payout = 1.0 / poly_newsom
print(f"\n  POLYMARKET COMPARISON:")
print(f"  Buy Newsom at ${poly_newsom:.3f} → pays $1.00 = {poly_payout:.1f}x")
print(f"  Basis ROI: {payout_per_share / (newsom_cost/newsom_shares):.1f}x")

# Now show for #3, #5, #10
print(f"\n{'='*100}")
print(f"  PAYOUT COMPARISON ACROSS RANKINGS:")
print(f"{'='*100}")
print(f"  {'#':<3} {'Outcome':<28} {'Poly Price':>10} {'Poly Payout':>12} {'Basis $/sh':>11} {'Basis Payout':>13} {'Advantage':>10}")
print(f"  {'-'*90}")

for i in range(min(15, n)):
    o = outcomes[i]
    poly_price = o["probability"]
    poly_pay = 1.0 / poly_price
    
    # Basis: if this outcome wins, total pool / this outcome's shares
    their_pool = sum(costs[j] for j in range(n))  # everyone's money
    their_payout_per_share = their_pool / shares[i] if shares[i] > 0 else 0
    their_cost_per_share = costs[i] / shares[i] if shares[i] > 0 else 0
    their_return = their_payout_per_share / their_cost_per_share if their_cost_per_share > 0 else 0
    
    advantage = their_return / poly_pay if poly_pay > 0 else 0
    
    print(f"  {i+1:<3} {o['title']:<28} ${poly_price:>8.3f} {poly_pay:>11.1f}x ${their_cost_per_share:>9.4f} {their_return:>12.1f}x {advantage:>9.1f}x")
