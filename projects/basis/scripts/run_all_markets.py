"""
Run all 5 Polymarket markets through the Basis bonding curve.
Focus: Does the frontrunner get identified? What are the payout multipliers?
$50K total pool, probability-weighted YES volume.
"""
import json
import urllib.request
import sys
import time

TAX = 0.015

MARKETS = [
    ("presidential-election-winner-2028", "Presidential Election Winner 2028"),
    ("2026-fifa-world-cup-winner", "2026 FIFA World Cup Winner"),
    ("2026-nba-champion", "2026 NBA Champion"),
    ("the-masters-winner", "The Masters - Golf Winner"),
]


def fetch_market(slug):
    url = f"https://gamma-api.polymarket.com/events?slug={slug}"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    data = json.loads(urllib.request.urlopen(req, timeout=15).read())
    if not data:
        return None, []
    event = data[0]
    outcomes = []
    for m in event.get("markets", []):
        vol = float(m.get("volume", "0") or "0")
        prices = m.get("outcomePrices", "")
        try:
            price_list = json.loads(prices) if prices else []
            yes_price = float(price_list[0]) if price_list else 0
        except:
            yes_price = 0
        title = m.get("groupItemTitle") or m.get("question", "")[:50]
        if vol > 0 and yes_price > 0:
            outcomes.append({
                "title": title,
                "volume": vol,
                "probability": yes_price,
                "yes_capital": vol * yes_price,
            })
    outcomes.sort(key=lambda x: x["yes_capital"], reverse=True)
    return event["title"], outcomes


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
    pool = sum(costs)
    return probs, costs, circ, vols, pool


def run_market(slug, label, total_pool=50000):
    title, outcomes = fetch_market(slug)
    if not outcomes:
        print(f"\n  SKIPPED: {label} (no data)")
        return None

    n = len(outcomes)
    total_vol = sum(o["volume"] for o in outcomes)
    total_yes = sum(o["yes_capital"] for o in outcomes)

    probs, costs, circ, vols, pool = sim(outcomes, total_pool)

    # Sort by Polymarket probability for display
    indexed = list(enumerate(outcomes))
    indexed.sort(key=lambda x: x[1]["probability"], reverse=True)

    print(f"\n{'='*120}")
    print(f"  {title}")
    print(f"  Outcomes: {n} | Raw volume: ${total_vol:,.0f} | YES capital: ${total_yes:,.0f} | Pool: ${total_pool:,.0f}")
    print(f"{'='*120}")

    top_n = min(15, n)
    print(f"\n{'#':<3} {'Outcome':<35} {'Poly':>6} {'Basis':>7} {'Delta':>7} {'Poly Pay':>9} {'Basis Pay':>10}")
    print("-" * 82)

    for rank, (i, o) in enumerate(indexed[:top_n], 1):
        bp = probs[i]
        pp = o["probability"]
        delta = bp - pp
        poly_pay = 1.0 / pp if pp > 0 else 0
        if circ[i] > 0 and vols[i] > 0:
            avg_share = circ[i] / vols[i]
            basis_pay = (pool / circ[i]) * avg_share
        else:
            basis_pay = 0
        print(f"{rank:<3} {o['title']:<35} {pp:>5.1%} {bp:>6.2%} {delta:>+6.1%} ${poly_pay:>7.2f} ${basis_pay:>8.2f}")

    # Frontrunner check
    poly_front = indexed[0][1]
    basis_front_idx = max(range(n), key=lambda i: probs[i])
    basis_front = outcomes[basis_front_idx]

    match = "YES" if poly_front["title"] == basis_front["title"] else "NO"
    print(f"\n  Frontrunner match: {match}")
    print(f"    Polymarket #1: {poly_front['title']} ({poly_front['probability']:.1%})")
    print(f"    Basis #1:      {basis_front['title']} ({probs[basis_front_idx]:.2%})")

    # Top 3 match
    poly_top3 = set(indexed[j][1]["title"] for j in range(min(3, n)))
    basis_top3_idx = sorted(range(n), key=lambda i: probs[i], reverse=True)[:3]
    basis_top3 = set(outcomes[j]["title"] for j in basis_top3_idx)
    overlap = len(poly_top3 & basis_top3)
    print(f"  Top 3 overlap: {overlap}/3")

    # Payout advantage
    if indexed[0][1]["probability"] > 0:
        i0 = indexed[0][0]
        if circ[i0] > 0 and vols[i0] > 0:
            avg_s = circ[i0] / vols[i0]
            bp_front = (pool / circ[i0]) * avg_s
            pp_front = 1.0 / indexed[0][1]["probability"]
            print(f"  Payout advantage (frontrunner): {bp_front/pp_front:.1f}x Polymarket")

    return {
        "title": title,
        "n": n,
        "frontrunner_match": match,
        "top3_overlap": overlap,
    }


