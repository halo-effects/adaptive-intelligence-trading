"""
Test suite for Upgrade 1: Dynamic Capital Management.
Tests resize(), capital ledger, and tier transitions on deposit/withdrawal.
"""
import sys
import os
import json
import tempfile
from pathlib import Path

sys.path.insert(0, r"C:\Users\Never\.openclaw\workspace")

from trading.spot.v14_capital_manager import (
    CapitalRouter, EQUITY_TIER_CAPS, EQUITY_TIER_SPLITS, TIER_HYSTERESIS_PCT,
    load_capital_ledger, save_capital_ledger, record_ledger_transaction,
    get_ledger_summary,
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


def test_resize():
    """Test router.resize() adjusts pools and tiers correctly."""
    print("\n=== Resize Tests ===")

    # T1.R1: Resize from $340 to $1340 (deposit $1K)
    r = CapitalRouter(340)
    assert r.tier_coin_cap == 3
    r.resize(1340)
    check("T1.R1", "Resize $340->$1340: still 3 coins, 90/10, pools updated",
          r.tier_coin_cap == 3
          and abs(r.active_pool_total - 1206) < 1
          and abs(r.reserve_pool_total - 134) < 1,
          f"coins={r.tier_coin_cap}, active={r.active_pool_total:.2f}, reserve={r.reserve_pool_total:.2f}")

    # T1.R2: Resize from $1340 to $3000 (crosses $3K tier)
    r.resize(3000)
    check("T1.R2", "Resize $1340->$3000: upgrades to 4 coins, 90/10",
          r.tier_coin_cap == 4
          and abs(r.active_pool_total - 2700) < 1,
          f"coins={r.tier_coin_cap}, active={r.active_pool_total:.2f}")

    # T1.R3: Resize from $3000 to $5000 (crosses $5K tier)
    r.resize(5000)
    check("T1.R3", "Resize $3000->$5000: upgrades to 5 coins, 90/10",
          r.tier_coin_cap == 5
          and abs(r.active_pool_total - 4500) < 1,
          f"coins={r.tier_coin_cap}, active={r.active_pool_total:.2f}")

    # T1.R4: Resize from $5000 to $10000 (crosses split boundary)
    r.resize(10000)
    check("T1.R4", "Resize $5000->$10000: 5 coins, split changes to 80/20",
          r.tier_coin_cap == 5
          and abs(r.active_pool_total - 8000) < 1
          and abs(r.reserve_pool_total - 2000) < 1,
          f"coins={r.tier_coin_cap}, active={r.active_pool_total:.2f}, reserve={r.reserve_pool_total:.2f}")

    # T1.R5: Resize down from $10000 to $9600 (within hysteresis buffer)
    r.resize(9600)
    split = EQUITY_TIER_SPLITS[r._split_tier_index]
    check("T1.R5", "Resize $10K->$9600: stays 80/20 (hysteresis buffer)",
          abs(split[1] - 0.80) < 0.01,
          f"split={split[1]*100:.0f}/{split[2]*100:.0f}")

    # T1.R6: Resize with existing allocations
    r2 = CapitalRouter(1000)
    r2.request_capital("GRASS/USDT", 200, "active")  # Lock $200
    r2.resize(1500)  # Deposit $500
    check("T1.R6", "Resize with $200 allocated: cash = pool_total - allocated",
          abs(r2.active_pool_cash - (1500 * 0.90 - 200)) < 1,
          f"active_cash={r2.active_pool_cash:.2f}, expected={1500*0.90 - 200:.2f}")

    # T1.R7: Withdrawal within hysteresis buffer ($2860 > $2850 trigger)
    r3 = CapitalRouter(3000)
    r3.resize(2860)  # Withdraw $140 — stays at 4 coins (above $2850 trigger)
    check("T1.R7", "Resize $3K->$2860: stays 4 coins (within hysteresis buffer)",
          r3.tier_coin_cap == 4,
          f"coins={r3.tier_coin_cap}")

    # T1.R8: Withdrawal that drops below hysteresis buffer
    r3.resize(2849)  # Below $2850 trigger
    check("T1.R8", "Resize $2860->$2849: drops to 3 coins (below trigger)",
          r3.tier_coin_cap == 3,
          f"coins={r3.tier_coin_cap}")


def test_capital_ledger():
    """Test capital ledger CRUD operations."""
    print("\n=== Capital Ledger Tests ===")

    with tempfile.TemporaryDirectory() as tmpdir:
        ledger_path = Path(tmpdir) / "test_ledger.json"

        # T1.L1: New ledger with seed
        ledger = record_ledger_transaction(ledger_path, "seed", 340.0, note="Test seed")
        check("T1.L1", "Seed creates ledger with $340",
              ledger["seed_capital"] == 340.0
              and ledger["current_capital"] == 340.0
              and len(ledger["transactions"]) == 1,
              f"seed={ledger['seed_capital']}, current={ledger['current_capital']}")

        # T1.L2: Deposit
        ledger = record_ledger_transaction(ledger_path, "deposit", 1000.0, note="Test deposit")
        check("T1.L2", "Deposit $1000: capital=$1340",
              abs(ledger["current_capital"] - 1340.0) < 0.01
              and len(ledger["transactions"]) == 2,
              f"current={ledger['current_capital']}")

        # T1.L3: Withdrawal
        ledger = record_ledger_transaction(ledger_path, "withdrawal", 200.0, note="Test withdraw")
        check("T1.L3", "Withdrawal $200: capital=$1140",
              abs(ledger["current_capital"] - 1140.0) < 0.01
              and len(ledger["transactions"]) == 3,
              f"current={ledger['current_capital']}")

        # T1.L4: Load persisted ledger
        loaded = load_capital_ledger(ledger_path)
        check("T1.L4", "Persisted ledger loads correctly",
              loaded is not None
              and abs(loaded["current_capital"] - 1140.0) < 0.01
              and len(loaded["transactions"]) == 3,
              f"current={loaded['current_capital'] if loaded else 'None'}")

        # T1.L5: Summary
        summary = get_ledger_summary(ledger_path)
        check("T1.L5", "Ledger summary correct",
              summary is not None
              and abs(summary["total_deposits"] - 1000.0) < 0.01
              and abs(summary["total_withdrawals"] - 200.0) < 0.01
              and summary["transaction_count"] == 3,
              f"deposits={summary['total_deposits']}, withdrawals={summary['total_withdrawals']}")

        # T1.L6: Non-existent ledger returns None
        check("T1.L6", "Non-existent ledger returns None",
              load_capital_ledger(Path(tmpdir) / "nonexistent.json") is None)

        # T1.L7: Transaction has ISO timestamp
        last_tx = ledger["transactions"][-1]
        check("T1.L7", "Transaction has ISO timestamp",
              "timestamp" in last_tx and "T" in last_tx["timestamp"],
              f"timestamp={last_tx.get('timestamp', 'MISSING')}")


def test_resize_with_ledger_flow():
    """Simulate the full deposit flow: ledger + resize."""
    print("\n=== Full Deposit Flow ===")

    with tempfile.TemporaryDirectory() as tmpdir:
        ledger_path = Path(tmpdir) / "flow_ledger.json"

        # Start bot at $340
        r = CapitalRouter(340)
        record_ledger_transaction(ledger_path, "seed", 340.0)

        # Deposit $1K
        record_ledger_transaction(ledger_path, "deposit", 1000.0, note="First deposit")
        summary = get_ledger_summary(ledger_path)
        r.resize(summary["current_capital"])

        check("T1.F1", "After $1K deposit: capital=$1340, 3 coins, 90/10",
              abs(r.total_equity - 1340) < 1
              and r.tier_coin_cap == 3,
              f"equity={r.total_equity:.2f}, coins={r.tier_coin_cap}")

        # Deposit another $2K (total $3340, crosses $3K tier)
        record_ledger_transaction(ledger_path, "deposit", 2000.0, note="Second deposit")
        summary = get_ledger_summary(ledger_path)
        r.resize(summary["current_capital"])

        check("T1.F2", "After $2K more: capital=$3340, 4 coins, 90/10",
              abs(r.total_equity - 3340) < 1
              and r.tier_coin_cap == 4,
              f"equity={r.total_equity:.2f}, coins={r.tier_coin_cap}")

        # Withdraw $500 (still above $3K trigger - $2850)
        record_ledger_transaction(ledger_path, "withdrawal", 500.0, note="Partial withdraw")
        summary = get_ledger_summary(ledger_path)
        r.resize(summary["current_capital"])

        check("T1.F3", "After $500 withdraw: capital=$2840, 4->3 coins (below $2850 trigger)",
              abs(r.total_equity - 2840) < 1
              and r.tier_coin_cap == 3,  # $2840 < $2850 trigger
              f"equity={r.total_equity:.2f}, coins={r.tier_coin_cap}")

        # Verify ledger accuracy
        summary = get_ledger_summary(ledger_path)
        check("T1.F4", "Ledger tracks all transactions",
              summary["transaction_count"] == 4  # seed + 2 deposits + 1 withdrawal
              and abs(summary["total_deposits"] - 3000.0) < 0.01
              and abs(summary["total_withdrawals"] - 500.0) < 0.01,
              f"txns={summary['transaction_count']}, deposits={summary['total_deposits']}, "
              f"withdrawals={summary['total_withdrawals']}")


if __name__ == "__main__":
    print("=" * 60)
    print("Upgrade 1 Test Suite: Dynamic Capital Management")
    print("=" * 60)

    test_resize()
    test_capital_ledger()
    test_resize_with_ledger_flow()

    print("\n" + "=" * 60)
    print(f"Results: {PASS} passed, {FAIL} failed")
    print("=" * 60)
    sys.exit(1 if FAIL > 0 else 0)
