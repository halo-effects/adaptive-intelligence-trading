"""
Interleaved payout simulation: Buy all outcomes simultaneously in proportion
to their final volume, in small consecutive steps. Track shares per tranche
for early vs late buyer comparison.

Approach:
- Use Polymarket YES capital as target final volume per outcome
- Each "round" buys a proportional chunk of each outcome (favorite gets more per round)
- 10,000 rounds to get smooth granularity
- Track 10 tranches per outcome for early/late comparison
- Compute final payout: total_pool / winner_shares
"""
import json
import time

TAX = 0.015
N_ROUNDS = 10000  # High granularity for smooth price curves

# Load data
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

# Seed formula: 128 in full dataset, but we use 44 active outcomes
# Actually use all outcomes we have
seed = min(50000, max(5000, 500 * n))
per = seed / n

print(f"{'#'*120}")
print(f"  INTERLEAVED PAYOUT SIMULATION")
print(f"  {n} outcomes | Seed: ${seed:,} (${per:.2f}/outcome) | {N_ROUNDS:,} rounds")
print(f"{'#'*120}")

# Target volumes per outcome
target_vols = [o["yes_capital"] for o in outcomes]
total_target = sum(target_vols)
vol_per_round = [tv / N_ROUNDS for tv in target_vols]

print(f"\n  Total target YES volume: ${total_target:,.0f}")
print(f"  Largest (Newsom): ${target_vols[0]:,.0f} → ${vol_per_round[0]:,.2f}/round")
print(f"  Smallest active: ${target_vols[-1]:,.0f} → ${vol_per_round[-1]:,.2f}/round")

# Initialize bonding curve
reserves = [float(per)] * n
total = float(seed)

# Tracking
costs = [0.0] * n           # Total $ spent per outcome
shares = [0.0] * n          # Total shares per outcome
spent_so_far = [0.0] * n    # Running total spent

# Track 10 tranches per outcome for early/late analysis
TRANCHES = 10
tranche_shares = [[0.0] * TRANCHES for _ in range(n)]
tranche_costs = [[0.0] * TRANCHES for _ in range(n)]
tranche_entry_price = [[0.0] * TRANCHES for _ in range(n)]  # avg cost/share in tranche

start = time.time()

for r in range(N_ROUNDS):
    for i in range(n):
        chunk = vol_per_round[i]
        if chunk <= 0:
            continue
        
        net = chunk * (1 - TAX)
        new_v = reserves[i] + net
        new_t = total + net
        s = (net * new_t) / new_v
        
        # Slippage penalty
        prob_bp = (new_v * 10000) / new_t
        if prob_bp > 9500:
            rem = 10000 - prob_bp
            s = (s * rem * rem) / 250000
        
        reserves[i] = new_v
        total = new_t
        costs[i] += chunk  # Track gross spend (before tax)
        shares[i] += s
        spent_so_far[i] += chunk
        
        # Assign to tranche
        tranche_idx = min(int(spent_so_far[i] / target_vols[i] * TRANCHES), TRANCHES - 1)
        tranche_shares[i][tranche_idx] += s
        tranche_costs[i][tranche_idx] += chunk

elapsed = time.time() - start
total_pool = sum(costs)

print(f"\n  Simulation complete in {elapsed:.1f}s")
print(f"  Total pool: ${total_pool:,.0f}")

# Compute final probabilities
probs = [reserves[i] / total for i in range(n)]

# Show top 15 outcomes
print(f"\n{'='*120}")
print(f"  FINAL STATE: Top 15 Outcomes")
print(f"{'='*120}")
print(f"  {'#':<3} {'Outcome':<28} {'Poly':>6} {'Basis':>7} {'$ Volume':>12} {'Shares':>14} {'Avg $/sh':>10}")
print(f"  {'-'*84}")

for i in range(min(15, n)):
    o = outcomes[i]
    avg = costs[i] / shares[i] if shares[i] > 0 else 0
    print(f"  {i+1:<3} {o['title']:<28} {o['probability']:>5.1%} {probs[i]:>6.2%} ${costs[i]:>10,.0f} {shares[i]:>13,.0f} ${avg:>8.4f}")

