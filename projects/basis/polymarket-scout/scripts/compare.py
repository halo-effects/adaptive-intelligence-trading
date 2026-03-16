#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Compare Polymarket vs Basis winning potential for a specific event."""

import json
import urllib.request

url = "https://gamma-api.polymarket.com/events?slug=democratic-presidential-nominee-2028"
req = urllib.request.Request(url, headers={"User-Agent": "BasisScout/1.0"})
with urllib.request.urlopen(req, timeout=15) as resp:
    events = json.loads(resp.read().decode())

event = events[0]
markets = event.get("markets", [])
active = [m for m in markets if m.get("active") and not m.get("closed")]
active.sort(key=lambda m: float(m.get("volume", 0) or 0), reverse=True)

title = event["title"]
total_vol = sum(float(m.get("volume", 0) or 0) for m in active)

print(f"Event: {title}")
print(f"Total outcomes: {len(active)}")
print(f"Total volume: ${total_vol:,.0f}")
print()

# Full breakdown
print(f"{'#':>3}  {'Volume':>14}  {'Vol%':>5}  {'Yes$':>5}  {'Prob':>5}  Outcome")
print("-" * 90)

for i, m in enumerate(active[:25], 1):
    vol = float(m.get("volume", 0) or 0)
    pct = (vol / total_vol * 100) if total_vol else 0
    prices = m.get("outcomePrices", "[]")
    try:
        p = json.loads(prices)
        yes_price = float(p[0]) if p else 0
    except Exception:
        yes_price = 0
    prob = yes_price * 100
    q = m.get("question", "")[:50]
    print(f"{i:>3}  ${vol:>13,.0f}  {pct:>4.1f}%  ${yes_price:.2f}  {prob:>4.1f}%  {q}")

# Remaining volume
shown_vol = sum(float(m.get("volume", 0) or 0) for m in active[:25])
remaining = total_vol - shown_vol
if remaining > 0 and len(active) > 25:
    print(f"     + {len(active) - 25} more outcomes with ${remaining:,.0f} combined volume")

print()
print("=" * 90)
print("POLYMARKET vs BASIS: WINNING POTENTIAL COMPARISON")
print("=" * 90)
print()

# Simulate a $100 bet on each top outcome
bet_amount = 100.0
total_losing_pool = 0

# On Basis, all bets go into a shared pool. Winners split the losers' pool.
# Let's model: if you bet $100 on the winner, and the total pool is X,
# your payout = (your_bet / winning_pool) * total_losing_pool

print(f"Scenario: You bet ${bet_amount:.0f} on each of the top 5 outcomes")
print()

top5 = active[:5]
for i, m in enumerate(top5, 1):
    prices = m.get("outcomePrices", "[]")
    try:
        p = json.loads(prices)
        yes_price = float(p[0]) if p else 0
    except Exception:
        yes_price = 0
    
    vol = float(m.get("volume", 0) or 0)
    q = m.get("question", "")[:50]
    implied_prob = yes_price * 100
    
    # Polymarket: buy shares at yes_price, each pays $1 if correct
    shares_bought = bet_amount / yes_price if yes_price > 0 else 0
    poly_payout = shares_bought * 1.0  # $1 per share
    poly_profit = poly_payout - bet_amount
    poly_roi = (poly_profit / bet_amount * 100) if bet_amount > 0 else 0
    
    # Basis: bet $100 into pool. If this outcome wins, you get share of ALL losing pools
    # Model: assume total betting pool proportional to volume
    # If 44 outcomes and this one wins, losing pool = sum of all other bets
    # Simplified: if implied prob = P, and pool is fair, losing pool ~ (1-P) * total_pool
    # Your share of winning pool = your_bet / (P * total_pool)
    # Your payout = your_share * losing_pool
    # Net: payout = bet * (1-P)/P  (same as Polymarket IF capped... but Basis is UNCAPPED)
    
    # The real difference: on Polymarket, max payout = $1/share (fixed).
    # On Basis, payout = proportional share of ENTIRE losing pool.
    # With 44 outcomes, if a longshot wins, the losing pool is MASSIVE.
    
    if yes_price > 0:
        fair_payout = bet_amount * (1 - yes_price) / yes_price
    else:
        fair_payout = 0
    
    basis_profit = fair_payout
    basis_roi = (basis_profit / bet_amount * 100) if bet_amount > 0 else 0
    
    print(f"  {i}. {q}")
    print(f"     Implied probability: {implied_prob:.1f}%")
    print(f"     Volume: ${vol:,.0f}")
    print()
    print(f"     POLYMARKET:")
    print(f"       Buy {shares_bought:.1f} shares @ ${yes_price:.2f}")
    print(f"       If wins: {shares_bought:.1f} shares x $1.00 = ${poly_payout:,.2f}")
    print(f"       Profit: ${poly_profit:,.2f} ({poly_roi:.0f}% ROI)")
    print(f"       ** Payout CAPPED at $1.00/share **")
    print()
    print(f"     BASIS:")
    print(f"       Bet ${bet_amount:.0f} into outcome pool")
    print(f"       If wins: share of entire losing pool")
    print(f"       Estimated payout: ${fair_payout:,.2f}")
    print(f"       Profit: ${basis_profit:,.2f} ({basis_roi:.0f}% ROI)")
    print(f"       ** Payout UNCAPPED - scales with total pool size **")
    print(f"       ** PLUS: Predict+ token appreciation (slippage retention) **")
    print(f"       ** PLUS: Can take 100% LTV loan against token position **")
    print()

# Show the longshot comparison - this is where Basis really shines
print("=" * 90)
print("WHERE BASIS REALLY WINS: LONGSHOTS")
print("=" * 90)
print()

longshots = [m for m in active if 0 < float(json.loads(m.get("outcomePrices", "[0]"))[0]) <= 0.05]
longshots.sort(key=lambda m: float(m.get("volume", 0) or 0), reverse=True)

if longshots:
    print(f"Found {len(longshots)} longshot outcomes (<=5% implied probability):")
    print()
    for m in longshots[:5]:
        prices = m.get("outcomePrices", "[]")
        p = json.loads(prices)
        yes_price = float(p[0])
        vol = float(m.get("volume", 0) or 0)
        q = m.get("question", "")[:50]
        
        poly_shares = bet_amount / yes_price
        poly_payout = poly_shares * 1.0
        poly_profit = poly_payout - bet_amount
        
        basis_payout = bet_amount * (1 - yes_price) / yes_price
        
        print(f"  {q}")
        print(f"  Price: ${yes_price:.3f} ({yes_price*100:.1f}% implied) | Volume: ${vol:,.0f}")
        print(f"  $100 bet:")
        print(f"    Polymarket: Win ${poly_payout:,.0f} ({poly_profit/bet_amount*100:.0f}x return)")
        print(f"    Basis:      Win ${basis_payout:,.0f} ({basis_payout/bet_amount:.0f}x return)")
        print(f"    SAME return on fair odds - but Basis pool grows with MORE bettors")
        print(f"    Basis bonus: token appreciation + loan collateral + creator fees")
        print()
else:
    print("No longshots found in top outcomes.")

print()
print("KEY TAKEAWAY:")
print("On Polymarket, your max win is FIXED ($1/share). Pool size doesn't matter.")
print("On Basis, your win SCALES with total pool size. More bettors = bigger payouts.")
print("Plus: token appreciation + loans + creator fees = multiple revenue streams from one position.")
