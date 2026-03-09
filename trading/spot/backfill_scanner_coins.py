#!/usr/bin/env python3
"""
Backfill 1h and daily candle data for 18 missing Hyperliquid coins.
Uses Binance via CCXT for both timeframes.
"""

import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace', line_buffering=True)
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace', line_buffering=True)

import ccxt
import sqlite3
import time
from datetime import datetime, timezone
from pathlib import Path

DB_PATH = Path(os.environ.get("AIT_CANDLES_DB", str(Path(__file__).parent / "data" / "candles.db")))

# Coins to backfill: (db_symbol, binance_symbol, approx_start_date)
# We use early start dates - Binance will just return from when data is available
COINS = [
    ("COMP/USDT",   "COMP/USDT",   "2020-06-01"),
    ("DYDX/USDT",   "DYDX/USDT",   "2021-09-01"),
    ("EIGEN/USDT",  "EIGEN/USDT",  "2024-10-01"),
    ("ENA/USDT",    "ENA/USDT",    "2024-04-01"),
    ("ENS/USDT",    "ENS/USDT",    "2021-11-01"),
    ("KAS/USDT",    "KAS/USDT",    "2023-11-01"),
    ("LDO/USDT",    "LDO/USDT",    "2022-08-01"),
    ("MKR/USDT",    "MKR/USDT",    "2020-06-01"),
    ("ONDO/USDT",   "ONDO/USDT",   "2024-01-01"),
    ("OP/USDT",     "OP/USDT",     "2022-06-01"),
    ("PENDLE/USDT", "PENDLE/USDT", "2023-07-01"),
    ("PYTH/USDT",   "PYTH/USDT",   "2023-11-01"),
    ("RENDER/USDT", "RENDER/USDT", "2020-06-01"),  # Try RENDER first, fallback to RNDR
    ("SNX/USDT",    "SNX/USDT",    "2020-03-01"),
    ("STX/USDT",    "STX/USDT",    "2021-10-01"),
    ("TIA/USDT",    "TIA/USDT",    "2023-11-01"),
    ("W/USDT",      "W/USDT",      "2024-04-01"),
    ("ZRO/USDT",    "ZRO/USDT",    "2024-06-01"),
]

# Fallback symbols for coins that might be listed differently
FALLBACKS = {
    "RENDER/USDT": "RNDR/USDT",
}


def date_to_ms(date_str):
    return int(datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc).timestamp() * 1000)


def ms_to_date(ms):
    return datetime.fromtimestamp(ms / 1000, tz=timezone.utc).strftime("%Y-%m-%d")


def ms_to_datetime(ms):
    return datetime.fromtimestamp(ms / 1000, tz=timezone.utc).strftime("%Y-%m-%d %H:%M")


def fetch_candles(exchange, symbol, timeframe, since_ms):
    """Fetch all candles from since_ms to now with pagination."""
    all_candles = []
    current_since = since_ms
    now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
    consecutive_errors = 0

    while current_since < now_ms:
        try:
            candles = exchange.fetch_ohlcv(symbol, timeframe, since=current_since, limit=1000)
            consecutive_errors = 0
            if not candles:
                break
            all_candles.extend(candles)
            last_ts = candles[-1][0]
            if last_ts <= current_since:
                break
            current_since = last_ts + 1
            # Progress every 5000 candles
            if len(all_candles) % 5000 < 1000:
                print(f"    ... {len(all_candles)} candles, up to {ms_to_datetime(last_ts)}")
            time.sleep(0.3)
        except Exception as e:
            consecutive_errors += 1
            print(f"    Error at {ms_to_datetime(current_since)}: {e}")
            if consecutive_errors >= 3:
                print(f"    Giving up after {consecutive_errors} consecutive errors")
                break
            time.sleep(2)

    return all_candles


def save_hourly(conn, symbol, candles):
    """Save 1h candles to candles table."""
    if not candles:
        return
    conn.executemany(
        "INSERT OR REPLACE INTO candles (symbol, timeframe, timestamp, open, high, low, close, volume) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        [(symbol, '1h', c[0], c[1], c[2], c[3], c[4], c[5]) for c in candles]
    )
    conn.commit()


def save_daily(conn, symbol, candles):
    """Save daily candles to candles_daily table."""
    if not candles:
        return
    conn.executemany(
        "INSERT OR REPLACE INTO candles_daily (symbol, timestamp, open, high, low, close, volume) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        [(symbol, c[0], c[1], c[2], c[3], c[4], c[5]) for c in candles]
    )
    conn.commit()


