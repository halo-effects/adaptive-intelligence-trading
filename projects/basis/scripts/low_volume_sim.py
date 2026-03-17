"""
Low volume simulation: Scale down real Polymarket markets to <$1M total volume.
Keep the same outcome distribution but reduce volume to see how $50K seed behaves.
"""
import json

TAX = 0.015
POOL = 50000


def sim(outcomes, total_pool):
    n = len(outcomes)
    per = total_pool / n
    reserves = [float(per)] * n
    total = float(total_pool)
    costs = [0.0] * n
    circ = [0.0] * n
    vols = [0.0] * n
    rounds = 500
    for _ in range(rounds):
        for i, o in enumerate(outcomes):
            chunk = o["yes_capital"] / rounds
            if chunk > 0:
                net = chunk * (1 - TAX)
                new_v = reserves[i] + net
                new_t = total + net
                shares = (net * new_t) / new_v
                prob_bp = (new_v * 10000) / new_t
                if prob_bp > 9500:
                    rem = 10000 - prob_bp
                    shares = (shares * rem * rem) / 250000
                reserves[i] = new_v
                total = new_t
                costs[i] += net
                circ[i] += shares
                vols[i] += chunk
    probs = [reserves[i] / total for i in range(n)]
    pool_total = sum(costs)
    return probs, costs, circ, vols, pool_total


def scale_outcomes(outcomes, target_total_yes):
    """Scale YES capital to target total while preserving distribution."""
    current_total = sum(o["yes_capital"] for o in outcomes)
    if current_total == 0:
        return outcomes
    scale = target_total_yes / current_total
    scaled = []
    for o in outcomes:
        scaled.append({
            "title": o["title"],
            "probability": o["probability"],
            "yes_capital": o["yes_capital"] * scale,
            "original_yes": o["yes_capital"],
        })
    return scaled


def run_market(title, outcomes, target_volumes):
    n = len(outcomes)
    original_yes = sum(o["yes_capital"] for o in outcomes)

    # Sort by probability for display
    by_prob = sorted(range(n), key=lambda i: outcomes[i]["probability"], reverse=True)
    top10 = by_prob[:min(10, n)]

    print(f"\n{'='*130}")
    print(f"  {title} ({n} outcomes)")
    print(f"  Original YES capital: ${original_yes:,.0f} | Seed: ${POOL:,.0f}")
    print(f"{'='*130}")

    # Header
    header = f"{'#':<3} {'Outcome':<30} {'Poly':>6}"
    for tv in target_volumes:
        header += f" {'$'+format(tv,',')+' YES':>12}"
    print(header)
    print("-" * (42 + 13 * len(target_volumes)))

    all_probs = {}
    for tv in target_volumes:
        scaled = scale_outcomes(outcomes, tv)
        probs, _, _, _, _ = sim(scaled, POOL)
        all_probs[tv] = probs

    for rank, i in enumerate(top10, 1):
        o = outcomes[i]
        line = f"{rank:<3} {o['title']:<30} {o['probability']:>5.1%}"
        for tv in target_volumes:
            line += f" {all_probs[tv][i]:>11.2%}"
        print(line)

    # Frontrunner analysis
    print(f"\n  {'Volume':>12} {'Seed/YES':>10} {'#1 Match?':>10} {'#1 Basis Prob':>14} {'#1 Poly Prob':>13} {'Delta':>8}")
    print(f"  {'-'*70}")

    poly_front_i = by_prob[0]
    for tv in target_volumes:
        basis_front_i = max(range(n), key=lambda i: all_probs[tv][i])
        match = "YES" if basis_front_i == poly_front_i else "NO"
        bp = all_probs[tv][poly_front_i]
        pp = outcomes[poly_front_i]["probability"]
        ratio = POOL / tv if tv > 0 else 999
        print(f"  ${tv:>10,} {ratio:>9.1f}x {match:>10} {bp:>13.2%} {pp:>12.1%} {bp-pp:>+7.1%}")


# Load markets
print(f"\n{'#'*130}")
print(f"  LOW VOLUME SIMULATION: How does $50K seed behave with small markets?")
print(f"  Scaling real Polymarket distributions down to $10K - $1M YES capital")
print(f"{'#'*130}")

# Target YES capital levels (these are YES conviction, not raw volume)
targets = [10_000, 25_000, 50_000, 100_000, 250_000, 500_000, 1_000_000]

# Market 1: Democratic Nominee (44 outcomes)
with open("polymarket_democratic_presidential_nominee_2028_outcomes.json") as f:
    dem_data = json.load(f)
dem = []
for o in dem_data["outcomes"]:
    if o["volume"] > 0 and o["probability"] > 0:
        dem.append({"title": o["title"], "probability": o["probability"],
                    "yes_capital": o["volume"] * o["probability"]})
dem.sort(key=lambda x: x["probability"], reverse=True)
run_market("Democratic Presidential Nominee 2028 (44 outcomes)", dem, targets)

# Market 2: Presidential Election (35 outcomes) - fetch
import urllib.request, time

def fetch(slug):
    url = f"https://gamma-api.polymarket.com/events?slug={slug}"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    data = json.loads(urllib.request.urlopen(req, timeout=15).read())
    if not data:
        return []
    outcomes = []
    for m in data[0].get("markets", []):
        vol = float(m.get("volume", "0") or "0")
        prices = m.get("outcomePrices", "")
        try:
            pl = json.loads(prices) if prices else []
            yp = float(pl[0]) if pl else 0
        except:
            yp = 0
        title = m.get("groupItemTitle") or m.get("question", "")[:40]
        if vol > 0 and yp > 0:
            outcomes.append({"title": title, "probability": yp, "yes_capital": vol * yp})
    return outcomes

pres = fetch("presidential-election-winner-2028")
if pres:
    pres.sort(key=lambda x: x["probability"], reverse=True)
    run_market("Presidential Election Winner 2028 (35 outcomes)", pres, targets)

time.sleep(1)
nba = fetch("2026-nba-champion")
if nba:
    nba.sort(key=lambda x: x["probability"], reverse=True)
    run_market("2026 NBA Champion (26 outcomes)", nba, targets)

# Summary insight
print(f"""

{'='*130}
  KEY INSIGHT: When does $50K seed start to matter?
{'='*130}

  The seed-to-volume ratio determines how much the initial equal-probability 
  assumption distorts the final odds:
  
  Ratio (Seed/YES)    Effect
  -------------------------
  > 5x                Seed dominates. All outcomes near equal. Unusable.
  1x - 5x            Seed pulls frontrunner toward mean. Noticeable distortion.
  0.1x - 1x          Transition zone. Frontrunner emerges but with dampened odds.
  < 0.1x             Volume dominates. Seed is irrelevant. Probabilities accurate.
  
  For $50K seed:
    $10K YES capital  → ratio 5.0x → seed dominates, frontrunner barely visible
    $50K YES capital  → ratio 1.0x → frontrunner visible but dampened
    $500K YES capital → ratio 0.1x → probabilities close to true odds
    $1M+ YES capital  → ratio <0.05x → seed is noise
    
  RECOMMENDATION: $50K seed is appropriate for markets expecting >$500K in 
  YES conviction capital. For smaller markets, reduce the seed proportionally.
  Rule of thumb: seed should be <10% of expected YES volume.
""")
