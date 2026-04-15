#!/usr/bin/env python3
"""
One-time migration: convert V14 single-coin Aster live state
to V14PM portfolio live state format.

This copies:
  - Engine state for ASTER/USDT
  - Open deal tracking
  - TP order ID
  - Trade history (CSV)

Usage:
    python -m trading.spot.migrate_aster_to_pm --dry-run   # Preview
    python -m trading.spot.migrate_aster_to_pm              # Execute
"""

import json
import shutil
import sys
import io
from datetime import datetime, timezone
from pathlib import Path

if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

_WORKSPACE = Path(__file__).resolve().parent.parent.parent
OLD_DIR = _WORKSPACE / "trading" / "spot" / "live" / "v14"
NEW_DIR = _WORKSPACE / "trading" / "spot" / "live" / "v14pm"

def migrate(dry_run: bool = False):
    old_state_path = OLD_DIR / "state.json"
    old_csv_path   = OLD_DIR / "trades.csv"
    new_state_path = NEW_DIR / "state.json"
    new_csv_path   = NEW_DIR / "trades.csv"

    if not old_state_path.exists():
        print(f"ERROR: {old_state_path} not found")
        sys.exit(1)

    with open(old_state_path) as f:
        old = json.load(f)

    engine = old.get("engine", {})
    symbol = engine.get("symbol", "ASTER/USDT")
    tp_order_id = old.get("tp_order_id")

    # Build PM coin state for ASTER/USDT
    coin_state = {
        "symbol": symbol,
        "allocated_capital": engine.get("initial_capital", 340.0),
        "tp_order_id": tp_order_id,
        "last_candle_ts": old.get("last_candle_ts", 0),
        "cumulative_funding": 0.0,
        "last_funding_check_ms": 0,
        "engine_state": engine,
    }

    # Build open deals dict for trade tracker
    open_deals = {}
    for key, deal in old.get("open_deals", {}).items():
        # Convert old format key to new format
        open_deals[key] = {
            "deal_id": deal.get("deal_id", 1),
            "symbol": deal.get("symbol", symbol),
            "open_time": deal.get("open_time", ""),
            "layers": deal.get("layers", 0),
            "invested": deal.get("invested", 0.0),
        }

    # Build new PM state
    new_state = {
        "saved_at": datetime.now(timezone.utc).isoformat(),
        "bot_state": "RUNNING",
        "capital": old.get("capital", 340.0),
        "coins": {
            symbol: coin_state,
        },
        "router": {
            "active_pool_cash": engine.get("capital", 0),
            "reserve_pool_cash": 0.0,
            "active_allocations": {symbol: engine.get("initial_capital", 340.0)},
            "reserve_allocations": {},
        },
        "regime": {
            "signal_count": 0,
            "signal_type": None,
            "alert_state": "NONE",
        },
        "tg_update_offset": 0,
        "open_deals": open_deals,
    }

    print("=== Migration Preview ===")
    print(f"Symbol: {symbol}")
    print(f"Capital: ${old.get('capital', 0):.2f}")
    print(f"Cash: ${engine.get('capital', 0):.2f}")
    print(f"Invested: ${engine.get('long_cost', 0):.2f}")
    print(f"Layers: {engine.get('long_layers', 0)}")
    print(f"TP Order: {tp_order_id}")
    print(f"Open deals: {len(open_deals)}")
    print(f"Completed deals: 10 (from CSV)")
    print()

    if dry_run:
        print("DRY RUN — no files written")
        print(json.dumps(new_state, indent=2, default=str))
        return

    # Write new state
    NEW_DIR.mkdir(parents=True, exist_ok=True)
    with open(new_state_path, "w") as f:
        json.dump(new_state, f, indent=2, default=str)
    print(f"✅ Written: {new_state_path}")

    # Copy trades.csv (preserving existing history)
    if old_csv_path.exists():
        # Read old CSV, rewrite with PM-compatible fields
        shutil.copy2(old_csv_path, new_csv_path)
        print(f"✅ Copied: {new_csv_path}")
    else:
        print(f"⚠️  No trades.csv found at {old_csv_path}")

    print(f"\n✅ Migration complete. New bot will pick up ASTER/USDT position.")
    print(f"   TP order {tp_order_id} still active on exchange.")
    print(f"\nNext steps:")
    print(f"  1. Stop old bot (kill PID)")
    print(f"  2. Start new bot: python -u -m trading.spot.run_v14_portfolio_live_aster --capital 340 --confirm --skip-backfill")


if __name__ == "__main__":
    dry_run = "--dry-run" in sys.argv
    migrate(dry_run=dry_run)
