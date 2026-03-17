"""
First $100 buy comparison: Basis vs Polymarket
128-outcome market, buying Newsom.
"""

TAX = 0.015

# Basis: 128 outcomes, $50K seed cap
n = 128
seed = 50000
per = seed / n  # $390.63 per outcome
init_prob = 1 / n  # 0.78%

# First $100 buy on Basis
amount = 100
net = amount * (1 - TAX)  # $98.50
new_v = per + net  # 390.63 + 98.50 = 489.13
new_t = seed + net  # 50000 + 98.50 = 50098.50
shares = (net * new_t) / new_v
new_prob = new_v / new_t

# Effective price per share
eff_price = amount / shares

print(f"{'='*80}")
print(f"  FIRST $100 BUY: Newsom on 128-outcome market")
print(f"{'='*80}")
print(f"\n  BASIS:")
print(f"    Seed: ${seed:,} (${per:.2f}/outcome)")
print(f"    Starting prob: {init_prob:.2%} (${init_prob:.4f}/share)")
print(f"    ")
print(f"    $100 buy:")
print(f"      Net after 1.5% tax: ${net:.2f}")
print(f"      Shares received: {shares:,.0f}")
print(f"      Effective price: ${eff_price:.6f}/share")
print(f"      New probability: {new_prob:.2%}")
print(f"      Probability move: {init_prob:.2%} → {new_prob:.2%}")

# Polymarket comparison at various starting prices
print(f"\n  POLYMARKET (each outcome = separate binary market):")
print(f"    Newsom probably opens around $0.15-$0.25 on CLOB")
print(f"")
print(f"    {'Poly Price':>12} {'Shares for $100':>16} {'Basis Shares':>14} {'Basis Advantage':>16}")
print(f"    {'-'*62}")

for poly_price in [0.05, 0.10, 0.15, 0.20, 0.244, 0.30]:
    poly_shares = 100 / poly_price
    advantage = shares / poly_shares
    print(f"    ${poly_price:>10.3f} {poly_shares:>15,.0f} {shares:>13,.0f} {advantage:>15.1f}x")

# What if Newsom wins? Payout comparison for this first $100 buyer
# Need to estimate eventual total pool. Use the sim data we have.
# At scale with $12.5M total pool and 12.55M Newsom shares:
# Payout per share ≈ $1.00
# But with 128 outcomes there'd be more losers...

print(f"\n\n{'='*80}")
print(f"  IF NEWSOM WINS — What does this first $100 buy return?")
print(f"{'='*80}")

# Basis: shares × payout_per_share
# payout_per_share = total_pool / winner_shares
# At scale, winner holds ~25% of shares, so payout ≈ total/winner ≈ 4x per share
# But more precisely: payout/share ≈ $1.00 at convergence (all shares ≈ equal count)
# Actually let's think about this properly.
# In equilibrium each outcome has roughly the same NUMBER of shares (bonding curve property)
# but the cost per share varies (favorites cost more per share)
# So payout per share ≈ total_cost_all / shares_of_winner

# For this first buyer specifically:
# They bought shares at $0.0079 each
# At resolution, payout per share will be ~$1.00 (as we saw in the full sim)
# Return = $1.00 / $0.0079 = 126.6x

print(f"\n  Basis first buyer:")
print(f"    Shares: {shares:,.0f}")
print(f"    Cost per share: ${eff_price:.6f}")
print(f"    If payout/share ≈ $1.00 (as shown in full sim): ${shares * 1.0:,.0f} payout")
print(f"    Return: {1.0 / eff_price:.0f}x on $100 = ${100 * (1.0/eff_price):,.0f}")

print(f"\n  Polymarket first buyer (at various entry prices):")
print(f"    {'Entry Price':>12} {'Shares':>10} {'Payout ($1/sh)':>15} {'Return':>8}")
print(f"    {'-'*48}")
for poly_price in [0.05, 0.10, 0.15, 0.20, 0.244]:
    poly_shares = 100 / poly_price
    print(f"    ${poly_price:>10.3f} {poly_shares:>9,.0f} ${poly_shares:>13,.0f} {1/poly_price:>7.1f}x")

# Cumulative: how much can you buy before reaching Polymarket's price?
print(f"\n\n{'='*80}")
print(f"  HOW MUCH CAN YOU BUY BEFORE REACHING POLYMARKET PRICE?")
print(f"{'='*80}")

poly_targets = [0.05, 0.10, 0.15, 0.20, 0.244]
for target in poly_targets:
    # Simulate buying until probability reaches target
    res = float(per)
    tot = float(seed)
    total_spent = 0.0
    total_shares = 0.0
    step = 10  # $10 increments
    
    while True:
        net_s = step * (1 - TAX)
        nv = res + net_s
        nt = tot + net_s
        prob = nv / nt
        if prob >= target:
            break
        s = (net_s * nt) / nv
        prob_bp = (nv * 10000) / nt
        if prob_bp > 9500:
            rem = 10000 - prob_bp
            s = (s * rem * rem) / 250000
        res = nv
        tot = nt
        total_spent += step
        total_shares += s
        
        if total_spent > 50000000:  # safety
            break
    
    avg_price = total_spent / total_shares if total_shares > 0 else 0
    print(f"  To reach {target:.1%} (Poly ${target:.3f}): ${total_spent:>12,.0f} total buy | {total_shares:>12,.0f} shares | avg ${avg_price:.4f}/share")
