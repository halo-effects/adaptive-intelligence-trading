#!/usr/bin/env python3
"""
Incremental 1h candle collector for V14 DCA Cycle Scanner.

Pulls latest 1h candles from Aster DEX (perps) for all scanner coins,
stores in candles.db. Only fetches from the last stored timestamp forward.

Switched from Hyperliquid to Aster (2026-04-17) to match the production
exchange. Several scanner coins (ORCA, TRUMP, BERA, VIRTUAL, etc.) are
only available on Aster.

Designed to run hourly via scheduled task.
"""

import ccxt
import os
import sqlite3
import sys
import io
import time
import logging
from datetime import datetime, timezone, timedelta
from pathlib import Path

# Force UTF-8 on Windows
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("candle_collector")

DB_PATH = Path(os.environ.get("AIT_CANDLES_DB", str(Path(__file__).parent / "data" / "candles.db")))

# ── Scanner universe ────────────────────────────────────────────────────────
# Must match v14_cycle_scanner.py COINS list exactly (50 coins).
# Format: (db_symbol, aster_perp_symbol)
# Aster perps trade as {COIN}/USDT:USDT.
# PEPE, BONK, FLOKI use 1000-prefix on Aster (1000PEPE/USDT:USDT).
# DB stores as standard symbol (PEPE/USDT) — prices are scaled back.

COINS = [
    # --- Established (pre-2024) — 19 coins ---
    ("BTC/USDT",     "BTC/USDT:USDT"),
    ("ETH/USDT",     "ETH/USDT:USDT"),
    ("SOL/USDT",     "SOL/USDT:USDT"),
    ("XRP/USDT",     "XRP/USDT:USDT"),
    ("LINK/USDT",    "LINK/USDT:USDT"),
    ("DOGE/USDT",    "DOGE/USDT:USDT"),
    ("ADA/USDT",     "ADA/USDT:USDT"),
    ("LTC/USDT",     "LTC/USDT:USDT"),
    ("AVAX/USDT",    "AVAX/USDT:USDT"),
    ("DOT/USDT",     "DOT/USDT:USDT"),
    ("UNI/USDT",     "UNI/USDT:USDT"),
    ("ATOM/USDT",    "ATOM/USDT:USDT"),
    ("NEAR/USDT",    "NEAR/USDT:USDT"),
    ("HBAR/USDT",    "HBAR/USDT:USDT"),
    ("INJ/USDT",     "INJ/USDT:USDT"),
    ("FIL/USDT",     "FIL/USDT:USDT"),
    ("CRV/USDT",     "CRV/USDT:USDT"),
    ("SNX/USDT",     "SNX/USDT:USDT"),
    ("ZEC/USDT",     "ZEC/USDT:USDT"),
    # --- DeFi / Mid-cap — 6 coins ---
    ("AAVE/USDT",    "AAVE/USDT:USDT"),
    ("ARB/USDT",     "ARB/USDT:USDT"),
    ("JUP/USDT",     "JUP/USDT:USDT"),
    ("PENDLE/USDT",  "PENDLE/USDT:USDT"),
    ("STX/USDT",     "STX/USDT:USDT"),
    ("ZRO/USDT",     "ZRO/USDT:USDT"),
    # --- High-beta / Speculative — 9 coins ---
    ("PEPE/USDT",    "1000PEPE/USDT:USDT"),
    ("BONK/USDT",    "1000BONK/USDT:USDT"),
    ("FLOKI/USDT",   "1000FLOKI/USDT:USDT"),
    ("JTO/USDT",     "JTO/USDT:USDT"),
    ("PYTH/USDT",    "PYTH/USDT:USDT"),
    ("TIA/USDT",     "TIA/USDT:USDT"),
    ("SEI/USDT",     "SEI/USDT:USDT"),
    ("APT/USDT",     "APT/USDT:USDT"),
    ("SUI/USDT",     "SUI/USDT:USDT"),
    # --- AI / Infrastructure — 5 coins ---
    ("FET/USDT",     "FET/USDT:USDT"),
    ("TAO/USDT",     "TAO/USDT:USDT"),
    ("HYPE/USDT",    "HYPE/USDT:USDT"),
    ("VIRTUAL/USDT", "VIRTUAL/USDT:USDT"),
    ("RENDER/USDT",  "RENDER/USDT:USDT"),
    # --- New L1/L2 — 5 coins ---
    ("BERA/USDT",    "BERA/USDT:USDT"),
    ("MOVE/USDT",    "MOVE/USDT:USDT"),
    ("INIT/USDT",    "INIT/USDT:USDT"),
    ("S/USDT",       "S/USDT:USDT"),
    ("IP/USDT",      "IP/USDT:USDT"),
    # --- Yield / RWA — 3 coins ---
    ("ONDO/USDT",    "ONDO/USDT:USDT"),
    ("EIGEN/USDT",   "EIGEN/USDT:USDT"),
    ("ENA/USDT",     "ENA/USDT:USDT"),
    # --- DePIN / Other — 3 coins ---
    ("GRASS/USDT",   "GRASS/USDT:USDT"),
    ("ORCA/USDT",    "ORCA/USDT:USDT"),
    ("TRUMP/USDT",   "TRUMP/USDT:USDT"),
]

# 1000-prefix coins: prices on Aster are 1000x the "real" price.
# We divide by 1000 when storing so DB matches the standard symbol.
PREFIX_1000_COINS = {"1000PEPE/USDT:USDT", "1000BONK/USDT:USDT", "1000FLOKI/USDT:USDT"}

# Default lookback for first-time pull (days)
DEFAULT_LOOKBACK_DAYS = 365 * 2  # 2 years
# Incremental lookback buffer (hours) to catch any gaps
INCREMENTAL_BUFFER_HOURS = 6


