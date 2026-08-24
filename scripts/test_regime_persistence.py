"""Synthetic test for RH-1 regime event persistence."""
import io
import os
import sys
import sqlite3
from pathlib import Path

if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

# Use a temp DB for testing
os.environ["AIT_REGIME_DB"] = str(Path(__file__).parent / "test_regime_events.db")

# Remove old test DB
test_db = Path(os.environ["AIT_REGIME_DB"])
if test_db.exists():
    test_db.unlink()

from trading.spot.engine.regime_persistence import (
    log_coin_phase, log_alert, log_alert_response, log_global_flip,
    seed_attested_history, seed_current_state, get_event_count, _get_conn
)

print("=== RH-1 Synthetic Test ===\n")

# Test 1: Seed attested history
print("1. Seed attested history...")
seed_attested_history()
assert get_event_count() == 2, f"Expected 2, got {get_event_count()}"
print("   OK: 2 attested rows")

# Test idempotency
seed_attested_history()
assert get_event_count() == 2, "Idempotency failed"
print("   OK: idempotent (still 2)")

# Test 2: Seed current state
print("2. Seed current state...")
test_coins = {
    "TAO/USDT": {"engine_state": {"phase": "LONG_DCA"}},
    "HYPE/USDT": {"engine_state": {"phase": "SHORT_DCA"}},
    "INJ/USDT": {"engine_state": {"phase": "LONG_DCA"}},
}
seed_current_state(test_coins, "LONG_DCA")
expected = 2 + 1 + 3  # attested + global backfill + 3 coin backfills
assert get_event_count() == expected, f"Expected {expected}, got {get_event_count()}"
print(f"   OK: {expected} total rows (2 attested + 1 global + 3 coins)")

# Test idempotency
seed_current_state(test_coins, "LONG_DCA")
assert get_event_count() == expected, "Backfill idempotency failed"
print(f"   OK: idempotent (still {expected})")

# Test 3: Log coin phase transition
print("3. Log coin phase transition...")
log_coin_phase("TAO/USDT", "LONG_DCA", "SHORT_DCA", "OB93_timeout_35d")
assert get_event_count() == expected + 1
print("   OK: COIN_PHASE row written")

# Test 4: Log alert
print("4. Log regime alert...")
log_alert(0.15, 3, 15)
assert get_event_count() == expected + 2
print("   OK: ALERT row written")

# Test 5: Log alert response
print("5. Log alert response...")
log_alert_response(0.15, "approve")
assert get_event_count() == expected + 3
print("   OK: ALERT_RESPONSE row written")

# Test 6: Log global flip
print("6. Log global flip...")
log_global_flip("LONG_DCA", "SHORT_DCA", 0.35, 5, 15, "approve")
assert get_event_count() == expected + 4
print("   OK: GLOBAL_FLIP row written")

# Test 7: Fail-open — simulate DB error
print("7. Fail-open test...")
import trading.spot.engine.regime_persistence as rp
original_path = rp.DB_PATH
rp.DB_PATH = Path("/nonexistent/path/regime_events.db")
# This should NOT raise
log_coin_phase("TEST/USDT", "A", "B", "test")
log_alert(0.50, 10, 15)
log_global_flip("A", "B")
rp.DB_PATH = original_path
print("   OK: all 3 calls survived with bad DB path")

# Test 8: Verify data integrity
print("8. Verify data integrity...")
conn = _get_conn()
rows = conn.execute(
    "SELECT ts_utc, event_type, symbol, from_state, to_state, source "
    "FROM regime_events ORDER BY id"
).fetchall()

print(f"   Total rows: {len(rows)}")
for r in rows:
    ts = r[0][:10]
    print(f"   {ts} {r[1]:<16} {r[2] or '-':<15} {r[3] or '-':<12} -> {r[4] or '-':<12} [{r[5]}]")

conn.close()

# Cleanup
test_db.unlink()
print("\n=== All tests passed ===")
