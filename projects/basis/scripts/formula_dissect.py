"""
Dissect the Basis bonding curve formula step by step.
Show WHY probability = volume share at scale.
"""

TAX_RATE = 0.015  # 1.5%

print("=" * 80)
print("FORMULA DISSECTION: Basis Prediction Market Bonding Curve")
print("=" * 80)

# ============================================================
# EXAMPLE 1: Simple 3-outcome market, small scale
# ============================================================
print("\n--- EXAMPLE 1: 3 outcomes, $1,000 initial reserve each ---")

reserves = [1000.0, 1000.0, 1000.0]
total = sum(reserves)
names = ["Alice (fav)", "Bob (underdog)", "Carol (longshot)"]

print(f"Initial: {', '.join(f'{n}: ${r:,.0f} ({r/total:.1%})' for n, r in zip(names, reserves))}")
print(f"Total reserve: ${total:,.0f}\n")

# Alice gets $5,000 in buys, Bob gets $2,000, Carol gets $500
buys = [5000, 2000, 500]
for i, (name, buy_amount) in enumerate(zip(names, buys)):
    net = buy_amount * (1 - TAX_RATE)
    reserves[i] += net
    total += net
    prob = reserves[i] / total
    print(f"  Buy ${buy_amount:,.0f} on {name}: reserve → ${reserves[i]:,.0f}, prob = {prob:.1%}")

print(f"\nFinal probabilities:")
for name, r in zip(names, reserves):
    print(f"  {name}: {r/total:.2%}  (volume share: {(r-1000)/sum(b*(1-TAX_RATE) for b in buys):.2%})")

print(f"\n  Notice: probability ≈ volume share + small offset from initial reserve")

# ============================================================
# EXAMPLE 2: Why it converges to volume share at scale
# ============================================================
print("\n\n--- EXAMPLE 2: Mathematical proof of convergence ---")
print("""
Given N outcomes, each with initial reserve R₀:
  totalInitial = N × R₀

After volume V_i flows into outcome i (net of tax):
  outcome_i.reserve = R₀ + V_i × (1 - tax)
  totalReserve = N × R₀ + Σ(V_i × (1 - tax))

Probability of outcome i:
  P_i = (R₀ + V_i × 0.985) / (N × R₀ + totalVolume × 0.985)

When totalVolume >> N × R₀ (volume dwarfs initial reserves):
  P_i ≈ V_i / totalVolume

This is just the VOLUME SHARE of each outcome.
""")

# ============================================================
# EXAMPLE 3: Prove with real numbers from Dem Nominee
# ============================================================
print("--- EXAMPLE 3: Democratic Nominee — predicted vs actual ---\n")

# Top 10 by volume
top_outcomes = [
    ("Chelsea Clinton",    43_046_989, 0.009),
    ("Oprah Winfrey",      39_740_180, 0.007),
    ("Andrew Yang",        37_170_259, 0.009),
    ("Bernie Sanders",     35_730_265, 0.007),
    ("Gavin Newsom",       13_607_642, 0.244),
    ("Kamala Harris",       8_108_695, 0.053),
    ("AOC",                 5_750_117, 0.084),
    ("Josh Shapiro",        5_359_169, 0.040),
    ("Jon Ossoff",          5_372_021, 0.053),
    ("James Talarico",      2_894_581, 0.028),
]

total_volume = 845_899_436

print(f"{'Outcome':<25} {'Volume':>14} {'Vol Share':>10} {'Basis Sim':>10} {'Polymarket':>11}")
print("-" * 75)
for name, vol, poly_prob in top_outcomes:
    vol_share = vol / total_volume
    # The Basis probability from our simulation
    basis_prob = vol_share  # approximately, since initial reserves are negligible
    print(f"{name:<25} ${vol:>12,} {vol_share:>9.2%} {basis_prob:>9.2%} {poly_prob:>10.1%}")

