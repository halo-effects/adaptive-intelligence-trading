#!/usr/bin/env python3
"""
One-time Binance Futures candle backfill for all 50 Aster scanner coins.

Pulls maximum available 1h candle history from Binance Futures API
and stores in candles.db. Designed to be run once before switching
the hourly collector to Aster.

After running this, run resample_daily.py to generate daily candles,
then run v14_cycle_scanner.py to generate initial scores.

Usage:
    python -u -m trading.spot.backfill_binance
    python -u -m trading.spot.backfill_binance --coin BTC   # Single coin
    python -u -m trading.spot.backfill_binance --dry-run    # Check coverage only
"""

import ccxt
import sqlite3
import sys
import io
import os
import time
import logging
import argparse
from datetime import datetime, timezone, timedelta
from pathlib import Path

if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("binance_backfill")

_WORKSPACE = Path(__file__).resolve().parent.parent.parent
DB_PATH = Path(os.environ.get("AIT_CANDLES_DB", str(_WORKSPACE / "trading" / "spot" / "data" / "candles.db")))

# ── 50-coin universe — Binance Futures symbols ──────────────────────────────
# Format: (db_symbol, binance_futures_symbol)
# Note: PEPE, BONK, FLOKI use 1000-prefix on Binance.
# DB stores as COIN/USDT (without 1000-prefix) — price scaled accordingly.
# Binance futures are USDT-margined linear contracts.

COINS = [
    # --- Established (pre-2024) ---
    ("BTC/USDT",    "BTC/USDT:USDT"),
    ("ETH/USDT",    "ETH/USDT:USDT"),
    ("SOL/USDT",    "SOL/USDT:USDT"),
    ("XRP/USDT",    "XRP/USDT:USDT"),
    ("LINK/USDT",   "LINK/USDT:USDT"),
    ("DOGE/USDT",   "DOGE/USDT:USDT"),
    ("ADA/USDT",    "ADA/USDT:USDT"),
    ("LTC/USDT",    "LTC/USDT:USDT"),
    ("AVAX/USDT",   "AVAX/USDT:USDT"),
    ("DOT/USDT",    "DOT/USDT:USDT"),
    ("UNI/USDT",    "UNI/USDT:USDT"),
    ("ATOM/USDT",   "ATOM/USDT:USDT"),
    ("NEAR/USDT",   "NEAR/USDT:USDT"),
    ("HBAR/USDT",   "HBAR/USDT:USDT"),
    ("INJ/USDT",    "INJ/USDT:USDT"),
    ("FIL/USDT",    "FIL/USDT:USDT"),
    ("CRV/USDT",    "CRV/USDT:USDT"),
    ("SNX/USDT",    "SNX/USDT:USDT"),
    ("ZEC/USDT",    "ZEC/USDT:USDT"),
    # --- DeFi / Mid-cap ---
    ("AAVE/USDT",   "AAVE/USDT:USDT"),
    ("ARB/USDT",    "ARB/USDT:USDT"),
    ("JUP/USDT",    "JUP/USDT:USDT"),
    ("PENDLE/USDT", "PENDLE/USDT:USDT"),
    ("STX/USDT",    "STX/USDT:USDT"),
    ("ZRO/USDT",    "ZRO/USDT:USDT"),
    # --- High-beta / Speculative ---
    # 1000-prefix: Binance uses 1000PEPEUSDT, we store as PEPE/USDT with scaled prices
    ("PEPE/USDT",   "1000PEPE/USDT:USDT"),
    ("BONK/USDT",   "1000BONK/USDT:USDT"),
    ("FLOKI/USDT",  "1000FLOKI/USDT:USDT"),
    ("JTO/USDT",    "JTO/USDT:USDT"),
    ("PYTH/USDT",   "PYTH/USDT:USDT"),
    ("TIA/USDT",    "TIA/USDT:USDT"),
    ("SEI/USDT",    "SEI/USDT:USDT"),
    ("APT/USDT",    "APT/USDT:USDT"),
    ("SUI/USDT",    "SUI/USDT:USDT"),
    # --- AI / Infrastructure ---
    ("FET/USDT",    "FET/USDT:USDT"),
    ("TAO/USDT",    "TAO/USDT:USDT"),
    ("HYPE/USDT",   "HYPE/USDT:USDT"),
    ("VIRTUAL/USDT","VIRTUAL/USDT:USDT"),
    ("RENDER/USDT", "RENDER/USDT:USDT"),
    # --- New L1/L2 ---
    ("BERA/USDT",   "BERA/USDT:USDT"),
    ("MOVE/USDT",   "MOVE/USDT:USDT"),
    ("INIT/USDT",   "INIT/USDT:USDT"),
    ("S/USDT",      "S/USDT:USDT"),
    ("IP/USDT",     "IP/USDT:USDT"),
    # --- Yield / RWA ---
    ("ONDO/USDT",   "ONDO/USDT:USDT"),
    ("EIGEN/USDT",  "EIGEN/USDT:USDT"),
    ("ENA/USDT",    "ENA/USDT:USDT"),
    # --- DePIN / Other ---
    ("GRASS/USDT",  "GRASS/USDT:USDT"),
    ("ORCA/USDT",   "ORCA/USDT:USDT"),
    ("TRUMP/USDT",  "TRUMP/USDT:USDT"),
]

