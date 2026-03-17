"""
Early vs late buyer payout comparison.
Break Newsom's volume into tranches and show what each tranche paid per share
vs what they'd receive if Newsom wins.
"""
import json

TAX = 0.015
N_OUTCOMES = 44
POOL = min(50000, max(5000, 500 * N_OUTCOMES))  # $22,000

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

# Simulate with detailed tracking of Newsom tranches
reserves = [float(per)] * n
total = float(POOL)
costs = [0.0] * n
circ = [0.0] * n

# Track Newsom buys in 10 tranches
TRANCHES = 10
newsom_total_yes = outcomes[0]["yes_capital"]
tranche_size = newsom_total_yes / TRANCHES
newsom_tranche_shares = [0.0] * TRANCHES
newsom_tranche_cost = [0.0] * TRANCHES
newsom_tranche_prob_at_entry = [0.0] * TRANCHES
current_tranche = 0
tranche_spent = 0.0

rounds = 500
for r in range(rounds):
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
            
            # Track Newsom tranches
            if i == 0:  # Newsom
                tranche_spent += chunk
                if current_tranche < TRANCHES:
                    newsom_tranche_shares[current_tranche] += s
                    newsom_tranche_cost[current_tranche] += chunk
                    newsom_tranche_prob_at_entry[current_tranche] = reserves[i] / total  # prob BEFORE this buy
                    
                    if tranche_spent >= tranche_size * (current_tranche + 1) and current_tranche < TRANCHES - 1:
                        current_tranche += 1
            
            reserves[i] = new_v
            total = new_t
            costs[i] += net
            circ[i] += s

total_pool = sum(costs)
total_newsom_shares = sum(newsom_tranche_shares)

# Payout per share if Newsom wins = total pool / Newsom shares
payout_per_share = total_pool / total_newsom_shares

print(f"{'='*110}")
print(f"  EARLY vs LATE BUYER: Newsom on Basis (44-outcome Democratic Nominee)")
print(f"  Total pool: ${total_pool:,.0f} | Newsom shares: {total_newsom_shares:,.0f} | Payout/share: ${payout_per_share:.4f}")
print(f"{'='*110}")

print(f"\n  {'Tranche':<10} {'$ Invested':>12} {'Shares':>14} {'Avg $/Share':>12} {'Prob at Entry':>14} {'Payout/Share':>13} {'Return':>8} {'ROI':>8}")
print(f"  {'-'*94}")

for t in range(TRANCHES):
    if newsom_tranche_shares[t] > 0:
        avg_cost = newsom_tranche_cost[t] / newsom_tranche_shares[t]
        ret = payout_per_share / avg_cost
        roi = (ret - 1) * 100
        pct = (t + 1) * 10
        label = f"First {pct}%" if t == 0 else f"{t*10+1}-{pct}%"
        print(f"  {label:<10} ${newsom_tranche_cost[t]:>10,.0f} {newsom_tranche_shares[t]:>13,.0f} ${avg_cost:>10.4f} {newsom_tranche_prob_at_entry[t]:>13.1%} ${payout_per_share:>11.4f} {ret:>7.1f}x {roi:>+7.0f}%")

# Polymarket comparison
poly_prob = outcomes[0]["probability"]
print(f"\n{'='*110}")
print(f"  POLYMARKET COMPARISON (Newsom at {poly_prob:.1%}):")
print(f"{'='*110}")
print(f"  On Polymarket, every buyer pays ~${poly_prob:.3f}/share and gets $1.00 if correct = {1/poly_prob:.1f}x")
print(f"  (CLOB means price is roughly stable — early and late buyers pay similar prices)")
print(f"")
print(f"  On Basis:")
print(f"    First 10% of buyers:  avg ${newsom_tranche_cost[0]/newsom_tranche_shares[0]:.4f}/share → {payout_per_share/(newsom_tranche_cost[0]/newsom_tranche_shares[0]):.1f}x return")
print(f"    Last 10% of buyers:   avg ${newsom_tranche_cost[-1]/newsom_tranche_shares[-1]:.4f}/share → {payout_per_share/(newsom_tranche_cost[-1]/newsom_tranche_shares[-1]):.1f}x return")
print(f"    Polymarket any buyer: ${poly_prob:.3f}/share → {1/poly_prob:.1f}x return")

