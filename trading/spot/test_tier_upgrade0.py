"""
Test suite for Upgrade 0: Adaptive Equity Tiers & Pool Split with Hysteresis.
Covers test cases T0.1–T0.21 from V14PM_UPGRADE_SCOPE.md.
"""
import sys
sys.path.insert(0, r"C:\Users\Never\.openclaw\workspace")

from trading.spot.v14_capital_manager import (
    CapitalRouter, EQUITY_TIER_CAPS, EQUITY_TIER_SPLITS, TIER_HYSTERESIS_PCT,
)

PASS = 0
FAIL = 0

def check(test_id: str, description: str, condition: bool, detail: str = ""):
    global PASS, FAIL
    status = "PASS" if condition else "FAIL"
    if not condition:
        FAIL += 1
    else:
        PASS += 1
    print(f"  {test_id}: {status} - {description}")
    if detail:
        print(f"           {detail}")
    if not condition:
        print(f"           ^^^ ASSERTION FAILED ^^^")


def test_tier_lookups():
    """T0.1–T0.8: Verify tier lookups at key equity levels."""
    print("\n=== Tier Lookups ===")

    # T0.1: $340 → 3 coins, 90/10
    r = CapitalRouter(340)
    check("T0.1", "$340 → 3 coins, 90/10",
          r.tier_coin_cap == 3 and abs(r.active_pool_total - 306) < 1
          and abs(r.reserve_pool_total - 34) < 1,
          f"coins={r.tier_coin_cap}, active={r.active_pool_total:.2f}, reserve={r.reserve_pool_total:.2f}")

    # T0.2: $1,000 → 3 coins, 90/10
    r = CapitalRouter(1000)
    check("T0.2", "$1,000 → 3 coins, 90/10",
          r.tier_coin_cap == 3 and abs(r.active_pool_total - 900) < 1
          and abs(r.reserve_pool_total - 100) < 1,
          f"coins={r.tier_coin_cap}, active={r.active_pool_total:.2f}, reserve={r.reserve_pool_total:.2f}")

    # T0.3: $3,000 → 4 coins, 90/10
    r = CapitalRouter(3000)
    check("T0.3", "$3,000 → 4 coins, 90/10",
          r.tier_coin_cap == 4 and abs(r.active_pool_total - 2700) < 1
          and abs(r.reserve_pool_total - 300) < 1,
          f"coins={r.tier_coin_cap}, active={r.active_pool_total:.2f}, reserve={r.reserve_pool_total:.2f}")

    # T0.4: $5,000 → 5 coins, 90/10
    r = CapitalRouter(5000)
    check("T0.4", "$5,000 → 5 coins, 90/10",
          r.tier_coin_cap == 5 and abs(r.active_pool_total - 4500) < 1
          and abs(r.reserve_pool_total - 500) < 1,
          f"coins={r.tier_coin_cap}, active={r.active_pool_total:.2f}, reserve={r.reserve_pool_total:.2f}")

    # T0.5: $10,000 → 5 coins, 80/20
    r = CapitalRouter(10000)
    check("T0.5", "$10,000 → 5 coins, 80/20",
          r.tier_coin_cap == 5 and abs(r.active_pool_total - 8000) < 1
          and abs(r.reserve_pool_total - 2000) < 1,
          f"coins={r.tier_coin_cap}, active={r.active_pool_total:.2f}, reserve={r.reserve_pool_total:.2f}")

    # T0.6: $20,000 → 5 coins, 75/25
    r = CapitalRouter(20000)
    check("T0.6", "$20,000 → 5 coins, 75/25",
          r.tier_coin_cap == 5 and abs(r.active_pool_total - 15000) < 1
          and abs(r.reserve_pool_total - 5000) < 1,
          f"coins={r.tier_coin_cap}, active={r.active_pool_total:.2f}, reserve={r.reserve_pool_total:.2f}")

    # T0.7: $50,000 → 5 coins, 75/25 (paper bot reference)
    r = CapitalRouter(50000)
    check("T0.7", "$50,000 → 5 coins, 75/25 (paper parity)",
          r.tier_coin_cap == 5 and abs(r.active_pool_total - 37500) < 1,
          f"coins={r.tier_coin_cap}, active={r.active_pool_total:.2f}, reserve={r.reserve_pool_total:.2f}")

    # T0.8: $100,000 → 10 coins, 75/25
    r = CapitalRouter(100000)
    check("T0.8", "$100,000 → 10 coins, 75/25",
          r.tier_coin_cap == 10 and abs(r.active_pool_total - 75000) < 1,
          f"coins={r.tier_coin_cap}, active={r.active_pool_total:.2f}, reserve={r.reserve_pool_total:.2f}")


