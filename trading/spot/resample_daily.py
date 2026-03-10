#!/usr/bin/env python3
"""
Resample 1h candles → daily candles for all coins in candles_daily.

Ensures candles_daily stays up-to-date for coins that only have 1h data
from the Hyperliquid collector. Existing daily data is preserved (INSERT OR IGNORE).

Run after collect_scanner_candles.py in the hourly pipeline.
"""

import sqlite3
import sys
import io
import logging
from pathlib import Path

if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("resample_daily")

DB_PATH = Path(__file__).resolve().parent / "data" / "candles.db"


def ensure_daily_table(conn: sqlite3.Connection):
    """Ensure candles_daily exists. Uses the existing schema if table is present."""
    # Check if table already exists
    exists = conn.execute(
        "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='candles_daily'"
    ).fetchone()[0]
    if not exists:
        conn.execute("""
            CREATE TABLE candles_daily (
                symbol TEXT, date TEXT, timestamp INTEGER,
                open REAL, high REAL, low REAL, close REAL, volume REAL,
                candle_count INTEGER DEFAULT 0,
                PRIMARY KEY (symbol, timestamp)
            )
        """)
        conn.commit()


def resample_coin(conn: sqlite3.Connection, symbol: str) -> int:
    """Resample 1h candles to daily for one symbol. Returns new rows inserted."""
    # Get all 1h candles
    rows = conn.execute(
        "SELECT timestamp, open, high, low, close, volume "
        "FROM candles WHERE symbol = ? AND timeframe = '1h' ORDER BY timestamp",
        (symbol,)
    ).fetchall()

    if not rows:
        return 0

    # Group by day (UTC midnight boundary)
    days = {}
    for ts_ms, o, h, l, c, v in rows:
        day_ms = (ts_ms // 86_400_000) * 86_400_000
        if day_ms not in days:
            days[day_ms] = {"open": o, "high": h, "low": l, "close": c, "volume": v, "count": 1}
        else:
            d = days[day_ms]
            d["high"] = max(d["high"], h)
            d["low"] = min(d["low"], l)
            d["close"] = c
            d["volume"] += v
            d["count"] += 1

    # Insert (ignore duplicates — existing daily data from other sources is preserved)
    from datetime import datetime, timezone
    before = conn.total_changes
    for day_ms, d in sorted(days.items()):
        date_str = datetime.fromtimestamp(day_ms / 1000, tz=timezone.utc).strftime("%Y-%m-%d")
        conn.execute(
            "INSERT OR IGNORE INTO candles_daily "
            "(symbol, date, timestamp, open, high, low, close, volume, candle_count) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (symbol, date_str, day_ms, d["open"], d["high"], d["low"], d["close"], d["volume"], d["count"])
        )

    return conn.total_changes - before


def main():
    if not DB_PATH.exists():
        logger.error(f"Database not found: {DB_PATH}")
        sys.exit(1)

    conn = sqlite3.connect(str(DB_PATH))
    ensure_daily_table(conn)

    # Get all symbols that have 1h candles
    hourly_symbols = [r[0] for r in conn.execute(
        "SELECT DISTINCT symbol FROM candles WHERE timeframe = '1h' ORDER BY symbol"
    ).fetchall()]

    # Get symbols that already have daily candles
    daily_symbols = set(r[0] for r in conn.execute(
        "SELECT DISTINCT symbol FROM candles_daily ORDER BY symbol"
    ).fetchall())

    logger.info(f"Resampling {len(hourly_symbols)} hourly symbols → daily")
    logger.info(f"  Already have daily data: {len(daily_symbols)} symbols")

    total_new = 0
    updated = 0

    for symbol in hourly_symbols:
        # Get latest daily timestamp for this symbol
        latest_daily = conn.execute(
            "SELECT MAX(timestamp) FROM candles_daily WHERE symbol = ?",
            (symbol,)
        ).fetchone()[0]

        # Get latest hourly timestamp
        latest_hourly = conn.execute(
            "SELECT MAX(timestamp) FROM candles WHERE symbol = ? AND timeframe = '1h'",
            (symbol,)
        ).fetchone()[0]

        if latest_daily and latest_hourly:
            # Only resample if hourly data is ahead of daily by >24h
            if latest_hourly - latest_daily < 86_400_000:
                continue

        new = resample_coin(conn, symbol)
        if new > 0:
            updated += 1
            total_new += new
            status = "NEW" if symbol not in daily_symbols else "updated"
            logger.info(f"  {symbol}: +{new} daily candles ({status})")

    conn.commit()
    conn.close()

    logger.info(f"Done. {updated} symbols updated, {total_new} new daily candles.")


if __name__ == "__main__":
    main()