# Run Democratic Nominee from cached data (already fetched)
print(f"\n{'#'*120}")
print(f"  RUNNING ALL 5 POLYMARKET MARKETS THROUGH BASIS BONDING CURVE")
print(f"  Pool: $50K total | Method: YES conviction (volume x probability)")
print(f"{'#'*120}")

# Market 1: Democratic Nominee (from cached file)
with open("polymarket_democratic_presidential_nominee_2028_outcomes.json") as f:
    dem_data = json.load(f)

dem_outcomes = []
for o in dem_data["outcomes"]:
    if o["volume"] > 0 and o["probability"] > 0:
        dem_outcomes.append({
            "title": o["title"],
            "volume": o["volume"],
            "probability": o["probability"],
            "yes_capital": o["volume"] * o["probability"],
        })
dem_outcomes.sort(key=lambda x: x["yes_capital"], reverse=True)

n = len(dem_outcomes)
total_vol = sum(o["volume"] for o in dem_outcomes)
total_yes = sum(o["yes_capital"] for o in dem_outcomes)
probs, costs, circ, vols, pool = sim(dem_outcomes, 50000)

indexed = list(enumerate(dem_outcomes))
indexed.sort(key=lambda x: x[1]["probability"], reverse=True)

print(f"\n{'='*120}")
print(f"  Democratic Presidential Nominee 2028")
print(f"  Outcomes: {n} | Raw volume: ${total_vol:,.0f} | YES capital: ${total_yes:,.0f} | Pool: $50,000")
print(f"{'='*120}")

top_n = min(15, n)
print(f"\n{'#':<3} {'Outcome':<35} {'Poly':>6} {'Basis':>7} {'Delta':>7} {'Poly Pay':>9} {'Basis Pay':>10}")
print("-" * 82)

for rank, (i, o) in enumerate(indexed[:top_n], 1):
    bp = probs[i]
    pp = o["probability"]
    delta = bp - pp
    poly_pay = 1.0 / pp if pp > 0 else 0
    if circ[i] > 0:
        avg_share = circ[i] / (o["yes_capital"] if o["yes_capital"] > 0 else 1)
        basis_pay = (pool / circ[i]) * avg_share
    else:
        basis_pay = 0
    print(f"{rank:<3} {o['title']:<35} {pp:>5.1%} {bp:>6.2%} {delta:>+6.1%} ${poly_pay:>7.2f} ${basis_pay:>8.2f}")

poly_front = indexed[0][1]
basis_front_idx = max(range(n), key=lambda i: probs[i])
basis_front = dem_outcomes[basis_front_idx]
print(f"\n  Frontrunner match: {'YES' if poly_front['title'] == basis_front['title'] else 'NO'}")
print(f"    Polymarket #1: {poly_front['title']} ({poly_front['probability']:.1%})")
print(f"    Basis #1:      {basis_front['title']} ({probs[basis_front_idx]:.2%})")

# Markets 2-5
results = [{"title": "Democratic Presidential Nominee 2028", "n": n, "frontrunner_match": "YES" if poly_front["title"] == basis_front["title"] else "NO"}]

for slug, label in MARKETS:
    time.sleep(1)  # rate limit
    r = run_market(slug, label)
    if r:
        results.append(r)

# Final summary
print(f"\n\n{'='*80}")
print(f"  FINAL SUMMARY: All Markets")
print(f"{'='*80}")
print(f"\n  {'Market':<45} {'N':>4} {'Front?':>7} {'Top3':>6}")
print(f"  {'-'*65}")
for r in results:
    t3 = f"{r.get('top3_overlap','?')}/3" if 'top3_overlap' in r else "N/A"
    print(f"  {r['title']:<45} {r['n']:>4} {r['frontrunner_match']:>7} {t3:>6}")