def try_fetch(exchange, symbol, timeframe, since_ms, fallback=None):
    """Try fetching with primary symbol, fall back if needed. Returns (actual_symbol, candles)."""
    try:
        candles = fetch_candles(exchange, symbol, timeframe, since_ms)
        if candles:
            return symbol, candles
    except Exception as e:
        print(f"    Primary {symbol} failed: {e}")

    if fallback:
        print(f"    Trying fallback: {fallback}")
        try:
            candles = fetch_candles(exchange, fallback, timeframe, since_ms)
            if candles:
                return fallback, candles
        except Exception as e:
            print(f"    Fallback {fallback} also failed: {e}")

    return symbol, []


def main():
    print("=" * 60)
    print("Backfilling 18 scanner coins from Binance")
    print("=" * 60)

    conn = sqlite3.connect(str(DB_PATH))
    
    exchange = ccxt.binance()
    exchange.load_markets()

    total_hourly = 0
    total_daily = 0
    success = []
    failed = []

    # Check which coins already have data (for resume)
    already_done = set()
    for db_symbol, _, _ in COINS:
        cur = conn.execute('SELECT COUNT(*) FROM candles WHERE symbol=? AND timeframe=?', (db_symbol, '1h'))
        if cur.fetchone()[0] > 1000:
            already_done.add(db_symbol)

    for db_symbol, binance_symbol, start_date in COINS:
        print(f"\n{'='*40}")
        print(f"  {db_symbol}")
        print(f"{'='*40}")

        if db_symbol in already_done:
            print(f"  Already has data, skipping...")
            success.append(db_symbol)
            continue

        since_ms = date_to_ms(start_date)
        # For daily, go back further for SMA200 warmup
        daily_since_ms = min(since_ms, date_to_ms("2023-01-01"))
        fallback = FALLBACKS.get(binance_symbol)

        # --- 1h candles ---
        # For 1h, start from Jan 2024 at earliest (that's what scanner needs)
        hourly_since = max(since_ms, date_to_ms("2024-01-01"))
        print(f"  Fetching 1h from {ms_to_date(hourly_since)}...")
        actual_sym, hourly = try_fetch(exchange, binance_symbol, '1h', hourly_since, fallback)
        
        if hourly:
            save_hourly(conn, db_symbol, hourly)
            h_min = ms_to_date(hourly[0][0])
            h_max = ms_to_date(hourly[-1][0])
            print(f"  1h: {len(hourly)} candles ({h_min} -> {h_max})")
            total_hourly += len(hourly)
        else:
            print(f"  1h: NO DATA")

        # --- Daily candles ---
        print(f"  Fetching daily from {ms_to_date(daily_since_ms)}...")
        actual_sym_d, daily = try_fetch(exchange, actual_sym if hourly else binance_symbol, '1d', daily_since_ms, fallback)
        
        if daily:
            save_daily(conn, db_symbol, daily)
            d_min = ms_to_date(daily[0][0])
            d_max = ms_to_date(daily[-1][0])
            print(f"  daily: {len(daily)} candles ({d_min} -> {d_max})")
            total_daily += len(daily)
        else:
            print(f"  daily: NO DATA")

        if hourly or daily:
            success.append(db_symbol)
        else:
            failed.append(db_symbol)

    # --- Summary ---
    print(f"\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")
    print(f"  Success: {len(success)}/{len(COINS)} coins")
    print(f"  Total 1h candles: {total_hourly:,}")
    print(f"  Total daily candles: {total_daily:,}")
    if failed:
        print(f"  Failed: {', '.join(failed)}")
    
    # Verification
    print(f"\nVERIFICATION:")
    for db_symbol, _, _ in COINS:
        cur = conn.execute(
            'SELECT MIN(timestamp), MAX(timestamp), COUNT(*) FROM candles WHERE symbol=? AND timeframe=?',
            (db_symbol, '1h')
        )
        h = cur.fetchone()
        cur2 = conn.execute(
            'SELECT MIN(timestamp), MAX(timestamp), COUNT(*) FROM candles_daily WHERE symbol=?',
            (db_symbol,)
        )
        d = cur2.fetchone()
        h_str = f"{h[2]} ({ms_to_date(h[0])}-{ms_to_date(h[1])})" if h and h[2] else "NONE"
        d_str = f"{d[2]} ({ms_to_date(d[0])}-{ms_to_date(d[1])})" if d and d[2] else "NONE"
        print(f"  {db_symbol:15s}  1h: {h_str:>35s}  daily: {d_str}")

    conn.close()
    print("\nDone!")


if __name__ == "__main__":
    main()
