"""
V13 Daily Collection Runner — Migrate DB, then collect all data.
Usage: python -u -m trading.spot.run_daily_collector
"""
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent / 'data' / 'candles.db'


def main():
    print("=" * 60)
    print("  V13 Daily Collection Runner")
    print("=" * 60)

    # Step 1: Ensure tables exist
    print("\n--- DB Migration ---")
    from trading.spot.db_migrate_v13_analytics import run_migration
    run_migration()

    # Step 2: Run collector
    print("\n--- Daily Collector ---")
    from trading.spot.daily_collector import run_collector
    run_collector()

    # Step 3: Summary
    print("\n--- Summary ---")
    conn = sqlite3.connect(str(DB_PATH))
    tables = ['scanner_results', 'phase_transitions', 'signal_snapshots',
              'coin_correlations', 'trade_context']
    for t in tables:
        try:
            row = conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()
            print(f"  {t}: {row[0]} rows")
        except Exception as e:
            print(f"  {t}: error - {e}")
    conn.close()
    print("\nDone.")


if __name__ == '__main__':
    main()
