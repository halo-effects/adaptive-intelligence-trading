"""Verify the revised GAP-13 fix produces correct layer sizing."""

alloc = 9000  # $50K / 5 coins * 90%
BO = 0.30
MULT = 1.5

print("REVISED GAP-13: capital = allocation - invested")
print(f"Allocation: ${alloc}")
print()

invested = 0
for i in range(12):
    remaining = alloc - invested
    if i == 0:
        order = remaining * BO
    else:
        order = remaining * BO * (MULT ** min(i, 4))
    
    if order > remaining:
        order = remaining  # Cap at what's left
    if order < 5:
        print(f"  L{i+1}: TOO SMALL (${order:.2f}), stopping")
        break
    
    invested += order
    remaining_after = alloc - invested
    pct = order / alloc * 100
    print(f"  L{i+1}: ${order:>8,.2f} ({pct:>5.1f}% of alloc) | "
          f"invested: ${invested:>8,.2f} | remaining: ${remaining_after:>8,.2f}")

print(f"\n  Total: ${invested:,.2f} of ${alloc:,.2f} ({invested/alloc*100:.1f}%)")
print(f"  Layers filled: {i+1 if order >= 5 else i}")