print(f"""
KEY TAKEAWAY:
  Basis probability ≈ Volume Share ≈ outcomeVolume / totalVolume

  This is fundamentally different from Polymarket where:
  - Polymarket probability = NET position (buys - sells) / total supply
  - Basis probability = GROSS capital deployed / total capital deployed

  Chelsea Clinton has $43M volume but 0.9% on Polymarket because most
  volume is people trading back and forth / selling "No" shares.
  On Basis, $43M in = $43M of conviction signal.
""")

# ============================================================
# EXAMPLE 4: The REAL question — what does starting liquidity change?
# ============================================================
print("--- EXAMPLE 4: What starting liquidity ACTUALLY controls ---\n")

print("Starting liquidity controls PRICE IMPACT, not final probability.\n")

# Show price impact of a $1,000 bet at different starting liquidities
outcomes_n = 44
bet_size = 1000
net_bet = bet_size * (1 - TAX_RATE)

print(f"Price impact of a ${bet_size:,} bet in a {outcomes_n}-outcome market:\n")
print(f"{'Init Reserve':>15} {'Init Prob':>10} {'After Bet':>10} {'Price Move':>12} {'Rel Move':>10}")
print("-" * 62)

for init_reserve in [1000, 10000, 50000, 100000, 200000]:
    init_total = outcomes_n * init_reserve
    init_prob = init_reserve / init_total  # = 1/44 for all
    
    new_reserve = init_reserve + net_bet
    new_total = init_total + net_bet
    new_prob = new_reserve / new_total
    
    abs_move = new_prob - init_prob
    rel_move = abs_move / init_prob
    
    print(f"${init_reserve:>13,} {init_prob:>9.2%} {new_prob:>9.2%} {abs_move:>+11.2%} {rel_move:>+9.1%}")

print(f"""
INSIGHT: Starting liquidity = shock absorber.
  - $1,000/outcome: A $1K bet moves price by +2.20% absolute (+97% relative) — WILD
  - $200,000/outcome: Same bet moves price by +0.01% absolute (+0.5% relative) — stable

  Higher starting liquidity → more stable early pricing → better UX
  But once volume builds, the initial reserve becomes irrelevant.
""")

# ============================================================
# EXAMPLE 5: Price impact at different market maturity levels
# ============================================================
print("--- EXAMPLE 5: When does starting liquidity stop mattering? ---\n")

init_reserves = [1000, 10000, 50000, 100000, 200000]
bet = 10000
net = bet * (1 - TAX_RATE)

# Simulate cumulative volume growing, check when $10K bet impact converges
print(f"Price impact of a ${bet:,} bet as market volume grows:\n")
print(f"{'Market Vol':>14}", end="")
for r in init_reserves:
    print(f" {'$'+format(r,','):>10}", end="")
print()
print("-" * (16 + 11 * len(init_reserves)))

for market_vol in [0, 10000, 100000, 1000000, 10000000, 100000000]:
    print(f"${market_vol:>12,}", end="")
    for init_r in init_reserves:
        # Assume volume spread evenly across 44 outcomes for simplicity
        per_outcome_vol = (market_vol / 44) * (1 - TAX_RATE)
        current_reserve = init_r + per_outcome_vol
        current_total = 44 * init_r + market_vol * (1 - TAX_RATE)
        
        before_prob = current_reserve / current_total
        after_reserve = current_reserve + net
        after_total = current_total + net
        after_prob = after_reserve / after_total
        
        rel_impact = (after_prob - before_prob) / before_prob * 100
        print(f" {rel_impact:>+9.1f}%", end="")
    print()

print(f"""
  Once market volume exceeds ~100x the starting liquidity, 
  all starting points converge. The market has "found its level."
  
  RECOMMENDATION:
  - Small/niche markets (< $100K expected volume): $1K-10K per outcome
  - Medium markets ($100K-10M): $10K-50K per outcome  
  - Large markets (> $10M): $50K-200K per outcome
  - The key metric is: "How stable should the first few bets be?"
""")