def init_db(conn: sqlite3.Connection):
    """Ensure candles table exists."""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS candles (
            symbol TEXT, timeframe TEXT, timestamp INTEGER,
            open REAL, high REAL, low REAL, close REAL, volume REAL,
            PRIMARY KEY (symbol, timeframe, timestamp)
        )
    """)
    conn.commit()


def get_last_timestamp(conn: sqlite3.Connection, symbol: str) -> int | None:
    """Get the latest 1h candle timestamp for a symbol."""
    row = conn.execute(
        "SELECT MAX(timestamp) FROM candles WHERE symbol = ? AND timeframe = '1h'",
        (symbol,)
    ).fetchone()
    return row[0] if row and row[0] else None


def fetch_candles(exchange, aster_symbol: str, since_ms: int) -> list:
    """Fetch 1h candles from Aster, paginating forward."""
    all_candles = []
    cursor = since_ms
    now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)

    retries = 0
    max_retries = 3

    while cursor < now_ms:
        try:
            batch = exchange.fetch_ohlcv(aster_symbol, "1h", since=cursor, limit=1000)
            retries = 0  # Reset on success
        except Exception as e:
            if "429" in str(e) and retries < max_retries:
                retries += 1
                wait = 5 * retries
                logger.info(f"  Rate limited on {aster_symbol}, waiting {wait}s (retry {retries}/{max_retries})")
                time.sleep(wait)
                continue
            logger.warning(f"  Error fetching {aster_symbol} from {cursor}: {e}")
            break

        if not batch:
            break

        all_candles.extend(batch)
        last_ts = batch[-1][0]

        if last_ts <= cursor:
            break
        cursor = last_ts + 1

        time.sleep(0.5)  # Rate limit — 0.5s between pages

    # Deduplicate
    seen = set()
    unique = []
    for c in all_candles:
        if c[0] not in seen:
            seen.add(c[0])
            unique.append(c)

    unique.sort(key=lambda x: x[0])
    return unique


def store_candles(conn: sqlite3.Connection, db_symbol: str, candles: list, scale: float = 1.0) -> int:
    """Store 1h candles in DB. Returns count of new rows inserted.
    
    Args:
        scale: Price scaling factor. 1/1000 for 1000PEPE etc.
    """
    if not candles:
        return 0

    before = conn.execute(
        "SELECT COUNT(*) FROM candles WHERE symbol = ? AND timeframe = '1h'",
        (db_symbol,)
    ).fetchone()[0]

    conn.executemany(
        "INSERT OR IGNORE INTO candles (symbol, timeframe, timestamp, open, high, low, close, volume) "
        "VALUES (?, '1h', ?, ?, ?, ?, ?, ?)",
        [
            (db_symbol, c[0],
             c[1] * scale, c[2] * scale, c[3] * scale, c[4] * scale,
             c[5])
            for c in candles
        ]
    )
    conn.commit()

    after = conn.execute(
        "SELECT COUNT(*) FROM candles WHERE symbol = ? AND timeframe = '1h'",
        (db_symbol,)
    ).fetchone()[0]

    return after - before


def main():
    if not DB_PATH.exists():
        logger.error(f"Database not found: {DB_PATH}")
        sys.exit(1)

    conn = sqlite3.connect(str(DB_PATH))
    init_db(conn)

    logger.info(f"Candle Collector — {len(COINS)} coins from Aster DEX")

    # Connect to Aster
    aster = ccxt.aster({
        "apiKey": os.environ.get("ASTER_API_KEY", ""),
        "secret": os.environ.get("ASTER_API_SECRET", ""),
    })
    try:
        aster.load_markets()
    except Exception as e:
        logger.error(f"Failed to connect to Aster: {e}")
        sys.exit(1)

    available_symbols = set(aster.symbols)
    total_new = 0
    coins_updated = 0
    coins_skipped = 0
    coins_failed = 0

    for db_sym, aster_sym in COINS:
        short = db_sym.split("/")[0]

        # Check if symbol exists on Aster
        if aster_sym not in available_symbols:
            logger.warning(f"  {short}: {aster_sym} not available on Aster, skipping")
            coins_skipped += 1
            continue

        # Price scaling for 1000-prefix coins
        scale = 1.0 / 1000.0 if aster_sym in PREFIX_1000_COINS else 1.0

        # Determine start point
        last_ts = get_last_timestamp(conn, db_sym)
        if last_ts:
            # Incremental: start from last timestamp minus buffer
            since_ms = last_ts - (INCREMENTAL_BUFFER_HOURS * 3600 * 1000)
            mode = "incremental"
        else:
            # First time: pull full history
            since_ms = int(
                (datetime.now(timezone.utc) - timedelta(days=DEFAULT_LOOKBACK_DAYS))
                .timestamp() * 1000
            )
            mode = "full"

        try:
            candles = fetch_candles(aster, aster_sym, since_ms)
            new_count = store_candles(conn, db_sym, candles, scale=scale)
            total_new += new_count

            if new_count > 0:
                coins_updated += 1
                logger.info(f"  {short}: +{new_count} new candles ({mode}, {len(candles)} fetched)")
            else:
                logger.info(f"  {short}: up to date ({len(candles)} checked)")
        except Exception as e:
            logger.error(f"  {short}: FAILED — {e}")
            coins_failed += 1

        # Pause between coins to avoid rate limits
        time.sleep(0.8)

    conn.close()

    logger.info(f"Done. {coins_updated} coins updated, {total_new} new candles, "
                f"{coins_skipped} skipped, {coins_failed} failed.")


if __name__ == "__main__":
    main()