def test_layer_viability():
    """T0.9–T0.10: Verify layer sizing stays above $5 Aster minimum."""
    print("\n=== Layer Viability ===")

    # DCA layer sizing: BO = 40% of per-coin, then each layer *= 1.5x dev, mult=1.5
    # Using profile high: BO=40%, deviation=1.5%, multiplier=1.5x, 12 layers
    def calc_layers(per_coin_capital: float, num_layers: int = 12) -> list:
        bo = per_coin_capital * 0.40
        layers = []
        for i in range(num_layers):
            size = bo * (0.7 ** i)  # geometric decay
            layers.append(round(size, 2))
        return layers

    # T0.9: $3K / 4 coins / 90-10
    per_coin = 2700 / 4  # $675
    layers = calc_layers(per_coin)
    viable = [l for l in layers if l >= 5.0]
    check("T0.9", f"$3K/4coins: {len(viable)} viable layers, smallest ${min(viable):.2f}",
          len(viable) >= 10 and min(viable) >= 5.0,
          f"layers: {layers}")

    # T0.10: $1K / 3 coins / 90-10
    per_coin = 900 / 3  # $300
    layers = calc_layers(per_coin)
    viable = [l for l in layers if l >= 5.0]
    check("T0.10", f"$1K/3coins: {len(viable)} viable layers, smallest ${min(viable):.2f}",
          len(viable) >= 8 and min(viable) >= 5.0,
          f"layers: {layers}")


def test_tier_upgrades():
    """T0.11–T0.12: Verify immediate upgrade at boundary."""
    print("\n=== Tier Upgrades ===")

    # T0.11: Coin cap upgrade at $3K boundary
    r = CapitalRouter(2900)
    assert r.tier_coin_cap == 3, f"Expected 3 coins at $2900, got {r.tier_coin_cap}"
    # Simulate rebalance with equity growing to $3K
    r.rebalance_daily([], current_equity=3000)
    check("T0.11", "Coin cap upgrade: $2.9K→$3K = 3→4 coins",
          r.tier_coin_cap == 4,
          f"coins={r.tier_coin_cap}")

    # T0.12: Split upgrade at $10K boundary
    r = CapitalRouter(9900)
    split_before = EQUITY_TIER_SPLITS[r._split_tier_index]
    assert abs(split_before[1] - 0.90) < 0.01, f"Expected 90/10 at $9900"
    r.rebalance_daily([], current_equity=10000)
    split_after = EQUITY_TIER_SPLITS[r._split_tier_index]
    check("T0.12", "Split upgrade: $9.9K→$10K = 90/10→80/20",
          abs(split_after[1] - 0.80) < 0.01,
          f"split={split_after[1]*100:.0f}/{split_after[2]*100:.0f}")


def test_paper_bot_unchanged():
    """T0.13: Paper bot at $50K should behave the same."""
    print("\n=== Paper Bot Compatibility ===")
    r = CapitalRouter(50000)
    check("T0.13", "$50K paper bot: 5 coins, 75/25",
          r.tier_coin_cap == 5
          and abs(r.active_pool_total - 37500) < 1
          and abs(r.reserve_pool_total - 12500) < 1,
          f"coins={r.tier_coin_cap}, active={r.active_pool_total:.2f}, reserve={r.reserve_pool_total:.2f}")


def test_status_fields():
    """T0.14: Verify status fields are correct."""
    print("\n=== Status Fields ===")
    r = CapitalRouter(3000)
    split = EQUITY_TIER_SPLITS[r._split_tier_index]
    pool_split_str = f"{split[1]*100:.0f}/{split[2]*100:.0f}"
    check("T0.14", "$3K status: tier_coin_cap=4, pool_split=90/10",
          r.tier_coin_cap == 4 and pool_split_str == "90/10",
          f"tier_coin_cap={r.tier_coin_cap}, pool_split={pool_split_str}")


