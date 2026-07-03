"""
GridModel — Single source of truth for DCA grid geometry.
==========================================================
Version: 1.0 | Date: 2026-07-03 | Audit: C1/F1

All layer sizing, deviation triggers, TP math, and cumulative cost
calculations live here. Imported by:
  - v14_dca_engine.py (order sizing)
  - v14_cycle_scanner.py (simulation)
  - run_v14_portfolio_live_aster.py (top-up deficit math)
  - overflow-entry-v2 (L1 cost check)

This module is a LEAF dependency — zero imports from engine, runner,
or any other trading module.

Grid (d) — Bull-phase grid (resolved 2026-07-03, D-GRID):
  Layer sizes as fixed fractions of ALLOCATED CAPITAL (not remaining).
  L1=40%, L2=24%, L3=20%, L4=16%. Sum=100%, fully self-funded.
  Deviation 1.5% linear from average entry (unchanged).
  TP 3.0% above average entry (unchanged).
  Max 4 layers (unchanged). Leverage 1.0x (unchanged).
"""

# ── Grid Constants ────────────────────────────────────────────────────────────

# Fixed fractions of allocated capital per layer (sum = 1.00)
LAYER_FRACTIONS = [0.40, 0.24, 0.20, 0.16]

# Convenience alias for the L1 fraction (used by overflow entry, top-up checks)
L1_COST_FRACTION = LAYER_FRACTIONS[0]  # 0.40

# Deviation between safety orders (linear, from volume-weighted average entry)
SO_DEVIATION = 0.015  # 1.5%

# Take-profit percentage above average entry
TP_PCT = 0.030  # 3.0%

# Maximum DCA layers (including base order L1)
MAX_LAYERS = 4


# ── Grid Math ─────────────────────────────────────────────────────────────────

def layer_cost(layer_idx: int, allocation: float) -> float:
    """Cost of a single layer in dollar terms.

    Args:
        layer_idx: 0-based layer index (0=L1, 1=L2, 2=L3, 3=L4)
        allocation: total capital allocated to this coin

    Returns:
        Dollar cost for this layer
    """
    if layer_idx < 0 or layer_idx >= len(LAYER_FRACTIONS):
        return 0.0
    return allocation * LAYER_FRACTIONS[layer_idx]


def cumulative_cost(n_layers: int, allocation: float) -> float:
    """Total cost of filling n layers.

    Args:
        n_layers: number of layers to fill (1-4)
        allocation: total capital allocated to this coin

    Returns:
        Total dollar cost for all n layers
    """
    n = min(n_layers, len(LAYER_FRACTIONS))
    return allocation * sum(LAYER_FRACTIONS[:n])


def remaining_grid_cost(current_layers: int, allocation: float) -> float:
    """Cost of unfilled layers remaining in the grid.

    Args:
        current_layers: number of layers already filled (0-4)
        allocation: total capital allocated to this coin

    Returns:
        Dollar cost for layers not yet filled
    """
    if current_layers >= len(LAYER_FRACTIONS):
        return 0.0
    return allocation * sum(LAYER_FRACTIONS[current_layers:])


def tp_price(avg_entry: float, side: str = "long") -> float:
    """Take-profit price given an average entry.

    Args:
        avg_entry: volume-weighted average entry price
        side: "long" or "short"

    Returns:
        TP trigger price
    """
    if side == "long":
        return avg_entry * (1.0 + TP_PCT)
    else:
        return avg_entry * (1.0 - TP_PCT)


def trigger_price(avg_entry: float, layer_count: int, side: str = "long") -> float:
    """Price at which the next DCA layer triggers.

    Deviation is linear from average entry: SO_DEVIATION * layer_count.
    This matches the engine's actual trigger logic (not the scanner's old
    geometric-from-previous-SO model).

    Args:
        avg_entry: current volume-weighted average entry
        layer_count: number of layers already filled (next layer = layer_count + 1)
        side: "long" (trigger below) or "short" (trigger above)

    Returns:
        Price at which the next layer should fill
    """
    deviation = SO_DEVIATION * (layer_count + 1)
    if side == "long":
        return avg_entry * (1.0 - deviation)
    else:
        return avg_entry * (1.0 + deviation)


# ── Self-Test ─────────────────────────────────────────────────────────────────

def self_test():
    """Reproduce the D-GRID reference table from the implementation handoff.

    Reference (entry at 100, fills at 100 / 98.5 / 97.0 / 95.5):
    | Layer | Fraction | Cumulative | Avg entry | TP price | Bounce to TP |
    |-------|----------|------------|-----------|----------|--------------|
    | L1    | 40%      | 40%        | 100.00    | 103.00   | +3.0%        |
    | L2    | 24%      | 64%        | 99.44     | 102.42   | +4.0%        |
    | L3    | 20%      | 84%        | 98.85     | 101.82   | +5.0%        |
    | L4    | 16%      | 100%       | 98.29     | 101.24   | +6.0%        |
    """
    allocation = 100.0  # Use $100 for clean percentages
    fill_prices = [100.0, 98.5, 97.0, 95.5]

    # Expected values computed from the grid math (reference table was display-rounded)
    expected_avg = [100.00, 99.43, 98.84, 98.29]
    expected_tp = [103.00, 102.42, 101.81, 101.24]

    print("GridModel Self-Test")
    print("=" * 70)
    print(f"{'Layer':<8}{'Fraction':>10}{'Cumul':>10}{'Avg Entry':>12}{'TP Price':>12}{'Bounce':>10}")
    print("-" * 70)

    total_qty = 0.0
    total_cost = 0.0
    all_pass = True

    for i in range(MAX_LAYERS):
        cost = layer_cost(i, allocation)
        qty = cost / fill_prices[i]
        total_qty += qty
        total_cost += cost
        avg = total_cost / total_qty
        tp = tp_price(avg, "long")
        bounce = (tp / fill_prices[i] - 1.0) * 100
        cumul = cumulative_cost(i + 1, allocation)

        # Verify against expected (tolerance 0.02 for rounding)
        avg_ok = abs(avg - expected_avg[i]) < 0.02
        tp_ok = abs(tp - expected_tp[i]) < 0.02

        status = "✓" if (avg_ok and tp_ok) else "✗"
        if not (avg_ok and tp_ok):
            all_pass = False

        print(
            f"L{i+1:<7}{LAYER_FRACTIONS[i]*100:>9.0f}%{cumul:>9.0f}%"
            f"{avg:>12.2f}{tp:>12.2f}{bounce:>9.1f}%  {status}"
        )

    print("-" * 70)

    # Verify structural properties
    assert sum(LAYER_FRACTIONS) == 1.0, f"Fractions must sum to 1.0, got {sum(LAYER_FRACTIONS)}"
    assert len(LAYER_FRACTIONS) == MAX_LAYERS, f"Must have {MAX_LAYERS} fractions"
    assert L1_COST_FRACTION == LAYER_FRACTIONS[0], "L1_COST_FRACTION must equal first fraction"
    assert remaining_grid_cost(0, 100) == 100.0, "0 layers filled = full cost"
    assert remaining_grid_cost(4, 100) == 0.0, "4 layers filled = zero remaining"
    assert abs(remaining_grid_cost(2, 100) - 36.0) < 0.01, "2 layers filled = 36% remaining"

    if all_pass:
        print("ALL CHECKS PASSED ✓")
    else:
        print("SOME CHECKS FAILED ✗")
        raise AssertionError("Self-test failed")  # noqa: intentional custom name

    return all_pass


if __name__ == "__main__":
    self_test()
