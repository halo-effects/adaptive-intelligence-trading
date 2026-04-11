"""
Analyze why 12 layers are unreachable with current formula,
and design a proper pre-calculated grid.
"""

print("=" * 80)
print("CURRENT FORMULA ANALYSIS")
print("Why 12 layers is unreachable")
print("=" * 80)

# Current: order = capital * BO_PCT * mult^min(layer, 4)
# Capital depletes after each buy (paper) or resets to alloc (live)

alloc = 20000
BO = 0.30
MULT = 1.5

print("\n--- Scenario A: Depleting capital (paper bot, no 30% cap) ---")
cap = alloc
for i in range(12):
    if i == 0:
        order = cap * BO
    else:
        order = cap * BO * (MULT ** min(i, 4))
    if order > cap:
        print(f"  L{i+1}: BLOCKED (wants ${order:,.0f}, only ${cap:,.0f} left)")
        print(f"  >> Grid stops at {i} layers")
        break
    if order < 10:
        print(f"  L{i+1}: TOO SMALL (${order:.2f})")
        break
    cap -= order
    print(f"  L{i+1}: ${order:>9,.2f} | remaining: ${cap:>9,.2f}")

print("\n--- Scenario B: GAP-13 reset (live bot) ---")
for i in range(12):
    if i == 0:
        order = alloc * BO
    else:
        order = alloc * BO * (MULT ** min(i, 4))
    if order > alloc:
        print(f"  L{i+1}: BLOCKED (wants ${order:,.0f} > alloc ${alloc:,.0f})")
        print(f"  >> Grid stops at {i} layers")
        break
    print(f"  L{i+1}: ${order:>9,.2f} ({order/alloc*100:.1f}% of alloc)")

print("\n--- Scenario C: 30% cap (old paper bot) ---")
cap = alloc
total = 0
for i in range(12):
    if i == 0:
        order = cap * BO
    else:
        order = cap * BO * (MULT ** min(i, 4))
    order = min(order, cap * 0.3)  # 30% cap
    if order < 10:
        print(f"  L{i+1}: TOO SMALL (${order:.2f})")
        break
    cap -= order
    total += order
    print(f"  L{i+1}: ${order:>9,.2f} | remaining: ${cap:>9,.2f}")
print(f"  Total deployed: ${total:,.2f} of ${alloc:,.0f}")

# ================================================================
print("\n" + "=" * 80)
print("SOLUTION: PRE-CALCULATED GRID")
print("Size all layers upfront to fit within allocation")
print("=" * 80)

# Pre-calculate: base_order * sum_of_multipliers = allocation
# L1 = base (mult^0 = 1)
# L2 = base * mult^1
# L3 = base * mult^2
# L4 = base * mult^3
# L5-L12 = base * mult^4 (capped at 4)
# Total = base * (1 + 1.5 + 2.25 + 3.375 + 8*5.0625)

mult_sum = 1.0  # L1
for i in range(1, 12):
    mult_sum += MULT ** min(i, 4)

base = alloc / mult_sum

print(f"\nMultiplier sum (12 layers, capped at ^4): {mult_sum:.4f}")
print(f"Base order: ${alloc:,.0f} / {mult_sum:.2f} = ${base:,.2f}")
print()

total = 0
for i in range(12):
    layer_mult = MULT ** min(i, 4)
    order = base * layer_mult
    total += order
    pool = "reserve" if i >= 5 else "active"
    print(f"  L{i+1:>2}: ${order:>9,.2f} (x{layer_mult:.4f}) [{pool}]")

print(f"\n  Total: ${total:,.2f} (should = ${alloc:,.0f})")
print(f"  L1 is {base/alloc*100:.1f}% of allocation")
print(f"  L5-L12 are each {base * MULT**4 / alloc * 100:.1f}% of allocation")

# What does this look like for different allocations?
print("\n" + "=" * 80)
print("PRE-CALCULATED GRID AT DIFFERENT CAPITAL LEVELS")
print("=" * 80)

for name, a in [("Live $340, 3 coins, ~$102/coin", 102),
                ("Live $1K deposit, 3 coins, ~$300/coin", 300),
                ("Prod $20K, 5 coins, ~$3K/coin", 3000),
                ("Paper $50K, 5 coins, ~$20K/coin", 20000)]:
    base = a / mult_sum
    l1 = base
    l12 = base * MULT**4
    print(f"\n  {name}:")
    print(f"    L1=${l1:>8,.2f}  L4=${base*MULT**3:>8,.2f}  L5-L12=${l12:>8,.2f} each")
    print(f"    Smallest=${l1:>8,.2f}  Largest=${l12:>8,.2f}  Ratio=1:{l12/l1:.1f}")

# Compare grid depth
print("\n" + "=" * 80)
print("GRID DEPTH COMPARISON (how far the grid covers)")
print("=" * 80)
print(f"  SO deviation: 2% per layer")
print(f"  12 layers = grid covers up to {2*11:.0f}% price drop from L1")
print(f"  With proper Martingale, deeper layers have MORE weight")
print(f"  L12 is {MULT**4:.1f}x the size of L1 — pulls avg down aggressively")
