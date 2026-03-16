import json, urllib.request

url = "https://gamma-api.polymarket.com/events?slug=democratic-presidential-nominee-2028"
req = urllib.request.Request(url, headers={"User-Agent": "B/1"})
resp = urllib.request.urlopen(req, timeout=15)
events = json.loads(resp.read().decode())
markets = events[0].get("markets", [])
active = [m for m in markets if m.get("active") and not m.get("closed")]

def info(m):
    p = float(json.loads(m.get("outcomePrices", "[0]"))[0])
    v = float(m.get("volume", 0) or 0)
    l = float(m.get("liquidity", 0) or 0)
    return p, v, l

active.sort(key=lambda m: info(m)[0], reverse=True)

total_vol = sum(info(m)[1] for m in active)
total_liq = sum(info(m)[2] for m in active)
my_bet = 100

print("DEMOCRATIC PRESIDENTIAL NOMINEE 2028")
print(f"Total outcomes: {len(active)}")
print(f"Total volume: {total_vol:,.0f} USD")
print(f"Total liquidity: {total_liq:,.0f} USD")
print()
print("TOP 5 BY PROBABILITY - EXACT PAYOUT MATH")
print("=" * 90)

for i, m in enumerate(active[:5], 1):
    p, v, l = info(m)
    q = m.get("question", "")[:55]
    losing_pool = total_vol - v
    
    # Basis: your share of winning pool * losing pool
    # your_share = my_bet / winning_pool_size
    # payout = your_share * losing_pool
    basis_payout = (my_bet / v) * losing_pool if v > 0 else 0
    basis_profit = basis_payout - my_bet
    basis_roi = basis_profit / my_bet * 100
    
    # Polymarket: buy shares at price p, each pays $1
    poly_shares = my_bet / p if p > 0 else 0
    poly_payout = poly_shares * 1.0
    poly_profit = poly_payout - my_bet
    poly_roi = poly_profit / my_bet * 100
    
    diff = basis_payout - poly_payout
    
    print(f"\n{i}. {q}")
    print(f"   Implied probability: {p*100:.1f}%")
    print(f"   Winning pool (Newsom bettors): {v:,.0f} USD")
    print(f"   Losing pool (all 43 others):   {losing_pool:,.0f} USD")
    print(f"   Your bet: 100 USD")
    print(f"   Your share of winning pool: {my_bet/v*100:.6f}%")
    print()
    print(f"   POLYMARKET:  100 USD -> buy {poly_shares:.1f} shares @ {p:.3f}")
    print(f"                Payout: {poly_payout:,.0f} USD  |  Profit: {poly_profit:,.0f} USD  |  ROI: {poly_roi:,.0f}%")
    print(f"                ** CAPPED at 1.00 per share **")
    print()
    print(f"   BASIS:       100 USD -> bet into {q[:20]}... pool")
    print(f"                Payout: {basis_payout:,.0f} USD  |  Profit: {basis_profit:,.0f} USD  |  ROI: {basis_roi:,.0f}%")
    print(f"                ** UNCAPPED - proportional share of entire losing pool **")
    print()
    print(f"   DIFFERENCE:  Basis pays {diff:+,.0f} USD more ({diff/poly_payout*100:+.1f}%)")
    print(f"                + token appreciation + loan collateral + creator fees")
