"""
Whale protection analysis: How much can a whale buy before getting punished by slippage?
And how quickly does organic volume make the whale's early advantage irrelevant?
"""
import json

TAX = 0.015


def buy_and_report(n_outcomes, seed_total, buy_amount):
    """Single whale buy on outcome 0 from a fresh market. Return prob and effective price."""
    per = seed_total / n_outcomes
    reserves = [float(per)] * n_outcomes
    total = float(seed_total)
    
    init_prob = per / total
    
    # Execute buy
    net = buy_amount * (1 - TAX)
    new_v = reserves[0] + net
    new_t = total + net
    shares = (net * new_t) / new_v
    
    # Slippage check
    prob_bp = (new_v * 10000) / new_t
    slipped = False
    if prob_bp > 9500:
        rem = 10000 - prob_bp
        original_shares = shares
        shares = (shares * rem * rem) / 250000
        slipped = True
    
    new_prob = new_v / new_t
    # Effective price per share = amount paid / shares received
    eff_price = buy_amount / shares if shares > 0 else 999
    
    return {
        "init_prob": init_prob,
        "new_prob": new_prob,
        "shares": shares,
        "eff_price": eff_price,
        "slipped": slipped,
        "prob_bp": prob_bp,
    }


print(f"\n{'#'*120}")
print(f"  WHALE PROTECTION ANALYSIS")
print(f"  How much slippage does a whale face at different seed levels?")
print(f"{'#'*120}")

# Test different market sizes and seed formulas
configs = [
    (2, "$1K min", 1000),
    (5, "$1K min", 1000),
    (10, "$100x10", 1000),
    (20, "$100x20", 2000),
    (44, "$100x44", 4400),
]

whale_buys = [100, 500, 1000, 5000, 10000, 50000, 100000]

for n_outcomes, label, seed in configs:
    per = seed / n_outcomes
    print(f"\n{'='*120}")
    print(f"  {n_outcomes} outcomes | Seed: ${seed:,} ({label}) | ${per:,.0f}/outcome | Init prob: {1/n_outcomes:.1%}")
    print(f"{'='*120}")
    print(f"  {'Whale Buy':>12} {'New Prob':>9} {'Abs Move':>9} {'Rel Move':>9} {'Eff $/share':>12} {'Slippage?':>10} {'Shares':>12}")
    print(f"  {'-'*78}")
    
    for wb in whale_buys:
        r = buy_and_report(n_outcomes, seed, wb)
        abs_move = r["new_prob"] - r["init_prob"]
        rel_move = abs_move / r["init_prob"]
        slip_label = f"YES @{r['prob_bp']/100:.0f}%" if r["slipped"] else "no"
        print(f"  ${wb:>10,} {r['new_prob']:>8.1%} {abs_move:>+8.1%} {rel_move:>+8.0%} ${r['eff_price']:>10.4f} {slip_label:>10} {r['shares']:>11,.0f}")


# Now show how quickly organic volume dilutes the whale
print(f"\n\n{'#'*120}")
print(f"  WHALE DILUTION: How fast does organic volume erase the whale's advantage?")
print(f"{'#'*120}")

for n_outcomes, label, seed in [(10, "$100x10", 1000), (44, "$100x44", 4400)]:
    per = seed / n_outcomes
    
    # Whale buys $10K on outcome 0 immediately
    whale_buy = 10000
    
    print(f"\n{'='*100}")
    print(f"  {n_outcomes} outcomes | Seed ${seed:,} | Whale buys ${whale_buy:,} on outcome 0 at launch")
    print(f"{'='*100}")
    
    # After whale buy
    reserves = [float(per)] * n_outcomes
    total = float(seed)
    
    net_w = whale_buy * (1 - TAX)
    reserves[0] += net_w
    total += net_w
    
    whale_prob = reserves[0] / total
    whale_shares_pre = (net_w * (per + net_w + seed - per)) / (per + net_w)  # approximate
    
    print(f"  After whale: outcome 0 at {whale_prob:.1%} (from {1/n_outcomes:.1%})")
    
    # Now simulate organic volume flowing in evenly across all outcomes
    # and also proportionally (frontrunner gets more)
    print(f"\n  {'Organic Vol':>14} {'Even: #0 prob':>14} {'Proportional: #0 prob':>22} {'Whale share of pool':>20}")
    print(f"  {'-'*74}")
    
    organic_levels = [1000, 5000, 10000, 25000, 50000, 100000, 500000]
    
    for org_vol in organic_levels:
        # Scenario 1: even distribution
        res_even = [float(r) for r in reserves]
        tot_even = float(total)
        per_outcome_org = org_vol / n_outcomes
        for i in range(n_outcomes):
            net = per_outcome_org * (1 - TAX)
            res_even[i] += net
            tot_even += net
        prob_even = res_even[0] / tot_even
        
        # Scenario 2: proportional (frontrunner gets 30%, rest split)
        res_prop = [float(r) for r in reserves]
        tot_prop = float(total)
        front_share = org_vol * 0.30
        rest_share = (org_vol * 0.70) / (n_outcomes - 1)
        net_f = front_share * (1 - TAX)
        res_prop[0] += net_f
        tot_prop += net_f
        for i in range(1, n_outcomes):
            net_r = rest_share * (1 - TAX)
            res_prop[i] += net_r
            tot_prop += net_r
        prob_prop = res_prop[0] / tot_prop
        
        # Whale's share of total pool
        total_pool_even = sum(r - per for r in res_even)  # net of seed
        whale_pct = (net_w / total_pool_even * 100) if total_pool_even > 0 else 100
        
        print(f"  ${org_vol:>12,} {prob_even:>13.1%} {prob_prop:>21.1%} {whale_pct:>19.1f}%")


# Final recommendation
print(f"""

{'='*120}
  RECOMMENDATION: Seed Formula
{'='*120}

  seed = max(MINIMUM, $100 x numOutcomes)

  Minimum thresholds to explore:

  {'Minimum':>10} {'2-out $100 bet':>16} {'2-out $1K bet':>15} {'2-out $10K bet':>16} {'Whale $50K on 2-out':>22}
  {'-'*82}""")

for minimum in [500, 1000, 2500, 5000, 10000]:
    r100 = buy_and_report(2, minimum, 100)
    r1k = buy_and_report(2, minimum, 1000)
    r10k = buy_and_report(2, minimum, 10000)
    r50k = buy_and_report(2, minimum, 50000)
    print(f"  ${minimum:>8,} {r100['new_prob']-0.5:>+15.1%} {r1k['new_prob']-0.5:>+14.1%} {r10k['new_prob']-0.5:>+15.1%} {r50k['new_prob']-0.5:>+21.1%}")

print(f"""
  Reading: How much does a single bet move probability from 50% on a 2-outcome market.

  Key tradeoff:
    Low minimum ($500-1K)  → Responsive but whale-vulnerable early
    High minimum ($5K-10K) → Stable but slow to reflect real sentiment in small markets
    
  The whale protection comes from the BONDING CURVE ITSELF:
    Each additional dollar buys fewer shares as probability rises.
    At 95%+, the slippage penalty crushes share output exponentially.
    A whale can't corner an outcome to 99% without paying astronomical prices.
    
  The seed just controls how much the FIRST bet matters.
  After 10-20x the seed in volume, it's irrelevant.
""")