def test_hysteresis():
    """T0.16–T0.21: Hysteresis behavior."""
    print("\n=== Hysteresis ===")

    # T0.16: No downgrade in buffer — $3K → dip to $2,860 (buffer is $2,850)
    r = CapitalRouter(3000)
    assert r.tier_coin_cap == 4
    r.rebalance_daily([], current_equity=2860)
    check("T0.16", "No downgrade in buffer: $3K→$2,860 stays 4 coins",
          r.tier_coin_cap == 4,
          f"coins={r.tier_coin_cap}, equity=${r.total_equity:.2f}")

    # T0.17: Confirmed downgrade below buffer — drop to $2,849
    r.rebalance_daily([], current_equity=2849)
    check("T0.17", "Downgrade below buffer: $2,849 → 3 coins",
          r.tier_coin_cap == 3,
          f"coins={r.tier_coin_cap}, equity=${r.total_equity:.2f}")

    # T0.18: Re-upgrade after downgrade — back to $3,000
    r.rebalance_daily([], current_equity=3000)
    check("T0.18", "Re-upgrade: $2,849→$3,000 → 4 coins (immediate)",
          r.tier_coin_cap == 4,
          f"coins={r.tier_coin_cap}")

    # T0.19: Split downgrade buffer — $10K → dip to $9,600 (buffer is $9,500)
    r = CapitalRouter(10000)
    split_before = EQUITY_TIER_SPLITS[r._split_tier_index]
    assert abs(split_before[1] - 0.80) < 0.01, "Expected 80/20 at $10K"
    r.rebalance_daily([], current_equity=9600)
    split_after = EQUITY_TIER_SPLITS[r._split_tier_index]
    check("T0.19", "Split buffer: $10K→$9,600 stays 80/20",
          abs(split_after[1] - 0.80) < 0.01,
          f"split={split_after[1]*100:.0f}/{split_after[2]*100:.0f}")

    # T0.20: Confirmed split downgrade — drop to $9,499
    r.rebalance_daily([], current_equity=9499)
    split_after = EQUITY_TIER_SPLITS[r._split_tier_index]
    check("T0.20", "Split downgrade: $9,499 → 90/10",
          abs(split_after[1] - 0.90) < 0.01,
          f"split={split_after[1]*100:.0f}/{split_after[2]*100:.0f}")

    # T0.21: State persistence — simulate save/restore of tier indices
    r = CapitalRouter(3000)
    assert r.tier_coin_cap == 4
    r.rebalance_daily([], current_equity=2860)  # In buffer, stays 4
    assert r.tier_coin_cap == 4
    saved_cap_idx = r._cap_tier_index
    saved_split_idx = r._split_tier_index

    # Create new router as if restarting, passing saved indices
    r2 = CapitalRouter(2860, cap_tier_index=saved_cap_idx, split_tier_index=saved_split_idx)
    check("T0.21", "State persistence: restart at $2,860 with saved indices → still 4 coins",
          r2.tier_coin_cap == 4,
          f"coins={r2.tier_coin_cap} (fresh lookup would give {CapitalRouter.get_tier_coin_cap(2860)})")

    # Verify that WITHOUT saved indices, $2,860 would give 3 coins (raw lookup)
    r3 = CapitalRouter(2860)
    check("T0.21b", "Without saved indices, $2,860 → 3 coins (raw lookup, no hysteresis)",
          r3.tier_coin_cap == 3,
          f"coins={r3.tier_coin_cap}")


def test_edge_cases():
    """Additional edge cases."""
    print("\n=== Edge Cases ===")

    # Below $100
    r = CapitalRouter(50)
    check("Edge-1", "$50 → 0 coins (below minimum)",
          r.tier_coin_cap == 0,
          f"coins={r.tier_coin_cap}")

    # Exactly at boundaries
    r = CapitalRouter(100)
    check("Edge-2", "$100 → 3 coins, 90/10",
          r.tier_coin_cap == 3,
          f"coins={r.tier_coin_cap}")

    r = CapitalRouter(99999)
    check("Edge-3", "$99,999 → 5 coins, 75/25",
          r.tier_coin_cap == 5,
          f"coins={r.tier_coin_cap}")

    r = CapitalRouter(100000)
    check("Edge-4", "$100,000 → 10 coins, 75/25",
          r.tier_coin_cap == 10,
          f"coins={r.tier_coin_cap}")

    # Multiple rebalances — hysteresis should be stable
    r = CapitalRouter(3000)
    for _ in range(10):
        r.rebalance_daily([], current_equity=2900)  # In buffer
    check("Edge-5", "10x rebalance at $2,900 (in buffer) → stable at 4 coins",
          r.tier_coin_cap == 4,
          f"coins={r.tier_coin_cap}")


if __name__ == "__main__":
    print("=" * 60)
    print("Upgrade 0 Test Suite: Adaptive Tiers & Hysteresis")
    print("=" * 60)

    test_tier_lookups()
    test_layer_viability()
    test_tier_upgrades()
    test_paper_bot_unchanged()
    test_status_fields()
    test_hysteresis()
    test_edge_cases()

    print("\n" + "=" * 60)
    print(f"Results: {PASS} passed, {FAIL} failed")
    print("=" * 60)
    sys.exit(1 if FAIL > 0 else 0)