# 1000-prefix coins: price from Binance is per 1000 units.
# Multiply by 1000 to get actual price when storing in DB.
PRICE_SCALE_1000 = {"PEPE/USDT", "BONK/USDT", "FLOKI/USDT"}

# Incremental buffer — overlap to catch any gaps
INCREMENTAL_BUFFER_HOURS = 6


def init_db(conn: sqlite3.Connection):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS candles (
            symbol TEXT, timeframe TEXT, timestamp INTEGER,
            open REAL, high REAL, low REAL, close REAL, volume REAL,
            PRIMARY KEY (symbol, timeframe, timestamp)
        )
    """)
    conn.commit()


def get_coverage(conn: sqlite3.Connection, db_symbol: str) -> dict:
    """Get current candle coverage for a symbol."""
    row = conn.execute(
        "SELECT COUNT(*), MIN(timestamp), MAX(timestamp) FROM candles "
        "WHERE symbol = ? AND timeframe = '1h'",
        (db_symbol,)
    ).fetchone()
    count = row[0] or 0
    if count == 0:
        return {"count": 0, "days": 0, "first": None, "last": None}
    first = datetime.fromtimestamp(row[1] / 1000, tz=timezone.utc)
    last = datetime.fromtimestamp(row[2] / 1000, tz=timezone.utc)
    days = (row[2] - row[1]) / (1000 * 86400)
    return {"count": count, "days": days, "first": first, "last": last}


def fetch_candles_from(exchange, binance_symbol: str, since_ms: int, db_symbol: str) -> list:
    """
    Fetch 1h candles from Binance, paginating forward from since_ms.
    Applies 1000x price scaling for PEPE/BONK/FLOKI.
    Returns list of (timestamp, open, high, low, close, volume).
    """
    scale = 1000.0 if db_symbol in PRICE_SCALE_1000 else 1.0
    all_candles = []
    cursor = since_ms
    now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
    retries = 0

    while cursor < now_ms:
        try:
            batch = exchange.fetch_ohlcv(binance_symbol, "1h", since=cursor, limit=1500)
            retries = 0
        except Exception as e:
            if "429" in str(e) and retries < 3:
                retries += 1
                wait = 10 * retries
                logger.info(f"  Rate limited, waiting {wait}s (retry {retries}/3)")
                time.sleep(wait)
                continue
            logger.warning(f"  Error fetching {binance_symbol} from {cursor}: {e}")
            break

        if not batch:
            break

        # Apply price scaling if needed
        if scale != 1.0:
            batch = [[c[0], c[1]*scale, c[2]*scale, c[3]*scale, c[4]*scale, c[5]/scale] for c in batch]

        all_candles.extend(batch)
        last_ts = batch[-1][0]

        if last_ts <= cursor:
            break
        cursor = last_ts + 1
        time.sleep(0.3)

    # Deduplicate and sort
    seen = set()
    unique = []
    for c in all_candles:
        if c[0] not in seen:
            seen.add(c[0])
            unique.append(c)
    unique.sort(key=lambda x: x[0])
    return unique


def store_candles(conn: sqlite3.Connection, db_symbol: str, candles: list) -> int:
    """Store candles, return count of new rows inserted."""
    if not candles:
        return 0
    before = conn.execute(
        "SELECT COUNT(*) FROM candles WHERE symbol = ? AND timeframe = '1h'",
        (db_symbol,)
    ).fetchone()[0]
    conn.executemany(
        "INSERT OR IGNORE INTO candles "
        "(symbol, timeframe, timestamp, open, high, low, close, volume) "
        "VALUES (?, '1h', ?, ?, ?, ?, ?, ?)",
        [(db_symbol, c[0], c[1], c[2], c[3], c[4], c[5]) for c in candles]
    )
    conn.commit()
    after = conn.execute(
        "SELECT COUNT(*) FROM candles WHERE symbol = ? AND timeframe = '1h'",
        (db_symbol,)
    ).fetchone()[0]
    return after - before


def main():
    parser = argparse.ArgumentParser(description="Binance Futures candle backfill for 50-coin universe")
    parser.add_argument("--coin", help="Backfill a single coin (e.g. BTC)")
    parser.add_argument("--dry-run", action="store_true", help="Show coverage only, no fetching")
    args = parser.parse_args()

    if not DB_PATH.exists():
        logger.error(f"Database not found: {DB_PATH}")
        sys.exit(1)

    conn = sqlite3.connect(str(DB_PATH))
    init_db(conn)

    # Filter to single coin if requested
    coins = COINS
    if args.coin:
        coins = [(db, bn) for db, bn in COINS if db.split("/")[0].upper() == args.coin.upper()]
        if not coins:
            logger.error(f"Coin '{args.coin}' not in universe. Available: {[c[0].split('/')[0] for c in COINS]}")
            sys.exit(1)

    if args.dry_run:
        logger.info("=== DRY RUN — Coverage check only ===")
        for db_sym, _ in coins:
            short = db_sym.split("/")[0]
            cov = get_coverage(conn, db_sym)
            if cov["count"] == 0:
                logger.info(f"  {short:12s}: NO DATA")
            else:
                status = "✅" if cov["days"] >= 600 else ("⚠️" if cov["days"] >= 180 else "❌")
                logger.info(f"  {short:12s}: {cov['count']:6d} candles | {cov['days']:.0f}d | "
                           f"{cov['first'].strftime('%Y-%m-%d')} → {cov['last'].strftime('%Y-%m-%d')} {status}")
        conn.close()
        return

    # Connect to Binance Futures
    exchange = ccxt.binance({
        'enableRateLimit': True,
        'options': {'defaultType': 'future'},
    })
    try:
        exchange.load_markets()
    except Exception as e:
        logger.error(f"Failed to connect to Binance Futures: {e}")
        sys.exit(1)

    available = set(exchange.symbols)
    total_new = 0
    coins_updated = 0
    coins_skipped = 0
    coins_failed = 0

    logger.info(f"Starting Binance backfill — {len(coins)} coins")
    logger.info(f"Database: {DB_PATH}")

    for db_sym, binance_sym in coins:
        short = db_sym.split("/")[0]

        if binance_sym not in available:
            logger.warning(f"  {short}: {binance_sym} not on Binance Futures — skipping")
            coins_skipped += 1
            continue

        cov = get_coverage(conn, db_sym)

        if cov["count"] > 0 and cov["days"] >= 600:
            # Already have 600+ days — just extend forward
            since_ms = cov["last"] - timedelta(hours=INCREMENTAL_BUFFER_HOURS)
            since_ms = int(since_ms.timestamp() * 1000)
            logger.info(f"  {short}: existing {cov['days']:.0f}d ✅ — extending forward only")
        elif cov["count"] > 0:
            # Have data but < 600 days — backfill backwards THEN extend forward
            logger.info(f"  {short}: existing {cov['days']:.0f}d — need backward backfill + forward extend")
        else:
            logger.info(f"  {short}: no data — full backfill from Binance start")

        try:
            new_count = 0

            if cov["count"] > 0 and cov["days"] < 600:
                # Phase 1: Backward backfill (from 2019 up to existing first candle)
                backward_start = int(datetime(2019, 1, 1, tzinfo=timezone.utc).timestamp() * 1000)
                backward_end   = int(cov["first"].timestamp() * 1000)
                logger.info(f"  {short}: backward fill 2019-01-01 → {cov['first'].strftime('%Y-%m-%d')}")
                backward_candles = fetch_candles_from(exchange, binance_sym, backward_start, db_sym)
                # Only keep candles before existing data
                backward_candles = [c for c in backward_candles if c[0] < backward_end]
                new_count += store_candles(conn, db_sym, backward_candles)
                logger.info(f"  {short}: +{new_count} backward candles")

                # Phase 2: Forward extend
                forward_since = cov["last"] - timedelta(hours=INCREMENTAL_BUFFER_HOURS)
                forward_since = int(forward_since.timestamp() * 1000)
                forward_candles = fetch_candles_from(exchange, binance_sym, forward_since, db_sym)
                fwd_count = store_candles(conn, db_sym, forward_candles)
                new_count += fwd_count

            elif cov["count"] > 0:
                # Already >= 600d, just extend forward
                since_ms = cov["last"] - timedelta(hours=INCREMENTAL_BUFFER_HOURS)
                since_ms = int(since_ms.timestamp() * 1000)
                candles = fetch_candles_from(exchange, binance_sym, since_ms, db_sym)
                new_count = store_candles(conn, db_sym, candles)

            else:
                # No data at all — full backfill
                since_ms = int(datetime(2019, 1, 1, tzinfo=timezone.utc).timestamp() * 1000)
                candles = fetch_candles_from(exchange, binance_sym, since_ms, db_sym)
                new_count = store_candles(conn, db_sym, candles)

            total_new += new_count
            coins_updated += 1

            cov_after = get_coverage(conn, db_sym)
            status = "✅" if cov_after["days"] >= 600 else ("⚠️" if cov_after["days"] >= 180 else "❌")
            logger.info(f"  {short}: +{new_count} new | {cov_after['days']:.0f}d total {status}")
        except Exception as e:
            logger.error(f"  {short}: FAILED — {e}")
            coins_failed += 1

        time.sleep(1.0)  # Be nice to Binance

    conn.close()
    logger.info(f"\nDone. {coins_updated} coins updated | {total_new} new candles | "
                f"{coins_skipped} skipped | {coins_failed} failed")
    logger.info("Next step: run resample_daily.py to generate daily candles")
    logger.info("Then: run v14_cycle_scanner.py to generate initial scores")


if __name__ == "__main__":
    main()