# Now do the same for an underdog — Shapiro (#5)
shapiro_idx = 4
print(f"\n\n{'='*110}")
print(f"  UNDERDOG COMPARISON: Shapiro (#5, Poly {outcomes[shapiro_idx]['probability']:.1%})")
print(f"{'='*110}")

# Re-simulate with Shapiro tranche tracking
reserves2 = [float(per)] * n
total2 = float(POOL)
costs2 = [0.0] * n
circ2 = [0.0] * n

shapiro_total_yes = outcomes[shapiro_idx]["yes_capital"]
tranche_size_s = shapiro_total_yes / TRANCHES
shapiro_tranche_shares = [0.0] * TRANCHES
shapiro_tranche_cost = [0.0] * TRANCHES
shapiro_tranche_prob = [0.0] * TRANCHES
current_tranche_s = 0
tranche_spent_s = 0.0

for r in range(rounds):
    for i, o in enumerate(outcomes):
        chunk = o["yes_capital"] / rounds
        if chunk > 0:
            net = chunk * (1 - TAX)
            new_v = reserves2[i] + net
            new_t = total2 + net
            s = (net * new_t) / new_v
            prob_bp = (new_v * 10000) / new_t
            if prob_bp > 9500:
                rem = 10000 - prob_bp
                s = (s * rem * rem) / 250000
            
            if i == shapiro_idx:
                tranche_spent_s += chunk
                if current_tranche_s < TRANCHES:
                    shapiro_tranche_shares[current_tranche_s] += s
                    shapiro_tranche_cost[current_tranche_s] += chunk
                    shapiro_tranche_prob[current_tranche_s] = reserves2[i] / total2
                    if tranche_spent_s >= tranche_size_s * (current_tranche_s + 1) and current_tranche_s < TRANCHES - 1:
                        current_tranche_s += 1
            
            reserves2[i] = new_v
            total2 = new_t
            costs2[i] += net
            circ2[i] += s

total_pool2 = sum(costs2)
total_shapiro_shares = sum(shapiro_tranche_shares)
payout_shapiro = total_pool2 / total_shapiro_shares if total_shapiro_shares > 0 else 0

print(f"  Total pool: ${total_pool2:,.0f} | Shapiro shares: {total_shapiro_shares:,.0f} | Payout/share: ${payout_shapiro:.4f}")

print(f"\n  {'Tranche':<10} {'$ Invested':>12} {'Shares':>14} {'Avg $/Share':>12} {'Prob at Entry':>14} {'Payout/Share':>13} {'Return':>8} {'ROI':>8}")
print(f"  {'-'*94}")

for t in range(TRANCHES):
    if shapiro_tranche_shares[t] > 0:
        avg_cost = shapiro_tranche_cost[t] / shapiro_tranche_shares[t]
        ret = payout_shapiro / avg_cost
        roi = (ret - 1) * 100
        pct = (t + 1) * 10
        label = f"First {pct}%" if t == 0 else f"{t*10+1}-{pct}%"
        print(f"  {label:<10} ${shapiro_tranche_cost[t]:>10,.0f} {shapiro_tranche_shares[t]:>13,.0f} ${avg_cost:>10.4f} {shapiro_tranche_prob[t]:>13.1%} ${payout_shapiro:>11.4f} {ret:>7.1f}x {roi:>+7.0f}%")

poly_shapiro = outcomes[shapiro_idx]["probability"]
print(f"\n  Polymarket: ${poly_shapiro:.3f}/share → {1/poly_shapiro:.1f}x")
print(f"  Basis first 10%: ${shapiro_tranche_cost[0]/shapiro_tranche_shares[0]:.4f}/share → {payout_shapiro/(shapiro_tranche_cost[0]/shapiro_tranche_shares[0]):.1f}x")
print(f"  Basis last 10%:  ${shapiro_tranche_cost[-1]/shapiro_tranche_shares[-1]:.4f}/share → {payout_shapiro/(shapiro_tranche_cost[-1]/shapiro_tranche_shares[-1]):.1f}x")