# PAYOUT ANALYSIS: For each potential winner, show early vs late buyer returns
print(f"\n\n{'='*120}")
print(f"  PAYOUT ANALYSIS: Early vs Late Buyers")
print(f"  payout_per_share = total_pool / winner_total_shares")
print(f"{'='*120}")

# Analyze top 5 outcomes as potential winners
for wi in range(min(5, n)):
    winner_shares = shares[wi]
    payout_per_share = total_pool / winner_shares if winner_shares > 0 else 0
    
    o = outcomes[wi]
    poly_price = o["probability"]
    poly_return = 1.0 / poly_price
    
    print(f"\n  {'─'*100}")
    print(f"  IF {o['title'].upper()} WINS (Poly: {poly_price:.1%})")
    print(f"  Total pool: ${total_pool:,.0f} | Winner shares: {winner_shares:,.0f} | Payout/share: ${payout_per_share:.4f}")
    print(f"  {'─'*100}")
    
    print(f"  {'Tranche':<12} {'$ Spent':>12} {'Shares':>14} {'Avg $/sh':>10} {'Payout/sh':>11} {'Return':>8} {'vs Poly':>10}")
    print(f"  {'-'*80}")
    
    for t in range(TRANCHES):
        ts = tranche_shares[wi][t]
        tc = tranche_costs[wi][t]
        if ts > 0:
            avg_cost = tc / ts
            ret = payout_per_share / avg_cost
            poly_adv = ret / poly_return
            pct = (t + 1) * 10
            label = f"First {pct}%" if t == 0 else f"{t*10+1}-{pct}%"
            print(f"  {label:<12} ${tc:>10,.0f} {ts:>13,.0f} ${avg_cost:>8.4f} ${payout_per_share:>9.4f} {ret:>7.1f}x {poly_adv:>9.1f}x")
    
    # Summary
    early_cost = tranche_costs[wi][0] / tranche_shares[wi][0] if tranche_shares[wi][0] > 0 else 0
    late_cost = tranche_costs[wi][-1] / tranche_shares[wi][-1] if tranche_shares[wi][-1] > 0 else 0
    early_ret = payout_per_share / early_cost if early_cost > 0 else 0
    late_ret = payout_per_share / late_cost if late_cost > 0 else 0
    
    print(f"\n  Summary:")
    print(f"    Polymarket (any buyer):  ${poly_price:.4f}/share → {poly_return:.1f}x return")
    print(f"    Basis FIRST 10% buyers: ${early_cost:.4f}/share → {early_ret:.1f}x return  ({early_ret/poly_return:.1f}x vs Poly)")
    print(f"    Basis LAST 10% buyers:  ${late_cost:.4f}/share → {late_ret:.1f}x return  ({late_ret/poly_return:.1f}x vs Poly)")
    print(f"    Early buyer advantage over late: {late_cost/early_cost:.1f}x more shares per dollar")


# Grand summary
print(f"\n\n{'='*120}")
print(f"  GRAND SUMMARY: Basis vs Polymarket Payout Multiples")
print(f"{'='*120}")
print(f"\n  {'Outcome':<28} {'Poly Return':>12} {'Basis Early':>12} {'Basis Late':>12} {'Early vs Poly':>14} {'Late vs Poly':>13}")
print(f"  {'-'*94}")

for wi in range(min(10, n)):
    o = outcomes[wi]
    poly_ret = 1.0 / o["probability"]
    pps = total_pool / shares[wi] if shares[wi] > 0 else 0
    
    ec = tranche_costs[wi][0] / tranche_shares[wi][0] if tranche_shares[wi][0] > 0 else 1
    lc = tranche_costs[wi][-1] / tranche_shares[wi][-1] if tranche_shares[wi][-1] > 0 else 1
    
    er = pps / ec if ec > 0 else 0
    lr = pps / lc if lc > 0 else 0
    
    print(f"  {o['title']:<28} {poly_ret:>11.1f}x {er:>11.1f}x {lr:>11.1f}x {er/poly_ret:>13.1f}x {lr/poly_ret:>12.1f}x")
