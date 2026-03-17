"""
Deep differential analysis at $50K starting liquidity.
Show exactly where and why Basis diverges from Polymarket.
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
RESERVE = 50000
total_yes = sum(o["yes_cap"] for o in outcomes)


def sim(init_r):
    res = [float(init_r)] * n
    total = float(init_r * n)
    rounds = 1000
    costs = [0.0] * n
    circ = [0.0] * n
    vol = [0.0] * n
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
                vol[i] += chunk
    probs = [r / total for r in res]
    return probs, costs, circ, vol, total


probs, costs, circ, vol, total_res = sim(RESERVE)

pool = sum(costs)
init_pool = RESERVE * n

print(f"\n{'='*130}")
print(f"  DEEP DIFFERENTIAL: $50K/outcome | {n} outcomes | Init pool: ${init_pool:,.0f} | YES capital: ${total_yes:,.0f}")
print(f"  Init pool is {init_pool/total_yes:.1%} of YES capital -- this is the 'dilution factor'")
print(f"{'='*130}")

print(f"\n{'#':<3} {'Outcome':<28} {'Poly':>6} {'Basis':>7} {'Delta':>7} {'YES Cap':>11} {'YES%':>6} {'Init%':>6} {'Diluted?':>9}")
print("-" * 115)

# Calculate what probability WOULD be with zero initial reserve (pure volume share)
for i, o in enumerate(outcomes):
    bp = probs[i]
    pp = o["prob"]
    delta = bp - pp
    yes_pct = o["yes_cap"] / total_yes * 100
    # Init reserve share = what the initial reserve contributes to this outcome's probability
    # Without init reserve, prob would be ~ yes_cap / total_yes
    pure_vol_prob = o["yes_cap"] / total_yes
    init_share = RESERVE / total_res * 100  # each outcome's init reserve as % of final total
    
    # Is this outcome diluted (init reserve pushes toward mean) or concentrated?
    if pp > 1/n:  # outcome should be ABOVE average
        diluted = "diluted" if bp < pure_vol_prob else ""
    else:
        diluted = "inflated" if bp > pure_vol_prob else ""
    
    print(f"{i+1:<3} {o['title']:<28} {pp:>5.1%} {bp:>6.2%} {delta:>+6.1%} ${o['yes_cap']:>9,.0f} {yes_pct:>5.1f}% {init_share:>5.1f}% {diluted:>9}")

print(f"\n\n{'='*130}")
print(f"  DECOMPOSITION: Where does each outcome's probability come from?")
print(f"{'='*130}")
print(f"\n  Each outcome's Basis probability = (initial_reserve + YES_capital_net) / total_reserve")
print(f"  The initial reserve acts as a 'gravity pull' toward {1/n:.2%} (equal probability)")
print(f"  This effect is stronger when YES capital is small relative to initial reserves")

print(f"\n  Init pool: ${init_pool:,.0f} | YES pool (net): ${pool:,.0f} | Ratio: {init_pool/pool:.2f}x")
print(f"  At this ratio, ~{init_pool/(init_pool+pool)*100:.0f}% of each outcome's reserve comes from the SEED, not from bets")

print(f"\n{'#':<3} {'Outcome':<28} {'Poly':>6} {'Pure Vol':>9} {'Basis':>7} {'Seed Pull':>10} {'Accuracy':>10}")
print("-" * 90)

for i, o in enumerate(outcomes[:20]):
    bp = probs[i]
    pp = o["prob"]
    pure = o["yes_cap"] / total_yes
    seed_pull = bp - pure  # how much the seed moves probability vs pure volume
    accuracy = abs(bp - pp) - abs(pure - pp)  # negative = Basis is MORE accurate than pure vol
    
    acc_label = "better" if accuracy < -0.001 else ("worse" if accuracy > 0.001 else "same")
    
    print(f"{i+1:<3} {o['title']:<28} {pp:>5.1%} {pure:>8.2%} {bp:>6.2%} {seed_pull:>+9.2%} {acc_label:>10}")

print(f"""

{'='*130}
  KEY INSIGHT: The Proxy Problem
{'='*130}

  Our proxy (YES_capital = volume x probability) assumes:
    "The fraction of volume that represents genuine YES conviction 
     is proportional to the current probability."
     
  This works well for the FRONTRUNNER (Newsom: 24.4% prob, high YES fraction).
  But it breaks down for outcomes where:
  
  1. HIGH VOLUME + LOW PROBABILITY (Chelsea Clinton, LeBron, MrBeast):
     These have massive volume but tiny odds. Our proxy says only 0.9% of 
     their $43M is YES conviction ($387K). But in reality, some of that 
     volume is genuine YES bettors buying at $0.009/share for a potential 
     111:1 payout. The proxy UNDERWEIGHTS longshot YES conviction.
     
  2. LOW VOLUME + HIGH PROBABILITY (AOC, Shapiro, Ossoff):
     These have less raw volume but higher odds. Our proxy says 8.4% of 
     AOC's $5.75M is YES ($483K). But much of that volume might be 
     efficient market makers, not conviction. The proxy may OVERWEIGHT 
     mid-tier YES conviction relative to longshots.
     
  3. THE CLOB vs BONDING CURVE FUNDAMENTAL:
     On Polymarket's CLOB, price is set by the MARGINAL trader (bid/ask).
     On Basis's bonding curve, price is set by CUMULATIVE capital.
     A CLOB needs one smart trader to move the price.
     A bonding curve needs proportional capital to move the price.
     This means the bonding curve is structurally "slower" to differentiate.
     
  POSSIBLE SOLUTIONS:
  a) Accept the difference - Basis markets ARE different from Polymarket
  b) Use the P2P order book for price discovery, bonding curve for payouts
  c) Allow variable initial reserves per outcome (creator sets initial odds)
  d) Add a "sell" mechanism to the bonding curve (reduces reserve, lowers prob)
""")
