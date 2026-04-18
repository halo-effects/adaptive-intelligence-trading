#!/usr/bin/env python3
"""
Incremental 1h candle collector for V14 DCA Cycle Scanner.

Pulls latest 1h candles from Hyperliquid (perps) for all scanner coins,
stores in candles.db. Only fetches from the last stored timestamp forward.

Designed to run hourly via scheduled task.
"""

import ccxt
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
# Must match v14_cycle_scanner.py COINS list.
# Format: (db_symbol, hyperliquid_perp_symbol)
# Hyperliquid perps all trade as COIN/USDC:USDC

COINS = [
    # --- Established (pre-2024) ---
    ("BTC/USDC",    "BTC/USDC:USDC"),
    ("ETH/USDC",    "ETH/USDC:USDC"),
    ("SOL/USDT",    "SOL/USDC:USDC"),    # DB stores as USDT, HL uses USDC perp
    ("XRP/USDT",    "XRP/USDC:USDC"),
    ("LINK/USDT",   "LINK/USDC:USDC"),
    ("DOGE/USDT",   "DOGE/USDC:USDC"),
    ("ADA/USDT",    "ADA/USDC:USDC"),
    ("LTC/USDT",    "LTC/USDC:USDC"),
    ("AVAX/USDT",   "AVAX/USDC:USDC"),
    ("DOT/USDT",    "DOT/USDC:USDC"),
    ("UNI/USDT",    "UNI/USDC:USDC"),
    ("ATOM/USDT",   "ATOM/USDC:USDC"),
    ("NEAR/USDT",   "NEAR/USDC:USDC"),
    ("HBAR/USDT",   "HBAR/USDC:USDC"),
    ("INJ/USDT",    "INJ/USDC:USDC"),
    ("FIL/USDT",    "FIL/USDC:USDC"),
    ("RUNE/USDT",   "RUNE/USDC:USDC"),
    ("CRV/USDT",    "CRV/USDC:USDC"),
    ("SNX/USDT",    "SNX/USDC:USDC"),
    ("COMP/USDT",   "COMP/USDC:USDC"),
    ("MKR/USDT",    "MKR/USDC:USDC"),
    ("ENS/USDT",    "ENS/USDC:USDC"),
    ("DYDX/USDT",   "DYDX/USDC:USDC"),
    ("LDO/USDT",    "LDO/USDC:USDC"),
    ("ARB/USDT",    "ARB/USDC:USDC"),
    ("OP/USDT",     "OP/USDC:USDC"),
    ("STX/USDT",    "STX/USDC:USDC"),
    ("SEI/USDT",    "SEI/USDC:USDC"),
    ("RENDER/USDT", "RENDER/USDC:USDC"),
    # --- 2024 launches ---
    ("SUI/USDT",    "SUI/USDC:USDC"),
    ("FET/USDT",    "FET/USDC:USDC"),
    ("TAO/USDT",    "TAO/USDC:USDC"),
    ("TON/USDT",    "TON/USDC:USDC"),
    ("JUP/USDT",    "JUP/USDC:USDC"),
    ("KAS/USDT",    "KAS/USDC:USDC"),
    ("PENDLE/USDT", "PENDLE/USDC:USDC"),
    ("PYTH/USDT",   "PYTH/USDC:USDC"),
    ("TIA/USDT",    "TIA/USDC:USDC"),
    ("ONDO/USDT",   "ONDO/USDC:USDC"),
    ("ENA/USDT",    "ENA/USDC:USDC"),
    ("EIGEN/USDT",  "EIGEN/USDC:USDC"),
    ("W/USDT",      "W/USDC:USDC"),
    ("ZRO/USDT",    "ZRO/USDC:USDC"),
    # --- Mid-cycle 2025 ---
    ("HYPE/USDC",   "HYPE/USDC:USDC"),
    # --- AAVE ---
    ("AAVE/USDT",   "AAVE/USDC:USDC"),
]

# ASTER is on a different exchange — handled separately by the live bot.
# The scanner will use whatever ASTER data exists in the DB already.
# If we need fresh ASTER candles, that requires the Aster exchange client.

# Also pull USDC-quoted versions that may exist in the DB
USDC_COINS = [
    ("LINK/USDC",   "LINK/USDC:USDC"),
    ("XRP/USDC",    "XRP/USDC:USDC"),
    ("SOL/USDC",    "SOL/USDC:USDC"),
    ("ETH/USDC",    "ETH/USDC:USDC"),
    ("BTC/USDC",    "BTC/USDC:USDC"),
]

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


def fetch_candles(exchange, hl_symbol: str, since_ms: int) -> list:
    """Fetch 1h candles from Hyperliquid, paginating forward."""
    all_candles = []
    cursor = since_ms
    now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)

    retries = 0
    max_retries = 3

    while cursor < now_ms:
        try:
            batch = exchange.fetch_ohlcv(hl_symbol, "1h", since=cursor, limit=1000)
            retries = 0  # Reset on success
        except Exception as e:
            if "429" in str(e) and retries < max_retries:
                retries += 1
                wait = 5 * retries
                logger.info(f"  Rate limited on {hl_symbol}, waiting {wait}s (retry {retries}/{max_retries})")
                time.sleep(wait)
                continue
            logger.warning(f"  Error fetching {hl_symbol} from {cursor}: {e}")
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


def store_candles(conn: sqlite3.Connection, db_symbol: str, candles: list) -> int:
    """Store 1h candles in DB. Returns count of new rows inserted."""
    if not candles:
        return 0

    before = conn.execute(
        "SELECT COUNT(*) FROM candles WHERE symbol = ? AND timeframe = '1h'",
        (db_symbol,)
    ).fetchone()[0]

    conn.executemany(
        "INSERT OR IGNORE INTO candles (symbol, timeframe, timestamp, open, high, low, close, volume) "
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
    if not DB_PATH.exists():
        logger.error(f"Database not found: {DB_PATH}")
        sys.exit(1)

    conn = sqlite3.connect(str(DB_PATH))
    init_db(conn)

    # Build deduplicated coin list (avoid pulling same HL symbol twice)
    seen_hl = set()
    coin_list = []
    for db_sym, hl_sym in COINS + USDC_COINS:
        key = (db_sym, hl_sym)
        if key not in seen_hl:
            seen_hl.add(key)
            coin_list.append((db_sym, hl_sym))

    logger.info(f"Candle Collector — {len(coin_list)} coins from Hyperliquid")

    # Connect to Hyperliquid
    hl = ccxt.hyperliquid()
    try:
        hl.load_markets()
    except Exception as e:
        logger.error(f"Failed to connect to Hyperliquid: {e}")
        sys.exit(1)

    available_symbols = set(hl.symbols)
    total_new = 0
    coins_updated = 0
    coins_skipped = 0
    coins_failed = 0

    for db_sym, hl_sym in coin_list:
        short = db_sym.split("/")[0]

        # Check if symbol exists on Hyperliquid
        if hl_sym not in available_symbols:
            logger.warning(f"  {short}: {hl_sym} not available on Hyperliquid, skipping")
            coins_skipped += 1
            continue

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
            candles = fetch_candles(hl, hl_sym, since_ms)
            new_count = store_candles(conn, db_sym, candles)
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
